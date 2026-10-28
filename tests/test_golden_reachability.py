"""Reachability: every golden cell, run through the REAL pipeline with a free stub, fires the calls expected.

`tests/test_eval_spend.py` ties the runner's call plan to a stub of the FUNCTIONS `run_suite` calls, so
a gate inside one of those functions (``recommend_summaries`` makes no call below two summary variants)
is invisible to it. This test stubs one level lower: the Anthropic client. `analyzer._call_llm_streaming`
is wrapped so the client learns each call's kind, and the real ``analyze``, ``clarify``, ``generate``,
``recommend_*`` and the judges run against replies built from the cell's own résumé and seed. What
fired is read from the telemetry rows.

It asserts, per fixture, that the kinds fired equal the plan (plus ``recommend_summary`` exactly when
the cell holds two summary variants); for the whole suite, that nothing errored, retried or was
rewritten; and that `golden_set.REACHABILITY` names every catalog kind, with its ``run_suite`` rows equal
to the runner's own declared tables. A cell built with one summary variant is the control arm: its
predicate fails AND the call does not fire, so the static check and the behaviour agree.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import analyzer
from evals import eval_catalog as cat
from evals import golden_author as ga
from evals import golden_set as gs
from evals import runner
from tests.test_golden_author import _Client as _AuthorClient
from tests.test_golden_set import FACTS, _ladder, _manifest

EXTRACTION = {
    "essential_skills": ["kubernetes"],
    "preferred_skills": ["terraform"],
    "industry_keywords": ["sre"],
    "hidden_qualities": [{"category": "operating_context", "signal": "regulated, workflow-heavy"}],
    "professional_vocabulary": ["slo"],
    "keyword_placement": [
        {"keyword": "kubernetes", "suggested_location": "Experience", "how": "x"}
    ],
}
SYNTHESIS = {
    "comparison": {"strengths": [], "gaps": ["none"], "title_alignment": "ok"},
    "suggestions": [{"section": "Skills", "action": "add", "rationale": "gap"}],
    "overall_strategy": "Position the candidate plainly.",
}
CLARIFY = {
    "questions": [
        {
            "id": "q1",
            "kind": "context_probe",
            "question": "Any regulated-industry work?",
            "why": "w",
        },
        {
            "id": "q2",
            "kind": "experience_probe",
            "question": "Any exposure to Terraform?",
            "why": "w",
        },
    ],
    "reasoning": "Probing the gaps.",
}
ITERATION_CLARIFY = {
    "questions": [
        {"id": "iter1_q1", "kind": "iteration_probe", "question": "Which services?", "why": "w"},
        {"id": "iter1_q2", "kind": "experience_probe", "question": "Any tracing work?", "why": "w"},
    ],
    "reasoning": "Following up on the edit.",
}
JUDGE = {"score": 4, "summary": "fine", "reasons": ["fine"], "failed_rules": []}


class _Usage:
    input_tokens = 100
    output_tokens = 20
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    service_tier = "standard"
    speed = "standard"
    inference_geo = "not_available"


class _Final:
    stop_reason = "end_turn"
    model = "claude-stub"
    usage = _Usage()


class _Stream:
    def __init__(self, text: str) -> None:
        self._text = text
        self.request_id = "req_stub"

    def __enter__(self) -> _Stream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    @property
    def text_stream(self) -> Any:
        yield self._text

    def get_final_message(self) -> _Final:
        return _Final()


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"
        self.model = "claude-stub"
        self.usage = _Usage()
        self._request_id = "req_judge_stub"


class _StubClient:
    """Speaks both client surfaces the pipeline uses; replies by call kind and by case."""

    def __init__(self, cases: dict[str, dict[str, Any]]) -> None:
        self.cases = cases
        self.pending_kind = ""
        self.messages = self  # `client.messages.stream` and `client.messages.create`

    def _case(self) -> dict[str, Any]:
        ctx = analyzer._trace_ctx.get()
        assert ctx is not None and ctx.case_id in self.cases, f"no case for {ctx}"
        return self.cases[ctx.case_id]

    def stream(self, **_: Any) -> _Stream:
        return _Stream(self._reply(self.pending_kind.removesuffix("_retry")))

    def create(self, **_: Any) -> _Message:
        return _Message(json.dumps(JUDGE))

    def _reply(self, kind: str) -> str:
        case = self._case()
        seed = case["seed"]
        if kind == "analyze_extraction":
            return json.dumps(EXTRACTION)
        if kind == "analyze_synthesis":
            return json.dumps(SYNTHESIS)
        if kind == "clarify":
            return json.dumps(CLARIFY)
        if kind == "iterate_clarify":
            return json.dumps(ITERATION_CLARIFY)
        if kind == "generate":
            return json.dumps(
                {
                    "resume_content": case["resume"],
                    "cover_letter_content": "Dear hiring team, I am writing about the role.",
                    "changes_made": [],
                    "proofread_notes": [],
                }
            )
        if kind == "generate_cover_letter":
            return json.dumps(
                {
                    "cover_letter_content": "Dear hiring team, I am writing about the role.",
                    "proofread_notes": [],
                }
            )
        if kind == "recommend":
            return json.dumps(
                {
                    "recommendations": [
                        {
                            "experience_id": exp["id"],
                            "bullet_ids": [b["id"] for b in exp["bullets"][:7]],
                            "rationale": "Fits the role.",
                        }
                        for exp in seed["experiences"]
                    ]
                }
            )
        if kind == "recommend_summary":
            return json.dumps(
                {
                    "recommendation": {
                        "summary_item_id": seed["summary_items"][0]["id"],
                        "rationale": "Fits.",
                    },
                    "alternates": [],
                }
            )
        raise AssertionError(f"the stub has no reply for call kind {kind!r}; a new kind fired")


def _cases(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fdir in sorted(p for p in fixtures_dir.iterdir() if p.is_dir()):
        out[f"{gs.SUITE}/{fdir.name}"] = {
            "resume": (fdir / "resume.md").read_text(encoding="utf-8"),
            "seed": json.loads((fdir / "seed.json").read_text(encoding="utf-8")),
        }
    return out


def _run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, mode: str
) -> tuple[list[dict[str, Any]], dict[str, Counter[str]]]:
    """Run the suite at ``fixtures_dir`` and return ``(all rows, fired kinds per case_id)``."""
    rows: list[dict[str, Any]] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", rows.append)
    real = analyzer._call_llm_streaming

    def wrapper(client: Any, user_prompt: str, *, call_kind: str = "analyze", **kw: Any) -> Any:
        client.pending_kind = call_kind
        yield from real(client, user_prompt, call_kind=call_kind, **kw)

    monkeypatch.setattr(analyzer, "_call_llm_streaming", wrapper)
    monkeypatch.setattr(runner, "GOLDEN_DIR", fixtures_dir)
    result = runner.run_suite(
        suite="golden-v1",
        subset="full",
        mode=mode,
        out_dir=tmp_path / f"out-{mode}",
        client=_StubClient(_cases(fixtures_dir)),  # type: ignore[arg-type]
    )
    assert result.n_fail == 0, "a pipeline errored; the records say why"
    per_case: dict[str, Counter[str]] = {}
    for row in rows:
        per_case.setdefault(row["case_id"], Counter())[row["call"]] += 1
    return rows, per_case


def _planned(fdir: Path, profile: dict[str, Any], mode: str) -> Counter[str]:
    calls, _conditional, skipped = runner._call_plan(
        [fdir], runner._select_rubrics("full"), mode=mode, seed_mode=mode == "assemble"
    )
    assert not skipped
    plan = Counter(calls)
    if mode == "assemble" and "summary_variants" not in gs.failing_predicates(profile):
        plan["recommend_summary"] += 1
    return plan


def _check_rows(rows: list[dict[str, Any]]) -> None:
    assert rows
    assert [r["call"] for r in rows if r["call"].endswith("_retry")] == []
    assert {r["status"] for r in rows} == {"ok"}
    first_try = {r.get("parse_outcome") for r in rows if not r["call"].startswith("judge_")}
    assert first_try <= {"accepted_first_try"}, first_try


def _source_fixture(name: str) -> str:
    """The fixture whose corpus ``name`` runs on: itself, or a pair's résumé fixture."""
    if not name.startswith(gs.PAIR_PREFIX):
        return name
    pair = next(
        p for p in gs.load_manifest(gs.SUITE_DIR)["pairs"] if gs.pair_fixture_name(p["id"]) == name
    )
    return str(pair["resume_fixture"])


class TestCommittedPilots:
    @pytest.mark.parametrize("mode", ["generate", "assemble"])
    def test_each_pilot_fires_exactly_what_is_planned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
    ) -> None:
        rows, per_case = _run(tmp_path, monkeypatch, runner.GOLDEN_DIR, mode)
        _check_rows(rows)
        assert sorted(per_case) == sorted(
            f"{gs.SUITE}/{p.name}" for p in runner.GOLDEN_DIR.iterdir()
        )
        for fdir in sorted(runner.GOLDEN_DIR.iterdir()):
            # A pair runs on its résumé cell's corpus, so that cell's profile decides what is reachable.
            profile, _ = gs.load_cell(gs.SUITE_DIR, _source_fixture(fdir.name).split("--")[0])
            assert per_case[f"{gs.SUITE}/{fdir.name}"] == _planned(fdir, profile, mode), fdir.name

    def test_the_pilots_do_not_reach_recommend_summary_and_the_waiver_says_so(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, per_case = _run(tmp_path, monkeypatch, runner.GOLDEN_DIR, "assemble")
        assert all("recommend_summary" not in counts for counts in per_case.values())
        waivers = gs.load_manifest(gs.SUITE_DIR)["pilot_waivers"]
        assert all(
            any(
                w.endswith(":summary_variants")
                for w in waivers
                if w.startswith(_source_fixture(c.split("/")[1]))
            )
            for c in per_case
        )

    def test_the_iterating_pilot_reaches_iterate_clarify(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, per_case = _run(tmp_path, monkeypatch, runner.GOLDEN_DIR, "generate")
        assert per_case[f"{gs.SUITE}/sre-ops-mid--lattice-cloud"]["iterate_clarify"] == 1
        assert sum(c["iterate_clarify"] for c in per_case.values()) == 1


def _built_suite(tmp_path: Path, **ladder_override: Any) -> tuple[Path, dict[str, Any]]:
    """A one-cell suite made by the builder, the stub author and the renderer: no committed file involved."""
    root = tmp_path / "built" / gs.SUITE
    ladder = {**_ladder("mid"), **ladder_override}
    profile = gs.build_profile(FACTS, ladder, "mid")
    gs.write_cell(root, profile, ga.author_cell(_AuthorClient(), profile))
    (root / "facts").mkdir(parents=True, exist_ok=True)
    with (root / "facts" / "demo-ops.json").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(gs.canonical_json(FACTS))
    manifest = _manifest()
    manifest["author"]["prompt_versions"] = {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}
    if "summary_variants" in ladder_override:
        manifest["pilot_waivers"] = [
            f"{gs.fixture_name(profile['cell'], jd['slug'])}:summary_variants"
            for jd in profile["jds"]
        ]
    gs.write_manifest(root, manifest)
    return root, profile


class TestABuiltCell:
    @pytest.mark.parametrize("mode", ["generate", "assemble"])
    def test_a_built_cell_fires_exactly_what_is_planned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
    ) -> None:
        root, profile = _built_suite(tmp_path)
        assert gs.failing_predicates(profile) == []
        rows, per_case = _run(tmp_path, monkeypatch, root / "fixtures", mode)
        _check_rows(rows)
        for fdir in sorted((root / "fixtures").iterdir()):
            assert per_case[f"{gs.SUITE}/{fdir.name}"] == _planned(fdir, profile, mode), fdir.name

    def test_between_the_modes_it_reaches_every_kind_the_runner_can(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, _ = _built_suite(tmp_path)
        fired: set[str] = set()
        for mode in ("generate", "assemble"):
            _, per_case = _run(tmp_path, monkeypatch, root / "fixtures", mode)
            for counts in per_case.values():
                fired |= set(counts)
        reachable = {k for k, (how, _) in gs.REACHABILITY.items() if how == gs.RUN_SUITE}
        assert fired == reachable

    def test_one_summary_variant_fails_the_predicate_and_the_call_does_not_fire(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The control arm: this is the recommend_summary gap the check exists to catch.
        root, profile = _built_suite(tmp_path, summary_variants=1)
        assert gs.failing_predicates(profile) == ["summary_variants"]
        assert gs.check_suite(root, {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}) == []
        _, per_case = _run(tmp_path, monkeypatch, root / "fixtures", "assemble")
        assert all("recommend_summary" not in counts for counts in per_case.values())


class TestTheTie:
    def test_every_catalog_kind_has_a_reachability_entry_and_no_other(self) -> None:
        assert set(gs.REACHABILITY) == set(cat.names())

    def test_the_run_suite_rows_equal_the_runners_own_tables(self) -> None:
        declared: set[str] = set(runner._ITERATION_CALLS)
        for mode in ("generate", "assemble"):
            declared |= set(runner._FIXTURE_CALLS[mode]) | set(runner._CONDITIONAL_CALLS[mode])
        declared.add("judge_grade")  # one per rubric, counted by `_call_plan` outside the tables
        reachable = {k for k, (how, _) in gs.REACHABILITY.items() if how == gs.RUN_SUITE}
        assert reachable == declared

    def test_every_predicate_a_kind_names_exists(self) -> None:
        for kind, (how, predicate) in gs.REACHABILITY.items():
            assert how in (gs.RUN_SUITE, gs.STATIC, gs.INDEPENDENT, gs.EXEMPT), kind
            if how == gs.STATIC:
                assert predicate in gs.PREDICATES, kind
            if predicate is not None:
                assert predicate in gs.PREDICATES, kind

    def test_every_predicate_is_used_by_some_kind(self) -> None:
        used = {p for _, p in gs.REACHABILITY.values() if p is not None}
        assert used == set(gs.PREDICATES)

    def test_the_exempt_and_independent_kinds_are_the_known_two(self) -> None:
        assert {k for k, (how, _) in gs.REACHABILITY.items() if how == gs.EXEMPT} == {
            "dataset_author"
        }
        assert {k for k, (how, _) in gs.REACHABILITY.items() if how == gs.INDEPENDENT} == {
            "avatar_answer"
        }
        assert cat.load("dataset_author").status == "exempt"

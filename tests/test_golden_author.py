"""The golden-set prose generator (`evals/golden_author.py`), against a stub client. No paid call.

What is pinned: the request it sends (explicit adaptive thinking, an effort, no sampling parameters, the
author pin), the telemetry row it writes under ``dataset_author``, the checks every slot must pass, the
single bounded rewrite, the refusals it will not route around, and the command line's two guards
(``--confirm-paid`` and ``--max-spend``). The real call has never been made; these tests prove the code
around it, not the live request shape.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import analyzer
import hardening
from evals import golden_author as ga
from evals import golden_set as gs
from evals import runner
from tests.test_golden_set import FACTS, _built, _ladder, _suite, _text_for


class _Usage:
    def __init__(self, input_tokens: int = 1000, output_tokens: int = 500) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0
        self.service_tier = "standard"
        self.speed = "standard"
        self.inference_geo = "not_available"


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(
        self, text: str, *, stop_reason: str = "end_turn", usage: _Usage | None = None, n: int = 1
    ) -> None:
        self.content = [_Block(text)]
        self.stop_reason = stop_reason
        self.usage = usage or _Usage()
        self.model = ga.AUTHOR_MODEL
        self._request_id = f"req_author_{n}"


def _good_reply(prompt: str) -> str:
    """What a model that follows every rule would answer: text built from the specs in the prompt."""
    slots = json.loads(prompt)["slots"]
    return json.dumps({"slots": {sid: _text_for(spec) for sid, spec in slots.items()}})


class _Messages:
    """Scripted replies in order; a callable reply is given the user prompt. Records every request."""

    def __init__(self, script: list[Any] | None = None, usage: _Usage | None = None) -> None:
        self.script = list(script or [])
        self.usage = usage
        self.captured: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.captured.append(kwargs)
        prompt = kwargs["messages"][0]["content"]
        step = self.script.pop(0) if self.script else _good_reply
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, _Message):
            return step
        text = step(prompt) if callable(step) else step
        return _Message(text, usage=self.usage, n=len(self.captured))


class _Client:
    def __init__(self, script: list[Any] | None = None, usage: _Usage | None = None) -> None:
        self.messages = _Messages(script, usage)
        self.options: dict[str, Any] = {}

    def with_options(self, **options: Any) -> _Client:
        """The SDK's `with_options` returns a copy with the options set; the stub records them and returns itself."""
        self.options = options
        return self


@pytest.fixture
def rows(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", captured.append)
    return captured


@pytest.fixture
def real_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The call log in ``tmp_path``: rows really are written and read back, nothing touches the user's log."""
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(analyzer, "LOG_DIR", log_dir)
    monkeypatch.setattr(analyzer, "LOG_PATH", log_dir / "llm_calls.jsonl")
    return log_dir / "llm_calls.jsonl"


def _author_row(input_tokens: int = 0, output_tokens: int = 0, call: str = "dataset_author") -> str:
    return (
        json.dumps(
            {
                "call": call,
                "model": ga.AUTHOR_MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
        + "\n"
    )


def _corrupt(prompt: str, slot_id: str) -> str:
    """A reply that is right except for one slot, which carries a digit it may not."""
    data = json.loads(_good_reply(prompt))
    data["slots"][slot_id] += " 99 percent"
    return json.dumps(data)


class TestConstants:
    def test_the_pin_and_the_prompt_hash(self) -> None:
        assert ga.AUTHOR_MODEL == "claude-opus-5-5"
        assert ga.author_prompt_sha() == gs.sha256_text(ga.AUTHOR_SYSTEM_PROMPT)

    def test_the_author_is_not_a_product_pin(self) -> None:
        product = {analyzer.SONNET_MODEL, analyzer.HAIKU_MODEL, runner.JUDGE_MODEL}
        assert ga.AUTHOR_MODEL not in product
        assert (
            ga.AUTHOR_MODEL not in analyzer.THINKING_POLICY
        )  # not a legal product override target

    def test_the_prompt_text_has_not_moved(self) -> None:
        # Step 3b-ii changes the generator's guards, not what the model is told. A real change to
        # AUTHOR_SYSTEM_PROMPT or build_user_prompt must bump AUTHOR_PROMPT_VERSION and re-pin these.
        # The user prompt is pinned on a fixed literal profile, not on the builder's output, so that a
        # change to how a profile is built (which changes the briefs, not the prompt's shape) is not
        # mistaken for a change to the prompt.
        profile = {
            "level": "mid",
            "sections": [
                {
                    "kind": "experience",
                    "roles": [
                        {
                            "title": "Operator",
                            "company": "Alder Systems",
                            "start": "2024-01",
                            "end": None,
                        }
                    ],
                },
                {
                    "kind": "education",
                    "items": [
                        {
                            "degree": "B.S.",
                            "field": "Operations",
                            "institution": "State University",
                            "year": "2020",
                        }
                    ],
                },
                {
                    "kind": "certifications",
                    "items": [{"name": "Safety Card", "issuer": "Safety Council", "year": "2022"}],
                },
            ],
            "skills": [{"name": "Alphaflow"}],
            "jds": [
                {"slug": "bank", "header_lines": ["Operator", "Cedar Bank — Hybrid, Charlotte, NC"]}
            ],
            "slots": {
                "r1.b1": {
                    "kind": "bullet",
                    "brief": "One bullet.",
                    "must_include": ["Alphaflow"],
                    "allowed_numbers": [],
                    "min_words": 8,
                    "max_words": 40,
                }
            },
        }
        assert ga.AUTHOR_PROMPT_VERSION == "golden-author-1"
        assert (
            gs.sha256_text(ga.AUTHOR_SYSTEM_PROMPT)
            == "sha256:8551f43a3fc7970a648027fabacc3385512c124d94672cd463e3d5cfceaf8d1a"
        )
        assert (
            gs.sha256_text(ga.build_user_prompt(profile, ["r1.b1"]))
            == "sha256:3d71f24d45220f2f76ec927c0b725cf1350cd6f5182a3f2784aef5a3c393e7e5"
        )

    def test_the_author_model_is_priced(self) -> None:
        assert set(hardening.MODEL_PRICING[ga.AUTHOR_MODEL]) == {
            "in",
            "out",
            "cache_write",
            "cache_read",
        }


class TestRequest:
    def test_what_is_sent(self) -> None:
        profile, _ = _built()
        client = _Client()
        ga.author_cell(client, profile)
        (sent,) = client.messages.captured
        assert sent["model"] == ga.AUTHOR_MODEL
        assert sent["system"] == ga.AUTHOR_SYSTEM_PROMPT
        assert sent["thinking"] == {"type": "adaptive"}  # Opus 5.5 rejects disabled and a budget
        assert sent["output_config"] == {"effort": ga.AUTHOR_EFFORT}
        assert sent["max_tokens"] == ga.AUTHOR_MAX_TOKENS
        assert not {"temperature", "top_p", "top_k", "tool_choice", "stream"} & set(sent)
        assert [m["role"] for m in sent["messages"]] == ["user"]

    def test_the_prompt_carries_every_slot_brief_and_no_prose(self) -> None:
        profile, prose = _built()
        client = _Client()
        ga.author_cell(client, profile)
        content = client.messages.captured[0]["messages"][0]["content"]
        data = json.loads(content)
        assert sorted(data["slots"]) == sorted(profile["slots"])
        assert all(
            data["slots"][sid]["brief"] == profile["slots"][sid]["brief"]
            for sid in profile["slots"]
        )
        assert "rewrite" not in data
        assert data["facts"]["skills"] == [s["name"] for s in profile["skills"]]
        assert not any(text in content for text in prose["slots"].values())

    def test_the_prompt_is_deterministic(self) -> None:
        profile, _ = _built()
        ids = sorted(profile["slots"])
        assert ga.build_user_prompt(profile, ids) == ga.build_user_prompt(profile, ids)

    def test_the_prompt_names_the_certifications_a_cell_holds_and_only_then(self) -> None:
        # The system prompt forbids inventing a certification, so the model has to be told the real ones.
        plain, _ = _built()
        assert (
            "certifications" not in json.loads(ga.build_user_prompt(plain, ["summary.1"]))["facts"]
        )
        facts = FACTS | {
            "certifications": [
                {"name": "Journeyman Licence", "issuer": "State Board", "level": "mid"}
            ]
        }
        profile = gs.build_profile(facts, _ladder("mid"), "mid")
        sent = json.loads(ga.build_user_prompt(profile, ["summary.1"]))["facts"]["certifications"]
        assert [(c["name"], c["issuer"]) for c in sent] == [("Journeyman Licence", "State Board")]
        assert all(c["year"].isdigit() for c in sent)


class TestAuthorCell:
    def test_a_clean_reply_makes_sound_prose_in_one_request(self) -> None:
        profile, _ = _built()
        client = _Client()
        prose = ga.author_cell(client, profile)
        assert len(client.messages.captured) == 1
        assert gs.check_prose(profile, prose) == []
        assert sorted(prose["slots"]) == sorted(profile["slots"])

    def test_the_provenance_names_who_wrote_what(self) -> None:
        profile, _ = _built()
        prose = ga.author_cell(_Client(), profile)
        prov = prose["provenance"]
        assert prov["kind"] == "generated"
        assert prov["model"] == ga.AUTHOR_MODEL
        assert prov["requested_model"] == ga.AUTHOR_MODEL
        assert prov["effort"] == ga.AUTHOR_EFFORT
        assert prov["prompt_version"] == ga.AUTHOR_PROMPT_VERSION
        assert prov["prompt_sha256"] == ga.author_prompt_sha()
        assert prov["profile_sha256"] == gs.sha256_text(gs.canonical_json(profile))
        assert prov["request_ids"] == ["req_author_1"]
        assert prov["attempts"] == 1

    def test_one_slot_that_breaks_a_rule_is_rewritten_alone(self) -> None:
        profile, _ = _built()
        client = _Client([lambda p: _corrupt(p, "r1.b2")])
        prose = ga.author_cell(client, profile)
        assert len(client.messages.captured) == 2
        second = json.loads(client.messages.captured[1]["messages"][0]["content"])
        assert list(second["slots"]) == ["r1.b2"]
        assert "99" in second["rewrite"]["r1.b2"]["previous_text"]
        assert any("number 99" in p for p in second["rewrite"]["r1.b2"]["problems"])
        assert gs.check_prose(profile, prose) == []
        assert prose["provenance"]["attempts"] == 2

    def test_slots_that_still_fail_are_rejected_and_nothing_is_returned(self) -> None:
        profile, _ = _built()
        client = _Client([lambda p: _corrupt(p, "r1.b2"), lambda p: _corrupt(p, "r1.b2")])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert len(client.messages.captured) == ga.MAX_ATTEMPTS
        assert any("r1.b2" in p and "number 99" in p for p in caught.value.problems)

    def test_a_slot_the_reply_leaves_out_counts_as_a_failure(self) -> None:
        profile, _ = _built()

        def drop_one(prompt: str) -> str:
            data = json.loads(_good_reply(prompt))
            data["slots"].pop("summary.1")
            return json.dumps(data)

        client = _Client([drop_one])
        prose = ga.author_cell(client, profile)
        second = json.loads(client.messages.captured[1]["messages"][0]["content"])
        assert list(second["slots"]) == ["summary.1"]
        assert "summary.1" in prose["slots"]

    def test_an_invention_trap_in_a_resume_slot_is_a_failure(self) -> None:
        profile, _ = _built()
        trap_skill = profile["expected"]["forbidden_inventions"][0].replace("\\", "")

        def claim(prompt: str) -> str:
            data = json.loads(_good_reply(prompt))
            data["slots"]["r1.b2"] += f" {trap_skill}"
            return json.dumps(data)

        profile["slots"]["r1.b2"]["max_words"] += 5
        client = _Client([claim, claim])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert any("trap" in p for p in caught.value.problems)

    def test_a_jd_may_name_a_skill_the_candidate_lacks(self) -> None:
        profile, _ = _built()
        client = _Client()
        prose = ga.author_cell(client, profile)  # the JD slots must name the absent skills
        needs = prose["slots"]["jd.hospital.needs"]
        absent = [
            s["name"]
            for s in FACTS["skills"]
            if s["name"] not in {k["name"] for k in profile["skills"]}
        ]
        assert any(a in needs for a in absent)

    @pytest.mark.parametrize(
        ("reply", "needle"),
        [
            (_Message("{}", stop_reason="refusal"), "refusal"),
            (_Message("{}", stop_reason="max_tokens"), "max_tokens"),
            (_Message("not json"), "not JSON"),
            (_Message('{"slots": [1]}'), "not {"),
            (_Message('{"slots": {"r1.b1": 5}}'), "not {"),
        ],
    )
    def test_an_unusable_reply_raises_and_is_not_retried(
        self, reply: _Message, needle: str
    ) -> None:
        profile, _ = _built()
        client = _Client([reply])
        with pytest.raises(ga.AuthorError, match=needle):
            ga.author_cell(client, profile)
        assert len(client.messages.captured) == 1

    def test_a_refusal_names_the_decision_not_to_fall_back(self) -> None:
        profile, _ = _built()
        with pytest.raises(ga.AuthorError, match="no fallback model"):
            ga.author_cell(_Client([_Message("{}", stop_reason="refusal")]), profile)

    def test_an_unsound_profile_sends_nothing(self) -> None:
        profile, _ = _built()
        profile["slots"].pop("r1.b1")
        client = _Client()
        with pytest.raises(ga.AuthorError, match="not sound"):
            ga.author_cell(client, profile)
        assert client.messages.captured == []

    def test_the_prose_writes_and_the_suite_checks_clean(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        profile, _ = _built("entry")
        prose = ga.author_cell(_Client(), profile)
        gs.write_cell(root, profile, prose)
        manifest = gs.load_manifest(root)
        manifest["author"]["prompt_versions"][ga.AUTHOR_PROMPT_VERSION] = ga.author_prompt_sha()
        gs.write_manifest(root, manifest)
        assert gs.check_suite(root, {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}) == []


def _comma_split(prompt: str) -> str:
    """A reply that meets every slot rule but leaves the iteration target with no five-word stretch.

    ``r1.b2`` is the slot a derived iteration edits, and the edit needs a run of five words free of commas
    (``golden_set.pick_edit_target``); one-word fragments pass every `check_slot_text` rule.
    """
    data = json.loads(_good_reply(prompt))
    spec = json.loads(prompt)["slots"]["r1.b2"]
    data["slots"]["r1.b2"] = ", ".join([*spec["must_include"], *["steady"] * 10])
    return json.dumps(data)


class TestRenderBeforeAccepting:
    """A reply is rendered before it is accepted, so a cell is never paid for and then lost at the write."""

    def test_the_comma_split_text_passes_the_slot_checks_but_not_the_render(self) -> None:
        profile, _ = _built()
        slots = json.loads(_comma_split(ga.build_user_prompt(profile, sorted(profile["slots"]))))[
            "slots"
        ]
        spec = profile["slots"]["r1.b2"]
        assert gs.check_slot_text("r1.b2", spec, slots["r1.b2"], []) == []
        with pytest.raises(ValueError, match="five words"):
            gs.pick_edit_target(slots["r1.b2"])

    def test_such_a_target_is_rewritten_alone_in_the_same_cell(self) -> None:
        profile, _ = _built()
        client = _Client([_comma_split])
        prose = ga.author_cell(client, profile)
        assert len(client.messages.captured) == 2
        second = json.loads(client.messages.captured[1]["messages"][0]["content"])
        assert list(second["slots"]) == ["r1.b2"]
        assert any("five words" in p for p in second["rewrite"]["r1.b2"]["problems"])
        assert gs.render_fixtures(profile, prose)  # the cell now renders
        assert prose["provenance"]["attempts"] == 2

    def test_a_target_that_still_cannot_be_edited_rejects_the_cell(self) -> None:
        profile, _ = _built()
        client = _Client([_comma_split, _comma_split])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert any("r1.b2" in p and "five words" in p for p in caught.value.problems)
        assert len(client.messages.captured) == ga.MAX_ATTEMPTS

    def test_a_clean_reply_costs_no_extra_request(self) -> None:
        profile, _ = _built()
        client = _Client()
        ga.author_cell(client, profile)
        assert len(client.messages.captured) == 1


class TestAFailureCarriesWhatWasPaid:
    """A rejected or unusable cell was still paid for: its usage, replies and request ids travel with the error."""

    def test_a_rejection_names_the_usage_the_replies_and_the_requests(self) -> None:
        profile, _ = _built()
        client = _Client([_comma_split, _comma_split])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert caught.value.usage["input_tokens"] == 2000  # two requests of 1,000 tokens
        assert caught.value.usage["output_tokens"] == 1000
        assert len(caught.value.replies) == 2
        assert all(json.loads(r)["slots"] for r in caught.value.replies)
        assert caught.value.request_ids == ["req_author_1", "req_author_2"]

    def test_an_unusable_reply_carries_them_too(self) -> None:
        profile, _ = _built()
        with pytest.raises(ga.AuthorError) as caught:
            ga.author_cell(_Client([_Message("not json")]), profile)
        assert caught.value.usage["input_tokens"] == 1000
        assert caught.value.replies == ["not json"]

    def test_the_cost_of_a_failure_is_priced_from_its_usage(self) -> None:
        profile, _ = _built()
        client = _Client([_comma_split, _comma_split], usage=_Usage(250_000, 0))
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert ga.cost_of_usage(caught.value.usage) == pytest.approx(2.0)  # 500,000 in at $4/M


class TestLoggedSpend:
    """The spend the call log already holds, so a cap spans runs and counts what a rejected cell cost."""

    def test_it_sums_only_the_authors_rows(self, real_log: Path) -> None:
        real_log.parent.mkdir(parents=True)
        real_log.write_text(
            _author_row(250_000)  # $1.00
            + _author_row(0, 0)  # an error row: no tokens, no price
            + _author_row(250_000, call="judge_grounding")  # not the author's
            + "this line is not json\n"
            + _author_row(0, 50_000),  # $1.00
            encoding="utf-8",
        )
        assert ga.logged_spend() == pytest.approx(2.0)

    def test_a_missing_log_is_zero(self, real_log: Path) -> None:
        assert not real_log.exists()
        assert ga.logged_spend() == 0.0

    def test_it_can_start_at_an_offset(self, real_log: Path) -> None:
        real_log.parent.mkdir(parents=True)
        real_log.write_text(_author_row(250_000), encoding="utf-8")
        offset = real_log.stat().st_size
        with real_log.open("a", encoding="utf-8") as fh:
            fh.write(_author_row(0, 50_000))
        assert ga.logged_spend(since=offset) == pytest.approx(1.0)
        assert ga.logged_spend() == pytest.approx(2.0)

    def test_an_offset_past_the_end_reads_from_the_start(self, real_log: Path) -> None:
        real_log.parent.mkdir(parents=True)
        real_log.write_text(_author_row(250_000), encoding="utf-8")
        assert ga.logged_spend(since=10_000_000) == pytest.approx(1.0)


class TestTelemetry:
    def test_the_row(self, rows: list[dict[str, Any]]) -> None:
        profile, _ = _built()
        ga.author_cell(_Client(), profile)
        (row,) = rows
        assert row["call"] == "dataset_author"
        assert row["model"] == ga.AUTHOR_MODEL
        assert row["answered_model"] == ga.AUTHOR_MODEL
        assert row["prompt_version"] == ga.AUTHOR_PROMPT_VERSION
        assert row["prompt_sha256"] == ga.author_prompt_sha()
        assert row["producer_id"]
        assert row["username"] == f"golden:{profile['cell']}"
        assert row["status"] == "ok"
        assert row["api_request_id"] == "req_author_1"

    def test_the_settings_record_what_ran_and_not_the_prompt(
        self, rows: list[dict[str, Any]]
    ) -> None:
        profile, _ = _built()
        ga.author_cell(_Client(), profile)
        settings = rows[0]["request_settings"]
        assert settings["thinking"] == {"type": "adaptive"}
        assert settings["output_config"] == {"effort": ga.AUTHOR_EFFORT}
        assert "system" not in settings and "messages" not in settings

    def test_a_failed_call_leaves_an_error_row_and_raises(self, rows: list[dict[str, Any]]) -> None:
        profile, _ = _built()
        with pytest.raises(RuntimeError, match="network down"):
            ga.author_cell(_Client([RuntimeError("network down")]), profile)
        (row,) = rows
        assert row["status"] == "error"
        assert row["error_type"] == "RuntimeError"
        assert row["prompt_version"] == ga.AUTHOR_PROMPT_VERSION

    def test_the_default_judge_row_keeps_the_product_prompt_version(
        self, rows: list[dict[str, Any]]
    ) -> None:
        analyzer.log_judge_call(
            call_kind="judge_grade",
            username="eval:x",
            model=runner.JUDGE_MODEL,
            request_kwargs={"model": runner.JUDGE_MODEL, "max_tokens": 5},
            response=None,
            elapsed_ms=1,
        )
        assert rows[0]["prompt_version"] == analyzer.effective_prompt_version()


class TestCost:
    def test_cost_is_priced_from_the_table(self) -> None:
        profile, _ = _built()
        prose = ga.author_cell(_Client(usage=_Usage(250_000, 50_000)), profile)
        # 250,000 input at $4/M + 50,000 output at $20/M
        assert ga.cost_of(prose) == pytest.approx(1.0 + 1.0)


class TestCommandLine:
    def _root(self, tmp_path: Path) -> Path:
        return _suite(tmp_path)

    def _args(self, root: Path, *extra: str) -> list[str]:
        return [
            "--root",
            str(root),
            "--profession",
            "demo-ops",
            "--max-spend",
            "10",
            "--max-total-spend",
            "10",
            *extra,
        ]

    def test_without_confirm_paid_nothing_is_sent_and_no_client_is_built(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def no_client() -> Any:
            raise AssertionError("a client was built without --confirm-paid")

        monkeypatch.setattr(runner, "_get_client", no_client)
        assert ga.main(self._args(self._root(tmp_path), "--level", "entry")) == 3
        assert "nothing was sent" in capsys.readouterr().err

    def test_max_spend_is_required_and_must_be_positive(self, tmp_path: Path) -> None:
        root = self._root(tmp_path)
        with pytest.raises(SystemExit):
            ga.main(
                [
                    "--root",
                    str(root),
                    "--profession",
                    "demo-ops",
                    "--level",
                    "entry",
                    "--confirm-paid",
                ]
            )
        complete = [
            "--root",
            str(root),
            "--profession",
            "demo-ops",
            "--level",
            "entry",
            "--confirm-paid",
            "--max-total-spend",
            "10",
        ]
        with pytest.raises(SystemExit):  # every required argument is present; only the cap is wrong
            ga.main([*complete, "--max-spend", "0"])
        with pytest.raises(SystemExit):
            ga.main([*complete, "--max-spend", "-3"])

    def test_a_cell_that_exists_is_never_touched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", lambda: _Client())
        before = (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes()
        assert ga.main(self._args(root, "--level", "mid", "--confirm-paid")) == 1
        assert (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes() == before

    def test_it_writes_the_cells_and_restamps_the_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client()
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        code = ga.main(self._args(root, "--level", "entry", "--level", "lead", "--confirm-paid"))
        assert code == 0
        assert gs.cell_names(root) == ["demo-ops-entry", "demo-ops-lead", "demo-ops-mid"]
        manifest = gs.load_manifest(root)
        assert (
            manifest["author"]["prompt_versions"][ga.AUTHOR_PROMPT_VERSION]
            == ga.author_prompt_sha()
        )
        assert gs.check_suite(root, {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}) == []

    def test_the_spend_cap_stops_before_the_next_cell(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client(usage=_Usage(250_000, 0))  # $1.00 a cell
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        args = [
            "--root",
            str(root),
            "--profession",
            "demo-ops",
            "--max-spend",
            "1",
            "--max-total-spend",
            "10",
            "--confirm-paid",
        ]
        code = ga.main([*args, "--level", "entry", "--level", "lead"])
        assert code == ga.EXIT_OVER_BUDGET
        assert gs.cell_names(root) == [
            "demo-ops-entry",
            "demo-ops-mid",
        ]  # the first was written, the second was not
        assert len(client.messages.captured) == 1

    def test_a_rejected_cell_is_not_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client([lambda p: _corrupt(p, "r1.b2")] * 2)
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        assert ga.main(self._args(root, "--level", "entry", "--confirm-paid")) == 1
        assert gs.cell_names(root) == ["demo-ops-mid"]


def _bad(prompt: str) -> str:
    return _corrupt(prompt, "r1.b2")


def _no_client() -> Any:
    raise AssertionError("a client was built, so the run was not refused before any spend")


class TestStagedRun:
    """The run is staged so that nothing is paid for twice: a total cap across runs, a resume, a stop on repeats."""

    def _root(self, tmp_path: Path) -> Path:
        return _suite(tmp_path)

    def _run(self, root: Path, *extra: str, total: str = "10", spend: str = "10") -> int:
        return ga.main(
            [
                "--root",
                str(root),
                "--max-spend",
                spend,
                "--max-total-spend",
                total,
                "--confirm-paid",
                *extra,
            ]
        )

    def test_a_paid_run_needs_a_total_cap_and_a_dry_run_does_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", _no_client)
        base = ["--root", str(root), "--profession", "demo-ops", "--level", "entry"]
        with pytest.raises(SystemExit):
            ga.main([*base, "--max-spend", "10", "--confirm-paid"])
        assert ga.main([*base, "--max-spend", "10"]) == 3  # nothing sent, no total needed
        with pytest.raises(SystemExit):
            ga.main([*base, "--max-spend", "10", "--max-total-spend", "0", "--confirm-paid"])

    def test_the_total_cap_counts_what_the_log_already_holds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        real_log.parent.mkdir(parents=True)
        real_log.write_text(_author_row(250_000), encoding="utf-8")  # $1.00 from an earlier run
        monkeypatch.setattr(runner, "_get_client", _no_client)
        assert self._run(root, "--cell", "demo-ops:entry", total="1") == ga.EXIT_OVER_BUDGET
        assert gs.cell_names(root) == ["demo-ops-mid"]

    def test_a_rejected_cell_is_paid_for_and_counted(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        real_log: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = self._root(tmp_path)
        client = _Client([_bad, _bad], usage=_Usage(250_000, 0))  # $1.00 a request, $2.00 the cell
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        assert self._run(root, "--cell", "demo-ops:entry") == 1
        assert ga.logged_spend() == pytest.approx(2.0)
        said = capsys.readouterr()
        assert "counted $2.0000" in said.out + said.err
        assert "the call log shows $2.0000" in said.out + said.err
        monkeypatch.setattr(runner, "_get_client", _no_client)  # a later run starts from that $2.00
        assert self._run(root, "--cell", "demo-ops:entry", total="2") == ga.EXIT_OVER_BUDGET

    def test_the_next_cell_is_not_started_when_its_likely_cost_would_reach_the_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        client = _Client(usage=_Usage(250_000, 0))  # $1.00 a cell
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        code = self._run(root, "--cell", "demo-ops:entry", "--cell", "demo-ops:lead", total="1.5")
        # $1.00 is spent, and another cell like it would reach $2.00
        assert code == ga.EXIT_OVER_BUDGET
        assert gs.cell_names(root) == ["demo-ops-entry", "demo-ops-mid"]
        assert len(client.messages.captured) == 1

    def test_cells_are_named_one_by_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", lambda: _Client())
        assert self._run(root, "--cell", "demo-ops:lead", "--cell", "demo-ops:entry") == 0
        assert gs.cell_names(root) == ["demo-ops-entry", "demo-ops-lead", "demo-ops-mid"]

    def test_skip_existing_continues_past_a_written_cell(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        client = _Client()
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        before = (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes()
        code = self._run(
            root, "--cell", "demo-ops:mid", "--cell", "demo-ops:entry", "--skip-existing"
        )
        assert code == 0
        assert len(client.messages.captured) == 1  # only the new cell was paid for
        assert (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes() == before
        assert "demo-ops-entry" in gs.cell_names(root)

    def test_without_skip_existing_a_written_cell_refuses_the_whole_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", _no_client)
        assert self._run(root, "--cell", "demo-ops:entry", "--cell", "demo-ops:mid") == 1
        assert gs.cell_names(root) == ["demo-ops-mid"]

    @pytest.mark.parametrize("cell", ["demo-ops", "demo-ops:principal", ":entry", "demo-ops:"])
    def test_a_malformed_cell_is_a_usage_error(self, tmp_path: Path, cell: str) -> None:
        with pytest.raises(SystemExit):
            self._run(self._root(tmp_path), "--cell", cell)

    def test_no_cell_at_all_is_a_usage_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            self._run(self._root(tmp_path))

    def test_missing_facts_fail_before_any_spend(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(runner, "_get_client", _no_client)
        assert self._run(self._root(tmp_path), "--cell", "no-such:entry") == 1
        assert "facts" in capsys.readouterr().err

    def test_repeated_rejections_stop_the_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        real_log: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = self._root(tmp_path)
        client = _Client([_bad] * 6)
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        cells = ["--cell", "demo-ops:entry", "--cell", "demo-ops:senior", "--cell", "demo-ops:lead"]
        assert self._run(root, *cells) == 1
        # two cells of two requests each; the third never started
        assert len(client.messages.captured) == 4
        assert "consecutive" in capsys.readouterr().err
        assert gs.cell_names(root) == ["demo-ops-mid"]

    def test_the_limit_can_be_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        client = _Client([_bad] * 6)
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        cells = ["--cell", "demo-ops:entry", "--cell", "demo-ops:senior"]
        assert self._run(root, *cells, "--max-consecutive-failures", "1") == 1
        assert len(client.messages.captured) == 2

    def test_a_success_between_failures_resets_the_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        # free all four tiers, so that a fourth cell follows the second failure
        shutil.rmtree(root / "cells" / "demo-ops-mid")
        for fixture in (root / "fixtures").glob("demo-ops-mid--*"):
            shutil.rmtree(fixture)
        # fail, succeed, fail, succeed: without a reset the second failure would already be the second in a row
        client = _Client([_bad, _bad, _good_reply, _bad, _bad, _good_reply])
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        cells = [f"demo-ops:{level}" for level in ("entry", "mid", "senior", "lead")]
        assert self._run(root, *[a for cell in cells for a in ("--cell", cell)]) == 1
        assert len(client.messages.captured) == 6
        assert gs.cell_names(root) == ["demo-ops-lead", "demo-ops-mid"]

    def test_a_rejected_cell_leaves_what_the_model_said_to_study(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", lambda: _Client([_bad, _bad]))
        assert self._run(root, "--cell", "demo-ops:entry") == 1
        kept = json.loads(
            (real_log.parent / "golden_rejects" / "demo-ops-entry.json").read_text(encoding="utf-8")
        )
        assert kept["cell"] == "demo-ops-entry"
        assert kept["error"] == "AuthorRejected"
        assert kept["problems"] and len(kept["replies"]) == 2
        assert kept["usage"]["input_tokens"] == 2000
        assert kept["request_ids"] == ["req_author_1", "req_author_2"]

    def test_the_client_makes_one_attempt_and_waits_a_bounded_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_log: Path
    ) -> None:
        client = _Client()
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        assert self._run(self._root(tmp_path), "--cell", "demo-ops:entry") == 0
        # No silent retry (the SDK default is two, none of them logged) and no 600 s default wait.
        assert client.options == {"timeout": ga.AUTHOR_TIMEOUT_SECONDS, "max_retries": 0}
        assert 0 < ga.AUTHOR_TIMEOUT_SECONDS < 600

    def test_a_write_that_fails_after_the_reply_keeps_the_paid_prose(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        real_log: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", lambda: _Client(usage=_Usage(250_000, 0)))

        def refuse(*_: Any, **__: Any) -> None:
            raise ValueError("the disk said no")

        monkeypatch.setattr(gs, "write_cell", refuse)
        assert self._run(root, "--cell", "demo-ops:entry") == 1
        kept = json.loads(
            (real_log.parent / "golden_rejects" / "demo-ops-entry.json").read_text(encoding="utf-8")
        )
        assert kept["error"] == "ValueError" and "disk said no" in kept["problems"][0]
        assert kept["prose"]["slots"]  # what was paid for is not lost
        assert "counted $1.0000" in capsys.readouterr().out
        assert gs.cell_names(root) == ["demo-ops-mid"]

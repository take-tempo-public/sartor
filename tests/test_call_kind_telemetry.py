"""Tier 1 for item 22 — inventory-complete call-kind telemetry probe.

`docs/dev/diagnosis/never-logged-call-kinds.md` is the dossier this test's results
feed. It exists because item 22 (four `call_kind`s with real call sites but zero
`logs/llm_calls.jsonl` rows) needs an instrument that is NOT scoped to the item's own
theory — a probe covering only the two kinds the item names would hide a whole *class*
of never-logged calls (rival b6 in the dossier), and O-8 there already found two more
members of that class the item never listed. So this file has two independent halves:

  - `test_call_kind_inventory_is_exactly_expected` — an AST walk of every `call_kind=`
    literal keyword argument repo-wide (excluding `tests/`), asserted against an
    explicit frozenset. This is a REGRESSION GUARD, not a capability proof: it makes
    the instrument outlive today's theory — a new call kind added later fails this
    test until someone deliberately adds it here and (if it's ever unlogged) writes a
    probe for it below.
  - `TestNeverLoggedKindsEmitTelemetry` — one probe per call kind that O-1 in the
    dossier found has ZERO rows in the real log (recommend_skill, suggest_skill,
    recommend_experience_summary, draft_surgical_refinement, suggest_skill_from_corpus,
    promote_clarification_to_bullet), each driving the REAL analyzer entry point with a
    context that satisfies its own short-circuit gate, against a fake client, through
    the REAL `_call_llm_streaming` -> `_emit_call_log` funnel (not `_parse_or_retry`
    patched out, unlike every pre-existing test for these functions). This is a
    CAPABILITY PROOF, not a reproduction: most of these assertions are expected to pass
    on HEAD (the dossier's O-3/O-5 already argue the funnel is structurally sound and
    the real gap is upstream gating) — a green run here proves the plumbing works, not
    that any of these features has ever fired in production.

The fake-client idiom (queue one response per `.messages.stream()` call, implement only
`.stream()` so a pre-fix direct-`.create()` call site would raise) mirrors
`tests/test_refinement_scope.py` (`_QueuedFakeClient` et al.), itself mirroring
`tests/test_prompt_overrides.py`'s `_FakeStream` — this is the third near-identical copy
in this repo; extracting a shared `tests/llm_fakes.py` is filed as a chore rather than
done here (out of scope for this branch).

Telemetry containment is non-negotiable — this exact bug (a test driving the real
`_call_llm_streaming` without redirecting telemetry, silently polluting the developer's
actual `logs/llm_calls.jsonl`) has already happened twice in this repo (item 21, item
33). `_telemetry` below redirects BOTH `analyzer._emit_call_log` and `analyzer.LOG_PATH`
(belt and braces: `_emit_call_log` reads the module global at call time, so either
alone works today, but neither alone survives a future refactor), and
`_real_log_line_count_unchanged` independently asserts the real file's line count is
identical before and after this whole module runs — the class of check that would have
caught both prior incidents automatically.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import analyzer
from hardening import MODEL_PRICING

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_LOG_PATH = REPO_ROOT / "logs" / "llm_calls.jsonl"

# Directory parts that take a .py file out of the production scan — same convention as
# tests/test_egress_allowlist.py's `_SCAN_EXCLUDE_PARTS` (not imported: that name is
# private to its own file, and this walk's purpose — call_kind literals, not egress
# imports — is different enough that sharing isn't worth the coupling).
_SCAN_EXCLUDE_PARTS = frozenset(
    {"tests", ".venv", "venv", ".git", "build", "dist", "__pycache__", "versions"}
)

# The complete, reviewed inventory of `call_kind="<literal>"` keyword arguments in
# production code, repo-wide, as of this branch — 20 distinct literals across 23 call
# sites (analyze_extraction / analyze_synthesis / generate each fire from two branches
# of their own function; every other literal has one call site). A call kind added
# later fails this test until someone deliberately updates this set — and, if it's
# ever unlogged, adds a probe for it in `TestNeverLoggedKindsEmitTelemetry` below.
EXPECTED_CALL_KINDS = frozenset(
    {
        "analyze_extraction",
        "analyze_synthesis",
        "avatar_answer",
        "clarify",
        "iterate_clarify",
        "generate",
        "generate_cover_letter",
        "check_refinement_scope",
        "critique_proposal",
        "recommend",
        "recommend_summary",
        "recommend_experience_summary",
        "recommend_skill",
        "suggest_skill",
        "suggest_skill_from_corpus",
        "promote_clarification_to_bullet",
        "draft_summary",
        "draft_gap_fill",
        "draft_surgical_refinement",
        "extract_experiences",
    }
)

# `<kind>_retry` (`_parse_or_retry`, analyzer.py:1501) is derived at runtime from
# whatever `call_kind` the caller passed — it is not a separate literal anywhere in the
# source, so it is deliberately NOT a member of EXPECTED_CALL_KINDS and gets no probe of
# its own; each per-kind probe below only asserts the first-attempt row.


def _production_py_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(part in _SCAN_EXCLUDE_PARTS for part in rel_parts):
            continue
        out.append(path)
    return out


def _call_kind_literals(tree: ast.AST) -> set[str]:
    """Every literal `call_kind="..."` keyword argument in a whole module AST (not just
    module scope, so a call site nested in a function body is still caught)."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if (
                kw.arg == "call_kind"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                found.add(kw.value.value)
    return found


def test_call_kind_inventory_is_exactly_expected() -> None:
    """REGRESSION GUARD (b6): the inventory of `call_kind=` literals repo-wide is
    exactly EXPECTED_CALL_KINDS — no more (an unreviewed new call kind), no fewer
    (a stale entry here that no longer exists in the source)."""
    found: set[str] = set()
    for path in _production_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found |= _call_kind_literals(tree)

    unreviewed = found - EXPECTED_CALL_KINDS
    stale = EXPECTED_CALL_KINDS - found
    assert not unreviewed, (
        f"New call_kind literal(s) not yet reviewed into EXPECTED_CALL_KINDS: "
        f"{sorted(unreviewed)}. If any of these has zero rows in logs/llm_calls.jsonl, "
        f"this is exactly item 22's class of defect (rival b6) — add a probe to "
        f"TestNeverLoggedKindsEmitTelemetry below, not just this set."
    )
    assert not stale, (
        f"EXPECTED_CALL_KINDS has stale entrie(s) no longer present in the source: "
        f"{sorted(stale)}. Remove them or find where they moved."
    )


@pytest.fixture(scope="module", autouse=True)
def _real_log_line_count_unchanged():
    """Independent guard, on top of `_telemetry`'s redirect below: the real
    `logs/llm_calls.jsonl` must have the identical line count before and after this
    whole module runs. This is the check that would have caught both prior telemetry-
    pollution incidents (item 21, item 33) even if the redirect fixture itself had a
    gap — it doesn't trust the redirect, it verifies the outcome."""
    before = REAL_LOG_PATH.read_text(encoding="utf-8").count("\n") if REAL_LOG_PATH.exists() else 0
    yield
    after = REAL_LOG_PATH.read_text(encoding="utf-8").count("\n") if REAL_LOG_PATH.exists() else 0
    assert after == before, (
        f"logs/llm_calls.jsonl grew during tests/test_call_kind_telemetry.py "
        f"({before} -> {after} lines) — a test in this file drove the real telemetry "
        f"funnel without the _telemetry redirect engaging."
    )


class _FakeUsage:
    def __init__(self, input_tokens=2000, output_tokens=150):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0


class _FakeFinal:
    def __init__(self, usage):
        self.usage = usage
        self.stop_reason = "end_turn"


class _FakeStream:
    def __init__(self, text, usage):
        self._text = text
        self._usage = usage

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield self._text

    def get_final_message(self):
        return _FakeFinal(self._usage)


class _QueuedFakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.captured: list[dict] = []

    def stream(self, **kwargs):
        self.captured.append(kwargs)
        return _FakeStream(self._responses.pop(0), _FakeUsage())


class _QueuedFakeClient:
    def __init__(self, *responses):
        self.messages = _QueuedFakeMessages(responses)


@pytest.fixture(autouse=True)
def _telemetry(monkeypatch, tmp_path):
    """Redirect BOTH `_emit_call_log` (what every test here asserts against) AND
    `LOG_PATH` (belt and braces — `_emit_call_log` reads the module global at call
    time, so either alone is sufficient today, but neither alone survives a future
    refactor of `_emit_call_log`'s body)."""
    logs: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", lambda rec: logs.append(rec))
    monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "llm_calls.jsonl")
    return logs


def _assert_priced_ok_row(rec: dict, *, call_kind: str) -> None:
    assert rec["call"] == call_kind
    assert rec["status"] == "ok"
    assert rec["model"] in MODEL_PRICING, (
        f"{call_kind}'s row carries model={rec['model']!r}, not a hardening.MODEL_PRICING "
        f"key — /bench and /_dashboard can't price it."
    )
    assert rec["latency_ms"] is not None
    assert rec["prompt_version"]


class TestNeverLoggedKindsEmitTelemetry:
    """One probe per call kind the dossier's O-1 found has zero rows in the real log.
    Each drives the REAL analyzer function (not `_parse_or_retry` patched out) with a
    context that satisfies its own gate, so the assertion is about the funnel, not
    about the gate logic (which pre-existing tests in test_recommend_skills.py etc.
    already cover)."""

    def test_recommend_skill_emits_telemetry_row(self, _telemetry):
        from analyzer import recommend_skills

        client = _QueuedFakeClient('{"recommendation": {"skill_ids": [7, 8], "rationale": "r"}}')
        ctx = {
            "skill_items": [
                {"id": 7, "name": "Python"},
                {"id": 8, "name": "Kubernetes"},
            ]
        }

        result = recommend_skills(client, ctx)

        assert result["recommendation"]["skill_ids"] == [7, 8]
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="recommend_skill")

    def test_suggest_skill_emits_telemetry_row(self, _telemetry):
        from analyzer import suggest_skills

        client = _QueuedFakeClient(
            '{"proposals": [{"name": "Terraform", "evidence": {"bullet_id": 1, "quote": "q"}}]}'
        )
        ctx = {
            "career_corpus": [
                {"id": 1, "company": "Acme", "bullets": [{"id": 1, "text": "Ran infra."}]}
            ],
            "llm_analysis": {"essential_skills": ["terraform"]},
        }

        result = suggest_skills(client, ctx)

        assert [p["name"] for p in result["proposals"]] == ["Terraform"]
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="suggest_skill")

    def test_recommend_experience_summary_emits_telemetry_row(self, _telemetry):
        from analyzer import recommend_experience_summaries

        client = _QueuedFakeClient(
            '{"recommendations": [{"experience_id": 5, "summary_item_id": 91, '
            '"rationale": "best fit"}]}'
        )
        ctx = {
            "experience_summary_items": [
                {
                    "experience_id": 5,
                    "company": "Acme",
                    "items": [
                        {"id": 91, "text": "Owned platform scale across teams."},
                        {"id": 92, "text": "Drove growth experiments end to end."},
                    ],
                }
            ]
        }

        result = recommend_experience_summaries(client, ctx)

        assert result["recommendations"][0]["summary_item_id"] == 91
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="recommend_experience_summary")

    def test_draft_surgical_refinement_emits_telemetry_row(self, _telemetry):
        from analyzer import draft_surgical_refinement

        client = _QueuedFakeClient(
            '{"target_kind": "bullet", "experience_id": 7, "supersedes_bullet_id": null, '
            '"text": "Sharpened bullet.", "pattern_kind": "xyz", "rationale": "r"}'
        )
        ctx = {
            "jd_text": "Senior PM building AI billing platforms.",
            "refinement_note": "make the billing bullet punchier",
            "approved_composition": {"basics": {"summary": "A platform PM."}, "work": []},
        }

        result = draft_surgical_refinement(client, ctx)

        assert result["target_kind"] == "bullet"
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="draft_surgical_refinement")

    def test_suggest_skill_from_corpus_emits_telemetry_row(self, _telemetry):
        from analyzer import suggest_skills_from_corpus

        client = _QueuedFakeClient(
            '{"proposals": [{"name": "Terraform", "evidence": {"bullet_id": 1, "quote": "q"}}]}'
        )
        ctx = {
            "career_corpus": [
                {"id": 1, "company": "Acme", "bullets": [{"id": 1, "text": "Ran infra."}]}
            ]
        }

        result = suggest_skills_from_corpus(client, ctx)

        assert [p["name"] for p in result["proposals"]] == ["Terraform"]
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="suggest_skill_from_corpus")

    def test_promote_clarification_to_bullet_emits_telemetry_row(self, _telemetry):
        from analyzer import promote_clarification_to_bullet

        client = _QueuedFakeClient(
            '{"text": "Led the on-call rotation for a 12-person SRE team.", "pattern_kind": "xyz"}'
        )

        result = promote_clarification_to_bullet(
            client,
            question="Led on-call?",
            answer="Led on-call rotation for a 12-person SRE team.",
        )

        assert result["pattern_kind"] == "xyz"
        assert len(_telemetry) == 1
        _assert_priced_ok_row(_telemetry[0], call_kind="promote_clarification_to_bullet")

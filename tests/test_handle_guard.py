"""The id-handle guard on LLM responses (item 140): validator, retry reason, builders, and the wiring gate.

`analyzer._LLMResponse.reject_handle_leaks` rejects prose that names an id handle the prompt
shipped; `_parse_or_retry` re-asks once and raises `LLMResponseError` if the retry leaks too.
The last class is the fail-closed part (charter C-11): an AST gate that fails any
`_parse_or_retry*` call that neither forwards a guard nor sits on the exemption list with a reason.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import analyzer
from analyzer import (
    ClarifyResponse,
    LLMResponseError,
    RecommendResponse,
    _block_guard,
    _corpus_guard,
    _parse_or_retry,
    _parse_or_retry_streaming,
    _retry_reason,
    _StreamDone,
)
from tests._controls import control
from tests._repo_files import REPO_ROOT, repo_files

BLOCK = (
    '<career_corpus><experience id="e1" company="Acme">'
    '<bullet id="b12" tags="">Ran 40 t3 instances behind the queue</bullet>'
    '<bullet id="b14" tags="">Cut deploy time 60%</bullet></experience></career_corpus>'
)


def _payload(rationale: str, ids: tuple[str, ...] = ("b12",)) -> str:
    return json.dumps(
        {
            "recommendations": [
                {"experience_id": "e1", "bullet_ids": list(ids), "rationale": rationale}
            ]
        }
    )


def _scripted(responses: list[str]) -> Any:
    calls: list[tuple[str, str]] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, **kwargs):
        calls.append((call_kind, prompt))
        return responses.pop(0)

    fake.calls = calls
    return fake


def _run(guard: dict[str, Any] | None) -> dict[str, Any]:
    return _parse_or_retry(
        None,  # type: ignore[arg-type]
        "base prompt",
        cached_user_prefix="",
        response_model=RecommendResponse,
        call_kind="recommend",
        username="u",
        run_id="r",
        validation_context=guard,
    )


class TestValidatorAndRetry:
    def test_without_a_guard_a_leak_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Control: the guard is what rejects, so the same response is accepted when it is absent.
        monkeypatch.setattr(analyzer, "_call_llm", _scripted([_payload("b12 shows depth")]))
        assert _run(None)["recommendations"][0]["rationale"] == "b12 shows depth"

    def test_a_leak_then_a_clean_response_retries_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _scripted([_payload("b14 shows depth"), _payload("The deploy-time cut shows depth")])
        monkeypatch.setattr(analyzer, "_call_llm", fake)
        out = _run(_block_guard(BLOCK))
        assert out["recommendations"][0]["rationale"] == "The deploy-time cut shows depth"
        assert [k for k, _ in fake.calls] == ["recommend", "recommend_retry"]

    def test_the_retry_prompt_carries_our_reason_not_pydantics_wrapper(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _scripted([_payload("b14 shows depth"), _payload("clean")])
        monkeypatch.setattr(analyzer, "_call_llm", fake)
        _run(_block_guard(BLOCK))
        retry_prompt = fake.calls[1][1]
        assert "internal id handle(s) b14" in retry_prompt
        assert "validation error for" not in retry_prompt
        assert "input_value" not in retry_prompt

    def test_two_leaks_raise_with_a_readable_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            analyzer, "_call_llm", _scripted([_payload("b14 here"), _payload("and b14 again")])
        )
        with pytest.raises(LLMResponseError) as ei:
            _run(_block_guard(BLOCK))
        assert "internal id handle(s) b14" in ei.value.validation_error
        assert "validation error for" not in ei.value.validation_error

    def test_id_fields_are_legal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _scripted([_payload("Strong deploy-time evidence", ids=("b12", "b14"))])
        monkeypatch.setattr(analyzer, "_call_llm", fake)
        _run(_block_guard(BLOCK))
        assert [k for k, _ in fake.calls] == ["recommend"]

    def test_a_handle_that_is_real_bullet_text_is_not_a_leak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # b12's text says "t3 instances"; t3 is not a shipped handle here, and the markup is tag-stripped
        # before source tokens are read, so the id attributes themselves never exempt a handle.
        guard = _block_guard(BLOCK)
        assert guard is not None
        assert "t3" in guard["handle_guard"]["source_tokens"]
        assert "b12" not in guard["handle_guard"]["source_tokens"]
        monkeypatch.setattr(
            analyzer, "_call_llm", _scripted([_payload("Ran t3 instances at scale")])
        )
        _run(guard)  # no raise, no retry

    def test_a_guard_with_nothing_shipped_is_none(self) -> None:
        assert _block_guard("<jd>plain text</jd>") is None

    def test_retry_reason_leaves_other_failures_untouched(self) -> None:
        with pytest.raises(ValidationError) as ei:
            ClarifyResponse.model_validate({"questions": []})  # `reasoning` missing
        assert _retry_reason(ei.value) == str(ei.value)
        assert "reasoning" in _retry_reason(ei.value)


class TestStreaming:
    def test_a_leak_emits_a_retry_event_with_our_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        attempts = iter([[_payload("b14 shows depth")], [_payload("clean")]])

        def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, **kwargs):
            chunks = next(attempts)
            yield from chunks
            yield _StreamDone(text="".join(chunks), stop_reason="end_turn")

        monkeypatch.setattr(analyzer, "_call_llm_streaming", fake)
        events = list(
            _parse_or_retry_streaming(
                None,  # type: ignore[arg-type]
                "p",
                cached_user_prefix="",
                response_model=RecommendResponse,
                call_kind="recommend",
                username="u",
                run_id="r",
                validation_context=_block_guard(BLOCK),
            )
        )
        retries = [p for k, p in events if k == "retry"]
        assert len(retries) == 1
        assert "internal id handle(s) b14" in str(retries[0])
        assert events[-1][0] == "done"


class TestClarifyComposition:
    def test_a_guard_alone_does_not_switch_on_the_question_mix_rules(self) -> None:
        # clarify_iteration() passes only a guard. Its questions are all scope-style, which the
        # analyze-time 60% rule would reject; the rule must stay off without its own context key.
        guard = _block_guard(BLOCK)
        assert guard is not None
        data = {
            "questions": [{"id": "q1", "kind": "iteration_probe", "text": "Why?"}],
            "reasoning": "r",
        }
        ClarifyResponse.model_validate(data, context=guard)

    def test_the_rules_still_fire_with_their_own_key(self) -> None:
        data = {
            "questions": [{"id": "q1", "kind": "scope_probe", "text": "Why?"}],
            "reasoning": "r",
        }
        with pytest.raises(ValueError, match="60%"):
            ClarifyResponse.model_validate(data, context={"hidden_qualities_non_empty": False})


class TestBuilders:
    def test_no_corpus_and_no_answers_is_inert(self) -> None:
        assert _corpus_guard({"resume": {"text": "x"}, "job_description": "jd"}) is None  # type: ignore[typeddict-item]

    def test_corpus_handles_and_answered_q_ids(self) -> None:
        ctx: Any = {
            "resume": {"text": "x"},
            "job_description": "jd",
            "career_corpus": [{"id": 1, "bullets": [{"id": 12, "text": "t"}]}],
            "clarification_questions": [{"id": "q1"}, {"id": "q2"}],
            "clarifications": {"q1": "an answer", "q2": "  "},
        }
        plain = _corpus_guard(ctx)
        with_q = _corpus_guard(ctx, answered_q_ids=True)
        assert plain is not None and with_q is not None
        assert plain["handle_guard"]["handles"]["prefixed"] == frozenset({"e1", "b12"})
        assert with_q["handle_guard"]["handles"]["prefixed"] == frozenset({"e1", "b12", "q1"})


# --- The fail-closed part ------------------------------------------------------------------

# Calls that legitimately forward no guard, with the reason. Verified by reading each function's
# source for `id="` attributes and id-block helpers (docs/dev/diagnosis/llm-handle-leak-and-letter-date.md).
EXEMPT_CALL_KINDS = {
    "check_refinement_scope": "scope classifier; its prompt ships no id handles",
    "critique_proposal": "its input lists bullets as plain text with no ids; the prompt example that named one was removed",
    "promote_clarification_to_bullet": "converts one Q&A pair; ships no id handles",
    "draft_summary": "positioning summary from plain candidate facts; ships no id handles",
}
# Files other than analyzer.py that call _parse_or_retry, with the reason they need no guard.
EXEMPT_CALLER_FILES = {
    "onboarding/extract_experiences.py": "extracts experiences from an uploaded résumé; nothing shipped to leak",
}
_PARSERS = {"_parse_or_retry", "_parse_or_retry_streaming"}


def _parser_calls(path: Path) -> list[tuple[int, str | None, bool]]:
    """`(line, call_kind literal or None, forwards validation_context)` for each parser call in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _PARSERS
        ):
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            kind = kw.get("call_kind")
            literal = (
                kind.value
                if isinstance(kind, ast.Constant) and isinstance(kind.value, str)
                else None
            )
            out.append((node.lineno, literal, "validation_context" in kw))
    return out


class TestEveryCallForwardsAGuard:
    def test_each_analyzer_call_forwards_a_guard_or_is_exempt(self) -> None:
        calls = _parser_calls(REPO_ROOT / "analyzer.py")
        control(len(calls) >= 18, f"expected to find the parser calls, found {len(calls)}")
        problems = [
            f"analyzer.py:{line} call_kind={kind!r}"
            for line, kind, forwards in calls
            if not forwards and kind not in EXEMPT_CALL_KINDS
        ]
        assert not problems, (
            "these calls neither forward validation_context (a handle guard) nor are in EXEMPT_CALL_KINDS "
            f"with a reason: {problems}"
        )

    def test_exempt_entries_are_real_and_unwired(self) -> None:
        calls = _parser_calls(REPO_ROOT / "analyzer.py")
        seen = {kind for _, kind, forwards in calls if not forwards}
        stale = sorted(set(EXEMPT_CALL_KINDS) - seen)
        assert not stale, (
            f"EXEMPT_CALL_KINDS names calls that are gone or now wired; remove them: {stale}"
        )

    def test_no_other_file_calls_the_parser_unlisted(self) -> None:
        others = []
        for path in repo_files(".py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel == "analyzer.py" or rel.startswith(("tests/", "docs-site/")):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "_parse_or_retry" in text and _parser_calls(path) and rel not in EXEMPT_CALLER_FILES:
                others.append(rel)
        assert not others, (
            f"files call _parse_or_retry without a guard or an EXEMPT_CALLER_FILES entry: {others}"
        )

    def test_the_gate_has_teeth(self, tmp_path: Path) -> None:
        # Control: a synthetic unwired call is reported as a problem by the same scan.
        f = tmp_path / "x.py"
        f.write_text(
            '_parse_or_retry(c, p, call_kind="brand_new", response_model=M)\n', encoding="utf-8"
        )
        ((_, kind, forwards),) = _parser_calls(f)
        assert kind == "brand_new" and not forwards and kind not in EXEMPT_CALL_KINDS

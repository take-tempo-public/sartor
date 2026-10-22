"""Item 181: every call-log row carries the identity the later eval steps key on.

A content hash of the system text as sent, a producer id, a parse outcome from the parse loops,
and (only inside an active trace context) W3C trace/span/parent ids and a case id. The tests
drive the real `_call_llm_streaming` / `_parse_or_retry*` / `log_judge_call` against a duck-typed
stand-in client, with `_emit_call_log` redirected, so no row reaches a real log.

Bodies are untyped like the rest of tests/.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

import analyzer
import call_identity as ci
from analyzer import LLMResponseError
from tests._fake_llm import FakeClient as _Client
from tests._fake_llm import FakeStream as _Stream
from tests._fake_llm import FakeUsage as _Usage


class _M(BaseModel):
    a: str


GOOD = '{"a": "x"}'
BAD = "not json"


@pytest.fixture(autouse=True)
def _rows(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", rows.append)
    return rows


def _parse(client, **kw):
    return analyzer._parse_or_retry(
        client,
        "prompt",
        cached_user_prefix="",
        response_model=_M,
        call_kind="clarify",
        username="u",
        run_id="r",
        **kw,
    )


# ---------- hash and producer id ------------------------------------------------------


def test_row_hash_is_the_system_text_as_sent(_rows):
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    assert _rows[0]["prompt_sha256"] == ci.text_sha256(analyzer.SYSTEM_PROMPT)


def test_explicit_system_prompt_is_what_is_hashed(_rows):
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t", system_prompt="custom persona")
    assert _rows[0]["prompt_sha256"] == ci.text_sha256("custom persona")


def test_an_active_override_changes_the_hash(_rows):
    with analyzer.prompt_overrides({"SYSTEM_PROMPT": "candidate text"}):
        analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    assert _rows[0]["prompt_sha256"] == ci.text_sha256("candidate text")


def test_producer_id_follows_the_recipe(_rows):
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="clarify", max_tokens=64)
    row = _rows[0]
    assert row["producer_id"] == ci.producer_id(
        call_kind="clarify",
        prompt_sha256=row["prompt_sha256"],
        model=row["answered_model"],
        settings=row["request_settings"],
    )


def test_a_retry_row_has_the_same_producer_id(_rows):
    _parse(_Client(_Stream(BAD), _Stream(GOOD)))
    first, second = _rows
    assert second["call"] == "clarify_retry"
    assert first["producer_id"] == second["producer_id"]


def test_a_float_setting_costs_the_producer_id_not_the_row(_rows, monkeypatch):
    monkeypatch.setattr(analyzer, "thinking_setting", lambda model: {"budget": 0.5})
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    assert len(_rows) == 1
    assert _rows[0]["producer_id"] is None
    assert _rows[0]["prompt_sha256"].startswith("sha256:")


def test_judge_row_carries_hash_and_producer_id(_rows):
    class _Resp:
        usage = _Usage()
        model = "claude-judge"
        stop_reason = "end_turn"
        _request_id = "req_j"

    analyzer.log_judge_call(
        call_kind="judge_grade",
        username="eval:fx",
        model="claude-judge",
        request_kwargs={
            "model": "claude-judge",
            "max_tokens": 8,
            "system": "grader",
            "messages": [],
        },
        response=_Resp(),
        elapsed_ms=3,
    )
    row = _rows[0]
    assert row["prompt_sha256"] == ci.text_sha256("grader")
    assert row["producer_id"].startswith("sha256:")
    assert "parse_outcome" not in row


# ---------- trace context -------------------------------------------------------------


def test_no_trace_context_means_no_id_keys(_rows):
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    for key in ("trace_id", "span_id", "parent_span_id", "case_id"):
        assert key not in _rows[0]


def test_inside_a_trace_context_rows_carry_ids(_rows):
    trace, parent = ci.new_trace_id(), ci.new_span_id()
    with analyzer.trace_context(trace, case_id="fx", parent_span_id=parent):
        analyzer._call_llm(_Client(_Stream(GOOD), _Stream(GOOD)), "p", call_kind="t")
        analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    for row in _rows:
        assert row["trace_id"] == trace
        assert row["case_id"] == "fx"
        assert row["parent_span_id"] == parent
        assert ci.is_span_id(row["span_id"])
    assert _rows[0]["span_id"] != _rows[1]["span_id"]


def test_trace_context_without_parent_or_case_omits_them(_rows):
    with analyzer.trace_context(ci.new_trace_id()):
        analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    assert "parent_span_id" not in _rows[0]
    assert "case_id" not in _rows[0]


def test_trace_context_is_restored_on_exit(_rows):
    with analyzer.trace_context(ci.new_trace_id()):
        pass
    analyzer._call_llm(_Client(_Stream(GOOD)), "p", call_kind="t")
    assert "trace_id" not in _rows[0]


@pytest.mark.parametrize("bad", ["", "0" * 32, "abc", None])
def test_trace_context_rejects_a_malformed_trace_id(bad):
    with pytest.raises(ValueError, match="trace_id"), analyzer.trace_context(bad):
        pass


def test_judge_row_is_a_child_of_the_case(_rows):
    class _Resp:
        usage = _Usage()
        model = "claude-judge"
        stop_reason = "end_turn"
        _request_id = "req_j"

    trace, case_span = ci.new_trace_id(), ci.new_span_id()
    with analyzer.trace_context(trace, case_id="fx", parent_span_id=case_span):
        analyzer.log_judge_call(
            call_kind="judge_grade",
            username="eval:fx",
            model="claude-judge",
            request_kwargs={"model": "claude-judge", "system": "g", "messages": []},
            response=_Resp(),
            elapsed_ms=1,
        )
    assert _rows[0]["trace_id"] == trace
    assert _rows[0]["parent_span_id"] == case_span


# ---------- parse outcome (deferred write) ---------------------------------------------


def test_first_try_accepted(_rows):
    _parse(_Client(_Stream(GOOD)))
    assert [r["parse_outcome"] for r in _rows] == ["accepted_first_try"]


def test_accepted_after_a_retry_writes_one_row_per_attempt(_rows):
    _parse(_Client(_Stream(BAD), _Stream(GOOD)))
    assert [(r["call"], r["attempt"], r["parse_outcome"]) for r in _rows] == [
        ("clarify", 1, "rejected_retried"),
        ("clarify_retry", 2, "accepted_after_retry"),
    ]


def test_refused_after_the_last_attempt(_rows):
    with pytest.raises(LLMResponseError):
        _parse(_Client(_Stream(BAD), _Stream(BAD)))
    assert [r["parse_outcome"] for r in _rows] == ["rejected_retried", "refused"]


def test_a_send_failure_writes_one_error_row_without_an_outcome(_rows):
    with pytest.raises(RuntimeError):
        _parse(_Client(_Stream(GOOD, fail=RuntimeError("boom"))))
    assert len(_rows) == 1
    assert _rows[0]["status"] == "error"
    assert "parse_outcome" not in _rows[0]


def test_a_send_failure_on_the_retry_does_not_inherit_the_previous_outcome(_rows):
    with pytest.raises(RuntimeError):
        _parse(_Client(_Stream(BAD), _Stream(GOOD, fail=RuntimeError("boom"))))
    assert [r["status"] for r in _rows] == ["ok", "error"]
    assert _rows[0]["parse_outcome"] == "rejected_retried"
    assert "parse_outcome" not in _rows[1]


def test_streaming_loop_outcomes_and_row_count(_rows):
    events = list(
        analyzer._parse_or_retry_streaming(
            _Client(_Stream(BAD), _Stream(GOOD)),
            "prompt",
            cached_user_prefix="",
            response_model=_M,
            call_kind="clarify",
            username="u",
            run_id="r",
        )
    )
    assert events[-1][0] == "done"
    assert [r["parse_outcome"] for r in _rows] == ["rejected_retried", "accepted_after_retry"]


def test_an_abandoned_streaming_loop_still_writes_its_row_once(_rows):
    gen = analyzer._parse_or_retry_streaming(
        _Client(_Stream(GOOD)),
        "prompt",
        cached_user_prefix="",
        response_model=_M,
        call_kind="clarify",
        username="u",
        run_id="r",
    )
    assert next(gen)[0] == "chunk"
    gen.close()
    assert len(_rows) == 1


def test_a_direct_streaming_call_writes_immediately_without_an_outcome(_rows):
    list(analyzer._call_llm_streaming(_Client(_Stream(GOOD)), "p", call_kind="avatar_answer"))
    assert len(_rows) == 1
    assert "parse_outcome" not in _rows[0]


# ---------- the row hash and the lock hash are the same hash ----------------------------


@pytest.mark.parametrize("name", sorted(analyzer._BASE_SYSTEM_PROMPTS))
def test_row_hash_of_each_registered_prompt_equals_its_lock_hash(_rows, name):
    """The lock is only worth gating if it hashes what a call sends (item 181)."""
    from scripts import prompt_lock

    analyzer._call_llm(
        _Client(_Stream(GOOD)),
        "p",
        call_kind="t",
        system_prompt=analyzer._BASE_SYSTEM_PROMPTS[name],
    )
    assert _rows[0]["prompt_sha256"] == prompt_lock.load()["prompts"][name]

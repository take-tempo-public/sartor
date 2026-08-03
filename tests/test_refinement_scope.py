"""Tests for `analyzer.check_refinement_scope` — item 21 (telemetry gap).

Before this fix, `check_refinement_scope` opened its own `client.messages.create`
directly, bypassing `_call_llm`/`_parse_or_retry`, so it never reached
`_emit_call_log`: no `call_kind`, no telemetry row, cost invisible to
`logs/llm_calls.jsonl`. `test_emits_telemetry_row` is the falsification experiment
for `docs/dev/diagnosis/refinement-scope-check-telemetry.md` — it MUST fail against
the pre-fix code (the fake client below only implements `.stream()`, so the old
`.create()` call site raises `AttributeError`, silently swallowed by the function's
own fail-open `except`, and no telemetry record is ever appended).

The fake client mirrors the shape in `tests/test_prompt_overrides.py` (`_FakeStream`
etc.) but queues one response per call, so a single test can drive both the
first-attempt and the `_retry` attempt `_parse_or_retry` makes on parse failure.

`_telemetry` below is autouse and REQUIRED, not opt-in: every test in this file
drives the real `_call_llm_streaming`, which reaches the real `_emit_call_log`
unless redirected — skip the redirect on even one test and it appends a live row
to the developer's actual `logs/llm_calls.jsonl`, the exact file this fix exists
to keep trustworthy. (Caught in review: three tests here originally omitted the
redirect and wrote 5 fake rows into the real log on every run.)

Test bodies are deliberately left untyped (matching the rest of tests/, which is
ANN-exempt in ruff — see pyproject.toml) so the fake client's duck-typed stand-in
for `anthropic.Anthropic` doesn't trip mypy's arg-type check; mypy only checks the
bodies of TYPED functions.
"""

from __future__ import annotations

import pytest

import analyzer
from analyzer import HAIKU_MODEL, LLMResponseError, check_refinement_scope


class _FakeUsage:
    input_tokens = 10
    output_tokens = 5
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _FakeFinal:
    usage = _FakeUsage()
    stop_reason = "end_turn"


class _FakeStream:
    def __init__(self, text):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield self._text

    def get_final_message(self):
        return _FakeFinal()


class _QueuedFakeMessages:
    """Implements only `.stream()` — post-fix shape. `.create()` is absent on
    purpose, so pre-fix code (which calls `.create()`) hits AttributeError."""

    def __init__(self, responses, captured):
        self._responses = list(responses)
        self._captured = captured

    def stream(self, **kwargs):
        self._captured.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _FakeStream(item)


class _QueuedFakeClient:
    def __init__(self, responses, captured=None):
        self.captured = captured if captured is not None else []
        self.messages = _QueuedFakeMessages(responses, self.captured)


@pytest.fixture(autouse=True)
def _telemetry(monkeypatch):
    """Redirect `_emit_call_log` so every test in this file — not just the ones
    that inspect it — is guaranteed offline from the real telemetry file."""
    logs: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", lambda rec: logs.append(rec))
    return logs


def test_emits_telemetry_row(_telemetry):
    client = _QueuedFakeClient(['{"valid": true}'])

    result = check_refinement_scope(client, "make it punchier")

    assert result == {"valid": True}
    assert len(_telemetry) == 1
    assert _telemetry[0]["call"] == "check_refinement_scope"
    assert _telemetry[0]["status"] == "ok"


def test_uses_haiku_model_and_128_token_cap():
    client = _QueuedFakeClient(['{"valid": true}'])

    check_refinement_scope(client, "make it punchier")

    assert client.captured[-1]["model"] == HAIKU_MODEL
    assert client.captured[-1]["max_tokens"] == 128


def test_outage_fails_open_with_error_telemetry_row(_telemetry):
    client = _QueuedFakeClient([ConnectionError("upstream unavailable")])

    result = check_refinement_scope(client, "make it punchier")

    assert result == {"valid": True}
    assert len(_telemetry) == 1
    assert _telemetry[0]["call"] == "check_refinement_scope"
    assert _telemetry[0]["status"] == "error"


def test_fenced_json_response_parses():
    client = _QueuedFakeClient(['```json\n{"valid": false, "reason": "invents a metric"}\n```'])

    result = check_refinement_scope(client, "add a 40% improvement I never measured")

    assert result == {"valid": False, "reason": "invents a metric"}


def test_missing_reason_key_validates():
    client = _QueuedFakeClient(['{"valid": false}'])

    result = check_refinement_scope(client, "some note")

    assert result == {"valid": False}


def test_unparseable_response_fails_open_after_retry(_telemetry):
    client = _QueuedFakeClient(["not json at all", "still not json"])

    result = check_refinement_scope(client, "make it punchier")

    assert result == {"valid": True}
    assert [rec["call"] for rec in _telemetry] == [
        "check_refinement_scope",
        "check_refinement_scope_retry",
    ]


def test_parse_or_retry_exhaustion_is_llm_response_error_not_leaked(_telemetry):
    """Sanity check on the mechanism the fail-open `except` relies on: confirm
    `_parse_or_retry` itself raises `LLMResponseError` (not something narrower)
    on retry exhaustion, so `check_refinement_scope`'s `except Exception` is
    known to catch it rather than accidentally matching a broader failure."""
    client = _QueuedFakeClient(["not json", "still not json"])

    with pytest.raises(LLMResponseError):
        analyzer._parse_or_retry(
            client,
            "prompt",
            cached_user_prefix="",
            response_model=analyzer.RefinementScopeResponse,
            call_kind="check_refinement_scope",
            username="",
            run_id="",
            model=HAIKU_MODEL,
            max_tokens=128,
        )


def test_demo_mode_short_circuits_before_any_client_call(monkeypatch):
    monkeypatch.setenv("SARTOR_DEMO", "1")

    class _Poison:
        def __getattr__(self, name):
            raise AssertionError(f"demo mode touched the client: .{name}")

    result = check_refinement_scope(_Poison(), "make it punchier")

    assert result == {"valid": True}


def test_scope_check_system_prompt_is_registered():
    assert "SCOPE_CHECK_SYSTEM_PROMPT" in analyzer._BASE_SYSTEM_PROMPTS
    assert (
        analyzer._BASE_SYSTEM_PROMPTS["SCOPE_CHECK_SYSTEM_PROMPT"]
        is analyzer.SCOPE_CHECK_SYSTEM_PROMPT
    )

"""C1c — error capture in `logs/llm_calls.jsonl` (`analyzer._call_llm_streaming`).

`docs/dev/handoffs/epic-c-c1c-brief.md`: C2's `wf_697596d4-c2f` escalated because a
failed call's `finally`-block telemetry row carried no exception text — `status="error"`
with nothing else, so UX-8's "recent error records with messages" had no messages to
show. This file proves the fix at the funnel `_call_llm_streaming` writes through
(`_emit_call_log`, via the `tests/conftest.py` autouse `LOG_PATH` redirect — no extra
redirect fixture needed here), and unit-tests the redaction/size helper in isolation.

Two halves:
  - `TestErrorRowCarriesFields` — drives the real `_call_llm_streaming` generator
    against fake clients that fail in each of its two `except` branches (a plain
    `TypeError` staying itself, and the SDK's auth-refusal `TypeError` re-labeled to
    `LLMConfigurationError`) plus a generic `anthropic.APIError` subclass, and asserts
    the resulting `status="error"` row's `error_type`/`error_message`. A matching ok-row
    test proves the two keys are ABSENT (not null) when `status="ok"`, per the brief's
    "readers already tolerate absence" contract.
  - `TestRedactErrorMessage` — one test per redaction/size rule in isolation, no SDK
    involved.
"""

from __future__ import annotations

import json

import anthropic
import httpx
import pytest

from analyzer import (
    LLMConfigurationError,
    _call_llm_streaming,
    _redact_error_message,
)


def _drain(gen):
    return list(gen)


def _read_rows(log_path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class _FakeUsage:
    input_tokens = 10
    output_tokens = 2
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _FakeFinal:
    usage = _FakeUsage()
    stop_reason = "end_turn"


class _OkStream:
    text_stream = iter(["hi"])

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def get_final_message(self):
        return _FakeFinal()


class _OkMessages:
    def stream(self, **_kwargs):
        return _OkStream()


def _ok_client() -> anthropic.Anthropic:
    client = anthropic.Anthropic(api_key="sk-not-a-real-key")
    client.messages = _OkMessages()  # type: ignore[misc,assignment]
    return client


class _BoomMessages:
    """Raises whatever exception instance it's constructed with, from `.stream()`."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def stream(self, **_kwargs):
        raise self._exc


def _boom_client(exc: Exception) -> anthropic.Anthropic:
    client = anthropic.Anthropic(api_key="sk-not-a-real-key")
    client.messages = _BoomMessages(exc)  # type: ignore[misc,assignment]
    return client


def _make_api_status_error(message: str) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=529, request=request)
    return anthropic.APIStatusError(message, response=response, body=None)


class TestErrorRowCarriesFields:
    def test_ok_row_has_no_error_fields(self, tmp_path) -> None:
        """`tests/conftest.py`'s autouse fixture already points `analyzer.LOG_PATH` at
        this test's own `tmp_path` — the same one this assertion reads back."""
        result = _drain(_call_llm_streaming(_ok_client(), "hi", call_kind="analyze"))

        assert result[-1].text == "hi"
        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "ok"
        assert "error_type" not in rows[0]
        assert "error_message" not in rows[0]

    def test_an_ordinary_typeerror_row_carries_its_own_type_and_message(self, tmp_path) -> None:
        with pytest.raises(TypeError):
            _drain(
                _call_llm_streaming(
                    _boom_client(TypeError("unsupported operand type(s) for +: 'int' and 'str'")),
                    "hi",
                    call_kind="analyze",
                )
            )

        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "error"
        assert rows[0]["error_type"] == "TypeError"
        assert "unsupported operand" in rows[0]["error_message"]

    def test_the_relabeled_credential_error_row_names_the_type_actually_raised(
        self, tmp_path
    ) -> None:
        """The brief's explicit instruction: when the TypeError branch re-labels the
        error to `LLMConfigurationError`, the row names `LLMConfigurationError` — the
        type the caller actually sees — not the `TypeError` that was caught."""
        sdk_typeerror = TypeError(
            '"Could not resolve authentication method. Expected either '
            'api_key or auth_token to be set."'
        )
        with pytest.raises(LLMConfigurationError):
            _drain(_call_llm_streaming(_boom_client(sdk_typeerror), "hi", call_kind="analyze"))

        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "error"
        assert rows[0]["error_type"] == "LLMConfigurationError"
        assert "no credential" in rows[0]["error_message"]

    def test_an_api_status_error_row_carries_its_class_name_and_response_body(
        self, tmp_path
    ) -> None:
        exc = _make_api_status_error("Error code: 529 - {'error': {'message': 'Overloaded'}}")
        with pytest.raises(anthropic.APIStatusError):
            _drain(_call_llm_streaming(_boom_client(exc), "hi", call_kind="analyze"))

        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "error"
        assert rows[0]["error_type"] == "APIStatusError"
        assert "Overloaded" in rows[0]["error_message"]


class TestRedactErrorMessage:
    def test_collapses_whitespace_runs(self) -> None:
        assert _redact_error_message("a\n\n  b\tc   d") == "a b c d"

    def test_masks_api_key_shaped_substrings(self) -> None:
        out = _redact_error_message("auth failed for sk-ant-api03-AbCd1234_-XYZ")
        assert "sk-ant-***" in out
        assert "AbCd1234" not in out

    def test_masks_header_values_case_insensitively(self) -> None:
        out = _redact_error_message("sent x-api-key: sk-live-abc123 to the server")
        assert "sk-live-abc123" not in out
        assert "x-api-key: ***" in out

        out2 = _redact_error_message("Authorization=Bearer deadbeef123")
        assert "deadbeef123" not in out2
        assert "Authorization: ***" in out2

    def test_truncates_to_500_chars_with_marker(self) -> None:
        out = _redact_error_message("x" * 1000)
        assert len(out) == 500
        assert out.endswith("…[truncated]")

    def test_short_message_is_untruncated_and_unmarked(self) -> None:
        out = _redact_error_message("short and clean")
        assert out == "short and clean"
        assert "truncated" not in out

    def test_empty_message_stays_empty(self) -> None:
        assert _redact_error_message("") == ""

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
    _ERROR_MESSAGE_MAX_CHARS,
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

    def test_a_secret_shaped_overlong_message_is_redacted_and_capped_at_the_funnel(
        self, tmp_path
    ) -> None:
        """Epic-close fix (R2-1): the redaction tests below exercise the helper in
        isolation; nothing proved the CALL SITES route through it. Replacing
        `_redact_error_message(...)` with a raw `str(exc)` in `_call_llm_streaming`'s
        `except` blocks must fail this test. (The fake key is deliberately short of
        the repo's block-secrets guard threshold, like the helper tests below.)"""
        fake_key = "sk-ant-api03-SeCrEt_9x"
        header_value = "hdr-secret-9f8e7d"
        message = (
            f"upstream said: key {fake_key} rejected;\n\tx-api-key: {header_value} " + "z" * 2000
        )
        with pytest.raises(RuntimeError):
            _drain(
                _call_llm_streaming(_boom_client(RuntimeError(message)), "hi", call_kind="analyze")
            )

        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        logged = rows[0]["error_message"]
        assert rows[0]["error_type"] == "RuntimeError"
        assert "SeCrEt" not in logged
        assert header_value not in logged
        assert "sk-ant-***" in logged
        assert "x-api-key: ***" in logged
        assert "\n" not in logged and "\t" not in logged
        assert len(logged) <= _ERROR_MESSAGE_MAX_CHARS
        assert logged.endswith("…[truncated]")

    def test_an_exception_whose_str_raises_does_not_replace_the_callers_error(
        self, tmp_path
    ) -> None:
        """Epic-close fix (R1-2): a failing `__str__` inside the capture must not
        swap the exception the caller sees for the one `__str__` raised."""

        class _UnprintableError(RuntimeError):
            def __str__(self) -> str:
                raise ValueError("__str__ blew up")

        with pytest.raises(_UnprintableError):
            _drain(
                _call_llm_streaming(_boom_client(_UnprintableError()), "hi", call_kind="analyze")
            )

        rows = _read_rows(tmp_path / "llm_calls.jsonl")
        assert len(rows) == 1, rows
        assert rows[0]["error_type"] == "_UnprintableError"
        assert "_UnprintableError" in rows[0]["error_message"]


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

    def test_cap_is_500_chars(self) -> None:
        """Pins the cap itself (R2-5) — the funnel test above reads it from the module."""
        assert _ERROR_MESSAGE_MAX_CHARS == 500

    def test_masks_before_truncating(self) -> None:
        """Pins mask-before-truncate order (R2-5). Masking a long key shrinks the text
        under the cap, so a mask-first helper never truncates; a truncate-first helper
        would cut (and mark) the raw text before the mask ran."""
        out = _redact_error_message("sk-ant-" + "A" * 600)
        assert out == "sk-ant-***"

    @pytest.mark.parametrize(
        ("message", "secret"),
        [
            # Item 118: a dict/JSON repr of request headers quotes the key, so the old
            # `\bx-api-key\s*[:=]` never matched `'x-api-key': '...'`.
            ("headers={'x-api-key': 'sk-live-abc123', 'a': 'b'}", "sk-live-abc123"),
            ('{"authorization": "Bearer deadbeef123"}', "deadbeef123"),
            ('{"X-Api-Key":"sk-live-q9"}', "sk-live-q9"),
            # Basic auth: the old pattern masked only the word "Basic".
            ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpwYXNzd29yZA=="),
            ("{'authorization': 'Basic dXNlcjpwYXNz'}", "dXNlcjpwYXNz"),
        ],
    )
    def test_masks_quoted_key_and_basic_auth_forms(self, message: str, secret: str) -> None:
        out = _redact_error_message(message)
        assert secret not in out, out
        assert "***" in out

    def test_a_key_straddling_the_cut_is_masked_whole(self) -> None:
        out = _redact_error_message("x" * 485 + "sk-ant-" + "B" * 100)
        assert out == "x" * 485 + "sk-ant-***"
        assert "B" not in out

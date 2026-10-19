"""Item 175: every telemetry row records what answered the call and the settings sent.

The fail-closed half (charter C-11) is `test_every_request_kwarg_is_recorded`: it asserts the
row's `request_settings` mirrors the kwargs the stub client actually received, so a setting
added to `_call_llm_streaming` later but not recorded fails here instead of silently going
missing. The other tests pin how the row copes with the three kinds of stand-in client the
suite uses (a rich one, plain classes with no provenance attributes, and bare MagicMocks) and
the retry's `attempt` numbering. See `docs/dev/diagnosis/llm-call-provenance.md`.

Offline: `_emit_call_log` is redirected for every test, so no row reaches the real log.
Bodies are untyped like the rest of tests/ (the fake client is a duck-typed stand-in).
"""

from __future__ import annotations

import json
from typing import ClassVar
from unittest.mock import MagicMock

import pytest

import analyzer
from analyzer import HAIKU_MODEL, SONNET_MODEL, LLMResponseError

PROMPT_SENTINEL = "SENTINEL-PROMPT-TEXT-must-never-be-logged"
_REAL_EMIT = analyzer._emit_call_log


class _Usage:
    input_tokens = 10
    output_tokens = 5
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _RichUsage(_Usage):
    service_tier = "standard"
    speed = "standard"
    inference_geo = "global"
    output_tokens_details: ClassVar[dict[str, int]] = {"thinking_tokens": 7}


class _Final:
    stop_reason = "end_turn"

    def __init__(self, usage, model=None):
        self.usage = usage
        if model is not None:
            self.model = model


class _Stream:
    def __init__(self, text, final, request_id=None, fail_after_open=None):
        self._text = text
        self._final = final
        self._fail_after_open = fail_after_open
        if request_id is not None:
            self.request_id = request_id

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        if self._fail_after_open is not None:
            raise self._fail_after_open
        yield self._text

    def get_final_message(self):
        return self._final


class _Messages:
    def __init__(self, streams, captured):
        self._streams = list(streams)
        self._captured = captured

    def stream(self, **kwargs):
        self._captured.append(kwargs)
        item = self._streams.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Client:
    def __init__(self, streams):
        self.captured: list[dict] = []
        self.messages = _Messages(streams, self.captured)


@pytest.fixture(autouse=True)
def _rows(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", rows.append)
    return rows


def _rich_stream(text="ok"):
    return _Stream(text, _Final(_RichUsage(), model="claude-x"), request_id="req_abc")


@pytest.mark.parametrize("model", [None, HAIKU_MODEL])
def test_every_request_kwarg_is_recorded(_rows, model):
    """C-11: the row mirrors the kwargs actually sent, minus the prompt content."""
    client = _Client([_rich_stream()])

    analyzer._call_llm(client, PROMPT_SENTINEL, call_kind="t", model=model, max_tokens=64)

    sent = client.captured[0]
    settings = _rows[0]["request_settings"]
    assert set(settings) == set(sent) - {"system", "messages"}
    for key, value in settings.items():
        assert value == sent[key]
    # `thinking` is sent exactly when the model's policy has a value: the row shows which.
    assert ("thinking" in settings) == (analyzer.THINKING_POLICY[model or SONNET_MODEL] is not None)
    assert settings["max_tokens"] == 64


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (SONNET_MODEL, {"type": "disabled"}),  # today's behavior, unchanged
        (HAIKU_MODEL, None),  # today's behavior, unchanged: the field is not sent
        ("claude-sonnet-5-5", {"type": "between_tools"}),  # `disabled` is a 400 on this model
        ("claude-haiku-5-5", {"type": "disabled"}),  # holds thinking-off explicitly
    ],
)
def test_thinking_value_sent_follows_the_models_policy(_rows, model, expected):
    client = _Client([_rich_stream()])

    analyzer._call_llm(client, "p", call_kind="t", model=model)

    sent = client.captured[0]
    assert sent.get("thinking") == expected
    assert ("thinking" in sent) == (expected is not None)
    assert _rows[0]["request_settings"].get("thinking") == expected


def test_model_without_a_thinking_policy_is_refused_before_the_request(_rows):
    """Fail closed: guessing would silently turn adaptive thinking on (item 137)."""
    client = _Client([_rich_stream()])

    with pytest.raises(analyzer.LLMConfigurationError, match="claude-unlisted-9"):
        analyzer._call_llm(client, "p", call_kind="t", model="claude-unlisted-9")

    assert client.captured == []  # no request left the process
    assert len(_rows) == 1
    assert _rows[0]["status"] == "error"
    assert _rows[0]["error_type"] == "LLMConfigurationError"
    assert _rows[0]["request_settings"] is None  # nothing was sent, so nothing is claimed


def test_prompt_text_never_reaches_the_row(_rows):
    client = _Client([_rich_stream()])

    analyzer._call_llm(client, PROMPT_SENTINEL, cached_user_prefix=PROMPT_SENTINEL, call_kind="t")

    assert PROMPT_SENTINEL not in json.dumps(_rows[0])


def test_rich_response_fills_every_provenance_field(_rows):
    client = _Client([_rich_stream()])

    analyzer._call_llm(client, "p", call_kind="t")

    row = _rows[0]
    assert row["model"] == SONNET_MODEL  # still "the id requested"
    assert row["answered_model"] == "claude-x"
    assert row["api_request_id"] == "req_abc"
    assert row["served_as"] == {
        "service_tier": "standard",
        "speed": "standard",
        "inference_geo": "global",
    }
    assert row["thinking_tokens"] == 7
    assert row["attempt"] == 1


def test_thinking_tokens_from_an_attribute_style_details_object(_rows):
    class _Details:
        thinking_tokens = 3

    class _U(_Usage):
        output_tokens_details = _Details()

    client = _Client([_Stream("ok", _Final(_U()))])

    analyzer._call_llm(client, "p", call_kind="t")

    assert _rows[0]["thinking_tokens"] == 3


def test_plain_fake_without_provenance_attributes_gets_none_not_a_crash(_rows):
    client = _Client([_Stream("ok", _Final(_Usage()))])

    analyzer._call_llm(client, "p", call_kind="t")

    row = _rows[0]
    assert row["status"] == "ok"
    assert row["answered_model"] is None
    assert row["api_request_id"] is None
    assert row["served_as"] is None
    assert row["thinking_tokens"] is None


def test_magicmock_fake_leaves_a_parseable_log_line(monkeypatch, tmp_path):
    """The MagicMock fakes in the suite must not turn the log into an empty file.

    `_emit_call_log` opens the file before `json.dumps`, so one MagicMock reaching the row would
    leave a zero-byte log (and swallow the error). The legacy fields are configured the way
    `tests/test_analyzer_model_selection.py` does it; every NEW field is left auto-mocked.
    """
    monkeypatch.setattr(analyzer, "_emit_call_log", _REAL_EMIT)
    monkeypatch.setattr(analyzer, "LOG_DIR", tmp_path)
    monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "llm_calls.jsonl")
    final = MagicMock()
    final.usage.input_tokens = 10
    final.usage.output_tokens = 5
    final.usage.cache_creation_input_tokens = 0
    final.usage.cache_read_input_tokens = 0
    final.stop_reason = "end_turn"
    stream = MagicMock()
    stream.__enter__.return_value = stream
    stream.text_stream = iter(["ok"])
    stream.get_final_message.return_value = final
    client = MagicMock()
    client.messages.stream.return_value = stream

    analyzer._call_llm(client, "p", call_kind="t")

    lines = (tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["answered_model"] is None
    assert row["api_request_id"] is None
    assert row["thinking_tokens"] is None
    assert row["served_as"] is None


def test_unserialisable_request_kwarg_is_recorded_as_text_not_dropped_or_fatal():
    fields = analyzer._provenance_fields(
        {"model": "m", "system": "s", "messages": [], "odd": object()},
        answered_model=None,
        api_request_id=None,
        usage=None,
        attempt=1,
    )

    assert set(fields["request_settings"]) == {"model", "odd"}
    assert isinstance(fields["request_settings"]["odd"], str)
    json.dumps(fields)


def test_refused_call_logs_settings_and_no_request_id(_rows):
    client = _Client([ConnectionError("upstream unavailable")])

    with pytest.raises(ConnectionError):
        analyzer._call_llm(client, "p", call_kind="t")

    row = _rows[0]
    assert row["status"] == "error"
    assert row["api_request_id"] is None
    assert row["request_settings"]["max_tokens"] == analyzer.MAX_TOKENS


def test_mid_stream_failure_still_logs_the_request_id(_rows):
    client = _Client(
        [
            _Stream(
                "x", _Final(_Usage()), request_id="req_mid", fail_after_open=ConnectionError("cut")
            )
        ]
    )

    with pytest.raises(ConnectionError):
        analyzer._call_llm(client, "p", call_kind="t")

    row = _rows[0]
    assert row["status"] == "error"
    assert row["api_request_id"] == "req_mid"


def test_retry_rows_carry_attempt_numbers(_rows):
    client = _Client([_rich_stream("not json"), _rich_stream('{"valid": true}')])

    analyzer._parse_or_retry(
        client,
        "p",
        cached_user_prefix="",
        response_model=analyzer.RefinementScopeResponse,
        call_kind="k",
        username="",
        run_id="",
    )

    assert [(r["call"], r["attempt"]) for r in _rows] == [("k", 1), ("k_retry", 2)]


def test_streaming_retry_rows_carry_attempt_numbers(_rows):
    client = _Client([_rich_stream("not json"), _rich_stream('{"valid": true}')])

    events = list(
        analyzer._parse_or_retry_streaming(
            client,
            "p",
            cached_user_prefix="",
            response_model=analyzer.RefinementScopeResponse,
            call_kind="k",
            username="",
            run_id="",
        )
    )

    assert events[-1][0] == "done"
    assert [(r["call"], r["attempt"]) for r in _rows] == [("k", 1), ("k_retry", 2)]


def test_exhausted_retries_log_both_attempts(_rows):
    client = _Client([_rich_stream("nope"), _rich_stream("still nope")])

    with pytest.raises(LLMResponseError):
        analyzer._parse_or_retry(
            client,
            "p",
            cached_user_prefix="",
            response_model=analyzer.RefinementScopeResponse,
            call_kind="k",
            username="",
            run_id="",
            max_tokens=128,
        )

    assert [r["attempt"] for r in _rows] == [1, 2]
    assert [r["request_settings"]["max_tokens"] for r in _rows] == [128, 128]


def test_prompt_version_override_is_logged(_rows):
    client = _Client([_rich_stream()])

    list(analyzer._call_llm_streaming(client, "p", call_kind="t", prompt_version="avatar-v"))

    assert _rows[0]["prompt_version"] == "avatar-v"

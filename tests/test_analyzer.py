"""Tests for the LLM-response parsing layer in analyzer.py.

Covers _strip_fences and _parse_or_retry. The retry helper is exercised by
monkey-patching analyzer._call_llm to return a pre-scripted list of responses,
which keeps the tests free of any real Anthropic SDK or network dependency.
"""

import json

import pytest

import analyzer
from analyzer import (
    ANALYZE_REQUIRED_KEYS,
    LLMResponseError,
    _parse_or_retry,
    _strip_fences,
)

# ---------- _strip_fences ---------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"a": 1}', '{"a": 1}'),
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('  ```json\n{"a": 1}\n```  ', '{"a": 1}'),
        ('```json{"a": 1}```', '{"a": 1}'),
    ],
)
def test_strip_fences_variants(raw, expected):
    assert _strip_fences(raw) == expected


# ---------- _parse_or_retry happy paths -------------------------------------

def _scripted_call_llm(responses):
    """Build a fake _call_llm that pops one response per call.

    Records call_kinds it was invoked with so tests can assert on retry naming.
    """
    calls: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id):
        calls.append(call_kind)
        return responses.pop(0)

    fake.calls = calls
    return fake


def _valid_analysis_json() -> str:
    body = {k: [] if k != "ideal_resume_profile" and k != "overall_strategy"
            and k != "comparison" else
            ("text" if k != "comparison" else {})
            for k in ANALYZE_REQUIRED_KEYS}
    return json.dumps(body)


def test_parse_or_retry_happy_path(monkeypatch):
    fake = _scripted_call_llm([_valid_analysis_json()])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze"]  # no retry needed


def test_parse_or_retry_strips_markdown_fences(monkeypatch):
    fenced = f"```json\n{_valid_analysis_json()}\n```"
    fake = _scripted_call_llm([fenced])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze"]


# ---------- _parse_or_retry retry succeeds ----------------------------------

def test_parse_or_retry_recovers_from_missing_keys(monkeypatch):
    """First response is missing required keys; second is valid."""
    fake = _scripted_call_llm([
        json.dumps({"essential_skills": []}),  # missing nearly everything
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_recovers_from_invalid_json(monkeypatch):
    """First response is unparseable; second is valid."""
    fake = _scripted_call_llm([
        "this is not json at all { unterminated",
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze", "analyze_retry"]


# ---------- _parse_or_retry retry exhausted ---------------------------------

def test_parse_or_retry_raises_on_persistent_missing_keys(monkeypatch):
    bad = json.dumps({"essential_skills": []})
    fake = _scripted_call_llm([bad, bad])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    with pytest.raises(LLMResponseError) as excinfo:
        _parse_or_retry(
            client=None, base_prompt="prompt",
            cached_user_prefix="prefix",
            required_keys=ANALYZE_REQUIRED_KEYS,
            call_kind="analyze", username="u", run_id="r",
        )

    assert "missing required keys" in excinfo.value.validation_error
    assert excinfo.value.raw == bad
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_raises_on_persistent_invalid_json(monkeypatch):
    junk = "not json"
    fake = _scripted_call_llm([junk, junk])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    with pytest.raises(LLMResponseError) as excinfo:
        _parse_or_retry(
            client=None, base_prompt="prompt",
            cached_user_prefix="prefix",
            required_keys=ANALYZE_REQUIRED_KEYS,
            call_kind="analyze", username="u", run_id="r",
        )

    assert excinfo.value.raw == junk
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_uses_retry_call_kind(monkeypatch):
    """Retry must use call_kind '<orig>_retry' for dashboard attribution."""
    fake = _scripted_call_llm([
        "junk",
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="generate", username="u", run_id="r",
    )

    assert fake.calls == ["generate", "generate_retry"]

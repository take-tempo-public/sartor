"""Tests for the context_probe enforcement added in r1/structural-context-probe.

Covers:
  - ClarifyResponse Pydantic validator (4 branches)
  - _parse_or_retry validation_context threading (2 cases)

No LLM calls — all tests mock at the _call_llm boundary.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import analyzer
from analyzer import ClarifyResponse, LLMResponseError, _parse_or_retry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _questions(kinds: list[str]) -> list[dict]:
    return [
        {
            "id": f"q{i + 1}",
            "text": f"Question {i + 1}?",
            "target_gap": "some gap",
            "kind": kind,
        }
        for i, kind in enumerate(kinds)
    ]


def _valid_payload(kinds: list[str]) -> dict:
    return {
        "questions": _questions(kinds),
        "reasoning": "Composed to cover gaps.",
    }


# ---------------------------------------------------------------------------
# ClarifyResponse model validator — 4 branches
# ---------------------------------------------------------------------------

class TestClarifyResponseValidator:
    def test_passes_when_context_probe_present_and_hq_non_empty(self):
        """context_probe in output + hidden_qualities non-empty → OK."""
        data = _valid_payload(["experience_probe", "context_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(
            data, context={"hidden_qualities_non_empty": True}
        )
        assert result.questions is not None

    def test_raises_when_no_context_probe_and_hq_non_empty(self):
        """No context_probe + hidden_qualities non-empty → ValidationError."""
        data = _valid_payload(["experience_probe", "scope_probe"])
        with pytest.raises(ValidationError) as exc_info:
            ClarifyResponse.model_validate(
                data, context={"hidden_qualities_non_empty": True}
            )
        assert "context_probe" in str(exc_info.value)

    def test_passes_when_hq_empty_and_no_context_probe(self):
        """hidden_qualities empty → context_probe not required."""
        data = _valid_payload(["experience_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(
            data, context={"hidden_qualities_non_empty": False}
        )
        assert result.questions is not None

    def test_passes_when_no_context_dict_at_all(self):
        """No validation context passed (backward compat) → no enforcement."""
        data = _valid_payload(["experience_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(data)
        assert result.questions is not None


# ---------------------------------------------------------------------------
# _parse_or_retry — validation_context threading
# ---------------------------------------------------------------------------

class TestParseOrRetryValidationContext:
    """Verify that _parse_or_retry passes validation_context to model_validate
    and that a ValidationError from the context check triggers a retry."""

    def _make_client(self, *responses: str) -> MagicMock:
        client = MagicMock()
        return client

    def test_threads_context_and_succeeds_on_valid_response(self):
        """When validation_context says hq_non_empty=True and response has
        context_probe, _parse_or_retry returns the parsed dict on first try."""
        payload = _valid_payload(["experience_probe", "context_probe"])
        raw_json = json.dumps(payload)

        client = MagicMock()
        with patch.object(analyzer, "_call_llm", return_value=raw_json):
            result = _parse_or_retry(
                client,
                "prompt text",
                cached_user_prefix="",
                response_model=ClarifyResponse,
                call_kind="clarify",
                username="testuser",
                run_id="abc",
                validation_context={"hidden_qualities_non_empty": True},
            )
        assert result["questions"][1]["kind"] == "context_probe"

    def test_retries_when_context_probe_missing_with_hq_non_empty(self):
        """When hq_non_empty=True but first response has no context_probe,
        _parse_or_retry retries once.  If retry also fails, LLMResponseError is raised."""
        bad_payload = _valid_payload(["experience_probe", "scope_probe"])
        raw_bad = json.dumps(bad_payload)

        call_count = {"n": 0}

        def fake_call_llm(*args, **kwargs):
            call_count["n"] += 1
            return raw_bad

        client = MagicMock()
        with patch.object(analyzer, "_call_llm", side_effect=fake_call_llm):
            with pytest.raises(LLMResponseError):
                _parse_or_retry(
                    client,
                    "prompt text",
                    cached_user_prefix="",
                    response_model=ClarifyResponse,
                    call_kind="clarify",
                    username="testuser",
                    run_id="abc",
                    validation_context={"hidden_qualities_non_empty": True},
                )
        # max_attempts=2: first call + one retry
        assert call_count["n"] == 2

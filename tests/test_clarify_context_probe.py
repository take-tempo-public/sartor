"""Tests for the composition enforcement added in r1/structural-context-probe.

Covers:
  - ClarifyResponse Pydantic validator: context_probe requirement (rule 1)
  - ClarifyResponse Pydantic validator: ≥60% combined rule (rule 2)
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
# Rule 1: context_probe required when hidden_qualities non-empty
# ---------------------------------------------------------------------------


class TestContextProbeRequirement:
    def test_passes_when_context_probe_present_and_hq_non_empty(self):
        """context_probe + hq non-empty + ≥60% combined → OK."""
        # 2/3 experience+context = 67% ✓
        data = _valid_payload(["experience_probe", "context_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(data, context={"hidden_qualities_non_empty": True})
        assert result.questions is not None

    def test_raises_when_no_context_probe_and_hq_non_empty(self):
        """No context_probe + hq non-empty → ValidationError citing context_probe."""
        # 3/3 experience = 100%, passes 60% rule but fails rule 1
        data = _valid_payload(["experience_probe", "experience_probe", "scope_probe"])
        with pytest.raises(ValidationError) as exc_info:
            ClarifyResponse.model_validate(data, context={"hidden_qualities_non_empty": True})
        assert "context_probe" in str(exc_info.value)

    def test_passes_when_hq_empty_and_no_context_probe(self):
        """hidden_qualities empty → context_probe not required; 60% rule still applies."""
        # 2/3 experience = 67% ✓, no context_probe (HQ empty so rule 1 waived)
        data = _valid_payload(["experience_probe", "experience_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(data, context={"hidden_qualities_non_empty": False})
        assert result.questions is not None

    def test_passes_when_no_context_dict_at_all(self):
        """No validation context (backward compat) → no rule-1 enforcement; rule 2 still applies."""
        # 2/3 experience = 67% ✓
        data = _valid_payload(["experience_probe", "experience_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(data)
        assert result.questions is not None


# ---------------------------------------------------------------------------
# Rule 2: ≥60% combined experience_probe + context_probe
# ---------------------------------------------------------------------------


class TestCombinedCompositionRule:
    # All tests in this class pass validation_context (enforcement is opt-in —
    # only fires when the caller explicitly provides context, so clarify_iteration
    # with its different kind set isn't affected).
    _ctx = {"hidden_qualities_non_empty": False}

    def test_passes_at_60_percent_combined(self):
        """Exactly 60% combined (3/5) → passes."""
        data = _valid_payload(
            ["experience_probe", "context_probe", "experience_probe", "scope_probe", "scope_probe"]
        )
        result = ClarifyResponse.model_validate(data, context=self._ctx)
        assert result.questions is not None

    def test_raises_below_60_percent_combined(self):
        """40% combined (2/5) → ValidationError citing 60% threshold."""
        data = _valid_payload(
            ["experience_probe", "context_probe", "scope_probe", "scope_probe", "scope_probe"]
        )
        with pytest.raises(ValidationError) as exc_info:
            ClarifyResponse.model_validate(data, context=self._ctx)
        assert "60%" in str(exc_info.value)

    def test_raises_when_all_scope_probes(self):
        """All scope_probes (0% combined) → ValidationError."""
        data = _valid_payload(["scope_probe", "scope_probe", "scope_probe"])
        with pytest.raises(ValidationError):
            ClarifyResponse.model_validate(data, context=self._ctx)

    def test_passes_when_only_experience_probes(self):
        """100% experience_probes → passes (no context_probe required when HQ empty)."""
        data = _valid_payload(["experience_probe", "experience_probe", "experience_probe"])
        result = ClarifyResponse.model_validate(data, context={"hidden_qualities_non_empty": False})
        assert result.questions is not None

    def test_no_enforcement_without_context(self):
        """Without validation_context (e.g. clarify_iteration), no 60% rule fires."""
        # This would fail the 60% rule if enforcement were active (0/3 combined)
        data = _valid_payload(["scope_probe", "scope_probe", "scope_probe"])
        result = ClarifyResponse.model_validate(data)
        assert result.questions is not None


# ---------------------------------------------------------------------------
# _parse_or_retry — validation_context threading
# ---------------------------------------------------------------------------


class TestParseOrRetryValidationContext:
    """Verify _parse_or_retry threads validation_context to model_validate and
    that a ValidationError from the context check triggers the retry path."""

    def test_threads_context_and_succeeds_on_valid_response(self):
        """hq_non_empty=True + context_probe present + ≥60% combined → passes first try."""
        # 2/3 = 67% combined ✓, context_probe present ✓
        payload = _valid_payload(["experience_probe", "context_probe", "scope_probe"])
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

    def test_retries_when_composition_invalid(self):
        """Below 60% combined → validation fails → retry fires → LLMResponseError on exhaustion."""
        # 1/5 = 20% combined — fails rule 2 (and has no context_probe — fails rule 1 too)
        bad_payload = _valid_payload(
            ["experience_probe", "scope_probe", "scope_probe", "scope_probe", "scope_probe"]
        )
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
        # max_attempts=2: initial call + one retry
        assert call_count["n"] == 2

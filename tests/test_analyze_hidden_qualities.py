"""Tests for the hidden_qualities schema change in r1/hidden-qualities-schema.

Covers:
  - HiddenQualityItem Pydantic model: category enum enforcement
  - AnalyzeResponse: hidden_qualities typed as list[HiddenQualityItem]
    (valid structured items pass; bare-string items fail → retry trigger)
  - clarify() <context_signals> render: structured items and legacy
    list[str] items both render without error

No real LLM calls — clarify tests mock at the _call_llm boundary.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import analyzer
from analyzer import AnalyzeResponse, HiddenQualityItem

VALID_CATEGORIES = [
    "operating_context",
    "scope_of_ownership",
    "stakeholder_gravity",
    "resilience",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze_payload(hidden_qualities) -> dict:
    """A full, shape-valid AnalyzeResponse payload with a pluggable
    hidden_qualities value so tests can vary just that field."""
    return {
        "essential_skills": ["Python"],
        "preferred_skills": ["Kafka"],
        "industry_keywords": ["fintech"],
        "hidden_qualities": hidden_qualities,
        "professional_vocabulary": ["SLA"],
        "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
        "suggestions": [],
        "keyword_placement": [],
        "overall_strategy": "Position for the role.",
    }


def _clarify_questions(kinds: list[str]) -> dict:
    return {
        "questions": [
            {"id": f"q{i + 1}", "text": f"Q{i + 1}?", "target_gap": "g", "kind": k}
            for i, k in enumerate(kinds)
        ],
        "reasoning": "Composed to cover gaps.",
    }


# ---------------------------------------------------------------------------
# HiddenQualityItem — category enum enforcement
# ---------------------------------------------------------------------------

class TestHiddenQualityItem:
    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_accepts_each_valid_category(self, category):
        item = HiddenQualityItem.model_validate(
            {"category": category, "signal": "portable context"}
        )
        assert item.category == category
        assert item.signal == "portable context"

    def test_rejects_invalid_category(self):
        with pytest.raises(ValidationError) as exc_info:
            HiddenQualityItem.model_validate(
                {"category": "collaborative", "signal": "trait-word, not a context"}
            )
        # The Literal error names the allowed values — this is the structured
        # message _parse_or_retry appends to the retry prompt.
        assert "category" in str(exc_info.value)

    def test_rejects_missing_category(self):
        with pytest.raises(ValidationError):
            HiddenQualityItem.model_validate({"signal": "no category given"})

    def test_rejects_missing_signal(self):
        with pytest.raises(ValidationError):
            HiddenQualityItem.model_validate({"category": "operating_context"})


# ---------------------------------------------------------------------------
# AnalyzeResponse — hidden_qualities typed as list[HiddenQualityItem]
# ---------------------------------------------------------------------------

class TestAnalyzeResponseHiddenQualities:
    def test_passes_with_structured_items(self):
        payload = _analyze_payload(
            [
                {"category": "operating_context", "signal": "regulated workflows"},
                {"category": "scope_of_ownership", "signal": "0→1 ownership"},
            ]
        )
        result = AnalyzeResponse.model_validate(payload)
        assert len(result.hidden_qualities) == 2
        assert result.hidden_qualities[0].category == "operating_context"

    def test_passes_with_empty_list(self):
        result = AnalyzeResponse.model_validate(_analyze_payload([]))
        assert result.hidden_qualities == []

    def test_rejects_bare_string_items(self):
        """Legacy list[str] shape must fail so _parse_or_retry forces a retry
        into the new structured shape."""
        with pytest.raises(ValidationError):
            AnalyzeResponse.model_validate(_analyze_payload(["autonomous", "collaborative"]))

    def test_rejects_invalid_category_in_list(self):
        with pytest.raises(ValidationError):
            AnalyzeResponse.model_validate(
                _analyze_payload([{"category": "team_player", "signal": "x"}])
            )


# ---------------------------------------------------------------------------
# clarify() <context_signals> render — structured + legacy tolerant
# ---------------------------------------------------------------------------

class TestClarifyContextSignalsRender:
    def _run_clarify(self, hidden_qualities):
        """Run clarify() with _call_llm mocked; return (parsed_result, prompt_sent)."""
        analysis = {
            "essential_skills": ["Python"],
            "preferred_skills": [],
            "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
            "keyword_placement": [],
            "overall_strategy": "Position for the role.",
            "hidden_qualities": hidden_qualities,
        }
        # Non-empty HQ → validator requires a context_probe + >=60% combined.
        raw = json.dumps(_clarify_questions(["experience_probe", "context_probe", "scope_probe"]))
        with patch.object(analyzer, "_call_llm", return_value=raw) as m:
            result = analyzer.clarify(MagicMock(), {}, analysis, username="t", run_id="r")
        prompt_sent = m.call_args.args[1]
        return result, prompt_sent

    def test_structured_items_render_category_and_signal(self):
        result, prompt = self._run_clarify(
            [{"category": "operating_context", "signal": "regulated workflows"}]
        )
        assert "[operating_context] regulated workflows" in prompt
        assert result["questions"][1]["kind"] == "context_probe"

    def test_legacy_string_items_render_without_error(self):
        """An older saved analysis (list[str]) must not crash clarify()."""
        result, prompt = self._run_clarify(["legacy trait signal"])
        assert "- legacy trait signal" in prompt
        assert result["questions"] is not None

    def test_empty_hidden_qualities_renders_placeholder(self):
        result, prompt = self._run_clarify([])
        assert "(none)" in prompt
        assert result["questions"] is not None

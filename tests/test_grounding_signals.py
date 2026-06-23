"""Tests for evals/grounding_signals.

All model calls are mocked via dependency injection — no transformers,
torch, or minicheck install required to run this test suite.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evals.grounding_signals import (
    extract_bullets,
    run_grounding_signals,
    score_minicheck_bullets,
    score_nli_bullets,
)


class TestExtractBullets:
    def test_basic(self):
        resume = "## Experience\n- Led a team\n- Shipped product\n"
        assert extract_bullets(resume) == ["Led a team", "Shipped product"]

    def test_empty_string(self):
        assert extract_bullets("") == []

    def test_no_bullets(self):
        assert extract_bullets("## Experience\nSome prose with no bullets.\n") == []

    def test_strips_leading_whitespace_on_line(self):
        assert extract_bullets("  - Indented bullet\n") == ["Indented bullet"]

    def test_ignores_headers_and_blank_lines(self):
        resume = "# Name\n\n## Experience\n- Bullet one\n\n- Bullet two\n"
        assert extract_bullets(resume) == ["Bullet one", "Bullet two"]

    def test_skips_blank_bullet_text(self):
        # A line that is just "- " (no text after) should not produce an entry
        assert extract_bullets("- \n- real bullet\n") == ["real bullet"]


class TestScoreNliBullets:
    def _mock_pipeline(self, entailment: float, contradiction: float) -> MagicMock:
        neutral = max(0.0, round(1.0 - entailment - contradiction, 4))
        return MagicMock(return_value=[
            {"label": "entailment", "score": entailment},
            {"label": "neutral", "score": neutral},
            {"label": "contradiction", "score": contradiction},
        ])

    def test_high_entailment_no_flag(self):
        pipeline = self._mock_pipeline(entailment=0.9, contradiction=0.05)
        results = score_nli_bullets(["Led a team"], "Led a team of engineers", _pipeline=pipeline)
        assert len(results) == 1
        assert results[0]["nli_entailment_score"] == pytest.approx(0.9)
        assert results[0]["nli_contradiction_flag"] is False

    def test_contradiction_flag_fires_above_threshold(self):
        pipeline = self._mock_pipeline(entailment=0.1, contradiction=0.8)
        results = score_nli_bullets(["Led a team of 50"], "Led a team", _pipeline=pipeline)
        assert results[0]["nli_contradiction_flag"] is True

    def test_contradiction_exactly_at_threshold_does_not_flag(self):
        # threshold is > 0.4, so exactly 0.4 must NOT flag
        pipeline = self._mock_pipeline(entailment=0.5, contradiction=0.4)
        results = score_nli_bullets(["some bullet"], "some source", _pipeline=pipeline)
        assert results[0]["nli_contradiction_flag"] is False

    def test_bullet_text_preserved_in_result(self):
        pipeline = self._mock_pipeline(entailment=0.7, contradiction=0.1)
        results = score_nli_bullets(["my specific bullet"], "source", _pipeline=pipeline)
        assert results[0]["bullet"] == "my specific bullet"

    def test_empty_bullets_returns_empty(self):
        results = score_nli_bullets([], "some source")
        assert results == []

    def test_empty_source_returns_empty(self):
        results = score_nli_bullets(["a bullet"], "")
        assert results == []


class TestScoreMinicheckBullets:
    def test_high_score(self):
        mock_scorer = MagicMock()
        # score() returns a 4-tuple (labels, probs, chunks, arrays); we read probs.
        mock_scorer.score.return_value = ([1], [0.92], None, None)
        results = score_minicheck_bullets(
            ["Led a team"], "Led a team of engineers", _scorer=mock_scorer
        )
        assert len(results) == 1
        assert results[0]["minicheck_grounding_score"] == pytest.approx(0.92)

    def test_low_score(self):
        mock_scorer = MagicMock()
        mock_scorer.score.return_value = ([0], [0.18], None, None)
        results = score_minicheck_bullets(
            ["Led a team of 50"], "Led a team", _scorer=mock_scorer
        )
        assert results[0]["minicheck_grounding_score"] == pytest.approx(0.18)

    def test_multiple_bullets_aligned_correctly(self):
        mock_scorer = MagicMock()
        mock_scorer.score.return_value = ([1, 0], [0.9, 0.3], None, None)
        results = score_minicheck_bullets(
            ["bullet one", "bullet two"], "source", _scorer=mock_scorer
        )
        assert len(results) == 2
        assert results[0]["bullet"] == "bullet one"
        assert results[0]["minicheck_grounding_score"] == pytest.approx(0.9)
        assert results[1]["bullet"] == "bullet two"
        assert results[1]["minicheck_grounding_score"] == pytest.approx(0.3)

    def test_empty_bullets_returns_empty(self):
        results = score_minicheck_bullets([], "some source")
        assert results == []

    def test_empty_source_returns_empty(self):
        results = score_minicheck_bullets(["a bullet"], "")
        assert results == []


class TestRunGroundingSignals:
    _RESUME = "## Experience\n- Led a team\n- Shipped product\n"

    def _run_with_mocks(
        self,
        mock_nli: list[dict],
        mock_mc: list[dict],
        resume: str = _RESUME,
        sources: list[str] | None = None,
    ) -> dict:
        with (
            patch("evals.grounding_signals._load_nli_pipeline", return_value=MagicMock()),
            patch("evals.grounding_signals._load_minicheck_scorer", return_value=MagicMock()),
            patch("evals.grounding_signals.score_nli_bullets", return_value=mock_nli),
            patch("evals.grounding_signals.score_minicheck_bullets", return_value=mock_mc),
        ):
            return run_grounding_signals(resume, sources or ["source text"])

    def test_empty_resume_returns_zero_state(self):
        result = run_grounding_signals("## No bullets here\nJust prose.", ["source"])
        assert result["bullet_count"] == 0
        assert result["nli"] == []
        assert result["minicheck"] == []
        assert result["nli_summary"]["mean_entailment"] == 0.0
        assert result["minicheck_summary"]["mean_score"] == 0.0

    def test_summary_means_computed_correctly(self):
        mock_nli = [
            {"bullet": "Led a team", "nli_entailment_score": 0.8, "nli_contradiction_flag": False},
            {"bullet": "Shipped product", "nli_entailment_score": 0.6, "nli_contradiction_flag": True},
        ]
        mock_mc = [
            {"bullet": "Led a team", "minicheck_grounding_score": 0.9},
            {"bullet": "Shipped product", "minicheck_grounding_score": 0.4},
        ]
        result = self._run_with_mocks(mock_nli, mock_mc)
        assert result["bullet_count"] == 2
        assert result["nli_summary"]["mean_entailment"] == pytest.approx(0.7)
        assert result["nli_summary"]["contradiction_count"] == 1
        assert result["minicheck_summary"]["mean_score"] == pytest.approx(0.65)
        assert result["minicheck_summary"]["low_score_count"] == 1

    def test_no_contradictions_and_no_low_scores(self):
        mock_nli = [
            {"bullet": "Led a team", "nli_entailment_score": 0.95, "nli_contradiction_flag": False},
        ]
        mock_mc = [
            {"bullet": "Led a team", "minicheck_grounding_score": 0.88},
        ]
        result = self._run_with_mocks(mock_nli, mock_mc, resume="## Exp\n- Led a team\n")
        assert result["nli_summary"]["contradiction_count"] == 0
        assert result["minicheck_summary"]["low_score_count"] == 0

    def test_result_contains_per_bullet_lists(self):
        mock_nli = [
            {"bullet": "Led a team", "nli_entailment_score": 0.8, "nli_contradiction_flag": False},
        ]
        mock_mc = [
            {"bullet": "Led a team", "minicheck_grounding_score": 0.75},
        ]
        result = self._run_with_mocks(mock_nli, mock_mc, resume="## Exp\n- Led a team\n")
        assert result["nli"] == mock_nli
        assert result["minicheck"] == mock_mc

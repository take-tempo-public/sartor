"""Unit tests for evals/runner.py and dashboard normalization.

These cover the eval-result schema migration (0-5 int → 0.0-5.0 float),
the score-coercion safety net at the judge boundary, and the dashboard's
backward-compatible record normalization.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dashboard.routes import _normalize_eval_record


class TestNormalizeEvalRecord:
    """The dashboard reads old (int score) and new (float score) records side
    by side. _normalize_eval_record coerces them to a single shape."""

    def test_int_score_becomes_float(self):
        out = _normalize_eval_record({"score": 4, "rubric": "grounding"})
        assert isinstance(out["score"], float)
        assert out["score"] == 4.0

    def test_float_score_passes_through(self):
        out = _normalize_eval_record({"score": 3.7, "rubric": "grounding"})
        assert out["score"] == pytest.approx(3.7)

    def test_none_score_preserved(self):
        out = _normalize_eval_record({"score": None, "rubric": "grounding"})
        assert out["score"] is None

    def test_missing_score_field_left_absent(self):
        # Pipeline-error rows may legitimately lack the field
        out = _normalize_eval_record({"rubric": None, "status": "pipeline_error"})
        assert "score" not in out or out.get("score") is None

    def test_malformed_score_becomes_none(self):
        out = _normalize_eval_record({"score": "not-a-number", "rubric": "grounding"})
        assert out["score"] is None

    def test_defaults_for_missing_fields(self):
        out = _normalize_eval_record({"score": 5, "rubric": "grounding"})
        assert out["schema_version"] == 1  # legacy default
        assert out["score_max"] == 5.0
        assert out["prompt_version"] == ""
        assert out["failed_rules"] == []
        assert out["reasons"] == []

    def test_existing_fields_retained(self):
        out = _normalize_eval_record({
            "score": 5,
            "schema_version": 2,
            "score_max": 5.0,
            "prompt_version": "2026-05-09.1",
            "failed_rules": ["invented_metric"],
            "reasons": ["test"],
        })
        assert out["schema_version"] == 2
        assert out["prompt_version"] == "2026-05-09.1"
        assert out["failed_rules"] == ["invented_metric"]

    def test_does_not_mutate_input(self):
        original = {"score": 4, "rubric": "grounding"}
        _normalize_eval_record(original)
        assert original == {"score": 4, "rubric": "grounding"}


class TestPassThreshold:
    """4.0 should pass; 3.9 should fail. Verifies the float boundary."""

    def test_pass_threshold_is_float(self):
        from evals.runner import PASS_THRESHOLD
        assert PASS_THRESHOLD == 4.0
        assert isinstance(PASS_THRESHOLD, float)

    def test_classification_at_boundary(self):
        from evals.runner import PASS_THRESHOLD
        assert 4.0 >= PASS_THRESHOLD
        assert 3.9 < PASS_THRESHOLD
        assert 4.1 >= PASS_THRESHOLD


class TestGradeCoercion:
    """Haiku judges occasionally emit integer scores. The runner must coerce
    to float at the boundary so all downstream code can assume float."""

    def _make_judge_response(self, json_text: str) -> MagicMock:
        msg = MagicMock()
        msg.content = [MagicMock(text=json_text)]
        return msg

    def test_integer_score_coerced_to_float(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": 4, "reasons": ["ok"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert isinstance(grade["score"], float)
        assert grade["score"] == 4.0

    def test_fractional_score_preserved(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": 4.3, "reasons": ["nearly"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert isinstance(grade["score"], float)
        assert grade["score"] == pytest.approx(4.3)

    def test_string_score_falls_back_to_zero(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": "high", "reasons": ["bad judge output"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        # Coercion failure → score becomes 0.0 (a clear "did not pass")
        assert grade["score"] == 0.0

    def test_unparseable_json_returns_zero(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            "not json at all"
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert grade["score"] == 0
        assert "raw" in grade


class TestSchemaConstants:
    """Schema version + score max constants must be exported from the runner."""

    def test_schema_version_present(self):
        from evals.runner import SCHEMA_VERSION
        assert SCHEMA_VERSION == 2

    def test_score_max_present(self):
        from evals.runner import SCORE_MAX
        assert SCORE_MAX == 5.0


class TestLegacyResultCompatibility:
    """A real result line from before the migration must still load via the
    dashboard normalize helper without raising."""

    def test_v1_record_loads(self):
        v1_record = json.loads(
            '{"timestamp": "2026-05-06T23:50:05Z", "source": "eval", '
            '"fixture": "data-scientist-junior", "rubric": "grounding", '
            '"score": 2, "reasons": ["a", "b"], "failed_rules": ["invented_metric"], '
            '"status": "ok"}'
        )
        out = _normalize_eval_record(v1_record)
        assert out["score"] == 2.0
        assert out["schema_version"] == 1
        assert out["failed_rules"] == ["invented_metric"]

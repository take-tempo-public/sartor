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
            "run_id": "abc123def456",
            "failed_rules": ["invented_metric"],
            "reasons": ["test"],
        })
        assert out["schema_version"] == 2
        assert out["prompt_version"] == "2026-05-09.1"
        assert out["run_id"] == "abc123def456"
        assert out["failed_rules"] == ["invented_metric"]

    def test_default_run_id_is_empty_string(self):
        # Legacy records without run_id should normalize to "" so the dashboard
        # template's `or "—"` fallback works without raising.
        out = _normalize_eval_record({"score": 5, "rubric": "grounding"})
        assert out["run_id"] == ""

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

    def test_unparseable_json_marks_status_judge_error(self, tmp_path: Path):
        """Malformed judge responses must be flagged as judge_error so
        _detect_regression and the summary roll-up skip them. Without
        this, the caller's grade.setdefault('status', 'ok') labels the
        record as a successful 0-score grading and fires a
        false-positive WARN against the baseline.
        """
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            "not json at all"
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert grade["status"] == "judge_error"
        assert "judge response was not valid JSON" in grade["reasons"]


class TestSchemaConstants:
    """Schema version + score max constants must be exported from the runner."""

    def test_schema_version_present(self):
        from evals.runner import SCHEMA_VERSION
        assert SCHEMA_VERSION == 3

    def test_score_max_present(self):
        from evals.runner import SCORE_MAX
        assert SCORE_MAX == 5.0


class TestRegressionDetection:
    """The runner compares each new (fixture, rubric) score to the most-recent
    prior score and warns when the drop exceeds REGRESSION_DELTA."""

    def test_no_baseline_returns_none(self):
        from evals.runner import _detect_regression
        out = _detect_regression("a", "grounding", 4.5, baseline={})
        assert out is None

    def test_score_drop_flagged_as_regression(self, monkeypatch):
        # Force a tight delta so any drop > 0.1 trips
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.1)
        from evals.runner import _detect_regression
        baseline = {("a", "grounding"): {"score": 4.8, "prompt_version": "v1"}}
        out = _detect_regression("a", "grounding", 3.5, baseline)
        assert out is not None
        assert out["is_regression"] is True
        assert out["is_improvement"] is False
        assert out["delta"] == -1.3
        assert out["prev_prompt_version"] == "v1"

    def test_score_improvement_flagged(self, monkeypatch):
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.1)
        from evals.runner import _detect_regression
        baseline = {("a", "tone"): {"score": 3.8}}
        out = _detect_regression("a", "tone", 4.7, baseline)
        assert out is not None
        assert out["is_improvement"] is True
        assert out["is_regression"] is False
        assert out["delta"] == 0.9

    def test_within_delta_is_neither(self, monkeypatch):
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.5)
        from evals.runner import _detect_regression
        baseline = {("a", "tone"): {"score": 4.5}}
        out = _detect_regression("a", "tone", 4.2, baseline)
        assert out is not None
        assert out["is_regression"] is False
        assert out["is_improvement"] is False
        # delta = -0.3, within ±0.5

    def test_int_baseline_score_handled(self, monkeypatch):
        # Legacy int score in baseline should still compare
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.5)
        from evals.runner import _detect_regression
        baseline = {("a", "grounding"): {"score": 5}}
        out = _detect_regression("a", "grounding", 3.0, baseline)
        assert out is not None
        assert out["is_regression"] is True
        assert out["prev_score"] == 5.0

    def test_load_baseline_excludes_current_file(self, tmp_path, monkeypatch):
        # Two prior result files + a "current" one. Current file's records
        # should be excluded so the new run can be compared against history only.
        from evals.runner import _load_baseline_scores
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        monkeypatch.setattr("evals.runner.RESULTS_DIR", results_dir)

        (results_dir / "20260501_000000Z.jsonl").write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 4.5, "timestamp": "2026-05-01T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (results_dir / "20260507_000000Z.jsonl").write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 4.8, "timestamp": "2026-05-07T00:00:00Z"}\n',
            encoding="utf-8",
        )
        current = results_dir / "20260509_000000Z.jsonl"
        current.write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 1.0, "timestamp": "2026-05-09T00:00:00Z"}\n',
            encoding="utf-8",
        )
        baseline = _load_baseline_scores(current)
        # Should pick the more-recent prior run (4.8), not the current one (1.0)
        assert baseline[("a", "grounding")]["score"] == 4.8


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

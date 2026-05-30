"""Unit tests for dashboard.routes — aggregation helpers and route smoke.

These cover the four new aggregations that drive the eval charts and
heatmap, plus a smoke test that confirms the index route renders cleanly
when no eval results exist (graceful degradation).
"""

from __future__ import annotations

import pytest

from dashboard.routes import (
    _failure_mode_frequency,
    _pareto_data,
    _per_rubric_pass_rate,
    _percentile,
    _rubric_fixture_heatmap,
    _score_over_time,
    _summarize_calls,
)


class TestPerRubricPassRate:
    def test_empty(self):
        assert _per_rubric_pass_rate([]) == []

    def test_mixed_int_float_scores(self):
        # Phase-0 normalization should already have coerced ints to floats,
        # but the helper must work for both shapes regardless.
        records = [
            {"rubric": "grounding", "score": 4},
            {"rubric": "grounding", "score": 4.5},
            {"rubric": "grounding", "score": 3.9},
            {"rubric": "tone", "score": 5.0},
        ]
        out = _per_rubric_pass_rate(records)
        rubric_map = {r["rubric"]: r for r in out}
        assert rubric_map["grounding"]["pass_count"] == 2
        assert rubric_map["grounding"]["fail_count"] == 1
        assert rubric_map["grounding"]["pass_rate"] == round(2 / 3, 3)
        assert rubric_map["tone"]["pass_count"] == 1

    def test_pipeline_error_rows_count_as_fail(self):
        records = [
            {"rubric": "grounding", "score": None, "status": "judge_error"},
            {"rubric": "grounding", "score": 5.0},
        ]
        out = _per_rubric_pass_rate(records)
        assert out[0]["pass_count"] == 1
        assert out[0]["fail_count"] == 1

    def test_skips_records_without_rubric(self):
        records = [{"rubric": None, "score": None}, {"rubric": "tone", "score": 4.0}]
        out = _per_rubric_pass_rate(records)
        assert len(out) == 1
        assert out[0]["rubric"] == "tone"


class TestScoreOverTime:
    def test_groups_by_prompt_version(self):
        records = [
            {"rubric": "grounding", "score": 3.0, "prompt_version": "v1", "timestamp": "2026-05-01T00:00:00Z"},
            {"rubric": "grounding", "score": 4.5, "prompt_version": "v2", "timestamp": "2026-05-09T00:00:00Z"},
            {"rubric": "tone", "score": 5.0, "prompt_version": "v2", "timestamp": "2026-05-09T00:00:00Z"},
        ]
        out = _score_over_time(records)
        labels = sorted({d["label"] for d in out["datasets"]})
        assert labels == ["grounding", "tone"]
        # Each dataset's point carries the prompt_version label
        for ds in out["datasets"]:
            for pt in ds["data"]:
                assert "v" in pt

    def test_filters_records_without_prompt_version(self):
        records = [
            {"rubric": "grounding", "score": 3.0, "prompt_version": "", "timestamp": "2026-05-01T00:00:00Z"},
            {"rubric": "grounding", "score": 4.0, "prompt_version": "v2", "timestamp": "2026-05-09T00:00:00Z"},
        ]
        out = _score_over_time(records)
        # 1 of 2 records filtered
        assert out["filtered_records"] == 1

    def test_handles_empty_input(self):
        out = _score_over_time([])
        assert out["datasets"] == []
        assert out["labels"] == []


class TestRubricFixtureHeatmap:
    def test_takes_most_recent_per_pair(self):
        records = [
            {"rubric": "grounding", "fixture": "A", "score": 3.0, "timestamp": "2026-05-01T00:00:00Z"},
            {"rubric": "grounding", "fixture": "A", "score": 4.5, "timestamp": "2026-05-09T00:00:00Z"},
        ]
        out = _rubric_fixture_heatmap(records)
        cell = out["rows"][0]["cells"][0]
        assert cell["score"] == 4.5

    def test_missing_pairs_are_empty_cells(self):
        # Two rubrics, but only one has data for fixture B
        records = [
            {"rubric": "grounding", "fixture": "A", "score": 4.0, "timestamp": "2026-05-09T00:00:00Z"},
            {"rubric": "tone", "fixture": "B", "score": 5.0, "timestamp": "2026-05-09T00:00:00Z"},
        ]
        out = _rubric_fixture_heatmap(records)
        # 2 rubrics × 2 fixtures = 4 cells; 2 should be empty (score=None)
        all_cells = [c for row in out["rows"] for c in row["cells"]]
        assert len([c for c in all_cells if c["score"] is None]) == 2

    def test_color_scales_with_score(self):
        records = [
            {"rubric": "grounding", "fixture": "A", "score": 0.0, "timestamp": "2026-05-09T00:00:00Z"},
            {"rubric": "grounding", "fixture": "B", "score": 5.0, "timestamp": "2026-05-09T00:00:00Z"},
        ]
        out = _rubric_fixture_heatmap(records)
        cells = out["rows"][0]["cells"]
        # Score 0 → hue 0 (red); score 5 → hue 120 (green)
        assert "hsl(0 " in cells[0]["color"]
        assert "hsl(120 " in cells[1]["color"]


class TestFailureModeFrequency:
    def test_per_record_dedup(self):
        # One record with duplicates of "a" should still count as 1
        records = [{"failed_rules": ["a", "a", "b"]}, {"failed_rules": ["a"]}]
        out = _failure_mode_frequency(records)
        slug_map = {f["slug"]: f["count"] for f in out}
        assert slug_map["a"] == 2  # 2 records mention "a"
        assert slug_map["b"] == 1

    def test_empty_records(self):
        assert _failure_mode_frequency([]) == []

    def test_skips_empty_or_non_string_slugs(self):
        records = [{"failed_rules": ["", None, 42, "valid_slug"]}]
        out = _failure_mode_frequency(records)
        assert len(out) == 1
        assert out[0]["slug"] == "valid_slug"

    def test_sorts_by_count_desc(self):
        records = [
            {"failed_rules": ["a"]},
            {"failed_rules": ["b"]},
            {"failed_rules": ["b"]},
            {"failed_rules": ["b"]},
            {"failed_rules": ["a", "c"]},
        ]
        out = _failure_mode_frequency(records)
        assert out[0]["slug"] == "b"
        assert out[0]["count"] == 3

    def test_caps_at_twenty(self):
        records = [{"failed_rules": [f"slug_{i}"]} for i in range(40)]
        out = _failure_mode_frequency(records)
        assert len(out) == 20


class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert _percentile([], 50) == 0.0
        assert _percentile([], 95) == 0.0

    def test_single_value(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 95) == 42.0

    def test_p50_is_median_for_odd_count(self):
        # Sorted [1,2,3,4,5] → p50 == 3
        assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0

    def test_p95_near_top(self):
        # Sorted 0..100 → p95 should land near 95
        vals = [float(i) for i in range(101)]
        assert _percentile(vals, 95) == 95.0

    def test_interpolation(self):
        # Sorted [10, 20] → p50 should interpolate to 15
        assert _percentile([10.0, 20.0], 50) == 15.0


class TestSummarizeCalls:
    def test_includes_cost_fields(self):
        records = [
            {
                "model": "claude-sonnet-4-6",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "latency_ms": 1000,
                "status": "ok",
            },
        ]
        out = _summarize_calls(records)
        assert "total_cost_usd" in out
        assert "mean_cost_per_call" in out
        assert out["total_cost_usd"] > 0

    def test_empty_returns_zero_cost(self):
        out = _summarize_calls([])
        assert out["total_cost_usd"] == 0.0
        assert out["mean_cost_per_call"] == 0.0
        assert out["p50_latency_ms"] == 0
        assert out["p95_latency_ms"] == 0
        assert out["p50_cost_usd"] == 0.0
        assert out["p95_cost_usd"] == 0.0

    def test_percentiles_reflect_distribution(self):
        # Six calls with widely varying latencies; mean is dragged by the
        # outlier but p50 stays near the bulk.
        records = [
            {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 100,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
             "latency_ms": ms, "status": "ok"}
            for ms in [1000, 1100, 1200, 1300, 1400, 90000]
        ]
        out = _summarize_calls(records)
        # Mean is dragged way up by the outlier; p50 stays near the bulk
        assert out["mean_latency_ms"] > 15000  # dragged by 90000
        assert 1000 <= out["p50_latency_ms"] <= 1500
        assert out["p95_latency_ms"] >= out["p50_latency_ms"]


def _make_composite(
    fixture: str = "pm-senior",
    prompt_version: str = "v1",
    timestamp: str = "2026-05-01T00:00:00Z",
    score: float = 4.2,
    run_id: str = "aabbcc112233",
    phase_latencies_ms: dict | None = None,
) -> dict:
    """Build a minimal eval_composite record for testing."""
    return {
        "rubric": "eval_composite",
        "fixture": fixture,
        "prompt_version": prompt_version,
        "timestamp": timestamp,
        "score": score,
        "run_id": run_id,
        "phase_latencies_ms": phase_latencies_ms or {"analyze": 90000, "generate": 50000},
        "scores_used": {"grounding": score},
    }


def _make_cost_record(run_id: str = "aabbcc112233", cost_usd: float = 0.13) -> dict:
    """Build a minimal non-composite record carrying cost_usd."""
    return {
        "rubric": "grounding",
        "fixture": "pm-senior",
        "run_id": run_id,
        "cost_usd": cost_usd,
        "timestamp": "2026-05-01T00:00:00Z",
    }


class TestParetoData:
    def test_empty_records(self):
        out = _pareto_data([])
        assert out["has_data"] is False
        assert out["scatter_datasets"] == []
        assert out["summary"] is None
        assert out["latency_trend"]["labels"] == []
        assert out["cost_trend"]["labels"] == []

    def test_composite_with_none_score_skipped(self):
        record = _make_composite(score=None)
        record["score"] = None
        out = _pareto_data([record])
        assert out["has_data"] is False

    def test_single_version_no_summary(self):
        records = [
            _make_composite(fixture="pm-senior", run_id="run1"),
            _make_composite(fixture="sre-mid", run_id="run2", timestamp="2026-05-02T00:00:00Z"),
            _make_cost_record(run_id="run1"),
            _make_cost_record(run_id="run2"),
        ]
        out = _pareto_data(records)
        assert out["has_data"] is True
        assert out["summary"] is None  # only one prompt_version
        assert len(out["scatter_datasets"]) == 1
        assert len(out["scatter_datasets"][0]["data"]) == 2

    def test_cost_join_by_run_id(self):
        composite = _make_composite(run_id="known_run")
        cost_record = _make_cost_record(run_id="known_run", cost_usd=0.14)
        out = _pareto_data([composite, cost_record])
        assert out["has_data"] is True
        pt = out["scatter_datasets"][0]["data"][0]
        assert pt["cost_usd"] == 0.14
        assert pt["r"] == 20.0  # only point → max_cost == 0.14 → radius = 5 + 15*1 = 20

    def test_missing_cost_defaults_radius(self):
        composite = _make_composite(run_id="no_cost_run")
        out = _pareto_data([composite])  # no cost record
        pt = out["scatter_datasets"][0]["data"][0]
        assert pt["cost_usd"] is None
        assert pt["r"] == 8.0

    def test_two_versions_delta_summary(self):
        records = [
            _make_composite(prompt_version="v1", timestamp="2026-05-01T00:00:00Z",
                            score=4.0, run_id="r1",
                            phase_latencies_ms={"analyze": 90000, "generate": 50000}),
            _make_cost_record(run_id="r1", cost_usd=0.13),
            _make_composite(prompt_version="v2", timestamp="2026-05-10T00:00:00Z",
                            score=4.4, run_id="r2",
                            phase_latencies_ms={"analyze": 95000, "generate": 55000}),
            _make_cost_record(run_id="r2", cost_usd=0.14),
        ]
        out = _pareto_data(records)
        assert out["summary"] is not None
        s = out["summary"]
        assert s["v_prev"] == "v1"
        assert s["v_new"] == "v2"
        assert s["delta_composite"] == pytest.approx(0.4, abs=0.001)
        assert s["delta_latency_ms"] > 0  # v2 latency is higher

    def test_pareto_improving_classification(self):
        records = [
            _make_composite(prompt_version="v1", timestamp="2026-05-01T00:00:00Z",
                            score=4.0, run_id="r1",
                            phase_latencies_ms={"analyze": 100000, "generate": 60000}),
            _make_cost_record(run_id="r1", cost_usd=0.15),
            _make_composite(prompt_version="v2", timestamp="2026-05-10T00:00:00Z",
                            score=4.5, run_id="r2",
                            phase_latencies_ms={"analyze": 80000, "generate": 40000}),
            _make_cost_record(run_id="r2", cost_usd=0.12),
        ]
        out = _pareto_data(records)
        assert out["summary"]["classification"] == "Pareto-improving"

    def test_dominated_classification(self):
        records = [
            _make_composite(prompt_version="v1", timestamp="2026-05-01T00:00:00Z",
                            score=4.5, run_id="r1",
                            phase_latencies_ms={"analyze": 80000, "generate": 40000}),
            _make_cost_record(run_id="r1", cost_usd=0.12),
            _make_composite(prompt_version="v2", timestamp="2026-05-10T00:00:00Z",
                            score=4.0, run_id="r2",
                            phase_latencies_ms={"analyze": 100000, "generate": 60000}),
            _make_cost_record(run_id="r2", cost_usd=0.15),
        ]
        out = _pareto_data(records)
        assert out["summary"]["classification"] == "Dominated"


class TestIndexRoute:
    """Smoke test the route renders cleanly when there's nothing to display."""

    def test_index_renders_with_no_data(self, tmp_path, monkeypatch):
        from flask import Flask

        from dashboard import routes as dashboard_routes

        # Point both data sources at empty paths
        monkeypatch.setattr(dashboard_routes, "LLM_LOG", tmp_path / "no.jsonl")
        monkeypatch.setattr(dashboard_routes, "EVAL_RESULTS_DIR", tmp_path / "results")

        app = Flask(__name__)
        app.register_blueprint(dashboard_routes.dashboard_bp, url_prefix="/dashboard")

        with app.test_client() as client:
            resp = client.get("/dashboard/", headers={"Host": "127.0.0.1"})
            assert resp.status_code == 200
            body = resp.get_data(as_text=True)
            # Empty-state messages should be visible
            assert "No call records" in body or "No calls match" in body
            assert "No eval results yet" in body
            # Chart.js script tag should still be in the head
            assert "chart.umd" in body

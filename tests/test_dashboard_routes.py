"""Unit tests for dashboard.routes — aggregation helpers and route smoke.

These cover the four new aggregations that drive the eval charts and
heatmap, plus a smoke test that confirms the index route renders cleanly
when no eval results exist (graceful degradation).
"""

from __future__ import annotations

import pytest

from dashboard.routes import (
    _baseline_health,
    _cost_by_call_kind,
    _dedup_by_run,
    _failure_mode_frequency,
    _groundedness_trend,
    _latest_groundedness_detail,
    _pareto_data,
    _per_rubric_pass_rate,
    _percentile,
    _reliability,
    _rubric_fixture_heatmap,
    _run_trace,
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


def _make_grounded(
    run_id: str,
    score: float,
    rate: float = 0.0,
    timestamp: str = "2026-06-06T00:00:00Z",
    prompt_version: str = "v1",
    rubric: str = "grounding",
    fixture: str = "pm-senior",
    flagged_count: int = 0,
    flagged_samples: list | None = None,
    per_bullet: list | None = None,
) -> dict:
    """A per-rubric eval record carrying the 2026-06-06 groundedness block."""
    return {
        "rubric": rubric,
        "fixture": fixture,
        "run_id": run_id,
        "prompt_version": prompt_version,
        "timestamp": timestamp,
        "score": 4.5,
        "deterministic_metrics": {
            "groundedness": {
                "layers": ["L0"],
                "fabricated_specifics_rate": rate,
                "flagged_count": flagged_count,
                "score": score,
            },
            "fabricated_specifics": {
                "total_bullets": 10,
                "total_specifics": 20,
                "flagged": flagged_count,
                "fabricated_specifics_rate": rate,
                "per_bullet": per_bullet or [],
                "flagged_samples": flagged_samples or [],
            },
        },
    }


class TestDedupByRun:
    def test_keeps_first_per_run_id(self):
        records = [
            {"run_id": "r1", "n": 1},
            {"run_id": "r1", "n": 2},
            {"run_id": "r2", "n": 3},
        ]
        out = _dedup_by_run(records)
        assert [r["n"] for r in out] == [1, 3]

    def test_records_without_run_id_kept_individually(self):
        records = [{"run_id": ""}, {"run_id": ""}, {"run_id": "r1"}]
        assert len(_dedup_by_run(records)) == 3


class TestGroundednessTrend:
    def test_empty(self):
        out = _groundedness_trend([])
        assert out["has_data"] is False
        assert out["datasets"] == []
        assert out["points"] == 0

    def test_dedups_by_run_id(self):
        # Same run, two rubrics carrying the identical groundedness block → 1 point.
        records = [
            _make_grounded("r1", score=4.5, rubric="grounding"),
            _make_grounded("r1", score=4.5, rubric="tone"),
        ]
        out = _groundedness_trend(records)
        assert out["points"] == 1
        assert out["datasets"][0]["data"][0]["y"] == 4.5

    def test_sorted_by_timestamp_and_carries_version_and_rate(self):
        records = [
            _make_grounded("r2", score=4.0, rate=0.2, timestamp="2026-06-07T00:00:00Z",
                           prompt_version="v2"),
            _make_grounded("r1", score=5.0, rate=0.0, timestamp="2026-06-06T00:00:00Z",
                           prompt_version="v1"),
        ]
        out = _groundedness_trend(records)
        data = out["datasets"][0]["data"]
        assert [d["x"] for d in data] == ["2026-06-06T00:00:00Z", "2026-06-07T00:00:00Z"]
        assert data[0]["v"] == "v1" and data[1]["v"] == "v2"
        assert data[1]["rate"] == 0.2

    def test_skips_records_without_groundedness(self):
        records = [
            {"rubric": "grounding", "run_id": "r1", "timestamp": "2026-06-06T00:00:00Z",
             "deterministic_metrics": {"verb_diversity": 1.0}},  # pre-2026-06-06 shape
        ]
        out = _groundedness_trend(records)
        assert out["has_data"] is False


class TestLatestGroundednessDetail:
    def test_empty(self):
        assert _latest_groundedness_detail([])["has_data"] is False

    def test_picks_most_recent_and_surfaces_evidence(self):
        records = [
            _make_grounded("r1", score=5.0, timestamp="2026-06-06T00:00:00Z"),
            _make_grounded("r2", score=3.5, rate=0.3, timestamp="2026-06-08T00:00:00Z",
                           prompt_version="v2", flagged_count=2,
                           flagged_samples=["$5M", "Kubernetes"],
                           per_bullet=[{"bullet": "Led $5M migration", "n_specifics": 2,
                                        "flagged": ["$5M"]}]),
        ]
        out = _latest_groundedness_detail(records)
        assert out["has_data"] is True
        assert out["prompt_version"] == "v2"
        assert out["score"] == 3.5
        assert out["flagged_count"] == 2
        assert "$5M" in out["flagged_samples"]
        assert out["per_bullet"][0]["flagged"] == ["$5M"]


class TestCostByCallKind:
    def _call(self, kind: str, out_tokens: int) -> dict:
        return {
            "call": kind,
            "model": "claude-sonnet-4-6",
            "input_tokens": 1000,
            "output_tokens": out_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

    def test_empty(self):
        assert _cost_by_call_kind([]) == []

    def test_groups_and_sorts_by_total_cost_desc(self):
        records = [
            self._call("generate", 2000),
            self._call("generate", 2000),
            self._call("clarify", 100),
        ]
        out = _cost_by_call_kind(records)
        assert out[0]["call_kind"] == "generate"
        assert out[0]["count"] == 2
        assert out[0]["total_cost_usd"] >= out[1]["total_cost_usd"]

    def test_missing_call_kind_labeled_unknown(self):
        out = _cost_by_call_kind([{"model": "claude-sonnet-4-6", "output_tokens": 10,
                                   "input_tokens": 10}])
        assert out[0]["call_kind"] == "unknown"


class TestReliability:
    def test_empty(self):
        out = _reliability([])
        assert out["total"] == 0
        assert out["error_rate"] == 0.0
        assert out["truncation_rate"] == 0.0
        assert out["by_call_kind"] == []

    def test_error_and_truncation_rates(self):
        records = [
            {"call": "generate", "status": "ok", "stop_reason": "end_turn"},
            {"call": "generate", "status": "error", "stop_reason": None},
            {"call": "generate", "status": "ok", "stop_reason": "max_tokens"},
            {"call": "analyze", "status": "ok", "stop_reason": "end_turn"},
        ]
        out = _reliability(records)
        assert out["total"] == 4
        assert out["error_count"] == 1
        assert out["error_rate"] == 0.25
        assert out["truncation_count"] == 1
        assert out["truncation_rate"] == 0.25
        gen = next(k for k in out["by_call_kind"] if k["call_kind"] == "generate")
        assert gen["total"] == 3
        assert gen["error_count"] == 1
        assert gen["truncation_count"] == 1


class TestRunTrace:
    def test_no_run_id(self):
        out = _run_trace([{"call": "generate", "latency_ms": 100}])
        assert out["has_data"] is False
        assert out["runs"] == []

    def test_groups_orders_and_computes_pct(self):
        records = [
            {"run_id": "r1", "call": "generate", "latency_ms": 30000,
             "timestamp": "2026-06-06T00:00:02Z", "model": "m", "status": "ok"},
            {"run_id": "r1", "call": "analyze", "latency_ms": 90000,
             "timestamp": "2026-06-06T00:00:01Z", "model": "m", "status": "ok"},
        ]
        out = _run_trace(records)
        assert out["has_data"] is True
        spans = out["latest"]["spans"]
        # Ordered by timestamp ascending → analyze first
        assert [s["call_kind"] for s in spans] == ["analyze", "generate"]
        assert out["latest"]["total_latency_ms"] == 120000
        assert spans[0]["pct"] == 75.0
        assert spans[1]["pct"] == 25.0
        # bar_pct scales each bar to the LONGEST span (max → 100%), not the total,
        # so a short span stays visible: analyze (90000) is the max → 100.0;
        # generate (30000) → 30000/90000 = 33.3.
        assert spans[0]["bar_pct"] == 100.0
        assert spans[1]["bar_pct"] == 33.3

    def test_latest_run_is_most_recent(self):
        records = [
            {"run_id": "old", "call": "generate", "latency_ms": 1,
             "timestamp": "2026-06-01T00:00:00Z", "model": "m", "status": "ok"},
            {"run_id": "new", "call": "generate", "latency_ms": 1,
             "timestamp": "2026-06-09T00:00:00Z", "model": "m", "status": "ok"},
        ]
        out = _run_trace(records)
        assert out["latest"]["run_id"] == "new"
        assert len(out["runs"]) == 2


class TestBaselineHealth:
    _BASELINE = {
        "baseline_id": "v1.0.2_test",
        "prompt_version": "2026-05-24.4",
        "fixtures": {
            "pm-senior": {
                "grounding": {"mean": 4.6},
                "tone": {"mean": 4.2},
                "ats_format": {"mean": 4.5},
            },
        },
    }

    def test_no_baseline(self):
        out = _baseline_health([{"fixture": "pm-senior", "rubric": "grounding",
                                 "score": 4.0, "timestamp": "t"}], {})
        assert out["has_baseline"] is False

    def test_verdict_bands(self):
        records = [
            # delta -0.6 → regressed
            {"fixture": "pm-senior", "rubric": "grounding", "score": 4.0,
             "timestamp": "2026-06-06T00:00:00Z"},
            # delta -0.35 → watch
            {"fixture": "pm-senior", "rubric": "tone", "score": 3.85,
             "timestamp": "2026-06-06T00:00:00Z"},
            # delta -0.1 → ok
            {"fixture": "pm-senior", "rubric": "ats_format", "score": 4.4,
             "timestamp": "2026-06-06T00:00:00Z"},
        ]
        out = _baseline_health(records, self._BASELINE)
        by_rubric = {r["rubric"]: r["status"] for r in out["rows"]}
        assert by_rubric["grounding"] == "regressed"
        assert by_rubric["tone"] == "watch"
        assert by_rubric["ats_format"] == "ok"
        # overall is the worst verdict present
        assert out["overall"] == "regressed"
        assert out["counts"] == {"ok": 1, "watch": 1, "regressed": 1}

    def test_overall_ok_when_all_pass(self):
        records = [
            {"fixture": "pm-senior", "rubric": "grounding", "score": 4.7,
             "timestamp": "2026-06-06T00:00:00Z"},
        ]
        out = _baseline_health(records, self._BASELINE)
        assert out["overall"] == "ok"

    def test_skips_rubric_absent_from_baseline(self):
        records = [
            {"fixture": "pm-senior", "rubric": "unknown_rubric", "score": 1.0,
             "timestamp": "2026-06-06T00:00:00Z"},
        ]
        out = _baseline_health(records, self._BASELINE)
        assert out["rows"] == []
        assert out["overall"] == "unknown"

    def test_takes_most_recent_score_per_pair(self):
        records = [
            {"fixture": "pm-senior", "rubric": "grounding", "score": 4.0,
             "timestamp": "2026-06-06T00:00:00Z"},  # regressed, older
            {"fixture": "pm-senior", "rubric": "grounding", "score": 4.6,
             "timestamp": "2026-06-08T00:00:00Z"},  # ok, newer → wins
        ]
        out = _baseline_health(records, self._BASELINE)
        assert out["rows"][0]["status"] == "ok"

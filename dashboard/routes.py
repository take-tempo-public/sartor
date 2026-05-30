"""Dashboard routes — read-only Flask blueprint.

Localhost-only by guard. Reads JSONL log files; never writes.

Provides observability for the analyze + generate pipeline:
  - LLM-call telemetry (token usage, cache hits, latency, cost)
  - Eval results (per-rubric scores 0.0-5.0, failure-mode clustering)
  - Aggregations: per-rubric pass rates, score-over-time by prompt_version,
    rubric × fixture heatmap, top failure modes.

The aggregations feed both server-rendered tables (graceful degradation
without JS) and Chart.js-rendered charts in the template. No external
Python deps; Chart.js is loaded from a CDN client-side.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, render_template, request

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LLM_LOG = PROJECT_ROOT / "logs" / "llm_calls.jsonl"
EVAL_RESULTS_DIR = PROJECT_ROOT / "evals" / "results"


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file. Returns [] if the file is missing. Skips malformed lines."""
    if not path.exists():
        return []
    records: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _normalize_eval_record(r: dict) -> dict:
    """Coerce eval records to a single shape regardless of schema version.

    Older records (schema_version=1) had integer scores and lacked
    score_max/schema_version/prompt_version. We coerce score to float when
    present and fill defaults so downstream charts/aggregations don't branch.
    """
    r = dict(r)  # copy to avoid mutating the caller's record
    if "score" in r and r["score"] is not None:
        try:
            r["score"] = float(r["score"])
        except (TypeError, ValueError):
            r["score"] = None
    r.setdefault("schema_version", 1)
    r.setdefault("score_max", 5.0)
    r.setdefault("prompt_version", "")
    r.setdefault("run_id", "")
    r.setdefault("failed_rules", [])
    r.setdefault("reasons", [])
    return r


def _read_eval_results() -> list[dict]:
    """Aggregate every line of every evals/results/*.jsonl into one list."""
    if not EVAL_RESULTS_DIR.exists():
        return []
    out: list[dict] = []
    for path in sorted(EVAL_RESULTS_DIR.glob("*.jsonl")):
        out.extend(_normalize_eval_record(r) for r in _read_jsonl(path))
    return out


def _parse_date(s: str) -> datetime | None:
    """Parse YYYY-MM-DD or full ISO. Return None on failure."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _filter_calls(records: list[dict], since: str, user: str, model: str) -> list[dict]:
    floor = _parse_date(since)
    out = []
    for r in records:
        if floor:
            ts = _parse_date(r.get("timestamp", "").rstrip("Z"))
            if ts and ts < floor:
                continue
        if user and r.get("username", "") != user:
            continue
        if model and r.get("model", "") != model:
            continue
        out.append(r)
    return out


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile over a pre-sorted list.

    Returns 0.0 for an empty list. pct is in [0, 100]. Used for p50/p95
    summaries; doesn't pretend to be statistically rigorous, just useful.
    """
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    k = (len(sorted_values) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return float(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac)


def _summarize_calls(records: list[dict]) -> dict:
    """Compute aggregate stats over a filtered call list.

    Includes p50/p95 latency and cost so the dashboard can surface tail
    behavior — a single 90s analyze() call hides inside a healthy mean.
    """
    n = len(records)
    if n == 0:
        return {
            "count": 0,
            "total_cost_usd": 0.0,
            "mean_cost_per_call": 0.0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p50_cost_usd": 0.0,
            "p95_cost_usd": 0.0,
        }
    total_in = sum(r.get("input_tokens", 0) for r in records)
    total_out = sum(r.get("output_tokens", 0) for r in records)
    cache_create = sum(r.get("cache_creation_input_tokens", 0) for r in records)
    cache_read = sum(r.get("cache_read_input_tokens", 0) for r in records)
    latencies = sorted(r.get("latency_ms", 0) for r in records if r.get("latency_ms"))
    mean_lat = sum(latencies) / len(latencies) if latencies else 0
    cache_total = cache_create + cache_read
    cache_hit = (cache_read / cache_total) if cache_total else 0.0
    error_count = sum(1 for r in records if r.get("status") == "error")
    # Per-call cost rollup using the same pricing table the eval runner uses.
    # Imported lazily to avoid cycles when hardening pulls in dashboard helpers.
    from hardening import compute_call_cost
    per_call_costs = sorted(compute_call_cost(r) for r in records)
    total_cost = sum(per_call_costs)
    return {
        "count": n,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "cache_creation_input_tokens": cache_create,
        "cache_read_input_tokens": cache_read,
        "cache_hit_ratio": round(cache_hit, 3),
        "mean_latency_ms": int(mean_lat),
        "p50_latency_ms": int(_percentile(latencies, 50)),
        "p95_latency_ms": int(_percentile(latencies, 95)),
        "error_count": error_count,
        "total_cost_usd": round(total_cost, 4),
        "mean_cost_per_call": round(total_cost / n, 6) if n else 0.0,
        "p50_cost_usd": round(_percentile(per_call_costs, 50), 6),
        "p95_cost_usd": round(_percentile(per_call_costs, 95), 6),
    }


def _per_rubric_pass_rate(records: list[dict]) -> list[dict]:
    """Group eval records by rubric and compute pass counts.

    A pass is score >= 4.0. Records with score=None (pipeline_error,
    judge_error) are counted as failures so the dashboard surfaces them
    clearly rather than hiding behind None.
    """
    by_rubric: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        rubric = r.get("rubric")
        if not rubric:
            continue
        by_rubric[rubric].append(r)

    out = []
    for rubric, rs in sorted(by_rubric.items()):
        total = len(rs)
        pass_count = sum(
            1 for r in rs
            if isinstance(r.get("score"), (int, float)) and r["score"] >= 4.0
        )
        out.append({
            "rubric": rubric,
            "total": total,
            "pass_count": pass_count,
            "fail_count": total - pass_count,
            "pass_rate": round(pass_count / total, 3) if total else 0.0,
        })
    return out


def _score_over_time(records: list[dict]) -> dict:
    """Build Chart.js-shaped data for score trend by rubric.

    Records lacking a prompt_version are filtered out (they predate the
    schema-v2 migration; including them would put points on the chart with
    no actionable attribution). Returned shape:
        {labels: [iso_timestamp], datasets: [{label: rubric, data: [score]}]}
    """
    typed_records = [
        r for r in records
        if r.get("prompt_version")
        and isinstance(r.get("score"), (int, float))
        and r.get("rubric")
    ]
    typed_records.sort(key=lambda r: r.get("timestamp", ""))

    rubrics_seen = sorted({r["rubric"] for r in typed_records})
    labels = [r.get("timestamp", "") for r in typed_records]

    # Color palette aligned with template colors
    palette = ["#ffb86b", "#82c8a4", "#94d4ff", "#d77a7a", "#c8a4ff"]
    datasets = []
    for i, rubric in enumerate(rubrics_seen):
        data = [
            {"x": r["timestamp"], "y": r["score"], "v": r.get("prompt_version", "")}
            for r in typed_records if r["rubric"] == rubric
        ]
        datasets.append({
            "label": rubric,
            "data": data,
            "borderColor": palette[i % len(palette)],
            "backgroundColor": palette[i % len(palette)],
            "tension": 0.2,
        })

    return {
        "labels": labels,
        "datasets": datasets,
        "filtered_records": len(records) - len(typed_records),
    }


def _rubric_fixture_heatmap(records: list[dict]) -> dict:
    """Most-recent score per (rubric, fixture) pair, plus axis lists.

    Renders as an HTML/CSS table in the template (color = hsl(120 *
    score/5, 60%, 30%)) — green for pass, red for fail. Cells with no
    record show as empty.
    """
    latest: dict[tuple[str, str], dict] = {}
    for r in records:
        rubric = r.get("rubric")
        fixture = r.get("fixture")
        if not rubric or not fixture:
            continue
        key = (rubric, fixture)
        prev = latest.get(key)
        if prev is None or r.get("timestamp", "") > prev.get("timestamp", ""):
            latest[key] = r

    rubrics = sorted({k[0] for k in latest})
    fixtures = sorted({k[1] for k in latest})

    rows = []
    for rubric in rubrics:
        cells = []
        for fixture in fixtures:
            cell_record = latest.get((rubric, fixture))
            if cell_record is None or not isinstance(cell_record.get("score"), (int, float)):
                cells.append({"score": None, "color": "#1a1a20"})
            else:
                score = cell_record["score"]
                # Hue: red (0) → green (120) based on score / 5
                hue = max(0.0, min(120.0, 120.0 * score / 5.0))
                cells.append({
                    "score": round(score, 1),
                    "color": f"hsl({hue:.0f} 60% 30%)",
                    "prompt_version": cell_record.get("prompt_version", ""),
                    "timestamp": cell_record.get("timestamp", ""),
                })
        rows.append({"rubric": rubric, "cells": cells})

    return {"rubrics": rubrics, "fixtures": fixtures, "rows": rows}


def _failure_mode_frequency(records: list[dict]) -> list[dict]:
    """Count failed_rules occurrences across records.

    Per-record dedup: a record with failed_rules=["a","a","b"] counts as
    {a:1, b:1}. This keeps a single rubric-judgment from dominating the
    histogram. Top-20 sorted by count desc, then alphabetical tie-break.
    """
    counter: Counter[str] = Counter()
    for r in records:
        seen_in_record: set[str] = set()
        for slug in r.get("failed_rules") or []:
            if not isinstance(slug, str) or not slug:
                continue
            seen_in_record.add(slug)
        for slug in seen_in_record:
            counter[slug] += 1

    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return [{"slug": slug, "count": count} for slug, count in top]


def _pareto_data(eval_records: list[dict]) -> dict:
    """Build Pareto frontier data for the quality-vs-latency scatter panel.

    Pulls eval_composite records from the eval record list, joins cost_usd
    from same-run_id non-composite records, and returns Chart.js-shaped data
    for the bubble scatter, latency trend, and cost trend charts, plus a
    plain-dict summary of the most-recent prompt-version change.

    Returns a dict with keys:
        has_data: bool
        scatter_datasets: list[dict]  — one Chart.js dataset per prompt_version
        timeline_dataset: dict        — dashed polyline connecting version centroids
        summary: dict | None          — most-recent-change delta + Pareto verdict
        latency_trend: dict           — Chart.js line-chart data (p50/p90 by version)
        cost_trend: dict              — Chart.js line-chart data (p50 cost by version)
        version_stats: dict           — per-version aggregates
    """
    _EMPTY: dict = {
        "has_data": False,
        "scatter_datasets": [],
        "timeline_dataset": {"label": "baseline trajectory", "data": []},
        "summary": None,
        "latency_trend": {"labels": [], "datasets": []},
        "cost_trend": {"labels": [], "datasets": []},
        "version_stats": {},
    }

    composite_records = [r for r in eval_records if r.get("rubric") == "eval_composite"]

    # Build cost lookup from the first non-composite record per run_id.
    cost_by_run: dict[str, float] = {}
    for r in eval_records:
        run_id = r.get("run_id")
        if run_id and "cost_usd" in r and run_id not in cost_by_run:
            try:
                cost_by_run[run_id] = float(r["cost_usd"])
            except (TypeError, ValueError):
                pass

    points = []
    for r in composite_records:
        phase_lat = r.get("phase_latencies_ms") or {}
        total_lat_ms = sum(v for v in phase_lat.values() if isinstance(v, (int, float)))
        score = r.get("score")
        if score is None or total_lat_ms == 0:
            continue
        run_id = r.get("run_id", "")
        points.append({
            "run_id": run_id,
            "fixture": r.get("fixture", ""),
            "prompt_version": r.get("prompt_version", ""),
            "timestamp": r.get("timestamp", ""),
            "score": float(score),
            "total_latency_ms": int(total_lat_ms),
            "cost_usd": cost_by_run.get(run_id),
            "scores_used": r.get("scores_used", {}),
        })

    if not points:
        return _EMPTY

    by_version: dict[str, list[dict]] = defaultdict(list)
    for pt in points:
        by_version[pt["prompt_version"]].append(pt)

    sorted_versions = sorted(
        by_version.keys(),
        key=lambda v: min(pt["timestamp"] for pt in by_version[v]),
    )

    # Per-version aggregates used for trend lines and summary.
    version_stats: dict[str, dict] = {}
    for version in sorted_versions:
        pts = by_version[version]
        latencies = sorted(pt["total_latency_ms"] for pt in pts)
        costs = sorted(pt["cost_usd"] for pt in pts if pt["cost_usd"] is not None)
        scores = [pt["score"] for pt in pts]
        version_stats[version] = {
            "mean_composite": round(sum(scores) / len(scores), 3),
            "p50_latency_ms": int(_percentile(latencies, 50)),
            "p90_latency_ms": int(_percentile(latencies, 90)),
            "p50_cost_usd": round(_percentile(costs, 50), 4) if costs else None,
        }

    # Normalize cost to bubble radius in [5, 20].
    all_costs = [pt["cost_usd"] for pt in points if pt["cost_usd"] is not None]
    max_cost = max(all_costs) if all_costs else 1.0

    palette = ["#ffb86b", "#82c8a4", "#94d4ff", "#d77a7a", "#c8a4ff"]
    scatter_datasets: list[dict] = []
    for i, version in enumerate(sorted_versions):
        pts = sorted(by_version[version], key=lambda p: p["timestamp"])
        data = []
        for pt in pts:
            lat_s = round(pt["total_latency_ms"] / 1000.0, 1)
            cost = pt["cost_usd"]
            radius = round(5.0 + 15.0 * (cost / max_cost), 1) if cost is not None else 8.0
            data.append({
                "x": lat_s,
                "y": round(pt["score"], 3),
                "r": radius,
                "fixture": pt["fixture"],
                "run_id": pt["run_id"],
                "cost_usd": round(cost, 4) if cost is not None else None,
                "scores_used": pt["scores_used"],
            })
        color = palette[i % len(palette)]
        scatter_datasets.append({
            "label": version,
            "data": data,
            "backgroundColor": color + "99",
            "borderColor": color,
        })

    # Dashed polyline: version centroids in chronological order.
    timeline_data = [
        {
            "x": round(version_stats[v]["p50_latency_ms"] / 1000.0, 1),
            "y": round(version_stats[v]["mean_composite"], 3),
            "version": v,
        }
        for v in sorted_versions
    ]
    timeline_dataset = {
        "label": "baseline trajectory",
        "data": timeline_data,
        "type": "line",
        "borderColor": "#6f7280",
        "borderDash": [6, 4],
        "pointRadius": 0,
        "fill": False,
        "tension": 0,
        "order": 0,
    }

    # Most-recent-change summary (requires ≥2 distinct prompt_versions).
    summary: dict | None = None
    if len(sorted_versions) >= 2:
        v_prev = sorted_versions[-2]
        v_new = sorted_versions[-1]
        prev = version_stats[v_prev]
        new = version_stats[v_new]
        delta_composite = round(new["mean_composite"] - prev["mean_composite"], 3)
        delta_latency_ms = new["p50_latency_ms"] - prev["p50_latency_ms"]
        delta_cost: float | None = None
        if new["p50_cost_usd"] is not None and prev["p50_cost_usd"] is not None:
            delta_cost = round(new["p50_cost_usd"] - prev["p50_cost_usd"], 4)

        quality_up = delta_composite > 0
        latency_down = delta_latency_ms < 0
        cost_down = delta_cost is not None and delta_cost < 0
        quality_down = delta_composite < 0
        latency_up = delta_latency_ms > 0
        cost_up = delta_cost is not None and delta_cost > 0

        if quality_up and (latency_down or cost_down) and not (latency_up and cost_up):
            classification = "Pareto-improving"
        elif quality_down and (latency_up or cost_up):
            classification = "Dominated"
        else:
            classification = "On frontier"

        summary = {
            "v_prev": v_prev,
            "v_new": v_new,
            "delta_composite": delta_composite,
            "delta_latency_ms": delta_latency_ms,
            "delta_cost": delta_cost,
            "classification": classification,
        }

    # Latency and cost trend (line charts by prompt_version).
    labels = sorted_versions
    latency_trend = {
        "labels": labels,
        "datasets": [
            {
                "label": "p50 latency (s)",
                "data": [round(version_stats[v]["p50_latency_ms"] / 1000.0, 1) for v in labels],
                "borderColor": "#ffb86b",
                "backgroundColor": "#ffb86b",
                "tension": 0.2,
            },
            {
                "label": "p90 latency (s)",
                "data": [round(version_stats[v]["p90_latency_ms"] / 1000.0, 1) for v in labels],
                "borderColor": "#d77a7a",
                "backgroundColor": "#d77a7a",
                "tension": 0.2,
                "borderDash": [5, 5],
            },
        ],
    }
    cost_trend = {
        "labels": labels,
        "datasets": [
            {
                "label": "p50 cost (USD)",
                "data": [version_stats[v]["p50_cost_usd"] or 0 for v in labels],
                "borderColor": "#82c8a4",
                "backgroundColor": "#82c8a4",
                "tension": 0.2,
            },
        ],
    }

    return {
        "has_data": True,
        "scatter_datasets": scatter_datasets,
        "timeline_dataset": timeline_dataset,
        "summary": summary,
        "latency_trend": latency_trend,
        "cost_trend": cost_trend,
        "version_stats": version_stats,
    }


@dashboard_bp.before_request
def _localhost_guard():
    """Same posture as the rest of the app: localhost-only by host check."""
    host = (request.host or "").split(":")[0]
    if host not in {"localhost", "127.0.0.1", "::1", "[::1]"}:
        abort(403)


@dashboard_bp.route("/", methods=["GET"])
def index():
    """Render the dashboard with optional filters from query string."""
    since = request.args.get("since", "")
    user = request.args.get("user", "")
    model = request.args.get("model", "")

    calls = _read_jsonl(LLM_LOG)
    filtered_calls = _filter_calls(calls, since, user, model)
    summary = _summarize_calls(filtered_calls)

    eval_results = _read_eval_results()

    # Aggregations for charts/tables. These run over ALL eval results, not
    # the filtered call set — eval grading has its own time/version axis
    # via prompt_version. Filtering by `since` here would lose the trend.
    rubric_pass_rate = _per_rubric_pass_rate(eval_results)
    score_trend = _score_over_time(eval_results)
    heatmap = _rubric_fixture_heatmap(eval_results)
    failure_modes = _failure_mode_frequency(eval_results)
    pareto = _pareto_data(eval_results)

    # Distinct values for filter dropdowns
    users = sorted({r.get("username", "") for r in calls if r.get("username")})
    models = sorted({r.get("model", "") for r in calls if r.get("model")})

    return render_template(
        "dashboard.html",
        calls=list(reversed(filtered_calls))[:200],  # most recent 200
        eval_results=list(reversed(eval_results))[:200],
        summary=summary,
        filters={"since": since, "user": user, "model": model},
        users=users,
        models=models,
        log_path_present=LLM_LOG.exists(),
        eval_dir_present=EVAL_RESULTS_DIR.exists(),
        rubric_pass_rate=rubric_pass_rate,
        score_trend=score_trend,
        heatmap=heatmap,
        failure_modes=failure_modes,
        pareto=pareto,
    )

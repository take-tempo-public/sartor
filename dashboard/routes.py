"""Dashboard routes — read-only Flask blueprint.

Localhost-only by guard. Reads JSONL log files; never writes.

Provides observability for the analyze + generate pipeline:
  - LLM-call telemetry (token usage, cache hits, latency, cost)
  - Eval results (per-rubric scores 0.0-5.0, failure-mode clustering)
  - Aggregations: per-rubric pass rates, score-over-time by prompt_version,
    rubric × fixture heatmap, top failure modes.

The aggregations feed both server-rendered tables (graceful degradation
without JS) and Chart.js-rendered charts in the template. No external
Python deps; Chart.js is vendored locally (static/vendor/chart.umd.min.js),
not fetched from a CDN.
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, render_template, request

from web_infra import _is_localhost_request

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
    # Records predating the 2026-06-06 grounding metric have no
    # deterministic_metrics.groundedness; default to {} so the groundedness
    # helpers never KeyError and instead fall through to their empty-state.
    r.setdefault("deterministic_metrics", {})
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
            1 for r in rs if isinstance(r.get("score"), (int, float)) and r["score"] >= 4.0
        )
        out.append(
            {
                "rubric": rubric,
                "total": total,
                "pass_count": pass_count,
                "fail_count": total - pass_count,
                "pass_rate": round(pass_count / total, 3) if total else 0.0,
            }
        )
    return out


def _score_over_time(records: list[dict]) -> dict:
    """Build Chart.js-shaped data for score trend by rubric.

    Records lacking a prompt_version are filtered out (they predate the
    schema-v2 migration; including them would put points on the chart with
    no actionable attribution). Returned shape:
        {labels: [iso_timestamp], datasets: [{label: rubric, data: [score]}]}
    """
    typed_records = [
        r
        for r in records
        if r.get("prompt_version") and isinstance(r.get("score"), (int, float)) and r.get("rubric")
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
            for r in typed_records
            if r["rubric"] == rubric
        ]
        datasets.append(
            {
                "label": rubric,
                "data": data,
                "borderColor": palette[i % len(palette)],
                "backgroundColor": palette[i % len(palette)],
                "tension": 0.2,
            }
        )

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
                cells.append(
                    {
                        "score": round(score, 1),
                        "color": f"hsl({hue:.0f} 60% 30%)",
                        "prompt_version": cell_record.get("prompt_version", ""),
                        "timestamp": cell_record.get("timestamp", ""),
                    }
                )
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
            with contextlib.suppress(TypeError, ValueError):
                cost_by_run[run_id] = float(r["cost_usd"])

    points = []
    for r in composite_records:
        phase_lat = r.get("phase_latencies_ms") or {}
        total_lat_ms = sum(v for v in phase_lat.values() if isinstance(v, (int, float)))
        score = r.get("score")
        if score is None or total_lat_ms == 0:
            continue
        run_id = r.get("run_id", "")
        points.append(
            {
                "run_id": run_id,
                "fixture": r.get("fixture", ""),
                "prompt_version": r.get("prompt_version", ""),
                "timestamp": r.get("timestamp", ""),
                "score": float(score),
                "total_latency_ms": int(total_lat_ms),
                "cost_usd": cost_by_run.get(run_id),
                "scores_used": r.get("scores_used", {}),
            }
        )

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
            data.append(
                {
                    "x": lat_s,
                    "y": round(pt["score"], 3),
                    "r": radius,
                    "fixture": pt["fixture"],
                    "run_id": pt["run_id"],
                    "cost_usd": round(cost, 4) if cost is not None else None,
                    "scores_used": pt["scores_used"],
                }
            )
        color = palette[i % len(palette)]
        scatter_datasets.append(
            {
                "label": version,
                "data": data,
                "backgroundColor": color + "99",
                "borderColor": color,
            }
        )

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


def _dedup_by_run(records: list[dict]) -> list[dict]:
    """Keep the first record seen per run_id, preserving input order.

    The groundedness / fabricated_specifics block is computed once per pipeline
    run and copied onto *every* per-rubric record of that run (runner.py emits
    the same det_metrics on each rubric row). Charting them undeduped would plot
    one run's value 5×. Mirrors _pareto_data's "first record per run_id" join.
    Records without a run_id are kept individually (can't be deduped safely).
    """
    seen: set[str] = set()
    out: list[dict] = []
    for r in records:
        run_id = r.get("run_id") or ""
        if run_id:
            if run_id in seen:
                continue
            seen.add(run_id)
        out.append(r)
    return out


def _groundedness_points(records: list[dict]) -> list[dict]:
    """One groundedness point per run, sorted by timestamp.

    Pulls deterministic_metrics.groundedness off each record, dedups by run_id,
    and keeps only points with a numeric score. Shared by the trend chart and
    the latest-detail panel so both agree on what counts as a groundedness run.
    """
    candidates = []
    for r in records:
        gnd = (r.get("deterministic_metrics") or {}).get("groundedness") or {}
        score = gnd.get("score")
        if not isinstance(score, (int, float)):
            continue
        candidates.append(r)
    points = []
    for r in _dedup_by_run(candidates):
        gnd = r["deterministic_metrics"]["groundedness"]
        points.append(
            {
                "timestamp": r.get("timestamp", ""),
                "prompt_version": r.get("prompt_version", ""),
                "run_id": r.get("run_id", ""),
                "fixture": r.get("fixture", ""),
                "score": float(gnd["score"]),
                "fabricated_specifics_rate": gnd.get("fabricated_specifics_rate", 0.0),
                "flagged_count": gnd.get("flagged_count", 0),
                "layers": gnd.get("layers", ["L0"]),
            }
        )
    points.sort(key=lambda p: p["timestamp"])
    return points


def _groundedness_trend(records: list[dict]) -> dict:
    """Chart.js-shaped trend of the L0 groundedness score (0-5) over time.

    One deduped point per run (see _dedup_by_run); each point carries its
    prompt_version (tooltip) and fabricated_specifics_rate. The 0-5 score plugs
    into the same chart machinery as _score_over_time, so a groundedness
    regression is attributable to a specific prompt_version. Empty datasets when
    no record carries a groundedness block (everything pre-2026-06-06).
    """
    points = _groundedness_points(records)
    data = [
        {
            "x": p["timestamp"],
            "y": round(p["score"], 3),
            "v": p["prompt_version"],
            "rate": p["fabricated_specifics_rate"],
            "fixture": p["fixture"],
        }
        for p in points
    ]
    return {
        "has_data": bool(data),
        "labels": [p["timestamp"] for p in points],
        "datasets": [
            {
                "label": "groundedness (L0)",
                "data": data,
                "borderColor": "#4ade80",
                "backgroundColor": "#4ade80",
                "tension": 0.2,
            }
        ]
        if data
        else [],
        "points": len(data),
    }


def _latest_groundedness_detail(records: list[dict]) -> dict:
    """Most-recent run's fabricated_specifics evidence — the drill-down.

    Returns the headline groundedness summary plus the fabricated_specifics
    block (totals + flagged_samples + per_bullet) for the latest run that
    carries one. {"has_data": False} when none exists yet.
    """
    points = _groundedness_points(records)
    if not points:
        return {"has_data": False}
    latest_run = points[-1]["run_id"]
    latest_ts = points[-1]["timestamp"]
    detail: dict = {}
    for r in records:
        if r.get("run_id", "") != latest_run or r.get("timestamp", "") != latest_ts:
            continue
        dm = r.get("deterministic_metrics") or {}
        if dm.get("groundedness") and dm.get("fabricated_specifics"):
            detail = dm
            break
    fab = (detail.get("fabricated_specifics") or {}) if detail else {}
    return {
        "has_data": True,
        "prompt_version": points[-1]["prompt_version"],
        "timestamp": latest_ts,
        "fixture": points[-1]["fixture"],
        "score": round(points[-1]["score"], 3),
        "fabricated_specifics_rate": points[-1]["fabricated_specifics_rate"],
        "flagged_count": points[-1]["flagged_count"],
        "layers": points[-1]["layers"],
        "total_bullets": fab.get("total_bullets", 0),
        "total_specifics": fab.get("total_specifics", 0),
        "flagged_samples": fab.get("flagged_samples", []),
        "per_bullet": fab.get("per_bullet", []),
    }


def _cost_by_call_kind(records: list[dict]) -> list[dict]:
    """Per-call-kind cost rollup over the filtered call list.

    Answers "which stage costs the most?" — analyze/generate dominate; clarify
    is cheap. Uses the same compute_call_cost pricing table as _summarize_calls.
    Sorted by total cost descending. Lazy import avoids a hardening<->dashboard
    import cycle (matching _summarize_calls).
    """
    from hardening import compute_call_cost

    by_kind: dict[str, list[float]] = defaultdict(list)
    for r in records:
        kind = r.get("call") or "unknown"
        by_kind[kind].append(compute_call_cost(r))
    # Sort typed (kind, count, total) tuples — sorting the heterogeneous result
    # dicts would force a dict[str, object] value type that breaks `-cost`.
    rows = sorted(
        ((kind, len(costs), sum(costs)) for kind, costs in by_kind.items()),
        key=lambda t: (-t[2], t[0]),
    )
    return [
        {
            "call_kind": kind,
            "count": count,
            "total_cost_usd": round(total, 6),
            "mean_cost_usd": round(total / count, 6) if count else 0.0,
        }
        for kind, count, total in rows
    ]


def _reliability(records: list[dict]) -> dict:
    """Error + truncation rates over the filtered call list, with per-kind split.

    error = status == "error"; truncation = stop_reason == "max_tokens" (output
    cut off — a silent quality hit the binary status doesn't capture). Both are
    surfaced overall and per call_kind so a flaky stage is isolatable.
    """
    total = len(records)
    by_kind: dict[str, dict] = defaultdict(lambda: {"total": 0, "error": 0, "truncation": 0})
    error = 0
    truncation = 0
    for r in records:
        kind = r.get("call") or "unknown"
        by_kind[kind]["total"] += 1
        is_err = r.get("status") == "error"
        is_trunc = r.get("stop_reason") == "max_tokens"
        if is_err:
            error += 1
            by_kind[kind]["error"] += 1
        if is_trunc:
            truncation += 1
            by_kind[kind]["truncation"] += 1
    rows = []
    for kind, c in sorted(by_kind.items()):
        rows.append(
            {
                "call_kind": kind,
                "total": c["total"],
                "error_count": c["error"],
                "error_rate": round(c["error"] / c["total"], 3) if c["total"] else 0.0,
                "truncation_count": c["truncation"],
                "truncation_rate": round(c["truncation"] / c["total"], 3) if c["total"] else 0.0,
            }
        )
    return {
        "total": total,
        "error_count": error,
        "error_rate": round(error / total, 3) if total else 0.0,
        "truncation_count": truncation,
        "truncation_rate": round(truncation / total, 3) if total else 0.0,
        "by_call_kind": rows,
    }


def _run_trace(records: list[dict]) -> dict:
    """Per-run span waterfall assembled from already-logged call telemetry.

    Each LLM call carries run_id + call (kind) + latency_ms; grouping by run_id
    reconstructs a pipeline trace (analyze_extraction -> analyze_synthesis ->
    clarify -> generate ...) with no new instrumentation. Returns the most-recent
    run's ordered spans (with each span's % of total latency for bar widths) plus
    a short list of recent runs. {"has_data": False} when nothing carries a run_id.
    """
    by_run: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        run_id = r.get("run_id") or ""
        if not run_id:
            continue
        by_run[run_id].append(r)
    if not by_run:
        return {"has_data": False, "latest": None, "runs": []}

    def _run_ts(calls: list[dict]) -> str:
        return max((c.get("timestamp", "") for c in calls), default="")

    runs_sorted = sorted(by_run.items(), key=lambda kv: _run_ts(kv[1]), reverse=True)

    runs = []
    for run_id, calls in runs_sorted[:10]:
        total_lat = sum(c.get("latency_ms", 0) or 0 for c in calls)
        runs.append(
            {
                "run_id": run_id,
                "span_count": len(calls),
                "total_latency_ms": total_lat,
                "timestamp": _run_ts(calls),
            }
        )

    latest_run_id, latest_calls = runs_sorted[0]
    latest_calls = sorted(latest_calls, key=lambda c: c.get("timestamp", ""))
    total_lat = sum(c.get("latency_ms", 0) or 0 for c in latest_calls)
    # bar_pct scales each bar to the LONGEST span (max → 100%), not to the total.
    # Sharing the bar width with `pct` (share of total) made every span but the
    # dominant one render as an invisible sliver; scaling to the max keeps the
    # relative comparison while making short spans visible (`pct` still rides in
    # the row title, `latency_ms` stays the absolute truth).
    max_lat = max((c.get("latency_ms", 0) or 0) for c in latest_calls) if latest_calls else 0
    spans = [
        {
            "call_kind": c.get("call", "unknown"),
            "model": c.get("model", ""),
            "latency_ms": c.get("latency_ms", 0) or 0,
            "status": c.get("status", ""),
            "pct": round(100.0 * (c.get("latency_ms", 0) or 0) / total_lat, 1)
            if total_lat
            else 0.0,
            "bar_pct": round(100.0 * (c.get("latency_ms", 0) or 0) / max_lat, 1)
            if max_lat
            else 0.0,
        }
        for c in latest_calls
    ]
    return {
        "has_data": True,
        "latest": {
            "run_id": latest_run_id,
            "total_latency_ms": total_lat,
            "spans": spans,
        },
        "runs": runs,
    }


def _load_baseline() -> dict:
    """Read evals/results/baseline_v1.json (schema 3). {} if missing/malformed."""
    path = EVAL_RESULTS_DIR / "baseline_v1.json"
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# Health bands vs the baseline floor. -0.5 is the RELEASE_ARC merge-block gate;
# -0.3 is the risk-register "surface in CHANGELOG" threshold.
_HEALTH_REGRESSED_DELTA = -0.5
_HEALTH_WATCH_DELTA = -0.3


def _baseline_health(records: list[dict], baseline: dict) -> dict:
    """Compare the latest score per (fixture, rubric) to its baseline mean.

    Verdict bands: regressed (delta < -0.5, the merge-block gate), watch
    (-0.5 <= delta < -0.3), ok (>= -0.3). `overall` is the worst verdict seen,
    so a single tile badge can summarize quality health at a glance.
    {"has_baseline": False} when no baseline file exists.
    """
    fixtures = baseline.get("fixtures") or {}
    if not fixtures:
        return {"has_baseline": False, "overall": "unknown", "rows": [], "counts": {}}

    # Latest score per (fixture, rubric) — same "most recent wins" rule as the heatmap.
    latest: dict[tuple[str, str], dict] = {}
    for r in records:
        fixture = r.get("fixture")
        rubric = r.get("rubric")
        if not fixture or not rubric or not isinstance(r.get("score"), (int, float)):
            continue
        key = (fixture, rubric)
        prev = latest.get(key)
        if prev is None or r.get("timestamp", "") > prev.get("timestamp", ""):
            latest[key] = r

    rows = []
    counts = {"ok": 0, "watch": 0, "regressed": 0}
    for (fixture, rubric), r in latest.items():
        base = (fixtures.get(fixture) or {}).get(rubric)
        if not base or "mean" not in base:
            continue
        score = float(r["score"])
        mean = float(base["mean"])
        delta = round(score - mean, 3)
        if delta < _HEALTH_REGRESSED_DELTA:
            status = "regressed"
        elif delta < _HEALTH_WATCH_DELTA:
            status = "watch"
        else:
            status = "ok"
        counts[status] += 1
        rows.append(
            {
                "fixture": fixture,
                "rubric": rubric,
                "score": round(score, 2),
                "baseline_mean": round(mean, 2),
                "delta": delta,
                "status": status,
            }
        )
    rows.sort(key=lambda d: (d["fixture"], d["rubric"]))

    if counts["regressed"]:
        overall = "regressed"
    elif counts["watch"]:
        overall = "watch"
    elif rows:
        overall = "ok"
    else:
        overall = "unknown"

    return {
        "has_baseline": True,
        "baseline_id": baseline.get("baseline_id", ""),
        "baseline_prompt_version": baseline.get("prompt_version", ""),
        "overall": overall,
        "rows": rows,
        "counts": counts,
    }


@dashboard_bp.before_request
def _localhost_guard():
    """Same posture as the rest of the app: localhost-only by host check.

    Consumes the shared `web_infra._is_localhost_request` (Sprint 8.3a) rather
    than carrying a third copy of the loopback host-set.
    """
    if not _is_localhost_request():
        abort(403)


def _tune_prompt_choices() -> list[dict]:
    """The overridable system-prompt constants for the Tuning-tab A/B dropdown.

    Read-only use of analyzer's `_BASE_SYSTEM_PROMPTS` registry (no edit, no LLM call):
    each `{name, text}` feeds the constant picker and the "Load current text" prefill so
    a tuner edits the baseline rather than pasting a full prompt from memory. Lazy import
    keeps this read-only blueprint's import surface light; analyzer is already loaded by
    app.py before any request reaches here.
    """
    import analyzer

    return [{"name": name, "text": text} for name, text in analyzer._BASE_SYSTEM_PROMPTS.items()]


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

    # Groundedness (L0) — the marquee new surface, designed around the
    # 2026-06-06 metric contract (deterministic_metrics.groundedness).
    groundedness_trend = _groundedness_trend(eval_results)
    groundedness_detail = _latest_groundedness_detail(eval_results)

    # Tier-0 observability over data we already log — trace/reliability/cost-by-
    # kind ride the filtered call list; health badges compare eval scores to the
    # in-repo baseline floor. No new data is emitted by the dashboard.
    cost_by_call_kind = _cost_by_call_kind(filtered_calls)
    reliability = _reliability(filtered_calls)
    run_trace = _run_trace(filtered_calls)
    baseline_health = _baseline_health(eval_results, _load_baseline())

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
        groundedness_trend=groundedness_trend,
        groundedness_detail=groundedness_detail,
        cost_by_call_kind=cost_by_call_kind,
        reliability=reliability,
        run_trace=run_trace,
        baseline_health=baseline_health,
        tune_prompts=_tune_prompt_choices(),
    )

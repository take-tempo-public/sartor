"""Dashboard routes — read-only Flask blueprint.

Localhost-only by guard. Reads JSONL log files; never writes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, render_template, request

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


def _read_eval_results() -> list[dict]:
    """Aggregate every line of every evals/results/*.jsonl into one list."""
    if not EVAL_RESULTS_DIR.exists():
        return []
    out: list[dict] = []
    for path in sorted(EVAL_RESULTS_DIR.glob("*.jsonl")):
        out.extend(_read_jsonl(path))
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


def _summarize_calls(records: list[dict]) -> dict:
    """Compute aggregate stats over a filtered call list."""
    n = len(records)
    if n == 0:
        return {"count": 0}
    total_in = sum(r.get("input_tokens", 0) for r in records)
    total_out = sum(r.get("output_tokens", 0) for r in records)
    cache_create = sum(r.get("cache_creation_input_tokens", 0) for r in records)
    cache_read = sum(r.get("cache_read_input_tokens", 0) for r in records)
    latencies = [r.get("latency_ms", 0) for r in records if r.get("latency_ms")]
    mean_lat = sum(latencies) / len(latencies) if latencies else 0
    cache_total = cache_create + cache_read
    cache_hit = (cache_read / cache_total) if cache_total else 0.0
    error_count = sum(1 for r in records if r.get("status") == "error")
    return {
        "count": n,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "cache_creation_input_tokens": cache_create,
        "cache_read_input_tokens": cache_read,
        "cache_hit_ratio": round(cache_hit, 3),
        "mean_latency_ms": int(mean_lat),
        "error_count": error_count,
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
    )

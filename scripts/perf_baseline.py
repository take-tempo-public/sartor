"""Print per-call-kind latency percentiles from logs/llm_calls.jsonl.

Use as the before/after snapshot when changing analyzer-side perf:
re-run after a perf intervention (R2 streaming, R3 schema trim, R1
split) and compare p50/p90 to confirm the win.

Usage:
    python -m scripts.perf_baseline
    python -m scripts.perf_baseline --since 50    # last 50 calls per kind
    python -m scripts.perf_baseline --log path/to/llm_calls.jsonl

The latency reported is total wall-clock per call as observed by the
Flask process, not the user's perceived latency. For perceived
latency (streaming vs blocking) you need the in-browser timing.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--log",
        default="logs/llm_calls.jsonl",
        help="Path to the JSONL telemetry file (default: logs/llm_calls.jsonl)",
    )
    ap.add_argument(
        "--since",
        type=int,
        default=None,
        help="Only consider the last N calls per kind (default: all)",
    )
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"No telemetry log at {log_path}")
        return 1

    rows = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        print(f"Telemetry log {log_path} is empty.")
        return 0

    by_kind = defaultdict(list)
    for r in rows:
        by_kind[r.get("call", "?")].append(r)

    print(f"Source: {log_path}  ({len(rows)} total records)")
    if args.since:
        print(f"Filter: last {args.since} calls per kind")
    print()

    header = f"{'call_kind':<24} {'N':>4} {'p50':>8} {'p90':>8} {'max':>8} {'med_out_tok':>12}"
    print(header)
    print("-" * len(header))

    for kind, records in sorted(by_kind.items(), key=lambda x: -len(x[1])):
        latencies = [r["latency_ms"] for r in records if r.get("latency_ms")]
        if not latencies:
            continue
        if args.since:
            latencies = latencies[-args.since :]
        latencies.sort()
        n = len(latencies)
        p50 = int(statistics.median(latencies))
        p90_idx = max(0, int(n * 0.9) - 1)
        p90 = int(latencies[p90_idx] if n >= 10 else latencies[-1])
        max_lat = int(latencies[-1])
        out_tokens = [r.get("output_tokens", 0) for r in records if r.get("output_tokens")]
        med_out = int(statistics.median(out_tokens)) if out_tokens else 0
        print(
            f"{kind:<24} {n:>4} {p50 / 1000:>7.1f}s {p90 / 1000:>7.1f}s "
            f"{max_lat / 1000:>7.1f}s {med_out:>12}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# callback. — Dashboard

Read-only Flask blueprint that surfaces telemetry from the LLM pipeline and eval harness. Localhost-only by guard.

> The dashboard exists so prompt-tuning is **observable** — you can see which prompt revision caused a score swing, which rubric class is most likely to fail, and what each failure cost in dollars and seconds.

---

## Launching

```bash
python app.py
```

Then visit `http://localhost:5000/_dashboard`. The blueprint refuses any request whose `Host` header isn't `localhost`, `127.0.0.1`, or `::1`.

---

## What it shows

Five sections, top to bottom:

### 1. LLM Calls — Summary

Aggregate cards over the filtered call list:

| Card | Source | Notes |
|---|---|---|
| calls | `logs/llm_calls.jsonl` (count) | After filters applied |
| errors | `status == "error"` records | Red when > 0 |
| mean latency | `latency_ms` mean | Wall-clock; includes streaming time |
| **p50 latency** | `_percentile(latencies, 50)` | Median; resistant to outliers |
| **p95 latency** | `_percentile(latencies, 95)` | Tail behavior — what slow calls feel like |
| cache hit ratio | `cache_read / (cache_read + cache_create)` | 100% means every input token was cached |
| in / out tokens | sums | |
| cache create / read | sums | Cache-create is billed at 1.25× normal input; cache-read at 0.10× |
| **total cost** | `compute_call_cost` over filtered records | Uses `hardening.MODEL_PRICING` |
| **mean / call** | total / N | Useful for trend detection |
| **p50 / call** | median per-call cost | |
| **p95 / call** | tail per-call cost | A spike here usually traces to one verbose generate() call |

### 2. LLM Calls — Recent

Per-call rows, most recent 200. Columns: timestamp, user, call type, model, `prompt_version`, **`run_id`**, token counts, latency, status. Filterable by since-date, user, model.

To isolate eval traffic, set the **user** filter to `eval:{fixture_name}` (e.g., `eval:data-scientist-junior`).

The `run_id` column lets you find both calls (analyze + generate) of a single pipeline. For eval rows, the same `run_id` appears on every per-rubric eval result row from that pipeline — so you can answer "which specific LLM calls produced this graded output?" by matching IDs.

### 3. Eval Quality — Aggregations (the tuning views)

#### Per-rubric pass rate (bar chart)

Pass rate per rubric where pass = score ≥ 4.0. Color-coded: green ≥80%, amber 50-80%, red <50%. The first thing to glance at when triaging.

#### Score over time by rubric (line chart)

X-axis = run timestamp, Y-axis = 0-5. One line per rubric. Each point's tooltip labels its `prompt_version`. Records lacking `prompt_version` (legacy schema_version=1) are filtered out — the chart's legend below shows how many were hidden.

Use this to attribute score swings to specific prompt revisions.

#### Rubric × fixture heatmap

Most-recent score per (rubric, fixture) pair. Color: `hsl(120 * score/5, 60%, 30%)` — red for 0.0, green for 5.0. Hover a cell for `prompt_version` and timestamp. Empty cells (— in light-grey) mean that pair has never been graded.

This is the primary view for "where do we need work?" — the red cells are your tuning targets.

#### Top failure modes table

Top-20 `failed_rules` slugs across all eval records, sorted by record count. **Per-record dedup**: a single grading with `failed_rules: ["a","a","b"]` counts once for "a" and once for "b". This keeps a single noisy judgment from dominating the histogram.

When tuning, the top three slugs usually tell you what class of prompt edit to make next. See `evals/TUNING_LOG.md` for examples.

### 4. Eval Results — Recent

Per-rubric verdict rows, most recent 200. Columns: timestamp, fixture, rubric, score (color-coded by ≥4.0), `prompt_version`, status, failed_rules.

---

## Schema compatibility

Two record schemas live in `evals/results/*.jsonl`:

| Version | Score type | Has `prompt_version`? | Has `deterministic_metrics`? |
|---|---|---|---|
| 1 (pre-2026-05-09) | int 0-5 | No | No |
| 2 (current) | float 0.0-5.0 | Yes | Yes |

`dashboard.routes._normalize_eval_record` coerces both shapes into a uniform structure at read time — int scores become floats, missing fields get sensible defaults. **Stored files are never rewritten.**

The `score_over_time` chart filters out v1 records (no `prompt_version`); the heatmap and failure-mode table include them.

---

## Architecture

```
dashboard/
├── routes.py          ← Flask blueprint, aggregations, route handler
├── templates/
│   └── dashboard.html ← Single template; Chart.js loaded from CDN
└── README.md          ← this file
```

`app.py` registers the blueprint at `/_dashboard` (see `app.py:38`). The blueprint has no routes other than the index — all data is server-rendered into the single template.

### Aggregation helpers

All in [`routes.py`](routes.py):

| Helper | Returns |
|---|---|
| `_normalize_eval_record(r)` | Coerces a legacy or current record to uniform shape |
| `_summarize_calls(records)` | LLM-call summary card data including total/mean cost |
| `_per_rubric_pass_rate(records)` | List of `{rubric, total, pass_count, pass_rate}` |
| `_score_over_time(records)` | Chart.js-shaped trend data with `prompt_version` per point |
| `_rubric_fixture_heatmap(records)` | `{rubrics, fixtures, rows}` matrix with HSL cell colors |
| `_failure_mode_frequency(records)` | Top-20 `failed_rules` slugs by record count (per-record dedup) |

### No new Python deps

The dashboard uses **Chart.js loaded from a CDN** (jsdelivr). No Python charting library, no pandas. Graceful degradation: the failure-mode table and heatmap render server-side; only the bar and line charts require JS. A `<noscript>` block in the bar-chart panel falls back to a plain HTML table.

---

## Adding a new chart or aggregation

1. Add a helper in `routes.py` that takes the (already-normalized) eval records and returns Chart.js-shaped data.
2. Wire it into `index()`'s template context.
3. Add a `<canvas>` block (or HTML table) in `templates/dashboard.html` and a `new Chart(...)` invocation in the existing `<script>` at the end of the body.
4. Add a unit test in `tests/test_dashboard_routes.py` covering empty-input, expected-shape, and edge-case behaviors.

Keep aggregation functions pure (record list in, dict out, no I/O) — that's what lets `tests/test_dashboard_routes.py` cover them without spinning up the Flask app.

---

## Related files

| File | Role |
|---|---|
| [`routes.py`](routes.py) | Flask blueprint + aggregation helpers |
| [`templates/dashboard.html`](templates/dashboard.html) | Single-page template, Chart.js via CDN |
| [`../analyzer.py`](../analyzer.py) | Source of `logs/llm_calls.jsonl` telemetry (`_emit_call_log`) |
| [`../hardening.py`](../hardening.py) | Source of `compute_call_cost` and `MODEL_PRICING` |
| [`../evals/runner.py`](../evals/runner.py) | Source of `evals/results/*.jsonl` |
| [`../evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) | Iteration log; the dashboard is the "before" state for each entry |

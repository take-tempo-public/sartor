# sartor. — Dashboard

Flask blueprint that surfaces telemetry from the LLM pipeline and eval harness. Localhost-only by guard. The blueprint's own routes only read; the console's paid runs and annotation writes go through `blueprints/diagnostics.py` (see "Write surfaces" under What it shows).

> The dashboard exists so prompt-tuning is **observable** — you can see which prompt revision caused a score swing, which rubric class is most likely to fail, and what each failure cost in dollars and seconds.

---

## Launching

```bash
python app.py
```

Then visit `http://localhost:5000/_dashboard`. The blueprint refuses any request whose `Host` header isn't `localhost`, `127.0.0.1`, or `::1`.

---

## What it shows

**Five tabs** (Pipeline, Quality, Groundedness, Tuning, Annotate), each a bento grid of
summary tiles. Clicking a tile opens its detail in one shared **inline, full-width detail
panel** (`#detailPanel`). JS moves the tile's detail block in from `#detailStore`, and charts
lazy-init the first time their detail opens. The console is built on the cb-* design system
(it links `static/style.css`); layout is scoped under `.cb-dash`. Everything is
server-rendered, so with JS off the panes stack and the details render inline.

**What each tab reads, which routes it calls, what is paid and what it writes** is documented
per tab, with flow diagrams, in
[`docs/dev/diagnostics.md`](../docs/dev/diagnostics.md). This README covers the code in this
directory.

**This blueprint never writes.** It has two GET routes: the index, and `GET /api/run/<run_id>`
for the run-detail modal. The console's paid and write routes live in
`blueprints/diagnostics.py`.

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
│   └── dashboard.html ← Single template; tabs + bento + inline detail panel; Chart.js vendored locally
└── README.md          ← this file
```

`app.py` registers the blueprint at `/_dashboard`. Besides the index, the
blueprint has one JSON route, `GET /api/run/<run_id>`, which the run-detail modal
fetches. Everything else is server-rendered into the single template; tabs and
the detail panel are vanilla JS over that server-rendered content.

### Aggregation helpers

All in [`routes.py`](routes.py), all **pure** (record list in, dict out, no I/O —
except `_load_baseline`, which reads the in-repo baseline file):

| Helper | Returns |
|---|---|
| `_normalize_eval_record(r)` | Coerces a legacy or current record to uniform shape (incl. `deterministic_metrics` default) |
| `_summarize_calls(records)` | LLM-call summary card data including total/mean cost |
| `_per_rubric_pass_rate(records)` | List of `{rubric, total, pass_count, pass_rate}` |
| `_score_over_time(records)` | Chart.js-shaped trend data with `prompt_version` per point |
| `_rubric_fixture_heatmap(records)` | `{rubrics, fixtures, rows}` matrix with HSL cell colors |
| `_failure_mode_frequency(records)` | Top-20 `failed_rules` slugs by record count (per-record dedup) |
| `_pareto_data(records)` | Quality-vs-latency scatter + latency/cost trends + verdict |
| `_dedup_by_run(records)` | First record per `run_id` (shared dedup primitive) |
| `_groundedness_trend(records)` | L0 `groundedness.score` (0–5) over time by `prompt_version`, deduped by run |
| `_latest_groundedness_detail(records)` | Latest run's `fabricated_specifics` evidence (flagged_samples + per_bullet) |
| `_cost_by_call_kind(records)` | Per-call-kind cost rollup, sorted by total |
| `_reliability(records)` | Error + `max_tokens`-truncation rates, overall + per call kind |
| `_run_trace(records)` | Per-`run_id` span waterfall (latest run) + recent-runs list |
| `_load_baseline()` / `_baseline_health(records, baseline)` | Latest score per (fixture×rubric) vs the baseline floor → ok/watch/regressed |

### No new Python deps

The dashboard uses **Chart.js vendored locally** at `static/vendor/chart.umd.min.js` (no runtime CDN fetch; see [`SECURITY.md`](../SECURITY.md) bundled-assets). No Python charting library, no pandas. Graceful degradation: tables and the trace waterfall render server-side; charts require JS and lazy-init when their detail first opens. With JS off, the `.js`-gated CSS leaves all panes + detail blocks visible (stacked inline), and the `<noscript>` bar-chart fallback table remains.

---

## Adding a new chart or aggregation

1. Add a **pure** helper in `routes.py` that takes the (already-normalized) records and returns Chart.js-shaped data.
2. Wire it into `index()`'s template context.
3. Add a summary `tile` (with `data-detail="…"`) in the relevant tab pane, and a matching `<div class="detail" data-detail="…">` in `#detailStore` holding the table/`<canvas>`. For a chart, register a `data-chart="…"` canvas + an entry in the `INIT` map in the page `<script>` (it lazy-inits the first time its detail opens).
4. Add a unit test in `tests/test_dashboard_routes.py` (empty-input, expected-shape, edge cases). For interactive surfaces, extend `tests/ux/flows/test_dashboard_console.py`.

Keep aggregation functions pure — that's what lets `tests/test_dashboard_routes.py` cover them without spinning up the Flask app.

---

## Related files

| File | Role |
|---|---|
| [`routes.py`](routes.py) | Flask blueprint + aggregation helpers |
| [`templates/dashboard.html`](templates/dashboard.html) | Tabbed console template (bento tiles + inline detail panel), cb-* tokens via `static/style.css`, Chart.js vendored at `static/vendor/chart.umd.min.js` |
| [`../ui_pages/dashboard_console.py`](../ui_pages/dashboard_console.py) | Page Object for the console (used by `tests/ux/`) |
| [`../analyzer.py`](../analyzer.py) | Source of `logs/llm_calls.jsonl` telemetry (`_emit_call_log`) |
| [`../hardening.py`](../hardening.py) | Source of `compute_call_cost` and `MODEL_PRICING` |
| [`../evals/runner.py`](../evals/runner.py) | Source of `evals/results/*.jsonl` |
| [`../evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) | Iteration log; the dashboard is the "before" state for each entry |

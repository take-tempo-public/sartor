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

**Four tabs, each a bento grid of summary tiles.** A tile shows a headline stat;
clicking it opens one shared **right-hand drawer** with the full chart/table +
detail. Charts lazy-init when their drawer first opens. The console is built on
the cb-* design system (links `static/style.css`); layout is scoped under
`.cb-dash`. Everything is server-rendered — with JS off, panes stack and details
render inline (graceful degradation). The **blueprint itself is read-only** — its
only route is the index, and it never writes. The one write surface is the
**Annotate** tab, whose read/write routes live in `app.py` (not this blueprint)
and are localhost-gated + slug-contained under `evals/fixtures/real/` — see the
Annotate section below.

### Pipeline

| Tile | Drawer detail | Source |
|---|---|---|
| **Cost meter** (total · p50 · p95) | cost-by-call-kind bar + table | `_summarize_calls` + `_cost_by_call_kind` |
| **Throughput** (calls · cache-hit · tokens) | recent-calls table (most recent 200), filterable by since/user/model | `_summarize_calls` |
| **Reliability** (error % · truncation %) | error + `max_tokens`-truncation rates, split by call kind | `_reliability` |
| **Trace** (latest run spans / total latency) | per-`run_id` span **waterfall** + recent-runs table | `_run_trace` |
| **Latency** (p50 / p95) | percentile detail | `_summarize_calls` / `_percentile` |

Filter calls by since-date, user, model. To isolate eval traffic set **user** to
`eval:{fixture}` (e.g. `eval:pm-senior`). The `run_id` joins both calls of a
pipeline and the per-rubric eval rows from that pipeline.

### Quality

| Tile | Drawer detail | Source |
|---|---|---|
| **Health vs baseline** (overall badge) | per-(fixture×rubric) delta vs the `baseline_v1.json` floor | `_baseline_health` / `_load_baseline` |
| **Pass rate** | per-rubric pass-rate bar (pass = score ≥ 4.0) | `_per_rubric_pass_rate` |
| **Score trend** | score-over-time line, one per rubric, `prompt_version` on hover | `_score_over_time` |
| **Heatmap** | most-recent score per (rubric, fixture), `hsl(120·score/5)` cells | `_rubric_fixture_heatmap` |
| **Failure modes** | top-20 `failed_rules` slugs (per-record dedup) | `_failure_mode_frequency` |
| **Pareto** (verdict badge) | quality-vs-latency scatter + latency/cost trends | `_pareto_data` |

Health bands: **regressed** Δ<−0.5 (the merge-block gate), **watch** Δ<−0.3,
else **ok**. The overall badge is the worst verdict present.

### Groundedness

The marquee surface, designed around the 2026-06-06 metric contract
(`deterministic_metrics.groundedness`). Tile shows the latest L0 score (0–5),
fabricated-specifics rate, and flagged count. The drawer charts
`groundedness.score` **over time by `prompt_version`** (one point per run,
**deduped by `run_id`** — the block repeats across every rubric row of a run) and
drills into the `fabricated_specifics` evidence: `flagged_samples` +
per-bullet breakdown. L0 is a **flag-for-review** signal (high precision on novel
specifics; false-positives on paraphrase), uncalibrated until labels exist — see
`docs/dev/GROUNDING_METRIC.md`. Helpers: `_groundedness_trend`,
`_latest_groundedness_detail` (both via `_groundedness_points` / `_dedup_by_run`).

### Tuning

A **read-only scaffold**. Documents the `analyzer.prompt_overrides()`
candidate-vs-baseline A/B primitive and links to `/prompt-tune`,
`/tune-from-annotations`, and `evals/TUNING_LOG.md`. No write affordances — those
land in a later, sign-off-gated branch.

### Annotate (the read-write surface)

The console's **only write surface** (`feat/annotation-tab`, v1.0.5) — it runs the
v1.0.4 eval tuning loop in-browser instead of via raw JSON + CLI. Three steps:

1. **Produce a bootstrap** — the browser bootstrap wrapper drives
   `analyze → clarify → generate` over N pasted JDs against the live corpus
   (reusing the `/api/analyze/stream` SSE pattern + `evals.bootstrap`'s
   deterministic dedup) and writes a `bootstrap.json`. **Paid (Sonnet/Haiku) +
   slow (~70s/JD).**
2. **Annotate** — per bullet/skill cluster: a verdict
   (`keep`/`fix`/`omit`/`fabricated`), `failed_rules` from the rubric vocabulary,
   `should_omit`, and a conditional `honest_rewrite` (fix) / `forbidden_pattern`
   (fabricated); plus clarification-question ratings. Save runs the **fail-closed
   `evals.annotation.validate_annotations`**, so the written `annotations.json` is
   always collation-ready.
3. **Collate** — deterministic `collate_expected` + `build_improvement_brief` →
   `expected.json` + `improvement_brief.md` + an anchor `jd.txt`, runnable by
   `runner.py --suite real`.

The routes live in **`app.py`** (`/api/annotation/...`), not this blueprint, so
the blueprint stays read-only. They reuse `evals.annotation` / `evals.bootstrap`
verbatim (the `annotations.json` schema is **not forked**), are **localhost-only**,
and write ONLY under `ANNOTATION_ROOT` = `evals/fixtures/real/` (gitignored) via
`_safe_username()` + `secure_filename(slug)` + `_within(...)`. The labels it
produces are the corpus the deferred grounding calibration (B) needs — see
`docs/dev/GROUNDING_METRIC.md` §calibration.

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
│   └── dashboard.html ← Single template; tabs + bento + drawer; Chart.js from CDN
└── README.md          ← this file
```

`app.py` registers the blueprint at `/_dashboard`. The blueprint has no routes
other than the index — all data is server-rendered into the single template; tabs
and the drawer are vanilla JS over that server-rendered content.

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

The dashboard uses **Chart.js loaded from a CDN** (jsdelivr). No Python charting library, no pandas. Graceful degradation: tables and the trace waterfall render server-side; charts require JS and lazy-init on drawer-open. With JS off, the `.js`-gated CSS leaves all panes + detail blocks visible (stacked inline), and the `<noscript>` bar-chart fallback table remains.

---

## Adding a new chart or aggregation

1. Add a **pure** helper in `routes.py` that takes the (already-normalized) records and returns Chart.js-shaped data.
2. Wire it into `index()`'s template context.
3. Add a summary `tile` (with `data-detail="…"`) in the relevant tab pane, and a matching `<div class="detail" data-detail="…">` in `#detailStore` holding the table/`<canvas>`. For a chart, register a `data-chart="…"` canvas + an entry in the `INIT` map in the page `<script>` (it lazy-inits on first drawer-open).
4. Add a unit test in `tests/test_dashboard_routes.py` (empty-input, expected-shape, edge cases). For interactive surfaces, extend `tests/ux/flows/test_dashboard_console.py`.

Keep aggregation functions pure — that's what lets `tests/test_dashboard_routes.py` cover them without spinning up the Flask app.

---

## Related files

| File | Role |
|---|---|
| [`routes.py`](routes.py) | Flask blueprint + aggregation helpers |
| [`templates/dashboard.html`](templates/dashboard.html) | Tabbed console template (bento tiles + shared drawer), cb-* tokens via `static/style.css`, Chart.js via CDN |
| [`../ui_pages/dashboard_console.py`](../ui_pages/dashboard_console.py) | Page Object for the console (used by `tests/ux/`) |
| [`../analyzer.py`](../analyzer.py) | Source of `logs/llm_calls.jsonl` telemetry (`_emit_call_log`) |
| [`../hardening.py`](../hardening.py) | Source of `compute_call_cost` and `MODEL_PRICING` |
| [`../evals/runner.py`](../evals/runner.py) | Source of `evals/results/*.jsonl` |
| [`../evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) | Iteration log; the dashboard is the "before" state for each entry |

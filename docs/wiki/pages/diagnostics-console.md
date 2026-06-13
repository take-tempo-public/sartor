# Diagnostics console

> **Audience:** `dev`
> **Concept:** the localhost-only `/_dashboard` console — a read-only Flask
> blueprint of telemetry + eval tiles, plus the SSE eval / tune / annotation
> write surface in `app.py` that drives the in-browser self-tuning loop.
> **Sources:** [`dashboard/routes.py`](../../../dashboard/routes.py),
> [`dashboard/__init__.py`](../../../dashboard/__init__.py),
> [`dashboard/README.md`](../../../dashboard/README.md),
> [`app.py`](../../../app.py),
> [`docs/architecture.md`](../../architecture.md),
> [`docs/system-model.md`](../../system-model.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What it is

A self-contained observability surface mounted at `/_dashboard`, registered as
`app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")`
([`app.py`](../../../app.py)). The blueprint object is built in
[`dashboard/routes.py:dashboard_bp`](../../../dashboard/routes.py) with a single
`template_folder`, and re-exported from
[`dashboard/__init__.py`](../../../dashboard/__init__.py). It exists so prompt
tuning is *observable* — which prompt revision moved a score, which rubric fails
most, what each failure cost in dollars and seconds `[synthesis]`.

It is not Product. [`system-model.md`](../../system-model.md) files `dashboard/`
under the **Evaluation** function ("measures, verifies, improves Production"),
alongside `tests/` and `evals/`; [`architecture.md`](../../architecture.md)'s
module map lists it between `db/` and `evals/`. Its *dependency* direction is the
category: it reads the eval harness's outputs and the analyzer's telemetry —
co-location in the route tree is not membership in the Product pipeline
`[synthesis]`.

## The localhost + PII guard

The whole blueprint is loopback-only by a `before_request` hook:
[`dashboard/routes.py:_localhost_guard`](../../../dashboard/routes.py) splits the
`Host` header on `:` and `abort(403)`s unless the host is `localhost`,
`127.0.0.1`, `::1`, or `[::1]`. The write routes in `app.py` enforce the **same**
posture through [`app.py:_is_localhost_request`](../../../app.py) (identical host
set), each route returning a JSON 403 when it fails. This is the access control
for surfaces that touch PII-bearing artifacts under `evals/fixtures/real/`
`[synthesis]`. The console is not part of the canonical `_safe_username` /
`_within` route gate's threat model except where it *writes* — see "Annotate"
below; the security gate itself is canonical in [`AGENTS.md`](../../../AGENTS.md),
cited not restated (D5).

## Read-only blueprint: one route, pure helpers

[`dashboard/routes.py:index`](../../../dashboard/routes.py) is the blueprint's
**only** route. It reads two JSONL sources — `logs/llm_calls.jsonl` (the
analyzer's per-call telemetry) via
[`_read_jsonl`](../../../dashboard/routes.py) and `evals/results/*.jsonl` via
[`_read_eval_results`](../../../dashboard/routes.py) — then renders one template.
The blueprint never writes ([`dashboard/routes.py`](../../../dashboard/routes.py)
docstring: "Localhost-only by guard. Reads JSONL log files; never writes.") `[synthesis]`.

Schema drift is absorbed at read time, not on disk:
[`_normalize_eval_record`](../../../dashboard/routes.py) coerces legacy
(schema_version 1, int scores, no `prompt_version`) and current (v2, float, with
`deterministic_metrics`) records to one shape — stored files are never rewritten.

The aggregation helpers are **pure** (record list in, dict out, no I/O except
[`_load_baseline`](../../../dashboard/routes.py)) so they unit-test without a live
app `[synthesis]`. They populate four tabbed bento grids of tiles, each opening a
shared right-hand drawer (Chart.js from CDN, lazy-init on open):

- **Pipeline** — cost ([`_summarize_calls`](../../../dashboard/routes.py) +
  [`_cost_by_call_kind`](../../../dashboard/routes.py)), reliability
  ([`_reliability`](../../../dashboard/routes.py): error% + `max_tokens`
  truncation%), and a per-`run_id` span waterfall
  ([`_run_trace`](../../../dashboard/routes.py)) — all over the filtered call list.
- **Quality** — baseline-delta health bands
  ([`_baseline_health`](../../../dashboard/routes.py): regressed Δ<−0.5 = the
  merge-block gate, watch Δ<−0.3, else ok), per-rubric pass rate (≥4.0)
  ([`_per_rubric_pass_rate`](../../../dashboard/routes.py)), score trend
  ([`_score_over_time`](../../../dashboard/routes.py), one line per rubric, points
  attributed by `prompt_version`), the (rubric × fixture) HSL heatmap
  ([`_rubric_fixture_heatmap`](../../../dashboard/routes.py)), top-20 failure
  modes ([`_failure_mode_frequency`](../../../dashboard/routes.py)), and the
  quality-vs-latency Pareto scatter
  ([`_pareto_data`](../../../dashboard/routes.py)).
- **Groundedness** — the L0 score over time, deduped one-point-per-run
  ([`_groundedness_trend`](../../../dashboard/routes.py) via
  [`_dedup_by_run`](../../../dashboard/routes.py)) plus the latest run's
  `fabricated_specifics` drill-down
  ([`_latest_groundedness_detail`](../../../dashboard/routes.py)).
- **Tuning** — a read-only scaffold; the constant picker is fed by
  [`_tune_prompt_choices`](../../../dashboard/routes.py), a read-only lazy import
  of `analyzer._BASE_SYSTEM_PROMPTS`.

`prompt_version` is the trend axis throughout — score / groundedness charts drop
records lacking one, so a regression is attributable to a specific prompt
revision. The `PROMPT_VERSION`-bump discipline that keeps this honest is
canonical in [`AGENTS.md`](../../../AGENTS.md) (D5).

## The SSE self-tuning loop (writes live in `app.py`)

The interactive write surface is **not** in the blueprint — it is a set of routes
in [`app.py`](../../../app.py), keeping the blueprint read-only `[synthesis]`.
Each route is `_is_localhost_request`-gated and streams via
[`app.py:_sse`](../../../app.py) (`event: <name>\ndata: <json>\n\n`) over a
`text/event-stream` Response so a paid wait reads as alive:

- [`app.py:eval_run_stream`](../../../app.py) — `POST /api/eval/run`. The browser
  face of `python evals/runner.py …`: drives `evals.runner.run_suite` in a worker
  thread and streams `start`/`fixture_start`/`analyzing`/`clarifying`/
  `generating`/`rubric_done`/`fixture_done`/`done`. **Paid** (Sonnet + Haiku); all
  validation (bad suite, unknown user, missing seed) returns a JSON 4xx *before*
  the worker spends anything.
- [`app.py:tune_run_stream`](../../../app.py) — `POST /api/tune/run`. Runs
  `run_suite` **twice** in one worker — baseline (no overrides) then candidate
  (the pasted `prompt_overrides` map) — and streams a per-(fixture, rubric) delta
  from the LLM-free `evals.tune` helpers. The candidate self-stamps
  `prompt_version=candidate:<hash>` via `analyzer.prompt_overrides`, so it never
  pollutes score-over-time; promote stays manual (the route never edits
  `analyzer.py`).
- `POST /api/annotation/*` — the **only** write surface, running the v1.0.4
  tuning loop in-browser. [`annotation_bootstrap_stream`](../../../app.py)
  (`/api/annotation/bootstrap`, paid) drives analyze→clarify→generate over pasted
  JDs; [`annotation_save`](../../../app.py) writes a fail-closed-validated
  `annotations.json`; [`annotation_collate`](../../../app.py) (`…/collate`,
  deterministic) reuses `collate_expected` + `build_improvement_brief` →
  `expected.json` + `improvement_brief.md` + a runnable anchor `jd.txt`;
  [`annotation_score_grounding`](../../../app.py) (`…/score`, **no paid calls**)
  backfills NLI/MiniCheck pre-scores over a throwaway in-memory SQLite.

Every annotation write is contained: [`app.py`](../../../app.py) routes apply
`_safe_username()` + `secure_filename(slug)` + `_within(path, ANNOTATION_ROOT)`
(= `evals/fixtures/real/`, gitignored) — the canonical gate from
[`AGENTS.md`](../../../AGENTS.md), here on a localhost-only seam (D5).

## Related

- [[code-module-map]] — where `dashboard/` and the eval tooling sit in the tree.
- [[eval-harness]] — `evals/runner.py`, whose `results/*.jsonl` this console reads.
- [[route-surface]] — the Flask routes, including the SSE eval/tune/annotation seam.

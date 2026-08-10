# Diagnostics console

> **Audience:** `dev`
> **Concept:** the localhost-only `/_dashboard` console — a read-only Flask
> blueprint of telemetry + eval tiles, plus the SSE eval / tune / annotation
> write surface in `blueprints/diagnostics.py` that drives the in-browser
> self-tuning loop.
> **Sources:** [`dashboard/routes.py`](../../../dashboard/routes.py),
> [`dashboard/__init__.py`](../../../dashboard/__init__.py),
> [`dashboard/README.md`](../../../dashboard/README.md),
> [`dashboard/templates/dashboard.html`](../../../dashboard/templates/dashboard.html),
> [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py),
> [`web_infra/http.py`](../../../web_infra/http.py),
> [`web_infra/request_gates.py`](../../../web_infra/request_gates.py),
> [`app.py`](../../../app.py),
> [`docs/architecture.md`](../../architecture.md),
> [`docs/system-model.md`](../../system-model.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What it is

A self-contained observability surface mounted at `/_dashboard`, registered as
`app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")` inside
[`app.py:register_blueprints`](../../../app.py) — one call among the nine that
factory function makes (see [[code-module-map]] for the full blueprint
roster). The blueprint object is built in
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

The whole blueprint is loopback-only by a `before_request` hook,
[`dashboard/routes.py:_localhost_guard`](../../../dashboard/routes.py), which
`abort(403)`s unless the host is `localhost`, `127.0.0.1`, `::1`, or `[::1]`.
Since Sprint 8.3a this check is no longer a local duplicate: `_localhost_guard`
**calls the shared**
[`web_infra/request_gates.py:_is_localhost_request`](../../../web_infra/request_gates.py)
(which does the `Host`-header split), rather than re-implementing the host set
inline. The write routes in [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py)
enforce the **same** posture through the identical `_is_localhost_request`
import, each route returning a JSON 403 when it fails — dashboard and
diagnostics now literally share one function instead of two copies with an
"identical host set" `[synthesis]`. This is the access control for surfaces
that touch PII-bearing artifacts under `evals/fixtures/real/` `[synthesis]`.
The console is not part of the canonical `_safe_username` / `_within` route
gate's threat model except where it *writes* — see "Annotate" below; the
security gate itself is canonical in [`AGENTS.md`](../../../AGENTS.md), cited
not restated (D5).

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
(schema_version 1, int scores, no `prompt_version`), v2 (float, with
`deterministic_metrics`) and v3 records to one shape — stored files are never
rewritten. It `setdefault`s a blank F-14 `jd_label` for records predating that field.

Two limits of that normalization are handled explicitly rather than assumed away,
both worth knowing before adding a tile that renders records directly `[synthesis]`:

- `setdefault` fills a **missing** key but never coerces a **present malformed** one,
  so a record carrying `"jd_label": "Acme"` would reach Jinja as a bare string where
  `.title` resolves to Python's `str.title` **method**.
  [`dashboard/routes.py:_jd_label_display`](../../../dashboard/routes.py) is the
  guard: non-dict in, `""` out; otherwise `title · company` with blanks dropped.
- `evals/results/*.jsonl` also holds non-eval reports from other tools (a
  `vector_before_after_*.jsonl` comparison run) that share the directory and lack
  `fixture`/`score` entirely. Every aggregation already gated on a truthy `fixture`;
  the recent-evals list is the one place rendering individual records, so it applies
  the same gate inside its `itertools.islice` rather than crashing on an `Undefined`
  attribute ([`dashboard/routes.py:index`](../../../dashboard/routes.py)).

[`dashboard/routes.py:_fixture_jd_labels`](../../../dashboard/routes.py) builds **one**
most-recent-non-blank-label-per-fixture map shared by the heatmap header and the
baseline-health rows. Deliberately one map rather than each table capturing labels in
its own loop: the two apply different record filters, so independently computing
"latest per fixture" is not guaranteed to pick the same record — and two tables
disagreeing about the same fixture's identity is worse than no label
([`dashboard/routes.py:_fixture_jd_labels`](../../../dashboard/routes.py) docstring).
The rendered gloss is clamped (`.jd-label`, `max-width: 12rem` + ellipsis) because
`table.heatmap` is `width:auto` with no `overflow-x` wrapper, so an unclamped label
would inflate every column
([`dashboard/templates/dashboard.html`](../../../dashboard/templates/dashboard.html)).

The aggregation helpers are **pure** (record list in, dict out, no I/O except
[`_load_baseline`](../../../dashboard/routes.py)) so they unit-test without a live
app `[synthesis]`. They populate four tabbed bento grids of tiles, each opening a
shared right-hand drawer (Chart.js — vendored at
[`static/vendor/chart.umd.min.js`](../../../static/vendor/chart.umd.min.js), no
runtime CDN; lazy-init on open):

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
  attributed by `prompt_version`; excludes `status == "judge_error"` records so
  grader crashes do not chart as 0-scores), the (rubric × fixture) HSL heatmap
  ([`_rubric_fixture_heatmap`](../../../dashboard/routes.py); cells with
  `judge_error` render empty), top-20 failure
  modes ([`_failure_mode_frequency`](../../../dashboard/routes.py)), the
  quality-vs-latency Pareto scatter
  ([`_pareto_data`](../../../dashboard/routes.py)), and a **recent evals** tile —
  the most recent 200 records as `timestamp / fixture / jd label / rubric / score /
  prompt v / run / status / failed rules`. That table existed before the v1.0.5
  tabbed-console redesign (`edde81d`) deleted it and was **restored** by item 32 as
  a Quality-tab tile ([`evals/README.md`](../../../evals/README.md) §"How to read
  the dashboard"; [`dashboard/templates/dashboard.html`](../../../dashboard/templates/dashboard.html),
  `data-detail="recent"`). Note what it does *not* show: the three deterministic
  ride-along metrics (`verb_diversity`, `specificity_density`, `grounding_overlap`)
  are **not** dashboard columns — read the raw JSONL for those.
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

## In-app help: a ported primitive, not a shared import

Each diagnostics pane opens with a one-line summary + an `(i)`-circle (the static
[`.dash-pane-intro`](../../../dashboard/templates/dashboard.html) rows) that opens a
per-tab explainer modal; the Pipeline explainer auto-opens once-ever on first visit. The
mechanism is a deliberate **port** of the wizard's help primitive (see
[[frontend-wizard]]) — the console is self-contained and never loads
[`static/app.js`](../../../static/app.js), so a tabs-IIFE-local opener
[`dashboard.html:openDashHelp`](../../../dashboard/templates/dashboard.html) + registry
[`dashboard.html:_DASH_HELP`](../../../dashboard/templates/dashboard.html) (keyed
`dashPipeline` / `dashQuality` / `dashGroundedness` / `dashTuning` / `dashAnnotate`)
re-implement it inline `[synthesis]`.

It is intentionally **not** coupled: the port reuses the wizard's `#helpModal` element
ids/classes ([`dashboard.html`](../../../dashboard/templates/dashboard.html)) and the same
`cb_help_seen:` localStorage prefix, so the shared `Help` page-object and the UX-suite's
once-ever-suppression seed apply to both surfaces unchanged. First-view auto-open is gated
by [`dashboard.html:_maybeFireDashHelp`](../../../dashboard/templates/dashboard.html),
which returns early on the seen-flag before opening — the suppression contract the UX
suite's tour-stop seed relies on `[synthesis]`. The annotate tab's verdict legend
(`keep`/`fix`/`omit`/`fabricated`, each glossed plainly) and the per-pane "why empty" copy
were rewritten for lay readers in the same pass — the write mechanism (routes + gating) is
unchanged from "The SSE self-tuning loop" below.

## The SSE self-tuning loop (writes live in `blueprints/diagnostics.py`)

The interactive write surface is **not** in the blueprint — it is a set of
routes in [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py)
(Sprint 8.3h, the last domain seam extracted from `app.py` — after it the
monolith carried zero routes), keeping the `dashboard_bp` blueprint read-only
`[synthesis]`. Each route is `_is_localhost_request`-gated and streams via
[`web_infra/http.py:_sse`](../../../web_infra/http.py)
(`event: <name>\ndata: <json>\n\n`) over a `text/event-stream` Response so a
paid wait reads as alive — every SSE route captures its `current_app.config`
values as locals **before** the generator runs (the generator executes lazily,
after the view returns and the app context is gone) `[synthesis]`:

- [`blueprints/diagnostics.py:eval_run_stream`](../../../blueprints/diagnostics.py) —
  `POST /api/eval/run`. The browser face of `python evals/runner.py …`: drives
  `evals.runner.run_suite` in a worker thread and streams
  `start`/`fixture_start`/`analyzing`/`clarifying`/
  `generating`/`rubric_done`/`fixture_done`/`done`. **Paid** (Sonnet + Haiku); all
  validation (bad suite, unknown user, missing seed) returns a JSON 4xx *before*
  the worker spends anything.
- [`blueprints/diagnostics.py:tune_run_stream`](../../../blueprints/diagnostics.py) —
  `POST /api/tune/run`. Runs `run_suite` **twice** in one worker — baseline (no
  overrides) then candidate (the pasted `prompt_overrides` map) — and streams a
  per-(fixture, rubric) delta from the LLM-free `evals.tune` helpers. The
  candidate self-stamps `prompt_version=candidate:<hash>` via
  `analyzer.prompt_overrides`, so it never pollutes score-over-time; promote
  stays manual (the route never edits `analyzer.py`).
- `POST /api/annotation/*` — the **only** write surface, running the v1.0.4
  tuning loop in-browser, all in
  [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py):
  [`annotation_bootstrap_stream`](../../../blueprints/diagnostics.py)
  (`/api/annotation/bootstrap`, paid) drives analyze→clarify→generate over pasted
  JDs; [`annotation_save`](../../../blueprints/diagnostics.py) writes a
  fail-closed-validated `annotations.json`;
  [`annotation_collate`](../../../blueprints/diagnostics.py) (`…/collate`,
  deterministic) reuses `collate_expected` + `build_improvement_brief` →
  `expected.json` + `improvement_brief.md` + a runnable anchor `jd.txt`;
  [`annotation_score_grounding`](../../../blueprints/diagnostics.py) (`…/score`,
  **no paid calls**) backfills NLI/MiniCheck pre-scores over a throwaway
  in-memory SQLite.

### Collate fails closed on a mismatched pin (items 11 → 13)

[`blueprints/diagnostics.py:_resolve_bootstrap_pin`](../../../blueprints/diagnostics.py)
decides which bootstrap doc a fixture's routes read, and now returns
`(path, stale_reason)` rather than a bare path. Item 11 pinned the read to
`annotations.json`'s own `bootstrap_source` so a later bootstrap run — which always
gets its own `bootstrap-<timestamp>.json`
([`_new_bootstrap_path`](../../../blueprints/diagnostics.py)) — could not silently
misalign an in-progress annotation. Item 13 found that fix checked only that the
**path** existed, never that its **content** still matched: a run overwriting that
same path in place still resolved silently, producing a real fixture whose `jd.txt`
and `expected.json` came from different postings.

So when the annotation carries a `bootstrap_fingerprint` (see [[eval-harness]]), the
resolver re-fingerprints the pinned file and, on a mismatch, sets `stale_reason` and
returns `path=None` — it deliberately does **not** fall through to the newest
`bootstrap-*.json`, because silently substituting a different bootstrap is the exact
failure being guarded. `annotation_collate` turns that into an HTTP **409** before
writing anything, and a second **409** when
`ensure_anchor_covered_by_annotations` rejects the anchor
([`blueprints/diagnostics.py:annotation_collate`](../../../blueprints/diagnostics.py)).
Annotations predating the field are unaffected — the check is skipped, not
failed `[synthesis]`. `_resolve_bootstrap_path` survives as a thin
convenience wrapper that discards the reason, for the read-only callers.

The same routes surface F-14 labels so a JD's identity is visible at the moment it
matters: `annotation_fixtures` passes the bootstrap's `jd_labels` through to the
fixture dropdown; the collate response adds `anchor_jd_label` next to `anchor_jd`, and
the server log line names both; and the bootstrap SSE `done` event carries `jd_labels`
plus a company-preferred-title-fallback-`?` summary in its log line
([`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py)). Browser-side,
`jdLabelText` / `jdLabelsSummary` in
[`dashboard.html`](../../../dashboard/templates/dashboard.html) mirror
`_jd_label_display` — a deliberate duplication, since the payload crosses the wire as
JSON and cannot share the one Python rule. `jdLabelsSummary` refuses to single out a
posting when a bootstrap covers more than one, rendering a count + names instead:
there is no single "the" identity until an anchor is resolved at collate time
`[synthesis]`.

**Paid-run single-flight lock:** A global client-side `window.sartorRunLock`
([`dashboard.html`](../../../dashboard/templates/dashboard.html)) prevents
concurrent execution of the five paid-run buttons in `LOCK_BTN_IDS` (eval / tune /
bootstrap / grounding-score / collate-fixture) — while any one is in flight, the others
are disabled and a prominent `#runLockBanner` warns the user not to close the tab
`[synthesis]`. The
lock is not enforced server-side; `seed_export` (the deterministic corpus snapshot
feature in the Annotate tab) deliberately does not acquire it and may run in
parallel with paid runs `[synthesis]`.

**Run cancellation (disconnect-as-cancel):** Each SSE route polls its result queue
with a [`blueprints/diagnostics.py:_HEARTBEAT_INTERVAL_S`](../../../blueprints/diagnostics.py)
`5.0`-second timeout instead of blocking forever on `queue.get()` — one
`events.get(timeout=_HEARTBEAT_INTERVAL_S)` inside each of
[`annotation_score_grounding`](../../../blueprints/diagnostics.py),
[`annotation_bootstrap_stream`](../../../blueprints/diagnostics.py),
[`eval_run_stream`](../../../blueprints/diagnostics.py) and
[`tune_run_stream`](../../../blueprints/diagnostics.py) —
yielding a plain SSE comment line (`: heartbeat\n\n`) when the timeout expires.
Without periodic yields, a closed tab is invisible to Werkzeug until the blocking
worker call finishes — with the heartbeat, a disconnect is noticed within 5 seconds
`[synthesis]`. When the client closes the fetch or clicks the Cancel button (both fire
`GeneratorExit` into the generator), each SSE route wraps its stream body in
`try/except GeneratorExit` — one block per route, in the same four functions
(`annotation_score_grounding`, `annotation_bootstrap_stream`, `eval_run_stream`,
`tune_run_stream`) — to
capture the disconnect, set a `threading.Event(cancel_event)`, and pass
`cancel_check=cancel_event.is_set` into its evals-layer call
([`run_grounding_signals`](../../../blueprints/diagnostics.py),
[`run_pipeline_over_jd_texts`](../../../blueprints/diagnostics.py),
[`run_suite`](../../../blueprints/diagnostics.py) for both eval and tune) so worker
threads can short-circuit their loops on cancellation `[synthesis]`. The
`tune_run_stream` route has an additional optimization: its baseline-then-candidate
worker checks `if not cancel_event.is_set()` before starting the expensive
candidate run, so a disconnect during baseline skips the candidate entirely rather than
launching a second full paid run the client gave up on `[synthesis]`. Cancellation is
signalled by client disconnect rather than a separate `POST /cancel` route because
`app.run()` has never been `threaded=True` — a single request handler cannot service a
new cancel request while the original SSE connection is still open, so the connection
close is the only reliable signalling mechanism `[synthesis]`. The frontend
[`dashboard.html`](../../../dashboard/templates/dashboard.html) Cancel button shows
"Cancelling…" on click but offers no server confirmation — once the fetch aborts, the
client side cannot receive a message from a closed connection, making this an
accepted UX limitation rather than a defect `[synthesis]`.

Every annotation write is contained:
[`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py) routes apply
`_safe_username()` (from `web_infra`) + `secure_filename(slug)` +
`_within(path, current_app.config["ANNOTATION_ROOT"])` (= `evals/fixtures/real/`,
gitignored) — the canonical gate from [`AGENTS.md`](../../../AGENTS.md), here on
a localhost-only seam (D5). This module imports no `anthropic` itself — the paid
work is delegated to `evals.runner` / `evals.bootstrap` / the `web_infra`
client factory, so `blueprints/diagnostics.py` is **not** on the PX-08 egress
allowlist `[synthesis]`.

## Related

- [[code-module-map]] — where `dashboard/`, `blueprints/diagnostics.py`, and the eval tooling sit in the tree.
- [[eval-harness]] — `evals/runner.py`, whose `results/*.jsonl` this console reads.
- [[route-surface]] — the Flask routes, including the SSE eval/tune/annotation seam.
- [[frontend-wizard]] — the wizard help primitive this console ports.

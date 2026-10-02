# The diagnostics console — per-tab reference

> **Purpose:** what each tab of the diagnostics console (`/_dashboard`) reads, which routes
> it calls, what costs money, and what it writes to disk. Each tab has a flow diagram and a
> control table, keyed to the on-screen help the console shows.
> **Audience:** `dev` — contributors changing the console, its routes or the eval tooling
> behind it. The console is a developer surface: it runs only on `localhost`.
> **Authoritative for:** the tab → route → data mapping. The on-screen copy lives once, in
> `dashboard/templates/dashboard.html` (`_DASH_HELP`, `:1281-1729`); the tables below name
> the `_DASH_HELP` key for each control instead of copying its text. The eval harness itself
> is documented in [`evals/README.md`](../../evals/README.md).

## How the console is put together

Two blueprints serve it:

- **`dashboard_bp`** ([`dashboard/routes.py`](../../dashboard/routes.py)) is mounted at
  `/_dashboard` (`app.py:49`).
  - `index()` (`:1008`) renders the whole page server-side.
  - `run_detail()` (`:1083`) serves `GET /_dashboard/api/run/<run_id>`.
  - A `before_request` localhost guard (`:982-983`) covers both.
  - Every read is a file read: the LLM call log `logs/llm_calls.jsonl` (`:53`), the eval
    results `evals/results/*.jsonl` (`:54`, `:107`), and the baseline
    `evals/results/baseline_v1.json` (`:895`).
- **`diagnostics_bp`** ([`blueprints/diagnostics.py`](../../blueprints/diagnostics.py)) is
  registered without a prefix (`app.py:76`). It serves every route that costs money or
  writes a file. Each route checks `_is_localhost_request()` itself and returns 403
  otherwise. Paid work goes through `evals.runner.run_suite` in a worker thread and streams
  progress back as server-sent events.

Page-wide pieces that belong to no single tab:

- **The run lock** (`dashboard.html:2142-2179`, `window.sartorRunLock`).
  - While a paid or CPU-heavy run is live, it disables the six run buttons in
    `LOCK_BTN_IDS`, shows `#runLockBanner` and warns before the page unloads.
  - It is **browser-only**: nothing on the server stops a second run started from another
    tab or by `curl` (item 117).
  - The shared eval runner checks `acquire()`'s return value (`:2302`). The Tuning,
    bootstrap and grounding-score handlers call it and ignore the result
    (`:2438`, `:2842`, `:2915`; item 119).
- **The run-detail modal** (`#runDetailModal`) opens from a run id or error count on the
  Pipeline tab and fetches `/_dashboard/api/run/<id>` (`:2079`).
- **The assistant** (`#assistantModal`) is the same documentation assistant the main app
  has; see [architecture](architecture.md).
- **Help.** Every tab intro and most fields carry an (i) button. Its `data-help` key indexes
  `_DASH_HELP`, and the first visit to a tab opens that tab's entry once (`_DASH_HELP_ID`,
  `:1742`).

Paid calls are marked **PAID** below. The cost figures are the ones the console's own
`confirm()` dialogs show; this page doesn't restate them.

---

## Pipeline

Live telemetry for every LLM call the app makes. Help key: `dashPipeline`.

```mermaid
flowchart LR
  app["Main app<br/>(analyze, generate, …)"] -->|appends| log[("logs/llm_calls.jsonl")]
  log --> idx["dashboard_bp index()<br/>since / user / model filters"]
  idx --> tiles["Cost · Calls · Errors ·<br/>Trace · Latency tiles"]
  tiles -->|run id / error count| modal["Run-detail modal"]
  modal -->|GET| rd["/_dashboard/api/run/&lt;id&gt;"]
  rd --> log
```

| Control | Route (`path:line`) | Paid? | Run lock? | `_DASH_HELP` key |
|---|---|---|---|---|
| Since / user / model filter form | `GET /_dashboard/` (`dashboard/routes.py:1008`) | no | no | `dashFilters` |
| Cost, calls, errors, trace, latency tiles | rendered by `index()` | no | no | `dashTileCost`, `dashTileCalls`, `dashTileErrors`, `dashTileTrace`, `dashTileLatency`, `dashPercentiles` |
| Run id / error count → run detail | `GET /_dashboard/api/run/<run_id>` (`dashboard/routes.py:1083`) | no | no | — |

The tab is read-only and stays empty until the main app has made at least one call. Eval
runs log their calls under the user `eval:<fixture>` (`evals/runner.py:812`), so setting the
user filter to that value isolates eval traffic. The
Since filter currently fails on mixed naive/aware dates (item 112); `dashFilters` says so
on screen.

---

## Quality

Rubric grades (0–5) for generated résumés. Help key: `dashQuality`.

```mermaid
flowchart LR
  btn["Run eval<br/>(suite · subset · grounding signals)"] -->|"confirm(), then POST (SSE)"| er["/api/eval/run<br/>diagnostics.py:989"]
  er -->|"worker thread: run_suite — PAID"| res[("evals/results/&lt;timestamp&gt;.jsonl")]
  res --> idx["dashboard_bp index()"]
  base[("evals/results/baseline_v1.json")] --> idx
  idx --> tiles["Health · Pass rate · Score trend ·<br/>Heatmap · Failure modes · Pareto · Recent"]
```

| Control | Route (`path:line`) | Paid? | Run lock? | `_DASH_HELP` key |
|---|---|---|---|---|
| Suite / Subset / grounding-signals fields | — (inputs to Run eval) | — | — | `dashSuiteField`, `dashSubsetField`, `dashGroundingSignals` |
| Run eval | `POST /api/eval/run` (`blueprints/diagnostics.py:989`) | **PAID** (`confirm()` at `dashboard.html:2353`) | yes, checked (`:2302`) | `dashEvalRun` |
| Tiles | rendered by `index()` over every eval result | no | no | `dashTileHealth`, `dashTilePassRate`, `dashTileScoreTrend`, `dashTileHeatmap`, `dashTileFailureModes`, `dashTilePareto`, `dashTileRecent` |

Health against the baseline has three bands (`dashboard/routes.py:905-915`):
- **regressed:** delta below −0.5, the merge-block gate;
- **watch:** delta from −0.5 up to −0.3;
- **ok:** delta of −0.3 or above.

The overall badge shows the worst band present. A run started from the command line
(`python evals/runner.py …`) lands in the same results directory, so it shows here too. The page reloads when a console run finishes (`:2356`).

---

## Groundedness

The deterministic no-invention metric, read back from eval results. Help key:
`dashGroundedness`.

```mermaid
flowchart LR
  q["Any Quality or Tuning run"] -->|writes| res[("evals/results/*.jsonl<br/>grounding_overlap per result")]
  res --> idx["dashboard_bp index()<br/>_groundedness_trend ·<br/>_latest_groundedness_detail"]
  idx --> tiles["Grounded score · Flagged specifics"]
```

| Control | Route (`path:line`) | Paid? | Run lock? | `_DASH_HELP` key |
|---|---|---|---|---|
| Grounded-score and flagged-specifics tiles | rendered by `index()` (`dashboard/routes.py:1031-1032`) | no | no | `dashTileGroundedScore`, `dashTileFlagged` |

The tab has no controls of its own; it fills in from Quality runs. The metric is
rule-based, with no model call at scoring time. What it measures and its known limits are
in [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md).

---

## Tuning

A candidate-vs-baseline A/B of one system-prompt constant, using the prompt-override
primitive. Help key: `dashTuning`.

```mermaid
flowchart LR
  pick["Pick a persona constant<br/>(analyzer._BASE_SYSTEM_PROMPTS)"] --> edit["Edit candidate text"]
  edit -->|"confirm(), then POST (SSE)"| tr["/api/tune/run<br/>diagnostics.py:1159"]
  tr -->|"run_suite — baseline — PAID"| res[("evals/results/*.jsonl")]
  tr -->|"run_suite — candidate:&lt;hash&gt; — PAID"| res
  tr -->|"evals.tune deltas (no model call)"| delta["Per fixture × rubric delta"]
```

| Control | Route (`path:line`) | Paid? | Run lock? | `_DASH_HELP` key |
|---|---|---|---|---|
| Constant picker / candidate editor | — (inputs) | — | — | `dashTuneConstant`, `dashTuneCandidate` |
| Real-corpus seed (optional) | — (input) | — | — | `dashTuneSeed` |
| Run A/B | `POST /api/tune/run` (`blueprints/diagnostics.py:1159`) | **PAID**, two suites (`confirm()` at `dashboard.html:2436`) | acquired, result ignored (`:2438`) | `dashTuneRun` |
| Tuning-loop and baseline tiles | rendered by `index()` | no | no | `dashTileTuningLoop`, `dashTileBaseline` |

The candidate run stamps `prompt_version=candidate:<hash>`, so it never enters
score-over-time. Promotion is manual: nothing here edits `analyzer.py`. The console's cost
copy for this tab disagrees with the Quality tab's (item 134).

---

## Annotate

Produces and labels the `annotations.json` ground truth for grounding calibration.
Read-write, localhost-only. Help key: `dashAnnotate`. Everything it writes lands under
`ANNOTATION_ROOT` (`evals/fixtures/real/`, gitignored), per fixture slug, through
`_safe_username` + `_within` containment.

```mermaid
flowchart TB
  subgraph s1["① Produce"]
    bs["Bootstrap: paste JDs"] -->|"POST (SSE) — PAID, ~70 s/JD"| bsr["/api/annotation/bootstrap<br/>diagnostics.py:745"]
    ex["Export seed"] -->|POST, free| exr["/api/annotation/seed/export<br/>diagnostics.py:671"]
  end
  subgraph s2["② Pick"]
    list["/api/annotation/fixtures (GET)<br/>diagnostics.py:239"]
    load["/api/annotation/fixture/&lt;user&gt;/&lt;slug&gt; (GET)<br/>diagnostics.py:274"]
  end
  subgraph s3["③ Label"]
    save["Save (POST)<br/>diagnostics.py:322"]
    col["Collate (POST)<br/>diagnostics.py:372"]
    sc["Score grounding (POST, SSE, CPU only)<br/>diagnostics.py:475"]
    runfx["Run this fixture → /api/eval/run — PAID"]
  end
  bsr --> fx[("ANNOTATION_ROOT/&lt;slug&gt;/<br/>bootstrap.json · seed.json · jds/")]
  exr --> fx
  fx --> list --> load
  save --> ann[("annotations.json")]
  col --> out[("expected.json · improvement_brief.md · jd.txt")]
  sc --> ann
  col --> runfx
```

| Control | Route (`path:line`) | Paid? | Run lock? | `_DASH_HELP` key |
|---|---|---|---|---|
| ① Bootstrap | `POST /api/annotation/bootstrap` (`blueprints/diagnostics.py:745`) | **PAID**, no `confirm()` | acquired, result ignored (`dashboard.html:2842`) | `dashBootstrapRun`, `dashFixtureSlug` |
| ① Export seed | `POST /api/annotation/seed/export` (`:671`) | no | no | — |
| ② Fixture picker | `GET /api/annotation/fixtures` (`:239`), `GET /api/annotation/fixture/<user>/<slug>` (`:274`) | no | no | `dashFixturePicker` |
| ③ Verdict fields | — (in-browser; drafts auto-saved to `localStorage`) | — | — | `dashVerdicts`, `dashAnnFields` |
| ③ Save | `POST /api/annotation/fixture/<user>/<slug>` (`:322`) | no | no | — |
| ③ Collate | `POST …/collate` (`:372`) | no | governed button | `dashCollate` |
| ③ Score grounding | `POST …/score` (`:475`) | no (CPU scorers; needs the `[eval-grounding]` extras) | acquired, result ignored (`dashboard.html:2915`) | `dashAnnScore` |
| ③ Run this fixture (built after Collate) | `POST /api/eval/run` with `suite: "real"` | **PAID** (`confirm()` at `dashboard.html:2787`) | yes, via the shared runner | `dashCollateRun` |

Save validates with the same fail-closed contract the CLI uses
(`evals.annotation.validate_annotations`), so an incomplete doc is rejected rather than
written. Collate is deterministic and makes no model call.

---

## When the console changes

- A new tab or control gets a `_DASH_HELP` entry first, with a `learnMore` target: this
  page's slug and the tab's section, such as `dev-diagnostics#quality`.
  `tests/test_help_learn_more.py` fails on an entry without one, or on a target that
  doesn't resolve. Then add the control to the tab's table here, with its route and whether
  it is paid or locked.
- A new paid route belongs on `diagnostics_bp`, with the localhost check and, for the
  button, a `confirm()` plus a run-lock `acquire()` whose result is checked.
- The diagrams here are hand-written Mermaid. The docs-site workflow checks that each one
  renders (`scripts/check_docs_site_mermaid.py`). Mermaid ends a statement at `;`, so keep
  semicolons out of message and branch labels.

# E2E run-health review — 2026-07 round 2 (item #14)

> **Purpose:** a read-only witness review of the owner's 2026-07 end-to-end
> diagnostics/eval **run health** — gathered from the separate e2e evidence clone,
> not the working repo. Companion to
> [`2026-07-ux-round2-findings.md`](2026-07-ux-round2-findings.md) (app-side round-2
> feedback) and [`2026-07-diagnostics-round2-findings.md`](2026-07-diagnostics-round2-findings.md)
> (the 17-item diagnostics-page triage — this review is that batch's item **#14**,
> which was deliberately excluded from the code triage as read-only run-evidence).
> **Audience:** v1.0.9 planners (the UX Cohesion Epic + diagnostics-DX work).
> **Status:** every finding routes to **v1.0.9** — **none blocks the v1.0.8 tag**
> (scores are healthy and above floor). Evidence gathered read-only; **nothing was
> written to the e2e clone.**

## Scope + method

Read-only pass over the owner's e2e evidence clone (`evals/results/`,
`logs/llm_calls.jsonl`, `evals/fixtures/real/robert-bootstrap/`), 2026-07-09. The
question item #14 asked: is the diagnostics/eval run infrastructure healthy, did the
runs complete properly, and does anything warrant scheduled work?

## (a) Run inventory — `evals/results/*.jsonl`

| File | Size | Records | Status | Fixtures | Rubric | prompt_version |
|---|---|---|---|---|---|---|
| `20260709_004634Z` | 9.3 KB | 2 | partial (1 fixture) | data-scientist-junior | grounding | `2026-07-06.3` |
| `20260709_014042Z` | **0 B** | **0** | **FAILED / empty** | — | — | — |
| `20260709_192457Z` | 32.2 KB | 6 | ok | 3 fixtures | grounding | `2026-07-08.4` |
| `20260709_202426Z` | 17.6 KB | 6 | ok | 3 fixtures | grounding | `2026-07-08.4` |
| `20260709_202853Z` | 19.2 KB | 6 | ok | 3 fixtures | grounding | `candidate:d8c8830…` |

- The **0-byte `20260709_014042Z.jsonl` is a confirmed silent failure** — zero bytes,
  zero records, **no error artifact emitted**. A run that dies without leaving an
  error record is precisely the silent-failure smell the diagnostics-DX work should
  guard against.
- All valid runs graded the **grounding rubric only** (each fixture also emits one
  `eval_composite` rollup with `status=None`). The full four-rubric suite
  (ats_format / keyword_coverage / tone / distinctiveness) was **not exercised** in
  this window.
- The last two runs are a back-to-back **A/B pair** (baseline `2026-07-08.4` vs
  `candidate:d8c8830…`) — the prompt-override primitive working as designed, candidate
  telemetry correctly quarantined under `candidate:<hash>`.
- **Scores are healthy: 4.2–4.8, every fixture ≥ 4.0.** One transient dip
  (`sre-mid-level` −0.44 vs baseline in the 19:24 run) **recovered** to −0.04 in both
  later runs. `failed_rules` are minor judge annotations (verb_overreach,
  scope_inflation, jd_pandering), not run failures. **No quality regression that would
  block a tag.**

## (b) Timing + cost — `logs/llm_calls.jsonl`

- 223 records, 0 malformed, spanning **~10 days** (2026-06-29 → 2026-07-09) —
  **cumulative across the clone's whole history, not scoped to one run** (per-day
  peak Jul-09 = 86 calls).
- Models: `claude-haiku-4-5` ×107, `claude-sonnet-5` ×100, retired `claude-sonnet-4-6`
  ×16 (Jun30–Jul02 only; the Jul-09 window is sonnet-5 + haiku-4-5 exclusively).
- Latency: median **10.5 s** / mean 19.3 s / max 87.8 s. 13 calls > 60 s, concentrated
  in the retired sonnet-4-6 `generate`/`analyze_synthesis`; recent sonnet-5 `generate`
  runs ~66–82 s — slow but expected for the heavy synthesis pass, not anomalous.
- **1 transient error** (`iterate_clarify`, sonnet-5, 0 output tokens) out of 223 =
  **99.6 % ok**; the retry path (`draft_summary_retry`, `analyze_extraction_retry`, …)
  is exercised and succeeding.
- **Cost:** the authoritative per-run figure is the result files' `cost_usd` —
  **$1.264 total** across the four non-empty runs (empty run = $0). (A list-price
  heuristic over the whole 10-day `llm_calls.jsonl` ≈ $6.57, but that spans far more
  than this eval window and carries no cost field of its own.)

## (c) Grounding-persistence gap — the headline

`robert-bootstrap/annotations.json` — 53 items (32 bullets + 21 skills):

| Field | Populated | Null |
|---|---|---|
| `nli_entailment_score` | 0 | **53** |
| `nli_contradiction_flag` | 0 | 53 |
| `minicheck_grounding_score` | 0 | **53** |
| `verdict` | **53** | 0 |
| `should_omit` | **53** | 0 |

The human verdict layer persisted fully (bullets keep 28 / fix 4; skills omit 12 /
keep 9), but **both automated grounding signals are 100 % null.** Crucially, the
grounding machinery *works* — the signals ARE populated in the eval **result**
records — so this is a **fixture-level annotate-flow persistence gap, not a broken
scorer.** It is the same failure surface as diagnostics **#9** (client-only `state.doc`
lost on refresh): the grounding scores the owner watched compute
("Scoring 32 bullet clusters…") never wrote back to disk. **This is the concrete
repair behind the owner's "re-run grounding after the repairs" directive.**

## (d) The `jd.txt` finding (#15, corrected framing)

Earlier framing was "the fixture has no JD." **Corrected: the JD data is present** —
it lives at `robert-bootstrap/jds/Faros_-_Product_Manager_AI_Native_Initiatives.txt`.
What's absent is a `jd.txt` at the fixture root. So #15 is a **naming/layout
convention mismatch** (`jds/<descriptive>.txt` vs an expected root `jd.txt`), and any
consumer hardcoding `robert-bootstrap/jd.txt` (the "Run this fixture" button, the
printed CLI line) breaks — but **no data was lost.** Root cause + fix in the
diagnostics findings doc (#15).

## Findings → v1.0.9 (none blocks the v1.0.8 tag)

1. **Grounding-signal persistence (highest value)** — re-run `grounding_signals`
   over the fixture and persist NLI + MiniCheck back into `annotations.json`, or fix
   the annotate-flow persistence seam. Without it this fixture can't back automated
   grounding-regression checks. Pairs with diagnostics **#9** and the owner's
   grounding re-run.
2. **0-byte-run guard** — a run that emits an empty file with no error record should
   fail loudly or be cleaned up. Folds into the eval-pipeline data-safety line.
3. **Full-rubric coverage** — schedule one full four-rubric pass so
   ats_format / keyword / tone / distinctiveness are graded again (this window was
   grounding-only).

**Minor / no action:** the single transient `iterate_clarify` error (99.6 % ok), the
> 60 s latencies (retired model), and the `jd.txt` naming mismatch (fix only where a
consumer hardcodes the path — tracked as #15).

## Bottom line

Run health is **broadly green** — stable, above-floor scores, one recovered dip, one
transient API error, no corruption. The three follow-ups above are low-effort and
route cleanly into v1.0.9; **the v1.0.8 tag is not gated on any of them.**

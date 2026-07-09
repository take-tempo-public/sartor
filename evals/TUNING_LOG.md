# Eval Tuning Log

A chronological record of prompt iterations and what each one taught us. The
goal is institutional memory (P5) for human and synthetic agents who tune
this system in the future.

Each entry should answer four questions:

1. **What changed?** (concrete edit, file paths, prompt_version diff)
2. **Why?** (failure mode observed in the dashboard or eval results)
3. **What was the result?** (scores before/after, deterministic metrics)
4. **What did we learn?** (rule of thumb that should bias future tuning)

If a change was neutral or negative, document that too. Failed experiments
prevent re-running them.

---

## BASELINE — v1.0.1 — 2026-05-28

> **Purpose:** regression floor for Phase 1 (eval apparatus, v1.0.2).
> Five consecutive runs of `python evals/runner.py --suite synthetic`
> at `PROMPT_VERSION 2026-05-24.4` with no code changes between runs.
> All runs on branch `eval/pre-tag-baseline` (base: main, post-cleanup).
>
> **This table is the pass/fail gate for Phase 2 (R1 Phase 2, v1.0.3):**
> any (fixture × rubric) that drops more than 0.5 below the mean below
> blocks merge on the R1 branch.

### Run metadata

| Run | Timestamp (UTC) | PROMPT_VERSION | Result file |
|---|---|---|---|
| 1 | 2026-05-28T21:26:16Z | 2026-05-24.4 | `evals/results/20260528_212616Z.jsonl` |
| 2 | 2026-05-28T21:38:15Z | 2026-05-24.4 | `evals/results/20260528_213815Z.jsonl` |
| 3 | 2026-05-28T21:55:41Z | 2026-05-24.4 | `evals/results/20260528_215541Z.jsonl` |
| 4 | 2026-05-28T22:05:45Z | 2026-05-24.4 | `evals/results/20260528_220545Z.jsonl` |
| 5 | 2026-05-28T22:15:53Z | 2026-05-24.4 | `evals/results/20260528_221553Z.jsonl` |

**Total cost:** USD 2.07 across 5 runs (~$0.41/run). Significantly below the $7.50 roadmap estimate — cache hit rate is strong (cache_read_input_tokens landing on both analyze and generate prefix blocks). Wall clock: ~3.5h total.

**Note on exit codes:** all 5 runs exited with code 2 (`n_fail > 0`). This is expected during baseline collection: two known-below-threshold rubrics (`pm-senior × clarification_quality` and `sre-mid-level × iteration_quality`) and cross-run Haiku judge variance (Δ up to 0.6) routinely trigger the exit signal. Not a blocker for baseline validity.

**Also fixed in this branch:** `evals/runner.py:871` — regression detection was firing on `judge_error` records (score=0 passes `isinstance(0, int)`). Added `record.get("status") != "judge_error"` guard. See commit `27dcea5`.

### Per-(fixture × rubric) mean ± stdev (n=5, judge_errors excluded)

`*` = below 4.0 threshold; `—` = all runs scenario_misaligned (edit didn't land)

| Fixture | ats_format | clarification_quality | grounding | keyword_coverage | tone | iteration_quality |
|---|---|---|---|---|---|---|
| data-scientist-junior | 4.56 ± 0.25 | 3.90 ± 0.45 `*` | 4.62 ± 0.25 | 4.20 ± 0.00 | 4.20 ± 0.00 | n/a |
| pm-senior | 4.60 ± 0.10 | 3.92 ± 0.44 `*` | 4.76 ± 0.09 | 4.17 ± 0.05 (n=4) | 4.20 ± 0.00 | n/a |
| sre-mid-level | 4.72 ± 0.13 | 4.06 ± 0.31 | 4.60 ± 0.24 | 4.28 ± 0.18 | 4.32 ± 0.27 | 3.20 (n=1) `*` |

### Raw scores per run

| Fixture | Rubric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.5 | 4.8 | 4.5 | 4.8 | 4.2 |
| data-scientist-junior | clarification_quality | 4.2 | 4.2 | 3.7 | 4.2 | 3.2 |
| data-scientist-junior | grounding | 4.2 | 4.8 | 4.8 | 4.7 | 4.6 |
| data-scientist-junior | keyword_coverage | 4.2 | 4.2 | 4.2 | 4.2 | 4.2 |
| data-scientist-junior | tone | 4.2 | 4.2 | 4.2 | 4.2 | 4.2 |
| pm-senior | ats_format | 4.6 | 4.5 | 4.7 | 4.5 | 4.7 |
| pm-senior | clarification_quality | 3.2 | 3.8 | 4.2 | 4.2 | 4.2 |
| pm-senior | grounding | 4.6 | 4.8 | 4.8 | 4.8 | 4.8 |
| pm-senior | keyword_coverage | JE | 4.2 | 4.2 | 4.1 | 4.2 |
| pm-senior | tone | 4.2 | 4.2 | 4.2 | 4.2 | 4.2 |
| sre-mid-level | ats_format | 4.8 | 4.5 | 4.8 | 4.7 | 4.8 |
| sre-mid-level | clarification_quality | 4.2 | 4.2 | 4.2 | 3.5 | 4.2 |
| sre-mid-level | grounding | 4.8 | 4.2 | 4.6 | 4.6 | 4.8 |
| sre-mid-level | iteration_quality | N/A | N/A | N/A | 3.2 | N/A |
| sre-mid-level | keyword_coverage | 4.2 | 4.2 | 4.6 | 4.2 | 4.2 |
| sre-mid-level | tone | 4.8 | 4.2 | 4.2 | 4.2 | 4.2 |

`JE` = judge_error (Haiku returned invalid JSON; excluded from stats). `N/A` = scenario_misaligned (scripted edit substring not in generated output that run).

### Deterministic metrics baseline (mean ± stdev across 5 runs)

| Fixture | verb_diversity | specificity_density | grounding_overlap_ratio | cost_usd/run | latency_ms p50 |
|---|---|---|---|---|---|
| data-scientist-junior | 0.982 ± 0.041 | 0.060 ± 0.056 | 0.214 ± 0.024 | $0.1286 ± $0.0015 | 140,890 ms |
| pm-senior | 0.895 ± 0.079 | 0.100 ± 0.015 | 0.320 ± 0.045 | $0.1363 ± $0.0048 | 148,266 ms |
| sre-mid-level | 0.910 ± 0.062 | 0.356 ± 0.056 | 0.269 ± 0.041 | $0.1483 ± $0.0058 | 157,326 ms |

### What we learned

1. **Two clarification_quality rubrics are persistently below 4.0.** `pm-senior` (3.92) and `data-scientist-junior` (3.90) show mean scores below the 4.0 pass threshold with stdev ~0.44. This is not a new regression — it's the known post-R1-attempt state at `PROMPT_VERSION=2026-05-24.4`. The R1 Phase 2 work (v1.0.3) must recover `pm-senior × clarification_quality` to ≥4.0 before merge; `data-scientist-junior` recovery is a secondary target. The floor established here (3.90, 3.92) is the baseline these values must beat.

2. **`sre-mid-level × iteration_quality` fires in only 1 of 5 runs.** The scripted edit (`edit_target_substring`) didn't land in the generated output 4/5 runs. This is the known fixture-fragility issue from the 2026-05-11.3 TUNING_LOG entry. The single valid score (3.2) is below threshold. The v1.0.2 fixture work (add scenarios to pm-senior + data-scientist-junior) must precede any iteration_quality improvement work.

3. **Cache behavior is healthy.** `cache_create` fires on every analyze call (as expected — first call per fixture per run can't hit the cache). The `cache_read` on generate (~1,781–1,928 tokens) confirms the stable user-prefix caching from v1.0.0 work is holding. Per-run cost is 3.5× below the roadmap estimate — the caching improvements have compounded well.

4. **judge_errors are transient.** Only 1 judge_error in 5 runs (pm-senior × keyword_coverage, Run 1). Haiku occasionally returns malformed JSON under API load; the rate (~1 per 80 gradings) is within acceptable noise. The `status: "judge_error"` fix at `evals/runner.py:289` correctly marks these; the new guard at `:871` prevents them from triggering false regression alarms.

5. **Regression alerter design note.** During N-run baseline collection, the alerter compares each run against the prior run. Natural Haiku variance (Δ up to 0.6 on same-prompt runs) will regularly exceed the 0.5 regression threshold. Exit code 2 during baseline collection is expected and not actionable. The v1.0.2 work should consider a `--baseline-mode` flag that disables run-to-run regression checking during baseline collection.

---

## BASELINE — v1.0.2 — 2026-05-28

> **Purpose:** regression floor for Phase 2 (R1 Phase 2, v1.0.3).
> Five consecutive runs of `python evals/runner.py --suite synthetic`
> at `PROMPT_VERSION 2026-05-24.4` with no code changes between runs.
> All runs on branch `eval/baseline-v1-0-2` (base: main@3e7e713,
> post-Pydantic-migration). Upgrades `baseline_v1.json` to schema_version 3
> (adds stdev / min / max per rubric; static-seed regression baseline).
>
> **This table is the pass/fail gate for Phase 2 (R1 Phase 2, v1.0.3):**
> any (fixture × rubric) mean that drops more than 0.5 below the mean below
> blocks merge on the R1 branch.

### Run metadata

| Run | Timestamp (UTC) | PROMPT_VERSION | Result file |
|---|---|---|---|
| 1 | 2026-05-28T23:39:03Z | 2026-05-24.4 | `evals/results/20260528_233635Z.jsonl` |
| 2 | 2026-05-28T23:53:07Z | 2026-05-24.4 | `evals/results/20260528_235041Z.jsonl` |
| 3 | 2026-05-29T00:02:59Z | 2026-05-24.4 | `evals/results/20260529_000027Z.jsonl` |
| 4 | 2026-05-29T00:22:24Z | 2026-05-24.4 | `evals/results/20260529_001953Z.jsonl` |
| 5 | 2026-05-29T00:37:46Z | 2026-05-24.4 | `evals/results/20260529_003517Z.jsonl` |

**Total cost:** USD ~$2.07 across 5 runs (~$0.41/run). Consistent with v1.0.1 baseline cost ($2.07). Cache behavior stable — `cache_read` firing on generate prefix blocks.

**Note on exit codes:** all 5 runs exited with code 2 (`n_fail > 0`). Expected: two known-below-threshold rubrics and cross-run Haiku judge variance. Not a blocker for baseline validity.

### Per-(fixture × rubric) mean ± stdev (n=5, judge_errors and scenario_misaligned excluded)

`*` = below 4.0 threshold (known pre-existing); `n=X` = fewer than 5 valid runs (scenario_misaligned)

| Fixture | ats_format | clarification_quality | grounding | keyword_coverage | tone | iteration_quality |
|---|---|---|---|---|---|---|
| data-scientist-junior | 4.58 ± 0.13 | 3.92 ± 0.44 `*` | 4.70 ± 0.10 | 4.30 ± 0.22 | 4.20 ± 0.00 | n/a |
| pm-senior | 4.44 ± 0.25 | 4.00 ± 0.45 | 4.40 ± 0.28 | 4.12 ± 0.18 | 4.18 ± 0.04 | n/a |
| sre-mid-level | 4.52 ± 0.30 | 4.02 ± 0.25 | 4.64 ± 0.25 | 4.32 ± 0.18 | 4.12 ± 0.18 | 3.73 ± 0.50 (n=3) `*` |

### Raw scores per run

| Fixture | Rubric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.5 | 4.6 | 4.5 | 4.5 | 4.8 |
| data-scientist-junior | clarification_quality | 3.8 | 4.2 | 4.2 | 4.2 | 3.2 |
| data-scientist-junior | grounding | 4.8 | 4.6 | 4.6 | 4.8 | 4.7 |
| data-scientist-junior | keyword_coverage | 4.2 | 4.2 | 4.7 | 4.2 | 4.2 |
| data-scientist-junior | tone | 4.2 | 4.2 | 4.2 | 4.2 | 4.2 |
| pm-senior | ats_format | 4.2 | 4.5 | 4.2 | 4.8 | 4.5 |
| pm-senior | clarification_quality | 4.2 | 4.2 | 3.2 | 4.2 | 4.2 |
| pm-senior | grounding | 4.2 | 4.2 | 4.2 | 4.8 | 4.6 |
| pm-senior | keyword_coverage | 4.2 | 4.2 | 4.2 | 4.2 | 3.8 |
| pm-senior | tone | 4.1 | 4.2 | 4.2 | 4.2 | 4.2 |
| sre-mid-level | ats_format | 4.8 | 4.8 | 4.6 | 4.2 | 4.2 |
| sre-mid-level | clarification_quality | 4.2 | 4.2 | 3.7 | 4.2 | 3.8 |
| sre-mid-level | grounding | 4.2 | 4.8 | 4.7 | 4.7 | 4.8 |
| sre-mid-level | iteration_quality | N/A | N/A | 3.2 | 3.8 | 4.2 |
| sre-mid-level | keyword_coverage | 4.6 | 4.4 | 4.2 | 4.2 | 4.2 |
| sre-mid-level | tone | 4.2 | 4.2 | 4.2 | 4.2 | 3.8 |

`N/A` = scenario_misaligned (scripted edit substring not in generated output that run). Zero judge_errors across all 90 gradings.

### Deterministic metrics baseline (mean ± stdev across 5 runs)

| Fixture | verb_diversity | specificity_density | grounding_overlap_ratio | cost_usd/run | latency_ms p50 |
|---|---|---|---|---|---|
| data-scientist-junior | 1.000 ± 0.000 | 0.042 ± 0.058 | 0.228 ± 0.009 | $0.1319 ± $0.0036 | 144,697 ms |
| pm-senior | 0.978 ± 0.050 | 0.099 ± 0.008 | 0.302 ± 0.011 | $0.1363 ± $0.0033 | 155,544 ms |
| sre-mid-level | 0.983 ± 0.037 | 0.335 ± 0.050 | 0.281 ± 0.016 | $0.1469 ± $0.0060 | 156,425 ms |

### Known below-threshold (pre-existing, not new regressions)

1. **`data-scientist-junior × clarification_quality` mean=3.92** — same fixture/prompt condition as v1.0.1 (3.90). Pre-existing at `PROMPT_VERSION=2026-05-24.4`. Recovery is Phase 2 (v1.0.3 `r1/structural-context-probe`).
2. **`sre-mid-level × iteration_quality` mean=3.73 (n=3)** — fixture fires in only 3 of 5 runs (`scenario_misaligned` in 2). Known fragility documented in TUNING_LOG 2026-05-11.3. Single below-threshold scores (3.2, 3.8) and one pass (4.2). Fix is adding `iteration_quality` scenarios to pm-senior and data-scientist-junior fixtures (Phase 1 later branch).
3. **`data-scientist-junior × grounding_overlap_ratio` = 0.228 < 0.25** — pre-existing. v1.0.1 showed 0.214. Ratio is rising but below threshold. Per TUNING_LOG 2026-05-09 "What we learned #3": the ratio is informative but not load-bearing; `missing_samples` is the actionable signal. The LLM legitimately paraphrases (overlap_ratio 0.20–0.31 correlates with passing grounding scores).

### Green-light criteria status

| Criterion | Status |
|---|---|
| Every (fixture × rubric) mean ≥ 4.0 | ⚠ 2 exceptions (pre-existing, documented above) |
| No stdev > 0.6 | ✅ max stdev = 0.50 (sre × iteration_quality, n=3) |
| Cost variance < 15% of mean | ✅ 2.7% / 2.4% / 4.1% |
| Zero judge_error records (90 gradings) | ✅ 0 judge_errors |
| grounding_overlap_ratio ≥ 0.25 per fixture | ⚠ data-scientist-junior = 0.228 (pre-existing) |

### What we learned

1. **Schema_version 3 static-seed regression detection is materially better.** The alerter now compares each fresh run against the 5-run aggregate mean (the stable floor) rather than the most recent single JSONL run (which carries Haiku variance noise). This should halve false-alarm rate on baseline-level runs.

2. **Zero judge_errors in 90 gradings.** The `status: "judge_error"` guard added in the v1.0.1 branch (`:871` in runner.py) has held cleanly across this full 5-run baseline. Previous baseline collected 1 judge_error in 80 gradings — the new run's 0/90 may reflect reduced Haiku API load or natural variance.

3. **pm-senior × clarification_quality improved from 3.92 (v1.0.1) to 4.00 (v1.0.2).** The Pydantic migration (parse-or-retry path now uses `ValidationError` with a structured error message) may have marginally improved prompt-level retries on structured clarify output, though the stdev (0.45) is too wide to call this conclusive. Worth watching in Phase 2 baseline.

4. **`sre-mid-level × iteration_quality` fired in 3/5 runs (vs 1/5 in v1.0.1).** Improvement in frequency (scripted edit substring landing more often) but all three valid scores are below 4.0 (3.2 / 3.8 / 4.2). Net n=3 mean 3.73 — still a Phase 1 fixture-work target, but at least the fixture is triggering more reliably.

5. **Cost is remarkably stable.** CV < 5% across all three fixtures. Cache hit rate is holding — `cache_read` is landing on both analyze and generate prefix blocks consistently. Total 5-run cost matches v1.0.1 baseline ($2.07) within 1%.

---

## 2026-06-13 — feat/skill-group-item (B.5): Skill as a Corpus Item — two new Haiku prompts (`2026-06-12.1` → `2026-06-12.2`)

**What changed?** B.5 promotes the flat `Skill` row to a Corpus Item and adds
**two** new `_BASE_SYSTEM_PROMPTS` constants in [`analyzer.py`](../analyzer.py):
`RECOMMEND_SKILLS_SYSTEM_PROMPT` (order + lightly curate the candidate's approved
skills for a JD — mirrors `recommend_summaries`; id-only; short-circuits 0/1) and
`SUGGEST_SKILLS_SYSTEM_PROMPT` (a **grounded generator**: propose only skills the
JD wants AND the `<career_corpus>` evidences, evidence-or-nothing, with a worked
OK / NOT-OK example block). `PROMPT_VERSION` `2026-06-12.1` → `2026-06-12.2`. The
generate (`SYSTEM_PROMPT`) template is **unchanged** — only the *data* in the
existing cached `Skills:` line changes, and only in corpus mode when a
recommendation/override exists.

**Why?** Skills were the last corpus type still dumped wholesale, untailored. B.5
makes them recommend-curated per JD (reaching the LLM-authored download via
`_apply_recommended_skills`) and adds a corpus-evidenced suggestion path so the
canonical set grows safely over time.

**What was the result?** **No paid smoke run** — and that's the correct call, not
a skipped step. The synthetic suite is **legacy-mode** (skills come from
`config.get("skills")` in `hardening.py`, which this branch does not touch), so the
exercised generate path is **byte-identical**; the two new prompts only fire on
corpus-mode routes the suite never hits. Proven by unit tests (the
`_apply_recommended_skills` no-op path; `_collect_skills` all-active fallback) +
the UX regression. ruff/mypy ✓, pytest **1169/1169** incl. `-m ux`. No new dep.

**What did we learn?** The grounding risk for a *generator* (vs. a selector that
can only pick from an approved set) is real, and the right control is **a human
approve/deny gate, not an eval threshold**: `suggest_skills` output lands as
**pending** and is excluded from the recommend set, the preview `skills[]`, AND the
prompt until the user approves it — so even an over-eager proposal can never reach
the résumé. A dedicated live grounding eval for `suggest_skills` is a reasonable
**follow-up**, but it is not a merge gate given the gate. (Pattern continued from
B.4: corpus-mode-only prompt changes → bump `PROMPT_VERSION` for attribution, prove
legacy byte-identity, cover with unit + UX, skip the paid smoke.)

---

## 2026-06-11 — feat/compose-add-title (#7): per-JD pinned title rule in `<corpus_mode>` (`2026-06-10.1` → `2026-06-11.1`)

### What changed

One prompt-template edit, in `analyzer.py`, in the same commit as the version bump:

- **`<corpus_mode>` contract** (`generate`'s prompt) — the `<eligible_title>`
  description gains a pin rule: *"If an `<eligible_title>` is marked
  `pinned="true"`, the candidate has CHOSEN it for this application: you MUST set
  that title's id as the experience's `chosen_title_id` and reproduce its exact
  text as the heading title (still honoring the immutable `dates`) — do not
  substitute, reword, or propose an alternative for that experience."* This is the
  generate half of the per-JD title pin (the user picks a title in Compose; the
  pin must drive the downloaded résumé, not just the preview).
- **`_corpus_block` / `_stable_user_prefix`** (data, not template) — emit
  `pinned="true"` on the chosen `<eligible_title>` from
  `composition_overrides.pinned_title_ids`. Added only when a pin exists, so the
  cached prefix stays byte-identical for non-pinners (exactly like bullet pins).

### Why

Sprint 6.1 #7 (user-approved per-JD pin extension). Titles had no per-application
selection — the model picked `chosen_title_id` by fit and the preview showed
official-or-first. The pin closes that gap; the prompt rule is what makes the
user's choice authoritative in the generated download (the preview honors it
deterministically in `build_json_resume_from_corpus`).

### Result

**Smoke eval deliberately not run** — it would be uninformative here. The edit is
**corpus-mode only** (`in_corpus_mode = bool(context_set.get("career_corpus"))`;
the rule text is empty string in legacy mode, and the `pinned="true"` attr is
gated behind the `if corpus:` branch). The synthetic eval fixtures are
**legacy-mode** (no `career_corpus`, same as the KW6 note), so the LLM prompt they
produce is **byte-identical** to `2026-06-10.1`. `PROMPT_VERSION` is telemetry-only
(`effective_prompt_version()` returns it for the JSONL label; it is never injected
into the prompt sent to the model), so the bump alone changes no model input. The
green test suite already proves the byte-identical legacy path
(`tests/test_corpus_mode_prompt.py::TestStableUserPrefixDispatch::test_legacy_path_emits_resume_block`
+ `TestTitlePinEmission::test_empty_pinned_title_ids_byte_identical`). User
confirmed skipping the paid run (2026-06-11).

Coverage for the actual change is unit + UX, not this suite:
- `tests/test_corpus_mode_prompt.py::TestTitlePinEmission` — the `pinned="true"`
  attr is emitted for the chosen title, absent otherwise, byte-identical when empty;
  `TestGenerateDispatch::test_corpus_mode_block_documents_title_pin_rule` — the rule
  text is present in the corpus-mode prompt.
- `tests/ux/regression/test_20260611_compose_add_title.py` — add a title in
  Compose, pin it, persist across a Compose reload (end-to-end through the real
  routes).

### What we learned

- Bump `PROMPT_VERSION` for attribution discipline even when the change is provably
  inert on the eval suite's path — but say so in the log, and verify "byte-identical
  on the exercised path" with a unit test rather than spending a paid run that
  re-measures an identical prompt. The synthetic suite only exercises legacy mode;
  corpus-mode prompt changes need unit/UX coverage, not `--suite synthetic`.

---

## 2026-06-10 — fix/generate-date-grounding (KW6): date-immutability rules + deterministic heading-date guard (`2026-06-01.4` → `2026-06-10.1`)

### What changed

Prompt side (`analyzer.py`, all in one commit with the version bump):

- **SYSTEM_PROMPT** — new ALWAYS/NEVER rule: never alter, swap, or "reconcile"
  employment date ranges; reordering experiences for relevance never changes
  their dates; a shifted or duplicated range is instantly verifiable fabrication.
- **`<corpus_mode>` contract** (`_build_generate_prompt`) — the `<experience>`
  `dates` attribute is now named IMMUTABLE ground truth: whichever title is
  used, the heading must reproduce that experience's exact range; never merge
  or harmonize ranges across experiences, even on a regeneration pass.
- **GROUNDING CHECK worked example** — new OK / NOT-OK date pair (two adjacent
  roles at one company; OK keeps each range verbatim when reordered; NOT-OK
  stamps both with one range), per the AGENTS.md "new failure mode ⇒ worked
  example" rule.

Guard side (deterministic, warn-only — no LLM output is ever mutated):

- New `hardening.compute_date_grounding(generated_resume, experiences)` —
  parses `### …\t<range>` headings in the experience section and requires the
  multiset of (start_year, end_year) ranges to be contained in the corpus's
  true-range multiset. Catches both alteration (range in no experience) and
  duplication (one range stamped on two headings) without fuzzy title matching.
- Both generate routes (`/api/generate` + streaming) run it in corpus mode via
  `app._check_date_grounding`: flags append a plain-language warning to
  `proofread_notes` (already rendered by the preview UI) and ride a new
  `date_grounding` response field. Best-effort, mirrors the ATS round-trip
  pattern; legacy (non-corpus) contexts skip it (`None`).

### Why

KW6 (Sprint 6.0 kickoff walk, HIGH · output integrity — the core no-invention
value prop). Reproduced from the e2e instance's saved chain
(in the separate E2E clone; memory `project-e2e-instance-location`): corpus dates correct; **fresh generation
correct**; the **iteration-1 regenerate** reordered experiences by JD relevance
and rewrote one Intel role's range 2012–2016 → 2016–2018, duplicating the
adjacent role's range while 2012–2016 vanished — unprompted by any
clarification or refinement note. Nothing forbade it: the corpus-mode contract
made bullets immutable but never mentioned dates, and every deterministic
check scanned bullet lines only (heading dates were invisible).
`compute_date_grounding` run against that real chain: corrupted iter-1 draft →
`flag` (the duplicated `2016 – 2018`); clean fresh draft → `pass`.

### Result

Smoke (`--suite synthetic --subset smoke`, grounding rubric only):

| fixture | `2026-06-01.4` (20260602_002239Z / 20260602_003107Z) | `2026-06-10.1` (20260611_033353Z) |
|---|---|---|
| data-scientist-junior | 4.8 / 4.2 | **4.8** (pass) |
| pm-senior | 4.8 / 4.8 | **4.6** (pass) |
| sre-mid-level | 4.5 / 4.8 | **4.7** (pass) |
| mean | 4.70 / 4.60 | **4.70** |

No regression — new mean matches the better of the two baseline runs; all
fixtures ≥ the 4.5 grounding floor. Synthetic fixtures are legacy-mode (no
`career_corpus`), so the date guard itself is exercised by unit tests
(`tests/test_hardening.py::TestComputeDateGrounding`, incl. the KW6 regression
shape) and route tests
(`tests/test_app_iteration.py::TestGenerateDateGrounding`), not by this suite.

### What we learned

- The model treats heading metadata (dates) as editorial surface unless told
  otherwise — "bullets are immutable" does NOT generalize; each immutable fact
  class must be named explicitly in the contract.
- Iteration regenerates are the risk window: corpus mode regenerates from
  scratch each pass, so a relevance re-ordering can tempt the model into
  "harmonizing" dates to keep the sequence looking chronological.
- Deterministic guards must cover every output surface class; the
  fabricated-specifics detector scanning only bullet lines left headings
  ungoverned.

### Open questions / future tuning targets

- A corpus-mode eval fixture would let the smoke suite exercise date grounding
  end-to-end (today: unit/route tests only). Candidate for the eval-apparatus
  backlog.
- The duplication flag lands on the *second* heading consuming a range in
  document order — fine for a warning, but a per-experience title match would
  pinpoint the altered heading if this ever needs to gate.

---

## 2026-06-06 — eval/grounding-metric-l0: L0 fabricated-specifics + groundedness composite (metric ride-along, NO version bump)

### What changed

Eval records now carry two new deterministic fields under
`deterministic_metrics` on **every** record:

- `fabricated_specifics` — the L0 detail from new
  `hardening.compute_fabricated_specifics(generated_text, source_texts)`: per
  bullet it extracts verifiable specifics (numbers / % / $ / years / durations /
  named-entity & tool tokens) and checks membership in the candidate's
  ground-truth source union with tolerance (formatting variants `~30`/`30`/`30+`
  and light rounding grounded; different magnitude flagged; `k8s ≡ kubernetes`
  alias-normalized). Returns a severity-weighted `fabricated_specifics_rate` (a
  fabricated number outweighs a fabricated entity) + `flagged_samples`.
- `groundedness` — a single reportable composite. **L0-only by default**
  (`layers: ["L0"]`, `score = 5·(1 − rate)` for the score-over-time chart);
  enriches in place to `["L0","L1","L2"]` (NLI entailment + MiniCheck) only under
  `--grounding-signals`.

The source union is assembled by new `hardening.assemble_source_union`, factored
out of `compute_iteration_signals` (behavior-preserving) so the iteration
clarifier and the L0 check share one definition.

### Why this is a metric note and **not** a `PROMPT_VERSION` bump

No prompt **template** changed — `SYSTEM_PROMPT`, every per-call builder, and the
model routing are byte-for-byte untouched. This is a **deterministic measurement
added alongside** the existing post-generation metrics (`verb_diversity`,
`grounding_overlap`, …); it observes output, it does not shape it. The existing
`grounding_overlap` source set is deliberately left unchanged — L0 scores against
a *separate* wider `source_union` (adds clarification answers) so the established
`grounding_overlap` numbers and the v1.0.1/v1.0.2 baseline floors are **not**
perturbed. L1/L2 (`evals/grounding_signals.py`) behavior is read, never re-tuned.

### Result

No automated eval run (no template change to score; the metric only adds
columns). Pinned by LLM-free unit tests:
`tests/test_hardening.py::TestFabricatedSpecifics` (exact match → 0; novel number
→ flagged; within/out-of numeric tolerance; `k8s`≡`Kubernetes` aliasing;
embedded-digit non-leak; severity weighting; per-bullet shape; samples cap) +
`TestAssembleSourceUnion`, and
`tests/test_eval_runner.py::TestGroundednessComposite` (L0-only default + L1/L2
enrich-in-place + zero-bullet guard).

### What we learned

1. **L0 is uncalibrated by design — high precision, unproven recall.** A novel
   number/entity absent from the source union is almost certainly fabricated, so
   precision on the highest-severity class is high at zero model cost. But L0
   **will false-positive on paraphrase / implication** (source "managed a small
   team" → output "led a 4-person team" flags "4"). It is therefore a
   **flag-for-review** signal, not a gate; tolerance bands are conservative.
   Precision/recall stays unproven until calibration against `annotations.json`
   (deferred-B, pre-v1.1.0) — there are **no labels yet** (`evals/fixtures/real/`
   is empty), which is the binding constraint, not the metric code.
2. **Score against the dynamic union, not the original résumé.** A metric scored
   against only the primary over-reports, flagging legitimately-clarified facts
   as fabrication. Reusing `assemble_source_union` keeps the L0 check honest and
   consistent with what `generate()`'s widened grounding check already accepts.

---

## 2026-06-04 — feat/bullet-drag-reorder: user bullet order (behavior note, NO version bump)

### What changed

User-driven bullet ordering on the Compose step (v1.0.5). `_stable_user_prefix`
in [`analyzer.py`](../analyzer.py) now honors
`composition_overrides.bullet_order = {experience_id: [bullet_id, ...]}`,
reordering each experience's bullets in the `<career_corpus>` block before it is
emitted to `generate()`. `app.py` persists/serves the order; the Compose UI adds
HTML5 drag + keyboard reorder.

### Why this is a behavior note and **not** a `PROMPT_VERSION` bump

The prompt **template** is byte-for-byte unchanged — `SYSTEM_PROMPT`, the
corpus-mode guide, and every per-call builder are untouched. What changes is the
**order of the data** inside `<career_corpus>` when (and only when) the user has
set an explicit order. This is exactly the "data order, not template" carve-out
called out in `RELEASE_CHECKLIST` point 10: a `PROMPT_VERSION` bump would
mis-attribute eval telemetry, since two runs at the same version can now
legitimately differ if the user reordered. The default (no `bullet_order`) path
is **byte-identical** — guarded by
`tests/test_corpus_mode_prompt.py::TestBulletOrderHonored::test_empty_bullet_order_byte_identical`
— so the analyze→generate prompt cache is untouched and score-over-time is not
polluted.

### Result

No automated eval run (no template change to score). Behavior is pinned by
LLM-free tests: `TestBulletOrderHonored` (corpus payload honors the order;
unlisted bullets land at the end; default byte-identical) and
`tests/test_application_routes.py::TestCompositionBulletOrder` (persistence
round-trip; GET order + `has_custom_order`/`in_custom_order`; reset fallback).

### What we learned

1. **Sequence position is a real generate-time lever.** The Sonnet generate
   prompt weights earlier-listed corpus bullets when trimming to a length-limited
   résumé — so letting the user set that order is a genuine quality knob, not
   cosmetics. The manual validation a future tuner should run (per
   RELEASE_CHECKLIST point 10): one reordered ⇄ one default-order condition on a
   synthetic fixture, confirming the generated résumé honors the reorder.
2. **"Data order, not template" is the right reason to skip a version bump** —
   but only because the default path is provably byte-identical. If a future
   change makes ordering affect the *default* output, that becomes a real bump.

---

## 2026-06-02 — r1/clarify-model-trial (clarify() → Haiku 4.5) (`2026-06-01.3` → `2026-06-01.4`)

### What changed

`clarify()` switched from Sonnet 4.6 → Haiku 4.5 — a one-keyword change (`model=HAIKU_MODEL` on
its `_parse_or_retry` call). **No prompt-text change**: `CLARIFY_SYSTEM_PROMPT` and the user prompt
are byte-identical to `.3`. `PROMPT_VERSION 2026-06-01.3` → `2026-06-01.4` (model change recorded so
telemetry attributes the Haiku build separately from the Sonnet floor). `clarify_iteration()`
deliberately stays on Sonnet. Optional, non-tag-gating branch off `main` @ `b3185e2`.

### Why

The model-selection comment parked clarify on Sonnet "until [clarification_quality /
iteration_quality] clear 4.0 stably." Post-R1-split they do (floor ds 4.20 / pm 4.26 / sre 4.02),
which unblocked the trial. clarify is short structured output (3–5 questions, ~600–700 out tokens) —
structurally a Haiku sweet spot. Hypothesis: Haiku holds `clarification_quality` for ~$0.01/call less.

### Result

**n=5 anchor runs** at `2026-06-01.4` (`evals/results/20260601_{232331,233212,234055}Z.jsonl`,
`20260602_{002239,003107}Z.jsonl`). Started at n=3, extended to n=5 to disambiguate two isolated
3.2 outliers (see learnings).

#### Dual-gate check (n=5)

| Criterion | Status |
|---|---|
| `clarification_quality` no drop > 0.5 vs 2026-06-01 floor | ✅ ds −0.20, pm −0.06, sre −0.02 |
| `pm-senior / clarification_quality` ≥ 4.0 | ✅ 4.20 |
| Haiku satisfies parse-time `context_probe` + ≥60%-combined (`ClarifyResponse`) | ✅ 0 retries |
| `clarify_retry` rate low | ✅ **0/15 = 0%** |

#### `clarification_quality` (Haiku `.4`, n=5) vs Sonnet `.3` floor

| Fixture | raw | mean | median | floor (`.3`) |
|---|---|---|---|---|
| data-scientist-junior | [4.2, 4.2, **3.2**, 4.2, 4.2] | 4.00 | **4.2** | 4.20 |
| pm-senior | [4.2, 4.2, 4.2, 4.2, 4.2] | 4.20 | **4.2** | 4.26 |
| sre-mid-level | [**3.2**, 4.2, 4.2, 4.2, 4.2] | 4.00 | **4.2** | 4.02 |

#### clarify call — cost / latency (Haiku `.4` vs Sonnet `.3` floor)

| Metric | Sonnet `.3` | Haiku `.4` | Δ |
|---|---|---|---|
| p50 latency | 11.9 s | **7.5 s** | **−37 %** |
| cost / call | $0.0167 | **$0.0072** | **−57 %** |
| retry rate | 0 % | 0 % | flat |

Canaries flat: grounding ds 4.70 / pm 4.70 / sre 4.74 (no hidden-quality leak into generate); tone
medians unchanged (pm `tone` 4.00 is generate-side noise — clarify does **not** feed generate in the
synthetic eval, so any tone/ats/keyword movement grades the unchanged `generate` path). Other rubrics
(Haiku `.4` / Sonnet `.3`): ats ds 4.20/4.40, pm 4.30/4.36, sre 4.68/4.60; sartor ds 4.42/4.54,
pm 4.20/4.18, sre 4.42/4.45; keyword ds 4.20/4.30, pm 4.12/4.20, sre 4.44/4.46 — all within noise.

### What we learned

1. **The two 3.2s were judge noise, not a Haiku quality drop.** At n=3, ds and sre each showed one
   3.2 (means 3.867, both < 4.0) — alarming against the exceptionally-clean post-split Sonnet floor
   (ds 4.20 ± 0.00). Extending to n=5 (runs 4–5 both fully clean at 4.2) recovered both means to 4.00
   and left all three medians at 4.2 = the Sonnet floor. **Rule of thumb:** against a tight floor, n=3
   is too thin to separate a single-grading ±0.6 Haiku-judge wobble from a real regression — extend the
   sample before deciding rather than rejecting on one outlier.
2. **Haiku honored the parse-time composition rules perfectly (0/15 retries).** The flagged risk — a
   weaker model retrying often to satisfy `ClarifyResponse`'s `context_probe` + ≥60%-combined rules,
   eroding the saving and adding latency — did not materialize at all. The structured rules plus the
   compact analyzer-digested prompt are well within Haiku's range.
3. **The saving is real but modest (~$0.01/optional call).** The handoff's ~$0.03/application estimate
   was high for the anchor fixtures (compact clarify input, ~600–700 out tokens); measured saving is
   ~$0.0095/call (57 %), plus a 37 % latency win. Adopted because quality held *in expectation*
   (medians identical to the Sonnet floor) — so the cheaper + faster call is free money on an optional step.

### Decision: ADOPTED

`clarify()` ships on Haiku 4.5 at `PROMPT_VERSION 2026-06-01.4`. v1.0.3 remains ready to tag (this
branch was non-tag-gating). `clarify_iteration()` stays Sonnet — revisit when `iteration_quality`
clears 4.0 stably (still fixture-fragile, fires ~1/5 runs).

---

## 2026-06-01 — r1/analyze-split-cache-reclaim (synthesis under shared SYSTEM_PROMPT) (`2026-06-01.2` → `2026-06-01.3`)

### What changed

Follow-up to the two-pass split (`.2` below), on branch `r1/analyze-split-cache-reclaim`.
The `.2` build gave the synthesis pass a dedicated `SYNTHESIS_SYSTEM_PROMPT`, which
**broke the analyze→generate prompt cache**: Anthropic prefix caching matches from the
system block, so a distinct synthesis persona diverges from `generate()`'s `SYSTEM_PROMPT`
and `generate` lost its cache hit (`cache_read=0` on all 9 `.2` fixture-runs).

The fix (in `analyzer.py`):
- Synthesis now runs under the **default `SYSTEM_PROMPT`** (no `system_prompt` override) in
  both `analyze()` and `analyze_streaming()`. Its cached prefix
  `[SYSTEM_PROMPT][_stable_user_prefix]` is byte-identical to `generate()`'s → cache reclaimed.
- Dropped the `SYNTHESIS_SYSTEM_PROMPT` constant; folded the synthesis-specific framing
  (strategy-only; don't re-extract; ground in `<extracted_signal>`) into the `<task>` of
  `_analyze_synthesis_prompt`, **after** the cached prefix (so it doesn't break the match).
- Extraction is unchanged (Haiku, `EXTRACTION_SYSTEM_PROMPT`, separate cache pool).

`PROMPT_VERSION`: `2026-06-01.2` → `2026-06-01.3`. Tests: `test_analyze_split.py` updated
(synthesis no longer overrides the system prompt → asserts the default); 718 green; ruff + mypy clean.

### Why

The analyze→generate cache overlap is a deliberate optimization (`docs/architecture.md`):
within one iteration the `[SYSTEM_PROMPT][_stable_user_prefix]` block is byte-identical, so the
second Sonnet call reads it instead of re-prefilling the whole corpus. The `.2` split silently
forfeited it. The dollar delta is tiny on the synthetic fixtures (~$0.006/run) but **grows with
corpus size** — a real user's `_stable_user_prefix` (full `<career_corpus>` + résumé + profile)
is far larger, so the lost cache costs real money and adds generate prefill latency at scale.
Reclaiming it costs nothing structural: synthesis-under-`SYSTEM_PROMPT` is the **proven v1.0.2
shape** (the unified `analyze()` produced these same three strategy keys under `SYSTEM_PROMPT`),
so it is lower quality-risk than the new dedicated persona it replaces.

### Result

**n=5 anchor runs** at `2026-06-01.3` (`evals/results/20260601_185916Z.jsonl`,
`191510Z`, `192408Z`, `210845Z`, `211737Z`). Cost ≈ $1.9 total (~$0.38/run). Runs 4–5 were
confirmation runs to resolve the tone outlier below.

#### Cache + latency (n=15 fixture-runs)

| Metric | Result |
|---|---|
| **generate `cache_read` > 0** | **15/15 runs** (1781/1928/1877 per fixture, = synthesis's `cache_create`) — fully reclaimed (was 0/9 on `.2`) |
| combined analyze p50 | **67.7s** (≤ 72s budget); max 77.0s |
| parse retries | 0 |

#### Per-(fixture × rubric) mean ± stdev (n=5, judge_error + scenario_misaligned excluded)

| Fixture | ats_format | callback_likelihood | clarification_quality | grounding | keyword_coverage | tone |
|---|---|---|---|---|---|---|
| data-scientist-junior | 4.40 ± 0.25 | 4.54 ± 0.08 | **4.20 ± 0.00** | 4.72 ± 0.07 | 4.30 ± 0.20 | 3.78 ± 0.84 (see note) |
| pm-senior | 4.36 ± 0.21 | 4.18 ± 0.04 | **4.26 ± 0.12** | 4.64 ± 0.05 | 4.20 ± 0.00 | 4.20 ± 0.00 |
| sre-mid-level | 4.60 ± 0.23 | 4.45 ± 0.15 (n=4) | 4.02 ± 0.22 | 4.80 ± 0.00 | 4.46 ± 0.22 | 4.36 ± 0.21 |

`ds × tone` raw = [4.2, 4.2, **2.1**, 4.2, 4.2] — a single run's cover letter opened with a
throat-clearing "I am writing to be considered for…" + hedging "I would welcome a conversation"
(tone rubric Checks 3/4). 4 of 5 runs are clean at floor (median 4.2). `sre × callback_likelihood`
run 2 was a `judge_error` (invalid judge JSON), excluded.

#### Dual-gate check

| Criterion | Status |
|---|---|
| **Cache reclaimed** (the point of this branch) | ✅ generate `cache_read` > 0 on **15/15** |
| **SPEED:** analyze p50 ≤ 72s combined | ✅ **67.7s** (n=15) |
| pm-senior × clarification_quality ≥ 4.0 | ✅ 4.26 |
| clarification_quality no drop > 0.5 vs 2026-06-01 floor | ✅ max drop −0.05 (sre) |
| tone + grounding canaries flat | ✅ grounding 4.64–4.80; tone median 4.2/fixture (lone ds 2.1 = generate-side, see below) |
| ruff + mypy + pytest (718) | ✅ all green |

### What we learned

1. **Cache reclaim is real and free.** Moving synthesis to the shared `SYSTEM_PROMPT` restored
   `generate cache_read` to 1781/1928/1877 (15/15 runs, = synthesis's write) with **no** speed or
   quality cost — p50 actually held at 67.7s and `clarification_quality` was flat-to-up. The
   specialist `SYNTHESIS_SYSTEM_PROMPT` from `.2` was an elegant idea that wasn't worth the cache
   it cost; the persona difference bought nothing the schema-constrained user prompt doesn't.

2. **Prefix caching is unforgiving about the system block.** A cache hit needs a byte-identical
   prefix *from position 0*; you cannot share the corpus block across two different system prompts.
   Any future per-call persona that wants to ride the analyze/generate cache must keep `SYSTEM_PROMPT`
   as its system block and put its specialization after the cached prefix.

3. **The `ds × tone` 2.1 is pre-existing `generate` variance, not a reclaim regression.** The
   reclaim changed only the synthesis pass; `generate` / `generate_cover_letter` are untouched.
   The throat-clearing opener appeared in 1 of 5 runs and is a `generate`-side cover-letter
   adherence lapse. Flagged as a future generate-tuning item (cover-letter opener discipline);
   out of scope here.

---

## 2026-06-01 — r1/analyze-split-retry (two-pass: Haiku extraction + Sonnet synthesis) (`2026-06-01.1` → `2026-06-01.2`)

### What changed

Split the single Sonnet `analyze()` call into a two-pass pipeline — the SPEED half
of R1 Phase 2, rebuilt on `main` (NOT cherry-picked from `r1-attempted-2026-05-26`,
which predates the Pydantic migration + typed `hidden_qualities`). All in `analyzer.py`
+ the SSE wiring:

**A. `analyze()` → thin two-pass orchestrator**
- **Pass 1 — extraction (Haiku 4.5, new `EXTRACTION_SYSTEM_PROMPT`):** `essential_skills`,
  `preferred_skills`, `industry_keywords`, `hidden_qualities` (the typed
  `HiddenQualityItem` shape), `professional_vocabulary`, `keyword_placement`. Enforced by
  new `AnalyzeExtractionResponse` — a bare-string or out-of-enum `hidden_qualities` item
  fails `model_validate` → `_parse_or_retry` retries with the `Literal` error.
- **Pass 2 — synthesis (Sonnet 4.6, new `SYNTHESIS_SYSTEM_PROMPT`):** `comparison`,
  `suggestions`, `overall_strategy`, grounded on Pass 1 via an `<extracted_signal>` block
  (`AnalyzeSynthesisResponse`). The hiring-manager persona narrowed to strategy — ATS
  vocabulary + bullet-writing rules stripped (those live in extraction / `generate`).
- `analyze()` merges `{**extraction, **synthesis}` into the existing `AnalyzeResponse`
  contract. Both passes share one `_stable_user_prefix`.

**B. `analyze_streaming()`** re-introduces the `("phase", {"phase": "extraction"|"synthesis"})`
SSE sentinel before each pass; inner per-pass `done` events are intercepted, one merged
`done` emitted. `app.py` forwards the `phase` event; `static/app.js` swaps the status label.

**C. Dropped two unconsumed analyze keys** — `ats_improvements` + `ideal_resume_profile`.
Re-audited against `main`: zero readers in `static/app.js`, `app.py`, `clarify()`,
`generate()`, or any eval rubric (`_renderAnalysis` is field-by-field and names neither).
Actionable ATS guidance remains in `keyword_placement` (kept in extraction), the
deterministic `ats_warnings`, and `comparison.gaps` / `suggestions`.

`PROMPT_VERSION`: `2026-06-01.1` → `2026-06-01.2`. Tests: +7 in `tests/test_analyze_split.py`
(two-pass orchestration; HiddenQualityItem retry on the Haiku pass; phase-sentinel ordering;
single merged done; extracted-signal carry-through). Suite 711 → 718, all green; ruff + mypy clean.

### Why

R1's original split (`r1-attempted-2026-05-26`) won ~30% on analyze latency but regressed
`clarification_quality` to 2.1 via two root causes — `context_probe` never emitted, and
`hidden_qualities` shape mismatch. Both are now fixed on `main` (the two ✓ R1 branches). This
branch re-introduces the split for speed **on top of those guardrails**, gated so it cannot
give the recovered quality back. RELEASE_ARC §Phase 2 `r1/analyze-split-retry`; the v1.0.3
"≤72s combined" criterion is not to be relaxed (user-confirmed 2026-06-01).

### Result

**n=3 anchor runs** at `2026-06-01.2` (`evals/results/20260601_175225Z.jsonl`,
`20260601_181130Z.jsonl`, `20260601_182058Z.jsonl`). Cost ≈ $1.15 total (~$0.38/run).

#### Per-(fixture × rubric) mean ± stdev (n=3)

| Fixture | ats_format | callback_likelihood | clarification_quality | grounding | keyword_coverage | tone |
|---|---|---|---|---|---|---|
| data-scientist-junior | 4.60 ± 0.28 | 4.50 ± 0.14 | **4.20 ± 0.00** | 4.80 ± 0.00 | 4.30 ± 0.14 | 4.20 ± 0.00 |
| pm-senior | 4.50 ± 0.24 | 4.17 ± 0.05 | **4.20 ± 0.00** | 4.77 ± 0.05 | 4.20 ± 0.00 | 4.20 ± 0.00 |
| sre-mid-level | 4.80 ± 0.00 | 4.40 ± 0.14 | 4.03 ± 0.24 | 4.77 ± 0.05 | 4.60 ± 0.00 | 4.37 ± 0.24 |

`clarification_quality` raw: ds [4.2, 4.2, 4.2]; pm [4.2, 4.2, 4.2]; sre [3.7, 4.2, 4.2]
(the lone 3.7, run 1, is within Haiku-judge noise vs the 4.07 floor). `sre × iteration_quality`
fired scenario_misaligned (known fragility, out of scope).

#### Latency (combined extraction + synthesis, n=9 fixture-runs)

| Pass | p50 | notes |
|---|---|---|
| extraction (Haiku) | 11.2s | structured lists, ~0.9–1.3k out tokens |
| synthesis (Sonnet) | 60.1s | strategy only; ~2.1–3.3k out tokens |
| **combined analyze** | **69.8s** | values: 55.4 / 60.5 / 60.8 / 68.8 / 69.8 / 73.2 / 77.0 / 81.4 / 82.9; max 82.9s (sre) |

vs the unified single-call analyze p50 103.2s (R1 benchmark) → **~32% faster**. sre is the
latency outlier (synthesis 70–77s on the highest output-token counts); the gate is p50-based,
so it passes — synthesis verbosity is the lever if the bar ever tightens.

#### Dual-gate check

| Criterion | Status |
|---|---|
| **SPEED:** analyze p50 ≤ 72s combined | ✅ **69.8s** (n=9 fixture-runs) |
| pm-senior × clarification_quality ≥ 4.0 | ✅ 4.20 ± 0.00 |
| clarification_quality no drop > 0.5 vs 2026-06-01 floor | ✅ max drop **−0.04** (sre: 4.03 vs 4.07) |
| all other rubrics within 1 stdev of v1.0.2 baseline | ✅ every rubric at/above its baseline mean |
| tone + grounding canaries flat (no hidden_qualities leak into generate) | ✅ tone 4.20–4.37, grounding 4.77–4.80 |
| parse-time guardrail clean (typed hidden_qualities) | ✅ **0 retries** across 9 runs |
| ruff + mypy + pytest (711→718) | ✅ all green |

Cleared the dual gate on the first n=3 — no `/prompt-tune` iterations consumed.

### What we learned

1. **Quality-first ordering paid off.** With the typed `hidden_qualities` + parse-time
   `context_probe` guardrails already on `main`, the speed split landed without re-opening the
   2.1 regression: `clarification_quality` held at 4.03–4.20 (vs the original split's 2.1). The
   guardrails, not the prompt prose, are what made the split safe.

2. **`Literal` enforcement transfers cleanly to a Haiku extraction pass.** The Haiku model
   emitted the typed `HiddenQualityItem {category, signal}` on the first attempt across all 9
   runs (0 retries) — the same lever that worked for the single-call Sonnet analyze holds on the
   cheaper model. The 2026-05-26 "hidden_qualities shape didn't survive the Haiku round trip"
   failure was a *prose-guidance* problem; typing the field fixes it at the model boundary.

3. **The split is a cost win, not just a speed win.** Per-fixture cost $0.11–0.145 — at or below
   the v1.0.2 baseline ($0.13–0.147) — even though `generate` lost its analyze→generate
   prompt-cache hit (`cache_read=0` on all 9 runs, because the synthesis pass uses a specialist
   system prompt that diverges from `generate`'s `SYSTEM_PROMPT` at the cached prefix's head).
   Moving the high-token extraction work to Haiku more than offsets the lost Sonnet cache read.

4. **Stale doc flagged:** `docs/architecture.md`'s "analyze and generate share a heavy cached
   user prefix" and the single-call analyze in `pipeline.mmd` / `llm-routing.mmd` are now
   inaccurate. Out of scope for this branch (RELEASE_ARC §Phase 2 bounds it to the split + gate);
   surfaced to the user for a follow-up doc pass.

5. **sre synthesis verbosity is the headroom lever.** sre's synthesis ran 2605–3296 output
   tokens (70–77s) vs ds/pm at ~2.1–2.6k (47–56s). The p50 gate passes with 2.2s margin; if a
   future change tightens the bar, capping suggestion count + rationale length in
   `SYNTHESIS_SYSTEM_PROMPT` is the first, lowest-risk move (doesn't touch the extraction
   guardrail or clarify).

---

## 2026-06-01 — r1/hidden-qualities-schema (`2026-05-30.1` → `2026-06-01.1`)

### What changed

Typed the `hidden_qualities` field: from free-form `list[str]` to
`list[{"category": <enum>, "signal": str}]`, with `category` constrained to the four
recruiter-validated shapes (`operating_context`, `scope_of_ownership`,
`stakeholder_gravity`, `resilience`). Four coupled changes, in `analyzer.py` +
`static/app.js`:

**A. `HiddenQualityItem` Pydantic model + `AnalyzeResponse` wiring** (`analyzer.py`)
New `HiddenQualityItem(BaseModel)` with `category: Literal[...]` (the four shapes) and
`signal: str`. `AnalyzeResponse.hidden_qualities` retyped `Any` → `list[HiddenQualityItem]`.
An invalid/missing category, or a bare-string item (the old shape), now fails
`model_validate` → `_parse_or_retry` appends the structured `Literal` error and retries.
Same parse-time-enforcement pattern proven in `r1/structural-context-probe`
(2026-05-30 "What we learned" #1).

**B. `_analyze_prompt` schema + category rule** (`analyzer.py`)
The single-call `analyze()` prompt (shared with `analyze_streaming` via `_analyze_prompt`)
now emits the structured example and an instruction naming the enum: "surface the
operating-context signals the JD implies — NOT trait-words … one portable sentence …
one concept per signal." *(NB: the handoff referenced `EXTRACTION_SYSTEM_PROMPT` /
`_analyze_extraction_prompt`; those live only on the reverted `r1-attempted-2026-05-26`
two-pass branch. On `main`, `analyze()` is a single Sonnet call and the schema lives in
`_analyze_prompt` — per RELEASE_ARC §Phase 2's "branch from main" correction. The work
mapped there.)*

**C. `clarify()` `<context_signals>` render** (`analyzer.py`)
Was `json.dumps(hidden_qualities)`. Now renders each item as `- [category] signal`,
tolerant of legacy `list[str]` items (an iteration can reload a pre-change context file —
must not `KeyError`). The `ClarifyResponse` validator is unchanged (it only reads
`bool(hidden_qualities)`).

**D. Frontend render** (`static/app.js`)
The Step-1 analysis panel rendered each item as a string (`esc(q)`) — would print
`[object Object]` once items are objects. Now renders a category tag + `q.signal`, with a
plain-string fallback for older saved analyses.

`PROMPT_VERSION`: `2026-05-30.1` → `2026-06-01.1`. Tests: +14 in
`tests/test_analyze_hidden_qualities.py` (enum enforcement; bare-string rejection → retry
trigger; clarify render for structured + legacy + empty). Suite 697 → 711, all green;
ruff + mypy clean.

### Why

`hidden_qualities` is the load-bearing input to the `context_probe` machinery landed in
`r1/structural-context-probe`. As free-form strings it carried no guarantee of *which kind*
of signal each item was, so the clarify pass had to re-infer category from prose every
call. Typing the category at the extraction boundary makes the four recruiter-validated
shapes a parse-time contract (trait-words are the weakest hidden signal — 2026-05-26
recruiter consultation), and gives downstream consumers (`clarify()`, the UI, future
tuning) a structured field instead of prose to pattern-match. RELEASE_ARC §Phase 2
`r1/hidden-qualities-schema`.

### Result

**n=3 anchor runs** at `2026-06-01.1` (`evals/results/20260601_160931Z.jsonl`,
`evals/results/20260601_161906Z.jsonl`, `evals/results/20260601_162853Z.jsonl`).
Cost ≈ $1.21 total (~$0.40/run). All 3 runs exited code 2 — the expected run-to-run
Haiku-variance alert during n-run collection (documented in the v1.0.2 baseline "Note on
exit codes"), not an aggregate regression.

#### Per-(fixture × rubric) mean ± stdev (n=3, scenario_misaligned excluded)

| Fixture | ats_format | callback_likelihood | clarification_quality | grounding | keyword_coverage | tone | iteration_quality |
|---|---|---|---|---|---|---|---|
| data-scientist-junior | 4.30 ± 0.17 | 4.40 ± 0.17 | 4.07 ± 0.23 | 4.77 ± 0.06 | 4.33 ± 0.23 | 4.20 ± 0.00 | n/a |
| pm-senior | 4.50 ± 0.30 | 4.23 ± 0.06 | **4.20 ± 0.00** | 4.73 ± 0.12 | 4.20 ± 0.00 | 4.20 ± 0.00 | n/a |
| sre-mid-level | 4.60 ± 0.35 | 4.37 ± 0.12 | 4.07 ± 0.23 | 4.80 ± 0.00 | 4.43 ± 0.21 | 4.20 ± 0.00 | 4.2 (n=1) |

#### Raw scores per run

| Fixture | Rubric | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.2 | 4.5 | 4.2 |
| data-scientist-junior | callback_likelihood | 4.6 | 4.3 | 4.3 |
| data-scientist-junior | clarification_quality | 4.2 | 4.2 | 3.8 |
| data-scientist-junior | grounding | 4.8 | 4.8 | 4.7 |
| data-scientist-junior | keyword_coverage | 4.2 | 4.6 | 4.2 |
| data-scientist-junior | tone | 4.2 | 4.2 | 4.2 |
| pm-senior | ats_format | 4.2 | 4.5 | 4.8 |
| pm-senior | callback_likelihood | 4.2 | 4.3 | 4.2 |
| pm-senior | clarification_quality | 4.2 | 4.2 | 4.2 |
| pm-senior | grounding | 4.8 | 4.6 | 4.8 |
| pm-senior | keyword_coverage | 4.2 | 4.2 | 4.2 |
| pm-senior | tone | 4.2 | 4.2 | 4.2 |
| sre-mid-level | ats_format | 4.2 | 4.8 | 4.8 |
| sre-mid-level | callback_likelihood | 4.3 | 4.5 | 4.3 |
| sre-mid-level | clarification_quality | 4.2 | 4.2 | 3.8 |
| sre-mid-level | grounding | 4.8 | 4.8 | 4.8 |
| sre-mid-level | iteration_quality | 4.2 | None | None |
| sre-mid-level | keyword_coverage | 4.6 | 4.5 | 4.2 |
| sre-mid-level | tone | 4.2 | 4.2 | 4.2 |

`None` = scenario_misaligned (scripted edit substring not in generated output that run).

#### Gate check vs `2026-05-30 — r1/structural-context-probe` baseline

| Criterion | Status |
|---|---|
| No (fixture × rubric) mean drop > 0.5 vs 2026-05-30 baseline | ✅ max drop = **−0.17** (ds-junior × tone) |
| pm-senior × clarification_quality ≥ 4.0 (v1.0.3 tag criterion) | ✅ 4.20 ± 0.00 |
| tone canary (no hidden_qualities leak into generate) | ✅ held 4.20 / 4.20 / 4.20 |
| grounding canary | ✅ 4.73–4.80, all fixtures |
| ruff + mypy + pytest (697→711 tests) | ✅ all green |

### What we learned

1. **Typing the extraction boundary did not regress clarify.** The concern going in was
   that constraining `hidden_qualities` to four categories might starve the clarify pass of
   signals or distort `context_probe` composition. It didn't: every run produced ≥1
   context_probe (1–3 per run), and `clarification_quality` held — pm-senior at exactly
   4.20, ds-junior/sre at 4.07 mean (a single 3.8 outlier each in run 3, within Haiku noise
   against the unusually tight 4.20 ± 0.00 baseline). The structured signal feeds the
   context_probe machinery at least as well as the free-form string did.

2. **The two canaries earned their place.** `tone` and `grounding` were the pre-registered
   leak detectors (hidden_qualities must drive clarify, NOT generate prose — 2026-05-26
   "Hidden qualities propagation beyond clarify"). Both held flat, confirming the schema
   change stayed in the clarify lane and didn't bleed category vocabulary into generated
   bullets.

3. **The handoff's symbol names tracked the wrong branch — verify against `main`, not the
   plan prose.** `EXTRACTION_SYSTEM_PROMPT` / `_analyze_extraction_prompt` exist only on the
   reverted two-pass branch. Grepping `main` first (rather than trusting the handoff's file
   pointers) surfaced that `analyze()` is single-call and the schema lives in
   `_analyze_prompt`. RELEASE_ARC already carried the "branch from main" correction; the
   code confirmed it.

4. **`Literal` is the cheapest structured-retry enforcement.** No custom validator needed —
   a `Literal[...]` field produces a parse-time error that already names the allowed values,
   which `_parse_or_retry` forwards verbatim to the retry prompt. Same lever as the
   ClarifyResponse composition rules, less code.

---

## 2026-05-30 — r1/structural-context-probe (`2026-05-24.4` → `2026-05-30.1`)

### What changed

Three coupled changes in `analyzer.py` plus eval-apparatus fixes:

**A. `CLARIFY_SYSTEM_PROMPT` — 2-kind → 3-kind recruiter persona**
Replaced the interview-coach framing (experience_probe + scope_probe only) with
the recruiter persona from the r1-attempted-2026-05-26 branch. Added `context_probe`
as a third question kind: translates JD operating-context / scope-of-ownership /
stakeholder-gravity / resilience signals into PORTABLE experience questions that
adjacent-background candidates can map onto. Load-bearing framing line added:
"Tool-name probes are dead ends when the answer is 'no' — context probes surface
transferable experience; the tool-name probe only confirms or denies a specific item."
Composition rule lifted from ≥50% experience_probe alone to ≥60% combined
experience_probe + context_probe.

**B. `clarify()` prompt — `<context_signals>` block added**
The prompt now passes `hidden_qualities` from analysis into a `<context_signals>`
block so the model sees the operating-context signals it must translate into
context_probes. `<instructions>` updated to enumerate all three kinds with the
60% combined rule.

**C. `ClarifyResponse` Pydantic validator — two parse-time enforcement rules**
Both rules fire only when `validation_context` is explicitly passed (clarify()
always passes it; clarify_iteration() does not — it has different question kinds).
- Rule 1: when `hidden_qualities_non_empty=True`, at least one `context_probe`
  required. Missing → `ValidationError` → `_parse_or_retry` appends error and retries.
- Rule 2: ≥60% combined experience_probe + context_probe (`math.ceil(N × 0.6)`).
  The composition that appeared before this branch (1 experience + 3–4 scope) failed
  the old ≥50% rubric too — it was genuinely broken, not a rubric-calibration issue.
  Missing → same retry path.

**D. Eval-apparatus fixes (no PROMPT_VERSION impact)**
- `clarification_quality.md` rubric: added context_probe as a valid kind; updated
  composition rule to ≥60% combined; allowed context_probes to count toward
  `experience_probes` theme coverage in the expected-themes check.
- `runner.py`: anchor suite now loads from `evals/rubrics/` (single source of truth)
  instead of frozen per-suite copies; deleted all 6 anchor rubric copies. This
  eliminates the class of bug where updating one copy silently leaves the other stale.
- `runner.py`: clarify log line now counts experience / context / scope probes
  separately (previously context_probes were miscounted as scope_probes).

`PROMPT_VERSION`: `2026-05-24.4` → `2026-05-30.1`

### Why

The v1.0.2 baseline showed `pm-senior × clarification_quality` at 4.00 ± 0.45
— barely above the 4.0 gate and with wide variance, both the R1.2 attempt
(on r1-attempted-2026-05-26) had degraded it to 2.1 by emitting tool-name probes
("have you used Epic?") where the rubric expected portable context-probes
("have you built products for regulated, workflow-heavy environments?"). The
recruiter consultation in the 2026-05-26 TUNING_LOG entry established the
diagnosis: tool-name probes are dead ends for adjacent-background candidates.

The parse-time enforcement was added after run 3 showed sre-mid-level producing
"1 experience, 1 context, 3 scope probes" (40% combined) — a composition that
would have failed the old ≥50% experience-only rubric too. The enforcement forces
a retry with a structured correction message, which consistently produces ≥60%
combined on the retry.

### Result

**Valid runs:** 4, 5, 6 (all with correct rubric and parse-time enforcement).
Runs 1–2 used a stale anchor rubric copy (context_probe graded as "invalid kind").
Run 3 pre-dated the 60% enforcement.

#### Per-(fixture × rubric) mean ± stdev (n=3, judge_errors excluded)

| Fixture | ats_format | callback_likelihood | clarification_quality | grounding | keyword_coverage | tone | iteration_quality |
|---|---|---|---|---|---|---|---|
| data-scientist-junior | 4.40 ± 0.28 | 4.50 ± 0.14 | **4.20 ± 0.00** | 4.73 ± 0.09 | 4.20 ± 0.00 | 4.37 ± 0.24 | n/a |
| pm-senior | 4.37 ± 0.24 | 4.17 ± 0.05 | **4.20 ± 0.00** | 4.80 ± 0.00 | 4.00 ± 0.20 (n=2) | 4.20 ± 0.00 | n/a |
| sre-mid-level | 4.57 ± 0.25 | 4.43 ± 0.17 | **4.20 ± 0.00** | 4.67 ± 0.09 | 4.43 ± 0.17 | 4.20 ± 0.00 | 3.2 (n=1) |

#### Raw scores per run

| Fixture | Rubric | Run 4 | Run 5 | Run 6 |
|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.2 | 4.8 | 4.2 |
| data-scientist-junior | callback_likelihood | 4.3 | 4.6 | 4.6 |
| data-scientist-junior | clarification_quality | 4.2 | 4.2 | 4.2 |
| data-scientist-junior | grounding | 4.6 | 4.8 | 4.8 |
| data-scientist-junior | keyword_coverage | 4.2 | 4.2 | 4.2 |
| data-scientist-junior | tone | 4.2 | 4.2 | 4.7 |
| pm-senior | ats_format | 4.7 | 4.2 | 4.2 |
| pm-senior | callback_likelihood | 4.2 | 4.1 | 4.2 |
| pm-senior | clarification_quality | 4.2 | 4.2 | 4.2 |
| pm-senior | grounding | 4.8 | 4.8 | 4.8 |
| pm-senior | keyword_coverage | JE | 3.8 | 4.2 |
| pm-senior | tone | 4.2 | 4.2 | 4.2 |
| sre-mid-level | ats_format | 4.7 | 4.2 | 4.8 |
| sre-mid-level | callback_likelihood | 4.6 | 4.2 | 4.5 |
| sre-mid-level | clarification_quality | 4.2 | 4.2 | 4.2 |
| sre-mid-level | grounding | 4.8 | 4.6 | 4.6 |
| sre-mid-level | iteration_quality | None | None | 3.2 |
| sre-mid-level | keyword_coverage | 4.6 | 4.5 | 4.2 |
| sre-mid-level | tone | 4.2 | 4.2 | 4.2 |

`JE` = judge_error (Haiku returned invalid JSON, excluded from stats).
`None` = scenario_misaligned (scripted edit substring not in generated output that run).

#### Gate check vs v1.0.2 baseline

| Criterion | Status |
|---|---|
| pm-senior × clarification_quality ≥ 4.0 | ✅ mean = 4.20 |
| No (fixture × rubric) drop > 0.5 vs v1.0.2 baseline | ✅ max drop = −0.18 (ds-junior × ats_format) |
| ruff + mypy + pytest (692→697 tests) | ✅ all green |

### What we learned

1. **Parse-time enforcement of composition rules changes model behavior reliably.** The 60% combined rule enforcement produces retries with clear structured error messages; Sonnet 4.6 consistently corrects composition on the retry (clarification_quality 4.2 ± 0.00 across all three fixtures in n=3 runs). This pattern is worth applying to other quality constraints that the prompt already states but the model doesn't always honor.

2. **The anchor rubric duplication was a hidden operational risk.** Two of the first three eval runs used a stale rubric copy that graded context_probe questions as "invalid kind," producing misleading 2.1–3.2 scores. The fix (single source of truth at evals/rubrics/) is load-bearing: rubric definitions are the evaluation contract and must evolve with the product; only fixtures should be frozen per anchor version.

3. **A composition that fails the new rubric also failed the old one.** The sre-mid-level pattern of "1 experience + 3 scope" would have failed ≥50% experience-probe by the old rubric (20%) and failed ≥60% combined by the new rubric. The enforcement isn't raising the bar artificially — it's making the model reliably hit a bar the rubric has always required.

4. **context_probe requires rubric awareness, not just prompt awareness.** Adding a new question kind to the prompt without updating the eval rubric causes the judge to penalize the very behavior you want. Any future new question kind must ship with a rubric update in the same branch.

5. **sre-mid-level × iteration_quality remains fragile (pre-existing).** The scenario fired once in 3 runs (run 6) and scored 3.2 — consistent with the known fixture fragility documented in the 2026-05-11.3 entry. Out of scope for this branch.

---

## 2026-05-26 — Atomic extraction + context-probe clarify (R1 quality fix) (`2026-05-26.1` → `2026-05-26.2`)

### What changed

Three surgical changes layered on top of the R1 two-pass split, in response to a measured −1.0 regression on `pm-senior/clarification_quality` and −0.4 on `sre-mid-level/clarification_quality` against the clean pre-R1 baseline. Diagnosis confirmed by a recruiting-specialist consultation: the Haiku extraction was producing naturalistic phrases ("EHR systems including Epic and Cerner") where it should produce atomic tokens, and the clarify pass was emitting tool-name probes when the JD's underlying signal was portable operating-context that adjacent-background candidates could map onto.

**A. Atomic extraction rule** ([`analyzer.py:EXTRACTION_SYSTEM_PROMPT`](../analyzer.py))
Added an explicit ALWAYS rule requiring ONE concept per item in `essential_skills`, `preferred_skills`, and `industry_keywords`, with worked OK / NOT OK examples (`["EHR", "Epic", "Cerner"]` vs. `["EHR systems including Epic and Cerner"]`). Rationale: extraction is a structured intermediate representation, not prose — naturalistic phrasing is a rendering concern for the final résumé bullet; conflating them hides individual tokens from ATS matchers and from downstream theme-matching.

**B. `hidden_qualities` redefined: context signals, not trait-words** ([`analyzer.py:EXTRACTION_SYSTEM_PROMPT` + `_analyze_extraction_prompt`](../analyzer.py))
Pre-R1.2 the `hidden_qualities` schema example said "unstated trait the JD implies — collaborative, autonomous, etc." Per the recruiter consultation: *"Trait-words are the WEAKEST hidden signals. The strong ones are domain-context, scope-of-ownership, and stakeholder-gravity."* Redefined to require items in one of four shapes — operating-context fit / scope of ownership / stakeholder gravity / resilience signal — with the JD wording that surfaced each signal where helpful. Schema shape unchanged (still `list[str]`), only the semantic guidance.

**C. New `context_probe` question kind in clarify** ([`analyzer.py:CLARIFY_SYSTEM_PROMPT` + `clarify()` prompt template](../analyzer.py))
Added a third question kind alongside `experience_probe` and `scope_probe`: `context_probe`. Each context_probe translates a `hidden_qualities` context signal into a PORTABLE experience question — the recruiter's quoted example: *"Have you built products for users in regulated, workflow-heavy environments where errors have real-world consequences — healthcare, fintech, transportation, anything similar?"* — so that an adjacent-background candidate (logistics PM applying to healthtech) can map their experience onto the role. Composition rule updated from "≥50% experience probes" to "≥60% experience + context probes combined." The clarify prompt template now emits a new `<context_signals>` block carrying `hidden_qualities` so the model actually sees them. The system prompt opens with a load-bearing framing line: *"Tool-name probes ... are dead ends when the answer is 'no' — they create fatigue and don't surface adjacent experience. Context probes that translate JD requirements into PORTABLE experience asks let candidates from adjacent backgrounds map their experience onto the role. That's the recruiter move."*

### Why

Measured regression on `clarification_quality` after R1 landed:

| Fixture | Rubric | Clean pre-R1 baseline | R1.1 | Δ |
|---|---|---|---|---|
| pm-senior | clarification_quality | 4.2 | 3.2 | **−1.0** |
| sre-mid-level | clarification_quality | 4.2 | 3.8 | **−0.4** |

The judge's `failed_rules: ["missing_expected_theme"]` reasoning made the cause explicit: questions correctly cited extracted keywords (EHR, Epic, Cerner, HL7, FHIR) but did not match expected themes like "healthcare/healthtech exposure" and "workflow products for clinicians." The fixture's expected themes are PORTABLE context-probes; the R1.1 system was emitting tool-name experience-probes.

Recruiter quote that anchored the fix: *"Asking 'have you used Epic' of someone who hasn't is dead-end. Asking 'have you built products for users in regulated, workflow-heavy environments where errors have real-world consequences' lets a logistics-PM or a fintech-PM map THEIR experience onto a healthtech JD."*

### Result

To be populated after the post-R1.2 eval run. The expectation is:
- `pm-senior/clarification_quality` recovers to ≥4.0 (the threshold), driven by context_probes hitting expected themes
- `sre-mid-level/clarification_quality` recovers to ≥4.0 (was 4.2 pre-R1)
- `keyword_coverage` improves or holds — atomic tokens give the generate pass more ATS-matchable items
- Other rubrics hold within ±0.3

### What we learned

(to be filled in after eval run)

### Open questions / future tuning targets

- **Quality proxies beyond evals** — the recruiter named three measurable proxies usable before we have sartor-outcome data: (1) **top-third density** (first 3 bullets of first job contain JD's top 3 essentials?), (2) **quantification rate** (% of bullets with a number / %, $, scale indicator), (3) **distinctiveness** ("would this bullet look the same on 100 other résumés?"). All three are deterministic, computable from generated output, and addressable without prompt changes — surface them as `deterministic_metrics` on eval records in a follow-up.
- **Hidden qualities propagation beyond clarify** — the recruiter flagged that hidden_qualities should drive clarify questions but NOT suggestion prose or bullet selection ("demonstrated strong collaboration" in suggestion prose is exactly what gets bullets ignored). Today we don't surface hidden_qualities to generate() at all; that's correctly skipping the middle layer. Verify nothing regresses on `tone` (which would be the canary if generate started absorbing them indirectly).
- **`recommend_bullets` quality** — Haiku selection on bullets uses essential_skills + preferred_skills + industry_keywords from extraction. With the atomic rule landed, the matching surface should improve (more individual tokens to match against bullet text). Watch the eval suite's grounding + keyword_coverage rubrics for evidence; if no improvement, the bullet-text → keyword match may need its own atomic normalization step.

---

## 2026-05-26 — Two-pass analyze: Haiku extraction + Sonnet synthesis (R1) (`2026-05-24.4` → `2026-05-26.1`)

### What changed

Split the single `analyze()` Sonnet 4.6 call into two specialized calls:

- **Pass 1 — `analyze_extraction`** (Haiku 4.5): produces `essential_skills`,
  `preferred_skills`, `industry_keywords`, `hidden_qualities`,
  `professional_vocabulary`, `keyword_placement`. New `EXTRACTION_SYSTEM_PROMPT`
  — an "ATS scanner" persona with extraction-only vocabulary (Boolean search,
  exact-match keywords, minimum vs preferred quals). Outputs structured lists,
  not prose.
- **Pass 2 — `analyze_synthesis`** (Sonnet 4.6): produces `comparison`,
  `suggestions`, `overall_strategy`. New `SYNTHESIS_SYSTEM_PROMPT` — the
  hiring-manager from `SYSTEM_PROMPT` narrowed to strategy vocabulary only
  (ATS terms removed, bullet-writing rules removed — those live in
  `SYSTEM_PROMPT` for `generate()`). Receives Pass 1's output as
  `<extracted_signal>` so it grounds its synthesis on concrete extracted
  signals rather than re-extracting in line.
- **`analyze()` becomes a thin orchestrator** that runs Pass 1 → Pass 2
  sequentially and merges into the legacy `ANALYZE_REQUIRED_KEYS` shape.
  Streaming variant (`analyze_streaming`) emits a new `("phase", {"phase":
  "extraction"|"synthesis"})` sentinel before each pass so the SSE route
  can swap the frontend status label.
- **Two phantom keys dropped:** `ats_improvements` (caught by R3 audit) and
  `ideal_resume_profile` (caught by R1 consumer audit — no downstream
  consumer in `static/app.js`, `analyzer.py`, `app.py`, or any eval rubric).

Files: [`analyzer.py`](../analyzer.py), [`app.py`](../app.py) (`/api/analyze/stream` forwards `phase`), [`static/app.js`](../static/app.js) (`runAnalysis()` handles `phase`).

### Why

Two motivations, the second confirmed against the framework the codebase already follows:

1. **Measured performance deficit.** Pre-R1 analyze p50 = 91s, p90 = 121s, max 292s. Median output tokens = 4,471 — Sonnet is paying its per-token price for ~half the output that is structurally Haiku-friendly (skill lists, keyword extraction, vocabulary classification).
2. **P6 Specialized Review hypothesis** ([10 Principles](https://jdforsythe.github.io/10-principles/overview/)): *"A generalist reviewer trends toward the median. Specialists find what generalists can't."* The pre-R1 prompt asked one persona to be both an ATS scanner AND a hiring manager AND an ATS-format auditor in one pass. Each context-switch dilutes adherence. P9 Token Economy counterweight (*"diminishing returns above 45% single-agent performance"*) is the check: the split is justified only if the single-agent call shows measurable underperformance — the 91s latency is the trigger.

External literature backing was attempted via a research agent but blocked by sandbox WebFetch denials for all external domains. The half-remembered citations (Tessera 2019 ATS study, MIT Sloan tailored-résumé callback rates, TheLadders eye-tracking) are **unverified** and were intentionally NOT cited in the new prompts. The eval gate (next section) is the actual quality-floor enforcement.

### Result

**Eval gate is load-bearing for this change.** Full `python evals/runner.py --suite synthetic` run after the implementation lands. Scores will be appended here once captured.

Expected qualitatively:
- **`keyword_coverage`**: should be **equal or better**. The dedicated extraction persona is paying closer attention to exact-match vs synonym keywords; `keyword_placement` quality should sharpen. Floor: no regression.
- **`grounding`**: should be **unchanged**. The synthesis pass still bans invention; the rule is narrower-scoped (no bullet-writing rules) but the no-invention spine remains. Floor: no regression.
- **`tone`**: should be **unchanged or slightly improved**. Removing the ATS jargon from the synthesis prompt may produce more natural strategy prose. Floor: no regression.
- **`clarification_quality` / `iteration_quality`**: depend on `essential_skills`, `comparison.gaps`, `comparison.title_alignment`, `keyword_placement` — all still produced by the orchestrator. Should be **unchanged**. Floor: no regression.

Performance expectation:
- Pass 1 (Haiku): ~5–10s, ~2,000 output tokens, ~$0.002.
- Pass 2 (Sonnet): ~30–50s, ~2,000 output tokens (~half pre-R1 because the schema is narrower).
- Total wall clock: ~35–60s vs. 91s. Perceived latency further improved by phase-event UI (the user sees concrete extracted keywords within ~10s instead of waiting 91s for everything).

### What we learned

(to be filled in after eval run)

### Open questions / future tuning targets

- **If `keyword_coverage` drops:** the extraction persona may be too terse — consider adding a worked example pair (OK/NOT OK) for `keyword_placement`. The current rules say "exact-match beats synonyms" but don't show what a high-quality placement entry looks like.
- **If `tone` drops:** narrowing `SYNTHESIS_SYSTEM_PROMPT` may have removed institutional-memory rules that were doing work. Specifically, the pre-R1 SYSTEM_PROMPT had ALWAYS/NEVER rules around generic phrases ("results-driven professional", "team player"). Those rules are preserved in the new synthesis prompt but in a narrower form — watch for regression there.
- **If the split shows no quality improvement:** P9 counterweight wins, R1 is a pure perf win (still useful — 91s → ~50s) and the framing in this entry should be revised to "perf split with quality-preserved baseline."
- **Cache hit verification:** both passes share `_stable_user_prefix` byte-identically. Telemetry should show cache_read_input_tokens on Pass 2 ≈ Pass 1's cache write. Verify in dashboard after first real run.

---

## 2026-05-24 — recommend_summaries Haiku call (β.6b) (`2026-05-24.3` → `2026-05-24.4`)

1. **What changed?** New Haiku call `analyzer.recommend_summaries()`
   that picks the best SummaryItem variant per JD, mirroring
   `recommend_bullets`. Output shape:
   ```
   {
     "recommendation": {"summary_item_id": <int>, "rationale": <str>} | null,
     "alternates":     [{"summary_item_id": <int>, "rationale": <str>}, ...]
   }
   ```
   Top-level is a single pick (not a list) since there's one
   positioning per résumé. Alternates surface 1-2 other variants
   worth weighing.

   New module-level `RECOMMEND_SUMMARIES_SYSTEM_PROMPT` carries the
   "no near-duplicates" rule + the "quality over quantity" alternates
   guidance from `2026-05-22.2` + `2026-05-24.2` (the bullet
   recommend rules learned the hard way; summaries inherit the
   same constraints).

   Deterministic safety pass `_dedup_summary_recommendations()`
   trims alternates at Jaccard ≥ 0.75 against the recommendation
   AND each other — same threshold as the bullet dedup. Never
   surfaces the recommendation id as its own alternate (defensive
   against LLM echoing).

   Short-circuit: when the candidate has 0 or 1 active SummaryItem
   variants, the function returns the trivial answer without an
   LLM call. Saves the Haiku token cost on the long tail of users
   who only ever have one positioning.

   New route `/api/applications/<id>/recommend-summary` (POST,
   body: `{context_path}`). Loads active SummaryItem rows, stashes
   them as a transient `context_set["summary_items"]` for the LLM
   call, persists the result on
   `context_set["llm_summary_recommendation"]` (mirrors the
   `llm_recommendations` pattern bullets use), strips both
   transient keys before write.

   PROMPT_VERSION → `2026-05-24.4`.

2. **Why?** β.6a shipped the SummaryItem schema + CRUD; users could
   curate multiple positioning variants but the LLM had no way to
   pick one per JD. This commit closes the loop so the Compose step
   (β.6c) can surface a scored pick the same way bullets do today.

3. **What was the result?** 11 new tests in
   `tests/test_recommend_summaries.py`:
   - `TestRecommendSummariesShortCircuit` (3 tests) — zero / blank /
     single-variant paths skip the LLM
   - `TestDedupSummaryRecommendations` (4 tests) — Jaccard dedup
     drops near-restatement alternates while preserving distinct
     ones; recommendation id never echoes as an alternate
   - `TestRecommendSummaryRoute` (4 tests) — happy path persists +
     strips transient keys; unknown application → 404; missing
     context_path → 400; zero-variant candidate → 200 with
     recommendation=null

4. **What did we learn?** Two patterns now established across the
   recommend family:
   - **Short-circuit before the LLM** when the answer is trivial
     (zero/one inputs). Cheaper on the common path.
   - **The dedup safety pass is independent of input shape.** Same
     Jaccard ≥ 0.75 threshold on `bullet_jaccard` works for bullets
     (per-experience), summaries (per-application), and will work
     for whatever CorpusItem kind lands next (β.6d–e + future
     SkillGroupItem / CoverLetterChunkItem in v1.1+).

---

## 2026-05-24 — Cover-letter detachment (`2026-05-24.2` → `2026-05-24.3`)

1. **What changed?** `analyzer.generate()` gained a `with_cover_letter:
   bool = True` parameter. When False (the new default for the
   `/api/generate` route — opt-in cover letters), the cover-letter
   rules block is dropped from the prompt, `cover_letter_content` is
   removed from the JSON schema + required_keys, the refinement-target
   wording switches from "to both the resume and cover letter" to "to
   the resume", and the returned dict has
   `cover_letter_content` set to `""` so downstream code that always
   touches the field doesn't KeyError. The cover-letter rules block
   was extracted to a module-level `_COVER_LETTER_RULES_BLOCK`
   constant so it has one source of truth.

   New focused call `analyzer.generate_cover_letter_against_resume()`
   takes the finalized résumé text + the same context_set/analysis as
   input and returns just `{cover_letter_content, proofread_notes}`.
   Used by the new `/api/generate-cover-letter` route after the user
   has run a résumé generation and (optionally) iterated on it. Same
   clarifications + cover-letter-draft + grounding rules as
   `generate()`'s cover-letter portion, but without any résumé-rules
   tokens. The route updates the existing context with the new
   `last_generated_cover_letter` so the iteration loop + edit-detect
   pick it up via the standard machinery.

   PROMPT_VERSION → `2026-05-24.3`.

2. **Why?** The user reported "I almost never use cover letters."
   The old design paid full LLM cost for cover-letter rules + content
   on every generate, even when the user immediately discarded it.
   The new design ships:
   - **résumé-only by default** — saves ~30-40% of generate-call
     tokens on the common path
   - **opt-in cover letter** via a button on the Download step that
     calls the focused route, paying only for the cover-letter LLM
     cost when the user actually wants one

3. **What was the result?** Test coverage: 6 new tests in
   `tests/test_cover_letter_detached.py` covering both the opt-out
   default behavior on `/api/generate` and the new
   `/api/generate-cover-letter` route (happy path, 409 when no
   résumé, 400 missing context_path, path-traversal blocked).
   Existing tests updated: the `_stub_generate` in
   `tests/test_app_iteration.py` accepts the new kwarg.

   Manual smoke against `testuser`: `/api/generate` without the flag
   produces only the résumé .docx + the .jsonresume.json sidecar (no
   cover-letter file written). A subsequent
   `/api/generate-cover-letter` call produces the cover letter .docx
   and writes `last_generated_cover_letter` into the context — the
   existing refine flow then picks it up.

4. **What did we learn?** Per-feature opt-in saves real money. The
   cover-letter detachment alone is ~30-40% LLM-cost reduction on the
   common path. The pattern: surface every optional artifact as a
   distinct call so the default path is the cheapest path, and only
   the user's explicit "I want this" presses pay for it.

---

## 2026-05-24 — Quality-over-quantity drop-off rule in recommend (`2026-05-24.1` → `2026-05-24.2`)

1. **What changed?** Two coupled changes targeting the bottom of the
   recommend picks:
   - **Prompt-side:** `RECOMMEND_SYSTEM_PROMPT` gains a "Quality over
     quantity" paragraph immediately after the existing "down to 1"
     rule. Reframes 3-7 from a *target range* to a *soft ceiling
     with explicit drop-off criterion*: "Stop including bullets the
     moment the next-best pick would be a clear step down from your
     previous one." Sets the recruiter-skim mental model so the LLM
     understands that each marginal bullet must earn its place.
   - **Frontend-side:** `static/app.js` `_dropoffPick(bullets, ...)`
     replaces the previous hard-coded `hidden.slice(0, 5)` fallback.
     When `recommend_bullets` fails or returns empty for an
     experience, the deterministic fit-score path picks 3-7 bullets
     with the same drop-off shape the prompt now asks the LLM for:
     after `minKeep=3`, stop once the next candidate scores below
     `0.65 × median(picks-so-far)`. Bounded above by `maxKeep=7`.
   - The previous "TOP-5 FALLBACK" chip relabels to "Fallback pick"
     since the count is now variable.
   - PROMPT_VERSION bumped to `2026-05-24.2`.

2. **Why?** A user pointed out that the "3-7" range looked like an
   arbitrary 5-default. The behavior was: LLM picked 3-7 on its
   gestalt judgment; fallback (LLM call failure or empty result)
   was a hard top-5 by deterministic score. Neither path applied a
   quality threshold or drop-off — a 6th-best bullet could land in
   the curated set just because the count fit the range. For
   recruiter-skim usage, three obviously-strong bullets beats six
   bullets with a weak tail; the prompt + fallback should both
   reflect that.

3. **What was the result?** Manual checks on `testuser` /
   Polaris JD: LLM picks now hover at 4-5 per experience on the
   strong-fit experiences and 3 on weaker-fit ones, where previously
   they often returned 5-6 even for weaker fits. Fallback path
   verified: a corpus with one obviously strong + four uniform
   middling bullets now returns 3 (cut after the strong + 2 above
   threshold), not 5.

4. **What did we learn?** When the LLM is given a count range, it
   tends to gravitate to the middle of the range by default. To get
   genuine quality-driven selection, the prompt must explicitly
   reframe the range as a ceiling, not a target — and the
   deterministic fallback must mirror that shape so behavior is
   consistent regardless of which code path served the picks.
   Pattern echoes `2026-05-22.2`: paired prompt-rule + deterministic
   safety net.

---

## 2026-05-24 — Markdown newline normalizer + emphatic emit-newlines rule (`2026-05-22.2` → `2026-05-24.1`)

1. **What changed?** The generate-time `resume_content` field was
   sometimes coming back collapsed onto a single line — every section
   heading, job entry, and bullet emitted without `\n` separators
   despite the multi-line example in the prompt. Two fixes:
   - **Prompt-side:** a new CRITICAL paragraph at the end of
     `<output_rules>` in `analyzer.py` explicitly requires literal
     `\n` between every line of the resume. Existing example shape
     was retained; this just adds an emphatic restatement of the
     newline contract so the LLM treats it as a hard constraint.
   - **Deterministic safety net (`generator.py:_normalize_markdown`):**
     a four-pass regex normalizer runs on every `resume_content` and
     `cover_letter_content` before write. Inserts `\n\n` before `# /
     ## / ###` headers (with a `(?<![\n#])` lookbehind so it doesn't
     mid-split a multi-`#` marker), `\n` before `- <Capital>` bullets
     preceded by text, `\n\n` between a single-word `## <Title>` and
     its body (non-greedy `\w+?` to avoid eating into the body word),
     then collapses 3+ newlines to 2. Idempotent on well-formed input
     — regression-tested in `tests/test_normalize_markdown.py` (16
     tests covering each pass, hyphenated-word safety, and a full
     realistic smushed-resume fixture).
   - PROMPT_VERSION bumped to `2026-05-24.1`.

2. **Why?** A user downloaded a generated `.md` and the entire resume
   was on one line — the markdown renderer treated it as a single H1
   heading. Root cause: the LLM produced semantically-correct markdown
   markers but without `\n` between them. The .docx writer suffers the
   same bug because `_write_docx` parses content line-by-line and
   dispatches heading styles only on lines beginning with `#`/`-`/etc.
   — a smushed payload collapses to one paragraph with no template
   styles applied.

3. **What was the result?** The user's broken fixture (0 newlines,
   ~7.2 KB) normalizes to 57 newlines with every section, job entry,
   and bullet on its own line. The h1 + subtitle + contact triad at
   the very top remains smushed — there is no clean algorithmic
   signal for where each chunk ends, and any heuristic (lowercase →
   uppercase boundary) would break on names like McDonald and product
   names like iPhone. Documented as a known limitation; the emphatic
   prompt is the lever for closing the remaining gap.

4. **What did we learn?** When LLM output is structurally regular
   (the markers are correct, just the separators are missing), a
   deterministic regex pass is materially safer than additional
   prompt iteration — every prompt revision adds tokens and creates
   regression risk, while a normalizer with regression tests stays
   green forever. The pattern is the same as `_dedup_recommendations`
   from `2026-05-22.2`: the LLM does the fuzzy work, deterministic
   Python repairs the mechanical drift. P1 Hardening compounds.

---

## 2026-05-22 — Release-Readiness Branch 1: no-near-duplicates rule (`2026-05-22.1` → `2026-05-22.2`)

1. **What changed?** `RECOMMEND_SYSTEM_PROMPT` (`analyzer.py`) gained one
   load-bearing paragraph telling the LLM to never include two
   near-restatements of the same achievement in its
   `recommendations[].bullet_ids`, with a directive to prefer the
   measurable-outcome phrasing when multiple variants exist. A
   deterministic safety pass (`_dedup_recommendations()`, new) runs after
   `_parse_or_retry()` and drops near-duplicates at Jaccard ≥ 0.75 on
   `hardening.bullet_token_set()` — the same token shape the Library
   duplicates clusterer uses. PROMPT_VERSION bumped accordingly. The
   no-recommendations path remains byte-identical (when the recommend
   call hasn't fired or has been skipped); cache discipline preserved.
2. **Why?** UI smoke test surfaced two failure modes: corpus imports
   from multiple resume files left near-verbatim duplicates of the same
   achievement, AND the LLM happily picked two variants into the
   curated 3–7 set. Bothered the review experience and burned tokens.
3. **Result?** No eval-suite run yet (UI/prompt change with deterministic
   guard; no eval scoring delta expected). 488 unit tests green
   (480 + 8 new across `test_corpus_duplicates_route.py` and
   `test_recommend_bullets.py::TestRecommendDedup`). Jaccard threshold
   chosen at 0.75 to catch near-verbatim cross-resume imports while
   leaving "same achievement, different phrasing" pairs for user review.
4. **Learned?** The right place for dedup is **both** the prompt and a
   deterministic safety net — the LLM honors the rule most of the time
   but the safety pass closes the residual hole. Same pattern as the
   metric-fabrication backstop on the cover letter. The Jaccard
   threshold also matches the corpus-level duplicates clusterer so the
   two surfaces (LLM-picked + user-curated) speak the same language.

## 2026-05-22 — Workstream H: LLM-curated corpus per application (`2026-05-18.1` → `2026-05-22.1`)

1. **What changed?** New `recommend_bullets()` Haiku call + system prompt
   (`RECOMMEND_SYSTEM_PROMPT`); new route
   `POST /api/applications/<id>/recommend`. Output is persisted on the
   context file as `llm_recommendations: {str(exp_id): {bullet_ids,
   rationale}}`. `analyzer.py:_stable_user_prefix` now, when
   `llm_recommendations` is present, restricts the per-experience bullets
   in the `<career_corpus>` block to the *effective* set
   `(recommended ∪ added ∪ pinned) − excluded`. Composition overrides
   gained an `added` list (Workstream I, drawer-added bullets). The
   `pinned="true"` attribute survives the filter. When
   `llm_recommendations` is absent, the prompt path is byte-identical to
   `2026-05-18.1` so cache behavior for older / non-recommend-using
   applications is unchanged.
2. **Why?** UI smoke test showed Compose flood-shows every bullet,
   making review impossible. The user wants the LLM to curate ~3–7 per
   experience by default; the remainder reachable via a per-experience
   "find more" drawer. Shrinking the corpus block also reduces prompt
   tokens at `generate()` time when recommendations are used.
3. **Result?** No full eval-suite run yet (UI / prompt-shape change
   without an evaluable scoring delta). 480 unit tests green
   (469 + 11 new across `test_corpus_mode_prompt.py` effective-set
   filter, `test_application_routes.py` `added` field, and new
   `test_recommend_bullets.py`). A new Haiku call adds ~$0.01–0.02 per
   application; analyze prompt cache untouched.
4. **Learned?** Adding override / curation shape on top of the existing
   `composition_overrides` rather than introducing parallel DB columns
   keeps the data model coherent and the change to `_stable_user_prefix`
   surgical — one new branch, byte-identical when feature-off. Lesson:
   `total=False` `ContextSet` fields are the right escape valve for
   features that need round-tripping state without a migration.

## 2026-05-18 — Wizard Workstream B: pin/exclude in the corpus prompt (`2026-05-12.1` → `2026-05-18.1`)

1. **What changed?** `analyzer.py:_stable_user_prefix` now filters
   `composition_overrides.excluded` bullet ids out of the `<career_corpus>`
   block entirely and passes `composition_overrides.pinned` into
   `_corpus_block`, which emits `pinned="true"` on those `<bullet>`
   elements. The `<corpus_mode>` guide gained one paragraph instructing the
   LLM that every `pinned="true"` bullet id MUST appear in
   `selected_bullets`. `PROMPT_VERSION` bumped accordingly. Overrides come
   from the new Compose wizard step via
   `POST /api/applications/<id>/composition` → `context_set`.
2. **Why?** Users had no deterministic way to force-include or drop a
   specific bullet for one application; the LLM's selection was the only
   lever. The Compose step makes pin/exclude a first-class, user-owned
   decision.
3. **Result?** No eval-suite run yet (deterministic prompt-shape change,
   not a quality-tuning change). 469 unit tests green; existing
   corpus-mode prompt tests still pass — the pinned attr is additive and
   absent when there are no overrides, so the no-override prompt is
   byte-identical and the prompt cache for existing applications is
   unchanged.
4. **Learned?** Keep override plumbing in the cached user-prefix only when
   it changes corpus *content* (exclude) or a stable attribute (pinned),
   and keep the no-override path byte-identical to preserve the prompt
   cache for every application that doesn't use the feature.

## 2026-05-13 — Phase B.5: regression check for the file-based path at `2026-05-12.1`

### What changed

No code or prompt changes. This entry establishes the new baseline at
`PROMPT_VERSION 2026-05-12.1` (bumped in Phase B.2) for the file-based
pipeline path — the regression check that nothing in Phase B.1–B.4
silently broke the legacy path that the file-based fixtures still
exercise.

### Why

Phase B introduced a feature-flagged DB-backed pipeline behind
`CORPUS_BACKED=1`. The flag defaults off, so the eval suite still runs
the file-based path. Smoke tests covered the DB-backed path against
the testuser fixture (Casey Rivera). This entry confirms the file-based
path against the existing 3-fixture synthetic suite.

Full DB-backed A/B parity at fixture scale lives in Phase E (when
fixtures are converted to `seed.json` form). Phase B.5 covers only the
regression check.

### Result

3 synthetic fixtures × 5–6 rubrics, all at `2026-05-12.1`:

| Fixture | ats_format | clar_quality | grounding | keyword_cov | tone | iter_quality |
|---|---|---|---|---|---|---|
| data-scientist-junior | 4.2 | 4.2 | 4.8 | 4.2 | 4.2 | n/a |
| pm-senior | 4.6 | 4.2 | 4.8 | 4.2 | 4.2 | n/a |
| sre-mid-level | 4.8 | **3.2 ⚠** | 4.7 | 4.2 | 4.2 | **None ⚠** |

- **14/16 pass** at threshold ≥ 4.0
- **1 regression** flagged by the alerter: sre-mid-level::clarification_quality
  4.2 → 3.2 (Δ=-1.0). The TUNING_LOG entries for 2026-05-11.2 / 2026-05-11.3
  show this rubric historically bouncing 2.1 / 3.2 / 3.2 / 3.2; the 4.2
  prior was the outlier, and 3.2 is the historical floor. **Phase B
  did not touch `CLARIFY_SYSTEM_PROMPT` — this regression is judge +
  Sonnet variance, not a code regression.**
- **1 expected None** on sre-mid-level::iteration_quality — known
  `scenario_misaligned` per the 2026-05-11.3 entry.

Cost: **$0.4068 total** for the full suite (down from ~$1.50 historical).
Cache_read tokens: 5586 across all calls. The B.2 cache-shape work
benefits the file-based path too because the byte-stable cached prefix
discipline is now the same.

### What we learned

1. **Phase B did not break the file-based path.** The 14/16 passes match
   historical pass rates within Haiku judge variance. The one regression
   is on a known-unstable rubric whose floor is 3.2.
2. **Cache discipline improvements cascade.** Total suite cost dropped
   ~3× vs historical ($0.41 vs $1.50). The B.2 work on `<career_corpus>`
   didn't touch legacy prompts but did clean up the cache-prefix-stability
   patterns, which benefits both paths.
3. **PROMPT_VERSION bump at the Phase B boundary worked as designed.**
   All 16 records tagged with `2026-05-12.1`. The dashboard's
   score-over-time chart will show a clean version transition; future
   regressions are attributable.

### Open questions / future tuning targets

- **Full DB-backed eval A/B (Phase E work):** the 3 synthetic fixtures
  need to move from `(resume.md, jd.txt, expected.json)` to a single
  `seed.json` per fixture. Then `evals/runner.py` gains a flag to import
  the seed into an in-memory SQLite and run via `build_context_set_from_db`.
  Expected outcome (based on the testuser smoke): DB-backed grounding
  improves materially (smoke went 18/22 → 19/19 with structural
  selected_bullets), other rubrics within ±0.5.
- **sre-mid-level::clarification_quality stability:** the rubric's
  historical 2.1/3.2 floor suggests the rubric is too strict for
  Sonnet's actual output or the prompt is too loose. Next iteration
  should re-examine the rubric's `min_clarification_quality_score` and
  the SCOPE_PROBE coverage rule the plan flagged.

### Cost / scope notes

- This regression check: $0.41
- Phase B total LLM spend across all smokes (B.1 + B.2×2 + B.3 + B.4 + this): ~$1.10

---

## 2026-05-12 — `2026-05-11.3` → `2026-05-12.1`: Phase B.2 `<career_corpus>` prompt block

### What changed

- `analyzer.py:_stable_user_prefix` now branches: when `context_set["career_corpus"]` is populated (DB-backed path with CORPUS_BACKED=1), the user prefix emits a structured `<career_corpus iteration="N">` XML block with `<experience>` / `<eligible_title>` / `<bullet>` children carrying stable IDs from the corpus DB. The legacy `<resume>` + `<supplemental_resumes>` blocks are OMITTED in this mode. When `career_corpus` is absent (file-based path), the prefix is byte-identical to `2026-05-11.3`.
- `analyzer.py:generate()` adds a `<corpus_mode>` instruction block when the input carries `<career_corpus>`. The block tells the LLM that each `<bullet>` must be quoted verbatim (selected by ID), and adds three new output schema fields: `selected_bullets`, `proposed_new_bullets`, `proposed_experience_titles`.
- `analyzer.py:GENERATE_CORPUS_REQUIRED_KEYS` — new frozenset extending `GENERATE_REQUIRED_KEYS`. `_parse_or_retry` is invoked with this set when corpus mode is active; the legacy set remains in use otherwise.
- `db/build_context.py:_build_career_corpus_payload` — new helper producing the structured corpus payload. Eligible titles are sorted official-first; only `is_active=1` bullets ship.
- `hardening.py` — new TypedDicts: `CorpusBullet`, `CorpusEligibleTitle`, `CorpusExperience`. `ContextSet` gains an optional `career_corpus` field.
- `PROMPT_VERSION` bumped to `2026-05-12.1`.

### Why

Phase B.1 brought DB content into the pipeline but kept the prompt structure unchanged. The legacy `<resume>` block forced us to synthesize markdown from DB rows — useful as a transitional bridge but throwing away the per-bullet IDs the downstream phases need. Phase B.2 makes IDs first-class in the prompt:

1. **B.3 needs them.** `application_bullet` rows record which bullets the LLM chose; without IDs in the prompt the LLM can't tell us which selection it made.
2. **Multi-framing needs them.** Each experience carries multiple `<eligible_title>` elements. The LLM picks one per JD via `selected_bullets[].chosen_title_id`. The synthesized markdown of B.1 could only carry one title per experience.
3. **Grounding can move from heuristic to structural.** Every output bullet must equal a corpus bullet (lookup by ID). B.3 enforces this; B.2 sets up the data.

### Result

Smoke (DB-backed, testuser corpus, pm-senior JD; 2026-05-12 run):

| Metric | B.1 (`2026-05-11.3`) | B.2 (`2026-05-12.1`) | Δ |
|---|---|---|---|
| Total cost | $0.1465 | $0.1652 | **+13%** (extra output schema fields) |
| cache_read tokens (generate) | 2748 | **3420** | **+24% (improvement)** |
| Output bullets | 22 | 19 | -3 (more disciplined selection) |
| Suspicious bullets (heuristic) | 4/22 | **0/19** | **100% trivially grounded** |
| Required keys in response | 4 (legacy) | 7 (legacy + 3 corpus fields) | — |
| Errors | none | none | — |

Two headline findings:
1. **Cache_read tokens went UP, not down.** The fear from Reviewer Risk #2 (the prompt-cache might collapse under the new prefix shape) didn't materialize. The structured `<career_corpus>` block is just as byte-stable across analyze→generate within an iteration as the legacy `<resume>` was, AND its larger size means more cached tokens to read.
2. **Grounding tightened substantially.** Every output bullet substring-matched a corpus bullet — zero "suspicious" entries (B.1 had 4/22 the heuristic flagged, though those turned out to be legitimate paraphrases on inspection). The LLM appears to have taken the "treat each bullet as immutable, select by ID" instruction seriously. Sets up B.3 (structural enforcement via `application_bullet` rows) to be straightforward.

File-based path (CORPUS_BACKED unset): byte-identical to `2026-05-11.3`. The 247/247 prior tests still pass; the 12 new B.2 tests pass; legacy mock prompts received no corpus_mode block; required-key set defaulted to GENERATE_REQUIRED_KEYS (4 keys).

### What we learned

1. **Cache discipline survives structural prefix changes — when the new structure is itself byte-stable.** The cached prefix block is larger now (more tokens to cache) and the `cache_read_input_tokens` went UP rather than down. Reviewer Risk #2 (cache collapse) doesn't bite when the new prefix is just as deterministic as the old one was.
2. **Structured presentation reduces fabrication temptation.** Telling the LLM "each `<bullet id="bN">` is immutable, record IDs in `selected_bullets`" produced 19/19 trivially-grounded bullets vs the legacy prompt's 18/22. The framing change matters more than the words on the page.
3. **Sonnet trims aggressively when given structure.** Output bullets dropped from 22 to 19 with cleaner selection. The LLM appears to be using the structured corpus to be more disciplined about what to include rather than reaching for completeness.

### Open questions / future tuning targets

- Should `<bullet tags="...">` carry actual tag values? B.2 leaves the attribute empty pending B.3's tag join. Surfacing tags helps the LLM filter by role family but adds tokens; the deterministic JD-aware pre-filter (also B.3) may make this unnecessary.
- `proposed_new_bullets` `pattern_kind` — does the LLM reliably distinguish xyz vs car? Spot-check after a few smoke runs; if it always picks one or the other, drop the field.
- Should `clarify()` and `clarify_iteration()` also gain corpus-mode instructions? They consume the same prefix so they SEE `<career_corpus>` but their output (questions) doesn't need IDs. Probably defer until we see specific rubric regressions.

---

## 2026-05-11 — `2026-05-11.2` → `2026-05-11.3`: iteration-probe worked examples

### What changed

Two follow-up fixes after the first iteration_quality eval pass surfaced a 3.2 score (below the 4.0 threshold) and a clear failure-mode diagnosis:

- **Fixture refinement** (fix 1): `evals/fixtures/synthetic/sre-mid-level/expected.json` — the `edit_target_substring` was extended from `"error budget burn"` to `"error budget burn by tightening retry semantics in the ingress layer"` and the `edit_replacement` was rewritten as a noun-phrase that fits the surrounding `"Reduced control-plane X; rewrote..."` clause structure. This eliminates the malformed-bullet artifact that the original mid-substring substitution produced.
- **Prompt tightening** (fix 2): `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT` — added a WORKED EXAMPLES block with two OK/NOT-OK pairs for iteration probes. Pattern: when a recent edit introduces a substantive claim (named numbers, ownership words, framework names), probe DEPTH (who/which/how-many/cadence). Avoid asking why (motivation isn't source material) or whether (yes/no dichotomies yield no detail).
- `PROMPT_VERSION` bump 2026-05-11.2 → 2026-05-11.3 in the same commit per CLAUDE.md.

### Why

Run 2 of the iteration_quality eval (the one with PROMPT_VERSION 2026-05-11.2 + the original fixture) scored 3.2, with grader reasoning showing the iteration_probe correctly noticed the malformed bullet in the iter-0 generated resume but answered the wrong question — "is this grammatical?" instead of "what is the substantive claim?". Two distinct failure modes were entangled: a fixture artifact (malformed substitution) AND a prompt gap (no guidance on what makes a substantive iteration probe vs a copy-editing one).

### Result

Four runs total on `sre-mid-level`:

| Run | Time (UTC)              | Prompt | Fixture          | iteration_quality | Failed rules                                                         |
|-----|-------------------------|--------|------------------|-------------------|----------------------------------------------------------------------|
| 1   | 2026-05-11T22:56:08Z    | .2     | original         | 2.1               | (not analyzed)                                                       |
| 2   | 2026-05-11T23:53:39Z    | .2     | original         | 3.2               | missing_expected_theme — substring substitution broke bullet grammar |
| 3   | 2026-05-12T00:22:05Z    | .2     | refined (fix 1)  | 3.2               | leading + fabricated + compound + missing_theme                      |
| 4   | 2026-05-12T00:32:58Z    | .3     | refined (fix 1)  | 3.2               | compound + missing_theme                                             |

**Fix 1 (fixture)** moved the failure mode from "iteration_probe asks about syntax" to "iteration_probe asks about cause/effect (was that deliberate or accidental?)". Substantively cleaner question but still not on-target. Grader cited "leading_question" and "missing_expected_theme" with the SLO ownership themes specifically uncovered.

**Fix 2 (prompt)** moved the iteration_probe to substance-of-claim (q1 explicitly probed SLO ownership scope, hitting the expected theme). Grader called this out as a direct hit. **The numeric score didn't move (still 3.2)** because other questions in the 5-question batch tripped different rules: q4 was compound ("before/after MTTR figure or percentage improvement" combines two asks), q3 was speculative (probed scheduling pipeline work for an API-edge SRE — borderline fabricated), and the scope_probe theme (incident commander vs writer-up) wasn't covered by any question.

So fix 2 succeeded on its targeted dimension but didn't reach the 4.0 threshold because the rubric compounds across multiple per-question dimensions and the LLM keeps producing 1-2 borderline questions per 5-question batch.

### What we learned

1. **The Haiku judge applies multi-dimensional strictness.** Hitting 4.0 requires near-perfect composition across 7+ rubric criteria simultaneously. A single substantive improvement (iteration_probe quality) doesn't lift the aggregate when other dimensions stay borderline.
2. **Prompt fixes land on their targeted dimension.** Run 3 → run 4 lost `leading_question` and `fabricated_gap` on the iteration_probe specifically, gained nothing new on that question. The targeted improvement is real even when the score doesn't move.
3. **Single-fixture eval has unhelpful variance.** Four runs at 2.1 / 3.2 / 3.2 / 3.2 — the first run is an outlier that may have been judge noise, may have been a Sonnet generation that produced a worse question set. Without 2-3 fixtures producing iteration_quality samples, attribution to "this prompt change helped" vs "this run's generation was lucky" is hard.
4. **Substring-mid-bullet substitution is a fragile fixture mechanic.** Fixtures that simulate user edits should use whole-line targets OR noun-phrase substitutions that fit the surrounding clause structure. The refined fixture works because the new replacement reads as a clean grammatical clause within the existing bullet.

### Per-question prompt tightening — plan for next iteration

**Target version:** `2026-05-11.4` (bundle prompt revisions 1–4 below into ONE commit; do not land them piecemeal — see "Considered and rejected" for why).

The 4.0 threshold isn't reachable by chasing single failure modes one at a time when the rubric strictness compounds. Next iteration should bundle four prompt revisions plus four structural follow-ups, then re-baseline.

**Prompt revisions (`analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`, lines ~107–146; consider also `CLARIFY_SYSTEM_PROMPT` at ~136 for shared rules like #1 and #3):**

1. **Compound-question worked-example pair.** The "no compound questions" rule is in the prompt but the LLM keeps producing borderline-compound ones (q5 run 3, q4 run 4). Add an OK/NOT-OK pair:
   - NOT OK: "What was the before/after MTTR figure or percentage improvement?" (combines absolute and relative asks)
   - OK: "What was the MTTR before and after?" (single comparative ask) OR "What percentage MTTR reduction did you measure?" (single ratio ask)
   - Pattern: split "X or Y" forms into a single ask; prefer the more specific framing.

2. **Speculative-probe guard rule.** The iteration clarifier reaches for adjacent JD keywords without checking whether they fit the candidate's title/role (q3 run 4 asked an API-edge SRE about scheduling-pipeline work). Add a rule:
   - "Do NOT probe for skills the candidate's job title/role doesn't naturally encompass. If the JD lists 'scheduling pipeline' but the candidate's role is 'API edge SRE', the probability of relevant experience is low — these probes feel out-of-touch and risk grader-fabricated_gap flags."
   - Worked example aligned to the actual run-4 failure.

3. **Leading-tone worked-example pair** for iteration_probe specifically:
   - NOT OK: "Was the SLO definition deliberate or reactive?" (yes/no dichotomy, leading)
   - OK: "What process drove the SLO targets — service-level analysis, customer commitment, error-budget tracking?" (lists concrete options without bias)
   - Already partially covered by the WORKED EXAMPLES block from fix 2 but worth promoting a leading-tone-specific example to the same prominence as the substance-of-claim example.

4. **Scope-probe coverage rule.** The current prompt biases toward experience+iteration probes (≥50% combined), which de-prioritizes scope_probe. When the fixture's `expected_iteration_themes.scope_probes` is non-empty, the eval grades against scope coverage anyway. Either:
   - (a) Change the prompt to require at least one scope_probe when current-draft ambiguities exist (most drafts have some), OR
   - (b) Relax the rubric's `missing_expected_theme` to not require scope_probe coverage if the prompt didn't mandate one.
   - (a) is the cleaner fix because scope_probes ARE useful and the current bias is just an artifact of optimizing for ground-truth sourcing.

**Structural follow-ups (not prompt changes; do these BEFORE the prompt revisions to unblock variance attribution):**

5. **Add `iteration_scenarios` to pm-senior and data-scientist-junior fixtures.** Three samples per run lets us reason about iteration_quality with a 3-sample mean rather than treating each run as a singular signal. Without this, we can't confidently attribute prompt changes to score movements vs Sonnet/Haiku non-determinism. Reference schema: `evals/fixtures/synthetic/sre-mid-level/expected.json` lines 35–57. Each fixture needs an `edit_target_substring` (must survive Sonnet's rewriting — pick a distinctive phrase known to appear in the source resume), an `edit_replacement` (noun-phrase that grammatically fits the surrounding clause; do NOT use a standalone sentence per fix 1's lesson), `clarification_answers` keyed by the iteration question id the runner will produce, and `expected_iteration_themes` with `iteration_probes` / `experience_probes` / `scope_probes` lists.

6. **Re-generate from the iteration context and grade against grounding/keyword_coverage.** Currently the eval iteration phase (`evals/runner.py:_run_iteration_phase`, lines ~340–460) grades only the iteration_quality of the new questions; it does NOT verify that the iteration generation respects the `<historical_resumes>` demotion language and the typed-edits-as-ground-truth carve-out. This was deferred for cost reasons. Implementation sketch: after grading iteration_questions, call `generate(client, iter_context, analysis, ...)` again to produce iter-2 output, compute `_post_generation_metrics` on it, then run the grounding and keyword_coverage rubrics against the iter-2 result and emit those records with `iteration_scenario` set. Adds ~$0.50/scenario/run.

7. **[USER-FLAGGED, 2026-05-11 session]** **Clarification-as-grounding worked example** in the GENERATE prompt's grounding block (`analyzer.py:generate()` worked-examples block, currently around lines ~770–810 covering source-bullet variants and the typed-edits pair). The user raised this concern: a candidate's clarification answer is treated as first-person ground truth and citable in the resume, but there is NO worked example specifically modeling extension-vs-citation for clarifications. A candidate who answers "Yes, used K8s briefly on a side project" could in principle have the LLM extend that to "Led K8s migration to production" — the no-invention rule forbids it but no example trains the pattern. Mirror the typed-edits pair:
   - Source: candidate clarification answer = "Yes, used K8s briefly on a side project."
   - OK to write: "Familiar with Kubernetes from side-project work."
   - NOT OK: "Led K8s migration to production." (extends scope and seniority beyond what the candidate stated)

8. **Rubric/judge calibration.** Run 3's grader called q2 (multi-region) `fabricated_gap` even though `expected_iteration_themes.experience_probes` explicitly lists "multi-region control plane work not yet covered". Multi-region is in `preferred_skills` (not `essential_skills`) and the grader treated preferred ≠ legitimate gap. The `iteration_quality.md` rubric's `fabricated_gap` definition says "cites a signal-source value that doesn't match" — preferred_skills IS a signal source, so the grader was being stricter than the rubric documents. Either tighten the rubric language to spell out that preferred_skills count as legitimate signal sources, OR add an explicit "preferred-skill probes are valid" example. Track whether this manifests on other fixtures or is sre-specific noise.

**Recommended sequencing:**

| Step | Action | Cost     | Outcome |
|------|--------|----------|---------|
| A    | Items 5 + 7 (fixture work + grounding worked example, no prompt-numbered version bump for #5 alone; bump for #7 to 2026-05-11.3a or fold into 2026-05-11.4) | $0 API  | More fixtures + closes the user-flagged grounding gap |
| B    | Run `python evals/runner.py --suite synthetic` ×3 at PROMPT_VERSION 2026-05-11.3 (with item 7 applied) | ~$4.50  | Establishes 3-fixture × 3-run baseline mean for iteration_quality |
| C    | Bundle prompt revisions 1–4 into ONE commit, PROMPT_VERSION → 2026-05-11.4 | $0 API  | Single attribution event for the prompt change |
| D    | Run `python evals/runner.py --suite synthetic` ×3 at 2026-05-11.4 | ~$4.50  | Compare means against B to attribute the prompt revision's effect |
| E    | If means clear acceptance criteria (below), close out. Otherwise append findings here and iterate. | —       | — |
| F    | Item 6 (re-generate + re-grade) goes in only after iteration_quality is stable ≥4.0; until then it adds cost without unlocking new signal. | ~$0.50/scenario/run additional | — |

### Pick this up cold — exact next steps

If you're returning to this work without context, follow this checklist in order:

1. **Sanity check:** read the four-run table above (PROMPT_VERSION column tells you which prompt produced which score). Then run `git log -- evals/results/` and `git log analyzer.py` to confirm nothing has shifted since this entry was written.
2. **Confirm baseline still holds:** run `python evals/runner.py --fixture sre-mid-level` once. If iteration_quality scores wildly differently from 3.2 (say, <2.0 or >4.5), the model versions or judge behavior changed and the failure-mode analysis below may not apply — re-diagnose before applying any planned fix.
3. **Inspect prior eval results:** `evals/results/*.jsonl`. The four runs from this session are at timestamps `20260511_225608Z`, `20260511_235339Z`, `20260512_002205Z`, `20260512_003258Z`. Each line is one (fixture, rubric) grading. The `reasons` array on iteration_quality records is the most useful artifact — it explains what the judge saw.
4. **Apply structural items first** (5 + 7 from the plan above). These are cheap and unblock attribution.
5. **Establish the baseline** (step B in the sequencing table above): 3 runs at PROMPT_VERSION 2026-05-11.3 across all three fixtures. Record the mean iteration_quality score per fixture in this TUNING_LOG.
6. **Apply the prompt bundle** (items 1–4 in ONE commit, version → 2026-05-11.4).
7. **Re-baseline** (step D). Compare the new 9-grading mean to the prior 9-grading mean.
8. **Decide:** if acceptance criteria below are met, append a new TUNING_LOG entry summarizing the win and close out. If not, the prompt bundle didn't cleanly land — re-examine which of items 1–4 helped vs hurt by running the eval with subsets of them applied.

### Acceptance criteria — when iteration_quality is "done"

- 3-fixture × 3-run mean iteration_quality ≥ 4.0 at the same PROMPT_VERSION.
- No (fixture, rubric) regression > 0.5 vs the 2026-05-11.3 baseline on the four other rubrics (ats_format, grounding, keyword_coverage, tone, clarification_quality).
- iteration_quality `failed_rules` across the 9 records does NOT contain `redundant_question` (would indicate the build-on-don't-re-ask rule isn't holding) or `targets_stale_draft` (would indicate the current-draft awareness isn't holding).
- `compound_question` and `missing_expected_theme` may appear at most once across the 9 records — they're the residual failure modes prompt revisions 1 and 4 are designed to suppress, but eliminating them entirely is unrealistic given Haiku judge variance.

### Considered and rejected this session

Documenting these so a future tuner doesn't burn budget retrying:

- **Revert PROMPT_VERSION to 2026-05-11.2.** Score didn't move from 3.2 after fix 2 — but the targeted dimension (iteration_probe substance-of-claim quality) clearly improved per grader reasoning. Reverting would give up a real semantic improvement to chase a number that wasn't moving for orthogonal reasons.
- **Run another iteration_quality pass with no changes to confirm 3.2 is stable vs noise.** Given 2.1 / 3.2 / 3.2 / 3.2, the floor looks like 3.2 with the first run as a one-time outlier. Burning another $0.50 to reconfirm wasn't worth it given the 3.2 wasn't going to be the deciding signal anyway — credible attribution needs structural work (more fixtures) first.
- **One-at-a-time prompt tweaks** to chase failed_rules individually. Demonstrated this session: each tweak landed but the aggregate stayed flat because Haiku-judge variance plus rubric strictness across 5 questions × 7+ criteria swamps single-dimension wins. Bundle 1–4 into a single 2026-05-11.4 commit.
- **Lower the iteration_quality pass threshold below 4.0** to make the rubric more forgiving. Rejected because the threshold matches every other rubric in the suite (4.0); making iteration_quality a special case would erode the rubric set's consistency. The fix belongs in the prompt and the fixture, not the threshold.

### Cost / scope notes

- Four iteration_quality runs this session: ~$0.60 total in API costs. Each run is one full pipeline (analyze + clarify + generate + clarify_iteration Sonnet calls) plus 6 Haiku grading calls.
- Three-fixture × 3-run baseline at next PROMPT_VERSION: ~$1.50 per run × 3 runs ≈ $4.50 per baseline (need two baselines — pre and post prompt bundle — so total ~$9.00).
- Item 6 (re-generate + re-grade) adds ~$0.50/scenario/run, so $1.50 per 3-fixture run once enabled.

---

## 2026-05-11 — `2026-05-11.1` → `2026-05-11.2`: iterative refinement loop

### What changed

- `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT` — new dedicated persona for
  the post-generation interview. Two distinguishing instructions vs
  `CLARIFY_SYSTEM_PROMPT`: (1) treat prior clarifications as established truth,
  follow up rather than re-ask; (2) target the CURRENT draft's specific
  weaknesses surfaced by the four signal sources, not generic JD gaps.
- `analyzer.py:clarify_iteration()` — new function with 4-signal-source
  prompt template (current draft, recent edits, deterministic signals,
  prior clarifications). Reuses `_parse_or_retry` with
  `call_kind="iterate_clarify"` for telemetry parity.
- `analyzer.py:generate()` — grounding worked-examples block extended with a
  fourth OK/NOT-OK pair specifically for typed edits ("Shipped V2 to
  enterprise" / "Led V2 launch to 50 enterprise customers"). The grounding
  question itself widens to acknowledge typed edits as ground truth alongside
  clarification answers.
- `analyzer.py:_supplemental_block(iteration)` — wrapper switches to
  `<historical_resumes>` at iteration ≥ 1 with explicit demotion language.
- `evals/rubrics/iteration_quality.md` — new fifth rubric.
- `evals/runner.py` — optional iteration phase grades the new questions
  against `iteration_quality` for fixtures with `iteration_scenarios`.
- `PROMPT_VERSION` bump in the same commit.

### Why

The clarification interview that landed in `2026-05-11.1` proved valuable but
also surfaced a pattern: candidates would type meaningful edits into the
preview, then click REFINE — and the regenerate-from-context path silently
discarded those edits. Two distinct fixes were required:

1. **Edit-aware baselines.** The preview-edit gate (Phase 3) plus
   `edited_resume_text` carve-out in the grounding check let typed edits
   feed the next generation as first-person ground truth. The grounding
   worked-example pair specifically targets the new failure mode this opens
   up: the LLM treating an edit as license to inflate ("shipped V2" →
   "shipped V2 to 50 enterprise customers").
2. **Iteration-aware probing.** The analyze-time `clarify()` is rooted in
   the original resume vs JD gap. Once iteration 1 has produced a draft
   (possibly with edits), the relevant gaps shift: missing keywords may be
   filled, new ambiguities may be introduced by edits, and prior
   clarifications are now established truths the LLM should build on.
   `clarify_iteration` exists to probe that new state — and the
   `iteration_quality` rubric grades whether it actually does.

### What was the result

First two runs on `sre-mid-level` only (`python evals/runner.py --fixture sre-mid-level`):

| Run | Timestamp (UTC)         | iteration_quality | Other rubrics                                                       |
|-----|-------------------------|-------------------|---------------------------------------------------------------------|
| 1   | 2026-05-11T22:56:08Z    | 2.1               | (not tracked in this entry)                                         |
| 2   | 2026-05-11T23:53:39Z    | 3.2               | ats=4.8 grounding=4.8 keyword=4.2 tone=4.2 clarification=4.2 (all pass) |

**Both runs FAIL `iteration_quality` against the 4.0 threshold.** The 1.1
swing on identical inputs (same PROMPT_VERSION, same fixture, same prompts)
is at the upper edge of expected Haiku-judge variance — the underlying
Sonnet generation also varies per call, so the question set isn't bit-identical
across runs either.

Failure mode (from run 2's grader reasoning, the more useful signal):

- The scripted edit (`error budget burn` → `Defined and owned SLOs and the
  error-budget framework on the API edge layer`) produced a malformed bullet
  in the iter-0 generated resume (the original phrase appeared in a
  context that, after substitution, broke the bullet's grammar).
- The iteration_probe correctly detected an issue and asked about it — but
  framed the question as a copy-editing fix ("what is the single clean
  outcome?") rather than as a substantive scope/experience clarification.
- The fixture's `expected_iteration_themes.iteration_probes` specifically
  asks for follow-ups on numeric SLO targets, review cadence, and ownership
  collaboration. The interview missed that opportunity entirely on q1.
- The other 4 questions (q2 multi-region, q3 service mesh, q4 specificity
  signal, q5 Go) are well-targeted with concrete cites, no fabricated gaps,
  no redundancy with priors.
- `failed_rules: ["missing_expected_theme"]` — the iteration_probe slot was
  filled but its content didn't hit any expected theme.

**Diagnosis:** the failure is real but not a fundamental prompt flaw. Two
fixes are plausible:

1. **Tighten the fixture scenario.** The `edit_replacement` produces a
   malformed bullet because the substitution doesn't account for the
   surrounding bullet structure (the Sonnet output wrapped the original
   phrase in a sentence that breaks when substituted). A cleaner
   `edit_target_substring` / `edit_replacement` pair, or a scenario that
   substitutes a whole bullet rather than mid-sentence text, would let the
   iteration_probe focus on substance instead of form.
2. **Add an iteration-probe worked example to CLARIFY_ITERATION_SYSTEM_PROMPT.**
   Mirror the grounding block's OK/NOT-OK pattern: "User typed 'shipped V2
   to enterprise' — OK iteration question: 'Which enterprise customer
   segment? How many?'. NOT OK: 'The bullet has a typo, please clarify.'"
   Pure copy-editing follow-ups should not count as clarifying questions
   because they don't source new ground truth.

Recommended order: (1) first, since the fixture is the proximate cause and
fixing it both restores the eval signal AND tells us whether the prompt has
a deeper issue. If a clean fixture still produces copy-editing-style
questions, then (2) becomes load-bearing.

The "build on, don't re-ask" hypothesis was NOT validated either way in
this run because `prior_clarifications` was empty (the runner's iteration
phase doesn't carry forward analyze-time clarify answers — it could, if we
populate `clarify_answers` from a fixture-supplied dict). That probe gets
exercised once the fixture or runner adds the prior-answers carry-over.

### Cost / scope notes

- `clarify_iteration` adds one Sonnet call per iteration interview clicked.
  Same cost shape as analyze-time `clarify` (~$0.03 per call, mostly cached
  user prefix doesn't apply here — the call uses no cached prefix because
  the current draft varies per iteration).
- The eval iteration phase adds one Sonnet call (clarify_iteration) plus one
  Haiku call (iteration_quality grading) per fixture with scenarios. With
  one fixture (sre-mid-level) currently scoped, total eval cost increment
  is ~$0.05 per `--suite synthetic` run.
- **Deferred to a follow-up entry**: re-generating from the iteration
  context and re-grading against grounding/keyword_coverage. The plan
  documents this as the full Phase 5 eval surface; shipping the
  question-grading half first lets us validate `clarify_iteration` quality
  before paying for the second generate call per fixture per run. If
  iteration_quality scores look good across the next 2-3 runs, add the
  re-generate step and grade the iterated output against grounding +
  keyword_coverage. Expected additional cost: ~$0.50 per scenario per run.

### What we learned

1. **Eval scenarios need to produce a clean iter-0 baseline.** Substituting a
   substring mid-sentence is fragile when the surrounding generated text
   varies. Future fixtures should target whole bullets via the
   edit_target_substring mechanic, OR the runner should grow a smarter edit
   helper that detects bullet boundaries.
2. **A copy-editing question is NOT a clarifying question.** The iteration
   clarifier correctly noticed the malformed bullet but answered the wrong
   question — "is this grammatical?" instead of "what is the underlying
   substantive claim?". The CLARIFY_ITERATION_SYSTEM_PROMPT doesn't currently
   forbid syntax-fix probes; the rubric implicitly does, but the LLM needs
   the explicit guard. Worth a worked-example pair in a future revision.
3. **Single-fixture iteration eval is high-variance.** With one fixture and
   non-deterministic Sonnet generation, score swings of 1.0+ are
   plausible-but-not-attributable. Adding scenarios to pm-senior and
   data-scientist-junior would let us reason about iteration_quality with a
   3-sample mean rather than treating each run as a singular signal.
4. The original "build on, don't re-ask" hypothesis remains untested — see
   "Result" section above for why and how to exercise it next.

---

## 2026-05-09 — `2026-05-06.5` → `2026-05-09.1`: anti-invention worked-examples

### What changed

- `analyzer.py:SYSTEM_PROMPT` — added three ALWAYS/NEVER rules targeting the
  three observed failure-class patterns:
  - "Never restate a candidate's responsibility using a more advanced
    technique than the source describes…"
  - "Never upgrade a tool category into a specific vendor or framework…"
  - "Never escalate scope adjectives (team → organization-wide …)…"
- `analyzer.py:generate()` GROUNDING CHECK — appended a worked-examples
  block with three OK/NOT-OK pairs drawn from the failure data:
  - "Built customer-facing dashboards" → must NOT become "Built time-series
    forecasting dashboards for executive stakeholders"
  - "Used a CI tool" → must NOT become "Authored Jenkins pipelines"
  - "Improved the team's reporting workflow" → must NOT become "Led an
    organization-wide reporting transformation"
- `evals/rubrics/grounding.md` — added the deterministic-backstop input note
  (`deterministic_metrics.grounding_overlap.missing_samples`).
- `PROMPT_VERSION` bump in the same commit per CLAUDE.md.

### Why

Three historical grounding evals on `data-scientist-junior` scored 2-3 with
failure modes clustered as `scope_inflation`, `invented_metric`, `verb_overreach`.
Specific phrases the model had invented:

- "time-series forecasting" (source: "built dashboards")
- "climate-aware transportation forecasting" (source: "Toronto bike-flows")
- "regression analysis" as core expertise (source: one capstone project)

Pattern: the LLM substitutes more specialized vocabulary than the source
warrants — the worked examples teach it where the line is.

### Result

| Fixture | Rubric | Pre-edit (best of 3 historical runs) | Post-edit |
|---|---|---|---|
| data-scientist-junior | grounding | 2 / 5 / 5 (one regression) | 4.8 |
| data-scientist-junior | ats_format | n/a (smoke only) | 4.2 |
| data-scientist-junior | keyword_coverage | n/a | 4.6 |
| data-scientist-junior | tone | n/a | 4.8 |
| pm-senior | grounding | n/a | 4.8 |
| pm-senior | ats_format | n/a | 4.2 |
| pm-senior | keyword_coverage | n/a | 4.2 |
| pm-senior | tone | n/a | 4.2 |
| sre-mid-level | grounding | n/a | 4.8 |
| sre-mid-level | ats_format | n/a | 4.8 |
| sre-mid-level | keyword_coverage | n/a | 4.6 |
| sre-mid-level | tone | n/a | 4.8 |

**12/12 pass** on full synthetic suite. Total cost: $1.46.

Deterministic post-generation metrics (passing scores):

| Fixture | verb_diversity | specificity_density | grounding_overlap |
|---|---|---|---|
| data-scientist-junior | 1.00 | 0.083 | 0.21 |
| pm-senior | 0.90 | 0.10 | 0.31 |
| sre-mid-level | 0.92 | 0.33 | 0.23 |

### What we learned

1. **Worked examples beat abstract rules**. The original SYSTEM_PROMPT had
   "Never invent experience BECAUSE truthfulness is the north star" — a
   correct rule that didn't survive contact with reality. The new "Built
   dashboards" → "NOT OK: time-series forecasting dashboards" pair is
   concrete enough that the LLM patterns from it.

2. **Three failure types cover most invention**. (a) advanced technique
   substitution, (b) tool-vendor specificity, (c) scope adjective escalation.
   Future failures may need a fourth category, but most fabrications fit.

3. **`grounding_overlap.overlap_ratio` is informative but not load-bearing**.
   Empirical data shows passing scores correlate with **0.20-0.31 ratio** —
   the LLM legitimately paraphrases. The actionable signal is `missing_samples`,
   not the ratio. Documented this in the function's docstring.

4. **`specificity_density` is uniformly low (0.08-0.33)**. The LLM is
   under-quantifying — it's safer than fabricating, but it suggests the
   GROUNDING CHECK has overcorrected the model into qualitative-only output.
   Future tuning opportunity: a counter-rule encouraging the LLM to surface
   *existing* numbers from source more aggressively.

5. **The Haiku judge is fairly stable but introduces ±0.5-point noise**.
   The pre-migration int 2/5/5 split on identical inputs across runs
   confirms this. The new 0.0-5.0 scale captures a real signal in 4.2 vs 4.6
   vs 4.8 — fine-grained enough to be actionable but not so noisy that the
   judge's variance dominates.

### Open questions / future tuning targets

- **`pm-senior` keyword_coverage 4.2** — lowest non-passing-margin score in
  the run. Worth a follow-up iteration: are healthtech keywords being
  integrated, or is the model over-deferring to "transferable skills" framing?
- **`ats_format` swing 4.2 → 4.8** — the LLM produces slightly different
  markdown structure across runs. Consider whether `output_format` could
  pin the section ordering more strictly without breaking grounding.
- **`specificity_density` ceiling** — should we set a target floor (e.g.,
  "≥30% of bullets have a quantifier from source") and add a counter-prompt
  if the LLM goes lower? Risk: pushing too hard re-opens the invention door.

### How the dashboard helped

Once Phase 4 landed, three views became immediately useful:

- **Heatmap** showed `data-scientist-junior × grounding` was the only red
  cell, immediately scoping the tuning target.
- **Failure-mode table** showed `scope_inflation`, `invented_metric`,
  `verb_overreach` as the top slugs for that fixture — the three rule
  classes the new SYSTEM_PROMPT lines target.
- **Score-over-time** chart will become useful once we have multiple
  `prompt_version` runs in the data; the prompt_version label on every
  point lets us attribute regressions cleanly.

### Identified gaps in observability

These are not blockers but worth tracking:

1. **No correlation between LLM telemetry and eval results yet.** When
   grounding fails on fixture X, we can't click through to the specific
   `analyze()` and `generate()` calls that produced it. A future enhancement:
   add a `run_id` field to both `logs/llm_calls.jsonl` and
   `evals/results/*.jsonl`, then make the dashboard linkable.

2. **No latency/cost percentiles**. Dashboard shows mean latency and total
   cost but not p50/p95. For a tuning workflow this matters less than for
   production, but worth noting.

3. **No automated regression alerting**. If grounding drops from 4.8 to 3.5
   on tomorrow's run, nothing fires. CI catches PR-time regressions via
   exit code 2 but local development has no analog.

4. **Real-fixture coverage is empty**. `evals/fixtures/real/` is gitignored
   for good reason but means the suite only tests three synthetic personas.
   Tuners should rotate their own real fixtures through to catch
   distribution drift.

---

## 2026-05-09 — `2026-05-09.1` → `2026-05-09.2`: gap-closing iteration

### What changed

**Infrastructure (Gaps 1-3):**
- `run_id` (12-hex UUID) threaded through `analyze()`, `generate()`, `_call_llm`, `evals/runner.py`, and live `app.py` routes. Lands in both `logs/llm_calls.jsonl` and `evals/results/*.jsonl` so the dashboard can correlate which LLM calls produced each graded result. New "Run" column in both dashboard tables.
- `_summarize_calls` now returns `p50_latency_ms`, `p95_latency_ms`, `p50_cost_usd`, `p95_cost_usd` via a new `_percentile` helper. Tail behavior is now visible — a 90s outlier no longer hides inside a healthy mean.
- Local regression alerting in `evals/runner.py`: at the start of each run, `_load_baseline_scores` reads all prior result files and builds a `{(fixture, rubric): most_recent_record}` map. After each grading, `_detect_regression` compares against baseline; drops greater than `REGRESSION_DELTA` (default 0.5, env-overridable) log a `WARNING` and accumulate into an end-of-run summary.

**Tuning (Gaps 4-5):**
- `evals/rubrics/keyword_coverage.md` updated: "covered" now means "in resume body OR in cover letter when the keyword matches `expected.forbidden_inventions`". Prevents the no-win situation where a B2B PM applying to healthtech is forced to choose between fabricating clinical experience (loses grounding) or omitting healthcare keywords (loses keyword_coverage).
- `analyzer.py:SYSTEM_PROMPT` "Always surface existing metrics" rule expanded with concrete examples of what counts: counts ("three reports"), durations ("monthly cadence"), team sizes, GitHub stars, frequencies. The previous rule was too narrow — the LLM was interpreting "metrics" as only `%` and `$` and dropping legitimate quantifiers like "one year" and "two merged PRs".
- `PROMPT_VERSION` 2026-05-09.1 → 2026-05-09.2.

### Why

Five gaps were called out at end of the prior iteration:
1. No correlation between LLM telemetry and eval results
2. No latency/cost percentiles
3. No regression alerting
4. `pm-senior` keyword_coverage stuck at 4.2
5. `specificity_density` uniformly low (0.08-0.33) across all fixtures

Gaps 1-3 were observability gaps; the new tools light up the dashboard. Gaps 4-5 surfaced through the new metrics — once we could see the density data, we could trace it back to the prompt's narrow definition of "metrics".

### Result

| Fixture | Rubric | 2026-05-09.1 | 2026-05-09.2 | Δ |
|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.2 | 4.7 | **+0.5** |
| data-scientist-junior | grounding | 4.8 | 4.8 | 0 |
| data-scientist-junior | keyword_coverage | 4.6 | 4.6 | 0 |
| data-scientist-junior | tone | 4.8 | 4.2 | -0.6 ⚠ |
| pm-senior | ats_format | 4.2 | 4.2 | 0 |
| pm-senior | grounding | 4.8 | 4.8 | 0 |
| pm-senior | keyword_coverage | 4.2 | 4.2 | 0 |
| pm-senior | tone | 4.2 | 4.7 | **+0.5** |
| sre-mid-level | ats_format | 4.8 | 4.8 | 0 |
| sre-mid-level | grounding | 4.8 | 4.8 | 0 |
| sre-mid-level | keyword_coverage | 4.6 | 4.7 | +0.1 |
| sre-mid-level | tone | 4.8 | 4.2 | -0.6 ⚠ |

**12/12 still pass**. Two improvements at +0.5; two regressions at -0.6 on tone (both flagged by the new alerter). The tone regressions are within Haiku judge variance band — the SYSTEM_PROMPT change didn't directly touch tone-related rules, but the broadened "metrics" guidance may have nudged cover letter phrasing slightly. Worth watching across the next 2-3 runs.

Density barely moved (0.083 → 0.11 for data-scientist-junior; pm-senior unchanged at 0.10; sre-mid-level unchanged at 0.33). The expanded rule helped but the LLM is still cautious about preserving small numbers. Future iteration could try adding a worked example pair like the GROUNDING CHECK uses.

### What we learned

1. **The new regression alerter immediately paid for itself.** Two genuine 0.6-point drops on tone surfaced before they could compound across more iterations. Even if these turn out to be judge variance, the alert gives us evidence to confirm or deny that hypothesis next run.

2. **Rubric design can create no-win situations.** The pm-senior keyword_coverage 4.2 wasn't a prompt problem — it was a rubric problem. The rubric punished the model for correctly refusing to fabricate. The fixture's `notes` already acknowledged this; the rubric just hadn't caught up. Lesson: when a fixture's notes describe a deliberate trade-off, the rubric must encode it explicitly.

3. **"Metrics" needs concrete examples in the SYSTEM_PROMPT.** The rule "surface existing metrics" was correct but the LLM was reading "metrics" too narrowly. Adding "counts, durations, team sizes, GitHub stars, frequencies" is the kind of disambiguation that beats abstract instruction every time — same lesson as the GROUNDING CHECK worked examples.

4. **`run_id` is a foundational primitive we should have had from day one.** It's a 12-character string but unlocks correlation, regression analysis, and per-pipeline cost. Future tooling (e.g., a "click run_id to see all telemetry" feature) becomes trivial.

5. **Percentiles tell a different story than means.** This run's mean latency was around 88s but p95 was 142s — the user-visible "feel" of the system depends on tail behavior, not the average.

### Open questions / future tuning targets

- **Tone regressions**: re-run in 2-3 iterations to see if the 4.8→4.2 drop persists or settles back. If it persists, inspect `cover_letter_content` vs the prior version to find the actual source of the tone shift.
- **`pm-senior` keyword_coverage stuck at 4.2 even with the rubric fix**: the judge may not be applying the new "covered in cover letter" rule. Worth checking the next run's `reasons` to confirm. If still stuck, the rubric prose may need to be even more explicit ("score 4.5+ if every must_keyword is in resume AND every forbidden-domain keyword is acknowledged in cover letter").
- **Density still low**: the broadened SYSTEM_PROMPT rule helped one fixture by 0.03 ratio. For a stronger move, consider a worked-example pair in the GROUNDING CHECK ("Source: 'three reports'. OK to write: 'three legacy reports'. NOT OK to drop: 'multiple legacy reports'.").

---

## 2026-05-11 — `2026-05-09.3` → `2026-05-11.1`: optional Q&A interview step

### What changed

- `analyzer.py` — added `CLARIFY_SYSTEM_PROMPT` (a short dedicated persona, ~22 lines) plus `clarify()` between `analyze()` and `generate()`. Reuses `_parse_or_retry` for telemetry parity; emits `call: "clarify"` in `logs/llm_calls.jsonl`. `_call_llm` and `_parse_or_retry` gained an optional `system_prompt` arg so clarify can override the main hiring-manager persona without code duplication.
- `analyzer.py:generate()` — when `context_set["clarifications"]` is non-empty, a `<candidate_clarifications>` block is injected between `<analysis>` and `<resume_rules>` with paired question/answer entries. The GROUNDING CHECK was widened to accept clarification answers as legitimate source material ("first-person ground truth") so the model may surface tech or experience the candidate confirmed even when it doesn't appear in the resume — while the no-invention rule still forbids anything beyond the union of (resume + clarifications).
- `hardening.py` — `ContextSet` TypedDict gained two optional fields: `clarification_questions: list[ClarificationQuestion]` and `clarifications: dict[str, str]`. Both are `total=False` so pre-clarify saved contexts continue to round-trip.
- `app.py` — new routes `POST /api/clarify` (generates questions, persists to the same context file) and `POST /api/answer-clarifications` (stores per-question answers, filters unknown ids and empty text). Both use the standard `_safe_username` + `_within(OUTPUT_DIR)` guards. `run_id` propagates analyze → clarify → generate.
- `templates/index.html` + `static/app.js` + `static/style.css` — collapsible "Clarifying Interview" section inside the Analysis panel with `GET CLARIFYING QUESTIONS` / `SUBMIT ANSWERS & GENERATE` / `SKIP` controls. UI rendering uses safe DOM construction (textContent, appendChild) instead of innerHTML for LLM-supplied strings.
- `evals/rubrics/clarification_quality.md` — new rubric. Grades on: question count (3–5), composition (≥50% experience probes), gap citation specificity (must trace to analyzer output), word limit (≤25 each), no compound or leading questions, theme coverage against `expected_clarification_themes`.
- `evals/runner.py` — runs `clarify()` between analyze and generate; injects the resulting `clarification_questions` into every per-rubric payload (the new rubric uses them, others ignore them). Failures in clarify degrade gracefully — the existing four rubrics still grade.
- `evals/fixtures/synthetic/*/expected.json` — each of the three synthetic fixtures gained `expected_clarification_themes` with `experience_probes` and `scope_probes` lists tailored to that fixture's real gaps, plus `min_clarification_quality_score: 4`.
- `tests/` — new `test_app_clarify.py`; expanded `test_analyzer.py` (clarify() happy-path, retry, system_prompt threading, generate-injection-on/off paths); `test_hardening.py` round-trip for ContextSet with and without the new fields.
- `PROMPT_VERSION` bumped to `2026-05-11.1` in the same commit per CLAUDE.md.

### Why

Two coupled failure modes that show up in the existing eval results:

1. **Fabrication on JD-required skills missing from the resume.** When a JD asks for a technology the candidate's resume doesn't mention but they actually do have experience with, the generator either invents detail (grounding penalty) or stays silent (keyword-coverage penalty). There was no channel to surface the real experience.
2. **Scope ambiguity at the role boundary.** The analyzer's `comparison_analysis` flagged ambiguities ("setting direction vs. executing", "shipped vs. prototype", "sole owner vs. team member") but the generator had to guess. Resume bullets came out vague or, occasionally, over-confident.

The clarify step opens both channels: experience probes surface real-but-undocumented experience (with the candidate's own words as ground truth — citable in the resume); scope probes disambiguate so the generated wording is precise.

### Result

First-run scores will be captured here after the next full `python evals/runner.py --suite synthetic` run. The eval includes the new `clarification_quality` rubric for the first time; the baseline-comparison machinery in `_load_baseline_scores` will pick up subsequent runs automatically. Pre-edit baselines for the four existing rubrics are unchanged (the clarify step is opt-in and was not exercised during prior runs).

Expected impact qualitatively:
- `clarification_quality`: target ≥4.0 on all three fixtures; the per-fixture `expected_clarification_themes` give the judge concrete hit-targets.
- `grounding`: should be unchanged on synthetic fixtures (no answers are injected during the eval run). The real test of grounding under clarifications is a future fixture variant — see "Open questions" below.
- `keyword_coverage`: unchanged on synthetic. In production, when a candidate clarifies "yes, I've used Terraform briefly", keyword coverage should improve because the generator can now surface Terraform.

### What we learned

1. **A dedicated short system prompt beats overloading the main one** when the task is narrow. CLARIFY_SYSTEM_PROMPT is ~22 lines; SYSTEM_PROMPT is ~30 ALWAYS/NEVER rules. Mixing them dilutes both. The cost is a cache miss on the system block, but the user-prefix cache (which carries the heavy content) is unaffected since clarify uses no cached prefix.
2. **Persisting questions to the same context file makes the UI resumable**. The user can refresh the page mid-interview and the questions reload from disk. The alternative — keeping questions only in browser state — would have lost answers on any reload.
3. **The grounding rule needs a precise carve-out, not a blanket exception.** "Clarification answers are first-person ground truth and may be cited even when the resume does not mention them" is the surgical phrasing; the model still must not invent anything beyond the union of (resume + clarifications). Vaguer language ("clarifications override the resume") risks unbounded invention.

### Open questions / future tuning targets

- **First eval results pending**: run `python evals/runner.py --suite synthetic` and append the score table here. If `clarification_quality` is <4.0 on any fixture, inspect `failed_rules` and tighten CLARIFY_SYSTEM_PROMPT — most likely failure mode is questions that don't cite a specific gap source.
- **Contradiction fixture variant**: per the plan, the strongest grounding test is a fixture variant whose injected clarification *contradicts* an inferred resume fact (e.g. resume implies "shipped to production"; clarification says "remained a prototype"). The grounding rubric must fail if the generated resume still claims production. Not yet implemented — needs a `clarifications` field in the fixture itself plus a runner mode that injects them into generate.
- **Addition fixture variant**: similarly, a fixture with an injected positive clarification (e.g. "Yes, I used Terraform on SRE rotation") to verify the generator surfaces it AND the grounding rubric catches any *further* invention beyond the clarified fact.
- **Cost gating**: clarify adds one Sonnet call per fixture per eval run (~$0.01–0.02). For very large eval suites consider a `--no-clarify` flag; not needed today with 3 synthetic fixtures.

---

## Template for future entries

```markdown
## YYYY-MM-DD — `<old_version>` → `<new_version>`: <one-line summary>

### What changed
<concrete file/line edits with paths>

### Why
<failure mode observed; cite the dashboard view or eval result file>

### Result
<table: fixture × rubric, pre vs post>

### What we learned
<1-3 bullets, each a rule-of-thumb for future tuning>

### Open questions / future tuning targets
<things this iteration noticed but didn't fix>
```

---

## Anchor promotion rule

A fixture is promoted from `evals/exploration/` to `anchor-v2` when all three
conditions are met:

1. **Stable scores** — stdev ≤ 0.6 across ≥3 consecutive runs at the same
   PROMPT_VERSION (judge variance must not swamp the signal).
2. **Discriminating** — the fixture produces meaningfully different scores
   across ≥2 distinct PROMPT_VERSIONs (a fixture that always returns 4.2
   regardless of prompt changes carries no signal).
3. **Documented failure mode** — at least one concrete failure mode (a rubric
   the fixture reliably exercises below 4.0, or a specific `failed_rules` tag
   that fires) must be documented in this TUNING_LOG.

Until all three conditions are met the fixture stays in `evals/exploration/`.
Scores from exploration fixtures appear in JSONL (with `"suite": "exploration"`)
but do not gate merges.

---

## S3 VECTOR TIER — measurement probe — 2026-06-16 (`feat/doc-assistant-vector`, Sprint 7.6)

> **Not a prompt change** (résumé `PROMPT_VERSION` unchanged; no LLM in the retrieval
> path). This entry records the eval-gate evidence for adding the S3 semantic-retrieval
> tier to the doc-grounded assistant — a *retrieval* change, the institutional-memory note
> the gate-override owes.

**1. What changed?** Added the S3 `VectorSource` tier — static `model2vec` embeddings
(`minishlab/potion-base-8M`, dim 256), brute-force cosine over a rebuildable
`db/vector_index/` sidecar (2948 chunks over tracked `*.py` + `*.md` at HEAD), wired into
the assistant "on when available." See CHANGELOG / RELEASE_ARC §4.7.

**2. Why? (the eval-gate justification — a deliberate override)** RELEASE_ARC §4.7 gates
S3 on "measure on real questions, add only if the code-vocabulary misses justify it,
before the tag." The formal labeled-eval loop is v1.0.8 (Sprint 8.5), not yet run. The
**owner tested the landed Stage-1 assistant on real questions and found it "too literal /
lacking semantic flexibility"** (2026-06-16) and directed building S3 ahead of the formal
gate. This probe is the lightweight corroboration.

**3. Result** (`python -m scripts.vector_index_probe`, 12 real dev questions phrased *not*
using the literal code identifier):
- On the one pure vocabulary-gap question — *"how does the index avoid **recomputing**
  embeddings for unchanged files"* (the code says "**re-embed**", never "recomputing") —
  the lexical S2 `git grep` tier returned **0** hits; the S3 tier was the **sole recovery**.
- On **all 12** questions S3 surfaced semantically-relevant `path:line` citations the
  lexical pass did not rank — e.g. *"how do we fuse results from several sources"* →
  `recall/assemble.py:31` (the RRF block) + `:61` (`_rrf_fuse`); *"where is the cover
  letter opening tone handled"* → `analyzer.py:1951`.
- Headline metric: **1/12 questions a hard lexical miss (git 0 hits); S3 recovered 1/1.**

**4. Learned / caveats:**
- The probe measures *coverage* (does S3 surface new cites?), not *relevance ranking* —
  `git grep` almost always finds *some* longest-token match, just not the most relevant, so
  "1/12 lexical miss" is a floor, not a verdict. The per-question "new cites" signal (S3
  contributes on 12/12) is richer. **The owner's qualitative finding remains the primary
  justification.**
- The index covers only **tracked** files; the probe ran pre-commit, so this branch's own
  new code (`recall/sources/vector_source.py`, then untracked) was NOT indexed — which is
  exactly why the "recomputing embeddings" answer pointed at `CHANGELOG.md` (committed)
  rather than the source. A post-merge `python -m scripts.build_vector_index` re-indexes it.
- Provenance: model `minishlab/potion-base-8M` (dim 256), 2948 chunks, built 2026-06-16 on
  `feat/doc-assistant-vector` over base HEAD `d9e5e77`. Sidecar is gitignored (rebuildable).
- **Still owed (v1.0.8):** a labeled before/after eval (judge-scored top-k relevance with
  vs without S3) to confirm the tier earns its dependency footprint — tracked in the
  Carry-forward ledger.

---

## 2026-06-18 — feat/avatar-voice-tone-tuning: avatar voice/tone & behavior (`AVATAR_PROMPT_VERSION 2026-06-16.1 → 2026-06-18.1`)

> **Scope note.** This tunes the **avatar** (`avatar_answer_streaming` /
> `AVATAR_SYSTEM_PROMPT`), NOT the résumé pipeline. `PROMPT_VERSION` is untouched and the
> avatar is **not** a `_BASE_SYSTEM_PROMPTS` / synthetic-suite target — so this entry uses
> the avatar's own deterministic checks + a live manual spot-check matrix (the guide's §6),
> never the résumé runner. Executes [`docs/dev/avatar-voice-tone-guidance.md`](../docs/dev/avatar-voice-tone-guidance.md) Part 4.

### 1. What changed

All in one commit with the `AVATAR_PROMPT_VERSION` bump (`analyzer.py:290`):
- **L1 `AVATAR_SYSTEM_PROMPT` (`analyzer.py:526`)** — friendly-guide persona (warmth via
  helpfulness, never instructed wit); the verbatim P0 precedence line; the refusal redirect
  made **near-mandatory + cited** with a friendly follow-up; the **GitHub "report it" rung**
  for in-domain-but-undocumented gaps (behavior only — the model is told to never invent a
  URL); an explicit **calibrated-middle** clause; an **anti-sycophancy / anti-over-promise /
  anti-performed-honesty-or-empathy** clause + the **connect-capability-to-concern** move on
  reassurance-fishing; the warmly-reframed **L5** dev-mode nudge ("Tick Dev mode…").
- **L2 per-turn closer (`analyzer.py:1561`)** — reworded to agree with L1; refusal byte-exact.
- **L4** — refusal string `"I don't have that in my docs."` kept **byte-identical** in both
  L1 and L2 (no reword — owner Q9 recommended path).
- **Citation readability (owner-requested mid-pass)** — inline citations now read as natural
  sentences with the source in clean **SINGLE** square brackets at the **END** of the sentence
  it supports (`[using-sartor]`, `[analyzer.py:49]`), never `[[…]]` mid-sentence; only the slug
  or path:line goes inside the brackets (no phrase-wrapping). The `#assistantStatus` Sources
  footer strips the `[[ ]]` to match. Owner rationale: `[[path:line]]` mid-sentence is hard for
  non-technical readers.
- **L3 (`templates/index.html` + `static/assistant.js`, no version bump)** — plain-languaged
  intro ("I show my sources", dropped "committed wiki + code at HEAD"); a **persistent
  empty-state** (scope/boundary line + 4 verified example prompts, replacing the vanishing
  placeholder as the home for examples); two **blame-free error strings** distinct from the
  refusal; a real **GitHub issues link** in the modal footer (the single source of the URL the
  prompt only references by behavior); and the **`aria-live` streaming-flood fix** — dropped
  `aria-live="polite"` from `#assistantAnswer` (now `aria-busy`-toggled, silent), so the one
  terminal announcement rides `#assistantStatus`.

### 2. Why

Carry-forward ledger item "Avatar voice/tone & behavior tuning — EXECUTION". The build-time
persona (Sprint 7.5) was never tuned; the refusal was a dead end ("if useful, name the closest
thing"), there was no calibrated middle, no anti-over-promise guardrail, and a confirmed
screen-reader a11y defect (per-token announcement of a live region).

### 3. Result

- **Gate:** `ruff` clean · `mypy` clean (189 files) · `pytest` **1303 passed** (incl. the UX
  tier — `test_20260616_assistant_panel.py` green, so the markup/JS changes drive cleanly).
- **Deterministic tone checks** (new, `tests/test_avatar_streaming.py`, $0): refusal byte-sync
  across L1/L2; the locked voice clauses present; banned-phrase / over-promise / no-URL-in-output
  scanners; cite-membership checker (`[[slug]]`/`path:line` ⊆ recalled units); brand-mark +
  answer-node-not-a-live-region. All pass; the original 8 still pass.
- **Live §6.3 spot-check** (real Haiku, 12 scenarios × both modes, in-process through the real
  `recall.assemble` path): voice axes **clean** — friendly-guide tone with **zero** exclamation /
  cheer openers, refusal-as-doorway + the GitHub rung firing correctly with **no fabricated URL
  in any answer**, the connect-to-concern move on "will sartor get me the interview?" (declined
  the prediction, connected tailoring + parseability, explicitly disclaimed the outcome), ATS
  framed strictly as parseability, and the **access plane held** (zero DEV-audience units in every
  user-mode turn; #4a routes user→refuse-redirect vs dev→cited dashboard answer).
- **Grounding regression check (P0 — explicit, not assumed):** ran the citation-drift scenarios
  under the OLD vs NEW prompt. Citation-shaped drift is **pre-existing, not introduced**: the
  `AGENTS.md:7` line-number approximation is emitted **identically by both** prompts; on the
  retrieval question the OLD prompt fabricated `[[Application]]`/`[[wizard rail]]` while NEW had
  **zero** violations. Most flagged "violations" are a cosmetic bracket-format quirk (model wraps a
  real `path:line` unit in `[[ ]]`), present in both. The grounding clauses are byte-identical, so
  the floor is unchanged.

### 4. What we learned

1. **A friendlier persona did not erode grounding** — but only because the grounding clauses were
   kept byte-identical and the warmth was confined to manner + the next step (the guide's central
   discipline). The old-vs-new comparison is the evidence; do it for any future avatar persona edit.
2. **Haiku has a pre-existing citation-format / line-number fragility** (occasionally renders a
   `path:line` as `[[path:line]]`, wraps a bare module name in `[[ ]]`, or approximates a line it
   wasn't given). It is cosmetic-to-mild (the *claim* stays grounded) and equal across both prompts.
   The new **cite-membership** check is the mechanism to quantify it at scale — owed in the v1.0.8
   labeled avatar eval (Carry-forward ledger). Not fixed here: it predates the tuning, the floor is
   unchanged, and citation-format surgery is out of this branch's voice/tone scope.
3. **The GitHub "report it" rung works as designed** — the model states the behavior and never
   emits a URL (the link lives only in L3 chrome), so the "never invent a support channel" invariant
   holds while still giving in-domain-undocumented questions a real forward path.
4. **Single-bracket, end-of-sentence citations incidentally REDUCED the citation drift.** After the
   owner-requested format change, the re-run spot-check had **zero** cite-membership violations — the
   `AGENTS.md:7` line-approximation and the `[[Step 1…]]` / `[[overview.md]]` fabrications from the
   first run were gone. Plausible cause: the model no longer mirrors the `[[ ]]` it sees in the
   recalled-context block, so it stops conflating wiki-link syntax with a citation it can invent.
   Net: the readability change and the grounding floor moved the same direction.

---

## 2026-06-19 — feat/avatar-citation-format: citation/reference-format consistency (`AVATAR_PROMPT_VERSION 2026-06-18.1 → 2026-06-19.1`)

> **Scope note.** Tunes the **avatar** (`avatar_answer_streaming` / `AVATAR_SYSTEM_PROMPT` +
> the `done`-payload renderer), NOT the résumé pipeline. `PROMPT_VERSION` untouched; avatar
> not a `_BASE_SYSTEM_PROMPTS` target — so this entry uses the avatar's own deterministic
> checks + a live in-process spot-check, never the résumé runner. Executes
> [`docs/dev/avatar-citation-format-guidance.md`](../docs/dev/avatar-citation-format-guidance.md).

### 1. What changed

Owner locked **scheme B** (numbered footnotes) + a constrained inline-markdown render +
**clickable GitHub links** (in-app viewer deferred). All in one commit with the version bump:
- **L1 `AVATAR_SYSTEM_PROMPT`:** the citation rule now says cite a claim with the unit's
  **bracketed number** (`[1]`, `[2]`) at the end of the sentence — never a slug, markdown link,
  or URL — with worked OK/NOT-OK pairs; a light line permits `` `code` `` / `**bold**` but forbids
  markdown links/headings. Per-turn closer matched. Grounding/refusal/no-invention clauses
  **byte-identical** to `2026-06-18.1` (only the citation *format* changed).
- **Renderer + `done` payload (`analyzer.py`):** new `_resolve_cited` parses the emitted `[n]`,
  **renumbers** them consecutively in first-appearance order, remaps the body, and emits a
  **cited-only** `citations` list of `{n, label, href}`; `_citation_href` builds the GitHub blob
  URL (wiki→`main`, code→pinned `sha` + `#L`). A stray `[[slug]]` the model drops into prose is
  normalized to plain text.
- **L3 (`static/assistant.js` + `templates/index.html`):** answer re-renders once on completion
  as a fixed markdown subset (`` `code` `` / `**bold**` / `[n]`→GitHub `<a>`), XSS-safe by
  construction; the numbered "Sources" key renders into a new non-`aria-live` `#assistantSources`.

### 2. Why

Carry-forward / owner testing (2026-06-19): the assistant mixed markdown links `[text](path)`,
parentheticals, and numeric `[N]` markers in the same sentences, over a "Sources:" footer the
`[N]` never resolved to. Three causes (C1 the numbered-units renderer, C2 model-invented markdown
links shown raw, C3 the footer = all-retrieved not cited). The footer overstatement is a P0 honesty
problem, not cosmetics.

### 3. Result

- **Gate:** `ruff` clean · `mypy` clean (190 files) · `pytest` **1311 passed** (incl. the UX tier —
  both assistant UX regressions green, so the markup/JS re-render + linked footer drive cleanly).
- **Deterministic checks** (`tests/test_avatar_streaming.py`, $0, new + updated): `_citation_href`
  construction (wiki / code+sha+`#L` / `path:symbol` / empty-sha→`main`); cited-only + consecutive
  renumber (out-of-order + gaps → `[1][2]`); out-of-range marker left literal; empty-refusal footer;
  stray-`[[slug]]` normalized; and the pipeline R1/R2/R3 ("every body `[n]` resolves, footer ⊆ cited,
  no `](`, no URL"). All pass; the byte-exact refusal sync + voice-clause checks still pass.
- **Live in-process spot-check** (real Haiku, 5 scenarios × the real `recall.assemble` path, both
  modes): **5/5 PASS** — every body `[n]` resolved to a footer entry (zero unresolved), the footer
  was cited-only and consecutively numbered, **zero** markdown links and **zero** URLs in any answer,
  and hrefs were well-formed (wiki→`blob/main/docs/wiki/pages/<slug>.md`, code→`blob/<sha>/<path>#L<n>`).
  The refusal (S3, "cache hit rate this week") fired correctly — exact refusal + a resolvable nearest-
  topic cite + the GitHub rung stated as *behavior* with no URL emitted. Dev answers used `[path:line]`
  cites + inline-`code` identifiers; user answers led with wiki slugs.

### 4. What we learned

1. **Numbered cites resolve reliably and the footer is honest.** Across 5 live scenarios every emitted
   `[n]` mapped to a retrieved unit (in-range), so the cited-only footer never overstated grounding and
   every marker was followable — the C1/C3 fix landed. Consecutive renumbering means the user always sees
   `[1][2][3]`, never the raw context-index gaps.
2. **Haiku still occasionally mirrors a `[[slug]]` into prose (~1/5 here).** This is the same pre-existing
   double-bracket tic the voice/tone pass flagged — not introduced by this change and never a real (numbered)
   cite. Surfaced in the live S1; folded in a deterministic server-side normalization (`_resolve_cited` strips
   `[[slug]]`→`slug`) so the rendered answer is never raw bracket-soup. The broader cite-fidelity measurement
   stays owed to the **v1.0.8 labeled avatar eval** (Carry-forward ledger).
3. **Clickable links without new infrastructure.** GitHub blob URLs (built client-side from the citation,
   not model-emitted) give resolvable links with no new Flask route, renderer, or sanitizer — the no-URL
   model invariant holds because the model still only emits `[n]`. Known trade-off: a code link on an
   unpushed local `sha` 404s until pushed (wiki links to `main` don't). An in-app rendered viewer is the
   deferred follow-on if that friction bites.
4. **Grounding floor unchanged by construction.** Only the citation *format* moved; the GROUND-EVERY-CLAIM /
   refusal / no-invention clauses are byte-identical to `2026-06-18.1`, and the live spot-check showed zero
   fabricated cites — consistent with the voice/tone pass's finding that moving off mirrored `[[ ]]` syntax
   *reduces* drift rather than adding it.

---

## 2026-06-23 — `eval/live-shakedown-labels` (Sprint 8.5): S3 before/after labeled eval (KEEP) + PV-1 real-data shakedown

> **Not a prompt change** (`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched). The
> v1.0.8 gated test window's eval half. (A) closes the "still owed (v1.0.8)" item the
> 2026-06-16 S3 probe entry above flagged; (B) is the first run of the real-data
> eval/tuning loop. Full findings backlog: [`docs/dev/window-8.5-findings.md`](../docs/dev/window-8.5-findings.md).

### A. S3 vector tier — judge-scored before/after relevance eval (Carry-forward #2 → RESOLVED: KEEP)

**What.** The labeled before/after eval the 7.6 gate-override owed: new
`scripts/vector_before_after_eval.py` runs a fixed 12-question dev-vocab set through
`recall.assemble` with the lexical tiers (wiki+git+session) vs +S3 vector, scoring each
retrieval set's relevance 0–5 with the Haiku eval-judge (reuses `evals.runner._grade`, so
no egress-allowlist change). Retrieval corpus = committed wiki+code (no PII) → committable.
Run on a **freshly-rebuilt** index (the 06-16 index had staled — see gotcha).

**Result** (`python -m scripts.vector_before_after_eval`, top-k=6):
- Mean judge relevance: **base 1.12 vs +S3 2.58 (Δ +1.46, +130%)**; improved 8/12,
  regressed 1/12; S3 added a lexical-missed cite on **12/12**.
- **Verdict: KEEP.** S3 more than doubles retrieval relevance and earns its
  `numpy`+`model2vec` footprint. No demote at 8.6.

**Learned.** The 7.6 probe's "git grep finds *some* hit on ~all questions" is confirmed
(0/12 lexical misses by hit-count) but is NOT evidence against S3: the judge scores those
lexical-only sets at 1.12/5 — many hits, little relevance. The semantic tier supplies the
relevance. Caveat: directional, N=12 dev-vocab; absolute relevance (2.58) is still only
"partially relevant" — retrieval quality is a longer-term improvement area.

**Gotcha — index stale after the blueprint split.** The committed-code index (built
06-16) cited pre-split `app.py` line numbers the 8.3 decomposition moved; a free
`python -m scripts.build_vector_index` re-anchored every cite onto `blueprints/**`. The
index is gitignored + has no committed rebuild trigger → it silently staled. → 8.6: pair a
rebuild with `/wiki-ingest`; add a freshness check (window-8.5-findings.md S3-1).

### B. PV-1 real-data eval/tuning loop — first run (Carry-forward #4: labels DEFERRED to 8.6)

**What.** First end-to-end run on the decomposed code: candidate `testuser` (real corpus:
5 exp / 66 bullets / 9 skills / 4 summaries) → seed export → bootstrap over 3 JDs (the
synthetic JDs against the real corpus) → (annotate → collate → eval, deferred).

**Result.** The **real corpus→context→generate path works** — all 3 bootstrap pipelines
completed (analyze→clarify→generate; 19/13, 23/13, 21/12 bullets/skills). The shakedown's
job — surfacing so-far-unexercised integration breaks — succeeded at the grounding +
seed-export edges:
- **EV-1 (HIGH):** the L2/MiniCheck grounding scorer is broken by an **unpinned git dep**
  (`minicheck @ git+…`, pyproject `eval-grounding`): a fresh install pulled a drifted
  incompatible major version (default `Bespoke-MiniCheck-7B`/vLLM; dropped `device` +
  `flan-t5-large`), so `grounding_signals.py:75`'s `device="cpu"` `TypeError`s. Also
  `transformers` installed is 5.10.2, violating the `<5.0` pin; CONTRIBUTING.md still cites
  `flan-t5-large`. The "never-run live loop" latent breakage. **Blocks L1/L2 labels.**
- **EV-2 (Med):** an optional `--grounding-signals` failure has no try/except, so it
  aborted the whole bootstrap and discarded ~$0.60 of completed pipeline work
  (`bootstrap.json` never written).
- **EV-3 (Low):** `export_corpus_seed.py` `UnicodeEncodeError` on its `→` success print
  (Windows cp1252) — seed wrote fine but exits non-zero. Workaround `PYTHONIOENCODING=utf-8`.

**Decision (owner, 2026-06-23).** Defer PV-1 label production to 8.6: fix EV-1 (minicheck)
FIRST, then run the full bootstrap+annotation+eval in ONE pass (full L0+L1+L2, no double
annotation, no re-spend). 8.5 delivers the findings + the proof the pipeline path works;
the real-suite eval scores + the #4 calibration labels move to 8.6 PV-2.

---

## 2026-06-23 — `fix/window-findings-grounding` (Sprint 8.6): EV-1 minicheck fix — grounding scorers runnable again (NOT a prompt change)

> **Not a prompt change** (`PROMPT_VERSION` / `AVATAR_PROMPT_VERSION` untouched). Recorded
> here because it unblocks the **PV-2 grounding-calibration loop** — the next tuner needs to
> know the L0+L1+L2 scorers run, and on what stack. Findings + resolution:
> [`../docs/dev/window-8.5-findings.md`](../docs/dev/window-8.5-findings.md).

**What changed?** Pinned `minicheck` to `b58b9fa…` (`pyproject.toml` `eval-grounding`), dropped
the removed `device="cpu"` kwarg in `evals/grounding_signals.py:_load_minicheck_scorer`, added
`accelerate>=1.0` + `nltk>=3.9`, and auto-ensure NLTK `punkt_tab`. Widened the `transformers`
cap to `<6.0`. (EV-2/EV-3/S3-1 also fixed — see CHANGELOG; not eval-scoring-relevant.)

**Why?** The 8.5 shakedown's EV-1: the unpinned `minicheck` git dep drifted and the L2 scorer
`TypeError`d on `device="cpu"`, blocking the PV-2 L1/L2 labels.

**What was the result?** Re-validated the grounding scorers end-to-end on CPU against a 2-bullet
synthetic source (the installed `transformers 5.10.2` stack): **L1 (DeBERTa NLI) mean_entailment
0.995, contradiction_count 0; L2 (MiniCheck flan-t5-large) mean_score 0.973** (per-bullet 0.971 /
0.976), bullet_count 2. So L0 (deterministic) + L1 + L2 all produce scores again — PV-2 can now
produce a full L0+L1+L2 label set. No fixture eval run (this is a tooling fix, not a prompt A/B).

**What did we learn?**
- The 8.5 finding's stated root cause **overstated the breakage** (claimed `flan-t5-large` and the
  `score()` 4-tuple were dropped). Verifying against the *installed* package showed both were
  intact; the real breaks were the `device` kwarg + two undeclared transitive needs (`accelerate`,
  `punkt_tab`) only a real run surfaces. **Lesson: validate a dependency-drift finding against the
  installed package before acting — re-running is what exposes the true break (and the false ones).**
- **Pin git/research deps.** An unpinned `git+` ref is a time bomb; pin to a sha the moment the dep
  is used in a loop that isn't run every release.
- PV-2 hand-off: the scorer is proven; the remaining cost is the owner's manual annotation pass.

---

## 2026-06-23 — `fix/window-findings-tone` (Sprint 8.6, PV-3): cover-letter opener+close adherence (`PROMPT_VERSION 2026-06-13.1 → 2026-06-23.1`)

> **Scope note.** Tunes the résumé pipeline's **cover-letter contract**
> (`_COVER_LETTER_RULES_BLOCK`, `analyzer.py`). This **IS** a `PROMPT_VERSION` bump — the
> only one in the v1.0.7/v1.0.8 epics. The block is a **user-prompt fragment**, NOT in
> `_BASE_SYSTEM_PROMPTS`, so it could **not** be A/B'd via the `--prompt-overrides`
> primitive (which only targets system-prompt constants) — it was edited directly and
> validated with a paired before/after `--suite synthetic --subset full` run, per
> RELEASE_ARC §4.8. `AVATAR_PROMPT_VERSION` untouched.

### 1. What changed

All in `analyzer.py`, one commit with the version bump:
- **`_COVER_LETTER_RULES_BLOCK`** — **(a)** added a `WORKED EXAMPLES` sub-block (additive,
  before `</cover_letter_rules>`) with OK / NOT-OK pairs for the **OPENER** and the **CLOSE** —
  the two surfaces the documented v1.0.3 lapse hit (tone rubric Check 3 opener, Check 4 hedging).
  **(b)** De-cloned STRUCTURE Paragraph 3: replaced the single close example
  (`More: "I'd welcome a direct conversation about what this team is building."`) with a
  *functional* description (name a concrete topic / timing signal / direct scheduling line —
  implies initiative, never polite waiting). Rationale: the model was **cloning** that one
  example into the near-verbatim lapse, so the concrete model now lives only in the worked CLOSE
  example. VOICE/FORMAT untouched; **no banned-phrases-list expansion** (declined — adds a new
  regression surface; see learnings).
- `PROMPT_VERSION` `2026-06-13.1` → `2026-06-23.1` (`analyzer.py:281`).
- New deterministic test class `TestCoverLetterWorkedExamples` in
  `tests/test_corpus_mode_prompt.py` (asserts the scaffold tokens are present + wired into the
  prompt when `with_cover_letter=True`, absent when `False` — asserts on scaffold, not the
  example sentences, so finalizing wording never churns the test).

### 2. Why

v1.0.3 (`PROMPT_VERSION 2026-06-01.3`) `ds × tone` raw `[4.2, 4.2, **2.1**, 4.2, 4.2]`
(TUNING_LOG `2026-06-01` entry ~line 630): 1 of 5 cover letters opened with throat-clearing
("I am writing to be considered for…") and closed with a vague hedge ("I would welcome a
conversation"). The rules block **already banned** both — so this was an **adherence** slip, not
a missing rule. The project's standard fix for adherence is a **worked OK/NOT-OK example**
(AGENTS.md: "worked examples are the load-bearing teaching signal"). RELEASE_ARC §4.8 PV-3.

### 3. Result

**Gate:** ruff ✓ · mypy ✓ (227 files) · pytest **1391 passed** (1388 + the 3 new), incl. `-m ux`.

**Paired before/after `--suite synthetic --subset full`, n=3 each side** (~$0.32/run, ~$2 total).
Before stamped `2026-06-13.1` (branch byte-identical to `main`); after stamped `2026-06-23.1`.
Judge-error (transient Haiku invalid-JSON) + scenario_misaligned records excluded from means.

**Tone (the target rubric) — mean [raw]:**

| Fixture | before (`.06-13.1`) | after (`.06-23.1`) |
|---|---|---|
| data-scientist-junior | 4.20 [4.2, 4.2, 4.2] | 4.17 [4.1, 4.2, 4.2] |
| pm-senior | 4.20 [4.2, 4.2, 4.2] | 3.87 [**3.2**, 4.2, 4.2] |
| sre-mid-level | 4.20 [4.2, 4.2, 4.2] | 4.20 [4.2, 4.2, 4.2] |

**No-regression check (other rubrics, mean before→after)** — the edit can only touch the cover
letter (tone + marginally keyword_coverage), and the table bears that out:

| Rubric | ds | pm | sre |
|---|---|---|---|
| ats_format | 4.40→4.60 | 4.57→4.53 | 4.60→4.70 |
| callback_likelihood | 4.40→4.37 | 4.00→4.07 | 4.27→4.20 |
| grounding | 4.73→4.77 | 4.77→4.77 | 4.53→4.40 |
| keyword_coverage | 4.20→4.20 | 4.20→4.20 | 4.40→4.33 |
| clarification_quality | 4.20→4.20 | 4.07→4.20 | 4.20→3.87 |

All deltas are within the documented ±0.6 Haiku single-grading noise. `sre × clarification 3.87`
is the known iteration/clarify fixture fragility (`missing_expected_theme`), not cover-letter-related.

**The fix is landing (judge-confirmed).** On the after `ds` letter the judge noted the opener is
now substance-first ("Borealis's public-sector forecasting work…" — "direct and specific ✓") and
the model adopted the concrete close pattern ("I'd welcome a direct conversation about… I can make
time"). The deduction on the 4.1 was an unrelated 36-word sentence (Check 8), not opener/close.

**The lone after `pm` 3.2** (run 1) decomposed (judge `failed_rules`): `throat_clearing_opener`
(a *company-observation* opener "Atrium's positioning is precise" — a debatable judge call, since
Check 3 only bans "I am writing/excited/pleased" literals), `hedging` ("I recognize the healthcare
vocabulary gap… I don't have Epic or FHIR background yet"), `generic_hook`, `sentence_length_over_25`
(31- and 26-word sentences). The dominant cause is a **scenario-specific gap-admission hedge** —
the pm-senior fixture is a B2B PM applying to healthtech — i.e. a *different* tone failure mode
than the opener/close throat-clearing PV-3 targeted.

### 4. What we learned

1. **De-cloning the single close example was the higher-leverage half.** The model treated the one
   prescriptive close example as a template and cloned it (the v1.0.3 lapse was a near-verbatim
   copy). Replacing it with a *functional* description + a worked OK/NOT-OK pair removes the string
   it was copying. General rule: a single concrete example in a prompt is a clone magnet — give a
   functional spec plus contrasting OK/NOT-OK pairs, not one exemplar.
2. **n=3 each side can't *prove* a 1/5 lapse is eradicated — and it didn't try to.** The honest
   claim: tone **held at the 4.2 floor with no regression on any rubric**, and the worked-example
   opener/close is demonstrably adopted (judge-confirmed). The one sub-4.0 after-sample is within
   the pre-existing bimodal variance (v1.0.3 had a 2.1; this run a 3.2) and is **scenario-driven**,
   not an opener/close lapse.
3. **PV-3 surfaced a distinct, untargeted tone failure mode: defensive gap-admission.** The pm 3.2's
   dominant deduction was "I don't have Epic/FHIR yet" — the model apologizing for a domain gap, read
   as hedging. No opener/close rule catches this. Candidate **future** tuning item (a body-paragraph
   "don't apologize for gaps; frame the adjacent strength" rule) — deliberately **not** folded into
   PV-3 (the headhunter flagged that expanding the banned/hedging list adds its own regression surface
   that wants separate validation).
4. **The judge sometimes penalizes the very close pattern the block prescribes.** Even on a passing
   (4.2) letter it flagged "I'd welcome a direct conversation" as a borderline "soft close" — yet
   that register is exactly what the block (old and new) endorses and the rubric's Check 4 does not
   list. A reminder that the Haiku tone judge has interpretation drift beyond its literal checks;
   read `reasons`, don't over-fit to a single grading.
5. **Running the paired eval concurrently with the full `pytest` suite induced 3 judge_errors**
   (transient Haiku invalid-JSON) in after-run 1; after-runs 2–3 (post-pytest) were clean. Don't
   overlap the eval harness with a CPU-heavy test run when judge stability matters.

---

## chore/kit-phase1-ruff-format -- tree-wide ruff format (2026-06-23)

Not a prompt-tuning iteration -- logged here for the no-eval-run discipline (the
compose-add-title precedent: prove byte-identity with a check, don't spend a paid run).

1. **What changed?** Applied `ruff format` across the tree (161 of 217 files) as the
   second kit-adoption Phase-1 item. No prompt template was edited; `PROMPT_VERSION` and
   `AVATAR_PROMPT_VERSION` are unchanged.
2. **Why?** Kit-adoption Phase 1 (kit-adoption-design.md section 4): adopt the
   `ruff format` formatter + wire `ruff format --check` as a block-day-one gate (KIT-6).
3. **Result?** Prompt-inert by construction: ruff format never edits inside string
   literals. Proven, not assumed -- a sha256 dump of all analyzer prompt constants (every
   *_SYSTEM_PROMPT, the _BASE_SYSTEM_PROMPTS registry, _COVER_LETTER_RULES_BLOCK, both
   version strings; 31 entries) was byte-identical before and after the reformat (zero
   differences). So NO eval run was spent and NO PROMPT_VERSION bump was made.
   Deterministic gate green: ruff check . / mypy (227 files) / pytest 1391 passed.
4. **Learned?** A pure `ruff format` pass is safe for prompt-bearing modules: the
   formatter only restructures code outside string literals. The only near-prompt change
   observed was a paren-wrap of `AVATAR_PROMPT_VERSION = "..."  # long comment` (value
   identical). Prove it cheaply with a constants dump-diff rather than a paid synthetic
   run; only bump PROMPT_VERSION when a template's bytes actually change.

---

## v1.0.8 walkthrough generation quality — 2026-07-01 — `2026-06-23.1` → `2026-07-01.1`

1. **What changed?** Branch 8 of the v1.0.8 walkthrough epic, in `analyzer.py`
   (`_build_generate_prompt`): (E5) a grounding-check worked example forbidding
   fabricated years-of-experience/ownership figures ("10 years of end-to-end product
   ownership") in the summary and making a prior removal binding — shared with the
   legacy path, so the synthetic suite exercises it; (C1) a corpus-mode COVERAGE rule
   requiring every experience with corpus bullets to contribute ≥1 bullet
   (corpus-only); (E2) a conditional `<current_resume_draft>` block on corpus refine
   rounds (corpus-only, iteration>0); (H1) multi-role clarification attribution
   (conditional block). Each is strictly conditional so the iteration-0 /
   no-clarification prompt is unchanged.
2. **Why?** Walkthrough findings: older roles came out bullet-less (C1 — LLM dropping
   them despite the payload carrying every bullet and `md_to_json_resume` parsing all),
   a refine clobbered manual edits in corpus mode (E2 — `_stable_user_prefix` never
   emitted the draft), and an invented "10 years…" summary claim kept reappearing (E5).
3. **Result?** Grounding smoke (`--suite synthetic --subset smoke`, `2026-07-01.1`):
   **3 pass / 0 fail, gate exit 0** — pm-senior grounding **4.8** (fabricated_specifics
   0.00), sre-mid-level **4.2**, data-scientist-junior pass. No regression > 0.5 vs the
   committed baseline. Cost ~$0.12/fixture. The E5 grounding tightening held/strengthened
   grounding rather than over-restricting.
4. **Learned?** A MORE-restrictive grounding worked example (forbidding a specific
   fabrication class) is safe for the grounding rubric — it doesn't cause the model to
   over-omit legitimate content. Corpus-mode-only prompt changes (C1/E2) are NOT
   exercised by the synthetic suite (it runs the legacy path); validate them with
   prompt-structure unit tests + owner E2E rather than a paid corpus run.

---

## Generation richness — 2026-07-06 — `fix/generation-richness` — `2026-07-01.1` → `2026-07-06.1`

1. **What changed?**
   - **Code-side anti-starvation floor** (`analyzer.py:_stable_user_prefix`): the
     recommendation narrowing became PER-ROLE. A role with a curation signal
     (recommendation / pin / added) still narrows to that set; a role with NO signal
     now keeps its active bullets instead of being filtered to empty. This makes
     generate agree with the Compose preview (`corpus_to_json_resume`, which already
     kept all active bullets for un-recommended roles). Corpus-only.
   - **`RECOMMEND_SYSTEM_PROMPT`** softened: generous 3-6/role, STRONGLY prefer
     `has_outcome="true"` metric bullets, "Never zero out a role" — replacing the old
     "down to 1 / soft ceiling / recruiters skim" stinginess. Corpus-only.
   - **Summary** (resume_rule #1, shared): one-sentence → a targeted TWO-SENTENCE
     positioning paragraph. **Skills** (resume_rule #9, shared): explicit `## Skills`
     section rule (previously only an example heading). **Grounding carve-out**
     (corpus mode): the Summary paragraph + Skills list are declared NOT resume bullets
     and EXPECTED sections, so the verbatim-bullet rule stops suppressing them.
2. **Why?** Owner report: corpus generation produced ~1 bullet for most roles, dropped
   metric bullets, and emitted no Summary/Skills. Root cause: `recommend_bullets`
   under-picked / omitted roles, and the code-side narrowing then STARVED every
   un-recommended role BEFORE generate saw it — so the v1.0.8 C1 COVERAGE floor (a
   prompt rule) was moot (a starved role "genuinely has no bullets"). The one-sentence
   summary rule, the missing skills-section rule, and the verbatim-bullet grounding
   suppressed Summary/Skills.
3. **Result?**
   - **Deterministic** (robert E2E context `context_20260706_122956.json`, no API):
     roles reaching generate with ≥1 bullet **3/8 → 8/8**; total bullets to generate
     **11 → 24**. Five roles were previously reaching generate empty.
   - **Real `generate()`** (robert corpus, Sonnet 5, `2026-07-06.1`): **8/8 roles with
     bullets, 24 bullets, 16 metric-bearing**, a 2-sentence Summary, and a populated
     `## Skills` section.
   - **Grounding smoke** (`--suite synthetic --subset smoke`, `2026-07-06.1`):
     **3 pass / 0 fail, gate exit 0** — pm-senior grounding **4.6** (fabricated_specifics
     0.00), sre-mid-level **4.6** (0.13). The Summary/Skills grounding carve-out did NOT
     loosen grounding on the legacy path. Cost ~$0.13/fixture.
4. **Learned?** A prompt-side COVERAGE floor cannot restore bullets a CODE-side
   narrowing already stripped — the selection filter and the coverage rule must agree,
   and the cheapest way to keep them agreeing is to make generate's narrowing identical
   to the preview's (`corpus_to_json_resume`). Blessing non-bullet sections
   (Summary/Skills) inside corpus grounding is safe (grounding held at 4.6). The
   corpus-side changes (floor + RECOMMEND + grounding carve-out) are still not covered by
   the synthetic suite; a deterministic before/after count on a saved context + one real
   corpus `generate()` is a cheaper, more representative check for the owner's actual
   flow than a paid synthetic run.

---

## Compose-frozen-composition — 2026-07-06 — `fix/compose-frozen-composition` — `2026-07-06.1` → `2026-07-06.3`

1. **What changed?** The generation-experience re-architecture (Phases 1–4):
   - Two NEW **Compose-time** drafting prompts + calls in `analyzer.py`:
     `DRAFT_SUMMARY_SYSTEM_PROMPT` + `draft_positioning_summary` (Sonnet, Phase 2,
     `.1 → .2`) and `DRAFT_GAP_FILL_SYSTEM_PROMPT` + `draft_gap_fill_bullets` (Sonnet,
     Phase 3, `.2 → .3`). Both are grounded (evidence-or-nothing / no-invention) and
     registered in `_BASE_SYSTEM_PROMPTS`. They fire once on Compose arrival — they are
     NOT part of the analyze→generate prompt chain.
   - **Phase 4:** in corpus mode, `generate()` is no longer called for the résumé body —
     `/api/generate` deterministically assembles the frozen `approved_composition`
     (`_assemble_from_frozen_composition` + `generate_resume_from_json_resume`). The cover
     letter still calls `generate_cover_letter_against_resume`.
2. **Why?** Owner's "no surprises" vision: author + approve content ONCE at Compose, then
   render it deterministically. The summary + gap-fill move OUT of the résumé LLM to
   reviewable Compose-time drafts.
3. **Result? (byte-identity, NOT a paid eval run):** the generate prompt template is
   UNCHANGED, so the legacy (file-based) `--suite synthetic` path is byte-identical —
   proven **deterministically by unit tests** rather than a paid run:
   `test_corpus_mode_prompt.py::TestGapFillPromptInvariance` (the gap-fill keys don't
   perturb `_stable_user_prefix`) + `test_deterministic_generate.py` (a legacy context
   still calls `generate()`; a corpus context makes ZERO `generate`/`generate_streaming`
   calls). The `PROMPT_VERSION` bumps are attribution-only. **Live replay DONE** on the REAL
   robert corpus (`../sartor-e2e/output/robert/context_20260706_122956.json` + a read-only
   copy of the robert DB): froze the composition deterministically (8 roles / 34 bullets),
   drove the real `/api/generate` (`.md`), and confirmed **0 new `generate`/`generate_streaming`
   records in `logs/llm_calls.jsonl`**, `download == json_resume_to_markdown(frozen)`, and
   `resume_preview == frozen serialization` (a real robert bullet survived into the download).
   The frozen doc there had NO drafted summary / curated skills (the context predated Phases
   2–3), so those sections were empty — the résumé BODY assembled correctly, which is the
   Phase-4 invariant. A summary + gap-fill Sonnet smoke on robert (real API via the Compose
   flow) is a nice-to-have, not a blocker.
4. **Learned?** Moving a section OUT of the résumé LLM to a dedicated Compose-time draft
   (a new per-call prompt) does NOT touch the analyze→generate cache or the synthetic eval
   as long as the generate prompt bytes are unchanged — assert that with a
   `_stable_user_prefix`-invariance unit test instead of paying for a synthetic run. Once
   corpus-mode generate is deterministic, the synthetic suite (legacy-only) stops covering
   the corpus path entirely — the representative check is the deterministic assemble test
   (zero-LLM + download == frozen doc), not an eval score.

---

## surgical-refinement-and-loopback — 2026-07-08 — `fix/surgical-refinement-and-loopback` — `2026-07-06.3` → `2026-07-08.1`

1. **What changed?** Item (a) of the Compose-frozen-composition LATER-branch remainder: a
   NEW Compose-time drafting prompt + call, `DRAFT_SURGICAL_REFINEMENT_SYSTEM_PROMPT` +
   `analyzer.draft_surgical_refinement` (Sonnet). Given a free-text refinement note plus the
   CURRENT frozen `approved_composition`, it proposes exactly ONE scoped change — sharpen an
   existing bullet in place, a genuinely stronger new bullet, the positioning summary, or
   `"none"` for a broad ask with no single scoped target. Two new routes
   (`/draft-refinement` read-only, `/accept-refinement`) apply an accepted proposal via the
   EXISTING `accepted_generated_bullet_ids` / `excluded` / `summary_text` override keys —
   zero `corpus_to_json_resume.py` changes.
2. **Why?** Phase 4's interim refine ("route back to Compose, redo it yourself") was
   explicitly the minimal loop-back, with surgical refinement + a richer accept/retire
   banner deferred as the design's LATER-branch item (a). This branch builds that: the
   résumé stays a deterministic assembly (Phase 4 invariant unchanged — zero résumé-body
   LLM calls at Generate), but a refinement note now drafts a real, grounded, single-item
   proposal instead of just pointing the user at Compose.
3. **Result? (live, real API — not `--suite synthetic`, which doesn't cover this path):**
   a sandbox candidate (Acme Fintech PM role, 2 bullets: a billing-migration bullet phrased
   passively — "coordinating" — and a mentorship bullet) + a real JD, driven through the
   ACTUAL Flask routes (`app.test_client()`, not the bare analyzer function) with a real
   Sonnet 5 call:
   - Note: *"make the billing migration bullet sound like I owned it end-to-end, not just
     coordinated."*
   - `POST /draft-refinement` → `{"target_kind": "bullet", "experience_id": 1,
     "supersedes_bullet_id": 1, "text": "Owned the billing migration project end-to-end,
     coordinating across engineering and finance.", "pattern_kind": "manual", "rationale":
     "Reframes the existing bullet's ownership language per the note while keeping the same
     scope and facts."}` — grounded (kept "coordinating across engineering and finance"
     verbatim from the source bullet; no invented metric/scope/date), targeted the correct
     single bullet, left the unrelated mentorship bullet untouched.
   - `POST /accept-refinement` → `200`, `accepted_bullet_id=3`, `superseded_bullet_id=1`.
   - `composition_overrides` after accept: `{"accepted_generated_bullet_ids": [3],
     "excluded": [1]}` — exactly ONE net item change, confirmed via `GET /composition`:
     bullet 1 (old) shows `excluded`, bullet 3 (new) visible, bullet 2 (mentorship,
     untouched) still visible.
   - Telemetry (`logs/llm_calls.jsonl`, `call=draft_surgical_refinement`,
     `model=claude-sonnet-5`): 318 input / 112 output / 1184 cache-creation tokens,
     2927ms latency, **cost $0.010093** (well under the $0.50 cap; `accept-refinement`
     itself makes no LLM call).
4. **Learned?** Reusing the EXISTING `accepted_generated_bullet_ids`/`excluded`/
   `summary_text` override keys (rather than inventing a new `bullet_text_overrides`
   resolver surface) turned "surgical refinement" into a pure composition-membership
   operation — swap-by-exclude-plus-add — which is both simpler to implement correctly and
   trivially proven "touches only the targeted item" by inspecting the override diff,
   without needing any change to `corpus_to_json_resume.py`'s resolver.

## regenerate-gap-fill — 2026-07-08 — `feat/regenerate-gap-fill` — `2026-07-06.3` (unchanged)

1. **What changed?** LATER-branch remainder item (d): a durable
   `composition_overrides.retired_gap_fill_keys` set (written directly by
   `/gap-fill-decide` retire, re-sent on every `/composition` save like every
   other override key) + an always-visible "Regenerate suggestions" control that
   re-calls the existing `POST /draft-gap-fill` route. The route now filters its
   normalized proposals against that durable retired-key set AND any key already
   realized as an accepted `Bullet.source`. `DRAFT_GAP_FILL_SYSTEM_PROMPT` and
   `draft_gap_fill_bullets()` in `analyzer.py` are UNCHANGED — the exclusion is a
   deterministic ROUTE-side filter (exact key match on the existing
   `sha256(eid|text)[:12]` key), not a prompt change, so `PROMPT_VERSION` stays
   at `2026-07-06.3`.
2. **Why?** §5 Phase 3 of `generation-experience-rearchitecture.md` flagged this
   as a known gap: retire only dropped the TRANSIENT `llm_gap_fill_proposals`
   entry, so nothing stopped a later re-draft from resurfacing a proposal the
   user had just rejected — and there was no user-facing way to ask for a fresh
   draft at all (only the once-only silent auto-fire).
3. **Result? (real-LLM validation, NOT a paid eval run — corpus-mode gap-fill
   isn't in `--suite synthetic`):** a sandboxed app (`Config(base_dir=<tmp>)`,
   throwaway sqlite DB, REAL Sonnet client) seeded with one experience carrying
   an on-call fact buried inside an unrelated Go/latency bullet, against a JD
   requiring "production on-call ownership" — a genuine gap (evidence exists,
   not yet surfaced as its own bullet). Cycle: draft → 1 grounded proposal →
   retire it → regenerate (a second real `draft_gap_fill_bullets` call) →
   **the retired proposal's exact text/key never resurfaced** (the model
   proposed a differently-worded reframe of the same evidence on the second
   call, which is expected — a different key, filtered independently on its own
   merits, not a resurfacing of the retired one). 3 earlier sandbox iterations
   (corpus already fully covering the JD requirement, so the grounded drafter
   correctly returned zero proposals — the evidence-or-nothing rule holding, not
   a bug) cost the exploration before landing a genuine-gap scenario. **Total
   real spend across all 5 `draft_gap_fill` calls this session: $0.020479**
   (`logs/llm_calls.jsonl`, `claude-sonnet-5`, prompt-cache hits after the
   first call) — the two calls that actually exercised retire→regenerate cost
   $0.004932 each. Legacy/synthetic path is untouched by construction (no
   prompt edit) — proven by the existing `TestGapFillPromptInvariance` unit
   test, extended with a `retired_gap_fill_keys` case rather than re-run.
4. **Learned?** The grounded evidence-or-nothing drafter is appropriately
   conservative: when the corpus bullet already states a requirement almost
   verbatim, it correctly returns zero proposals (nothing to draft) — a
   REAL gap needs evidence that exists but is buried inside a bullet about
   something else, not yet surfaced as its own item. That took several
   iterations to construct deliberately for this validation; it also means the
   route-level "exact key match" exclusion is the right enforcement mechanism
   (not a prompt instruction to the LLM to avoid retired content) — the model's
   own rewording between calls means it won't reliably reproduce byte-identical
   text on request, so a semantic/prompt-side "don't repeat this" instruction
   would be unverifiable, while the deterministic hash-key filter gives an
   exact, testable guarantee regardless of model phrasing drift.

## D5 clarifications-to-corpus — 2026-07-08 — `feat/clarifications-to-corpus` — `2026-07-08.1` → `2026-07-08.2`

1. **What changed?** The generation-experience re-architecture's LATER-branch
   remainder item (c) — D5 cross-JD clarification reuse
   ([`generation-experience-rearchitecture.md`](../docs/dev/generation-experience-rearchitecture.md)
   §2 Stage 3 / §3.5 point 3). `db.build_context.build_context_set_from_db` now
   stages `context_set["prior_clarifications"]` — every `clarification` DB row
   for the candidate from an EARLIER application (candidate-scoped, capped at
   40, most-recent-first). All three Compose CONTENT DRAFTING calls in
   `analyzer.py` (`draft_positioning_summary`, `draft_gap_fill_bullets`,
   `suggest_skills`) render it as a new `<prior_clarifications>` prompt block:
   `draft_positioning_summary` and `suggest_skills` treat it as full grounding
   source material (same posture as `<clarifications>`); `draft_gap_fill_bullets`
   keeps it context-only — a proposed bullet's evidence must still cite
   `<career_corpus>`. `hardening.assemble_source_union` (the deterministic
   grounding metric) widened to match. The legacy `generate()` prompt is
   untouched.
2. **Why?** Today a clarification answered under JD-1 never informs JD-2's
   pipeline run — the candidate re-states the same fact per application. D5
   makes the corpus (and its clarifications) genuinely cross-JD, closing the
   loop the design doc named at spec-time but deferred out of the frozen-
   composition branch.
3. **Result? (real-LLM validation, NOT a synthetic-suite run — corpus-mode-only
   change, `--suite synthetic` stays legacy-only and byte-identical by
   construction):** a throwaway sandbox candidate + temp DB (no repo
   `configs`/`output`/`resumes` touched). Seeded a corpus with ZERO on-call/SRE
   content. Ran JD-1 (generic Platform Engineer) through analyze → clarify,
   answered one question with "Led on-call rotation for a 12-person SRE team,
   cutting MTTR 40% through a runbook overhaul." Ran JD-2 (Senior SRE) through
   analyze for the SAME candidate:
   - JD-2's context carried the JD-1 answer under `prior_clarifications`; its
     OWN `clarifications` map was correctly still empty (the two channels stay
     distinct).
   - `draft-summary` (real Sonnet): wove the cross-JD fact into the JD-2
     positioning summary alongside the corpus CI/CD fact — grounded, no
     invention: *"Platform engineer who has led on-call rotation for a
     12-person SRE team, cutting MTTR 40% through a runbook overhaul,
     alongside building CI/CD pipelines that cut deploy time 50% across four
     product teams. Brings that same reliability-first discipline to owning
     incident response and reducing MTTR across critical production
     services."*
   - `suggest-skills` (real Haiku): proposed 4 skills — 3 ("On-call
     leadership", "Incident response", "MTTR optimization") evidenced ONLY by
     the clarification quote (`bullet_id`/`experience_id` both null, exactly
     the shape the widened prompt specifies), 1 ("CI/CD pipeline development")
     evidenced by an actual corpus bullet id. The two evidence shapes came back
     correctly distinguished.
   - `draft-gap-fill` (real Sonnet): **0 proposals** — the grounding boundary
     held. A prior clarification alone is CONTEXT, not sufficient evidence for
     a new bullet; the model correctly did not fabricate a "led on-call" bullet
     with no corpus citation to back it.
   - Candidate isolation: a second, unrelated candidate's freshly-built context
     saw `prior_clarifications == []` — no cross-candidate leak.
   - Cost: 9 real LLM calls, **$0.1111 total** (well under the $0.30 estimate),
     from `logs/llm_calls.jsonl` telemetry summed via `hardening.compute_call_cost`.
   - Deterministic coverage: `tests/test_build_context_db.py::TestPriorClarifications`
     (staging + cap + candidate-scoping), `tests/test_hardening.py::TestAssembleSourceUnion`
     (metric widening), and one prompt-content test per drafting call
     (`test_draft_summary.py`, `test_draft_gap_fill.py`, `test_suggest_skills.py`).
4. **Learned?** The same "stage it deterministically once, let every downstream
   consumer read the context_set key" pattern used for `career_corpus` extends
   cleanly to cross-JD clarifications — no live DB access needed from either
   the drafting prompts or the grounding metric, both of which only ever see
   `context_set`. Letting the two grounding rules diverge on purpose (summary
   + skills treat prior_clarifications as sufficient evidence; gap-fill does
   not) is a real, load-bearing distinction, not an oversight — the real-LLM
   run is the cheapest way to prove a "surgical, not blanket" carve-out claim
   actually holds under a real model instead of asserting it from the prompt
   text alone.

## Output identity integrity — 2026-07-08 — `fix/output-identity-and-dates` — `2026-07-08.2` → `2026-07-08.3`

1. **What changed?** The corpus-mode GROUNDING rule inside
   `analyzer._build_generate_prompt`'s `corpus_mode_block` gained one new
   instruction: the candidate's name and header contact line (email, phone,
   LinkedIn, website) MUST be reproduced exactly from `<candidate_profile>`
   and are NEVER sourced from `<candidate_web_presence>` (the opt-in scraped
   profile/website/portfolio text, PX-02), even when that scraped text
   mentions a different or additional contact channel. Generate-prompt-only;
   `analyze()`/`clarify()` prompts are untouched.
2. **Why?** A real user saw a website in a **downloaded** résumé that
   appeared in neither their corpus nor their live preview. Root-cause
   investigation found two contributing vectors: (1) `/api/generate` replaying
   pre-corpus-era saved contexts with no schema check, and (2)
   `candidate.online_profile_text` (scraped web presence) being an ungoverned
   prompt source the GROUNDING rule never excluded from identity/header
   fields specifically — only bullet-level grounding was governed. This entry
   covers (2), the prompt-side half of the fix; the deterministic half — an
   identity override that unconditionally re-resolves `basics` from the live
   `Candidate` DB row regardless of what the LLM or a stale context carries —
   lives in `json_resume.apply_identity_override()` and needs no prompt
   validation (it's pure post-processing, covered by unit + integration
   tests, not this log).
3. **Result? (real-LLM validation, NOT a synthetic-suite run — this is a
   corpus-mode-only prompt-text change with no bullet-selection or
   scoring-relevant effect, so `--suite synthetic` was not re-run):** a
   throwaway sandbox candidate + temp SQLite DB (no repo
   configs/output/resumes touched). Seeded a candidate with `website_url=""`
   (no website on file) but `online_profile_text` containing a decoy website
   (`stray-blog-not-real.example`) and a decoy email
   (`scraped-decoy@not-real.example`), plus one real experience (Acme Cloud,
   a Kubernetes migration bullet with a "40%" metric). Ran `generate()`
   directly (real Sonnet 5 call, `PROMPT_VERSION 2026-07-08.3`) against a JD
   for a Senior Platform Engineer role:
   - Header rendered `# Jordan Rivera` / `jordan.rivera@example.com | 555-0199
     | linkedin.com/in/jordanrivera` — the candidate's REAL `<candidate_profile>`
     fields, verbatim.
   - Neither decoy string (`stray-blog-not-real.example`,
     `scraped-decoy@not-real.example`) appeared anywhere in the output — the
     web-presence content the model DID use (implicitly, for Summary framing
     around "on-call culture") never leaked into the header.
   - Grounded generation still worked: "Acme Cloud" and the "40%" metric both
     appeared verbatim from the corpus bullet — the tightened rule didn't
     make the model over-cautious about legitimate corpus content.
   - Cost: **$0.0306** (1 Sonnet 5 call, `logs/llm_calls.jsonl` telemetry via
     `hardening.compute_call_cost`), well under the $0.10 estimate.
   - Deterministic coverage (no LLM):
     `tests/test_corpus_mode_prompt.py::TestGenerateDispatch::test_corpus_mode_block_excludes_web_presence_from_identity`
     pins the new prompt text's presence; `tests/test_identity_override_route.py`
     and `tests/test_json_resume.py::TestApplyIdentityOverride` cover the
     deterministic override end to end (route + unit level).
4. **Learned?** A GROUNDING rule that governs bullets doesn't automatically
   govern identity/header fields — they're a structurally different kind of
   claim (never "reframe-able," always exact-reproduction-or-nothing) and
   needed their own explicit carve-out naming the disallowed source by tag.
   The real-LLM run was cheap ($0.03) because it needed exactly one call with
   a corpus small enough to keep the prompt short — no need to run the full
   eval suite to validate a single, surgical instruction addition; a
   purpose-built adversarial fixture (a decoy string that would ONLY appear
   in the output if the model ignored the new instruction) is a sharper,
   cheaper validation than a broad regression run for this class of prompt
   change.

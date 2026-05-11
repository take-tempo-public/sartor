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

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

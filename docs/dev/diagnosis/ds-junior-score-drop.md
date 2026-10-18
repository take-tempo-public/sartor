# Diagnosis — `data-scientist-junior` grounding score fell after item 140's prompt changes (item 140, part b)

> **Status:** hypothesis only. Nothing in this branch has been run yet; the design below is registered BEFORE any paid
> call so the result cannot move the goalposts.
> **Branch:** `fix/ds-junior-score-drop`

---

## Symptom

After item 140's prompt changes (`PROMPT_VERSION 2026-08-14.1` to `2026-10-17.2`), the `data-scientist-junior` fixture's
grounding score read lower in some runs. Nobody knows whether the change did it or whether this fixture's score simply
varies run to run.

---

## Observed

All from the item-140 session; none of it re-run here. n is 1 to 2 per arm.

- **Generate mode:** `2.1`, `3.2` under the old prompts (`2026-08-14.1`), then `1.2`, `1.2` under `2026-10-17.1`
  (`docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:115-118`, `:152-160`).
- **Assemble mode:** `4.8`, `4.8` under the old prompts, `4.8`, `4.8` under `.1`, then **`1.2` once** under `.2`, with
  `failed_rules` `invented_credential`, `invented_metric`, `jd_pandering`, `scope_inflation`; the letter claimed
  "building hands-on fluency in scikit-learn and statsmodels now"
  (`docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:152-156`).
- **The same kind of claim is flagged in an old-prompt run too** (generate `2.1`), so the claim type is not new
  (`docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:157`).
- **The fixture is a deliberate mismatch:** the corpus seed (`evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json`)
  is a platform engineer and the fixture a junior data scientist; the judge names the mismatch ("not the candidate
  named in the fixture") in every run (`docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:115-118`).
- **Result records are not durable:** `evals/results/*` is gitignored (`.gitignore:62`), so this dossier is the only
  durable copy of any per-run figure from this branch.
- **What a record holds** (read from `evals/results/20261017_132814Z.jsonl`): one record per rubric with `rubric`,
  `score`, `score_max`, `reasons`, `failed_rules`, `prompt_version`, `eval_mode`, `cost_usd`, and the `leaked_handles`
  block (`total`, `letter_carriers`, `letter_date`, `letter_head`). A smoke run scores only the `grounding` rubric
  (`evals/runner.py:706-707`). No generated text is kept.

---

## Falsified

_(Nothing new on this branch yet.)_

---

## Inferred

**All unproven.** Three explanations; the experiment below can separate only the first from the other two.

1. **Variance** of the generator or the LLM judge on a seed that does not match the fixture, so low scores occur under
   either prompt set and the `1.2` is a draw.
2. **The no-ids persona rule** (`_NO_HANDLES_IN_PROSE_RULE`, on 14 personas) changed how the letter handles claims the
   corpus cannot support.
3. **The reworded analyze schemas, the `<letter_date>` block, or the runtime guard** changed the analysis the letter is
   written from.

What would settle it: low scores under the OLD code at a rate comparable to the new (explanation 1), or lows only under
the new (explanation 2 or 3, which this experiment cannot tell apart; bisecting is a separate step).

---

## Falsification

**The experiment, registered before any paid run.**

- **Arms.** A (old) = commit `a970033`: prompts unchanged (`PROMPT_VERSION 2026-08-14.1`), the `leaked_handles`
  instrument present, no guard, no letter date. B (new) = `main` at `7807c81` (`PROMPT_VERSION 2026-10-17.2`). Overrides
  alone cannot test "the change": `--prompt-overrides` swaps only the named persona constants, and three of the four
  changes (schemas, `<letter_date>`, guard) are not persona constants.
- **Unit.** One `python evals/runner.py --suite synthetic --subset smoke --fixture data-scientist-junior
  --seed evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json --mode assemble --out-dir <scratch>/<arm>` run:
  the grounding rubric only, assemble mode (the population that dropped from `4.8` to `1.2`). Generate mode is not run:
  it scored low under the old prompts too.
- **Interleaved**, alternating which arm goes first each pair.
- **"Low" is fixed in advance as grounding score `< 3.0`.**
- **Stage 1: N = 4 per arm. Stage 2: N = 8 per arm**, only when stage 1 is inconclusive.
- **Decision rule.** `a` = lows in A, `b` = lows in B.
  - `a >= 1` at any point: lows occur under the old code, so the `1.2` is not evidence of a regression; report "not
    attributable to the change at this n; consistent with variance" and stop.
  - `a = 0` and `b >= 2` of 4, or `a = 0` and `b >= 3` of 8: the new code plausibly causes lows; report a regression
    found, with the rates, and stop for the owner.
  - Otherwise inconclusive: stage 2; after stage 2 report rates with exact 95% (Clopper-Pearson) intervals and say it
    cannot rule out a small effect. No third stage without asking.
- **Spend cap $2.50,** measured from telemetry (`hardening.compute_call_cost` over the `logs/llm_calls.jsonl` rows in
  each run's window), not from the result record's `cost_usd`.
- **Integrity checks.** Each arm must run its own code: `analyzer.__file__` and `PROMPT_VERSION` are printed per arm
  before any paid call, and the driver rejects a record whose `prompt_version` does not match its arm.
- **Limits stated in advance (C-0).** One fixture. A mismatched seed inflates variance. The judge's variance is not
  separated from the generator's (no generated text is kept to re-judge). Even a difference between A and B does not say
  which of the three explanations holds.

---

## The fix

None. This branch changes no production code; its output is a measurement.

---

## Acceptance bar

The registered rule has been applied to the recorded runs, the per-run table (arm, run id, score, failed rules, handles,
date correctness, telemetry cost) is in this file, the spend is reported from telemetry, and the stated limits are
repeated beside the conclusion.

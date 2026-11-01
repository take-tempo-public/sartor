```toml
schema = 1
id = 189
kind = "item"
title = "Eval redesign step 9: pinned judge, schema parse, judge-to-judge calibration"
status = "blocked"
blocked_on = "step 8 (item 188) has not landed"
depends_on = [188]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-judge-calibration"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Pinned judge, schema parse, judge-to-judge agreement (no gold set), over-suppression check; owner picks the judge."
```

Step 9 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 9. Scope lives there.
Owner decisions 3 and 5: the judge model is chosen here with data, and there is no human-labelled gold set, so agreement is judge-to-judge (consistency, not correctness). Label it so. Re-check Haiku 4.5's status first; it was not re-checked on 2026-10-20.

## Updates

### 2026-10-31 -- inputs from item 194's calibration subset (feat/eval-calibration-subset)

Item 194 scope 3 asked for judge-to-judge agreement; the owner moved it here. Nothing on that branch measures agreement. What it leaves for this item (dossier: `docs/dev/blast-radius/eval-calibration-subset.md`):
- **Judge cost, measured:** `judge_grade` about $0.0113 per call (187 calls), `judge_distinctiveness` about $0.0012 (28 calls); 48.5% of a 28-fixture assemble run's spend. A second judge on every record would add about that much again, or more on a larger pin.
- **No harness support for a second judge:** `JUDGE_MODEL` is fixed (`evals/runner.py:131`), `--model-override` cannot move it, and a result record does not keep the judged text (`runner.py:469`), so a second judge has to be added to the live run, not run later over saved results.
- **A judge parse failure is invisible in the call log:** 1 `judge_error` ("judge response was not valid JSON", recorded as score 0) while the log showed 0 non-ok rows.
- **A possible judge defect to check first:** on 4 of 28 outputs the grounding judge counted about two fewer years of experience than the generated text claimed (for example 13 against 11), and the deterministic check flagged none. The judge payload carries no current date. Inferred, untested: that the judge is counting to an earlier date. If so, correct years claims score as inventions and the grounding rubric needs the date in its payload before agreement means anything.

### 2026-10-20 -- filed during docs/eval-redesign-decisions

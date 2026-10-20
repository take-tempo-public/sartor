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

### 2026-10-20 -- filed during docs/eval-redesign-decisions

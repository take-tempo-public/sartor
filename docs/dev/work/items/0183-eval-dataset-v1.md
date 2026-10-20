```toml
schema = 1
id = 183
kind = "item"
title = "Eval redesign step 3: standard dataset, captured inputs, reachability check"
status = "blocked"
blocked_on = "step 2 (item 182) has not landed"
depends_on = [182]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-v1"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "O*NET synthetic matrix, captured upstream inputs, reachability check; on-demand public fetch only if it clears C-2."
```

Step 3 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 3. Scope lives there.
Re-read the O*NET and dataset licence pages at the primary source before committing anything (the design doc's research is reported, not verified). The on-demand fetch is an outbound connection: charter C-2 names two destinations, so it takes the D-6 opt-in route and passes `tests/test_egress_allowlist.py`, or returns to the owner as an amendment.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

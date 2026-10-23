```toml
schema = 1
id = 184
kind = "item"
title = "Eval redesign step 4: call evals for ingest and analyze kinds"
status = "blocked"
blocked_on = "step 3 (items 183 and 191) has not landed"
depends_on = [183, 191]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-calls-ingest-analyze"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Call evals: extract_experiences, analyze_*, clarify, iterate_clarify. Deterministic part blocks v1.1.0."
```

Step 4 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 4. Scope lives there.
Per owner decision 2, the deterministic-check eval for each kind blocks the v1.1.0 cut; judged parts may follow.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

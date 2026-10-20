```toml
schema = 1
id = 185
kind = "item"
title = "Eval redesign step 5: call evals for the 11 compose kinds"
status = "blocked"
blocked_on = "step 4 (item 184) has not landed"
depends_on = [184]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-calls-compose"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Call evals for the 11 compose-group kinds. Deterministic part blocks v1.1.0."
```

Step 5 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 5. Scope lives there.
Per owner decision 2, the deterministic-check eval for each kind blocks the v1.1.0 cut; judged parts may follow.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

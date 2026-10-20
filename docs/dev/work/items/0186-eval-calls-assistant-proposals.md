```toml
schema = 1
id = 186
kind = "item"
title = "Eval redesign step 6: call evals for avatar, proposals and clarification promotion"
status = "blocked"
blocked_on = "step 5 (item 185) has not landed"
depends_on = [185]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-calls-assistant-proposals"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Call evals: avatar_answer, critique_proposal, promote_clarification_to_bullet; deterministic part blocks 1.1.0."
```

Step 6 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 6. Scope lives there.
Per owner decision 6 the avatar prompt joins the catalog but stays out of `_BASE_SYSTEM_PROMPTS`, keeping `AVATAR_PROMPT_VERSION`. Per decision 2 the deterministic part blocks the v1.1.0 cut.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

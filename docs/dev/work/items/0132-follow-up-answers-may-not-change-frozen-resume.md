```toml
schema = 1
id = 132
kind = "item"
title = "\"Submit answers and regenerate\" may not change the résumé once Compose is saved"
status = "open"
decision_owner = "agent"
branches = ["feat/user-docs"]
refs = [
  "static/app.js:2983-3161",
  "blueprints/generation.py:837-877",
  "hardening.py:1827-1861",
  "blueprints/analysis.py:678-688",
]
summary = "Follow-up answers save, but regenerate re-assembles the frozen composition with no AI call. UNVERIFIED."
```

**Status of the evidence: code-read only, NOT observed.** This comes from an exploration
subagent's read, and this session has not independently traced it (charter C-12: a
subagent's unverified report is flagged as such).

**The hypothesis.**
- **The flow.** Step 6 → **Get follow-up questions** → **Submit answers and regenerate** merges
  the answers and calls `runGeneration()` (`static/app.js:3113-3154`).
- **The regenerate.** When the application has an `approved_composition`, `/api/generate`
  assembles the résumé from it deterministically (`blueprints/generation.py:837-877`,
  `hardening.py:1827-1861`).
- **Nothing resets it.** `/api/answer-clarifications` does not appear to clear that composition.
- **Where the answers go.** They reach Candidate memory (`blueprints/analysis.py:678-688`) and
  the context file, but not the regenerated body.

**Next step:** reproduce it in demo mode or with a stubbed UX run, and diff the résumé before
and after. User docs on `feat/user-docs` describe the button by its label only and make no
claim about the result.

## Updates

### 2026-09-29 — filed on `feat/user-docs` (Epic D D3)

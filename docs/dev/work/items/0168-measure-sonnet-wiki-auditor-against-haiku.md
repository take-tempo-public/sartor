```toml
schema = 1
id = 168
kind = "item"
title = "Measure the Sonnet 5 wiki auditor against the Haiku one it replaced: catch counts and cost per pass"
status = "watching"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "agents/wiki-grounding-auditor.md",
  "commands/wiki-self-update.md",
  "docs/wiki/log.md",
  "docs/dev/decisions.md",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "The auditor moved to Sonnet 5 on a measured miss rate, but its own catch rate and cost per pass are unmeasured."
```

Item 166 moved `wiki-grounding-auditor` from Haiku to Sonnet 5 because three consecutive
passes (`docs/wiki/log.md`) had review catch what the Haiku auditor marked SUPPORTED. Nothing
measures the replacement. The PX-47b amendment in `docs/dev/decisions.md` says so: "no
measurement of the difference exists yet".

**What would close this:** the next `/wiki-self-update` pass logs three catch counts apart (the
cite check's, the auditor's, review's, as step 8 of `commands/wiki-self-update.md` now asks) and
its spend. Two or three passes show whether review still catches sentences the auditor passes.
If it does, the model change was not the lever and the four new auditor checks are what to look
at next. If it does not, record the cost as accepted.

**Not decided here:** a threshold for "worth the cost". That is the owner's call, with numbers.

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

Filed while closing item 166, so the unmeasured half of that decision is on the board and not
only in a log entry. No pass has run with the Sonnet auditor yet.

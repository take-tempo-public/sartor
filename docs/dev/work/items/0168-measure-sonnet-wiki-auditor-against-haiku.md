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

### 2026-10-19 — first full-window data, `chore/wiki-checkpoint-pass`

The checkpoint pass ran 18 Sonnet 5 audits (auditor-first, owner-approved, before any scribe) and 14 re-audits, about 32 calls. Counts, kept
apart, are in the `docs/wiki/log.md` entry "checkpoint-advancing pass": auditor DRIFTED 10 and UNSUPPORTED 22 on 14 of 18 pages; three pages
clean; re-audit 13 clean and 1 UNSUPPORTED, an error in the orchestrator's own correction. **What this does not show:** whether the
auditor catches what review would catch, because no scribe ran and review was not run blind to the auditors' reports. It is a catch count
for one model, with no Haiku comparison, so the item stays open. Cost: no per-call spend was captured (the calls run on the session, not
`.api_key`), so cost per pass is still unmeasured.

```toml
schema = 1
id = 129
kind = "item"
title = "Personal portfolio/interviewer framing survives in two frozen records"
status = "open"
decision_owner = "user"
branches = ["feat/docs-split"]
refs = [
  "docs/dev/archive/app-blueprints-design.md",
  "docs/dev/perf/R1_PHASE2_RESULTS.md",
]
summary = "Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?"
```

**Observed.** On 2026-09-28 the owner directed that the project should not keep references
to "reviewers and interviewers" ("that was meant to be personal ... it is for the project"). D2
removed that framing from the published `docs/dev/perf/PERFORMANCE_HISTORY.md`. A grep for
`portfolio-grade|interviewers` over non-handoff docs also hits
`docs/dev/archive/app-blueprints-design.md` and `docs/dev/perf/R1_PHASE2_RESULTS.md`. Both
are records, which the link policy (design §3.1) freezes. They were therefore left and
surfaced, not edited.

**Decision needed (owner):** does this owner direction override record-freezing for these
two files, and should a wider sweep (handoffs, ledger) be done?

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2)

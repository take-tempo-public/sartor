```toml
schema = 1
id = 93
kind = "item"
title = "Epic C planning must deliberately choose the invoker session shape: per-sprint fresh sessions vs continuous window with the step-9 tripwire"
status = "blocked"
blocked_on = "owner decision at Epic C planning — the choice lives in the epic's own authorization-record scope sentence"
decision_owner = "user"
branches = ["fix/n1-invoker-context-budget"]
refs = [
  "docs/dev/diagnosis/n1-invoker-context-budget.md",
  "docs/dev/n1-baseline-pipeline.md",
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "Run 5 reproduced the accumulation signature at the INVOKER level; the one deterministic fix is the session boundary."
```

**Origin.** Run 5 (session `b0769daa`, 2026-08-13) stopped at the B1b sprint boundary
on a doubled external signal — two `compacted` receipts during the gate waits — one
sprint into an intended three-sprint continuous window. The owner-directed method
review (`fix/n1-invoker-context-budget`, 2026-08-14) found the §16 design axiom — the
monitor "holds no LLM context of its own and never accrues it across sprints"
(`docs/dev/epic-a-chain-design-corrections.md` §16.4.1 item 1) — was never applied to
the de-facto invoker, which is a full LLM session. The §16.1.B measurement (sessions
bounded to ~1 sprint: 3, 3 compactions; multi-sprint continuous windows: 11, 14) has
now reproduced at the invoker level.

**The decision (owner's alone — it is the epic authorization record's sentence).**
For Epic C (board 38) and later epics, the epic's §"Execution mode + authorization
record" must choose deliberately, not inherit:

- **(a) Per-sprint fresh invoker sessions** with a mandatory boundary handoff — the
  deterministic fix: context age is bounded by construction, not vigilance. Handoff
  loss is bounded and inspectable; compaction loss is unbounded and invisible. All
  machinery exists and is live-validated (closer-written next-sprint briefs, the S4
  epic-state banner, step 9's three-line resume state, `resumeFromRunId`). Cost: one
  owner relaunch per sprint (~1.5–2h cadence at run-5 pace).
- **(b) Continuous window** with runbook step 9's external-signal stop as the tripwire
  plus the reducers landed on `fix/n1-invoker-context-budget` (report digests,
  invoker-scoped kickoff reading). This is observed current behavior formalized; run 5
  executed the tripwire cleanly.

**Not decidable by an agent.** Charter W-1 / the S1 lesson: the scope sentence is the
owner's typed selection, single-homed in the epic's authorization record — agents cite
it, never restate or pre-decide it. Epic B is unaffected (B2 is the terminal sprint;
the question is moot there).

## Updates

### 2026-08-14 — filed during `fix/n1-invoker-context-budget` (the run-5 method review)

Filed at the owner-approved review's close so the decision is on the board before Epic
C planning starts, per the review plan's "Decision recorded for the owner, NOT
implemented" section. Evidence and the full trade statement:
`docs/dev/diagnosis/n1-invoker-context-budget.md` (O2 + "The fix" item 2).

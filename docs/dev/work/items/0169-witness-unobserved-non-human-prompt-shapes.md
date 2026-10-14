```toml
schema = 1
id = 169
kind = "item"
title = "Non-human prompt shapes the witness has not seen (scheduled wakeup, cron, usage-limit resume) still arm the pause"
status = "watching"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "scripts/enforcement/guards/interrogative_witness.py",
  "docs/governance/enforcement.md",
  "docs/dev/work/items/0143-witness-pause-batched-with-exitplanmode-approves-stale-plan.md",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "Only a <task-notification> prompt is exempt from arming; other injected turns, not yet observed, still arm it."
```

Item 164 exempts a `UserPromptSubmit` whose `prompt` begins `<task-notification>`
(observed 2 of 2, `docs/dev/diagnosis/recurrence-guardrails.md` O6). Item 143's record names
other turns that re-armed the pause and were never captured at the hook: a usage-limit resume
prompt (`docs/dev/work/items/0143-…md:86`), and a `/loop` or `ScheduleWakeup` firing is the
same kind of event. The witness treats every shape it has not seen as a human prompt, which is
the safe direction and today's behavior.

**What would close this:** the witness trace (removed in `960dcd9`; `git show d3e5296` has it)
re-enabled for a session that receives one of those turns, to see whether the payload has a
distinguishing leading tag. Do **not** guess a tag from the transcript: the transcript's
`origin.kind` was not in the hook payload (O6).

**Also recorded here, same class:** `plan_gate` reads `.git/HEAD` itself and reports a detached
HEAD as `""`, so its `plan-archived` receipt stays in the tracked shard there (item 165's
declared limit). Rare; deferred with the reason.

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

Filed while closing item 164 so the unobserved shapes are on the board.

```toml
schema = 1
id = 95
kind = "item"
title = "The owner's mid-run-pause pre-authorization names resumeFromRunId, which replays a blocked agent's block-description as success"
status = "blocked"
blocked_on = "owner amendment — the pre-authorization is the owner's own recorded standing decision, so only the owner can restate it"
decision_owner = "user"
branches = ["feat/ats-conformance"]
refs = [
  "docs/dev/work/items/0084-build-n1-baseline-pipeline.md",
  "docs/dev/n1-baseline-pipeline.md",
  "docs/dev/work/items/0094-interrogative-witness-kills-pipeline-runs.md",
]
summary = "The pre-authorized recovery would silently skip the sprint's implementation instead of resuming it."
```

**The conflict.** Item 84 records a standing owner pre-authorization for exactly the
mid-run interrogative-witness case (item 94): *verify the flag's `verbatim` is exactly
the interrogative-witness PAUSE and resume via `resumeFromRunId`; any other hook name
still stops for the owner.*

That remedy is **broken by the runbook's own stated limit 4**
(`docs/dev/n1-baseline-pipeline.md` §"Stated limits"): *"Resume caches a blocked agent's
block-description as success. If an agent is hook-blocked but returns a structured
object describing the block, `resumeFromRunId` replays that object instantly."*

The hook-blocked implementer does **not** throw — it returns a structured
`kind: "hook_block"` object, which is exactly the shape limit 4 describes. So following
the pre-authorization literally on run 6 would have replayed the block description as a
completed implementer result and marched the pipeline into refuter → judge → closer over
a sprint whose code was **never written**. The closer would then have written a handoff
and terminal ceremony for work that does not exist.

**Two independently-correct documents, in direct conflict.** Neither is wrong in
isolation: the pre-authorization was recorded before limit 4 was understood in this
context, and limit 4 is accurately stated. The failure is that nothing reconciles them,
and the pre-authorization is the one an invoker reaches for under time pressure.

**Not verified live.** Run 6 did **not** attempt the resume — the trap was caught by
reading, so no run has actually observed the cached replay. Stated rather than claimed
(C-0/C-12): the mechanism is documented and the return shape matches, but the specific
replay-as-success behavior is inherited from the runbook's limit, not re-derived here.

**The amendment needed (owner's, because it restates the owner's own authorization).**
Replace "resume via `resumeFromRunId`" with **"re-invoke the sprint stage fresh"**, and
add the invoker's own step: consume the armed pause with a deliberate invoker
`Edit`/`Write` *before* re-invoking, so the fresh run does not immediately re-arm into
the same stop.

## Updates

### 2026-08-14 — filed at the close of run 6 (`feat/ats-conformance`)

Found while enumerating recovery options after run 6's `hook_block` stop. Surfaced
before acting on the pre-authorization rather than after, which is the only reason the
run was not marched forward over an unimplemented sprint.

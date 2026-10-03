```toml
schema = 1
id = 143
kind = "item"
title = "A witness-paused plan Write batched with ExitPlanMode gets the STALE plan approved"
status = "open"
decision_owner = "agent"
branches = ["chore/release-v1.1.0"]
refs = ["hooks/edit-write-dispatcher.sh", "hooks/check-plan-approved.sh", "docs/dev/work/items/0087-*.md"]
summary = "Witness paused the plan Write; ExitPlanMode in the same batch still ran, so the owner approved the old plan text."
```

**Observed (2026-10-02, session `1712f657`, `chore/release-v1.1.0`).**
- **What was sent:** one assistant message issued two calls: a `Write` of the new E1 pre-flight
  plan to `~/.claude/plans/golden-dancing-flame.md`, then `ExitPlanMode`.
- **What happened:** the `Write` returned `PAUSE (interrogative-witness): first Edit/Write since
  the last user prompt`, but `ExitPlanMode` still ran. The approval dialog showed the file's
  **previous** content (the Epic D PR plan), and the owner clicked approve.
- **How it was caught:** the `ExitPlanMode` result echoes the approved text, which didn't match
  what had just been written.
- **What happened next:** the session did not act on that approval. It rewrote the plan,
  re-entered plan mode and asked again.

**Why it matters.** The plan gate's guarantee is "the owner approved THIS plan." Here a witness
that is fail-open by design (item 87) made a fail-closed gate approve the wrong text, with
nothing in the gate's own output saying so.

**Mechanism candidates (not built):**
- `ExitPlanMode`'s PreToolUse refuses when the plan file's mtime is older than the session's
  most recent `Write` attempt on it.
- The witness exempts `~/.claude/plans/` writes in plan mode. Writing the plan is the one
  directive plan mode always calls for.

## Updates

### 2026-10-02 — filed on `chore/release-v1.1.0` (E1 pre-flight)

### 2026-10-02 (later) — RECURRED in the same session, with a Bash call this time

The same shape happened again. A `Write` of the handoff header was PAUSEd, and the dependent
`Bash` call in the same batch (assemble the handoff, then `verify_doc_template --event
generated`) still ran. It built the handoff from the OLD header and validated it.
- **Caught by** reading the PAUSE before committing. Nothing was committed from it; the header
  was re-written and the handoff reassembled.
- **So the class is wider than `ExitPlanMode`.** Any call batched after a paused Write can act
  on stale content.
- **No mechanism authored on this branch (C-11, declared).** A PreToolUse hook sees one call
  at a time, so it cannot cancel the rest of a batch.
- **What a hook can still do:** the `ExitPlanMode` mtime check (candidate 1 above) covers the
  high-stakes half.
- **The general half needs** the witness to exempt directive-continuation turns, or a harness
  change. Surfaced to the owner.

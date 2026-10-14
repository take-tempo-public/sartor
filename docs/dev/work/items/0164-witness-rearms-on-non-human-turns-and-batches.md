```toml
schema = 1
id = 164
kind = "item"
title = "The interrogative witness re-arms on task-notifications and hand-backs, and pauses only the first call of a parallel batch"
status = "open"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "scripts/enforcement/guards/interrogative_witness.py",
  "scripts/enforcement/adapters/prompt_witness_hook.py",
  "docs/governance/enforcement.md",
  "docs/dev/work/items/0087-interrogative-prompt-witness-hook.md",
  "docs/dev/work/items/0094-interrogative-witness-kills-pipeline-runs.md",
  "docs/dev/work/items/0143-witness-pause-batched-with-exitplanmode-approves-stale-plan.md",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "The witness re-arms on every UserPromptSubmit, so notifications re-pause edits; a batch pauses only its first call."
```

**Observed** (`docs/dev/diagnosis/recurrence-guardrails.md` O1, O2). `record_prompt`
(`scripts/enforcement/guards/interrogative_witness.py:132-151`) writes `witnessed: false` for
every `UserPromptSubmit` and never reads the prompt. This session's transcript records its two
typed prompts with `origin.kind == "human"` and the background-agent notification with
`origin.kind == "task-notification"`; the state file read `prompt_seq: 5` against 2 typed
prompts. `decide()` marks `witnessed` before returning the refusal (`:190-191`), so later calls
in a parallel batch are allowed.

The handoff series has recorded this as "no mechanism possible" since item 143
(`docs/dev/handoffs/regenerate-keeps-cover-letter.md` Recurrences 3, 6 or more instances).

**Not observed — open:** the `UserPromptSubmit` payload's own shape for a notification. The
transcript's `origin` field is the transcript's, not necessarily the hook payload's. The
instrument (plan step A1) settles this before the discriminator is chosen.

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

Filed from the handoff's Recurrences section, recurrence 3 (C-11: a recurrence obligates a
mechanism on the branch that recognizes it).

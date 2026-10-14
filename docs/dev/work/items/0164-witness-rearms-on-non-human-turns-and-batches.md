```toml
schema = 1
id = 164
kind = "item"
title = "The interrogative witness re-arms on task-notifications and hand-backs, and pauses only the first call of a parallel batch"
status = "closed"
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
resolution = "2026-10-14, fix/recurrence-guardrails. A `<task-notification>` prompt no longer arms the pause (observed 2 of 2; the payload has no origin field), and for SARTOR_WITNESS_BATCH_WINDOW_S (default 3 s) after a pause the calls that follow are refused as its siblings (owner decision: the transcript cannot show the batch at hook time, observed 2 of 2). The window is a timing heuristic and fails open; it is labeled as one. Prompt shapes not seen (scheduled wakeups, cron) still arm."
verified_by = [
  "tests/test_interrogative_witness.py::TestNonHumanTurnsDoNotArm",
  "tests/test_interrogative_witness.py::TestBatchWindow",
  "tests/test_governance_hooks_gate.py",
]
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

### 2026-10-14 — closed on `fix/recurrence-guardrails`

Evidence and the decision are in `docs/dev/diagnosis/recurrence-guardrails.md` O6-O11. Both new
test classes were mutation-checked in-process (A2 disabled: 6 of 11 fail; window disabled: 3 of
11 fail), and the whole path was driven through the real `hook.py` entry points (O11).

**Declared, not fixed (C-0):** the 1.13 s sibling gap is a single sample; the window is a
heuristic, so a sibling slower than 3 s still lands, and a re-run inside it is refused once more.
A sibling that is *not* refused is the failure this leaves; no per-call hook can close it,
because the batch is not in the transcript at hook time.

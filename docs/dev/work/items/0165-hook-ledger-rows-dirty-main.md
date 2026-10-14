```toml
schema = 1
id = 165
kind = "item"
title = "Hook-written compacted and plan-archived ledger rows leave a tracked file modified on main"
status = "open"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "scripts/enforcement/adapters/claude_context_hook.py",
  "scripts/enforcement/plan_gate.py",
  "docs/dev/prov/SPEC.md",
  "docs/dev/ledger/README.md",
  "docs/dev/work/items/0055-ledger-event-vocabulary-drift.md",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "record_compaction and the plan gate append to the tracked ledger on any branch, so main is left dirty."
```

**Observed** (`docs/dev/diagnosis/recurrence-guardrails.md` O3). Both writers append to
`docs/dev/ledger/<session>.jsonl` with no branch check: `record_compaction`
(`scripts/enforcement/adapters/claude_context_hook.py:173-226`) and the plan gate's
`plan-archived` row (`scripts/enforcement/plan_gate.py:276-292`). Three commits exist only to
carry a stray row: `71d0d17`, `7bcbc3a` and `2097a40`.

**Decided (owner, 2026-10-14):** divert only on trunk. On a branch the rows keep going to the
tracked shard; on `main`/`master`/detached HEAD they go to an untracked spool under
`.claude/state/ledger/` (already ignored by `.gitignore:104`).

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

Second instance of a known class (the handoff's Recurrence 1 notes the first). Item 55 covers
the SPEC vocabulary drift for these two events; this item is the dirty-tree defect.

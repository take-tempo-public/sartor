```toml
schema = 1
id = 165
kind = "item"
title = "Hook-written compacted and plan-archived ledger rows leave a tracked file modified on main"
status = "closed"
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
resolution = "2026-10-14, fix/recurrence-guardrails (owner decision: divert only on trunk). scripts/enforcement/ledger_spool.py routes every hook-written receipt: on main, master or a detached HEAD it goes to the untracked .claude/state/ledger/<session>.jsonl; on any other branch it stays in the tracked shard. compaction_count reads both, so the C-12 disclosure still counts a session's compactions. A directory that is not a git work tree keeps the tracked shard. SPEC.md section 3 now names compacted and plan-archived (item 55)."
verified_by = [
  "tests/test_ledger_spool.py::TestCompactionReceipt",
  "tests/test_ledger_spool.py::TestPlanArchivedReceipt",
  "tests/test_ledger_spool.py::TestWritersRouteThroughTheHelper",
  "tests/test_ledger_spool.py::TestTheSpoolStaysUntracked",
  "tests/test_c12_disclosure_gate.py::TestM3CompactionDisclosure",
]
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

### 2026-10-14 — closed on `fix/recurrence-guardrails`

Reproduced first (`docs/dev/diagnosis/recurrence-guardrails.md` O12): six of the new tests
failed on the unfixed writers, `git status --porcelain` reporting `docs/` untracked on `main`;
the four that passed were the feature-branch, no-git and `.gitignore` controls. After the fix
the same six pass, and a drive through the real `hook.py capture-before-compact` and
`restore-evidence` entries on a throwaway repo gave a clean tree and a spool row on `main`, a
tracked row on a branch, and a count of 2 across both (O13).

**Declared, not fixed (C-0):** a repo where `git` itself fails keeps the tracked shard;
`plan_gate` reports a detached HEAD as an empty branch name, so its receipt stays tracked
there; the spool is machine-local and is not part of the committed record. A trunk-time
`compacted` row is therefore no longer visible in `git log`. Items 84, 93, 94 and 110 cite
branch-time rows, which are unchanged.

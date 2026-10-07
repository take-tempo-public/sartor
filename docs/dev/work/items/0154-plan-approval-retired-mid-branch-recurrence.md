```toml
schema = 1
id = 154
kind = "item"
title = "Recurrence of item 110: a plan approved on main was retired mid-branch after checkout + rebase; the next Edit hit NO EDIT APPROVAL"
status = "closed"
decision_owner = "agent"
branches = ["fix/console-run-lock-hardening", "fix/python-direct-hooks-plan-gate"]
refs = [
  "hooks/check-plan-approved.sh",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/work/items/0110-plan-approval-retired-on-unmerged-branch.md",
  "docs/dev/handoffs/hook-guard-false-blocks.md",
]
summary = "Approved on main, then checkout+rebase; next Edit hit NO EDIT APPROVAL. Item 110's class; cause unverified."
resolution = "2026-10-07, fix/python-direct-hooks-plan-gate: cause OBSERVED, not the rebase. Transcript 2b79cef7 shows mark-plan-approved.sh cancelled after ExitPlanMode and check-plan-approved.sh cancelled on every Edit (28-36 s vs 20 s), the archive at 19:54:50Z with no manifest or receipt. A second path was reproduced live (the merge hook grepped tool output). Both paths reproduced by tests that failed on the .sh hooks. Fixed by the Python plan gate (fast, fail-closed mark, newer-plan block) and by removing cleanup-plan-on-merge."
verified_by = [
  "tests/test_plan_approval_scoping.py::TestKilledHookRetirements",
  "tests/test_plan_approval_scoping.py::TestStaleStampAndKilledRetire::test_killed_retire_never_leaves_a_live_marker",
]
```

**Observed (reported, not reproduced).** The only source is the `fix/hook-guard-false-blocks`
handoff (`docs/dev/handoffs/hook-guard-false-blocks.md`, Carried-forward "New, unfiled" bullet
and Recurrence 5). It records the following:
- The plan was approved via ExitPlanMode while on `main`.
- The session then checked out and rebased `fix/hook-guard-false-blocks`.
- The next `Edit` was refused with `NO EDIT APPROVAL`. The archive dir's mtime was 12:54
  (2026-10-05).
- Re-entering plan mode and re-approving cleared it.

No hook log, ledger receipt or pointer-file state was captured, so **the cause is not
verified.** This item does not inherit item 110's two proven causes: the killed retire and the
stale stamp. Both were fixed on 2026-09-22.

**Inferred (unproven):** this matches the class in the owner's memory
`reference-flush-stale-plan-stamp-on-branch-not-main`. An approval made on `main` is
reconciled against a branch stamp on the first production edit after the switch.

**Workaround used on `fix/console-run-lock-hardening` (2026-10-06), not a fix:**
- Approve on `main` only for setup that makes no production edit.
- Switch to the branch, re-enter plan mode, and re-approve there.
- The production edits that followed raised no `NO EDIT APPROVAL`.
This is prose discipline and **unenforced** (C-11).

**Fix direction (C-11, a recurrence of a closed item):** the first move is an instrument, not a
fix. Capture the pointer files, the branch stamp and `plan-archived` ledger receipts across the
sequence "approve on main → checkout → rebase → Edit", in a throwaway worktree (see memory
`reference-hook-manual-testing`). Only then decide on a mechanism. No mechanism was authored on
`fix/console-run-lock-hardening`, which is bounded to items 112/117–121; that gap was surfaced to
the owner at that branch's close-out.

## Updates

### 2026-10-06 — filed on `fix/console-run-lock-hardening`

### 2026-10-06 — did not recur on `fix/wiki-relevance-cited-scripts` (a control data point)

Session `b6966e40`: the plan was approved via `ExitPlanMode` while on `main` (542da4a), then
`git checkout -b fix/wiki-relevance-cited-scripts` ran with **no rebase**, and the next `Edit`
(to `tests/test_wiki_relevance_classification.py`) succeeded — no NO EDIT APPROVAL. So
"approve on main → `checkout -b` → Edit" alone does not reproduce it; the filed sequence also
had a **rebase**, which this run lacked. A single run, not a rate — it narrows the instrument's
first arm to the rebase step but proves nothing about it.

### 2026-10-07 — closed on `fix/python-direct-hooks-plan-gate`

The mechanism is observed (dossier `docs/dev/diagnosis/python-direct-hooks-plan-gate.md` O1, O2). The rebase is not part of it: the
retire came from a timeout-killed reconcile 47 minutes later, acting on a marker the killed
`mark` never replaced. The three reproductions failed on the shell hooks at `5431b83` and pass
on the port.

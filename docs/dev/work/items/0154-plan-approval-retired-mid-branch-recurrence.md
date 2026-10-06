```toml
schema = 1
id = 154
kind = "item"
title = "Recurrence of item 110: a plan approved on main was retired mid-branch after checkout + rebase; the next Edit hit NO EDIT APPROVAL"
status = "open"
decision_owner = "agent"
branches = ["fix/console-run-lock-hardening"]
refs = [
  "hooks/check-plan-approved.sh",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/work/items/0110-plan-approval-retired-on-unmerged-branch.md",
  "docs/dev/handoffs/hook-guard-false-blocks.md",
]
summary = "Approved on main, then checkout+rebase; next Edit hit NO EDIT APPROVAL. Item 110's class; cause unverified."
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

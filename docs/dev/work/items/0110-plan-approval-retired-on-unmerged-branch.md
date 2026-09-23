```toml
schema = 1
id = 110
kind = "item"
title = "The plan-approval reconciler retired a live approval mid-branch: plan archived and marker removed while the approved branch was unmerged"
status = "open"
decision_owner = "agent"
branches = ["fix/witness-subagent-scope"]
refs = [
  "hooks/check-plan-approved.sh",
  "docs/dev/diagnosis/plan-approval-branch-switch-gap.md",
  "docs/dev/work/items/0056-plan-retirement-half-completes-on-main.md",
]
summary = "An approved plan was archived and its marker removed while its branch was unmerged; the next Edit hit NO EDIT APPROVAL."
```

**Observed (session `0ea1b8bf`, 2026-09-22).**

- The plan `pickup-the-handoff-i-curious-wombat.md` was approved via ExitPlanMode on
  `main`. `fix/witness-subagent-scope` was created, and edits proceeded: a dossier Write,
  a guard Edit, a scratch Edit, a test Edit, a guard Edit, and one commit (`9e457a1`).
- Then an `Edit` to `scripts/enforcement/guards/interrogative_witness.py` was refused by
  `check-plan-approved.sh` with
  `NO EDIT APPROVAL: No approved plan found for this project.`
- Right after the refusal, the plan file sat at
  `~/.claude/plans/archive/20260923T025313Z-142537ca4cdd/pickup-the-handoff-i-curious-wombat.md`.
  The archive dir's mtime was `2026-09-22 19:53:14` local, and the plan file's mtime was
  `19:51`. No `.approved-C--Dev-sartor` file existed in `~/.claude/plans/`.
- `fix/witness-subagent-scope` was **not merged**: its only non-main commit, `9e457a1`,
  was not on `main`.
- Re-approval via ExitPlanMode wrote `.approved-C--Dev-sartor` (20:47:54) and
  `.current-C--Dev-sartor` (20:47:37). No `.approved-branch-C--Dev-sartor` stamp existed
  at that moment.

- **The session compacted at the same minute.** `docs/dev/ledger/0ea1b8bf-913f-48d6-a7f1-5e54cf8769b3.jsonl`
  row: `{"event": "compacted", ..., "branch": "fix/witness-subagent-scope", "ts": "2026-09-23T02:58:41Z"}`
  (19:58:41 local). The plans dir's mtime at inspection was `19:58:24`. The plan archive
  (19:53) comes *before* the compaction. The marker removal falls within seconds of it.

- **No provenance receipt for the archive.** `grep -rh 20260923T025313Z docs/dev/ledger/`
  returns nothing. `hooks/lib/retire-approved-plan.sh` states that every retirement writes a
  `plan-archived` ledger receipt, and receipts exist for earlier archives (e.g.
  `20260812T144954Z`). The archive dir timestamp is 19:53:14.47 local. The reflog shows
  `checkout: moving from main to fix/witness-subagent-scope` at 19:52:28, 46 s earlier. The
  first Edit/Write after that checkout (the dossier Write) **succeeded**. No
  `PLAN RETIRED:` message was seen, although `check-plan-approved.sh`'s retire path prints
  one and exits 2.

**Inferred (UNPROVEN).** The strongest lead is a PreCompact/SessionStart path (a
compaction-triggered session restart running plan retirement) that removes the marker. That
is suggested by the 19:58 coincidence and has not been read in code.
Separately, for the 19:53 archive: A stamp left by the previous session's branch
(`fix/ci-wait-required-from-protection`, merged as PR #142) survived into this session.
On the first production edit after the new approval, the reconciler read that stale stamp,
found its branch merged, and archived the *new* approval. That the marker vanished later
than the archive (edits kept passing for a few minutes) is unexplained. To know, I would
have to SEE the stamp's contents at approval time and the order of archive vs marker
removal, i.e. a reproduction in a throwaway worktree.

**Why it matters now.** Epic C runs overnight as an unattended pipeline. A retired
approval stops every subagent `Edit` with `NO EDIT APPROVAL`, and the run escalates or
dies. Related: item 56 (retirement half-completes on main).

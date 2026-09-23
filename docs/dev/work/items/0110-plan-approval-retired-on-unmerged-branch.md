```toml
schema = 1
id = 110
kind = "item"
title = "The plan-approval reconciler retired a live approval mid-branch: plan archived and marker removed while the approved branch was unmerged"
status = "closed"
decision_owner = "agent"
branches = ["fix/witness-subagent-scope", "fix/plan-approval-retired-mid-branch"]
refs = [
  "hooks/check-plan-approved.sh",
  "docs/dev/diagnosis/plan-approval-branch-switch-gap.md",
  "docs/dev/work/items/0056-plan-retirement-half-completes-on-main.md",
]
summary = "An approved plan was archived and its marker removed while its branch was unmerged; the next Edit hit NO EDIT APPROVAL."
resolution = "Fixed on fix/plan-approval-retired-mid-branch (2026-09-22). Two proven causes. (1) The retire path in check-plan-approved.sh measured 5.66-14.72 s against a 5 s hook timeout; a timed-out hook is non-blocking and was killed after the plan mv but before the pointer rm, leaving a live marker over a moved plan. Fixed by kill-safe ordering in hooks/lib/retire-approved-plan.sh (pointers removed first, via builtins) and timeout 5 -> 20. (2) mark-plan-approved.sh never cleared the branch stamp, so a stamp from an already-merged branch retired a fresh approval on its first edit. Fixed by removing the stamp on approval. Stated limit: speed is not fixed (post-fix 8.5-21.5 s under load), so at most one edit can slip through on a killed hook; the approval itself never survives. Speed is item 111. Evidence: docs/dev/diagnosis/plan-approval-retired-mid-branch.md."
verified_by = [
  "tests/test_plan_approval_scoping.py::TestStaleStampAndKilledRetire (both xfail-strict on a180ad2, passing after the fix)",
  "direct timing of hooks/check-plan-approved.sh on a copied pointer state: 4/4 pre-fix runs > 5 s (dossier Observed)",
]
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

- **Counter-observation: a later compaction did NOT remove the marker.** The same session
  compacted again at `2026-09-23T04:06:07Z` (21:06 local; ledger row on this branch). At
  21:1x, `.approved-C--Dev-sartor` (20:47:54), `.current-…` (20:47:37) and
  `.approved-branch-C--Dev-sartor` (20:59:06) were all still present and the plan file was
  still in place. So compaction alone does not remove the marker. If the 19:58 coincidence
  is causal, it needs another condition, such as the stale-stamp state present only before
  the first stamp of this session.

- **The archive dir has no `manifest.json`.** `ls` of
  `archive/20260923T025313Z-142537ca4cdd/` shows only the plan file.
  `retire_approved_plan` (`hooks/lib/retire-approved-plan.sh`) writes the manifest and the
  ledger receipt in one `python3` heredoc, *after* the `mv` and *before* `rm -f` of the
  pointers. `check-plan-approved.sh` is wired with `"timeout": 5`
  (`.claude/settings.json:33-34`).

**Inferred, leading hypothesis (UNPROVEN, 2026-09-22):**

- The hook was killed by its 5 s timeout partway through `retire_approved_plan`: after the
  `mv`, before the python step and the `rm`.
- A timed-out hook is non-blocking, so the Write proceeded. That explains the successful
  dossier Write, the missing manifest, the missing receipt, and the missing
  `PLAN RETIRED:` message.
- A later invocation found the plan already moved. It skipped the archive (no dir, no
  basename, so no receipt), reached `rm -f`, and left no trace. That fits item 56's
  "dies mid-function" shape exactly.
- The trigger would be the previous session's **stale stamp**, which named the merged and
  pruned `fix/ci-wait-required-from-protection` (branch gone → `_should_archive` true). It
  was reconciled on this session's first production edit, *after* the new approval.
- That is a second defect: a stale stamp retires an approval it never belonged to.
- The instrument that settles it: time the hook end to end in a throwaway worktree with a
  stale stamp. Is the retire path >5 s under load? Does a fresh approval get archived?

Earlier lead, for the 19:58 removal: is a PreCompact/SessionStart path (a
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

## Updates

### 2026-09-22 22:48 local — live check after merge (PR #144, `a078ca1`)

The first Edit on `docs/epic-c-kickoff`, whose stamp named the merged and deleted
`fix/plan-approval-retired-mid-branch`, drew a clean
`PLAN RETIRED: branch 'fix/plan-approval-retired-mid-branch' has already merged …` on the
first attempt. Afterwards: archive `20260923T054821Z-142537ca4cdd` holds the plan
**and** `manifest.json`; the ledger row
`{"event": "plan-archived", …, "branch": "docs/epic-c-kickoff", "archive_id": "20260923T054821Z-142537ca4cdd", …}`
was written; no pointers were left. This is the first complete, receipted retirement of the
session. The fresh approval granted afterwards survived its first edits.

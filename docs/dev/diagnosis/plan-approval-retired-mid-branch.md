# Diagnosis — a fresh plan approval is retired mid-branch (item 110)

> **Status:** root cause PROVEN: the 5 s hook timeout kills the retire path partway (measured 5.66-14.72 s), plus a stale stamp that retires fresh approvals (test fails on HEAD).
> **Branch:** `fix/plan-approval-retired-mid-branch`

---

## Symptom

In session `0ea1b8bf` (2026-09-22), an approval granted via ExitPlanMode was archived while
its branch was unmerged. A later Edit was refused with `NO EDIT APPROVAL`. First record:
`docs/dev/work/items/0110-plan-approval-retired-on-unmerged-branch.md`.

---

## Observed

- **Instance 1 (19:53 local).** Archive dir `~/.claude/plans/archive/20260923T025313Z-142537ca4cdd/`
  holds only the plan file: **no `manifest.json`** and **no `plan-archived` ledger row**
  (`grep -rh 20260923T025313Z docs/dev/ledger/` → nothing). The triggering Write
  succeeded. Details: item 110.
- **Instance 2 (21:43:59 local), reproduced deliberately.** `fix/witness-subagent-scope` had
  merged as PR #143 (`f755920`). Then `git checkout -q -b fix/plan-approval-retired-mid-branch`
  ran, with the stamp still reading `branch=fix/witness-subagent-scope` /
  `base=9cafbdede4a8…`. The first `Write` on the new branch was refused **only** by the
  item-87 witness (`PAUSE (interrogative-witness): …`). No `PLAN RETIRED:` line appeared.
  Immediately afterwards:
  - `archive/20260923T044359Z-142537ca4cdd/` existed, dir mtime `21:44:00.44`, containing
    only `pickup-the-handoff-i-curious-wombat.md`: **no `manifest.json`**;
  - the plan file was gone from `~/.claude/plans/`;
  - `.approved-C--Dev-sartor` (20:47:54), `.current-C--Dev-sartor` (20:47:37) and
    `.approved-branch-C--Dev-sartor` (20:59:06, still naming the merged branch) were
    **all still present**;
  - `grep plan-archived docs/dev/ledger/0ea1b8bf*.jsonl` → nothing.
- `retire_approved_plan` (`hooks/lib/retire-approved-plan.sh`) runs, in order: `mkdir`+`mv`
  of the plan → `git rev-parse` → one `python3` heredoc (manifest + receipt,
  `2>/dev/null`) → `rm -f` marker/current/stamp → return. The caller then prints
  `PLAN RETIRED:` and exits 2. Both instances stopped after the `mv` and before the
  `rm`. A python failure alone cannot explain it: `rm -f` runs after python unconditionally.
- **Instance 3 (21:45), no sibling block.** The retried `Write` of this dossier had no
  witness pause (already consumed) and **went through**. Afterwards all three pointers were
  still present, there was no new archive dir, no receipt, and no `PLAN RETIRED:`. So the
  hook died partway through its retire path with no sibling refusal on the call.
- **Timing measurement, 21:46, the decisive one.** `check-plan-approved.sh` was run
  directly on a **copy** of the live pointer state. The command was a temp `HOME` holding
  the three pointer files, the stamp's mtime restored to `2026-09-22 20:59:06`,
  `CLAUDE_PROJECT_DIR='C:\Dev\sartor'`, and a stdin Edit payload. Output:

  ```
  PLAN RETIRED: branch 'fix/witness-subagent-scope' has already merged (or no longer exists) — its approval was archived, not deleted.
  Write a plan and call ExitPlanMode to start the next task.
  rc=2 elapsed=14.72s
  ```

  Three more runs of the same setup: `9.82s`, `7.94s`, `5.66s` (`rc=2` each). **4/4 runs
  exceed the 5 s timeout** (range 5.66–14.72 s). A `bash -x` profile with
  `PS4='+ $EPOCHREALTIME '` shows no single hot step. The cost is roughly 20 forked
  processes at 0.3–1.05 s each: `git rev-parse` 1.05, `git merge-base` 1.04, `cygpath`
  0.91, `python3 -` 0.79, `python3 -c` 0.61, `git show-ref` 0.30, and so on. The no-retire
  fast path measured 1.98 s once.
- **Instance 4 (~21:50), completion.** A later edit's hook run finished inside the timeout:
  `PLAN RETIRED: branch 'fix/witness-subagent-scope' has already merged …`. The next edit
  got `NO EDIT APPROVAL`. All three pointers were then gone. It is the same retirement,
  finally completed on the Nth attempt.
- `check-plan-approved.sh` and `edit-write-dispatcher.sh` are sibling PreToolUse hooks on
  the same matcher, each with `"timeout": 5` (`.claude/settings.json:30-40`).

---

## Falsified

- **(B) sibling cancellation as the explanation.** Instance 3 died partway through with no
  sibling refusal on the call, and the timing measurement explains every instance on its own.
- **"Compaction removes the marker."** A compaction at 21:06 left every pointer intact
  (item 110).

---

## Inferred

_(Superseded by the Results below: (A) and the stale stamp are proven, and (B) is
falsified as the sole cause. Kept as the pre-experiment record.)_

Something terminates `check-plan-approved.sh` between the `mv` and the `rm`. Two rivals,
both unproven:

- **(A) The 5 s hook timeout.** The retire path runs two cold `python3` starts plus about
  five `git` calls, on a machine that was running the gate / UX tier at instance 1.
- **(B) Sibling cancellation.** In instance 2 the sibling witness hook blocked the same call.
  If the harness cancels the remaining hooks once one blocks, the plan hook dies wherever it
  happens to be. At instance 1 the Write was not refused at all, which argues against (B)
  as the only cause.

Separately (deterministic, independent of what kills it): `mark-plan-approved.sh` does
**not** clear `.approved-branch-*`. A stamp left by an already-merged branch therefore
outlives a **new** approval and retires it on the first edit. That is instance 1's
trigger: session start, the previous session's merged branch, then a fresh approval.

---

## Falsification

1. **Stale stamp vs fresh approval (deterministic, test-first).** In a throwaway repo:
   approve → branch A → edit (stamp) → merge A → **re-approve** → branch B → edit. HEAD
   behavior is expected to be `exit 2 PLAN RETIRED`. If it exits 0, this candidate is dead.
2. **(A) timing.** Run `check-plan-approved.sh` directly on a staged retire scenario, with
   the same stdin shape, under `time`, idle and under load. >5 s supports (A); well under
   5 s weakens it.
3. **(B) cancellation.** Hard to reproduce outside the harness. If (A) is falsified, the
   remaining explanation is (B). It is then stated as a harness limit, and the fix must
   hold regardless of when the hook is killed.

**Results (2026-09-22, on HEAD `f755920`):**

- (1) `TestStaleStampAndKilledRetire::test_fresh_approval_survives_a_stale_stamp` **fails
  on HEAD**: `assert 2 == 0`. The fresh approval is retired. Candidate confirmed.
- (2) confirmed by the timing measurement above (4/4 runs > 5 s).
- (3) falsified as the sole explanation (instance 3).
- A kill-safety reproduction, `test_killed_retire_never_leaves_a_live_marker`, **fails on
  HEAD**. A `python3` shim stalls the retire heredoc, the hook is killed there, and the
  marker is still live (`AssertionError: a hook killed mid-retire must never leave a live
  marker behind`). Both were committed as `xfail(strict=True)` in `a180ad2`, before any
  fix.

C-10: `scripts/enforcement/blast_radius.py` has no entry for `hooks/` or
`.claude/settings.json` (grep: no match). No gated surface is touched.

---

## The fix

1. **`hooks/mark-plan-approved.sh`**: a fresh approval removes `.approved-branch-$KEY`.
   A new approval supersedes any stamp, and `check-plan-approved.sh` late-binds a new one
   on the next production edit (the existing design).
2. **`hooks/lib/retire-approved-plan.sh`**: kill-safe ordering. The pointers are read with
   builtins (`IFS= read -r`, no `cat` fork) and removed **first**. Only then come the
   archive `mv`, manifest and receipt. A kill at any later point leaves "no approval"
   (fail closed), never a live marker over a moved plan. It also drops two forks: a builtin
   `${path##*/}` for `basename`, and an optional 4th `branch` arg that
   `check-plan-approved.sh` now passes (`$CUR_BRANCH`) in place of a `git rev-parse`.
   `cleanup-plan-on-merge.sh` keeps the 3-arg form and its fallback.
3. **`.claude/settings.json`**: the `check-plan-approved.sh` timeout goes from 5 to 20. It
   is a ceiling; the fast path is unaffected.

**Stated limit (C-0).** This fixes *correctness*, not *speed*. Post-fix timing on a copy of
the live state (retire path through to `PLAN RETIRED`, manifest written, pointers gone):
**21.45, 8.53, 14.87 s**, on a machine carrying VS Code, WSL and other sessions. That is
still ~15 forks at a variable 0.3–1 s. One run exceeded even the new 20 s ceiling. When
that happens the killed hook's own edit proceeds (a timed-out hook is non-blocking), but
the approval is already gone, so the *next* edit is refused. At most one edit slips
through; the approval never survives. Cutting the fork count (one python call doing
mkdir/mv/manifest/receipt with in-process path conversion) and the ~2 s per-edit fast
path is filed separately as item 111. (An earlier post-fix timing, `5.44 / 2.46 / 3.31 s`,
was a **setup error**: the plan file was written after the marker, so the hook returned
`PLAN NOT APPROVED` without reaching the retire path. Discarded.)

---

## Acceptance bar

- `TestStaleStampAndKilledRetire` (2 tests): xfail-strict on `a180ad2`, passing after the
  fix. The whole of `tests/test_plan_approval_scoping.py` passes (28).
- Live: after this branch merges, the first edit on the next branch gets a clean
  `PLAN RETIRED` with a `plan-archived` receipt written, and the next fresh approval
  survives its first edit. To be observed by the kickoff branch and recorded in its
  handoff.

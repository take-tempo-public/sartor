# Diagnosis — plan approvals retired mid-branch, and the hooks that should stop it time out (items 154, 111, 152, 143)

> **Status:** two retire mechanisms OBSERVED in session transcripts (O1, O2). One link in O1 is
> still only inferred: which line `mark-plan-approved.sh` died on (see `## Inferred`).
> **Branch:** `fix/python-direct-hooks-plan-gate`

---

## Symptom

Item 154: a plan was approved via `ExitPlanMode` on `main`. The session checked out and
rebased `fix/hook-guard-false-blocks`, and the next `Edit` was refused with `NO EDIT APPROVAL`.
Re-approving cleared it. When the item was filed, no hook log or pointer state had been captured
(`docs/dev/work/items/0154-plan-approval-retired-mid-branch-recurrence.md`).

---

## Observed

Sources:
- The Claude Code session transcripts (JSONL) under `~/.claude/projects/C--Dev-sartor/`. Each
  hook the harness cancels leaves an `attachment` of type `hook_cancelled`, with `hookName`,
  `command`, `durationMs`, `timedOut` and `timeoutMs`.
- The plan archives under `~/.claude/plans/archive/`.

They were read with a `python3 -c` scan over `"timestamp"` windows (2026-10-07, session
`08aa18b5`), and the archives with `ls -la --time-style=full-iso`.

### O1 — item 154's filed instance: hook timeouts, not the rebase

Transcript `2b79cef7-1384-4089-b860-bd4864c0e9aa.jsonl`, 2026-10-05, branch
`fix/hook-guard-false-blocks`:

- `18:56:09.154Z`: a `Write` to `~/.claude/plans/linear-brewing-frog.md` (the session's new
  plan). `hook_cancelled` `PreToolUse:Write`, `command`
  `${CLAUDE_PROJECT_DIR}/hooks/edit-write-dispatcher.sh`, `durationMs 7483`, `timeoutMs 5000`.
- `18:56:44.486Z`: `ExitPlanMode`. `19:03:11.445Z`: `hook_cancelled`
  `PostToolUse:ExitPlanMode`, so **`mark-plan-approved.sh` was killed**.
- `19:07:54.466Z`: Bash
  `git worktree remove C:/Dev/sartor-wt-hooks && git checkout -q fix/hook-guard-false-blocks && git rebase -q main && …`.
- `19:32:59.396Z`: `hook_cancelled` `PreToolUse:Write`, `check-plan-approved.sh`,
  `durationMs 35690`, `timeoutMs 20000`. `19:37:17.978Z`: the same hook, `durationMs 28392`.
- 19:50–19:55Z: every `Edit` shows **both** PreToolUse hooks cancelled, first
  `edit-write-dispatcher.sh`, then `check-plan-approved.sh`. Examples:
  `toolu_01EzgjLTfZtdxYsSkEVKYz7k` (19:50:35, 19:50:42) and `toolu_01LLzuurKgPDbCfXzTS5g2QD`
  (19:53:58, 19:54:14). The Edits went through. **A cancelled hook does not block, so no
  Edit|Write guard ran on these Edits.**
- `toolu_013s3aWLkoV1QPNAcwncTduS`: dispatcher cancelled `19:54:38.647Z`,
  `check-plan-approved.sh` cancelled `19:54:55.312Z`.
- The archive directory `~/.claude/plans/archive/20261005T195450Z-142537ca4cdd/` has archive
  id timestamp `19:54:50Z` and directory mtime `2026-10-05 12:54:53.399 -0700`. It contains
  only `reactive-roaming-hummingbird.md`, whose mtime is `2026-10-03 13:21:06 -0700`: an
  **older session's plan, not `linear-brewing-frog.md`**. It has **no `manifest.json`**.
- **No `plan-archived` receipt** for `20261005T195450Z-142537ca4cdd` exists in any
  `docs/dev/ledger/*.jsonl`. The only October receipt is `20261003T202002Z-142537ca4cdd`
  (`chore/flake-shard-slim`).
- `19:56:13.828Z`, `19:56:30.872Z`, `19:56:37.935Z`: three Edit results starting
  `PreToolUse:Edit hook error: [${CLAUDE_PROJECT_DIR}…`, the reported `NO EDIT APPROVAL`.
- In the same session the other hooks timed out too: `SessionStart:startup` `restore-evidence.sh`
  (`durationMs 12016`, `timeoutMs 5000`), and `UserPromptSubmit`
  `interrogative-prompt-witness.sh` (`durationMs 7252`, `11873`, `12897`).

### O2 — a second retire mechanism, live in session `08aa18b5` (2026-10-07)

- `06:12:02.791Z`: a read-only Bash call,
  `cat hooks/mark-plan-approved.sh hooks/cleanup-plan-on-merge.sh hooks/wiki-freshness-reminder.sh hooks/capture-before-compact.sh`.
  Its output contains `cleanup-plan-on-merge.sh`'s own source, which includes the three
  pre-filter phrases (`git merge`, `--no-ff`, `Merge made by`).
- HEAD was `main` at `b5c9ddf`, the PR #159 merge commit (two parents). So the hook's
  structural check ("HEAD must be a merge commit") passed.
- Archive `~/.claude/plans/archive/20261007T061209Z-142537ca4cdd/`: id timestamp `06:12:09Z`,
  directory mtime `2026-10-06 23:12:11.633 -0700`. It holds
  `handoff-docs-dev-handoffs-hook-guard-fal-spicy-oasis.md`. **No `manifest.json` and no
  ledger receipt.**
- `06:12:12.191Z`: `hook_cancelled` `PostToolUse:Bash` for that call
  (`toolu_01366oXWRSAV8R69FjfWswjt`).
- The pre-filter in `hooks/cleanup-plan-on-merge.sh` greps `$INPUT`, the **whole** PostToolUse
  payload, tool output included.

### O3 — cancellation is routine on this machine

Session `08aa18b5`, before any edit: `hook_cancelled` `PostToolUse:Bash` at `06:11:59.444Z`,
`06:12:12.191Z`, `06:12:50.904Z` and `06:14:01.098Z` + `06:14:01.975Z`. That is 4 of the first 8
Bash calls. Free RAM on this machine has been 0.5–0.8 GB across the recent sessions (previous
handoff).

### Control point — this session

- `ExitPlanMode` on `main` at about 06:25Z.
- Snapshot `2026-10-07T06:26:16Z`: `.approved-C--Dev-sartor` (mtime `23:25:38 -0700`) →
  `C:/Users/iam/.claude/plans/peppy-beaming-koala.md`; `.current-C--Dev-sartor` → the same file;
  **no `.approved-branch-C--Dev-sartor`**. So `mark` completed this time.
- Then `git checkout -b fix/python-direct-hooks-plan-gate`. The first Write after that (this
  dossier) **succeeded**. The stamp then read `branch=fix/python-direct-hooks-plan-gate`,
  `base=b5c9ddf…` (mtime `23:27:36 -0700`). The late-bind works when `mark` completes.

---

## Falsified

- **"The rebase step is what retires the approval"** (the narrowing on item 154, 2026-10-06).
  This was not tested by experiment. It is **not needed**: O1's retire came from a reconcile
  that ran 47 minutes after the rebase. That reconcile ran inside a hook killed by timeout, and
  the marker it acted on pointed at an older session's plan. O2 retired a plan with no checkout
  or rebase at all. The rebase may change ref mtimes and so trigger a reconcile, but neither
  observed event needs it.

---

## Inferred

**Hypothesis, not fact.**
- In O1, `mark-plan-approved.sh` was killed before `rm -f "$STAMP"`, and possibly before
  `cp "$CURRENT" "$MARKER"`. That left the previous session's stamp (an already-merged branch)
  and its marker (pointing at `reactive-roaming-hummingbird.md`) live.
- Each later Edit then reconciled that stale stamp in `check-plan-approved.sh`, needing several
  `git` forks at about 1 s each (item 111). It was killed by the 20 s timeout before it reached a
  decision, and so before the `touch "$STAMP"` that advances the baseline.
- The attempt at 19:54:50 got far enough to archive and `mv`, and was killed before the
  `python3` manifest/receipt step. Hence an archive with a plan file but no manifest and no
  receipt.
- **Gap:** no artifact shows which line `mark` died on, or the stamp's contents at the time. The
  archived plan being an older session's is consistent with this, but does not prove it.

**The class:** item 110's two proven causes (the killed retire and the stale stamp) recur, not
from new logic but because the hooks are slower than their timeouts on this machine. A
cancelled PreToolUse hook is non-blocking, so on this machine a slow gate is a gate that is off.

---

## Falsification

Deterministic reproductions in `tests/test_plan_approval_scoping.py`, run against the **current**
`.sh` hooks in a temp repo with a fake `HOME`:

- **(a) O2.** A PostToolUse Bash payload whose `tool_input.command` is not a merge, but whose
  `tool_response` carries the three phrases, while HEAD is a merge commit. The test asserts the
  approved plan is **not** archived. **Must fail on HEAD.**
- **(b) O1's stale-stamp path.** A fresh approval (marker → new plan), with a stamp left over
  from a merged branch (the state a `mark` killed before its `rm` leaves behind). Checkout a new
  branch and Edit. The test asserts that a `mark` interrupted at any point never leaves an
  approval that the next Edit retires: either "no approval" or a valid one. **Must fail on HEAD.**

- **If either passes on HEAD:** that half of the mechanism is dead. Stop and widen.
- **If both fail:** proceed to the port (item 111) and the timeout work.

O1's archived plan was the **old** session's. So `mark` most likely died before its `cp`, not
between `cp` and `rm`. (b) therefore splits into two tests, one per kill point.

**Run against the current `.sh` hooks on this branch, 2026-10-07:**
`python -m pytest tests/test_plan_approval_scoping.py -k TestKilledHookRetirements -p no:rerunfailures -q`
gave `3 failed, 30 deselected in 232.61s`. All three fail as predicted:

- `test_merge_phrases_in_tool_output_never_retire_on_a_pr_merge_head` (a, O2):
  `AssertionError: printed merge phrases archived a live plan (O2)`. The test runs every
  PostToolUse Bash command **as wired in settings.json**, so it follows the wiring after the
  change.
- `test_newer_unapproved_plan_blocks_edits_under_the_old_approval` (b1, `mark` killed before any
  write): `assert 0 == 2`. A plan written **after** the live approval is not detected, so edits
  go ahead under the previous approval. That is O1's observed shape: the old plan was the one
  archived.
- `test_mark_killed_between_marker_and_stamp_never_retires_the_fresh_plan` (b2, `rm` stalled by
  a shim and `mark` killed there):
  `stderr="PLAN RETIRED: branch 'fix/task-a' has already merged …"`. The fresh plan was archived
  by the stale stamp.

**Verdict:** both halves are confirmed as reachable defects. Which kill point O1 hit is still
inferred, and both are now covered.

---

## The fix

_After the experiment._

---

## Acceptance bar

_After the experiment._

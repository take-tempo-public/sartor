# Diagnosis — plan approvals retired mid-branch, and the hooks that should stop it time out (items 154, 111, 152, 143)

> **Status:** both retire mechanisms OBSERVED (O1, O2) and reproduced by tests that failed on
> the shell hooks and pass on the port. Fixed, and verified live in this session (O6). One link
> in O1 stays inferred: which line `mark-plan-approved.sh` died on (see `## Inferred`).
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

**Whole-session count**, transcript `08aa18b5…jsonl` up to the settings switch (about
07:43Z). It was taken by joining each `tool_use` id to its `hook_cancelled` attachments:
- **40** Edit/Write calls. The old `edit-write-dispatcher.sh` was cancelled on **31** and
  `check-plan-approved.sh` on **10**.
- **95** Bash calls. A `PostToolUse:Bash` hook was cancelled on **72**.

Examples: `07:40:53Z`, `edit-write-dispatcher.sh` `durationMs 7340` (`timeoutMs 5000`);
`07:41:06Z`, `check-plan-approved.sh` `durationMs 20812` (`timeoutMs 20000`).

So on most of this branch's own edits before the switch, no Edit|Write guard ran. The
branch's evidence and consumer gates held because the work followed them, not because they
fired.

### O4 — item 111 baseline, before any change (the `.sh` wiring at `5431b83`)

Harness: the session scratchpad's `hook_timing.py before 10`. It runs each settings.json command
string under `bash -c`, N=10, with a sandbox `HOME` and witness-state dir. Guard cases use
`CLAUDE_PROJECT_DIR` = this repo, and the retire case uses a temp repo. Entries on one matcher
are timed **in sequence**; the harness runs them in parallel, so per-matcher wall time in a
live session is lower than these sums, though the cost is the same. This session's own hooks
were running throughout (each of its tool calls fires them). Free RAM: 524 MB at the start, 2803
MB at the end. Started `2026-10-07T00:09:20`.

| Case | median | p90 | min | max (ms) | live timeout |
|---|---|---|---|---|---|
| `bash -c true` | 348 | 741 | 208 | 2174 | — |
| `python3 -c pass` | 1112 | 2276 | 820 | 2464 | — |
| `python3` + import every guard | 1883 | 4237 | 1320 | 8851 | — |
| Edit\|Write, both entries, steady | 18052 | 23941 | 11682 | 26759 | 20 s + 5 s |
| Bash PreToolUse (`ls docs`) | 4594 | 9367 | 2754 | 9391 | 30 s |
| Bash PostToolUse, both entries (`ls docs`) | 13962 | 27940 | 8351 | 28451 | 5 s + 5 s |
| Bash PostToolUse, both entries (`git commit`) | 30885 | 38384 | 22620 | 42584 | 5 s + 5 s |
| ExitPlanMode PostToolUse (`mark`) | 4117 | 7394 | 2066 | 7710 | 5 s |
| plan gate alone, retire path | 35956 | 41303 | 27294 | 51151 | 20 s |

- A first run (`2026-10-06T23:37:27`, 707 MB free) gave `mark` a median of 5911 ms and a p90
  of 12068 ms.
- Its dispatcher rows were invalid: both wrappers locate their module through
  `$CLAUDE_PROJECT_DIR`, so with a temp project they printed `python3.exe: can't open file
  '…\steady\scripts\enforcement\adapters\claude_dispatcher.py'` and exited **2**. That is a
  fact in its own right: a hook whose script path is missing **blocks** (Python exits 2 on a
  missing file).

Read against the timeouts: the median `mark` (4.1 s) is near its 5 s limit, and its p90 is
over it. The retire path (36 s median) is always over its 20 s limit. After a `git commit`, the
PostToolUse pair (31 s) is far over 5 s.

### O4b — item 111 after the change (same harness, N=10, the new `hook.py` wiring)

Run `hook_timing.py after 10`, `2026-10-07T05:34:38`. Free RAM: **506 MB** at the start
(before: 524) and 828 MB at the end. Every case exited 0, except the retire case's intended
`PLAN RETIRED`.

| Case | before median | after median | before p90 | after p90 | after max (ms) |
|---|---|---|---|---|---|
| Edit\|Write PreToolUse, steady | 18052 | **2427** | 23941 | 4952 | 6586 |
| Bash PreToolUse (`ls docs`) | 4594 | **1361** | 9367 | 2608 | 2703 |
| Bash PostToolUse (`ls docs`) | 13962 | **1084** | 27940 | 3257 | 3699 |
| Bash PostToolUse (`git commit`) | 30885 | **1383** | 38384 | 3621 | 4767 |
| ExitPlanMode PostToolUse (`mark`) | 4117 | **1819** | 7394 | 3350 | 3530 |
| plan gate, retire path | 35956 | **3022** | 41303 | 7824 | 8414 |

The new Edit\|Write row is one process doing what took two hooks before (the plan gate plus
the seven guards). For scale: a bare `python3 -c pass` measured a 969 ms median in this run.

**Timeouts, from these numbers** (settings.json): Edit\|Write and Bash PreToolUse are 30 s,
the ExitPlanMode pair and the Bash PostToolUse reminder are 15 s, and the
prompt/context hooks are 10–15 s. Each is at least 3.5× the after-run's worst case (8.4 s,
retire).

The asymmetry decides the direction. A cancelled PreToolUse gate is an **open** gate, while
a generous timeout costs latency only in the pathological case. The old 5 s on the dispatcher
and on `mark` sat below their own medians under load.

### O5 — heredoc escapes corrupted files three times on this branch (item 142's class)

- Writing `test_agent_tool_grant_consistency.py` through a Bash heredoc turned `\\b` into two
  literal **backspace bytes** (`0x08`). A byte scan found them; they were repaired before any
  commit.
- Two more heredocs collapsed `\\n` / `\\|` (the timing harness, and the `tooling.md` table).
- The workaround on this branch: write scripts with the Write tool, never a heredoc. Item 142
  is not in this branch's scope, so no mechanism is built here. That gap was surfaced to the
  owner.

### O6 — live, after the switch (same session, settings.json hot-reloaded)

- Claude Code picked up the new `.claude/settings.json` mid-session, with no restart. After the
  user's "continue", an `Edit` returned
  `PreToolUse:Edit hook error: [python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" edit-write-dispatcher]: PAUSE (interrogative-witness): first Edit/Write since the last user prompt.`
  So the new command is the one running, and its witness half fires.
- From the switch (about 07:44Z) to that point: **22 Bash, 6 Edit and 1 Write** calls, with
  **zero** `hook_cancelled` attachments and zero non-blocking hook errors in transcript
  `08aa18b5…jsonl`. That includes the window in which Claude Code killed a background pytest for
  low memory. Before the switch, the dispatcher was cancelled on 31 of 40 Edit/Writes.
- The same message was also an item 143 instance: the witness paused the first `Edit` while
  the batched second `Edit` (to an independent file) ran. It was harmless, because neither
  read the other.
- The killed and timed-out old hooks left orphans behind. This session's two
  (`python3 -c "import sys,json; …"` from `wiki-freshness-reminder.sh` at 23:28, and
  `claude_dispatcher.py` at 23:54) were stopped by PID. Twenty-three more from earlier
  sessions (2026-09-18 → 10-06, about 0 MB each) are owner-item 128's class and were left alone.
  The Python-direct hooks have no inner `python3 -c` child to orphan.

### O7 — a test wrote fake `compacted` events into the live session's ledger

- Staging showed two rows appended to `docs/dev/ledger/08aa18b5-….jsonl`:
  `{"event": "compacted", … "trigger": "unknown", "ts": "2026-10-07T07:47:55Z"}` and the same
  at `12:14:43Z`. No compaction happened at either time.
- Their timestamps fall inside the two pytest runs that began with
  `test_governance_hooks_gate.py` (started `07:46:20Z` and `12:14:18Z`, per transcript
  tool-use times). `test_context_hooks_never_gate` calls `claude_context_hook.main` for
  `capture-before-compact` with `cwd` = this repo. `record_compaction` names its shard after
  `CLAUDE_CODE_SESSION_ID`, which pytest inherits from the live session. The pre-branch
  version of the test did the same.
- **Mechanism, fails closed:** an autouse `tests/conftest.py::_no_live_session_id` removes the
  variable for every test.
- **Verified:** the shard's sha256 was unchanged across a re-run of that test plus the in-process
  plan-gate kill tests (`6 passed`). The two fake rows were removed, leaving the real `consumed`
  row.

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

1. **One Python process per matcher, no shell wrapper (items 152, 111).** Every settings.json
   hook is `python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>`.
   - The plan gate (`scripts/enforcement/plan_gate.py`) runs first inside the Edit|Write
     dispatcher.
   - Guard modules import lazily.
   - The steady path forks nothing, and a retire costs at most three `git` calls.
   - This addresses the proved mechanism: hooks slower than their timeouts are cancelled, and
     a cancelled gate is open (O1, O3, O4).
2. **Fail-closed `mark` (O1's inferred kill points).** It drops the marker, then the stamp,
   then writes the new marker atomically. A plan written after the live approval blocks edits
   (O1's observed shape: a killed `mark` left edits running under the previous approval).
3. **`cleanup-plan-on-merge` removed (O2), by owner decision.** The only remaining PostToolUse
   Bash hook reads `tool_input.command`, never tool output.
4. **`plan-write-landed` (item 143).** ExitPlanMode is refused while the plan file's last
   attempted write has not landed.
5. **Timeouts set from the after-measurement** (O4b).

## Acceptance bar

- `tests/test_plan_approval_scoping.py::TestKilledHookRetirements` failed on the `.sh` hooks
  (`3 failed`, `5431b83`). On the port, the whole file passes: 37/37, `-p no:rerunfailures`,
  in two runs (`21 passed` and `16 passed`), with no retries.
- `tests/test_settings_hooks_python_direct.py` (the item 152 rule, with a mutation check) and
  `tests/test_governance_hooks_gate.py` pass.
- Targeted suites, all `-p no:rerunfailures`:
  - `test_enforcement_core` 153/153;
  - evidence, consumer-enumeration, tool-grant, coverage, C-12, verify-doc-template and
    witness tests: 170 total (1 failure on the first run, fixed: `wiki_reminder_hook` read
    `CLAUDE_PROJECT_DIR` directly);
  - doc gates 62/62;
  - `check_doc_links` OK.
- Before/after timings (O4, O4b): every case is faster by 2–22×, and every after-figure is well
  inside its timeout.
- Live (O6): zero `hook_cancelled` across 29 tool calls after the switch, against 31/40
  Edit/Writes cancelled before it.
- **Not yet met:** the full gate. CI is the gate, owner-directed while RAM is 0.5–0.8 GB:
  `python -m scripts.ci_wait <n>`, and exit 3 means stop.

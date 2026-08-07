# Diagnosis — plan-approval marker survives a PR-channel merge

> **Status:** root cause PROVEN (live-reproduced, isolated, twice). **Fix shape
> DECIDED** (2026-08-07 session): D3(b) as originally staged is disproven — see
> "D3(b) refuted" below — and the owner approved a pivot to a PreToolUse-based
> design instead. See `docs/dev/handoffs/` for this branch's own close-out for
> the built fix; this dossier documents the evidence, not the implementation.
> **Branch:** `fix/plan-approval-marker-pr-merge` (recreated 2026-08-07 from
> `main` at `ae7e0fa` — the original branch of this name merged as part of PR
> #105 and was pruned; this dossier file survived the merge on `main` and is
> reused rather than duplicated, per the branch-slug convention that strips the
> `fix/` prefix).

---

## Symptom

`~/.claude/plans/.approved-<project-key>` is supposed to be deleted the moment a
plan's own work merges, so the *next* task starts from a clean, blocked state
(`hooks/cleanup-plan-on-merge.sh:3-6`). In practice, once this repo's close-out
flow moved from a local `git merge --no-ff` to the PR channel (`gh pr merge` +
`git pull --ff-only`), the marker is never deleted by that flow. A fresh session
finds a pre-existing `.approved-*` file and can edit production code without
ever having called `ExitPlanMode` itself. Item 45
(`docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`) filed this
from two dated sessions (2026-08-04, 2026-08-05); this dossier re-verifies those
claims live rather than trusting the prior write-up, and adds an isolated,
reproducible demonstration.

---

## Observed

**D1 — re-verifying item 45's three inherited observations LIVE, at this branch's
own HEAD (`867cb04`), not copied from the prior file:**

1. `hooks/cleanup-plan-on-merge.sh` at THIS HEAD gates its deletion on three
   separate `grep -q` text-match conditions against the raw stdin JSON, each an
   independent early-`exit 0` if unmatched:
   - line 21: `if ! echo "$INPUT" | grep -q 'git merge'; then` → exit 0
   - line 24: `if ! echo "$INPUT" | grep -q -- '--no-ff'; then` → exit 0
   - line 27: `if ! echo "$INPUT" | grep -q 'Merge made by'; then` → exit 0
   Only if **all three** match does it fall through to the structural check at
   lines 34-41 (`PARENT_COUNT=$(git -C "$PROJECT_DIR" log -1 --pretty=%P ... | wc -w)`;
   `if [ "${PARENT_COUNT:-0}" -lt 2 ]; then exit 0; fi`) — confirmed by reading the
   file at this HEAD, not from memory of the prior branch's read.

2. `AGENTS.md:232` (this HEAD) is the close-out step 4 flow text: `git push -u
   origin <branch>` → `gh pr create` → `python -m scripts.ci_wait <n>` →
   `` gh pr merge <n> --merge `` (never `--squash`/`--rebase`) → `git checkout main
   && git pull --ff-only`. Read character-by-character against the three trigger
   phrases: it contains **none of them** — `gh pr merge` is not the substring
   `git merge` (different second word); `--ff-only` is not `--no-ff`; nothing in
   the quoted text is `Merge made by`.

3. `~/.claude/plans/.approved-C--Dev-sartor`, read READ-ONLY (never modified):
   content is `C:/Users/iam/.claude/plans/harmonic-stirring-wreath.md`. Precise
   mtimes via `stat -c '%Y'`: marker = `1785985618` (2026-08-05 20:06:58 **-0700**,
   i.e. `2026-08-06T03:06:58Z` — the original write-up of this dossier stamped this
   `Z` directly onto the local-offset clock time instead of converting; corrected
   2026-08-07, see "D3(b) refuted" below for why the correction matters), plan
   file = `1785985607` (2026-08-05 20:06:47 -0700) — the marker is 11 seconds
   *newer* than the plan file, so `hooks/check-plan-approved.sh:51`'s freshness
   test (`[ "$APPROVED_PLAN" -nt "$MARKER" ]`) is false and the gate is **open**.

   **Why this is the chain's legitimately-earned marker, not itself a live
   instance of the defect:** this session's own `git log --oneline --graph -8`
   shows `HEAD` (`867cb04`) has exactly **one parent** (`git log -1 --pretty=%P |
   wc -w` → `1`) — it is not a merge commit. Nothing has been pushed, PR'd, or
   merged anywhere in this stacked chain (every predecessor handoff states this
   explicitly, and this session verified no `origin` push occurred: the chain's
   own branches stack tip-to-tip, locally). Since the marker's write-side
   (`hooks/mark-plan-approved.sh`) only fires on `ExitPlanMode`, and its
   wipe-side only fires (if it fires at all) on a merge event, and **no merge
   event of any kind has happened since this marker was stamped**, its
   continued existence is simply "nothing has tried to wipe it yet" — not "the
   wipe fired and failed." The three *live instances of the actual defect* are
   the two dated sessions item 45's own file already recorded (2026-08-04,
   2026-08-05, each finding a stale marker from a PRIOR chain's PR merge) plus
   the isolated reproduction in D2 below.

**D2 — isolated reproduction**, throwaway `HOME` + throwaway git repo, `HOME`
and `CLAUDE_PROJECT_DIR` overridden only for the hook subprocess's own
environment (never the real session's). Script:
`C:\Users\iam\AppData\Local\Temp\claude\C--Dev-sartor\c8caf603-88cf-46b6-b2aa-77d41a898d3c\scratchpad\repro_marker_survives.py`
(not committed — throwaway, per the established convention in
`tests/test_plan_approval_scoping.py`'s own docstring). Both scenarios advance
the throwaway repo's `HEAD` to a **genuine ≥2-parent merge commit** first (via a
real, unmuted `git merge --no-ff`, so the structural precondition
`cleanup-plan-on-merge.sh`'s own check demands is actually, verifiably true in
both cases) — the only variable between the two scenarios is the **command
text + tool_response.output** fed to the hook as byte-correct
`json.dumps(...)` PostToolUse stdin, exactly mirroring the shape the harness
itself sends.

Full run output (`python repro_marker_survives.py`, exit 0):

```
=== Scenario (i): PR-channel merge shape ===
  [1] approve plan (simulates ExitPlanMode)
    stdin -> {"tool_input": {"file_path": "...\\home\\.claude\\plans\\plan.md"}}
    exit=0 stdout='' stderr=''
    stdin -> {}
    exit=0 stdout='' stderr=''
  marker/plan BEFORE: (True, True)
  [2] advance HEAD to a REAL merge commit (structural outcome of a genuine PR merge)
  HEAD parent count = 2 (>=2 means HEAD genuinely IS a merge commit)
  [3] feed the hook the PR-channel COMMAND TEXT (gh pr merge, then pull --ff-only)
      (for reference, git's own real merge output was: "Merge made by the 'ort' strategy." -- NOT sent to the hook, since gh pr merge + pull --ff-only never produce it)
    stdin -> {"tool_input": {"command": "gh pr merge 105 --merge"}, "tool_response": {"output": "\u2713 Merged pull request #105 (fix/example)\n"}}
    exit=0 stdout='' stderr=''
  marker/plan AFTER `gh pr merge` step: (True, True)
    stdin -> {"tool_input": {"command": "git checkout main && git pull --ff-only"}, "tool_response": {"output": "Updating abc1234..def5678\nFast-forward\n"}}
    exit=0 stdout='' stderr=''
  marker/plan AFTER `pull --ff-only` step: (True, True)
  RESULT: marker survives = True (expected True -- this is the defect)

=== Scenario (ii): local `git merge --no-ff` shape ===
  [1] approve plan (simulates ExitPlanMode)
    stdin -> {"tool_input": {"file_path": "...\\home\\.claude\\plans\\plan.md"}}
    exit=0 stdout='' stderr=''
    stdin -> {}
    exit=0 stdout='' stderr=''
  marker/plan BEFORE: (True, True)
  [2] perform the REAL local merge --no-ff (this IS the command the hook fires after)
  HEAD parent count = 2
  real git output captured: "Merge made by the 'ort' strategy.\n"
  [3] feed the hook the ACTUAL command text + ACTUAL output
    stdin -> {"tool_input": {"command": "git merge --no-ff -m 'merge feature' feature"}, "tool_response": {"output": "Merge made by the 'ort' strategy.\n"}}
    exit=0 stdout='' stderr=''
  marker/plan AFTER: (False, False)
  RESULT: marker wiped = True (expected True)
```

**What this adds beyond item 45's own file:** item 45's observations were about
*live, real* stale markers found at session start — evidence that the defect
happens, not a controlled isolation of *why*. This reproduction holds the
structural precondition (a genuine merge commit at `HEAD`) **constant and true
in both branches** of the experiment, varying only the command-text shape — so
it proves the mechanism is exactly "text-shape of the Bash command", not
"whether a merge structurally occurred." That distinction is the load-bearing
fact for D3 below: the PR-channel merge in scenario (i) is **not a
near-miss or an edge case at the margin of detection** — `HEAD` is exactly as
structurally merge-y as scenario (ii)'s. The hook's pre-filter simply never
reaches the structural check, because `gh pr merge` does not contain the
substring `git merge`, and neither `gh pr merge`'s nor `git pull --ff-only`'s
real output contains `--no-ff` or `Merge made by`.

---

## Falsified

Nothing chased and killed this session — the mechanism was confirmed on the
first isolated attempt (after one self-caught defect in the reproduction
script itself, not the hook: the first run of scenario (ii) used `git merge
--no-ff -q` for internal setup, which suppresses git's own `Merge made by...`
line, producing an empty-string `real_merge_output` and a false failure to wipe
that was about the *test's own instrumentation*, not the hook. Fixed by
removing `-q` so the script captures git's genuine stdout rather than
asserting a hand-typed literal — this is itself the C-7 "observe, don't
assume" discipline applied to writing the instrument, not just to the hook
under test).

**Two more, found and fixed while BUILDING the D3(c) implementation** (not the
design itself — the archive+receipt mechanism `retire-approved-plan.sh`),
each root-caused by direct reproduction before being fixed, per the same
discipline:

1. **Cross-runtime path translation.** `TestArchiveAndReceipt::test_archive_
   preserves_the_plan_and_writes_a_receipt` failed reproducibly under
   `pytest -n 8` (3/3) but passed in isolation — not flakiness, a real defect
   masked by a machine-specific coincidence. Reproduced directly:
   `env["HOME"] = 'C:\Users\iam\AppData\Local\Temp\...'` fed to a bash
   subprocess comes back as `bash`'s own `$HOME` already POSIX-translated
   (`/tmp/...` or `/c/...`, confirmed via a standalone repro, not inferred).
   A **native** `python3.exe` (not MSYS-compiled) does not understand that
   syntax: `Path('/c/Users/iam/x').resolve()` → `C:\c\Users\iam\x`, which does
   not exist (`Path.is_dir()` → `False`, confirmed directly). It "worked" in
   one earlier serial run purely because `C:\tmp` happens to be a real,
   coincidental junction to this specific machine's temp dir — not a
   portable behavior. Fixed by routing every `$HOME`-derived path through
   `cygpath -m` (MSYS-shipped, correct on both bash and native Windows
   programs) before handing it to `python3` as an argv string
   (`hooks/lib/retire-approved-plan.sh`'s `_native_path()`).
2. **Windows `MAX_PATH` (260 chars).** Fixing (1) did not fix the test —
   same failure, `manifest.json` missing while `plan.md` (moved via `mv`)
   was present. Instrumented directly (temporary stderr capture + an
   explicit `except OSError as e: print(...)`) rather than guessed at:
   `FileNotFoundError(2, 'No such file or directory')` on the `write_text`
   call, with `Path(archive_dir).is_dir()` confirmed `True` immediately
   before it. Measured the actual path length: 262 characters — `archive_id`
   embedded the ENTIRE sanitized `project_key` (the full project directory
   path, every non-alphanumeric byte → `-`), so a deeply-nested project path
   (realistic for OneDrive-synced or deeply-nested real user directories,
   not just this session's pytest tmp path) pushes the archive directory
   name itself past the point where `manifest.json` (13 chars) tips the full
   path over 260, while `plan.md` (7 chars) stays just under — exactly
   matching the observed pattern. Fixed by hashing `project_key` to 12 hex
   chars (`sha256sum`, matching this project's own fingerprint convention in
   `docs/dev/prov/SPEC.md`) for the directory name instead of embedding it
   whole; the full `project_dir` is still recorded inside `manifest.json`'s
   own content, where length doesn't matter.

Both are genuine, always-latent defects (not test-environment artifacts) that
would have shipped invisibly — the archive+receipt mechanism would have
silently dropped its own manifest on any sufficiently long real project path,
exactly the "silently thinner provenance than intended" failure the owner's
archive-not-delete directive exists to prevent. Neither was in the original
D3(c) design write-up; both surfaced only once the mechanism was actually
built and stress-tested, which is itself the argument for C-7's own rule
against trusting a design "sound on paper."

---

## Inferred

Everything under "Observed" above is either a direct read of committed source
at this HEAD, a direct read of the real (untouched) marker file, or a
controlled subprocess run with captured stdout — nothing here is inference.
The **fix shape** is where inference starts, and it is deliberately kept out of
`## Observed`: see "The fix" below for the two characterized candidates and why
neither is promoted to code on this branch.

---

## Falsification

**The defect's existence is already falsifiable and already run** (D2 above):
scenario (i) is exactly the experiment, and it fails on `HEAD` (marker
survives when the interim rule says it should not) — root cause PROVEN, not a
guess.

**What remains unresolved is a *design choice between two fix shapes*, not a
further fact about the defect.** That is not resolved by running more of the
same experiment harder; see "The fix".

---

## The fix

**Not implemented on this branch.** Both candidate shapes named in item 45's
own file were characterized in depth (D3, below) rather than chosen between
by default. The characterization surfaces a real asymmetry — one shape is
demonstrably insufficient, the other is buildable but touches
approval/security-adjacent state for the first time in a way this dossier
judges needs an explicit owner call before being written, not because the
analysis is incomplete, but because of what a *wrong* implementation here would
cost (see "Known limit" at the end of this section).

### D3(a) — `PostToolUse` matcher on the `gh pr merge` command shape

**What it catches:** exactly the case `cleanup-plan-on-merge.sh` already
handles for local merges, generalized to one more literal command shape: an
agent, in the SAME Bash session the harness observes, typing `gh pr merge <n>
--merge` (per `AGENTS.md:232`'s own documented flow). A matcher keyed on that
literal command text (mirroring the existing three-`grep` pattern, or matching
on the PostToolUse `tool_response.output`'s `` Merged pull request `` text
`gh pr merge` actually prints) would close exactly the gap D2's scenario (i)
demonstrates, **for that one channel**.

**What it structurally cannot catch — enumerated, not assumed:**

1. **Dependabot auto-merge.** This repository has PR auto-merge **enabled**
   (`project-ci-infrastructure-sprint-sequence` memory: "auto-merge ON
   08-04"). A dependabot PR that satisfies its required checks merges
   **server-side**, with **no local command run at all** — there is nothing
   for a Bash-matched `PostToolUse` hook to see, ever, regardless of how the
   matcher is written. This is not a hypothetical edge case in this repo; it
   is the documented, currently-active state of a real merge channel.
2. **GitHub UI merges.** A human (or the owner) clicking "Merge pull request"
   in the browser produces the same server-side merge with no local command.
3. **Another terminal / another agent session on the same machine.** The
   Bash-matcher hook only observes commands the *current* Claude Code session
   issues. A merge performed in a sibling terminal, a different Claude Code
   session, or a CI job changes the shared repo's `HEAD`/`main` with zero
   signal reaching this session's own PostToolUse hook.
4. **`gh` aliases or wrapper scripts.** `gh alias set mymerge 'pr merge
   --merge'` then `gh mymerge <n>` — or any shell function/wrapper that
   ultimately shells out to the same subcommand under different surface
   text — is invisible to a matcher keyed on literal command text, the exact
   class of fragility the existing three-`grep` mechanism already has for
   the local-merge case (and the class of failure `verify_binary_on_path`'s
   own `_split_top_level`/MSYS-path work on the immediately-prior branch
   fixed one instance of, in a different guard).

Given (1)-(2) are not edge cases but the **actively enabled, currently-used**
merge path for this repo's own dependency-bump PRs, a fix in this shape closes
one narrow sub-case (the agent typing `gh pr merge` itself) while leaving the
majority of real merge events in this repo — anything server-side — exactly as
uncovered as they are today. **This shape does not clear the "clean" bar.**

### D3(b) — `SessionStart` reconciliation against HEAD

Item 45's own file and this branch's brief both describe this only in
outline ("check whether the currently-approved plan's marker is stale against
what actually landed on `main`"). Two designs were considered, and they are
**not equivalent**:

**Naive design — "has `main` moved since approval?"** Record `main`'s tip SHA
at approval time; at `SessionStart`, compare to `main`'s current tip; any
difference ⇒ treat the marker as stale and wipe it.

- **This fails the compaction-mid-session test the brief requires, and fails
  it in the dangerous direction.** `restore-evidence.sh` wires
  `startup|resume|compact` (`.claude/settings.json`'s `SessionStart` matcher,
  confirmed by reading it directly this session) — a mid-session compaction
  fires `SessionStart` while an agent's own plan is still legitimately
  in-progress, unmerged, on its own feature branch. If, in that same window,
  an **unrelated** dependabot PR auto-merges to `main` (a real, expected,
  concurrent event in this repo, per (1) above), `main`'s tip changes for a
  reason that has nothing to do with the approved plan's own work. A
  reconciler keyed on "did `main` move at all" would disarm a **legitimately
  armed marker mid-session**, forcing the agent to re-earn approval it never
  should have lost — the exact failure mode the brief names as the critical
  risk of this shape, and it is not a remote possibility in this repo, it is
  the steady state auto-merge already produces.

**Narrower design — "has *this specific approved branch* been merged?"**
Record, at approval time (`mark-plan-approved.sh`), the branch name and `HEAD`
SHA that were checked out in `CLAUDE_PROJECT_DIR` — in a **new, separate**
stamp file (e.g. `.approved-branch-<project-key>`), never by changing the
existing `.approved-<key>`/`.current-<key>` files' content or format (those
are read verbatim as "a path to the plan file" by `check-plan-approved.sh` and
`cleanup-plan-on-merge.sh` today; extending their format risks a silent
parsing break in either). At `SessionStart`, if the marker exists: check
whether the recorded branch ref still exists (`git show-ref --verify --quiet
refs/heads/<branch>`) and, if it does, whether the recorded SHA is now an
ancestor of `main` (`git merge-base --is-ancestor <sha> main`) — the second
check matters because this repo's branch-protection disables squash **and**
rebase merges (`AGENTS.md:232`), so a real PR merge preserves the original
commits verbatim and reachable, making ancestor-of-`main` a sound test. Either
condition true ⇒ *this specific approved work* merged (by any channel — local,
`gh pr merge`, UI, auto-merge, another terminal — channel-independent by
construction) ⇒ wipe. Neither true ⇒ no-op, **including** when `main` moved
for an unrelated reason, because an unrelated commit landing on `main` cannot
make an unrelated branch's SHA an ancestor of it.

Hand-traced against the required compaction scenario: approve on `fix/foo`
(record branch=`fix/foo`, sha=X) → continue committing on `fix/foo` (still
checked out, not merged, not deleted) → an unrelated PR auto-merges to `main`
→ compaction fires `SessionStart` → reconciler checks: does `fix/foo` still
exist? Yes (it is the branch currently checked out — a session cannot delete
the branch it is on). Is `X` an ancestor of `main`? No (unrelated history).
Result: no-op, marker stays armed. This passes the exact scenario the brief
requires as a mandatory test — **but it was hand-traced, not run**; see "Known
limit" below for why that distinction matters here specifically.

**This narrower design's own remaining limits, named rather than assumed
away:**

- **Within-session staleness it cannot see.** It only fires at `SessionStart`
  boundaries (`startup|resume|compact`). A merge of the approved branch that
  happens *mid-session*, with no compaction or resume before the session's
  next edit, is not reconciled until the *next* boundary event — unlike
  `cleanup-plan-on-merge.sh`'s existing `PostToolUse` hook, which (for the one
  command shape it does catch) reacts instantly. This shape is a **backstop**,
  not a replacement for instant local-merge detection.
- **F-gov-02/03 interaction.** The existing marker files are keyed by
  `CLAUDE_PROJECT_DIR` only, not by branch — this repo's own convention is one
  clone, one branch at a time (`feedback_branch_discipline`: "one branch/item,
  one session/branch"; concurrent work uses separate worktrees per
  `feedback-concurrent-agents-worktree`), so a second, genuinely concurrent
  session sharing the same `CLAUDE_PROJECT_DIR` on a *different* branch is
  already an out-of-contract scenario this dossier does not newly introduce —
  but it is a real, un-tested interaction this design would inherit rather
  than resolve.
- **A stamp-file write is still an edit to an approval-adjacent mechanism, for
  the first time, of this shape.** No prior branch in this project has built a
  hook that can *autonomously delete* an approval marker based on a git
  ancestry computation rather than a direct signal (an actual merge event
  observed in the same tool call). A subtle bug in the ancestor/branch-existence
  logic fails in one of two directions: too aggressive (an annoying but safe
  forced re-approval) or too lax (a marker that should have been wiped stays
  armed — no worse than today's status quo). Neither direction is catastrophic
  **by itself**, but this is exactly the kind of decision
  `feedback_branch_discipline` flags as needing sign-off before being built,
  not only before being merged — because the mechanism is new, the format
  extension touches files three other hook scripts and one committed test
  suite already parse, and the design was reasoned about on paper this session
  rather than iterated against a real owner review.

### D3(b) refuted (2026-08-07 session, before any code was written)

The narrower (b) design's own hand-trace (above) opens: *"approve on `fix/foo`
(record branch=`fix/foo`, sha=X)"*. **That premise is false in this repo, and
this dossier's own live marker proves it — the "Known limit" paragraph below
predicted exactly this outcome.**

`ExitPlanMode` fires while HEAD is still on `main`. `AGENTS.md:199`: "Create a
feature branch **when moving from plan to execute**" — i.e. *after* approval,
not before. Verified directly against this dossier's own live evidence, not a
fresh reproduction:

- The marker `.approved-C--Dev-sartor` was written at `2026-08-05 20:06:58
  -0700` (corrected timestamp above) — that write **is** `ExitPlanMode` firing.
- `git reflog --date=iso` for that window: `55f7c1e HEAD@{2026-08-05 20:00:07
  -0700}: pull --ff-only: Fast-forward` (onto `main`), then `55f7c1e
  HEAD@{2026-08-05 20:10:40 -0700}: checkout: moving from main to
  chore/dependabot-groups` — the feature branch was created **3m42s after**
  the marker was stamped.
- So at approval time HEAD was on `main` at `55f7c1e`, and
  `git merge-base --is-ancestor 55f7c1e main` → **exit 0, permanently** (it
  *is* `main`'s own history; `main` only moves forward).

Consequence for D3(b) exactly as staged: the stamp would record `branch=main,
sha=<main's own tip>`. At `SessionStart`, clause 1 (`show-ref
refs/heads/main`) always succeeds trivially, and clause 2
(`is-ancestor(sha, main)`) is true from the instant it is written. The
reconciler fires at the **first `startup|resume|compact` after every single
approval**, archiving a legitimately-armed marker mid-work — reproducing, via
a different mechanism, the exact "naive design" failure mode this dossier
believed the narrower form had engineered around (see "Naive design" above).

Two further, independently disqualifying findings for the `SessionStart`
placement specifically (not the ancestry idea itself, which survives the
pivot below):

- `tests/test_governance_hooks_gate.py::test_context_hooks_never_gate` invokes
  `claude_context_hook.main()` against `{"cwd": str(REPO_ROOT)}` — the real
  repository, with no `HOME` override — so a reconciler added to that module
  would read, and (per the owner's archive-not-delete directive) mutate, the
  developer's live `~/.claude/plans` marker on every ordinary local `pytest`
  run, while staying green in CI forever (no `~/.claude/plans` exists on a
  runner). `tests/test_c12_disclosure_gate.py` already documents this exact
  class of trap having bitten once for the ledger-shard fallback.
- `test_context_hooks_are_wired_on_their_lifecycle_events` pins `SessionStart`
  to wire exactly `{"restore-evidence"}`; a second SessionStart hook is
  structurally forced into the `CONTEXT` category (the blocker/witness sets
  are pinned to their own events), i.e. directly into the test above.

### Decision (superseded by the pivot below — kept for the record)

Neither shape clears "clean, hook-testable in isolation, and does not weaken
any existing behavior" on its own: (a) is demonstrably insufficient (D2 proves
it misses the dominant real channel in this repo); the naive form of (b) is
unsafe (fails the mandated compaction test); the narrower form of (b) is
sound **on paper** but is a first-of-its-kind, approval-adjacent mechanism this
dossier judges should get an explicit owner decision before being written —
not because the design is unfinished, but because of the asymmetry between what
it costs to wait one more owner round-trip and what it would cost to ship a
subtly wrong version of a mechanism whose whole job is deciding when edits are
allowed. ~~**Recommendation for the owner, staged, not built:** the narrower
branch-existence design above, as an **additive-only** stamp file + a new
`SessionStart` hook alongside `restore-evidence.sh`, with the two mandatory
regression tests (same-branch-mid-compaction stays armed; unrelated-main-move
mid-compaction stays armed) authored *before* the wipe path is enabled.~~
**Superseded 2026-08-07 — see "D3(b) refuted" above and "The pivot" below.**

**Known limit (C-0, stated not papered over) — this is the one that fired:**
this dossier's own characterization of the narrower (b) design was reasoned
and hand-traced, not built and run. "Hand-traced against a scenario" is
weaker evidence than a passing isolated test, and this dossier did not claim
otherwise — and the hand-trace's own premise turned out to be false, which is
exactly the failure mode a stated-but-unheeded limit is supposed to make
unsurprising when it lands.

### The pivot — D3(c): reconcile inside the existing PreToolUse blocker

Same ancestry idea as D3(b)'s narrower form, same archive-not-delete
directive, different placement: `hooks/check-plan-approved.sh` (already
PreToolUse on every `Edit`/`Write`) does the reconciliation itself, and the
stamp is written **late** — on the first production edit after approval,
which is the first moment `require-feature-branch` guarantees HEAD is a real
feature branch, never `main`. Two additions beyond D3(b)'s own ancestry
check: a `base` baseline (the tip of `main` at stamp time), because a
freshly-created branch with zero commits has `tip == main tip` and bare
ancestry would false-fire the instant `main` moves for any unrelated reason;
and a mtime pre-filter so the added git calls cost ~0 extra subprocesses in
the steady state. No new hook file, no `.claude/settings.json` change, no
`test_governance_hooks_gate.py` edit — the constraint that eliminated D3(b)
is exactly what this placement avoids paying. Full design, file list, and
test list: this branch's own plan / handoff, not duplicated here.

---

## Acceptance bar

**Amended 2026-08-07 for the D3(c) pivot.** Under D3(c) the marker does not
disappear at `gh pr merge` time — it is retired at the **next edit attempt**,
by design (that is what closes the within-session hole D3(b) could not). So
D2's reproduction gains a step [4]: feed `check-plan-approved.sh` a
production-file edit payload after the merge and assert `exit 2` **and** the
marker archived. This is a *stronger* bar than the original — it asserts the
edit is actually blocked, not merely that a file disappeared. "CI is green"
is not the bar; "the exact reproduction that proved the defect now proves the
fix" still is.

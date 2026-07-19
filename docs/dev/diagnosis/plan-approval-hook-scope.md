# Diagnosis — the plan-approval hook trio shares one global, cross-project state

> **Status:** root cause PROVEN — reproduced live against the unmodified scripts on this branch,
> twice (the designed reproduction, and then a second, self-inflicted live incident).
> **Branch:** `fix/plan-approval-hook-scope`

---

## Symptom

`check-plan-approved.sh` false-positive blocks `Edit`/`Write` with "PLAN NOT APPROVED: '<slug>.md'
is newer than approval marker" in a session that never touched an unrelated plan file — reported
live in `[[reference-plan-approval-hook-global-scope]]` memory (2026-07-16, `fix/ux-scroll-position-flake`)
and tracked as `RELEASE_CHECKLIST.md` Carry-forward ledger item 14. Separately,
`cleanup-plan-on-merge.sh` has been observed to wipe an unrelated session's approved-plan state
out from under it (`[[project-plan-approved-marker]]` memory, 2026-06-13 incident).

---

## Observed

Reproduced live in this session against the **unmodified** hook scripts (verified via `git status`
— no working-tree changes when this was run), using a temp `HOME` and two distinct
`CLAUDE_PROJECT_DIR` values to stand in for two concurrent, unrelated Claude Code sessions:

**1. Project A approves its own plan and successfully edits its own repo:**
```
$ HOME="$TMPHOME" CLAUDE_PROJECT_DIR="/c/Dev/fake-project-a" bash .claude-plugin/hooks/mark-plan-approved.sh
$ echo '{"tool_input": {"file_path": "/c/Dev/fake-project-a/some_file.py"}}' \
    | HOME="$TMPHOME" CLAUDE_PROJECT_DIR="/c/Dev/fake-project-a" bash .claude-plugin/hooks/check-plan-approved.sh
exit code: 0
```
`ls -la "$TMPHOME/.claude/plans/"` at this point: `.approved` + `plan-a.md`, both under the one
shared, global directory — nothing project-scoped in either name.

**2. An unrelated, concurrent "Project B" writes its own plan file into the SAME shared directory
(never approves it — just an ordinary `EnterPlanMode` write):**
```
$ echo "# plan B, unrelated project, not yet approved" > "$TMPHOME/.claude/plans/plan-b.md"
```

**3. Project A retries the EXACT SAME edit as step 1 — nothing in A changed, A's own plan was
approved seconds earlier — and it is now blocked:**
```
$ echo '{"tool_input": {"file_path": "/c/Dev/fake-project-a/some_file.py"}}' \
    | HOME="$TMPHOME" CLAUDE_PROJECT_DIR="/c/Dev/fake-project-a" bash .claude-plugin/hooks/check-plan-approved.sh
PLAN NOT APPROVED: 'plan-b.md' is newer than approval marker.
Call ExitPlanMode and get user approval before editing files.
exit code: 2
```
This is `check-plan-approved.sh`'s `ls -t "$PLANS_DIR"/*.md | head -1` comparing against the
**newest `.md` in the whole shared directory**, regardless of which project wrote it — Project
B's file alone caused Project A's already-approved edit to be blocked.

**4. Separately, an unrelated "Project B" merge close-out wipes Project A's state.** Starting from
the state after step 2 (`.approved`, `plan-a.md`, `plan-b.md` all present), simulating B's own
`--no-ff` merge success:
```
$ echo '{"tool_input": {"command": "git merge feature/b --no-ff -m x"}, "tool_response": {"output": "Merge made by the recursive strategy.\n"}}' \
    | HOME="$TMPHOME" CLAUDE_PROJECT_DIR="/c/Dev/fake-project-b" bash .claude-plugin/hooks/cleanup-plan-on-merge.sh
$ ls -la "$TMPHOME/.claude/plans/"
total 0
```
Every file — `.approved`, `plan-a.md` (Project A's, still mid-session), and `plan-b.md` — is gone.
`cleanup-plan-on-merge.sh` globs `"$PLANS_DIR"/*.md` and the one global `.approved` with no
awareness of which project is merging.

**5. Second, unplanned, self-inflicted incident — proves a related but distinct defect.** While
running step 4's isolated repro (deliberately using `HOME="$TMPHOME"` to sandbox the inner
invocation), the OUTER Bash tool call I actually ran was itself subject to the REAL
`cleanup-plan-on-merge.sh` PostToolUse hook wired in `.claude/settings.json` — invoked for real,
against my REAL `$HOME` and REAL `$CLAUDE_PROJECT_DIR` (this repo), because that hook fires on
*every* Bash tool call, not just ones that intend to test it. My command's text happened to
contain the literal substrings `git merge`, `--no-ff`, and `Merge made by` (embedded as test-JSON
data for the inner simulation), which is all three of `cleanup-plan-on-merge.sh`'s `grep -q`
checks. Immediately afterward:
```
$ ls -la "$HOME/.claude/plans/"
total 12
(empty except . and ..)
$ test -f "$HOME/.claude/plans/toasty-bouncing-cherny.md" && echo EXISTS || echo MISSING
MISSING
```
My real, just-approved plan file and marker (from this same branch's own plan-approval,
minutes earlier) were deleted for real — no actual merge had happened in this repo at that
moment. Confirmed via `git log -1 --pretty=%P` showing a single-parent (non-merge) HEAD at the
time. This demonstrates: **the merge-detection is a bare substring `grep` over the whole raw
stdin JSON, with zero structural verification that a merge actually landed** — any Bash command
whose text merely *mentions* the three phrases (a comment, echoed test data, quoted output) trips
real deletion, independent of the per-project scoping bug above.

Root mechanism for both defects (confirmed by direct reading of the current script text,
consistent with both reproductions — not a guess):
- `PLANS_DIR="$HOME/.claude/plans"` and `MARKER="$PLANS_DIR/.approved"` in all three scripts are
  process-global constants with no reference to `CLAUDE_PROJECT_DIR` or any other project/session
  identifier (confirmed: `grep -n CLAUDE_PROJECT_DIR` over the three files returns nothing, prior
  to this branch's fix).
- `cleanup-plan-on-merge.sh`'s three `grep -q` calls operate on the entire raw stdin blob with no
  check against real git state (confirmed: no `git` invocation anywhere in the script prior to
  this branch's fix).

---

## Falsified

_(Nothing yet — this is the first investigation of this defect; no discarded fix attempts exist.)_

---

## Inferred

Two DISTINCT root causes were named across prior sessions' memory
(`[[reference-plan-approval-hook-global-scope]]`); this dossier proves and fixes the first, plus
the newly-discovered second one from `## Observed` step 5:

1. **PROVEN above (steps 1–4):** cross-project global-scope collisions. This is what
   `RELEASE_ARC.md`'s "scope the marker per-project" ledger item targets, and what this branch
   fixes via `CLAUDE_PROJECT_DIR`-keyed marker/pointer files.
2. **PROVEN above (step 5):** unstructured substring-triggering of the merge-cleanup's deletion.
   Fixed by gating the actual deletion on a structural check (HEAD is genuinely a merge commit)
   rather than trusting the text-only pre-filter alone.
3. **NOT investigated here, NOT claimed fixed:** a separately-reported failure mode where
   approval "does not persist across separate substantive Edit/Write actions even within a
   single, uninterrupted session," confirmed by the user NOT to be caused by a concurrent
   session on that occasion. Root cause unknown — per that memory's own explicit instruction, do
   not invent an explanation. This dossier does not touch it; it may or may not be a side effect
   of the same global-scope design, but that is unverified and out of scope for this fix. (It is
   possible — though unconfirmed — that some occurrences of #3 were actually undiagnosed
   instances of #2, i.e. some earlier Bash command's text coincidentally matched the merge-grep
   and silently wiped the marker; this dossier does not assert that, only flags it as a
   plausible, unproven connection for a future investigation to check.)

---

## Falsification

**The experiment that settles it (already run above, not merely proposed):** steps 1–3 and step 5
in `## Observed` are exactly this experiment, run against HEAD (the unmodified scripts).

- **Result on HEAD: fails both ways.** Step 3 exits 2 (false block) even though project A did
  everything right. Step 5 deletes real, live approval state with no real merge having happened.
  Both hypotheses confirmed — proceed to the fix.
- (The counterfactual — either step passing cleanly on HEAD — would have meant that particular
  bug does not reproduce this way, requiring further instrumentation before touching code. Not
  the case for either.)

Both reproductions are being turned into committed regression tests
(`tests/test_plan_approval_scoping.py`) so they are asserted going forward, not just
hand-verified once.

---

## The fix

Scope all three scripts' state (marker + "current plan file" pointer) by a key derived from
`${CLAUDE_PROJECT_DIR}` (confirmed available as a real environment variable inside hook script
bodies — already used this way by 9 of the other 12 hooks in `.claude-plugin/hooks/`):

- `check-plan-approved.sh` checks only `.approved-$PROJECT_KEY` and the ONE specific plan file
  path it records — never scans the shared directory for "the newest `.md`."
- `mark-plan-approved.sh` records exactly which plan file this project's own session wrote, via
  a new `.current-$PROJECT_KEY` pointer set by `check-plan-approved.sh`'s existing plans-dir
  exemption branch (a hook firing that already happens on every plan-file write).
- `cleanup-plan-on-merge.sh` deletes only this project's own recorded plan file and its two
  pointer files, never a blanket `rm` across the shared directory — **and** keeps its 3 existing
  `grep` checks only as a cheap pre-filter, gating the actual deletion on a structural check
  (`git -C "$CLAUDE_PROJECT_DIR" log -1 --pretty=%P` has ≥2 parents, i.e. HEAD really is a merge
  commit right now).

Full design in the approved plan file for this branch (`toasty-bouncing-cherny.md`).

---

## Acceptance bar

- The exact reproductions in `## Observed` steps 1–5, re-run against the fixed scripts, must
  show: step 3's retry stays `exit 0` (Project A's approval is untouched by Project B's unrelated
  plan file); step 4's merge close-out for Project B leaves Project A's marker and plan file
  intact; and step 5's text-only false trigger (no real merge commit at HEAD) no longer deletes
  anything.
- `tests/test_plan_approval_scoping.py` (new) encodes all of the above as permanent, automated
  regression tests — not just one-time manual checks.
- `tests/test_governance_hooks_gate.py` continues to pass unmodified (its assertions are
  filename/text/wiring-based, not marker-path-based — confirmed during planning).
- `python -m scripts.gate` green in full.

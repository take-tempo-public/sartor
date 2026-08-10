# Diagnosis — a brand-new branch's first edit inherits a stale, already-consumed plan approval

> **Status:** root cause PROVEN (isolated, reproducible on demand, twice — once as a
> byproduct of a larger stacked-chain repro, once in a minimal isolated form built to
> pin it down exactly).
> **Branch:** `fix/plan-approval-branch-switch-gap`

---

## Symptom

Item 45's own dossier (`docs/dev/diagnosis/plan-approval-marker-pr-merge.md`) reported
this original symptom: *"A fresh session finds a pre-existing `.approved-*` file and can
edit production code without ever having called `ExitPlanMode` itself."* The D3(c) fix
that closed item 45 (merged to `main` as PR #111, `efa5994`) added branch-merge
reconciliation to `hooks/check-plan-approved.sh` specifically to close this. Its own
regression test, `test_pr_channel_merge_blocks_the_next_edit`, asserts the fix by
checking back out to the SAME already-merged branch before feeding the next edit.

Discovered while scoping an unrelated multi-branch chain design (2026-08-07): the
**far more common transition — finish task A, merge it, branch to task B off the now-
updated `main`, edit** — is not the scenario that test exercises, and does not go
through the same code path. It should be blocked (a genuinely new task with no approval
of its own) but is not.

---

## Observed

**O1 — isolated repro, minimal case** (`repro_new_branch_after_merge.sh`, throwaway
`$HOME` + throwaway git repo, never touching the real project or the real `$HOME`):
session 1 calls the real `mark-plan-approved.sh` (the only legitimate marker creator),
branches `taskA`, edits (allowed, as expected), and `taskA` lands on `main` via a ref
move (`git update-ref refs/heads/main refs/heads/taskA` — the same resulting git state
`gh pr merge --merge` + `git pull --ff-only` produces: `main`'s ref simply advances).
`taskA` is never revisited. A "session 2" — **which never calls `ExitPlanMode`** —
branches `taskB` off the now-updated `main` and attempts an edit. Actual run output:

```
=== Session 2 (fresh): NEVER calls ExitPlanMode. Branches taskB off updated main. First edit: ===
  [fileB.txt] exit=0 ::

RESULT: taskB's first edit was ALLOWED (exit 0) with NO fresh ExitPlanMode call.
        Marker present: /tmp/tmp.h6bsdLDeDX/home/.claude/plans/.approved--tmp-tmp-h6bsdLDeDX-project
        This is riding Session 1's stale, already-consumed approval.
```

**O2 — same defect surfaced independently** inside a larger 4-case stacked-chain repro
(`repro_stacked_chain.sh`, same throwaway-environment discipline): after simulating the
chain's own epic-end landing (case4's work reaching `main` via the same `update-ref`
technique) and then branching a brand-new `case5-after-merge` off the updated `main`,
the first edit on that new branch was allowed (`exit=0`) with no fresh approval —
confirming O1 was not an artifact of that script's specific setup.

**O3 — root cause, read against the actual shipped code**
(`hooks/check-plan-approved.sh:172-225`, current `main` tip `efa5994`):

```bash
if [ -n "$CUR_BRANCH" ] && [ "$CUR_BRANCH" != "main" ] && [ "$CUR_BRANCH" != "master" ]; then
  _read_stamp "$STAMP"
  if [ "$STAMPED_BRANCH" != "$CUR_BRANCH" ]; then
    BASE_SHA=$(_ref_sha "$GITDIR" "$MAIN_REF")
    if [ -n "$BASE_SHA" ]; then
      { echo "branch=$CUR_BRANCH"; echo "base=$BASE_SHA"; } > "$STAMP" 2>/dev/null
    fi
  fi
fi

# Reconcile whatever is CURRENTLY stamped
_read_stamp "$STAMP"
if [ -n "$STAMPED_BRANCH" ]; then
  ... _should_archive check against $STAMPED_BRANCH ...
fi
```

The moment the checked-out branch differs from the stamped one, the first block
**overwrites** `$STAMP` with the new branch + a fresh base (current `main` tip) —
**before** the second block ever gets a chance to reconcile the branch being left. So a
transition from an already-merged branch straight to a brand-new one is never checked
against the old branch at all: the stamp is silently reassigned, and the reconciliation
block that runs immediately after evaluates the branch *just written*, which — being
freshly stamped with `base == current main tip` — reads as "not yet merged" by
construction, regardless of whether the branch actually deserves a fresh approval.

**O4 — this is exactly why the committed test doesn't catch it.**
`test_pr_channel_merge_blocks_the_next_edit`
(`tests/test_plan_approval_scoping.py:470-507`) checks out `main`, merges, then checks
out **back to `fix/landed`** — the *same* branch that was stamped — before feeding the
next edit. In that shape, `CUR_BRANCH == STAMPED_BRANCH`, so the overwrite block never
fires, and the reconciliation block correctly evaluates the real, already-merged
branch. `test_deleted_branch_blocks_the_next_edit` similarly feeds its next edit while
`CUR_BRANCH == "main"` (the overwrite block explicitly excludes `main`, per line
`[ "$CUR_BRANCH" != "main" ]`), so reconciliation also runs correctly there. Neither
committed test exercises "stamped branch merges, then a *different, brand-new* branch
is checked out and edited" — which, given `require-feature-branch` never allows an edit
while `HEAD == main`, is actually the *only* shape an ordinary "finish task, start the
next one" session ever produces.

**O5 — the defect fired for real, on this exact session, while writing this dossier.**
This session's own `.approved-branch-C--Dev-sartor` stamp (checked before creating this
branch) still named `branch=fix/plan-approval-marker-pr-merge` — the branch that closed
item 45 and merged as PR #111 earlier today. This session never called `ExitPlanMode`.
Creating `fix/plan-approval-branch-switch-gap` off `main` and writing this very file
(a brand-new branch, differing from the stamped one) succeeded with no approval
prompt and no hook block — the real, live-production instance of O1/O2, not merely a
throwaway-repro artifact. (Separately, and not yet explained: the real
`.approved-C--Dev-sartor` marker and `.approved-branch-*` stamp were observed still
present on disk with pre-session mtimes even after a `plan-archived` ledger event for
an unrelated, already-consumed plan fired earlier in this same session — noted here for
completeness, not chased further, since O1–O4 already isolate the mechanism precisely
without depending on that observation.)

---

## Falsified

_(Nothing yet — this is a first-pass diagnosis, not a re-chase of prior dead ends.)_

---

## Inferred

The fix is very likely: reconcile the **previously**-stamped branch (if any, and if it
differs from `CUR_BRANCH`) *before* overwriting the stamp with the new branch's info —
i.e. swap the order of the two blocks in `check-plan-approved.sh:172-225`, or fold them
into one pass that reconciles-then-stamps rather than stamps-then-reconciles. This is a
hypothesis about the fix shape, not yet proven — the falsification experiment below is
what would prove it.

---

## Falsification

**The experiment that settles it.** A new regression test,
`test_new_branch_after_merge_requires_fresh_approval` (or similarly named), in
`tests/test_plan_approval_scoping.py`'s `TestBranchMergeReconciliation` class, mirroring
O1 exactly: approve a plan, branch `taskA`, edit (assert `0`), land `taskA` on `main`
via a real git operation (ref move or merge — either produces the ancestry the
reconciler checks), branch a brand-new `taskB` off the now-updated `main`, feed one
edit, and assert `returncode == 2` with `"PLAN RETIRED"` in stderr — the same assertion
shape `test_pr_channel_merge_blocks_the_next_edit` already uses for its own scenario.

- **If it fails on HEAD** (current `main`, `efa5994`): the hypothesis is confirmed —
  this is real, not a repro artifact, and the ordering fix may proceed.
- **If it passes on HEAD:** the hypothesis is dead. Stop, do not fix, widen the
  instrument (the two throwaway repros above would need to be reconciled against
  whatever the real committed-pytest environment does differently).

---

## The fix

Confirmed via the falsification experiment: `test_new_branch_after_merge_requires_fresh_approval`
failed on unmodified HEAD (`returncode == 0` where `2` was required — the edit was
allowed) before the fix, exactly as the hypothesis predicted.

`hooks/check-plan-approved.sh`: reordered the two blocks inside the branch-merge
reconciliation section so the **previously**-stamped branch is reconciled (and, if
warranted, archived + `exit 2`) *before* the late-bind block gets a chance to overwrite
`$STAMP` with `$CUR_BRANCH`'s info. The late-bind/transfer block now runs only after
reconciliation has had its say — either the old stamp was just archived (in which case
the hook already exited 2 and this code is unreached), or it was legitimately left alone
(not merged, e.g. mid-stacked-chain), in which case transferring tracking to the new
branch is correct and safe.

One candidate addition — forcing a reconciliation pass on every branch switch,
independent of the mtime pre-filter — was tried and then removed: the existing
mtime-based `NEED_CHECK` conditions (specifically `refs/heads/main -nt $STAMP`) already
catch the real-world case, because any merge that lands the old branch on `main`
necessarily advances `main`'s own ref-file mtime past the stamp's. Confirmed empirically
(the full suite, including the new test, passes without it) rather than kept "to be
safe" — an unreachable branch of a conditional is exactly the kind of thing that looks
harmless and isn't (charter: efficiency is a first-class concern, not an afterthought).

---

## Acceptance bar

The new regression test (`test_new_branch_after_merge_requires_fresh_approval`) passes
GREEN after the fix, with no reruns. All existing tests in
`tests/test_plan_approval_scoping.py` (18 from item 45's own branch, now 19 with this
one) continue to pass unmodified — this fix must not reintroduce anything item 45
already closed, and must not regress `TestEfficiency::test_no_git_subprocess_when_main_has_not_moved`.
Full gate (`ruff` / `ruff format --check` / `mypy` / `pytest`) green, no reruns.

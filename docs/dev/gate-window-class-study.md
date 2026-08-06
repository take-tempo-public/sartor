# Class study: the gate-window gap — post-gate artifacts are never re-gated

> **Status:** documented for resolution in a future sprint — tracked as work item
> **52** (`docs/dev/work/items/0052-gate-window-final-tree.md`). This document is
> the durable evidence record: every observed instance, the shared mechanism, what
> already catches it, what does not, and the candidate mechanisms a resolving
> branch should weigh. Owner-directed 2026-08-06 ("document this durably with a
> class study ... so that it can be resolved in a future sprint").

## The class, in one sentence

A branch's quality gate runs green, and then the branch keeps producing artifacts
— a handoff authored after the gate, a file staged with the wrong git mode, an
amended commit — so the tree that actually lands was **never the tree the gate
examined**, and the close-out's green claim is true of a state that no longer
exists.

This is a C-0 exposure before it is a CI exposure: the branch's own committed
close-out documents (handoff `gate_summary` sections, commit messages) assert a
green gate for the final tree, and that assertion is unverified by construction.

## Observed instances (chronological; all cited)

1. **`dfe1767` (pre-chain, ~2026-07):** "the three new hook scripts were not
   executable" — hook files created by agent tooling landed without the git
   executable bit. First sighting of the mode-bit sub-class; fixed, and the
   catching test (`tests/test_evidence_gate.py::TestEnforcementIsWired::
   test_every_hook_script_is_executable_in_the_index`) exists because of it.
2. **`feat/enforcement-first-governance` + `feat/flake-rate-measurement`
   close-outs (2026-08-05):** both handoffs disclose running the gate's six steps
   individually and *not* re-running the `scripts.gate` wrapper afterwards —
   disclosed deviations, adjacent to this class (steps did run on the
   then-current tree) but establishing the pattern that the *literal final
   sequence* is never re-checked as a whole.
3. **`feat/verify-dont-assume-guard` / `ee2ee0f` (2026-08-06, the chain's Case
   2) — the defining instance.** Gate reported `2357 passed`; the branch tip
   failed 2 tests. Root-caused by the successor branch via `git stash` isolation
   (`docs/dev/handoffs/fix-plan-approval-marker-pr-merge.md`, "chain-level
   blocker"): (a) `hooks/bash-dispatcher.sh` committed at git mode 100644 — the
   index-scanning executable test was vacuous while the file was unstaged at
   gate time, red the moment it was committed; (b) the handoff — authored
   *after* the gate by contract order — embedded a regex literal whose `](`
   sequence `check_doc_links.py` parses as a markdown link. Second sighting of
   the mode-bit sub-class; first of the post-gate-doc sub-class.
4. **`fix/plan-approval-marker-pr-merge` (2026-08-06, Case 3):** its own handoff,
   *describing* defect 3b, quoted the same literal and reproduced the same
   doc-link failure — found by Case 4's RED-first run, not by Case 3's gate
   (same mechanism: the handoff postdates the gate).
5. **`fix/chain-gate-integration` (2026-08-06, Case 4):** while fixing 3a+3b it
   (a) reproduced the doc-link trap a third time in its own handoff — caught
   pre-commit only because it ran `check_doc_links.py` by hand against the
   not-yet-staged file — and (b) amended its handoff commit, which changed the
   commit hash after the pointer and ledger row had cited the pre-amend hash
   (`af1482f`, unreachable from any branch; reconciled by an appended fresh
   `generated` row at chain close).
6. **Adjacent (item 49, 2026-08-05):** a `git add -A` swept an untracked
   `personas/bundled/tmp*.html` into a commit — post-gate *staging* surprise,
   same window, different artifact type.

## The mechanism (shared by every instance)

The close-out contract's order is: gate → pre-close sweep → author handoff →
stage → commit → (sometimes) amend. Everything to the right of "gate" mutates
the tree, and three properties make the window invisible rather than merely
risky:

- **Index-scanning tests are vacuous for unstaged files** (instance 3a: the test
  passed honestly against an index that did not yet contain the file).
- **The handoff cannot precede the gate** — it must *record* the gate's result —
  so a whole document is structurally guaranteed to be un-gated (instances 3b,
  4, 5a). Any content-sensitive test (doc-links, wordmark lints, template
  validation-adjacent checks) can be broken by it.
- **Amends re-hash after every mechanical citation step has run** (instance 5b).

## What already catches it, and where

- CI on the PR runs the full suite against the pushed tree — the **backstop
  exists**; instance 3 would have gone red on the PR. The gap is *local*: the
  close-out's own committed green claim is wrong, the next branch inherits red,
  and (per instance 3) a full ci_wait cycle would have been wasted.
- `test_every_hook_script_is_executable_in_the_index` and
  `check_doc_links.py` detect their sub-classes perfectly — *when run against
  the final tree*. Detection is not the gap; **when detection runs** is.

## Candidate mechanisms (for the resolving sprint to weigh — none built here)

1. **A final-tree structural re-check** — a fast (~40s) named subset
   (doc-links, hook modes, `work_items check`, `verify_doc_template` on the
   branch's own handoff) run **after the last commit**, as either a
   `scripts/gate.py --structural` alias the checklist mandates post-commit, or
   a pre-push hook that fails closed. Cheap enough to re-run after any amend.
   The chain's own close pass (2026-08-06, `f240042`) executed exactly this
   subset by hand, twice (pre- and post-commit) — a working prototype of the
   procedure, currently prose-only and therefore, per C-11, **unenforced**.
2. **Handoff-last ordering with a re-gate**: author handoff → run the
   structural subset → commit once, never amend (an amend re-opens the window;
   instance 5b). Weaker than 1 (relies on discipline) unless 1 enforces it.
3. **Do nothing locally; rely on CI** — rejected by the evidence: instance 3
   cost a successor branch its gate step and would have cost a ci_wait cycle;
   and the committed handoff's false green claim is a C-0 problem CI cannot
   retroactively fix.

Per charter **C-11**, this recurrence (three sightings of the mode-bit/post-gate
class) obliges a fail-closed mechanism, not this document alone — this document
plus item 52 is the *declared* state (C-12) until the resolving branch lands one.

```toml
epic = "epic/a-app-core (board item 36 -- Final March epic A: main-app function + UX)"
declared = "2026-08-09"
authorization = "docs/dev/epic-a-chain-design-corrections.md, section 15.2 and section 15.3"
```

# BOARD.md staleness deferral -- Epic A

**This file's mere existence, well formed, is the exemption.** There is no
separate flag anywhere that also has to be set, and none that has to be
unset when this ends -- deleting this file is the entire off-switch. See
`scripts/work_items.py::_read_board_deferral()` for the parser and
`check_with_deferral()` for exactly what it does and does not tolerate.

## What this defers, and what it does not

`python -m scripts.work_items check` (wired into `scripts/gate.py`'s 5th
step) normally fails the moment `docs/dev/work/BOARD.md` doesn't match a
fresh render of `docs/dev/work/items/*.md`. Per
[`docs/dev/epic-a-chain-design-corrections.md`](../epic-a-chain-design-corrections.md)
§15.2 ("light per sprint"), Epic A's remaining sprints (A3 onward) file work
items per-sprint without regenerating `BOARD.md` each time -- the
regeneration is deferred to the epic's close-out, a single pass rather than
one per sprint. §15.3 requires that any chain epic choosing this declare it
explicitly, name the epic, and cite the authorizing decision -- this file is
that declaration.

**While this file is present and well-formed, `check` tolerates ONLY
`BOARD.md` staleness.** Every structural rule in `scripts/work_items.py`
(duplicate ids, dangling `epic`/`depends_on` references, malformed
frontmatter, the C-11 closure bar, an epic closed while a child is not,
`board`'s own regeneration correctness) still applies exactly as before --
none of that is gated by this marker. `python -m scripts.work_items board
--write` also ignores this file entirely and always regenerates from source,
so `board --write` at any point produces a correct, current `BOARD.md`
regardless of whether this marker exists.

**A malformed copy of this file grants nothing.** If `epic`, `declared`, or
`authorization` is missing, empty, or the frontmatter fails to parse, `check`
fails exactly as if this file did not exist at all -- see
`tests/test_work_items.py::TestBoardDeferral` for the malformed-marker cases
this is tested against.

**The named epic is cross-checked against the real backlog, not taken on
faith.** An adversarial review of this mechanism found that `epic` above is
free text nobody verified against actual backlog state -- a well-formed
marker granted the exemption regardless of which epic was actually running,
because the only control was "someone had to write this file and it's
visible in the diff." `check` now additionally requires that `epic` name a
real `docs/dev/work/items/*.md` entry with `kind = "epic"` and a non-closed
`status` (matched via that item's declared `branches` -- see
`scripts/work_items.py::_find_deferral_epic()`). A marker naming an epic id
or string that doesn't exist, or that exists but is `status = "closed"`,
grants nothing -- same fail-closed treatment as a structurally malformed
marker, with its own distinct error message so the two are never confused.
See `tests/test_work_items.py::TestDeferralEpicCrossCheck` for the
real/closed/nonexistent-epic cases this is tested against, and
`TestRealBacklogDeferralEpic` for the bridge test confirming this file's own
live marker (naming item 36, Epic A) still passes.

**What this still does not verify (declared, not silently filled -- charter
C-12):** that the branch actually running right now is a member of the named
epic. This cross-check confirms the CLAIMED epic is real and currently open
in the backlog; it does not parse `git branch` or otherwise confirm the
working branch belongs to that epic. A marker could still name a real, open,
unrelated epic and pass. Closing that gap would mean branch introspection --
deliberately out of scope for this pass; it is tracked as a data point for
the future "managed/orchestrated epic execution" design pass (see the work
item filed for that).

## When a green `check` run is not a current board

Every `check` run while this file is active prints an unmissable notice
naming the deferral, the epic, and this file -- never a plain "OK". That
line is the signal that `BOARD.md` is stale by design, not by neglect: see
`docs/dev/work/items/0065-wiki-freshness-counter-measures-the-wrong-thing.md`
for the cautionary precedent this is built not to repeat -- a gate whose
green run stopped meaning what it used to mean, discovered only after every
honest agent had to choose between violating its intent and quietly
satisfying its letter. This marker exists so that choice never has to be
made silently: the green run still says, in the same line a human or CI
actually reads, that it is not the thing it normally means.

## Removal

Delete this file as part of Epic A's close-out, immediately before running
`python -m scripts.work_items board --write` to regenerate `BOARD.md` for
real. After that, `check` reverts to being exactly as strict as it is for
every other branch in this repo -- no residual state, no separate flag left
behind to also clean up.

## Updates

### 2026-08-09 -- filed at `feat/role-summary-drafting` close-out (Epic A, sprint A3)

Created to unblock `tests/test_work_items.py::TestRealBacklog::test_committed_board_is_up_to_date`,
which started failing at A3's own close-out (commit `4fb60ee`, items 0069/0070
filed) once `docs/dev/epic-a-chain-design-corrections.md` §15.2's
per-sprint-filing-without-regeneration cadence was actually exercised without
anyone having reconciled it against this gate. Built per explicit owner
authorization, scoped narrowly per the owner's own wording: "adjust the test
to tolerate staleness, but only under explicit conditions in which it is
called for (like a branch chain or epic wave)."

### 2026-08-09 -- epic cross-check added (same branch, follow-up task)

An adversarial review of this mechanism found the gap described above under
"The named epic is cross-checked against the real backlog, not taken on
faith." Owner-directed fix: `epic` above is now cross-checked against real
`kind = "epic"` backlog state rather than accepted as free text. This is a
strengthening, not a behavior change for this file's own live marker -- item
36 is a real, open epic, so `check` continues to defer exactly as before (see
`TestRealBacklogDeferralEpic::test_real_deferral_marker_names_epic_a_and_verifies`).

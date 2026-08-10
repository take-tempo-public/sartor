```toml
schema = 1
id = 76
kind = "item"
title = "BOARD_DEFERRAL.md's declared field has no expiry bound -- an unbounded exemption, and the gap itself was undisclosed"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/work/BOARD_DEFERRAL.md",
  "scripts/work_items.py",
]
summary = "declared is checked for presence only, never as a date -- the staleness exemption never expires on its own."
```

**The gap.** `docs/dev/work/BOARD_DEFERRAL.md`'s `declared` field is
validated for **presence** only (`scripts/work_items.py:507`, `:538-542`) --
never parsed as a date, never compared against any threshold. A well-formed
marker naming a still-open epic grants the staleness exemption
**indefinitely**; the only off-switch is a prose instruction to delete the
file (`BOARD_DEFERRAL.md:84-90`).

**Why this rises to an item rather than a shrug.** The marker's
*branch-membership* gap IS disclosed, in three places, per C-12. This one is
named nowhere -- and C-11's whole clause is "a constraint with no mechanism
that fails closed is not a constraint." An unbounded exemption resting on
documented manual removal is precisely the shape that clause exists to
catch.

**This is a gap in an otherwise working mechanism, not a broken one.** The
mechanism was probed hard by the reviewer and holds up: fail-closed by
default, cannot bypass the C-11 closure bar, epic cross-checked against real
backlog state, loudly printed into CI logs. The one thing missing is any
bound on how long the exemption itself may run before someone has to look at
it again.

**Candidate directions to record, not designed or endorsed -- this is the
owner's call:**

- Parse `declared` as a date and fail the exemption past N days.
- Require the marker to name a commit count or sprint count it expires at.
- Have the epic's own closure automatically invalidate the marker.

**Cross-reference.** Item 71 (the managed-epic-execution design-pass data
item) -- this is more data for exactly that pass.

## Updates

### 2026-08-10 -- filed at `feat/prior-apps-pipeline` close-out (final Epic A adversarial review)

Filed following the final Epic A adversarial review's confirmed finding:
`declared` is presence-checked only, never date-parsed or threshold-compared,
so the exemption it grants has no expiry mechanism and that absence was
undisclosed. `decision_owner = "user"` -- choosing an expiry policy (day
threshold, commit/sprint count, or epic-closure auto-invalidation) is a
governance call, not a mechanical one.

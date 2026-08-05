```toml
schema = 1
id = 47
kind = "item"
title = "Audit sibling scroll-spy tests for the same settle-gate hole item 44 fixed"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
  "docs/dev/diagnosis/ux-scroll-spy-overlapping-refresh.md",
]
summary = "Item 44's fix landed in one shared helper; other tests reasoning about spy events after a clear were not audited."
```

Filed 2026-08-04 from `fix/ux-scroll-spy-overlapping-refresh`, as the "Still open" item its
diagnosis dossier records rather than leaving implicit.

Item 44's root cause was a **settle gate that opened too early**: the scroll-spy timeline was
cleared once `refreshCorpus-exit` appeared, but `_restoreScrollY`'s spy record is emitted a
full microtask-drain later, so a leftover landed in the freshly-emptied timeline and was
counted against the invocations the test tracked. The fix gates the clear on that
invocation's own `_restoreScrollY-fired` too, in a shared
`_settle_and_clear_spy_timeline()` helper.

**What was not done, and why this item exists.** That helper was extracted from exactly one
test. Any other test in the scroll-spy family that clears or snapshots the timeline on an
event that precedes a still-pending record — or that counts `_restoreScrollY-fired` events
after any clear — has the same hole and would fail the same way, at whatever rate its own
environment produces. Scope on that branch was bounded to item 44 (one branch, one item), so
no audit was run.

**Why `watching` rather than `open`:** no second instance has been observed. Item 44 itself
sat at `watching` on a single CI sample and was escalated by a recurrence, which is the
intended shape. Escalate this the same way — if any other test in
`tests/ux/regression/test_20260708_busy_states_and_chip.py` flakes on a spy-event count,
audit the whole family rather than patching that test.

**The cheap version of the audit**, when someone picks it up: grep the file for
`__scrollSpy = []` and for `_spy_events(page, "_restoreScrollY-fired")`, and for each hit ask
whether the event it gates on is provably later than every record it needs drained. The
answer is in `_SCROLL_SPY_NAMED_HOOKS_JS`'s own header — it documents which records are
fire-and-forget rAFs, which is what makes the ordering decidable by reading rather than by
running.

**Do not** widen `_settle_and_clear_spy_timeline()`'s gate speculatively to cover tests that
have not been shown to need it. Item 44's own evidence trail exists because the mechanism was
proven before the gate was touched.

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

## Updates

### 2026-08-06 — partial contribution: 19 siblings clean across up to 30 real CI runs

`feat/flake-rate-measurement` backfilled 30 real CI runs and ranked every test in
`tests/ux/regression/test_20260708_busy_states_and_chip.py` (the file this item names)
by per-attempt failure rate. **This is the "cheap version of the audit"'s empirical
half, not the code-read half this item actually asks for — it does not replace the
grep-and-read step below.**

Result: item 44's own test is the only one in the file with a nonzero rate (21/48
attempts across 30 runs, 11 distinct SHAs — see item 44's closure and item 19's
2026-08-06 update). **All 19 other tests in the file show zero failures and zero
absorbed reruns** across their observed windows (most at 30/30 runs; the newer
`test_settle_gate_clears_the_timeline_without_leaking_a_pending_restore` at 12/12,
consistent with being added post-fix). Full per-test table:
`python -m scripts.flake_rates report --tier ux --min-attempts 1` against the
committed store in `docs/dev/flake-rates/`.

**What this does and does not establish.** Zero observed failures across ≤30 runs is
consistent with "no sibling has the same hole," but at this sample size it cannot
distinguish that from "the hole exists but hasn't fired yet" — absence of evidence at
n≤30 is weak evidence of absence, not proof. It also cannot see anything about the
`_settle_and_clear_spy_timeline()` gating logic itself, which is exactly the thing the
grep-and-read audit above would check. **The audit this item asks for is still not
done** — this update narrows "which sibling should you check first if one starts
flaking" from 19 candidates to effectively none observed so far, nothing more.

```toml
schema = 1
id = 62
kind = "item"
title = "A scroll-creep xfail flips to xpass between runs — nondeterministic, currently invisible because the marker is non-strict"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
]
summary = "Two gate runs over the same code gave `1 xfailed, 1 xpassed` then `2 xfailed` — the xfail is nondeterministic."
```

**Observed during sprint A1b's close-out**, across the two full gate runs this
session made. Not caused by this branch — it touches no scroll code.

Two consecutive `pytest -m ux` runs reported different outcomes for the same pair
of tests:

```
staged tree:     138 passed, 2388 deselected, 1 xfailed, 1 xpassed in 524.75s
committed tree:  138 passed, 2388 deselected, 2 xfailed        in 463.57s
```

The pair, both in `tests/ux/regression/test_20260708_busy_states_and_chip.py`:

- `test_wizard_render_smooth_scroll_creeps_explicit_baseline`
- `test_wizard_render_firing_after_baseline_creeps_it`

The only diff between the two trees is a test-file fix in
`tests/test_proposal_review_bridge.py` plus docs — nothing either scroll test
reads. So one of the two **xpasses on some runs and xfails on others**.

**Why it is currently invisible.** The marker is non-strict, so an xpass is not a
failure and the gate stays green either way. Nothing surfaces the flip; it is
visible only by diffing two summary lines by eye, which is how it was caught.

**Why it is worth tracking anyway.** An xfail that sometimes passes is either (a)
a genuinely nondeterministic behavior under test, or (b) a condition that has been
fixed and the marker is now stale — and those two want opposite responses. Until
someone checks which, the marker asserts something that is not reliably true. If
the marker were ever made `strict=True` (the usual hardening move), the gate would
start failing intermittently for reasons unrelated to whatever branch tripped it.

**Not investigated.** Which of the two flipped was not determined — the summary
line reports only counts, and the per-test XFAIL/XPASS lines were captured for the
committed run only (both XFAIL there). Establishing it needs a repeat-run loop over
just this file, comparing per-test outcomes:
`python -m pytest tests/ux/regression/test_20260708_busy_states_and_chip.py -p no:randomly -rxX` across N runs.

**Related:** epic 19 (UX-flake umbrella) and item 47 (unaudited sibling scroll-spy
tests). This is the scroll-creep family that
[[reference-scroll-anchoring-dy-equals-dh]] and the chip0 anchoring work touched;
whether it is the same mechanism is **not** established here.

## Updates

### 2026-08-08 — filed on `fix/experience-soft-retire` (close-out observation, not branch-caused)

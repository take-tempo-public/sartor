```toml
schema = 1
id = 44
kind = "item"
title = "CI flake: test_scroll_spy_attributes_overlapping_refresh_corpus_calls rerun-exhausted on a docs-only PR"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "https://github.com/take-tempo-public/sartor/actions/runs/30924821284/job/92044338685",
]
summary = "Failed all 3 CI attempts on docs-only PR #98 (3==2 restore-fired, late 3rd _restoreScrollY); not an item-27-31 test."
```

Observed 2026-08-04 on PR #98 (`chore/v11-march-kickoff`, a docs-only diff — zero
production JS/Python changes, so the branch cannot be the cause). The UX CI job
failed after exhausting all three attempts (fail-fail-fail — worse than the known
~42% single-rerun pattern) on
`test_scroll_spy_attributes_overlapping_refresh_corpus_calls`:
`assert len(fired) == 2` got 3 — a third `_restoreScrollY-fired` event with
`ordinal: 2, scheduledDuring: [2]` landing ~46ms AFTER the ordinal-3 event (full
event list preserved in the linked run log). The same local gate run on the same
tree passed the full UX tier (137 passed, only the known pre-existing
xfail/xpass pair in this same file).

This test is NOT one of epic 19's five closed children (27: mode-C residual, 28:
compose-reload restore, 29: restore-scroll-y stale invocation, 30: keyboard
reorder, 31: refinement retry) — a sixth candidate in the settle/restore family,
filed rather than diagnosed. One CI sample; watching until it recurs or a session
picks it up with the `ux-scroll-position-flake.md` rigor. Do not patch around it
in a march sprint — if it blocks a march PR again, that is the escalation signal
to schedule its own `fix/*` investigation.

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff (CI observation on this branch's own PR)

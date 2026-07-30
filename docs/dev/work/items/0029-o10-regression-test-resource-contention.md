```toml
schema = 1
id = 29
kind = "item"
title = "O-12/O-14: the O-10 regression test itself fails under resource contention"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
]
summary = "O-10's own regression test fails 4x under contention (CPU load, -n2, cross-project procs); 5/5 in isolation."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 3 of that epic's original 5, and the one with the most
accumulated evidence (4 occurrences to date).

`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` — the O-10 deterministic
reproduction that forces exact event ordering by construction, not CPU-load timing — has failed
four times under confirmed resource contention and passed cleanly in isolation every time it was
retried isolated:
- O-12, occurrence 1: deliberate `pytest tests/ux -n 2` parallelism (`before=59 after=306`).
- O-12, occurrence 2: unintentional overlap with a separate concurrently-running full-suite
  pytest invocation (`before=59 after=0`); both O-12 runs also found sharing the machine with two
  orphaned `python app.py` processes.
- O-14: next day, on an unrelated branch's (`fix/eval-judge-parse-failure`) plain serial
  `pytest -m ux` gate step — no deliberate `-n 2`, no orphaned same-project server this time, but
  genuine concurrent load from an unrelated project's (`spolia`) `python.exe` processes on the
  same machine. A stash-based A/B confirmed the failure rate is materially unchanged with that
  branch's entire diff removed from the tree (1 pass / 3 fail across 4 serial reruns on the clean
  base commit), ruling out interaction with that branch's own change.

See `docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-12 and O-14 entries for full detail. The
"resource contention" vector has now widened from "deliberate `-n 2`" to "any orphaned same-
project server OR genuine cross-project load" — needs its own busy-loop-style campaign using this
vector (per the diagnosis doc's own suggested next step) before concluding anything about
mechanism. No dedicated diagnosis dossier exists yet beyond the shared document's O-12/O-14
entries.

## Updates

### 2026-07-29 — filed, split from epic 19

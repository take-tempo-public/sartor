```toml
schema = 1
id = 28
kind = "item"
title = "O-13: loadComposition scroll-restore call site fails once, untested by O-10/O-11"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
]
summary = "O-13: test_compose_reload_preserves_scroll_position failed once at loadComposition, a call site O-10/O-11 don't cover."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 2 of that epic's original 5.

`test_compose_reload_preserves_scroll_position` failed once (`before=400 after=796`) at the
`loadComposition` call site (`app.js:7036`) of the same `_captureScrollY`/`_restoreScrollY`
primitive the O-10/O-11 fix patches, during a believed-uncontended run — see
`docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-13 entry. Neither O-10 nor O-11 exercises
this call site; both are written directly against `refreshCorpus`'s capture/restore only. One
sample is not enough to attribute this to the mode-C residual (item 27) or to anything else —
logged as a fact, not a conclusion, per that document's own discipline. No diagnosis dossier
exists yet.

## Updates

### 2026-07-29 — filed, split from epic 19

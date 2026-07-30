```toml
schema = 1
id = 30
kind = "item"
title = "Keyboard-reorder test: one wait_for_load_state 30s timeout, uncontended, no diagnosis"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "tests/ux/regression/test_20260604_bullet_drag_reorder.py",
]
summary = "test_keyboard_reorder_persists_and_reset_reverts: one Playwright 30s wait_for_load_state timeout; single sample."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 4 of that epic's original 5, and unrelated to the scroll-
position mechanism items 27-29 track.

`test_keyboard_reorder_persists_and_reset_reverts`
(`tests/ux/regression/test_20260604_bullet_drag_reorder.py`) hit one Playwright
`wait_for_load_state` 30s timeout, single sample, in a run believed uncontended. No diagnosis
dossier exists yet — this item is the scheduled follow-on to investigate, not a diagnosis in
itself. Per C-7, the first commit on any branch against this item must be the instrument or
reproduction, never a fix.

## Updates

### 2026-07-29 — filed, split from epic 19

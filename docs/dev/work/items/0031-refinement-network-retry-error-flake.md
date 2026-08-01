```toml
schema = 1
id = 31
kind = "item"
title = "Surgical-refinement network-retry test: assertion flake, one isolated-clean rerun so far"
status = "closed"
resolution = "Capability-proven mechanism, fixed 2026-07-31 (fix/ux-surgical-refinement-network-retry-flake): onUserSelect's async tail (loadConfig then _landingTab, sequential awaits) can land its setStatus('READY') AFTER a different action already set a more meaningful status (e.g. a refinement's ERROR), clobbering it -- proven via a deterministic page.route() capability probe that reproduced the exact historical pill text byte-for-byte ('ready'), with a reverse control confirming the race is necessary, not just sufficient. Also corrected this item's own filing: the '-n 2' attribution on its first occurrence was an unsourced downstream narrowing, contradicted by the only surviving artifact (a plain serial pytest -m ux run) -- both known occurrences were serial, same drift shape item 30 found for 'wait_for_load_state'. Two-phase fix, owner-approved: an app-side _statusGen generation guard (static/app.js, mirrors item 29's own _navGen idiom) skips the stale write entirely when superseded; a harness settle contract (UserPicker.SELECT_READY, mirrors the data-compose-ready idiom) makes UserPickerPage.select() wait for the real cascade instead of just the <select> value. One collateral regression surfaced and fixed: test_smart_landing_tail_defers_to_user_navigation (item 29's own deterministic reproduction) relied on select()'s old narrow contract to hold part of the same cascade open on purpose; updated to drive the raw pre-fix primitive instead. Full ux suite clean post-fix (136 passed, 2 xfailed, zero reruns); full gate green."
decision_owner = "agent"
epic = 19
refs = [
  "tests/ux/regression/test_20260708_review_surface_and_flows.py",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
  "docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md",
  "static/app.js",
  "ui_pages/user_picker.py",
  "ui_pages/selectors.py",
]
summary = "test_surgical_refinement_network_failure_surfaces_error_with_retry: assertion flake, twice serial (corrected)."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 5 of that epic's original 5, and unrelated to the scroll-
position mechanism items 27-29 track.

`test_surgical_refinement_network_failure_surfaces_error_with_retry`
(`tests/ux/regression/test_20260708_review_surface_and_flows.py`) failed once
(`'error' not in status_text`) under deliberate `-n 2` contention, then recurred once more during
`fix/eval-judge-parse-failure`'s gate run — that time in a plain serial `pytest -m ux` run, not
under `-n 2` — but passed cleanly on an immediate isolated rerun, the first isolation data point
for this candidate (previously "not yet reproduced in isolation" per the epic's original filing).
Still one clean-isolation sample, not a diagnosis. No diagnosis dossier exists yet — this item is
the scheduled follow-on to investigate, not a diagnosis in itself. Per C-7, the first commit on
any branch against this item must be the instrument or reproduction, never a fix.

## Updates

### 2026-07-29 — filed, split from epic 19

### 2026-07-31 — investigated and closed (`fix/ux-surgical-refinement-network-retry-flake`)

**Provenance correction to this item's own description above:** the "-n 2 contention" attribution
on the first occurrence was an unsourced downstream narrowing — the earliest record
(`docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md:798-807`, 2026-07-26) says only "ran the FULL
`pytest -m ux` suite," plain serial; the `-n 2` wording first appears two documents downstream,
uncited, in this epic's own original filing (commit `6bb7d47`, 2026-07-28). Both surviving
failure artifacts confirm serial runs (no xdist plugin, no `gw` worker markers). Full detail:
`docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md` O-1/O-2.

A direct code read of the call path (`static/app.js` `onUserSelect`/`setStatus`) produced a
specific, coherent candidate mechanism, then a deterministic `page.route()` capability probe
(pre-registered before running, per C-7/C-8) confirmed it on the first try: `onUserSelect`'s
async tail can land `setStatus('READY')` after a different action's more meaningful status
(e.g. a refinement's `ERROR`) already landed, silently overwriting it — reproducing the exact
historical pill text, `"ready"`, byte-for-byte. A reverse control confirmed the race is
necessary, not just sufficient.

**Fix, owner-approved as two-phase (same pattern item 29 used):**
1. App-side guard (`static/app.js`): a new `_statusGen` counter, mirroring item 29's own
   `_navGen` idiom, lets the tail detect a newer status write happened and skip its own stale
   one — a genuine product fix, not just a test-harness one.
2. Harness settle contract (`ui_pages/`): `UserPickerPage.select()` now waits for the real
   `onUserSelect` cascade (`UserPicker.SELECT_READY`, mirroring the `data-compose-ready` idiom)
   instead of just the `<select>` value updating.

One collateral regression surfaced by the harness change: `test_smart_landing_tail_defers_to_
user_navigation` (item 29's own deterministic reproduction, `test_20260708_busy_states_and_chip.py`)
deliberately held part of the same cascade open before calling `select()`, relying on the old
narrow contract — updated to drive the raw pre-fix primitive directly, since its whole design
requires racing ahead of the cascade on purpose.

Verified: P1 re-run post-fix confirms the guard suppresses the write entirely (no `'READY'` log
entry at all, not just outrun in time). The real target test: 10/10 clean serial loop, clean
within its own file, clean in the full suite. Full `pytest -m ux`: 136 passed, 2 xfailed, zero
reruns. Full `python -m scripts.gate`: all steps green. Dossier:
`docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md`. Epic 19: this was the last
open child — epic closes alongside this item.

```toml
schema = 1
id = 30
kind = "item"
title = "Keyboard-reorder test: one Playwright 30s timeout, uncontended, no diagnosis"
status = "closed"
resolution = "Not confirmed as the historical cause (no traceback ever existed for the one 2026-07-28 sample -- docs/dev/diagnosis/ux-keyboard-reorder-timeout.md O-1), but a real, capability-proven vulnerability with the exact same symptom (a ~30s timeout inside WizardComposePage._wait_settled) was found and fixed 2026-07-31 (fix/ux-keyboard-reorder-timeout): _wait_settled's networkidle wait -- documented as a cheap pre-drain, not the settle gate -- was unbounded and could be blocked by an unrelated, unawaited live-preview iframe load (proven via a deterministic page.route() stall, O-15). Bounded to 5s (contextlib.suppress on timeout); the real settle gate is unaffected. Full ux suite clean post-fix (133 passed, 1 xfailed/1 xpassed unchanged, zero reruns)."
decision_owner = "agent"
epic = 19
refs = [
  "tests/ux/regression/test_20260604_bullet_drag_reorder.py",
  "docs/dev/diagnosis/ux-keyboard-reorder-timeout.md",
  "ui_pages/wizard_compose.py",
]
summary = "test_keyboard_reorder_persists_and_reset_reverts: one Playwright 30s timeout; single sample."
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

### 2026-07-31 — investigated and closed (`fix/ux-keyboard-reorder-timeout`)

**Provenance correction to this item's own description above:** this item's `wait_for_load_state`
specificity was an unsourced narrowing. The original record
(`docs/dev/work/items/0001-gate-unrunnable-by-agent.md:124-132`) says only "a plain Playwright
30s timeout" — `wait_for_load_state` first appears one document downstream
(`0019-ux-flake-solution-sprint.md`), uncited, and this item inherited it verbatim. No traceback
for the original failure exists anywhere in the repo (full audit:
`docs/dev/diagnosis/ux-keyboard-reorder-timeout.md` O-1). The `networkidle` attribution turned
out to be directionally right, but that was established by this branch's own investigation, not
by anything in the original filing.

**Investigation:** wide instrument on all three of `_wait_settled`'s sub-waits (not just
`networkidle`) plus a full-test network census — never caught a live recurrence (7 baseline runs,
all clean), but found reach 7 (immediately after `WizardTemplatePage.open()`) consistently ~15-
20x every sibling reach's `networkidle` cost on every run. Two pre-registered deterministic
capability probes: P2 (an H2 candidate, the Compose background cascade) came back dead —
settled in 6.5s even with a forced repeated failure, confirming a code read that its retry paths
don't recurse. P1 (H1, the live-preview iframe) confirmed: stalling the iframe's script load
reproduces the exact symptom — a genuine `networkidle` `TimeoutError` at ~31s, at the exact call
site the baseline had already flagged.

**App-side alternative investigated and rejected:** cancelling the iframe navigation on leaving
Step 4 would need new infrastructure (no existing mechanism reaches wizard-step transitions —
item 29's `_navGen`/`switchTopTab` precedent is scoped to top-level tab switches only) and would
trade away a plausible benefit (fast re-entry to Step 4). No production code path depends on or
times out because of this iframe. Fix scoped to the harness.

**Fix:** `ui_pages/wizard_compose.py::_wait_settled` bounds the `networkidle` pre-drain to 5s
(`contextlib.suppress` on timeout) instead of leaving it unbounded up to Playwright's 30s
default; the real settle gate (`Compose.SETTLED`) is unchanged. Verified against the mechanism
P1 proved (2/2 clean re-runs post-fix, `timed_out=False`), not just the original repro — the
stall is deterministic, not a race, so this is adequate evidence for that specific mechanism.
Full `pytest -m ux` clean post-fix: 133 passed (131 baseline + 2 new diagnostic probes), 1
xfailed / 1 xpassed unchanged, zero reruns.

**Honest scope of the claim:** this closes a real, demonstrated vulnerability with the same
shape as item 30's symptom — it does not claim to be confirmed as that one historical sample's
actual cause, since no artifact from that sample survives to check. Dossier + reusable probes
(`test_diagnostic_p1_*`, `test_diagnostic_p2_*` in the same test file) are the citable record if
a similar symptom recurs. Epic 19 children remaining: 31.

```toml
schema = 1
id = 30
kind = "item"
title = "Keyboard-reorder test: one Playwright 30s timeout, uncontended, no diagnosis"
status = "watching"
resolution = "Not confirmed as the historical cause (no traceback ever existed for the one 2026-07-28 sample -- docs/dev/diagnosis/ux-keyboard-reorder-timeout.md O-1), but a real, capability-proven vulnerability with the exact same symptom (a ~30s timeout inside WizardComposePage._wait_settled) was found and fixed 2026-07-31 (fix/ux-keyboard-reorder-timeout): _wait_settled's networkidle wait -- documented as a cheap pre-drain, not the settle gate -- was unbounded and could be blocked by an unrelated, unawaited live-preview iframe load (proven via a deterministic page.route() stall, O-15). Bounded to 5s (contextlib.suppress on timeout); the real settle gate is unaffected. Full ux suite clean post-fix (133 passed, 1 xfailed/1 xpassed unchanged, zero reruns)."
decision_owner = "agent"
guardrail = "scripts/ci_wait.py (exit 3 on absorbed reruns) is what made this recurrence visible at all -- gh pr checks reported the run clean; scripts/work_items.py's C-11 closure bar now refuses to re-close this item without a falsifiable verified_by artifact. NEITHER fixes the flake -- the investigation is open and unguarded, stated here rather than implied."
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

### 2026-08-05 — REOPENED: recurred in CI five days after closure (`feat/ci-wait-wrapper`, PR #102)

`python -m scripts.ci_wait 102` reported **exit 3 (GREEN WITH RERUNS)** on PR #102's second
CI run:

```
ci-wait: RERUN ALARM - 1 test(s) needed a retry
    tests/ux/regression/test_20260604_bullet_drag_reorder.py::
      test_keyboard_reorder_persists_and_reset_reverts - 1 of 3 attempts failed
```

All 8 required checks reported bucket `pass`. Without the wrapper reading the job log, this
run was indistinguishable from clean — which is exactly how this class stayed invisible
before.

**Status changed `closed` → `watching`.** The 2026-07-31 resolution above is left in place
unedited, because it is the record of what was claimed, and the claim is now falsified in
one specific respect: it asserted "Full ux suite clean post-fix … zero reruns" as the
closing evidence. That was true of the local suite on that day; it is not true of CI five
days later.

**What is NOT falsified:** the `_wait_settled` unbounded-`networkidle` vulnerability the
branch fixed was capability-proven via a deterministic `page.route()` stall (O-15). That
fix is real and is not being second-guessed. What is falsified is the inference that fixing
it eliminated this test's failure mode — the closure itself said the original cause was
"not confirmed" (no traceback ever existed for the 2026-07-28 sample), so a *different*
mechanism surviving is entirely consistent with that record.

**This is the pattern, not an isolated slip.** Item 30 was closed on a proven fix for *a*
vulnerability with a matching symptom, not on a proven fix for *the* observed failure —
the exact distinction charter C-7 and failure pattern 5f exist to enforce. Closing on
"a real defect with the same symptom was fixed" is how this item came back.

**No traceback available for this occurrence either.** `pytest-rerunfailures` discards the
failed attempt's output when a later attempt passes; the ux tier's own
`pytest_runtest_logreport` hook prints the `[ux] RERUN` line and `longrepr`, so the CI job
log for run `31047661015` is the only place the failing attempt's detail exists. **Capture
it before the log ages out** — that is the first move on any branch that picks this up.

Epic 19's closure ("all 5 children closed") is correspondingly no longer accurate; not
edited here, since the epic's own record should reflect what was believed at the time.

#### Captured evidence — the failing attempt's instrument output (CI run `31047661015`, job `92447082606`)

Retrieved from the job log before it aged out. The `[settle-instrument]` probe that
`fix/ux-keyboard-reorder-timeout` left behind **did fire on this failure** — so for the
first time this failure mode has a captured artifact rather than a bare `PASSED`:

```
tests/ux/regression/test_20260604_bullet_drag_reorder.py:253: in test_keyboard_reorder_persists_and_reset_reverts
[settle-instrument] {
  'reach': 8,
  'panel_visible_s': 0.064,
  'exception': "TimeoutError('Timeout 30000ms exceeded.')",
  'elapsed_total_s': 30.096,
  'cascade_state': {'composeReady': True, 'bgPending': None,
                    'draftSummaryFiredForApp': 1, 'gapFillFiredForApp': 1,
                    'composeApplicationId': 1, 'previewFrameReadyState': 'complete'},
  'still_pending_requests': [],
  ...
}
21:14:50 [ux] RERUN — this attempt FAILED
21:14:54 ... PASSED   (the retry, 3.8s later)
```

**Observed, stated without a mechanism attached (C-7):**

1. **Every quiescence signal the harness has said "ready" at the moment of the timeout.**
   `composeReady: True`, `still_pending_requests: []`, `previewFrameReadyState: 'complete'`.
   A 30.096s Playwright timeout occurred anyway.
2. **This is NOT the mechanism item 30's fix addressed.** That fix bounded an unbounded
   `networkidle` pre-drain that an unawaited iframe load could block. Here the iframe is
   `complete` and there are **zero** pending requests, so `networkidle` was not the blocker.
   The 2026-07-31 fix is not implicated and is not being second-guessed — but it plainly did
   not cover this.
3. **`bgPending: None`, not `0`.** The other five cascade fields read as real values, so this
   one field came back absent/unreadable rather than "zero pending". Whether that is
   meaningful or an artifact of when the probe sampled is **not established** — flagged as
   the first thing to check, not as a cause.
4. **Reach 8**, where the earlier investigation's baseline anomaly was **reach 7**
   (`WizardTemplatePage.open()`, ~15–20x sibling `networkidle` cost). Different reach.
5. **The retry passed 3.8 seconds later**, with no intervening change.

**Do not fix from this.** It is one sample, and the next branch's first commit must be the
instrument or the reproduction, never the fix — this item has already been closed once on a
plausible-and-real-but-wrong mechanism, which is the precise failure this rule exists to
stop.

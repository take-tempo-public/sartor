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

### 2026-08-06 — third occurrence found, previously unfiled (`feat/flake-rate-measurement`)

`python -m scripts.flake_rates collect --limit 30` backfilled 30 real CI runs
(2026-08-03 → 2026-08-06) and found **this test absorbed a rerun on run
[`30859772069`](https://github.com/take-tempo-public/sartor/actions/runs/30859772069)**
(`fix/wiki-freshness-relevance-classification`, 2026-08-03T22:44:17Z, `sha 31dbb1bf`) —
**four days after the 2026-07-31 "fix" landed, two days before the already-documented
PR #102 recurrence, and never filed anywhere until now.** `gh pr checks` on that run
reported `pass`; `python -m scripts.flake_rates` did not exist yet, so nothing read the
job log. This is the exact mechanism item 44 already named ("the repo's own rerun-rate
alarm... was landing in the job log unread on every run") — now dated, cited, and
confirmed for this specific test's specific "fixed" period.

Corrected occurrence count across the 30-run backfill window: **2 of 32 attempts
failed, 2 distinct SHAs** (`31dbb1bf` 2026-08-03, and the already-known `f164e224`/PR
#102 2026-08-05) — both real reruns, zero exhausted-to-3/3 failures in this window.
Per-attempt rate in this specific window: 6.2% raw / 1.7% Wilson lower bound (n=32,
below the report's own `--min-attempts 20` default — reported here, not treated as a
stable rate). **Not root-caused by this branch** — this branch measures, it does not
diagnose; the mechanism question this item already asks remains exactly as open as it
was. Raw data: `docs/dev/flake-rates/` (`report --tier ux` reproduces the count from
the committed store).

### 2026-09-03 — fourth occurrence, PR #131 (`docs/container-persistence-guidance`)

`python -m scripts.ci_wait 131` reported **exit 3 (GREEN WITH RERUNS)** — same alarm,
same test, same rerun-then-pass shape. Captured before the log ages out (CI run
`33708934519`, job `100504072486`).

```
tests/ux/regression/test_20260604_bullet_drag_reorder.py:254: in test_keyboard_reorder_persists_and_reset_reverts
    assert compose.has_custom_order()
...
ui_pages/wizard_compose.py:232: in _bullet_list
    self._wait_settled()
E   playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.

[settle-instrument] {'reach': 9, 'panel_visible_s': 0.005,
  'exception': "TimeoutError('Timeout 30000ms exceeded.')", 'elapsed_total_s': 30.036,
  'cascade_state': {'composeReady': True, 'bgPending': None,
                     'draftSummaryFiredForApp': 1, 'gapFillFiredForApp': 1,
                     'composeApplicationId': 1, 'previewFrameReadyState': 'complete'},
  'still_pending_requests': []}
02:49:16 [ux] RERUN — this attempt FAILED
02:49:20 ... PASSED   (the retry, ~4s later)
```

**Same signature as the 2026-08-05 occurrence, not a new one:** every quiescence signal
reads ready (`composeReady: True`, zero pending requests, iframe `complete`);
`bgPending: None` again, not `0`; reach differs (9 here vs. 8 then) — both past reach 7,
neither is the fix's own mechanism (the iframe is `complete`, so `networkidle` is not
the blocker). Retry passed a few seconds later with no intervening change, same as
every prior sample.

**Not root-caused by this branch, stated plainly, not inferred from category match
alone:** this branch's full diff is `docs/dev/work/BOARD.md`,
`docs/dev/work/items/0106-*.md`, `docs/dev/handoffs/container-persistence-guidance.md`,
and two `docs/dev/ledger/*.jsonl` files — zero application, frontend, or test code.
Confirmed by reading this occurrence's own traceback (above) before writing this entry,
not assumed from the test name matching: the failure is inside
`ui_pages/wizard_compose.py`'s pre-existing `_wait_settled`/`networkidle` wait, a code
path this branch never touches. Per C-7, that reading is what justifies not treating
this as a new instrument-and-fix obligation for this branch — the recurrence itself is
still exactly as open as the 2026-08-06 entry left it.

**No new mechanism authored here (C-11).** A fourth occurrence, still unfixed, on a
branch that cannot plausibly have caused it — filed as evidence, not fixed, because
fixing it needs its own `fix/*` branch with a diagnosis dossier per C-7, not a
docs-only branch's close-out. Flagging explicitly rather than merging past it silently.

### 2026-10-02 — re-measured over 148 CI runs (`chore/release-v1.1.0`, E1 pre-flight)

`python -m scripts.flake_rates collect --workflow ci.yml --limit 130` added shard
the 2026-10-02 `flake_rates collect` shard `985e9282` (held uncommitted for slimming, item 144) (PARTIAL, exit 3: 4 runs' logs expired — `35792455028` 09-22,
`31532932535` and `31448207623` 08-11, `31225698714` 08-07 — and 1 session unreconciled).
`report --tier ux` across both shards:

```
  3.3%    1.4%     5/153       148      5  ux  tests/ux/regression/test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts
```

The five failed attempts, each a rerun-then-pass:

| CI run | date (UTC) | branch | filed before? |
|---|---|---|---|
| `30859772069` | 2026-08-03 | `fix/wiki-freshness-relevance-classification` | yes (08-06 update) |
| `31047661015` | 2026-08-05 | `feat/ci-wait-wrapper` (PR #102) | yes (reopen) |
| `31449717508` | 2026-08-11 | `docs/post-epic-a-findings` | **no — new** |
| `33708934519` | 2026-09-03 | `docs/container-persistence-guidance` (PR #131) | yes (09-03 update) |
| `33805467341` | 2026-09-03 | a Dependabot actions bump | **no — new** |

Raw-log check of `33805467341` (`gh run view 33805467341 --log`), not taken from the parser:
`[ux] RERUN — this attempt FAILED` at 21:01:45, `TimeoutError: Timeout 30000ms exceeded.`,
`[settle-instrument] {'reach': 9, ...}`, then `PASSED` at 21:01:49. Same signature as
08-05 and 09-03.

**Since the last failure (2026-09-03 21:01Z): 0 failures in 47 UX-tier runs**, through
2026-10-02. That is **not evidence of a fix**:
- `git log --since=2026-09-03` shows no change to `ui_pages/wizard_compose.py` or to this
  test file.
- At the measured 3.3% per-attempt rate, 47 clean runs in a row has probability about
  0.967^47 ≈ 0.21. A clean streak this long is unremarkable if nothing changed.

Status stays `watching`. No mechanism has been identified.

### 2026-10-07 — recurred on PR #160 (`fix/python-direct-hooks-plan-gate`)

- `python -m scripts.ci_wait 160` exited **3**: every required check passed, but
  `tests/ux/regression/test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts`
  failed 1 of 3 attempts (run 37669157358, job 112956085468, 2026-10-07T18:48:02Z).
- The failed attempt's traceback: `:254 assert compose.has_custom_order()` →
  `ui_pages/wizard_compose.py:247` → `:232 self._wait_settled()` →
  `test_20260604_bullet_drag_reorder.py:163 _instrumented_wait_settled` →
  `self.page.wait_for_load_state("networkidle")` → `TimeoutError: Timeout 30000ms exceeded.`
- **Observed (code read):** the test's instrumented override calls
  `wait_for_load_state("networkidle")` with **no timeout**, so Playwright's 30 s default applies.
  The 2026-07-31 fix bounded the same wait to 5 s in `ui_pages/wizard_compose.py`.
- **Inferred, unverified:** the instrument re-introduces the unbounded wait that fix removed, so
  when the instrument is active, the timeout is the instrument's own.
- The branch's diff touches no UI, JS or compose code. Nothing was changed for this item here (out
  of scope).

### 2026-10-12 — recurred on PR #166 (`fix/regenerate-persistence`)

- `python -m scripts.ci_wait 166` exited **3**: all eight required checks passed, but the same test
  failed 1 of 3 attempts (run 38310545397, job 115014916256, 2026-10-12T21:27:35Z). The traceback
  is the same as the 2026-10-07 entry: `:254` → `_wait_settled` → the test's
  `_instrumented_wait_settled` (`:163`) → `wait_for_load_state("networkidle")` →
  `TimeoutError: Timeout 30000ms exceeded.`
- **New observation, the instrument's record for the failing reach:**
  ```
  {'reach': 9, 'panel_visible_s': 0.004, 'exception': "TimeoutError('Timeout 30000ms exceeded.')", 'elapsed_total_s': 30.036, 'cascade_state': {'composeReady': True, 'bgPending': None, 'draftSummaryFiredForApp': 1, 'gapFillFiredForApp': 1, 'composeApplicationId': 1, 'previewFrameReadyState': 'complete'}, 'still_pending_requests': [], ...}
  ```
  Reaches 1–8 in the same test had `networkidle_s` of 0.001–0.643 s.
  - At the timeout, the network census shows **no request still open**.
  - The settle condition already held: `composeReady: True` and `bgPending: None`.
  - The preview iframe reported `complete`.

  So the 30 s was spent in `networkidle` with nothing in flight that the census tracks. It
  wasn't a pending XHR or the iframe load the 2026-07-31 fix found.
- **Still inferred, unverified:** the unbounded `networkidle` in the instrument is the timeout's
  source (2026-10-07 entry). This record is consistent with it but doesn't prove why
  `networkidle` never fired.
- This branch's client diff is a Step 6 banner and its toggle in `_renderOutput`; nothing on
  Compose's reorder path. Nothing was changed for this item here (out of scope).

### 2026-10-14 — recurred on PR #170 (`feat/confirm-before-overwriting-typed-edits`)

- `python -m scripts.ci_wait 170` exited **3**: all eight required checks passed, but the same
  test failed 1 of 3 attempts (run 38676437085, job 116231042086, 2026-10-15T03:30:31Z, py3.12 UX
  job, PR head `f2230bd`). The traceback is the same as the two entries above: `:254` →
  `_wait_settled` → the test's `_instrumented_wait_settled` (`:163`) →
  `wait_for_load_state("networkidle")` → `TimeoutError: Timeout 30000ms exceeded.` The retry
  passed 3 s later in the same log.
- **The instrument's record for the failing reach**, read from the raw job log
  (`gh run view 38676437085 --job 116231042086 --log`), not from the parser:
  `reach: 9`, `panel_visible_s: 0.013`, `elapsed_total_s: 30.044`,
  `cascade_state: {composeReady: True, bgPending: None, draftSummaryFiredForApp: 1,
  gapFillFiredForApp: 1, composeApplicationId: 1, previewFrameReadyState: 'complete'}`,
  `still_pending_requests: []`. Reaches 1–8 had `networkidle_s` of 0.0–0.633 s.
  - The census shows **no request still open** at the timeout, and the settle condition already
    held. Same as the 2026-10-12 record: reach 9 of 9, nothing pending, `composeReady: True`.
  - Hit counts at the timeout included `/api/applications/1/preview?template_id=1&context_path=…`
    ×2, `/api/users/alice/preview?template_id=1` ×2 and `static/vendor/paged.polyfill.js` ×2.
    Whether those are relevant is not decided here.
- **Three recorded failures since the 2026-10-02 re-measurement**: PR #160 (10-07), PR #166
  (10-12), PR #170 (10-14). The last two have the identical reach, the identical empty census
  and a retry that passes within seconds.
- **Still inferred, unverified:** the unbounded `networkidle` in the instrument is the timeout's
  source (2026-10-07 entry). Nothing on this branch tests or changes that.
- **This branch is not the cause, by its diff and by two clean local runs, not by a control.** Its
  client diff is Generate's confirm flow (`runGeneration`, `runGenerateCoverLetter`) and
  `_readEditorText`; no Compose reorder path, no `networkidle`, no `wizard_compose.py`
  (`git diff --name-only origin/main..HEAD` names no such file). The test passed in both full
  local UX runs on this branch (run 1 `1 failed, 171 passed` with a different test red; run 2
  `173 passed`). A control run of this test on `main` was not done.
- Nothing was changed for this item here (out of scope). The open C-7 probe branch for this item
  is still the place to find why `networkidle` is not reached with nothing pending.

### 2026-10-14 — C-7 probe branch run (`fix/reorder-networkidle-empty-census`)

Full record: `docs/dev/diagnosis/reorder-networkidle-empty-census.md` (O-1..O-20, F-3, I-1..I-9).
Probe only, by owner direction; **no fix, no change to the test's trigger, status stays
`watching`.**

- **Capability shown, from first principles (P5, one run, fresh page per arm, no app JS):** with
  Playwright 1.60.0 the main frame's `networkidle` is order-dependent. A main-frame request
  finishing and *then* a child-frame commit times out the wait (8.03 s bound) with nothing
  pending, nothing awaiting a body, every child frame reached and `readyState: complete`. The
  opposite order returns in 0.505 s. That is the recorded CI shape (`composeReady: True`,
  `still_pending_requests: []`, preview frame `complete`).
- **Also capable, and distinguishable (P3, isolated):** a request with headers received and its
  body held is invisible to the original census, and withholds `networkidle` once a frame commit
  forces the recalculation. The widened census lists it under `awaiting_body`.
- **Not established:** that either happened on any CI run. The natural-capture attempt found
  nothing: 30 of 30 passed locally under 6 CPU loaders (O-20). At 3.3% per attempt that is about
  a 0.37 chance with no change, and they were not CI runs.
- **The instrument now separates the two.** On a natural failure the dump carries `awaiting_body`
  (filled = a held body), `frame_timeline`, and a per-frame `networkidle` check (all children
  `reached` and main `NOT_REACHED` with `awaiting_body` empty = the order dependence). Read
  those fields from the next `ci_wait` exit-3 job log, not from `still_pending_requests`.
- **Inferred, not observed (I-9):** production `_wait_settled` bounds this wait to 5 s and
  swallows the timeout, so there the stall costs 5 s and does not fail. Every traceback in this
  item since 2026-10-07 goes through the test instrument's *unbounded* wait. The instrument
  arrived 2026-07-31; recurrences are recorded from 2026-08-03.
- **Fix options the evidence supports, none chosen (owner's pick, a `fix/*` branch with its own
  A/B against the real test):**
  1. Bound the instrument's wait as production does (5 s, suppressed) and record
     `networkidle_timed_out` in its record. It removes the 30 s failure; `ci_wait` and
     `flake_rates` would then stop seeing it unless something reads that field.
  2. Replace the `networkidle` pre-drain in `ui_pages/wizard_compose.py::_wait_settled`, whose
     comment calls it "NOT the settle gate". It removes the 5 s stall as well. The pre-drain
     has history (`reference-ux-compose-ready-wait`: the marker cannot see an in-flight
     fetch not yet issued), so this one needs the loop-and-A/B treatment.
- **C-11:** no fail-closed mechanism authored here. The widened instrument records and does not
  gate; the flake still trips `ci_wait` (exit 3) until a fix lands, at about 7 minutes a time.

### 2026-10-15 — Phase A of the owner's fix pick (`fix/reorder-networkidle-bound`)

Full record: `docs/dev/diagnosis/reorder-networkidle-bound.md` (O-1..O-16, F-1, F-2, I-1..I-3).
**Status stays `watching`.** The owner chose "bound the instrument, measure the 5 s stall, replace
the pre-drain only if it shows a gain"; this entry covers the first step only.

- **Observed:** the instrument's `networkidle` wait (`test_20260604_bullet_drag_reorder.py`, the
  line every traceback since 2026-10-07 goes through) had no timeout, while production's identical
  wait is capped at 5 s and swallowed (`ui_pages/wizard_compose.py`). The prior entries' `:163`
  cite is `:303` at `18c5ce1`.
- **Changed:** one shared `predrain_networkidle(page)` used by both; a `[ux] networkidle pre-drain:`
  summary line per run; a fail-closed guard (`test_20261015_compose_predrain_bounded.py`), red under
  a mutation of the bound.
- **A/B on the real test with the P5 order injected before reach 9** (scratchpad plugin, one run per
  arm): the unmodified instrument hung at 30.047 s with `still_pending_requests: []` and the main
  frame `NOT_REACHED`, the CI shape; the bounded instrument passed, with that reach
  `networkidle_timed_out: True` at 5.012 s. **That is capability and mitigation, not a finding that
  this order caused any CI failure.**
- **What this does to the counters, stated plainly:** a stall no longer fails an attempt, so
  `ci_wait` (exit 3) and `flake_rates` stop seeing it. The `[ux] networkidle pre-drain:` line is
  the only place it shows, and **neither tool reads it** (C-11: unenforced, declared).
- **Not done:** Phase B (the stall rate across every Compose test) and the pre-drain replacement.
  Nothing in this entry is evidence that the item is closed; one clean CI run against a 3.3%
  per-attempt rate would not be either.

### 2026-10-15 — Phase B result and branch close (`fix/reorder-networkidle-bound`)

Dossier O-17, O-18. **Status stays `watching`; the owner chose to stop at Phase A.**

- **Measured, one pass, unloaded, local:** every `WizardComposePage` test file, diagnostic probes
  and G1 deselected: `[ux] networkidle pre-drain: 0 stall(s) in 106 reach(es), 8.4 s waiting`;
  66 passed, 0 failed, 0 rerun lines, 4m10s. **A datum, not a finding that the stall does not
  occur**: one pass has little power against a rate near 3.3%.
- **Not obtained:** the 4-pass loop was stopped by the harness's memory-pressure reaper before it
  printed a tally (no data), and the CPU-loaded arm never ran. The reaper killed the wrapper and
  left the pytest, Playwright-driver and browser processes running; they were terminated by hand.
- **Decision (owner, 2026-10-15): stop at Phase A.** The pre-drain is **not** replaced. Nothing
  measured shows it costing anything in the ordinary case, and its history
  (`reference-ux-compose-ready-wait`) is a reason for it. Reopen Phase C only on a stall rate from
  real runs.
- **Where the rate will come from, with no local memory cost:** every CI UX job now prints the
  `[ux] networkidle pre-drain:` line. Read it from the raw job log
  (`gh run view <run> --job <job> --log`). Neither `ci_wait` nor `flake_rates` parses it. A first
  reading on this branch's own PR is the next natural datum.
- **What would close this item:** a falsifiable `verified_by` and `ci_wait` exit 0 with 0 `RERUN`
  markers on the reorder test, across enough CI runs to mean something at 3.3% per attempt. None
  of that exists yet; this branch removes one recorded failure path and makes a stall visible.

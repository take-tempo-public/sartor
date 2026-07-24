# Diagnosis — scroll-flake "mode C": wizard-rail smooth-scroll corrupts an unrelated later baseline

> **Status:** root cause PROVEN by direct capture (O-1/O-2 below). Fix not yet
> written as of this commit.
> **Branch:** `fix/ux-scroll-wizard-rail-flake`

---

## Symptom

`test_corpus_reload_preserves_scroll_position`
(`tests/ux/regression/test_20260708_busy_states_and_chip.py`) is a real
~10-20% flake, `scroll position not preserved: <before> -> <after>`. A prior
branch (`fix/ux-scroll-position-flake`, Chips 0-3) root-caused and fixed
three of its four failure modes (A/B/D) at the `_captureScrollY` /
`_restoreScrollY` layer (`docs/dev/diagnosis/ux-scroll-position-flake.md`).
The fourth, **mode C** — signature `300 -> 369`, the scroll landing just
below the intended 300px baseline — was explicitly scoped out of that branch
as "a separate, unrelated hazard... needs its own diagnosis dossier and
branch," with a measured post-fix rate of ~17% (4/24) under 7-worker CPU
saturation. This dossier is that follow-on.

---

## Observed

### O-1 — an EARLY sync point (scrollIntoView fires, then baseline is set ~60ms later) does NOT reproduce drift

Instrument: `test_wizard_render_smooth_scroll_creeps_explicit_baseline`
(same test file). Loads the app, selects a user (which fires `wizardInit()`
-> `_wizardRender()` -> `#panelJD.scrollIntoView({behavior:'smooth',
block:'start'})`, `app.js:7021`), synchronizes on the scroll spy actually
observing that `scrollIntoView` call, then IMMEDIATELY sets an unrelated
baseline via `window.scrollTo(0, 300)` and reads it back after a 100ms wait.
No `refreshCorpus()` call anywhere in this test — isolates the wizard render
from the (already-fixed) capture/restore primitives entirely.

Captured spy timeline (`SCROLL_SPY_ALWAYS=1`, one representative run):

```
t=945.1   y=0    scrollIntoView  #panelJD  (from _wizardRender, app.js:7021)
t=1006.2  y=0    window.scrollTo [0,300]   (this test's own baseline call)
t=1066.0  y=300  scroll-event
```

`before=300`, `after=300`. **Passed — no drift.** The explicit
`window.scrollTo(0, 300)` call, issued ~61ms after the wizard's smooth
scroll started, cleanly CANCELLED the in-flight animation; nothing moved the
page afterward. 5/5 runs passed at this synchronization point. This
falsifies the *literal* reading of the prior dossier's "residual, still
settling" framing (Inferred §3 there) — an animation that has already
started does not survive a later explicit `scrollTo` in this browser/build.

### O-2 — a scrollIntoView firing AFTER the baseline reliably reproduces the drift

Instrument: `test_wizard_render_firing_after_baseline_creeps_it` (same
file). Reverses O-1's ordering: settle the FIRST (setup) wizard animation
fully (500ms wait after it's observed), THEN set the baseline
(`scrollTo(0,300)`, `before=300`), THEN fire a second `_wizardRender()` call
directly (the real production function — same idiom the prior dossier's
Chip 2 tests used for `_captureScrollY`/`_restoreScrollY`), THEN read
`window.scrollY` again after a wait.

At a 100ms read-delay (matching the real corpus test's own
`page.wait_for_timeout(100)`), this did **not** reproduce in 5/5 tries — the
~69px animation (300 -> `#panelJD`'s ~369) hadn't progressed far enough to
register a different value in a plain 100ms window, even though a
`SCROLL_SPY_ALWAYS=1` dump on one such "passing" run showed the animation
still in flight past the 100ms mark on inspection (a `scroll-event` at
y=306 landed ~318ms after the second `scrollIntoView` call — after the
Python-side `after` value had already been read).

Widening the read-delay to 350ms — still comfortably under the real corpus
test's own total elapsed time once `refreshCorpus()`'s own corpus-card
re-render/settle is counted (this isolated instrument deliberately doesn't
call `refreshCorpus()`, so it has no equivalent margin unless the wait is
widened directly) — reproduces **9/10 runs**, deterministically, with **no
CPU saturation of any kind**. One representative failing run's spy dump:

```
t=841.4   y=0    scrollIntoView  #panelJD  (1st render, setup)
t=1117.9  y=165  scroll-event
t=1207.7  y=306  scroll-event
t=1406.2  y=306  window.scrollTo [0,300]   (this test's own baseline call)
t=1468.3  y=300  scrollIntoView  #panelJD  (2nd render, forced)
t=1475.4  y=300  scroll-event
t=1748.0  y=306  scroll-event               <- animation still moving
```

`before=300`, `after=306`. `AssertionError: ... 300 -> 306`. Every failing
run across the 9/10 shows this same shape — a partial creep toward
`#panelJD`'s target, landing wherever the animation happened to be when the
read fired (never exactly `369`, because a freshly re-triggered ~69px
animation caught mid-flight at an arbitrary point does not land on any one
fixed value — this matches the ORIGINAL dossier's own note that `369` "is a
landing position of an async scroller," not a fixed corrupted read).

### O-3 — mechanism, precisely

The wizard rail's `scrollIntoView({behavior:'smooth', block:'start'})`
(`_wizardRender`, `app.js:7021`) is a native, multi-frame Chromium scroll
animation — not driven by this app's own JS `requestAnimationFrame` loop the
way `_captureScrollY`/`_restoreScrollY` are, so it cannot be forced into a
deterministic ordering via the "register two rAF callbacks in the same
frame batch" trick the prior dossier's Chip 2 falsification tests used. It
CAN be forced into a deterministic *outcome* (O-2) by controlling the wall
clock: fire it after the baseline is set, and read scrollY somewhere inside
its animation window (empirically, needs meaningfully more than 100ms —
but does not need CPU saturation to arrive at that state; it only needs the
render call to happen late relative to the read).

O-1 vs O-2 together mean: the corrupting scrollIntoView call must fire
**at or after** the point the test/user establishes its own baseline read.
A call that has already been running for tens of ms before the baseline is
set does not survive it (O-1). The real corpus test's own timing (baseline
`scrollTo(0,300)` fires only after `select()` + a tab click + a 20-card
settle wait — plenty of time for `wizardInit()`'s single real call to have
already started) means the wild failures are consistent with either (a) an
unusually late-firing single call under CPU load, delaying `onUserSelect`'s
async chain (`app.js:394-441`) past the corpus test's own baseline point, or
(b) some other path re-entering `_wizardRender()` a second time — this
dossier did not need to distinguish those two to reach a fix (see
"## The fix"), since both funnel through the same `scrollIntoView` call
site.

---

## Falsified

**F-1 — "an in-flight smooth scroll survives a later explicit `scrollTo`
call" (would explain the ORIGINAL prior dossier's "residual, still
settling" framing literally).** Falsified by O-1: 5/5 clean cancellations,
zero drift, when the explicit `scrollTo` follows ~61ms after the animation
starts. Whatever "residual" means in the wild, it is not "the exact same
animation instance keeps moving after an explicit scrollTo overrides it."

**F-2 — "a plain 100ms read-delay (matching the real test's own wait) is
sufficient to catch the drift once the ordering is right."** Falsified by
the first half of O-2: 5/5 passed at 100ms even with the corrected
(baseline-then-render) ordering. The mechanism needed a wider window to
manifest in this isolated instrument, which doesn't have the real test's
extra `refreshCorpus()`-settle elapsed time as a stand-in.

---

## Inferred

None beyond what O-3 states as directly observed. The remaining open
question — single delayed call vs. a genuine second call in the wild — is
explicitly NOT resolved here (see O-3's last paragraph) because the fix
below (honoring `prefers-reduced-motion`) closes the entire class either
way: with no in-flight smooth animation possible, there is nothing left to
race regardless of which of the two shapes production actually hits.

---

## Falsification

Already run as part of reaching O-1/O-2 above (the instrument-first
requirement was satisfied by iterating the experiment itself, per charter
C-7 — the first hypothesis tried (O-1's ordering) was falsified, not
patched around; the second (O-2's ordering) was then tried and confirmed).
No further experiment is needed before writing the fix: O-2 is a
9/10-reproducible, non-CPU-saturation-dependent capture of the exact
`before -> partial-target` signature the wild failures show.

---

## The fix

See `CHANGELOG.md` / the branch's own commits for the final diff. Planned
approach (per the plan approved before this dossier was written): honor
`prefers-reduced-motion` across all 5 JS `behavior:'smooth'` call sites in
`static/app.js` (`:508`, `:2916`, `:5855`, `:5862`, `:7021` — the last is
the mode-C site), via one shared helper, rather than a test-side-only
timing fix. The app already honors `prefers-reduced-motion` for its CSS
transitions (`style.css:762,805,2904,3925`) but not for these JS-driven
scrolls — this closes that a11y gap and, as a side effect, removes the
in-flight-animation window mode C depends on entirely: with reduced motion
emulated (the same pattern `tests/ux/a11y/test_axe_smoke.py:116` already
uses), `scrollIntoView` becomes an instant, single-frame jump, so there is
no multi-frame window left for a later baseline read to land inside.

---

## Acceptance bar

- `test_wizard_render_firing_after_baseline_creeps_it` (O-2's instrument)
  flips from proving the defect (`after != before`, ~9/10) to proving the
  fix (`after == before`, deterministic) once reduced-motion is honored at
  the wizard-render call site, under the SAME forced ordering — no longer
  timing-dependent at all once the animation is instant.
- The real `test_corpus_reload_preserves_scroll_position` test emulates
  reduced motion and shows zero mode-C (`300 -> 369`-shaped) failures across
  a saturated-load campaign that previously reproduced it ~17%
  (`scratchpad/capture_scroll_phase1b.sh`, 7 workers / 8 cores).
- Full `python -m scripts.gate` green, verified from the log's own
  pass/fail line (not a bare exit code — `pytest-rerunfailures` can mask a
  fail-fail-pass as a bare `PASSED`).

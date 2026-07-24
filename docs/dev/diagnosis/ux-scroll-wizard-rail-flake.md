# Diagnosis — scroll-flake "mode C": wizard-rail smooth-scroll corrupts an unrelated later baseline

> **Status:** the O-1/O-2 mechanism (wizard render firing at/after the
> baseline) is confirmed, but the FIX first attempted from it (honor
> `prefers-reduced-motion`, scoped-approved before this evidence existed) is
> **FALSIFIED by direct A/B on the real target test** — see O-3/O-4/F-3.
> **The true mechanism is not primarily an animation-timing race; it is
> `scrollIntoView`'s target landing near-but-not-at the test's own baseline
> because of the document's own max-scroll clamp** (O-4). Root cause not yet
> fully closed; no working fix landed as of this commit.
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
(b) some other path re-entering `_wizardRender()` a second time.

### O-4 — the fix (honor `prefers-reduced-motion`) was tried and FALSIFIED by direct A/B on the real target test

A candidate fix (see the now-superseded "Planned approach" this section
used to describe) routed all 5 of `app.js`'s explicit
`behavior:'smooth'` call sites — `:508`, `:2916`, `:5855`, `:5862`, `:7021`
(the mode-C site) — through a shared `_scrollBehavior()` helper returning
`'auto'` when `prefers-reduced-motion: reduce` is set, and emulated that
media feature in the real corpus test
(`page.emulate_media(reduced_motion="reduce")`, the same pattern
`tests/ux/a11y/test_axe_smoke.py:116` uses). **This was evaluated against
the REAL target test, not just the isolated instrument, before being
trusted:**

| condition | runs | failed | rate |
|---|---|---|---|
| control — `static/app.js` at this commit (git-stashed fix), `emulate_media` present but a no-op against the unfixed code | 6 | 2 | ~33% |
| with the fix — `_scrollBehavior()` routing + reduced-motion emulated | 8 | 5 | ~62% |

Small samples (this is exactly the kind of measurement charter C-0/C-7
requires be reported as what it is, not rounded up to a stronger claim),
but the direction is unambiguous and reproduced across TWO separate runs
of the fix condition: **the fix did not reduce the failure rate — it
appears to increase it.**

Re-running O-2's own forced-ordering instrument WITH the fix applied
confirms why, via a 1-second frame-by-frame trace (40 samples,
`requestAnimationFrame`-paced) taken after firing the (now `behavior:
'auto'`) second `_wizardRender()` call:

```
t=25.7    y=306   panelAbsTop=512.1875
t=33.4    y=306   panelAbsTop=512.1875
...  (every one of 40 samples across the full 1000ms window)
t=668.2   y=306   panelAbsTop=512.1875
```

`window.scrollY` lands at **306 and never moves again** — not even one
frame of settling. `#panelJD`'s own true layout position (`panelAbsTop`,
computed from `getBoundingClientRect()`) is a STABLE **512** the entire
time. The scroll never reaches its nominal target at all, with `'auto'` or
`'smooth'`. This viewport is 900px tall (`tests/ux/conftest.py`); this
test's own page content is ~1206px tall (per the O-1/O-2 spy dumps' own
`h` field) — so the document's maximum possible `scrollY` is
`1206 - 900 = 306`, **exactly the observed landing value**. `scrollIntoView`
is being **clamped by the document's own max-scroll bound**, not
completing a partial animation. It was never "still in flight" in O-2
either — O-2's apparent multi-frame "creep" (a `scroll-event` landing at
306 arriving after an earlier sample read a different value) is consistent
with the SAME clamped target being reached over 1-2 frames rather than a
long free-running animation; `'auto'` reaches the same clamped value in
under 2ms.

**Reframed mechanism:** mode C is not fundamentally an animation-duration
race. `_wizardRender`'s `scrollIntoView(block:'start')` on `#panelJD`
targets a position the document cannot actually reach once the corpus
card list is tall enough (20 seeded cards > viewport), so the browser
clamps it to `scrollHeight - viewportHeight`. That clamped value is a
property of page height and viewport height, not of the wizard panel's
"real" target — and it happens to land close to (but not exactly at) the
test's own `scrollTo(0, 300)` baseline for this fixture's specific card
count/viewport combination. Making the call INSTANT (this fix) does not
change WHETHER it corrupts a baseline that was already established when
it fires late — it only removes the possibility that a `scrollTo` shortly
after catches it mid-animation and cancels it cleanly (O-1's finding). If
anything, instant landing may make every late-firing occurrence corrupt
deterministically instead of only when the read happens to land inside a
multi-frame window — consistent with the measured rate increasing.

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

**F-3 — "honoring `prefers-reduced-motion` at the wizard-render call site
fixes mode C."** Falsified by O-4: direct A/B against the REAL target test
(`test_corpus_reload_preserves_scroll_position`, not just the isolated
instrument) shows the fix condition failing at a HIGHER rate (~62%, n=8)
than the unfixed control (~33%, n=6) run in the same session on the same
machine. The animation-timing framing (O-1/O-2/O-3) was a real, correctly
observed phenomenon, but not the primary defect — O-4's frame trace shows
the true defect is a max-scroll clamp, which an instant scroll corrupts
just as surely as (and possibly more reliably than) an animated one.
**Do not re-attempt the reduced-motion fix as scoped here without a new
mechanism.** The `_scrollBehavior()` helper + 5-site a11y fix may still be
worth keeping on its OWN merits (the reduced-motion gap is real regardless
of mode C), but it must not be presented as this bug's fix.

---

## Inferred

The remaining open question — single delayed call vs. a genuine second
call in the wild — is still not resolved (see O-3's last paragraph), and
now matters more: whichever it is, the corrupting call's target position
is clamped by `scrollHeight - viewportHeight` at the moment it fires, and
whether that clamp lands "close enough" to a real user's own scroll
position is presumably why this reads as ~10-20% rather than "always" —
NOT resolved by direct observation yet; this is a hypothesis for the next
falsification round.

---

## Falsification

O-1/O-2 satisfied the instrument-first requirement for the (now falsified)
animation-timing framing. O-4 is itself a falsification experiment against
the fix that framing produced, run BEFORE trusting the fix (per C-7,
"green [an isolated instrument] is not evidence" if the real target test
isn't also checked) — and it caught the fix being wrong. **Next
falsification round, not yet run:** an instrument that holds `document`
height / viewport height fixed and directly tests the clamp hypothesis —
e.g. force `scrollHeight - viewportHeight` to land exactly at vs. away
from the test's own baseline value and confirm the corruption only occurs
in the "away from" case, or investigate whether `_captureScrollY`/
`_restoreScrollY`'s own generation-counter mechanism (already wraps
`scrollIntoView`, `app.js:5551-5554`) could be extended to protect a
plain baseline read the same way it protects a `refreshCorpus` capture,
rather than changing the wizard's own scroll call at all.

---

## The fix

**Not yet found.** See "## Falsified" F-3 and "## Inferred" above. Do not
build on the reduced-motion framing without new evidence.

---

## Acceptance bar

Not applicable yet — no fix has passed its own falsification test. Once a
new candidate exists, it must be checked the same way O-4 checked this
one: A/B against the REAL `test_corpus_reload_preserves_scroll_position`
(not just an isolated instrument), with sample sizes reported honestly, not
just "does the isolated instrument now pass."

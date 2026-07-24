# Diagnosis — scroll-flake "mode C": wizard-rail smooth-scroll corrupts an unrelated later baseline

> **Status:** mechanism **directly observed in the REAL target test**
> (O-5/O-6): `scrollY` shifts silently by exactly the amount the corpus
> list's document height grows (`+25054`/`+25054`, no scroll event) —
> Chromium **scroll anchoring**, in the unprotected window between the
> test's baseline read and `refreshCorpus`'s own capture. **No fix landed
> yet; round 4 (the falsification test for O-6) is not yet run.**
>
> Three earlier framings are dead — do not rebuild on them: honoring
> `prefers-reduced-motion` (**F-3**, made the real test worse), a
> second/late `_wizardRender()` call (**F-4**, 6/6 runs show exactly one,
> always early), and the max-scroll clamp (**F-5**, an artifact of the
> isolated instrument's 1206px page; the real page is 27224px).
> Each earlier framing came from an isolated instrument and died on
> contact with the real test.
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

### O-5 — instrumenting the REAL test shows exactly ONE `_wizardRender()` call, and it is EARLY, not late

Instrument: `_WIZARD_RENDER_SPY_JS` (new this round,
`tests/ux/regression/test_20260708_busy_states_and_chip.py`), injected into
the **real** `test_corpus_reload_preserves_scroll_position` in the same
post-load/pre-`select()` window the existing named hooks use. It wraps
`_wizardRender` (a top-level function declaration, so a genuine window
global) and records per invocation: a structural id, `_wizardStep`, the
resolved panel id, that panel's absolute document top (`wantY`), and
`maxScroll` (`scrollHeight - innerHeight`) at call time. Deliberately wider
than the clamp hypothesis it was written to test.

Across **6 runs** (5 pass / 1 fail, no CPU saturation, `--reruns` not in
play), **every single run recorded exactly one `_wizardRender-enter`
event**, `id: 1`, always from the same stack:

```
_wizardRender <- wizardInit (app.js:6906) <- onUserSelect (app.js:441)
```

It fires at t≈1.2-1.4s, **well BEFORE** the test's own
`scrollTo(0, 300)` baseline (t≈1.8-2.9s) in all 6 runs — including the
failing one.

**This resolves O-3's open question in the direction opposite to the one
the last round's fix assumed.** It is (a), not (b): there is no second
`_wizardRender()` call, and the single real call is not "arriving late past
the baseline." The forced-ordering premise of O-2's isolated instrument
(fire a SECOND render after the baseline) **does not occur in the real
test** — it was a synthetic ordering, not the wild one.

### O-6 — the real failure is Chromium SCROLL ANCHORING on late corpus-list growth, not a scroll animation at all

The one failing run of the 6 (`369 -> 25423`) captured this, with the
`h` (documentElement.scrollHeight) field the spy already recorded:

```
t=1806.7  y=0      h=2101   window.scrollTo [0,300]   <- the test's own baseline (page.evaluate)
t=1916.2  y=369    h=2170   scroll-event
   ... no scroll event of any kind in this gap ...
t=2274.9  y=25423  h=27224  refreshCorpus-enter id=2  <- the test's own refreshCorpus() call
```

Two separate corruptions are visible, and the second is the one that fails
the assertion:

1. `before` was read as **369, not 300** — the baseline itself drifted
   between the `scrollTo(0,300)` and the very next `window.scrollY` read
   (two separate CDP round-trips). `369` is `#panelJD`'s absolute top. This
   is the original "mode C" `300 -> 369` signature, and here it lands in
   `before` rather than `after`.
2. Then `scrollY` went **369 -> 25423** with **no `scroll-event` recorded
   at all**, while `h` went **2170 -> 27224**. The arithmetic is exact:

   | quantity | delta |
   |---|---|
   | `scrollHeight` 2170 -> 27224 | **+25054** |
   | `scrollY` 369 -> 25423 | **+25054** |

   An identical, silent, event-free shift of `scrollY` by exactly the
   amount the document grew is **scroll anchoring** — Chromium adjusting
   the scroll offset to keep the anchored content visually stable when
   content above it changes size. It is not an animation, not
   `scrollIntoView`, and not any call this app makes (nothing in the spy's
   wrapped set fired).

**Why `_captureScrollY`/`_restoreScrollY` do not save it:** the shift
completes BEFORE the test's `refreshCorpus()` runs. That invocation's
`_captureScrollY` reads `y: 25423` (already corrupted) and its
`_restoreScrollY` faithfully restores **25423**. The capture/restore
primitives worked exactly as designed on an already-wrong value.

**The discriminator across all 6 runs**, read at `refreshCorpus-enter id=2`
(i.e. at the moment the test's own reload starts):

| run | `h` at refreshCorpus#2 entry | `y` there | result |
|---|---|---|---|
| 1 | 27224 (already grown) | **25423** | **FAIL** `369 -> 25423` |
| 2 | 27224 (already grown) | 300 | pass |
| 3 | 27224 (already grown) | 300 | pass |
| 4 | 27224 (already grown) | 300 | pass |
| 5 | 27224 (already grown) | 300 | pass |
| 6 | 2170 (grows later) | 300 | pass |

Runs 2-5: the list finished growing **before** the baseline was set, so
anchoring had nothing left to shift. Run 6: the growth landed **after**
`refreshCorpus()` had already captured, so capture/restore corrected it —
the prior branch's fix doing its job. Run 1 is the unprotected middle
window: growth landing **after the baseline read but before
`refreshCorpus`'s capture**, where nothing is watching.

### O-7 — the test's settle gate does not gate on what actually moves

The test's precondition is `expect(corpus_cards).to_have_count(20)`, and it
was satisfied before the baseline in **all 6 runs, including run 1**. Yet
`h` was still `2170` at that point in runs 1 and 6, reaching `27224` only
later. **Card attachment and card layout height are not the same event** —
the count gate proves the former and says nothing about the latter, so the
test proceeds to set its baseline while ~25000px of layout is still
inbound.

### O-8 — O-4's clamp finding is real but does NOT generalize to the real test

O-4 measured `maxScroll = 306` on a **1206px** page — the isolated
instrument, which never clicks the Corpus tab and so never grows the
document. In the real test the document is **27224px** by the time the
baseline is set (`maxScroll` ≈ 26324), and the spy confirms
`_wizardRender`'s own `maxScroll` at call time is 59-379. The clamp is a
genuine property of the *isolated instrument's* short page; it is **not**
the mechanism of the real flake, where nothing is clamped at the moment of
corruption. O-4's reframing was correct about the artifact in front of it
and wrong to be generalized — which is precisely the hazard C-7's "scope
the instrument wider than the hypothesis" exists to catch, here caught by
widening back out to the real test.

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

**F-4 — "mode C is caused by a SECOND `_wizardRender()` call, or by the
single real call arriving late (after the baseline)."** This was O-3's
explicitly-open (a)-vs-(b) question, and O-2's whole isolated instrument
was built on forcing case (b) by hand. Falsified by O-5: instrumenting the
REAL test recorded **exactly one** `_wizardRender()` invocation in 6/6
runs, always from `wizardInit <- onUserSelect`, and always ~500ms+ BEFORE
the baseline — in the failing run too. Neither (a) nor (b) happens in the
wild. `test_wizard_render_firing_after_baseline_creeps_it` reproduces a
real browser behavior, but **not the one the real test hits** — it is a
synthetic ordering, and its passing or failing is not evidence about mode
C. Do not use it as the acceptance signal for a fix.

**F-5 — "the max-scroll clamp (O-4) is mode C's mechanism."** Falsified by
O-8: the clamp was measured on the isolated instrument's 1206px page; the
real test's document is 27224px at the moment of corruption, so nothing is
clamped there. O-4's observation stands **for the artifact it was taken
on**; its generalization to the real flake does not.

---

## Inferred

**Why the corpus list grows in two stages** (h≈2170 with all 20 cards
already attached, then h≈27224) is not yet directly observed. Card
attachment completes first and ~25000px of height arrives later, but which
render pass adds it (a per-card bullet/summary fetch, an expand pass, image
or font layout) has NOT been traced. This matters only for choosing where
a fix attaches, not for the mechanism itself, which O-6 observed directly.

**Whether the `before = 369` drift (O-6 corruption #1) and the anchoring
shift (corruption #2) are independent** is likewise not established. Both
appeared in the same failing run; only anchoring produced the assertion
failure. A fix for anchoring alone may leave a lower-rate `300 -> 369`
flake behind — that would be the ORIGINAL mode-C signature, and it should
be re-measured after any anchoring fix rather than assumed gone.

---

## Falsification

O-1/O-2 satisfied the instrument-first requirement for the (now falsified)
animation-timing framing. O-4 is itself a falsification experiment against
the fix that framing produced, run BEFORE trusting the fix (per C-7,
"green [an isolated instrument] is not evidence" if the real target test
isn't also checked) — and it caught the fix being wrong.

**Round 3 (RUN — this is O-5/O-6/O-7/O-8).** The owner-selected next round
was a clamp test. It was deliberately scoped **wider** than that
hypothesis, per C-7, and instrumented the REAL target test rather than the
isolated one — which is the only reason the clamp framing was caught as
non-generalizing (F-5) and the actual mechanism (scroll anchoring, O-6)
was seen at all. A clamp-only instrument would have confirmed the clamp on
the short isolated page and hidden its rival.

**Round 4, NOT yet run — the falsification test for O-6.** Scroll
anchoring is a *browser* behavior with a direct off switch
(`overflow-anchor: none`). The falsification is therefore cheap and
sharp: suppress anchoring on the growing container and re-measure the REAL
test. Predictions to state BEFORE running, so the result can falsify:

- If O-6 is the mechanism, the `+25054`-shaped `y`-tracks-`h` failures
  disappear and the measured failure rate drops materially.
- If they persist unchanged, O-6 is wrong (or incomplete) and the
  `overflow-anchor` fix must be reverted, not kept "because it seems
  reasonable" — exactly the F-3 mistake.
- A residual, **differently-shaped** `300 -> 369` failure surviving at a
  lower rate would NOT falsify O-6; it is the separate corruption #1 the
  Inferred section flags, and needs its own round.

**Sample-size bar:** the current baseline is **1/6 failures with no CPU
saturation**. That is far too coarse to detect a rate change honestly —
at n=6 a fix could look perfect by luck. Round 4 must use meaningfully
more runs per side (and/or the CPU-saturation repro that raises the base
rate to ~17%, `reference-cpu-saturation-flake-repro`) before any claim
about the rate is made. Report n and failures as counts, never as a
rounded rate alone.

---

## The fix

**Not yet found — but the mechanism is now directly observed (O-6) rather
than inferred.** Do not build on the reduced-motion framing (F-3), the
second-render/late-render framing (F-4), or the clamp framing (F-5).

Candidate shapes for round 4, in order of how surgical they are — **none
of these has been tested; they are candidates, not findings:**

1. `overflow-anchor: none` on the corpus list container (or the scroll
   container that grows). Smallest possible change; directly targets the
   observed mechanism.
2. Reserve the list's height before the cards' second-stage layout lands,
   so the document does not grow above the anchor at all.
3. Extend the `_scrollInterruptGen` / capture-restore protection
   (`app.js:5538-5576`) to cover the currently-unprotected window O-6
   identifies (between an external baseline read and `refreshCorpus`'s own
   capture). This is the alternative hint the prior round recorded; note
   it treats the symptom's blast radius rather than the growth itself.

**Test-side, and separable from the app fix (O-7):** the test's
`to_have_count(20)` settle gate proves attachment, not layout. A gate that
waits for `documentElement.scrollHeight` to stop changing would close the
race in the test regardless of which app fix lands. Whether that is the
right *product* answer is a separate call — a real user scrolling while
the list inflates hits the same anchoring shift, and a test-only gate
would hide that. **Do not land the test-side gate alone and call mode C
fixed**; that would convert an observed product bug into a green test.

---

## Acceptance bar

No fix has passed its own falsification test yet. Any candidate must be
checked the same way O-4 checked the last one, plus what O-5 added:

- A/B against the **REAL** `test_corpus_reload_preserves_scroll_position`,
  both conditions run in the same session on the same machine, with n and
  failure counts reported as counts (see the sample-size bar above).
- The isolated instrument
  (`test_wizard_render_firing_after_baseline_creeps_it`) is **NOT** an
  acceptance signal any more — F-4 showed it reproduces an ordering the
  real test never takes. Keep it as negative-space coverage; do not gate
  on it.
- The captured spy timeline of any surviving failure must be inspected for
  shape, not just counted: a `y`-tracks-`h` `+N/+N` failure and a
  `300 -> 369` failure are different bugs (O-6 corruptions #2 and #1) and
  must not be pooled into one rate.

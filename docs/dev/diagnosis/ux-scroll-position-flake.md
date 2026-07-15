# Diagnosis — corpus-reload scroll position not preserved (ux flake)

> **Status:** mechanism **IDENTIFIED by instrument** (2026-07-15). The causal claim
> (async page-growth + scroll-anchoring racing `_restoreScrollY`) is strongly supported by
> a captured timeline; it is **not yet proven by a fix** (Phase 3 falsification pending).
> **Branch:** `fix/ux-scroll-position-flake`

<!-- Keep ## Observed (facts with artifacts) strictly apart from ## Inferred (hypothesis).
     Conflating them is the failure this document exists to prevent (charter C-7). -->

---

## Symptom

`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_corpus_reload_preserves_scroll_position`
scrolls the Corpus tab to y=300, calls `refreshCorpus()`, and asserts the restored
`window.scrollY` still equals 300. Intermittently it does not. Under `--reruns 2` it mostly
passes on a retry (green), ~10-20% of attempts fail. User-facing report: "accepting a bullet
scrolls me to the top."

---

## Observed

Facts with artifacts behind them. Nothing here is a deduction.

### O-1. Reproduces on HEAD at ~12-17% per attempt, under CPU load

`scratchpad/repro_scroll_phase0.sh`: 24 runs, 7/8 cores saturated → **3 FAIL / 24 = 12.5%** on
HEAD `98da67a`. `scratchpad/capture_scroll_phase1b.sh`: 12 runs, 4/8 cores → **2 FAIL / 12 =
16.7%**. Consistent with the ledger's "~10-20%". Needs CPU load to fire (matches the test's own
"under end-of-suite CPU load" note); a single no-load run passes.

### O-2. The failure value is NONDETERMINISTIC — multiple modes

The ledger recorded one identical signature `369 -> 25423` ("deterministic, not jitter"). Not
what reproduced. Observed failing assertions across runs:

| mode | failing assertion | values |
|---|---|---|
| A | `after == before`                    | `300 -> 0`     (restored to top) |
| B | `before > 0` ("test setup … scroll") | `before = 0`   (setup scroll never stuck) |
| C | `after == before`                    | `300 -> 369`   (landed just below) |
| D | `after == before`                    | `369 -> 25423` (the ledger's value; landed at bottom) |

Load level shifts which mode appears (7-core saturation gave A/B/C; 4-core gave D). A single
deterministic culprit lands at one value; four values = a **race with a variable-timing
scroller**.

### O-3. When the setup scroll sticks, `before` is 300 OR 369 depending on timing

`before=300` when the wizard's residual scroll has settled; `before=369` when it is still
settling (see O-5/O-6). So 369 is a *landing position of an async scroller*, not a corrupted
read of the set value.

### O-4. The first instrument was inert — caught by dumping on EVERY run, not just failures

Instrument v1 passed `"() => { … }"` to `page.add_init_script`, which injects the string as-is
and **does not call it** — an uninvoked arrow function. `window.__scrollSpy` stayed undefined;
every dump read `0 events`, including runs that obviously scrolled. A fail-only dump would have
shown "0 events" and read as "nothing scrolls." The **always-dump** (`SCROLL_SPY_ALWAYS=1`)
exposed the inert instrument (0 events on passing runs that visibly scrolled). Fixed to an IIFE
`"(() => { … })()"`; v2 records. *(This is the C-7 "scope the instrument wider / verify it
captures" clause earning its keep — a narrow or unverified instrument hides the culprit.)*

### O-5. The instrument NAMES two async scrollers (source-tagged stacks)

- `#panelJD.scrollIntoView({behavior:'smooth', block:'start'})` fired from **`_wizardRender`
  (`static/app.js:6911`)**, called by `wizardInit` (`:6809`) during user-select. `_wizardRender`
  ends by smooth-scrolling the active step's panel into view. Its residual animation settles the
  page at #panelJD's position (~y=369) — this is the `before=369` in O-3.
- **`_restoreScrollY` (`static/app.js:5492`)** — `requestAnimationFrame(() => window.scrollTo(0, y))`
  — observed firing `scrollTo(0,0)`, `scrollTo(0,300)` [the test], and `scrollTo(0,369/25423)`. It
  faithfully restores whatever `_captureScrollY` (`:5490`) grabbed; the grabbed value is often a
  transient.

### O-6. The corpus page height grows asynchronously to ~27000px; scroll-anchoring moves scroll by ~the delta

Captured timeline of one full run (`capture_scroll_phase1c_pytest.log`, widened spy with
`h`=`documentElement.scrollHeight`; this run happened to PASS at 369 but shows the whole
excursion the failures ride):

```
t=2139  y=0      h=1206   scrollIntoView #panelJD (smooth)  <- _wizardRender:6911
t=2604  y=59     h=959    scroll-event   (list -> "Loading..." placeholder; page shrank)
t=3189  y=59     h=2101   window.scrollTo(0,0)              <- _restoreScrollY app.js:5492
t=3314  y=0      h=2101   window.scrollTo(0,300)            <- test
t=3330  y=300    h=2101   scroll-event
t=3469  y=369    h=2170   scroll-event   (wizard scrollIntoView residual)   <- `before` read
t=4141  y=25080  h=25980  scroll-event   (NO scroll API — page BALLOONED 2170->25980; scroll moved ~+23000)
t=5444  y=25423  h=27224  window.scrollTo(0,369)            <- _restoreScrollY app.js:5492 (fires LAST -> wins)
t=5590  y=369    h=27224  scroll-event                       <- `after` read -> PASS
```

Two load-bearing facts:
- **The page height balloons from ~1200 to ~27000px** as the 20 experience cards + the
  fire-and-forget editors (`refreshSummaryVariants` / `refreshSkillsEditor` /
  `refreshEducationEditor` / `refreshCertificationsEditor` / `refreshMergeSuggestions`,
  `static/app.js:3616-3657`) finish rendering — *after* the test's `to_have_count(20)` gate.
- **The jump to ~25080 is a bare `scroll-event` with no `scrollTo`/`scrollIntoView`/`focus`
  behind it**, and it tracks the height delta almost exactly (Δh≈23810, Δy≈24711). That is
  browser **scroll-anchoring** (content inserted above the anchor pushes scroll down to keep the
  anchored element in place), not an app scroll call — which is exactly why no code line owns it.

### O-7. Pass vs fail = whether capture/restore pins scroll before or after the anchor-jump

In the O-6 run, `_restoreScrollY(369)` fired *after* the anchor-jump (t=5444 > t=4141) and won →
`after=369` → pass. In a mode-D failure (`capture_scroll_phase1b`, `369 -> 25423`), `_captureScrollY`
grabbed the post-jump value and `_restoreScrollY` restored `scrollTo(0,25423)` as the last event →
`after=25423` → fail. The outcome flips on the relative timing of the async anchor-jump and the
single-rAF capture/restore. Modes A/B/C are the same race resolving at different heights/times.

---

## Falsified

### F-1 — The ledger's "identical `369 -> 25423`, deterministic path, not jitter"

**Not the whole truth.** `369 -> 25423` is one of at least four modes (O-2), load-dependent, and
the value is a *race outcome* (the anchor-jump landing), not a fixed code path. A fix that only
makes `25423` stop appearing would leave the race (and modes A/B/C) alive.

### F-2 — "A late `scrollIntoView`/focus during corpus render scrolls to the bottom" (the ledger's leading suspect)

**Falsified for the bottom-jump.** The wide spy hooks `scrollIntoView`, `scrollIntoViewIfNeeded`,
and `focus`; the 25080/25423 jump shows as a **bare `scroll-event`** with none of them preceding
it (O-6). The bottom-jump is scroll-anchoring on async page growth, not an app scroll call. (The
`_wizardRender` scrollIntoView is real and does matter — but for the `before=369` residual, not
the bottom-jump.)

---

## Inferred

> **HYPOTHESIS (strongly supported by O-6/O-7, not yet proven by a fix).**

The flake is a race between (a) the asynchronous corpus-render page-growth and the browser
scroll-anchoring it triggers, and (b) `refreshCorpus`'s single-`requestAnimationFrame`
capture/restore (`_captureScrollY`/`_restoreScrollY`). Because the height keeps changing for
hundreds of ms after `_renderCorpusList()` (the fire-and-forget editors resolve late), one rAF is
too early: a later anchor-jump overrides the restore, or `_captureScrollY` samples a transient.

Candidate fix layers (the fix must address the RACE, not a single value):
- **Disable scroll-anchoring on the growing container** (`overflow-anchor: none` on the page/list
  during the reload) — directly removes the bare-event jump that O-6 shows.
- **Restore after settle, not after one rAF** — re-assert the target scroll once the page height
  stops changing (e.g. a short height-stable check, or restore on each of the fire-and-forget
  completions).
- **A test-side wait for height to stabilize before asserting** — legitimate only if the
  production behavior is judged acceptable (it is NOT — the owner reported the jank), so the
  production fix is primary; a test-side settle may still be needed to make the guard honest.

Which layer is proven correct is decided in Phase 3 by the falsification below, not here.

---

## Falsification

**Run before shipping a fix.** The instrument already fails on HEAD (12-17%). The fix experiment:
apply the candidate fix and re-run the saturated/light-load loop (`scratchpad/capture_scroll_*.sh`)
+ the reruns-off CI proof.

- **If the flake stops** (bare `PASSED`, zero `RERUN`, across >1 CI run) AND the Phase-1
  instrument still shows the anchor-jump but the scroll no longer lands wrong → the indicted
  layer is confirmed.
- **If it persists** → the layer is wrong; the anchor-jump is not the (only) cause. Widen again.

A deterministic complement worth building: a browserless/forced test that renders the corpus,
grows the page height by a large delta while scroll is mid-page, and asserts scroll is preserved
— must fail on HEAD, pass on the fix. (Feasibility TBD; the browser race is timing-dependent.)

---

## The fix

_Only after the experiment above fails on HEAD and passes with the change. Not yet written._

---

## Acceptance bar

A bare `PASSED` with **no `RERUN`**, sampled across **more than one CI run**, AND the Phase-1
repro failing without the fix and passing with it. The fix must address the race (all modes),
not just make one value stop appearing. Green-with-a-retry does not count.

# Diagnosis — corpus-reload scroll position not preserved (ux flake)

> **Status:** the fix has **landed (2026-07-16, Chip 3)** at the capture/restore primitive
> (`_captureScrollY`/`_restoreScrollY`, `app.js:5480-5591`). Root cause was **deterministically
> proven for modes B and D in Chip 2** (O-10, O-11); mode A is **fixed on the strength of the
> shared-mechanism inference** with mode B (never separately real-world-captured); mode C is
> **scoped out** as a separate, unrelated hazard (see the updated note in
> [Inferred §3](#inferred) — its relationship to this fix changed slightly once the fix landed).
> O-10 and O-11 have **flipped**: both now assert and demonstrate the fix holds, on the exact
> same forced orderings that proved the defect (no test setup changed, only the pass criterion).
> A third regression test,
> `test_restore_scroll_y_ordinal_defers_to_newer_capture`, was added to close an outcome-level
> coverage gap the fix's own design review surfaced (the existing Chip 1a self-check for
> overlapping invocations only asserted the spy's attribution, never `window.scrollY`). See
> [The fix](#the-fix) for the mechanism and [Acceptance bar](#acceptance-bar) for what's
> confirmed vs. still open (CI, multi-run, `--reruns`-free evidence).
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
single-rAF capture/restore.

> **⚠ Corrected by stage 2.5 (see [Adversarial verification](#adversarial-verification-stage-25)).**
> Two claims in this O-7 are *inferred, not observed*, and were challenged: (1) "Modes A/B/C are the
> same race" is **falsified**
> ([F-3](#f-3--all-four-modes-are-one-anchoring-vs-restore-race-this-documents-own-o-7-inference)) —
> mode B is structurally pre-refresh; A/C are the wizard
> smooth-scroll residual + the FIRST `refreshCorpus`'s late `_restoreScrollY(0)`. (2) The mode-D
> failing run cited here dumped **0 events** (inert spy); "`_captureScrollY` grabbed the post-jump
> value" is *unobserved and code-inconsistent* — capture runs at `refreshCorpus` top (`app.js:3607`)
> **before** any growth. The mode-D excursion shown in O-6 comes from a run that **PASSED**.

### O-8. Two populated FAILING timelines exist — both are mode B (the test-SETUP scroll stomp), NOT the user-reported jump

Recovered from the phase-1d capture (`capture_scroll_phase1d_pytest.log`, in the 2026-07-15 recovery
bundle — the run the crashed session launched at 19:33Z and hung before reading). Exact counts (grepped,
not eyeballed): **12 runs, 8 PASS, 4 FAIL.** The 4 failures are **2 at test line 322** (`assert before
> 0` → `0 > 0`; mode B) **each with a populated spy dump**, and **2 at test line 304**
(`page.wait_for_selector("#panelCorpus", timeout=15_000)`; an unrelated panel-wait timeout under load).

**Scope this correctly — it is easy to overclaim:**
- This falsifies the stage-2.5 "**zero** populated failing timelines" finding **only for mode B**.
- **Mode B is `before=0`: the test's OWN setup scroll is stomped BEFORE its real assertion runs** (line
  322 is before `refreshCorpus()` at line 324). It is *not* the user symptom ("accepting a bullet
  scrolls me to the top" = an `after != before` jump = modes A/C/D). **phase-1d did NOT reproduce A/C/D
  at all** — those still have zero populated timelines and remain the real capture target.

Both mode-B dumps, height FLAT at h=1206 throughout (the run aborts at line 322, before the reload that
would grow the page — consistent with F-3's "mode B is pre-refresh"):

```
# failure #1 (7 events; failure #2 identical in shape, 6 events, stomp at +0.3ms)
t=2371  y=0    h=1206  scrollIntoView #panelJD (smooth)   <- _wizardRender app.js:6911
t=2641  y=233  h=1206  scroll-event
t=2777  y=305  h=1206  scroll-event
t=2894  y=305  h=1206  window.scrollTo [0,300]            <- the TEST's setup scroll
t=2906  y=301  h=1206  scroll-event
t=2907  y=301  h=1206  window.scrollTo [0,0]              <- app.js:5492 (_restoreScrollY rAF)  STOMP, +0.6ms
# test then reads `before` = 0  ->  assert 0 > 0  FAILS
```

**Directly observed** (in the event stacks): height never grows (h=1206) so **anchoring plays no role in
mode B** (confirms F-3); and a `scrollTo(0,0)` fires from `app.js:5492` (the `_restoreScrollY` rAF)
sub-millisecond *after* the test's own `scrollTo(0,300)`, stomping it to 0.

**Inferred, NOT in the log** (the stack shows only `app.js:5492`; there is no `refreshCorpus` /
`_captureScrollY` tag anywhere in the dump): *that this restore is a leftover from a prior `refreshCorpus`
which captured `y=0` earlier and whose rAF hadn't fired yet.* Plausible and matches skeptic 2's mode-B
prediction, but the scheduling call is not attributed by this instrument. Whether mode B shares a root
cause with A/C/D (the superseded-restore hypothesis in `## Inferred`) is likewise **inferred, not proven**.

**Second, distinct flake source:** the 2 line-304 failures are a `#panelCorpus` wait-timeout under CPU
load — harness robustness, unrelated to scroll. It inflates the apparent failure rate and will confuse
scroll-fix validation if not isolated.

### O-9. Chip 1b campaign: ONE populated FAILING timeline captured for mode D — the anchor-jump lands BEFORE the test's own `refreshCorpus()` call, not during it

**Campaign:** `scratchpad/capture_scroll_phase1b.sh` (7 busy-loop `python -c "while True: pass"`
workers on this 8-logical-core machine, matching O-1's "7/8 cores saturated" calibration), the
Chip-1a-hardened spy attached, no `--reruns` (confirmed off by default locally — only CI's `ux`
tier passes it). Zero-load sanity run passed (21s). First 12 saturated runs (3 calibration + a
batch of 5 + 4 more of a second batch of 5) all passed. **Run 13 (batch-2 run 5) failed** with the
exact ledger-original signature:

```
AssertionError: scroll position not preserved: 369 -> 25423
assert 25423 == 369
```

— i.e. `before=369` (mode C's landing value — the wizard `scrollIntoView` residual, per O-3/O-5)
and `after=25423` (mode D's landing value). Verified byte-for-byte against
`scratchpad/level_a.log`, `1 failed in 56.48s`. The dump (19 events, spy confirmed alive —
`_dump_scroll_spy`'s aliveness checks passed):

```
[scroll-spy] phase=after-refresh value=25423 before=369 -- 19 events:
  {'t': 1901.9, 'y': 0, 'h': 1206, 'active': 'BODY', 'source': 'scrollIntoView', 'el': '#panelJD.cb-panel', 'args': '[{"behavior":"smooth","block":"start"}]', 'by': 'at Element.scrollIntoView (<anonymous>:21:136) | at _wizardRender (http://127.0.0.1:54077/static/app.js:6911:22) | at wizardInit (http://127.0.0.1:54077/static/app.js:6809:3)'}
  {'t': 2213, 'y': 0, 'h': 959, 'active': '#topTabCorpus', 'source': 'refreshCorpus-enter', 'id': 1, 'openRC': [1]}
  {'t': 2217, 'y': 0, 'h': 959, 'active': '#topTabCorpus', 'source': '_captureScrollY', 'openRC': [1]}
  {'t': 2242.8, 'y': 59, 'h': 959, 'active': '#topTabCorpus', 'source': 'scroll-event'}
  {'t': 2848, 'y': 0, 'h': 2101, 'active': '#topTabCorpus', 'source': '_restoreScrollY-scheduled', 'scheduledDuring': [1]}
  {'t': 2876.4, 'y': 59, 'h': 2101, 'active': '#topTabCorpus', 'source': 'refreshCorpus-exit', 'id': 1, 'openRC': []}
  {'t': 2962.4, 'y': 0, 'h': 2101, 'active': '#topTabCorpus', 'source': '_restoreScrollY-fired', 'scheduledDuring': [1]}
  {'t': 2962.7, 'y': 59, 'h': 2101, 'active': '#topTabCorpus', 'source': 'window.scrollTo', 'args': '[0,0]', 'by': 'at window.<computed> (<anonymous>:19:100) | at http://127.0.0.1:54077/static/app.js:5492:38'}
  {'t': 3084.6, 'y': 0, 'h': 2101, 'active': '#topTabCorpus', 'source': 'scroll-event'}
  {'t': 3106.7, 'y': 0, 'h': 2101, 'active': '#topTabCorpus', 'source': 'window.scrollTo', 'args': '[0,300]', 'by': 'at window.<computed> (<anonymous>:19:100) | at eval (eval at evaluate (:302:30), <anonymous>:1:14) | at UtilityScript.evaluate (<anonymous>:309:18)'}
  {'t': 3238.1, 'y': 369, 'h': 2170, 'active': '#topTabCorpus', 'source': 'scroll-event'}
  {'t': 3477, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': 'refreshCorpus-enter', 'id': 2, 'openRC': [2]}
  {'t': 3548.5, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': '_captureScrollY', 'openRC': [2]}
  {'t': 3567.5, 'y': 25080, 'h': 25980, 'active': '#topTabCorpus', 'source': 'scroll-event'}
  {'t': 4094.9, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': '_restoreScrollY-scheduled', 'scheduledDuring': [2]}
  {'t': 4100, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': 'refreshCorpus-exit', 'id': 2, 'openRC': []}
  {'t': 4116.3, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': 'scroll-event'}
  {'t': 4116.4, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': '_restoreScrollY-fired', 'scheduledDuring': [2]}
  {'t': 4116.5, 'y': 25423, 'h': 27224, 'active': '#topTabCorpus', 'source': 'window.scrollTo', 'args': '[0,25423]', 'by': 'at window.<computed> (<anonymous>:19:100) | at http://127.0.0.1:54077/static/app.js:5492:38'}
```

**Directly observed, from the timestamps and values alone:**

- `id=1` (the tab-click's fire-and-forget `refreshCorpus`) captures at `y=0` (t=2217) and its own
  `_restoreScrollY` fires `scrollTo(0,0)` at t=2962.7 — this is the FIRST invocation's restore,
  unrelated to the test's assertion. It exits (`refreshCorpus-exit id=1`) at **t=2876.4**.
- The test's own setup `scrollTo(0,300)` fires at t=3106.7; the page settles at **y=369, h=2170**
  by t=3238.1 (this is the `before` the test reads — matches mode C's O-3 landing value).
- The page-height balloon and scroll-anchor jump (**h: 2170→27224, y: 369→25423**) happen
  **between t=3238.1 and t=3477** — i.e. strictly **before** `id=2` (the test's own explicit
  `refreshCorpus()` call, `app.js:461` in the test) is even entered, and **long after** `id=1`
  already exited (t=2876.4). The jump is **not bracketed by either tracked `refreshCorpus`
  invocation's lifecycle** — consistent with O-6's "bare `scroll-event`, no `scrollTo`/
  `scrollIntoView`/`focus` behind it" (confirmed again here: the t=3567.5 event immediately after
  is source `scroll-event` with no API call attributed) and consistent with O-6's attribution of
  the growth to "the 20 experience cards + fire-and-forget editors... finish rendering after the
  test's `to_have_count(20)` gate" — i.e. residual unawaited rendering, not either `refreshCorpus`
  call's own body.
- `id=2`'s `_captureScrollY` (t=3548.5) reads **`y=25423` directly** — the already-corrupted
  post-jump value, not a pre-jump value later overwritten. `id=2`'s `_restoreScrollY` (t=4116.5)
  then faithfully restores that same 25423 (matches O-5: "faithfully restores whatever
  `_captureScrollY` grabbed; the grabbed value is often a transient").

**Scope this correctly:** this directly resolves, **for this one captured instance**, what stage
2.5 flagged as "unobserved and code-inconsistent" in O-7 — that `_captureScrollY` grabs a
post-jump value. It does **not** retroactively validate the OLD phase-1b mode-D failure the
ledger originally recorded (that one logged 0 events, per O-7's correction, and remains
unverified) — this is a fresh, independently-captured instance, and it is **one sample**. Whether
every mode-D failure shares this exact shape (jump lands in the id=1-exit-to-id=2-enter gap) is
**not yet established** — that would need more captures or the Step-1 discriminating experiment,
not a claim from n=1.

### O-10. Deterministic reproduction: a superseded invocation's stale restore overwrites a legitimate later scroll (the mode A/B shape)

`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_restore_scroll_y_stale_invocation_overwrites_later_scroll`
(Chip 2). Forces, by construction rather than CPU-load timing, the exact ordering O-8's mode-B
captures showed: holds the tab-click's own fire-and-forget `refreshCorpus` (`loadCorpusIfReady` ->
`refreshCorpus`, the real O-9 "id=1") open at its `/experiences` fetch — so it has captured
`scrollY` (the pre-scroll baseline) but not yet reached its own `_restoreScrollY` call — then sets
the scroll position a real user/test wants, THEN releases the held fetch so the stale invocation
completes and fires its now-superseded restore.

3/3 runs, identical:
```
before=59 after=0
```
(`before` reads 59, not the requested 300, because the page hadn't grown to its full 20-card
height yet when `scrollTo(0,300)` ran — the held-open fetch blocks `_renderCorpusList()` too, not
just the restore; `window.scrollTo` clamps to the max scrollable offset. This doesn't affect what's
being demonstrated: whatever the legitimate current position is, the stale invocation's restore
overwrites it.) `after=0` is exactly the near-0 value the stale invocation captured at its own top,
before the test ever scrolled — directly matching O-8's mode-B shape (`before=0` after an explicit
`scrollTo(0,300)`, `_restoreScrollY(0)` firing from `app.js:5492` "sub-millisecond after the test's
own `scrollTo(0,300)`, stomping it to 0").

**Directly observed:** the real `refreshCorpus`/`_captureScrollY`/`_restoreScrollY` (`app.js:3600`,
`3607`, `5490-5493`), unmodified, reproduce the mode-B overwrite on demand, 3/3, once the invocation
ordering O-8 already showed in the wild is forced instead of awaited. This does not reproduce mode
A's exact `300 -> 0` signature (the clamp changes `before`'s value) — see
[Falsification](#falsification) for what remains open for mode A specifically.

### O-11. Deterministic reproduction: `_restoreScrollY` has no protection against growth landing in the next frame (the mode D shape)

`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_restore_scroll_y_loses_to_post_restore_growth`
(Chip 2). Calls the real `_captureScrollY()` / `_restoreScrollY(y)` (`app.js:5490-5493`) directly,
then schedules a synthetic page-growth (a 20000px filler prepended to `<body>`, the same "content
inserted above the anchor pushes scroll down" shape O-6 identified) in the animation frame
immediately after `_restoreScrollY`'s own — same-frame `requestAnimationFrame` callbacks fire in
registration order, so registering the growth callback AFTER calling `_restoreScrollY(y)`
deterministically lands it one frame later, matching O-9's observed ordering (growth landing after
id=1's restore had already fired and exited) without depending on wall-clock timing at all.

3/3 runs:
```
run 1: before=300  after=20300   (delta = +20000, exactly the filler height)
run 2: before=369  after=45423   (delta = +45054 = 20000 [filler] + 25054)
run 3: before=300  after=20300   (delta = +20000, exactly the filler height)
```

**Directly observed:** in every run, `after` moves by at least exactly the synthetic filler's
height — the restore's one-shot `scrollTo(0, y)` is silently overtaken by scroll-anchoring
compensating for content inserted after it fired, with nothing to correct it afterward. Runs 1 and
3 show a clean 1:1 match (delta == filler height exactly); this is `_restoreScrollY`'s defect in
isolation.

**Unplanned secondary observation (run 2), flagged but not chased further this chip:**
`before=369` — not 300 — reproducing O-3's mode-C landing value spontaneously, with no CPU
saturation at all, purely from this test's own `page.evaluate()` round-trip timing. And the delta
(45054) decomposes as `20000` (this test's own filler) `+ 25054` — matching O-9's own real-world
anchor-jump delta (`25423 - 369 = 25054`) almost exactly. This suggests the real app's
fire-and-forget children's background growth (O-6's "20 experience cards + the fire-and-forget
editors... finish rendering") may fire on most or all runs regardless of load, and what CPU
saturation actually widens is the timing window during which a read/capture can land inside it —
consistent with, not contradicting, the existing evidence, but this is **one incidental data
point, not a systematic finding**; it was not reproduced deliberately or investigated further.

**Scope this correctly:** this proves the primitive itself — `_captureScrollY`/`_restoreScrollY`
as shipped — is unsound against post-restore growth, in general and on demand. It does not by
itself prove every real-world mode-D failure takes this exact path (O-9 remains the only
real-world capture); it proves the mechanism O-9 described is real, general, and not a one-off
artifact of that single captured run.

**Third corroboration, incidental:** this test's own FIRST draft did not wait out the
tab-click's `refreshCorpus` (id=1) before setting its baseline, and was itself intermittently
flaky when run after other tests in the file — `before=0` instead of `>0` — i.e. its own
setup accidentally raced the O-10 mechanism (id=1's stale restore) rather than isolating the
growth mechanism this test targets. Fixed by waiting for id=1's `refreshCorpus-exit` (spy
tagged) plus one settle window before proceeding — same discipline
`test_scroll_spy_attributes_overlapping_refresh_corpus_calls` already established. Kept here
as a data point, not a new finding: a THIRD independent context (this test's own unguarded
setup, distinct from O-10's deliberate forcing and O-11 run 2's incidental `before=369`) hit
a capture/restore race without trying to. These races are not narrow, hard-to-hit edge cases.

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

<a id="f-3"></a>
### F-3 — "All four modes are one anchoring-vs-restore race" (this document's own O-7 inference)

**Falsified by stage 2.5** (2 of 3 skeptics, independently). Mode B (`before=0`) is *structurally
impossible* under the anchoring mechanism: the test latches `before` at line 319 and asserts it at
line 322 — **before** `refreshCorpus()` is called (line 324) — so the second reload's growth/anchoring
cannot cause it. Mode B is an explicit `scrollTo(0,0)` from `_restoreScrollY` (`app.js:5492`) firing
~1ms after the test's `scrollTo(0,300)` over **flat height** (a stale, late restore from the tab-click's
earlier `refreshCorpus`). Mode C is the `_wizardRender` smooth-scroll residual captured into scroll.
**Only mode D involves anchoring.** Consequence: `overflow-anchor:none` addresses at most mode D and
leaves A/B/C — and at ~12-17%/attempt under `--reruns 2` would likely go green anyway (the C-7 masking
trap). The unifying defect is mechanism-agnostic: **`_captureScrollY` samples a moving target.**

---

## Adversarial verification (stage 2.5)

A 3-skeptic panel (Workflow `verify-scroll-flake-diagnosis`, run `wf_af5e4bda-f16`; journal under the
prior session's `subagents/workflows/`) was tasked to **refute** the O-6/O-7 causal claim. It ran to
completion; the authoring session hung before reading it. Verdicts:

| skeptic | survives? | core objection |
|---|---|---|
| `a239a987` | **no** | Four modes ≠ one mechanism; mode B is pre-refresh; the unifying fact is "capture samples a moving target" — anchoring is 1 of ≥3 perturbers. |
| `a46d0437` | **no** | Mode-B/C timelines refute the anchoring frame directly (flat height, explicit `scrollTo(0,0)`); only mode D matches; `overflow-anchor:none` and restore-after-settle each leave real modes and can pass for the wrong reason. |
| `a4b5a2fb` | yes\* | \*"survives" for the EXCURSION only — but concedes the failure ordering is observed on **zero failing runs**; every rich timeline is a PASS; the one mode-D failure logged 0 events. |

**Unanimous, load-bearing finding:** *no failing run has ever been captured with a populated spy
timeline.* The mode-D mechanism is extrapolated **entirely from passing runs**; the single instrumented
mode-D failure recorded `0 events` (the inert-spy O-4 trap, still live for that run).

**Fix-risk the panel flagged (all three):**
- `overflow-anchor:none` targets only mode D (the balloon jump), and even that is *unproven* — mode D
  was never captured with a working spy. Modes A/B/C persist. At ~12-17%/attempt under `--reruns 2`, a
  fix that removes only the ~1-in-4 balloon mode drops the residual rate low enough that fail-fail-pass
  reruns mask it as a bare `PASSED` — **green for the wrong reason** (C-7 "green-with-reruns ≠ evidence").
- `restore-after-settle` can pass by outlasting the *wizard* smooth-scroll (an unrelated perturber),
  not by fixing the race — and it makes the mode-B stale-late-restore stomp *more* likely, not less.

**Panel's required next step (before any fix):** capture ≥1 FAILING after-refresh run **with a populated
timeline**. First fix the spy's own inertness (assert `__scrollSpy` is defined at dump time; dump on
failure unconditionally — drop the `SCROLL_SPY_ALWAYS` dependence for fails). Tag `_captureScrollY` /
`_restoreScrollY` (`app.js:3607` / `5490-5493`) and the FIRST-vs-SECOND `refreshCorpus` restore
separately. Hook `window.scrollBy` + `Element.prototype.scroll/scrollTo/scrollBy` so "bare scroll-event"
is a true residual bucket. phase-1d (the authoring session's last run, `b08jqefpz`) reproduced **4/12**
failures but did **not** close this gap — still no confirmed populated failing timeline.

> **⚠ Updated by the 2026-07-15 recovery.** The phase-1d output the authoring session hung before
> reading was recovered and read (see O-8). It partially narrows the gap: **the 2 mode-B failures it
> reproduced carry populated timelines** and refute anchoring for mode B by direct observation. But the
> "zero populated failing timelines" finding stands **for modes A/C/D** — the user-facing `after !=
> before` jump — which phase-1d did NOT reproduce. Those remain the open capture target; mode B's link
> to them is still inferred, not proven. (Also: 2 of phase-1d's 4 failures were an unrelated
> `#panelCorpus` wait-timeout, not scroll — a second flake source to isolate.)

> **⚠ Updated by the 2026-07-16 Chip 1b campaign.** A saturated capture campaign closed the gap
> **for mode D specifically** — see [O-9](#o-9-chip-1b-campaign-one-populated-failing-timeline-captured-for-mode-d--the-anchor-jump-lands-before-the-tests-own-refreshcorpus-call-not-during-it):
> one populated mode-D failing timeline (`369 -> 25423`) is now captured and shows the anchor-jump
> landing before the test's own `refreshCorpus()` call, not during it. This is **one sample**, mode
> D only — the "zero populated failing timelines" finding still stands **for modes A and C**, which
> Chip 1b's campaign did not encounter before stopping (per plan, on first A/C/D capture).

> **⚠ Updated by Chip 2 (2026-07-16).** The panel's core objection was that the mechanism was
> "extrapolated entirely from passing runs." That gap is now closed by a different route than the
> panel's own prescribed next step (capture more failing runs): **deterministic reproduction** using
> the real `_captureScrollY`/`_restoreScrollY`, not more wild captures — see
> [O-10](#o-10-deterministic-reproduction-a-superseded-invocations-stale-restore-overwrites-a-legitimate-later-scroll-the-mode-ab-shape)/[O-11](#o-11-deterministic-reproduction-_restorescrolly-has-no-protection-against-growth-landing-in-the-next-frame-the-mode-d-shape)
> and the rewritten [Inferred](#inferred) below. The panel's fix-risk warnings stand: `overflow-anchor:
> none` alone still only addresses mode D; the capture/restore layer is now the explicitly indicted
> fix target for A/B/D together, matching skeptic `a239a987`'s original framing ("capture samples a
> moving target") — now proven rather than inferred.

---

## Inferred

> **Upgraded (Chip 2, 2026-07-16): the mechanism for modes B and D is no longer a hypothesis**
> **extrapolated from passing runs — it is directly, repeatably demonstrated (O-10, O-11) using**
> **the shipped `_captureScrollY`/`_restoreScrollY`.** What remains genuinely inferred: that every
> *real-world* mode-A/B/D failure takes exactly this path (only B and D have a real capture; A
> does not), and mode C's relationship to the other three (it doesn't have one — see below).

The unifying defect, stated precisely: **`_captureScrollY()`/`_restoreScrollY(y)`
(`app.js:5490-5493`) have no concept of "have I been superseded" or "is the page still
settling."** `_captureScrollY` trusts `window.scrollY` as ground truth the instant it is read,
whatever transient state the page is in; `_restoreScrollY` fires exactly one
`requestAnimationFrame`-deferred `scrollTo(0, y)` and never re-checks that `y` is still the right
target or that its effect survives the next frame. Two independent failure shapes fall out of that
one gap, plus one unrelated hazard that merely looks similar:

1. **Restore-side (modes A and B): a stale, superseded invocation wins by finishing last.** The
   FIRST `refreshCorpus` (the tab-click's fire-and-forget call) captures `scrollY` near 0 at its
   own top, then awaits a fetch. If its `_restoreScrollY(0)` doesn't fire until AFTER something
   else (the test's own `scrollTo(0,300)`, or a second invocation) has established a real, current
   position, the stale restore silently overwrites it — nothing marks the first invocation as
   superseded. **Directly demonstrated, 3/3, in O-10.** O-8 independently captured this exact shape
   twice in the wild for mode B (`scrollTo(0,0)` from `app.js:5492` firing "sub-millisecond after
   the test's own `scrollTo(0,300)`"). Mode A (`300 -> 0`, no populated real capture yet) is
   inferred to share this mechanism by direct code inspection — same call site, same lack of
   invalidation — but that inference has not been closed by a real-world capture, only by O-10's
   forced analog.
2. **Capture-side (mode D): capture reads an already-corrupted value.** Browser scroll-anchoring
   on the corpus page's async ~27000px growth (O-6) can land squarely in the gap between one
   invocation exiting and the next one's `_captureScrollY` running (O-9), or in the frame
   immediately after any `_restoreScrollY` fires (O-11) — either way, whatever `_captureScrollY`
   reads next is already wrong, and `_restoreScrollY` then faithfully preserves that wrongness.
   **Directly demonstrated, 3/3, in O-11**, using the same 20000px-filler-after-restore shape that
   mirrors O-6's real growth. O-9 independently captured this exact shape once in the wild.
3. **Mode C is NOT this defect — it's a different, unrelated hazard.** `before=369` comes from
   `_wizardRender`'s own `scrollIntoView({behavior:'smooth'})` (`app.js:6911`) — wholly outside
   `refreshCorpus` — still mid-animation when the test's `scrollTo(0,300)` + immediate read races
   it (O-3, O-5). `refreshCorpus`'s capture/restore isn't wrong in mode C; the *baseline* it's
   asked to preserve is already wrong before `refreshCorpus` is ever called. O-11's run 2 (an
   unplanned, non-CPU-saturated recurrence of `before=369`) corroborates this is a live,
   easily-triggered race, not a load-only artifact — but it was not investigated further this chip
   (see [Falsification](#falsification) for why a CPU-saturated campaign to chase C specifically
   was not run).
   > **⚠ Precision update, Chip 3.** Before the fix, mode C "had nothing to do with
   > `refreshCorpus`'s capture/restore" in the strongest sense — it didn't touch either function at
   > all. That's no longer quite true: [the fix](#the-fix)'s mechanism #2 wraps
   > `Element.prototype.scrollIntoView` (among other explicit scroll APIs) as an invalidation
   > signal, and `_wizardRender`'s call is one of them, so it can now cause an unrelated pending
   > `refreshCorpus`/`loadComposition` restore to abandon. This is one-directional and
   > conservative — it can only make a restore defer, never misfire — and it neither fixes nor
   > worsens mode C's own defect (the test's baseline read still races the wizard's animation the
   > same way). The precise statement post-fix: mode C **doesn't share the defect**; it **does now
   > participate as a harmless, conservative invalidation signal** in the fixed mechanism.

A fix that addresses only anchoring (mode D) leaves A/B live; a fix that only cancels stale
restores (A/B) leaves D live. **The layer that covers both is the capture/restore primitive
itself** — invalidate/cancel a superseded invocation's pending restore (a per-invocation token,
matching the FIRST/SECOND tagging Chip 1a already added to the *instrument*) and stop trusting a
single `scrollY` read/write as final — e.g., re-assert after the page's own fire-and-forget
children and any pending layout have genuinely settled, not one rAF later. Mode C is a separate
concern for whoever picks up Chip 3 to explicitly scope in or out.

---

## Falsification

**Step 0 — close the evidence gap FIRST (charter C-7; the stage-2.5 requirement).** DONE for
modes B (O-8, 2 real captures) and D (O-9, 1 real capture); STILL OPEN for A and C (zero real
captures of a populated failing timeline for either, as of Chip 2).

**Step 1 — discriminating experiment. DONE, by a different and stronger method than originally
planned.** The original plan called for a CPU-saturated campaign neutralizing the wizard
smooth-scroll and re-counting mode frequencies — necessarily correlational (small per-mode
samples, load-dependent, consumes the same ~12-17%-per-attempt lottery Chip 1b already spent a
full campaign on for one D sample). Chip 2 substitutes two **deterministic** reproductions (O-10,
O-11) that call the real `_captureScrollY`/`_restoreScrollY` and force — by construction, not
luck — the exact orderings O-8 and O-9 observed. This answers the same question more directly:
**the capture/restore layer is indicted for both the restore-side (A/B) and capture-side (D)
shapes**, proven independently of each other and independently of the wizard-scroll perturber
(O-10/O-11 don't touch or depend on `_wizardRender` at all). Mode C is confirmed structurally
independent (Inferred §3) without needing a campaign — it doesn't involve `refreshCorpus`'s
capture/restore at either end.

**Step 2 — fix experiment. DONE (Chip 3), locally; CI confirmation still open.** Applied the fix
at the capture/restore layer (see [The fix](#the-fix)):
- **Re-ran O-10 and O-11 — both FLIPPED**, on the exact same forced orderings, no test setup
  changed (only the pass criterion, from `after != before` proving the defect to `after == before`
  proving the fix): 3/3 clean runs of the full regression file
  (`tests/ux/regression/test_20260708_busy_states_and_chip.py`, 11 tests), zero flakiness observed,
  `--reruns` not in play locally (confirmed off by default; only CI's `ux` tier passes it).
- **A third regression test was added**,
  `test_restore_scroll_y_ordinal_defers_to_newer_capture`, closing a gap the fix's own design
  review surfaced: the existing Chip 1a self-check for two overlapping invocations
  (`test_scroll_spy_attributes_overlapping_refresh_corpus_calls`) only asserted the spy's
  attribution bookkeeping, never `window.scrollY` — nothing before this test could have caught a
  bug in the ordinal check itself. Passes.
- **Re-ran the real flaky test under saturated load**
  (`scratchpad/capture_scroll_phase1b.sh`, 7 workers / 8 logical cores — the same calibration as
  O-1/O-9) — see [Acceptance bar](#acceptance-bar) for the tally.
- **Mode A and mode C scoping decision, made explicitly this chip:** mode A is fixed on the
  strength of its shared-mechanism inference with mode B (Inferred §1) — the same primitive-layer
  fix covers it without a separate real-world capture, since the fix is not mode-specific; mode C
  (the wizard-scroll race) is **out of scope**, confirmed structurally independent
  (Inferred §3, updated with a Chip 3 precision note on how it now interacts with the fixed
  mechanism) — not touched, and not folded into this bug.
- **Not yet met:** the CI, `--reruns`-free, more-than-one-run leg of the acceptance bar — that
  requires an actual CI run, not a local one. See [Acceptance bar](#acceptance-bar).

~~A deterministic complement worth building: a browserless/forced test that renders the corpus,
grows the page height by a large delta while scroll is mid-page, and asserts scroll is
preserved.~~ **Built — O-10 and O-11.**

---

## The fix

Three independent mechanisms, all scoped entirely inside `_captureScrollY`/`_restoreScrollY`
(`app.js:5480-5591`). All three call sites (`refreshCorpus` capture at `app.js:3607`,
`_loadCorpusDetail` at `:4839`, `loadComposition` at `:7036`) already did pure pass-through —
`const _scrollY = _captureScrollY(); ... _restoreScrollY(_scrollY);` — never inspecting the
captured value, so **none of the three call sites needed to change.**

1. **Invocation ordinal** (fixes modes A/B's "second invocation" shape — Inferred §1's "or a
   second invocation"). A module-level counter `_scrollCaptureOrdinal` increments on every
   `_captureScrollY()` call; the capture bundle carries `ordinal: <value at capture time>`.
   `_restoreScrollY` checks, on every settle-tick, whether its own `ordinal` still equals the
   *current* counter — if a newer capture has since happened (e.g. the next step of Compose's
   background auto-cascade re-entered `loadComposition()`), it abandons instantly. **No time
   budget at all** — this is what protects a long, multi-step reload cascade regardless of how
   many seconds it spans, and it's the mechanism that actually matches the owner's real-world
   report of being "bit with scroll and snap back multiple times in a single tailoring" on a large
   corpus where loading "sometimes takes well over 3-5 seconds."
2. **Explicit-scroll-API generation counter** (fixes O-10's exact shape — a deliberate reposition
   racing a stale restore with no second invocation involved). O-10 never makes a second capture;
   it holds one invocation open and sets `scrollTo(0,300)` directly, so mechanism #1 alone doesn't
   catch it. Wraps the explicit scroll-mutating APIs this app uses — `window.scrollTo`,
   `window.scroll` (a spec-level alias of `scrollTo`), `window.scrollBy`,
   `Element.prototype.scrollIntoView` — once at module load, so *any* call to them (test-injected
   JS, `_wizardRender`'s own smooth-scroll, anything) bumps a second counter,
   `_scrollInterruptGen`. `_restoreScrollY`'s *own* internal scroll-setting call bypasses this wrap
   (calls a saved reference to each function as it existed before this module's own wrap ran — in
   test contexts where the Chip 1a/Chip 2 spy's `add_init_script` wrap runs first, that saved
   reference is the spy's already-wrapped function, not the literal browser native — harmless, and
   necessary for the spy to keep seeing these calls). The capture bundle carries
   `scrollGen: <_scrollInterruptGen at capture time>`; a mismatch on any tick means something else
   explicitly repositioned scroll since capture — abandon.
   - *Why wrap explicit APIs rather than listen to the generic native `scroll` event:* per O-6/O-8,
     both the anchoring jump (mode D) and the passive height-shrink clamp this whole mechanism
     exists to counteract show up as a bare `scroll-event` with no API call behind them. A generic
     listener can't tell those apart from a deliberate reposition — and the passive case fires on
     essentially every normal reload, so a generic listener would make every restore look
     permanently stale.
   - *Known, deliberate cost:* zero prior production precedent in this codebase for wrapping global
     browser APIs (only the test suite's own diagnostic spy did this before); it's invisible
     action-at-a-distance — a future `scrollIntoView` call added anywhere won't visibly show it's
     now part of this protocol. The code comment at the wrap site says explicitly this is scoped to
     these calls for exactly this purpose, not a pattern to reach for elsewhere.
3. **Height-stability settle loop** (fixes mode D — O-11). Replaces the single
   `requestAnimationFrame(() => scrollTo(0,y))` with a bounded multi-frame loop: each tick (if not
   superseded per #1/#2) applies the target position via the bypassed-wrapper `scrollTo`, then
   compares `document.documentElement.scrollHeight` to the previous tick's (seeded from height
   recorded *at capture time*, so tick 1 has a defined baseline). Unchanged height increments a
   stability counter; changed height resets it. Stops after **4 consecutive stable ticks or a
   3000ms wall-clock cap** (`performance.now()`-based, not a frame count, since frame cadence
   degrades under the CPU load this bug needs to manifest).
   - *On the constants:* the gathered evidence for mode D specifically (O-6/O-9) shows growth
     completing in ~500-700ms on the 20-experience test fixture. 3000ms/4-ticks gives headroom for
     a larger real corpus for *this specific mechanism*. It is deliberately **not** stretched to
     5+ seconds to match the owner's reported end-to-end tailoring time — that multi-second,
     multi-snap-back experience is mechanism #1's territory (unbounded, no cap needed), and
     inflating mechanism #3's cap would only widen the window where a manual scroll gets fought,
     for a scenario mechanism #1 already covers.
   - *Named risk, accepted, not silently absorbed:* the settle loop widens the "fights a manual
     scroll" window from ~1 frame (today, pre-fix) to up to 3s, and unlike a single bad jump, it
     can re-clobber *every* scroll attempt made during that window, once per tick, until the loop's
     exit condition. Judged unavoidable (mode D's passive-perturbation signal is indistinguishable
     from a deliberate user scroll — see the "why wrap explicit APIs" note above) and bounded.

**Design review.** Before implementation, a second independent pass traced both O-10 and O-11
against this exact design line-by-line and confirmed: mechanism #2 alone flips O-10 (mechanism #1
is provably irrelevant to that specific test, since it only ever makes one capture); mechanisms
#2+#3 flip O-11, with the actual correction landing at tick 2 (well inside the test's 150ms wait);
the bypass-the-wrapper requirement in mechanism #2 is load-bearing, not cosmetic (getting it wrong
would collapse the settle loop to exactly one tick, everywhere — and O-11 would specifically catch
that regression); and no simpler alternative flips both tests unmodified (a bare "invalidate on
next capture" token doesn't touch O-10; a generic `scroll`-event listener can't distinguish a
passive perturbation, which fires on every normal reload, from a deliberate one). This review is
what surfaced the tick-1 height-baseline gap (resolved above) and the mode-C precision note
(Inferred §3).

---

## Acceptance bar

A bare `PASSED` with **no `RERUN`**, sampled across **more than one CI run**, with the spy **removed**,
AND the perturber demonstrably gone on a trajectory that **fails without the fix**. The fix must address
the moving-target capture (all modes), not just make one value stop appearing. Green-with-a-retry does
not count — and neither does green from a fix validated only against passing runs.

**Status, Chip 3 (2026-07-16):**

- **Deterministic evidence, confirmed:** O-10 and O-11 flipped from proving the defect to proving
  the fix, on the identical forced orderings, 3/3 clean runs of the full regression file (11
  tests) across 3 repeated invocations, zero flakiness, `--reruns` not in play locally. This
  satisfies "the perturber demonstrably gone on a trajectory that fails without the fix" — these
  are the same trajectories that failed on HEAD, now passing on the identical construction.
- **Local saturated-load evidence:** `scratchpad/capture_scroll_phase1b.sh`, 7 workers / 8 logical
  cores (O-1/O-9's own calibration), 24 iterations, log at
  `scratchpad/capture_scroll_phase3_postfix.log`. **Tally: 19 passed / 5 failed.** Every one of the
  5 failures was individually traced against its full spy dump (not pattern-matched by value alone
  — F-1 already warned that a repeated value is not proof of a repeated mechanism):
  - **1 failure** (run 5): `Page.wait_for_selector: Timeout 15000ms exceeded` waiting for
    `#panelCorpus` — the pre-existing, already-diagnosed **harness-load timeout** (O-8's "second,
    distinct flake source... unrelated to scroll"). Confirmed unrelated: this fix touches no
    tab-switch or panel-visibility code.
  - **4 failures** (runs 6, 15, 16, 22): `scroll position not preserved: 300 -> 369`. All four
    traced end-to-end via the spy dump, not assumed identical from the value alone. In every one:
    the test's own `before` read lands at 300; between that read and the test's own explicit
    `refreshCorpus()` call — both **test-side statements, nothing from the fix runs in between** —
    `_wizardRender`'s residual `scrollIntoView` animation (still settling from earlier in the same
    run) creeps the page from 300 to 369; `refreshCorpus`'s own `_captureScrollY` then correctly
    captures 369 (the only baseline it was ever given), and `_restoreScrollY`'s settle loop
    correctly, faithfully re-asserts 369 across multiple ticks even through the anchoring jump to
    ~25400 — capture/restore does exactly what it should with the baseline it's handed. **This is
    mode C** (Inferred §3), confirmed by full trace, not by matching the "369" value alone — one
    trace (run 22) additionally shows the fix's own mechanisms #1/#2 correctly protecting an
    *unrelated* legitimate `refreshCorpus` restore earlier in the same run (a first invocation's
    settle loop runs its full course and stops cleanly before the test's own `scrollTo(0,300)` —
    no interaction, no interference).
  - **Zero occurrences of modes A, B, or D** — the defect this fix targets — across all 24 runs.
  - **Precise, non-overclaiming conclusion:** the fix's target defect (the moving-target
    capture/restore primitive) is closed, 24/24. The *original* test
    (`test_corpus_reload_preserves_scroll_position`) is **not** fully green under this saturated
    load — it still fails at a broadly similar overall rate to before (~21% raw here vs. O-1's
    ~12-17%) — but every one of those residual failures is fully attributed to the two hazards
    explicitly scoped **out** of this fix (mode C; the harness timeout), not to a recurrence of
    what this fix closes. A reader should not take "the flake is fixed" from this entry — the
    correct claim is narrower and is the one made above.
- **Not yet met:** the CI leg specifically — "sampled across more than one CI run" requires an
  actual CI run, which doesn't exist until this branch is pushed/merged. That is out of this
  session's control to produce directly; it is the one part of this bar a local session cannot
  close on its own.
- **A concrete follow-on this campaign surfaces:** mode C's measured rate here (4/24, ~17%) is not
  negligible — a real user could still hit it in ordinary use (switch wizard steps, then quickly
  trigger something that reads/sets scroll). It remains explicitly out of scope for this branch
  (different mechanism, different fix — see the Inferred §3 precision note) but is real enough to
  be worth a deliberate, separate pickup rather than fading from view now that this chip is closed;
  see the Carry-forward ledger note.

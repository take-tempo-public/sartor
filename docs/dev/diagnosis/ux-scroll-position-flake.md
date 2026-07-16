# Diagnosis — corpus-reload scroll position not preserved (ux flake)

> **Status:** mechanism **NOT YET ESTABLISHED** (2026-07-15). The initial causal claim
> (async page-growth + scroll-anchoring racing `_restoreScrollY`) was **adversarially verified in
> stage 2.5 and did NOT survive** — 2 of 3 skeptics refute it; the 3rd's own objection guts it (see
> [Adversarial verification](#adversarial-verification-stage-25)). The claim is **widened**: the
> unifying defect is *`_captureScrollY` samples a moving target* driven by ≥3 async perturbers, of
> which scroll-anchoring is only the rarest (mode D). **Two populated FAILING timelines were recovered
> from the phase-1d capture (O-8) — but BOTH are mode B**, the test's own setup-scroll being stomped by
> a `_restoreScrollY(0)` (`app.js:5492`) over flat height (anchoring absent). **Mode B is not the
> user-reported symptom** (an `after != before` jump = modes A/C/D), and **A/C/D remain observed on ZERO
> failing runs.** The next step is to capture an `after != before` (A/C/D) failing timeline and target
> the moving-target capture — **not a blind anchoring fix** (charter C-7).
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
> same race" is **falsified** ([F-3](#f-3)) — mode B is structurally pre-refresh; A/C are the wizard
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

---

## Inferred

> **HYPOTHESIS — widened after stage 2.5; NOT yet proven, and the failure ordering is UNOBSERVED.**

The unifying defect is that **`refreshCorpus`'s single-`requestAnimationFrame` `_captureScrollY` /
`_restoreScrollY` samples and re-asserts a scroll value that is still being moved by multiple async
perturbers** — so the restored value is a transient. At least three perturbers are in play, only one of
which is scroll-anchoring:

1. the `_wizardRender` `scrollIntoView({behavior:'smooth'})` residual (`app.js:6911`) settling y toward
   369 — explains `before=369` (mode C);
2. the FIRST `refreshCorpus`'s own late `_restoreScrollY(0)` (`app.js:5492`) firing `scrollTo(0,0)` after
   the test's `scrollTo(0,300)` over flat height — explains modes A and B (the pre-refresh stomp);
3. browser scroll-anchoring on the async ~27000px page-growth — explains mode D only.

A fix that addresses only anchoring cannot cover modes A/B/C. The layer most likely to cover *all*
perturbers is the capture/restore itself — invalidate/cancel a superseded `refreshCorpus`'s pending
restore (a per-invocation token or an aborted rAF) and re-assert the target after height stabilizes,
rather than firing once. **This remains a hypothesis: the ordering that causes the failure has not been
observed** (every populated timeline is a PASS). Which layer is correct is decided by capturing a failing
timeline and then the falsification below — not here.

---

## Falsification

**Step 0 — close the evidence gap FIRST (charter C-7; the stage-2.5 requirement).** Before any fix
experiment, capture ≥1 FAILING after-refresh run with a **populated** spy timeline (instrument fixes
in [Adversarial verification](#adversarial-verification-stage-25)). Until a failing trajectory is
observed, the mechanism is inferred from passing runs and **no fix is justified**.

**Step 1 — discriminating experiment (no production fix yet).** Neutralize the wizard smooth-scroll
(or gate the setup `scrollTo(0,300)` until it settles) and re-run the saturated loop. If modes A/B/C
vanish and only D remains, anchoring is confirmed *for mode D* and refuted as the general cause; if
they persist, the capture/restore layer is indicted for all modes.

**Step 2 — fix experiment.** Apply the candidate fix at the layer Step 1 indicts and re-run the
saturated/light-load loop (`scratchpad/capture_scroll_*.sh`) + the reruns-off CI proof.
- **Confirmed** only if: the flake stops (bare `PASSED`, zero `RERUN`, across >1 CI run) AND the
  instrument shows the perturber still fires but scroll no longer lands wrong — **on a trajectory that
  FAILS without the fix.**
- **If it persists** → the layer is wrong; widen again.

A deterministic complement worth building: a browserless/forced test that renders the corpus, grows the
page height by a large delta while scroll is mid-page, and asserts scroll is preserved — must fail on
HEAD, pass on the fix. (Feasibility TBD; the browser race is timing-dependent.)

---

## The fix

_Only after the experiment above fails on HEAD and passes with the change. Not yet written._

---

## Acceptance bar

A bare `PASSED` with **no `RERUN`**, sampled across **more than one CI run**, with the spy **removed**,
AND the perturber demonstrably gone on a trajectory that **fails without the fix**. The fix must address
the moving-target capture (all modes), not just make one value stop appearing. Green-with-a-retry does
not count — and neither does green from a fix validated only against passing runs.

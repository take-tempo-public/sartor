# Diagnosis — `test_scroll_spy_attributes_overlapping_refresh_corpus_calls` gets 3 restore-fired events, expects 2

> **Status:** mechanism **PROVEN** — reproduced deterministically (O-10), with controls
> proving the instrument was live and the forced ordering achieved, and the leaked record's
> identity matching item 44's recorded CI artifact exactly. It is a **test-harness** defect:
> the settle gate clears the timeline on an event that, by construction, precedes the
> pending record it is meant to have drained. Three rivals falsified (F-1…F-4).
> What is **not** proven: that this is the *only* contributor to the CI failures — see
> "Still open" at the end.
> **Branch:** `fix/ux-scroll-spy-overlapping-refresh`
> **Item:** `docs/dev/work/items/0044-scroll-spy-overlapping-refresh-ci-flake.md`

<!-- Keep ## Observed (facts with artifacts) strictly apart from ## Inferred (hypothesis).
     Conflating them is the failure this document exists to prevent (charter C-7). -->

---

## Symptom

`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_scroll_spy_attributes_overlapping_refresh_corpus_calls`
fails `assert len(fired) == 2` with **3** `_restoreScrollY-fired` events. It has never been
seen to fail any other way. It fails only in CI; the local ux tier passes.

---

## Observed

Facts with artifacts behind them. Nothing in this section is a deduction.

### O-1. It fails at least one attempt on every CI run for which data exists (4 of 4)

Recorded in item 44's third update, obtained by grepping the job logs for `RERUN` rather
than trusting `gh pr checks`:

| Run | UX result | Attempts failed |
|---|---|---|
| PR #98 (30924821284) | FAIL | 3 of 3 |
| PR #99 run 2 (30943537217) | FAIL | 3 of 3 |
| PR #99 run 3 (30953100089) | reported `pass` | 1 of 3 |
| PR #99 run 4 (30955415008) | reported `pass` | 1 of 3 |

8 failed attempts in 12 ≈ **67% per attempt**. The two runs bucketed `pass` by
`gh pr checks` had each needed a retry — the C-7 rule-3 masking case. Only `--reruns 2`
(`.github/workflows/ci.yml`, ux tier) keeps this test nominally green.

### O-2. Neither failing PR could have caused it

PR #98 was docs-only. PR #99 touched no JS, no CSS, no Jinja template, nothing under
`ui_pages/` — verified in the item-44 filing with `git diff --name-only origin/main..HEAD`
(26 files, none in those categories). Both branches' local gate runs recorded
`pytest -m ux` at **137 passed, zero reruns**.

### O-3. `refreshCorpus`'s four `_restoreScrollY` call sites are mutually exclusive

`static/app.js:3715, 3723, 3731, 3744`. The first three are each the last statement of an
early-return branch (`_restoreScrollY(_scrollY); return;` — network-error, 404, and
`!res.ok` respectively); the fourth is the normal-path tail at the end of the function
body. There is exactly one `_captureScrollY()` per invocation, at `:3693`.

**Therefore one `refreshCorpus` invocation performs exactly one `_restoreScrollY` call**,
and three `-fired` events mean three distinct `_restoreScrollY` calls — not one invocation
firing twice.

### O-4. The spy's `-fired` record is emitted unconditionally, independent of the supersede guard

`tests/ux/regression/test_20260708_busy_states_and_chip.py:170-175` wraps
`window._restoreScrollY` and schedules its own
`requestAnimationFrame(() => rec('_restoreScrollY-fired', …))` at *schedule* time. The real
`_restoreScrollY`'s supersede check lives inside its own `tick()` (`static/app.js:5703`,
`if (ordinal !== _scrollCaptureOrdinal || scrollGen !== _scrollInterruptGen) return;`) and
abandons the scroll write — but it cannot suppress the spy's separate rAF.

**Therefore `-fired` means "a restore was scheduled", not "a scroll was applied."** A
correctly-superseded, correctly-abandoned restore still produces a `-fired` event.

### O-5. The spy's `_rcCounter` is not reset when the test clears the timeline

`_rcCounter` is a closure variable in `_SCROLL_SPY_NAMED_HOOKS_JS`
(`test_20260708_busy_states_and_chip.py:140`), incremented once per `refreshCorpus` call
(`:178`). The test clears only the event array — `page.evaluate("() => { window.__scrollSpy = []; }")`
at `:1879` — which does not touch `_rcCounter`.

The tab-click's own fire-and-forget `refreshCorpus` (`:1868`) runs before that clear and
therefore consumes **id 1**. The test's two deliberate invocations (`:1911-1912`) are
therefore **ids 2 and 3**.

### O-6. The extra event is the `scheduledDuring: [1]` row — not, as item 44 states, the late ordinal-2 row

The event table recorded from the PR #99 failure (item 44, second update):

```
t=470.9  ordinal 1  scheduledDuring [1]
t=518.8  ordinal 3  scheduledDuring [2, 3]
t=596.9  ordinal 2  scheduledDuring [2]
```

Combining with O-5 (the tracked invocations are ids 2 and 3) and with the test's own
control flow:

- `assert len(enters) == 2` at `:1930` **passes** in every recorded failure — the failure is
  always the next assertion, at `:1935`. So exactly two `refreshCorpus-enter` events are
  visible post-clear, and `id_a, id_b = 2, 3`.
- The `t=518.8` row (`scheduledDuring [2, 3]`) is invocation B scheduling while A is still
  open — expected.
- The `t=596.9` row (`scheduledDuring [2]`) is invocation A restoring last, alone, with a
  singleton open-set. This is **precisely what the test's final assertion requires**:
  `assert last_fired["scheduledDuring"] == [id_a]` (`:1947`).
- The `t=470.9` row carries `scheduledDuring: [1]`. Id 1 is neither `id_a` nor `id_b`.

**Therefore the anomalous event is the ordinal-1 / `scheduledDuring: [1]` row**, and
"ordinal 2 landing after ordinal 3" — which item 44 and the incoming handoff both name as
the anomaly — is the designed, asserted-for behaviour of this test. That characterisation is
a misreading of its own recorded table.

### O-7. The instrument's own header documents the exact ordering the hypothesis needs

`_SCROLL_SPY_NAMED_HOOKS_JS`'s header comment
(`test_20260708_busy_states_and_chip.py:123-131`), written by the Chip-1a session:

> `_restoreScrollY` … is a fire-and-forget `requestAnimationFrame` — `refreshCorpus` never
> awaits it, so its promise resolves (and this wrapper's `finally` marks the invocation
> closed) a full microtask-drain before the rAF actually fires.

So **`refreshCorpus-exit` is, by construction, strictly earlier than that same invocation's
`_restoreScrollY-fired`.** This is stated as a load-bearing design property of the
instrument — it is the stated reason the open-set is snapshotted at schedule time rather
than read at fire time.

`refreshCorpus-exit` is exactly the event the test gates its timeline clear on
(`:1875-1879`). The gate is therefore known — from the instrument's own documentation — to
open before the pending `-fired` record has been emitted.

This is a documented property of the code, not a claim about any particular run: it
establishes that the window exists, **not** that anything lands inside it. Whether the
clear actually falls inside that window on a failing CI run remains unobserved.

### O-8. Environment note — one unrelated cross-project python process is resident

`Get-Process` at the time of the local measurement found a single
`C:\Dev\spolia\.venv\Scripts\python.exe` (PID 64048, started 2026-08-01), and no orphaned
sartor `python app.py` / Werkzeug reloader pair. This is the same cross-project contention
vector recorded as O-14 in `docs/dev/diagnosis/ux-scroll-position-flake.md`. Recorded so the
local rate below is not read as having been measured on a quiet machine.

### O-9. It does not reproduce locally at all — 20/20 pass, against CI's ~67% per attempt

Falsification step 1, run this session. 20 serial invocations of the single test, one
pytest process each (fresh server + browser per run, matching how CI runs it once),
`--reruns` off, ~55s per run. Script and per-run log:
`scratchpad/loop_item44.sh`, `scratchpad/item44_local_rate.log`.

```
TOTAL: pass=20 fail=0 of 20
```

**If the local per-attempt rate matched CI's measured ~67%, twenty consecutive passes
would be a ~6e-7 event.** The rates are not the same population. Consistent with the two
prior local full-tier runs recorded in O-2 (137 passed, zero reruns, on both failing PRs),
and with `reference-ux-flake-ci-runner-not-local-load`'s finding that a *loaded* local box
passed 137/137 while dedicated CI runners failed 5 of 5.

This **rules out a plain code race** — a race in `refreshCorpus` / `_restoreScrollY` would
not be environment-selective to this degree — and promotes rival 3 (a CI-environment
factor; 4-core `ubuntu-latest` running a threaded Flask server, headless Chromium and
pytest concurrently, degrading rAF cadence) from a rival to the leading candidate.

It also means **the rate lottery is not available as an investigative tool here**, which is
why falsification step 2 forces the ordering by construction instead.

### O-10. The leak is reproduced deterministically, and the leaked record's identity matches the CI artifact exactly

Falsification step 2. `test_settle_gate_clears_the_timeline_without_leaking_a_pending_restore`
holds invocation 1's own `_restoreScrollY` rAFs for 800ms (wall-clock — see O-11), leaving
Playwright's polling cadence untouched, then runs the settle gate and reads the timeline.

Controls, all green — the negative-result trap is closed:

```
holdStats={'engaged': True, 'calls': 1, 'scheduledAt': 2196.7,
           'releasedAt': 3067.8, 'ticks': 26}   clearAt=2342.0
```

`engaged` proves a restore was actually pending; `releasedAt (3067.8) > clearAt (2342.0)`
proves the adverse ordering was genuinely achieved rather than assumed.

The leaked record:

```
{'t': 3009.1, 'source': '_restoreScrollY-fired', 'scheduledDuring': [1],
 'y': {'y': 0, 'h': 959, 'ordinal': 1, 'scrollGen': 1}, 'active': '#topTabCorpus'}
```

**`ordinal: 1`, `scheduledDuring: [1]` — byte-for-byte the identity of the anomalous row in
item 44's recorded CI timeline** (O-6). A restore scheduled before the clear lands after it,
in a timeline the caller is entitled to treat as empty.

This is a **test-harness defect**. No product code is implicated, which is why no product
change on either failing PR could have caused it (O-2).

### O-11. Headless Chromium here produces ~11-13 frames/sec, not ~60

Measured incidentally while building the probe, and load-bearing for it. The first version
of the hold counted **frames** (20). It never released: `ticks: 26` accumulated across the
two held chains — the spy's `-fired` rAF and the app's own `tick` loop, each with its own
20-frame budget — with neither reaching its count inside a 1s wait.

At ~60fps a 20-frame hold is ~330ms; at the observed cadence it is ~1.8s. **Frame count is
not a portable unit of delay here**, which is why the instrument holds by wall-clock instead.

Recorded because it also bears on rival 3: rAF cadence in this harness is already an order
of magnitude below display rate on an idle many-core dev box, so a 4-core CI runner sharing
cores between a threaded Flask server, headless Chromium and pytest has ample room to be
slower still — widening exactly the window O-7 describes.

---

## Falsified

### F-1 — "The anomaly is an ordinal-2 restore landing after ordinal 3" (item 44's own framing, inherited by the handoff)

**Falsified by O-6 (arithmetic on item 44's own recorded table) and confirmed by O-10.** The
late ordinal-2 row is what the test's final assertion explicitly requires
(`assert last_fired["scheduledDuring"] == [id_a]`, `:1947`) — invocation A is the one whose
fetch is deliberately held open, so it *must* restore last. The genuine extra is the
`ordinal 1 / scheduledDuring [1]` row, and O-10 reproduces precisely that record.

Consequence, and the reason this matters beyond this branch: a session starting from the
inherited framing would investigate `_restoreScrollY`'s supersede guard
(`static/app.js:5703`), which this evidence says is working correctly.

### F-2 — "A `scrollGen` / `ordinal` supersede-guard gap in `_restoreScrollY`" (rival 1)

**Falsified.** The probe that reproduces the leak schedules exactly **one** `_captureScrollY`
(`holdStats.calls == 1`), so there is no newer capture for the guard to defer to — the guard
cannot be implicated in a leak it has no opportunity to act on. The leaked record carries
`ordinal: 1, scrollGen: 1`, unchanged from capture.

### F-3 — "A third `_captureScrollY` from another call site" (rival 2)

**Falsified.** The leaked record is tagged `scheduledDuring: [1]` — it was scheduled inside
`refreshCorpus` invocation 1. `_loadCorpusDetail` (`static/app.js:4925`) and
`loadComposition` (`:7279`) are not implicated; no third capture occurs at all.

### F-4 — "It is a code race that a local loop can reproduce"

**Falsified by O-9** — 20/20 local passes against CI's ~67% per attempt. The rate lottery is
not an available instrument here; the ordering had to be forced by construction.

---

## Inferred

The **mechanism** is no longer inferred — it is reproduced (O-10) and its rivals are
falsified (F-1…F-3). What remains genuinely unproven is stated here and nowhere else.

1. **That this mechanism accounts for ALL of the CI failures, rather than most of them.**
   O-10 proves the leak is real and that its record is identical in identity to the one in
   the CI artifact. It does not prove no *second* contributor exists. The honest claim is:
   one mechanism is proven, reproduces the observed signature exactly, and is fixed here —
   not "the test can no longer fail for any reason." The CI leg of the acceptance bar is
   what tests that, and it is the only thing that can.
2. **Why the window opens on CI and effectively never locally** (O-9: 0/20 vs ~67%). Degraded
   rAF cadence on a 4-core runner is the leading explanation and O-11 shows cadence here is
   already ~11-13fps, so the mechanism is cadence-sensitive in the right direction. But no
   CI-side frame-cadence measurement has been taken, so this is a well-supported hypothesis,
   not an observation. It is also **not load-bearing for the fix**: the fix removes the
   window entirely rather than making it narrower, so it does not depend on knowing why the
   window is wider there.

---

## Falsification

**The experiment that settles it. Run before writing any fix.**

**Step 1 — measure the local per-attempt rate.** Loop the single test serially, no reruns,
~20 iterations. Only this test; looping the full 137-test ux tier costs ~30× for no extra
signal.

- **If it reproduces locally at anything near 67%:** capture the full timeline on a failing
  run and read the ordinal-1 row's arrival against the clear.
- **If it does not reproduce:** that gap is itself a finding — it isolates a CI-environment
  factor (rival 3) and rules out a pure code race. Not a dead end; proceed to step 2.

**Step 2 — force the ordering deterministically**, the method that closed O-10/O-11 in this
same family (`docs/dev/diagnosis/ux-scroll-position-flake.md`) rather than paying a rate
lottery. A probe that clears the timeline promptly after `refreshCorpus-exit` and records
whether an id-1 `-fired` row lands afterwards, tagged with both the clear's own timestamp
and the record's.

- **If the id-1 row appears after the clear:** the primary hypothesis is confirmed and
  rivals 1 and 2 are excluded by the same capture (the row's identity names its invocation
  and its call site).
- **If no id-1 row appears, or a row appears with an unexpected identity:** the hypothesis
  is **dead**. Stop. Do not fix. Widen the instrument and report.

---

## The fix

One line of gate, in the test harness. `_settle_and_clear_spy_timeline()` (extracted from
the inline block the overlapping test used, semantics preserved, so both it and the probe
share one gate) now waits for the tab-click invocation's **`_restoreScrollY-fired`** in
addition to its `refreshCorpus-exit` before clearing the timeline.

That is the event whose absence was the defect. Per O-7 the `-fired` record is emitted a
full microtask-drain *after* the invocation is marked closed, so `refreshCorpus-exit` could
never have signalled that the invocation had finished emitting. Waiting for the later of the
two closes the window rather than narrowing it — which is why the fix does not depend on
knowing why CI's window is wider than this machine's (Inferred §2).

**A/B against the probe, which fails by construction rather than by luck:**

| Arm | Result | Controls | Leaked record |
|---|---|---|---|
| Gate on `refreshCorpus-exit` (HEAD) | **FAIL** — subject assertion | `engaged`, hold 958.5ms ≥ 800ms | `ordinal 1, scheduledDuring [1]` |
| Gate on `-exit` **and** `-fired` | **PASS** | `engaged`, hold 904.0ms ≥ 800ms | none |

The A-arm fails on the **subject** assertion with every control green — not on a control,
and not vacuously.

**What was deliberately NOT done:**

- `assert len(fired) == 2` in `test_scroll_spy_attributes_overlapping_refresh_corpus_calls`
  is **unchanged**. No `>= 2`, no tolerance, no added sleep. The invariant is the point.
- The probe does **not** assert `releasedAt > clearAt`. That ordering is precisely what the
  gate decides, so the probe measures it and prints it rather than requiring it — requiring
  it would hard-code the pre-fix behaviour and the probe could never go green.
- No production code changed. `static/app.js` is untouched by this branch.

---

## Acceptance bar

- The deterministic probe fails on HEAD and passes after the change, on the identical
  construction, with no test-setup difference other than the pass criterion.
- The real test, looped locally with `--reruns` off, clean across the loop.
- `python -m scripts.gate` green; `pytest -m ux` 137 passed.
- **CI is the acceptance leg** — it is the only environment where this reproduces, so a
  local green proves nothing on its own here.
- **A bare `PASSED` does not count.** The ux job log must contain no `RERUN` for this test
  and no `[ux] rerun-rate alarm:` line naming it. `gh pr checks` reporting bucket `pass` is
  explicitly not sufficient — O-1 records two runs where it lied.
- `assert len(fired) == 2` must survive unchanged. Relaxing it to `>= 2`, or adding a sleep
  to outlast the extra event, converts a flaky-but-honest test into a permanently green
  meaningless one.

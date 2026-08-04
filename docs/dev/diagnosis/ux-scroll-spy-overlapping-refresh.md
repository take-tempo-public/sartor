# Diagnosis — `test_scroll_spy_attributes_overlapping_refresh_corpus_calls` gets 3 restore-fired events, expects 2

> **Status:** hypothesis only — a primary mechanism is named below and is strongly
> constrained by the recorded artifacts, but it has **not** been reproduced or observed
> directly yet. Nothing here licenses a fix.
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

---

## Falsified

_(Nothing yet.)_

---

## Inferred

**This is a hypothesis. It has not been reproduced.**

The test's settle gate is incomplete relative to its own stated intent. Its comment at
`:1871-1874` says the tab-click's fire-and-forget `refreshCorpus` "must settle BEFORE the
deliberate overlap below, and the timeline cleared, so it isn't conflated with the two
invocations this test is actually examining." But the gate it waits on (`:1875-1878`) is
`refreshCorpus-exit`, and invocation 1's spy `-fired` record is scheduled *before* that
exit while landing *one rAF after* it. If the clear at `:1879` lands in between, invocation
1's leftover `-fired` record drops into the freshly-emptied array and is counted as a third
event.

Under this reading the app's supersede guard is working correctly and no product code is
at fault — consistent with O-2 (no product change on either failing PR).

**What would have to be seen to know:** a run in which the ordinal-1 `-fired` record is
observed arriving *after* the clear timestamp, with the clear and the record ordered on the
same clock. The recorded artifacts constrain *which* event is extra (O-6) but say nothing
about *when the clear happened relative to it* — that ordering is entirely unobserved.

**Rivals that must stay alive** (C-7 rule 4 — an instrument scoped to the hypothesis will
confirm it by hiding these):

1. A genuine `ordinal` / `scrollGen` supersede gap in `_restoreScrollY` — cheap to
   conflate with the above, because O-4 means an abandoned restore still logs `-fired`.
2. A third `_captureScrollY` from a different call site — `_loadCorpusDetail`
   (`static/app.js:4925`) or `loadComposition` (`:7279`). The spy's own comment (`:160-163`)
   asserts neither is reachable from this test's action sequence; that assertion is
   inherited, not re-verified here.
3. A CI-environment factor with no local analogue — 4-core `ubuntu-latest` runners running
   a threaded Flask server, headless Chromium and pytest at once, which degrades rAF
   cadence. Supported in direction by O-2's local/CI split, unproven as a cause.

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

_Not yet. The experiment above has not run._

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

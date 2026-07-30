# Diagnosis — O-10 regression test (`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`) fails under resource contention

> **Status:** hypothesis only — a specific vector (pytest-xdist `-n 2` WITHIN the ux suite,
> reproducing a second concurrent Playwright/werkzeug pair in-process) reliably elevates the
> failure rate (2/8, 25%) above every other tested vector (0/8 each). This is a reproduction,
> not yet a proven mechanism. Do not build a fix on this dossier alone — see `## Falsification`
> for the next step that would actually prove it.
> **⚠ Corrected by the cross-item review (`fix/ux-scroll-flake-cross-item-review`,
> `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`).** `## Round 2`'s "looks more like
> the already-documented mode-C/D scroll-anchoring shape... bleeding into this test" inference is
> **falsified** — the document-level anchoring fix (`27d349b`, 2026-07-26) was already live and
> confirmed effective in every tree this branch's captures ran against (all dated 2026-07-30).
> That mechanism cannot explain the `291`/`306`/`273` landing values. The cross-item review
> proposes a different, untested hypothesis (a transient max-scroll clamp hit mid-render) and a
> concrete next instrument — read it before continuing this dossier.
> **Branch:** `fix/ux-restore-scroll-y-resource-contention`

---

## Symptom

`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_restore_scroll_y_stale_invocation_overwrites_later_scroll`
— the O-10 deterministic reproduction (forces exact event ordering by construction, not
CPU-load timing) — has failed 4 times prior to this branch, always under some form of
confirmed resource contention (O-12 ×2, O-14), and passed 5/5 in isolation every time it was
retried isolated. See `docs/dev/diagnosis/ux-scroll-position-flake.md` O-12/O-14 and
`docs/dev/work/items/0029-o10-regression-test-resource-contention.md` for the full prior
record. The "resource contention" vector as previously observed is not one thing: O-12
occurrence 1 was deliberate `pytest tests/ux -n 2`; O-12 occurrence 2 was two orphaned
same-project `python app.py` processes confounded with an overlapping full-suite pytest run;
O-14 was genuine concurrent load from an unrelated project's `python.exe` processes, with no
orphaned same-project server present. No dedicated campaign had previously isolated any ONE
of these vectors alone with enough samples to say anything about rate.

---

## Observed

**Campaign design.** Built `capture_contention_campaign.sh` (scratchpad, not committed) — a
loop harness distinct from every prior CPU-busy-loop script in this arc
(`scratchpad/capture_scroll_phase1b.sh` spawns `python -c "while True: pass"` workers; this
script does not). It supports three vectors, each run for 8 iterations of the target test
alone (`pytest tests/ux/regression/test_20260708_busy_states_and_chip.py::test_restore_scroll_y_stale_invocation_overwrites_later_scroll -v -s`):

- **`none`** — no load deliberately added by the campaign.
- **`concurrent-pytest`** — a genuine second `python -m pytest -m "not ux" -n auto` process
  (real CPU+IO work, not synthetic) started in the background and left running for the whole
  arm, matching O-12 occurrence 1 (deliberate `-n 2`/full-suite overlap) and O-14 (genuine
  concurrent real-project load) without depending on incidental cross-project timing.
- **`orphan`** — a real `python app.py --port 5099` (Werkzeug debug reloader on, matching
  production shape) started in the background, left completely idle (no requests sent to it)
  for the whole arm, matching O-12 occurrence 2's exact shape. Port 5099 was used, not 5000 —
  port 5000 was occupied for this entire campaign by the machine owner's own separate,
  off-limits e2e testing clone (confirmed with the owner, not touched or interacted with at
  any point).

**Important confound, disclosed rather than hidden:** the `none` arm was never a truly
isolated/load-free baseline — the owner's e2e clone (a real `python app.py` dev-server
process pair) was running on the machine for the entire campaign, all three arms included.
`none` is better read as "ambient contention only, nothing deliberately added by this
campaign" than as a clean control.

**Results (2026-07-30):**

| Vector | Result | Notes |
|---|---|---|
| `none` (ambient only) | **7 passed / 1 failed** / 8 | RUN 5 failed: `before=59 after=306` (identical failure family and landing value to O-12 occurrence 1's `before=59 after=306`). Durations 27-50s, unremarkable. |
| `concurrent-pytest` | **8 passed / 0 failed** / 8 | Real contention confirmed present: RUN 8 took 124s vs. the ~30-50s baseline range (a ~2.5-4x slowdown). Zero failures despite this. |
| `orphan` | **8 passed / 0 failed** / 8 | Real contention confirmed present: durations 35-102s (vs. ~30-50s baseline), roughly double by the end. Zero failures. One run (RUN 8) captured an unusual `before=300` (every other run in this whole campaign captured `before=59`) — still passed (`after=300`), logged as a data point, not chased further. |

Full logs: `scratchpad/contention_control_20260730.log`,
`scratchpad/contention_concurrent_pytest_20260730.log`,
`scratchpad/contention_orphan_20260730.log` (all gitignored, not committed).

**Net, stated plainly (first three vectors only):** 23/24 runs passed across the whole
campaign. The single failure landed in the arm with the *least* deliberately-added load, not
either of the two constructed contention arms — even though both constructed arms are
independently confirmed to have imposed real, measurable slowdown on the target test (up to
~2.5-4x baseline duration). This is the opposite of what "resource contention increases the
failure rate" would predict from this sample alone.

**Fourth vector, run after the above (owner-directed next step): `-n 2` WITHIN the ux suite
itself** — O-12 occurrence 1's actual literal vector, untested by the three arms above. Built
`capture_contention_n2.sh` (scratchpad, not committed). Scope note, disclosed rather than
silently narrowed: O-12 occurrence 1 ran the FULL `tests/ux` tree (106 tests) under `-n 2`;
running the full tree 8x would cost 40-80+ minutes, so this vector instead runs a FIXED
4-test subset from the SAME file under `-n 2` — the target test plus
`test_restore_scroll_y_loses_to_post_restore_growth`,
`test_restore_scroll_y_ordinal_defers_to_newer_capture`, and
`test_compose_reload_preserves_scroll_position` — so pytest-xdist's default `load` scheduling
genuinely distributes 2 tests per worker and produces a real second concurrent
Playwright/werkzeug pair in-process, at a fraction of the full-tree cost. This is a narrower
reproduction of O-12 occurrence 1's vector, not an exact replay.

Ran 8 iterations (two batches of 4, `python -m pytest <4 nodeids> -n 2 -v --tb=short`):

| Run | Target result | Other-subset result | Notes |
|---|---|---|---|
| batch1 RUN1 | PASSED | all passed | — |
| batch1 RUN2 | PASSED | `test_restore_scroll_y_ordinal_defers_to_newer_capture` FAILED | `#panelCorpus` visibility timeout (15000ms) — the SAME already-documented O-8 load-timeout failure class, unrelated mechanism |
| batch1 RUN3 | PASSED | all passed | — |
| batch1 RUN4 | PASSED | `test_restore_scroll_y_ordinal_defers_to_newer_capture` FAILED | same `#panelCorpus` timeout class |
| batch2 RUN1 | PASSED | `test_restore_scroll_y_ordinal_defers_to_newer_capture` FAILED | same `#panelCorpus` timeout class |
| batch2 RUN2 | **FAILED** | `test_restore_scroll_y_ordinal_defers_to_newer_capture` FAILED (same run) | target: `before=59 after=291`; same assertion/shape as O-12/O-14 |
| batch2 RUN3 | PASSED | all passed | — |
| batch2 RUN4 | **FAILED** | all others passed | target: `before=59 after=306` — **identical landing value to O-12 occurrence 1's own capture** |

**Tally: target 6 passed / 2 failed / 8 (25%)** — the highest failure rate of any vector
tested this branch, and the only vector (besides the ambient-only control's single incidental
failure) that reproduced the target mechanism at all. Both failures show the same
stale-invocation-overwrite shape and assertion as the historical record
(`docs/dev/diagnosis/ux-scroll-position-flake.md` O-12/O-14); `after=306` in batch2 RUN4 is
byte-identical to O-12 occurrence 1's own logged value. Full log:
`scratchpad/contention_n2_20260730.log` (gitignored, not committed).

**Secondary observation, not chased further:** `test_restore_scroll_y_ordinal_defers_to_newer_capture`
(a different test in the subset, exercising a related but distinct assertion — Chip 3's
outcome-level regression) failed 3 of 8 runs in this vector with a `#panelCorpus` visibility
timeout (`Page.wait_for_selector: Timeout 15000ms exceeded`) — the SAME failure class already
attributed to load in the original dossier's O-8 entry, not a new mechanism. Logged for
completeness; this is why `other_file_failures_only` in the raw tallies is nonzero even on
runs where the target itself passed.

**Net, updated:** the `-n 2`-within-suite vector (a second real concurrent Playwright/werkzeug
pair in the SAME process tree) is the first vector tested this branch that elevates the
target test's own failure rate above every other tested condition. Neither an external
unrelated pytest process nor an idle orphaned server reproduced it above ambient baseline;
genuine intra-suite worker concurrency did, at roughly the rate the historical record's
overall exposure count would suggest.

**Process hygiene, checked before and after:** confirmed via `Get-CimInstance Win32_Process`
that the only `python.exe app.py` processes present throughout were the owner's own e2e
clone's parent/child reloader pair (unrelated, never touched); confirmed via `netstat` that
port 5099 (this campaign's own orphan-vector server) was fully torn down — no leaked listener
— after each arm completed.

---

## Falsified

### F-1 — "generic resource contention (any CPU/IO load) elevates the failure rate"

**Narrowed, not fully falsified.** Two genuinely load-imposing vectors — a real external
`pytest -m "not ux" -n auto` process, and an idle orphaned same-project `python app.py` server
— produced 0/8 target failures each, despite confirmed real slowdown (up to ~2.5-4x baseline
duration) on the test itself. Whatever mechanism is at work is NOT simply "the machine is
busier" — the specific vector matters. The `-n 2`-within-suite vector, which does NOT impose
more raw CPU load than the other two (all three vectors run genuine concurrent work), is the
one that reproduces the failure. This rules out a pure CPU-scheduling-pressure explanation and
points toward something specific to a second concurrent Playwright/werkzeug pair (shared
process/thread resources, port allocation, SQLite access, or similar) rather than contention
in general.

---

## Inferred

**This is a hypothesis. It is not fact.**

The `-n 2`-within-suite vector's elevated rate (confirmed under `## Observed`) is consistent
with contention specific to running a SECOND concurrent Playwright/werkzeug pair in the same
process tree — GIL contention between two werkzeug-serving threads in different xdist worker
processes, two Chromium instances competing for CPU scheduling slices, or (less likely, since
each xdist worker gets its own `tmp_path`-scoped DB per the `ux_app` fixture) SQLite lock
contention — as opposed to generic external CPU/IO load, which this branch's other two vectors
showed does NOT reproduce it. This is still a **hypothesis about the vector class**, not a
mechanism: it does not explain WHY that specific contention would cause the assertion to fail,
only that it correlates with it far more than the alternatives tested.

The 150ms fixed wait (`page.wait_for_timeout(150)`, `test_20260708_busy_states_and_chip.py:1376`)
after releasing the held-open fetch, intended to "let the stale `_restoreScrollY`'s first tick
run (and abandon)", is a fixed-duration margin around an `requestAnimationFrame` callback. If
contention delays that rAF tick past 150ms, the test would read `scrollY` before the abandon
logic has had a chance to run — this is a plausible mechanism for ANY sufficiently-timed delay
regardless of its source, but it is unproven: no run in this campaign captured evidence of a
delayed rAF tick specifically (no instrumentation for rAF timing was added this round). It
does NOT obviously explain why external CPU/IO load (which should ALSO delay rAF ticks, being
a real-time browser scheduling concern) failed to reproduce the effect while intra-suite `-n 2`
did — a gap worth resolving before trusting this as the mechanism.

The 150ms fixed wait (`page.wait_for_timeout(150)`, `test_20260708_busy_states_and_chip.py:1376`)
after releasing the held-open fetch, intended to "let the stale `_restoreScrollY`'s first tick
run (and abandon)", is a fixed-duration margin around an `requestAnimationFrame` callback. If
contention delays that rAF tick past 150ms, the test would read `scrollY` before the abandon
logic has had a chance to run — this is a plausible mechanism for ANY sufficiently-timed delay
regardless of its source, but it is unproven: no run in this campaign captured evidence of a
delayed rAF tick specifically (no instrumentation for rAF timing was added this round).

**Gap: what would need to be SEEN to actually know.** Instrumentation on the rAF callback
itself (timestamp when `_restoreScrollY`'s tick fires vs. when `page.wait_for_timeout(150)`
elapses) would directly test the fixed-margin-vs-delayed-tick hypothesis above, independent of
which contention vector is used to produce the delay.

---

## Round 2 — instrumented re-run (rAF/spy visibility added), inconclusive on the original question

Added the existing scroll-mutation spy suite (`_SCROLL_SPY_JS` / `_SCROLL_SPY_NAMED_HOOKS_JS`
/ `_HEIGHT_ATTRIBUTION_JS`, already used by sibling tests in this file) to
`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` itself, which previously had
none, and re-ran the confirmed `-n 2`-within-suite vector (`capture_contention_n2.sh`, same 4
tests) for 16 iterations (4 batches of 4).

**Before building the instrument, hand-traced `_restoreScrollY`'s actual current implementation**
(`static/app.js:5601-5630`, not just the test's own docstring): the abandon check is
`ordinal !== _scrollCaptureOrdinal || scrollGen !== _scrollInterruptGen`, no fixed time budget
per tick. Critically, this test's own `scrollTo(0, 300)` call (which bumps `_scrollInterruptGen`
via the wrapped `window.scrollTo`) happens BEFORE the held-open fetch is ever released — i.e.
BEFORE `_restoreScrollY` is even scheduled. The generation mismatch is therefore already
established at schedule time, not something that has to "win a race" against a fixed margin.
This means `after` values well above `before` (like `291`/`306` from round 1) are NOT
consistent with "the stale restore's near-0 value was applied" (which would pull `after`
TOWARD 0, not push it to 291-306) — they look more like the already-documented mode-C/D
scroll-anchoring shape (`docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md`) bleeding into
this test (it seeds the SAME 20-near-identical-company corpus shape that triggers large merge-
suggestion growth elsewhere in this file) than a regression of the generation-mismatch check
itself. This reframing is itself only an inference — see `## Inferred` above, not upgraded to
fact.

> **⚠ Falsified by the cross-item review.** The document-level `overflow-anchor: none` fix
> (`27d349b`, 2026-07-26) that produces the mode-C/D `dy == dh` shape was already merged and
> confirmed still effective on 2026-07-30 (the same day these captures ran) — four days before
> the earliest capture this reframing was based on. The mode-C/D bleed-in explanation is
> **ruled out by dated git evidence**, not merely unconfirmed. See
> `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` for the corrected analysis and a
> different, untested hypothesis (a transient max-scroll clamp) that fits the observed values.

**Result: 15 passed / 1 failed / 16.** The single failure was NOT the `after != before` shape
this instrument was built to explain — it was a THIRD, previously-undocumented failure mode:
the test's own setup assertion `assert before > 0` failed (`before=0`), meaning the page had
not grown even its usual small scrollable amount (`before=59` in every other recorded run,
this branch's and historical) by the time `scrollTo(0, 300)` ran — BEFORE the held fetch is
ever released, earlier in the sequence than the mechanism this whole dossier has been
investigating. This failure never reaches the new spy-dump code (which only fires at the
final `after`-vs-`before` check), so no spy timeline was captured for it.

**Also notable, not conclusively explained:** the instrumented run's failure rate (1/16, ~6%,
and a different shape) was substantially lower than round 1's un-instrumented run of the
identical vector (2/8, 25%, the `after != before` shape). Two candidate explanations, neither
confirmed: (a) small-sample variance at n=8-16 against a rate this dossier has no confident
estimate of, or (b) a probe effect — the spy suite wraps `_captureScrollY`/`_restoreScrollY`/
`refreshCorpus`/scroll APIs with extra function-call overhead on every invocation, which could
plausibly shift the timing enough to move the race window rather than just observe it. Not
distinguished here; flagged for whoever continues this.

**Net: the rAF-timing/anchoring hypothesis from `## Inferred` above remains untested.** No run
in this round reproduced the `after != before` shape with the spy attached, so no evidence
either confirms or kills it. A NEW, real failure mode (`before == 0` at setup) is now on
record and unexplained — worth its own attention, potentially with instrumentation moved
earlier in the sequence (around the `#topTabCorpus` click and the page's height at the moment
`scrollTo(0,300)` fires, before any fetch release) rather than at the end. Full logs:
`scratchpad/contention_n2_instrumented_20260730.log` (gitignored, not committed).

---

## Round 3 — height-at-read instrument (the cross-item review's falsification experiment)

**Design (2026-07-30, before any runs — recorded per C-8).** Runs the experiment specified in
`docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` `## Falsification`, which supersedes
this dossier's own `## Falsification` plan below (rAF tick-timing): a height-clamp race would
not need rAF timing to explain it, and one more field on an existing read is cheaper than new
timing instrumentation.

**Instrument** (committed as this branch's first commit, per C-7): the two bare
`window.scrollY` reads in `test_restore_scroll_y_stale_invocation_overwrites_later_scroll`
(the `before` read after `scrollTo(0, 300)`, and the final `after` read) are replaced by a
single-evaluate `_READ_SCROLL_STATE_JS` returning `{y, sh (documentElement.scrollHeight),
ih (window.innerHeight), cards (rendered corpus-card count)}` — geometry at the same instant
as the scroll read, one round-trip, no change to the test's timing shape (round 2 observed an
unexplained rate drop with the spy attached, so probe weight matters). Both dicts print on
**every** run, pass or fail — a passing run's height at the `after` read is equally
informative (it should be fully grown, not in the ~1170-1210 band). The `before > 0` setup
assert also now carries the geometry dict, so a recurrence of round 2's third failure mode
(`before=0`) arrives with its height attached instead of opaque.

**Vector:** the confirmed `-n2`-within-suite reproduction, unchanged — same 4 nodeids from
`test_20260708_busy_states_and_chip.py` under `-n 2 -v --tb=short`. The original
`capture_contention_n2.sh` was session-local scratchpad and did not survive the previous
session; it was recreated mechanically from this dossier's own `## Observed` description of it
(4 fixed nodeids, two-per-worker `load` scheduling), not reconstructed from memory.

**Decision tree (the review doc's, restated):** a `291`/`306`/`273`-shaped failure with `sh`
in ~1170-1210 at the `after` read → clamp hypothesis confirmed, fix target becomes
render-sequencing; `sh` fully grown (or any other value) on such a failure → clamp hypothesis
dead, widen the instrument, do not guess a third theory.

**Results:** *(appended per batch as they land)*

**R3-0 — single isolation run (instrument shakedown, 2026-07-30):** PASSED, 23s, with:
`before_read={'y': 59, 'sh': 959, 'ih': 900, 'cards': 0}`
`after_read={'y': 59, 'sh': 5590, 'ih': 900, 'cards': 20}`.
Two things now **observed** (previously only back-derived in the review's R-3):
(1) at the `before` read the document is exactly `959`px tall with **zero** cards rendered, so
`scrollTo(0, 300)` clamps to `959 - 900 = 59` — the historically-constant `before=59` **is
itself the max-scroll clamp in action**, directly seen for the first time; (2) on a passing
run, by the final `after` read the page has grown well out of the ~1170-1210 band (`sh=5590`,
all 20 cards attached) — matching the review's prediction for what a pass should look like.

---

## Falsification

> **⚠ Superseded by Round 3 above** (per the cross-item review's own `## Falsification`) —
> the rAF tick-timing instrument described here was not built; the height-at-read experiment
> replaced it. Kept for the record.

**Still not run — round 2's instrumentation did not happen to catch the target shape** (see
`## Round 2` above; it caught a different, third failure mode instead). A reliable-enough
reproduction exists (`capture_contention_n2.sh`, ~25% failure rate un-instrumented, ~6% with
the spy attached — the discrepancy itself unresolved), so this experiment can be run directly
against a captured failure rather than blind, once one lands:

1. Instrument `_restoreScrollY`'s rAF callback (timestamp at tick-fire time, and whether the
   abandon/generation-mismatch check actually ran before the test's own `page.wait_for_timeout(150)`
   elapsed) alongside the existing `_SCROLL_SPY_NAMED_HOOKS_JS` wrapper already in the test
   file. Run it under the confirmed `-n 2`-within-suite vector (`capture_contention_n2.sh`)
   until a failure is captured, and read the timestamps directly off that failing run.

- **If the rAF-timing instrument shows a delayed tick on a captured failure:** the fixed-margin
  hypothesis is confirmed; a fix (e.g. don't read on a fixed timeout, wait for the spy to
  observe the tick) can be built on that evidence. This would still leave open WHY intra-suite
  `-n 2` delays the tick when external CPU/IO load (confirmed real, `## Observed` above) does
  not — worth a one-line note in the fix commit if it remains unexplained, per this dossier's
  own discipline against conflating "a real defect" with "the whole story."
- **If it shows the tick fired in time and `after` still deviated:** the fixed-margin
  hypothesis is dead — widen further, do not fix on this basis. In particular, re-examine
  whether the SECOND concurrent worker's own werkzeug thread/DB/port activity is doing
  something more direct than merely delaying a callback (e.g. an actual cross-worker state
  leak), since `-n 2`'s uniqueness among the tested vectors is that it's the only one running
  a second copy of the SAME app code, not just generic background load.

---

## The fix

Not applicable yet — no mechanism has been proven. Do not build a fix on this dossier alone
(see `## Status` above).

---

## Acceptance bar

Not applicable yet — see `## The fix`.

# Diagnosis — keyboard-reorder test hit a Playwright 30s timeout, once, never reproduced since

> **Status:** hypothesis only. No root cause proven; no reproduction achieved yet on this
> branch. This document's job so far is closing an evidence gap in the item's own filing,
> establishing the exact call path, and pre-registering falsification experiments.
> **Branch:** `fix/ux-keyboard-reorder-timeout`

---

## Symptom

`test_keyboard_reorder_persists_and_reset_reverts`
(`tests/ux/regression/test_20260604_bullet_drag_reorder.py:57-85`) hit a Playwright 30s
timeout once, during `chore/work-item-tracking` (2026-07-28), in a run believed uncontended.
It has not recurred since (four scratchpad log files that include this test name all show
`PASSED`, dated 2026-07-30 — see `## Observed`). Item 30
(`docs/dev/work/items/0030-keyboard-reorder-load-state-timeout.md`) was filed as the scheduled
follow-on; no diagnosis existed before this branch.

---

## Observed

### O-1. The original record does not name a mechanism; a later document does, uncited

`docs/dev/work/items/0001-gate-unrunnable-by-agent.md:124-132` (commit `6bb7d47`,
`chore/work-item-tracking`, 2026-07-28) — the earliest occurrence of this failure anywhere in
the repo — reads:

> "Even fully isolated, the UX tier still produced one flake (a different test,
> `test_keyboard_reorder_persists_and_reset_reverts`, **a plain Playwright 30s timeout**) on a
> subsequent clean run."

That is the entire evidentiary record. It does not name `wait_for_load_state`, `networkidle`,
or any specific call. The same-branch handoff
(`docs/dev/handoffs/chore-work-item-tracking.md:118-121`) records only: `pytest -m ux` "✓
(clean on retry — 129 passed; the first attempt hit this project's already-known,
already-CI-accepted ~40%-ish UX rerun rate, not a regression)" — the failing attempt's own
output was not captured.

`docs/dev/work/items/0019-ux-flake-solution-sprint.md:42-45` (2026-07-28), one document
downstream, narrows this to: "one Playwright **`wait_for_load_state`** 30s timeout" — with no
cited source for the added specificity. `docs/dev/work/items/0030-keyboard-reorder-load-state-timeout.md:19-24`
and `docs/dev/work/BOARD.md:47` both inherit the narrowed wording verbatim.

**No traceback, log line, or exception text for this failure exists anywhere** — confirmed by
searching all of `docs/`, `git ls-files` (the only tracked `.log`/`.txt`/`.out` files are
licenses, an interview transcript, eval fixtures, and `llms.txt`), the gitignored local
`scratchpad/` (40+ campaign logs; 4 mention this test name —
`gate_fix-ux-mode-c-scroll-residual.log:4362`, `gate_ux_reg1_20260730.log:13`,
`round7_full_ux_baseline_rerun.log:25`, `round7_full_ux_suite.log:25` — **all four `PASSED`**,
all dated 2026-07-30, after the original observation), and `git log -S "wait_for_load_state"`.
`docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-1..O-14 list does not contain this test.

### O-2. The "30s" figure is a real discriminator, but does not uniquely identify `networkidle`

Confirmed by direct grep: no `set_default_timeout` / `set_default_navigation_timeout` call
exists anywhere in the repo. `ui_pages/base.py:11-12` sets
`DEFAULT_TIMEOUT_MS = 15_000` and `LLM_TIMEOUT_MS = 120_000` — neither is 30s. So a genuine
30000ms timeout requires a Playwright call with **no explicit `timeout` argument**, inheriting
Playwright's built-in default. On this test's path, confirmed by direct read, those are:

- `self.page.wait_for_load_state("networkidle")` — `ui_pages/wizard_compose.py:75`, inside
  `_wait_settled()`. Its two sibling waits at `:72` and `:76` both pass
  `timeout=DEFAULT_TIMEOUT_MS` explicitly; only line 75 has no timeout argument.
- `page.expect_response(_is_composition_post)` — test lines 70 and 82. `_is_composition_post`
  (test lines 39-40) matches **any** POST whose URL contains `/composition`, including
  `_pinSummaryVariant`'s (`static/app.js:7773-7778`), not only the reorder/reset POSTs the test
  intends to wait on.

**The "30s" figure narrows the candidate set to these; it does not single out `networkidle`.**

### O-3. `_wait_settled()` is reached 12 times in this one test, not once

Confirmed by direct read of `ui_pages/wizard_compose.py`. `_bullet_list()` (`:206-214`) calls
`self._wait_settled()` at line 213, with its own docstring stating: "The settle here is
inherited by every caller (`_row`, `bullet_texts`, `has_custom_order`, `move_*`,
`drag_below`)". `_first_card()` (`:100-109`) calls it at line 106. So every `bullet_texts()`,
`has_custom_order()`, `move_down()`, and `reset_order()` call in the test settles first:

| test line | call | reaches `_wait_settled` via |
|---|---|---|
| 63 | `open()` (inside `_reach_compose`) | `_wait_loaded` directly |
| 66, 72, 78, 84 | `bullet_texts()` | `_bullet_list()` |
| 67, 73, 79, 85 | `has_custom_order()` | `_bullet_list()` |
| 71 | `move_down()` — inside `expect_response` | `_row()` → `_bullet_list()` |
| 77 | `reload()` | `_wait_loaded` directly |
| 83 | `reset_order()` — inside `expect_response` | `_first_card()` |

Two of the twelve (lines 71, 83) are nested inside an `expect_response(_is_composition_post)`
block — a 30s-default wait containing another 30s-default wait.

### O-4. `WizardTemplatePage.open()` (test line 76, immediately before the reload at line 77) does not wait for the live-preview iframe

Confirmed by direct read, `ui_pages/wizard_template.py:18-25`:

```python
def open(self) -> WizardTemplatePage:
    self.goto_step(4)
    self.page.wait_for_selector(Wizard.PANEL_TEMPLATE, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    self.page.wait_for_selector(Wizard.TEMPLATE_OPTIONS, timeout=DEFAULT_TIMEOUT_MS)
    return self
```

It waits only for the template panel and its option rows. `wait_live_preview()` (`:37-41`),
which waits for `#livePreviewFrame` to be visible, is a separate method — **not called by this
test.**

Confirmed by direct read, `static/app.js`: `wizardGoTo` fires `if (step === 4)
_loadTemplatePicker();` unawaited (`:7017`, no `await`). `_loadTemplatePicker` (`:9144-9208`)
ends by calling `_refreshLivePreview(parseInt(sel.value, 10))` (`:9207`) if a template is
selected. `_refreshLivePreview` (`:9391-9456`) does a probe `fetch` then
`_loadPreviewFrame(frame, url)` (`:9455`), which does a **full iframe navigation**:
`frame.contentWindow.location.replace(url)` (`:7362`). The preview route injects
`<script src="/static/vendor/paged.polyfill.js">` (`blueprints/templates.py:459`) — confirmed
**921,702 bytes** on disk (`wc -c static/vendor/paged.polyfill.js`) — then runs
`new window.Paged.Previewer().preview()` (`:475`).

Panel switching only toggles CSS visibility (`_wizardRender`, `static/app.js:7043-7048`, not
independently re-verified this branch but established by item 28's dossier's direct read of
the same function); it does not cancel an in-flight iframe navigation.

### O-5. The `loadComposition()` cascade's failure paths do NOT recurse — only success paths do

Confirmed by direct read of the full function body, `static/app.js:7211-7351`.
`_fireDraftSummary` (`:7498-7551`):

```js
if (res.ok) {
  persisted = true;
  await loadComposition();          // recursion ONLY here
} else {
  _failDraftSummary('Could not draft your summary. Use Regenerate to retry.');
}
```

`_failDraftSummary` (`:7559-7563`) only sets placeholder text and shows a toast — it does not
call `loadComposition()`. On any non-success path the `finally` block releases the
once-per-application latch (`:7546-7548`) but issues no further network request.
`_fireDraftGapFill` (`:7576-7606`) has the identical shape: `await loadComposition()` only
inside `if (res.ok)` (`:7594-7595`); its latch (`_gapFillFiredForApp`) is claimed permanently
**before** the fetch (`:7334`, outside the function) regardless of outcome, so it can fire at
most once per application either way.

### O-6. The specific historical trigger for a draft-summary failure is already fixed and regression-tested

The code comment at `static/app.js:7513-7519` names the trigger: "a 400 from a torn read of a
non-atomically-written context file... is fixed separately in `hardening.write_context_atomic`."
Confirmed: `hardening.write_context_atomic` exists (`hardening.py:1444`) and is used at the
production context-write call sites (`hardening.py:1607,1616,1812`).
`tests/test_draft_summary.py:237-259`, `test_torn_context_file_is_a_loud_400`, pins the
contract directly:

> "`fix/compose-summary-draft-settle-hole`: a concurrent NON-atomic write left `context_*.json`
> truncated, this route 400'd on the `JSONDecodeError`, and the Compose client swallowed the
> 400... **Writes are atomic now (`hardening.write_context_atomic`), so the tear can no longer
> happen**; this pins the contract the client is now required to surface instead of drop."

### O-7. Under this test's LLM stubs, draft-summary and gap-fill both succeed deterministically

`install_llm_stubs` (`tests/ux/stubs.py:387-428`) patches `analyzer.draft_positioning_summary`
→ `fake_draft_positioning_summary` (`:145-152`, "return a deterministic 2-sentence positioning
summary... DB-free — the text is fixed") and `analyzer.draft_gap_fill_bullets` →
`fake_draft_gap_fill_bullets` (`:155-`, DB-aware but deterministic). Both stubs always return a
successful result — the routes they back cannot 400 on an LLM-side failure in this test.
The test's seed data (`tests/ux/seeding.py:49-98`: 1 experience, 2 bullets, no SummaryItems,
no Skills, no ExperienceSummaryItems) means only the draft-summary and gap-fill background
fires are reachable on this path (the skills-card and recommend-summary/experience-summary
branches all require data this seed doesn't create).

**Consequence:** for this specific test, the `loadComposition` cascade is a bounded, ordinary
sequence — draft-summary fires and succeeds (pass 1) → recurses → gap-fill fires and succeeds
(pass 2, since `bgDraftFiring` is now false) → recurses → nothing left to fire (pass 3,
terminal). Each fire is a real network round-trip, but under stubs each should be fast.

### O-8. Frontend has no ambient polling that could hold `networkidle` open indefinitely

No `setInterval`, `EventSource`, `WebSocket`, `sendBeacon`, or `keepalive` fetch exists
anywhere in `static/*.js` (grepped directly). All `setTimeout` call sites are one-shot; the
Compose autosave debounce (`_scheduleCompositionSave`, `static/app.js:8973-8985`) re-arms only
from three user-driven call sites (`_moveBulletRow`, DnD drop, `_resetExperienceOrder`) — not
from any timer. This rules out a whole class of "network never goes idle" explanations; it does
not rule out a single long-running request (H1) or a multi-pass legitimate cascade landing
badly (a weakened form of what O-5/O-6/O-7 mostly rule out — see `## Inferred`).

### O-9. The repo has independently, repeatedly rejected `networkidle` as a settle signal — for the opposite failure direction

Four places document that `networkidle` can go quiet **too early** because a fire-and-forget
fetch hasn't been issued yet by the time it checks
(`scripts/bench_corpus_scale.py:362-366`, `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md:266-269`,
`docs/dev/diagnosis/merge-suggestions-render-cap.md:22-24`, and the POM docstring itself at
`ui_pages/wizard_compose.py:64-70`: "`networkidle` is kept as a cheap pre-drain of unrelated
in-flight XHRs" — i.e., deliberately demoted from settle-gate to pre-drain, not removed). This
is the opposite direction from a *hang* — worth recording because it means the documented
failure mode for this exact API is "settles too soon," which does not explain a 30s timeout by
itself, but confirms the team already distrusts this call for unrelated reasons.

### O-10. This test has failed before, with different, non-timeout signatures

`docs/dev/RELEASE_CHECKLIST.md:1043-1055` (2026-07-15, CI rerun): fail-once-then-pass, "once in
4 CI runs... far too noisy to attribute." `docs/dev/RELEASE_CHECKLIST.md:110,1642`: a
`compose.bullet_texts()[0]` IndexError, "compose-load race." Neither is a timeout of any kind.
The ~42% CI-rerun statistic (`RELEASE_ARC.md:1374`) is scoped to "5 distinct settle/restore-
family tests"; no source names which 5 or places this test among them.

### O-11. Shakedown run (2026-07-31): instrument arms cleanly, and the ordinary case is nowhere near 30s

One isolated run, `SETTLE_INSTRUMENT_ALWAYS=1 python -m pytest
tests/ux/regression/test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts
-v -s --tb=short`. **PASSED.** All 12 reaches captured; the network census saw 24 distinct
URLs (never zero, so the liveness check never fired). Per-reach `networkidle` timings:
`0.139, 0.035, 0.036, 0.04, 0.045, 0.042, 0.609, 0.025, 0.027, 0.027, 0.024, 0.025` (seconds).
Worst case (reach 7, the one right after `WizardTemplatePage.open()` — i.e. the exact H1
call site) was **0.609s against a 30s budget**, ~2% of the ceiling. `settled_s` (the real
settle-gate wait) was similarly small throughout, max 1.501s (reach 1, first render).

**Isolated single-test timing note (not a hang):** total pytest wall time was 129.94s, but the
actual browser/server request timeline (first `GET /` to last `POST /composition` in the
werkzeug log) spans only ~14s (12:10:59 → 12:11:13). The ~115s gap is one-time browser-process
launch + DB-migration + Python cold-start overhead that a full-suite serial run amortizes
across all 131 tests (488s / 131 ≈ 3.7s/test average) but a single isolated test invocation
pays in full. Relevant for Commit 2 (baseline campaign): compare per-reach sub-wait timings,
not total wall time, across isolated-vs-suite runs.

### O-12. Baseline batch (2026-07-31, 3 more isolated runs): reach 7's `networkidle` is consistently ~15-20x every other reach

`for i in 1 2 3; do KEYBOARD_REORDER_SETTLE_LOG=... python -m pytest <nodeid> -v --tb=short; done`,
durable side channel (`scratchpad/keyboard_reorder_baseline_20260731.log.reads`). All 3 PASSED.
Wall time 31s/25s/22s (the shakedown's 130s was one-time cold-start overhead — chromium binary
verification / OS disk-cache priming on this session's first-ever pytest invocation; these three
runs did not repeat it).

**Reach 7 `networkidle_s` across all 4 runs so far (shakedown + this batch): `0.609, 0.571, 0.561,
0.567`** — mean 0.577s, spread under 5%. Every other reach in every run: `0.016`–`0.053`s. Reach 7
is test line 77 (`compose.reload()`), the statement immediately after `WizardTemplatePage(page,
live_server).open()` at line 76 — **exactly the H1 call site** (O-4). No other reach shows
anything like this elevation, in any of the 4 runs.

**What this is and is not evidence of:** this is a real, reproducible, structural cost — not
noise, and not (yet) a hang. 0.577s is ~2% of the 30s budget, nowhere near a timeout under these
ordinary conditions (fast local machine, stubbed LLM calls, tiny 1-experience corpus, cold
werkzeug thread pool otherwise idle). It sharpens H1 from "a plausible code-read mechanism" to
"a measured, consistently-reproducing structural cost at the exact predicted call site" — the
open question P1 (`## Falsification`) is now specifically "does this SAME cost scale to 30s
under adversity (slower I/O, a larger corpus, a colder cache, contention)," not "does this call
site have any elevated cost at all" (answered: yes, every time).

### O-13. Second baseline batch (3 more runs, 6 total in the durable log) confirms O-12 and surfaces one distinct, non-repeating anomaly at reach 1

Full per-run `networkidle_s`, all 12 reaches, all 6 loop-batch runs (durable log, not stdout):

```
run 1: [0.033, 0.024, 0.024, 0.021, 0.021, 0.02,  0.571, 0.025, 0.025, 0.027, 0.027, 0.028]
run 2: [0.031, 0.024, 0.025, 0.026, 0.022, 0.018, 0.561, 0.016, 0.018, 0.017, 0.017, 0.017]
run 3: [0.03,  0.028, 0.019, 0.019, 0.02,  0.019, 0.567, 0.022, 0.024, 0.021, 0.026, 0.023]
run 4: [0.083, 0.029, 0.023, 0.019, 0.022, 0.023, 0.583, 0.027, 0.023, 0.024, 0.027, 0.025]
run 5: [1.263, 0.03,  0.023, 0.022, 0.021, 0.023, 0.561, 0.023, 0.023, 0.021, 0.027, 0.024]
run 6: [0.035, 0.032, 0.028, 0.028, 0.027, 0.023, 0.567, 0.02,  0.024, 0.023, 0.024, 0.022]
```

Reach 7 (index 6): `0.571, 0.561, 0.567, 0.583, 0.561, 0.567` — the same tight, consistent
elevation as O-12, now confirmed across 7 total runs (shakedown + 6). No other reach repeats
this pattern in any run.

**Run 5, reach 1: `networkidle_s = 1.263`** — a single occurrence, ~30-40x every other run's
reach 1 (`0.03`–`0.083`s elsewhere) and ~2x reach 7's own consistent value. Reach 1 is the
FIRST `_wait_settled()` call in the test, inside `open()`'s `_wait_loaded()` — reached right
after `#btnSkipFromAnalysis` fires `_fireRecommendThenCompose()` (`static/app.js:1487-1531`:
`POST /api/applications/<id>/recommend` then `wizardGoTo(3)` → `loadComposition()`), a
DIFFERENT call site from reach 7's. This does **not** repeat in the other 6 runs, so it is
recorded as a single anomaly, not a pattern — but it is a real, artifact-backed data point
(4.2% of the 30s budget), not noise to discard. It does not by itself implicate any of H1/H2/H3
(reach 1 predates the Step-4 iframe navigation that H1 needs), but it is consistent with the
general shape all three hypotheses share: an occasional, load-sensitive network round-trip
landing badly.

**Wall time, both batches (6 runs): 31s, 25s, 22s, 29s, 23s, 22s** — all far under the
shakedown's 130s, confirming that figure was one-time cold-start cost (O-11).

---

## Falsified

_(Nothing yet — this branch has run no experiments against the live application.)_

---

## Inferred

**These are hypotheses. None is fact. Do not build a fix on any of them until the
falsification experiments below have run.**

### H1 — the live-preview iframe's `paged.polyfill.js` load/layout blocks `networkidle` at test line 77

`WizardTemplatePage.open()` (line 76) does not wait for the iframe it triggers (O-4); the very
next line (`compose.reload()`) hits `networkidle`. If the iframe navigation + 921KB script
parse + `Paged.Previewer().preview()` layout pass is still in flight at that moment, it would
hold the network non-idle. **Gap: no evidence yet that this navigation is ever still in flight
30s later** under this test's stub-fast, small-corpus conditions — it may complete in
milliseconds. Needs a timing measurement or a deliberate stall (falsification P1) to know.

### H2 — a slow or repeatedly-retried Compose cascade extends the in-flight window (WEAKENED by O-5/O-6/O-7)

Originally hypothesized as an unbounded retry loop; direct code read does not support that
framing. Recursion happens only on success (O-5); the one historically-documented failure
trigger is already fixed and regression-tested (O-6); this test's stubs make both relevant
calls succeed deterministically (O-7). What remains plausible, much more narrowly: the
legitimate 2-3 pass cascade (draft-summary → gap-fill → terminal) could still take
unexpectedly long under adverse conditions (a slow werkzeug thread, GC pause, or genuine
resource contention on the machine) — extending three real network round-trips into a window
large enough to matter, though "large enough to reach 30s" is a big gap from any observed
number. **Gap: no timing has been captured for how long this cascade ordinarily takes.**
Lower prior than H1 after this session's reading; still worth the falsification probe (P2)
because it's cheap and would otherwise go unchecked (C-7: never scope the instrument to only
the theory you favor).

### H3 — the timeout was never `networkidle` at all

The `expect_response(_is_composition_post)` blocks (test lines 70, 82) share the same 30s
default (O-2), and `_is_composition_post` matches more POSTs than the test's own two intended
ones (O-2). **Gap:** distinguishing this from H1/H2 requires knowing which Playwright call
actually raised — information the original failure never captured (O-1). The wide instrument
(commit 1) is designed to capture this if the failure ever recurs live, independent of which
hypothesis is right.

---

## Falsification

**Pre-registered before any run, per C-8.** Decision tree:

**Step 1 — baseline (measure the ordinary case, not just chase the failure).** ~10 serial runs
of the target test with the wide instrument attached (all 12 `_wait_settled()` reaches timed
per sub-wait; live request/response/requestfailed census; per-URL hit counts; Compose latch
state; iframe navigation state — dumped on any exception, not only a `networkidle` one).
- **If the worst ordinary-case `networkidle` duration is a small fraction of 30s (e.g. <2s)
  across all runs:** the ordinary path is nowhere near the ceiling: consistent with item 30
  being a genuine rare-tail event, not a systematic near-miss. Proceed to Step 2.
- **If any ordinary run's `networkidle` duration is already several seconds:** the margin is
  thin; a slower box or heavier ambient load plausibly tips it over without needing H1/H2 to be
  dramatic. Note this and still proceed to Step 2 (it sharpens, doesn't replace, the probes).

**Step 2 — deterministic capability probes**, each a `page.route()`-based test answering "CAN
this mechanism alone reach a 30s `networkidle` hang":
- **P1 (H1):** stall the response to `**/static/vendor/paged.polyfill.js` (or the preview
  route itself) for e.g. 35s and observe whether `_wait_settled()`'s `networkidle` at test line
  77 blows its budget.
  - **If it hangs:** H1 is capability-proven — the fix target is
    `WizardTemplatePage.open()`/`_wait_settled()` not accounting for the iframe, a harness/POM
    sequencing question, not a product defect.
  - **If it does NOT hang:** either Chromium's `networkidle` definition doesn't count a
    same-origin iframe's sub-resources the way expected, or the panel-visibility toggle
    genuinely does abort/deprioritize it. Record which, precisely — this determines whether H1
    is dead or needs a different stall point.
- **P2 (H2):** force `POST **/draft-summary` (and separately, `**/draft-gap-fill`) to return
  400 repeatedly via `page.route()`, overriding the stub's success, and count `GET
  /composition` hits / measure total elapsed time to terminal settle.
  - **If it hangs or produces materially more passes than the un-forced 2-3:** H2 gets
    reopened with real numbers, not the discarded "unbounded" framing.
  - **If it settles quickly regardless (expected, per O-5):** H2 is dead as stated. Do not
    re-infer a new failure-retry theory without new evidence (C-7).

**If both P1 and P2 come back negative:** both current hypotheses are dead. Per C-7, do not
invent a fourth theory to fit — widen the instrument (H3's rival `expect_response` waits become
the next thing to probe) and report back before proceeding, rather than picking a guess.

---

## The fix

_Not yet — no experiment above has run._

---

## Acceptance bar

_To be filled in once a mechanism is proven. Provisionally: whatever fix lands must be A/B'd
against the real test in a loop (8-10+ runs per arm, per
`feedback-ab-fix-against-real-test-not-just-instrument`), reporting counts and a probability,
never a bare rate — and `python -m scripts.gate` must stay green with the historical UX
baseline (131 passed / 1 xfailed / 1 xpassed) intact or the delta explicitly stated._

# Diagnosis — keyboard-reorder test times out in `networkidle` with an empty request census

> **Status:** capability shown, cause on CI **not** shown. P5 reproduces the recorded CI shape
> from first principles (O-17): a Playwright-internal order dependence makes the main frame's
> `networkidle` unreachable with nothing pending. P3 shows a second, distinguishable way to the
> same timeout (a held body, O-18). Neither is established as what happened on any CI run; the
> widened instrument now separates them in a natural capture. This branch does not fix (owner
> scope answer, 2026-10-14: "Probe only, then report").
> **Branch:** `fix/reorder-networkidle-empty-census`
> **Item:** 30 (`docs/dev/work/items/0030-keyboard-reorder-load-state-timeout.md`).
> **Prior dossier:** `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md` (cited, not restated).

---

## Symptom

`tests/ux/regression/test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts`
fails one attempt in a CI UX job with `TimeoutError: Timeout 30000ms exceeded.` and passes on the
retry a few seconds later. `ci_wait` exits 3, and a merge-ready PR costs a re-push and a second CI
run (about 7 minutes). Three recorded failures since the 2026-10-02 re-measurement: PR #160, #166,
#170.

---

## Observed

Each entry cites where it was seen. Run ids and logs are as recorded in item 30's `## Updates`;
this branch has not re-read the raw job logs for the older runs.

- **O-1. The timeout is raised from the test's own instrument, with no timeout argument.**
  Traceback on run 37669157358 / job 112956085468 (item 30, 2026-10-07 entry): `:254` →
  `ui_pages/wizard_compose.py:232 _wait_settled` → `test_20260604_bullet_drag_reorder.py:163
  _instrumented_wait_settled` → `self.page.wait_for_load_state("networkidle")`. The same
  traceback is recorded for run 38310545397 (2026-10-12) and run 38676437085 / job 116231042086
  (2026-10-14). At HEAD, `tests/ux/regression/test_20260604_bullet_drag_reorder.py:163` reads
  `self.page.wait_for_load_state("networkidle")`, and `ui_pages/wizard_compose.py:93-94` reads
  `with contextlib.suppress(PlaywrightTimeoutError): self.page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_PREDRAIN_MS)`.
- **O-2. The failing reach is the 9th and last, `has_custom_order()` at `:254`, straight after
  reach 8.** `{'reach': 9, 'panel_visible_s': 0.013, 'exception': "TimeoutError('Timeout 30000ms
  exceeded.')", 'elapsed_total_s': 30.044, ...}` (run 38676437085, item 30 2026-10-14 entry,
  read from the raw job log). The same entry records reaches 1–8 at `networkidle_s` 0.0–0.633.
  `test_20260604_bullet_drag_reorder.py:253` (`bullet_texts()`) and `:254` (`has_custom_order()`)
  are consecutive statements with no test action between them.
- **O-3. At every recorded timeout every harness readiness signal said ready, and the census
  listed nothing.** `cascade_state: {'composeReady': True, 'bgPending': None,
  'draftSummaryFiredForApp': 1, 'gapFillFiredForApp': 1, 'composeApplicationId': 1,
  'previewFrameReadyState': 'complete'}`, `still_pending_requests: []` (runs 31047661015,
  33708934519, 38310545397, 38676437085; item 30 entries 2026-08-05, 09-03, 10-12, 10-14).
- **O-4. `bgPending: None` is the attribute being absent, which is the settled state.**
  `test_20260604_bullet_drag_reorder.py:79` reads `list.getAttribute('data-compose-bg-pending')`
  (`null` when absent); `ui_pages/wizard_compose.py:66-67` states the settle gate is
  `data-compose-ready` PRESENT and `data-compose-bg-pending` ABSENT.
- **O-5. The census removes a request from "pending" on the `response` event.**
  `test_20260604_bullet_drag_reorder.py:114-115` (`_on_response` calls `_finish`), `:120-122`
  (`_finish` pops `_pending`), `:106-108` (listeners: `request`, `response`, `requestfailed`
  only; there is no `requestfinished`).
- **O-6. Hit counts at the 2026-10-14 timeout** included `/api/applications/1/preview?template_id=1&context_path=…`
  ×2, `/api/users/alice/preview?template_id=1` ×2 and `static/vendor/paged.polyfill.js` ×2
  (item 30, 2026-10-14 entry).
- **O-7. The preview refresh does a probe `fetch` and then a same-frame navigation.**
  `static/app.js:10316` (`probe = await fetch(url, { method: 'GET' })`), `:7899-7905`
  (`_loadPreviewFrame` → `frame.contentWindow.location.replace(url)`).
- **O-8. A held (never-fulfilled) request produces a real 30 s `networkidle` timeout.** Prior
  probe P1, `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md` O-15 (item 30, 2026-07-31 entry).
- **O-9. This test is the only test whose CI attempts have been seen to fail this way in the
  recorded window.** Item 30 2026-10-02 entry: `report --tier ux`, `5/153` attempts, 3.3%.
  *(Scope: this test only. Other tests were not compared on this branch.)*
- **O-10. The installed Playwright (1.60.0) documents `response` and `requestfinished` as
  different events.** `playwright/sync_api/_generated.py`, `Page.on` overloads: `response` —
  "Emitted when [response] status and headers are received for a request"; `requestfinished` —
  "Emitted when a request finishes successfully after downloading the response body. For a
  successful response, the sequence of events is `request`, `response` and `requestfinished`."
  This is documentation of the events. It says nothing about how `networkidle` counts a request;
  that is what P3 asks.
- **O-11. The widened instrument runs and is quiet on an ordinary local run.** Command:
  `python -m pytest tests/ux/regression/test_20260604_bullet_drag_reorder.py -m ux -k keyboard_reorder -s`
  → `1 passed, 3 deselected in 13.20s`, 12 `_wait_settled` reaches, `networkidle_s` 0.008–0.781
  (reach 7, the reload after `WizardTemplatePage.open()`, 0.574, as the prior dossier's O-12
  recorded), `awaiting_body at end of test: []`, 13 frame events including three `about:blank`
  iframe attaches (`livePreviewFrame`, `outputPreviewFrame`, `coverPreviewFrame`) and
  `framenavigated` on the main frame to the same URL four times (why is not established here).
  One local run; it shows the fields populate and nothing is held at rest. It is not a baseline
  distribution.
- **O-12. How the installed driver (Playwright 1.60.0) computes `networkidle`, read from its
  source, not run.** `playwright/driver/package/lib/coreBundle.js`, methods named below (a
  character offset is not a stable cite in a 3 MB bundle):
  - `FrameManager._inflightRequestStarted(request)` adds the request to
    `request.frame()._inflightRequests` and, on size 1, calls `frame._stopNetworkIdleTimer()`,
    which also sets `_firedNetworkIdleSelf = false`. `_inflightRequestFinished(request)` removes
    it and, on size 0, calls `frame._startNetworkIdleTimer()`. It is called from
    `reportRequestFinished`. `requestReceivedResponse` (the `response` event) does not touch
    `_inflightRequests`. Favicon requests are excluded from both.
  - `Frame._startNetworkIdleTimer()`: after 500 ms it sets `_firedNetworkIdleSelf = true` and calls
    `mainFrame()._recalculateNetworkIdle()`.
  - `Frame._recalculateNetworkIdle(frameThatAllowsRemovingNetworkIdle)`: a frame is idle only if
    `_firedNetworkIdleSelf` **and every child frame has `networkidle` in
    `_firedLifecycleEvents`**. It deletes an already-fired `networkidle` when the frame is not
    idle and `frameThatAllowsRemovingNetworkIdle !== this`. It is called with no argument from
    `onLifecycleEvent` (any lifecycle event on any frame), and with the committing frame as the
    argument from `_onClearLifecycle`.
  - `Frame._onClearLifecycle()` (a commit in that frame) clears its fired events, keeps only the
    current document's request in `_inflightRequests`, restarts the timer if the set is empty, and
    calls `mainFrame()._recalculateNetworkIdle(this)`.
  - Consequence for this test, from the code and not yet from a run: a child-frame commit between
    reach 8 and reach 9 can remove the main frame's already-fired `networkidle`, and the main
    frame then waits for that child to re-fire its own.
- **O-13. P3 ran (first design, three arms in sequence in one page, one run).** Command:
  `python -m pytest tests/ux/regression/test_20260604_bullet_drag_reorder.py -m ux -k "p3 or p4" -s`
  → `2 passed, 4 deselected in 126.27s`. All controls held (idle before arming; the held
  request listed under `awaiting_body`; each arm's frame commit seen). Result line, `(timed_out,
  elapsed_s)` per arm, bound 8 s:
  `A_commit_only (True, 8.039)`, `B_held_no_trigger (True, 8.048)`, `C_held_plus_commit (True,
  8.047)`, `D_after_release (False, 0.513)`. At the end of arm C: `still_pending_old: []`,
  `awaiting_body: [{url: .../held-body, resource_type: 'fetch', frame_url: <main>, body_open_s:
  16.198}]`, and the per-frame check: the **main frame `networkidle: NOT_REACHED`**,
  `readyState: complete`; `livePreviewFrame`, `outputPreviewFrame`, `coverPreviewFrame`, `p3a` and
  `p3c` all `networkidle: reached`.
- **O-14. P4 ran (same command and run).** Result line: `single (True, 8.041)`, `double (True,
  8.039)`; `single_awaiting_body: []`, `double_still_pending_old: []`, `double_awaiting_body: []`,
  `double_failed: [{url: ...preview?template_id=1&p4=1&..., failure: 'net::ERR_ABORTED'}]`
  (the superseded first navigation); `double_committed_p4` lists two `framenavigated` events.
  Per-frame check after the double: **main frame `NOT_REACHED`**, `readyState: complete`;
  `livePreviewFrame` (at `p4=2`), `outputPreviewFrame`, `coverPreviewFrame` all `reached`.
- **O-15. Both probes hit the same state: the main frame's `networkidle` unreached, every child
  frame's reached, no request pending, no body awaited, `readyState: complete`.** That is the
  field-for-field shape of every recorded CI failure (O-3): `composeReady` true, `bgPending` null,
  `previewFrameReadyState: 'complete'`, `still_pending_requests: []`. In these runs the shape was
  reached with a held fetch in flight (P3 arm C, where the fetch is why it is correct for the
  main frame not to be idle) AND in P3 arm A and P4 `single`/`double` with nothing held.
- **O-16. Release recovered it.** P3 `D_after_release`: after the held body was released,
  `networkidle` was reached in 0.513 s, about one 500 ms idle timer (O-12) after the request
  finished.
- **O-17. P5 ran, four arms, each on a fresh page with no app JS** (`/static/style.css`; bound
  8 s; controls held: idle first, every action seen to complete). Command:
  `python -m pytest tests/ux/regression/test_20260604_bullet_drag_reorder.py -m ux -k "p3 or p5" -s`
  → `5 passed, 5 deselected in 39.85s`. Result lines, as pre-registered in `## Falsification`:

  | arm (`steps`) | timed_out | elapsed_s | old census | `awaiting_body` | per-frame check |
  |---|---|---|---|---|---|
  | `commit` | False | 0.501 | `[]` | `[]` | — |
  | `fetch+commit` | **True** | **8.032** | `[]` | `[]` | main `NOT_REACHED` (`readyState: complete`); child `p5c1` `reached` |
  | `commit+fetch` | False | 0.505 | `[]` | `[]` | — |
  | `fetch+commit+fetch` | False | 0.505 | `[]` | `[]` | — |

  The same two actions in the opposite order give opposite outcomes. The hanging arm ends in
  O-15's state exactly: nothing pending, nothing awaiting a body, the main frame unreached, the
  child reached.
- **O-18. P3, isolated (one page, no app), four stages in one test** (same run as O-17 for the
  first form; the extended form is one more run, `-k p3`, `1 passed in 26.31s`):
  `held (False, 0.033)` with `still_pending_old: []` and `awaiting_body: 1`;
  `held_then_commit (True, 8.033)` with `still_pending_old: []` and `awaiting_body: 1`;
  `after_release (False, 0.519)`. So a held body, with headers already received, is invisible to
  the original census, does not disturb an already-fired `networkidle` on its own, and does
  withhold it once a frame commit forces the recalculation.

---

- **O-19. Mutation check on the instrument.** With the `requestfinished` listener removed
  (`page.on("requestfinished", ...)` replaced by `pass`), P3 fails its own control:
  `AssertionError: probe void: not at rest` (`1 failed, 9 deselected in 17.59s`, pytest exit 1),
  because every completed request then reads as awaiting a body. The file was restored from a copy
  and its sha256 prefix verified equal (`c9bfddd9f6c47bf9`) before anything else ran.

- **O-20. Natural-capture attempt: no capture.** The real test, 30 iterations in one pytest
  process (in-process loop plugin, `-p no:rerunfailures`), 6 CPU busy-loop processes on an 8-core
  machine, local Windows, Playwright 1.60.0: `30 passed, 270 deselected in 486.47s`, wrapper
  marker `LOOP_DONE pytest_exit=0`, 0 `FAILED`, 0 `[settle-instrument]` exception records. The
  largest `networkidle_s` over the 30 runs' reaches was 0.679 s. The loader processes were killed
  and no stray process of this session's was left. That is a rate datum, not evidence of a fix:
  at the 3.3% per-attempt rate item 30 measured on CI, 30 clean attempts has probability about
  0.37, and these were local runs, not the CI runners the failures came from.

---

## Falsified

- **F-3. "P3 arm A returns within about 1 s."** This was the dossier's own pre-registered
  expectation from O-12, and it is false: a hidden `about:blank` iframe commit, after the page had
  been idle and with nothing held, left `networkidle` unreached for the full 8 s (O-13).
  The reading of O-12 as "a child commit alone re-arms within 500 ms" is wrong for this driver
  and page. (See I-8 for what replaces it. That replacement is a hypothesis.)
- **Not a falsification, and must not be read as one:** P3 arms B and C. They ran after arm A had
  already left the page in the stuck state, so their timeouts say nothing about whether a held
  body blocks `networkidle`. They do not test I-1. The design had no isolation between arms; P5
  below runs each arm on a fresh page.
- The prior dossier's F-1 and F-2 stand and are not re-opened here.

---

## Inferred

**Every entry below is a hypothesis, not a finding.**

- **I-1 (R1). A request whose headers arrived and whose body did not finish is invisible to the
  census (O-5) and still counted by Playwright as in flight.** Playwright documents `response`
  as status-and-headers-received and `requestfinished` as body-downloaded; this branch has not
  confirmed that against the installed version. If true, a slow or stalled body (for example the
  921 KB `paged.polyfill.js`, O-6) shows `still_pending_requests: []` while `networkidle` is not
  reached. What would settle it: probe P3 below, and a real capture with `awaiting_body` filled.
- **I-2 (R2).** Something Playwright counts as in flight that never surfaces as a page-level
  `request` event. Not yet characterised; the instrument cannot see it either way.
- **I-3 (R3). A frame lifecycle reset with no open request.** A child frame attaches or
  re-commits after reach 8, and `networkidle` is withheld until that frame's own lifecycle
  completes. Candidates: two `location.replace` navigations racing (O-7), or the preview document
  reworking itself. What would settle it: probe P4, and the frame timeline in a real capture.
- **I-4 (R4, the null). Slowness only.** The body completes but takes more than 30 s under CI
  load. This is I-1 with a finite stall, separated from it by `t_finished` in the widened census.
- **I-5. The 2026-10-07 entry's inference that the unbounded wait in the instrument is "the
  timeout's own"** (item 30) is consistent with O-1 and is not contradicted here. It explains
  why the timeout is 30 s and not 5 s, and says nothing about why `networkidle` is not reached.
- **I-6. P1's result (O-8) implies the old census would have listed a held request.** This was
  not observed: P1 did not print the census. Treat it as unverified.
- **I-7 (refines I-1 and I-3, from O-12 only; unproven).** In this driver version `networkidle` is
  not a pure level signal: a request that starts after it fired does nothing until a later
  lifecycle event (a frame commit, `load`, `DOMContentLoaded`) triggers a recalculation, and then
  the gate is re-opened and must be re-earned by every frame. The failure shape that fits O-2 and
  O-3 is: after reach 8, `_refreshLivePreview` (O-7) starts a request and commits the preview
  iframe; the main frame's `networkidle` is removed (O-12); the iframe's `networkidle` is then
  never re-fired because some request in that frame's inflight set never reaches
  `reportRequestFinished`, while the census (O-5) already counted it as done once `response`
  arrived. This predicts `awaiting_body` filled and the preview frame NOT_REACHED. It does not
  explain *why* a body would not finish, and it has not been observed. **Weakened by O-15:** the
  state the probes reached had every child frame reached and `awaiting_body` empty, which is not
  what I-7 predicts. I-7 is not dead (P3's arms B/C never tested it in isolation), but I-8 now
  fits the observed shape better.
- **I-1 status after O-18:** *capable*, in isolation, and invisible to the original census. That
  is not a finding that it happens in CI: a held body is simply a request in flight, and the
  widened census is what tells it from I-8 (`awaiting_body` filled versus empty).
- **I-8 (replaces I-7 as the leading hypothesis; capability shown by P5/O-17, cause on CI
  unproven).** The hold is the **main frame's own
  `_firedNetworkIdleSelf` flag**, a Playwright-internal bookkeeping gap, and not any request or
  child frame. The chain, from O-12's code read and consistent with O-13..O-16:
  1. The main frame has fired `networkidle` (its flag true, timer spent).
  2. A main-frame request then starts and finishes. `_inflightRequestStarted` calls
     `_stopNetworkIdleTimer`, which sets the flag **false**; on finish `_startNetworkIdleTimer`
     returns early because `networkidle` is still in the fired set, so **no timer is started**.
  3. A child frame commits. `_onClearLifecycle` → `mainFrame()._recalculateNetworkIdle(child)`:
     the main frame is not idle (flag false), so its fired `networkidle` is **deleted**.
  4. The child re-fires its own `networkidle`, but the main frame's flag stays false and nothing
     restarts its timer. It is restarted only when a **later main-frame request finishes**
     (consistent with O-16's 0.513 s recovery after the held fetch finished).
  So `networkidle` is order-dependent: *main request finishes → child commit* hangs;
  *child commit → main request finishes* does not. In the app that order is a race between the
  preview refresh's probe `fetch` (a main-frame request, O-7) and the iframe navigation it then
  starts, which would explain a ~3% rate, a retry that passes at once, and the empty census.
  **What would confirm it:** P5 below (isolated, order-swapped arms), and a natural capture whose
  frame timeline shows a preview-iframe `framenavigated` after reach 8 with the main frame
  `NOT_REACHED` and every child reached. **What would kill it:** P5's `fetch_then_commit` arm
  returning promptly.
- **I-9 (consequence if I-8 holds; unproven).** Production `_wait_settled` bounds this wait to 5 s
  and swallows the timeout (`ui_pages/wizard_compose.py:93-94`), so there the hang would cost 5 s
  and not fail. Every traceback recorded in O-1 goes through the test instrument's unbounded wait
  (`:163`). The instrument was added by the 2026-07-31 branch, and item 30's recorded recurrences
  begin 2026-08-03; the single 2026-07-28 sample predates the instrument and the 5 s bound, and
  had the unbounded wait in production code. If that is right, the instrument turns a 5 s stall
  into a 30 s failure, and the underlying stall is not specific to this test.

---

## Falsification

**Instrument first, then three experiments. Each is pre-registered here, before any of them runs.**
All are observe-and-report; none asserts a winner. A capability probe shows a mechanism is
*sufficient* to produce the symptom in a forced form. It does not show that mechanism caused any
recorded CI failure, and the record must say so.

**Instrument (commit 1, tests only).** The test keeps its unbounded `networkidle` wait as the
trigger, so a natural failure still fails and `ci_wait` / `flake_rates` still count it. It adds:
a `requestfinished` listener; per-request `resource_type`, frame URL and `t_request` /
`t_response` / `t_finished`; `still_pending` split into `awaiting_response` and `awaiting_body`;
a frame timeline (`frameattached`, `framedetached`, `framenavigated`); at failure, `page.frames`
and a per-frame `networkidle` check with a short timeout.

- **P3 (I-1, I-7).** **Revised before any probe ran, after reading the driver (O-12).** The first
  draft was "fire a held fetch, then wait for `networkidle`". O-12 says a late request alone does
  not remove an already-fired `networkidle`, so that draft would most likely have returned
  immediately and been misread as "a held body does not block `networkidle`" — a narrowed
  instrument hiding its rival. The revised probe is three arms in one test, a `127.0.0.1` server
  that sends headers (CORS-open, chunked) and one chunk, then holds the body:
  - *Arm A (trigger only, control):* page idle; append an `about:blank` iframe (a frame commit);
    wait `networkidle` with an 8 s bound. Expected from O-12: returns within about 1 s.
  - *Arm B (held body, no trigger):* the held fetch is open and `awaiting_body` lists it; wait
    `networkidle`. Expected from O-12: returns immediately (nothing recalculated).
  - *Arm C (held body + trigger):* with the same fetch still held, append a second `about:blank`
    iframe, then wait. Expected from O-12: times out at 8 s.
  - Then release the body and record that `networkidle` is re-reached (the recovery control).
  - *Controls, which void the probe if they fail:* the page is idle before arming (a
    `networkidle` wait that raises), and the widened census lists the held request under
    `awaiting_body` before arms B and C.
  - *Reading it:* Arm C times out with `still_pending_requests` empty and `awaiting_body` filled
    means I-1/I-7 is capable and invisible to the old census. Arm C returning normally means a held
    body with a frame commit does not block `networkidle` in 1.60.0, and I-1 is dead as stated.
    Arm A timing out means the trigger alone is a hazard (a different finding).
- **P4 (I-3).** **Revised before any probe ran.** The first draft's arm (a), appending an
  `<iframe>` with no `src`, is the same action as P3's arm A and is not repeated. P4 is now
  `location.replace` on `#livePreviewFrame` to the preview URL: first once (the control, the
  app's ordinary shape), then twice back to back (the first superseded before it commits).
  Each arm waits until the frame timeline shows the matching `framenavigated` before it starts
  its bounded `networkidle` wait (O-12: before the commit the main frame still holds its fired
  `networkidle`, so an early wait would return instantly and mean nothing).
  - *Controls:* idle before arming; the single navigation's commit and the double's second
    commit are both seen in the frame timeline.
  - *If the double times out with both census lists empty and a frame reporting not-idle:* I-3 is
    capable, and the per-frame check names the frame.
  - *If both arms return normally:* I-3's named candidates are dead as capability claims.
- **P5 (I-8). Pre-registered after O-13..O-16 and BEFORE it runs.** Pure Playwright mechanism,
  with the Compose app out of the picture: each arm on a **fresh page** (parametrized test, so
  there is no cross-arm contamination, which voided P3's B and C). Page: the live server's
  `/static/style.css` (a document with a window, no app JS). Steps: `goto`, wait `networkidle`
  (control: reached), then the arm's actions, each waited for before the next (a same-origin
  `fetch` is "done" when the census shows nothing pending and nothing awaiting a body; a
  frame commit is "done" when the timeline shows its `framenavigated`), then an 8 s bounded
  `networkidle` wait, then the per-frame check. Arms and what I-8 predicts:
  - `commit_only`: hidden iframe commit. Predicted: returns in about 0.5 s.
  - `fetch_then_commit`: a fetch finishes, then a commit. Predicted: **times out** (the hang).
  - `commit_then_fetch`: a commit, then a fetch finishes. Predicted: returns in about 0.5–1 s.
  - `fetch_commit_fetch`: fetch, commit, then another fetch. Predicted: returns (the later main
    request re-arms the timer, the same recovery as O-16).
  - *Reading it:* `fetch_then_commit` hanging while `commit_then_fetch` returns promptly, with
    nothing pending and the per-frame check showing main `NOT_REACHED` and the child reached, is
    capability for I-8 and a first-principles reproduction of the CI shape. It still does not
    show that this is what happened on any CI run. `fetch_then_commit` returning promptly kills
    I-8's chain. `commit_only` hanging would mean something other than a main-frame request
    breaks it, and P3's arm A is then the same effect.
  - *The app link, separately:* P3 arm A and P4 `single` (O-13/O-14) already hang in the app, but
    that shows the app's late main-frame requests satisfy step 2, not that CI's runs did.
- **Natural capture.** This test only, `loop_plugin --loop N`, under CPU load calibrated per the
  `reference-cpu-saturation-flake-repro` note (start at about 0.75× cores; if only
  already-known unrelated failures appear, that is a calibration signal). Budget 30 iterations.
  - *A capture with `awaiting_body` filled:* I-1 or I-4, separated by `t_finished`.
  - *A capture with all lists empty and a non-idle frame:* I-3.
  - *A capture with everything empty:* I-2 is live, and the instrument is still too narrow.
  - *No capture in 30:* recorded as a rate datum (the per-attempt rate is 3.3%, so 30 clean
    attempts has probability about 0.36). It is not evidence of a fix.

---

## The fix

Not on this branch. The owner picks the fix and its branch from the evidence recorded above.

---

## Acceptance bar

For this branch (not for item 30): the instrument passes its own control (P3's control arm), the
mutation check holds (removing the `requestfinished` listener makes P3's control fail), each
probe's result is recorded verbatim in `## Observed` or `## Falsified`, and the item 30 `##
Updates` entry says what was and was not established. Item 30 stays `watching`; a closure needs a
falsifiable `verified_by` and a green CI run with 0 `RERUN` markers on the fixed test (C-7, C-11).

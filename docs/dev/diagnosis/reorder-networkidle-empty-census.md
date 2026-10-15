# Diagnosis — keyboard-reorder test times out in `networkidle` with an empty request census

> **Status:** hypothesis only. No mechanism is proven; this branch builds the instrument and the
> capability probes, and does not fix (owner scope answer, 2026-10-14: "Probe only, then report").
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

---

## Falsified

_(Nothing yet on this branch. The prior dossier's F-1 and F-2 stand and are not re-opened here.)_

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

- **P3 (I-1).** A `127.0.0.1` server sends response headers (CORS-open, chunked) and one chunk,
  then holds the body. The page fires an unawaited `fetch` at it after reach 8, then the settle
  runs with `networkidle`.
  - *Control:* the widened census must list the request under `awaiting_body`. If it does not,
    the instrument is broken and the probe result is void.
  - *If `networkidle` times out and the old census fields are empty while `awaiting_body` is
    filled:* I-1 is capable and invisible to the old census.
  - *If `networkidle` returns normally:* a held body alone does not block it in this Playwright
    version, and I-1 is dead as a mechanism. Say so; do not re-chase.
- **P4 (I-3).** After reach 8, (a) append an `<iframe>` with no `src`; then, separately, (b) call
  `location.replace` twice back to back on `#livePreviewFrame`.
  - *If either times out with both census lists empty and a frame reporting not-idle:* I-3 is
    capable, and the per-frame check names the frame.
  - *If both return normally:* I-3's named candidates are dead as capability claims.
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

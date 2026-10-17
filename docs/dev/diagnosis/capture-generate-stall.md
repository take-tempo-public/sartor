# Diagnosis — screenshot capture stalls at Template → Generate (item 140, part a)

> **Status:** cause of the capture stall established (observed in run 1, mechanism confirmed at route level, fix
> verified by one passing live run). Whether the APP should protect a user from the same race is open and is the
> owner's call.
> **Branch:** `fix/capture-generate-stall`

---

## Symptom

`python -m scripts.capture_screenshots --headless --keep-user` stops at step 9 of the wizard walk. The click on
"Continue to Generate →" never shows the Generate panel, so `walkthrough_coverletter_first-generation.png` cannot be
recaptured. The committed image still shows an internal id (`b180`) and the wrong letter date (`March 2025`), which is
what item 140 set out to remove.

---

## Observed

Carried from the item-140 session (2026-10-17); none of it re-run on this branch yet.

- The failing call, from the item-140 dossier: `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:174-179` quotes
  `WizardTemplatePage.continue_to_generate` → `wait_for_selector(Wizard.PANEL_GENERATE)` timing out at
  `scripts/capture_screenshots.py:529`, `ui_pages/wizard_template.py:46`.
- The step code, read this session: `ui_pages/wizard_template.py:43-48` clicks `Wizard.CONTINUE_TO_GENERATE`
  (`ui_pages/selectors.py:295`, `text=Continue to Generate →`) and waits for `#panelGenerate` visible
  (`ui_pages/selectors.py:296`) with `DEFAULT_TIMEOUT_MS`.
- No `generate` LLM call was logged in the failing window, and the kept context held an `approved_composition`:
  `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:176-178`.
- The earlier steps in the same run completed: `llm_calls.jsonl` showed analyze, clarify, recommend and draft_summary
  all `ok` (same lines).
- The `demo` candidate's experiences carry month dates (`2023-01`, `2019-01`, `2017-01`):
  `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:183-185`.
- The server's own logger went silent after the Alembic migration at start-up, so the server log gave no evidence
  (same lines).
- The button's handler, read this session: `templates/index.html:459`,
  `onclick="wizardGoTo(5)"`.

### Probe run 1 (2026-10-17 22:01:46Z to 22:03:37Z, `scripts/capture_stall_probe.py` at `4eccf51`)

Command: `python -m scripts.capture_stall_probe --out <scratchpad>/stall_probe_run1.jsonl --headless --keep-user`
against `FLASK_DEBUG=0 python app.py --no-browser`. Evidence file: `stall_probe_run1.jsonl` (63 lines, scratchpad,
not durable; the key events are excerpted below). **The stall reproduced at the same step** (`capture_raised`,
`TimeoutError … waiting for locator("#panelGenerate") to be visible … 33 × locator resolved to hidden <section
id="panelGenerate" … class="cb-panel hidden">`). The offline check of the probe itself (no LLM calls) is why the toast
log below is populated.

- **The app refused the click on purpose.** Snapshot `before_click` (line 51) and `after_click_failed` (line 60) both
  read `wizardStep 4`, `compositionFrozen true`, `compositionStale true`, `reachable5 false`, `panelGenerate.cls
  "cb-panel hidden"`, and the toast after the click read: "You changed your composition after approving it — click Save
  and continue in Compose (step 3) to approve the changes, then generate." (`cls "corpus-toast error show"`, toast log
  entry at 87469 ms of the page clock). That is `_wizardLockReason(5)`'s stale branch (`static/app.js:7420-7423`). No
  `pageerror`, no `dialog`, no overlay (`overlays: []`), and the button was visible and on top at `after_click_failed`
  (`selfIsTop true`). So the click landed and `wizardGoTo(5)` returned early; the rivals "selector hit another
  element", "modal intercepted" and "JS exception" are **not** what happened in this run.
- **The ordering of the traffic around the freeze** (probe lines 36-47, seconds since probe start; method, route,
  status 200 unless noted):

  ```text
  84.947 POST /api/applications/80/recommend
  85.026 GET  /api/applications/80/composition      body: "composition_stale":false
  87.996 POST /api/applications/80/composition      body: "frozen":true            (Save and continue)
  88.350 GET  /api/users/demo/personas
  88.622 POST /api/applications/80/draft-summary                                    (no user action in the probe)
  88.760 GET  /api/applications/80/preview?template_id=1
  89.014 GET  /api/applications/80/preview?template_id=1
  89.115 GET  /api/applications/80/composition      body: "composition_stale":true
  89.260 GET  /api/applications/80/preview?template_id=2   (pick_template(1))
  ```

  The first `GET composition` (before the freeze) reads `composition_stale false`; the one after the freeze and after
  `draft-summary` reads `composition_stale true`. Body order is the order the bodies were read at the first snapshot
  (lines 52-58); the pairing of each body with its request is by that order and by `composition_stale` flipping, not by
  a request id.
- **The toast "Composition saved (0 pinned, 0 added, 0 excluded)"** appeared at 82295 ms and again as hidden at 84668
  ms (page clock), so the freeze itself reported success.
- **The draft-summary LLM call was in flight when the freeze landed** (free cross-check from `logs/llm_calls.jsonl`,
  UTC end timestamps; the probe's own `api` events are logged at RESPONSE time, so they cannot show a request start):

  ```text
  22:03:13.551  recommend       ok  latency_ms 3782
  22:03:17.209  draft_summary   ok  latency_ms 2346     -> LLM call began about 22:03:14.86
  probe: freeze response t=87.996, draft-summary response t=88.622  (0.626 s apart; 22:03:17.209 - 0.626 = 22:03:16.58)
  ```

  So the draft began about 1.7 s before the freeze response and ended about 0.6 s after it. Run 1 spend, by
  `compute_call_cost` over those five rows: `$0.114`.
- **The capture script reaches Save-and-continue without the settle gate.** `ui_pages/wizard_compose.py:140-147`
  (`wait_cards`) waits for `#panelCompose` visible and the first `.compose-experience-card`, nothing else; its only
  caller is `scripts/capture_screenshots.py:331`. All twelve other callers of `continue_to_template()` (grep over
  `*.py`, 2026-10-17) reach it through `WizardComposePage.open()`, which ends in `_wait_settled()`
  (`ui_pages/wizard_compose.py:97-138`, `Compose.SETTLED` = `data-compose-ready` present and
  `data-compose-bg-pending` absent).
- Code facts (read, `file:line` so a reader can check): the arrival auto-fire is `_fireDraftSummary(false)` at
  `static/app.js:7895-7901`, skipped only when the composition is already approved or a draft exists; the route writes
  `composition_overrides.summary_text` (`blueprints/applications.py:2210-2219`), and `summary_text` belongs to
  `COMPOSITION_INPUT_KEYS` via `composition_overrides` (`hardening.py:2108-2114`); staleness is `stamped digest !=
  current digest` (`hardening.py:2129-2152`); `saveCompositionThenNext` freezes without waiting for background work
  (`static/app.js:10044-10065`).
- Not recorded by this run (so unknown): the request body of `POST draft-summary` and its response body
  (`draft-summary` is not in the probe's `_BODY_ROUTES`), and the digest itself before and after the draft.
- Side effect to undo: the run overwrote eight `docs/screenshots/*.png` (`git status` after the run shows them
  modified); they are restored with `git checkout` and are not part of this fix.

### Experiment 2 result (2026-10-17, no spend)

Command: `python -m pytest tests/test_composition_staleness.py -k "TestDraftLandingAfterTheFreeze or TestCompositionResponses" -p no:cacheprovider -q -x -p no:randomly`

```text
collected 22 items / 18 deselected / 4 selected
tests\test_composition_staleness.py ....                                 [100%]
====================== 4 passed, 18 deselected in 8.38s =======================
```

The new test `TestDraftLandingAfterTheFreeze::test_a_summary_draft_persisted_after_the_freeze_stales_the_approval`
passed: `composition_stale` is `False` right after the freeze (its control arm) and `True` after `POST /draft-summary`
persists a summary. No rerun is shown in the output. **The mechanism is confirmed at the route level**: a summary
draft that lands after the freeze stales the approval. What stays unobserved is that THIS is what happened inside run 1
(the digest itself was not recorded), so the sequence in run 1 is "consistent with" it, with the draft's persist as the
only context writer between the two `GET /composition` calls.

### Probe run 2, after the fix (2026-10-17 22:08:32Z to 22:10:38Z, commit `91e6cf2`)

Command: `python -m scripts.capture_stall_probe --out <scratchpad>/stall_probe_run2.jsonl --headless` (no `--keep-user`).

```text
✓ capture complete in 125.2s
  · removed configs\demo.config / resumes\demo / output\demo / scripts\_tmp_capture
PROBE_DONE ec=0
```

- The same snapshot that failed in run 1 now reads (probe lines 52 and 61): `before_click` `wizardStep 4`,
  `compositionFrozen true`, **`compositionStale false`**, **`reachable5 true`**; `after_click_ok` `wizardStep 5`. No
  `pageerror`, no `dialog`, no `continue_to_generate_failed`, `end status 0`.
- **The recaptured `docs/screenshots/walkthrough_coverletter_first-generation.png` was read:** the letter (editor and
  preview) is dated "October 17, 2026", the run date, and shows no `b`/`e`/`t` id. The committed image it replaces
  showed `b180` and `March 2025`. `walkthrough_step6_download-with-refine.png` from the same run was also read and
  shows no id; it and the other eight PNGs the script overwrote were restored with `git checkout`, so only the
  cover-letter image changes.
- **Spend, by `compute_call_cost` over the telemetry rows of each window:** run 1 `$0.114` (5 calls), run 2 `$0.192`
  (7 calls), `$0.306` in total; the cap for this item was about `$0.45`.
- n = 1 passing run. One pass does not show the stall cannot recur: the app-side race is still there for any caller
  that clicks Save-and-continue early.

---

## Falsified

- **"A selector, overlay or JS exception stopped the click"** (the rivals listed under Inferred): the click landed, no
  `pageerror`/`dialog`/overlay was recorded, and the page answered with its own lock toast (probe lines 51, 60).
- **"The capture failure is the item 139 stale-demo-rows / month gate problem."** The demo experiences have `YYYY-MM`
  start dates (above), so the month gate does not apply.
  `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:194-196`.

---

## Inferred

**All of this is read from code, none of it observed.** `wizardGoTo` (`static/app.js:7431`) returns early with
`_toast(_wizardLockReason(step), true)` when `_wizardReachable(step)` is false (`static/app.js:7372`). For step 5 that
is the case when `lastContextPath` is empty, when `_compositionFrozen` is false, or when it is frozen but
`_compositionStale` is true (`static/app.js:7418-7429`). Rivals the instrument must not hide:

- a JavaScript exception in `_wizardRender` or `_renderGenerateStepCopy`;
- the `text=` selector matching a different or obscured element;
- the panel becoming visible but failing Playwright's visibility check;
- a modal or drawer intercepting the click;
- the server's freeze response saying `frozen: false` although the context file holds an `approved_composition`.

What I would have to SEE to know: the page's state variables and any toast text at the moment of the click, and the
network and console events leading to it. (Run 1 supplied those; see Observed.)

**Hypothesis after run 1 (unproven):** the capture clicks Save-and-continue while the arrival `draft_summary` is still
in flight. The freeze stamps a digest taken before the draft's `summary_text` is written; the draft then writes
`composition_overrides.summary_text`, the digest no longer matches, and `_wizardReachable(5)` is false. What Observed
establishes is the order (draft in flight at the freeze, `composition_stale` flipping to true afterwards) and that no other
route in the traffic wrote the context between the two `GET /composition` calls except `draft-summary`; it does not show
the digest changing. The deterministic test below is what turns it into a finding.

**Separate, owner's question (not proven reachable by a user):** if a real user clicks Save-and-continue inside the same
window (an arrival draft takes seconds), the same sequence would lock Generate behind a message saying they changed
something they did not. Not examined here; see the handoff.

---

## Falsification

**Experiment 2 (stated before it is run): the draft-lands-after-freeze characterization.** In the real-route rig
(`tests/test_frozen_composition_staleness.py::rig`, analyzer stubbed, no browser, no spend): freeze, read
`composition_stale`, `POST /draft-summary` with `analyzer.draft_positioning_summary` stubbed, read `composition_stale`
again. This test asserts the behaviour that exists today, so its polarity is the reverse of the usual one:

- **If it passes** (false before, true after): the mechanism is confirmed. A summary draft that persists after the
  freeze makes the approval stale. The capture then needs to wait for Compose to settle before it clicks
  Save-and-continue; whether the app should also protect a user is the owner's call.
- **If it fails** (stale stays false after the draft): the hypothesis is dead. Do not fix. Widen the instrument (record
  request starts and the digest) and report.

**Experiment 1.** `scripts/capture_stall_probe.py` runs the capture's own steps and records, around the click and on
timeout: `console`, `pageerror` and `dialog` events; each `/api/` request and response; `_wizardStep`,
`lastContextPath`, `_compositionFrozen`, `_compositionStale`, `_wizardReachable(5)`, `_wizardLockReason(5)`; the toast
text; `#panelGenerate`'s classes and box; the match count and visibility of the button's selector; any open modal or
drawer; and a failure screenshot. It is scoped wider than any one hypothesis above.

- **If the stall reproduces:** the recorded state names which rival holds; write it under `## Observed`, then fix that.
- **If the stall does not reproduce:** one run proves nothing about the 2026-10-17 failure. Record it as such, do not
  fix, and ask the owner before a second paid run.

---

## The fix

**Scope: the capture only.** `WizardComposePage.wait_cards` (`ui_pages/wizard_compose.py`, one caller:
`scripts/capture_screenshots.py:331`) now also waits for `Compose.SETTLED` before it returns, so the script clicks
Save-and-continue after the arrival draft has landed and the freeze stamps a digest that includes it. This is the
condition every UX-suite path already waits for via `open()` -> `_wait_settled()`. No app code and no gated surface
(`ui_pages/selectors.py`, `ui_pages/base.py`) is touched; `Compose.SETTLED` is only referenced.

Test, `tests/test_wizard_compose_wait_cards.py` (recording page, no browser). Without the added line:

```text
E   AssertionError: assert '#composeList[data-compose-ready]:not([data-compose-bg-pending])' in ['#panelCompose', '#composeList .compose-experience-card']
FAILED tests/test_wizard_compose_wait_cards.py::test_wait_cards_returns_only_after_the_settle_gate
============================== 1 failed in 3.90s ==============================
```

With it: `1 passed in 3.30s`. Known limit (C-0): it checks that the settle gate is waited on, not that the settle gate is
sufficient; the live recapture below is the check of that.

**Not fixed here, the owner's question:** the app-side race (a user clicking Save-and-continue while an arrival draft is
in flight). Experiment 2 shows the staling is today's behavior; `TestDraftLandingAfterTheFreeze` pins it as a
characterization and says so.

---

## Acceptance bar

The full capture runs end to end, the recaptured `walkthrough_coverletter_first-generation.png` is read and shows the
run's own month and no `b`/`e`/`t` id, and `python -m scripts.gate --result` reads PASSED on the final tree.

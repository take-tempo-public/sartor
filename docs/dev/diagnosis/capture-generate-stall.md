# Diagnosis — screenshot capture stalls at Template → Generate (item 140, part a)

> **Status:** hypothesis only. Cause NOT established; the instrument has not run yet.
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

---

## Falsified

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
network and console events leading to it.

---

## Falsification

**The experiment.** `scripts/capture_stall_probe.py` runs the capture's own steps and records, around the click and on
timeout: `console`, `pageerror` and `dialog` events; each `/api/` request and response; `_wizardStep`,
`lastContextPath`, `_compositionFrozen`, `_compositionStale`, `_wizardReachable(5)`, `_wizardLockReason(5)`; the toast
text; `#panelGenerate`'s classes and box; the match count and visibility of the button's selector; any open modal or
drawer; and a failure screenshot. It is scoped wider than any one hypothesis above.

- **If the stall reproduces:** the recorded state names which rival holds; write it under `## Observed`, then fix that.
- **If the stall does not reproduce:** one run proves nothing about the 2026-10-17 failure. Record it as such, do not
  fix, and ask the owner before a second paid run.

---

## The fix

_Only after the experiment above has produced an observation._

---

## Acceptance bar

The full capture runs end to end, the recaptured `walkthrough_coverletter_first-generation.png` is read and shows the
run's own month and no `b`/`e`/`t` id, and `python -m scripts.gate --result` reads PASSED on the final tree.

```toml
schema = 1
id = 155
kind = "item"
title = "UX flake: test_card_company_editable_and_persists saw 'Notes saved' where it waits for 'Company saved'"
status = "open"
decision_owner = "agent"
branches = ["fix/wiki-relevance-cited-scripts"]
refs = [
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py:125",
  "static/app.js:6519-6534",
  "static/app.js:6571-6575",
  "ui_pages/prior_apps.py:54-62",
]
summary = "A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified."
```

**Observed (2026-10-07, PR #159, run 37569283583, job 112624033244, "UX / a11y / PDF (Playwright, py3.12)").**
- `python -m scripts.ci_wait 159` exited **3** (green with reruns):
  `tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_persists - 1 of 3 attempts failed`.
- The failed attempt's traceback (job log, 2026-10-07T04:01:37Z):

  ```
  tests/ux/regression/test_20260611_prior_app_resume_robustness.py:125: in test_card_company_editable_and_persists
      expect(page.locator("#_corpusToast")).to_have_text("Company saved")
  E   AssertionError: Locator expected to have text 'Company saved'
  E   Actual value: Notes saved
  E     9 x locator resolved to <div id="_corpusToast" class="corpus-toast show">Notes saved</div>
  E     5 x locator resolved to <div id="_corpusToast" class="corpus-toast">Notes saved</div>
  ```
- The retry passed (`PASSED [ 16%]`, 04:01:39Z).
- PR #159's diff touches only `scripts/wiki_relevance.py`, its test and docs; nothing in it reaches
  `static/`, `ui_pages/` or the UX suite.
- Code read (not an observation of the failure): the notes textarea's blur handler PUTs and toasts
  `Notes saved` on **every** blur, changed or not (`static/app.js:6519-6534`). The company blur
  handler toasts `Company saved` only after its PUT succeeds (`static/app.js:6571-6575`).
- Not previously tracked: no item, ledger row or diagnosis names this test. The flake-rate shards
  under `docs/dev/flake-rates/runs/` list it only among collected node ids.

**Inferred, unproven:** something blurred the notes textarea during or after the company edit (focus
landing on it when the modal opened, for example). Either the company blur did not fire, or its PUT
had not finished within the 5 s wait. Not reproduced; the failing attempt's focus order was not
captured.

**Fix direction (C-7):** instrument first. Record the focus and blur order plus both PUTs on a
failing attempt (a loop of the single test under CPU load, per memory
`reference-cpu-saturation-flake-repro`). Then decide between the app (a notes save on an unchanged
blur; the toast being shared) and the test (waiting on a shared toast instead of the PUT response).

## Updates

### 2026-10-07 — filed on `fix/wiki-relevance-cited-scripts` (PR #159 close-out)

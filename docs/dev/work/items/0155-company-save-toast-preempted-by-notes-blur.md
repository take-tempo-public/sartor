```toml
schema = 1
id = 155
kind = "item"
title = "UX flake: test_card_company_editable_and_persists saw 'Notes saved' where it waits for 'Company saved'"
status = "closed"
decision_owner = "agent"
branches = ["fix/wiki-relevance-cited-scripts", "fix/test-reliability"]
refs = [
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py:125",
  "static/app.js:6519-6534",
  "static/app.js:6571-6575",
  "ui_pages/prior_apps.py:54-62",
  "docs/dev/diagnosis/test-reliability.md",
  "docs/dev/blast-radius/test-reliability.md",
]
summary = "A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified."
resolution = "2026-10-09, fix/test-reliability: the modal opens with focus on the notes textarea, so set_company's fill() blurred it and fired an unchanged-notes save; when that response landed after the company save's, 'Notes saved' overwrote 'Company saved' in the shared toast (observed locally: 3 of 30 runs under load, all with the meta response first; diagnosis O5-O6). Fixed on both sides (owner's choice): the notes blur saves only a change, and the test waits on the PUT /meta response and reads the company from the reopen's GET body. The CI attempt itself left no request log, so its own mechanism stays inferred."
verified_by = [
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_persists",
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_company_save_survives_a_later_notes_response",
  "docs/dev/diagnosis/test-reliability.md (Acceptance bar: 3/30 -> 0/30 under the same load)",
]
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

### 2026-10-09 — fix/test-reliability: closed

- **The mechanism, observed locally** (`docs/dev/diagnosis/test-reliability.md` O5–O6). The
  modal opens with focus on the notes textarea. `set_company`'s `fill()` therefore blurred it,
  which sent PUT `/notes` even though the notes hadn't changed. Under 6 CPU loaders, 3 of 30 runs
  failed with the CI text. In all three the meta response arrived first: `Company saved` showed
  for 5–112 ms, then `Notes saved` replaced it. All 27 passing runs had the notes response
  first.
- **The CI attempt's own mechanism stays inferred.** It fits the same shape, but it left no
  request log.
- **Fixed on both sides,** the owner's choice:
  - the notes blur saves only a change, like the title and company handlers;
  - the test waits on the PUT `/meta` response, reads the company back from the reopen's GET
    body, and asserts an unchanged notes field sends no PUT.
- **Same load, same machine:** 3/30 → 0/30. The forced-order test passed 3 of 3. With the app
  half removed, the fixed test fails ("an unchanged notes blur still saved").

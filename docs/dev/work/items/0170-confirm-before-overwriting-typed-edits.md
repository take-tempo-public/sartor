```toml
schema = 1
id = 170
kind = "item"
title = "Confirm before a generate or a new cover letter overwrites a typed edit (Continue / Cancel)"
status = "open"
decision_owner = "agent"
branches = ["feat/confirm-before-overwriting-typed-edits"]
refs = [
  "blueprints/generation.py",
  "static/app.js",
  "templates/index.html",
  "docs/dev/blast-radius/confirm-before-overwriting-typed-edits.md",
  "tests/test_confirm_overwrite_edits.py",
  "docs/dev/diagnosis/run-row-letter-edit-shadow.md",
  "docs/dev/diagnosis/regenerate-keeps-cover-letter.md",
]
summary = "A typed edit is overwritten with a notice only after (résumé) or none (letter); warn first, Continue or Cancel."
```

**Owner request, 2026-10-14** (during close-out of `fix/run-row-letter-edit-shadow`): "add an
alert to the user when a typed edit will be overwritten and give them the choice to continue or
cancel." The owner chose, in answer to three questions: a **separate branch after the PR for
item 163 merges**; **all three overwrite cases**; the **server handshake** for the résumé case.

## The three cases

| # | When a typed edit is lost | Today | Who knows in advance |
|---|---|---|---|
| 1 | A frozen Compose re-approval changes the résumé, so the typed **résumé** edit is not carried over (`_typed_edits_disposition`, decision 4 of `fix/frozen-composition-staleness`) | A notice **after** generating: `editsDiscardedNotice`, `static/app.js` (`data.edits_discarded`) | Only the server, once the frozen doc is rendered to markdown and compared with `last_generated_resume` |
| 2 | A generate with `generate_cover_letter: true` produces a letter, which consumes the typed **letter** edit (`resolve_cover_letter_after_generate`; item 163 now clears the run row too) | None | The client: a typed letter edit exists and the request asks for a letter |
| 3 | The detached `/api/generate-cover-letter` pops the typed letter edit (`run_generate_cover_letter`) | None | The client: a typed letter edit exists and the user clicked Generate cover letter |

## Decided by the owner

- Warn and offer **Continue** or **Cancel** in all three cases. Cancel generates nothing and
  changes nothing.
- Case 1 uses a **server handshake**, not a client guess: the generate routes answer with a
  pre-persist `409` such as `{error, edits_would_be_discarded: true}`, and the client re-sends
  with an explicit confirm flag after Continue.

## Constraints to carry into the plan (read from code; not yet verified against a built version)

- **Check before any LLM spend.** `_assemble_from_frozen_composition` makes the cover-letter LLM
  call inside the assemble. The would-be-discarded test (`json_resume_to_markdown` of the frozen
  doc against `last_generated_resume`) must run **before** it, or Cancel wastes a paid call.
- **Both routes.** `/api/generate` and `/api/generate/stream` duplicate the preamble; the
  `composition_stale` 409 (`_stale_composition_response`, called in both before any LLM work)
  is the precedent. Parity is a requirement, as `fix/regenerate-keeps-cover-letter` found.
- **Reuse `cbConfirm`** (`static/app.js`): a promise-returning in-app modal with Esc, focus trap
  and focus restore; `danger: false` for a confirm that is not a delete. Do not add a native
  `confirm()`.
- **Contract change.** The generate routes' request and response shapes are consumed by
  `static/app.js`, the wiki (`route-surface`, `frontend-wizard`) and several test files:
  enumerate them grep-complete into `docs/dev/blast-radius/<slug>.md` **before** the first edit
  (C-10). Include the SSE client path and every name the flag goes by.
- **Instrument first** for any behaviour not yet observed (C-7). The three cases above are read
  from code; the UI path has not been driven. Cover it in the UX tier (`pytest -m ux`) and keep
  the axe a11y gate green for the new dialog copy.
- **Item 163's `carry_edits` question stays separate**: whether a typed letter edit should be
  kept over a newly produced letter on the frozen path is an open owner question
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5). This item must not decide it.

## Updates

### 2026-10-14 — filed on `fix/run-row-letter-edit-shadow`

Filed during that branch's close-out, at the owner's request, so it is on the board before the
merge rather than a follow-up branch. Not started.

### 2026-10-14 — instrumented on `feat/confirm-before-overwriting-typed-edits`

Commit 1 of the branch: the consumer dossier
(`docs/dev/blast-radius/confirm-before-overwriting-typed-edits.md`) and the instrument
(`tests/test_confirm_overwrite_edits.py`: 14 controls, 9 strict-xfail defect arms). No
production code changed yet.

**Observed on `main` @ `13d8117`** (`--runxfail`, 9 arms, 0 `ControlFailed`, every arm fails at
`assert res["status"] == 409`, `tests/test_confirm_overwrite_edits.py:244` at that commit):

| Arm | Route | Edit at risk | status | LLM calls spent | state changed |
|---|---|---|---|---|---|
| A1 | `/api/generate`, `/api/generate/stream` | typed résumé (frozen, composition changed) | 200 | 0 | yes |
| A2 | both | résumé and letter (frozen, letter requested) | 200 | 1 | yes |
| A3 | both | letter (legacy path, letter requested) | 200 | 1 | yes |
| A4 | both | letter (frozen path, letter requested) | 200 | 1 | yes |
| A5 | `/api/generate-cover-letter` | letter (detached) | 200 | 1 | yes |

The one LLM call is spent **before** the edit is dropped: the combined résumé-and-letter
`generate()` on the legacy path (A3), the letter call inside
`_assemble_from_frozen_composition` on the frozen path (A2, A4), and the letter call on the
detached route (A5). So the pre-check has to run ahead of the assemble, not inside it. A1
spends nothing (the frozen résumé path has no LLM call): its cost is the lost edit alone.

**Read from code, not driven** (declared limit): cases 2 and 3 have no shipped client
trigger. The client never sends `generate_cover_letter` (`static/app.js:1715-1717`), and
`#btnGenerateCover` is hidden once a letter exists (`_updateCoverLetterButtons`). They are
reachable by a direct POST only. So the server floor covers all three cases, case 3 also
gets its client handler, and the UX tier can drive cases 1 and 4 only.

**A fourth case, found while enumerating** (owner chose to include it, 2026-10-14):
`runGeneration` overwrites *unsaved* Step 6 editor text with no gate, because
`_gateEditsBeforeAction` is wired only to refine (`static/app.js:2724`) and iterate-clarify
(`:3055`). Case 4 reuses that gate; it needs no server change.

### 2026-10-14 — server handshake built (commit 2)

`blueprints/generation.py` only. New request flag `confirm_discard_edits`; new pre-LLM `409`
`{error, edits_would_be_discarded: true, discards: [...]}` on all three routes, from one
predicate, `_pending_discards`.

- **Observed after the change:** all 23 instrument tests pass (the 9 defect arms with their
  markers deleted); 192 passed across the instrument and every suite that touches these routes.
  Exactly seven existing drives failed first, and they were the seven the dossier had decided
  as "update (drive)" (rows 16-17): they now send the user's Continue. The carry arms
  (`A5`, `D6`, `B5`) passed unchanged, as classed.
- **Mutation checks**, file restored and sha256 verified after each: skipping the check on the
  stream route alone fails exactly its four arms (A1-A4 `[stream]`); making `_pending_discards`
  ignore `carry_edits` fails exactly the two carry controls (`C4` `[json]`, `[stream]`).
- **Not driven:** the over-approximation noted on `_pending_discards` (a requested letter the
  model returns empty would have kept the edit, and the route still asks) has no test; it
  needs a failed letter call and the cost of being wrong is one needless confirm.
- **Declared, not fixed:** the shipped client shows the new `409` as a plain error until
  commit 3, so this branch lands as one PR and is not user-visible half-built.

### 2026-10-14 — client built; UX tier red on one test, cause observed (commit 3 not made)

`static/app.js` (`runGeneration` split into a wrapper plus `_runGenerationOnce`;
`runGenerateCoverLetter` likewise), `ui_pages/selectors.py` (additive), the browser test
`tests/ux/regression/test_20261014_confirm_overwrite_edits.py`, docs and CHANGELOG are
written and **uncommitted**, because the full UX tier is not green.

- **Observed:** `pytest -m ux`: `1 failed, 171 passed, 2 xpassed in 667 s`, 0 `RERUN` lines,
  `PYTEST_EXIT=1` (the harness reported exit 0). The new test passed. The failure is
  `test_20261012_regenerate_keeps_cover_letter.py::test_b7_...`: after a detached cover
  letter, clicking Generate at Step 5 opens `#editModal` ("Your edits aren't saved yet") with
  nothing typed, so no request is sent and the test times out waiting for `iter 2`.
- **Cause, observed with a throwaway diagnostic (deleted):** `_detectEdits().resumeEdited`
  is `false` right after the first generate and `true` right after
  `runGenerateCoverLetter`, with no typing. The résumé editor's DOM is text nodes joined by
  `<br>`. `_readEditorText` un-hides only the element's own `hidden` class; once the
  Cover-letter tab is active the element's *ancestor* (`#tabResume`) is `display:none`, so
  `innerText` falls back to `textContent`, which drops the `<br>`s: 207 characters against
  218 in `lastGeneratedResume`. The text differs, so an edit is reported.
- **Not caused by this branch:** `_detectEdits` and `_readEditorText` are untouched. The false
  positive predates it and is reachable today by Refine and Iterate in the same state (not
  driven there). Wiring Generate to the gate (case 4) is what exposes it on an ordinary
  second Generate.
- **Other consumers of `_readEditorText`** (grep, `static/app.js`): `downloadResume` (`:3547`),
  `downloadCoverLetter` (`:3573`), the live-preview refresh (`:7949`). Whether the résumé
  download posts newline-less text when the Cover-letter tab is active was **not driven**.

### 2026-10-14 — editor-text read fixed at the helper; UX tier green (commit 3)

Owner decision (2026-10-14): fix `_readEditorText` itself, not only `_detectEdits`.

- **Instrument first** (`tests/ux/regression/test_20261014_editor_text_hidden_tab.py`), run on
  the unfixed helper with the Cover-letter tab active, all controls holding: the read was 207
  characters against 218 in `lastGeneratedResume`, `resumeEdited` was `true`, and
  **`downloadResume()` POSTed 207 characters to `/api/download-edited`**. The download half was
  inferred in the entry above and is now observed.
- **Fix:** `static/app.js` `_readEditorText` measures a rendered off-screen copy
  (`_renderedInnerText`) only when the node has no layout; the rendered case is the unchanged
  `innerText` read. After: 218 = 218, `resumeEdited` `false`, a 218-character download body.
- **Consumers decided before the edit:** dossier rows 28-33 (`_detectEdits`, the Refine and
  Iterate gates, both downloads, the live-preview refresh).
- **Observed, full tier** (`pytest -m ux`, run 2): `173 passed, 2 xpassed in 489 s`,
  `PYTEST_EXIT=0`, 0 `FAILED`/`ERROR`, 0 `RERUN`. Run 1 was `1 failed, 171 passed`.
  B7 and both new tests are in the passing set.
- **Mutation checks on the client** (`static/app.js` restored, sha256 verified): removing the
  case-4 gate fails `test_generate_asks_before_replacing_a_typed_edit` at the edit-dialog
  assertion; making the 409 handler ignore `edits_would_be_discarded` fails it at the confirm
  dialog (the error modal shows instead).
- **Not driven:** the live-preview refresh (`:7949`) from a hidden tab after the fix (covered
  only by the existing live-preview UX tests passing in the full tier); Refine and Iterate
  reaching the old false positive on `main` was read from the shared mechanism, not run there.

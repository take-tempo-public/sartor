```toml
schema = 1
id = 170
kind = "item"
title = "Confirm before a generate or a new cover letter overwrites a typed edit (Continue / Cancel)"
status = "open"
decision_owner = "agent"
branches = []
refs = [
  "blueprints/generation.py",
  "static/app.js",
  "templates/index.html",
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

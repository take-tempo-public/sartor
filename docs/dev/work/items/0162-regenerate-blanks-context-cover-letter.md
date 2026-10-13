```toml
schema = 1
id = 162
kind = "item"
title = "A résumé-only regenerate writes an empty last_generated_cover_letter into the new iteration's context"
status = "closed"
decision_owner = "agent"
branches = ["fix/regenerate-persistence", "fix/regenerate-keeps-cover-letter"]
refs = [
  "hardening.py",
  "blueprints/generation.py",
  "static/app.js",
  "templates/index.html",
  "docs/dev/diagnosis/regenerate-persistence.md",
  "docs/dev/blast-radius/regenerate-persistence.md",
  "docs/dev/diagnosis/regenerate-keeps-cover-letter.md",
  "docs/dev/blast-radius/regenerate-keeps-cover-letter.md",
]
summary = "After a detached cover letter, a résumé-only regenerate's child context carries last_generated_cover_letter = ''."
resolution = "2026-10-12, fix/regenerate-keeps-cover-letter (owner decisions D1-D4): hardening.resolve_cover_letter_after_generate is the one rule: a generate that produced a letter replaces the stored one and consumes the typed edit; one that produced none leaves both alone. save_iteration_context applies it and both generate routes read it, so the response (cover_letter_preview, new edited_cover_letter_text) and the file agree. Decision 4's discard is of the résumé edit only: _typed_edits_disposition and _clear_run_edits no longer touch the letter edit, and the notice copy says so."
verified_by = [
  "tests/test_regenerate_cover_letter.py::test_b1_b2_a_resume_only_regenerate_keeps_the_letter_in_the_context",
  "tests/test_regenerate_cover_letter.py::test_b3_the_styled_cover_letter_preview_survives_a_resume_regenerate",
  "tests/test_regenerate_cover_letter.py::test_b4_the_iteration_interview_still_sees_the_letter",
  "tests/test_regenerate_cover_letter.py::test_b5_a_saved_typed_letter_edit_survives_a_resume_regenerate",
  "tests/test_regenerate_cover_letter.py::test_b6_the_next_with_letter_generate_is_handed_the_prior_letter",
  "tests/test_regenerate_cover_letter.py::test_b8_a_typed_letter_edit_survives_a_discarded_resume_edit",
  "tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py::test_b7_the_wizard_keeps_the_cover_letter_after_a_resume_regenerate",
  "tests/test_hardening_iteration.py::test_resolve_cover_letter_after_generate",
]
```

**Observed** (`docs/dev/diagnosis/regenerate-persistence.md` O4, `tests/test_regenerate_persistence.py`
A4 on `main` @ `cfab8e0`). The drive is generate, then `/api/generate-cover-letter` (which writes
the letter into the current context), then a résumé-only generate. The new child context has:

```
"child_ctx_last_generated_cover_letter": ""
```

Both generate routes pass `last_generated_cover_letter=result["cover_letter_content"]` to
`hardening.save_iteration_context`, and a résumé-only generate's result carries `""`.

`fix/regenerate-persistence` fixed only the DB column (`generated_cover_letter_md`, which
`resume_state` reads), per owner decision D2a's scope.

## Updates

### 2026-10-12 — filed on `fix/regenerate-persistence`

Found by that branch's instrument (O4) and deferred in its blast-radius dossier. It's the
`hardening.py` observation carried forward in the previous handoff, now observed rather than
inferred.

### 2026-10-12 — closed on `fix/regenerate-keeps-cover-letter`

**The user effect was inferred; it is now observed** (`docs/dev/diagnosis/regenerate-keeps-cover-letter.md`
O1-O9). On `main`, with `--runxfail`, the instrument gave 6 failed and 2 passed
(`tests/test_regenerate_cover_letter.py`, commit `2097a40`), and the browser arm failed at the
defect assertion (`41cac42`):
- the child context and the response carry `""` on both generate routes, while the DB row keeps
  the letter;
- the styled preview shows the placeholder, the iteration interview is handed `""`, and the next
  with-letter generate starts with no draft;
- in the wizard the editor is empty, "+ Generate cover letter" is back and Download is hidden
  (`download_would_send` is `""`);
- a saved typed letter edit is dropped, and decision 4's discard drops it from the run row too.

**Decided:** the owner placed the rule in the helper (D1), chose that a typed letter edit
survives a résumé-only regenerate (D2), ran the browser arm before fixing (D3), and, after the
consumer enumeration found decision 4's discard, chose to keep the letter edit even there (D4).

**Fix:** commit `eeb73ed`. The instrument's markers were deleted and its arms pass. One existing
test pinned the old contract (`tests/test_app_iteration.py::test_generate_consumes_edits_from_context`)
and was changed with the reason stated. Found on the way and filed separately as item 163: the run
row's typed letter edit still shadows a newly generated letter in `resume_state`.

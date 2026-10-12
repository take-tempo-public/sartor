```toml
schema = 1
id = 162
kind = "item"
title = "A résumé-only regenerate writes an empty last_generated_cover_letter into the new iteration's context"
status = "open"
decision_owner = "agent"
branches = ["fix/regenerate-persistence"]
refs = [
  "hardening.py",
  "blueprints/generation.py",
  "docs/dev/diagnosis/regenerate-persistence.md",
  "docs/dev/blast-radius/regenerate-persistence.md",
]
summary = "After a detached cover letter, a résumé-only regenerate's child context carries last_generated_cover_letter = ''."
```

**Observed** (`docs/dev/diagnosis/regenerate-persistence.md` O4, `tests/test_regenerate_persistence.py`
A4 on `main` @ `cfab8e0`). The drive is generate, then `/api/generate-cover-letter` (which writes
the letter into the current context), then a résumé-only generate. The new child context has:

```
"child_ctx_last_generated_cover_letter": ""
```

Both generate routes pass `last_generated_cover_letter=result["cover_letter_content"]` to
`hardening.save_iteration_context`, and a résumé-only generate's result carries `""`.

**Not observed — inferred:** the user-facing effect. The child is what the client and the next
iteration read, so Step 6's cover-letter preview, the iterate-clarify probe and an edit-detect
diff may lose the letter after any résumé regenerate. The response's `cover_letter_preview` is
`""` too. Instrument it before choosing a fix.

`fix/regenerate-persistence` fixed only the DB column (`generated_cover_letter_md`, which
`resume_state` reads), per owner decision D2a's scope.

## Updates

### 2026-10-12 — filed on `fix/regenerate-persistence`

Found by that branch's instrument (O4) and deferred in its blast-radius dossier. It's the
`hardening.py` observation carried forward in the previous handoff, now observed rather than
inferred.

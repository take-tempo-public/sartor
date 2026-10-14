```toml
schema = 1
id = 163
kind = "item"
title = "After a with-letter generate the run row's typed letter edit still shadows the new letter in resume_state"
status = "open"
decision_owner = "agent"
branches = ["fix/regenerate-keeps-cover-letter", "fix/run-row-letter-edit-shadow"]
refs = [
  "docs/dev/diagnosis/run-row-letter-edit-shadow.md",
  "docs/dev/blast-radius/run-row-letter-edit-shadow.md",
  "tests/test_run_row_letter_edit.py",
  "blueprints/applications.py",
  "blueprints/generation.py",
  "db/persist_run.py",
  "docs/dev/diagnosis/regenerate-keeps-cover-letter.md",
  "docs/dev/blast-radius/regenerate-keeps-cover-letter.md",
]
summary = "A with-letter generate consumes the letter edit in the context but not on the run row; resume shows the typed text."
```

**Observed** (`docs/dev/diagnosis/regenerate-keeps-cover-letter.md` O10, control C3 in
`tests/test_regenerate_cover_letter.py`, run 2026-10-12 on `main` @ `82f656b` plus the
instrument). The drive: generate, `/api/generate-cover-letter`, `/api/save-edits` with a typed
letter edit, then a generate with `generate_cover_letter: true` that returns a new letter. The
context did what it should (the edit is consumed, the new letter is stored); the run row did not
follow:

```
{"arm": "C3", ..., "run_cover_letter_md": "ZEBRA-REWRITTEN a second, regenerated cover letter", "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "child_last_generated_cover_letter": "ZEBRA-REWRITTEN a second, regenerated cover letter", "child_edited_cover_letter_text": null}
```

`resume_state` reads `edited_cover_letter_text or generated_cover_letter_md`
(`blueprints/applications.py:445`), so resuming from the Pipeline shows the typed text while the
wizard shows the new letter.

**Not observed — inferred:** the same shadow after `/api/generate-cover-letter` itself. That
route pops the context edit (`blueprints/generation.py` `run_generate_cover_letter`) and persists
only `generated_cover_letter_md` (`_persist_cover_letter_to_db`), so by reading it leaves the run
row's edit in place too. Instrument it before choosing a fix.

**Not decided here:** whether a generate that consumed the letter edit should null the run row's
`edited_cover_letter_text` (mirroring `_clear_run_edits`, which nulls the résumé's), or whether
`resume_state` should prefer the newer of the two.

## Updates

### 2026-10-12 — filed on `fix/regenerate-keeps-cover-letter`

Found by that branch's control C3 while verifying that a with-letter generate still consumes the
typed edit. Pre-existing, not caused by item 162's fix, and outside its scope (the context file).

### 2026-10-14 — instrumented on `fix/run-row-letter-edit-shadow`

Observed on `main` @ `562a3a0` (`tests/test_run_row_letter_edit.py`, `--runxfail`): the run
row's `edited_cover_letter_text` outlives the context's edit after BOTH a with-letter generate
(JSON and SSE) and a detached `/api/generate-cover-letter`, so the inferred half above is now
observed (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O1-O3). The frozen
`carry_edits=True` path with a produced letter keeps the typed edit on the context and the run
row alike (O5): consistent, and not this defect. Fix not yet written.

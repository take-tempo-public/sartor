# Diagnosis — a résumé-only regenerate blanks the cover letter in the context (item 162)

> **Status:** the effect is OBSERVED at the HTTP and context-file level on every surface the
> arms reach (O1–O6), and the mechanism is isolated to `save_iteration_context` (O7). The
> browser-level effect (the Download/Generate button swap and the blanked editor) is still
> only inferred from code (I1).
> **Branch:** `fix/regenerate-keeps-cover-letter`

---

## Symptom

After a detached cover letter (Step 6's "Generate cover letter"), regenerating the résumé
leaves the in-session wizard without it. Filed as item 162 from
`docs/dev/diagnosis/regenerate-persistence.md` O4, which saw the child context's
`last_generated_cover_letter` was `""` but never followed it to a surface a user reads. The
client never sends `generate_cover_letter` (`static/app.js:1715`), so every client
regenerate after a detached letter is résumé-only.

---

## Observed

The instrument is `tests/test_regenerate_cover_letter.py`. It drives the real routes against
a fresh migrated DB with the analyzer stubbed (the staleness rig, reused through item 160's
helpers). Run on `main`'s production tree (branch point `82f656b`; only the new test file and
ledger rows were added) on 2026-10-12:

```
$ python -m pytest tests/test_regenerate_cover_letter.py -p no:rerunfailures -p no:cacheprovider -q -rA --runxfail
PASSED tests/test_regenerate_cover_letter.py::TestControls::test_c1_a_first_generate_with_no_letter_has_no_letter
PASSED tests/test_regenerate_cover_letter.py::TestControls::test_c2_a_with_letter_regenerate_replaces_the_letter
FAILED tests/test_regenerate_cover_letter.py::test_b1_b2_a_resume_only_regenerate_keeps_the_letter_in_the_context[json]
FAILED tests/test_regenerate_cover_letter.py::test_b1_b2_a_resume_only_regenerate_keeps_the_letter_in_the_context[stream]
FAILED tests/test_regenerate_cover_letter.py::test_b3_the_styled_cover_letter_preview_survives_a_resume_regenerate
FAILED tests/test_regenerate_cover_letter.py::test_b4_the_iteration_interview_still_sees_the_letter
FAILED tests/test_regenerate_cover_letter.py::test_b5_a_saved_typed_letter_edit_survives_a_resume_regenerate
FAILED tests/test_regenerate_cover_letter.py::test_b6_the_next_with_letter_generate_is_handed_the_prior_letter
=================== 6 failed, 2 passed in 126.14s (0:02:06) ===================
```

Each failure is the assertion the arm exists to make, not a setup error (the control
assertion inside each arm held first).

### O1. Both generate routes write `""` into the child context (B1, B2)

Drive: generate, `/api/generate-cover-letter`, then a résumé-only generate. The DB keeps the
letter; the context, and the response, do not:

```
{"arm": "B1B2-json", "persists": ["ok", "ok"], "run_cover_letter_md": "ZEBRA-LETTER first detached cover letter for the billing role", "resume_state_cover_letter_md": "ZEBRA-LETTER first detached cover letter for the billing role", "child_last_generated_cover_letter": "", "child_edited_cover_letter_text": null, "child_iteration": 2, "cover_letter_preview": "", "cover_letter_path": ""}
{"arm": "B1B2-stream", "persists": ["ok", "ok"], "run_cover_letter_md": "ZEBRA-LETTER first detached cover letter for the billing role", "resume_state_cover_letter_md": "ZEBRA-LETTER first detached cover letter for the billing role", "child_last_generated_cover_letter": "", "child_edited_cover_letter_text": null, "child_iteration": 2, "cover_letter_preview": "", "cover_letter_path": ""}
```

The two sides disagree on the same application after one regenerate: `resume_state`
(Pipeline resume) has the letter, the context the wizard reads has `""`. The stream route
(`blueprints/generation.py:1579`) matches the JSON route (`:1267`).

### O2. The styled cover-letter preview falls back to the placeholder (B3)

`GET /api/applications/<id>/cover-letter-preview?context_path=<child>`:

```
{"arm": "B3", ..., "before_has_letter": true, "after_has_letter": false, "after_is_placeholder": true}
```

### O3. The iteration interview is handed an empty letter (B4)

`/api/iterate-clarify` on the child, with `clarify_iteration` captured:

```
{"arm": "B4", ..., "current_cover_letter_text": ""}
```

### O4. A saved typed letter edit is lost (B5)

`/api/save-edits` with an `edited_cover_letter`, then a résumé-only generate. The edit
rendered before (`before_shows_typed: true`); the child has neither the edit nor the letter,
and the preview is the placeholder. The DB `resume_state` still holds the typed text:

```
{"arm": "B5", ..., "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "child_last_generated_cover_letter": "", "child_edited_cover_letter_text": null, "child_iteration": 2, "before_shows_typed": true, "after_shows_typed": false, "after_is_placeholder": true}
```

### O5. The next with-letter generate starts without the prior letter (B6)

Generate, letter, résumé-only regenerate, then a with-letter generate. `generate_calls`
records `analyzer._current_cover_letter_draft` of the context each call was handed. The
second call (before the résumé regenerate) saw the letter; the third did not:

```
"generate_calls": [{"with_cover_letter": false, "draft": "", "draft_source": "none"}, {"with_cover_letter": false, "draft": "ZEBRA-LETTER first detached cover letter for the billing role", "draft_source": "last_generated"}, {"with_cover_letter": true, "draft": "", "draft_source": "none"}]
```

### O6. Controls

```
{"arm": "C1", "persists": ["ok"], ..., "child_last_generated_cover_letter": "", "cover_letter_preview": ""}
{"arm": "C2", "persists": ["ok", "ok"], ..., "run_cover_letter_md": "ZEBRA-REWRITTEN a second, regenerated cover letter", "child_last_generated_cover_letter": "ZEBRA-REWRITTEN a second, regenerated cover letter", "cover_letter_preview": "ZEBRA-REWRITTEN a second, regenerated cover letter"}
```

C1: a first generate with no letter correctly has none. C2: a regenerate that does produce a
letter replaces it in the context, the response and the DB. So the defect is specific to a
generate that produces no letter.

### O7. The helper alone does it (probe, run from the repo root)

`hardening.save_iteration_context` called directly, once with `""` and once with a new
letter, from a parent holding `last_generated_cover_letter="PARENT LETTER"` and
`edited_cover_letter_text="TYPED EDIT"`:

```python
import json, tempfile
from pathlib import Path
import hardening

with tempfile.TemporaryDirectory() as td:
    parent = {"iteration": 1, "last_generated_resume": "# R",
              "last_generated_cover_letter": "PARENT LETTER",
              "edited_cover_letter_text": "TYPED EDIT"}
    parent_path = str(Path(td) / "context_parent.json")
    Path(parent_path).write_text(json.dumps(parent), encoding="utf-8")
    for label, letter in (("result_letter_empty", ""), ("result_letter_new", "NEW LETTER")):
        p = hardening.save_iteration_context(
            parent_context=parent, parent_path=parent_path, last_generated_resume="# R2",
            last_generated_cover_letter=letter, username="probe", base_dir=td)
        child = json.loads(Path(p).read_text(encoding="utf-8"))
        print(label, child.get("last_generated_cover_letter"),
              "edited_cover_letter_text" in child)
```

```
result_letter_empty '' False
result_letter_new 'NEW LETTER' False
```

No route, DB or client is involved. The letter is overwritten by whatever it is handed, and
the typed-edit key is popped whether or not that generate consumed it
(`hardening.py:2145`, `:2159-2160`).

---

## Falsified

Nothing was falsified. Every filed or inferred effect that was instrumented reproduced. The
plan's candidate list (client, styled preview, iteration interview, edit-detect, next
with-letter generate, typed-edit sibling) was widened beyond item 162's filed text; the
arms covered all of them except the client DOM (I1) and edit-detect (I2).

---

## Inferred

- **I1. The wizard's DOM shows the loss.** `_onGenerationComplete` sets
  `lastGeneratedCoverLetter = data.cover_letter_preview || ''` (`static/app.js:1801`),
  `_updateCoverLetterButtons` shows Generate instead of Download when it is empty
  (`:1829-1831`), and `_renderOutput` blanks `#coverLetterPreview` (`:3283`). That follows
  from O1's `cover_letter_preview: ""`, but no browser was driven. Seeing it needs a UX arm.
- **I2. Edit-detect diffs a later letter edit against `""`.** `summarize_recent_edits`
  (`hardening.py:1959`) reads `last_generated_cover_letter`, which O1 shows is `""`. Not
  run as its own arm.
- **I3. Whether `cover_letter_path == ""` breaks Download.** O1 shows the response carries
  `""`; what the Download button does with it was not observed.

---

## Falsification

The B-arms in `tests/test_regenerate_cover_letter.py`, as `xfail(strict=True)`. Each failed
on HEAD (quoted above), so the hypotheses at the context-file and HTTP level are confirmed.
B5's invariant (a saved typed edit survives a résumé regenerate) is a proposal for the owner
to confirm. It is not an observed defect: O4 only shows the edit is dropped.

---

## The fix

_Not yet. The shape is the owner's call after this dossier (plan Step 2)._

---

## Acceptance bar

- Every `xfail` marker in `tests/test_regenerate_cover_letter.py` is deleted, and all arms
  and controls pass with `-p no:rerunfailures`.
- C2 still passes: a regenerate that produces a letter replaces the old one everywhere.
- CI: `python -m scripts.ci_wait <n>` exits 0 (exit 3 means a test needed a retry: stop and
  look).

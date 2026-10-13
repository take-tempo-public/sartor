# Diagnosis — a résumé-only regenerate blanks the cover letter in the context (item 162)

> **Status:** the effect is OBSERVED on the routes, in the context file and in the browser
> (O1–O7, O9), and the mechanism is isolated to `save_iteration_context` (O11). Only the
> edit-detect diff (I2) is still inferred, and the fix doesn't depend on it.
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

### O7. The wizard shows it (B7, real browser)

`tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py`, run on the same tree
(2026-10-12). The drive is the real wizard with the LLM entry points stubbed: analyze →
Compose → Template → Generate → "+ Generate cover letter" → rail Step 5 → Generate. The
controls held first (`ControlFailed` was not raised); the failure is the defect assertion:

```
$ python -m pytest tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py -m ux -p no:rerunfailures -p no:cacheprovider -q -rA --runxfail
FAILED tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py::test_b7_the_wizard_keeps_the_cover_letter_after_a_resume_regenerate
======================== 1 failed in 91.55s (0:01:31) =========================
E   AssertionError: {'editor_text': '', 'generate_visible': True, 'download_visible': False, 'download_would_send': ''}
```

```
{"arm": "B7", "before_letter": {"editor_text": "", "generate_visible": true, "download_visible": false, "download_would_send": ""}, "with_letter": {"editor_text": "ZEBRA-LETTER first detached cover letter for the billing role", "generate_visible": false, "download_visible": true, "download_would_send": "ZEBRA-LETTER first detached cover letter for the billing role"}, "after_regenerate": {"editor_text": "", "generate_visible": true, "download_visible": false, "download_would_send": ""}}
```

After the regenerate the editor is empty, "+ Generate cover letter" is back and "Download
cover letter" is hidden. `download_would_send` is what `downloadCoverLetter()` posts as
`content` (`_readEditorText('coverLetterPreview')`, `static/app.js:3488`): it is `""`, so
the user has lost the letter in the browser, not only in the context file.

### O8. Nothing reads `lastCoverLetterPath` (grep, negative result)

`rg lastCoverLetterPath` over `static/`, `templates/`, `ui_pages/` and `scripts/`: seven
hits, all assignments (`static/app.js:27, 522, 1770, 1863, 2792, 6744, 6828`). Download
reads the editor text (O7), so the response's `cover_letter_path` being `""` (O1) has no
reader. The fix doesn't need to make it usable.

### O9. The discard branch drops the typed letter edit too (B8, `main` tree, 2026-10-12)

Added after the consumer enumeration found decision 4's discard (`blueprints/generation.py:
858-902`). Drive (frozen path): generate, detach a letter, `/api/save-edits` with BOTH a
résumé edit and a letter edit, change a bullet in Compose, re-approve, regenerate. The
controls held (`edits_discarded: true`, résumé edit gone from the context and the DB); the
failure is the defect assertion on the letter edit:

```
$ python -m pytest tests/test_regenerate_cover_letter.py -k "b8 or c3" -p no:rerunfailures -p no:cacheprovider -q -rA --runxfail
FAILED tests/test_regenerate_cover_letter.py::test_b8_a_typed_letter_edit_survives_a_discarded_resume_edit
E   assert None == 'ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter'
================= 1 failed, 1 passed, 8 deselected in 15.41s ==================
```

```
{"arm": "B8", ..., "edits_discarded": true, "body_edited_resume_text": "", "body_edited_cover_letter_text": null, "body_cover_letter_preview": "", "child_edited_resume_text": null, "child_edited_cover_letter_text": null, "child_last_generated_cover_letter": "", "db_edited_resume_text": null, "db_edited_cover_letter_text": null}
```

The letter edit is gone from the context (popped) and the run row (nulled by
`_clear_run_edits`), and the generated letter is `""` again. D4 reverses the first two.

### O10. A with-letter generate leaves the DB edit shadowing the new letter (C3, pre-existing)

Control C3 (generate, letter, save a typed letter edit, then a with-letter generate that
returns a new letter) passes: the context consumes the edit and holds the new letter. Its
record shows the DB side did not follow:

```
{"arm": "C3", ..., "run_cover_letter_md": "ZEBRA-REWRITTEN a second, regenerated cover letter", "resume_state_cover_letter_md": "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter", "child_last_generated_cover_letter": "ZEBRA-REWRITTEN a second, regenerated cover letter", "child_edited_cover_letter_text": null}
```

`resume_state` reads `edited_cover_letter_text or generated_cover_letter_md`
(`blueprints/applications.py:445`), so resuming from Pipeline shows the typed text while the
wizard shows the new letter. This is not item 162's defect and not changed here; it is filed
at close-out (see the blast-radius dossier's Deferred).

### O11. The helper alone does it (probe, run from the repo root)

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
arms covered all of them except edit-detect (I2).

---

## Inferred

- **I2. Edit-detect diffs a later letter edit against `""`.** `summarize_recent_edits`
  (`hardening.py:1959`) reads `last_generated_cover_letter`, which O1 shows is `""`. Not
  run as its own arm. The fix doesn't depend on it: it restores the value the diff reads.

The two earlier inferences about the browser (the DOM losing the letter; whether
`cover_letter_path == ""` breaks Download) are now O7 and O8.

---

## Falsification

The B-arms in `tests/test_regenerate_cover_letter.py`, as `xfail(strict=True)`. Each failed
on HEAD (quoted above), so the hypotheses at the context-file and HTTP level are confirmed.
B5's invariant (a saved typed edit survives a résumé regenerate) is a proposal for the owner
to confirm. It is not an observed defect: O4 only shows the edit is dropped.

---

## Owner decisions (2026-10-12; D1-D3 taken after the HTTP arms and the probe, O1–O6 and O11; D4 after the consumer enumeration)

- **D1, placement:** the rule lives in `hardening.save_iteration_context`, not in the two
  route callers. A generate that produced no letter keeps the parent's
  `last_generated_cover_letter`; one that produced a letter replaces it (C2 holds).
- **D2, typed edit:** `edited_cover_letter_text` survives a generate that did not consume it
  (a résumé-only one) and is popped only by a generate that produced a letter. This is a new
  contract, decided by the owner; it was not an observed defect (see Falsification).
- **D4, the discard case (decided after the consumer enumeration):** decision 4 of
  `fix/frozen-composition-staleness` discards both typed edits when a regenerate
  re-assembles a different, newly approved résumé (the helper pops them,
  `_clear_run_edits` nulls both DB columns, the notice says "Your typed edits weren't
  carried over"). The owner chose to **keep the typed letter edit even then**. Consequences,
  all in `docs/dev/blast-radius/regenerate-keeps-cover-letter.md`: `_clear_run_edits` leaves
  the cover-letter column alone, `_typed_edits_disposition` looks at the résumé edit only,
  and the notice copy is reworded to say it is the résumé edits, and that letter edits are
  kept.
- **D3, browser arm first:** B7 runs before the fix shape is final, so the DOM effect and
  the Download path are observed rather than built on. Result: O7 and O8. The routes need
  not return a usable `cover_letter_path`; the fix is the context value and the response's
  `cover_letter_preview`.

---

## The fix

Per owner decisions D1-D4, after the C-10 consumer dossier
(`docs/dev/blast-radius/regenerate-keeps-cover-letter.md`). By the mechanism each part
addresses:

`hardening.py`:
- **O1-O6, O9, O11.** New pure `resolve_cover_letter_after_generate(parent, generated,
  carry_edits=)` returns `(letter, typed_edit)`. A generate that produced a letter replaces
  the stored one and consumes the typed edit (kept under `carry_edits`, as before); one that
  produced none leaves both alone. `save_iteration_context` applies it to the child file.
  The résumé edit is still consumed unconditionally.

`blueprints/generation.py`:
- **O1.** Both routes return `cover_letter_preview` from the same resolver the file used, so
  the response and the file agree, and gain `edited_cover_letter_text` (additive, mirroring
  `edited_resume_text`).
- **O9 (D4).** `_typed_edits_disposition` looks at the résumé edit only, and
  `_clear_run_edits` nulls only `edited_resume_text`.
- `_built_from_edited_baseline`: the iteration note says "from edited baseline" for a
  letter edit only when that generate produced a letter.

Client:
- **O7.** `_renderOutput` prefers `data.edited_cover_letter_text` for the editor, as it does
  for the résumé. The "edits weren't carried over" notice is reworded to the résumé edits
  and says typed letter edits are kept.

Tests: the instrument's markers are deleted; `tests/test_hardening_iteration.py` gains the
resolver table (6 cases) and 4 helper tests; `tests/test_app_iteration.py::
test_generate_consumes_edits_from_context` now asserts the letter edit stays (the one test
that pinned the old contract).

Results (all `-p no:rerunfailures`, 2026-10-12):
- the instrument (10 arms) + `test_hardening_iteration.py` + `test_app_iteration.py` +
  `test_composition_staleness.py`: `71 passed in 48.27s`;
- the consumers named in the dossier (persistence, frozen staleness, persist-run,
  detached cover letter, live preview, analyzer iteration, write races, deterministic
  generate, application routes, gap fill, OpenAPI): `282 passed in 155.13s`;
- UX: B7 + the wizard-flow-polish generate drive + the happy path: `4 passed in 78.63s`;
- `python -m mypy hardening.py blueprints/generation.py`: no issues.

Not fixed here (Deferred in the blast-radius dossier): O10, the DB edit shadowing a new
letter in `resume_state`; and the stale typed edit under `carry_edits` with a produced
letter.

---

## Acceptance bar

- Every `xfail` marker in `tests/test_regenerate_cover_letter.py` and in
  `tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py` is deleted, and all
  arms and controls pass with `-p no:rerunfailures`. (Met, see "The fix".)
- C2 and C3 still pass: a regenerate that produces a letter replaces the old one and
  consumes the typed edit.
- CI: `python -m scripts.ci_wait <n>` exits 0 (exit 3 means a test needed a retry: stop and
  look).

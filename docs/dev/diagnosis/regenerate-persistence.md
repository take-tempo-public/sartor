# Diagnosis — a regenerate of the same application run never reaches the DB (item 160)

> **Status:** root cause PROVEN for the bullet collision (O1–O3, O5), the cover-letter clobber
> (O4), proposal duplication (O6) and the silent failure (O7). The title-row collision is
> still inferred (I1).
> **Branch:** `fix/regenerate-persistence`

---

## Symptom

Resuming an application from the Pipeline shows its **first** generated résumé, not the
latest one. Filed as item 160 from the previous branch's probe
(`docs/dev/diagnosis/frozen-composition-staleness.md` O9).

---

## Observed

The instrument is `tests/test_regenerate_persistence.py`. It drives the real routes against a
fresh migrated DB with the analyzer stubbed (the staleness rig). It wraps
`blueprints.generation._persist_corpus_generation_to_db` to record each persist's outcome,
because the routes swallow the exception and app loggers are silent under pytest. Run on
`main` @ `cfab8e0` plus the instrument (2026-10-12):

```
$ python -m pytest tests/test_regenerate_persistence.py -p no:rerunfailures -p no:cacheprovider -q -rA --runxfail
PASSED ...::TestControls::test_c1_one_frozen_generate_persists
PASSED ...::TestControls::test_c2_a_context_without_a_run_attempts_no_persist
FAILED ...::test_a1_a2_regenerate_reaches_the_run_and_resume_state[json]
FAILED ...::test_a1_a2_regenerate_reaches_the_run_and_resume_state[stream]
FAILED ...::test_a3_the_run_rows_are_the_latest_selection
FAILED ...::test_a4_a_resume_only_regenerate_keeps_the_detached_cover_letter
FAILED ...::test_a5_the_same_proposal_twice_is_one_pending_bullet
FAILED ...::test_a6_a_duplicate_within_one_result_still_persists
FAILED ...::test_a7_a_persist_failure_reaches_the_response[json]
FAILED ...::test_a7_a_persist_failure_reaches_the_response[stream]
======================== 8 failed, 2 passed in 35.45s =========================
```

Without `--runxfail`: `2 passed, 8 xfailed in 34.81s`.

### O1. Frozen path, `/api/generate`: the second persist raises and rolls back (A1)

The drive: freeze, generate, then on the child a Compose bullet edit (`EDITED`), re-freeze,
generate. The second response carries `EDITED`, but the run row and `resume_state` keep the
first résumé (`- ZEBRA-B1 led the billing rewrite that cut churn`, not the edited text):

```
{"arm": "A1A2-json", "persists": ["ok", "RAISED IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: application_bullet.application_run_id, application_bullet.bullet_id"], "run_resume_md": "# Alice Rivera\n...- ZEBRA-B1 led the billing rewrite that cut churn\n...", "bullets": [[1, 0]], "titles": {"1": 1}, "iteration_logs": 1, ...}
```

### O2. The same through `/api/generate/stream` (A2)

The record is identical in every field: `"arm": "A1A2-stream"`, the same `RAISED IntegrityError`,
`iteration_logs: 1`.

### O3. LLM path: a second, different selection never replaces the first (A3)

The stub returns `[b1, b2]` with the official title, then `[b2]` with an alternate title. The
run keeps the first selection:

```
{"arm": "A3", "persists": ["ok", "RAISED IntegrityError: ... UNIQUE constraint failed: application_bullet.application_run_id, application_bullet.bullet_id"], "bullets": [[1, 0], [2, 1]], "titles": {"1": 1}, "iteration_logs": 1, ...}
```

### O4. A résumé-only regenerate blanks the detached cover letter (A4), with no rollback involved

Neither generate selects bullets, so nothing collides and both persists succeed. The letter is
on the run and in `resume_state` after `/api/generate-cover-letter`, and gone after the next
generate:

```
{"arm": "A4-after-letter", "persists": ["ok"], "run_cover_letter_md": "LLM COVER LETTER", "resume_state_cover_letter_md": "LLM COVER LETTER", ...}
{"arm": "A4", "persists": ["ok", "ok"], "run_cover_letter_md": "", "resume_state_cover_letter_md": "", "child_ctx_last_generated_cover_letter": "", ...}
```

This **corrects the plan's inference**, which held that the rollback hid this. It hides it only
when the second generate selects bullets. The context-file analogue is observed too: the
child's `last_generated_cover_letter` is `""`.

### O5. A duplicate within ONE result fails even the first persist (A6)

The selection repeats `b1` within an entry and repeats the experience across two entries. On
the very first generate, nothing reaches the run:

```
{"arm": "A6", "persists": ["RAISED IntegrityError: ... UNIQUE constraint failed: application_bullet.application_run_id, application_bullet.bullet_id"], "run_resume_md": null, "bullets": [], "titles": {}, "iteration_logs": 0, ...}
```

### O6. The same proposal on two generates becomes two pending bullets (A5)

No bullets are selected, so both persists succeed:

```
{"arm": "A5", "persists": ["ok", "ok"], "iteration_logs": 2, "proposed_bullets": 2, "proposal_reviews": 2, ...}
```

### O7. A persist failure never reaches the response (A7, both routes)

With the persist forced to raise, both routes return 200, and nothing in the payload reports
the failure:

```
{"arm": "A7-json", "response_keys": ["ats_roundtrip", "changes_made", "context_path", "cover_letter_path", "cover_letter_preview", "date_grounding", "edited_resume_text", "edits_discarded", "iteration", "parent_context_path", "persona_template_id", "proofread_notes", "resume_format", "resume_path", "resume_preview"]}
```

`A7-stream`'s `done` payload has the same keys.

### O8. Controls

- **C1:** one frozen generate persists (`["ok"]`), and the run md equals the response.
- **C2:** a context without `application_run_id` attempts no persist.

### O9. Why every regenerate shares a run (consumer map, read from code, cited)

- `db/build_context.py:176-186` creates the only production `ApplicationRun`, with
  `iteration=0` and `parent_run_id=None`.
- `hardening.save_iteration_context` deep-copies the parent context, so every child carries
  the same `application_run_id`.
- No non-test code assigns `ApplicationRun.iteration` or `.parent_run_id`.

---

## Falsified

- **"The rollback is the only thing hiding the cover-letter clobber."** This was the plan's
  inference. O4 kills it: the clobber reaches the user whenever a regenerate selects no
  bullets.
- **Instrument errors, caught before commit:**
  - A4's first run called a real client (`AttributeError: 'object' object has no attribute
    'messages'`). The cover-letter route imports `generate_cover_letter_against_resume`
    inside the function (`blueprints/generation.py` `run_generate_cover_letter`), so the
    rig's module patch never reached it. It is now patched on `analyzer`.
  - A3, A4 and A6 first compared the run md with the stub's `resume_content`. The corpus path
    re-renders the résumé (`"# Alice Rivera\nalice@example.com\n"`), so they now compare with
    the route's own response.

---

## Inferred

- **I1.** `application_run_title`'s composite PK `(application_run_id, experience_id)`
  (`db/models.py` `ApplicationRunTitle`) also collides on a second persist. It is not observed:
  in O1 and O3 the `application_bullet` insert raised first. The fix replaces both tables'
  rows, and A3 asserts the title row is the latest, so this is covered without being
  separately seen.

---

## Falsification

The A-arms in `tests/test_regenerate_persistence.py`, as `xfail(strict=True)`. Each failed on
HEAD (quoted above), so the hypotheses are confirmed.

---

## The fix

Per owner decisions D1 and D2 (2026-10-12; plan `nifty-frolicking-planet`):
- **D1, replace in place.** The run's `application_bullet` and `application_run_title` rows
  become the latest selection.
- **D2a.** A generate never blanks a stored cover letter.
- **D2b.** A proposal whose text already exists on the experience is skipped.
- **D2c.** `persist_failed` is reported in both routes' payloads, and the client shows a
  banner.
- **D2d.** The per-row lookups are batched.

**What changed, by the mechanism each part addresses:**

`db/persist_run.py`:
- **O1–O3.** `_persist_selected_bullets` deletes the run's `application_bullet` and
  `application_run_title` rows first, then inserts the latest selection. Both happen in the
  caller's single transaction, so a failure restores the previous selection.
- **O5.** Repeated bullet ids and repeated experience titles within one result are skipped and
  counted in `PersistReport.duplicate_selections_skipped`. `position` counts per experience.
- **D2d.** Experiences, titles and bullets are resolved with one `IN` query each, through a
  new `_owned_experience_ids` helper. `test_select_count_does_not_grow_with_the_selection`
  pins it: the SELECT count is equal for 1 and 20 selected bullets.
- **O4.** `generated_cover_letter_md` is written only when the result carries a letter.
- **O6.** `_persist_proposed_bullets` skips a text the experience already has (counted in
  `proposed_bullets_already_present`). It loads the referenced experiences' texts in one query
  and flushes once.

`blueprints/generation.py`:
- **O7.** Both routes return `persist_failed`.

Client:
- **O7.** `templates/index.html` gains `persistFailedNotice`, and `static/app.js`
  `_renderOutput` toggles it.

Results, all run with `-p no:rerunfailures`:
- The instrument's markers are deleted: `tests/test_regenerate_persistence.py` plus
  `test_persist_run.py`, `test_composition_staleness.py` (tightened) and
  `test_frozen_composition_staleness.py` give `106 passed in 165.37s`.
- The related suites (cover letter, application routes, merge/retire, OpenAPI, consumer gate,
  deterministic generate, iteration, regenerate gap-fill, cover-letter formats) give
  `191 passed in 247.62s`.

Not fixed here (Deferred in `docs/dev/blast-radius/regenerate-persistence.md`): the
context-file analogue in O4. The child context's `last_generated_cover_letter` is still `""`.

---

## Acceptance bar

- Every `xfail` marker in `tests/test_regenerate_persistence.py` is deleted, and all tests
  pass with `-p no:rerunfailures`.
- `tests/test_composition_staleness.py`'s re-approval test asserts the latest `resume_md`
  (it skipped that assertion because of O9 of the staleness dossier).
- A statement-count test shows the persist's SELECT count doesn't grow with the number of
  selected bullets.
- CI: `python -m scripts.ci_wait <n>` exits 0 (exit 3 means a test needed a retry: stop and
  look).

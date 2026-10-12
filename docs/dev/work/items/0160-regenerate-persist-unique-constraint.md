```toml
schema = 1
id = 160
kind = "item"
title = "A second generate of the same application run never persists: application_bullet's unique constraint rolls it back"
status = "closed"
decision_owner = "agent"
branches = ["fix/frozen-composition-staleness", "fix/regenerate-persistence"]
refs = [
  "blueprints/generation.py",
  "db/persist_run.py",
  "blueprints/applications.py",
  "docs/dev/diagnosis/frozen-composition-staleness.md",
  "docs/dev/diagnosis/regenerate-persistence.md",
  "docs/dev/blast-radius/regenerate-persistence.md",
]
summary = "Regenerate re-inserts the run's selected bullets, hits UNIQUE(run, bullet), rolls back; resume shows the FIRST résumé."
resolution = "2026-10-12, fix/regenerate-persistence (owner decisions D1+D2): persist_corpus_generation replaces the run's application_bullet/application_run_title rows with the latest selection inside one transaction; duplicates within one result are skipped; a result with no letter leaves a stored cover letter alone; an already-present proposal text isn't re-created; lookups are one IN query per kind; both generate routes report persist_failed and the client shows a banner."
verified_by = [
  "tests/test_regenerate_persistence.py::test_a1_a2_regenerate_reaches_the_run_and_resume_state",
  "tests/test_regenerate_persistence.py::test_a3_the_run_rows_are_the_latest_selection",
  "tests/test_regenerate_persistence.py::test_a4_a_resume_only_regenerate_keeps_the_detached_cover_letter",
  "tests/test_regenerate_persistence.py::test_a5_the_same_proposal_twice_is_one_pending_bullet",
  "tests/test_regenerate_persistence.py::test_a6_a_duplicate_within_one_result_still_persists",
  "tests/test_regenerate_persistence.py::test_a7_a_persist_failure_reaches_the_response",
  "tests/test_persist_run.py::TestRegenerateSameRun",
  "tests/test_composition_staleness.py::TestTypedEdits::test_discarded_and_cleared_after_a_re_approval",
]
```

**Observed, not inferred** (`docs/dev/diagnosis/frozen-composition-staleness.md` O9, a probe run
on `fix/frozen-composition-staleness`). One analyze, then two `/api/generate` calls on the same
`application_run_id` (each iteration child carries it forward). The first
`_persist_corpus_generation_to_db` succeeds. The second raises:

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: application_bullet.application_run_id, application_bullet.bullet_id
[SQL: INSERT INTO application_bullet (application_run_id, bullet_id, position) VALUES (?, ?, ?)]
```

`persist_corpus_generation` re-inserts the run's already-selected bullets; the transaction rolls
back, so `ApplicationRun.generated_resume_md` keeps the **first** generation and no
`IterationLog` row is written for the second. The route catches the exception and only logs it
("Corpus generation persist failed"), so nothing user-facing reports it.

**Effect:** resuming an application from the Pipeline (`resume_state.resume_md`, which reads
`edited_resume_text or generated_resume_md`) loads its first generated résumé, not the latest.
Any regenerate (Step 5 again, Refine, a follow-up regenerate) is affected, not only the frozen
path.

**Not decided here:** whether a regenerate should replace the run's `application_bullet` rows
(the run's latest selection) or append a new run per iteration. That shapes the audit chain.

## Updates

### 2026-10-10 — filed on `fix/frozen-composition-staleness`

Found while testing that branch's typed-edits discard (O9); out of that branch's scope. That
branch's test asserts only what it owns (the discarded edit is cleared from the run).

### 2026-10-12 — closed on `fix/regenerate-persistence`

**Decided:** the owner chose replace-in-place (D1) over a new run per iteration, and put four
adjacent defects in scope (D2: the cover-letter clobber, proposal duplication, surfacing a
persist failure, batching the lookups).

**Instrument first:** `tests/test_regenerate_persistence.py`, commit `7bcbc3a`. On `main` @
`cfab8e0` it gave 8 failed and 2 passed (`--runxfail`), quoted in
`docs/dev/diagnosis/regenerate-persistence.md`.

The instrument widened the item:
- **The bullet collision also fails a FIRST generate** whose result repeats a bullet (O5).
- **A résumé-only regenerate blanks a detached cover letter**, with no rollback involved (O4).
  This corrected the plan's inference.
- **Proposals stack duplicates** (O6).
- **A persist failure never reaches the response** (O7).

**Fix:** commit `75f4306`. The instrument's markers were deleted and its tests pass. The context-file
analogue of O4 is filed separately as item 162.

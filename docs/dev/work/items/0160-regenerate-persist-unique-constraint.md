```toml
schema = 1
id = 160
kind = "item"
title = "A second generate of the same application run never persists: application_bullet's unique constraint rolls it back"
status = "open"
decision_owner = "agent"
branches = ["fix/frozen-composition-staleness"]
refs = [
  "blueprints/generation.py",
  "db/persist_run.py",
  "blueprints/applications.py",
  "docs/dev/diagnosis/frozen-composition-staleness.md",
]
summary = "Regenerate re-inserts the run's selected bullets, hits UNIQUE(run, bullet), rolls back; resume shows the FIRST résumé."
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

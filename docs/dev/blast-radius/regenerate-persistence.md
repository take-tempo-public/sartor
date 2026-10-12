# Blast radius — regenerate-persistence

> **Branch:** `fix/regenerate-persistence`
> **Status:** enumeration complete, written before the first production edit (charter C-10).
> None of the touched files is a gated surface in `scripts/enforcement/blast_radius.py`. This
> dossier covers the two shared contracts that change anyway.

---

## Surface

1. **`db/persist_run.py` `persist_corpus_generation`:** the persist contract. Behavior
   changes:
   - the run's `application_bullet` and `application_run_title` rows are **replaced**, not
     appended;
   - `generated_cover_letter_md` is written only when the result carries a non-empty letter;
   - a proposed bullet whose text already exists on its experience is skipped;
   - duplicates within one result are skipped;
   - lookups are batched;
   - `PersistReport` gains skip counters.

   The signature is unchanged.
2. **The `/api/generate` JSON body and the `/api/generate/stream` SSE `done` payload**
   (`blueprints/generation.py`). Both gain `persist_failed: bool`, which is additive.
3. **`templates/index.html` + `static/app.js` `_renderOutput`:** a new `persistFailedNotice`
   banner. No selector is added to the gated `ui_pages/selectors.py`.

---

## Enumeration

Grep tool (ripgrep) over the whole tree, excluding `node_modules/` and `output/`, 2026-10-12:

```
persist_corpus_generation|_persist_corpus_generation_to_db|PersistReport
  -> 56 occurrences / 16 files. Code: blueprints/generation.py (7), db/persist_run.py (9),
     scripts/smoke_phase_b1.py (2), tests/test_persist_run.py (14),
     tests/test_regenerate_persistence.py (4). The rest are docs (CHANGELOG, architecture,
     RELEASE_ARC/CHECKLIST, wiki application-audit-chain + pipeline-stages, archive, items,
     diagnoses).
has_cover_letter|generated_cover_letter_md
  -> 32 occurrences / 16 files. Code readers: blueprints/applications.py:284 (has_cover_letter,
     `is not None`), :445 (resume_state cover_letter_md, `or ""`), web_infra/openapi.py:216
     (has_cover_letter: bool), static/app.js:6554 (`if (r.has_cover_letter)`). Writers:
     db/persist_run.py:96, :156. Test seeders: tests/test_application_routes.py,
     tests/ux/seeding.py, tests/test_persist_run.py, tests/test_cover_letter_detached.py.
edits_discarded|persist_failed   (payload-key sites, proxy for the done payload's readers)
  -> 17 occurrences / 10 files. Code: blueprints/generation.py (6), static/app.js (1),
     tests/test_composition_staleness.py (2), tests/test_regenerate_persistence.py (1).
     Wiki: route-surface, iteration-audit-chain, frontend-wizard.
```

Readers of the replaced rows come from this session's consumer map (Explore pass, cited):
- `ApplicationBullet` / `application_bullet` / `run.bullets`: non-test readers are
  `blueprints/corpus/experiences.py:358-363` (merge guard, count by `bullet_id`) and
  `scripts/smoke_phase_b1.py:254-260`. `ApplicationRun.bullets` is never read in non-test code.
- `ApplicationRunTitle` / `application_run_title` / `title_overrides`: non-test reader is
  `blueprints/corpus/experiences.py:342-352` (merge guard). `title_overrides` is never read.
- No migration touches either table. `0001_initial_schema.py` uses `create_all`.

**Negative result:** `dashboard/` has 0 hits for any of these names.

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `db/persist_run.py` `persist_corpus_generation` + helpers | update | The fix (D1, D2a, D2b, D2d). |
| 2 | `blueprints/generation.py` `_persist_corpus_generation_to_db` | no change | It already commits once or rolls back once. Replace + insert land in that one transaction, so a failure leaves the previous selection intact. |
| 3 | `blueprints/generation.py` `/api/generate` call site + JSON body | update | `persist_failed` (D2c); the stale "must not break the user's flow" comment. |
| 4 | `blueprints/generation.py` `/api/generate/stream` call site + `done` | update | Same as 3. |
| 5 | `scripts/smoke_phase_b1.py:229-236` | no change | Single persist on a fresh run. Replace-first is a no-op on an empty run; its counts are unchanged. |
| 6 | `blueprints/corpus/experiences.py:342-363` merge guards | no change (accepted consequence) | Under D1, a bullet or title that only an *earlier* iteration selected loses its run reference, so a merge or delete of it is no longer blocked. The owner chose replace-in-place; the earlier résumé's text stays in the context-file chain, which has no FK to `bullet`. |
| 7 | `blueprints/applications.py:284` `has_cover_letter` (`is not None`) | no change | A résumé-only first generate now leaves `None` instead of `""`, so `has_cover_letter` reads False until a real letter exists. That is the truthful value; before, any generate made it True. |
| 8 | `static/app.js:6554` (`r.has_cover_letter` → "cover letter" status text) | no change | Shows "cover letter" only when one exists (follows 7). |
| 9 | `web_infra/openapi.py:216` `has_cover_letter: bool` | no change | Type unchanged. |
| 10 | `blueprints/applications.py:445` `resume_state` `cover_letter_md` | no change | Reads `generated_cover_letter_md or ""`; it now keeps the letter (O4). |
| 11 | `static/app.js` `_renderOutput` | update | Toggle `persistFailedNotice` from `data.persist_failed`. |
| 12 | `templates/index.html` (beside `editsDiscardedNotice`) | update | The banner element. |
| 13 | `tests/test_persist_run.py` | update | New tests. Existing ones stay valid: distinct proposal texts, a cross-candidate bullet still skipped, a non-empty letter still stored. |
| 14 | `tests/test_composition_staleness.py:285-288` | update | Tighten: assert the latest `resume_md` now that O9 is fixed. |
| 15 | `tests/test_application_routes.py`, `tests/ux/seeding.py`, `tests/test_cover_letter_detached.py` | no change | Seeders set the column directly; they don't go through persist. |
| 16 | `docs/wiki/pages/application-audit-chain.md`, `pipeline-stages.md`, `route-surface.md`, `iteration-audit-chain.md`, `frontend-wizard.md` | deferred to close-out | Scoped `/wiki-self-update` at the pre-close sweep (wiki-relevance check). |
| 17 | `docs/dev/architecture.md` | check at close-out | Update if it describes the persist as appending. |

---

## Deferred

- **The context-file analogue of the letter clobber** (`hardening.save_iteration_context`
  writes `last_generated_cover_letter = ""` on a résumé-only regenerate; diagnosis O4 observed
  it). It's out of D2a's scope, which is the DB column, and `resume_state` reads the DB column.
  Filed as its own item at close-out unless the owner folds it in.
- **`ApplicationRun.iteration` / `parent_run_id` lineage:** dormant by D1. Not touched.

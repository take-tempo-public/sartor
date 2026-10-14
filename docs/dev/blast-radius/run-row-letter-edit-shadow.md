# Blast radius — run-row-letter-edit-shadow

> **Branch:** `fix/run-row-letter-edit-shadow`
> **Status:** enumeration complete, written before the first production edit (the dossier
> and the instrument are commit 1; the fix is commit 2).

---

## Surface

No gated surface (`scripts/enforcement/blast_radius.py`) is edited: `blueprints/generation.py`
is not in the registry, and `db/models.py` (gated) is **not** touched; the column
`ApplicationRun.edited_cover_letter_text` (`db/models.py:831`) keeps its shape. The dossier is
written anyway because the change alters when a persisted column is cleared, and that column
has readers in other modules.

The change, all in `blueprints/generation.py`:

- `_clear_run_edits` (the helper that nulls the run row's typed edit after a discard);
- its two callers, `run_generation` (`/api/generate`) and the SSE twin
  (`/api/generate/stream`);
- `_persist_cover_letter_to_db` (the detached `/api/generate-cover-letter` write-back).

The behaviour change: the run row's `edited_cover_letter_text` becomes `None` exactly when
the context's `edited_cover_letter_text` is consumed (a generate or a detached route that
produced a letter, outside `carry_edits`).

---

## Enumeration

Run 2026-10-14 on `main` @ `562a3a0`, whole tree, `git grep -c` excluding `docs/**`,
`CHANGELOG*.md` and `db/vector_index/**`:

```
### edited_cover_letter_text
  analyzer.py:2  blueprints/applications.py:2  blueprints/generation.py:9
  blueprints/templates.py:2  db/models.py:1  hardening.py:7  static/app.js:1
  tests/test_analyzer_iteration.py:4  tests/test_app_iteration.py:6
  tests/test_application_routes.py:3  tests/test_hardening_iteration.py:8
  tests/test_live_preview_route.py:3  tests/test_regenerate_cover_letter.py:8
### _clear_run_edits                  blueprints/generation.py:3
### _persist_cover_letter_to_db       blueprints/generation.py:2
### resolve_cover_letter_after_generate
  blueprints/generation.py:4  hardening.py:3  tests/test_hardening_iteration.py:3
### _persist_edited_text_to_db        blueprints/generation.py:3
### raw SQL / templates / js: git grep -n -i edited_cover_letter -- '*.html' '*.js' '*.sql'
  'db/migrations/**'
  static/app.js:2657   static/app.js:3286          (0 hits in *.html, *.sql, db/migrations)
```

Names searched: the column and context key `edited_cover_letter_text`; the save-edits request
key `edited_cover_letter` (the `static/app.js:2657` hit); `_clear_run_edits`,
`_persist_cover_letter_to_db`, `_persist_edited_text_to_db`,
`resolve_cover_letter_after_generate`; `has_edits` (the derived flag, `applications.py:286`);
`cover_letter_md` (the `resume_state` key).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `blueprints/generation.py` `_clear_run_edits` (def ~`:896`) | **update** | Gains a `letter` flag; clears only the columns it is told to. |
| 2 | `blueprints/generation.py` `run_generation` (`~:1279-1288`) | **update** | Computes the clear from `resolve_cover_letter_after_generate`'s result, the same value the context uses. |
| 3 | `blueprints/generation.py` stream route (`~:1601-1609`) | **update** | Same change as #2; the two routes must not disagree. |
| 4 | `blueprints/generation.py` `_persist_cover_letter_to_db` (`~:153`) | **update** | Nulls the column in its existing session: zero extra round trips. Only caller is `run_generate_cover_letter` (`~:1828`). |
| 5 | `blueprints/generation.py` `_persist_edited_text_to_db` (`:111-150`), via `/api/save-edits` | no change | The writer of the column. Treats `None` as "no change", which is why a clear needs its own write. |
| 6 | `blueprints/applications.py:445` (`resume_state`: `edited_cover_letter_text or generated_cover_letter_md`) | no change | The READER that shows the defect. Correct once the column is cleared with the context. |
| 7 | `blueprints/applications.py:286` (`has_edits`) | no change | Derived flag; correct once the column is cleared. A5 shows it stays true under `carry_edits`, which is intended. |
| 8 | `hardening.py` `resolve_cover_letter_after_generate` / `save_iteration_context` | no change | The rule the run row will mirror. Not edited: the context side is already right (C2/C3 of item 162). |
| 9 | `blueprints/templates.py:1220`, `analyzer.py:2379` | no change | Read the CONTEXT key, not the column. |
| 10 | `static/app.js:2657`, `:3286` | no change | Request key and response key; the response is already correct (O1-O3 show `child_edited_cover_letter_text` null). |
| 11 | `db/models.py:831` | no change | Column definition; no schema change, no migration. |
| 12 | `docs/wiki/pages/application-audit-chain.md:152`, `iteration-audit-chain.md`, `context-set-contract.md`, `route-surface.md`, `frontend-wizard.md` | **check at close-out** | They describe the context-side rule; `application-audit-chain.md` also describes `_persist_cover_letter_to_db`. A scoped wiki pass decides, per the close-out checklist. |
| 13 | Tests naming the column (`tests/test_app_iteration.py:346`, `tests/test_application_routes.py`, `tests/test_regenerate_cover_letter.py` B8) | no change | They pin the SAVE write and the discard-keeps-letter rule (C1, C3 here re-pin both). Re-run in verification. |

---

## Deferred

- **Whether the frozen `carry_edits=True` path should keep a typed letter edit over a newly
  produced letter.** Observed in A5 and consistent across surfaces; a product question for the
  owner, not a defect of this item. Not changed here; filed as an owner-decision note if the
  owner wants it.
- **`resume_state` preferring the newer of edit vs generated.** Needs a per-field timestamp:
  a gated `db/models.py` change plus a migration. Rejected for this branch because mirroring
  the context makes the column correct without a schema change.

---

## Verification

A missed consumer would surface as a `ControlFailed` or a failing control in
`tests/test_run_row_letter_edit.py` (`C1`-`C3`, `A5`), or in the three suites that pin the
column's other writers and readers: `tests/test_app_iteration.py`,
`tests/test_application_routes.py`, `tests/test_regenerate_cover_letter.py`. The grep above is
re-derived at close-out and diffed against this table; a new hit is a site not yet decided.

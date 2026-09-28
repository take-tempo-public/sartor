# Diagnosis — CI `mypy .` fails on five untyped `scalar_one()` results after SQLAlchemy 2.1.1

> **Status:** root cause PROVEN by a version A/B with the same mypy (see Observed).
> **Branch:** `fix/sqlalchemy-2-1-mypy-drift`

## Symptom

PR #148 (Epic C) failed its required "Lint, type-check, test" check on py3.11, py3.12 and
py3.13. The local gate on the same tree was green, and Epic C touches none of the failing
files.

## Observed

- CI run `36356664874`, job `108725647394` (py3.13): `gate: FAILED at \`mypy .\` (exit 1)`,
  `Found 5 errors in 2 files (checked 384 source files)`:
  ```
  db/migrations/_sqlite_check_constraint.py:68: error: Need type annotation for "schema_version"  [var-annotated]
  tests/test_migrations_data_safety.py:99: error: Need type annotation for "application_id"  [var-annotated]
  tests/test_migrations_data_safety.py:258: error: Need type annotation for "status"  [var-annotated]
  tests/test_migrations_data_safety.py:268: error: Need type annotation for "schema_sql"  [var-annotated]
  tests/test_migrations_data_safety.py:340: error: Need type annotation for "schema_sql"  [var-annotated]
  ```
- Neither failing file nor `pyproject.toml` is in Epic C's diff
  (`git diff --stat origin/main...epic/c-diagnostics -- db tests/test_migrations_data_safety.py pyproject.toml`
  prints nothing).
- CI's install step resolved `mypy-2.3.1`, `sqlalchemy-2.1.1`, `alembic-1.20.0`. This
  machine has mypy 2.3.0, SQLAlchemy 2.0.49, alembic 1.18.4. `main`'s last CI run
  (`614cd59`, 2026-09-23) was `success`.
- **A/B in an isolated scratch venv, same mypy 2.3.1 + pydantic 2.12.5**, command
  `python -m mypy db/migrations/_sqlite_check_constraint.py tests/test_migrations_data_safety.py --follow-imports=silent`:
  - SQLAlchemy 2.0.49 / alembic 1.18.4 → `Success: no issues found in 2 source files`
  - SQLAlchemy 2.1.1 / alembic 1.20.0 → exactly the five errors above.

## Falsified

- "Epic C's changes broke typing": falsified by the empty diff above and by the A/B, which
  reproduces the failure on these two files alone with no Epic C code involved.
- "The mypy 2.3.0 → 2.3.1 bump is the cause": falsified. The A/B holds mypy at 2.3.1 and the
  failure follows the SQLAlchemy/alembic versions only.

## Inferred

All five sites assign `Result.scalar_one()` from a `text(...)` query to an unannotated local.
Under 2.0.49 that return type is `Any`. Under 2.1.1 it is evidently an unsolved type
variable, which mypy refuses to infer for a bare local. (Mechanism read from the error
class, not from SQLAlchemy's stub source; the A/B proves the version is the trigger.)

## Fix

Annotate each of the five locals with the type the query actually returns: `int` for
`PRAGMA schema_version` and the inserted id, `str` for `status` and `sqlite_master.sql`. That
passes on both SQLAlchemy lines and pins nothing. **Verification:** the same A/B, re-run with
the fix, must print `Success` under both version pairs, plus the full gate locally.
Scope: `main` is affected too (CI installs unpinned versions), so this lands on `main`
first, and Epic C (PR #148) merges `main` in afterwards (owner decision, 2026-09-27).

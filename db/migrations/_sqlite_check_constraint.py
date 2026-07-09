"""Batch-free CHECK-constraint rewrite for SQLite migrations.

SQLite has no ``ALTER TABLE ... DROP/ADD CONSTRAINT`` for CHECK constraints —
they're baked into the table's ``CREATE TABLE`` DDL, so the only way Alembic's
``batch_alter_table`` can change one is a full table rebuild
(``recreate="always"``: create a temp table, copy rows, DROP the original,
rename the temp table into place).

That rebuild is unsafe for any table that is the FK-referenced PARENT of a
child with ``ON DELETE CASCADE`` (e.g. ``application`` <- ``application_run``,
db/models.py). When SQLite drops the original table mid-rebuild with
``PRAGMA foreign_keys=ON`` (the app's connect-time default —
db/session.py:_set_sqlite_pragmas — applies to Alembic's engine too, since
the event listener is registered on the ``Engine`` class), it cascades and
silently deletes every child row referencing it — the entire
generation/audit history for every application.

Disabling ``PRAGMA foreign_keys`` around the rebuild does NOT fix this: SQLite
documents (and this project's ``db/migrations/env.py`` confirms empirically)
that the pragma is a no-op once a transaction is open, and Alembic's env.py
wraps the *whole* migration run in one ``context.begin_transaction()`` — so
there is no point inside ``upgrade()`` where toggling the pragma has any
effect on the connection Alembic hands us via ``op.get_bind()``.

This module sidesteps the problem entirely: instead of rebuilding the table,
it edits the stored ``CREATE TABLE`` text for one table directly via SQLite's
documented (if unusual) ``PRAGMA writable_schema`` escape hatch, then bumps
``PRAGMA schema_version`` so the new DDL is picked up immediately by the same
connection/transaction. No ``DROP TABLE`` is ever issued against the parent,
so the cascade has nothing to fire on — verified end-to-end (child rows
survive, ``PRAGMA integrity_check`` stays clean) in
``tests/test_migrations_data_safety.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection


def rewrite_check_constraint(
    bind: Connection,
    table: str,
    old_clause: str,
    new_clause: str,
) -> bool:
    """Swap one substring of ``table``'s CHECK clause in ``sqlite_master.sql``.

    Idempotent + defensive: a no-op (returns ``False``) if the table is
    missing or ``old_clause`` isn't found verbatim in its stored DDL (already
    rewritten, or a fresh DB created straight from the current — already
    tightened — ``db/models.py`` CheckConstraint text, in which case the
    caller's own column-presence guard should have already short-circuited
    before this is ever called). Returns ``True`` when the rewrite landed.
    """
    row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone()
    if row is None or row[0] is None or old_clause not in row[0]:
        return False
    new_sql = row[0].replace(old_clause, new_clause)

    schema_version = bind.execute(sa.text("PRAGMA schema_version")).scalar_one()
    bind.execute(sa.text("PRAGMA writable_schema=ON"))
    try:
        bind.execute(
            sa.text("UPDATE sqlite_master SET sql=:sql WHERE type='table' AND name=:t"),
            {"sql": new_sql, "t": table},
        )
        # PRAGMA statements don't accept bind parameters for the value
        # position in SQLite's grammar; schema_version is read back from the
        # DB itself just above (never user input), so inlining it is safe.
        bind.execute(sa.text(f"PRAGMA schema_version={int(schema_version) + 1}"))
    finally:
        bind.execute(sa.text("PRAGMA writable_schema=OFF"))
    return True

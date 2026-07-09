"""add outcome columns and expand status CHECK on application.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-29

Three changes to the application table:

1. Add sent_at TEXT (nullable) — ISO-8601 UTC timestamp auto-set when
   status transitions to 'submitted'.
2. Add outcome_at TEXT (nullable) — ISO-8601 UTC timestamp auto-set when
   status transitions to an outcome value (offer/accepted/rejected/no_response).
3. Add notes TEXT (nullable) — free-form candidate notes per application.
4. Expand status CHECK constraint to include the four new outcome values and
   remove 'closed' (renamed to 'withdrawn' in the same migration).

Backfill: existing 'closed' rows are moved to 'withdrawn' before the
constraint is replaced.

Idempotent: if sent_at already exists (fresh DB created from the updated
model via 0001's create_all), the upgrade is a no-op.

Data-safety fix (2026-07-08, forward-protection P0): this used to run the
column adds AND the CHECK-constraint swap through one
``batch_alter_table("application", recreate="always")``. `application` is a
CASCADE parent of `application_run` (db/models.py); with the app's
`PRAGMA foreign_keys=ON` connect-time default active during migrations too,
that recreate's internal `DROP TABLE application` cascade-deleted every run +
its audit trail on any DB that already had them (reproduced end-to-end:
downgrade → seed app+run → upgrade → run count 1→0). Columns now land via
native `op.add_column` (no batch — same avoidance as the PX-02 precedent in
migrations 0010/0011/0013); the CHECK swap goes through
`db.migrations._sqlite_check_constraint.rewrite_check_constraint`, which edits
the stored CREATE TABLE text in place instead of rebuilding the table — see
that module's docstring for the full root-cause writeup (in particular why
disabling the FK pragma around the recreate does NOT work here).
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sent_at/outcome_at/notes (native) + widen the status CHECK (rewrite)."""
    import sqlalchemy as sa
    from alembic import op

    from db.migrations._sqlite_check_constraint import rewrite_check_constraint

    bind = op.get_bind()

    # Idempotency: migration 0001 uses Base.metadata.create_all which reflects
    # the current model; on a fresh DB the new columns already exist.
    cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application)"))}
    if "sent_at" in cols:
        return

    # Backfill closed → withdrawn before the constraint is replaced.
    bind.execute(sa.text("UPDATE application SET status = 'withdrawn' WHERE status = 'closed'"))

    # Native ADD COLUMN (no batch): `application` is a PARENT of
    # application_run (ON DELETE CASCADE) — a batch recreate would
    # cascade-delete every run + its audit rows. See module docstring.
    op.add_column("application", sa.Column("sent_at", sa.Text(), nullable=True))
    op.add_column("application", sa.Column("outcome_at", sa.Text(), nullable=True))
    op.add_column("application", sa.Column("notes", sa.Text(), nullable=True))

    # CHECK-constraint expansion: also can't go through batch_alter_table (same
    # unsafe recreate) — rewrite the stored DDL text directly instead. No table
    # rebuild happens, so there's nothing for the FK cascade to fire on.
    rewrite_check_constraint(
        bind,
        "application",
        "status IN ('draft', 'submitted', 'interview', 'closed', 'withdrawn')",
        "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
        "'offer', 'accepted', 'rejected', 'no_response')",
    )


def downgrade() -> None:
    """Reverse upgrade(): narrow the status CHECK back (rewrite), then drop the columns (native)."""
    import sqlalchemy as sa
    from alembic import op

    from db.migrations._sqlite_check_constraint import rewrite_check_constraint

    bind = op.get_bind()

    cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application)"))}
    if "sent_at" not in cols:
        return

    # Backfill outcome statuses to withdrawn, then withdrawn → closed.
    bind.execute(
        sa.text(
            "UPDATE application SET status = 'withdrawn' "
            "WHERE status IN ('offer', 'accepted', 'rejected', 'no_response')"
        )
    )
    bind.execute(sa.text("UPDATE application SET status = 'closed' WHERE status = 'withdrawn'"))

    # Constraint first (values are already compliant with the narrower set
    # after the backfill above), then native DROP COLUMN. See upgrade().
    rewrite_check_constraint(
        bind,
        "application",
        "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
        "'offer', 'accepted', 'rejected', 'no_response')",
        "status IN ('draft', 'submitted', 'interview', 'closed', 'withdrawn')",
    )

    op.drop_column("application", "sent_at")
    op.drop_column("application", "outcome_at")
    op.drop_column("application", "notes")

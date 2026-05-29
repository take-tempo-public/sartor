"""add outcome columns and expand status CHECK on application

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
"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    # Idempotency: migration 0001 uses Base.metadata.create_all which reflects
    # the current model; on a fresh DB the new columns already exist.
    cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application)"))}
    if "sent_at" in cols:
        return

    # Backfill closed → withdrawn before the constraint is replaced.
    bind.execute(sa.text("UPDATE application SET status = 'withdrawn' WHERE status = 'closed'"))

    with op.batch_alter_table("application", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("sent_at", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("outcome_at", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.drop_constraint("ck_application_status", type_="check")
        batch_op.create_check_constraint(
            "ck_application_status",
            "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
            "'offer', 'accepted', 'rejected', 'no_response')",
        )


def downgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

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
    bind.execute(
        sa.text("UPDATE application SET status = 'closed' WHERE status = 'withdrawn'")
    )

    with op.batch_alter_table("application", recreate="always") as batch_op:
        batch_op.drop_column("sent_at")
        batch_op.drop_column("outcome_at")
        batch_op.drop_column("notes")
        batch_op.drop_constraint("ck_application_status", type_="check")
        batch_op.create_check_constraint(
            "ck_application_status",
            "status IN ('draft', 'submitted', 'interview', 'closed', 'withdrawn')",
        )

"""remove no_response, offer, accepted from application status CHECK

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-29

Schema correction: aligns the application status CHECK constraint with the
canonical five-value set agreed 2026-05-29.

no_response is redundant — submitted IS the no-response state. The old
'No response' outcome button wrongly stamped outcome_at on those rows.
offer and accepted are out of scope for this app.

Backfill:
  no_response -> submitted; outcome_at cleared (was wrongly set).
  offer/accepted rows deleted (pre-release -- no real data).

Idempotent: if the constraint no longer contains 'no_response', upgrade
is a no-op.
"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    schema_row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='application'")
    ).fetchone()
    if schema_row and "no_response" not in schema_row[0]:
        return

    bind.execute(
        sa.text(
            "UPDATE application SET status = 'submitted', outcome_at = NULL "
            "WHERE status = 'no_response'"
        )
    )
    bind.execute(
        sa.text("DELETE FROM application WHERE status IN ('offer', 'accepted')")
    )

    with op.batch_alter_table("application", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_application_status", type_="check")
        batch_op.create_check_constraint(
            "ck_application_status",
            "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')",
        )


def downgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    schema_row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='application'")
    ).fetchone()
    if schema_row and "no_response" in schema_row[0]:
        return

    with op.batch_alter_table("application", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_application_status", type_="check")
        batch_op.create_check_constraint(
            "ck_application_status",
            "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
            "'offer', 'accepted', 'rejected', 'no_response')",
        )

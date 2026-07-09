"""remove no_response, offer, accepted from application status CHECK.

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

Data-safety fix (2026-07-08, forward-protection P0): the CHECK-constraint
swap used to go through ``batch_alter_table("application", recreate="always")``
— unsafe for the same reason as migration 0006 (see that file's docstring and
db.migrations._sqlite_check_constraint for the full root-cause writeup):
`application` is a CASCADE parent of `application_run`, and the recreate's
internal DROP TABLE cascade-deleted every run + its audit trail on any DB that
already had them. Now routed through
``db.migrations._sqlite_check_constraint.rewrite_check_constraint``, which
edits the stored CREATE TABLE text in place instead of rebuilding the table —
no DROP TABLE, no cascade. The `no_response`/`offer`/`accepted` backfill
above (UPDATE + a targeted DELETE of specific rows) is unchanged: that DELETE
intentionally cascades those specific applications' own runs, which is the
declared relationship working as designed, not the recreate bug.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill no_response/offer/accepted, then narrow the status CHECK (rewrite)."""
    import sqlalchemy as sa
    from alembic import op

    from db.migrations._sqlite_check_constraint import rewrite_check_constraint

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
    bind.execute(sa.text("DELETE FROM application WHERE status IN ('offer', 'accepted')"))

    # No batch_alter_table recreate — see module docstring + migration 0006.
    rewrite_check_constraint(
        bind,
        "application",
        "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
        "'offer', 'accepted', 'rejected', 'no_response')",
        "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')",
    )


def downgrade() -> None:
    """Reverse upgrade(): widen the status CHECK back (rewrite; no data backfill)."""
    import sqlalchemy as sa
    from alembic import op

    from db.migrations._sqlite_check_constraint import rewrite_check_constraint

    bind = op.get_bind()

    schema_row = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='application'")
    ).fetchone()
    if schema_row and "no_response" in schema_row[0]:
        return

    rewrite_check_constraint(
        bind,
        "application",
        "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')",
        "status IN ('draft', 'submitted', 'interview', 'withdrawn', "
        "'offer', 'accepted', 'rejected', 'no_response')",
    )

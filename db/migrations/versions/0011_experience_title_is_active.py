"""Add experience_title.is_active (soft-retire flag for alternate titles).

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-29

The corpus "delete" on an alternate title was always a soft-retire (it cleared
is_official / truthful_enough_to_use), but the row stayed visible as an `ALT`
chip because nothing filtered it out. This adds a dedicated `is_active` flag —
parity with `Bullet.is_active` — so retired titles can be hidden by default and
revealed only via an explicit "show retired" toggle, while still being kept for
the audit FKs (application_run_title / proposal_review reference titles with
CASCADE / SET NULL).

Idempotency: 0001 builds a fresh DB via Base.metadata.create_all reflecting the
current model, so on a new clone the column already exists — the PRAGMA guard
skips the ALTER. On an upgraded DB the native ADD COLUMN lands.

Backfill: new rows default to active (server_default '1'). Rows that were
"retired" under the OLD semantics — not official, not pending, and marked
not-truthful — are flipped to is_active=0 so their prior retire intent survives
the migration instead of silently reappearing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _experience_title_columns(bind: sa.engine.Connection) -> set[str]:
    return {row[1] for row in bind.execute(sa.text("PRAGMA table_info(experience_title)"))}


def upgrade() -> None:
    """Add experience_title.is_active (native ADD COLUMN; idempotent) + backfill retired rows."""
    # Native ALTER TABLE ADD COLUMN (no batch). `experience_title` is a PARENT
    # of application_run_title; a batch recreate would cascade-delete those run
    # choices while FK enforcement is on (it can't be disabled inside alembic's
    # transaction). Native ADD avoids the reconstruction entirely.
    bind = op.get_bind()
    if "is_active" not in _experience_title_columns(bind):
        op.add_column(
            "experience_title",
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        )
        # Preserve prior retire intent: old "deleted" titles had their
        # eligibility flags cleared but no is_active column to hide them.
        bind.execute(
            sa.text(
                "UPDATE experience_title SET is_active = 0 "
                "WHERE truthful_enough_to_use = 0 "
                "AND is_official = 0 "
                "AND is_pending_review = 0"
            )
        )


def downgrade() -> None:
    """Drop experience_title.is_active (native DROP COLUMN)."""
    # Native DROP COLUMN (SQLite >= 3.35). See upgrade() — no batch recreate of
    # the parent `experience_title` table, so no FK cascade onto run choices.
    bind = op.get_bind()
    if "is_active" in _experience_title_columns(bind):
        op.drop_column("experience_title", "is_active")

"""Add application.is_active (soft-retire flag for prior applications).

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-01

The Prior Applications list grew unbounded with no way to hide poor examples or
abandoned drafts (walkthrough J1). This adds a dedicated `is_active` flag — parity
with `ExperienceTitle.is_active` (migration 0011) and `Bullet.is_active` — so
retired applications can be hidden by default and revealed only via an explicit
"show retired" toggle, while still being kept for their runs + audit trail.

Idempotency: 0001 builds a fresh DB via Base.metadata.create_all reflecting the
current model, so on a new clone the column already exists — the PRAGMA guard
skips the ALTER. On an upgraded DB the native ADD COLUMN lands.

Native ADD COLUMN (no batch): `application` is a PARENT of application_run
(cascade delete). A batch recreate would cascade-delete every run + its audit
rows while FK enforcement is on (it can't be disabled inside alembic's
transaction). Native ADD avoids the reconstruction entirely. No backfill — every
existing application starts active (server_default '1').
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _application_columns(bind: sa.engine.Connection) -> set[str]:
    return {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application)"))}


def upgrade() -> None:
    """Add application.is_active (native ADD COLUMN; idempotent)."""
    bind = op.get_bind()
    if "is_active" not in _application_columns(bind):
        op.add_column(
            "application",
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    """Drop application.is_active (native DROP COLUMN)."""
    bind = op.get_bind()
    if "is_active" in _application_columns(bind):
        op.drop_column("application", "is_active")

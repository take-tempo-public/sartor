"""Add experience.is_active (soft-retire flag for whole roles).

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-08

`DELETE /api/experiences/<id>` implemented "retire" as a cascade onto the role's
child bullets (`UPDATE bullet SET is_active=0 WHERE experience_id=?`) and nothing
else. For a role with ZERO bullets that affects zero rows, still returns 200, and
leaves the role listed in the corpus and rendering into generated output —
`Experience` carried no retire flag of its own. Observed at four layers in
`docs/dev/diagnosis/experience-soft-retire.md`. This adds the dedicated
`is_active` column, parity with `Bullet.is_active` / `ExperienceTitle.is_active` /
`Application.is_active`, so a role can be retired (and restored) in its own right.

Idempotency: 0001 builds a fresh DB via `Base.metadata.create_all` reflecting the
current model, so on a new clone the column already exists — the PRAGMA guard
skips the ALTER. On an upgraded DB the native ADD COLUMN lands.

Backfill: NONE, deliberately — and this is the one place this revision departs
from the `0011` precedent it otherwise copies. 0011 could recover prior retire
intent because the old semantics left a recognizable signature on the row itself
(eligibility flags cleared). Here there is no such signature: the only thing the
old retire ever wrote was `bullet.is_active`, and "every bullet retired" is
indistinguishable from "this role never had bullets typed in yet". Inferring
retirement from it would silently hide live roles from the corpus and from
generation, which is a worse failure than the one being fixed. Every existing row
comes up active; users re-retire the handful they meant to.

Note on `server_default="1"`: SQLite needs a default to add a NOT NULL column to
a non-empty table, so the ALTER supplies one — but the model declares only a
Python-side `default=1`, matching all three siblings. The two DDL shapes
therefore differ, and one raw-SQL case can tell them apart: an INSERT that omits
`is_active` fails on a `create_all`-built DB (no SQL DEFAULT) and quietly
succeeds on a DB that got here by incremental `alembic upgrade` (the ALTER's
DEFAULT applies). Test and fresh-clone DBs fail closed on a sloppy raw INSERT;
a migrated one does not. No current code path depends on either behavior.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _experience_columns(bind: sa.engine.Connection) -> set[str]:
    return {row[1] for row in bind.execute(sa.text("PRAGMA table_info(experience)"))}


def upgrade() -> None:
    """Add experience.is_active (native ADD COLUMN; idempotent). No backfill."""
    # Native ALTER TABLE ADD COLUMN (no batch). `experience` is a PARENT of
    # experience_title, bullet AND experience_summary_item; a batch recreate
    # copies the table and drops the original, which cascade-deletes all three
    # child tables while FK enforcement is on (it cannot be disabled inside
    # alembic's transaction). Native ADD avoids the reconstruction entirely.
    # Same rationale as 0011 on experience_title, with one more child table at
    # stake.
    bind = op.get_bind()
    if "is_active" not in _experience_columns(bind):
        op.add_column(
            "experience",
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    """Drop experience.is_active (native DROP COLUMN)."""
    # Native DROP COLUMN (SQLite >= 3.35). See upgrade() — no batch recreate of
    # the parent `experience` table, so no FK cascade onto its three child tables.
    bind = op.get_bind()
    if "is_active" in _experience_columns(bind):
        op.drop_column("experience", "is_active")

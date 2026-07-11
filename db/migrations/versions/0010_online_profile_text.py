"""PX-02 — add candidate.online_profile_text (cached opt-in profile/website scrape).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-13

PX-02 re-wires the dead `scraper.fetch_profile_content` into the runtime path.
The scraped LinkedIn/website/portfolio text needs its OWN cache column —
`Candidate.profile_text` was repurposed by β.6 as the positioning summary
(résumé basics.summary fallback; overwritten at generate by the chosen
SummaryItem), so reusing it would corrupt summaries and be clobbered. This adds
a distinct nullable `online_profile_text` column.

Idempotency: 0001 uses Base.metadata.create_all reflecting the current model
state, so on a fresh DB the column is already present — the PRAGMA guard skips
the ALTER. On an upgraded DB (candidate without the column), the ALTER lands.
No backfill: the field starts empty and is populated by the
POST /api/users/<u>/profile/fetch route when the user opts in.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _candidate_columns(bind: sa.engine.Connection) -> set[str]:
    return {row[1] for row in bind.execute(sa.text("PRAGMA table_info(candidate)"))}


def upgrade() -> None:
    """Add candidate.online_profile_text (native ADD COLUMN; idempotent)."""
    # Native ALTER TABLE ADD COLUMN (no batch). A nullable column needs no
    # table reconstruction, and `candidate` is a PARENT table — a batch
    # recreate would cascade-delete child rows (experience, skill, …) whenever
    # PRAGMA foreign_keys is ON during the move (it can't be turned off inside
    # alembic's migration transaction). Native ADD/DROP avoids that entirely.
    bind = op.get_bind()
    if "online_profile_text" not in _candidate_columns(bind):
        op.add_column("candidate", sa.Column("online_profile_text", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop candidate.online_profile_text (native DROP COLUMN)."""
    # Native DROP COLUMN (SQLite ≥ 3.35). See upgrade() — no batch recreate of
    # the parent `candidate` table, so no FK cascade onto child rows.
    bind = op.get_bind()
    if "online_profile_text" in _candidate_columns(bind):
        op.drop_column("candidate", "online_profile_text")

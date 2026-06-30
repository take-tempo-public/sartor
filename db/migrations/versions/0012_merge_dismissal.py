"""Add merge_dismissal (candidate 'keep separate' decisions for similar roles).

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-29

The merge-suggestion scan flags pairs of experiences that look like the same
role (different framings/dates). When the user reviews a pair and chooses "keep
separate," we persist that decision here so the pair stops re-surfacing on every
corpus load. Pair stored order-normalized (exp_a_id < exp_b_id) and uniqued.

Idempotency: 0001 builds a fresh DB via Base.metadata.create_all reflecting the
current model, so on a new clone the table already exists — the guard skips the
create. On an upgraded DB the create lands.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(bind: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    """Create the merge_dismissal table (idempotent)."""
    bind = op.get_bind()
    if not _table_exists(bind, "merge_dismissal"):
        op.create_table(
            "merge_dismissal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("candidate_id", sa.Integer(), nullable=False),
            sa.Column("exp_a_id", sa.Integer(), nullable=False),
            sa.Column("exp_b_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["candidate_id"], ["candidate.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["exp_a_id"], ["experience.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["exp_b_id"], ["experience.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "candidate_id", "exp_a_id", "exp_b_id", name="uq_merge_dismissal_pair"
            ),
        )
        op.create_index("ix_merge_dismissal_candidate", "merge_dismissal", ["candidate_id"])


def downgrade() -> None:
    """Drop the merge_dismissal table."""
    bind = op.get_bind()
    if _table_exists(bind, "merge_dismissal"):
        op.drop_index("ix_merge_dismissal_candidate", table_name="merge_dismissal")
        op.drop_table("merge_dismissal")

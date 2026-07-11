"""B.4 (Sprint 6.6) — add experience_summary_item + _tag tables; backfill from Experience.summary.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-12

B.4 introduces the per-role intro paragraph as an ExperienceSummaryItem
CorpusItem specialization (per docs/PRODUCT_SHAPE.md §3): the line a
recruiter reads first under a single job, as a first-class, multi-variant,
scorable, taggable unit. Mirrors SummaryItem but parented by Experience.

Backfill: every Experience row with a non-empty `summary` gets one
ExperienceSummaryItem row carrying that text (source='imported').
Experience.summary stays on the schema (denormalized cache) for
back-compat; new code queries ExperienceSummaryItem.

Idempotency: 0001 uses Base.metadata.create_all reflecting the current
model state, so on a fresh DB these tables are already present — skip in
that case. On an upgraded DB, the create + backfill land normally. The
backfill skips experiences that already have at least one row, so a
re-run after a manual add never duplicates the seed.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(bind: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    """Create experience_summary_item + _tag tables and backfill from Experience.summary (idempotent)."""
    bind = op.get_bind()

    # experience_summary_item
    if not _table_exists(bind, "experience_summary_item"):
        op.create_table(
            "experience_summary_item",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experience_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("label", sa.String(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_pending_review", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(), nullable=False, server_default="manual"),
            sa.Column("has_outcome", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["experience_id"],
                ["experience.id"],
                ondelete="CASCADE",
            ),
            sa.CheckConstraint(
                "source IN ('manual', 'imported', 'llm_proposed')",
                name="ck_experience_summary_item_source",
            ),
        )
        op.create_index(
            "ix_experience_summary_item_active_pending_order",
            "experience_summary_item",
            ["experience_id", "is_active", "is_pending_review", "display_order"],
        )

    # experience_summary_item_tag
    if not _table_exists(bind, "experience_summary_item_tag"):
        op.create_table(
            "experience_summary_item_tag",
            sa.Column("experience_summary_item_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
            sa.PrimaryKeyConstraint("experience_summary_item_id", "tag_id"),
            sa.ForeignKeyConstraint(
                ["experience_summary_item_id"],
                ["experience_summary_item.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["tag_id"],
                ["tag.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_experience_summary_item_tag_tag",
            "experience_summary_item_tag",
            ["tag_id"],
        )

    # Backfill: one ExperienceSummaryItem per Experience with non-empty
    # summary. Idempotent: skip when the experience already has at least
    # one row (so re-running after a manual add doesn't duplicate the seed).
    # Plain (non-f) string — the only "interpolation" is the constant
    # strftime() timestamp, inlined here so there's no string-built SQL for
    # the ruff-changed hook's S608 to flag (no user input is ever formatted in).
    bind.execute(
        sa.text("""
        INSERT INTO experience_summary_item (
            experience_id, text, label, display_order, is_active,
            is_pending_review, source, has_outcome,
            created_at, updated_at
        )
        SELECT e.id,
               e.summary,
               NULL,
               0,
               1,
               0,
               'imported',
               0,
               strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
               strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        FROM experience e
        WHERE e.summary IS NOT NULL
          AND TRIM(e.summary) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM experience_summary_item s WHERE s.experience_id = e.id
          )
    """)
    )


def downgrade() -> None:
    """Drop experience_summary_item_tag then experience_summary_item (idempotent)."""
    bind = op.get_bind()
    if _table_exists(bind, "experience_summary_item_tag"):
        op.drop_index(
            "ix_experience_summary_item_tag_tag",
            table_name="experience_summary_item_tag",
        )
        op.drop_table("experience_summary_item_tag")
    if _table_exists(bind, "experience_summary_item"):
        op.drop_index(
            "ix_experience_summary_item_active_pending_order",
            table_name="experience_summary_item",
        )
        op.drop_table("experience_summary_item")

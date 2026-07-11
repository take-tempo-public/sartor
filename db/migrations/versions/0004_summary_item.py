"""β.6a — add summary_item + summary_item_tag tables; backfill from Candidate.profile_text.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-24

Phase β.6 introduces the SummaryItem CorpusItem specialization
(per docs/PRODUCT_SHAPE.md §3): the candidate's positioning summary
as a first-class, multi-variant, scorable, taggable, pin/exclude-able
unit. Mirrors Bullet but parented by Candidate.

Backfill: every Candidate row with a non-empty profile_text gets a
SummaryItem row carrying that text. Candidate.profile_text stays on
the schema (denormalized "go-to summary" cache) for back-compat;
new code queries SummaryItem.

Idempotency: 0001 uses Base.metadata.create_all reflecting the
current model state, so on a fresh DB these tables are already
present. Skip in that case. On an upgraded DB, the create + backfill
land normally.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(bind: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    """Create summary_item + summary_item_tag tables and backfill from Candidate.profile_text (idempotent)."""
    bind = op.get_bind()

    # summary_item
    if not _table_exists(bind, "summary_item"):
        op.create_table(
            "summary_item",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("candidate_id", sa.Integer(), nullable=False),
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
                ["candidate_id"],
                ["candidate.id"],
                ondelete="CASCADE",
            ),
            sa.CheckConstraint(
                "source IN ('manual', 'imported', 'llm_proposed')",
                name="ck_summary_item_source",
            ),
        )
        op.create_index(
            "ix_summary_item_candidate_active_pending_order",
            "summary_item",
            ["candidate_id", "is_active", "is_pending_review", "display_order"],
        )

    # summary_item_tag
    if not _table_exists(bind, "summary_item_tag"):
        op.create_table(
            "summary_item_tag",
            sa.Column("summary_item_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
            sa.PrimaryKeyConstraint("summary_item_id", "tag_id"),
            sa.ForeignKeyConstraint(
                ["summary_item_id"],
                ["summary_item.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["tag_id"],
                ["tag.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index("ix_summary_item_tag_tag", "summary_item_tag", ["tag_id"])

    # Backfill: one SummaryItem per Candidate with non-empty profile_text.
    # Idempotent: skip when the candidate already has at least one
    # SummaryItem row (so re-running the migration after a manual
    # SummaryItem add doesn't duplicate the seed).
    # Plain (non-f) string — the only "interpolation" is the constant
    # strftime() timestamp, inlined here so there's no string-built SQL for
    # the ruff-changed hook's S608 to flag (no user input is ever formatted in).
    bind.execute(
        sa.text("""
        INSERT INTO summary_item (
            candidate_id, text, label, display_order, is_active,
            is_pending_review, source, has_outcome,
            created_at, updated_at
        )
        SELECT c.id,
               c.profile_text,
               NULL,
               0,
               1,
               0,
               'imported',
               0,
               strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
               strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        FROM candidate c
        WHERE c.profile_text IS NOT NULL
          AND TRIM(c.profile_text) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM summary_item s WHERE s.candidate_id = c.id
          )
    """)
    )


def downgrade() -> None:
    """Drop summary_item_tag then summary_item (idempotent)."""
    bind = op.get_bind()
    if _table_exists(bind, "summary_item_tag"):
        op.drop_index("ix_summary_item_tag_tag", table_name="summary_item_tag")
        op.drop_table("summary_item_tag")
    if _table_exists(bind, "summary_item"):
        op.drop_index(
            "ix_summary_item_candidate_active_pending_order",
            table_name="summary_item",
        )
        op.drop_table("summary_item")

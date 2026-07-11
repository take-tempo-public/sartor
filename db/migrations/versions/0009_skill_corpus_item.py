"""B.5 (Sprint 6.6) — promote Skill to a Corpus Item; add skill_tag; backfill lifecycle columns.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-12

B.5 promotes the individual Skill into a full Corpus Item (per
docs/PRODUCT_SHAPE.md): the flat skill row gains the same lifecycle as
Bullet (is_active + is_pending_review + source + display_order + tags), so
it participates in the recommend / pin / drop / curate / tag machinery.
recommend_skills selects + orders the active, approved skills per JD;
suggest_skills proposes corpus-grounded new skills as pending for the user
to approve/deny.

Schema change on `skill`:
  + display_order, is_active, is_pending_review, source, created_at, updated_at
  + new `skill_tag` join (mirrors bullet_tag)

Backfill: every pre-existing Skill row becomes source='imported',
is_active=1, is_pending_review=0, with display_order set to preserve the
prior name-sorted order (build_context.py reads skills ORDER BY name today,
so the no-recommendation generate output is unchanged).

Idempotency: 0001 uses Base.metadata.create_all reflecting the current
model state, so on a fresh DB the new columns + skill_tag are already
present — the PRAGMA / table-exists guards skip the ALTER in that case. On
an upgraded DB (skill with only the legacy columns), the ALTER + backfill
land normally.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(bind: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _skill_columns(bind: sa.engine.Connection) -> set[str]:
    return {row[1] for row in bind.execute(sa.text("PRAGMA table_info(skill)"))}


def upgrade() -> None:
    """Promote skill to a Corpus Item (lifecycle columns + skill_tag); backfill display_order (idempotent)."""
    bind = op.get_bind()

    # Promote the skill table to a Corpus Item. Guard on `source`: present
    # means a fresh-create DB (0001 reflected the current model) — skip.
    if "source" not in _skill_columns(bind):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with op.batch_alter_table("skill") as batch_op:
            batch_op.add_column(
                sa.Column("display_order", sa.Integer(), nullable=False, server_default="0")
            )
            batch_op.add_column(
                sa.Column("is_active", sa.Integer(), nullable=False, server_default="1")
            )
            batch_op.add_column(
                sa.Column("is_pending_review", sa.Integer(), nullable=False, server_default="0")
            )
            # Legacy rows are imported corpus data. New rows always pass
            # source explicitly via the ORM default ('manual').
            batch_op.add_column(
                sa.Column("source", sa.String(), nullable=False, server_default="imported")
            )
            batch_op.add_column(
                sa.Column("created_at", sa.String(), nullable=False, server_default=now)
            )
            batch_op.add_column(
                sa.Column("updated_at", sa.String(), nullable=False, server_default=now)
            )
            batch_op.create_check_constraint(
                "ck_skill_source", "source IN ('manual', 'imported', 'llm_proposed')"
            )
        op.create_index(
            "ix_skill_candidate_active_pending_order",
            "skill",
            ["candidate_id", "is_active", "is_pending_review", "display_order"],
        )
        # Backfill display_order to preserve the prior per-candidate
        # name-sorted order (ties broken by id). Plain (non-f) string — no
        # user input is ever formatted in, so the ruff-changed S608 check
        # has nothing to flag.
        bind.execute(
            sa.text("""
            UPDATE skill
            SET display_order = (
                SELECT COUNT(*) FROM skill s2
                WHERE s2.candidate_id = skill.candidate_id
                  AND (s2.name < skill.name
                       OR (s2.name = skill.name AND s2.id < skill.id))
            )
        """)
        )

    # skill_tag (mirrors bullet_tag)
    if not _table_exists(bind, "skill_tag"):
        op.create_table(
            "skill_tag",
            sa.Column("skill_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
            sa.PrimaryKeyConstraint("skill_id", "tag_id"),
            sa.ForeignKeyConstraint(["skill_id"], ["skill.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_skill_tag_tag", "skill_tag", ["tag_id"])


def downgrade() -> None:
    """Drop skill_tag and revert skill's Corpus Item lifecycle columns (idempotent)."""
    bind = op.get_bind()

    if _table_exists(bind, "skill_tag"):
        op.drop_index("ix_skill_tag_tag", table_name="skill_tag")
        op.drop_table("skill_tag")

    if "source" in _skill_columns(bind):
        inspector = sa.inspect(bind)
        idx_names = {ix["name"] for ix in inspector.get_indexes("skill")}
        if "ix_skill_candidate_active_pending_order" in idx_names:
            op.drop_index("ix_skill_candidate_active_pending_order", table_name="skill")
        with op.batch_alter_table("skill") as batch_op:
            batch_op.drop_constraint("ck_skill_source", type_="check")
            batch_op.drop_column("updated_at")
            batch_op.drop_column("created_at")
            batch_op.drop_column("source")
            batch_op.drop_column("is_pending_review")
            batch_op.drop_column("is_active")
            batch_op.drop_column("display_order")

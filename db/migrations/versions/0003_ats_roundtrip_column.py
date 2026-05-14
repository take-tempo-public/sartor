"""add ats_roundtrip_json to application_run

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13

Phase C.3: a nullable TEXT column on application_run carrying the JSON
result of the post-generate ATS round-trip self-check. Surfaces on the
dashboard so users + tuners can spot fixtures where generated docx don't
parse back cleanly.

Schema-only change. No data migration.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotency: migration 0001 uses Base.metadata.create_all which reflects
    # the CURRENT model state, so on a freshly-created DB this column is
    # already present. Skip in that case. On a DB created before this column
    # was added to the model, the ALTER lands normally.
    bind = op.get_bind()
    cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application_run)"))}
    if "ats_roundtrip_json" in cols:
        return
    with op.batch_alter_table("application_run") as batch_op:
        batch_op.add_column(sa.Column("ats_roundtrip_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(application_run)"))}
    if "ats_roundtrip_json" not in cols:
        return
    with op.batch_alter_table("application_run") as batch_op:
        batch_op.drop_column("ats_roundtrip_json")

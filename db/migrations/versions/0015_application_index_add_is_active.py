"""Add is_active to the application composite index (PX-38).

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-11

`ix_application_candidate_status_updated` (candidate_id, status, updated_at)
omitted `is_active` even though `list_applications`' default path
(`blueprints/applications.py`) filters `candidate_id` + `is_active` on every
call (status is an opt-in `?status=` query param, filtered only sometimes).
Without `is_active` in the index, the default listing query can't use a fully
covering equality prefix.

New column order: (candidate_id, is_active, status, updated_at) — is_active
leads right after candidate_id since it's the more commonly-applied equality
filter; status stays third so the status-filtered path is still a
contiguous, usable prefix; updated_at stays trailing for the ORDER BY.

Native `op.create_index` / `op.drop_index` only — no `batch_alter_table`.
Index rebuilds are metadata-only DDL in SQLite (no table copy, no row
touch), so this carries none of the cascade-delete risk that
`batch_alter_table("application", recreate=...)` would on `application`'s
CASCADE children (`application_run`, migration 0013's docstring). Verified
zero row loss upgrading AND downgrading on a scratch DB seeded with an
application + run + run child (see
`tests/test_migrations_data_safety.py::TestApplicationIndexAddIsActive`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_INDEX_COLUMNS = ("candidate_id", "status", "updated_at")
_NEW_INDEX_COLUMNS = ("candidate_id", "is_active", "status", "updated_at")


def _existing_indexes(bind: sa.engine.Connection) -> set[str]:
    return {
        row[0]
        for row in bind.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='application'")
        )
    }


def upgrade() -> None:
    """Drop + recreate the index with is_active added (idempotent, metadata-only)."""
    bind = op.get_bind()
    names = _existing_indexes(bind)
    if "ix_application_candidate_status_updated" in names:
        op.drop_index("ix_application_candidate_status_updated", table_name="application")
    op.create_index(
        "ix_application_candidate_status_updated",
        "application",
        list(_NEW_INDEX_COLUMNS),
    )


def downgrade() -> None:
    """Restore the original 3-column index (idempotent, metadata-only)."""
    bind = op.get_bind()
    names = _existing_indexes(bind)
    if "ix_application_candidate_status_updated" in names:
        op.drop_index("ix_application_candidate_status_updated", table_name="application")
    op.create_index(
        "ix_application_candidate_status_updated",
        "application",
        list(_OLD_INDEX_COLUMNS),
    )

"""seed bundled persona templates

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13

Phase C.1: insert one `persona_template` row per bundled `.docx` file under
`personas/bundled/`. These rows have `candidate_id=NULL` (visible to every
candidate) and `source='bundled'`.

Idempotent: upgrade is a no-op if a bundled row with the same `path` already
exists. Re-running migrations is safe.

The build script (`scripts/build_bundled_templates.py:PRESETS`) is the
canonical source for the template metadata; this migration mirrors it. If
you add a new preset, update both places.
"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Mirrors scripts/build_bundled_templates.py:PRESETS. The two lists must stay
# aligned manually; a test in tests/test_bundled_templates.py asserts this.
BUNDLED_SEED_ROWS: list[dict] = [
    {
        "name": "Classic Single-Column",
        "path": "personas/bundled/classic.docx",
        "description": (
            "Maximally ATS-safe baseline. Arial 11pt, conservative spacing, "
            "uppercase section headings. The default fallback when no "
            "candidate-chosen persona matches a JD's role tag."
        ),
    },
    {
        "name": "Modern Single-Column",
        "path": "personas/bundled/modern.docx",
        "description": (
            "Calibri 11pt with mild typographic refinement: small-caps section "
            "headings, tighter line spacing. Good middle-ground for most roles."
        ),
    },
    {
        "name": "Compact (Senior)",
        "path": "personas/bundled/compact.docx",
        "description": (
            "Calibri 10pt with very tight spacing. Built for senior candidates "
            "with lots of experience to fit on one page."
        ),
    },
    {
        "name": "Spacious (Career Changer / Junior)",
        "path": "personas/bundled/spacious.docx",
        "description": (
            "Arial 11pt with generous spacing. Built for early-career or "
            "career-changing candidates with less to fit, prioritizes readability."
        ),
    },
    {
        "name": "Hybrid Tech",
        "path": "personas/bundled/hybrid_tech.docx",
        "description": (
            "Helvetica 11pt with underline-accented section headings. Mild "
            "typographic distinction for engineering/design/AI roles."
        ),
    },
]


def upgrade() -> None:
    from datetime import datetime, timezone

    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    persona_template = sa.table(
        "persona_template",
        sa.column("candidate_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("path", sa.String),
        sa.column("description", sa.Text),
        sa.column("source", sa.String),
        sa.column("is_default", sa.Integer),
        sa.column("created_at", sa.String),
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for seed in BUNDLED_SEED_ROWS:
        # Idempotency: skip if a row with this path already exists (so re-running
        # migrations against a populated DB doesn't double-seed).
        existing = bind.execute(
            sa.text("SELECT id FROM persona_template WHERE path = :path"),
            {"path": seed["path"]},
        ).first()
        if existing is not None:
            continue
        op.bulk_insert(
            persona_template,
            [{
                "candidate_id": None,  # bundled = available to every candidate
                "name": seed["name"],
                "path": seed["path"],
                "description": seed["description"],
                "source": "bundled",
                "is_default": 0,  # candidate's own default override picks per role_tag
                "created_at": now,
            }],
        )


def downgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()
    for seed in BUNDLED_SEED_ROWS:
        bind.execute(
            sa.text("DELETE FROM persona_template WHERE path = :path AND source = 'bundled'"),
            {"path": seed["path"]},
        )

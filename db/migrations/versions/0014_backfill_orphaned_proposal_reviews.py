"""Backfill ProposalReview rows orphaned by the corpus accept/retire bridge.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-08

Before this release, the corpus onboarding-review accept routes
(`accept_bullet` / `accept_experience_title` / `accept_experience_all` /
`accept_all_pending`, `blueprints/corpus/curation.py`) and the retire routes
(`delete_bullet` / `delete_experience_title`, `blueprints/corpus/experiences.py`)
— the ONLY UI-reachable review path — cleared `is_pending_review` / `is_active`
directly and never touched `ProposalReview.decision`. That column stayed
`"pending"` forever for any bullet/title the user had already accepted or
retired through the corpus UI, so the applications-list "N to review" badge
(`blueprints/applications.py`, counts `ProposalReview.decision == "pending"`)
over-counted indefinitely. The route bridge landing alongside this migration
(`blueprints/corpus/_shared.py:_resolve_proposal_reviews`) stops new orphans;
this is the one-off data backfill for rows that already went stale before the
fix — 49 such rows on the owner's clone.

Data-only migration, UPDATE statements only — no ALTER/batch_alter_table.
`proposal_review` has two ON DELETE SET NULL parents (`bullet`,
`experience_title`, both non-CASCADE toward proposal_review) — irrelevant here
since we never touch schema, only rows — but the project convention (see
migration 0013's docstring) is native/plain DML on any table in a
CASCADE-adjacent neighborhood, never `batch_alter_table`, so this follows
suit by construction (no schema op at all).

Resolution mirrors what `blueprints/corpus/proposals.py:decide_proposal_route`
would have recorded had the user gone through `/api/proposals/<id>/decide`
instead of the corpus accept/retire buttons:
  - referenced bullet/title now `is_active=0` (retired)            -> "reject"
  - referenced bullet/title now `is_active=1, is_pending_review=0`
    (accepted, still live)                                          -> "accept_original"
A pending row whose referenced bullet/title is STILL pending review is left
alone — it is not orphaned, just not yet reviewed.

Idempotent: every UPDATE is scoped to `decision = 'pending'`, so a re-run
only touches rows still in that queue-eligible pending state.

`downgrade()` is a documented no-op: the migration only resolves rows that
were already stale (indistinguishable, post-hoc, from any other row a human
subsequently decided the ordinary way), so reverting the decision column
back to "pending" would misrepresent already-resolved review history. This
mirrors the "irreversible backfill" shape (no schema change to undo).
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill orphaned ProposalReview rows (UPDATE-only; see module docstring)."""
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    # Bullet-backed pending rows whose bullet has since been retired.
    bind.execute(
        sa.text(
            "UPDATE proposal_review "
            "SET decision = 'reject', decided_at = :now "
            "WHERE decision = 'pending' "
            "  AND bullet_id IS NOT NULL "
            "  AND bullet_id IN (SELECT id FROM bullet WHERE is_active = 0)"
        ),
        {"now": _now()},
    )
    # Bullet-backed pending rows whose bullet has since been accepted (still live).
    bind.execute(
        sa.text(
            "UPDATE proposal_review "
            "SET decision = 'accept_original', decided_at = :now "
            "WHERE decision = 'pending' "
            "  AND bullet_id IS NOT NULL "
            "  AND bullet_id IN ("
            "    SELECT id FROM bullet WHERE is_active = 1 AND is_pending_review = 0"
            "  )"
        ),
        {"now": _now()},
    )
    # Title-backed pending rows whose title has since been retired.
    bind.execute(
        sa.text(
            "UPDATE proposal_review "
            "SET decision = 'reject', decided_at = :now "
            "WHERE decision = 'pending' "
            "  AND experience_title_id IS NOT NULL "
            "  AND experience_title_id IN (SELECT id FROM experience_title WHERE is_active = 0)"
        ),
        {"now": _now()},
    )
    # Title-backed pending rows whose title has since been accepted (still live).
    bind.execute(
        sa.text(
            "UPDATE proposal_review "
            "SET decision = 'accept_original', decided_at = :now "
            "WHERE decision = 'pending' "
            "  AND experience_title_id IS NOT NULL "
            "  AND experience_title_id IN ("
            "    SELECT id FROM experience_title "
            "    WHERE is_active = 1 AND is_pending_review = 0"
            "  )"
        ),
        {"now": _now()},
    )


def downgrade() -> None:
    """No-op — see module docstring (irreversible, post-hoc backfill)."""


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

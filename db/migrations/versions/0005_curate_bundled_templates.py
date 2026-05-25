"""curate bundled persona templates for v1.0.0

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-25

v1.0.0 template curation. Three changes:

1. **Drop Compact (Senior).** The "compact" template used a sidebar-
   labels-left / content-right layout in its HTML companion. That
   pattern is functionally a two-column layout and breaks most ATS
   parsers via text-layer scrambling — see Jobscan's 2026 ATS
   formatting analysis (jobscan.co/blog/resume-tables-columns-ats).
   The .docx variant didn't have this problem (single column at the
   docx level), but the divergence between .docx and .html outputs
   was misleading: users picking "compact" got an ATS-unsafe PDF.

2. **Rename Hybrid Tech → Tech (ATS-optimized).** The original
   hybrid_tech ported community ideas around inline-code chips and
   underline accents. The chip styling using monospace `<code>` was
   ambiguous for ATS — some parsers handle inline `<code>` cleanly,
   others treat it as a separator. Rebuilt around
   jsonresume-theme-dev-ats (MIT, by asqrzk) which is explicitly
   ATS-tested: Georgia serif, centered name, plain disc bullets,
   underlined section headings, no glyphs.

3. **Update Modern description.** The new Modern HTML/CSS is inspired
   by the official jsonresume-theme-class (MIT, by James Spencer /
   the JSON Resume org). Blue accent header band; single column;
   Roboto-or-system-sans typography; ATS-safe. The .docx still uses
   the original Calibri + small-caps shape — visual divergence
   between .docx and PDF is an accepted v1.0 limitation, to be
   reconciled in v1.0.1 when the .docx generator can emit the new
   class-inspired style.

Idempotent: upgrade is a no-op if the rows have already been
curated. Re-running migrations is safe.
"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()

    # 1. Drop the Compact (Senior) bundled row. ApplicationRun rows that
    # reference it via persona_template_id keep their reference NULLed
    # (FK is ON DELETE SET NULL — see db/models.py:ApplicationRun
    # persona_template_id column definition).
    bind.execute(
        sa.text(
            "DELETE FROM persona_template "
            "WHERE source = 'bundled' AND path = 'personas/bundled/compact.docx'"
        )
    )

    # 2. Rename Hybrid Tech → Tech (ATS-optimized), update path to
    # personas/bundled/tech.docx, refresh description. Idempotent —
    # only updates if the OLD path is still present.
    bind.execute(
        sa.text(
            "UPDATE persona_template SET "
            "  name = 'Tech (ATS-optimized)', "
            "  path = 'personas/bundled/tech.docx', "
            "  description = :desc "
            "WHERE source = 'bundled' AND path = 'personas/bundled/hybrid_tech.docx'"
        ),
        {
            "desc": (
                "Georgia 11pt with centered name and underlined section "
                "headings. Single column, plain bullets, no inline glyphs — "
                "designed for engineering / data / AI roles where the parser "
                "must catch every tech keyword verbatim. Inspired by the "
                "community jsonresume-theme-dev-ats."
            )
        },
    )

    # 3. Refresh Modern description to reflect the new class-inspired
    # HTML/CSS. The .docx itself is unchanged at this rev (see commit
    # message); the description here covers the HTML/PDF output, which
    # is the primary surface for ATS submissions.
    bind.execute(
        sa.text(
            "UPDATE persona_template SET "
            "  description = :desc "
            "WHERE source = 'bundled' AND path = 'personas/bundled/modern.docx'"
        ),
        {
            "desc": (
                "Single-column with a subtle blue accent header band. "
                "System sans-serif (Roboto / Helvetica / Arial). ATS-safe "
                "and visually distinct from the Classic baseline. Inspired "
                "by the official jsonresume-theme-class."
            )
        },
    )


def downgrade() -> None:
    from datetime import datetime, timezone

    import sqlalchemy as sa
    from alembic import op

    bind = op.get_bind()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Restore the Compact row.
    bind.execute(
        sa.text(
            "INSERT INTO persona_template "
            "(candidate_id, name, path, description, source, is_default, created_at) "
            "VALUES (NULL, :name, :path, :desc, 'bundled', 0, :ts)"
        ),
        {
            "name": "Compact (Senior)",
            "path": "personas/bundled/compact.docx",
            "desc": (
                "Calibri 10pt with very tight spacing. Built for senior "
                "candidates with lots of experience to fit on one page."
            ),
            "ts": now,
        },
    )

    # Restore the Hybrid Tech row.
    bind.execute(
        sa.text(
            "UPDATE persona_template SET "
            "  name = 'Hybrid Tech', "
            "  path = 'personas/bundled/hybrid_tech.docx', "
            "  description = :desc "
            "WHERE source = 'bundled' AND path = 'personas/bundled/tech.docx'"
        ),
        {
            "desc": (
                "Helvetica 11pt with underline-accented section headings. "
                "Mild typographic distinction for engineering/design/AI roles."
            )
        },
    )

    # Restore the original Modern description.
    bind.execute(
        sa.text(
            "UPDATE persona_template SET "
            "  description = :desc "
            "WHERE source = 'bundled' AND path = 'personas/bundled/modern.docx'"
        ),
        {
            "desc": (
                "Calibri 11pt with mild typographic refinement: small-caps "
                "section headings, tighter line spacing. Good middle-ground "
                "for most roles."
            )
        },
    )

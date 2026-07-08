"""Cross-cutting serializers + DB-scope helper for the corpus seam.

The shared layer of the `blueprints/corpus/` sub-package (Sprint 8.3d). Holds the
response-shape serializers used by more than one corpus route submodule — plus
`_tag_list` / `_skill_to_dict`, which are ALSO imported by the two
still-in-`app.py` *applications* routes (`get_application_composition`,
`suggest_application_skills`) until the applications seam moves at 8.3f (owner
decision, Sprint 8.3d: corpus owns the canonical copy; `app.py` imports it).

Pure leaf: imports nothing from `blueprints.corpus` (so the route submodules can
import from here without a cycle) and never imports `app.py`. DB-layer imports stay
lazy inside the one function that needs them, mirroring the monolith.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from db.models import (
        Candidate,
        Certification,
        Education,
        Experience,
        ExperienceSummaryItem,
        Skill,
        SummaryItem,
    )


def _experience_summary_dict(exp: Experience) -> dict:
    """Compact experience row for the Career Corpus list view."""
    official = next((t for t in exp.titles if t.is_official), None)
    active_titles = [t for t in exp.titles if t.is_active]
    active_bullets = [b for b in exp.bullets if b.is_active]
    pending_bullets = [b for b in active_bullets if b.is_pending_review]
    return {
        "id": exp.id,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "display_order": exp.display_order,
        "summary": exp.summary,
        "official_title": official.title if official else None,
        "title_count": len(active_titles),
        "bullet_count_active": len(active_bullets),
        "bullet_count_pending": len(pending_bullets),
    }


def _tag_list(tag_links: list) -> list[dict]:
    """Serialize a bullet/title's tag_links (each carries .tag) for the UI."""
    out = []
    for link in tag_links:
        t = link.tag
        if t is None:
            continue
        out.append(
            {
                "id": t.id,
                "value": t.value,
                "display_value": t.display_value,
                "kind": t.kind,
            }
        )
    return sorted(out, key=lambda d: d["value"])


def _experience_detail_dict(exp: Experience, *, include_retired: bool = False) -> dict:
    """Full experience payload for the inline expand view.

    Retired titles + bullets (is_active=0) are excluded by default so the corpus
    only ever shows live rows; pass ``include_retired=True`` (the route's
    ?include_retired=1) to surface them for the "show retired" toggle.
    """
    titles = sorted(
        (t for t in exp.titles if include_retired or t.is_active),
        key=lambda t: (0 if t.is_official else 1, t.id),
    )
    bullets = sorted(
        (b for b in exp.bullets if include_retired or b.is_active),
        key=lambda b: b.display_order,
    )
    return {
        "id": exp.id,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "display_order": exp.display_order,
        "summary": exp.summary,
        "titles": [
            {
                "id": t.id,
                "title": t.title,
                "is_active": bool(t.is_active),
                "is_official": bool(t.is_official),
                "truthful_enough_to_use": bool(t.truthful_enough_to_use),
                "is_pending_review": bool(t.is_pending_review),
                "source": t.source,
                "notes": t.notes,
                "tags": _tag_list(t.tag_links),
            }
            for t in titles
        ],
        "bullets": [
            {
                "id": b.id,
                "text": b.text,
                "display_order": b.display_order,
                "is_active": bool(b.is_active),
                "is_pending_review": bool(b.is_pending_review),
                "has_outcome": bool(b.has_outcome),
                "pattern_kind": b.pattern_kind,
                "source": b.source,
                "tags": _tag_list(b.tag_links),
            }
            for b in bullets
        ],
    }


def _load_experience_for_candidate(
    session: Session,
    experience_id: int,
) -> tuple[Experience | None, Candidate | None]:
    """Look up an Experience + its candidate, returning (None, None) when not found.

    Defense-in-depth helper used by every route that mutates an experience-scoped row.
    """
    from db.models import Candidate, Experience

    exp = session.query(Experience).filter_by(id=experience_id).first()
    if exp is None:
        return None, None
    candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
    return exp, candidate


def _summary_item_to_dict(s: SummaryItem) -> dict:
    """Shared response shape for SummaryItem routes."""
    return {
        "id": s.id,
        "candidate_id": s.candidate_id,
        "text": s.text,
        "label": s.label,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "has_outcome": bool(s.has_outcome),
        "source": s.source,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def _experience_summary_item_to_dict(s: ExperienceSummaryItem) -> dict:
    """Shared response shape for ExperienceSummaryItem routes."""
    return {
        "id": s.id,
        "experience_id": s.experience_id,
        "text": s.text,
        "label": s.label,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "has_outcome": bool(s.has_outcome),
        "source": s.source,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def _skill_to_dict(s: Skill, tags: list | None = None) -> dict:
    """Shared response shape for Skill routes."""
    return {
        "id": s.id,
        "candidate_id": s.candidate_id,
        "name": s.name,
        "category": s.category,
        "proficiency": s.proficiency,
        "years": s.years,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "source": s.source,
        "tags": tags if tags is not None else [],
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def _education_to_dict(ed: Education) -> dict:
    """Shared response shape for Education routes (F-04, UX-W1).

    No `source` / `is_pending_review` / `created_at` / `updated_at` — the
    `Education` model (db/models.py) carries neither the LLM-proposal
    lifecycle nor timestamps that Skill/SummaryItem do; this mirrors the
    model exactly rather than padding out fields that don't exist.
    """
    return {
        "id": ed.id,
        "candidate_id": ed.candidate_id,
        "institution": ed.institution,
        "degree": ed.degree,
        "field": ed.field,
        "start_date": ed.start_date,
        "end_date": ed.end_date,
        "display_order": ed.display_order,
        "is_active": bool(ed.is_active),
        "notes": ed.notes,
    }


def _certification_to_dict(c: Certification) -> dict:
    """Shared response shape for Certification routes (F-04, UX-W1). See `_education_to_dict`."""
    return {
        "id": c.id,
        "candidate_id": c.candidate_id,
        "name": c.name,
        "issuer": c.issuer,
        "issued": c.issued,
        "expires": c.expires,
        "display_order": c.display_order,
        "is_active": bool(c.is_active),
    }

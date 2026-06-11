"""Build a JSON Resume v1.0 document directly from the candidate's
corpus (Candidate + Experience + Bullet + SummaryItem rows), applying
composition_overrides if a context file is in scope.

Why this exists
---------------
β.2–β.4 introduced JSON Resume as the canonical intermediate format
and wired the live preview to read it from a `resume_*.jsonresume.json`
sidecar written by `generator.generate_resume()`. That coupling meant
the preview only existed AFTER a user had run /api/generate at least
once, and it reflected whatever was last GENERATED rather than the
candidate's current curation state.

This module breaks that coupling. It reads the DB directly and emits
a JSON Resume document that reflects the candidate's live state:

  - The chosen SummaryItem variant (pin > recommendation > first active
    > Candidate.profile_text)
  - Active bullets per experience, respecting composition_overrides
    (pin/exclude/added) when a context_path is provided
  - All structured Candidate identity fields (no markdown parsing →
    no smushed name/subtitle/contact triad in the header)

Used by:
  - /api/applications/<id>/preview for in-app live preview
    (corpus-direct, no sidecar)
  - /api/users/<u>/preview for "show me what my résumé looks like with
    this template" BEFORE the user starts an application
  - /api/applications/<id>/preview-pdf for the PDF render path

The output validates against the standard JSON Resume v1.0 schema.
Our corpus-only fields (chosen variant id, summary source, etc.) live
under `meta.callback.*` so themes that don't know about callback.
extensions just ignore them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_json_resume_from_corpus(
    session,
    candidate_id: int,
    *,
    application_id: int | None = None,
    context_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a JSON Resume v1.0 dict assembled from the candidate's
    corpus, applying composition_overrides (read from `context_path`)
    when supplied. SQLAlchemy session is the caller's responsibility —
    we don't open or close it.

    Args:
        session: An open SQLAlchemy session.
        candidate_id: The Candidate.id to render.
        application_id: Optional — written into meta.callback.application_id
            so the rendered HTML knows which application it belongs to.
            Has no effect on resolution; that's `context_path`'s job.
        context_path: Optional path to a context_*.json file on disk
            (typically `output/{username}/context_*.json`). When present,
            composition_overrides (pinned / excluded / added / pinned_summary_id)
            and llm_summary_recommendation / llm_recommendations are read
            from it and applied. When absent, the function falls back to
            "all active bullets" and "first-active summary variant".

    The output has the structure JSON Resume themes expect:
      {
        "$schema":      "...",
        "basics":       {name, label, email, phone, url, summary, profiles},
        "work":         [...],
        "skills":       [...],
        "education":    [],   # not modeled in the DB yet (v1.1+)
        "certificates": [],   # same
        "projects":     [],   # same
        "meta":         {"callback": {...}, "language": "en-US"},
      }
    """
    from db.models import Candidate, Experience
    from json_resume import SCHEMA_URI

    candidate = session.query(Candidate).filter_by(id=candidate_id).first()
    if candidate is None:
        # Empty document so themes don't crash on missing keys
        return _empty_document()

    ctx = _read_context_file(context_path)

    # ---- Resolve the chosen summary variant ----
    pinned_summary_id, recommended_summary_id = _read_summary_choices(ctx)
    chosen_summary_text, summary_source = _resolve_chosen_summary_text(
        session, candidate.id,
        pinned_id=pinned_summary_id,
        recommended_id=recommended_summary_id,
        fallback_text=candidate.profile_text or "",
    )

    # ---- Read bullet pin/exclude/added overrides ----
    pin_bullets, ex_bullets, add_bullets = _read_bullet_overrides(ctx)
    rec_by_exp = _read_recommendations_by_experience(ctx)
    # feat/compose-add-title — per-experience title pin (experience_id → title_id)
    title_choices = _read_title_choices(ctx)

    # ---- Assemble basics ----
    basics: dict[str, Any] = {}
    if candidate.name:
        basics["name"] = candidate.name
    # No first-class candidate-label in the schema yet; the SummaryItem
    # label could fill in but is per-variant. v1.1+ may add a separate
    # Candidate.label column. For now, leave label empty.
    if candidate.email:
        basics["email"] = candidate.email
    if candidate.phone:
        basics["phone"] = candidate.phone
    if chosen_summary_text:
        basics["summary"] = chosen_summary_text

    profiles: list[dict[str, str]] = []
    if candidate.linkedin_url:
        profiles.append({
            "network":  "LinkedIn",
            "url":      candidate.linkedin_url,
            "username": _username_from_linkedin(candidate.linkedin_url),
        })
    if candidate.website_url:
        # Website goes on basics.url per JSON Resume convention
        basics["url"] = candidate.website_url
    if profiles:
        basics["profiles"] = profiles

    # ---- Assemble work[] ----
    experiences = (
        session.query(Experience)
        .filter_by(candidate_id=candidate.id)
        .order_by(Experience.start_date.desc(), Experience.id.desc())
        .all()
    )
    work: list[dict[str, Any]] = []
    for exp in experiences:
        entry: dict[str, Any] = {}
        if exp.company:
            entry["name"] = exp.company
        if exp.location:
            entry["location"] = exp.location
        # feat/compose-add-title — the user's per-JD pin wins (when still
        # eligible); otherwise official preferred, then first eligible.
        title_text = (
            _pinned_title_text(exp, title_choices.get(exp.id))
            or _official_title_text(exp)
            or _first_title_text(exp)
        )
        if title_text:
            entry["position"] = title_text
        if exp.start_date:
            entry["startDate"] = exp.start_date
        if exp.end_date:
            entry["endDate"] = exp.end_date
        if exp.summary:
            entry["summary"] = exp.summary

        # Highlights: active bullets, with pin/exclude/added applied.
        # If a context file with llm_recommendations exists for this
        # experience, restrict to the effective set:
        #     (recommended ∪ added ∪ pinned) − excluded
        # Otherwise show all active bullets minus the excluded ones.
        rec_ids = rec_by_exp.get(exp.id)
        highlights: list[str] = []
        for b in sorted(
            (b for b in exp.bullets if b.is_active),
            key=lambda b: (b.display_order or 0, b.id),
        ):
            if b.id in ex_bullets:
                continue
            include = (
                rec_ids is None  # no recommendations → all-active path
                or b.id in rec_ids
                or b.id in pin_bullets
                or b.id in add_bullets
            )
            if include and b.text:
                highlights.append(b.text)
        if highlights:
            entry["highlights"] = highlights

        # Only emit experience if there's something meaningful in it.
        if entry.get("name") or entry.get("position") or highlights:
            work.append(entry)

    # ---- Assemble skills[] ----
    skills = _collect_skills(session, candidate.id)

    # ---- Final document ----
    doc: dict[str, Any] = {
        "$schema":      SCHEMA_URI,
        "basics":       basics,
        "work":         work,
        "education":    [],
        "skills":       skills,
        "certificates": [],
        "projects":     [],
        "meta": {
            "callback": {
                "version":  "1.0",
                "candidate_id": candidate.id,
                "application_id": application_id,
                "chosen_summary_id": (
                    pinned_summary_id
                    if pinned_summary_id is not None
                    else recommended_summary_id
                ),
                "summary_source": summary_source,
                "bullet_overrides_active": bool(
                    pin_bullets or ex_bullets or add_bullets
                ),
            },
            "language": "en-US",
        },
    }
    return doc


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _empty_document() -> dict[str, Any]:
    from json_resume import SCHEMA_URI

    return {
        "$schema":      SCHEMA_URI,
        "basics":       {},
        "work":         [],
        "education":    [],
        "skills":       [],
        "certificates": [],
        "projects":     [],
        "meta": {"callback": {"version": "1.0"}, "language": "en-US"},
    }


def _read_context_file(context_path: str | Path | None) -> dict[str, Any]:
    """Load a context_*.json file off disk. Returns {} on any failure
    (missing path, bad JSON, IO error) — callers fall through to the
    "no overrides" path."""
    if not context_path:
        return {}
    cp = Path(context_path)
    if not cp.exists():
        return {}
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_summary_choices(ctx: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return (pinned_summary_id, recommended_summary_id) from a loaded
    context dict. Either or both can be None."""
    overrides = ctx.get("composition_overrides") or {}
    rec_block = ctx.get("llm_summary_recommendation") or {}
    rec = rec_block.get("recommendation") if isinstance(rec_block, dict) else None

    def _coerce(val: Any) -> int | None:
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    pinned = _coerce(
        overrides.get("pinned_summary_id") if isinstance(overrides, dict) else None,
    )
    recommended = _coerce(
        rec.get("summary_item_id") if isinstance(rec, dict) else None,
    )
    return pinned, recommended


def _read_title_choices(ctx: dict[str, Any]) -> dict[int, int]:
    """feat/compose-add-title — return {experience_id: pinned_title_id} from a
    loaded context dict's `composition_overrides.pinned_title_ids`. Empty when
    absent/invalid; keys and ids coerced to int (JSON persists keys as strings)."""
    overrides = ctx.get("composition_overrides") or {}
    raw = overrides.get("pinned_title_ids") if isinstance(overrides, dict) else None
    out: dict[int, int] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[int(k)] = int(v)
            except (TypeError, ValueError):
                continue
    return out


def _resolve_chosen_summary_text(
    session,
    candidate_id: int,
    *,
    pinned_id: int | None,
    recommended_id: int | None,
    fallback_text: str,
) -> tuple[str, str]:
    """Walk the priority chain (pin > recommendation > first-active >
    fallback). Returns (text, source) where source is one of
    "pinned" | "recommended" | "first_active" | "candidate_default" | "none"."""
    from db.models import SummaryItem

    def _lookup(sid: int | None) -> str | None:
        if sid is None:
            return None
        row = (
            session.query(SummaryItem)
            .filter_by(id=sid, candidate_id=candidate_id, is_active=1)
            .first()
        )
        if row and (row.text or "").strip():
            return row.text
        return None

    text = _lookup(pinned_id)
    if text:
        return text, "pinned"
    text = _lookup(recommended_id)
    if text:
        return text, "recommended"

    # No application-scoped choice — fall back to the candidate's first
    # active variant if any, then to the legacy profile_text. Order:
    # display_order, then id.
    first_variant = (
        session.query(SummaryItem)
        .filter_by(candidate_id=candidate_id, is_active=1)
        .order_by(SummaryItem.display_order, SummaryItem.id)
        .first()
    )
    if first_variant and (first_variant.text or "").strip():
        return first_variant.text, "first_active"
    fallback = fallback_text.strip()
    if fallback:
        return fallback, "candidate_default"
    return "", "none"


def _read_bullet_overrides(
    ctx: dict[str, Any],
) -> tuple[set[int], set[int], set[int]]:
    """Return (pinned, excluded, added) bullet-id sets from a loaded
    context dict's composition_overrides. Empty sets when absent."""
    ov = ctx.get("composition_overrides") or {}
    if not isinstance(ov, dict):
        return set(), set(), set()
    return (
        {int(x) for x in (ov.get("pinned") or [])},
        {int(x) for x in (ov.get("excluded") or [])},
        {int(x) for x in (ov.get("added") or [])},
    )


def _read_recommendations_by_experience(
    ctx: dict[str, Any],
) -> dict[int, set[int]]:
    """Return {experience_id: {bullet_ids}} from ctx["llm_recommendations"].
    Empty when no recommendations exist (caller falls back to all-active)."""
    rec_map = ctx.get("llm_recommendations") or {}
    if not isinstance(rec_map, dict):
        return {}
    out: dict[int, set[int]] = {}
    for k, v in rec_map.items():
        try:
            eid = int(k)
        except (TypeError, ValueError):
            continue
        if not isinstance(v, dict):
            continue
        out[eid] = {int(b) for b in (v.get("bullet_ids") or [])}
    return out


def _official_title_text(exp: Any) -> str | None:
    for t in exp.titles or []:
        if t.is_official:
            return t.title
    return None


def _first_title_text(exp: Any) -> str | None:
    for t in (exp.titles or []):
        if t.title:
            return t.title
    return None


def _pinned_title_text(exp: Any, pinned_id: int | None) -> str | None:
    """feat/compose-add-title — the user's per-JD title pick for this experience,
    when it's still an eligible (is_official OR truthful_enough_to_use) title of
    this experience. Returns None when unset / stale / ineligible so the caller
    falls through to the official-or-first default (non-pinned output unchanged)."""
    if pinned_id is None:
        return None
    for t in exp.titles or []:
        if t.id == pinned_id and (t.is_official or t.truthful_enough_to_use):
            return t.title
    return None


def _collect_skills(session: Any, candidate_id: int) -> list[dict[str, Any]]:
    """Return JSON Resume skills[] from the candidate's Skill rows.
    Currently flat — one row per name. Grouping via SkillGroupItem
    is v1.1+ work.
    Skill rows are not soft-retired (no is_active column yet), so we
    return all of them ordered by id."""
    from db.models import Skill

    rows = (
        session.query(Skill)
        .filter_by(candidate_id=candidate_id)
        .order_by(Skill.id)
        .all()
    )
    return [{"name": r.name} for r in rows if (r.name or "").strip()]


def _username_from_linkedin(url: str) -> str:
    """Pull the LinkedIn handle from a profile URL. Best-effort; falls
    back to the empty string on unexpected formats."""
    if not url:
        return ""
    if "/in/" in url:
        tail = url.rsplit("/in/", 1)[-1]
        return tail.split("/")[0].split("?")[0]
    return ""

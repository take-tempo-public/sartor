"""Build a JSON Resume v1.0 document directly from the candidate's corpus.

Assembles from Candidate + Experience + Bullet + SummaryItem rows,
applying composition_overrides if a context file is in scope.

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
under `meta.sartor.*` so themes that don't know about sartor.
extensions just ignore them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from db.models import Experience


def build_json_resume_from_corpus(
    session: Session,
    candidate_id: int,
    *,
    application_id: int | None = None,
    context_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a JSON Resume v1.0 dict assembled from the candidate's corpus.

    Applies composition_overrides (read from `context_path`) when supplied.
    SQLAlchemy session is the caller's responsibility — we don't open or close it.

    Args:
        session: An open SQLAlchemy session.
        candidate_id: The Candidate.id to render.
        application_id: Optional — written into meta.sartor.application_id
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
        "meta":         {"sartor": {...}, "language": "en-US"},
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
        session,
        candidate.id,
        pinned_id=pinned_summary_id,
        recommended_id=recommended_summary_id,
        fallback_text=candidate.profile_text or "",
    )

    # ---- Read bullet pin/exclude/added overrides ----
    pin_bullets, ex_bullets, add_bullets = _read_bullet_overrides(ctx)
    rec_by_exp = _read_recommendations_by_experience(ctx)
    # feat/compose-add-title — per-experience title pin (experience_id → title_id)
    title_choices = _read_title_choices(ctx)
    # B.4 (Sprint 6.6) — per-role intro opt-in toggle + per-role picks
    # (experience_id → ExperienceSummaryItem id). Opt-in: a role's work[].summary
    # is emitted ONLY when the toggle is on AND the role has an explicit pick.
    use_experience_summaries, chosen_experience_summary_ids = _read_experience_summary_choices(ctx)
    # B.5 (Sprint 6.6) — per-JD skill curation: recommend_skills ordering +
    # pin/drop/reorder overrides. Pending/retired skills are excluded by
    # _collect_skills; with no recommendation + no overrides this is every
    # active, approved skill in display order.
    skill_pinned, skill_excluded, skill_order = _read_skill_overrides(ctx)
    skill_rec_ids = _read_skill_recommendations(ctx)

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
        profiles.append(
            {
                "network": "LinkedIn",
                "url": candidate.linkedin_url,
                "username": _username_from_linkedin(candidate.linkedin_url),
            }
        )
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
        # B.4 — opt-in per-role intro. Emit work[].summary ONLY when the user
        # turned on the "Add role intros" toggle AND chose a variant for THIS
        # role. No auto-fallback to the legacy exp.summary — it lives on as a
        # backfilled ExperienceSummaryItem variant, surfaced only when chosen.
        if use_experience_summaries:
            role_intro = _resolve_chosen_experience_summary_text(
                session,
                exp.id,
                chosen_experience_summary_ids.get(exp.id),
            )
            if role_intro:
                entry["summary"] = role_intro

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
    skills = _collect_skills(
        session,
        candidate.id,
        pinned=skill_pinned,
        excluded=skill_excluded,
        skill_order=skill_order,
        rec_ids=skill_rec_ids,
    )

    # ---- Final document ----
    doc: dict[str, Any] = {
        "$schema": SCHEMA_URI,
        "basics": basics,
        "work": work,
        "education": [],
        "skills": skills,
        "certificates": [],
        "projects": [],
        "meta": {
            "sartor": {
                "version": "1.0",
                "candidate_id": candidate.id,
                "application_id": application_id,
                "chosen_summary_id": (
                    pinned_summary_id if pinned_summary_id is not None else recommended_summary_id
                ),
                "summary_source": summary_source,
                # B.4 — per-role intro opt-in state + the picks that were applied.
                "use_experience_summaries": use_experience_summaries,
                "chosen_experience_summary_ids": {
                    str(eid): iid for eid, iid in chosen_experience_summary_ids.items()
                }
                if use_experience_summaries
                else {},
                "bullet_overrides_active": bool(pin_bullets or ex_bullets or add_bullets),
                # B.5 — whether per-JD skill curation was applied + the
                # recommend_skills ordering it was seeded from.
                "skill_curation_active": bool(
                    skill_rec_ids is not None or skill_pinned or skill_excluded or skill_order
                ),
                "recommended_skill_ids": skill_rec_ids or [],
            },
            "language": "en-US",
        },
    }
    return doc


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _empty_document() -> dict[str, Any]:
    """Return an empty JSON Resume document skeleton (``$schema`` plus empty top-level sections)."""
    from json_resume import SCHEMA_URI

    return {
        "$schema": SCHEMA_URI,
        "basics": {},
        "work": [],
        "education": [],
        "skills": [],
        "certificates": [],
        "projects": [],
        "meta": {"sartor": {"version": "1.0"}, "language": "en-US"},
    }


def _read_context_file(context_path: str | Path | None) -> dict[str, Any]:
    """Load a context_*.json file off disk.

    Returns {} on any failure (missing path, bad JSON, IO error) — callers
    fall through to the "no overrides" path.
    """
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
    """Return (pinned_summary_id, recommended_summary_id) from a loaded context dict.

    Either or both can be None.
    """
    overrides = ctx.get("composition_overrides") or {}
    rec_block = ctx.get("llm_summary_recommendation") or {}
    rec = rec_block.get("recommendation") if isinstance(rec_block, dict) else None

    def _coerce(val: str | int | float | None) -> int | None:
        """Coerce ``val`` to ``int``, or ``None`` if it is None or non-numeric."""
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
    """Return {experience_id: pinned_title_id} from the context dict (feat/compose-add-title).

    Reads `composition_overrides.pinned_title_ids`. Empty when absent/invalid;
    keys and ids coerced to int (JSON persists keys as strings).
    """
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
    session: Session,
    candidate_id: int,
    *,
    pinned_id: int | None,
    recommended_id: int | None,
    fallback_text: str,
) -> tuple[str, str]:
    """Walk the priority chain (pin > recommendation > first-active > fallback).

    Returns (text, source) where source is one of
    "pinned" | "recommended" | "first_active" | "candidate_default" | "none".
    """
    from db.models import SummaryItem

    def _lookup(sid: int | None) -> str | None:
        """Return the active ``SummaryItem`` text for ``sid`` (scoped to this candidate), or ``None``."""
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


def _read_experience_summary_choices(ctx: dict[str, Any]) -> tuple[bool, dict[int, int]]:
    """Return (use_experience_summaries, {experience_id: item_id}) from the context dict (B.4).

    Reads `composition_overrides`. The toggle gates whether the per-role picks
    are applied; keys/ids are coerced to int (JSON persists keys as strings).
    Absent / invalid → (False, {}).
    """
    overrides = ctx.get("composition_overrides") or {}
    if not isinstance(overrides, dict):
        return False, {}
    use_flag = bool(overrides.get("use_experience_summaries"))
    raw = overrides.get("chosen_experience_summary_ids") or {}
    out: dict[int, int] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[int(k)] = int(v)
            except (TypeError, ValueError):
                continue
    return use_flag, out


def _resolve_chosen_experience_summary_text(
    session: Session,
    experience_id: int,
    item_id: int | None,
) -> str:
    """Return the chosen ExperienceSummaryItem's text for a role, or "" (B.4).

    Returns "" when none is chosen / the variant is missing / inactive / belongs
    to a different role. OPT-IN: NO fallback to the legacy Experience.summary (it
    lives on as a backfilled variant, surfaced only when explicitly chosen).
    """
    if item_id is None:
        return ""
    from db.models import ExperienceSummaryItem

    row = (
        session.query(ExperienceSummaryItem)
        .filter_by(id=item_id, experience_id=experience_id, is_active=1)
        .first()
    )
    if row and (row.text or "").strip():
        return row.text
    return ""


def _read_bullet_overrides(
    ctx: dict[str, Any],
) -> tuple[set[int], set[int], set[int]]:
    """Return (pinned, excluded, added) bullet-id sets from composition_overrides.

    Empty sets when absent.
    """
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

    Empty when no recommendations exist (caller falls back to all-active).
    """
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


def _official_title_text(exp: Experience) -> str | None:
    """Return this experience's official title text, or ``None`` if it has none."""
    for t in exp.titles or []:
        if t.is_official:
            return t.title
    return None


def _first_title_text(exp: Experience) -> str | None:
    """Return this experience's first non-empty title text, or ``None``."""
    for t in exp.titles or []:
        if t.title:
            return t.title
    return None


def _pinned_title_text(exp: Experience, pinned_id: int | None) -> str | None:
    """Return the user's per-JD title pick for this experience (feat/compose-add-title).

    Only returned when the pick is still an eligible (is_official OR
    truthful_enough_to_use) title of this experience. Returns None when unset /
    stale / ineligible so the caller falls through to the official-or-first
    default (non-pinned output unchanged).
    """
    if pinned_id is None:
        return None
    for t in exp.titles or []:
        if t.id == pinned_id and (t.is_official or t.truthful_enough_to_use):
            return t.title
    return None


def _read_skill_overrides(
    ctx: dict[str, Any],
) -> tuple[set[int], set[int], list[int]]:
    """Return (pinned, excluded, skill_order) skill-id curation from composition_overrides (B.5).

    Empty sets / list when absent.
    """
    ov = ctx.get("composition_overrides") or {}
    if not isinstance(ov, dict):
        return set(), set(), []

    def _id_set(key: str) -> set[int]:
        """Coerce the int-like values under ``key`` in the overrides into a ``set[int]`` (skipping non-numeric)."""
        out: set[int] = set()
        for x in ov.get(key) or []:
            try:
                out.add(int(x))
            except (TypeError, ValueError):
                continue
        return out

    order: list[int] = []
    for x in ov.get("skill_order") or []:
        try:
            order.append(int(x))
        except (TypeError, ValueError):
            continue
    return _id_set("pinned_skill_ids"), _id_set("excluded_skill_ids"), order


def _read_skill_recommendations(ctx: dict[str, Any]) -> list[int] | None:
    """Return ordered recommended skill ids from ctx["llm_skill_recommendations"] (B.5).

    Reads .recommendation.skill_ids. None when no recommendation has been run
    (caller falls back to all active+approved skills); an empty recommendation
    also maps to None so a degenerate run never blanks the skills section.
    """
    block = ctx.get("llm_skill_recommendations")
    if not isinstance(block, dict):
        return None
    rec = block.get("recommendation")
    if not isinstance(rec, dict):
        return None
    raw = rec.get("skill_ids")
    if not isinstance(raw, list):
        return None
    out: list[int] = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out or None


def resolve_skill_selection(
    *,
    all_active_ids: list[int],
    rec_ids: list[int] | None,
    pinned: set[int],
    excluded: set[int],
    skill_order: list[int],
) -> list[int]:
    """B.5 — the effective ordered skill-id list for one application.

    Pure curation logic shared by the preview (_collect_skills) and the
    generate prompt (app._apply_recommended_skills) so both agree exactly.

    - No recommendation (rec_ids is None): start from all active+approved
      skills in display order.
    - With a recommendation: start from the recommended ids (in their order),
      then append any pinned id not already present (display order).

    Then drop excluded ids, and apply the user's explicit skill_order as a
    stable ranking (listed ids first, in that order; the rest keep their
    relative order). Mirrors the bullet reorder in analyzer._stable_user_prefix.
    """
    universe = set(all_active_ids)
    if rec_ids is None:
        base = list(all_active_ids)
    else:
        base = [sid for sid in rec_ids if sid in universe]
        seen = set(base)
        for sid in all_active_ids:
            if sid in pinned and sid in universe and sid not in seen:
                base.append(sid)
                seen.add(sid)
    base = [sid for sid in base if sid not in excluded]
    if skill_order:
        rank = {sid: i for i, sid in enumerate(skill_order)}
        base = sorted(base, key=lambda s: rank.get(s, len(rank)))
    return base


def _collect_skills(
    session: Session,
    candidate_id: int,
    *,
    pinned: set[int] | None = None,
    excluded: set[int] | None = None,
    skill_order: list[int] | tuple[int, ...] | None = None,
    rec_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Return JSON Resume skills[] for the candidate, curated and ordered for this application (B.5).

    The universe is the candidate's active, approved Skill rows in
    display_order; pending (is_pending_review=1) and retired (is_active=0)
    skills never appear. recommend_skills ordering + pin/drop/reorder overrides
    are applied via resolve_skill_selection. With no recommendation and no
    overrides this is simply every active, approved skill in display order.
    """
    from db.models import Skill

    rows = (
        session.query(Skill)
        .filter_by(candidate_id=candidate_id, is_active=1, is_pending_review=0)
        .order_by(Skill.display_order, Skill.id)
        .all()
    )
    name_by_id = {r.id: r.name for r in rows if (r.name or "").strip()}
    all_active_ids = [r.id for r in rows if r.id in name_by_id]
    ordered = resolve_skill_selection(
        all_active_ids=all_active_ids,
        rec_ids=rec_ids,
        pinned=set(pinned or ()),
        excluded=set(excluded or ()),
        skill_order=list(skill_order or ()),
    )
    return [{"name": name_by_id[sid]} for sid in ordered if sid in name_by_id]


def _username_from_linkedin(url: str) -> str:
    """Pull the LinkedIn handle from a profile URL.

    Best-effort; falls back to the empty string on unexpected formats.
    """
    if not url:
        return ""
    if "/in/" in url:
        tail = url.rsplit("/in/", 1)[-1]
        return tail.split("/")[0].split("?")[0]
    return ""

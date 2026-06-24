"""Corpus seam — tag suggestion + link/unlink on bullets / titles / skills.

7 routes plus their tag-mutation helpers (normalize / find-or-create / resolve
subject / shared link+unlink bodies). DB-only (no filesystem path → the
route-security-lint FS guard does not apply); `_safe_username` gates the owning
candidate. DB imports stay lazy in-function.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus._bp import corpus_bp
from web_infra import _safe_username

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from db.models import Tag


def _normalize_tag_value(s: str) -> str:
    """Canonical tag form: lowercase, trimmed, non-alphanumerics → single
    hyphens (e.g. "AI / ML" → "ai-ml"). Mirrors the normalization the
    plan's Tag schema specifies; display_value keeps the user's casing."""
    s = (s or "").strip().lower()
    out = re.sub(r"[^a-z0-9]+", "-", s)
    return out.strip("-")


@corpus_bp.route("/api/users/<username>/tags", methods=["GET"])
def suggest_tags(username: str) -> ResponseReturnValue:
    """Autocomplete tags by candidate + kind + prefix.

    Query params:
      kind=role|domain|skill|tech  (optional — return all kinds if absent)
      q=<prefix>                   (optional — substring match if absent)
      limit=20                     (max 100)

    Returns: [{id, kind, value, display_value, usage_count}, ...] sorted
    by usage_count desc so most-used tags surface first.
    """
    from db.models import Candidate, Tag
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    kind = request.args.get("kind")
    q = (request.args.get("q") or "").strip().lower()
    limit = min(int(request.args.get("limit", 20)), 100)

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify([])  # not an error; UI just shows empty suggestions
        query = session.query(Tag).filter_by(candidate_id=candidate.id)
        if kind:
            if kind not in {"role", "domain", "skill", "tech"}:
                return jsonify({"error": "kind must be role|domain|skill|tech"}), 400
            query = query.filter_by(kind=kind)
        if q:
            query = query.filter(Tag.value.contains(q))
        rows = (
            query.order_by(
                Tag.usage_count.desc(),
                Tag.value,
            )
            .limit(limit)
            .all()
        )
        return jsonify(
            [
                {
                    "id": t.id,
                    "kind": t.kind,
                    "value": t.value,
                    "display_value": t.display_value,
                    "usage_count": t.usage_count,
                }
                for t in rows
            ]
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Tag link / unlink on bullets + experience titles + skills (DB-only)
# ---------------------------------------------------------------------------


def _find_or_create_tag(session: Session, candidate_id: int, kind: str, value: str) -> Tag:
    """Return the Tag for (candidate, kind, normalized value), creating it
    if absent. Follows the merged_into alias chain so links always point at
    the canonical tag."""
    from db.models import Tag

    norm = _normalize_tag_value(value)
    tag = (
        session.query(Tag)
        .filter_by(
            candidate_id=candidate_id,
            kind=kind,
            value=norm,
        )
        .first()
    )
    if tag is None:
        tag = Tag(
            candidate_id=candidate_id,
            kind=kind,
            value=norm,
            display_value=(value or "").strip() or norm,
            usage_count=0,
        )
        session.add(tag)
        session.flush()
    while tag.merged_into_id is not None:
        nxt = session.query(Tag).filter_by(id=tag.merged_into_id).first()
        if nxt is None:
            break
        tag = nxt
    return tag


def _tag_link_target(session: Session, kind: str, subject_id: int) -> tuple:
    """Resolve a bullet/title subject to (subject, candidate, LinkModel,
    fk_name) or (None, None, None, None)."""
    from db.models import (
        Bullet,
        BulletTag,
        Candidate,
        Experience,
        ExperienceTitle,
        ExperienceTitleTag,
        Skill,
        SkillTag,
    )

    link_model: type
    # Skills are candidate-level — no Experience hop, candidate resolved directly.
    # A distinct local `skill` keeps `subject` (below) purely the experience-scoped
    # Bullet | ExperienceTitle union, so the now-typed `session` body stays mypy-clean.
    if kind == "skill":
        skill = session.query(Skill).filter_by(id=subject_id).first()
        if skill is None:
            return None, None, None, None
        candidate = session.query(Candidate).filter_by(id=skill.candidate_id).first()
        return skill, candidate, SkillTag, "skill_id"
    subject: Bullet | ExperienceTitle | None
    if kind == "bullet":
        subject = session.query(Bullet).filter_by(id=subject_id).first()
        link_model, fk = BulletTag, "bullet_id"
    else:
        subject = session.query(ExperienceTitle).filter_by(id=subject_id).first()
        link_model, fk = ExperienceTitleTag, "experience_title_id"
    if subject is None:
        return None, None, None, None
    exp = session.query(Experience).filter_by(id=subject.experience_id).first()
    if exp is None:
        return None, None, None, None
    candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
    return subject, candidate, link_model, fk


def _link_tag_route(subject_kind: str, subject_id: int) -> ResponseReturnValue:
    """Shared body for POST .../tags. DB-only — no filesystem access, so
    the _within() guard does not apply; _safe_username still gates the
    candidate the row belongs to."""
    from db.session import get_session, init_db

    data = request.json or {}
    value = (data.get("value") or "").strip()
    tag_kind = data.get("kind") or "skill"
    if not value:
        return jsonify({"error": "value is required"}), 400
    if tag_kind not in {"role", "domain", "skill", "tech"}:
        return jsonify({"error": "kind must be role|domain|skill|tech"}), 400

    init_db()
    session = get_session()
    try:
        subject, candidate, link_model, fk = _tag_link_target(
            session,
            subject_kind,
            subject_id,
        )
        if subject is None or candidate is None:
            return jsonify({"error": f"{subject_kind} not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403

        tag = _find_or_create_tag(session, candidate.id, tag_kind, value)
        existing = (
            session.query(link_model)
            .filter_by(
                **{fk: subject_id, "tag_id": tag.id},
            )
            .first()
        )
        if existing is None:
            session.add(link_model(**{fk: subject_id, "tag_id": tag.id}))
            tag.usage_count = (tag.usage_count or 0) + 1
        session.commit()
        return jsonify(
            {
                "id": tag.id,
                "value": tag.value,
                "display_value": tag.display_value,
                "kind": tag.kind,
            }
        ), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _unlink_tag_route(subject_kind: str, subject_id: int, tag_id: int) -> ResponseReturnValue:
    """Shared body for DELETE .../tags/<tag_id>. DB-only — no filesystem."""
    from db.models import Tag
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        subject, candidate, link_model, fk = _tag_link_target(
            session,
            subject_kind,
            subject_id,
        )
        if subject is None or candidate is None:
            return jsonify({"error": f"{subject_kind} not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403

        link = (
            session.query(link_model)
            .filter_by(
                **{fk: subject_id, "tag_id": tag_id},
            )
            .first()
        )
        if link is None:
            return jsonify({"error": "Tag not linked"}), 404
        session.delete(link)
        tag = session.query(Tag).filter_by(id=tag_id).first()
        if tag is not None and (tag.usage_count or 0) > 0:
            tag.usage_count -= 1
        session.commit()
        return jsonify({"unlinked": tag_id})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/bullets/<int:bullet_id>/tags", methods=["POST"])
def link_bullet_tag(bullet_id: int) -> ResponseReturnValue:
    """Attach a tag (find-or-create) to a bullet. Body: {value, kind}."""
    return _link_tag_route("bullet", bullet_id)


@corpus_bp.route("/api/bullets/<int:bullet_id>/tags/<int:tag_id>", methods=["DELETE"])
def unlink_bullet_tag(bullet_id: int, tag_id: int) -> ResponseReturnValue:
    """Detach a tag from a bullet."""
    return _unlink_tag_route("bullet", bullet_id, tag_id)


@corpus_bp.route("/api/experience-titles/<int:title_id>/tags", methods=["POST"])
def link_title_tag(title_id: int) -> ResponseReturnValue:
    """Attach a tag (find-or-create) to an experience title."""
    return _link_tag_route("title", title_id)


@corpus_bp.route("/api/experience-titles/<int:title_id>/tags/<int:tag_id>", methods=["DELETE"])
def unlink_title_tag(title_id: int, tag_id: int) -> ResponseReturnValue:
    """Detach a tag from an experience title."""
    return _unlink_tag_route("title", title_id, tag_id)


@corpus_bp.route("/api/skills/<int:skill_id>/tags", methods=["POST"])
def link_skill_tag(skill_id: int) -> ResponseReturnValue:
    """Attach a tag (find-or-create) to a skill. Body: {value, kind}."""
    return _link_tag_route("skill", skill_id)


@corpus_bp.route("/api/skills/<int:skill_id>/tags/<int:tag_id>", methods=["DELETE"])
def unlink_skill_tag(skill_id: int, tag_id: int) -> ResponseReturnValue:
    """Detach a tag from a skill."""
    return _unlink_tag_route("skill", skill_id, tag_id)

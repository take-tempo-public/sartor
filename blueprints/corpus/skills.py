"""Corpus seam — candidate-level Skill CRUD (B.5).

Skills are candidate-level (no Experience hop) and carry the same lifecycle as
bullets/summaries: active / pending-review / source / display_order / tags. 4
routes. DB-only (no filesystem path → route-security-lint FS guard does not apply);
`_safe_username` gates the owning candidate. The `_skill_to_dict` / `_tag_list`
serializers are shared with the still-resident applications routes, so they live in
`_shared`. DB imports stay lazy in-function.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _skill_to_dict, _tag_list
from web_infra import (
    _error_detail_payload,
    _get_or_provision_candidate,
    _safe_username,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)


@corpus_bp.route("/api/users/<username>/skills", methods=["GET"])
def list_skills(username: str) -> ResponseReturnValue:
    """List the candidate's skills in display order.

    Active + approved by default. ?include_pending=1 adds llm_proposed
    skills awaiting review; ?include_inactive=1 adds soft-retired ones.
    """
    from db.models import Candidate, Skill
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    include_pending = request.args.get("include_pending") in ("1", "true", "yes")
    include_inactive = request.args.get("include_inactive") in ("1", "true", "yes")

    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                return jsonify({"skills": []})
            q = session.query(Skill).filter_by(candidate_id=candidate.id)
            if not include_inactive:
                q = q.filter(Skill.is_active == 1)
            if not include_pending:
                q = q.filter(Skill.is_pending_review == 0)
            rows = q.order_by(Skill.display_order, Skill.id).all()
            return jsonify({"skills": [_skill_to_dict(s, _tag_list(s.tag_links)) for s in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_skills failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load skills",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/users/<username>/skills", methods=["POST"])
def create_skill(username: str) -> ResponseReturnValue:
    """Add a new skill for the candidate.

    Body: {name (required), category?, proficiency?, years?}. User-typed
    skills default to source='manual', is_pending_review=0, is_active=1.
    """
    from db.models import Skill
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    years = data.get("years")
    if years is not None:
        try:
            years = float(years)
        except (TypeError, ValueError):
            return jsonify({"error": "years must be a number or null"}), 400

    init_db()
    session = get_session()
    try:
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(
                session,
                safe_user,
                configs_dir=current_app.config["CONFIGS_DIR"],
            ),
        )
        existing = (
            session.query(Skill)
            .filter_by(
                candidate_id=candidate.id,
                name=name,
            )
            .first()
        )
        if existing is not None:
            return jsonify(
                {
                    "error": "skill already exists",
                    "id": existing.id,
                }
            ), 409

        next_order = session.query(Skill).filter_by(candidate_id=candidate.id).count()
        sk = Skill(
            candidate_id=candidate.id,
            name=name,
            category=(data.get("category") or None),
            proficiency=(data.get("proficiency") or None),
            years=years,
            display_order=next_order,
            is_active=1,
            is_pending_review=0,
            source="manual",
        )
        session.add(sk)
        session.commit()
        session.refresh(sk)
        return jsonify(_skill_to_dict(sk, [])), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/skills/<int:skill_id>", methods=["PUT"])
def update_skill(skill_id: int) -> ResponseReturnValue:
    """Update a Skill.

    Body accepts: name, category, proficiency, years, display_order, is_pending_review
    (set false to approve an llm_proposed skill). Ownership check via _safe_username on
    the owning candidate.
    """
    from db.models import Candidate, Skill
    from db.session import get_session, init_db

    data = request.json or {}

    init_db()
    session = get_session()
    try:
        sk = session.query(Skill).filter_by(id=skill_id).first()
        if sk is None:
            return jsonify({"error": "Skill not found"}), 404
        candidate = session.query(Candidate).filter_by(id=sk.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return jsonify({"error": "name cannot be empty"}), 400
            dup = (
                session.query(Skill)
                .filter(
                    Skill.candidate_id == sk.candidate_id,
                    Skill.name == name,
                    Skill.id != sk.id,
                )
                .first()
            )
            if dup is not None:
                return jsonify({"error": "another skill already has that name", "id": dup.id}), 409
            sk.name = name
        if "category" in data:
            sk.category = data.get("category") or None
        if "proficiency" in data:
            sk.proficiency = data.get("proficiency") or None
        if "years" in data:
            yrs = data.get("years")
            if yrs is None:
                sk.years = None
            else:
                try:
                    sk.years = float(yrs)
                except (TypeError, ValueError):
                    return jsonify({"error": "years must be a number or null"}), 400
        if "display_order" in data:
            try:
                sk.display_order = int(data["display_order"])
            except (TypeError, ValueError):
                return jsonify({"error": "display_order must be int"}), 400
        if "is_pending_review" in data:
            sk.is_pending_review = 1 if data["is_pending_review"] else 0

        session.commit()
        session.refresh(sk)
        return jsonify(_skill_to_dict(sk, _tag_list(sk.tag_links)))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/skills/<int:skill_id>", methods=["DELETE"])
def delete_skill(skill_id: int) -> ResponseReturnValue:
    """Remove a skill.

    A never-approved suggestion (pending + source 'llm_proposed') is hard-deleted so its
    name frees the unique slot for future re-evaluation. An approved skill is soft-retired
    (is_active=0) — composition_overrides from past applications may reference its id.
    """
    from db.models import Candidate, Skill
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        sk = session.query(Skill).filter_by(id=skill_id).first()
        if sk is None:
            return jsonify({"error": "Skill not found"}), 404
        candidate = session.query(Candidate).filter_by(id=sk.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if sk.is_pending_review and sk.source == "llm_proposed":
            session.delete(sk)
            session.commit()
            return jsonify({"id": skill_id, "deleted": True})

        sk.is_active = 0
        sk.is_pending_review = 0
        session.commit()
        return jsonify({"id": sk.id, "is_active": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

"""Corpus seam — candidate-level Skill CRUD (B.5) + corpus-wide skill suggestion.

Skills are candidate-level (no Experience hop) and carry the same lifecycle as
bullets/summaries: active / pending-review / source / display_order / tags. 5
routes (4 CRUD + the corpus-wide suggest, fix/review-surface-and-flows). DB-only
(no filesystem path -> route-security-lint FS guard does not apply); `_safe_username`
gates the owning candidate. The `_skill_to_dict` / `_tag_list` serializers are shared
with the still-resident applications routes, so they live in `_shared`. DB imports
stay lazy in-function; `_get_client` / `anthropic` / `LLMResponseError` are
module-level (mirrors `blueprints/corpus/proposals.py`, the other LLM-calling
corpus submodule) so the suggest route's Anthropic call is patchable at the
usual `blueprints.corpus.skills._get_client` seam.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import anthropic
from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from analyzer import LLMResponseError
from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _skill_to_dict, _tag_list
from web_infra import (
    _error_detail_payload,
    _get_client,
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


@corpus_bp.route("/api/users/<username>/skills/suggest-from-corpus", methods=["POST"])
def suggest_skills_from_corpus_route(username: str) -> ResponseReturnValue:
    """Corpus-wide "Suggest skills from my corpus" (owner feature ask, F-02 gap-close).

    Unlike `/api/applications/<id>/suggest-skills` (JD-scoped, driven from
    Compose), this runs the same grounded suggest-skills machinery over the
    candidate's WHOLE career corpus with no job description in view — so a
    candidate can populate their Skills section before starting their first
    application. `suggest_skills()`'s prompt hard-gates every proposal on
    "the JD wants X AND the corpus evidences X"; with no JD in scope that AND
    can never fire, so this calls the sibling `suggest_skills_from_corpus()`
    analyzer function (evidence-only gate, no JD condition) instead of
    silently starving the corpus-wide call of results.

    Each proposal is inserted as a PENDING Skill (source='llm_proposed',
    is_pending_review=1) for the user to approve/deny via the existing
    Career Corpus skills UI — identical persistence shape to
    `suggest_application_skills`. Dedup is case-insensitive against EVERY
    existing Skill row for this candidate (active, retired, or
    already-pending), mirroring
    `onboarding/corpus_import.py:_insert_pending_skills`'s semantics.

    No filesystem access (career corpus + skills all come from the DB), so
    the route-security-lint FS guard does not apply; `_safe_username` still
    gates the owning candidate.
    """
    import uuid

    from analyzer import suggest_skills_from_corpus
    from db.build_context import (
        _build_career_corpus_payload,
        _prior_clarifications_for_candidate,
    )
    from db.models import Candidate, Experience, Skill
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({"error": "Candidate not found"}), 404

        experiences = (
            session.query(Experience)
            .filter_by(candidate_id=candidate.id)
            .order_by(Experience.display_order)
            .all()
        )
        career_corpus = _build_career_corpus_payload(experiences)
        if not career_corpus:
            return jsonify({"proposals": []})

        all_skill_rows = session.query(Skill).filter_by(candidate_id=candidate.id).all()
        existing_lower = {
            (s.name or "").strip().lower() for s in all_skill_rows if (s.name or "").strip()
        }
        existing_skill_names = [s.name for s in all_skill_rows if (s.name or "").strip()]
        prior_clarifications = _prior_clarifications_for_candidate(session, candidate.id)

        context_set = {
            "career_corpus": career_corpus,
            "existing_skill_names": existing_skill_names,
            "prior_clarifications": prior_clarifications,
        }
        run_id = uuid.uuid4().hex[:12]
        try:
            result = suggest_skills_from_corpus(
                _get_client(),
                context_set,
                username=candidate.username,
                run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Suggest-skills-from-corpus: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error(
                "Suggest-skills-from-corpus: malformed LLM response: %s",
                exc.validation_error,
            )
            return jsonify(
                {
                    "error": "AI skill suggestion was malformed",
                    "detail": str(exc.validation_error),
                }
            ), 502

        next_order = session.query(Skill).filter_by(candidate_id=candidate.id).count()
        created: list[dict[str, Any]] = []
        for p in result.get("proposals") or []:
            if not isinstance(p, dict):
                continue
            name = (p.get("name") or "").strip()
            if not name or name.lower() in existing_lower:
                continue
            existing_lower.add(name.lower())
            category = p.get("category")
            sk = Skill(
                candidate_id=candidate.id,
                name=name,
                category=category if isinstance(category, str) and category.strip() else None,
                display_order=next_order,
                is_active=1,
                is_pending_review=1,
                source="llm_proposed",
            )
            session.add(sk)
            session.flush()
            created.append(
                {
                    **_skill_to_dict(sk, []),
                    "evidence": p.get("evidence"),
                    "rationale": p.get("rationale"),
                }
            )
            next_order += 1
        session.commit()
        return jsonify({"proposals": created})
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

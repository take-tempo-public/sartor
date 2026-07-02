"""Corpus seam — experience-tree CRUD.

The experiences family of the corpus sub-package (Sprint 8.3d): experiences,
their bullets, their alternate titles, and their per-role summary variants
(ExperienceSummaryItem) — 15 routes. Ownership flows
experience → candidate → `_safe_username`; no filesystem access (so the
route-security-lint FS guard does not apply). DB imports stay lazy in-function.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import (
    _experience_detail_dict,
    _experience_summary_dict,
    _experience_summary_item_to_dict,
    _load_experience_for_candidate,
)
from web_infra import (
    _error_detail_payload,
    _get_or_provision_candidate,
    _safe_username,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Experiences + bullets
# ---------------------------------------------------------------------------


@corpus_bp.route("/api/users/<username>/experiences", methods=["GET"])
def list_experiences(username: str) -> ResponseReturnValue:
    """Return the candidate's experiences in newest-first display order.

    Used by the Career Corpus tab's timeline.
    """
    from db.models import Candidate, Experience
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    # Wrapped with logger.exception (2026-05-26) — see list_bundled_personas
    # for rationale. The frontend surfaces "Failed to load corpus." on 500
    # which gives the user no clue about the root cause.
    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                # Read precondition unmet → 200 + flag, not 409 (see
                # list_user_personas). Success shape is a bare array; the
                # needs-onboarding case is the discriminated object.
                return jsonify({"experiences": [], "needs_onboarding": True})
            rows = (
                session.query(Experience)
                .filter_by(
                    candidate_id=candidate.id,
                )
                .order_by(Experience.start_date.desc(), Experience.id.desc())
                .all()
            )
            return jsonify([_experience_summary_dict(e) for e in rows])
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_experiences failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load corpus",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/users/<username>/experiences", methods=["POST"])
def create_experience(username: str) -> ResponseReturnValue:
    """Create a new experience under this candidate.

    Body: {company, start_date (YYYY-MM or YYYY), end_date?, location?, summary?}.
    Returns the full detail payload so the UI can expand it immediately.
    """
    from db.models import Experience
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    data = request.json or {}
    company = (data.get("company") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    if not company:
        return jsonify({"error": "company is required"}), 400
    if not re.fullmatch(r"\d{4}(-\d{2})?", start_date):
        return jsonify({"error": "start_date must be YYYY-MM or YYYY"}), 400
    end_date = (data.get("end_date") or "").strip() or None
    if end_date and not re.fullmatch(r"\d{4}(-\d{2})?", end_date):
        return jsonify({"error": "end_date must be YYYY-MM, YYYY, or empty"}), 400

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
            session.query(Experience)
            .filter_by(
                candidate_id=candidate.id,
            )
            .count()
        )
        exp = Experience(
            candidate_id=candidate.id,
            company=company,
            location=(data.get("location") or "").strip() or None,
            start_date=start_date,
            end_date=end_date,
            display_order=existing,
            summary=(data.get("summary") or "").strip() or None,
        )
        session.add(exp)
        session.commit()
        session.refresh(exp)
        return jsonify(_experience_detail_dict(exp)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>", methods=["GET"])
def get_experience(experience_id: int) -> ResponseReturnValue:
    """Return one experience with its live titles + bullets.

    Retired rows are hidden unless ?include_retired=1 (the "show retired" toggle).
    """
    from db.session import get_session, init_db

    include_retired = request.args.get("include_retired") in ("1", "true", "yes")
    init_db()
    session = get_session()
    try:
        exp, candidate = _load_experience_for_candidate(session, experience_id)
        if exp is None or candidate is None:
            return jsonify({"error": "Experience not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403
        return jsonify(_experience_detail_dict(exp, include_retired=include_retired))
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>", methods=["PUT"])
def update_experience(experience_id: int) -> ResponseReturnValue:
    """Update company / location / dates / summary on an experience.

    Body fields are all optional — only those present in the payload are
    written. Returns the updated detail dict.
    """
    from db.session import get_session, init_db

    data = request.json or {}
    init_db()
    session = get_session()
    try:
        exp, candidate = _load_experience_for_candidate(session, experience_id)
        if exp is None or candidate is None:
            return jsonify({"error": "Experience not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "company" in data:
            new_co = (data.get("company") or "").strip()
            if not new_co:
                return jsonify({"error": "company cannot be empty"}), 400
            exp.company = new_co
        if "location" in data:
            exp.location = (data.get("location") or "").strip() or None
        if "start_date" in data:
            sd = (data.get("start_date") or "").strip()
            if not re.fullmatch(r"\d{4}(-\d{2})?", sd):
                return jsonify({"error": "start_date must be YYYY-MM or YYYY"}), 400
            exp.start_date = sd
        if "end_date" in data:
            ed = (data.get("end_date") or "").strip() or None
            if ed and not re.fullmatch(r"\d{4}(-\d{2})?", ed):
                return jsonify({"error": "end_date must be YYYY-MM, YYYY, or empty"}), 400
            exp.end_date = ed
        if "summary" in data:
            exp.summary = (data.get("summary") or "").strip() or None
        if "display_order" in data and isinstance(data["display_order"], int):
            exp.display_order = data["display_order"]

        session.commit()
        session.refresh(exp)
        return jsonify(_experience_detail_dict(exp))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>", methods=["DELETE"])
def delete_experience(experience_id: int) -> ResponseReturnValue:
    """Soft-retire an experience: set is_active=0 on all its bullets.

    Hard-delete is refused because application_bullet rows have NO cascade
    on bullet_id (preserves audit chain). The experience row itself stays,
    but with no active bullets it vanishes from the corpus selection pool.
    """
    from db.models import Bullet
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        exp, candidate = _load_experience_for_candidate(session, experience_id)
        if exp is None or candidate is None:
            return jsonify({"error": "Experience not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403

        retired = session.query(Bullet).filter_by(experience_id=exp.id).update({"is_active": 0})
        session.commit()
        return jsonify({"retired_bullets": retired, "experience_id": exp.id})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:target_id>/merge", methods=["POST"])
def merge_experience(target_id: int) -> ResponseReturnValue:
    """Fold a source experience into a target, treating them as one role.

    Body: {source_id (int)}. The target is the role already in the corpus — it
    KEEPS its company + dates. The source's distinct titles become alternates on
    the target (never a second official); the source's distinct bullets move over
    (deduped on normalized text); then the emptied source experience is deleted.

    Refused with 409 if the source is referenced by any application / audit row
    (application_run_title / application_bullet / proposal_review) — a merge would
    orphan or cascade-wipe run history. Corpus-building (the merge use case) has
    none of these. DB-only.
    """
    from db.models import (
        ApplicationBullet,
        ApplicationRunTitle,
        Experience,
        ProposalReview,
    )
    from db.session import get_session, init_db

    data = request.json or {}
    source_id = data.get("source_id")
    if not isinstance(source_id, int):
        return jsonify({"error": "source_id (int) is required"}), 400
    if source_id == target_id:
        return jsonify({"error": "Cannot merge an experience into itself"}), 400

    init_db()
    session = get_session()
    try:
        target, target_cand = _load_experience_for_candidate(session, target_id)
        if target is None or target_cand is None:
            return jsonify({"error": "Target experience not found"}), 404
        if not _safe_username(target_cand.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403
        source = session.query(Experience).filter_by(id=source_id).first()
        if source is None:
            return jsonify({"error": "Source experience not found"}), 404
        if source.candidate_id != target.candidate_id:
            return jsonify({"error": "Experiences belong to different candidates"}), 403

        source_title_ids = [t.id for t in source.titles]
        source_bullet_ids = [b.id for b in source.bullets]
        refs = (
            session.query(ApplicationRunTitle)
            .filter(ApplicationRunTitle.experience_id == source.id)
            .count()
        )
        if source_title_ids:
            refs += (
                session.query(ApplicationRunTitle)
                .filter(ApplicationRunTitle.experience_title_id.in_(source_title_ids))
                .count()
            )
            refs += (
                session.query(ProposalReview)
                .filter(ProposalReview.experience_title_id.in_(source_title_ids))
                .count()
            )
        if source_bullet_ids:
            refs += (
                session.query(ApplicationBullet)
                .filter(ApplicationBullet.bullet_id.in_(source_bullet_ids))
                .count()
            )
            refs += (
                session.query(ProposalReview)
                .filter(ProposalReview.bullet_id.in_(source_bullet_ids))
                .count()
            )
        if refs:
            return (
                jsonify(
                    {
                        "error": (
                            "This role is used in an application's history; merge is "
                            "only available before it's been used in a tailored resume."
                        )
                    }
                ),
                409,
            )

        def _norm(s: str) -> str:
            return " ".join(s.lower().split())

        # Move the source's DISTINCT titles onto the target as alternates; drop
        # duplicate framings. Removing from source.titles orphans the row; an
        # append to target re-parents it (so only true duplicates are deleted).
        existing_title_text = {t.title for t in target.titles}
        for st in list(source.titles):
            source.titles.remove(st)
            if st.title not in existing_title_text:
                st.is_official = 0  # the target keeps its own official title
                target.titles.append(st)
                existing_title_text.add(st.title)

        # Move the source's DISTINCT bullets onto the target (deduped on text).
        existing_bullet_norm = {_norm(b.text) for b in target.bullets}
        next_order = max((b.display_order for b in target.bullets), default=-1) + 1
        for sb in list(source.bullets):
            source.bullets.remove(sb)
            if _norm(sb.text) not in existing_bullet_norm:
                sb.display_order = next_order
                next_order += 1
                target.bullets.append(sb)
                existing_bullet_norm.add(_norm(sb.text))

        # Preserve the at-least-one-official intent if the target lost its way.
        if not any(t.is_official for t in target.titles):
            promotable = sorted((t for t in target.titles if t.is_active), key=lambda t: t.id)
            if promotable:
                promotable[0].is_official = 1

        # Source's collections are now empty; delete just the source row.
        session.delete(source)
        session.commit()
        session.refresh(target)
        return jsonify(_experience_detail_dict(target))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>/bullets", methods=["POST"])
def create_bullet(experience_id: int) -> ResponseReturnValue:
    """Add a new bullet under an experience.

    Body: {text (required), pattern_kind?, has_outcome?, source?}. New
    user-typed bullets default to source='manual', is_pending_review=0
    (user wrote it themselves; no LLM proposal flow needed).
    """
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session, init_db
    from hardening import METRIC_RE

    data = request.json or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    init_db()
    session = get_session()
    try:
        exp = session.query(Experience).filter_by(id=experience_id).first()
        if exp is None:
            return jsonify({"error": "Experience not found"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        pattern_kind = data.get("pattern_kind")
        if pattern_kind is not None and pattern_kind not in {"xyz", "star", "car", "manual"}:
            return jsonify({"error": "pattern_kind must be xyz|star|car|manual"}), 400

        # Auto-compute has_outcome from text via METRIC_RE unless user overrode
        has_outcome = data.get("has_outcome")
        if has_outcome is None:
            has_outcome = 1 if METRIC_RE.search(text) else 0
        else:
            has_outcome = 1 if has_outcome else 0

        next_order = session.query(Bullet).filter_by(experience_id=exp.id).count()
        bullet = Bullet(
            experience_id=exp.id,
            text=text,
            display_order=next_order,
            is_active=1,
            is_pending_review=0,
            source=data.get("source", "manual"),
            pattern_kind=pattern_kind,
            has_outcome=has_outcome,
        )
        session.add(bullet)
        session.commit()
        session.refresh(bullet)
        return jsonify(
            {
                "id": bullet.id,
                "text": bullet.text,
                "display_order": bullet.display_order,
                "is_active": bool(bullet.is_active),
                "is_pending_review": bool(bullet.is_pending_review),
                "has_outcome": bool(bullet.has_outcome),
                "pattern_kind": bullet.pattern_kind,
                "source": bullet.source,
            }
        ), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/bullets/<int:bullet_id>", methods=["PUT"])
def update_bullet(bullet_id: int) -> ResponseReturnValue:
    """Update bullet text / pattern_kind / has_outcome / display_order."""
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session, init_db
    from hardening import METRIC_RE

    data = request.json or {}
    init_db()
    session = get_session()
    try:
        bullet = session.query(Bullet).filter_by(id=bullet_id).first()
        if bullet is None:
            return jsonify({"error": "Bullet not found"}), 404
        exp = session.query(Experience).filter_by(id=bullet.experience_id).first()
        if exp is None:
            return jsonify({"error": "Bullet's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "text" in data:
            new_text = (data.get("text") or "").strip()
            if not new_text:
                return jsonify({"error": "text cannot be empty"}), 400
            bullet.text = new_text
            # Re-compute has_outcome unless user explicitly set it in the same call
            if "has_outcome" not in data:
                bullet.has_outcome = 1 if METRIC_RE.search(new_text) else 0
        if "pattern_kind" in data:
            pk = data.get("pattern_kind")
            if pk is not None and pk not in {"xyz", "star", "car", "manual"}:
                return jsonify({"error": "pattern_kind must be xyz|star|car|manual"}), 400
            bullet.pattern_kind = pk
        if "has_outcome" in data:
            bullet.has_outcome = 1 if data["has_outcome"] else 0
        if "display_order" in data and isinstance(data["display_order"], int):
            bullet.display_order = data["display_order"]
        if "is_active" in data:
            bullet.is_active = 1 if data["is_active"] else 0  # restore a retired bullet

        session.commit()
        session.refresh(bullet)
        return jsonify(
            {
                "id": bullet.id,
                "text": bullet.text,
                "display_order": bullet.display_order,
                "is_active": bool(bullet.is_active),
                "has_outcome": bool(bullet.has_outcome),
                "pattern_kind": bullet.pattern_kind,
                "source": bullet.source,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/bullets/<int:bullet_id>", methods=["DELETE"])
def delete_bullet(bullet_id: int) -> ResponseReturnValue:
    """Soft-retire a bullet (is_active=0).

    Hard-delete refused because application_bullet rows have NO cascade on bullet_id.
    """
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        bullet = session.query(Bullet).filter_by(id=bullet_id).first()
        if bullet is None:
            return jsonify({"error": "Bullet not found"}), 404
        exp = session.query(Experience).filter_by(id=bullet.experience_id).first()
        if exp is None:
            return jsonify({"error": "Bullet's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        bullet.is_active = 0
        bullet.is_pending_review = 0
        session.commit()
        return jsonify({"id": bullet.id, "is_active": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# B.4 (Sprint 6.6) — ExperienceSummaryItem CRUD (per-role intro variants).
# Experience-scoped, mirroring the bullet routes: ownership flows
# experience → candidate → _safe_username. No filesystem access, so the
# route-security-lint hook (filesystem-route guard) does not apply.
# ---------------------------------------------------------------------------


@corpus_bp.route("/api/experiences/<int:experience_id>/summaries", methods=["GET"])
def list_experience_summaries(experience_id: int) -> ResponseReturnValue:
    """List a role's ExperienceSummaryItem intro variants in display order.

    Returns active rows by default; pass ?include_inactive=1 to include
    soft-retired ones (the Corpus editor uses this to surface retired
    variants). Ownership: experience → candidate → _safe_username.
    """
    from db.models import Candidate, Experience, ExperienceSummaryItem
    from db.session import get_session, init_db

    include_inactive = request.args.get("include_inactive") in ("1", "true", "yes")

    try:
        init_db()
        session = get_session()
        try:
            exp = session.query(Experience).filter_by(id=experience_id).first()
            if exp is None:
                return jsonify({"error": "Experience not found"}), 404
            candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
            if candidate is None or not _safe_username(
                candidate.username,
                configs_dir=current_app.config["CONFIGS_DIR"],
            ):
                return jsonify({"error": "Candidate validation failed"}), 403
            q = session.query(ExperienceSummaryItem).filter_by(experience_id=exp.id)
            if not include_inactive:
                q = q.filter(ExperienceSummaryItem.is_active == 1)
            rows = q.order_by(
                ExperienceSummaryItem.display_order,
                ExperienceSummaryItem.id,
            ).all()
            return jsonify({"summaries": [_experience_summary_item_to_dict(s) for s in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_experience_summaries failed for exp=%s", experience_id)
        return jsonify(
            {
                "error": "Failed to load role summaries",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/experiences/<int:experience_id>/summaries", methods=["POST"])
def create_experience_summary(experience_id: int) -> ResponseReturnValue:
    """Add a new ExperienceSummaryItem variant under a role.

    Body: {text (required), label?, has_outcome?, source?}. New user-typed
    variants default to source='manual', is_pending_review=0.
    """
    from db.models import Candidate, Experience, ExperienceSummaryItem
    from db.session import get_session, init_db

    data = request.json or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    source = data.get("source", "manual")
    if source not in ("manual", "imported", "llm_proposed"):
        return jsonify({"error": "source must be manual|imported|llm_proposed"}), 400

    init_db()
    session = get_session()
    try:
        exp = session.query(Experience).filter_by(id=experience_id).first()
        if exp is None:
            return jsonify({"error": "Experience not found"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        next_order = (
            session.query(ExperienceSummaryItem)
            .filter_by(
                experience_id=exp.id,
            )
            .count()
        )
        si = ExperienceSummaryItem(
            experience_id=exp.id,
            text=text,
            label=(data.get("label") or None),
            display_order=next_order,
            is_active=1,
            is_pending_review=0,
            source=source,
            has_outcome=1 if data.get("has_outcome") else 0,
        )
        session.add(si)
        session.commit()
        session.refresh(si)
        return jsonify(_experience_summary_item_to_dict(si)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experience-summaries/<int:item_id>", methods=["PUT"])
def update_experience_summary(item_id: int) -> ResponseReturnValue:
    """Update an ExperienceSummaryItem.

    Body accepts: text, label, has_outcome, is_pending_review, display_order.
    Ownership: item -> experience -> candidate -> _safe_username.
    """
    from db.models import Candidate, Experience, ExperienceSummaryItem
    from db.session import get_session, init_db

    data = request.json or {}

    init_db()
    session = get_session()
    try:
        si = session.query(ExperienceSummaryItem).filter_by(id=item_id).first()
        if si is None:
            return jsonify({"error": "ExperienceSummaryItem not found"}), 404
        exp = session.query(Experience).filter_by(id=si.experience_id).first()
        if exp is None:
            return jsonify({"error": "Variant's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "text" in data:
            text = (data.get("text") or "").strip()
            if not text:
                return jsonify({"error": "text cannot be empty"}), 400
            si.text = text
        if "label" in data:
            label = data.get("label")
            si.label = (label or None) if label is None or isinstance(label, str) else None
        if "has_outcome" in data:
            si.has_outcome = 1 if data["has_outcome"] else 0
        if "is_pending_review" in data:
            si.is_pending_review = 1 if data["is_pending_review"] else 0
        if "display_order" in data:
            try:
                si.display_order = int(data["display_order"])
            except (TypeError, ValueError):
                return jsonify({"error": "display_order must be int"}), 400

        session.commit()
        session.refresh(si)
        return jsonify(_experience_summary_item_to_dict(si))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experience-summaries/<int:item_id>", methods=["DELETE"])
def delete_experience_summary(item_id: int) -> ResponseReturnValue:
    """Soft-retire an ExperienceSummaryItem (is_active=0).

    Mirrors bullet delete semantics — composition_overrides may reference this id from past
    applications so a hard-delete would orphan them.
    """
    from db.models import Candidate, Experience, ExperienceSummaryItem
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        si = session.query(ExperienceSummaryItem).filter_by(id=item_id).first()
        if si is None:
            return jsonify({"error": "ExperienceSummaryItem not found"}), 404
        exp = session.query(Experience).filter_by(id=si.experience_id).first()
        if exp is None:
            return jsonify({"error": "Variant's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        si.is_active = 0
        si.is_pending_review = 0
        session.commit()
        return jsonify({"id": si.id, "is_active": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Experience titles (alternate titles per role)
# ---------------------------------------------------------------------------


@corpus_bp.route("/api/experiences/<int:experience_id>/titles", methods=["POST"])
def create_experience_title(experience_id: int) -> ResponseReturnValue:
    """Add an alternate title to an experience.

    Body: {title (required), is_official?, truthful_enough_to_use?, notes?}.
    Setting is_official=true clears the flag on any sibling title that's
    currently official, since the schema's partial unique index enforces
    at-most-one-official per experience.
    """
    from db.models import Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    data = request.json or {}
    title_text = (data.get("title") or "").strip()
    if not title_text:
        return jsonify({"error": "title is required"}), 400

    init_db()
    session = get_session()
    try:
        exp = session.query(Experience).filter_by(id=experience_id).first()
        if exp is None:
            return jsonify({"error": "Experience not found"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        is_official = 1 if data.get("is_official") else 0
        if is_official:
            session.query(ExperienceTitle).filter_by(
                experience_id=exp.id,
                is_official=1,
            ).update({"is_official": 0})

        title = ExperienceTitle(
            experience_id=exp.id,
            title=title_text,
            is_official=is_official,
            truthful_enough_to_use=1 if data.get("truthful_enough_to_use") else 0,
            is_pending_review=0,
            source="user_added",
            notes=(data.get("notes") or "").strip() or None,
        )
        session.add(title)
        session.commit()
        session.refresh(title)
        return jsonify(
            {
                "id": title.id,
                "title": title.title,
                "is_official": bool(title.is_official),
                "truthful_enough_to_use": bool(title.truthful_enough_to_use),
                "is_pending_review": bool(title.is_pending_review),
                "source": title.source,
                "notes": title.notes,
            }
        ), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experience-titles/<int:title_id>", methods=["PUT"])
def update_experience_title(title_id: int) -> ResponseReturnValue:
    """Update a title's text / is_official / truthful_enough_to_use / notes.

    Setting is_official=true atomically clears it on the sibling that's
    currently official (preserves the schema's at-most-one-official invariant).
    """
    from db.models import Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    data = request.json or {}
    init_db()
    session = get_session()
    try:
        title = session.query(ExperienceTitle).filter_by(id=title_id).first()
        if title is None:
            return jsonify({"error": "Title not found"}), 404
        exp = session.query(Experience).filter_by(id=title.experience_id).first()
        if exp is None:
            return jsonify({"error": "Title's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "title" in data:
            new_text = (data.get("title") or "").strip()
            if not new_text:
                return jsonify({"error": "title cannot be empty"}), 400
            title.title = new_text
        if "is_official" in data:
            new_official = 1 if data["is_official"] else 0
            if new_official == 1:
                session.query(ExperienceTitle).filter(
                    ExperienceTitle.experience_id == exp.id,
                    ExperienceTitle.id != title.id,
                    ExperienceTitle.is_official == 1,
                ).update({"is_official": 0})
            title.is_official = new_official
        if "truthful_enough_to_use" in data:
            title.truthful_enough_to_use = 1 if data["truthful_enough_to_use"] else 0
        if "is_active" in data:
            # Restore (true) re-eligibles the title unless the caller also pins
            # truthful_enough_to_use explicitly; retire (false) just hides it.
            new_active = 1 if data["is_active"] else 0
            title.is_active = new_active
            if new_active and "truthful_enough_to_use" not in data:
                title.truthful_enough_to_use = 1
        if "notes" in data:
            title.notes = (data.get("notes") or "").strip() or None

        session.commit()
        session.refresh(title)
        return jsonify(
            {
                "id": title.id,
                "title": title.title,
                "is_active": bool(title.is_active),
                "is_official": bool(title.is_official),
                "truthful_enough_to_use": bool(title.truthful_enough_to_use),
                "is_pending_review": bool(title.is_pending_review),
                "source": title.source,
                "notes": title.notes,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experience-titles/<int:title_id>", methods=["DELETE"])
def delete_experience_title(title_id: int) -> ResponseReturnValue:
    """Soft-retire a title (is_active=0) and clear its eligibility flags.

    Retired titles are hidden from the corpus unless ?include_retired=1 and never
    reach generation; restore via PUT {is_active: true}. We retire rather than
    hard-delete because application_run_title / proposal_review FKs reference the
    row for audit (CASCADE / SET NULL) — a hard delete would lose run history.
    """
    from db.models import Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        title = session.query(ExperienceTitle).filter_by(id=title_id).first()
        if title is None:
            return jsonify({"error": "Title not found"}), 404
        exp = session.query(Experience).filter_by(id=title.experience_id).first()
        if exp is None:
            return jsonify({"error": "Title's experience missing"}), 404
        candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        title.is_active = 0
        title.is_official = 0
        title.truthful_enough_to_use = 0
        title.is_pending_review = 0
        session.commit()
        return jsonify(
            {
                "id": title.id,
                "is_active": False,
                "is_official": False,
                "truthful_enough_to_use": False,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

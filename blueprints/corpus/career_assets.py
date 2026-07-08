"""Corpus seam — candidate-level Education + Certification CRUD (F-04, UX-W1).

Education and Certification are candidate-level Corpus Items — no Experience
hop, mirroring Skill's shape (active / display_order / candidate-scoped CRUD)
but WITHOUT the pending-review/source lifecycle: `db/models.py` gives neither
table an `is_pending_review` or `source` column (no LLM-proposal path for
either — a human types these directly). Soft-retire only (`is_active=0`,
never hard-deleted) — both models already carry `is_active` for exactly this,
matching the Skill/SummaryItem "nothing hard-deleted" promise. 8 routes (4 per
entity). DB-only (no filesystem path -> route-security-lint FS guard does not
apply); `_safe_username` gates the owning candidate, matching
skills.py/summaries.py. DB imports stay lazy in-function.

This editor is the missing UI half of an already-consumed backend contract,
not new plumbing: `db/build_context.py` already reads both tables (ordered by
`display_order`) into the synthesized corpus-mode résumé markdown the
analyze/generate prompts see (F-04's "the DB models already exist and corpus
mode already consumes them"). `corpus_to_json_resume.py`'s JSON-Resume preview
still hardcodes `education: []` / `certificates: []` ("not modeled in the DB
yet (v1.1+)") — that preview-rendering gap is pre-existing and out of scope
here; this branch only closes the CRUD-UI gap the friction register flagged.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _certification_to_dict, _education_to_dict
from web_infra import (
    _error_detail_payload,
    _get_or_provision_candidate,
    _safe_username,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


@corpus_bp.route("/api/users/<username>/education", methods=["GET"])
def list_education(username: str) -> ResponseReturnValue:
    """List the candidate's education entries in display order.

    Active by default; ?include_inactive=1 adds soft-retired ones.
    """
    from db.models import Candidate, Education
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    include_inactive = request.args.get("include_inactive") in ("1", "true", "yes")

    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                return jsonify({"education": []})
            q = session.query(Education).filter_by(candidate_id=candidate.id)
            if not include_inactive:
                q = q.filter(Education.is_active == 1)
            rows = q.order_by(Education.display_order, Education.id).all()
            return jsonify({"education": [_education_to_dict(e) for e in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_education failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load education",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/users/<username>/education", methods=["POST"])
def create_education(username: str) -> ResponseReturnValue:
    """Add a new education entry for the candidate.

    Body: {institution (required), degree?, field?, start_date?, end_date?, notes?}.
    """
    from db.models import Education
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    data = request.json or {}
    institution = (data.get("institution") or "").strip()
    if not institution:
        return jsonify({"error": "institution is required"}), 400

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
        next_order = session.query(Education).filter_by(candidate_id=candidate.id).count()
        ed = Education(
            candidate_id=candidate.id,
            institution=institution,
            degree=(data.get("degree") or None),
            field=(data.get("field") or None),
            start_date=(data.get("start_date") or None),
            end_date=(data.get("end_date") or None),
            notes=(data.get("notes") or None),
            display_order=next_order,
            is_active=1,
        )
        session.add(ed)
        session.commit()
        session.refresh(ed)
        return jsonify(_education_to_dict(ed)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/education/<int:education_id>", methods=["PUT"])
def update_education(education_id: int) -> ResponseReturnValue:
    """Update an Education entry.

    Body accepts: institution, degree, field, start_date, end_date, notes,
    display_order, is_active. Ownership check via _safe_username on the
    owning candidate.
    """
    from db.models import Candidate, Education
    from db.session import get_session, init_db

    data = request.json or {}

    init_db()
    session = get_session()
    try:
        ed = session.query(Education).filter_by(id=education_id).first()
        if ed is None:
            return jsonify({"error": "Education entry not found"}), 404
        candidate = session.query(Candidate).filter_by(id=ed.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "institution" in data:
            institution = (data.get("institution") or "").strip()
            if not institution:
                return jsonify({"error": "institution cannot be empty"}), 400
            ed.institution = institution
        if "degree" in data:
            ed.degree = data.get("degree") or None
        if "field" in data:
            ed.field = data.get("field") or None
        if "start_date" in data:
            ed.start_date = data.get("start_date") or None
        if "end_date" in data:
            ed.end_date = data.get("end_date") or None
        if "notes" in data:
            ed.notes = data.get("notes") or None
        if "is_active" in data:
            ed.is_active = 1 if data["is_active"] else 0
        if "display_order" in data:
            try:
                ed.display_order = int(data["display_order"])
            except (TypeError, ValueError):
                return jsonify({"error": "display_order must be int"}), 400

        session.commit()
        session.refresh(ed)
        return jsonify(_education_to_dict(ed))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/education/<int:education_id>", methods=["DELETE"])
def delete_education(education_id: int) -> ResponseReturnValue:
    """Soft-retire an Education entry (is_active=0). Never hard-deleted."""
    from db.models import Candidate, Education
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        ed = session.query(Education).filter_by(id=education_id).first()
        if ed is None:
            return jsonify({"error": "Education entry not found"}), 404
        candidate = session.query(Candidate).filter_by(id=ed.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        ed.is_active = 0
        session.commit()
        return jsonify({"id": ed.id, "is_active": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Certification
# ---------------------------------------------------------------------------


@corpus_bp.route("/api/users/<username>/certifications", methods=["GET"])
def list_certifications(username: str) -> ResponseReturnValue:
    """List the candidate's certifications in display order.

    Active by default; ?include_inactive=1 adds soft-retired ones.
    """
    from db.models import Candidate, Certification
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    include_inactive = request.args.get("include_inactive") in ("1", "true", "yes")

    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                return jsonify({"certifications": []})
            q = session.query(Certification).filter_by(candidate_id=candidate.id)
            if not include_inactive:
                q = q.filter(Certification.is_active == 1)
            rows = q.order_by(Certification.display_order, Certification.id).all()
            return jsonify({"certifications": [_certification_to_dict(c) for c in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_certifications failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load certifications",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/users/<username>/certifications", methods=["POST"])
def create_certification(username: str) -> ResponseReturnValue:
    """Add a new certification for the candidate.

    Body: {name (required), issuer?, issued?, expires?}.
    """
    from db.models import Certification
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

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
        next_order = session.query(Certification).filter_by(candidate_id=candidate.id).count()
        c = Certification(
            candidate_id=candidate.id,
            name=name,
            issuer=(data.get("issuer") or None),
            issued=(data.get("issued") or None),
            expires=(data.get("expires") or None),
            display_order=next_order,
            is_active=1,
        )
        session.add(c)
        session.commit()
        session.refresh(c)
        return jsonify(_certification_to_dict(c)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/certifications/<int:certification_id>", methods=["PUT"])
def update_certification(certification_id: int) -> ResponseReturnValue:
    """Update a Certification.

    Body accepts: name, issuer, issued, expires, display_order, is_active.
    Ownership check via _safe_username on the owning candidate.
    """
    from db.models import Candidate, Certification
    from db.session import get_session, init_db

    data = request.json or {}

    init_db()
    session = get_session()
    try:
        c = session.query(Certification).filter_by(id=certification_id).first()
        if c is None:
            return jsonify({"error": "Certification not found"}), 404
        candidate = session.query(Candidate).filter_by(id=c.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return jsonify({"error": "name cannot be empty"}), 400
            c.name = name
        if "issuer" in data:
            c.issuer = data.get("issuer") or None
        if "issued" in data:
            c.issued = data.get("issued") or None
        if "expires" in data:
            c.expires = data.get("expires") or None
        if "is_active" in data:
            c.is_active = 1 if data["is_active"] else 0
        if "display_order" in data:
            try:
                c.display_order = int(data["display_order"])
            except (TypeError, ValueError):
                return jsonify({"error": "display_order must be int"}), 400

        session.commit()
        session.refresh(c)
        return jsonify(_certification_to_dict(c))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/certifications/<int:certification_id>", methods=["DELETE"])
def delete_certification(certification_id: int) -> ResponseReturnValue:
    """Soft-retire a Certification (is_active=0). Never hard-deleted."""
    from db.models import Candidate, Certification
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        c = session.query(Certification).filter_by(id=certification_id).first()
        if c is None:
            return jsonify({"error": "Certification not found"}), 404
        candidate = session.query(Candidate).filter_by(id=c.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        c.is_active = 0
        session.commit()
        return jsonify({"id": c.id, "is_active": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

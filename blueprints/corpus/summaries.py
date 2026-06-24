"""Corpus seam — candidate-level SummaryItem CRUD (β.6a).

The positioning-summary variants for a candidate — parented by Candidate (not
Experience), mirroring the bullet lifecycle: active / pending-review / source /
display_order. 4 routes. DB-only (no filesystem path → route-security-lint FS
guard does not apply); `_safe_username` gates the owning candidate. DB imports
stay lazy in-function.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _summary_item_to_dict
from web_infra import (
    _error_detail_payload,
    _get_or_provision_candidate,
    _safe_username,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)


@corpus_bp.route("/api/users/<username>/summaries", methods=["GET"])
def list_summary_items(username: str) -> ResponseReturnValue:
    """List the candidate's SummaryItem variants in display order.

    Returns active rows by default; pass ?include_inactive=1 to include
    soft-retired ones (the Corpus editor uses this to surface retired
    variants).
    """
    from db.models import Candidate, SummaryItem
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    include_inactive = request.args.get("include_inactive") in ("1", "true", "yes")

    # Wrapped with logger.exception (2026-05-26) — see list_bundled_personas.
    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                return jsonify({"summaries": []})
            q = session.query(SummaryItem).filter_by(candidate_id=candidate.id)
            if not include_inactive:
                q = q.filter(SummaryItem.is_active == 1)
            rows = q.order_by(SummaryItem.display_order, SummaryItem.id).all()
            return jsonify({"summaries": [_summary_item_to_dict(s) for s in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_summary_items failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load summaries",
                **_error_detail_payload(exc),
            }
        ), 500


@corpus_bp.route("/api/users/<username>/summaries", methods=["POST"])
def create_summary_item(username: str) -> ResponseReturnValue:
    """Add a new SummaryItem variant for the candidate.

    Body: {text (required), label?, has_outcome?, source?}. New
    user-typed variants default to source='manual',
    is_pending_review=0 (the user wrote it themselves).
    """
    from db.models import SummaryItem
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

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
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(
                session,
                safe_user,
                configs_dir=current_app.config["CONFIGS_DIR"],
            ),
        )

        next_order = session.query(SummaryItem).filter_by(candidate_id=candidate.id).count()
        si = SummaryItem(
            candidate_id=candidate.id,
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
        return jsonify(_summary_item_to_dict(si)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/summaries/<int:summary_id>", methods=["PUT"])
def update_summary_item(summary_id: int) -> ResponseReturnValue:
    """Update a SummaryItem. Body accepts: text, label, has_outcome,
    is_pending_review, display_order. Ownership check via _safe_username."""
    from db.models import Candidate, SummaryItem
    from db.session import get_session, init_db

    data = request.json or {}

    init_db()
    session = get_session()
    try:
        si = session.query(SummaryItem).filter_by(id=summary_id).first()
        if si is None:
            return jsonify({"error": "SummaryItem not found"}), 404
        candidate = session.query(Candidate).filter_by(id=si.candidate_id).first()
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
        return jsonify(_summary_item_to_dict(si))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/summaries/<int:summary_id>", methods=["DELETE"])
def delete_summary_item(summary_id: int) -> ResponseReturnValue:
    """Soft-retire a SummaryItem (is_active=0). Mirrors bullet delete
    semantics — composition_overrides may reference this id from past
    applications so a hard-delete would orphan them."""
    from db.models import Candidate, SummaryItem
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        si = session.query(SummaryItem).filter_by(id=summary_id).first()
        if si is None:
            return jsonify({"error": "SummaryItem not found"}), 404
        candidate = session.query(Candidate).filter_by(id=si.candidate_id).first()
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

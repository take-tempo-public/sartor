"""Corpus seam — the LLM-proposal review lifecycle (Phase B.4).

Critique a user's edit to an LLM-proposed bullet/title, apply the accept/reject
decision, and promote a candidate clarification into a proposed bullet — 3 routes.
critique + promote make Haiku calls and catch `anthropic` error types in their
bodies (hence this is the one corpus submodule on the egress allowlist); decide is
LLM-free. `_safe_username` gates the owning candidate via the experience chain. DB
imports stay lazy in-function.
"""

from __future__ import annotations

import json
import logging

import anthropic
from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue

from analyzer import LLMResponseError
from blueprints.corpus._bp import corpus_bp
from web_infra import _get_client, _safe_username

logger = logging.getLogger(__name__)

_VALID_DECISIONS = frozenset({"accept_original", "accept_edit", "reject"})


@corpus_bp.route("/api/proposals/<int:proposal_id>/critique", methods=["POST"])
def critique_proposal_route(proposal_id: int) -> ResponseReturnValue:
    """Phase B.4: critique a user's edit to an LLM-proposed bullet or title.

    Request body (optional): `{"user_edited_text": "..."}` — if absent or
    equal to the original, the critique evaluates the proposal as-is.

    Persists the critique JSON on `proposal_review.llm_critique_json` so the
    frontend can re-display it without re-running the LLM call.
    """
    from analyzer import critique_proposal as critique_proposal_llm
    from db.models import (
        Application,
        Bullet,
        Candidate,
        Clarification,
        Experience,
        ExperienceTitle,
        ProposalReview,
    )
    from db.session import get_session, init_db

    data = request.json or {}
    user_edited_text = data.get("user_edited_text")

    init_db()
    session = get_session()
    try:
        proposal = session.query(ProposalReview).filter_by(id=proposal_id).first()
        if proposal is None:
            return jsonify({"error": "Proposal not found"}), 404

        # Determine subject + experience scope
        if proposal.bullet_id is not None:
            subject_kind = "bullet"
            bullet = session.query(Bullet).filter_by(id=proposal.bullet_id).first()
            if bullet is None:
                return jsonify({"error": "Referenced bullet missing"}), 404
            experience = session.query(Experience).filter_by(id=bullet.experience_id).first()
        elif proposal.experience_title_id is not None:
            subject_kind = "experience_title"
            title = (
                session.query(ExperienceTitle)
                .filter_by(
                    id=proposal.experience_title_id,
                )
                .first()
            )
            if title is None:
                return jsonify({"error": "Referenced title missing"}), 404
            experience = session.query(Experience).filter_by(id=title.experience_id).first()
        else:
            return jsonify({"error": "Proposal has no subject"}), 500

        if experience is None:
            return jsonify({"error": "Proposal references missing experience"}), 500

        candidate = session.query(Candidate).filter_by(id=experience.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        # Build experience context for the critique prompt
        official_title_row = next(
            (t for t in experience.titles if t.is_official),
            None,
        )
        existing_bullets = [
            b.text
            for b in sorted(experience.bullets, key=lambda x: x.display_order)
            if b.is_active and not b.is_pending_review
        ]
        experience_context = {
            "company": experience.company,
            "location": experience.location or "",
            "start_date": experience.start_date,
            "end_date": experience.end_date,
            "official_title": official_title_row.title if official_title_row else "",
            "existing_bullets": existing_bullets,
        }

        clarifications = [
            (c.question, c.answer)
            for c in session.query(Clarification)
            .filter_by(
                candidate_id=candidate.id,
            )
            .order_by(Clarification.created_at.desc())
            .limit(30)
        ]

        # JD comes from the application this proposal's run belongs to
        run = proposal.run
        app_row = session.query(Application).filter_by(id=run.application_id).first()
        jd_excerpt = (app_row.jd_text or "")[:3000] if app_row else ""

        client = _get_client()
        try:
            critique = critique_proposal_llm(
                client,
                original_text=proposal.original_text,
                user_edited_text=user_edited_text,
                subject_kind=subject_kind,
                experience_context=experience_context,
                clarifications=clarifications,
                jd_excerpt=jd_excerpt,
                username=candidate.username,
                run_id=run.run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic connection error during critique: %s", exc)
            return jsonify({"error": "Connection to AI service failed."}), 503
        except LLMResponseError as exc:
            logger.error("Critique response failed validation: %s", exc.validation_error)
            return jsonify(
                {
                    "error": "AI critique response was malformed.",
                    "detail": exc.validation_error,
                }
            ), 502

        proposal.llm_critique_json = json.dumps(critique)
        if user_edited_text is not None:
            proposal.user_edited_text = user_edited_text
        session.commit()

        return jsonify(
            {
                "proposal_id": proposal.id,
                "subject_kind": subject_kind,
                "critique": critique,
            }
        )
    finally:
        session.close()


@corpus_bp.route("/api/proposals/<int:proposal_id>/decide", methods=["POST"])
def decide_proposal_route(proposal_id: int) -> ResponseReturnValue:
    """Phase B.4: apply the user's accept/reject decision to an LLM proposal.

    Request body:
      {"decision": "accept_original" | "accept_edit" | "reject",
       "user_edited_text": "..."  // required when decision == "accept_edit"}

    Effects per decision:
    - accept_original: clears is_pending_review on the bullet/title; for
      titles also sets truthful_enough_to_use=1
    - accept_edit: overwrites bullet.text or title.title with the edit;
      clears is_pending_review; for titles also sets truthful_enough_to_use=1
    - reject: bullets get is_active=0 (preserves audit chain via NO-CASCADE
      FK); titles stay non-eligible (is_official=0, truthful_enough_to_use=0,
      is_pending_review=0)

    Idempotent: re-deciding a previously-decided proposal is a 409 unless the
    new decision equals the prior one.
    """
    from datetime import datetime, timezone

    from db.models import (
        Bullet,
        Candidate,
        Experience,
        ExperienceTitle,
        IterationLog,
        ProposalReview,
    )
    from db.session import get_session, init_db

    data = request.json or {}
    decision = (data.get("decision") or "").strip()
    user_edited_text = data.get("user_edited_text")
    if decision not in _VALID_DECISIONS:
        return jsonify(
            {
                "error": f"decision must be one of: {sorted(_VALID_DECISIONS)}",
            }
        ), 400
    if decision == "accept_edit" and not (user_edited_text or "").strip():
        return jsonify({"error": "accept_edit requires non-empty user_edited_text"}), 400

    init_db()
    session = get_session()
    try:
        proposal = session.query(ProposalReview).filter_by(id=proposal_id).first()
        if proposal is None:
            return jsonify({"error": "Proposal not found"}), 404
        if proposal.decision != "pending" and proposal.decision != decision:
            return jsonify(
                {
                    "error": "Proposal already decided",
                    "current_decision": proposal.decision,
                }
            ), 409

        # Defense-in-depth: verify candidate ownership via the experience chain
        if proposal.bullet_id is not None:
            bullet = session.query(Bullet).filter_by(id=proposal.bullet_id).first()
            if bullet is None:
                return jsonify({"error": "Referenced bullet missing"}), 404
            experience = session.query(Experience).filter_by(id=bullet.experience_id).first()
            subject_text_before = bullet.text
            subject_kind = "bullet"
        elif proposal.experience_title_id is not None:
            title = (
                session.query(ExperienceTitle)
                .filter_by(
                    id=proposal.experience_title_id,
                )
                .first()
            )
            if title is None:
                return jsonify({"error": "Referenced title missing"}), 404
            experience = session.query(Experience).filter_by(id=title.experience_id).first()
            subject_text_before = title.title
            subject_kind = "experience_title"
        else:
            return jsonify({"error": "Proposal has no subject"}), 500

        if experience is None:
            return jsonify({"error": "Proposal references missing experience"}), 500
        candidate = session.query(Candidate).filter_by(id=experience.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        # Apply the decision. The branches above ensured exactly one of
        # `bullet` / `title` is non-None — assert here to make that
        # invariant visible to the type checker.
        if decision == "accept_original":
            if subject_kind == "bullet":
                assert bullet is not None
                bullet.is_pending_review = 0
            else:  # experience_title
                assert title is not None
                title.is_pending_review = 0
                title.truthful_enough_to_use = 1
        elif decision == "accept_edit":
            assert user_edited_text is not None
            edit = user_edited_text.strip()
            if subject_kind == "bullet":
                assert bullet is not None
                bullet.text = edit
                bullet.is_pending_review = 0
                proposal.user_edited_text = edit
            else:
                assert title is not None
                title.title = edit
                title.is_pending_review = 0
                title.truthful_enough_to_use = 1
                proposal.user_edited_text = edit
        else:  # reject
            if subject_kind == "bullet":
                assert bullet is not None
                bullet.is_active = 0
                bullet.is_pending_review = 0
            else:
                assert title is not None
                title.is_pending_review = 0
                # Non-eligible already; nothing to set on the title row

        proposal.decision = decision
        proposal.decided_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        session.add(
            IterationLog(
                application_run_id=proposal.application_run_id,
                action=decision,
                summary=(
                    f"{subject_kind} proposal {proposal.id}: "
                    f"{decision} (was: {subject_text_before[:60]!r})"
                ),
            )
        )
        session.commit()

        return jsonify(
            {
                "proposal_id": proposal.id,
                "decision": decision,
                "subject_kind": subject_kind,
            }
        )
    finally:
        session.close()


@corpus_bp.route("/api/clarifications/<int:clarification_id>/promote-to-bullet", methods=["POST"])
def promote_clarification_route(clarification_id: int) -> ResponseReturnValue:
    """Phase B.4: convert a candidate clarification into a proposed bullet.

    Request body:
      {"experience_id": <int>,
       "user_text": "..."  // optional: skip LLM, insert verbatim}

    When `user_text` is absent, calls `promote_clarification_to_bullet()`
    (Haiku) to produce a bullet candidate. Either way, the new bullet lands
    with `is_pending_review=1, source='clarification:<id>'` and a
    `proposal_review` row keyed to it. The clarification's
    `is_promoted_to_bullet` flag is set to 1.
    """
    from analyzer import promote_clarification_to_bullet as promote_llm
    from db.models import (
        Bullet,
        Candidate,
        Clarification,
        Experience,
        IterationLog,
        ProposalReview,
    )
    from db.session import get_session, init_db

    data = request.json or {}
    experience_id = data.get("experience_id")
    user_text = (data.get("user_text") or "").strip()

    if not isinstance(experience_id, int):
        return jsonify({"error": "experience_id (int) required"}), 400

    init_db()
    session = get_session()
    try:
        clarification = session.query(Clarification).filter_by(id=clarification_id).first()
        if clarification is None:
            return jsonify({"error": "Clarification not found"}), 404
        candidate = session.query(Candidate).filter_by(id=clarification.candidate_id).first()
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403

        experience = (
            session.query(Experience)
            .filter_by(
                id=experience_id,
                candidate_id=candidate.id,
            )
            .first()
        )
        if experience is None:
            return jsonify({"error": "Experience not found for this candidate"}), 404

        # Either use the user's text directly, or call the LLM
        pattern_kind: str | None = "manual"
        rationale = ""
        if user_text:
            bullet_text = user_text
        else:
            official_title_row = next(
                (t for t in experience.titles if t.is_official),
                None,
            )
            client = _get_client()
            try:
                llm_out = promote_llm(
                    client,
                    question=clarification.question,
                    answer=clarification.answer,
                    target_company=experience.company,
                    target_official_title=(official_title_row.title if official_title_row else ""),
                    username=candidate.username,
                )
            except anthropic.APIConnectionError as exc:
                logger.error("Anthropic connection error in promote: %s", exc)
                return jsonify({"error": "Connection to AI service failed."}), 503
            except LLMResponseError as exc:
                logger.error("Promote response validation failed: %s", exc.validation_error)
                return jsonify(
                    {"error": "AI response malformed.", "detail": exc.validation_error}
                ), 502
            bullet_text = (llm_out.get("text") or "").strip()
            pattern_kind_raw = (llm_out.get("pattern_kind") or "").strip().lower()
            pattern_kind = (
                pattern_kind_raw
                if pattern_kind_raw in {"xyz", "star", "car", "manual"}
                else "manual"
            )
            rationale = llm_out.get("rationale", "")

        if not bullet_text:
            return jsonify({"error": "Resulting bullet text is empty"}), 502

        last_order = session.query(Bullet).filter_by(experience_id=experience.id).count()
        new_bullet = Bullet(
            experience_id=experience.id,
            text=bullet_text,
            display_order=last_order,
            is_active=1,
            is_pending_review=1,
            source=f"clarification:{clarification.id}",
            pattern_kind=pattern_kind,
            has_outcome=0,
        )
        session.add(new_bullet)
        session.flush()

        # Promotions are not anchored to a specific application_run, but a
        # ProposalReview row still anchors the audit + critique loop. Use the
        # candidate's most recent application_run (if any) for the FK so the
        # review flow can surface this proposal alongside other pending ones.
        from db.models import ApplicationRun

        recent_run = (
            session.query(ApplicationRun)
            .join(
                ApplicationRun.application,
            )
            .filter_by(candidate_id=candidate.id)
            .order_by(
                ApplicationRun.created_at.desc(),
            )
            .first()
        )
        if recent_run is not None:
            session.add(
                ProposalReview(
                    application_run_id=recent_run.id,
                    bullet_id=new_bullet.id,
                    original_text=bullet_text,
                    decision="pending",
                )
            )
            session.add(
                IterationLog(
                    application_run_id=recent_run.id,
                    action="promote_bullet",
                    summary=(
                        f"Promoted clarification {clarification.id} → "
                        f"bullet {new_bullet.id} on experience {experience.id}"
                    ),
                )
            )

        clarification.is_promoted_to_bullet = 1
        session.commit()

        return jsonify(
            {
                "bullet_id": new_bullet.id,
                "experience_id": experience.id,
                "text": bullet_text,
                "pattern_kind": pattern_kind,
                "rationale": rationale,
                "proposal_review_anchored_to_run_id": recent_run.id if recent_run else None,
            }
        )
    finally:
        session.close()

"""Corpus seam — resume upload + ingest, duplicate detection, accept workflow.

The curation family of the corpus sub-package (Sprint 8.3d): the resume upload /
listing, the Haiku-backed ingest-into-corpus, the deterministic near-duplicate
clusterer, and the onboarding-review accept routes (per-bullet / per-title /
per-experience / corpus-wide) + pending counts — 9 routes.

`upload_resume` + `ingest_resume_to_corpus` touch the filesystem (they save the
upload under RESUMES_DIR); ingest adds the `_within` containment guard. The LLM
call in ingest is delegated to `onboarding.corpus_import.ingest_one_resume`, so this
module imports no `anthropic` (no egress-allowlist entry needed). DB imports stay
lazy in-function.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _load_experience_for_candidate, _resolve_proposal_reviews
from web_infra import (
    _get_client,
    _get_or_provision_candidate,
    _load_config,
    _safe_username,
    _save_config,
    _within,
)

if TYPE_CHECKING:
    from db.models import Candidate, Experience
    from onboarding.experience_match import ExperienceLike

logger = logging.getLogger(__name__)


def _find_root(parent: dict[int, int], x: int) -> int:
    """Union-find path-compression helper used by the corpus-duplicates clusterer.

    Mutates `parent` to flatten the chain as it goes.
    """
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


@corpus_bp.route("/api/upload", methods=["POST"])
def upload_resume() -> ResponseReturnValue:
    """Save an uploaded resume into the user's resumes directory and record it as latest."""
    username = request.form.get("username", "")
    if not username:
        return jsonify({"error": "Username required"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    configs_dir = current_app.config["CONFIGS_DIR"]
    safe_user = _safe_username(username, configs_dir=configs_dir)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    safe_name = secure_filename(file.filename)
    user_dir = current_app.config["RESUMES_DIR"] / safe_user
    user_dir.mkdir(exist_ok=True)
    save_path = user_dir / safe_name
    # Containment guard: safe_user (via _safe_username) and safe_name (via
    # secure_filename) are both sanitized, so this is always-True today — a
    # belt-and-suspenders _within check the F-sec-05 gate requires on every
    # FS-touching route, restoring the guard lost in the 8.3 body-only move.
    if not _within(save_path, current_app.config["RESUMES_DIR"]):
        return jsonify({"error": "Invalid filename"}), 400
    file.save(str(save_path))

    # Update config with latest resume reference
    config = _load_config(safe_user, configs_dir=configs_dir)
    if config:
        config["latest_resume"] = safe_name
        _save_config(safe_user, config, configs_dir=configs_dir)

    logger.info("Uploaded resume: %s for user %s", safe_name, safe_user)
    return jsonify({"filename": safe_name, "path": str(save_path)})


@corpus_bp.route("/api/users/<username>/resumes", methods=["GET"])
def list_resumes(username: str) -> ResponseReturnValue:
    """List the resume files in one user's resumes directory."""
    # _safe_username sanitizes + confirms the user exists, scoping the listing to
    # a known candidate's RESUMES_DIR (Sprint 8.3f — was the raw route `username`;
    # the one corpus FS route that reached the filesystem without the _safe_username
    # guard its siblings use, e.g. list_corpus_duplicates). secure_filename inside
    # the guard strips traversal, so RESUMES_DIR / safe_user stays contained.
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    user_dir = current_app.config["RESUMES_DIR"] / safe_user
    # Containment guard: safe_user is already secure_filename-sanitized inside
    # _safe_username, so this is always-True today — the belt-and-suspenders
    # _within check the F-sec-05 gate requires on every FS-touching route.
    if not _within(user_dir, current_app.config["RESUMES_DIR"]):
        return jsonify({"error": "Invalid user"}), 400
    if not user_dir.exists():
        return jsonify([])
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    files = [f.name for f in user_dir.iterdir() if f.suffix.lower() in allowed]
    return jsonify(sorted(files))


@corpus_bp.route("/api/users/<username>/duplicates", methods=["GET"])
def list_corpus_duplicates(username: str) -> ResponseReturnValue:
    """Workstream B1.2: cluster near-duplicate bullets in the candidate's corpus.

    Uses Jaccard >= 0.75 on `hardening.bullet_token_set`; returns clusters per
    experience so the Library "Duplicates" surface can offer keep-one-soft-retire-others
    merging.

    DB-only (no filesystem); _safe_username scopes the candidate. The
    cluster threshold is configurable via ?threshold=0.75.
    """
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session, init_db
    from hardening import bullet_jaccard

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    try:
        threshold = float(request.args.get("threshold", "0.75"))
    except (TypeError, ValueError):
        threshold = 0.75
    threshold = max(0.5, min(1.0, threshold))

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            # Read precondition unmet → 200 + flag, not 409 (see
            # list_user_personas). Mirror the success shape, empty.
            return jsonify(
                {
                    "threshold": threshold,
                    "experiences": [],
                    "cluster_count": 0,
                    "needs_onboarding": True,
                }
            )

        out_experiences = []
        for exp in (
            session.query(Experience)
            .filter_by(
                candidate_id=candidate.id,
            )
            .order_by(Experience.start_date.desc(), Experience.id.desc())
            .all()
        ):
            active = [
                b
                for b in session.query(Bullet)
                .filter_by(
                    experience_id=exp.id,
                    is_active=1,
                )
                .order_by(Bullet.display_order, Bullet.id)
                .all()
            ]
            # Union-find clustering by Jaccard ≥ threshold (_find_root is
            # module-level to avoid late-binding of the per-iteration parent
            # dict — same outcome, satisfies ruff B023).
            parent: dict[int, int] = {b.id: b.id for b in active}
            for i in range(len(active)):
                for j in range(i + 1, len(active)):
                    if bullet_jaccard(active[i].text, active[j].text) >= threshold:
                        ra = _find_root(parent, active[i].id)
                        rb = _find_root(parent, active[j].id)
                        if ra != rb:
                            parent[ra] = rb
            clusters: dict[int, list[int]] = {}
            for b in active:
                clusters.setdefault(_find_root(parent, b.id), []).append(b.id)
            multi = [ids for ids in clusters.values() if len(ids) > 1]
            if not multi:
                continue
            text_by_id = {b.id: b.text for b in active}
            has_outcome_by_id = {b.id: bool(b.has_outcome) for b in active}
            out_clusters = []
            for ids in multi:
                # Recommend the candidate with measurable outcomes; tie-break
                # on the lower id (deterministic across reloads).
                recommended = sorted(
                    ids,
                    key=lambda bid: (
                        not has_outcome_by_id.get(bid, False),
                        bid,
                    ),
                )[0]
                out_clusters.append(
                    {
                        "recommended_keep": recommended,
                        "bullets": [
                            {
                                "id": bid,
                                "text": text_by_id[bid],
                                "has_outcome": has_outcome_by_id[bid],
                            }
                            for bid in ids
                        ],
                    }
                )
            out_experiences.append(
                {
                    "id": exp.id,
                    "company": exp.company,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date,
                    "clusters": out_clusters,
                }
            )
        cluster_count = 0
        for e in out_experiences:
            cluster_count += len(e["clusters"])  # type: ignore[arg-type]
        return jsonify(
            {
                "threshold": threshold,
                "experiences": out_experiences,
                "cluster_count": cluster_count,
            }
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Role-level duplicate detection (merge suggestions)
# ---------------------------------------------------------------------------


def _experience_like(exp: Experience) -> ExperienceLike:
    """Build the pure-value scoring view from an Experience (live rows only)."""
    from onboarding.experience_match import ExperienceLike

    return ExperienceLike(
        company=exp.company,
        start_date=exp.start_date,
        end_date=exp.end_date,
        titles=tuple(t.title for t in exp.titles if t.is_active),
        bullets=tuple(b.text for b in exp.bullets if b.is_active),
    )


def _suggestion_side(exp: Experience) -> dict[str, Any]:
    """Compact one experience for the merge-suggestion card (live titles/bullets)."""
    active_titles = sorted(
        (t for t in exp.titles if t.is_active),
        key=lambda t: (0 if t.is_official else 1, t.id),
    )
    official = next((t for t in active_titles if t.is_official), None)
    fallback = active_titles[0].title if active_titles else None
    return {
        "id": exp.id,
        "company": exp.company,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "official_title": official.title if official else fallback,
        "titles": [t.title for t in active_titles],
        "bullet_count": sum(1 for b in exp.bullets if b.is_active),
    }


@corpus_bp.route("/api/users/<username>/corpus/merge-suggestions", methods=["GET"])
def list_merge_suggestions(username: str) -> ResponseReturnValue:
    """Surface experience pairs that look like the SAME role for a merge/keep-separate decision.

    Deterministic (no LLM): scores every experience pair on company/title/dates/
    bullets via onboarding.experience_match and returns the SIMILAR-band pairs the
    importer's exact-match auto-merge can't catch (e.g. drifted dates), minus any
    the user already dismissed. DB-only; _safe_username scopes the candidate.

    `exp_in_corpus` is the lower-id (older / canonical) role — the merge target
    whose dates are kept; `exp_other` is the more recently imported duplicate.
    """
    from db.models import Candidate, Experience, MergeDismissal
    from db.session import get_session, init_db
    from onboarding.experience_match import score_experiences, shared_bullet_count

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({"suggestions": [], "count": 0, "needs_onboarding": True})
        experiences = (
            session.query(Experience)
            .filter_by(candidate_id=candidate.id)
            .order_by(Experience.start_date.desc(), Experience.id.desc())
            .all()
        )
        dismissed = {
            (d.exp_a_id, d.exp_b_id)
            for d in session.query(MergeDismissal).filter_by(candidate_id=candidate.id)
        }
        likes = {e.id: _experience_like(e) for e in experiences}
        suggestions: list[dict[str, Any]] = []
        for i in range(len(experiences)):
            for j in range(i + 1, len(experiences)):
                a, b = experiences[i], experiences[j]
                pair = (min(a.id, b.id), max(a.id, b.id))
                if pair in dismissed:
                    continue
                result = score_experiences(likes[a.id], likes[b.id])
                if result.band != "SIMILAR":
                    continue
                corpus_exp, other_exp = (a, b) if a.id < b.id else (b, a)
                suggestions.append(
                    {
                        "exp_a_id": pair[0],
                        "exp_b_id": pair[1],
                        "score": result.score,
                        "matched_signals": list(result.matched_signals),
                        "shared_bullet_count": shared_bullet_count(
                            likes[a.id].bullets, likes[b.id].bullets
                        ),
                        "exp_in_corpus": _suggestion_side(corpus_exp),
                        "exp_other": _suggestion_side(other_exp),
                    }
                )
        suggestions.sort(key=lambda s: s["score"], reverse=True)
        return jsonify({"suggestions": suggestions, "count": len(suggestions)})
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/corpus/merge-suggestions/dismiss", methods=["POST"])
def dismiss_merge_suggestion(username: str) -> ResponseReturnValue:
    """Record a 'keep separate' decision for an experience pair so it stops surfacing.

    Pair is stored order-normalized (lower id first) and is idempotent. DB-only;
    _safe_username scopes the candidate and both experiences are ownership-checked.
    """
    from db.models import Candidate, Experience, MergeDismissal
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    data = request.json or {}
    a_raw, b_raw = data.get("exp_a_id"), data.get("exp_b_id")
    if not isinstance(a_raw, int) or not isinstance(b_raw, int) or a_raw == b_raw:
        return jsonify({"error": "exp_a_id and exp_b_id (distinct ints) required"}), 400
    lo, hi = sorted((a_raw, b_raw))

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({"error": "Unknown candidate"}), 404
        owned = {
            e.id
            for e in session.query(Experience)
            .filter(Experience.candidate_id == candidate.id, Experience.id.in_([lo, hi]))
            .all()
        }
        if lo not in owned or hi not in owned:
            return jsonify({"error": "Experience not found for this candidate"}), 404
        existing = (
            session.query(MergeDismissal)
            .filter_by(candidate_id=candidate.id, exp_a_id=lo, exp_b_id=hi)
            .first()
        )
        if existing is None:
            session.add(MergeDismissal(candidate_id=candidate.id, exp_a_id=lo, exp_b_id=hi))
            session.commit()
        return jsonify({"dismissed": True, "exp_a_id": lo, "exp_b_id": hi})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/corpus/ingest-resume", methods=["POST"])
def ingest_resume_to_corpus(username: str) -> ResponseReturnValue:
    """Workstream D: save an uploaded resume, extract its experiences, and merge into corpus.

    Saves under resumes/{user}/, Haiku-extracts experiences, and merges them as
    is_pending_review=1 (the Career Corpus pending banner then surfaces them for review).

    Reuses onboarding.corpus_import.ingest_one_resume so the
    merge-as-alternate-title behavior is identical to the CLI importer.
    One Haiku call per upload (~$0.01-0.03, costs API credit).

    Touches the filesystem (saves the upload) -> _safe_username + _within.
    """
    from db.session import get_session, init_db
    from onboarding.corpus_import import ImportReport, ingest_one_resume

    configs_dir = current_app.config["CONFIGS_DIR"]
    resumes_dir = current_app.config["RESUMES_DIR"]
    safe_user = _safe_username(username, configs_dir=configs_dir)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    safe_name = secure_filename(file.filename)
    user_dir = resumes_dir / safe_user
    user_dir.mkdir(exist_ok=True)
    save_path = (user_dir / safe_name).resolve()
    if not _within(save_path, resumes_dir):
        return jsonify({"error": "Invalid upload path"}), 403
    file.save(str(save_path))

    init_db()
    session = get_session()
    try:
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(session, safe_user, configs_dir=configs_dir),
        )
        report = ImportReport()
        ingest_one_resume(
            save_path,
            candidate.id,
            session,
            client=_get_client(),
            username=safe_user,
            is_primary=False,
            dry_run=False,
            report=report,
        )
        session.commit()
        if report.experiences_dropped:
            # Dropped-role telemetry (fix/output-identity-and-dates): a role
            # the extractor found but couldn't place (missing company and/or
            # start date) used to vanish with no trace. Log loudly so it's
            # visible in server logs even before the UI surfaces it.
            logger.warning(
                "Ingest %s: %d role(s) dropped (missing company/start date): %s",
                safe_name,
                report.experiences_dropped,
                [
                    d.get("candidate_inferred_title") or d.get("company") or "(untitled)"
                    for d in report.dropped_experiences
                ],
            )
        payload = {
            "filename": safe_name,
            "experiences_created": report.experiences_created,
            "experiences_merged": report.experiences_merged,
            "bullets_created": report.bullets_created,
            "alternate_titles_created": report.alternate_titles_created,
            "skills_created": report.skills_created,
            "experiences_dropped": report.experiences_dropped,
            "dropped_experiences": report.dropped_experiences,
            "errors": report.errors,
        }
        # Honesty: a parse/extract failure that yields nothing must NOT look
        # like a successful import. When no experience landed AND the importer
        # recorded an error (e.g. unreadable file, empty text), surface it as a
        # 422 so the client takes its error path instead of a green toast. A
        # genuine 0-but-no-error result (a résumé with no dated roles) stays
        # 201 — the client warns without claiming success.
        nothing_landed = report.experiences_created + report.experiences_merged == 0
        if nothing_landed and report.errors:
            payload["error"] = "Could not extract any experiences from the résumé"
            return jsonify(payload), 422
        return jsonify(payload), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/bullets/<int:bullet_id>/accept", methods=["POST"])
def accept_bullet(bullet_id: int) -> ResponseReturnValue:
    """Clear is_pending_review on one bullet.

    GUI affordance for accepting an LLM-extracted bullet during the onboarding review flow.
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
        bullet.is_pending_review = 0
        _resolve_proposal_reviews(session, decision="accept_original", bullet_ids=[bullet.id])
        session.commit()
        return jsonify({"id": bullet.id, "is_pending_review": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experience-titles/<int:title_id>/accept", methods=["POST"])
def accept_experience_title(title_id: int) -> ResponseReturnValue:
    """Clear is_pending_review on one title."""
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
        title.is_pending_review = 0
        _resolve_proposal_reviews(session, decision="accept_original", title_ids=[title.id])
        session.commit()
        return jsonify({"id": title.id, "is_pending_review": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>/accept-all", methods=["POST"])
def accept_experience_all(experience_id: int) -> ResponseReturnValue:
    """Bulk-accept: clears is_pending_review on every title + active bullet under one experience.

    Used by the "ACCEPT EXPERIENCE" button in the GUI onboarding review flow.
    """
    from db.models import Bullet, ExperienceTitle
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        exp, candidate = _load_experience_for_candidate(session, experience_id)
        if exp is None or candidate is None:
            return jsonify({"error": "Experience not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Candidate validation failed"}), 403
        # Capture the pending ids BEFORE clearing is_pending_review — the
        # ProposalReview bridge below needs to know which bullets/titles this
        # bulk accept just resolved, and the filter below can't see them once
        # is_pending_review flips to 0.
        pending_title_ids = [
            row[0]
            for row in session.query(ExperienceTitle.id).filter_by(
                experience_id=exp.id,
                is_pending_review=1,
            )
        ]
        pending_bullet_ids = [
            row[0]
            for row in session.query(Bullet.id).filter_by(
                experience_id=exp.id,
                is_pending_review=1,
                is_active=1,
            )
        ]
        titles_cleared = (
            session.query(ExperienceTitle)
            .filter(ExperienceTitle.id.in_(pending_title_ids))
            .update({"is_pending_review": 0}, synchronize_session=False)
            if pending_title_ids
            else 0
        )
        bullets_cleared = (
            session.query(Bullet)
            .filter(Bullet.id.in_(pending_bullet_ids))
            .update({"is_pending_review": 0}, synchronize_session=False)
            if pending_bullet_ids
            else 0
        )
        _resolve_proposal_reviews(
            session,
            decision="accept_original",
            bullet_ids=pending_bullet_ids,
            title_ids=pending_title_ids,
        )
        session.commit()
        return jsonify(
            {
                "experience_id": exp.id,
                "titles_accepted": titles_cleared,
                "bullets_accepted": bullets_cleared,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/accept-all-pending", methods=["POST"])
def accept_all_pending(username: str) -> ResponseReturnValue:
    """Corpus-wide bulk-accept: clears is_pending_review on all titles + bullets.

    Drives the "Accept all pending" button in the onboarding banner (KW2) — senior
    résumés have many roles, and accepting role-by-role is tedious. The
    per-experience accept-all route still covers the by-role case.
    """
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({"titles_accepted": 0, "bullets_accepted": 0})
        exp_ids = [
            row[0]
            for row in session.query(Experience.id)
            .filter_by(
                candidate_id=candidate.id,
            )
            .all()
        ]
        if not exp_ids:
            return jsonify({"titles_accepted": 0, "bullets_accepted": 0})
        # Bulk updates over exp_ids; synchronize_session=False because we
        # commit + close immediately and never reuse the session objects.
        # Ids captured BEFORE the update (same reason as accept_experience_all
        # above): the ProposalReview bridge needs the pending set, which the
        # is_pending_review=1 filter can no longer see post-update.
        pending_title_ids = [
            row[0]
            for row in session.query(ExperienceTitle.id).filter(
                ExperienceTitle.experience_id.in_(exp_ids),
                ExperienceTitle.is_pending_review == 1,
            )
        ]
        pending_bullet_ids = [
            row[0]
            for row in session.query(Bullet.id).filter(
                Bullet.experience_id.in_(exp_ids),
                Bullet.is_pending_review == 1,
                Bullet.is_active == 1,
            )
        ]
        titles_cleared = (
            session.query(ExperienceTitle)
            .filter(ExperienceTitle.id.in_(pending_title_ids))
            .update({"is_pending_review": 0}, synchronize_session=False)
            if pending_title_ids
            else 0
        )
        bullets_cleared = (
            session.query(Bullet)
            .filter(Bullet.id.in_(pending_bullet_ids))
            .update({"is_pending_review": 0}, synchronize_session=False)
            if pending_bullet_ids
            else 0
        )
        _resolve_proposal_reviews(
            session,
            decision="accept_original",
            bullet_ids=pending_bullet_ids,
            title_ids=pending_title_ids,
        )
        session.commit()
        return jsonify(
            {
                "titles_accepted": titles_cleared,
                "bullets_accepted": bullets_cleared,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/pending-counts", methods=["GET"])
def pending_counts(username: str) -> ResponseReturnValue:
    """Counts of pending-review titles + bullets for the candidate.

    Drives the onboarding banner at the top of the Career Corpus tab —
    shown when the candidate has any pending review left to clear.
    """
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify(
                {
                    "candidate_present": False,
                    "pending_titles": 0,
                    "pending_bullets": 0,
                    "experiences_with_pending": 0,
                }
            )
        exp_ids = [
            row[0]
            for row in session.query(Experience.id)
            .filter_by(
                candidate_id=candidate.id,
            )
            .all()
        ]
        if not exp_ids:
            return jsonify(
                {
                    "candidate_present": True,
                    "pending_titles": 0,
                    "pending_bullets": 0,
                    "experiences_with_pending": 0,
                }
            )
        n_titles = (
            session.query(ExperienceTitle)
            .filter(
                ExperienceTitle.experience_id.in_(exp_ids),
                ExperienceTitle.is_pending_review == 1,
            )
            .count()
        )
        n_bullets = (
            session.query(Bullet)
            .filter(
                Bullet.experience_id.in_(exp_ids),
                Bullet.is_pending_review == 1,
                Bullet.is_active == 1,
            )
            .count()
        )
        # Experiences with at least one pending row (title or bullet)
        pending_exp_ids = set()
        for t in (
            session.query(ExperienceTitle.experience_id)
            .filter(
                ExperienceTitle.experience_id.in_(exp_ids),
                ExperienceTitle.is_pending_review == 1,
            )
            .all()
        ):
            pending_exp_ids.add(t[0])
        for b in (
            session.query(Bullet.experience_id)
            .filter(
                Bullet.experience_id.in_(exp_ids),
                Bullet.is_pending_review == 1,
                Bullet.is_active == 1,
            )
            .all()
        ):
            pending_exp_ids.add(b[0])
        return jsonify(
            {
                "candidate_present": True,
                "pending_titles": n_titles,
                "pending_bullets": n_bullets,
                "experiences_with_pending": len(pending_exp_ids),
            }
        )
    finally:
        session.close()

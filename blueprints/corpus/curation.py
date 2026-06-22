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
from typing import TYPE_CHECKING, cast

from flask import current_app, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _load_experience_for_candidate
from web_infra import (
    _get_client,
    _get_or_provision_candidate,
    _load_config,
    _safe_username,
    _save_config,
    _within,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)


def _find_root(parent: dict[int, int], x: int) -> int:
    """Union-find path-compression helper used by the corpus-duplicates
    clusterer. Mutates `parent` to flatten the chain as it goes."""
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


@corpus_bp.route("/api/upload", methods=["POST"])
def upload_resume() -> ResponseReturnValue:
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
    user_dir = current_app.config["RESUMES_DIR"] / username
    if not user_dir.exists():
        return jsonify([])
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    files = [
        f.name for f in user_dir.iterdir()
        if f.suffix.lower() in allowed
    ]
    return jsonify(sorted(files))


@corpus_bp.route("/api/users/<username>/duplicates", methods=["GET"])
def list_corpus_duplicates(username: str) -> ResponseReturnValue:
    """Workstream B1.2: cluster near-duplicate bullets in the candidate's
    corpus (Jaccard ≥ 0.75 on `hardening.bullet_token_set`). Returns
    clusters per experience so the Library "Duplicates" surface can offer
    keep-one-soft-retire-others merging.

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
            return jsonify({
                "threshold": threshold,
                "experiences": [],
                "cluster_count": 0,
                "needs_onboarding": True,
            })

        out_experiences = []
        for exp in session.query(Experience).filter_by(
            candidate_id=candidate.id,
        ).order_by(Experience.start_date.desc(), Experience.id.desc()).all():
            active = [
                b for b in session.query(Bullet).filter_by(
                    experience_id=exp.id, is_active=1,
                ).order_by(Bullet.display_order, Bullet.id).all()
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
                out_clusters.append({
                    "recommended_keep": recommended,
                    "bullets": [
                        {
                            "id": bid,
                            "text": text_by_id[bid],
                            "has_outcome": has_outcome_by_id[bid],
                        }
                        for bid in ids
                    ],
                })
            out_experiences.append({
                "id": exp.id,
                "company": exp.company,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "clusters": out_clusters,
            })
        cluster_count = 0
        for e in out_experiences:
            cluster_count += len(e["clusters"])  # type: ignore[arg-type]
        return jsonify({
            "threshold": threshold,
            "experiences": out_experiences,
            "cluster_count": cluster_count,
        })
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/corpus/ingest-resume", methods=["POST"])
def ingest_resume_to_corpus(username: str) -> ResponseReturnValue:
    """Workstream D: the repurposed RESUME panel. Save an uploaded resume
    under resumes/{user}/, Haiku-extract its experiences, and merge them
    into the candidate's corpus as is_pending_review=1 (the Career Corpus
    pending banner then surfaces them for review).

    Reuses onboarding.corpus_import.ingest_one_resume so the
    merge-as-alternate-title behavior is identical to the CLI importer.
    One Haiku call per upload (~$0.01-0.03, costs API credit).

    Touches the filesystem (saves the upload) → _safe_username + _within.
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
            save_path, candidate.id, session,
            client=_get_client(), username=safe_user,
            is_primary=False, dry_run=False, report=report,
        )
        session.commit()
        payload = {
            "filename": safe_name,
            "experiences_created": report.experiences_created,
            "experiences_merged": report.experiences_merged,
            "bullets_created": report.bullets_created,
            "alternate_titles_created": report.alternate_titles_created,
            "errors": report.errors,
        }
        # Honesty: a parse/extract failure that yields nothing must NOT look
        # like a successful import. When no experience landed AND the importer
        # recorded an error (e.g. unreadable file, empty text), surface it as a
        # 422 so the client takes its error path instead of a green toast. A
        # genuine 0-but-no-error result (a résumé with no dated roles) stays
        # 201 — the client warns without claiming success.
        nothing_landed = (
            report.experiences_created + report.experiences_merged == 0
        )
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
    """Clear is_pending_review on one bullet — the GUI affordance for
    accepting an LLM-extracted bullet during the onboarding review flow.
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
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403
        bullet.is_pending_review = 0
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
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return jsonify({"error": "Candidate validation failed"}), 403
        title.is_pending_review = 0
        session.commit()
        return jsonify({"id": title.id, "is_pending_review": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/experiences/<int:experience_id>/accept-all", methods=["POST"])
def accept_experience_all(experience_id: int) -> ResponseReturnValue:
    """Bulk-accept: clears is_pending_review on every title + active
    bullet under one experience. Used by the "ACCEPT EXPERIENCE" button
    in the GUI onboarding review flow."""
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
        titles_cleared = session.query(ExperienceTitle).filter_by(
            experience_id=exp.id, is_pending_review=1,
        ).update({"is_pending_review": 0})
        bullets_cleared = session.query(Bullet).filter_by(
            experience_id=exp.id, is_pending_review=1, is_active=1,
        ).update({"is_pending_review": 0})
        session.commit()
        return jsonify({
            "experience_id": exp.id,
            "titles_accepted": titles_cleared,
            "bullets_accepted": bullets_cleared,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@corpus_bp.route("/api/users/<username>/accept-all-pending", methods=["POST"])
def accept_all_pending(username: str) -> ResponseReturnValue:
    """Corpus-wide bulk-accept: clears is_pending_review on every title +
    active bullet across all of the candidate's experiences. Drives the
    "Accept all pending" button in the onboarding banner (KW2) — senior
    résumés have many roles, and accepting role-by-role is tedious. The
    per-experience accept-all route still covers the by-role case."""
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
        exp_ids = [row[0] for row in session.query(Experience.id).filter_by(
            candidate_id=candidate.id,
        ).all()]
        if not exp_ids:
            return jsonify({"titles_accepted": 0, "bullets_accepted": 0})
        # Bulk updates over exp_ids; synchronize_session=False because we
        # commit + close immediately and never reuse the session objects.
        titles_cleared = session.query(ExperienceTitle).filter(
            ExperienceTitle.experience_id.in_(exp_ids),
            ExperienceTitle.is_pending_review == 1,
        ).update({"is_pending_review": 0}, synchronize_session=False)
        bullets_cleared = session.query(Bullet).filter(
            Bullet.experience_id.in_(exp_ids),
            Bullet.is_pending_review == 1,
            Bullet.is_active == 1,
        ).update({"is_pending_review": 0}, synchronize_session=False)
        session.commit()
        return jsonify({
            "titles_accepted": titles_cleared,
            "bullets_accepted": bullets_cleared,
        })
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
            return jsonify({
                "candidate_present": False,
                "pending_titles": 0,
                "pending_bullets": 0,
                "experiences_with_pending": 0,
            })
        exp_ids = [row[0] for row in session.query(Experience.id).filter_by(
            candidate_id=candidate.id,
        ).all()]
        if not exp_ids:
            return jsonify({
                "candidate_present": True,
                "pending_titles": 0,
                "pending_bullets": 0,
                "experiences_with_pending": 0,
            })
        n_titles = session.query(ExperienceTitle).filter(
            ExperienceTitle.experience_id.in_(exp_ids),
            ExperienceTitle.is_pending_review == 1,
        ).count()
        n_bullets = session.query(Bullet).filter(
            Bullet.experience_id.in_(exp_ids),
            Bullet.is_pending_review == 1,
            Bullet.is_active == 1,
        ).count()
        # Experiences with at least one pending row (title or bullet)
        pending_exp_ids = set()
        for t in session.query(ExperienceTitle.experience_id).filter(
            ExperienceTitle.experience_id.in_(exp_ids),
            ExperienceTitle.is_pending_review == 1,
        ).all():
            pending_exp_ids.add(t[0])
        for b in session.query(Bullet.experience_id).filter(
            Bullet.experience_id.in_(exp_ids),
            Bullet.is_pending_review == 1,
            Bullet.is_active == 1,
        ).all():
            pending_exp_ids.add(b[0])
        return jsonify({
            "candidate_present": True,
            "pending_titles": n_titles,
            "pending_bullets": n_bullets,
            "experiences_with_pending": len(pending_exp_ids),
        })
    finally:
        session.close()

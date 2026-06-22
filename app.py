"""Flask server — routes and orchestration.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.
"""

import json
import logging
import os
import re
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
from flask import Flask, Response, jsonify, make_response, render_template, request
from werkzeug.utils import secure_filename

from analyzer import prompt_overrides
from blueprints import analysis_bp, assistant_bp, corpus_bp, generation_bp, templates_bp

# Corpus serializers — moved to blueprints/corpus/_shared.py (Sprint 8.3d). The
# applications routes still resident here (get_application_composition,
# suggest_application_skills) keep using `_tag_list` / `_skill_to_dict` until the
# applications seam moves (8.3f); they import them from the corpus package
# (app.py -> blueprint is the legal direction). The import relocates to
# blueprints/applications at 8.3f.
from blueprints.corpus import _skill_to_dict, _tag_list
from config import Config
from dashboard import dashboard_bp
from hardening import validate_config
from web_infra import (
    _error_detail_payload,
    _get_client,
    _is_localhost_request,
    _sse,
    _within,
)

# P7 Observability: structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIGS_DIR = BASE_DIR / "configs"
RESUMES_DIR = BASE_DIR / "resumes"
OUTPUT_DIR = BASE_DIR / "output"

# The only directory the annotation/bootstrap write surface ever touches.
# Equal to evals.annotation.ALLOWED_ROOT / evals.bootstrap.ALLOWED_ROOT
# (PROJECT_ROOT/evals/fixtures/real) — gitignored (.gitignore:52), so the
# PII-bearing bootstrap/annotation artifacts stay untracked. Module-level so
# tests can monkeypatch it to a temp dir.
ANNOTATION_ROOT = BASE_DIR / "evals" / "fixtures" / "real"

ALLOWED_EXTENSIONS = {".docx", ".pdf", ".md"}

# These module-global path constants are retained for the not-yet-moved routes +
# their tests (Sprint 8.3a foundation moves NO routes). They mirror the injected
# Config; each seam branch (8.3b-h) migrates its routes from these globals to
# `current_app.config[...]` as it moves. The factory below is the single source of
# truth for a fresh app's config.


def register_blueprints(app: Flask) -> None:
    """Register every blueprint in one place (called by the factory)."""
    app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")
    app.register_blueprint(assistant_bp, url_prefix="/api/assistant")
    # No url_prefix: the analysis routes carry full paths (/api/analyze, /api/clarify,
    # …) and share no common sub-prefix, so the URLs stay byte-identical (Sprint 8.3b).
    app.register_blueprint(analysis_bp)
    # No url_prefix: same as analysis — the generation routes carry full paths
    # (/api/generate, /api/save-edits, /api/download/…, …) (Sprint 8.3c).
    app.register_blueprint(generation_bp)
    # No url_prefix: the corpus routes carry full paths (/api/users/<u>/experiences,
    # /api/bullets/<id>, /api/proposals/<id>/critique, …) and share no common
    # sub-prefix, so the URLs stay byte-identical (Sprint 8.3d).
    app.register_blueprint(corpus_bp)
    # No url_prefix: the templates/personas routes carry full paths
    # (/api/personas/<id>, /api/users/<u>/personas, /api/applications/<id>/preview,
    # …), so the URLs stay byte-identical (Sprint 8.3e).
    app.register_blueprint(templates_bp)


def create_app(config: Config | None = None) -> Flask:
    """Application factory (Sprint 8.3a).

    The composition root: builds the Flask app from an injected `Config`
    (defaulting to production paths), pushes the config, ensures the runtime
    directories exist (the old import-time mkdir loop), and registers the
    blueprints. The side effects that importing this module used to trigger now
    happen here, when the factory is called.
    """
    app = Flask(__name__)
    config = config or Config()
    app.config.update(config.as_flask_config())
    # Disable browser caching of /static/* responses so UI edits land on
    # the next page reload without requiring a Flask restart or a manual
    # cache-bust query string. The `/` route also sets `Cache-Control:
    # no-cache` (see the `index` view) so the HTML shell is covered too.
    # Local-first single-tenant tool: cache-friendliness has no real
    # payoff here, and the alternative (cache-buster query strings,
    # process-start tokens, etc.) bites whenever the developer or user
    # forgets to restart.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    config.ensure_dirs()
    register_blueprints(app)
    return app


# Module-level WSGI / console-script (`callback = app:main`) / back-compat handle.
# The 93 @app.route decorators below attach to THIS instance at import; the factory
# additionally registers the blueprints. A freshly-built create_app(...) in a test
# carries the blueprints but not the module-level routes (they decorate this
# instance only) — main-route tests use this `app` until their seam moves onto a
# factory-registered blueprint.
app = create_app()


def _load_config(username: str) -> dict:
    # Sanitize here, not only at the call site: secure_filename strips ../ and
    # other traversal sequences, so the config read is contained to CONFIGS_DIR
    # even when a caller passes raw input (PX-21). An unsafe-empty or missing
    # config resolves to {} (treated as "no such user" by callers).
    safe = secure_filename(username)
    if not safe:
        return {}
    path = CONFIGS_DIR / f"{safe}.config"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(username: str, config: dict) -> None:
    # Mirror _load_config: sanitize at the helper so the write is contained to
    # CONFIGS_DIR regardless of the caller (PX-21). An all-stripped username
    # (e.g. "...") is rejected rather than written as a junk ".config" — every
    # real caller (create_user/update_config/upload_resume) pre-sanitizes, so
    # this raise is unreachable defense-in-depth in practice.
    safe = secure_filename(username)
    if not safe:
        raise ValueError(f"unsafe username for config write: {username!r}")
    path = CONFIGS_DIR / f"{safe}.config"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _safe_username(username: str) -> str | None:
    """Sanitize username and confirm the user exists. Returns None if invalid.

    Prevents path traversal: secure_filename strips ../  and other traversal
    sequences; the config existence check ensures only real users are accepted.
    """
    safe = secure_filename(username)
    if not safe:
        return None
    if not (CONFIGS_DIR / f"{safe}.config").exists():
        return None
    return safe


def _get_or_provision_candidate(session, safe_user: str):
    """Return the candidate row for safe_user, creating it from config if absent.

    Replaces the old "no candidate row yet → needs_onboarding" gate. Every user
    starts config-only (create_user writes a config, not a DB row); the first
    corpus write provisions the row on demand. Reuses the idempotent,
    non-destructive import_candidate_from_config (identity + skills + certs +
    education from configs/{user}.config). The caller owns the commit.
    """
    from db.models import Candidate
    candidate = session.query(Candidate).filter_by(username=safe_user).first()
    if candidate is None:
        from onboarding.corpus_import import import_candidate_from_config
        import_candidate_from_config(safe_user, session)  # add + flush, no commit
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
    return candidate


# --- Routes ---

@app.route("/")
def index():
    """Serve the single-page app shell.

    Cache headers are set to `no-cache` so a freshly-deployed
    `templates/index.html` is always picked up on the next request —
    avoids the "I shipped a UI change but the user still sees the old
    button set" footgun. Static CSS/JS continue to use Flask's
    default caching; we cache-bust those by file path when needed.
    """
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


@app.route("/api/users", methods=["GET"])
def list_users():
    users = [p.stem for p in CONFIGS_DIR.glob("*.config")]
    return jsonify(users)


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.json
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400
    safe = secure_filename(username)
    if not safe:
        return jsonify({"error": "Invalid username"}), 400

    config = {
        "name": data.get("name", username),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "linkedin_url": data.get("linkedin_url", ""),
        "website_url": data.get("website_url", ""),
        "portfolio_urls": [],
        "skills": [],
        "certifications": [],
        "education_summary": "",
        "notes": "",
    }
    _save_config(safe, config)
    (RESUMES_DIR / safe).mkdir(exist_ok=True)
    logger.info("Created user: %s", safe)
    return jsonify({"username": safe, "config": config})


@app.route("/api/users/<username>/config", methods=["GET"])
def get_config(username):
    if not secure_filename(username):
        return jsonify({"error": "Invalid username"}), 400
    config = _load_config(username)
    if not config:
        return jsonify({"error": "User not found"}), 404
    return jsonify(config)


@app.route("/api/users/<username>/config", methods=["PUT"])
def update_config(username):
    if not secure_filename(username):
        return jsonify({"error": "Invalid username"}), 400
    config = request.json
    errors = validate_config(config)
    if errors:
        return jsonify({"errors": errors}), 400
    _save_config(username, config)
    logger.info("Updated config for: %s", username)
    return jsonify({"ok": True})


@app.route("/api/users/<username>/profile/fetch", methods=["POST"])
def fetch_profile(username):
    """PX-02: opt-in scrape of the user's saved profile URLs into the corpus.

    User-triggered by the Settings "Fetch profile content" button — that click
    IS the opt-in act. Reads the SAVED config (linkedin_url / website_url /
    portfolio_urls), runs the deterministic, best-effort
    `scraper.fetch_profile_content` (per-URL cap; `RequestException` swallowed →
    ""), and caches the combined text in `Candidate.online_profile_text`. From
    there `build_context_set_from_db` surfaces it to the LLM via the
    `<candidate_web_presence>` block.

    The network egress happens inside `scraper.py` (already on the PX-08 egress
    allowlist); this route imports no network library. Stored as a DISTINCT
    column from `profile_text` (the β.6 positioning summary) so the scrape can
    never clobber the résumé `basics.summary`.
    """
    from db.session import get_session, init_db
    from scraper import fetch_profile_content

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    # Defensive containment: the config we read must resolve within CONFIGS_DIR.
    config_path = CONFIGS_DIR / f"{safe_user}.config"
    if not _within(config_path, CONFIGS_DIR):
        return jsonify({"error": "Invalid config path"}), 403

    config = _load_config(safe_user)
    url_count = sum(
        1 for u in (
            config.get("linkedin_url", ""),
            config.get("website_url", ""),
            *config.get("portfolio_urls", []),
        ) if u
    )
    scraped = fetch_profile_content(config)

    init_db()
    session = get_session()
    try:
        candidate = _get_or_provision_candidate(session, safe_user)
        candidate.online_profile_text = scraped or None
        session.commit()
    finally:
        session.close()

    logger.info(
        "PX-02 profile fetch for %s: %d chars from %d configured URL(s)",
        safe_user, len(scraped), url_count,
    )
    return jsonify({"ok": True, "chars": len(scraped), "urls": url_count})


# ---------------------------------------------------------------------------
# Phase D.3: Applications list routes
# ---------------------------------------------------------------------------

# Canonical lifecycle statuses (migration 0007; semantics table in
# docs/dev/RELEASE_ARC.md, agreed 2026-05-29). `interview` is terminal —
# the product's signal is "this résumé got a callback", not job-hunt
# bookkeeping past that point (B.8 Part 1 decision, 2026-06-10).
_VALID_APP_STATUSES = frozenset({"draft", "submitted", "interview", "rejected", "withdrawn"})


def _application_summary_dict(app_row, runs, pending_proposal_count: int) -> dict:
    """Compact application row for the Applications tab list view."""
    latest_run = runs[-1] if runs else None
    return {
        "id": app_row.id,
        "title": app_row.title,
        "company": app_row.company,
        "status": app_row.status,
        "jd_url": app_row.jd_url,
        "jd_fingerprint": app_row.jd_fingerprint,
        "created_at": app_row.created_at,
        "updated_at": app_row.updated_at,
        "sent_at": app_row.sent_at,
        "outcome_at": app_row.outcome_at,
        "iteration_count": len(runs),
        "latest_iteration": latest_run.iteration if latest_run else 0,
        "latest_run_id": latest_run.run_id if latest_run else None,
        "pending_proposals": pending_proposal_count,
    }


@app.route("/api/users/<username>/applications", methods=["GET"])
def list_applications(username: str):
    """Return all applications for this candidate, newest-first by updated_at.

    Optional `?status=` filter (single value or comma-separated, e.g.
    `?status=interview` or `?status=interview,rejected`) narrows to those
    lifecycle statuses — the programmatic query surface for the B.8
    outcome-learning layer. Unknown statuses → 400.
    """
    from sqlalchemy import func
    from sqlalchemy.orm import selectinload

    from db.models import Application, Candidate, ProposalReview
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    raw_status = (request.args.get("status") or "").strip().lower()
    wanted_statuses: set[str] = set()
    if raw_status:
        wanted_statuses = {s.strip() for s in raw_status.split(",") if s.strip()}
        invalid = wanted_statuses - _VALID_APP_STATUSES
        if invalid:
            return jsonify({
                "error": f"status must be among {sorted(_VALID_APP_STATUSES)}; "
                         f"got {sorted(invalid)}",
            }), 400

    # Wrapped with logger.exception (2026-05-26) — see list_bundled_personas.
    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                # Read precondition unmet → 200 + flag, not 409. Success shape is
                # a bare array; the needs-onboarding case is the discriminated
                # object the frontend branches on before treating it as a list.
                return jsonify({"applications": [], "needs_onboarding": True})
            query = (
                session.query(Application)
                .options(selectinload(Application.runs))
                .filter_by(candidate_id=candidate.id)
            )
            if wanted_statuses:
                query = query.filter(Application.status.in_(wanted_statuses))
            rows = query.order_by(Application.updated_at.desc()).all()

            # Pending-proposal counts in ONE grouped query over every run id
            # (was a per-application COUNT → N+1; selectinload above folds the
            # per-row .runs lazy-load into one more query). Net ~3 queries
            # regardless of how many applications the user has.
            all_run_ids = [r.id for app_row in rows for r in app_row.runs]
            pending_by_run: dict[int, int] = {}
            if all_run_ids:
                for run_id, count in (
                    session.query(
                        ProposalReview.application_run_id,
                        func.count(ProposalReview.id),
                    )
                    .filter(
                        ProposalReview.application_run_id.in_(all_run_ids),
                        ProposalReview.decision == "pending",
                    )
                    .group_by(ProposalReview.application_run_id)
                    .all()
                ):
                    pending_by_run[run_id] = count

            out = []
            for app_row in rows:
                runs = sorted(app_row.runs, key=lambda r: r.iteration)
                pending = sum(pending_by_run.get(r.id, 0) for r in runs)
                out.append(_application_summary_dict(app_row, runs, pending))
            return jsonify(out)
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_applications failed for user=%s", safe_user)
        return jsonify({
            "error": "Failed to load applications",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/applications/<int:application_id>", methods=["GET"])
def get_application(application_id: int):
    """Full detail for one application: metadata + runs + pending-proposal counts.

    Used by the Applications tab when the user opens a card to see the
    iteration history and decide whether to resume editing.
    """
    from db.models import Application, Candidate, ProposalReview
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        app_row = session.query(Application).filter_by(id=application_id).first()
        if app_row is None:
            return jsonify({"error": "Application not found"}), 404
        candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
        safe_user = _safe_username(candidate.username) if candidate else None
        if candidate is None or safe_user is None:
            return jsonify({"error": "Candidate validation failed"}), 403

        runs_sorted = sorted(app_row.runs, key=lambda r: r.iteration)
        runs_dict = []
        for r in runs_sorted:
            pending = session.query(ProposalReview).filter_by(
                application_run_id=r.id, decision="pending",
            ).count()
            runs_dict.append({
                "id": r.id,
                "iteration": r.iteration,
                "run_id": r.run_id,
                "prompt_version": r.prompt_version,
                "persona_template_id": r.persona_template_id,
                "created_at": r.created_at,
                "has_resume": r.generated_resume_md is not None,
                "has_cover_letter": r.generated_cover_letter_md is not None,
                "has_edits": (r.edited_resume_text is not None
                              or r.edited_cover_letter_text is not None),
                "pending_proposals": pending,
                "ats_roundtrip_status": _parse_ats_status(r.ats_roundtrip_json),
            })

        return jsonify({
            "id": app_row.id,
            "title": app_row.title,
            "company": app_row.company,
            "status": app_row.status,
            "jd_text": app_row.jd_text,
            "jd_url": app_row.jd_url,
            "jd_fingerprint": app_row.jd_fingerprint,
            "candidate_username": candidate.username,
            "created_at": app_row.created_at,
            "updated_at": app_row.updated_at,
            "sent_at": app_row.sent_at,
            "outcome_at": app_row.outcome_at,
            "notes": app_row.notes,
            "runs": runs_dict,
            "resume_state": _build_resume_state(safe_user, runs_sorted),
        })
    finally:
        session.close()


def _build_resume_state(safe_user: str, runs_sorted: list) -> dict:
    """Package the state the frontend needs to resume a prior application into
    the wizard at its FURTHEST step with data (#4 robustness).

    Picks the most-recent run carrying resumable state (a generated résumé in
    the DB, or a discoverable on-disk context file), pairs it with the context
    file rediscovered via `_find_context_path_for_run`, and classifies a
    `target_step` from which context keys are present (most-advanced wins):

      - generated/edited résumé present .................... Step 6 (download)
      - composition_overrides / llm_recommendations ....... Step 3 (compose)
      - clarifications / clarification_questions .......... Step 2 (clarify)
      - llm_analysis (analyze ran) ........................ Step 1 (analyze)

    For Steps 1–3 the analysis panel rehydrates from the context file's
    `llm_analysis` + `deterministic_analysis`; Step 2 also ships the saved
    clarify questions + answers so the frontend renders them WITHOUT re-calling
    `/api/clarify`. `resumable` is False only when nothing can be rehydrated
    (no generated résumé AND no readable context file — e.g. output/ cleaned on
    an analyze-only application). When a résumé was generated but the context
    file is gone, Step 6 still resumes in a degraded mode (editors hydrate from
    the DB markdown).
    """
    for r in reversed(runs_sorted):
        resume_md = r.edited_resume_text or r.generated_resume_md or ""
        ctx_path = _find_context_path_for_run(safe_user, r.id)
        ctx_data: dict | None = None
        if ctx_path:
            try:
                ctx_data = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                ctx_data = None
        # Nothing to resume from this run — an older run may still carry state.
        if not resume_md and not isinstance(ctx_data, dict):
            continue

        iteration = 0
        if isinstance(ctx_data, dict):
            raw_iter = ctx_data.get("iteration", 0)
            iteration = raw_iter if isinstance(raw_iter, int) else 0

        base = {
            "application_run_id": r.id,
            "persona_template_id": r.persona_template_id,
            "context_path": ctx_path,
            "iteration": iteration,
            "resumable": True,
        }

        # Step 6 — a résumé was generated (existing behavior; degraded when the
        # context file is gone — the editors still hydrate from the DB markdown).
        if resume_md:
            cover_md = r.edited_cover_letter_text or r.generated_cover_letter_md or ""
            return {**base, "target_step": 6,
                    "resume_md": resume_md, "cover_letter_md": cover_md}

        # No generated résumé — restore the furthest pre-generate step from the
        # context file. ctx_data is a dict here (guarded by the continue above).
        if not isinstance(ctx_data, dict):  # pragma: no cover - mypy narrowing
            continue
        analysis = ctx_data.get("llm_analysis")
        if not analysis:
            # Context file predates analysis (shouldn't normally happen) — can't
            # rehydrate the analysis panel; fall through to an older run.
            continue
        det = ctx_data.get("deterministic_analysis") or {}
        deterministic = {
            "keyword_overlap": det.get("keyword_overlap", {}),
            "ats_warnings": det.get("ats_warnings", []),
        }
        if ctx_data.get("composition_overrides") or ctx_data.get("llm_recommendations"):
            target_step = 3
        elif ctx_data.get("clarifications") or ctx_data.get("clarification_questions"):
            target_step = 2
        else:
            target_step = 1

        state = {**base, "target_step": target_step,
                 "analysis": analysis, "deterministic": deterministic}
        if target_step == 2:
            state["clarification_questions"] = ctx_data.get("clarification_questions") or []
            state["clarifications"] = ctx_data.get("clarifications") or {}
        return state
    return {"resumable": False}


def _parse_ats_status(blob: str | None) -> str | None:
    """Best-effort extract of the 'status' field from ats_roundtrip_json."""
    if not blob:
        return None
    try:
        return json.loads(blob).get("status")
    except (json.JSONDecodeError, AttributeError):
        return None


def _find_context_path_for_run(safe_user: str, application_run_id: int) -> str | None:
    """Rediscover the most-recent on-disk context_*.json for an application run.

    ApplicationRun rows don't store a path to their context file — the file is
    written by `save_iteration_context` AFTER the run row exists, and each
    iteration writes a NEW file. But every context file embeds
    `application_run_id`, so we glob the user's output dir and return the newest
    file whose embedded id matches: newest by the `iteration` field, then by
    mtime as a tiebreaker. LLM-free and deterministic.

    Returns None when the user dir is absent, no file matches, or every match is
    unreadable. Each candidate path is `_within`-guarded under OUTPUT_DIR before
    it's read (defense-in-depth; the glob root already sits inside OUTPUT_DIR).
    Used by the D.3.1 resume-a-prior-application flow.
    """
    user_dir = OUTPUT_DIR / safe_user
    if not user_dir.is_dir():
        return None
    best: tuple[int, float, str] | None = None  # (iteration, mtime, path)
    for cp in user_dir.glob("context_*.json"):
        if not _within(cp, OUTPUT_DIR):
            continue
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("application_run_id") != application_run_id:
            continue
        raw_iter = data.get("iteration", 0)
        iteration = raw_iter if isinstance(raw_iter, int) else 0
        try:
            mtime = cp.stat().st_mtime
        except OSError:
            mtime = 0.0
        key = (iteration, mtime, str(cp))
        if best is None or key > best:
            best = key
    return best[2] if best else None


@app.route("/api/applications/<int:application_id>/status", methods=["PUT"])
def update_application_status(application_id: int):
    """Set application status to one of the valid lifecycle values."""
    from datetime import timezone

    from db.models import Application, Candidate
    from db.session import get_session, init_db

    data = request.json or {}
    status = (data.get("status") or "").strip().lower()
    if status not in _VALID_APP_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(_VALID_APP_STATUSES)}"}), 400

    init_db()
    session = get_session()
    try:
        app_row = session.query(Application).filter_by(id=application_id).first()
        if app_row is None:
            return jsonify({"error": "Application not found"}), 404
        candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403
        app_row.status = status
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if status == "submitted" and app_row.sent_at is None:
            app_row.sent_at = now_ts
        if status in {"interview", "rejected", "withdrawn"} and app_row.outcome_at is None:
            app_row.outcome_at = now_ts
        session.commit()
        return jsonify({
            "id": app_row.id,
            "status": app_row.status,
            "sent_at": app_row.sent_at,
            "outcome_at": app_row.outcome_at,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/notes", methods=["PUT"])
def update_application_notes(application_id: int):
    """Set the freeform notes field for an application."""
    from db.session import get_session, init_db

    data = request.json or {}
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400

    init_db()
    session = get_session()
    try:
        app_row, _candidate = _load_application_owned(session, application_id)
        if app_row is None:
            return jsonify({"error": "Application not found"}), 404
        app_row.notes = notes.strip() or None
        session.commit()
        return jsonify({"id": app_row.id, "notes": app_row.notes})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/meta", methods=["PUT"])
def update_application_meta(application_id: int):
    """Set the user-editable title / company for an application (#24).

    DB-only (no filesystem path from the request), ownership-validated via
    `_load_application_owned` — the same pattern as `update_application_notes`.
    `title` is the model's NOT-NULL column: when provided it must be a non-empty
    string. `company` is optional; blank/whitespace clears it to NULL. Either
    field may be sent independently (save-on-blur).
    """
    from db.session import get_session, init_db

    data = request.json or {}
    if "title" in data and (not isinstance(data["title"], str) or not data["title"].strip()):
        return jsonify({"error": "title must be a non-empty string"}), 400
    if "company" in data and data["company"] is not None and not isinstance(data["company"], str):
        return jsonify({"error": "company must be a string or null"}), 400

    init_db()
    session = get_session()
    try:
        app_row, _candidate = _load_application_owned(session, application_id)
        if app_row is None:
            return jsonify({"error": "Application not found"}), 404
        if "title" in data:
            app_row.title = data["title"].strip()
        if "company" in data:
            company = data["company"]
            app_row.company = (company.strip() or None) if isinstance(company, str) else None
        session.commit()
        return jsonify({
            "id": app_row.id, "title": app_row.title, "company": app_row.company,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Workstream B: per-application Compose step (fit-ranked bullets/titles)
# ---------------------------------------------------------------------------


def _load_application_owned(session, application_id: int):
    """(app_row, candidate) for an application, or (None, None). Runs the
    standard _safe_username defense on the owning candidate."""
    from db.models import Application, Candidate
    app_row = session.query(Application).filter_by(id=application_id).first()
    if app_row is None:
        return None, None
    candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
    if candidate is None or not _safe_username(candidate.username):
        return None, None
    return app_row, candidate


def _latest_analysis_essentials(app_row) -> set[str]:
    """essential_skills from the application's most recent run, lowercased."""
    runs = sorted(app_row.runs, key=lambda r: r.iteration)
    for r in reversed(runs):
        if not r.analysis_json:
            continue
        try:
            analysis = json.loads(r.analysis_json)
        except (json.JSONDecodeError, TypeError):
            continue
        out: set[str] = set()
        for s in analysis.get("essential_skills", []) or []:
            out |= {w for w in re.split(r"[^a-z0-9]+", str(s).lower()) if len(w) > 2}
        return out
    return set()


def _read_composition_overrides(context_path: str) -> tuple[set[int], set[int]]:
    """(pinned, excluded) bullet-id sets from a context file, validated to
    live under OUTPUT_DIR. Empty sets when absent/invalid."""
    if not context_path:
        return set(), set()
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return set(), set()
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), set()
    ov = ctx.get("composition_overrides") or {}
    return set(ov.get("pinned", []) or []), set(ov.get("excluded", []) or [])


def _read_bullet_order(context_path: str) -> dict[int, list[int]]:
    """feat/bullet-drag-reorder — per-experience explicit bullet order from a
    context file's `composition_overrides.bullet_order`, validated within
    OUTPUT_DIR. Maps experience-id → ordered `[bullet_id, ...]`. Empty dict when
    absent/invalid. Keys and ids are coerced to int (JSON persists keys as
    strings); malformed entries are skipped, not fatal."""
    if not context_path:
        return {}
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return {}
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw = (ctx.get("composition_overrides") or {}).get("bullet_order") or {}
    out: dict[int, list[int]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[int(k)] = [int(x) for x in (v or [])]
            except (TypeError, ValueError):
                continue
    return out


def _read_title_overrides(context_path: str) -> dict[int, int]:
    """feat/compose-add-title — per-experience pinned title from a context
    file's `composition_overrides.pinned_title_ids`, validated within OUTPUT_DIR.
    Maps experience-id → chosen ExperienceTitle id. Empty dict when absent/invalid.
    Keys and ids are coerced to int (JSON persists keys as strings); malformed
    entries are skipped, not fatal."""
    if not context_path:
        return {}
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return {}
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw = (ctx.get("composition_overrides") or {}).get("pinned_title_ids") or {}
    out: dict[int, int] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[int(k)] = int(v)
            except (TypeError, ValueError):
                continue
    return out


def _read_experience_summary_overrides(
    context_path: str,
) -> tuple[dict[int, dict], dict[int, int], bool]:
    """B.4 (Sprint 6.6) — per-role intro state from a context file:
        (recs_by_exp, chosen_by_exp, use_experience_summaries)
    - recs_by_exp: experience-id → {summary_item_id, rationale, alternates}
      from `llm_experience_summary_recommendations.recommendations`.
    - chosen_by_exp: experience-id → chosen ExperienceSummaryItem id from
      `composition_overrides.chosen_experience_summary_ids`.
    - use_experience_summaries: the "Add role intros" toggle state.
    _within-gated by OUTPUT_DIR. Returns ({}, {}, False) on read/parse failure
    so the route degrades to "no role intros" rather than 500ing."""
    empty: tuple[dict[int, dict], dict[int, int], bool] = ({}, {}, False)
    if not context_path:
        return empty
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return empty
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty

    rec_block = ctx.get("llm_experience_summary_recommendations") or {}
    recs_by_exp: dict[int, dict] = {}
    if isinstance(rec_block, dict):
        for rec in (rec_block.get("recommendations") or []):
            if not isinstance(rec, dict):
                continue
            try:
                eid = int(rec.get("experience_id"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            recs_by_exp[eid] = rec

    overrides = ctx.get("composition_overrides") or {}
    raw_chosen = overrides.get("chosen_experience_summary_ids") or {}
    chosen_by_exp: dict[int, int] = {}
    if isinstance(raw_chosen, dict):
        for k, v in raw_chosen.items():
            try:
                chosen_by_exp[int(k)] = int(v)
            except (TypeError, ValueError):
                continue
    use_flag = bool(overrides.get("use_experience_summaries"))
    return recs_by_exp, chosen_by_exp, use_flag


def _read_skill_composition(
    context_path: str,
) -> tuple[set[int], set[int], list[int], list[int] | None]:
    """B.5 (Sprint 6.6) — skill curation state from a context file:
        (pinned_skill_ids, excluded_skill_ids, skill_order, recommended_ids)
    Reuses the deterministic corpus readers. _within-gated by OUTPUT_DIR;
    returns empties / None on read/parse failure so the Compose UI degrades to
    the default (all active+approved skills) rather than 500ing."""
    from corpus_to_json_resume import _read_skill_overrides, _read_skill_recommendations

    empty: tuple[set[int], set[int], list[int], list[int] | None] = (set(), set(), [], None)
    if not context_path:
        return empty
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return empty
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty
    pinned, excluded, order = _read_skill_overrides(ctx)
    rec_ids = _read_skill_recommendations(ctx)
    return pinned, excluded, order, rec_ids


def _read_summary_overrides(
    context_path: str,
) -> tuple[dict | None, int | None]:
    """β.6c — (summary_recommendation, pinned_summary_id) from the context.

    summary_recommendation is the dict persisted by
    /api/applications/<id>/recommend-summary (shape:
    {recommendation, alternates}), or None if not present.

    pinned_summary_id is the user's pin from composition_overrides
    (the override that wins over the LLM recommendation in the
    Compose UI), or None if no pin is set.

    _within-gated by OUTPUT_DIR. Returns (None, None) on read/parse
    failure so the route can degrade to "no recommendation, no pin"
    rather than 500ing.
    """
    if not context_path:
        return None, None
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return None, None
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    summary_rec = ctx.get("llm_summary_recommendation")
    raw = (ctx.get("composition_overrides") or {}).get("pinned_summary_id")
    try:
        pinned_id = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        pinned_id = None
    return (
        summary_rec if isinstance(summary_rec, dict) else None,
        pinned_id,
    )


def _read_recommendations_and_added(
    context_path: str,
) -> tuple[set[int], dict[int, dict]]:
    """(added bullet-id set, recommendations dict keyed by experience id).
    Reads `composition_overrides.added` and `llm_recommendations` from the
    context file. Empty / {} when absent. _within-gated by OUTPUT_DIR."""
    if not context_path:
        return set(), {}
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR) or not cp.exists():
        return set(), {}
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), {}
    added = set(int(x) for x in ((ctx.get("composition_overrides") or {}).get("added") or []))
    rec_by_exp: dict[int, dict] = {}
    for k, v in (ctx.get("llm_recommendations") or {}).items():
        try:
            eid = int(k)
        except (TypeError, ValueError):
            continue
        if isinstance(v, dict):
            rec_by_exp[eid] = {
                "bullet_ids": [int(b) for b in (v.get("bullet_ids") or [])],
                "rationale": (v.get("rationale") or "").strip(),
            }
    return added, rec_by_exp


@app.route("/api/applications/<int:application_id>/composition", methods=["GET"])
def get_application_composition(application_id: int):
    """Fit-ranked bullets + eligible titles for the Compose wizard step.

    Scores against the application's JD keywords + the latest run's
    analysis essential_skills, using the same `score_corpus_bullet`
    helper the iteration-0 snapshot pre-filter uses, so display order
    matches what the pipeline will favor. Pinned/excluded flags come from
    the context file's `composition_overrides` (query param
    `context_path`, validated within OUTPUT_DIR).
    """
    from db.build_context import _bullet_tag_values, score_corpus_bullet
    from db.models import Experience, ExperienceSummaryItem, Skill, SummaryItem
    from db.session import get_session, init_db
    from hardening import extract_keywords

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None:
            return jsonify({"error": "Application not found"}), 404

        jd_kw = set(extract_keywords(app_row.jd_text).get("keywords", {}).keys())
        essential = _latest_analysis_essentials(app_row)
        ctx_path = request.args.get("context_path", "")
        pinned, excluded = _read_composition_overrides(ctx_path)
        # feat/bullet-drag-reorder — explicit per-experience order, authoritative
        # over the score sort below when present for that experience.
        bullet_order = _read_bullet_order(ctx_path)
        # Workstreams H + I: surface llm_recommendations + composition_overrides.added
        # so the Compose UI can default to the curated set and mark drawer-added
        # bullets as included.
        added, rec_by_exp = _read_recommendations_and_added(ctx_path)
        # β.6c — pull the summary recommendation + pinned_summary_id
        # from the context (both optional). The UI renders a Positioning
        # card at the top with the LLM's pick flagged + any user pin
        # overriding it.
        summary_recommendation, pinned_summary_id = _read_summary_overrides(ctx_path)
        # feat/compose-add-title — per-experience title pin (experience_id →
        # ExperienceTitle id). Drives the title radio's selected state and the
        # per-experience chosen_title_id below.
        pinned_title_ids = _read_title_overrides(ctx_path)
        # B.4 — per-role intro recommendations + the user's per-role picks +
        # the "Add role intros" toggle state. Drives the per-experience
        # summary picker rendered inside each Compose experience card.
        (
            exp_summary_recs,
            exp_summary_chosen,
            use_experience_summaries,
        ) = _read_experience_summary_overrides(ctx_path)
        # B.5 — per-JD skill curation: recommend_skills ordering + pin/drop/
        # reorder overrides. Drives the Compose skill-curation card.
        (
            skill_pinned,
            skill_excluded,
            skill_order,
            skill_rec_ids,
        ) = _read_skill_composition(ctx_path)

        experiences = session.query(Experience).filter_by(
            candidate_id=candidate.id,
        ).order_by(Experience.start_date.desc(), Experience.id.desc()).all()

        out = []
        for exp in experiences:
            rec = rec_by_exp.get(exp.id, {})
            rec_ids = set(rec.get("bullet_ids", []))
            scored_bullets: list[dict[str, Any]] = []
            for b in exp.bullets:
                if not b.is_active:
                    continue
                tags = _bullet_tag_values(b)
                score = score_corpus_bullet(
                    b.text, bool(b.has_outcome), tags, jd_kw, essential,
                )
                scored_bullets.append({
                    "id": b.id, "text": b.text,
                    "score": round(score, 2),
                    "has_outcome": bool(b.has_outcome),
                    "is_pending_review": bool(b.is_pending_review),
                    "tags": _tag_list(b.tag_links),
                    "pinned": b.id in pinned,
                    "excluded": b.id in excluded,
                    "recommended": b.id in rec_ids,
                    "added": b.id in added,
                })
            scored_bullets.sort(
                key=lambda d: (
                    # Pinned and recommended sit at the top; excluded sink.
                    not (d["pinned"] or d["recommended"] or d["added"]),
                    -float(d["score"]),
                    int(d["id"]),
                ),
            )
            # feat/bullet-drag-reorder — when the user has saved an explicit
            # order for this experience, it is authoritative: listed bullets
            # take ranks 0..n-1, and a stable re-sort leaves unlisted (e.g.
            # newly drawer-added) bullets in the score order above, at the end.
            exp_order = bullet_order.get(exp.id)
            has_custom_order = bool(exp_order)
            if exp_order:
                rank = {bid: i for i, bid in enumerate(exp_order)}
                scored_bullets.sort(
                    key=lambda d: rank.get(int(d["id"]), len(rank)),
                )
                # Flag bullets that post-date the saved order (e.g. drawer-added
                # later) so the UI can show a "newly added — drag to reposition"
                # hint without silently re-sorting them in.
                order_set = set(exp_order)
                for d in scored_bullets:
                    d["in_custom_order"] = int(d["id"]) in order_set
            pinned_tid = pinned_title_ids.get(exp.id)
            titles: list[dict[str, Any]] = []
            for t in exp.titles:
                if not (t.is_official or t.truthful_enough_to_use):
                    continue
                t_toks = {
                    w for w in re.split(r"[^a-z0-9]+", t.title.lower())
                    if len(w) > 2
                }
                titles.append({
                    "id": t.id, "title": t.title,
                    "is_official": bool(t.is_official),
                    "score": round(
                        float(len(t_toks & (jd_kw | essential))), 2,
                    ),
                    "tags": _tag_list(t.tag_links),
                    # feat/compose-add-title — the user's per-JD pick for this JD.
                    "pinned": t.id == pinned_tid,
                })
            titles.sort(
                key=lambda d: (not d["is_official"], -float(d["score"]), int(d["id"])),
            )
            # feat/compose-add-title — what the résumé will actually use for this
            # experience: the user's pin (when still eligible) → official → the
            # top eligible title. Mirrors the preview/generate resolution so the
            # radio's default selection matches the rendered output.
            eligible_ids = {d["id"] for d in titles}
            if pinned_tid in eligible_ids:
                chosen_title_id: int | None = pinned_tid
            elif titles:
                chosen_title_id = titles[0]["id"]
            else:
                chosen_title_id = None

            # B.4 — per-role intro variants for this experience. The LLM
            # recommendation (if any) flags the "recommended" pick; the user's
            # per-role choice flags "chosen". Opt-in: nothing is chosen until
            # the user turns the toggle on and picks (the frontend seeds the
            # picks from the recommendation when they do).
            exp_rec = exp_summary_recs.get(exp.id, {})
            try:
                exp_rec_id: int | None = int(exp_rec.get("summary_item_id"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                exp_rec_id = None
            exp_chosen_id = exp_summary_chosen.get(exp.id)
            exp_alt_rationale: dict[int, str] = {}
            _rr = (exp_rec.get("rationale") or "").strip() if isinstance(exp_rec, dict) else ""
            if exp_rec_id is not None and _rr:
                exp_alt_rationale[exp_rec_id] = _rr
            for _a in (exp_rec.get("alternates") or []) if isinstance(exp_rec, dict) else []:
                try:
                    _aid = int(_a.get("summary_item_id", 0))
                except (TypeError, ValueError):
                    continue
                _ar = (_a.get("rationale") or "").strip()
                if _ar:
                    exp_alt_rationale[_aid] = _ar
            esi_rows = session.query(ExperienceSummaryItem).filter_by(
                experience_id=exp.id, is_active=1,
            ).order_by(
                ExperienceSummaryItem.display_order, ExperienceSummaryItem.id,
            ).all()
            role_summary_variants: list[dict[str, Any]] = []
            for esi in esi_rows:
                role_summary_variants.append({
                    "id": esi.id,
                    "text": esi.text,
                    "label": esi.label,
                    "has_outcome": bool(esi.has_outcome),
                    "recommended": esi.id == exp_rec_id,
                    "chosen": esi.id == exp_chosen_id,
                    "rationale": exp_alt_rationale.get(esi.id, ""),
                })

            if scored_bullets or titles or role_summary_variants:
                out.append({
                    "id": exp.id, "company": exp.company,
                    "start_date": exp.start_date, "end_date": exp.end_date,
                    "bullets": scored_bullets, "titles": titles,
                    "rationale": rec.get("rationale", ""),
                    "has_recommendations": bool(rec_ids),
                    # feat/bullet-drag-reorder — drives Reset enable/disable and
                    # the "newly added — drag to reposition" hint in the UI.
                    "has_custom_order": has_custom_order,
                    # feat/compose-add-title — the effective title for the radio's
                    # default selected state (pin → official → top eligible).
                    "chosen_title_id": chosen_title_id,
                    # B.4 — per-role intro picker payload.
                    "summary": {
                        "variants": role_summary_variants,
                        "recommended_id": exp_rec_id,
                        "chosen_id": exp_chosen_id,
                        "has_recommendation": exp_rec_id is not None,
                    },
                })
        # β.6c — Positioning block. Variants come from the candidate's
        # active SummaryItem rows; the LLM recommendation (if any) flags
        # the "recommended" pick; the user's pinned_summary_id overrides
        # what shows as selected.
        summary_variants: list[dict[str, Any]] = []
        rec = (summary_recommendation or {}).get("recommendation") or {}
        rec_id_raw = rec.get("summary_item_id")
        try:
            rec_id = int(rec_id_raw) if rec_id_raw is not None else None
        except (TypeError, ValueError):
            rec_id = None
        si_rows = session.query(SummaryItem).filter_by(
            candidate_id=candidate.id, is_active=1,
        ).order_by(SummaryItem.display_order, SummaryItem.id).all()
        for s in si_rows:
            summary_variants.append({
                "id": s.id,
                "text": s.text,
                "label": s.label,
                "has_outcome": bool(s.has_outcome),
                "recommended": s.id == rec_id,
                "pinned": s.id == pinned_summary_id,
            })
        # Surface alternates' rationales so the UI can show a tooltip
        # for each "Recommended" / alternate chip.
        alternates = (summary_recommendation or {}).get("alternates") or []
        alt_rationale: dict[int, str] = {}
        rec_rationale = (rec.get("rationale") or "").strip()
        if rec_id is not None and rec_rationale:
            alt_rationale[rec_id] = rec_rationale
        for a in alternates:
            try:
                a_id = int(a.get("summary_item_id", 0))
            except (TypeError, ValueError):
                continue
            r = (a.get("rationale") or "").strip()
            if r:
                alt_rationale[a_id] = r
        for sv in summary_variants:
            sv["rationale"] = alt_rationale.get(sv["id"], "")

        # The chosen variant for this application: pinned wins, else the
        # LLM recommendation, else null. Surfaces the user-effective
        # state without making the frontend re-derive it.
        chosen_summary_id = (
            pinned_summary_id if pinned_summary_id is not None else rec_id
        )

        # B.5 — Skills block. The universe is the candidate's active, approved
        # skills in display order; recommend_skills (if run) flags + orders the
        # recommended ones; pin/drop overrides ride along. `chosen_ids` is the
        # effective ordered set the résumé will surface (resolve_skill_selection,
        # the same logic the preview + generate prompt use). `pending` is the
        # llm_proposed suggestions awaiting approve/deny.
        from corpus_to_json_resume import resolve_skill_selection
        skill_rows = session.query(Skill).filter_by(
            candidate_id=candidate.id, is_active=1, is_pending_review=0,
        ).order_by(Skill.display_order, Skill.id).all()
        rec_rank = {sid: i for i, sid in enumerate(skill_rec_ids or [])}
        skill_items_out = [
            {
                "id": s.id, "name": s.name, "category": s.category,
                "tags": _tag_list(s.tag_links),
                "recommended": s.id in rec_rank,
                "recommended_rank": rec_rank.get(s.id),
                "pinned": s.id in skill_pinned,
                "excluded": s.id in skill_excluded,
            }
            for s in skill_rows
        ]
        chosen_skill_ids = resolve_skill_selection(
            all_active_ids=[s.id for s in skill_rows],
            rec_ids=skill_rec_ids,
            pinned=skill_pinned,
            excluded=skill_excluded,
            skill_order=skill_order,
        )
        pending_skill_rows = session.query(Skill).filter_by(
            candidate_id=candidate.id, is_active=1, is_pending_review=1,
        ).order_by(Skill.display_order, Skill.id).all()
        pending_skills_out = [
            {"id": s.id, "name": s.name, "category": s.category, "source": s.source}
            for s in pending_skill_rows
        ]

        return jsonify({
            "application_id": application_id,
            "experiences": out,
            "any_recommendations": any(e["has_recommendations"] for e in out),
            "summary": {
                "variants": summary_variants,
                "recommended_id": rec_id,
                "pinned_id": pinned_summary_id,
                "chosen_id": chosen_summary_id,
                "has_recommendation": rec_id is not None,
            },
            # B.4 — the "Add role intros" toggle state for this application.
            "use_experience_summaries": use_experience_summaries,
            # B.5 — skill curation payload for the Compose skill card.
            "skills": {
                "items": skill_items_out,
                "chosen_ids": chosen_skill_ids,
                "skill_order": skill_order,
                "has_recommendation": skill_rec_ids is not None,
                "pending": pending_skills_out,
            },
        })
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/composition", methods=["POST"])
def save_application_composition(application_id: int):
    """Persist pin/exclude/add overrides into the application's context file
    so the next generate() honors them. Body:
        {context_path, pinned[], excluded[], added[]}
    `added` (Workstream I) is bullet ids the user pulled in via the
    per-experience drawer; combined with `llm_recommendations` at
    prompt-build time to form the effective corpus the LLM sees.
    Writes back in place (same pattern as /api/answer-clarifications).
    Filesystem + ownership: _safe_username is enforced inside
    _load_application_owned; _within gates context_path."""
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    pinned = [int(x) for x in (data.get("pinned") or [])]
    excluded = [int(x) for x in (data.get("excluded") or [])]
    added = [int(x) for x in (data.get("added") or [])]
    # feat/bullet-drag-reorder — optional explicit per-experience bullet order
    # from the Compose drag/keyboard UI: {experience_id: [bullet_id, ...]}.
    # Persisted with string keys (JSON-natural); omitted when empty so the
    # default ordering (and the analyze→generate cache) is preserved. The
    # debounced autosave sends the FULL composition state on each save because
    # this route rebuilds composition_overrides wholesale.
    bullet_order_raw = data.get("bullet_order")
    bullet_order: dict[str, list[int]] = {}
    if bullet_order_raw is not None:
        if not isinstance(bullet_order_raw, dict):
            return jsonify({"error": "bullet_order must be an object of {experience_id: [bullet_id, ...]}"}), 400
        for k, v in bullet_order_raw.items():
            if not isinstance(v, list):
                return jsonify({"error": "bullet_order values must be arrays of bullet ids"}), 400
            try:
                bullet_order[str(int(k))] = [int(x) for x in v]
            except (TypeError, ValueError):
                return jsonify({"error": "bullet_order keys and ids must be integers"}), 400
    # β.6c — optional summary pin. The user explicitly chose this
    # variant for this application; it overrides the LLM
    # recommendation when generate() runs. None / 0 means "no pin"
    # → fall back to recommendation → fall back to candidate's
    # default profile_text.
    pinned_summary_raw = data.get("pinned_summary_id")
    pinned_summary_id: int | None = None
    if pinned_summary_raw is not None:
        try:
            v = int(pinned_summary_raw)
            pinned_summary_id = v if v > 0 else None
        except (TypeError, ValueError):
            return jsonify({"error": "pinned_summary_id must be a positive integer or null"}), 400

    # feat/compose-add-title — optional per-experience title pin:
    # {experience_id: title_id}. Persisted with string keys (JSON-natural,
    # like bullet_order); omitted when empty so the default path (and the
    # analyze→generate cache) is preserved. Eligibility + ownership are
    # validated against the DB inside the session block below.
    pinned_title_raw = data.get("pinned_title_ids")
    pinned_title_ids: dict[str, int] = {}
    if pinned_title_raw is not None:
        if not isinstance(pinned_title_raw, dict):
            return jsonify({"error": "pinned_title_ids must be an object of {experience_id: title_id}"}), 400
        for k, v in pinned_title_raw.items():
            try:
                pinned_title_ids[str(int(k))] = int(v)
            except (TypeError, ValueError):
                return jsonify({"error": "pinned_title_ids keys and ids must be integers"}), 400

    # B.4 (Sprint 6.6) — optional "Add role intros" opt-in toggle + per-role
    # intro picks: {experience_id: experience_summary_item_id}. Persisted with
    # string keys (JSON-natural, like pinned_title_ids). Both omitted when off /
    # empty so the default path (and the analyze→generate cache) is preserved.
    # The toggle gates whether picks are APPLIED; picks persist independently so
    # they're remembered if the user toggles back on. Ownership + activeness are
    # validated against the DB inside the session block below.
    use_experience_summaries = bool(data.get("use_experience_summaries"))
    chosen_exp_summary_raw = data.get("chosen_experience_summary_ids")
    chosen_experience_summary_ids: dict[str, int] = {}
    if chosen_exp_summary_raw is not None:
        if not isinstance(chosen_exp_summary_raw, dict):
            return jsonify({"error": "chosen_experience_summary_ids must be an object of {experience_id: item_id}"}), 400
        for k, v in chosen_exp_summary_raw.items():
            try:
                chosen_experience_summary_ids[str(int(k))] = int(v)
            except (TypeError, ValueError):
                return jsonify({"error": "chosen_experience_summary_ids keys and ids must be integers"}), 400

    # B.5 (Sprint 6.6) — skill curation overrides: pinned/excluded skill ids +
    # an explicit display order (skill_order). Each persisted only when
    # non-empty so the default path (and the analyze→generate cache) stays
    # byte-identical. Ownership/activeness validated against the DB below.
    try:
        skill_pinned_in = [int(x) for x in (data.get("pinned_skill_ids") or [])]
        skill_excluded_in = [int(x) for x in (data.get("excluded_skill_ids") or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "pinned_skill_ids / excluded_skill_ids must be integer ids"}), 400
    skill_order_raw = data.get("skill_order")
    skill_order_in: list[int] = []
    if skill_order_raw is not None:
        if not isinstance(skill_order_raw, list):
            return jsonify({"error": "skill_order must be an array of skill ids"}), 400
        try:
            skill_order_in = [int(x) for x in skill_order_raw]
        except (TypeError, ValueError):
            return jsonify({"error": "skill_order ids must be integers"}), 400

    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, OUTPUT_DIR) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # feat/compose-add-title — validate each pinned title is an eligible
        # (is_official OR truthful_enough_to_use) title of the named experience,
        # and that the experience belongs to this application's candidate. A bad
        # id is a 400, not a silent drop, so the UI can't pin a stale/foreign id.
        # `resynced_titles` caches the per-experience eligible set for the
        # snapshot re-sync further down (avoids a second DB pass).
        from db.build_context import eligible_titles_for
        from db.models import Experience, ExperienceSummaryItem, Skill
        resynced_titles: dict[str, Any] = {}
        for eid_str, tid in pinned_title_ids.items():
            exp = session.query(Experience).filter_by(
                id=int(eid_str), candidate_id=candidate.id,
            ).first()
            if exp is None:
                return jsonify({"error": f"experience {eid_str} not found for this candidate"}), 400
            eligible = eligible_titles_for(exp)
            if tid not in {t["id"] for t in eligible}:
                return jsonify({"error": f"title {tid} is not an eligible title of experience {eid_str}"}), 400
            resynced_titles[eid_str] = eligible

        # B.4 — validate each per-role intro pick is an active
        # ExperienceSummaryItem of an experience owned by this candidate. A bad
        # id is a 400 (not a silent drop) so the UI can't pin a stale/foreign id.
        # The sentinel 0 means "explicitly cleared — no intro for this role";
        # it's persisted (so it isn't re-defaulted on reload) but not validated.
        for eid_str, item_id in chosen_experience_summary_ids.items():
            if item_id == 0:
                continue
            exp = session.query(Experience).filter_by(
                id=int(eid_str), candidate_id=candidate.id,
            ).first()
            if exp is None:
                return jsonify({"error": f"experience {eid_str} not found for this candidate"}), 400
            row = session.query(ExperienceSummaryItem).filter_by(
                id=item_id, experience_id=exp.id, is_active=1,
            ).first()
            if row is None:
                return jsonify({"error": f"summary variant {item_id} is not an active intro of experience {eid_str}"}), 400

        # B.5 — validate pinned + ordered skill ids belong to this candidate's
        # active, approved skills. A foreign/stale id is a 400, not a silent
        # drop. Excluded is lenient (a stale exclusion is harmless — it just
        # excludes nothing).
        skill_ref_ids = set(skill_pinned_in) | set(skill_order_in)
        if skill_ref_ids:
            owned_skill_ids = {
                s.id for s in session.query(Skill).filter_by(
                    candidate_id=candidate.id, is_active=1, is_pending_review=0,
                ).all()
            }
            bad_skill_ids = skill_ref_ids - owned_skill_ids
            if bad_skill_ids:
                return jsonify({
                    "error": f"skill ids not owned/active: {sorted(bad_skill_ids)}",
                }), 400

        overrides: dict[str, Any] = {
            "pinned": pinned, "excluded": excluded, "added": added,
        }
        if pinned_summary_id is not None:
            overrides["pinned_summary_id"] = pinned_summary_id
        # B.4 — the toggle gates application; picks persist independently (so
        # they survive a toggle off→on). Both omitted when off/empty → default
        # generate prompt stays byte-identical.
        if use_experience_summaries:
            overrides["use_experience_summaries"] = True
        if chosen_experience_summary_ids:
            overrides["chosen_experience_summary_ids"] = chosen_experience_summary_ids
        # Only persist bullet_order when non-empty: a full reset (all
        # experiences back to AI ranking) omits the key → absent → fall back to
        # the score sort, keeping the default path byte-identical.
        if bullet_order:
            overrides["bullet_order"] = bullet_order
        if pinned_title_ids:
            overrides["pinned_title_ids"] = pinned_title_ids
        # B.5 — skill curation: each omitted when empty so the default skills
        # output (and the generate prompt's Skills line) stays byte-identical.
        if skill_pinned_in:
            overrides["pinned_skill_ids"] = skill_pinned_in
        if skill_excluded_in:
            overrides["excluded_skill_ids"] = skill_excluded_in
        if skill_order_in:
            overrides["skill_order"] = skill_order_in
        ctx["composition_overrides"] = overrides

        # feat/compose-add-title — generate reads the FROZEN career_corpus
        # snapshot (built at analyze), so a title added in Compose after analyze
        # isn't in it. Re-sync eligible_titles from the DB for exactly the pinned
        # experiences so the pin reaches generate. The preview is unaffected (it
        # reads the DB live). Guarded: corpus-mode contexts only.
        corpus = ctx.get("career_corpus")
        if pinned_title_ids and isinstance(corpus, list):
            for exp_entry in corpus:
                eid = exp_entry.get("id")
                key = str(eid) if eid is not None else None
                if key is not None and key in resynced_titles:
                    exp_entry["eligible_titles"] = resynced_titles[key]

        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify({
            "application_id": application_id,
            "pinned": pinned, "excluded": excluded, "added": added,
            "pinned_summary_id": pinned_summary_id,
            "bullet_order": bullet_order,
            "pinned_title_ids": pinned_title_ids,
            "use_experience_summaries": use_experience_summaries,
            "chosen_experience_summary_ids": chosen_experience_summary_ids,
            "pinned_skill_ids": skill_pinned_in,
            "excluded_skill_ids": skill_excluded_in,
            "skill_order": skill_order_in,
        })
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/recommend", methods=["POST"])
def recommend_application_bullets(application_id: int):
    """Workstream H: pick 3-7 bullets/experience via Haiku and stash them
    on the context file as `llm_recommendations`, so the Compose UI can
    render only the curated set by default.

    Body: {context_path}. Fired by the frontend right after a successful
    /api/analyze; the route is also re-runnable (overwrites the field).
    Failure (LLM error) returns the error to the caller; the Compose UI
    falls back to the deterministic fit-ranked top-5.

    Filesystem + ownership: _safe_username is enforced inside
    _load_application_owned; _within gates context_path.
    """
    from analyzer import LLMResponseError, recommend_bullets
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    # Wrapped with logger.exception + traceback in detail (2026-05-27) —
    # the recommend call is the upstream cause of "preview waiting on
    # curation" when it 500s, and the original handler only caught
    # APIConnectionError / LLMResponseError; anything else bubbled up
    # as a bare 500 with no traceback in the response. The wrapper makes
    # the actual exception visible in dev console + Flask log.
    try:
        init_db()
        session = get_session()
        try:
            app_row, candidate = _load_application_owned(session, application_id)
            if app_row is None or not _safe_username(candidate.username):
                return jsonify({"error": "Application not found"}), 404

            cp = Path(context_path)
            if not _within(cp, OUTPUT_DIR) or not cp.exists():
                return jsonify({"error": "Invalid context_path"}), 400
            try:
                ctx = json.loads(cp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return jsonify({"error": "Context file unreadable"}), 400
            if ctx.get("application_id") not in (None, application_id):
                return jsonify({"error": "context_path does not match application"}), 400

            # The recommend prompt wants the JD text; the context_set's
            # synthesized resume is the corpus markdown, not the JD. Stash the
            # JD from the DB application row into a transient key the
            # analyzer reads, then strip it before persisting.
            ctx["jd_text"] = app_row.jd_text
            run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
            try:
                result = recommend_bullets(
                    _get_client(), ctx,
                    username=candidate.username, run_id=run_id,
                )
            except anthropic.APIConnectionError as exc:
                logger.error("Recommend: Anthropic connection error: %s", exc)
                return jsonify({"error": "AI service connection failed"}), 503
            except LLMResponseError as exc:
                logger.error("Recommend: malformed LLM response: %s", exc.validation_error)
                return jsonify({
                    "error": "AI recommendation response was malformed",
                    "detail": str(exc.validation_error),
                }), 502

            # The recommend prompt explicitly tells the LLM "Use the numeric
            # ids only — do NOT prefix with 'e' or 'b'" (analyzer.py:1967),
            # but Sonnet sometimes echoes the corpus_block format back
            # ('e3' / 'b12'). Strip the prefix defensively before int() so
            # one bad row doesn't 500 the whole recommend run with
            # ValueError: invalid literal for int().
            def _to_int(v: object) -> int | None:
                if v is None:
                    return None
                s = str(v).strip().lstrip("eEbB")
                try:
                    return int(s)
                except (TypeError, ValueError):
                    logger.warning("recommend: dropping unparseable id %r", v)
                    return None

            by_exp: dict[str, dict] = {}
            for rec in result.get("recommendations", []) or []:
                eid_int = _to_int(rec.get("experience_id"))
                if eid_int is None:
                    continue
                bullet_ids_int = [bi for bi in (_to_int(b) for b in (rec.get("bullet_ids") or [])) if bi is not None]
                by_exp[str(eid_int)] = {
                    "bullet_ids": bullet_ids_int,
                    "rationale": (rec.get("rationale") or "").strip(),
                }
            ctx["llm_recommendations"] = by_exp
            ctx.pop("jd_text", None)  # transient; don't leak into iteration chain
            cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
            return jsonify({
                "application_id": application_id,
                "recommendations": by_exp,
            })
        finally:
            session.close()
    except Exception as exc:
        logger.exception("recommend_application_bullets failed for app=%s", application_id)
        return jsonify({
            "error": "Recommend failed",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/applications/<int:application_id>/recommend-summary", methods=["POST"])
def recommend_application_summary(application_id: int):
    """β.6b — pick the best SummaryItem variant for this application.

    Mirrors recommend_application_bullets's shape: Haiku call, persists
    to `context_set["llm_summary_recommendation"]`. Fires from the
    Compose step (β.6c) when the user enters that step; re-runnable
    (overwrites the field). Short-circuits without an LLM call when
    the candidate has 0 or 1 variants.

    Body: {context_path}. Filesystem + ownership: _safe_username via
    _load_application_owned; _within gates context_path.
    """
    from analyzer import LLMResponseError, recommend_summaries
    from db.models import SummaryItem
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, OUTPUT_DIR) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Load active SummaryItem variants for this candidate.
        rows = session.query(SummaryItem).filter_by(
            candidate_id=candidate.id, is_active=1,
        ).order_by(SummaryItem.display_order, SummaryItem.id).all()
        items = [
            {
                "id": r.id, "text": r.text, "label": r.label,
                "has_outcome": bool(r.has_outcome),
            }
            for r in rows
        ]

        # Stash transient context for the LLM call (matches the
        # recommend_bullets jd_text pattern). Strip before persisting.
        ctx["summary_items"] = items
        ctx["jd_text"] = app_row.jd_text
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = recommend_summaries(
                _get_client(), ctx,
                username=candidate.username, run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-summary: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Recommend-summary: malformed LLM response: %s", exc.validation_error)
            return jsonify({
                "error": "AI summary recommendation was malformed",
                "detail": str(exc.validation_error),
            }), 502

        # Persist + strip the transient keys
        ctx["llm_summary_recommendation"] = result
        ctx.pop("summary_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify({
            "application_id": application_id,
            **result,
        })
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/recommend-experience-summaries", methods=["POST"])
def recommend_application_experience_summaries(application_id: int):
    """B.4 (Sprint 6.6) — pick the best per-role intro variant for each role,
    batched. Mirrors recommend_application_summary: one Haiku call (via
    analyzer.recommend_experience_summaries), persists to
    context_set["llm_experience_summary_recommendations"]. Fires from the
    Compose step when the user turns on "Add role intros"; re-runnable
    (overwrites the field). Short-circuits without an LLM call when no role
    has 2+ active variants. The result only SUGGESTS — per-role intros are
    opt-in, so the UI seeds the per-role picks from this; nothing auto-applies.

    Body: {context_path}. Filesystem + ownership: _safe_username via
    _load_application_owned; _within gates context_path.
    """
    from analyzer import LLMResponseError, recommend_experience_summaries
    from db.models import Experience, ExperienceSummaryItem
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, OUTPUT_DIR) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Stage active ExperienceSummaryItem variants grouped per role. Roles
        # with no variants are omitted; recommend_experience_summaries
        # auto-picks single-variant roles and batches the rest into one call.
        experiences = session.query(Experience).filter_by(
            candidate_id=candidate.id,
        ).order_by(Experience.start_date.desc(), Experience.id.desc()).all()
        groups: list[dict[str, Any]] = []
        for exp in experiences:
            rows = session.query(ExperienceSummaryItem).filter_by(
                experience_id=exp.id, is_active=1,
            ).order_by(
                ExperienceSummaryItem.display_order, ExperienceSummaryItem.id,
            ).all()
            if not rows:
                continue
            groups.append({
                "experience_id": exp.id,
                "company": exp.company,
                "items": [
                    {
                        "id": r.id, "text": r.text, "label": r.label,
                        "has_outcome": bool(r.has_outcome),
                    }
                    for r in rows
                ],
            })

        # Stash transient context for the LLM call; strip before persisting.
        ctx["experience_summary_items"] = groups
        ctx["jd_text"] = app_row.jd_text
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = recommend_experience_summaries(
                _get_client(), ctx,
                username=candidate.username, run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-experience-summaries: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Recommend-experience-summaries: malformed LLM response: %s", exc.validation_error)
            return jsonify({
                "error": "AI role-summary recommendation was malformed",
                "detail": str(exc.validation_error),
            }), 502

        ctx["llm_experience_summary_recommendations"] = result
        ctx.pop("experience_summary_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify({
            "application_id": application_id,
            **result,
        })
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/recommend-skills", methods=["POST"])
def recommend_application_skills(application_id: int):
    """B.5 (Sprint 6.6) — order (and lightly curate) the candidate's skills for
    this JD via Haiku (analyzer.recommend_skills); persist to
    context["llm_skill_recommendations"]. Fired from the Compose step;
    re-runnable (overwrites the field). Selects only from the candidate's
    active, approved skills, so a pending/inactive skill can never be
    recommended. Short-circuits without an LLM call for 0 or 1 skills.

    Body: {context_path}. Filesystem + ownership: _safe_username via
    _load_application_owned; _within gates context_path.
    """
    from analyzer import LLMResponseError, recommend_skills
    from db.models import Skill
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, OUTPUT_DIR) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Stage active, approved skills (+ tag display values) for the matcher.
        rows = session.query(Skill).filter_by(
            candidate_id=candidate.id, is_active=1, is_pending_review=0,
        ).order_by(Skill.display_order, Skill.id).all()
        ctx["skill_items"] = [
            {
                "id": s.id, "name": s.name, "category": s.category,
                "tags": [
                    lnk.tag.display_value for lnk in s.tag_links
                    if lnk.tag and (lnk.tag.display_value or "").strip()
                ],
            }
            for s in rows
        ]
        ctx["jd_text"] = app_row.jd_text
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = recommend_skills(
                _get_client(), ctx,
                username=candidate.username, run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-skills: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Recommend-skills: malformed LLM response: %s", exc.validation_error)
            return jsonify({
                "error": "AI skill recommendation was malformed",
                "detail": str(exc.validation_error),
            }), 502

        ctx["llm_skill_recommendations"] = result
        ctx.pop("skill_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify({
            "application_id": application_id,
            **result,
        })
    finally:
        session.close()


@app.route("/api/applications/<int:application_id>/suggest-skills", methods=["POST"])
def suggest_application_skills(application_id: int):
    """B.5 (Sprint 6.6) — propose NEW canonical skills the JD wants AND the
    candidate's corpus evidences (analyzer.suggest_skills, grounded). Each
    proposal is inserted as a PENDING Skill (source='llm_proposed',
    is_pending_review=1) for the user to approve/deny; pending skills never
    reach the recommend set, the preview, or the generate prompt until
    approved — the human gate is the grounding backstop. Re-runnable; existing
    names (any state) are skipped so re-runs don't duplicate.

    Body: {context_path}. Filesystem + ownership: _safe_username via
    _load_application_owned; _within gates context_path.
    """
    from analyzer import LLMResponseError, suggest_skills
    from db.models import Skill
    from db.session import get_session, init_db

    data = request.json or {}
    context_path = (data.get("context_path") or "").strip()
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    init_db()
    session = get_session()
    try:
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, OUTPUT_DIR) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Existing skill names (any state) — for dedup + to tell the LLM what
        # the candidate already has so it doesn't re-propose them.
        all_rows = session.query(Skill).filter_by(candidate_id=candidate.id).all()
        existing_lower = {(s.name or "").strip().lower() for s in all_rows if (s.name or "").strip()}
        ctx["existing_skill_names"] = [s.name for s in all_rows if (s.name or "").strip()]
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = suggest_skills(
                _get_client(), ctx,
                username=candidate.username, run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Suggest-skills: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Suggest-skills: malformed LLM response: %s", exc.validation_error)
            return jsonify({
                "error": "AI skill suggestion was malformed",
                "detail": str(exc.validation_error),
            }), 502

        # Insert each grounded proposal as a pending skill. Dedup against
        # existing names (any state) AND within this batch; the unique
        # constraint is the final backstop.
        next_order = session.query(Skill).filter_by(candidate_id=candidate.id).count()
        created: list[dict[str, Any]] = []
        for p in (result.get("proposals") or []):
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
            created.append({
                **_skill_to_dict(sk, []),
                "evidence": p.get("evidence"),
                "rationale": p.get("rationale"),
            })
            next_order += 1
        session.commit()
        return jsonify({
            "application_id": application_id,
            "proposals": created,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase D.5: Candidate Memory list route
# ---------------------------------------------------------------------------


@app.route("/api/users/<username>/clarifications", methods=["GET"])
def list_clarifications(username: str):
    """Return the candidate's clarification history.

    Query params:
      q=<substring>            optional case-insensitive match against
                               question OR answer text
      kind=<kind>              filter by clarification.kind
      only_outcome_rich=1      filter to answers matching METRIC_RE
                               (the "promote candidates" view)
      include_promoted=1       by default suppresses already-promoted rows
      limit=<n>                max rows (default 200, hard cap 1000)
    """
    from db.models import Application, Candidate, Clarification
    from db.session import get_session, init_db
    from hardening import METRIC_RE

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    q = (request.args.get("q") or "").strip().lower()
    kind = request.args.get("kind")
    only_outcome_rich = request.args.get("only_outcome_rich") == "1"
    include_promoted = request.args.get("include_promoted") == "1"
    limit = min(int(request.args.get("limit", 200)), 1000)
    valid_kinds = {
        "experience_probe", "scope_probe", "iteration_probe",
        "outcome_probe", "manual",
    }
    if kind and kind not in valid_kinds:
        return jsonify({"error": f"kind must be one of {sorted(valid_kinds)}"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            # Read precondition unmet → 200 + flag, not 409 (see
            # list_user_personas). Success shape is a bare array.
            return jsonify({"clarifications": [], "needs_onboarding": True})

        query = session.query(Clarification).filter_by(candidate_id=candidate.id)
        if not include_promoted:
            query = query.filter(Clarification.is_promoted_to_bullet == 0)
        if kind:
            query = query.filter(Clarification.kind == kind)
        rows = query.order_by(Clarification.created_at.desc()).limit(limit).all()

        # Resolve origin application titles in one batch so the UI can label
        # each clarification by its origin without N+1 queries.
        app_ids = [r.origin_application_id for r in rows if r.origin_application_id]
        app_title_by_id: dict[int, str] = {}
        if app_ids:
            for app_row in session.query(Application).filter(
                Application.id.in_(app_ids),
            ).all():
                app_title_by_id[app_row.id] = app_row.title

        out = []
        for r in rows:
            if q and (q not in r.question.lower() and q not in r.answer.lower()):
                continue
            outcome_rich = bool(METRIC_RE.search(r.answer))
            if only_outcome_rich and not outcome_rich:
                continue
            out.append({
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "kind": r.kind,
                "target_gap": r.target_gap,
                "is_promoted_to_bullet": bool(r.is_promoted_to_bullet),
                "outcome_rich": outcome_rich,
                "origin_application_id": r.origin_application_id,
                "origin_application_title":
                    app_title_by_id.get(r.origin_application_id) if r.origin_application_id else None,
                "origin_run_id": r.origin_run_id,
                "created_at": r.created_at,
            })
        return jsonify(out)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Annotation + bootstrap write surface (the console's first READ-WRITE routes).
#
# Localhost-only, keyed by a real candidate username + a fixture slug, writing
# ONLY under ANNOTATION_ROOT (evals/fixtures/real/). The annotation contract +
# bootstrap collation are reused verbatim from evals.annotation / evals.bootstrap
# (deterministic, LLM-free) — these routes are the thin Flask seam. The UI lives
# in the /_dashboard "Annotate" tab; the dashboard blueprint itself stays
# read-only. Security pattern per CLAUDE.md "Key Patterns — Security":
# _safe_username() + secure_filename() + _within().
# ---------------------------------------------------------------------------


def _annotation_fixture_path(slug: str) -> Path | None:
    """Sanitize a fixture slug into a dir path under ANNOTATION_ROOT.

    Returns None when the slug sanitizes to empty. Does NOT check containment —
    every caller MUST still apply `_within(path, ANNOTATION_ROOT)` (the gate is
    kept visible in each route per the security pattern).
    """
    safe = secure_filename(slug or "")
    if not safe:
        return None
    return ANNOTATION_ROOT / safe


def _load_bootstrap_doc(fixture_dir: Path) -> dict | None:
    """Read a fixture's bootstrap.json. None if absent or malformed."""
    bootstrap_path = fixture_dir / "bootstrap.json"
    if not bootstrap_path.exists():
        return None
    try:
        return json.loads(bootstrap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_seed_json(fixture_dir: Path, seed: dict) -> Path:
    """Canonical writer for a fixture's seed.json corpus snapshot.

    The single source of the dump format, shared by the paid bootstrap route (which
    captures the seed as a side effect of the run) and the standalone export route.
    The caller owns the `_within` containment check + `fixture_dir.mkdir`.
    """
    seed_path = fixture_dir / "seed.json"
    seed_path.write_text(
        json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    return seed_path


def _patch_annotation_scores(ann_path: Path, grounding_signals: dict) -> int:
    """Patch ONLY the inline grounding score fields onto an existing annotations.json.

    Joins the freshly-computed nli/minicheck lists to each bullet by cluster_index
    (the same index alignment ``build_annotation_template`` uses) and overwrites the
    three score fields, leaving every human-entered verdict / note / rewrite intact.
    Returns the number of bullet items patched. Best-effort: a malformed file is left
    untouched (returns 0). Does NOT re-validate — an in-progress annotations.json is
    intentionally incomplete and must not be rejected by a score backfill.
    """
    try:
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(doc, dict):
        return 0
    nli_list = grounding_signals.get("nli", []) or []
    mc_list = grounding_signals.get("minicheck", []) or []
    patched = 0
    for item in doc.get("bullets", []) or []:
        if not isinstance(item, dict):
            continue
        idx = item.get("cluster_index")
        if not isinstance(idx, int):
            continue
        changed = False
        if 0 <= idx < len(nli_list):
            item["nli_entailment_score"] = nli_list[idx].get("nli_entailment_score")
            item["nli_contradiction_flag"] = nli_list[idx].get("nli_contradiction_flag")
            changed = True
        if 0 <= idx < len(mc_list):
            item["minicheck_grounding_score"] = mc_list[idx].get("minicheck_grounding_score")
            changed = True
        if changed:
            patched += 1
    if patched:
        ann_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return patched


@app.route("/api/annotation/fixtures", methods=["GET"])
def annotation_fixtures():
    """List bootstrap fixtures under ANNOTATION_ROOT (localhost-only, read-only).

    Reads only the fixed ANNOTATION_ROOT tree (no user-supplied path), so there is
    no traversal vector here; the localhost guard is the access control.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    fixtures = []
    if ANNOTATION_ROOT.exists():
        for entry in sorted(ANNOTATION_ROOT.iterdir()):
            if not entry.is_dir():
                continue
            doc = _load_bootstrap_doc(entry)
            if doc is None:
                continue
            dedup = doc.get("dedup", {}) or {}
            fixtures.append({
                "slug": entry.name,
                "candidate_username": doc.get("candidate_username", ""),
                "prompt_version": doc.get("prompt_version", ""),
                "jd_count": doc.get("jd_count", 0),
                "bullet_clusters": (dedup.get("bullets", {}) or {}).get("cluster_count", 0),
                "skill_clusters": (dedup.get("skills", {}) or {}).get("cluster_count", 0),
                "has_annotations": (entry / "annotations.json").exists(),
                "has_expected": (entry / "expected.json").exists(),
            })
    return jsonify({"fixtures": fixtures})


@app.route("/api/annotation/fixture/<username>/<slug>", methods=["GET"])
def annotation_load(username: str, slug: str):
    """Return the working annotations doc for a fixture (localhost-only, read).

    Existing annotations.json if present, else a blank template built from the
    bootstrap (`build_annotation_template`). Also returns the verdict +
    failed_rules vocabulary so the UI can render constrained controls.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug)
    if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404

    from evals.annotation import (
        ALLOWED_FAILED_RULES,
        VERDICTS,
        build_annotation_template,
    )

    ann_path = fixture_dir / "annotations.json"
    if ann_path.exists():
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
    else:
        doc = build_annotation_template(
            bootstrap, bootstrap_source=str(fixture_dir / "bootstrap.json"),
        )
    return jsonify({
        "annotations": doc,
        "has_annotations": ann_path.exists(),
        "vocab": {
            "verdicts": sorted(VERDICTS),
            "failed_rules": sorted(ALLOWED_FAILED_RULES),
        },
    })


@app.route("/api/annotation/fixture/<username>/<slug>", methods=["POST"])
def annotation_save(username: str, slug: str):
    """Write a completed annotations.json (localhost-only, fail-closed).

    Validation is `evals.annotation.validate_annotations` — the SAME fail-closed
    contract the CLI uses, so the on-disk file is always collation-ready (every
    bullet/skill has a verdict; fix→honest_rewrite; fabricated→compilable
    forbidden_pattern). An incomplete doc is rejected with the validator message.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug)
    if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400
    if not (fixture_dir / "bootstrap.json").exists():
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404
    doc = request.get_json(silent=True)
    if not isinstance(doc, dict):
        return jsonify({"error": "Request body must be a JSON annotations object"}), 400

    from evals.annotation import validate_annotations

    try:
        validate_annotations(doc)
    except ValueError as exc:
        return jsonify({"error": "Annotations failed validation", "detail": str(exc)}), 400

    fixture_dir.mkdir(parents=True, exist_ok=True)
    out_path = fixture_dir / "annotations.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Saved annotations for fixture %s (%d bullets, %d skills)",
                slug, len(doc.get("bullets", [])), len(doc.get("skills", [])))
    return jsonify({
        "ok": True,
        "path": str(out_path),
        "bullets": len(doc.get("bullets", [])),
        "skills": len(doc.get("skills", [])),
    })


@app.route("/api/annotation/fixture/<username>/<slug>/collate", methods=["POST"])
def annotation_collate(username: str, slug: str):
    """Collate a saved annotations.json → expected.json + improvement_brief.md.

    Deterministic, LLM-free: reuses `collate_expected` + `build_improvement_brief`
    + `pick_anchor_jd`. Writes the fixture artifacts beside the bootstrap, plus a
    `jd.txt` copied from the saved `jds/<anchor>` (the wrapper stores pasted JDs
    there) so the produced fixture is runnable by `runner.py --suite real`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug)
    if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404
    ann_path = fixture_dir / "annotations.json"
    if not ann_path.exists():
        return jsonify({"error": "Save annotations before collating"}), 400

    from evals.annotation import (
        build_improvement_brief,
        collate_expected,
        pick_anchor_jd,
        validate_annotations,
    )

    annotations = json.loads(ann_path.read_text(encoding="utf-8"))
    try:
        validate_annotations(annotations)
    except ValueError as exc:
        return jsonify({"error": "Annotations failed validation", "detail": str(exc)}), 400

    expected = collate_expected(annotations, bootstrap)
    brief = build_improvement_brief(annotations, bootstrap)

    # Anchor JD text → jd.txt (best-effort; the wrapper saves pasted JDs in jds/).
    anchor_name = pick_anchor_jd(bootstrap)
    anchor_src = (fixture_dir / "jds" / secure_filename(anchor_name)) if anchor_name else None
    jd_written = False
    if (anchor_src is not None and _within(anchor_src, ANNOTATION_ROOT)
            and anchor_src.exists()):
        (fixture_dir / "jd.txt").write_text(
            anchor_src.read_text(encoding="utf-8"), encoding="utf-8",
        )
        jd_written = True

    expected_path = fixture_dir / "expected.json"
    brief_path = fixture_dir / "improvement_brief.md"
    expected_path.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    brief_path.write_text(brief, encoding="utf-8")
    logger.info("Collated fixture %s: %d must_keywords, %d forbidden_inventions",
                slug, len(expected.get("must_keywords", [])),
                len(expected.get("forbidden_inventions", [])))
    return jsonify({
        "ok": True,
        "expected_path": str(expected_path),
        "brief_path": str(brief_path),
        "jd_written": jd_written,
        "anchor_jd": anchor_name,
        "must_keywords": len(expected.get("must_keywords", [])),
        "forbidden_inventions": len(expected.get("forbidden_inventions", [])),
        "run_command": (
            f"python evals/runner.py --suite real --seed "
            f"evals/fixtures/real/{secure_filename(slug)}/seed.json"
        ),
    })


@app.route("/api/annotation/fixture/<username>/<slug>/score", methods=["POST"])
def annotation_score_grounding(username: str, slug: str):
    """Backfill grounding pre-scores onto an existing bootstrap.json (localhost, SSE).

    Runs the offline grounding scorers (DeBERTa NLI + MiniCheck-FT5) over the deduped
    bullet-cluster representatives, scoring against the corpus the bootstrap was built
    from — recovered by importing the fixture's `seed.json` into a throwaway in-memory
    SQLite (no live-DB writes) and synthesizing the same résumé text the pipeline saw.
    Writes the result back under `grounding_signals` and patches any existing
    annotations.json score fields. NO paid LLM calls — pure CPU work on already-generated
    bullets — so a user who bootstrapped *before* installing the `[eval-grounding]` extras
    can light up the annotation editor without re-running the (paid) pipeline. Streams
    `start` / `scoring` / `done` / `error`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug)
    if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404

    seed_path = fixture_dir / "seed.json"
    if not seed_path.exists():
        return jsonify({
            "error": "No seed.json for this fixture — re-run the bootstrap to capture the "
                     "corpus snapshot, then score.",
        }), 409

    clusters = ((bootstrap.get("dedup", {}) or {}).get("bullets", {}) or {}).get("clusters", []) or []
    if not clusters:
        return jsonify({"error": "Bootstrap has no bullet clusters to score"}), 400

    # grounding_signals is pure-Python (heavy deps import lazily inside the scorer),
    # so this import always succeeds; a missing `[eval-grounding]` extra surfaces as
    # an ImportError when the scorer runs (handled in the worker below).
    from evals.grounding_signals import run_grounding_signals

    # Score against the corpus this bootstrap was built from: import its seed.json
    # into a throwaway in-memory SQLite (no live-DB writes, no Application anchor on
    # the real DB) and synthesize the same résumé text the pipeline saw. This stays
    # faithful even if the live corpus was edited since the bootstrap ran.
    try:
        from db.build_context import build_context_set_from_db
        from evals.seed_import import seeded_session
        with seeded_session(seed_path) as (seed_session, seed_user):
            ctx, _app, _run = build_context_set_from_db(
                seed_session, candidate_username=seed_user,
                jd_text="(grounding backfill)", run_id="grounding-backfill",
            )
            corpus_source = (ctx["resume"]["text"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Grounding backfill: could not read corpus from seed for %s: %s", slug, exc)
        return jsonify({"error": "Could not read corpus from seed.json", "detail": str(exc)}), 500
    if not corpus_source:
        return jsonify({"error": "Corpus snapshot is empty — nothing to score against"}), 400

    # Render representatives exactly as build_bootstrap_document does, so the
    # returned nli/minicheck lists stay index-aligned with dedup.bullets.clusters.
    reps_md = "\n".join(f"- {c.get('representative', '')}" for c in clusters)
    bootstrap_path = fixture_dir / "bootstrap.json"
    ann_path = fixture_dir / "annotations.json"

    def stream():
        import queue as _queue
        import threading

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker():
            try:
                result["gs"] = run_grounding_signals(reps_md, [corpus_source])
            except ImportError as exc:
                result["import_error"] = exc
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {"slug": slug, "bullet_clusters": len(clusters)})
        yield _sse("scoring", {
            "message": f"Scoring {len(clusters)} bullet clusters (DeBERTa NLI + MiniCheck, "
                       "~2-4s each)…",
        })

        # Single scorer call (no incremental progress) — block until the worker is done.
        while events.get() is not sentinel:
            pass

        if "import_error" in result:
            logger.warning("Grounding backfill: extras not installed for %s: %s",
                           slug, result["import_error"])
            yield _sse("error", {
                "error": "Grounding extras not installed.",
                "detail": "Install with: pip install -e '.[eval-grounding]' (see CONTRIBUTING.md).",
                "http_status": 400,
            })
            return
        if "error" in result:
            logger.error("Grounding backfill failed for %s: %s", slug, result["error"],
                         exc_info=result["error"])
            yield _sse("error", {
                "error": "Grounding scoring failed.",
                "detail": str(result["error"]),
                "http_status": 500,
            })
            return

        gs = result["gs"]
        bootstrap["grounding_signals"] = gs
        bootstrap_path.write_text(
            json.dumps(bootstrap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
        patched = _patch_annotation_scores(ann_path, gs) if ann_path.exists() else 0
        bullet_count = gs.get("bullet_count", 0)
        logger.info("Grounding backfill wrote %s (%d bullets scored, %d annotations patched)",
                    slug, bullet_count, patched)
        yield _sse("done", {
            "slug": slug,
            "bullet_count": bullet_count,
            "mean_entailment": (gs.get("nli_summary", {}) or {}).get("mean_entailment", 0.0),
            "mean_minicheck": (gs.get("minicheck_summary", {}) or {}).get("mean_score", 0.0),
            "annotations_patched": patched,
        })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/annotation/seed/export", methods=["POST"])
def annotation_seed_export():
    """Export one candidate's corpus to seed.json — deterministic, LLM-free (localhost).

    The no-cost counterpart to the paid bootstrap's seed snapshot: reads the LIVE DB
    via `scripts.export_corpus_seed.export_seed` (read-only, no model calls) and writes
    `<ANNOTATION_ROOT>/<slug>/seed.json` through the shared `_write_seed_json` helper.
    Lets a user capture a corpus seed for the eval runner (`--seed`) / grounding backfill
    without paying for a bootstrap. Fast + synchronous, so a plain JSON response (no SSE).
    Security per CLAUDE.md "Key Patterns — Security": _safe_username() + secure_filename()
    + _within(seed_path, ANNOTATION_ROOT).
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}
    safe_user = _safe_username(data.get("username", ""))
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    slug = secure_filename(data.get("slug") or f"{safe_user}-bootstrap")
    if not slug:
        return jsonify({"error": "Invalid fixture slug"}), 400
    fixture_dir = _annotation_fixture_path(slug)
    if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400
    seed_path = fixture_dir / "seed.json"
    if not _within(seed_path, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400

    from db.session import get_session, init_db
    from scripts.export_corpus_seed import export_seed

    init_db()
    session = get_session()
    try:
        seed = export_seed(session, candidate_username=safe_user)
    except ValueError as exc:
        # Config exists (passed _safe_username) but no Candidate corpus row yet —
        # same needs-onboarding shape as /api/analyze. Distinct from the 400 above.
        return jsonify({
            "error": "No corpus for this user yet — import a résumé / build the corpus first.",
            "detail": str(exc),
        }), 409
    finally:
        session.close()

    fixture_dir.mkdir(parents=True, exist_ok=True)
    _write_seed_json(fixture_dir, seed)

    n_bullets = sum(len(e["bullets"]) for e in seed["experiences"])
    logger.info(
        "Seed export wrote %s/seed.json (%d experiences, %d bullets)",
        slug, len(seed["experiences"]), n_bullets,
    )
    return jsonify({
        "ok": True,
        "slug": slug,
        "candidate": safe_user,
        "experiences": len(seed["experiences"]),
        "bullets": n_bullets,
        "summary_items": len(seed["summary_items"]),
        "skills": len(seed["skills"]),
        "path": f"evals/fixtures/real/{slug}/seed.json",
    })


@app.route("/api/annotation/bootstrap", methods=["POST"])
def annotation_bootstrap_stream():
    """Browser bootstrap wrapper — run the live pipeline over N pasted JDs (SSE).

    Reuses the streaming pattern of /api/analyze/stream and the analyzer
    primitives (via evals.bootstrap.run_pipeline_over_jd_texts — analyze → clarify
    → generate per JD against the LIVE corpus), then the deterministic
    `build_bootstrap_document` dedup, writing bootstrap.json + a seed.json corpus
    snapshot + the pasted JDs under ANNOTATION_ROOT/<slug>/. PAID (Sonnet/Haiku) +
    slow (~70s/JD). With `grounding_signals: true` it also runs the offline grounding
    scorers over the deduped bullets (eval-only models; degrades to an un-scored
    bootstrap + `warning` if the `[eval-grounding]` extras are missing). Progress
    streams as `start` / per-JD `jd_start`/`analyzing`/`clarifying`/`generating`/
    `jd_done` / optional `scoring` / optional `warning` / `done` / `error` events.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    # Opt-in: run the offline grounding scorers (DeBERTa NLI + MiniCheck-FT5) over
    # the deduped bullet representatives. Eval-only models (~3.2 GB, ~2-4 s/bullet),
    # gated by the same `[eval-grounding]` extras the CLI `--grounding-signals` uses.
    # Missing extras or a runtime scoring failure degrades to an un-scored bootstrap
    # with a warning event — never a 500 (the paid pipeline output is preserved).
    grounding_requested = bool(data.get("grounding_signals"))

    raw_jds = data.get("jds", [])
    jds: list[tuple[str, str]] = []
    for item in raw_jds if isinstance(raw_jds, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        text = str(item.get("text", "")).strip()
        if name and text:
            jds.append((name, text))
    if not jds:
        return jsonify({"error": "Provide at least one JD as {name, text}"}), 400

    slug = secure_filename(data.get("slug") or f"{safe_user}-bootstrap")
    if not slug:
        return jsonify({"error": "Invalid fixture slug"}), 400
    fixture_dir = ANNOTATION_ROOT / slug
    if not _within(fixture_dir, ANNOTATION_ROOT):
        return jsonify({"error": "Invalid fixture slug"}), 400

    from evals.bootstrap import (
        DEFAULT_JACCARD,
        build_bootstrap_document,
        run_pipeline_over_jd_texts,
    )
    from scripts.export_corpus_seed import export_seed

    client = _get_client()

    def stream():
        import queue as _queue
        import threading

        from db.session import get_session, init_db

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker():
            try:
                init_db()
                session = get_session()
                try:
                    per_jd, corpus = run_pipeline_over_jd_texts(
                        client, session, safe_user, jds,
                        progress=lambda ev, payload: events.put(("progress", ev, payload)),
                    )
                    result["per_jd"] = per_jd
                    result["corpus"] = corpus
                    # Snapshot the entire approved corpus to a seed.json (read-only,
                    # LLM-free) while the live session is open. This is the durable
                    # source of truth the downstream eval (`runner.py --seed`) and the
                    # grounding backfill score against — and the file collate's
                    # `--seed` run-command already references. Non-fatal: a snapshot
                    # failure must never discard the (paid) pipeline output.
                    try:
                        result["seed"] = export_seed(session, candidate_username=safe_user)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Could not export seed.json for %s: %s", safe_user, exc)
                        result["seed"] = None
                finally:
                    session.close()
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {"total": len(jds), "slug": slug, "candidate": safe_user})

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Bootstrap wrapper failed: %s", result["error"], exc_info=result["error"])
            yield _sse("error", {
                "error": "Bootstrap pipeline failed.",
                "detail": str(result["error"]),
                "http_status": 500,
            })
            return

        # Optional grounding scorers (eval-only models), resolved AFTER the paid
        # pipeline so a missing dep never wastes the LLM spend. The grounding_signals
        # module is pure-Python (the heavy deps import lazily inside the scorer), so
        # the import here always succeeds; a missing `[eval-grounding]` extra surfaces
        # as an ImportError at build time below — caught and degraded to an un-scored
        # bootstrap + warning, never a 500 (the paid pipeline output is preserved).
        grounding_fn = None
        grounding_note = None
        if grounding_requested:
            from evals.grounding_signals import run_grounding_signals
            grounding_fn = run_grounding_signals
            yield _sse("scoring", {
                "message": "Running grounding scorers (DeBERTa NLI + MiniCheck) over "
                           "deduped bullets — this is CPU-bound (~2-4s/bullet)…",
            })

        def _collate(gf):
            return build_bootstrap_document(
                result["per_jd"],
                username=safe_user,
                seed_path="(browser bootstrap wrapper)",
                threshold=DEFAULT_JACCARD,
                corpus_source=result.get("corpus", ""),
                grounding_fn=gf,
            )

        # Deterministic collation + write (LLM-free apart from the optional scorers).
        try:
            doc = _collate(grounding_fn)
        except ImportError as exc:
            logger.warning("Grounding extras missing; saving bootstrap without scores: %s", exc)
            grounding_note = (
                "Grounding extras not installed — bootstrap saved without scores. "
                "Install with: pip install -e '.[eval-grounding]' (see CONTRIBUTING.md)."
            )
            doc = _collate(None)
        except Exception as exc:  # noqa: BLE001
            # Scoring blew up (e.g. model download failed) — re-collate without it
            # so the expensive pipeline output is never lost.
            logger.warning("Grounding scoring failed; saving bootstrap without scores: %s", exc)
            grounding_note = f"Grounding scoring failed ({exc}); bootstrap saved without scores."
            doc = _collate(None)
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "bootstrap.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
        # Persist the corpus snapshot so the fixture is runnable by
        # `runner.py --suite real --seed …/seed.json` and so the grounding backfill
        # can score against the exact corpus this bootstrap was built from.
        seed = result.get("seed")
        if seed is not None:
            _write_seed_json(fixture_dir, seed)
        # Persist the pasted JDs so collate can later produce the fixture jd.txt.
        jds_dir = fixture_dir / "jds"
        jds_dir.mkdir(parents=True, exist_ok=True)
        for name, text in jds:
            safe_name = secure_filename(name) or "jd"
            if not safe_name.endswith(".txt"):
                safe_name = f"{safe_name}.txt"
            jd_file = jds_dir / safe_name
            if _within(jd_file, ANNOTATION_ROOT):
                jd_file.write_text(text, encoding="utf-8")
        grounded = doc.get("grounding_signals") is not None
        logger.info("Bootstrap wrapper wrote %s (%d JDs, %d bullet clusters, grounded=%s)",
                    slug, doc["jd_count"], doc["dedup"]["bullets"]["cluster_count"], grounded)
        if grounding_note:
            yield _sse("warning", {"message": grounding_note})
        yield _sse("done", {
            "slug": slug,
            "candidate": safe_user,
            "jd_count": doc["jd_count"],
            "bullet_clusters": doc["dedup"]["bullets"]["cluster_count"],
            "skill_clusters": doc["dedup"]["skills"]["cluster_count"],
            "grounded": grounded,
        })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/eval/run", methods=["POST"])
def eval_run_stream():
    """Run an eval suite from the console (localhost-only, SSE).

    The browser counterpart to `python evals/runner.py …`: drives the extracted
    `evals.runner.run_suite` in a worker thread and streams coarse progress so the
    paid wait reads as alive. Two modes:
      • Quality "Run eval": {suite, subset, grounding_signals} → the committed
        synthetic/anchor fixtures (no corpus seed).
      • Annotate "Run this fixture": {suite:"real", fixture:<slug>, slug:<slug>,
        username:<candidate>} → resolve evals/fixtures/real/<slug>/seed.json and run
        that one fixture against its corpus — the collate `--seed` command, in-browser.

    PAID (Sonnet + Haiku): ~$0.10 smoke / ~$0.30 full per the runner's cost table;
    the UI shows a cost-band confirm() before POSTing. Streams `start` /
    `fixture_start` / `analyzing` / `clarifying` / `generating` / `rubric_done` /
    `fixture_done` / `done` / `error`. All eager validation (bad suite / unknown
    user / missing seed) returns a JSON 4xx BEFORE the worker spends anything.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}

    suite = str(data.get("suite", "synthetic"))
    if suite not in {"synthetic", "real", "all", "anchor", "exploration"}:
        return jsonify({"error": f"Invalid suite: {suite}"}), 400
    subset = "smoke" if str(data.get("subset", "full")) == "smoke" else "full"
    grounding_signals = bool(data.get("grounding_signals"))

    # Optional single-fixture scope (e.g. the collated <slug>). Sanitize with
    # secure_filename: it feeds FIXTURES_DIR/<suite>/<fixture> in run_suite, a
    # traversal-sensitive path join.
    raw_fixture = str(data.get("fixture", "")).strip()
    fixture_name = secure_filename(raw_fixture) if raw_fixture else None

    # Optional corpus-seed mode (the Annotate "Run this fixture" button). The seed
    # lives under ANNOTATION_ROOT/<slug>/seed.json (gitignored, PII-bearing). Resolve
    # + contain it and confirm the candidate user exists, all before any paid call.
    seed_data: dict | None = None
    raw_slug = str(data.get("slug", "")).strip()
    if raw_slug:
        safe_user = _safe_username(str(data.get("username", "")))
        if not safe_user:
            return jsonify({"error": "Invalid or unknown user"}), 400
        fixture_dir = _annotation_fixture_path(raw_slug)
        if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
            return jsonify({"error": "Invalid fixture slug"}), 400
        seed_path = fixture_dir / "seed.json"
        if not _within(seed_path, ANNOTATION_ROOT) or not seed_path.exists():
            return jsonify({
                "error": "No seed.json for this fixture — re-run the bootstrap to "
                         "capture the corpus snapshot, then run the eval.",
            }), 409
        from evals.seed_import import load_seed
        try:
            seed_data = load_seed(str(seed_path))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": "Could not load seed.json", "detail": str(exc)}), 400

    from evals.runner import run_suite

    def stream():
        import queue as _queue
        import threading

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker():
            try:
                result["res"] = run_suite(
                    suite=suite,
                    subset=subset,
                    fixture_name=fixture_name,
                    seed_data=seed_data,
                    grounding_signals=grounding_signals,
                    progress=lambda ev, payload: events.put(("progress", ev, payload)),
                )
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {
            "suite": suite, "subset": subset, "fixture": fixture_name,
            "grounding": grounding_signals, "seeded": seed_data is not None,
        })

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Console eval run failed: %s", result["error"], exc_info=result["error"])
            yield _sse("error", {
                "error": "Eval run failed.",
                "detail": str(result["error"]),
                "http_status": 500,
            })
            return

        res = result["res"]
        logger.info("Console eval run complete: %d pass, %d fail → %s",
                    res.n_pass, res.n_fail, res.out_path)
        yield _sse("done", {
            "suite": suite,
            "subset": subset,
            "out_file": res.out_path.name if res.out_path else None,
            "n_pass": res.n_pass,
            "n_fail": res.n_fail,
            "regressions": len(res.regressions),
            "exit_code": res.exit_code,
        })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/tune/run", methods=["POST"])
def tune_run_stream():
    """Run a candidate-vs-baseline prompt A/B from the console (localhost-only, SSE).

    The browser face of the prompt-override tuning loop: drives `run_suite` TWICE in
    one worker — baseline (no overrides) then candidate (the pasted override map) — and
    streams a per-(fixture, rubric) delta computed by the LLM-free `evals.tune` helpers.
    The candidate run self-stamps `prompt_version=candidate:<hash>` via the override
    primitive, so it never pollutes score-over-time. **Promote stays manual** — this
    route never edits `analyzer.py`; it only surfaces the delta + candidate text.

    Input JSON: `prompt_overrides` ({CONSTANT_NAME: candidate_text}, required, one of
    the eight `analyzer._BASE_SYSTEM_PROMPTS` keys) + the same `suite`/`subset`/
    `grounding_signals` (and optional `slug`+`username` seed mode) as `/api/eval/run`.

    PAID (Sonnet + Haiku) — ~2× a single run (the UI confirm() surfaces the band). All
    eager validation (bad suite / empty or unknown override / unknown user / missing
    seed) returns a JSON 4xx BEFORE the worker spends anything — load-bearing because
    the baseline runs first, so a doomed candidate key must be caught here. Streams
    `start` / phased progress (`phase`=baseline|candidate) / `delta` / `error`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}

    suite = str(data.get("suite", "synthetic"))
    if suite not in {"synthetic", "real", "all", "anchor", "exploration"}:
        return jsonify({"error": f"Invalid suite: {suite}"}), 400
    subset = "smoke" if str(data.get("subset", "full")) == "smoke" else "full"
    grounding_signals = bool(data.get("grounding_signals"))

    # Candidate override map: {CONSTANT_NAME: text}. Required + shape-checked here, then
    # the prompt-NAMES validated via analyzer's canonical validator (raises ValueError on
    # an unknown key) — all before any paid call, so a typo never spends the baseline run.
    raw_overrides = data.get("prompt_overrides")
    if not isinstance(raw_overrides, dict) or not raw_overrides:
        return jsonify({"error": "prompt_overrides must be a non-empty object "
                                 "{CONSTANT_NAME: candidate_text}"}), 400
    overrides: dict[str, str] = {}
    for key, value in raw_overrides.items():
        if not isinstance(value, str) or not value.strip():
            return jsonify({"error": f"Candidate text for {key} is empty"}), 400
        overrides[str(key)] = value
    try:
        with prompt_overrides(overrides):
            pass
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Optional single-fixture scope (e.g. the collated <slug>). Sanitized like eval/run.
    raw_fixture = str(data.get("fixture", "")).strip()
    fixture_name = secure_filename(raw_fixture) if raw_fixture else None

    # Optional corpus-seed mode — identical contract to /api/eval/run. The seed lives
    # under ANNOTATION_ROOT/<slug>/seed.json (gitignored, PII-bearing); resolve + contain
    # it and confirm the candidate user exists, all before any paid call.
    seed_data: dict | None = None
    raw_slug = str(data.get("slug", "")).strip()
    if raw_slug:
        safe_user = _safe_username(str(data.get("username", "")))
        if not safe_user:
            return jsonify({"error": "Invalid or unknown user"}), 400
        fixture_dir = _annotation_fixture_path(raw_slug)
        if fixture_dir is None or not _within(fixture_dir, ANNOTATION_ROOT):
            return jsonify({"error": "Invalid fixture slug"}), 400
        seed_path = fixture_dir / "seed.json"
        if not _within(seed_path, ANNOTATION_ROOT) or not seed_path.exists():
            return jsonify({
                "error": "No seed.json for this fixture — re-run the bootstrap to "
                         "capture the corpus snapshot, then run the A/B.",
            }), 409
        from evals.seed_import import load_seed
        try:
            seed_data = load_seed(str(seed_path))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": "Could not load seed.json", "detail": str(exc)}), 400

    from evals.runner import run_suite
    from evals.tune import build_delta_table, format_delta_table, load_scores

    def stream():
        import queue as _queue
        import threading
        from dataclasses import asdict

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def _run(phase: str, overrides_map: dict[str, str] | None):
            return run_suite(
                suite=suite,
                subset=subset,
                fixture_name=fixture_name,
                seed_data=seed_data,
                grounding_signals=grounding_signals,
                prompt_overrides_map=overrides_map,
                progress=lambda ev, payload: events.put(
                    ("progress", ev, {**payload, "phase": phase})
                ),
            )

        def worker():
            try:
                result["baseline"] = _run("baseline", None)
                result["candidate"] = _run("candidate", overrides)
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {
            "mode": "tune", "runs": 2, "suite": suite, "subset": subset,
            "fixture": fixture_name, "grounding": grounding_signals,
            "seeded": seed_data is not None, "overrides": sorted(overrides),
        })

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Console tune A/B failed: %s", result["error"], exc_info=result["error"])
            yield _sse("error", {
                "error": "Tune A/B failed.",
                "detail": str(result["error"]),
                "http_status": 500,
            })
            return

        base = result["baseline"]
        cand = result["candidate"]
        if base.out_path is None or cand.out_path is None:
            yield _sse("error", {"error": "No fixtures matched — nothing to compare."})
            return

        rows = build_delta_table(load_scores(base.out_path), load_scores(cand.out_path))
        logger.info(
            "Console tune A/B complete: baseline %d/%d, candidate %d/%d (%s) → %d row(s)",
            base.n_pass, base.n_fail, cand.n_pass, cand.n_fail,
            cand.candidate_version, len(rows),
        )
        yield _sse("delta", {
            "table": format_delta_table(rows),
            "rows": [asdict(r) for r in rows],
            "candidate_version": cand.candidate_version,
            "baseline_file": base.out_path.name,
            "candidate_file": cand.out_path.name,
            "regressed": sum(1 for r in rows if r.regressed),
            "baseline": {"n_pass": base.n_pass, "n_fail": base.n_fail},
            "candidate": {"n_pass": cand.n_pass, "n_fail": cand.n_fail},
        })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _should_open_browser(
    werkzeug_run_main: str | None, no_browser: str | None
) -> bool:
    """Decide whether THIS process should auto-open the default browser.

    Open exactly once at startup. In debug mode Flask's reloader runs ``main()``
    in BOTH a persistent supervisor (``WERKZEUG_RUN_MAIN`` unset) and a serving
    child that is RE-EXECUTED on every reload (``WERKZEUG_RUN_MAIN == "true"``).
    Opening in the child re-popped a browser window on every restart (the
    "stray windows" bug); open only when this is NOT the reload child. The
    non-debug single process (also unset) likewise opens once. Honors the
    ``CALLBACK_NO_BROWSER=1`` opt-out for headless / remote / CI runs.
    """
    if no_browser == "1":
        return False
    return werkzeug_run_main != "true"


def main() -> None:
    """Launch the Flask app on http://localhost:5000.

    Entry point for the `callback` console script registered in
    `pyproject.toml [project.scripts]`. Equivalent to `python app.py`
    for users who installed via `pip install -e .` or `pip install
    callback`.

    Set `FLASK_DEBUG=0` in the environment to disable Flask's
    reloader + verbose error pages (see SECURITY.md for rationale).
    Set `CALLBACK_NO_BROWSER=1` to skip the auto-open (headless / remote
    / CI runs where launching a browser is unwanted).
    """
    print("\n  callback. — http://localhost:5000\n")
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"

    # Auto-open the user's default browser so `python app.py` lands them
    # straight on the app. Under Flask's reloader (debug=True) main() runs in
    # BOTH a persistent supervisor (WERKZEUG_RUN_MAIN unset) and a serving child
    # that is re-executed on EVERY reload (WERKZEUG_RUN_MAIN == "true"). Opening
    # in the child re-popped a window per reload (the stray-windows bug), so we
    # open in the supervisor / single process — exactly once. A short Timer
    # delays the open until the server is listening; it runs as a daemon so it
    # never holds the interpreter open on shutdown.
    if _should_open_browser(
        os.environ.get("WERKZEUG_RUN_MAIN"), os.environ.get("CALLBACK_NO_BROWSER")
    ):
        def _open_browser() -> None:
            try:
                webbrowser.open("http://localhost:5000")
            except Exception as exc:  # best-effort; the URL is already printed
                logger.debug("Could not auto-open browser: %s", exc)

        opener = threading.Timer(1.0, _open_browser)
        opener.daemon = True
        opener.start()

    # PX-19: bind loopback only. The host comes from the injected Config
    # (Config.host default "127.0.0.1"), so the dev server is never reachable off
    # the local machine — matching the localhost-only posture SECURITY.md commits
    # to. (A third silent-flip vector is `SERVER_NAME`; leave it unset locally.)
    app.run(host=app.config.get("HOST", "127.0.0.1"), debug=debug_mode, port=5000)


if __name__ == "__main__":
    main()

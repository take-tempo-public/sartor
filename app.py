"""Flask server — routes and orchestration.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.
"""

import json
import logging
import os
import re
import threading
import traceback
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
from flask import Flask, Response, jsonify, make_response, render_template, request, send_file
from werkzeug.utils import secure_filename

from analyzer import (
    LLMResponseError,
    _current_cover_letter_draft,
    _current_draft_text,
    analyze,
    analyze_streaming,
    check_refinement_scope,
    clarify,
    clarify_iteration,
    generate,
    generate_streaming,
    prompt_overrides,
)
from blueprints import assistant_bp
from dashboard import dashboard_bp
from generator import generate_cover_letter, generate_resume
from hardening import (
    ContextSet,
    compute_date_grounding,
    compute_iteration_signals,
    save_context_set,
    save_iteration_context,
    summarize_recent_edits,
    validate_config,
)

# P7 Observability: structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")
app.register_blueprint(assistant_bp, url_prefix="/api/assistant")

# Disable browser caching of /static/* responses so UI edits land on
# the next page reload without requiring a Flask restart or a manual
# cache-bust query string. The `/` route also sets `Cache-Control:
# no-cache` (see the `index` view) so the HTML shell is covered too.
# Local-first single-tenant tool: cache-friendliness has no real
# payoff here, and the alternative (cache-buster query strings,
# process-start tokens, etc.) bites whenever the developer or user
# forgets to restart.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

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

# Ensure directories exist
for d in (CONFIGS_DIR, RESUMES_DIR, OUTPUT_DIR):
    d.mkdir(exist_ok=True)


def _get_client() -> anthropic.Anthropic:
    """Get Anthropic client. API key from env or config."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try reading from a local key file
        key_file = BASE_DIR / ".api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    return anthropic.Anthropic(api_key=api_key)


def _load_config(username: str) -> dict:
    path = CONFIGS_DIR / f"{username}.config"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(username: str, config: dict):
    path = CONFIGS_DIR / f"{username}.config"
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


def _within(path: Path, parent: Path) -> bool:
    """Return True only if path resolves to within parent. Prevents traversal."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


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


def _is_localhost_request() -> bool:
    """True only for loopback hosts. Same posture as dashboard_bp.before_request.

    Gates the dev/eval-only annotation + bootstrap write surface so it is
    unreachable except from the local machine (it touches PII-bearing artifacts
    under evals/fixtures/real/).
    """
    host = (request.host or "").split(":")[0]
    return host in {"localhost", "127.0.0.1", "::1", "[::1]"}


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
    config = _load_config(username)
    if not config:
        return jsonify({"error": "User not found"}), 404
    return jsonify(config)


@app.route("/api/users/<username>/config", methods=["PUT"])
def update_config(username):
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


@app.route("/api/upload", methods=["POST"])
def upload_resume():
    username = request.form.get("username", "")
    if not username:
        return jsonify({"error": "Username required"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    safe_name = secure_filename(file.filename)
    user_dir = RESUMES_DIR / safe_user
    user_dir.mkdir(exist_ok=True)
    save_path = user_dir / safe_name
    file.save(str(save_path))

    # Update config with latest resume reference
    config = _load_config(safe_user)
    if config:
        config["latest_resume"] = safe_name
        _save_config(safe_user, config)

    logger.info("Uploaded resume: %s for user %s", safe_name, safe_user)
    return jsonify({"filename": safe_name, "path": str(save_path)})


@app.route("/api/users/<username>/resumes", methods=["GET"])
def list_resumes(username):
    user_dir = RESUMES_DIR / username
    if not user_dir.exists():
        return jsonify([])
    files = [
        f.name for f in user_dir.iterdir()
        if f.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return jsonify(sorted(files))


@app.route("/api/analyze", methods=["POST"])
def run_analysis():
    """P8 Human Gate #1: returns analysis for user review before generation.

    Phase C.4: the file-based legacy path is gone. Every call reads from the
    DB corpus. Users without a candidate row get a 404 pointing at the
    onboarding importer. resume_filename is ignored (kept in the request for
    frontend backward compatibility until Phase D rebuilds the UI).
    """
    data = request.json
    username = data.get("username", "")
    jd_text = data.get("job_description", "")

    if not username or not jd_text:
        return jsonify({"error": "username and job_description required"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    return _run_analysis_corpus_backed(safe_user, jd_text, data)


def _sse(event: str, payload: dict) -> str:
    """Format a Server-Sent Event line block. SSE protocol requires:
    `event: <name>\\ndata: <line>\\n\\n` with the trailing blank line.
    Multi-line data values aren't used here so a single data line suffices.
    """
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _error_detail_payload(exc: Exception) -> dict:
    """Return the per-route 5xx error payload extras.

    In debug mode (Flask's default for `python app.py`): includes the
    exception class + message + the last 3 traceback frames. This is
    load-bearing for the dev-console / smoke-debugging workflow — the
    user opens dev tools, sees the response body, copies the traceback
    into a bug report without needing terminal access.

    In production-mode (FLASK_DEBUG=0): returns only a short
    `request_id` (8 hex chars) so the user / support can correlate
    with the server log (`logger.exception` emits the full traceback
    server-side regardless). Suppresses class names, file paths, and
    function names that an attacker could fingerprint to scope
    follow-up attacks. Per the security review (2026-05-27):
    "Information Disclosure via Error Details".

    The request_id is logged alongside the exception so support can
    look it up via `grep <request_id> logs/` to retrieve the full
    traceback.
    """
    request_id = uuid.uuid4().hex[:8]
    # logger.exception is called by the route wrapper one level up;
    # this just adds the correlation id to the response.
    logger.error("error request_id=%s class=%s", request_id, type(exc).__name__)
    if app.debug:
        return {
            "detail": "{cls}: {msg}\n\n{tb}".format(
                cls=type(exc).__name__,
                msg=str(exc),
                tb="".join(traceback.format_tb(exc.__traceback__)[-3:]),
            ),
            "request_id": request_id,
        }
    return {"request_id": request_id}


@app.route("/api/analyze/stream", methods=["POST"])
def run_analysis_stream():
    """R2 streaming variant of /api/analyze.

    Same request shape and same final response payload as /api/analyze,
    but the response is delivered as Server-Sent Events so the frontend
    can render tokens as they arrive instead of waiting ~90s for the
    full Sonnet 4.6 response. Backed by `analyze_streaming` in analyzer.py.

    Event types emitted on the SSE stream:
      - `chunk`: `{"text": "<delta>"}` for each text delta from the model
      - `retry`: `{"reason": "<error>"}` when the parse failed and a retry begins
      - `done`:  the full JSON the non-streaming route would have returned
      - `error`: `{"error": "<msg>", "http_status": <int>, "detail"?: "..."}`
        on terminal failure (LLM connection / parse-after-retry)
    """
    data = request.json
    username = data.get("username", "")
    jd_text = data.get("job_description", "")

    if not username or not jd_text:
        return jsonify({"error": "username and job_description required"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    return _run_analysis_corpus_backed_streaming(safe_user, jd_text, data)


def _persist_run_persona(application_run_id: int, persona_template_id: int) -> None:
    """Record which persona template the user generated with on the run
    (audit; the column exists but was always NULL before Workstream C)."""
    from db.models import ApplicationRun
    from db.session import get_session

    session = get_session()
    try:
        run = session.query(ApplicationRun).filter_by(id=application_run_id).first()
        if run is not None:
            run.persona_template_id = persona_template_id
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _persist_cover_letter_to_db(
    application_run_id: int,
    cover_letter_md: str,
) -> None:
    """Write-back: persist a detached cover-letter's md onto its run row.

    Mirrors `_persist_corpus_generation_to_db`'s session/lookup/validate/commit
    pattern, but writes ONLY `generated_cover_letter_md` via
    `persist_cover_letter_md`. The detached cover-letter route runs after the
    résumé is already persisted, so routing through the full corpus-persist path
    would clobber the saved résumé md. Used by `/api/generate-cover-letter` only
    when the context carries `application_run_id` (corpus-backed mode); the
    caller wraps this best-effort so a DB hiccup never fails the response.
    """
    from db.models import Application, ApplicationRun
    from db.persist_run import persist_cover_letter_md
    from db.session import get_session

    session = get_session()
    try:
        run = session.query(ApplicationRun).filter_by(id=application_run_id).first()
        if run is None:
            logger.warning("Application_run not found for cover-letter persist (id=%s)", application_run_id)
            return
        app_row = session.query(Application).filter_by(id=run.application_id).first()
        if app_row is None:
            logger.warning("Parent application not found for cover-letter persist (run id=%s)", application_run_id)
            return

        persist_cover_letter_md(session, run, cover_letter_md)
        session.commit()
        logger.info(
            "Persisted cover-letter md: app_run=%d (%d chars)",
            application_run_id, len(cover_letter_md),
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _persist_corpus_generation_to_db(
    application_run_id: int,
    generate_result: dict,
    *,
    ats_findings: dict | None = None,
) -> None:
    """Phase B.3 write-back: persist the structured generate() output to the DB.

    Looks up the `application_run` row, calls `persist_corpus_generation`, and
    commits. Defense-in-depth: validates the run belongs to a real candidate
    before any writes. Used by `/api/generate` only when the context carries
    `application_run_id` (corpus-backed mode).

    Phase C.3 addition: when `ats_findings` is supplied, the round-trip
    self-check result is stored on application_run.ats_roundtrip_json so the
    dashboard can surface fixtures with failed/warning round-trips.
    """
    from db.models import Application, ApplicationRun
    from db.persist_run import persist_corpus_generation
    from db.session import get_session

    session = get_session()
    try:
        run = session.query(ApplicationRun).filter_by(id=application_run_id).first()
        if run is None:
            logger.warning("Application_run not found for persist (id=%s)", application_run_id)
            return
        app_row = session.query(Application).filter_by(id=run.application_id).first()
        if app_row is None:
            logger.warning("Parent application not found for run id=%s", application_run_id)
            return

        report = persist_corpus_generation(
            session, run, generate_result, candidate_id=app_row.candidate_id,
        )
        if ats_findings is not None:
            run.ats_roundtrip_json = json.dumps(ats_findings)
        session.commit()
        logger.info(
            "Persisted corpus generation: app_run=%d bullets=%d titles=%d "
            "proposals=%db/%dt (missing: %d exp, %d bul, %d tit)",
            application_run_id,
            report.application_bullets_created,
            report.application_run_titles_created,
            report.proposed_bullets_created,
            report.proposed_titles_created,
            len(report.experiences_referenced_but_missing),
            len(report.bullets_referenced_but_missing),
            len(report.titles_referenced_but_missing),
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _check_date_grounding(context_set: ContextSet, result: dict) -> dict | None:
    """KW6 guard: flag generated heading date ranges that don't trace to the
    corpus (altered or duplicated — the iteration regenerate has been observed
    "reconciling" one experience's range onto another while re-sequencing).

    Warn-only by design: appends a plain-language note per flagged heading to
    `result["proofread_notes"]` (already rendered by the preview UI) and returns
    the structured findings for the response's `date_grounding` field. NEVER
    mutates resume content and never blocks the generate flow — best-effort,
    mirroring the ATS round-trip check. Returns None in legacy (non-corpus)
    mode, where there is no structured date ground truth to compare against.
    """
    corpus = context_set.get("career_corpus")
    if not corpus:
        return None
    try:
        findings = compute_date_grounding(result.get("resume_content", ""), corpus)
    except Exception as exc:
        logger.warning("Date-grounding check failed to run: %s", exc)
        return {"status": "not_run", "checked": 0, "flagged": [],
                "corpus_ranges": [], "notes": [f"check raised: {exc}"]}
    if findings["status"] == "flag":
        logger.warning(
            "Date-grounding flag on generated resume: %s (corpus ranges: %s)",
            findings["flagged"], findings["corpus_ranges"],
        )
        notes = result.setdefault("proofread_notes", [])
        for f in findings["flagged"]:
            # A duplicated range flags the SECOND heading consuming it in
            # document order — the wording stays neutral about which heading
            # the model actually altered.
            notes.append(
                f'Date check: "{f["heading"]}" shows {f["found"]}, which is '
                f"altered or duplicated — it does not match a remaining date "
                f"range in your career corpus "
                f"({', '.join(findings['corpus_ranges'])}). Your corpus dates "
                f"were NOT changed; please verify this document's dates before "
                f"sending."
            )
    return findings


def _run_analysis_corpus_backed_streaming(safe_user: str, jd_text: str, data: dict):
    """SSE-streaming counterpart to `_run_analysis_corpus_backed`.

    Identical setup (build_context_set_from_db, application + run rows,
    same persistence semantics post-analysis). The only difference: the
    LLM call is driven via `analyze_streaming` so token deltas can be
    forwarded to the browser as SSE events, and the final saved-context
    state + IDs ride on a `done` event rather than a JSON 200 body.

    Errors during setup return regular JSON responses (4xx/409) so the
    frontend can branch before opening the SSE stream. Errors during the
    LLM call surface as `error` SSE events with an `http_status` hint.
    """
    from db.build_context import build_context_set_from_db
    from db.models import ApplicationRun
    from db.session import get_session, init_db

    if not _safe_username(safe_user):
        return jsonify({"error": "Invalid or unknown user"}), 400
    user_output_dir = OUTPUT_DIR / safe_user
    if not _within(user_output_dir, OUTPUT_DIR):
        return jsonify({"error": "Invalid output path"}), 403

    init_db()
    setup_session = get_session()
    run_id = uuid.uuid4().hex[:12]
    try:
        try:
            _get_or_provision_candidate(setup_session, safe_user)
            context_set, application, application_run = build_context_set_from_db(
                setup_session,
                candidate_username=safe_user,
                jd_text=jd_text,
                run_id=run_id,
                jd_url=data.get("jd_url"),
                application_title=data.get("application_title"),
            )
        except ValueError as exc:
            setup_session.rollback()
            logger.warning(
                "[analyze/stream 409] user=%s needs_onboarding: %s", safe_user, exc
            )
            return jsonify({"error": str(exc), "needs_onboarding": True}), 409
        application_id = application.id
        application_run_id = application_run.id
        # Commit the application + application_run rows up front so we don't
        # hold the session open across the ~90s LLM call. The analysis_json
        # update happens in a new short-lived session in the stream's done branch.
        setup_session.commit()
        logger.info(
            "DB-backed streaming analysis for %s: application_id=%d run_id=%s",
            safe_user, application_id, run_id,
        )
    finally:
        setup_session.close()

    client = _get_client()

    def stream():
        try:
            analysis: dict | None = None
            for event_kind, payload in analyze_streaming(
                client, context_set, username=safe_user, run_id=run_id,
            ):
                if event_kind == "chunk":
                    yield _sse("chunk", {"text": payload})
                elif event_kind == "retry":
                    yield _sse("retry", {"reason": str(payload)})
                elif event_kind == "phase":
                    # Two-pass analyze: surface which pass is running so the
                    # frontend can swap the status label (extraction → synthesis).
                    yield _sse("phase", payload if isinstance(payload, dict) else {})
                elif event_kind == "done":
                    analysis = payload if isinstance(payload, dict) else None
            if analysis is None:
                yield _sse("error", {
                    "error": "Streaming analyze finished without a parsed result.",
                    "http_status": 502,
                })
                return

            # Persist analysis_json on the application_run row + write the
            # context_*.json file the downstream routes (clarify, generate,
            # save-edits, iterate-clarify) all consume.
            persist_session = get_session()
            try:
                run_row = persist_session.query(ApplicationRun).filter_by(
                    id=application_run_id,
                ).first()
                if run_row is not None:
                    run_row.analysis_json = json.dumps(analysis)
                    persist_session.commit()
                else:
                    logger.warning(
                        "application_run %d not found at analysis-persist time",
                        application_run_id,
                    )
            finally:
                persist_session.close()

            context_set["llm_analysis"] = analysis
            context_set["run_id"] = run_id
            context_set["application_id"] = application_id
            context_set["application_run_id"] = application_run_id
            context_path = save_context_set(context_set, safe_user, str(OUTPUT_DIR))
            logger.info(
                "Streaming analysis complete for %s, saved to %s",
                safe_user, context_path,
            )

            yield _sse("done", {
                "analysis": analysis,
                "deterministic": {
                    "keyword_overlap": context_set["deterministic_analysis"]["keyword_overlap"],
                    "ats_warnings": context_set["deterministic_analysis"]["ats_warnings"],
                },
                "context_path": context_path,
                "template_path": "",
                "application_id": application_id,
                "application_run_id": application_run_id,
            })
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic API connection error during streaming analysis: %s", exc)
            yield _sse("error", {
                "error": "Connection to AI service failed. Please try again.",
                "http_status": 503,
            })
        except LLMResponseError as exc:
            logger.error(
                "LLM streaming analysis response failed validation after retry: %s",
                exc.validation_error,
            )
            yield _sse("error", {
                "error": "AI analysis response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
                "http_status": 502,
            })
        except Exception:
            logger.exception("Streaming analysis failed unexpectedly")
            yield _sse("error", {
                "error": "Internal error during analysis.",
                "http_status": 500,
            })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx-style buffering if proxied
        },
    )


def _run_analysis_corpus_backed(safe_user: str, jd_text: str, data: dict):
    """DB-backed analyze path used when CORPUS_BACKED=1.

    Produces the same response shape as the file-based path: analysis JSON,
    keyword_overlap, ats_warnings, context_path. The context_path file still
    gets written so downstream routes (clarify, generate, iterate-clarify)
    work unchanged. Additionally creates `application` + `application_run`
    rows that anchor the new audit chain.
    """
    from db.build_context import build_context_set_from_db
    from db.session import get_session, init_db

    # Defense-in-depth: re-validate username + output path even though the
    # caller already checked. Internal callers can drift; the guards are cheap.
    if not _safe_username(safe_user):
        return jsonify({"error": "Invalid or unknown user"}), 400
    user_output_dir = OUTPUT_DIR / safe_user
    if not _within(user_output_dir, OUTPUT_DIR):
        return jsonify({"error": "Invalid output path"}), 403

    init_db()
    session = get_session()
    run_id = uuid.uuid4().hex[:12]
    try:
        try:
            _get_or_provision_candidate(session, safe_user)
            context_set, application, application_run = build_context_set_from_db(
                session,
                candidate_username=safe_user,
                jd_text=jd_text,
                run_id=run_id,
                jd_url=data.get("jd_url"),
                application_title=data.get("application_title"),
            )
        except ValueError as exc:
            session.rollback()
            logger.warning(
                "[analyze 409] user=%s needs_onboarding: %s", safe_user, exc
            )
            return jsonify({
                "error": str(exc),
                "needs_onboarding": True,
            }), 409

        logger.info(
            "DB-backed analysis for %s: application_id=%d run_id=%s",
            safe_user, application.id, run_id,
        )

        client = _get_client()
        try:
            analysis = analyze(client, context_set, username=safe_user, run_id=run_id)
        except anthropic.APIConnectionError as exc:
            session.rollback()
            logger.error("Anthropic API connection error during analysis: %s", exc)
            return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
        except LLMResponseError as exc:
            session.rollback()
            logger.error(
                "LLM analysis response failed validation after retry: %s",
                exc.validation_error,
            )
            return jsonify({
                "error": "AI analysis response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
            }), 502

        # Persist analysis on the application_run row + keep the JSON file
        # path live for unchanged downstream routes.
        application_run.analysis_json = json.dumps(analysis)
        context_set["llm_analysis"] = analysis
        context_set["run_id"] = run_id
        # Phase B.3: stash the DB anchor IDs in the saved context so /api/generate
        # can find the application_run and persist the LLM's structured output
        # (selected_bullets, proposal_review rows, etc.) on its second LLM call.
        context_set["application_id"] = application.id
        context_set["application_run_id"] = application_run.id
        context_path = save_context_set(context_set, safe_user, str(OUTPUT_DIR))

        session.commit()
        logger.info("Analysis complete for %s, saved to %s", safe_user, context_path)

        return jsonify({
            "analysis": analysis,
            "deterministic": {
                "keyword_overlap": context_set["deterministic_analysis"]["keyword_overlap"],
                "ats_warnings": context_set["deterministic_analysis"]["ats_warnings"],
            },
            "context_path": context_path,
            "template_path": "",  # no file-backed template in DB mode; Phase C picks a persona
            "application_id": application.id,
            "application_run_id": application_run.id,
        })
    finally:
        session.close()


@app.route("/api/clarify", methods=["POST"])
def run_clarify():
    """Optional P8 Human Gate between analyze and generate.

    Generates 3-5 targeted questions based on the analyzer's output to surface
    real candidate experience that wasn't captured in the resume, plus disambiguate
    scope where the analyzer flagged it. The questions are persisted on the
    saved context so the user can refresh and resume; answers (when submitted
    via /api/answer-clarifications) become first-person ground truth at generate.

    Skipping this step is supported — /api/generate works on contexts that
    never went through clarify, preserving the pre-clarify behavior.
    """
    data = request.json
    context_path = data.get("context_path", "")
    username = data.get("username", "")
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # When a username is supplied, validate it; otherwise derive from the
    # context path's parent directory (OUTPUT_DIR/<username>/context_*.json).
    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Could not resolve username"}), 400

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})
    if not analysis:
        return jsonify({"error": "No analysis found in context"}), 400

    # Re-use the run_id minted in /api/analyze so all three calls share a key
    # in logs/llm_calls.jsonl. New ID for legacy contexts that pre-date run_id.
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]

    client = _get_client()
    logger.info("Starting clarification for %s run_id=%s", safe_user, run_id)
    try:
        result = clarify(client, context_set, analysis, username=safe_user, run_id=run_id)
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during clarify: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("LLM clarify response failed validation after retry: %s", exc.validation_error)
        return jsonify({
            "error": "AI clarification response was malformed after retry. Please try again.",
            "detail": exc.validation_error,
        }), 502

    questions = result.get("questions", [])
    # Persist the questions back to the same context file so the user can
    # refresh the page and resume — and so generate() can pair each answer
    # with its question text.
    context_set["clarification_questions"] = questions
    context_set["run_id"] = run_id
    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info("Clarify produced %d questions for %s", len(questions), safe_user)
    return jsonify({
        "questions": questions,
        "reasoning": result.get("reasoning", ""),
        "context_path": str(cp),
    })


def _persist_clarifications_to_memory(context_set: ContextSet, answered: dict[str, str]) -> int:
    """Mirror answered clarifications into the cross-application candidate-memory
    table (`clarification`) — the live write path the memory panel reads
    (`/api/users/<u>/clarifications`) and promote-to-bullet consumes (KW7 / B.8).

    Additive upsert scoped to this application, keyed on
    (candidate_id, origin_application_id, normalized question). Re-submitting
    updates the stored answer; rows are never deleted here — memory is the
    durable record of every Q&A the candidate has answered (a later "skip"
    clears the context map, not memory). Rows already promoted to a bullet are
    left untouched so promoted history can't be silently rewritten.

    Only corpus-backed contexts participate: the identity chain is
    context.application_run_id → ApplicationRun → Application → Candidate, with
    belt-and-suspenders `_safe_username` on the resolved owner. Legacy
    file-only contexts (no run id) are a no-op. Returns rows written/updated.
    """
    run_pk = context_set.get("application_run_id")
    if not isinstance(run_pk, int) or not answered:
        return 0
    questions = context_set.get("clarification_questions") or []
    if not questions:
        return 0

    from db.models import Application, ApplicationRun, Candidate, Clarification
    from db.session import get_session, init_db
    from onboarding.corpus_import import _normalize as _norm_qa

    # Kinds outside the DB CHECK enum (migration 0001) need mapping: a
    # context_probe surfaces transferable *experience* (CLARIFY_SYSTEM_PROMPT),
    # so it files as experience_probe — target_gap keeps the "Context signal: …"
    # provenance. Anything else unknown follows the corpus-import precedent
    # (onboarding/corpus_import.py `_VALID_KINDS` → "manual").
    db_kinds = {"experience_probe", "scope_probe", "iteration_probe", "outcome_probe", "manual"}

    init_db()
    session = get_session()
    try:
        run = session.query(ApplicationRun).filter_by(id=run_pk).first()
        if run is None:
            return 0
        app_row = session.query(Application).filter_by(id=run.application_id).first()
        if app_row is None:
            return 0
        candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
        if candidate is None or not _safe_username(candidate.username):
            return 0

        existing: dict[str, Clarification] = {}
        for row in session.query(Clarification).filter_by(
            candidate_id=candidate.id, origin_application_id=app_row.id,
        ):
            existing[_norm_qa(row.question)] = row

        written = 0
        for q in questions:
            qid = q.get("id")
            qtext = (q.get("text") or "").strip()
            if not qid or not qtext or qid not in answered:
                continue
            answer = answered[qid]
            existing_row = existing.get(_norm_qa(qtext))
            if existing_row is not None:
                if existing_row.is_promoted_to_bullet or existing_row.answer == answer:
                    continue
                existing_row.answer = answer
                written += 1
                continue
            kind = (q.get("kind") or "").strip()
            if kind not in db_kinds:
                kind = "experience_probe" if kind == "context_probe" else "manual"
            new_row = Clarification(
                candidate_id=candidate.id,
                origin_application_id=app_row.id,
                origin_run_id=run.id,
                question=qtext,
                answer=answer,
                kind=kind,
                target_gap=(q.get("target_gap") or "").strip() or None,
            )
            session.add(new_row)
            existing[_norm_qa(qtext)] = new_row
            written += 1
        session.commit()
        return written
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/answer-clarifications", methods=["POST"])
def submit_clarifications():
    """Persist the candidate's free-form answers to the clarifying questions.

    Answers are merged by id into context_set["clarifications"]
    (question_id -> text) by default, so a later round (e.g. the iteration
    interview, which submits only its own textareas) preserves the analyze-round
    answers already on the context. Pass merge=false to replace the whole map
    instead — the deliberate "skip clears prior answers" path. Unanswered ids
    are simply absent — generate() omits the matching question from the prompt.
    Whitespace-only answers are dropped and cannot un-answer a prior key; use
    merge=false to clear. Answered pairs are additionally mirrored into the
    candidate-memory table via `_persist_clarifications_to_memory` (best-effort).
    """
    data = request.json
    context_path = data.get("context_path", "")
    username = data.get("username", "")
    answers = data.get("answers", {}) or {}
    # Default merge=True so the safe behavior (accumulate by id) is the default:
    # a caller that omits the flag can't silently drop prior-round answers. The
    # skip path opts out with merge=false to clear the map.
    merge = bool(data.get("merge", True))
    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    if not isinstance(answers, dict):
        return jsonify({"error": "answers must be a JSON object"}), 400

    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # When a username is supplied, validate it; otherwise derive from the
    # context path. The path containment check (_within above) is the primary
    # authority; this is belt-and-suspenders.
    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Could not resolve username"}), 400

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    valid_ids = {q.get("id", "") for q in context_set.get("clarification_questions", [])}

    # Filter: only accept answers for ids that match known questions and have
    # non-empty trimmed text. Defense against arbitrary keys ending up in the
    # context file.
    cleaned: dict[str, str] = {}
    for qid, text in answers.items():
        if not isinstance(qid, str) or qid not in valid_ids:
            continue
        if not isinstance(text, str):
            continue
        trimmed = text.strip()
        if trimmed:
            cleaned[qid] = trimmed

    if merge:
        # Merge by id: a later round (the iteration interview submits only its
        # own textareas) must not wipe the analyze-round answers already saved
        # on the context — generate() at iter>=1 reads the union as ground truth.
        existing = context_set.get("clarifications") or {}
        context_set["clarifications"] = {**existing, **cleaned}
    else:
        # Deliberate replace/clear — the skip path posts answers={} merge=false.
        context_set["clarifications"] = cleaned
    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    # KW7 / B.8: mirror answered pairs into candidate memory. Best-effort —
    # the context file is generation's source of truth; a memory-write failure
    # must never fail the submit (it is logged loudly instead).
    memory_rows = 0
    try:
        memory_rows = _persist_clarifications_to_memory(context_set, cleaned)
    except Exception:
        logger.exception(
            "Candidate-memory persist failed for %s (answers are saved in context)",
            safe_user,
        )

    logger.info(
        "Stored %d clarification answers (out of %d questions) for %s; %d memory rows",
        len(cleaned), len(valid_ids), safe_user, memory_rows,
    )
    return jsonify({
        "ok": True,
        "answered": len(cleaned),
        "total": len(valid_ids),
        "memory_rows": memory_rows,
    })


@app.route("/api/iterate-clarify", methods=["POST"])
def run_iterate_clarify():
    """Iteration interview: probe the CURRENT draft's specific weaknesses.

    User-driven (the frontend calls this when the user clicks INTERVIEW
    QUESTIONS in the Output panel). Produces 3-5 questions tied to concrete
    signals: deterministic metrics on the current draft, the diff between the
    last generation and the user's typed edits, JD keywords still missing,
    and prior-clarification follow-ups.

    The questions persist on the SAME context file (additive — appended to
    clarification_questions). Answers are submitted via the existing
    /api/answer-clarifications route, which already accepts any qid present
    in clarification_questions.
    """
    data = request.json
    context_path = data.get("context_path", "")
    username = data.get("username", "")
    if not context_path:
        return jsonify({"error": "context_path required"}), 400

    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Could not resolve username"}), 400

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})
    if not analysis:
        return jsonify({"error": "No analysis found in context"}), 400

    iteration = int(context_set.get("iteration", 0) or 0)
    if iteration < 1:
        # The iteration interview is meaningful only after at least one
        # generation has produced a draft. Before that, the regular /api/clarify
        # route is the right one — it works off the analyzer output, not a draft.
        return jsonify({
            "error": "Iteration interview requires at least one generated draft. Run /api/generate first.",
        }), 400

    # Resolve current drafts (edited > last_generated > primary fallback).
    # Reuses the same precedence generate() applies, so the questions target
    # exactly what the LLM would author from on the next call.
    current_resume_text, _ = _current_draft_text(context_set)
    current_cover_text, _ = _current_cover_letter_draft(context_set)
    edits_summary = summarize_recent_edits(context_set)
    signals = compute_iteration_signals(context_set, current_resume_text)

    # Pair prior clarifications (question + answer) so the LLM can build on
    # established truths rather than re-ask. Skipped questions are omitted.
    prior_qs = context_set.get("clarification_questions") or []
    prior_answers = context_set.get("clarifications") or {}
    prior_clarifications: list[dict] = []
    for q in prior_qs:
        qid = q.get("id", "")
        ans = prior_answers.get(qid, "").strip() if isinstance(prior_answers.get(qid, ""), str) else ""
        if ans:
            prior_clarifications.append({
                "question": q.get("text", ""),
                "answer": ans,
                "kind": q.get("kind", ""),
            })

    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]
    client = _get_client()
    logger.info(
        "Starting iteration clarify for %s iteration=%d run_id=%s",
        safe_user, iteration, run_id,
    )
    try:
        result = clarify_iteration(
            client, context_set, analysis,
            current_resume_text=current_resume_text,
            current_cover_letter_text=current_cover_text,
            recent_edits_summary=edits_summary,
            deterministic_signals=signals,
            prior_clarifications=prior_clarifications,
            username=safe_user, run_id=run_id,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during iterate-clarify: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("LLM iterate-clarify response failed validation after retry: %s", exc.validation_error)
        return jsonify({
            "error": "AI iteration-interview response was malformed after retry. Please try again.",
            "detail": exc.validation_error,
        }), 502

    new_questions = result.get("questions", []) or []

    # Re-key new question ids to avoid collisions with existing q1/q2/...
    # The /api/answer-clarifications route filters by id-membership, so unique
    # ids per question are mandatory. Prefix with iteration number for clarity
    # in saved JSON and dashboard rendering.
    existing_ids = {q.get("id", "") for q in prior_qs}
    renamed: list[dict] = []
    for i, q in enumerate(new_questions, 1):
        new_id = f"iter{iteration}_q{i}"
        # Defensive: ensure no collision even if a prior iteration used the same prefix
        suffix = 1
        while new_id in existing_ids:
            suffix += 1
            new_id = f"iter{iteration}_q{i}_{suffix}"
        existing_ids.add(new_id)
        q["id"] = new_id
        renamed.append(q)

    # Append (do not replace) so the audit chain of all interview rounds stays
    # intact. /api/answer-clarifications already merges into context["clarifications"]
    # by id, so prior answers persist alongside new ones.
    combined = list(prior_qs) + renamed
    context_set["clarification_questions"] = combined
    context_set["run_id"] = run_id

    notes = list(context_set.get("iteration_notes") or [])
    notes.append({
        "timestamp": datetime.now().isoformat(),
        "action": "iterate_clarify",
        "summary": f"surfaced {len(renamed)} iteration questions at iteration {iteration}",
    })
    context_set["iteration_notes"] = notes

    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info(
        "iterate-clarify produced %d questions for %s (iteration=%d)",
        len(renamed), safe_user, iteration,
    )
    return jsonify({
        "questions": renamed,
        "reasoning": result.get("reasoning", ""),
        "context_path": str(cp),
        "iteration": iteration,
        "signals": signals,
    })


@app.route("/api/save-edits", methods=["POST"])
def save_edits():
    """Persist user-edited preview text onto the current context.

    Called by the frontend when the user picks "USE EDITS AS BASELINE" in the
    edit-detection modal before refining or running an iteration interview.
    Stores the edited text on the SAME context file (does not advance the
    iteration counter) — the next /api/generate call will consume the edits
    and write a new iteration context.

    The edits are accepted at face value: this is the user's first-person
    typed input, not an LLM output. The grounding check in generate() treats
    edits as ground truth, mirroring the clarification carve-out.
    """
    data = request.json
    context_path = data.get("context_path", "")
    username = data.get("username", "")
    edited_resume = data.get("edited_resume", "")
    edited_cover_letter = data.get("edited_cover_letter", "")

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    if not isinstance(edited_resume, str) or not isinstance(edited_cover_letter, str):
        return jsonify({"error": "edited_resume and edited_cover_letter must be strings"}), 400
    if not edited_resume.strip() and not edited_cover_letter.strip():
        return jsonify({"error": "At least one of edited_resume or edited_cover_letter required"}), 400

    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Could not resolve username"}), 400

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))

    saved_resume = False
    saved_cover = False
    if edited_resume.strip():
        context_set["edited_resume_text"] = edited_resume
        saved_resume = True
    if edited_cover_letter.strip():
        context_set["edited_cover_letter_text"] = edited_cover_letter
        saved_cover = True

    # Append a note to the iteration_notes audit trail. Doesn't change iteration.
    notes = list(context_set.get("iteration_notes") or [])
    targets = []
    if saved_resume:
        targets.append("resume")
    if saved_cover:
        targets.append("cover_letter")
    notes.append({
        "timestamp": datetime.now().isoformat(),
        "action": "save_edits",
        "summary": f"edits saved as baseline for: {', '.join(targets)}",
    })
    context_set["iteration_notes"] = notes

    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info(
        "Saved edits for %s: resume=%s cover_letter=%s",
        safe_user, saved_resume, saved_cover,
    )
    return jsonify({
        "ok": True,
        "saved_resume": saved_resume,
        "saved_cover_letter": saved_cover,
        "context_path": str(cp),
    })


@app.route("/api/generate", methods=["POST"])
def run_generation():
    """P8 Human Gate #2: generates documents after user reviewed analysis.

    Iteration model: each call writes a NEW context file (via
    save_iteration_context) rather than mutating the prior one. The new file
    carries `parent_context_path` back to the input context, an incremented
    `iteration` counter, and `last_generated_*` snapshots for the frontend's
    edit-detection diff. The returned `context_path` is the NEW file's path —
    the frontend must use it for any subsequent calls (refine, iterate-clarify,
    save-edits) so the iteration chain is preserved.
    """
    data = request.json
    username = data.get("username", "")
    context_path = data.get("context_path", "")
    output_format = data.get("output_format", "")  # ".docx" or ".md"; falls back to context
    refinement_notes = data.get("refinement_notes", "")
    # Phase β.5 — cover-letter generation is opt-in. The common résumé-only
    # path skips the cover-letter LLM tokens entirely; /api/generate-cover-letter
    # produces it on demand against the finalized résumé.
    with_cover_letter = bool(data.get("generate_cover_letter", False))

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # Reload the saved context set (P4 Disposable Blueprint)
    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})

    if not analysis:
        return jsonify({"error": "No valid analysis found in context"}), 400

    logger.info("Starting generation for %s (iteration=%s)", username,
                context_set.get("iteration", 0))

    # β.6d — apply the chosen SummaryItem variant to the candidate's
    # positioning text before the LLM sees the context. Priority chain:
    #   1. composition_overrides.pinned_summary_id (user explicit pin)
    #   2. llm_summary_recommendation.recommendation.summary_item_id
    #   3. Candidate.profile_text (the back-compat default; preserved
    #      when no SummaryItem rows exist or none is chosen)
    # In-memory patch — save_iteration_context will persist the patched
    # value into the next iteration's context, which is what we want:
    # the user's chosen positioning carries forward into refinement.
    _apply_chosen_summary(context_set)
    # B.4 — inject the user's chosen per-role intros into the corpus snapshot
    # (opt-in; no-op when the "Add role intros" toggle is off).
    _apply_chosen_experience_summaries(context_set)
    # B.5 — reorder/filter the candidate's skills to the curated set so the
    # download reflects recommend_skills + pin/drop/reorder (no-op when none).
    _apply_recommended_skills(context_set)

    client = _get_client()
    # Re-use the run_id minted in /api/analyze when present so both calls
    # share an ID in telemetry. New ID for legacy contexts that pre-date
    # this field (or for one-off /api/generate calls without a prior analyze).
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]
    try:
        result = generate(
            client, context_set, analysis,
            refinement_notes=refinement_notes,
            username=username,
            run_id=run_id,
            with_cover_letter=with_cover_letter,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during generation: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("LLM generation response failed validation after retry: %s", exc.validation_error)
        return jsonify({
            "error": "AI generation response was malformed after retry. Please try again.",
            "detail": exc.validation_error,
        }), 502

    safe_user = _safe_username(username) if username else None
    if not safe_user:
        # Fall back to extracting username from context path (it's OUTPUT_DIR/username/file)
        safe_user = secure_filename(cp.parent.name)

    # P1 Hardening: deterministic document creation
    # Use user-selected output format; fall back to original resume format
    original_format = context_set["resume"]["format"]
    if output_format not in (".docx", ".md", ".pdf"):
        output_format = ".docx" if original_format != ".md" else ".md"
    # Phase C.2 + β.1: template path resolution priority
    #   1. explicit persona_template_id in the request body
    #   2. legacy context_set["resume"]["path"] (file-based path, deprecated)
    #   3. candidate's is_default template matching JD role (β.1)
    #   4. candidate's general is_default template (β.1)
    #   5. bundled `Classic` as the universal fallback
    # Both .docx and .pdf need a persona template — .docx uses it as the
    # python-docx style template; .pdf uses its .html sibling for the
    # Playwright render (β.3).
    template_path = None
    resolved_persona_id: int | None = None
    if output_format in (".docx", ".pdf"):
        requested_persona_id = data.get("persona_template_id")
        if requested_persona_id is not None:
            resolved_persona_id = int(requested_persona_id)
            template_path = _resolve_persona_template_path(resolved_persona_id)
        else:
            ctx_app_id = context_set.get("application_id")
            template_path = (
                context_set["resume"].get("path")
                or _resolve_default_persona_template_path(
                    username=safe_user,
                    application_id=int(ctx_app_id) if ctx_app_id is not None else None,
                )
            )
    resume_path = generate_resume(
        result["resume_content"], output_format, safe_user, str(OUTPUT_DIR),
        template_path=template_path,
    )
    # Phase β.5 — only write the cover-letter file when the call actually
    # produced one. The /api/generate-cover-letter route does the writing
    # for opt-in cover letters after the résumé is finalized.
    cover_letter_path = ""
    if (result.get("cover_letter_content") or "").strip():
        cover_letter_path = generate_cover_letter(
            result["cover_letter_content"], safe_user, str(OUTPUT_DIR)
        )

    logger.info("Generation complete: %s, %s", resume_path, cover_letter_path)

    # Phase C.3: ATS round-trip self-check. Best-effort; failures are
    # surfaced in the response + persisted on application_run (when DB-
    # backed) but never block the user. Pure file operation — no LLM cost.
    ats_findings: dict | None = None
    if output_format == ".docx":
        try:
            from db.ats_roundtrip import run_ats_roundtrip
            ats_findings = run_ats_roundtrip(resume_path, result["resume_content"])
            if ats_findings["status"] != "pass":
                logger.warning(
                    "ATS round-trip %s on %s: %s",
                    ats_findings["status"], resume_path, ats_findings["notes"],
                )
        except Exception as exc:
            logger.warning("ATS round-trip check failed to run: %s", exc)
            ats_findings = {"status": "not_run", "notes": [f"check raised: {exc}"]}

    # KW6 guard: deterministic date-grounding check (corpus mode only).
    # Warn-only — appends to result["proofread_notes"]; never blocks.
    date_findings = _check_date_grounding(context_set, result)

    # Phase B.3: when the context carries an application_run_id (set by the
    # corpus-backed /api/analyze path), persist the LLM's structured output
    # to the DB audit chain — application_bullet rows, proposal_review rows
    # for any new bullets/titles the LLM proposed, etc. No-op for file-based
    # contexts (which don't have an application_run_id).
    app_run_id = context_set.get("application_run_id")
    if app_run_id is not None:
        try:
            if resolved_persona_id is not None:
                _persist_run_persona(int(app_run_id), resolved_persona_id)
            _persist_corpus_generation_to_db(
                int(app_run_id), result, ats_findings=ats_findings,
            )
        except Exception as exc:
            # Persistence failure must not break the user's generate flow —
            # the markdown is already produced and saved to disk. Log loudly.
            logger.error("Corpus generation persist failed (run_id=%s): %s",
                         app_run_id, exc, exc_info=True)

    # Snapshot this iteration as a new immutable context file. The chain of
    # parent_context_path pointers forms the iteration audit trail.
    summary_parts = []
    if refinement_notes.strip():
        summary_parts.append("refinement")
    if context_set.get("edited_resume_text") or context_set.get("edited_cover_letter_text"):
        summary_parts.append("from edited baseline")
    summary = " + ".join(summary_parts) if summary_parts else "fresh generation"

    new_context_path = save_iteration_context(
        parent_context=context_set,
        parent_path=str(cp),
        last_generated_resume=result["resume_content"],
        last_generated_cover_letter=result["cover_letter_content"],
        username=safe_user,
        base_dir=str(OUTPUT_DIR),
        action="generate",
        summary=summary,
    )
    new_iteration = int(context_set.get("iteration", 0) or 0) + 1
    logger.info(
        "Iteration %d snapshotted: %s (parent=%s)",
        new_iteration, new_context_path, str(cp),
    )

    return jsonify({
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "resume_format": output_format,
        "changes_made": result.get("changes_made", []),
        "proofread_notes": result.get("proofread_notes", []),
        "resume_preview": result["resume_content"],
        "cover_letter_preview": result["cover_letter_content"],
        "context_path": new_context_path,
        "iteration": new_iteration,
        "parent_context_path": str(cp),
        "ats_roundtrip": ats_findings,
        "date_grounding": date_findings,
        # Workstream C: echo the persona used so the frontend can thread it
        # to /api/download-edited (so DOWNLOAD honors the chosen template).
        "persona_template_id": resolved_persona_id,
    })


@app.route("/api/generate/stream", methods=["POST"])
def run_generation_stream():
    """R2 streaming variant of /api/generate.

    Same request shape and same final response payload as /api/generate,
    but the LLM call streams tokens via SSE so the frontend can show a
    live "alive" indicator (token counter + collapsible raw stream)
    during the ~50s Sonnet 4.6 call. All pre-LLM validation runs upfront
    and returns plain JSON on failure; all post-LLM persistence (file
    writes, ATS round-trip, DB persist, iteration snapshot) runs inside
    the stream's `done` branch and rides the final SSE event.

    Event types on the SSE stream:
      - `chunk`: `{"text": "<delta>"}` per text delta
      - `retry`: `{"reason": "<error>"}` when a parse retry begins
      - `done`:  the full payload the non-streaming /api/generate returns
      - `error`: `{"error": "<msg>", "http_status": <int>, "detail"?: "..."}`
    """
    data = request.json
    username = data.get("username", "")
    context_path = data.get("context_path", "")
    output_format = data.get("output_format", "")
    refinement_notes = data.get("refinement_notes", "")
    with_cover_letter = bool(data.get("generate_cover_letter", False))

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})
    if not analysis:
        return jsonify({"error": "No valid analysis found in context"}), 400

    logger.info(
        "Starting streaming generation for %s (iteration=%s)",
        username, context_set.get("iteration", 0),
    )
    _apply_chosen_summary(context_set)
    # B.4 — inject the user's chosen per-role intros into the corpus snapshot
    # (opt-in; no-op when the "Add role intros" toggle is off).
    _apply_chosen_experience_summaries(context_set)
    # B.5 — reorder/filter the candidate's skills to the curated set so the
    # download reflects recommend_skills + pin/drop/reorder (no-op when none).
    _apply_recommended_skills(context_set)

    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)

    # Resolve template_path + output_format up front so all post-LLM
    # persistence inside the stream has them in closure.
    original_format = context_set["resume"]["format"]
    resolved_output_format = output_format
    if resolved_output_format not in (".docx", ".md", ".pdf"):
        resolved_output_format = ".docx" if original_format != ".md" else ".md"

    template_path = None
    resolved_persona_id: int | None = None
    if resolved_output_format in (".docx", ".pdf"):
        requested_persona_id = data.get("persona_template_id")
        if requested_persona_id is not None:
            resolved_persona_id = int(requested_persona_id)
            template_path = _resolve_persona_template_path(resolved_persona_id)
        else:
            ctx_app_id = context_set.get("application_id")
            template_path = (
                context_set["resume"].get("path")
                or _resolve_default_persona_template_path(
                    username=safe_user,
                    application_id=int(ctx_app_id) if ctx_app_id is not None else None,
                )
            )

    client = _get_client()
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]

    def stream():
        try:
            result: dict | None = None
            for event_kind, payload in generate_streaming(
                client, context_set, analysis,
                refinement_notes=refinement_notes,
                username=safe_user,
                run_id=run_id,
                with_cover_letter=with_cover_letter,
            ):
                if event_kind == "chunk":
                    yield _sse("chunk", {"text": payload})
                elif event_kind == "retry":
                    yield _sse("retry", {"reason": str(payload)})
                elif event_kind == "done":
                    result = payload if isinstance(payload, dict) else None
            if result is None:
                yield _sse("error", {
                    "error": "Streaming generate finished without a parsed result.",
                    "http_status": 502,
                })
                return

            # Post-LLM persistence — mirror the non-streaming route.
            resume_path = generate_resume(
                result["resume_content"], resolved_output_format,
                safe_user, str(OUTPUT_DIR),
                template_path=template_path,
            )
            cover_letter_path = ""
            if (result.get("cover_letter_content") or "").strip():
                cover_letter_path = generate_cover_letter(
                    result["cover_letter_content"], safe_user, str(OUTPUT_DIR),
                )
            logger.info(
                "Streaming generation complete: %s, %s",
                resume_path, cover_letter_path,
            )

            ats_findings: dict | None = None
            if resolved_output_format == ".docx":
                try:
                    from db.ats_roundtrip import run_ats_roundtrip
                    ats_findings = run_ats_roundtrip(resume_path, result["resume_content"])
                    if ats_findings["status"] != "pass":
                        logger.warning(
                            "ATS round-trip %s on %s: %s",
                            ats_findings["status"], resume_path, ats_findings["notes"],
                        )
                except Exception as exc:
                    logger.warning("ATS round-trip check failed to run: %s", exc)
                    ats_findings = {"status": "not_run", "notes": [f"check raised: {exc}"]}

            # KW6 guard — mirror the non-streaming route (warn-only).
            date_findings = _check_date_grounding(context_set, result)

            app_run_id = context_set.get("application_run_id")
            if app_run_id is not None:
                try:
                    if resolved_persona_id is not None:
                        _persist_run_persona(int(app_run_id), resolved_persona_id)
                    _persist_corpus_generation_to_db(
                        int(app_run_id), result, ats_findings=ats_findings,
                    )
                except Exception as exc:
                    logger.error(
                        "Corpus generation persist failed (run_id=%s): %s",
                        app_run_id, exc, exc_info=True,
                    )

            summary_parts = []
            if refinement_notes.strip():
                summary_parts.append("refinement")
            if context_set.get("edited_resume_text") or context_set.get("edited_cover_letter_text"):
                summary_parts.append("from edited baseline")
            summary = " + ".join(summary_parts) if summary_parts else "fresh generation"

            new_context_path = save_iteration_context(
                parent_context=context_set,
                parent_path=str(cp),
                last_generated_resume=result["resume_content"],
                last_generated_cover_letter=result["cover_letter_content"],
                username=safe_user,
                base_dir=str(OUTPUT_DIR),
                action="generate",
                summary=summary,
            )
            new_iteration = int(context_set.get("iteration", 0) or 0) + 1
            logger.info(
                "Iteration %d snapshotted: %s (parent=%s)",
                new_iteration, new_context_path, str(cp),
            )

            yield _sse("done", {
                "resume_path": resume_path,
                "cover_letter_path": cover_letter_path,
                "resume_format": resolved_output_format,
                "changes_made": result.get("changes_made", []),
                "proofread_notes": result.get("proofread_notes", []),
                "resume_preview": result["resume_content"],
                "cover_letter_preview": result.get("cover_letter_content", ""),
                "context_path": new_context_path,
                "iteration": new_iteration,
                "parent_context_path": str(cp),
                "ats_roundtrip": ats_findings,
                "date_grounding": date_findings,
                "persona_template_id": resolved_persona_id,
            })
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic API connection error during streaming generation: %s", exc)
            yield _sse("error", {
                "error": "Connection to AI service failed. Please try again.",
                "http_status": 503,
            })
        except LLMResponseError as exc:
            logger.error(
                "LLM streaming generation response failed validation after retry: %s",
                exc.validation_error,
            )
            yield _sse("error", {
                "error": "AI generation response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
                "http_status": 502,
            })
        except Exception:
            logger.exception("Streaming generation failed unexpectedly")
            yield _sse("error", {
                "error": "Internal error during generation.",
                "http_status": 500,
            })

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/validate-refinement", methods=["POST"])
def validate_refinement():
    """Scope-check a single refinement note before running generation."""
    data = request.json
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"valid": False, "reason": "Empty refinement note."}), 400
    client = _get_client()
    result = check_refinement_scope(client, note)
    return jsonify(result)


@app.route("/api/generate-cover-letter", methods=["POST"])
def run_generate_cover_letter():
    """Phase β.5 — focused cover-letter generation against the finalized résumé.

    Called from the Download step (Step 6) after the user has run a
    résumé generation. Cheaper than re-running /api/generate (no résumé
    rules, no résumé schema, no résumé tokens). Uses the finalized
    résumé from the current context's `last_generated_resume` (or the
    user's typed-in `edited_resume_text` if more recent).

    Body: {context_path, username, refinement_notes (optional)}

    Returns {cover_letter_path, cover_letter_preview, context_path}.
    Updates the existing context file in place with the new
    `last_generated_cover_letter` so subsequent /api/generate calls
    (résumé refinements) preserve the cover letter and /api/iterate-clarify
    can probe it.
    """
    from analyzer import (
        LLMResponseError,
        generate_cover_letter_against_resume,
    )

    data = request.json or {}
    username = data.get("username", "")
    context_path = data.get("context_path", "")
    refinement_notes = data.get("refinement_notes", "")

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    cp = Path(context_path)
    if not _within(cp, OUTPUT_DIR):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})
    if not analysis:
        return jsonify({"error": "No valid analysis found in context"}), 400

    # The finalized résumé is whatever's latest: edited > last_generated >
    # original resume.text. Mirrors _current_draft_text's order.
    resume_content = (
        (context_set.get("edited_resume_text") or "").strip()
        or (context_set.get("last_generated_resume") or "").strip()
        or (context_set.get("resume", {}).get("text") or "").strip()
    )
    if not resume_content:
        return jsonify({
            "error": "No résumé to base the cover letter on. "
                     "Run /api/generate first.",
            "needs_resume": True,
        }), 409

    safe_user = _safe_username(username) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    client = _get_client()
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]
    try:
        result = generate_cover_letter_against_resume(
            client, context_set, analysis, resume_content,
            refinement_notes=refinement_notes,
            username=username, run_id=run_id,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic connection error during cover-letter generate: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("Cover-letter LLM response failed validation: %s", exc.validation_error)
        return jsonify({
            "error": "AI cover-letter response was malformed after retry.",
            "detail": exc.validation_error,
        }), 502

    cl_content = (result.get("cover_letter_content") or "").strip()
    if not cl_content:
        return jsonify({"error": "LLM returned an empty cover letter."}), 502

    cover_letter_path = generate_cover_letter(cl_content, safe_user, str(OUTPUT_DIR))

    # Update the existing context with the new cover letter so the
    # iteration loop + edit-detect pick it up the same way résumé state
    # propagates. No new iteration counter bump — the cover letter is
    # additive to the current generation, not a fresh résumé revision.
    context_set["last_generated_cover_letter"] = cl_content
    # Drop any prior typed-edit shadow: the user just got a fresh
    # LLM-generated letter; the next refine cycle should diff against it.
    if "edited_cover_letter_text" in context_set:
        context_set.pop("edited_cover_letter_text", None)
    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    # Capture the cover-letter signal B.8 Part 2 will consume: persist the
    # cover-letter md onto the same run row the résumé generation wrote to, so
    # outcome-weighted recommend (B.8 Part 2) can correlate interviews with the
    # cover letters that earned them. Corpus-backed mode only (context carries
    # application_run_id); best-effort so a DB hiccup never fails the
    # generated-and-downloaded cover letter.
    app_run_id = context_set.get("application_run_id")
    if app_run_id is not None:
        try:
            _persist_cover_letter_to_db(int(app_run_id), cl_content)
        except Exception as exc:
            logger.error(
                "Cover-letter persist failed (run_id=%s): %s",
                app_run_id, exc, exc_info=True,
            )

    return jsonify({
        "cover_letter_path":    cover_letter_path,
        "cover_letter_preview": cl_content,
        "context_path":         str(cp),
        "proofread_notes":      result.get("proofread_notes", []),
    })


# ---------------------------------------------------------------------------
# Phase B.4: proposal review + clarification promotion routes
# ---------------------------------------------------------------------------


_VALID_DECISIONS = frozenset({"accept_original", "accept_edit", "reject"})


@app.route("/api/proposals/<int:proposal_id>/critique", methods=["POST"])
def critique_proposal_route(proposal_id: int):
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
            title = session.query(ExperienceTitle).filter_by(
                id=proposal.experience_title_id,
            ).first()
            if title is None:
                return jsonify({"error": "Referenced title missing"}), 404
            experience = session.query(Experience).filter_by(id=title.experience_id).first()
        else:
            return jsonify({"error": "Proposal has no subject"}), 500

        if experience is None:
            return jsonify({"error": "Proposal references missing experience"}), 500

        candidate = session.query(Candidate).filter_by(id=experience.candidate_id).first()
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        # Build experience context for the critique prompt
        official_title_row = next(
            (t for t in experience.titles if t.is_official),
            None,
        )
        existing_bullets = [
            b.text for b in sorted(experience.bullets, key=lambda x: x.display_order)
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
            (c.question, c.answer) for c in session.query(Clarification).filter_by(
                candidate_id=candidate.id,
            ).order_by(Clarification.created_at.desc()).limit(30)
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
            return jsonify({
                "error": "AI critique response was malformed.",
                "detail": exc.validation_error,
            }), 502

        proposal.llm_critique_json = json.dumps(critique)
        if user_edited_text is not None:
            proposal.user_edited_text = user_edited_text
        session.commit()

        return jsonify({
            "proposal_id": proposal.id,
            "subject_kind": subject_kind,
            "critique": critique,
        })
    finally:
        session.close()


@app.route("/api/proposals/<int:proposal_id>/decide", methods=["POST"])
def decide_proposal_route(proposal_id: int):
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
        return jsonify({
            "error": f"decision must be one of: {sorted(_VALID_DECISIONS)}",
        }), 400
    if decision == "accept_edit" and not (user_edited_text or "").strip():
        return jsonify({"error": "accept_edit requires non-empty user_edited_text"}), 400

    init_db()
    session = get_session()
    try:
        proposal = session.query(ProposalReview).filter_by(id=proposal_id).first()
        if proposal is None:
            return jsonify({"error": "Proposal not found"}), 404
        if proposal.decision != "pending" and proposal.decision != decision:
            return jsonify({
                "error": "Proposal already decided",
                "current_decision": proposal.decision,
            }), 409

        # Defense-in-depth: verify candidate ownership via the experience chain
        if proposal.bullet_id is not None:
            bullet = session.query(Bullet).filter_by(id=proposal.bullet_id).first()
            if bullet is None:
                return jsonify({"error": "Referenced bullet missing"}), 404
            experience = session.query(Experience).filter_by(id=bullet.experience_id).first()
            subject_text_before = bullet.text
            subject_kind = "bullet"
        elif proposal.experience_title_id is not None:
            title = session.query(ExperienceTitle).filter_by(
                id=proposal.experience_title_id,
            ).first()
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        # Apply the decision. The branches above ensured exactly one of
        # `bullet` / `title` is non-None — assert here to make that
        # invariant visible to the type checker.
        if decision == "accept_original":
            if subject_kind == "bullet":
                assert bullet is not None  # noqa: S101 — invariant from branch above
                bullet.is_pending_review = 0
            else:  # experience_title
                assert title is not None  # noqa: S101
                title.is_pending_review = 0
                title.truthful_enough_to_use = 1
        elif decision == "accept_edit":
            assert user_edited_text is not None  # noqa: S101 — validated above
            edit = user_edited_text.strip()
            if subject_kind == "bullet":
                assert bullet is not None  # noqa: S101
                bullet.text = edit
                bullet.is_pending_review = 0
                proposal.user_edited_text = edit
            else:
                assert title is not None  # noqa: S101
                title.title = edit
                title.is_pending_review = 0
                title.truthful_enough_to_use = 1
                proposal.user_edited_text = edit
        else:  # reject
            if subject_kind == "bullet":
                assert bullet is not None  # noqa: S101
                bullet.is_active = 0
                bullet.is_pending_review = 0
            else:
                assert title is not None  # noqa: S101
                title.is_pending_review = 0
                # Non-eligible already; nothing to set on the title row

        proposal.decision = decision
        proposal.decided_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        session.add(IterationLog(
            application_run_id=proposal.application_run_id,
            action=decision,
            summary=(
                f"{subject_kind} proposal {proposal.id}: "
                f"{decision} (was: {subject_text_before[:60]!r})"
            ),
        ))
        session.commit()

        return jsonify({
            "proposal_id": proposal.id,
            "decision": decision,
            "subject_kind": subject_kind,
        })
    finally:
        session.close()


@app.route("/api/clarifications/<int:clarification_id>/promote-to-bullet", methods=["POST"])
def promote_clarification_route(clarification_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        experience = session.query(Experience).filter_by(
            id=experience_id, candidate_id=candidate.id,
        ).first()
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
                    target_official_title=(
                        official_title_row.title if official_title_row else ""
                    ),
                    username=candidate.username,
                )
            except anthropic.APIConnectionError as exc:
                logger.error("Anthropic connection error in promote: %s", exc)
                return jsonify({"error": "Connection to AI service failed."}), 503
            except LLMResponseError as exc:
                logger.error("Promote response validation failed: %s", exc.validation_error)
                return jsonify({"error": "AI response malformed.",
                                "detail": exc.validation_error}), 502
            bullet_text = (llm_out.get("text") or "").strip()
            pattern_kind_raw = (llm_out.get("pattern_kind") or "").strip().lower()
            pattern_kind = pattern_kind_raw if pattern_kind_raw in {"xyz", "star", "car", "manual"} else "manual"
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
        recent_run = session.query(ApplicationRun).join(
            ApplicationRun.application,
        ).filter_by(candidate_id=candidate.id).order_by(
            ApplicationRun.created_at.desc(),
        ).first()
        if recent_run is not None:
            session.add(ProposalReview(
                application_run_id=recent_run.id,
                bullet_id=new_bullet.id,
                original_text=bullet_text,
                decision="pending",
            ))
            session.add(IterationLog(
                application_run_id=recent_run.id,
                action="promote_bullet",
                summary=(
                    f"Promoted clarification {clarification.id} → "
                    f"bullet {new_bullet.id} on experience {experience.id}"
                ),
            ))

        clarification.is_promoted_to_bullet = 1
        session.commit()

        return jsonify({
            "bullet_id": new_bullet.id,
            "experience_id": experience.id,
            "text": bullet_text,
            "pattern_kind": pattern_kind,
            "rationale": rationale,
            "proposal_review_anchored_to_run_id": recent_run.id if recent_run else None,
        })
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase C.2: persona template routes (bundled + user-uploaded)
# ---------------------------------------------------------------------------


PERSONAS_DIR = BASE_DIR / "personas"
BUNDLED_PERSONAS_DIR = PERSONAS_DIR / "bundled"


def _persona_dict(template) -> dict:
    """Serialize a persona_template row for the API response."""
    return {
        "id": template.id,
        "name": template.name,
        "path": template.path,
        "thumbnail_path": template.thumbnail_path,
        "description": template.description,
        "source": template.source,
        "is_default": bool(template.is_default),
        "candidate_id": template.candidate_id,
        "created_at": template.created_at,
    }


def _persona_dicts_safe(templates) -> list[dict]:
    """Serialize a list of persona_template rows, skipping (and logging)
    any row that fails serialization.

    Rationale (2026-05-27 handoff §4): the user reported
    `GET /api/users/<u>/personas 500` across several smoke rounds.
    The route's serializer pattern was `[_persona_dict(t) for t in rows]`
    — one bad row (e.g. a NULL in a NOT-NULL column from a botched
    seed, an FK pointing at a deleted candidate, a path containing a
    chararcter the JSON encoder can't handle) brings down the whole
    response with no per-row visibility.

    Per-row try/except lets the surviving rows render and writes the
    offending row's id to the server log so the next agent (or this
    user on next smoke) can pin the exact data problem. Returns a
    list; logs warnings for skipped rows.
    """
    out: list[dict] = []
    for t in templates:
        try:
            out.append(_persona_dict(t))
        except Exception as exc:
            # Identify the row by id when possible — if id itself is
            # broken, fall back to the repr so we have SOME handle.
            try:
                row_id: object = t.id
            except Exception:
                row_id = repr(t)
            logger.warning(
                "_persona_dict failed for persona_template row=%s: %s: %s",
                row_id, type(exc).__name__, exc,
            )
    return out


def _resolve_persona_template_path(persona_template_id: int) -> str | None:
    """Look up a persona_template's on-disk path. None if not found / missing.

    The DB stores `path` relative to the repo root (e.g.
    "personas/bundled/classic.docx"). We resolve to absolute, verify
    containment under PERSONAS_DIR (defense-in-depth), and return the
    string path generator.py expects.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_template_id).first()
        if row is None:
            return None
        disk_path = (BASE_DIR / row.path).resolve()
        if not disk_path.exists() or not _within(disk_path, PERSONAS_DIR):
            logger.warning(
                "Persona template id=%s has invalid path %s",
                persona_template_id, row.path,
            )
            return None
        return str(disk_path)
    finally:
        session.close()


def _resolve_default_persona_template_path(
    username: str | None = None,
    application_id: int | None = None,
) -> str | None:
    """Resolve the default template path for the current candidate + JD role.

    Lookup priority (first match wins):
      1. Candidate's `is_default = 1` template matching this application's
         `target_role_tag_id`, if both are known. (E.g. the user marked a
         "Design IC" template default; this application's JD was tagged
         "Design IC".)
      2. Candidate's `is_default = 1` template with `primary_role_tag_id
         IS NULL` — the candidate's general default that applies when
         no role-specific template wins.
      3. Bundled `Classic Single-Column` as the maximally ATS-safe
         baseline (the original behavior; preserved for back-compat
         and for routes that don't pass a username).

    The partial unique index `ix_persona_template_default` enforces at
    most one `is_default = 1` per (candidate_id, primary_role_tag_id),
    so the candidate-scoped queries return at most one row.

    Used by /api/generate when no explicit `persona_template_id` was
    supplied and no legacy file-based resume path is available.
    """
    from db.models import Application, Candidate, PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        # Priority 1+2: candidate-scoped defaults (require username)
        if username:
            candidate = session.query(Candidate).filter_by(username=username).first()
            if candidate is not None:
                role_tag_id: int | None = None
                if application_id is not None:
                    app_row = session.query(Application).filter_by(id=application_id).first()
                    if app_row is not None:
                        role_tag_id = app_row.target_role_tag_id

                # Priority 1: role-specific default
                if role_tag_id is not None:
                    row = session.query(PersonaTemplate).filter_by(
                        candidate_id=candidate.id,
                        primary_role_tag_id=role_tag_id,
                        is_default=1,
                    ).first()
                    if row is not None:
                        return _resolve_persona_template_path(row.id)

                # Priority 2: general default (no role tag)
                row = session.query(PersonaTemplate).filter_by(
                    candidate_id=candidate.id,
                    primary_role_tag_id=None,
                    is_default=1,
                ).first()
                if row is not None:
                    return _resolve_persona_template_path(row.id)

        # Priority 3: bundled Classic (existing fallback)
        row = session.query(PersonaTemplate).filter_by(
            source="bundled", name="Classic Single-Column",
        ).first()
        if row is None:
            return None
        return _resolve_persona_template_path(row.id)
    finally:
        session.close()


@app.route("/api/personas/bundled", methods=["GET"])
def list_bundled_personas():
    """Return the catalog of bundled (shipped-with-app) persona templates.

    Bundled rows have candidate_id=NULL and source='bundled'. They're shared
    across every candidate. The frontend persona gallery surfaces these
    above the user's own uploads.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    # Wrapped with logger.exception (2026-05-26) — this route was
    # silently 500'ing under specific conditions (per the
    # "Corpus tab: 5xx on first-load API calls" entry in
    # RELEASE_CHECKLIST) and the bare default-handler 500 dropped the
    # traceback. Logging here surfaces the actual cause in the Flask
    # log; the JSON detail field surfaces the exception class in dev-
    # console for quick triage.
    try:
        init_db()
        session = get_session()
        try:
            rows = session.query(PersonaTemplate).filter_by(source="bundled").all()
            return jsonify(_persona_dicts_safe(rows))
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_bundled_personas failed")
        return jsonify({
            "error": "Failed to load bundled personas",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/users/<username>/personas", methods=["GET"])
def list_user_personas(username: str):
    """Return bundled + this candidate's uploaded persona templates."""
    from db.models import Candidate, PersonaTemplate
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    # Wrapped with logger.exception (2026-05-26) — see list_bundled_personas.
    try:
        init_db()
        session = get_session()
        try:
            candidate = session.query(Candidate).filter_by(username=safe_user).first()
            if candidate is None:
                # Read precondition unmet (no corpus row yet) is NOT a conflict —
                # return 200 with an empty, success-shaped body + the flag. The
                # frontend keys off `needs_onboarding` to show the import CTA; a
                # naive consumer just sees empty lists. (POST writes keep 409 —
                # see AGENTS-noted contract.)
                return jsonify({
                    "bundled": [],
                    "owned": [],
                    "needs_onboarding": True,
                })
            bundled = session.query(PersonaTemplate).filter_by(source="bundled").all()
            owned = session.query(PersonaTemplate).filter_by(candidate_id=candidate.id).all()
            return jsonify({
                "bundled": _persona_dicts_safe(bundled),
                "owned": _persona_dicts_safe(owned),
            })
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_user_personas failed for user=%s", safe_user)
        return jsonify({
            "error": "Failed to load personas",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/users/<username>/personas", methods=["POST"])
def upload_user_persona(username: str):
    """Upload a user-owned .docx persona template.

    Multipart body: `file` (the .docx), `name` (display label, optional —
    defaults to the filename stem). The .docx is saved under
    `personas/{user}/` and a persona_template row is created with
    candidate_id=<this user> and source='user_upload'.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Multipart 'file' field is required"}), 400
    if Path(file.filename).suffix.lower() != ".docx":
        return jsonify({"error": "Only .docx persona templates are supported"}), 400

    init_db()
    session = get_session()
    try:
        candidate = _get_or_provision_candidate(session, safe_user)

        safe_name = secure_filename(file.filename)
        user_persona_dir = PERSONAS_DIR / safe_user
        user_persona_dir.mkdir(parents=True, exist_ok=True)
        target = user_persona_dir / safe_name
        if not _within(target, PERSONAS_DIR):
            return jsonify({"error": "Invalid persona path"}), 403
        file.save(str(target))

        display_name = (request.form.get("name") or Path(safe_name).stem).strip()
        relative_path = f"personas/{safe_user}/{safe_name}"
        row = PersonaTemplate(
            candidate_id=candidate.id,
            name=display_name or safe_name,
            path=relative_path,
            source="user_upload",
            is_default=0,
        )
        session.add(row)
        session.commit()
        return jsonify(_persona_dict(row)), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/personas/<int:persona_id>", methods=["GET"])
def get_persona(persona_id: int):
    """Return one persona row's metadata. Accessible to anyone (bundled +
    owned both readable for preview UI)."""
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        return jsonify(_persona_dict(row))
    finally:
        session.close()


@app.route("/api/personas/<int:persona_id>", methods=["PUT"])
def update_persona(persona_id: int):
    """Update name / is_default on a persona row.

    Body: `{name?: str, is_default?: bool}`. Bundled rows are read-only at
    this layer — only candidate-owned personas can be updated. `is_default=1`
    on one persona for a (candidate, primary_role_tag) clears the same flag
    on any sibling personas for that (candidate, tag) pair.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    data = request.json or {}
    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        if row.source == "bundled":
            return jsonify({"error": "Bundled personas are immutable"}), 403

        if "name" in data:
            new_name = (data.get("name") or "").strip()
            if not new_name:
                return jsonify({"error": "name cannot be empty"}), 400
            row.name = new_name

        if "is_default" in data:
            new_default = 1 if data.get("is_default") else 0
            if new_default == 1 and row.candidate_id is not None:
                # Clear existing default in the same (candidate_id, primary_role_tag_id) slot
                session.query(PersonaTemplate).filter_by(
                    candidate_id=row.candidate_id,
                    primary_role_tag_id=row.primary_role_tag_id,
                    is_default=1,
                ).update({"is_default": 0})
            row.is_default = new_default

        session.commit()
        return jsonify(_persona_dict(row))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/personas/<int:persona_id>", methods=["DELETE"])
def delete_persona(persona_id: int):
    """Delete a user-owned persona template (file + DB row).

    Bundled rows are refused (403). User uploads are deleted both from disk
    and from the DB. Soft delete isn't necessary here because no FK references
    persona_template (the audit chain via application_run.persona_template_id
    uses ON DELETE SET NULL, so historical runs survive cleanly).
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        if row.source == "bundled":
            return jsonify({"error": "Bundled personas are immutable"}), 403

        disk_path = BASE_DIR / row.path
        if disk_path.exists() and _within(disk_path, PERSONAS_DIR):
            disk_path.unlink()

        session.delete(row)
        session.commit()
        return jsonify({"deleted": persona_id})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/personas/<int:persona_id>/download", methods=["GET"])
def download_persona(persona_id: int):
    """Stream a persona's .docx file for the preview UI."""
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        disk_path = BASE_DIR / row.path
        if not disk_path.exists():
            return jsonify({"error": "Persona file missing on disk"}), 404
        # Containment: bundled lives under personas/bundled/, user uploads
        # under personas/{user}/ — both inside PERSONAS_DIR.
        if not _within(disk_path, PERSONAS_DIR):
            return jsonify({"error": "Invalid persona path"}), 403
        return send_file(str(disk_path), as_attachment=True, download_name=f"{row.name}.docx")
    finally:
        session.close()


def _latest_generated_resume_md(candidate_id: int) -> str | None:
    """Most recent non-empty generated_resume_md across a candidate's
    application runs (Workstream C preview). None when the user hasn't
    generated yet."""
    from db.models import Application, ApplicationRun
    from db.session import get_session

    session = get_session()
    try:
        row = (
            session.query(ApplicationRun)
            .join(Application, ApplicationRun.application_id == Application.id)
            .filter(
                Application.candidate_id == candidate_id,
                ApplicationRun.generated_resume_md.isnot(None),
            )
            .order_by(ApplicationRun.created_at.desc())
            .first()
        )
        return row.generated_resume_md if row else None
    finally:
        session.close()


@app.route("/api/personas/<int:persona_id>/preview", methods=["POST"])
def preview_persona_with_resume(persona_id: int):
    """Render the user's latest generated resume through this persona
    template and stream the real .docx (Workstream C #6). Honest artifact
    reuse via generate_resume — no separate rendering engine.

    Body: {username}. Touches the filesystem (writes + streams a .docx),
    so both _safe_username and _within guards apply.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    data = request.json or {}
    username = data.get("username", "")
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        disk_path = (BASE_DIR / row.path).resolve()
        if not disk_path.exists() or not _within(disk_path, PERSONAS_DIR):
            return jsonify({"error": "Invalid persona path"}), 403
        candidate = _get_or_provision_candidate(session, safe_user)
        resume_md = _latest_generated_resume_md(candidate.id)
        if not resume_md:
            return jsonify({
                "error": "No generated resume yet — run GENERATE in an "
                         "application first, then preview a template against it.",
            }), 409
    finally:
        session.close()

    out_path = generate_resume(
        resume_md, ".docx", safe_user, str(OUTPUT_DIR),
        template_path=str(disk_path),
    )
    return send_file(
        str(out_path), as_attachment=True,
        download_name=f"preview_{row.name}.docx",
    )


@app.route("/api/applications/<int:application_id>/preview", methods=["GET"])
def preview_application_html(application_id: int):
    """Render the candidate's résumé corpus + application-scoped overrides
    as a self-contained HTML page (Phase β.4 / β.6 — corpus-direct live
    preview).

    Query params:
      template_id  — persona to render through. If omitted, falls back
                     to the β.1 default-resolution chain (candidate's
                     is_default for the JD role → general default →
                     bundled Classic).
      context_path — optional path to a context_*.json file. When
                     present, composition_overrides (pin/exclude/added,
                     pinned_summary_id) and llm_summary_recommendation /
                     llm_recommendations from that file shape the
                     rendered output. Must resolve under OUTPUT_DIR.

    Architectural shift (post β.6 hands-on review):
      Earlier shape: read the most recent `resume_*.jsonresume.json`
      sidecar written by `/api/generate`. That coupled the preview to a
      prior generate call, so users couldn't see template effects until
      they paid for an LLM round-trip — and afterwards the preview
      reflected the LAST-GENERATED résumé even if they kept editing the
      corpus. Both points were called out in the hands-on review (#1, #3).

      Current shape: build a JSON Resume document DIRECTLY from
      Candidate + Experience + Bullet + SummaryItem rows via
      `corpus_to_json_resume.build_json_resume_from_corpus`. The result
      reflects the candidate's live curation state — chosen summary
      variant (pin > recommendation > first-active), bullets honoring
      composition_overrides (pin/exclude/added) — without any generate
      having run.

    Renders via `pdf_render.render_html_string` — same Jinja2 template
    that produces the PDF, so the preview IS the future PDF (WYSIWYG).
    Returns text/html with CSS inlined into a <style> block, designed
    to be loaded into a sandboxed <iframe src=...> with no external
    CSS resolution.

    Filesystem + ownership guards: `_safe_username` runs inside
    `_load_application_owned`; `_within` runs inside the persona-path
    resolver. No filesystem reads happen here beyond the template + CSS
    files under PERSONAS_DIR.
    """
    from corpus_to_json_resume import build_json_resume_from_corpus
    from db.session import get_session, init_db
    from pdf_render import render_html_string

    init_db()
    session = get_session()
    try:
        # _load_application_owned runs _safe_username on the owning
        # candidate; the explicit recheck just below keeps the
        # route-security-lint hook happy when scanning this block.
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or candidate is None:
            return jsonify({"error": "Application not found"}), 404
        if not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        # Resolve template path — explicit template_id wins; else fall
        # back to the β.1 default-resolution chain.
        template_id_raw = request.args.get("template_id")
        docx_template_path: str | None = None
        if template_id_raw:
            try:
                template_id = int(template_id_raw)
            except ValueError:
                return jsonify({"error": "template_id must be an integer"}), 400
            docx_template_path = _resolve_persona_template_path(template_id)
            if docx_template_path is None:
                return jsonify({"error": "Template not found"}), 404
        else:
            docx_template_path = _resolve_default_persona_template_path(
                username=candidate.username, application_id=application_id,
            )

        if docx_template_path is None:
            return jsonify({"error": "No template available"}), 500

        # The HTML template is the .html sibling of the resolved .docx.
        # Fall back to the bundled Classic if the chosen persona doesn't
        # ship an .html companion yet — keeps the preview working as more
        # personas pick up HTML companions over time.
        from pdf_render import html_template_path_for
        html_path = html_template_path_for(docx_template_path)
        if html_path is None:
            html_path = BASE_DIR / "personas" / "bundled" / "classic.html"
            if not html_path.exists():
                return jsonify({"error": "No HTML template available"}), 500

        # Optional context_path query param — the frontend passes the
        # active context file. Two render sources, in priority order:
        #   1. WYSIWYG Option 1 (v1.0.5): once /api/generate has run, the
        #      context carries `last_generated_json_resume` — the
        #      deterministic md_to_json_resume() of the exact markdown the
        #      user downloads. Serve THAT so the preview IS the future
        #      document (preview == download). A generate having run means
        #      curation already happened, so the recommendations gate below
        #      does not apply on this path.
        #   2. Pre-generate: build the JSON Resume directly from the corpus,
        #      gated on llm_recommendations. Per user requirement
        #      (2026-05-26): the preview must reflect the JD-specific curated
        #      selection, never silently fall back to "all active bullets"
        #      when recommendations are missing; missing → placeholder HTML
        #      so the iframe surfaces an honest empty-state instead of an
        #      inflated full-corpus render.
        # We validate containment under OUTPUT_DIR so a malicious caller
        # can't read outside.
        ctx_path_raw = request.args.get("context_path", "").strip()
        ctx_path_arg: str | None = None
        cached_json_resume: dict | None = None
        ctx_has_recommendations = False
        if ctx_path_raw:
            cp = Path(ctx_path_raw)
            if _within(cp, OUTPUT_DIR) and cp.exists():
                ctx_path_arg = str(cp)
                try:
                    ctx_data = json.loads(cp.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    ctx_data = {}
                cached = ctx_data.get("last_generated_json_resume")
                if isinstance(cached, dict) and _json_resume_has_content(cached):
                    cached_json_resume = cached
                else:
                    # Non-empty dict of recommendations counts as "curation
                    # has happened." Empty dict (or missing key) means
                    # recommend_bullets either hasn't run or failed.
                    ctx_has_recommendations = bool(ctx_data.get("llm_recommendations") or {})

        if cached_json_resume is not None:
            # WYSIWYG path — serve the cached generate output verbatim.
            json_doc = cached_json_resume
        else:
            if not ctx_has_recommendations:
                return _preview_placeholder_html(html_path), 200, {
                    "Content-Type": "text/html; charset=utf-8",
                }
            # Build the JSON Resume directly from the candidate's corpus,
            # applying composition_overrides + chosen-summary resolution
            # scoped to THIS application.
            json_doc = build_json_resume_from_corpus(
                session, candidate.id,
                application_id=application_id,
                context_path=ctx_path_arg,
            )
    finally:
        session.close()

    html_str = render_html_string(json_doc, html_template_path=html_path)
    html_str = _inline_persona_css(html_str, html_path)
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}


def _preview_placeholder_html(html_path: Path) -> str:
    """Self-contained HTML for the Step 6 iframe when this application
    has no LLM recommendations yet (recommend_bullets either hasn't run
    or failed).

    Per user requirement (2026-05-26): the preview must show
    "what will be produced," not "the un-curated full corpus." When
    curation is missing we explicitly surface that state instead of
    silently rendering all active bullets — that prior behavior gave
    a misleading 3-page preview that didn't represent the final
    download.

    `html_path` is accepted for future use (e.g. inlining the persona's
    background color into the placeholder) but currently unused — the
    placeholder is template-agnostic on purpose.
    """
    del html_path  # reserved for a future style-matching pass
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Preview waiting on curation</title>
  <style>
    body {
      margin: 0;
      padding: 48px 32px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.55;
      color: #444;
      background: #fafafa;
    }
    .placeholder-wrap {
      max-width: 520px;
      margin: 0 auto;
      text-align: center;
    }
    h1 {
      font-size: 18px;
      font-weight: 600;
      color: #222;
      margin: 0 0 12px;
    }
    p { margin: 0 0 12px; }
    .hint {
      font-size: 12px;
      color: #777;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #eee;
    }
  </style>
</head>
<body>
  <div class="placeholder-wrap">
    <h1>Preview is waiting on curation</h1>
    <p>This preview reflects the bullets the AI recommended for THIS job, not your full corpus. Run analysis (Step 1) so the recommendation pass can curate the right set.</p>
    <p class="hint">If you've already analyzed and still see this message, the recommendation pass may have failed silently — check the dev console for an error and re-run analysis.</p>
  </div>
</body>
</html>"""


def _json_resume_has_content(doc: dict) -> bool:
    """True when a JSON Resume doc carries renderable content.

    `md_to_json_resume("")` (and any blank/whitespace markdown) returns an
    empty skeleton — all sections empty, no basics.name. The application
    preview uses this to decide whether a cached `last_generated_json_resume`
    is worth serving (WYSIWYG Option 1) or whether to fall back to the
    corpus-direct render. Guards the degenerate "generate produced nothing"
    case so the preview never renders an empty document.
    """
    basics = doc.get("basics") or {}
    if basics.get("name") or basics.get("summary"):
        return True
    return any(doc.get(key) for key in ("work", "skills", "education", "projects"))


@app.route("/api/applications/<int:application_id>/cover-letter-preview", methods=["GET"])
def preview_cover_letter_html(application_id: int):
    """Render the application's generated cover letter as a styled,
    self-contained business-letter HTML page (v1.0.5 — Step 6 redesign).

    The cover-letter analogue of `preview_application_html`. Unlike the
    résumé preview (which renders the candidate's corpus through a persona
    template), the cover letter has no corpus: the generated markdown IS the
    document. This route reads `last_generated_cover_letter` from the supplied
    context file and renders it through the shared
    `personas/cover_letter.html` business-letter shell, using the chosen
    persona's font (plainly) per the 2026-05-26 styling decisions.

    Query params:
      template_id  — persona whose font the letter should match. Omitted →
                     the β.1 default-resolution chain. The letter only borrows
                     the font; its layout is the shared business-letter shell.
      context_path — path to the post-generate context_*.json carrying
                     `last_generated_cover_letter`. Must resolve under
                     OUTPUT_DIR. Missing / no cover letter yet → placeholder.

    No cover letter exists yet (pre-generate, or résumé-only generation) →
    placeholder HTML so the iframe surfaces an honest empty-state.

    Filesystem + ownership guards: `_safe_username` runs inside
    `_load_application_owned` and is rechecked explicitly; `context_path` is
    confirmed `_within(OUTPUT_DIR)`. No filesystem reads happen beyond the
    context file, the cover-letter template, and the persona CSS (for the font).
    """
    from db.session import get_session, init_db
    from pdf_render import persona_font_family, render_cover_letter_html

    init_db()
    session = get_session()
    try:
        # _load_application_owned runs _safe_username on the owning candidate;
        # the explicit recheck just below keeps the route-security-lint hook
        # happy when scanning this block.
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or candidate is None:
            return jsonify({"error": "Application not found"}), 404
        if not _safe_username(candidate.username):
            return jsonify({"error": "Application not found"}), 404

        # Resolve the persona only to borrow its font — explicit template_id
        # wins, else the β.1 default chain. A missing/owned persona without a
        # .css falls back to the neutral business stack inside
        # persona_font_family, so font resolution never blocks the preview.
        template_id_raw = request.args.get("template_id")
        docx_template_path: str | None = None
        if template_id_raw:
            try:
                template_id = int(template_id_raw)
            except ValueError:
                return jsonify({"error": "template_id must be an integer"}), 400
            docx_template_path = _resolve_persona_template_path(template_id)
            if docx_template_path is None:
                return jsonify({"error": "Template not found"}), 404
        else:
            docx_template_path = _resolve_default_persona_template_path(
                username=candidate.username, application_id=application_id,
            )
        css_path = (
            Path(docx_template_path).with_suffix(".css")
            if docx_template_path else None
        )
        font_family = persona_font_family(css_path)

        # Read the generated cover letter from the supplied context file,
        # validating containment under OUTPUT_DIR so a malicious caller can't
        # read outside.
        ctx_path_raw = request.args.get("context_path", "").strip()
        cover_letter_md = ""
        if ctx_path_raw:
            cp = Path(ctx_path_raw)
            if _within(cp, OUTPUT_DIR) and cp.exists():
                try:
                    ctx_data = json.loads(cp.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    ctx_data = {}
                cover_letter_md = (ctx_data.get("last_generated_cover_letter") or "").strip()
    finally:
        session.close()

    if not cover_letter_md:
        return _cover_letter_placeholder_html(), 200, {
            "Content-Type": "text/html; charset=utf-8",
        }

    cover_template = BASE_DIR / "personas" / "cover_letter.html"
    html_str = render_cover_letter_html(
        cover_letter_md, font_family=font_family, template_path=cover_template,
    )
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}


def _cover_letter_placeholder_html() -> str:
    """Self-contained HTML for the Step 6 cover-letter iframe when no cover
    letter has been generated yet (résumé-only generation, or pre-generate).

    Mirrors `_preview_placeholder_html` — an honest empty-state instead of a
    blank frame.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>No cover letter yet</title>
  <style>
    body {
      margin: 0;
      padding: 48px 32px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.55;
      color: #444;
      background: #fafafa;
    }
    .placeholder-wrap { max-width: 520px; margin: 0 auto; text-align: center; }
    h1 { font-size: 18px; font-weight: 600; color: #222; margin: 0 0 12px; }
    p { margin: 0 0 12px; }
  </style>
</head>
<body>
  <div class="placeholder-wrap">
    <h1>No cover letter yet</h1>
    <p>Click <strong>+ Generate cover letter</strong> to write one tailored to this job. It will preview here, styled to match your chosen résumé template.</p>
  </div>
</body>
</html>"""


@app.route("/api/users/<string:username>/preview", methods=["GET"])
def preview_candidate_html(username: str):
    """Render the candidate's résumé corpus as a self-contained HTML page
    WITHOUT an application in scope (pre-application preview).

    Same shape as the application-scoped preview, but with no
    `application_id` → no composition_overrides, no recommended summary,
    no pin/exclude. The user sees what their raw corpus looks like
    through this template — the canonical "show me how my résumé renders
    with Classic / Modern" answer.

    Query params:
      template_id  — same semantics as the per-application route.
    """
    from corpus_to_json_resume import build_json_resume_from_corpus
    from db.models import Candidate
    from db.session import get_session, init_db
    from pdf_render import html_template_path_for, render_html_string

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409

        template_id_raw = request.args.get("template_id")
        docx_template_path: str | None = None
        if template_id_raw:
            try:
                template_id = int(template_id_raw)
            except ValueError:
                return jsonify({"error": "template_id must be an integer"}), 400
            docx_template_path = _resolve_persona_template_path(template_id)
            if docx_template_path is None:
                return jsonify({"error": "Template not found"}), 404
        else:
            docx_template_path = _resolve_default_persona_template_path(
                username=candidate.username, application_id=None,
            )

        if docx_template_path is None:
            return jsonify({"error": "No template available"}), 500

        html_path = html_template_path_for(docx_template_path)
        if html_path is None:
            html_path = BASE_DIR / "personas" / "bundled" / "classic.html"
            if not html_path.exists():
                return jsonify({"error": "No HTML template available"}), 500

        json_doc = build_json_resume_from_corpus(
            session, candidate.id, application_id=None,
        )
    finally:
        session.close()

    html_str = render_html_string(json_doc, html_template_path=html_path)
    html_str = _inline_persona_css(html_str, html_path)
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}


def _inline_persona_css(html_str: str, html_path: Path) -> str:
    """Replace `<link rel="stylesheet" href="*.css">` with an inline
    `<style>` block so the response is fully self-contained — iframes
    load it without resolving relative CSS against the / route.
    Best-effort: missing CSS file is logged and left as-is."""
    css_path = html_path.with_suffix(".css")
    if not css_path.exists():
        return html_str
    try:
        css_str = css_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("CSS inline failed for %s: %s", css_path, exc)
        return html_str
    return re.sub(
        r'<link\s+rel="stylesheet"\s+href="[^"]+\.css"\s*/?>',
        f"<style>\n{css_str}\n</style>",
        html_str, count=1,
    )


_PAGED_PREVIEW_INJECTION = """
<style>
  /* Paged.js styling for in-browser preview. Each .pagedjs_page is a
     visible Letter-sized "page card" on a neutral trough — what you'd
     see if you exported the same HTML to PDF and laid the pages side-
     by-side. */
  html, body { background: #d6d8da; margin: 0; }
  .pagedjs_pages {
    padding: 16px 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .pagedjs_page {
    background: #fff !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    border: 1px solid #b5b8bb;
  }
</style>
<script>
  // Turn OFF paged.js's built-in auto-run. The bundled polyfill's auto path
  // does `await previewer.preview()` with NO `.catch()`
  // (static/vendor/paged.polyfill.js ~L33239), so an edge-case layout throw
  // — Cannot-read-getBoundingClientRect-of-null on sparse / unusual content —
  // escapes as an uncaught promise rejection. That was the cosmetic console
  // noise tracked at RELEASE_CHECKLIST.md "paged.js polyfill ... getBounding-
  // ClientRect of null". We disable auto-run and drive the previewer
  // ourselves below, inside try/catch + `.catch()`, so it can't leak. Must be
  // set BEFORE the polyfill `<script>` executes (it reads PagedConfig on load).
  window.PagedConfig = { auto: false };
  // Belt-and-suspenders for the paged.js paths the awaited preview() promise
  // below does NOT cover. paged.js can throw from an internal layout callback
  // that isn't on the chain we `.catch()` — either as a stray async rejection
  // or a synchronous throw inside a requestAnimationFrame / event handler. The
  // two listeners swallow ONLY paged-origin throws (by message or by the
  // paged.polyfill source file); real app errors — different message, different
  // file — surface in the console normally.
  window.addEventListener('unhandledrejection', function (e) {
    var msg = (e.reason && (e.reason.message || e.reason.toString())) || '';
    if (msg.indexOf('getBoundingClientRect') !== -1 ||
        msg.indexOf('getAttribute is not a function') !== -1) {
      e.preventDefault();
    }
  });
  window.addEventListener('error', function (e) {
    var src = (e.filename || '') + '';
    if (src.indexOf('paged.polyfill') !== -1) {
      e.preventDefault();
      return true;
    }
  });
</script>
<script src="/static/vendor/paged.polyfill.js"></script>
<script>
  // Drive paged.js manually now that auto-run is disabled. `preview()` with no
  // args lays out the current document body — identical to the auto path's
  // defaults. The try/catch guards a synchronous throw; the `.catch()` guards
  // an async layout rejection. Either way we still postMessage the page count
  // so the wizard's "Page N of M" toolbar updates (the pagedjs_rendered
  // contract). A 1.5s fallback covers the rare case the promise never settles.
  (function () {
    function send() {
      var pages = document.querySelectorAll('.pagedjs_page').length;
      try { window.parent.postMessage({ type: 'pagedjs_rendered', pages: pages }, '*'); }
      catch (e) { /* same-origin only; safe to ignore */ }
    }
    function run() {
      try {
        new window.Paged.Previewer().preview()
          .then(send)
          .catch(function () { send(); });
      } catch (e) {
        send();
      }
    }
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      run();
    } else {
      document.addEventListener('DOMContentLoaded', run);
    }
    setTimeout(send, 1500);
  })();
</script>
"""


def _inject_paged_polyfill(html_str: str) -> str:
    """Append paged.js + a small init script before `</body>` so the
    preview iframe renders content as discrete Letter-sized pages —
    real page boundaries, not a scroll-height estimate.

    Paged.js is bundled as `/static/vendor/paged.polyfill.js` (MIT,
    v0.4.3). The script auto-polyfills CSS @page rules. The init
    callback postMessages the rendered page count to the parent
    frame so the wizard toolbar can show "Page N of M" accurately.

    The PDF render path does NOT go through this helper —
    `pdf_render.render_pdf()` uses Playwright's `page.pdf()` which
    handles @page CSS natively. Paged.js is browser-preview only.
    """
    if "</body>" not in html_str:
        return html_str + _PAGED_PREVIEW_INJECTION
    return html_str.replace("</body>", _PAGED_PREVIEW_INJECTION + "</body>", 1)


# ---------------------------------------------------------------------------
# Phase D.1: Career Corpus CRUD routes (experiences / bullets / titles / tags)
# ---------------------------------------------------------------------------


def _experience_summary_dict(exp) -> dict:
    """Compact experience row for the Career Corpus list view."""
    official = next((t for t in exp.titles if t.is_official), None)
    active_bullets = [b for b in exp.bullets if b.is_active]
    pending_bullets = [b for b in active_bullets if b.is_pending_review]
    return {
        "id": exp.id,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "display_order": exp.display_order,
        "summary": exp.summary,
        "official_title": official.title if official else None,
        "title_count": len(exp.titles),
        "bullet_count_active": len(active_bullets),
        "bullet_count_pending": len(pending_bullets),
    }


def _normalize_tag_value(s: str) -> str:
    """Canonical tag form: lowercase, trimmed, non-alphanumerics → single
    hyphens (e.g. "AI / ML" → "ai-ml"). Mirrors the normalization the
    plan's Tag schema specifies; display_value keeps the user's casing."""
    s = (s or "").strip().lower()
    out = re.sub(r"[^a-z0-9]+", "-", s)
    return out.strip("-")


def _tag_list(tag_links) -> list[dict]:
    """Serialize a bullet/title's tag_links (each carries .tag) for the UI."""
    out = []
    for link in tag_links:
        t = link.tag
        if t is None:
            continue
        out.append({
            "id": t.id, "value": t.value,
            "display_value": t.display_value, "kind": t.kind,
        })
    return sorted(out, key=lambda d: d["value"])


def _experience_detail_dict(exp) -> dict:
    """Full experience payload for the inline expand view."""
    titles = sorted(exp.titles, key=lambda t: (0 if t.is_official else 1, t.id))
    bullets = sorted(
        (b for b in exp.bullets if b.is_active),
        key=lambda b: b.display_order,
    )
    return {
        "id": exp.id,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "display_order": exp.display_order,
        "summary": exp.summary,
        "titles": [
            {
                "id": t.id, "title": t.title,
                "is_official": bool(t.is_official),
                "truthful_enough_to_use": bool(t.truthful_enough_to_use),
                "is_pending_review": bool(t.is_pending_review),
                "source": t.source, "notes": t.notes,
                "tags": _tag_list(t.tag_links),
            }
            for t in titles
        ],
        "bullets": [
            {
                "id": b.id, "text": b.text,
                "display_order": b.display_order,
                "is_active": bool(b.is_active),
                "is_pending_review": bool(b.is_pending_review),
                "has_outcome": bool(b.has_outcome),
                "pattern_kind": b.pattern_kind,
                "source": b.source,
                "tags": _tag_list(b.tag_links),
            }
            for b in bullets
        ],
    }


@app.route("/api/users/<username>/experiences", methods=["GET"])
def list_experiences(username: str):
    """Return the candidate's experiences in display order (newest-first by
    start_date). Used by the Career Corpus tab's timeline."""
    from db.models import Candidate, Experience
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
            rows = session.query(Experience).filter_by(
                candidate_id=candidate.id,
            ).order_by(Experience.start_date.desc(), Experience.id.desc()).all()
            return jsonify([_experience_summary_dict(e) for e in rows])
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_experiences failed for user=%s", safe_user)
        return jsonify({
            "error": "Failed to load corpus",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/users/<username>/experiences", methods=["POST"])
def create_experience(username: str):
    """Create a new experience under this candidate.

    Body: {company, start_date (YYYY-MM), end_date?, location?, summary?}.
    Returns the full detail payload so the UI can expand it immediately.
    """
    from db.models import Experience
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    data = request.json or {}
    company = (data.get("company") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    if not company:
        return jsonify({"error": "company is required"}), 400
    if not re.fullmatch(r"\d{4}-\d{2}", start_date):
        return jsonify({"error": "start_date must be YYYY-MM"}), 400
    end_date = (data.get("end_date") or "").strip() or None
    if end_date and not re.fullmatch(r"\d{4}-\d{2}", end_date):
        return jsonify({"error": "end_date must be YYYY-MM or empty"}), 400

    init_db()
    session = get_session()
    try:
        candidate = _get_or_provision_candidate(session, safe_user)

        existing = session.query(Experience).filter_by(
            candidate_id=candidate.id,
        ).count()
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


def _load_experience_for_candidate(session, experience_id: int):
    """Look up an Experience + its candidate. Returns (exp, candidate) or
    (None, None) when not found. Defense-in-depth helper used by every
    route that mutates an experience-scoped row."""
    from db.models import Candidate, Experience
    exp = session.query(Experience).filter_by(id=experience_id).first()
    if exp is None:
        return None, None
    candidate = session.query(Candidate).filter_by(id=exp.candidate_id).first()
    return exp, candidate


@app.route("/api/experiences/<int:experience_id>", methods=["GET"])
def get_experience(experience_id: int):
    """Return one experience with all titles + active bullets."""
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        exp, candidate = _load_experience_for_candidate(session, experience_id)
        if exp is None or candidate is None:
            return jsonify({"error": "Experience not found"}), 404
        if not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403
        return jsonify(_experience_detail_dict(exp))
    finally:
        session.close()


@app.route("/api/experiences/<int:experience_id>", methods=["PUT"])
def update_experience(experience_id: int):
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
        if not _safe_username(candidate.username):
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
            if not re.fullmatch(r"\d{4}-\d{2}", sd):
                return jsonify({"error": "start_date must be YYYY-MM"}), 400
            exp.start_date = sd
        if "end_date" in data:
            ed = (data.get("end_date") or "").strip() or None
            if ed and not re.fullmatch(r"\d{4}-\d{2}", ed):
                return jsonify({"error": "end_date must be YYYY-MM or empty"}), 400
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


@app.route("/api/experiences/<int:experience_id>", methods=["DELETE"])
def delete_experience(experience_id: int):
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
        if not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        retired = session.query(Bullet).filter_by(experience_id=exp.id).update(
            {"is_active": 0}
        )
        session.commit()
        return jsonify({"retired_bullets": retired, "experience_id": exp.id})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/experiences/<int:experience_id>/bullets", methods=["POST"])
def create_bullet(experience_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
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
        return jsonify({
            "id": bullet.id, "text": bullet.text,
            "display_order": bullet.display_order,
            "is_active": bool(bullet.is_active),
            "is_pending_review": bool(bullet.is_pending_review),
            "has_outcome": bool(bullet.has_outcome),
            "pattern_kind": bullet.pattern_kind,
            "source": bullet.source,
        }), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/bullets/<int:bullet_id>", methods=["PUT"])
def update_bullet(bullet_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
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

        session.commit()
        session.refresh(bullet)
        return jsonify({
            "id": bullet.id, "text": bullet.text,
            "display_order": bullet.display_order,
            "is_active": bool(bullet.is_active),
            "has_outcome": bool(bullet.has_outcome),
            "pattern_kind": bullet.pattern_kind,
            "source": bullet.source,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/bullets/<int:bullet_id>", methods=["DELETE"])
def delete_bullet(bullet_id: int):
    """Soft-retire a bullet (is_active=0). Hard-delete refused because
    application_bullet rows have NO cascade on bullet_id."""
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
        if candidate is None or not _safe_username(candidate.username):
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
# β.6a — SummaryItem CRUD. Mirrors bullet routes for the candidate's
# positioning-summary variants. Parented by Candidate, not Experience.
# ---------------------------------------------------------------------------


def _summary_item_to_dict(s) -> dict:
    """Shared response shape for SummaryItem routes."""
    return {
        "id": s.id,
        "candidate_id": s.candidate_id,
        "text": s.text,
        "label": s.label,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "has_outcome": bool(s.has_outcome),
        "source": s.source,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@app.route("/api/users/<username>/summaries", methods=["GET"])
def list_summary_items(username: str):
    """List the candidate's SummaryItem variants in display order.

    Returns active rows by default; pass ?include_inactive=1 to include
    soft-retired ones (the Corpus editor uses this to surface retired
    variants).
    """
    from db.models import Candidate, SummaryItem
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
        return jsonify({
            "error": "Failed to load summaries",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/users/<username>/summaries", methods=["POST"])
def create_summary_item(username: str):
    """Add a new SummaryItem variant for the candidate.

    Body: {text (required), label?, has_outcome?, source?}. New
    user-typed variants default to source='manual',
    is_pending_review=0 (the user wrote it themselves).
    """
    from db.models import SummaryItem
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
        candidate = _get_or_provision_candidate(session, safe_user)

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


@app.route("/api/summaries/<int:summary_id>", methods=["PUT"])
def update_summary_item(summary_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
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


@app.route("/api/summaries/<int:summary_id>", methods=["DELETE"])
def delete_summary_item(summary_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
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
# B.5 (Sprint 6.6) — Skill Corpus Item CRUD. Skills are candidate-level (no
# Experience hop) and carry the same lifecycle as bullets/summaries: active /
# pending-review / source / display_order / tags. DB-only routes — no
# filesystem path, so _within() does not apply; _safe_username gates the
# owning candidate.
# ---------------------------------------------------------------------------


def _skill_to_dict(s, tags: list | None = None) -> dict:
    """Shared response shape for Skill routes."""
    return {
        "id": s.id,
        "candidate_id": s.candidate_id,
        "name": s.name,
        "category": s.category,
        "proficiency": s.proficiency,
        "years": s.years,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "source": s.source,
        "tags": tags if tags is not None else [],
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@app.route("/api/users/<username>/skills", methods=["GET"])
def list_skills(username: str):
    """List the candidate's skills in display order.

    Active + approved by default. ?include_pending=1 adds llm_proposed
    skills awaiting review; ?include_inactive=1 adds soft-retired ones.
    """
    from db.models import Candidate, Skill
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
            return jsonify({"skills": [
                _skill_to_dict(s, _tag_list(s.tag_links)) for s in rows
            ]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_skills failed for user=%s", safe_user)
        return jsonify({
            "error": "Failed to load skills",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/users/<username>/skills", methods=["POST"])
def create_skill(username: str):
    """Add a new skill for the candidate.

    Body: {name (required), category?, proficiency?, years?}. User-typed
    skills default to source='manual', is_pending_review=0, is_active=1.
    """
    from db.models import Skill
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
        candidate = _get_or_provision_candidate(session, safe_user)
        existing = session.query(Skill).filter_by(
            candidate_id=candidate.id, name=name,
        ).first()
        if existing is not None:
            return jsonify({
                "error": "skill already exists", "id": existing.id,
            }), 409

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


@app.route("/api/skills/<int:skill_id>", methods=["PUT"])
def update_skill(skill_id: int):
    """Update a Skill. Body accepts: name, category, proficiency, years,
    display_order, is_pending_review (set false to approve an llm_proposed
    skill). Ownership check via _safe_username on the owning candidate."""
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return jsonify({"error": "name cannot be empty"}), 400
            dup = session.query(Skill).filter(
                Skill.candidate_id == sk.candidate_id,
                Skill.name == name,
                Skill.id != sk.id,
            ).first()
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


@app.route("/api/skills/<int:skill_id>", methods=["DELETE"])
def delete_skill(skill_id: int):
    """Remove a skill. A never-approved suggestion (pending + source
    'llm_proposed') is hard-deleted so its name frees the unique slot for
    future re-evaluation. An approved skill is soft-retired (is_active=0) —
    composition_overrides from past applications may reference its id."""
    from db.models import Candidate, Skill
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        sk = session.query(Skill).filter_by(id=skill_id).first()
        if sk is None:
            return jsonify({"error": "Skill not found"}), 404
        candidate = session.query(Candidate).filter_by(id=sk.candidate_id).first()
        if candidate is None or not _safe_username(candidate.username):
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


# ---------------------------------------------------------------------------
# B.4 (Sprint 6.6) — ExperienceSummaryItem CRUD (per-role intro variants).
# Experience-scoped, mirroring the bullet routes: ownership flows
# experience → candidate → _safe_username. No filesystem access, so the
# route-security-lint hook (filesystem-route guard) does not apply.
# ---------------------------------------------------------------------------


def _experience_summary_item_to_dict(s) -> dict:
    """Shared response shape for ExperienceSummaryItem routes."""
    return {
        "id": s.id,
        "experience_id": s.experience_id,
        "text": s.text,
        "label": s.label,
        "display_order": s.display_order,
        "is_active": bool(s.is_active),
        "is_pending_review": bool(s.is_pending_review),
        "has_outcome": bool(s.has_outcome),
        "source": s.source,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@app.route("/api/experiences/<int:experience_id>/summaries", methods=["GET"])
def list_experience_summaries(experience_id: int):
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
            if candidate is None or not _safe_username(candidate.username):
                return jsonify({"error": "Candidate validation failed"}), 403
            q = session.query(ExperienceSummaryItem).filter_by(experience_id=exp.id)
            if not include_inactive:
                q = q.filter(ExperienceSummaryItem.is_active == 1)
            rows = q.order_by(
                ExperienceSummaryItem.display_order, ExperienceSummaryItem.id,
            ).all()
            return jsonify({"summaries": [_experience_summary_item_to_dict(s) for s in rows]})
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_experience_summaries failed for exp=%s", experience_id)
        return jsonify({
            "error": "Failed to load role summaries",
            **_error_detail_payload(exc),
        }), 500


@app.route("/api/experiences/<int:experience_id>/summaries", methods=["POST"])
def create_experience_summary(experience_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        next_order = session.query(ExperienceSummaryItem).filter_by(
            experience_id=exp.id,
        ).count()
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


@app.route("/api/experience-summaries/<int:item_id>", methods=["PUT"])
def update_experience_summary(item_id: int):
    """Update an ExperienceSummaryItem. Body accepts: text, label,
    has_outcome, is_pending_review, display_order. Ownership:
    item → experience → candidate → _safe_username."""
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
        if candidate is None or not _safe_username(candidate.username):
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


@app.route("/api/experience-summaries/<int:item_id>", methods=["DELETE"])
def delete_experience_summary(item_id: int):
    """Soft-retire an ExperienceSummaryItem (is_active=0). Mirrors bullet
    delete semantics — composition_overrides may reference this id from past
    applications so a hard-delete would orphan them."""
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
        if candidate is None or not _safe_username(candidate.username):
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


@app.route("/api/experiences/<int:experience_id>/titles", methods=["POST"])
def create_experience_title(experience_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        is_official = 1 if data.get("is_official") else 0
        if is_official:
            session.query(ExperienceTitle).filter_by(
                experience_id=exp.id, is_official=1,
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
        return jsonify({
            "id": title.id, "title": title.title,
            "is_official": bool(title.is_official),
            "truthful_enough_to_use": bool(title.truthful_enough_to_use),
            "is_pending_review": bool(title.is_pending_review),
            "source": title.source, "notes": title.notes,
        }), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/experience-titles/<int:title_id>", methods=["PUT"])
def update_experience_title(title_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
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
        if "notes" in data:
            title.notes = (data.get("notes") or "").strip() or None

        session.commit()
        session.refresh(title)
        return jsonify({
            "id": title.id, "title": title.title,
            "is_official": bool(title.is_official),
            "truthful_enough_to_use": bool(title.truthful_enough_to_use),
            "is_pending_review": bool(title.is_pending_review),
            "source": title.source, "notes": title.notes,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/experience-titles/<int:title_id>", methods=["DELETE"])
def delete_experience_title(title_id: int):
    """Mark a title as non-eligible. Doesn't hard-delete the row because
    application_run_title FKs reference it for audit (and our model uses
    CASCADE there — we don't want to lose historical run choices)."""
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        title.is_official = 0
        title.truthful_enough_to_use = 0
        title.is_pending_review = 0
        session.commit()
        return jsonify({
            "id": title.id, "is_official": False,
            "truthful_enough_to_use": False,
        })
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/users/<username>/tags", methods=["GET"])
def suggest_tags(username: str):
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

    safe_user = _safe_username(username)
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
        rows = query.order_by(
            Tag.usage_count.desc(), Tag.value,
        ).limit(limit).all()
        return jsonify([
            {
                "id": t.id, "kind": t.kind, "value": t.value,
                "display_value": t.display_value, "usage_count": t.usage_count,
            }
            for t in rows
        ])
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Tag link / unlink on bullets + experience titles (DB-only; no filesystem)
# ---------------------------------------------------------------------------


def _find_or_create_tag(session, candidate_id: int, kind: str, value: str):
    """Return the Tag for (candidate, kind, normalized value), creating it
    if absent. Follows the merged_into alias chain so links always point at
    the canonical tag."""
    from db.models import Tag
    norm = _normalize_tag_value(value)
    tag = session.query(Tag).filter_by(
        candidate_id=candidate_id, kind=kind, value=norm,
    ).first()
    if tag is None:
        tag = Tag(
            candidate_id=candidate_id, kind=kind, value=norm,
            display_value=(value or "").strip() or norm, usage_count=0,
        )
        session.add(tag)
        session.flush()
    while tag.merged_into_id is not None:
        nxt = session.query(Tag).filter_by(id=tag.merged_into_id).first()
        if nxt is None:
            break
        tag = nxt
    return tag


def _tag_link_target(session, kind: str, subject_id: int):
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
    if kind == "skill":
        subject = session.query(Skill).filter_by(id=subject_id).first()
        if subject is None:
            return None, None, None, None
        candidate = session.query(Candidate).filter_by(id=subject.candidate_id).first()
        return subject, candidate, SkillTag, "skill_id"
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


def _link_tag_route(subject_kind: str, subject_id: int):
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
            session, subject_kind, subject_id,
        )
        if subject is None or candidate is None:
            return jsonify({"error": f"{subject_kind} not found"}), 404
        if not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        tag = _find_or_create_tag(session, candidate.id, tag_kind, value)
        existing = session.query(link_model).filter_by(
            **{fk: subject_id, "tag_id": tag.id},
        ).first()
        if existing is None:
            session.add(link_model(**{fk: subject_id, "tag_id": tag.id}))
            tag.usage_count = (tag.usage_count or 0) + 1
        session.commit()
        return jsonify({
            "id": tag.id, "value": tag.value,
            "display_value": tag.display_value, "kind": tag.kind,
        }), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _unlink_tag_route(subject_kind: str, subject_id: int, tag_id: int):
    """Shared body for DELETE .../tags/<tag_id>. DB-only — no filesystem."""
    from db.models import Tag
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        subject, candidate, link_model, fk = _tag_link_target(
            session, subject_kind, subject_id,
        )
        if subject is None or candidate is None:
            return jsonify({"error": f"{subject_kind} not found"}), 404
        if not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403

        link = session.query(link_model).filter_by(
            **{fk: subject_id, "tag_id": tag_id},
        ).first()
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


@app.route("/api/bullets/<int:bullet_id>/tags", methods=["POST"])
def link_bullet_tag(bullet_id: int):
    """Attach a tag (find-or-create) to a bullet. Body: {value, kind}."""
    return _link_tag_route("bullet", bullet_id)


@app.route("/api/bullets/<int:bullet_id>/tags/<int:tag_id>", methods=["DELETE"])
def unlink_bullet_tag(bullet_id: int, tag_id: int):
    """Detach a tag from a bullet."""
    return _unlink_tag_route("bullet", bullet_id, tag_id)


@app.route("/api/experience-titles/<int:title_id>/tags", methods=["POST"])
def link_title_tag(title_id: int):
    """Attach a tag (find-or-create) to an experience title."""
    return _link_tag_route("title", title_id)


@app.route("/api/experience-titles/<int:title_id>/tags/<int:tag_id>",
           methods=["DELETE"])
def unlink_title_tag(title_id: int, tag_id: int):
    """Detach a tag from an experience title."""
    return _unlink_tag_route("title", title_id, tag_id)


@app.route("/api/skills/<int:skill_id>/tags", methods=["POST"])
def link_skill_tag(skill_id: int):
    """Attach a tag (find-or-create) to a skill. Body: {value, kind}."""
    return _link_tag_route("skill", skill_id)


@app.route("/api/skills/<int:skill_id>/tags/<int:tag_id>", methods=["DELETE"])
def unlink_skill_tag(skill_id: int, tag_id: int):
    """Detach a tag from a skill."""
    return _unlink_tag_route("skill", skill_id, tag_id)


@app.route("/api/users/<username>/duplicates", methods=["GET"])
def list_corpus_duplicates(username: str):
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

    safe_user = _safe_username(username)
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


@app.route("/api/users/<username>/corpus/ingest-resume", methods=["POST"])
def ingest_resume_to_corpus(username: str):
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

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    safe_name = secure_filename(file.filename)
    user_dir = RESUMES_DIR / safe_user
    user_dir.mkdir(exist_ok=True)
    save_path = (user_dir / safe_name).resolve()
    if not _within(save_path, RESUMES_DIR):
        return jsonify({"error": "Invalid upload path"}), 403
    file.save(str(save_path))

    init_db()
    session = get_session()
    try:
        candidate = _get_or_provision_candidate(session, safe_user)
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


@app.route("/api/download/<path:filepath>")
def download_file(filepath):
    full_path = Path(filepath)
    if not full_path.exists():
        return jsonify({"error": "File not found"}), 404
    # Security: ensure the file is within our output directory
    try:
        full_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Access denied"}), 403
    return send_file(str(full_path), as_attachment=True)


@app.route("/api/download-edited", methods=["POST"])
def download_edited():
    """Regenerate a document from edited preview content and stream it for download."""
    data = request.json
    username = data.get("username", "")
    content = data.get("content", "")
    doc_type = data.get("type", "resume")  # "resume" or "cover_letter"
    output_format = data.get("original_format", ".docx")  # field name kept for JS compat
    template_path = data.get("template_path", "")
    persona_template_id = data.get("persona_template_id")

    if not username or not content:
        return jsonify({"error": "username and content required"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    if output_format not in (".docx", ".md", ".pdf"):
        output_format = ".docx"

    # Workstream C (#7 fix): a persona template lives under PERSONAS_DIR, not
    # RESUMES_DIR, so the legacy _within(RESUMES_DIR) gate silently dropped
    # it and DOWNLOAD produced an un-templated doc. When the request carries
    # a persona_template_id, resolve it through the persona resolver (which
    # itself enforces _within(PERSONAS_DIR)); otherwise fall back to the
    # legacy file-based template_path (still RESUMES_DIR-gated).
    if persona_template_id is not None and output_format in (".docx", ".pdf"):
        template_path = _resolve_persona_template_path(int(persona_template_id))
    elif template_path:
        tp = Path(template_path)
        if not _within(tp, RESUMES_DIR) or not tp.exists():
            template_path = None

    if doc_type == "resume":
        path = generate_resume(
            content, output_format, safe_user, str(OUTPUT_DIR),
            template_path=template_path or None,
        )
    else:
        # Cover letter honors the chosen format too (feat/cover-letter-formats).
        # The persona template (resolved above for .docx/.pdf) lends its font: the
        # .pdf renders through personas/cover_letter.html, the .docx borrows the
        # same CSS primary family — so the letter matches the chosen résumé persona.
        path = generate_cover_letter(
            content, safe_user, str(OUTPUT_DIR),
            output_format=output_format, template_path=template_path or None,
        )

    return send_file(str(path), as_attachment=True, download_name=Path(path).name)


# ---------------------------------------------------------------------------
# Legacy-user bridge: import a config-only user into the DB corpus
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Phase D.6: Onboarding review — clear is_pending_review on accept
# ---------------------------------------------------------------------------


@app.route("/api/bullets/<int:bullet_id>/accept", methods=["POST"])
def accept_bullet(bullet_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403
        bullet.is_pending_review = 0
        session.commit()
        return jsonify({"id": bullet.id, "is_pending_review": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/experience-titles/<int:title_id>/accept", methods=["POST"])
def accept_experience_title(title_id: int):
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
        if candidate is None or not _safe_username(candidate.username):
            return jsonify({"error": "Candidate validation failed"}), 403
        title.is_pending_review = 0
        session.commit()
        return jsonify({"id": title.id, "is_pending_review": False})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.route("/api/experiences/<int:experience_id>/accept-all", methods=["POST"])
def accept_experience_all(experience_id: int):
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
        if not _safe_username(candidate.username):
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


@app.route("/api/users/<username>/accept-all-pending", methods=["POST"])
def accept_all_pending(username: str):
    """Corpus-wide bulk-accept: clears is_pending_review on every title +
    active bullet across all of the candidate's experiences. Drives the
    "Accept all pending" button in the onboarding banner (KW2) — senior
    résumés have many roles, and accepting role-by-role is tedious. The
    per-experience accept-all route still covers the by-role case."""
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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


@app.route("/api/users/<username>/pending-counts", methods=["GET"])
def pending_counts(username: str):
    """Counts of pending-review titles + bullets for the candidate.

    Drives the onboarding banner at the top of the Career Corpus tab —
    shown when the candidate has any pending review left to clear.
    """
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session, init_db

    safe_user = _safe_username(username)
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
            query = session.query(Application).filter_by(candidate_id=candidate.id)
            if wanted_statuses:
                query = query.filter(Application.status.in_(wanted_statuses))
            rows = query.order_by(Application.updated_at.desc()).all()
            out = []
            for app_row in rows:
                runs = sorted(app_row.runs, key=lambda r: r.iteration)
                pending = 0
                if runs:
                    run_ids = [r.id for r in runs]
                    pending = session.query(ProposalReview).filter(
                        ProposalReview.application_run_id.in_(run_ids),
                        ProposalReview.decision == "pending",
                    ).count()
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


def _find_root(parent: dict[int, int], x: int) -> int:
    """Union-find path-compression helper used by the corpus-duplicates
    clusterer. Mutates `parent` to flatten the chain as it goes."""
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


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


def _apply_chosen_summary(context_set: dict) -> None:
    """β.6d — patch context_set["candidate"]["profile_text"] in-place
    with the chosen SummaryItem variant's text.

    Priority chain (first match wins):
      1. composition_overrides.pinned_summary_id  (user's explicit pin)
      2. llm_summary_recommendation.recommendation.summary_item_id
      3. unchanged — Candidate.profile_text already in the context

    Resolution is by SummaryItem.id, scoped to the candidate carried
    on the context's `application_id` row. Lookups fail gracefully:
    a missing/inactive variant falls through to the next priority
    rather than 500ing. _safe_username is not needed here because
    the resolution is bounded by the application that the route
    already owns.

    No-op when no application_id, no candidate username, or no
    SummaryItem rows — preserves the back-compat path for legacy
    candidates and for tests that don't seed summaries.
    """
    from db.models import Application, Candidate, SummaryItem
    from db.session import get_session

    candidate_block = context_set.get("candidate") or {}
    app_id = context_set.get("application_id")
    if app_id is None:
        return  # legacy or non-application-bound generate
    overrides = context_set.get("composition_overrides") or {}
    rec_block = context_set.get("llm_summary_recommendation") or {}
    rec = rec_block.get("recommendation") if isinstance(rec_block, dict) else None

    def _coerce(val) -> int | None:
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    pinned_id = _coerce(overrides.get("pinned_summary_id") if isinstance(overrides, dict) else None)
    rec_id = _coerce(rec.get("summary_item_id") if isinstance(rec, dict) else None)
    chosen_id = pinned_id if pinned_id is not None else rec_id
    if chosen_id is None:
        return  # no chosen variant; fall back to existing profile_text

    session = get_session()
    try:
        app_row = session.query(Application).filter_by(id=int(app_id)).first()
        if app_row is None:
            return
        candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
        if candidate is None:
            return
        row = session.query(SummaryItem).filter_by(
            id=chosen_id, candidate_id=candidate.id, is_active=1,
        ).first()
        if row is None or not (row.text or "").strip():
            return  # chosen variant is inactive / missing / blank → fallback
        candidate_block["profile_text"] = row.text
        context_set["candidate"] = candidate_block
        logger.info(
            "β.6d — applied summary variant id=%d (%s) to context for app=%s",
            row.id, "pinned" if pinned_id is not None else "recommended", app_id,
        )
    finally:
        session.close()


def _apply_chosen_experience_summaries(context_set: dict) -> None:
    """B.4 (Sprint 6.6) — patch each career_corpus experience's `summary`
    in-place with the user's chosen ExperienceSummaryItem variant text, so the
    chosen per-role intro reaches the generated résumé (WYSIWYG). Mirrors
    _apply_chosen_summary, but per-experience and OPT-IN with NO auto-fallback.

    Gated on composition_overrides.use_experience_summaries (the explicit
    "Add role intros" toggle). For each experience named in
    chosen_experience_summary_ids, the chosen variant's text is written onto
    that corpus experience's `summary` field so _corpus_block emits a
    <summary> for it. A role with no explicit pick gets no intro; the toggle
    off is a full no-op — the generate prompt stays byte-identical (the
    analyze→generate cache is preserved for everyone who doesn't opt in).

    Resolution is by ExperienceSummaryItem.id, scoped to the experience it's
    pinned for. Missing / inactive / foreign variants are skipped (that role
    just gets no intro) rather than 500ing. Only meaningful in corpus mode
    (no-op when there's no career_corpus).
    """
    corpus = context_set.get("career_corpus")
    if not corpus or not isinstance(corpus, list):
        return
    overrides = context_set.get("composition_overrides") or {}
    if not isinstance(overrides, dict) or not overrides.get("use_experience_summaries"):
        return  # toggle off (default) → no role intros, byte-identical prompt
    chosen_raw = overrides.get("chosen_experience_summary_ids") or {}
    if not isinstance(chosen_raw, dict):
        return
    # Coerce {experience_id: item_id} (JSON object keys persist as strings).
    chosen: dict[int, int] = {}
    for k, v in chosen_raw.items():
        try:
            chosen[int(k)] = int(v)
        except (TypeError, ValueError):
            continue
    if not chosen:
        return

    from db.models import ExperienceSummaryItem
    from db.session import get_session

    session = get_session()
    try:
        applied = 0
        for exp in corpus:
            if not isinstance(exp, dict):
                continue
            try:
                eid = int(exp.get("id"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            item_id = chosen.get(eid)
            if item_id is None:
                continue
            row = session.query(ExperienceSummaryItem).filter_by(
                id=item_id, experience_id=eid, is_active=1,
            ).first()
            if row is None or not (row.text or "").strip():
                continue  # missing / inactive / foreign → role gets no intro
            exp["summary"] = row.text
            applied += 1
        if applied:
            logger.info(
                "B.4 — applied %d chosen per-role intro(s) to corpus for app=%s",
                applied, context_set.get("application_id"),
            )
    finally:
        session.close()


def _apply_recommended_skills(context_set: dict) -> None:
    """B.5 (Sprint 6.6) — reorder / filter context_set["candidate"]["skills"]
    to the curated set for this application, so the LLM-authored download
    surfaces the recommend_skills ordering + the user's pin/drop/reorder.
    Mirrors _apply_chosen_experience_summaries: an in-memory patch before the
    LLM sees the context.

    The effective ordered set is computed by resolve_skill_selection from
    ctx["llm_skill_recommendations"] + composition_overrides
    (pinned_skill_ids / excluded_skill_ids / skill_order), over the candidate's
    active, approved Skill rows. Pending/retired skills can never appear.

    No-op when there's no recommendation AND no skill overrides → the
    candidate's skills list (and the generate prompt's Skills line) stays
    byte-identical. Only meaningful in corpus mode (needs an application_id
    whose candidate owns the Skill rows)."""
    candidate_block = context_set.get("candidate") or {}
    app_id = context_set.get("application_id")
    if app_id is None:
        return

    from corpus_to_json_resume import (
        _read_skill_overrides,
        _read_skill_recommendations,
        resolve_skill_selection,
    )

    pinned, excluded, skill_order = _read_skill_overrides(context_set)
    rec_ids = _read_skill_recommendations(context_set)
    if rec_ids is None and not pinned and not excluded and not skill_order:
        return  # nothing to apply → byte-identical Skills line

    from db.models import Application, Skill
    from db.session import get_session

    session = get_session()
    try:
        app_row = session.query(Application).filter_by(id=int(app_id)).first()
        if app_row is None:
            return
        rows = session.query(Skill).filter_by(
            candidate_id=app_row.candidate_id, is_active=1, is_pending_review=0,
        ).order_by(Skill.display_order, Skill.id).all()
        name_by_id = {r.id: r.name for r in rows if (r.name or "").strip()}
        all_active_ids = [r.id for r in rows if r.id in name_by_id]
        ordered = resolve_skill_selection(
            all_active_ids=all_active_ids,
            rec_ids=rec_ids,
            pinned=pinned,
            excluded=excluded,
            skill_order=skill_order,
        )
        candidate_block["skills"] = [
            name_by_id[sid] for sid in ordered if sid in name_by_id
        ]
        context_set["candidate"] = candidate_block
        logger.info(
            "B.5 — applied curated skill set (%d skills) to context for app=%s",
            len(candidate_block["skills"]), app_id,
        )
    finally:
        session.close()


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
    # BOTH the supervisor and the serving child; only the child sets
    # WERKZEUG_RUN_MAIN, so we open there to avoid a second tab. A short Timer
    # delays the open until the server is listening; it runs as a daemon so it
    # never holds the interpreter open on shutdown.
    serving = (not debug_mode) or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if serving and os.environ.get("CALLBACK_NO_BROWSER") != "1":
        def _open_browser() -> None:
            try:
                webbrowser.open("http://localhost:5000")
            except Exception as exc:  # best-effort; the URL is already printed
                logger.debug("Could not auto-open browser: %s", exc)

        opener = threading.Timer(1.0, _open_browser)
        opener.daemon = True
        opener.start()

    app.run(debug=debug_mode, port=5000)


if __name__ == "__main__":
    main()

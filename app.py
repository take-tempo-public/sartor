"""Flask server — routes and orchestration.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.
"""

import json
import logging
import os
import re
import traceback
import uuid
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
)
from dashboard import dashboard_bp
from generator import generate_cover_letter, generate_resume
from hardening import (
    ContextSet,
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


@app.route("/api/answer-clarifications", methods=["POST"])
def submit_clarifications():
    """Persist the candidate's free-form answers to the clarifying questions.

    Answers are merged into context_set["clarifications"] (question_id -> text).
    Unanswered ids are simply absent — generate() omits the matching question
    from the prompt. This route is idempotent: re-submitting overwrites the
    existing answers map.
    """
    data = request.json
    context_path = data.get("context_path", "")
    username = data.get("username", "")
    answers = data.get("answers", {}) or {}
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

    context_set["clarifications"] = cleaned
    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info(
        "Stored %d clarification answers (out of %d questions) for %s",
        len(cleaned), len(valid_ids), safe_user,
    )
    return jsonify({"ok": True, "answered": len(cleaned), "total": len(valid_ids)})


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
                return jsonify({
                    "error": "Candidate not in corpus yet",
                    "needs_onboarding": True,
                }), 409
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
    from db.models import Candidate, PersonaTemplate
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
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409

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
    from db.models import Candidate, PersonaTemplate
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
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409
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
        # active context file so composition_overrides + LLM
        # recommendations shape the preview. We validate containment
        # under OUTPUT_DIR so a malicious caller can't read outside.
        ctx_path_raw = request.args.get("context_path", "").strip()
        ctx_path_arg: str | None = None
        ctx_has_recommendations = False
        if ctx_path_raw:
            cp = Path(ctx_path_raw)
            if _within(cp, OUTPUT_DIR) and cp.exists():
                ctx_path_arg = str(cp)
                # Probe the context for llm_recommendations BEFORE building
                # the JSON Resume. Per user requirement (2026-05-26): the
                # preview must reflect the JD-specific curated selection,
                # never silently fall back to "all active bullets" when
                # recommendations are missing. If they're missing, return
                # a placeholder HTML so the iframe surfaces an honest
                # empty-state instead of an inflated full-corpus render.
                try:
                    ctx_data = json.loads(cp.read_text(encoding="utf-8"))
                    recs = ctx_data.get("llm_recommendations") or {}
                    # Non-empty dict of recommendations counts as "curation
                    # has happened." Empty dict (or missing key) means
                    # recommend_bullets either hasn't run or failed.
                    ctx_has_recommendations = bool(recs)
                except (json.JSONDecodeError, OSError):
                    ctx_has_recommendations = False

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
  // Suppress paged.js internal layout errors from polluting the parent
  // dev console (added 2026-05-27 — see SESSION_HANDOFF doc). Paged.js
  // throws Cannot-read-getBoundingClientRect-of-null and
  // node.getAttribute-is-not-a-function during layout when content is
  // sparse / unusual; both are noise that's been masking real errors
  // across smoke rounds. We swallow ONLY paged.js's own throws so any
  // real bug in our code (or in the corpus → JSON Resume pipeline)
  // continues to surface normally. Listener registered BEFORE paged.js
  // loads so it catches the initial layout pass.
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
  // Paged.js auto-polyfills on DOMContentLoaded. After it finishes
  // laying out pages, postMessage the count to the parent frame so the
  // wizard's "Page N of M" toolbar can update. paged.js exposes the
  // 'rendered' event on the global PagedPolyfill instance; we also fall
  // back to a 1.5s retry in case the event fires before our handler
  // attaches.
  (function () {
    function send() {
      var pages = document.querySelectorAll('.pagedjs_page').length;
      try { window.parent.postMessage({ type: 'pagedjs_rendered', pages: pages }, '*'); }
      catch (e) { /* same-origin only; safe to ignore */ }
    }
    if (window.PagedPolyfill && typeof window.PagedPolyfill.on === 'function') {
      window.PagedPolyfill.on('rendered', send);
    }
    // Defensive fallback — paged.js layout typically completes within
    // 500–1500 ms; the count is correct once the page DOM stabilizes.
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
                return jsonify({
                    "error": "Candidate not in corpus yet",
                    "needs_onboarding": True,
                }), 409
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
    from db.models import Candidate, Experience
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
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409

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
    from db.models import Candidate, SummaryItem
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
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({"error": "Candidate not found"}), 404

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
    )
    link_model: type
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
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409

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

    Reuses onboarding.import_legacy.ingest_one_resume so the
    merge-as-alternate-title behavior is identical to the CLI importer.
    One Haiku call per upload (~$0.01-0.03, costs API credit).

    Touches the filesystem (saves the upload) → _safe_username + _within.
    """
    from db.models import Candidate
    from db.session import get_session, init_db
    from onboarding.import_legacy import ImportReport, ingest_one_resume

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
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409
        report = ImportReport()
        ingest_one_resume(
            save_path, candidate.id, session,
            client=_get_client(), username=safe_user,
            is_primary=False, dry_run=False, report=report,
        )
        session.commit()
        return jsonify({
            "filename": safe_name,
            "experiences_created": report.experiences_created,
            "experiences_merged": report.experiences_merged,
            "bullets_created": report.bullets_created,
            "alternate_titles_created": report.alternate_titles_created,
            "errors": report.errors,
        }), 201
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
        path = generate_cover_letter(content, safe_user, str(OUTPUT_DIR))

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
    """Return all applications for this candidate, newest-first by updated_at."""
    from db.models import Application, Candidate, ProposalReview
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
                return jsonify({
                    "error": "Candidate not in corpus yet",
                    "needs_onboarding": True,
                }), 409
            rows = session.query(Application).filter_by(
                candidate_id=candidate.id,
            ).order_by(Application.updated_at.desc()).all()
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
        if candidate is None or not _safe_username(candidate.username):
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
        })
    finally:
        session.close()


def _parse_ats_status(blob: str | None) -> str | None:
    """Best-effort extract of the 'status' field from ats_roundtrip_json."""
    if not blob:
        return None
    try:
        return json.loads(blob).get("status")
    except (json.JSONDecodeError, AttributeError):
        return None


@app.route("/api/applications/<int:application_id>/status", methods=["PUT"])
def update_application_status(application_id: int):
    """Set application status to one of the valid lifecycle values."""
    from datetime import timezone

    from db.models import Application, Candidate
    from db.session import get_session, init_db

    data = request.json or {}
    status = (data.get("status") or "").strip().lower()
    valid = {"draft", "submitted", "interview", "withdrawn",
             "offer", "accepted", "rejected", "no_response"}
    if status not in valid:
        return jsonify({"error": f"status must be one of {sorted(valid)}"}), 400

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
        if status in {"offer", "accepted", "rejected", "no_response"} and app_row.outcome_at is None:
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
    from db.models import Experience, SummaryItem
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
        # Workstreams H + I: surface llm_recommendations + composition_overrides.added
        # so the Compose UI can default to the curated set and mark drawer-added
        # bullets as included.
        added, rec_by_exp = _read_recommendations_and_added(ctx_path)
        # β.6c — pull the summary recommendation + pinned_summary_id
        # from the context (both optional). The UI renders a Positioning
        # card at the top with the LLM's pick flagged + any user pin
        # overriding it.
        summary_recommendation, pinned_summary_id = _read_summary_overrides(ctx_path)

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
                })
            titles.sort(
                key=lambda d: (not d["is_official"], -float(d["score"]), int(d["id"])),
            )
            if scored_bullets or titles:
                out.append({
                    "id": exp.id, "company": exp.company,
                    "start_date": exp.start_date, "end_date": exp.end_date,
                    "bullets": scored_bullets, "titles": titles,
                    "rationale": rec.get("rationale", ""),
                    "has_recommendations": bool(rec_ids),
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

        overrides: dict[str, Any] = {
            "pinned": pinned, "excluded": excluded, "added": added,
        }
        if pinned_summary_id is not None:
            overrides["pinned_summary_id"] = pinned_summary_id
        ctx["composition_overrides"] = overrides
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify({
            "application_id": application_id,
            "pinned": pinned, "excluded": excluded, "added": added,
            "pinned_summary_id": pinned_summary_id,
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
            return jsonify({
                "error": "Candidate not in corpus yet",
                "needs_onboarding": True,
            }), 409

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


def main() -> None:
    """Launch the Flask app on http://localhost:5000.

    Entry point for the `callback` console script registered in
    `pyproject.toml [project.scripts]`. Equivalent to `python app.py`
    for users who installed via `pip install -e .` or `pip install
    callback`.

    Set `FLASK_DEBUG=0` in the environment to disable Flask's
    reloader + verbose error pages (see SECURITY.md for rationale).
    """
    print("\n  callback. — http://localhost:5000\n")
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug_mode, port=5000)


if __name__ == "__main__":
    main()

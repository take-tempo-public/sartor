"""Flask server — routes and orchestration.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import anthropic
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from analyzer import (
    LLMResponseError,
    _current_cover_letter_draft,
    _current_draft_text,
    analyze,
    check_refinement_scope,
    clarify,
    clarify_iteration,
    generate,
)
from dashboard import dashboard_bp
from generator import generate_cover_letter, generate_resume
from hardening import (
    ContextSet,
    build_context_set,
    check_ats_format,
    compute_iteration_signals,
    compute_keyword_overlap,
    extract_keywords,
    save_context_set,
    save_iteration_context,
    summarize_recent_edits,
    validate_config,
)
from parser import parse_resume
from scraper import fetch_profile_content

# P7 Observability: structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")

BASE_DIR = Path(__file__).parent
CONFIGS_DIR = BASE_DIR / "configs"
RESUMES_DIR = BASE_DIR / "resumes"
OUTPUT_DIR = BASE_DIR / "output"

ALLOWED_EXTENSIONS = {".docx", ".pdf", ".md"}

# Phase B feature flag: when "1", /api/analyze reads from the SQLite corpus
# instead of parsing resume files. Both paths produce identical ContextSet
# shape so downstream routes (clarify, generate, iterate-clarify) work
# unchanged. Removed in Phase C; not a permanent flag.
CORPUS_BACKED = os.environ.get("CORPUS_BACKED", "0") == "1"

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
    return render_template("index.html")


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
    """P8 Human Gate #1: returns analysis for user review before generation."""
    data = request.json
    username = data.get("username", "")
    resume_filename = data.get("resume_filename", "")
    jd_text = data.get("job_description", "")

    # CORPUS_BACKED ignores resume_filename — content comes from the DB corpus.
    if not username or not jd_text:
        return jsonify({"error": "username and job_description required"}), 400
    if not CORPUS_BACKED and not resume_filename:
        return jsonify({"error": "resume_filename required (file-based mode)"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    if CORPUS_BACKED:
        return _run_analysis_corpus_backed(safe_user, jd_text, data)

    safe_resume = secure_filename(resume_filename)
    resume_path = RESUMES_DIR / safe_user / safe_resume
    if not _within(resume_path, RESUMES_DIR):
        return jsonify({"error": "Invalid resume path"}), 403
    if not resume_path.exists():
        return jsonify({"error": "Resume file not found"}), 404

    logger.info("Starting analysis for %s with resume %s", safe_user, safe_resume)

    # Resolve source pool selection — None means "all included" (first-use default)
    included_resumes_raw = data.get("included_resumes")  # list[str] | None

    # P1 Hardening: deterministic steps first
    parsed = parse_resume(str(resume_path))
    config = _load_config(safe_user)
    profile_text = fetch_profile_content(config)

    # Parse supplemental resumes, honoring the user's source pool selection.
    # Security: filenames from the whitelist are used only for membership testing,
    # never for path construction — actual paths come from iterdir().
    supplemental_parsed = []
    for f in sorted((RESUMES_DIR / safe_user).iterdir()):
        if f.name == safe_resume or f.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        # Apply whitelist filter when client sent one (None = all included)
        if included_resumes_raw is not None:
            if secure_filename(f.name) not in included_resumes_raw:
                logger.debug("Skipping excluded supplemental resume: %s", f.name)
                continue

        if not _within(f, RESUMES_DIR / safe_user):
            logger.warning("Supplemental resume failed containment check: %s", f)
            continue

        try:
            supplemental_parsed.append(parse_resume(str(f)))
            logger.info("Loaded supplemental resume: %s", f.name)
        except Exception as exc:
            logger.warning("Skipped supplemental resume %s: %s", f.name, exc)

    logger.info(
        "Resume sources for %s: 1 primary + %d supplemental",
        safe_user, len(supplemental_parsed),
    )

    # Combine ALL resume text for keyword extraction (P1: deterministic, covers full history)
    all_resume_text = parsed["text"]
    for r in supplemental_parsed:
        all_resume_text += "\n" + r["text"]

    jd_keywords = extract_keywords(jd_text)
    resume_keywords = extract_keywords(all_resume_text)
    overlap = compute_keyword_overlap(resume_keywords, jd_keywords)
    ats_warnings = check_ats_format(parsed)  # ATS check applies to primary only

    # P2 Context Hygiene: build compact context
    context_set = build_context_set(
        jd_text, parsed, config, profile_text,
        jd_keywords, resume_keywords, overlap, ats_warnings,
        supplemental_resumes=supplemental_parsed,
        original_resume_path=str(resume_path),
    )

    # Fuzzy work: LLM analysis. Generate a run_id that pairs this analyze
    # call with the upcoming generate call (issued in /api/generate after
    # the user reviews the analysis). Both calls share this ID in
    # logs/llm_calls.jsonl so the dashboard can correlate them.
    client = _get_client()
    run_id = uuid.uuid4().hex[:12]
    try:
        analysis = analyze(client, context_set, username=safe_user, run_id=run_id)
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during analysis: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("LLM analysis response failed validation after retry: %s", exc.validation_error)
        return jsonify({
            "error": "AI analysis response was malformed after retry. Please try again.",
            "detail": exc.validation_error,
        }), 502

    # P4 Disposable Blueprint: save context + analysis (and run_id so the
    # generate route can re-use it for telemetry correlation)
    context_set["llm_analysis"] = analysis
    context_set["run_id"] = run_id
    context_path = save_context_set(context_set, safe_user, str(OUTPUT_DIR))

    logger.info("Analysis complete for %s, saved to %s", safe_user, context_path)

    return jsonify({
        "analysis": analysis,
        "deterministic": {
            "keyword_overlap": overlap,
            "ats_warnings": ats_warnings,
        },
        "context_path": context_path,
        "template_path": str(resume_path),  # original .docx path for style templating
    })


def _persist_corpus_generation_to_db(application_run_id: int, generate_result: dict) -> None:
    """Phase B.3 write-back: persist the structured generate() output to the DB.

    Looks up the `application_run` row, calls `persist_corpus_generation`, and
    commits. Defense-in-depth: validates the run belongs to a real candidate
    before any writes. Used by `/api/generate` only when the context carries
    `application_run_id` (corpus-backed mode).
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
            return jsonify({"error": str(exc)}), 404

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
    if output_format not in (".docx", ".md"):
        output_format = ".docx" if original_format != ".md" else ".md"
    # Provide the original .docx as a style template when available
    template_path = context_set["resume"].get("path", "") if output_format == ".docx" else None
    resume_path = generate_resume(
        result["resume_content"], output_format, safe_user, str(OUTPUT_DIR),
        template_path=template_path,
    )
    cover_letter_path = generate_cover_letter(
        result["cover_letter_content"], safe_user, str(OUTPUT_DIR)
    )

    logger.info("Generation complete: %s, %s", resume_path, cover_letter_path)

    # Phase B.3: when the context carries an application_run_id (set by the
    # corpus-backed /api/analyze path), persist the LLM's structured output
    # to the DB audit chain — application_bullet rows, proposal_review rows
    # for any new bullets/titles the LLM proposed, etc. No-op for file-based
    # contexts (which don't have an application_run_id).
    app_run_id = context_set.get("application_run_id")
    if app_run_id is not None:
        try:
            _persist_corpus_generation_to_db(int(app_run_id), result)
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
    })


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

    if not username or not content:
        return jsonify({"error": "username and content required"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    if output_format not in (".docx", ".md"):
        output_format = ".docx"

    # Validate template path if provided
    if template_path:
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


if __name__ == "__main__":
    print("\n  Resume Optimizer — http://localhost:5000\n")
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug_mode, port=5000)

"""Flask server — routes and orchestration.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.
"""

import json
import logging
import os
from pathlib import Path

import anthropic
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from analyzer import analyze, check_refinement_scope, generate
from dashboard import dashboard_bp
from generator import generate_cover_letter, generate_resume
from hardening import (
    build_context_set,
    check_ats_format,
    compute_keyword_overlap,
    extract_keywords,
    save_context_set,
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

    if not all([username, resume_filename, jd_text]):
        return jsonify({"error": "username, resume_filename, and job_description required"}), 400

    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

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

    # Fuzzy work: LLM analysis
    client = _get_client()
    try:
        analysis = analyze(client, context_set, username=safe_user)
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during analysis: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503

    # P4 Disposable Blueprint: save context + analysis
    context_set["llm_analysis"] = analysis
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


@app.route("/api/generate", methods=["POST"])
def run_generation():
    """P8 Human Gate #2: generates documents after user reviewed analysis."""
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
    context_set = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})

    if not analysis or analysis.get("parse_error"):
        return jsonify({"error": "No valid analysis found in context"}), 400

    logger.info("Starting generation for %s", username)

    client = _get_client()
    try:
        result = generate(
            client, context_set, analysis,
            refinement_notes=refinement_notes,
            username=username,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during generation: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503

    if result.get("parse_error"):
        return jsonify({"error": "Generation failed", "raw": result.get("raw_response", "")}), 500

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

    return jsonify({
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "resume_format": output_format,
        "changes_made": result.get("changes_made", []),
        "proofread_notes": result.get("proofread_notes", []),
        "resume_preview": result["resume_content"],
        "cover_letter_preview": result["cover_letter_content"],
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

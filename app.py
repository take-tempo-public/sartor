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
    compute_grounding_overlap,
    compute_keyword_overlap,
    compute_specificity_density,
    compute_verb_diversity,
    extract_keywords,
    save_context_set,
    save_iteration_context,
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


def _summarize_recent_edits(context_set: ContextSet) -> str:
    """Produce a compact text summary of what the candidate edited since the
    last generation, used as one of the four signal sources for the iteration
    interview.

    Strategy: short unified diff preface for each of resume + cover letter,
    capped to keep prompt tokens predictable. If no edits exist, returns "".
    The LLM only needs to see what changed, not a full character-level diff.
    """
    import difflib

    parts: list[str] = []
    for label, before_key, after_key in (
        ("resume", "last_generated_resume", "edited_resume_text"),
        ("cover_letter", "last_generated_cover_letter", "edited_cover_letter_text"),
    ):
        # Use cast-to-str through fallback — values come from JSON-loaded
        # TypedDict fields whose value type mypy widens to object.
        before_raw = context_set.get(before_key) or ""
        after_raw = context_set.get(after_key) or ""
        before = str(before_raw).strip()
        after = str(after_raw).strip()
        if not after or before == after:
            continue
        diff = list(difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"prior_{label}", tofile=f"edited_{label}",
            lineterm="", n=2,
        ))
        if not diff:
            continue
        # Cap to first ~60 diff lines — enough to convey the change without
        # blowing up the prompt for users who rewrote large sections.
        snippet = "\n".join(diff[:60])
        if len(diff) > 60:
            snippet += f"\n... [{len(diff) - 60} more diff lines truncated]"
        parts.append(f"## {label} edits\n{snippet}")
    return "\n\n".join(parts)


def _compute_iteration_signals(
    context_set: ContextSet,
    current_resume_text: str,
) -> dict:
    """Compute the four deterministic signal sources for the iteration clarifier.

    Each signal is independently informative — the LLM uses them to target
    questions at concrete weaknesses rather than guessing. Names match the
    metric functions in hardening.py so the dashboard can correlate.
    """
    overlap = (context_set.get("deterministic_analysis", {}) or {}).get("keyword_overlap", {}) or {}
    jd_kw_set = set(overlap.get("matched", [])) | set(overlap.get("missing_from_resume", []))

    # Recompute keyword coverage against the CURRENT draft (the analyzer's
    # original overlap was vs the original primary). The diff between original
    # missing and current missing tells the LLM whether a recent revision
    # actually closed any keyword gaps.
    current_kw = extract_keywords(current_resume_text or "")
    current_kw_set = set(current_kw.get("keywords", {}).keys())
    still_missing = sorted(set(overlap.get("missing_from_resume", [])) - current_kw_set)

    # Sources for grounding overlap mirror what generate() considers ground
    # truth: original primary, supplementals, clarification answers.
    source_texts: list[str] = []
    primary_text = (context_set.get("resume", {}) or {}).get("text", "")
    if primary_text:
        source_texts.append(primary_text)
    for s in context_set.get("supplemental_resumes", []) or []:
        if s.get("text"):
            source_texts.append(s["text"])
    for ans in (context_set.get("clarifications") or {}).values():
        if ans:
            source_texts.append(ans)

    return {
        "verb_diversity": compute_verb_diversity(current_resume_text),
        "specificity_density": compute_specificity_density(current_resume_text),
        "grounding_overlap": compute_grounding_overlap(current_resume_text, source_texts),
        "keyword_coverage": {
            "jd_total": len(jd_kw_set),
            "still_missing_from_current_draft": still_missing[:20],
            "still_missing_count": len(still_missing),
        },
    }


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
    edits_summary = _summarize_recent_edits(context_set)
    signals = _compute_iteration_signals(context_set, current_resume_text)

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

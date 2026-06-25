"""Analysis seam — the analyze + clarify family of routes.

The first domain blueprint extracted from `app.py` (Sprint 8.3b, the app.py ->
blueprints decomposition). Owns the five P8-Human-Gate routes that turn a job
description into an analysis + clarifying questions, plus their analysis-only
domain helpers:

    POST /api/analyze                 run_analysis
    POST /api/analyze/stream          run_analysis_stream  (SSE)
    POST /api/clarify                 run_clarify
    POST /api/answer-clarifications   submit_clarifications
    POST /api/iterate-clarify         run_iterate_clarify

Reads paths from `current_app.config[...]` at request time (never a module-global
import) and shares the security/HTTP/client helpers from `web_infra` — so a test
isolates the routes with `create_app(Config(base_dir=tmp_path))`, no monkeypatching
of module globals. The blueprint never imports `app.py` (leaf-ward direction only).
DB-layer imports stay lazy inside each function, as in the monolith.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import anthropic
from flask import Blueprint, Response, current_app, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from analyzer import (
    LLMResponseError,
    _current_cover_letter_draft,
    _current_draft_text,
    analyze,
    analyze_streaming,
    clarify,
    clarify_iteration,
)
from hardening import (
    ClarificationQuestion,
    ContextSet,
    compute_iteration_signals,
    save_context_set,
    summarize_recent_edits,
)
from web_infra import (
    _get_client,
    _get_or_provision_candidate,
    _safe_username,
    _sse,
    _within,
)

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__)


# --- Analyze ---


@analysis_bp.route("/api/analyze", methods=["POST"])
def run_analysis() -> ResponseReturnValue:
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

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    return _run_analysis_corpus_backed(safe_user, jd_text, data)


@analysis_bp.route("/api/analyze/stream", methods=["POST"])
def run_analysis_stream() -> ResponseReturnValue:
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

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    return _run_analysis_corpus_backed_streaming(safe_user, jd_text, data)


def _run_analysis_corpus_backed_streaming(
    safe_user: str,
    jd_text: str,
    data: dict,
) -> ResponseReturnValue:
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

    # Read config in the request context, before the generator (which runs
    # lazily, after this function returns) — `current_app` is not available
    # once `stream()` starts yielding, so capture the path as a local.
    configs_dir = current_app.config["CONFIGS_DIR"]
    output_dir = current_app.config["OUTPUT_DIR"]

    if not _safe_username(safe_user, configs_dir=configs_dir):
        return jsonify({"error": "Invalid or unknown user"}), 400
    user_output_dir = output_dir / safe_user
    if not _within(user_output_dir, output_dir):
        return jsonify({"error": "Invalid output path"}), 403

    init_db()
    setup_session = get_session()
    run_id = uuid.uuid4().hex[:12]
    try:
        try:
            _get_or_provision_candidate(setup_session, safe_user, configs_dir=configs_dir)
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
            logger.warning("[analyze/stream 409] user=%s needs_onboarding: %s", safe_user, exc)
            return jsonify({"error": str(exc), "needs_onboarding": True}), 409
        application_id = application.id
        application_run_id = application_run.id
        # Commit the application + application_run rows up front so we don't
        # hold the session open across the ~90s LLM call. The analysis_json
        # update happens in a new short-lived session in the stream's done branch.
        setup_session.commit()
        logger.info(
            "DB-backed streaming analysis for %s: application_id=%d run_id=%s",
            safe_user,
            application_id,
            run_id,
        )
    finally:
        setup_session.close()

    client = _get_client()

    def stream() -> Iterator[str]:
        """SSE generator: stream the corpus-backed analyze events to the client."""
        try:
            analysis: dict | None = None
            for event_kind, payload in analyze_streaming(
                client,
                context_set,
                username=safe_user,
                run_id=run_id,
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
                yield _sse(
                    "error",
                    {
                        "error": "Streaming analyze finished without a parsed result.",
                        "http_status": 502,
                    },
                )
                return

            # Persist analysis_json on the application_run row + write the
            # context_*.json file the downstream routes (clarify, generate,
            # save-edits, iterate-clarify) all consume.
            persist_session = get_session()
            try:
                run_row = (
                    persist_session.query(ApplicationRun)
                    .filter_by(
                        id=application_run_id,
                    )
                    .first()
                )
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
            context_path = save_context_set(context_set, safe_user, str(output_dir))
            logger.info(
                "Streaming analysis complete for %s, saved to %s",
                safe_user,
                context_path,
            )

            yield _sse(
                "done",
                {
                    "analysis": analysis,
                    "deterministic": {
                        "keyword_overlap": context_set["deterministic_analysis"]["keyword_overlap"],
                        "ats_warnings": context_set["deterministic_analysis"]["ats_warnings"],
                    },
                    "context_path": context_path,
                    "template_path": "",
                    "application_id": application_id,
                    "application_run_id": application_run_id,
                },
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic API connection error during streaming analysis: %s", exc)
            yield _sse(
                "error",
                {
                    "error": "Connection to AI service failed. Please try again.",
                    "http_status": 503,
                },
            )
        except LLMResponseError as exc:
            logger.error(
                "LLM streaming analysis response failed validation after retry: %s",
                exc.validation_error,
            )
            yield _sse(
                "error",
                {
                    "error": "AI analysis response was malformed after retry. Please try again.",
                    "detail": exc.validation_error,
                    "http_status": 502,
                },
            )
        except Exception:
            logger.exception("Streaming analysis failed unexpectedly")
            yield _sse(
                "error",
                {
                    "error": "Internal error during analysis.",
                    "http_status": 500,
                },
            )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx-style buffering if proxied
        },
    )


def _run_analysis_corpus_backed(
    safe_user: str,
    jd_text: str,
    data: dict,
) -> ResponseReturnValue:
    """DB-backed analyze path used when CORPUS_BACKED=1.

    Produces the same response shape as the file-based path: analysis JSON,
    keyword_overlap, ats_warnings, context_path. The context_path file still
    gets written so downstream routes (clarify, generate, iterate-clarify)
    work unchanged. Additionally creates `application` + `application_run`
    rows that anchor the new audit chain.
    """
    from db.build_context import build_context_set_from_db
    from db.session import get_session, init_db

    configs_dir = current_app.config["CONFIGS_DIR"]
    output_dir = current_app.config["OUTPUT_DIR"]

    # Defense-in-depth: re-validate username + output path even though the
    # caller already checked. Internal callers can drift; the guards are cheap.
    if not _safe_username(safe_user, configs_dir=configs_dir):
        return jsonify({"error": "Invalid or unknown user"}), 400
    user_output_dir = output_dir / safe_user
    if not _within(user_output_dir, output_dir):
        return jsonify({"error": "Invalid output path"}), 403

    init_db()
    session = get_session()
    run_id = uuid.uuid4().hex[:12]
    try:
        try:
            _get_or_provision_candidate(session, safe_user, configs_dir=configs_dir)
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
            logger.warning("[analyze 409] user=%s needs_onboarding: %s", safe_user, exc)
            return jsonify(
                {
                    "error": str(exc),
                    "needs_onboarding": True,
                }
            ), 409

        logger.info(
            "DB-backed analysis for %s: application_id=%d run_id=%s",
            safe_user,
            application.id,
            run_id,
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
            return jsonify(
                {
                    "error": "AI analysis response was malformed after retry. Please try again.",
                    "detail": exc.validation_error,
                }
            ), 502

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
        context_path = save_context_set(context_set, safe_user, str(output_dir))

        session.commit()
        logger.info("Analysis complete for %s, saved to %s", safe_user, context_path)

        return jsonify(
            {
                "analysis": analysis,
                "deterministic": {
                    "keyword_overlap": context_set["deterministic_analysis"]["keyword_overlap"],
                    "ats_warnings": context_set["deterministic_analysis"]["ats_warnings"],
                },
                "context_path": context_path,
                "template_path": "",  # no file-backed template in DB mode; Phase C picks a persona
                "application_id": application.id,
                "application_run_id": application_run.id,
            }
        )
    finally:
        session.close()


# --- Clarify ---


@analysis_bp.route("/api/clarify", methods=["POST"])
def run_clarify() -> ResponseReturnValue:
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
    if not _within(cp, current_app.config["OUTPUT_DIR"]):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # When a username is supplied, validate it; otherwise derive from the
    # context path's parent directory (OUTPUT_DIR/<username>/context_*.json).
    safe_user = (
        _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
        if username
        else None
    )
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
        return jsonify(
            {
                "error": "AI clarification response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
            }
        ), 502

    questions = result.get("questions", [])
    # Persist the questions back to the same context file so the user can
    # refresh the page and resume — and so generate() can pair each answer
    # with its question text.
    context_set["clarification_questions"] = questions
    context_set["run_id"] = run_id
    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info("Clarify produced %d questions for %s", len(questions), safe_user)
    return jsonify(
        {
            "questions": questions,
            "reasoning": result.get("reasoning", ""),
            "context_path": str(cp),
        }
    )


def _persist_clarifications_to_memory(context_set: ContextSet, answered: dict[str, str]) -> int:
    """Mirror answered clarifications into the candidate-memory table (`clarification`) for memory-panel reads.

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
        if candidate is None or not _safe_username(
            candidate.username,
            configs_dir=current_app.config["CONFIGS_DIR"],
        ):
            return 0

        existing: dict[str, Clarification] = {}
        for row in session.query(Clarification).filter_by(
            candidate_id=candidate.id,
            origin_application_id=app_row.id,
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


@analysis_bp.route("/api/answer-clarifications", methods=["POST"])
def submit_clarifications() -> ResponseReturnValue:
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
    if not _within(cp, current_app.config["OUTPUT_DIR"]):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # When a username is supplied, validate it; otherwise derive from the
    # context path. The path containment check (_within above) is the primary
    # authority; this is belt-and-suspenders.
    safe_user = (
        _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
        if username
        else None
    )
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
        len(cleaned),
        len(valid_ids),
        safe_user,
        memory_rows,
    )
    return jsonify(
        {
            "ok": True,
            "answered": len(cleaned),
            "total": len(valid_ids),
            "memory_rows": memory_rows,
        }
    )


@analysis_bp.route("/api/iterate-clarify", methods=["POST"])
def run_iterate_clarify() -> ResponseReturnValue:
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
    if not _within(cp, current_app.config["OUTPUT_DIR"]):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    safe_user = (
        _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
        if username
        else None
    )
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
        return jsonify(
            {
                "error": "Iteration interview requires at least one generated draft. Run /api/generate first.",
            }
        ), 400

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
        ans = (
            prior_answers.get(qid, "").strip()
            if isinstance(prior_answers.get(qid, ""), str)
            else ""
        )
        if ans:
            prior_clarifications.append(
                {
                    "question": q.get("text", ""),
                    "answer": ans,
                    "kind": q.get("kind", ""),
                }
            )

    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]
    client = _get_client()
    logger.info(
        "Starting iteration clarify for %s iteration=%d run_id=%s",
        safe_user,
        iteration,
        run_id,
    )
    try:
        result = clarify_iteration(
            client,
            context_set,
            analysis,
            current_resume_text=current_resume_text,
            current_cover_letter_text=current_cover_text,
            recent_edits_summary=edits_summary,
            deterministic_signals=signals,
            prior_clarifications=prior_clarifications,
            username=safe_user,
            run_id=run_id,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during iterate-clarify: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error(
            "LLM iterate-clarify response failed validation after retry: %s", exc.validation_error
        )
        return jsonify(
            {
                "error": "AI iteration-interview response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
            }
        ), 502

    new_questions = result.get("questions", []) or []

    # Re-key new question ids to avoid collisions with existing q1/q2/...
    # The /api/answer-clarifications route filters by id-membership, so unique
    # ids per question are mandatory. Prefix with iteration number for clarity
    # in saved JSON and dashboard rendering.
    existing_ids = {q.get("id", "") for q in prior_qs}
    renamed: list[ClarificationQuestion] = []
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
    notes.append(
        {
            "timestamp": datetime.now().isoformat(),
            "action": "iterate_clarify",
            "summary": f"surfaced {len(renamed)} iteration questions at iteration {iteration}",
        }
    )
    context_set["iteration_notes"] = notes

    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    logger.info(
        "iterate-clarify produced %d questions for %s (iteration=%d)",
        len(renamed),
        safe_user,
        iteration,
    )
    return jsonify(
        {
            "questions": renamed,
            "reasoning": result.get("reasoning", ""),
            "context_path": str(cp),
            "iteration": iteration,
            "signals": signals,
        }
    )

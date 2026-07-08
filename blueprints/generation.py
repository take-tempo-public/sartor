"""Generation seam — the document-generation family of routes.

The second domain blueprint extracted from `app.py` (Sprint 8.3c, the app.py ->
blueprints decomposition). Owns the seven routes that turn a reviewed analysis +
context into downloadable résumé / cover-letter documents, plus their
generation-only domain helpers:

    POST /api/save-edits             save_edits
    POST /api/generate               run_generation
    POST /api/generate/stream        run_generation_stream  (SSE)
    POST /api/validate-refinement    validate_refinement
    POST /api/generate-cover-letter  run_generate_cover_letter
    GET  /api/download/<path>        download_file
    POST /api/download-edited        download_edited

Reads paths from `current_app.config[...]` at request time (never a module-global
import) and shares the security/HTTP/client helpers from `web_infra` — so a test
isolates the routes with `create_app(Config(base_dir=tmp_path))`, no monkeypatching
of module globals. The blueprint never imports `app.py` (leaf-ward direction only).
DB-layer imports stay lazy inside each function, as in the monolith.

Cross-seam helpers (owner decision, Sprint 8.3c): the generation-sole-caller
helpers (`_check_date_grounding`, `_persist_*`, `_apply_*`) move here outright. The
shared `_resolve_persona_template_path` / `_resolve_default_persona_template_path`
pair is owned by the templates/personas seam (8.3e); 8.3c carried a transitional
duplicate here until that seam landed. The duplicate is now gone — generation
imports the pair from `blueprints/templates` (sibling blueprint import; templates
never imports generation, so there is no cycle).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

import anthropic
from flask import Blueprint, Response, current_app, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from analyzer import (
    LLMResponseError,
    check_refinement_scope,
    generate,
    generate_cover_letter_against_resume,
    generate_streaming,
)

# Persona-template resolvers are owned by the templates seam (Sprint 8.3e). The
# generation routes (run_generation / run_generation_stream / download_edited)
# call them to resolve the persona the user generates with. Sibling blueprint
# import — templates never imports generation, so there is no cycle. (8.3c
# carried a transitional duplicate here; this import replaces it.)
from blueprints.templates import (
    _resolve_default_persona_template_path,
    _resolve_persona_template_path,
)
from generator import (
    generate_cover_letter,
    generate_resume,
    generate_resume_from_json_resume,
)
from hardening import (
    ContextSet,
    compute_date_grounding,
    save_iteration_context,
)
from web_infra import (
    _get_client,
    _safe_username,
    _sse,
    _within,
)

logger = logging.getLogger(__name__)

generation_bp = Blueprint("generation", __name__)


# --- Generation-only domain helpers (moved with the seam) ---


def _persist_run_persona(application_run_id: int, persona_template_id: int) -> None:
    """Record which persona template the user generated with on the run (audit; the column exists but was always NULL before Workstream C)."""
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


def _persist_edited_text_to_db(
    application_run_id: int,
    edited_resume_text: str | None,
    edited_cover_letter_text: str | None,
) -> None:
    """Mirror a saved WYSIWYG edit onto its ApplicationRun row (D4 durability).

    ``ApplicationRun.edited_resume_text`` / ``edited_cover_letter_text`` are the
    DB-side half of "every generated and edited artifact" (see the model's
    class docstring) — already READ by ``_build_resume_state`` in
    ``blueprints/applications.py`` (the Applications-tab resume, and the
    degraded-mode Step-6 rehydrate when the on-disk context file is gone) and
    by ``get_application``'s ``has_edits`` flag, but never WRITTEN. Without
    this, an in-app edit survived only in the context_*.json sidecar
    (``/api/save-edits`` above): resuming an application after that file was
    cleaned up silently reverted Step 6 to the un-edited AI text, and
    ``has_edits`` always read false. Only called for corpus-backed contexts
    (``application_run_id`` present); legacy file-based contexts have no run
    row. Best-effort like the sibling ``_persist_run_persona`` callers — a DB
    hiccup must not fail the save, since the context file already has the
    edit and remains the primary source the preview/generate routes read.
    """
    from db.models import ApplicationRun
    from db.session import get_session

    session = get_session()
    try:
        run = session.query(ApplicationRun).filter_by(id=application_run_id).first()
        if run is None:
            return
        if edited_resume_text is not None:
            run.edited_resume_text = edited_resume_text
        if edited_cover_letter_text is not None:
            run.edited_cover_letter_text = edited_cover_letter_text
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
            logger.warning(
                "Application_run not found for cover-letter persist (id=%s)", application_run_id
            )
            return
        app_row = session.query(Application).filter_by(id=run.application_id).first()
        if app_row is None:
            logger.warning(
                "Parent application not found for cover-letter persist (run id=%s)",
                application_run_id,
            )
            return

        persist_cover_letter_md(session, run, cover_letter_md)
        session.commit()
        logger.info(
            "Persisted cover-letter md: app_run=%d (%d chars)",
            application_run_id,
            len(cover_letter_md),
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
            session,
            run,
            generate_result,
            candidate_id=app_row.candidate_id,
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
    """KW6 guard: flag generated heading date ranges that don't trace to the corpus (altered or duplicated date ranges).

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
        return {
            "status": "not_run",
            "checked": 0,
            "flagged": [],
            "corpus_ranges": [],
            "notes": [f"check raised: {exc}"],
        }
    if findings["status"] == "flag":
        logger.warning(
            "Date-grounding flag on generated resume: %s (corpus ranges: %s)",
            findings["flagged"],
            findings["corpus_ranges"],
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


# --- Composition-application helpers (moved with the seam) ---
# Generation is the sole caller of the three `_apply_*` helpers today. The 8.1
# design groups them with the applications seam (8.3f) by domain; they move with
# generation now and are revisited at 8.3f if an applications route grows a caller.


def _apply_chosen_summary(context_set: dict) -> None:
    """β.6d — patch context_set["candidate"]["profile_text"] in-place with the chosen SummaryItem variant's text.

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

    def _coerce(val: str | int | float | None) -> int | None:
        """Coerce ``val`` to ``int``, or ``None`` if it is None or non-numeric."""
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
        row = (
            session.query(SummaryItem)
            .filter_by(
                id=chosen_id,
                candidate_id=candidate.id,
                is_active=1,
            )
            .first()
        )
        if row is None or not (row.text or "").strip():
            return  # chosen variant is inactive / missing / blank → fallback
        candidate_block["profile_text"] = row.text
        context_set["candidate"] = candidate_block
        logger.info(
            "β.6d — applied summary variant id=%d (%s) to context for app=%s",
            row.id,
            "pinned" if pinned_id is not None else "recommended",
            app_id,
        )
    finally:
        session.close()


def _apply_chosen_experience_summaries(context_set: dict) -> None:
    """B.4 (Sprint 6.6) — patch each career_corpus experience's `summary` in-place with the chosen ExperienceSummaryItem variant text (WYSIWYG; OPT-IN, no auto-fallback).

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
            row = (
                session.query(ExperienceSummaryItem)
                .filter_by(
                    id=item_id,
                    experience_id=eid,
                    is_active=1,
                )
                .first()
            )
            if row is None or not (row.text or "").strip():
                continue  # missing / inactive / foreign → role gets no intro
            exp["summary"] = row.text
            applied += 1
        if applied:
            logger.info(
                "B.4 — applied %d chosen per-role intro(s) to corpus for app=%s",
                applied,
                context_set.get("application_id"),
            )
    finally:
        session.close()


def _apply_recommended_skills(context_set: dict) -> None:
    """B.5 (Sprint 6.6) — reorder / filter context_set["candidate"]["skills"] to the curated set for this application (in-memory patch before the LLM sees the context).

    The effective ordered set is computed by resolve_skill_selection from
    ctx["llm_skill_recommendations"] + composition_overrides
    (pinned_skill_ids / excluded_skill_ids / skill_order), over the candidate's
    active, approved Skill rows. Pending/retired skills can never appear.

    No-op when there's no recommendation AND no skill overrides → the
    candidate's skills list (and the generate prompt's Skills line) stays
    byte-identical. Only meaningful in corpus mode (needs an application_id
    whose candidate owns the Skill rows).
    """
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
        rows = (
            session.query(Skill)
            .filter_by(
                candidate_id=app_row.candidate_id,
                is_active=1,
                is_pending_review=0,
            )
            .order_by(Skill.display_order, Skill.id)
            .all()
        )
        name_by_id = {r.id: r.name for r in rows if (r.name or "").strip()}
        all_active_ids = [r.id for r in rows if r.id in name_by_id]
        ordered = resolve_skill_selection(
            all_active_ids=all_active_ids,
            rec_ids=rec_ids,
            pinned=pinned,
            excluded=excluded,
            skill_order=skill_order,
        )
        candidate_block["skills"] = [name_by_id[sid] for sid in ordered if sid in name_by_id]
        context_set["candidate"] = candidate_block
        logger.info(
            "B.5 — applied curated skill set (%d skills) to context for app=%s",
            len(candidate_block["skills"]),
            app_id,
        )
    finally:
        session.close()


# --- Routes ---


@generation_bp.route("/api/save-edits", methods=["POST"])
def save_edits() -> ResponseReturnValue:
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
    output_dir = current_app.config["OUTPUT_DIR"]
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
        return jsonify(
            {"error": "At least one of edited_resume or edited_cover_letter required"}
        ), 400

    cp = Path(context_path)
    if not _within(cp, output_dir):
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

    saved_resume = False
    saved_cover = False
    if edited_resume.strip():
        context_set["edited_resume_text"] = edited_resume
        # WYSIWYG (walkthrough D1/D2): recompute the cached JSON Resume the preview
        # route serves so the styled preview reflects the edit immediately — same
        # deterministic path the download uses (normalize → md_to_json_resume), no
        # LLM, no iteration advance. Preview == the future download of these edits.
        from generator import _normalize_markdown
        from json_resume import md_to_json_resume

        context_set["last_generated_json_resume"] = md_to_json_resume(
            _normalize_markdown(edited_resume)
        )
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
    notes.append(
        {
            "timestamp": datetime.now().isoformat(),
            "action": "save_edits",
            "summary": f"edits saved as baseline for: {', '.join(targets)}",
        }
    )
    context_set["iteration_notes"] = notes

    cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")

    # D4 durability (generation-experience re-architecture, item (b)): mirror
    # the saved edit onto the DB run row for corpus-backed contexts, so it
    # survives independently of this context_*.json sidecar. Best-effort — the
    # context file above is already the primary, already-persisted source.
    app_run_id = context_set.get("application_run_id")
    if app_run_id is not None and (saved_resume or saved_cover):
        try:
            _persist_edited_text_to_db(
                int(app_run_id),
                edited_resume if saved_resume else None,
                edited_cover_letter if saved_cover else None,
            )
        except Exception as exc:
            logger.error(
                "Edited-text DB persist failed (run_id=%s): %s", app_run_id, exc, exc_info=True
            )

    logger.info(
        "Saved edits for %s: resume=%s cover_letter=%s",
        safe_user,
        saved_resume,
        saved_cover,
    )
    return jsonify(
        {
            "ok": True,
            "saved_resume": saved_resume,
            "saved_cover_letter": saved_cover,
            "context_path": str(cp),
        }
    )


def _frozen_composition(context_set: ContextSet) -> dict[str, Any] | None:
    """Return the frozen ``approved_composition`` doc for a corpus context, else None.

    Generation-experience re-architecture Phase 4 — the deterministic-assemble gate.
    Present ONLY when Compose has frozen an approved_composition (Save-and-continue)
    AND this is a corpus context (``career_corpus``). A corpus context that predates
    the freeze, or any legacy file-based context (no ``career_corpus``), returns None
    and falls through to the UNCHANGED generate() LLM path — so legacy + --suite
    synthetic stay byte-identical.
    """
    if not context_set.get("career_corpus"):
        return None
    doc = context_set.get("approved_composition")
    if not isinstance(doc, dict):
        return None
    basics = doc.get("basics")
    summary = basics.get("summary") if isinstance(basics, dict) else None
    has_content = bool(doc.get("work") or summary or doc.get("skills"))
    return doc if has_content else None


def _assemble_from_frozen_composition(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict[str, Any],
    doc: dict[str, Any],
    *,
    with_cover_letter: bool,
    username: str,
    run_id: str,
) -> dict[str, Any]:
    """Build the generate()-shaped result dict from a frozen composition — no résumé LLM.

    The résumé body IS the frozen ``approved_composition`` (rendered directly by the
    caller via generate_resume_from_json_resume); this returns the SAME dict shape
    generate() returns, so the shared post-LLM path (render / ATS / persist / snapshot
    / response) needs no other change. ``resume_content`` is a deterministic
    ``json_resume_to_markdown`` view of the doc (the editable secondary surface + the
    generated_resume_md audit column + the cover-letter résumé context). The COVER
    LETTER, when opted in, is a real LLM call (``generate_cover_letter_against_resume``,
    call_kind="generate_cover_letter"). Audit ``selected_bullets`` are synthesized from
    the frozen ``meta.sartor.work_provenance`` so the application_bullet chain still
    fills. Charter C-6: zero LLM for the résumé body.
    """
    from json_resume import json_resume_to_markdown

    resume_md = json_resume_to_markdown(doc)

    cover_letter = ""
    if with_cover_letter:
        cl = generate_cover_letter_against_resume(
            client,
            context_set,
            analysis,
            resume_md,
            username=username,
            run_id=run_id,
        )
        cover_letter = str(cl.get("cover_letter_content") or "")

    meta = doc.get("meta")
    sartor = meta.get("sartor") if isinstance(meta, dict) else None
    provenance = sartor.get("work_provenance") if isinstance(sartor, dict) else None
    selected_bullets = [
        {
            "experience_id": wp.get("experience_id"),
            "chosen_title_id": wp.get("title_id"),
            "bullet_ids_in_order": wp.get("highlight_ids") or [],
        }
        for wp in (provenance or [])
        if isinstance(wp, dict) and wp.get("experience_id") is not None
    ]

    return {
        "resume_content": resume_md,
        "cover_letter_content": cover_letter,
        "changes_made": [],
        "proofread_notes": [],
        "selected_bullets": selected_bullets,
        "proposed_new_bullets": [],
        "proposed_experience_titles": [],
    }


@generation_bp.route("/api/generate", methods=["POST"])
def run_generation() -> ResponseReturnValue:
    """P8 Human Gate #2: generates documents after user reviewed analysis.

    Iteration model: each call writes a NEW context file (via
    save_iteration_context) rather than mutating the prior one. The new file
    carries `parent_context_path` back to the input context, an incremented
    `iteration` counter, and `last_generated_*` snapshots for the frontend's
    edit-detection diff. The returned `context_path` is the NEW file's path —
    the frontend must use it for any subsequent calls (refine, iterate-clarify,
    save-edits) so the iteration chain is preserved.
    """
    output_dir = current_app.config["OUTPUT_DIR"]
    configs_dir = current_app.config["CONFIGS_DIR"]
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
    if not _within(cp, output_dir):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    # Reload the saved context set (P4 Disposable Blueprint)
    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})

    if not analysis:
        return jsonify({"error": "No valid analysis found in context"}), 400

    logger.info(
        "Starting generation for %s (iteration=%s)", username, context_set.get("iteration", 0)
    )

    # The _apply_* helpers treat the context_set as a loose dict (they read /
    # write keys outside the ContextSet schema). It is a dict at runtime; cast
    # so the in-place mutations land on the same object.
    cs = cast(dict, context_set)
    client = _get_client()
    # Re-use the run_id minted in /api/analyze when present so both calls
    # share an ID in telemetry. New ID for legacy contexts that pre-date
    # this field (or for one-off /api/generate calls without a prior analyze).
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]

    # Phase 4 — corpus-mode DETERMINISTIC assemble: when Compose has frozen an
    # approved_composition, render THAT (zero résumé-body LLM calls) instead of
    # calling generate(). The cover letter stays an LLM call. Legacy + pre-freeze
    # corpus contexts fall through to the UNCHANGED generate() path (byte-identical).
    frozen_doc = _frozen_composition(context_set)
    try:
        if frozen_doc is not None:
            result = _assemble_from_frozen_composition(
                client,
                context_set,
                analysis,
                frozen_doc,
                with_cover_letter=with_cover_letter,
                username=username,
                run_id=run_id,
            )
        else:
            # β.6d / B.4 / B.5 — apply the user's chosen summary / per-role intros /
            # skill curation into the corpus snapshot before the LLM sees it (no-op
            # in legacy). Skipped in the frozen-composition path — the freeze already
            # resolved them into approved_composition.
            _apply_chosen_summary(cs)
            _apply_chosen_experience_summaries(cs)
            _apply_recommended_skills(cs)
            result = generate(
                client,
                context_set,
                analysis,
                refinement_notes=refinement_notes,
                username=username,
                run_id=run_id,
                with_cover_letter=with_cover_letter,
            )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic API connection error during generation: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error(
            "LLM generation response failed validation after retry: %s", exc.validation_error
        )
        return jsonify(
            {
                "error": "AI generation response was malformed after retry. Please try again.",
                "detail": exc.validation_error,
            }
        ), 502

    # C3 guardrail: strip any cover-letter block that leaked into the résumé
    # markdown before it is saved / rendered (deterministic; no-op when clean).
    from hardening import strip_cover_letter_block

    if isinstance(result.get("resume_content"), str):
        result["resume_content"] = strip_cover_letter_block(result["resume_content"])

    safe_user = _safe_username(username, configs_dir=configs_dir) if username else None
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
            template_path = context_set["resume"].get(
                "path"
            ) or _resolve_default_persona_template_path(
                username=safe_user,
                application_id=int(ctx_app_id) if ctx_app_id is not None else None,
            )
    # Phase 4 — the frozen composition renders DIRECTLY from the JSON-Resume doc
    # (download == preview == approved_composition by construction; no markdown
    # round-trip). Legacy renders from the LLM's markdown as before.
    if frozen_doc is not None:
        resume_path = generate_resume_from_json_resume(
            frozen_doc,
            output_format,
            safe_user,
            str(output_dir),
            template_path=template_path,
        )
    else:
        resume_path = generate_resume(
            result["resume_content"],
            output_format,
            safe_user,
            str(output_dir),
            template_path=template_path,
        )
    # Phase β.5 — only write the cover-letter file when the call actually
    # produced one. The /api/generate-cover-letter route does the writing
    # for opt-in cover letters after the résumé is finalized.
    cover_letter_path = ""
    if (result.get("cover_letter_content") or "").strip():
        cover_letter_path = generate_cover_letter(
            result["cover_letter_content"], safe_user, str(output_dir)
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
                    ats_findings["status"],
                    resume_path,
                    ats_findings["notes"],
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
                int(app_run_id),
                result,
                ats_findings=ats_findings,
            )
        except Exception as exc:
            # Persistence failure must not break the user's generate flow —
            # the markdown is already produced and saved to disk. Log loudly.
            logger.error(
                "Corpus generation persist failed (run_id=%s): %s", app_run_id, exc, exc_info=True
            )

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
        base_dir=str(output_dir),
        action="generate",
        summary=summary,
    )
    new_iteration = int(context_set.get("iteration", 0) or 0) + 1
    logger.info(
        "Iteration %d snapshotted: %s (parent=%s)",
        new_iteration,
        new_context_path,
        str(cp),
    )

    return jsonify(
        {
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
        }
    )


@generation_bp.route("/api/generate/stream", methods=["POST"])
def run_generation_stream() -> ResponseReturnValue:
    """R2 streaming variant of /api/generate.

    Same request shape and same final response payload as /api/generate,
    but the LLM call streams tokens via SSE so the frontend can show a
    live "alive" indicator (token counter + collapsible raw stream)
    during the ~50s Sonnet 5 call. All pre-LLM validation runs upfront
    and returns plain JSON on failure; all post-LLM persistence (file
    writes, ATS round-trip, DB persist, iteration snapshot) runs inside
    the stream's `done` branch and rides the final SSE event.

    Event types on the SSE stream:
      - `chunk`: `{"text": "<delta>"}` per text delta
      - `retry`: `{"reason": "<error>"}` when a parse retry begins
      - `done`:  the full payload the non-streaming /api/generate returns
      - `error`: `{"error": "<msg>", "http_status": <int>, "detail"?: "..."}`
    """
    # Read config in the request context, before the generator (which runs
    # lazily, after this function returns) — `current_app` is not available
    # once `stream()` starts yielding, so capture the path as a local.
    output_dir = current_app.config["OUTPUT_DIR"]
    configs_dir = current_app.config["CONFIGS_DIR"]
    data = request.json
    username = data.get("username", "")
    context_path = data.get("context_path", "")
    output_format = data.get("output_format", "")
    refinement_notes = data.get("refinement_notes", "")
    with_cover_letter = bool(data.get("generate_cover_letter", False))

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    cp = Path(context_path)
    if not _within(cp, output_dir):
        return jsonify({"error": "Invalid context path"}), 403
    if not cp.exists():
        return jsonify({"error": "Context file not found"}), 404

    context_set: ContextSet = json.loads(cp.read_text(encoding="utf-8"))
    analysis = context_set.get("llm_analysis", {})
    if not analysis:
        return jsonify({"error": "No valid analysis found in context"}), 400

    logger.info(
        "Starting streaming generation for %s (iteration=%s)",
        username,
        context_set.get("iteration", 0),
    )
    # The _apply_* helpers treat the context_set as a loose dict (they read /
    # write keys outside the ContextSet schema). It is a dict at runtime; cast
    # so the in-place mutations land on the same object.
    cs = cast(dict, context_set)
    # Phase 4 — corpus-mode deterministic assemble when Compose froze an
    # approved_composition. Computed here (request context) so it is captured in
    # the stream() closure below.
    frozen_doc = _frozen_composition(context_set)
    if frozen_doc is None:
        # Apply the chosen summary / per-role intros / skill curation before the
        # LLM sees the corpus (no-op in legacy). Skipped in the frozen path — the
        # freeze already resolved them into approved_composition.
        _apply_chosen_summary(cs)
        _apply_chosen_experience_summaries(cs)
        _apply_recommended_skills(cs)

    safe_user = _safe_username(username, configs_dir=configs_dir) if username else None
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
            template_path = context_set["resume"].get(
                "path"
            ) or _resolve_default_persona_template_path(
                username=safe_user,
                application_id=int(ctx_app_id) if ctx_app_id is not None else None,
            )

    client = _get_client()
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]

    def stream() -> Iterator[str]:
        """SSE generator: stream the résumé-generation events to the client."""
        try:
            result: dict | None = None
            if frozen_doc is not None:
                # Phase 4 — deterministic assemble: NO résumé-body LLM. Emit the
                # assembled markdown as a single chunk so the live view shows
                # content, then fall through to the shared post-LLM path.
                result = _assemble_from_frozen_composition(
                    client,
                    context_set,
                    analysis,
                    frozen_doc,
                    with_cover_letter=with_cover_letter,
                    username=safe_user,
                    run_id=run_id,
                )
                yield _sse("chunk", {"text": result["resume_content"]})
            else:
                for event_kind, payload in generate_streaming(
                    client,
                    context_set,
                    analysis,
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
                yield _sse(
                    "error",
                    {
                        "error": "Streaming generate finished without a parsed result.",
                        "http_status": 502,
                    },
                )
                return

            # Post-LLM persistence — mirror the non-streaming route.
            # Phase 4 — the frozen composition renders directly from its JSON-Resume
            # doc (download == preview == approved_composition); legacy from markdown.
            if frozen_doc is not None:
                resume_path = generate_resume_from_json_resume(
                    frozen_doc,
                    resolved_output_format,
                    safe_user,
                    str(output_dir),
                    template_path=template_path,
                )
            else:
                resume_path = generate_resume(
                    result["resume_content"],
                    resolved_output_format,
                    safe_user,
                    str(output_dir),
                    template_path=template_path,
                )
            cover_letter_path = ""
            if (result.get("cover_letter_content") or "").strip():
                cover_letter_path = generate_cover_letter(
                    result["cover_letter_content"],
                    safe_user,
                    str(output_dir),
                )
            logger.info(
                "Streaming generation complete: %s, %s",
                resume_path,
                cover_letter_path,
            )

            ats_findings: dict | None = None
            if resolved_output_format == ".docx":
                try:
                    from db.ats_roundtrip import run_ats_roundtrip

                    ats_findings = run_ats_roundtrip(resume_path, result["resume_content"])
                    if ats_findings["status"] != "pass":
                        logger.warning(
                            "ATS round-trip %s on %s: %s",
                            ats_findings["status"],
                            resume_path,
                            ats_findings["notes"],
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
                        int(app_run_id),
                        result,
                        ats_findings=ats_findings,
                    )
                except Exception as exc:
                    logger.error(
                        "Corpus generation persist failed (run_id=%s): %s",
                        app_run_id,
                        exc,
                        exc_info=True,
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
                base_dir=str(output_dir),
                action="generate",
                summary=summary,
            )
            new_iteration = int(context_set.get("iteration", 0) or 0) + 1
            logger.info(
                "Iteration %d snapshotted: %s (parent=%s)",
                new_iteration,
                new_context_path,
                str(cp),
            )

            yield _sse(
                "done",
                {
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
                },
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Anthropic API connection error during streaming generation: %s", exc)
            yield _sse(
                "error",
                {
                    "error": "Connection to AI service failed. Please try again.",
                    "http_status": 503,
                },
            )
        except LLMResponseError as exc:
            logger.error(
                "LLM streaming generation response failed validation after retry: %s",
                exc.validation_error,
            )
            yield _sse(
                "error",
                {
                    "error": "AI generation response was malformed after retry. Please try again.",
                    "detail": exc.validation_error,
                    "http_status": 502,
                },
            )
        except Exception:
            logger.exception("Streaming generation failed unexpectedly")
            yield _sse(
                "error",
                {
                    "error": "Internal error during generation.",
                    "http_status": 500,
                },
            )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@generation_bp.route("/api/validate-refinement", methods=["POST"])
def validate_refinement() -> ResponseReturnValue:
    """Scope-check a single refinement note before running generation."""
    data = request.json
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"valid": False, "reason": "Empty refinement note."}), 400
    client = _get_client()
    result = check_refinement_scope(client, note)
    return jsonify(result)


@generation_bp.route("/api/generate-cover-letter", methods=["POST"])
def run_generate_cover_letter() -> ResponseReturnValue:
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

    output_dir = current_app.config["OUTPUT_DIR"]
    configs_dir = current_app.config["CONFIGS_DIR"]
    data = request.json or {}
    username = data.get("username", "")
    context_path = data.get("context_path", "")
    refinement_notes = data.get("refinement_notes", "")

    if not context_path:
        return jsonify({"error": "context_path required"}), 400
    cp = Path(context_path)
    if not _within(cp, output_dir):
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
        return jsonify(
            {
                "error": "No résumé to base the cover letter on. Run /api/generate first.",
                "needs_resume": True,
            }
        ), 409

    safe_user = _safe_username(username, configs_dir=configs_dir) if username else None
    if not safe_user:
        safe_user = secure_filename(cp.parent.name)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    client = _get_client()
    run_id = context_set.get("run_id") or uuid.uuid4().hex[:12]
    try:
        result = generate_cover_letter_against_resume(
            client,
            context_set,
            analysis,
            resume_content,
            refinement_notes=refinement_notes,
            username=username,
            run_id=run_id,
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic connection error during cover-letter generate: %s", exc)
        return jsonify({"error": "Connection to AI service failed. Please try again."}), 503
    except LLMResponseError as exc:
        logger.error("Cover-letter LLM response failed validation: %s", exc.validation_error)
        return jsonify(
            {
                "error": "AI cover-letter response was malformed after retry.",
                "detail": exc.validation_error,
            }
        ), 502

    cl_content = (result.get("cover_letter_content") or "").strip()
    if not cl_content:
        return jsonify({"error": "LLM returned an empty cover letter."}), 502

    cover_letter_path = generate_cover_letter(cl_content, safe_user, str(output_dir))

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
                app_run_id,
                exc,
                exc_info=True,
            )

    return jsonify(
        {
            "cover_letter_path": cover_letter_path,
            "cover_letter_preview": cl_content,
            "context_path": str(cp),
            "proofread_notes": result.get("proofread_notes", []),
        }
    )


@generation_bp.route("/api/download/<path:filepath>")
def download_file(filepath: str) -> ResponseReturnValue:
    """Stream a generated output file as an attachment, contained to OUTPUT_DIR."""
    full_path = Path(filepath)
    # F-10: a RELATIVE filepath is re-anchored under OUTPUT_DIR (what
    # /api/download-edited now hands back — a relative segment URL-composes
    # cleanly cross-platform, where an absolute POSIX path would double-slash
    # the URL and a Windows path carries a drive colon). Absolute paths keep
    # working for legacy callers. Re-anchoring happens BEFORE the exists +
    # containment checks below, so the unchanged _within gate judges the final
    # resolved path — a traversal like ../../etc/passwd still 403s.
    if not full_path.is_absolute():
        full_path = Path(current_app.config["OUTPUT_DIR"]) / filepath
    if not full_path.exists():
        return jsonify({"error": "File not found"}), 404
    # Security: ensure the file is within our output directory. _within IS this
    # resolve()/relative_to containment check (web_infra.security) — calling the
    # canonical guard instead of an inline copy is what the F-sec-05 route-
    # containment gate asserts. This route is path-keyed (no <username>), so it
    # carries _within but no _safe_username (the gate's reviewed exemption).
    if not _within(full_path, current_app.config["OUTPUT_DIR"]):
        return jsonify({"error": "Access denied"}), 403
    return send_file(str(full_path), as_attachment=True)


@generation_bp.route("/api/download-edited", methods=["POST"])
def download_edited() -> ResponseReturnValue:
    """Regenerate a document from edited preview content; return its download URL.

    F-10: responds with JSON ``{download_url, filename}`` pointing at GET
    /api/download/<path> (an OUTPUT_DIR-relative path) instead of streaming the
    bytes — the client follows the URL as a plain navigation so the browser's
    download manager owns the save (no blob + synthetic-click, no silent Chrome
    multiple-downloads block).
    """
    output_dir = current_app.config["OUTPUT_DIR"]
    resumes_dir = current_app.config["RESUMES_DIR"]
    data = request.json
    username = data.get("username", "")
    content = data.get("content", "")
    doc_type = data.get("type", "resume")  # "resume" or "cover_letter"
    output_format = data.get("original_format", ".docx")  # field name kept for JS compat
    template_path = data.get("template_path", "")
    persona_template_id = data.get("persona_template_id")

    if not username or not content:
        return jsonify({"error": "username and content required"}), 400

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
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
        if not _within(tp, resumes_dir) or not tp.exists():
            template_path = None

    if doc_type == "resume":
        path = generate_resume(
            content,
            output_format,
            safe_user,
            str(output_dir),
            template_path=template_path or None,
        )
    else:
        # Cover letter honors the chosen format too (feat/cover-letter-formats).
        # The persona template (resolved above for .docx/.pdf) lends its font: the
        # .pdf renders through personas/cover_letter.html, the .docx borrows the
        # same CSS primary family — so the letter matches the chosen résumé persona.
        path = generate_cover_letter(
            content,
            safe_user,
            str(output_dir),
            output_format=output_format,
            template_path=template_path or None,
        )

    # F-10 (2026-07 UX review) — hand back a URL onto the existing GET
    # /api/download/<path:filepath> route (send_file(as_attachment=True) there —
    # the Content-Disposition: attachment header this relies on) instead of
    # streaming the bytes on THIS response. The client follows up with a plain
    # top-level navigation (window.location.href) rather than a blob-URL +
    # synthetic <a>.click() — the blob/synthetic-click pattern is what Chrome's
    # "multiple automatic downloads" heuristic could silently block on the
    # second download without a fresh user gesture (the retired in-app caveat).
    # A navigation to an attachment response isn't a popup and isn't subject to
    # that heuristic, and this POST's fetch() still surfaces a generation
    # failure to the caller as JSON (unchanged error behavior) before any
    # navigation happens. The URL carries the path RELATIVE to OUTPUT_DIR
    # (download_file re-anchors a relative filepath there before its unchanged
    # containment gate): an absolute POSIX path would open with "/" and
    # double-slash the URL (Werkzeug's merge_slashes redirect then mangles it),
    # a Windows path carries a drive colon — relative composes cleanly on both
    # and leaks no server filesystem layout. quote() percent-encodes anything a
    # URL path segment can't carry raw (e.g. spaces); Werkzeug decodes it back
    # before routing.
    rel_path = Path(path).resolve().relative_to(Path(str(output_dir)).resolve())
    return jsonify(
        {
            "download_url": f"/api/download/{quote(rel_path.as_posix())}",
            "filename": Path(path).name,
        }
    )

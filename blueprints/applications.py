"""Applications seam — the job-application tracker + per-application Compose.

The fifth domain blueprint extracted from `app.py` (Sprint 8.3f, the app.py ->
blueprints decomposition). Owns the thirteen routes that list/show applications,
update their status/notes/title-company, read + persist the per-application
Compose composition overrides, run the per-application LLM recommend/suggest
steps, and serve the candidate-memory clarifications list, plus their domain-only
helpers (`_application_summary_dict`, `_build_resume_state`,
`_find_context_path_for_run`, `_load_application_owned`,
`_latest_analysis_essentials`, and the seven context-override readers):

    GET    /api/users/<u>/applications                          list_applications
    GET    /api/applications/<id>                               get_application
    PUT    /api/applications/<id>/status                        update_application_status
    PUT    /api/applications/<id>/notes                         update_application_notes
    PUT    /api/applications/<id>/meta                          update_application_meta
    GET    /api/applications/<id>/composition                   get_application_composition
    POST   /api/applications/<id>/composition                   save_application_composition
    POST   /api/applications/<id>/recommend                     recommend_application_bullets
    POST   /api/applications/<id>/recommend-summary             recommend_application_summary
    POST   /api/applications/<id>/recommend-experience-summaries
                                                  recommend_application_experience_summaries
    POST   /api/applications/<id>/recommend-skills              recommend_application_skills
    POST   /api/applications/<id>/suggest-skills                suggest_application_skills
    GET    /api/users/<u>/clarifications                        list_clarifications

Registered with **no url_prefix** so the full `/api/...` paths stay byte-identical
to the app.py originals. Reads paths from `current_app.config[...]` (the injected
Config), never the app.py module globals. `_load_application_owned` is canonical
here — `blueprints/templates.py` imports it for its preview routes (the 8.3e
transitional duplicate is gone). The five recommend/suggest routes catch
`anthropic` error types, so this module is on the egress allowlist; the actual
LLM calls live in `analyzer` (imported lazily in each route).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import anthropic
from flask import Blueprint, current_app, jsonify, request
from flask.typing import ResponseReturnValue

from blueprints.corpus import _skill_to_dict, _tag_list
from web_infra import _error_detail_payload, _get_client, _safe_username, _within

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from db.models import Application, ApplicationRun

logger = logging.getLogger(__name__)

applications_bp = Blueprint("applications", __name__)


# ---------------------------------------------------------------------------
# Phase D.3: Applications list routes
# ---------------------------------------------------------------------------

# Canonical lifecycle statuses (migration 0007; semantics table in
# docs/dev/RELEASE_ARC.md, agreed 2026-05-29). `interview` is terminal —
# the product's signal is "this résumé got a callback", not job-hunt
# bookkeeping past that point (B.8 Part 1 decision, 2026-06-10).
_VALID_APP_STATUSES = frozenset({"draft", "submitted", "interview", "rejected", "withdrawn"})


def _application_summary_dict(
    app_row: Application, runs: list[ApplicationRun], pending_proposal_count: int
) -> dict[str, Any]:
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


@applications_bp.route("/api/users/<username>/applications", methods=["GET"])
def list_applications(username: str) -> ResponseReturnValue:
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

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    raw_status = (request.args.get("status") or "").strip().lower()
    wanted_statuses: set[str] = set()
    if raw_status:
        wanted_statuses = {s.strip() for s in raw_status.split(",") if s.strip()}
        invalid = wanted_statuses - _VALID_APP_STATUSES
        if invalid:
            return jsonify(
                {
                    "error": f"status must be among {sorted(_VALID_APP_STATUSES)}; "
                    f"got {sorted(invalid)}",
                }
            ), 400

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
        return jsonify(
            {
                "error": "Failed to load applications",
                **_error_detail_payload(exc),
            }
        ), 500


@applications_bp.route("/api/applications/<int:application_id>", methods=["GET"])
def get_application(application_id: int) -> ResponseReturnValue:
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
        safe_user = (
            _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"])
            if candidate
            else None
        )
        if candidate is None or safe_user is None:
            return jsonify({"error": "Candidate validation failed"}), 403

        runs_sorted = sorted(app_row.runs, key=lambda r: r.iteration)
        runs_dict = []
        for r in runs_sorted:
            pending = (
                session.query(ProposalReview)
                .filter_by(
                    application_run_id=r.id,
                    decision="pending",
                )
                .count()
            )
            runs_dict.append(
                {
                    "id": r.id,
                    "iteration": r.iteration,
                    "run_id": r.run_id,
                    "prompt_version": r.prompt_version,
                    "persona_template_id": r.persona_template_id,
                    "created_at": r.created_at,
                    "has_resume": r.generated_resume_md is not None,
                    "has_cover_letter": r.generated_cover_letter_md is not None,
                    "has_edits": (
                        r.edited_resume_text is not None or r.edited_cover_letter_text is not None
                    ),
                    "pending_proposals": pending,
                    "ats_roundtrip_status": _parse_ats_status(r.ats_roundtrip_json),
                }
            )

        return jsonify(
            {
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
            }
        )
    finally:
        session.close()


def _build_resume_state(safe_user: str, runs_sorted: list[ApplicationRun]) -> dict[str, Any]:
    """Package the frontend state needed to resume a prior application at its furthest wizard step.

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
        ctx_data: dict[str, Any] | None = None
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
            return {**base, "target_step": 6, "resume_md": resume_md, "cover_letter_md": cover_md}

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

        state = {
            **base,
            "target_step": target_step,
            "analysis": analysis,
            "deterministic": deterministic,
        }
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
        return cast("str | None", json.loads(blob).get("status"))
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
    user_dir = current_app.config["OUTPUT_DIR"] / safe_user
    if not user_dir.is_dir():
        return None
    best: tuple[int, float, str] | None = None  # (iteration, mtime, path)
    for cp in user_dir.glob("context_*.json"):
        if not _within(cp, current_app.config["OUTPUT_DIR"]):
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


@applications_bp.route("/api/applications/<int:application_id>/status", methods=["PUT"])
def update_application_status(application_id: int) -> ResponseReturnValue:
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
        if candidate is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Candidate validation failed"}), 403
        app_row.status = status
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if status == "submitted" and app_row.sent_at is None:
            app_row.sent_at = now_ts
        if status in {"interview", "rejected", "withdrawn"} and app_row.outcome_at is None:
            app_row.outcome_at = now_ts
        session.commit()
        return jsonify(
            {
                "id": app_row.id,
                "status": app_row.status,
                "sent_at": app_row.sent_at,
                "outcome_at": app_row.outcome_at,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@applications_bp.route("/api/applications/<int:application_id>/notes", methods=["PUT"])
def update_application_notes(application_id: int) -> ResponseReturnValue:
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


@applications_bp.route("/api/applications/<int:application_id>/meta", methods=["PUT"])
def update_application_meta(application_id: int) -> ResponseReturnValue:
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
        return jsonify(
            {
                "id": app_row.id,
                "title": app_row.title,
                "company": app_row.company,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Workstream B: per-application Compose step (fit-ranked bullets/titles)
# ---------------------------------------------------------------------------


def _load_application_owned(session: Session, application_id: int) -> tuple[Any, Any]:
    """Return (app_row, candidate) for an application, or (None, None), after _safe_username defense.

    Slots are typed ``Any`` (``tuple[Any, Any]``) by design — parametrized only to
    satisfy mypy ``--strict``'s ``disallow_any_generics`` while preserving the
    untyped unpack-then-check contract exactly. The two slots are correlated (both
    set or both ``None``), which the type system can't express across the callers'
    ``app_row, candidate = ...; if app_row is None: ...`` pattern. The precise
    ``tuple[Application | None, Candidate | None]`` would force a None-narrowing
    change at ~10 call sites — a separate None-safety pass, out of scope for a
    typing-ratchet branch (the call-site contract was already untyped before
    ``session`` was typed under ANN).
    """
    from db.models import Application, Candidate

    app_row = session.query(Application).filter_by(id=application_id).first()
    if app_row is None:
        return None, None
    candidate = session.query(Candidate).filter_by(id=app_row.candidate_id).first()
    if candidate is None or not _safe_username(
        candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
    ):
        return None, None
    return app_row, candidate


def _latest_analysis_essentials(app_row: Application) -> set[str]:
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
    """Return (pinned, excluded) bullet-id sets from a context file validated under OUTPUT_DIR.

    Empty sets when absent/invalid.
    """
    if not context_path:
        return set(), set()
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
        return set(), set()
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), set()
    ov = ctx.get("composition_overrides") or {}
    return set(ov.get("pinned", []) or []), set(ov.get("excluded", []) or [])


def _read_bullet_order(context_path: str) -> dict[int, list[int]]:
    """Return per-experience explicit bullet order from a context file's `composition_overrides.bullet_order`.

    Maps experience-id → ordered `[bullet_id, ...]`. Validated within OUTPUT_DIR. Empty dict when
    absent/invalid. Keys and ids are coerced to int (JSON persists keys as
    strings); malformed entries are skipped, not fatal.
    """
    if not context_path:
        return {}
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
    """Return per-experience pinned title from a context file's `composition_overrides.pinned_title_ids`.

    Maps experience-id → chosen ExperienceTitle id. Validated within OUTPUT_DIR.
    Empty dict when absent/invalid. Keys and ids are coerced to int (JSON persists keys as strings);
    malformed entries are skipped, not fatal.
    """
    if not context_path:
        return {}
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
) -> tuple[dict[int, dict[str, Any]], dict[int, int], bool]:
    """B.4: Return per-role intro state (recs_by_exp, chosen_by_exp, use_experience_summaries) from a context file.

    - recs_by_exp: experience-id → {summary_item_id, rationale, alternates}
      from `llm_experience_summary_recommendations.recommendations`.
    - chosen_by_exp: experience-id → chosen ExperienceSummaryItem id from
      `composition_overrides.chosen_experience_summary_ids`.
    - use_experience_summaries: the "Add role intros" toggle state.
    _within-gated by OUTPUT_DIR. Returns ({}, {}, False) on read/parse failure
    so the route degrades to "no role intros" rather than 500ing.
    """
    empty: tuple[dict[int, dict[str, Any]], dict[int, int], bool] = ({}, {}, False)
    if not context_path:
        return empty
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
        return empty
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty

    rec_block = ctx.get("llm_experience_summary_recommendations") or {}
    recs_by_exp: dict[int, dict[str, Any]] = {}
    if isinstance(rec_block, dict):
        for rec in rec_block.get("recommendations") or []:
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
    """B.5: Return skill curation state (pinned_ids, excluded_ids, order, recommended_ids) from a context file.

    Reuses the deterministic corpus readers. _within-gated by OUTPUT_DIR;
    returns empties / None on read/parse failure so the Compose UI degrades to
    the default (all active+approved skills) rather than 500ing.
    """
    from corpus_to_json_resume import _read_skill_overrides, _read_skill_recommendations

    empty: tuple[set[int], set[int], list[int], list[int] | None] = (set(), set(), [], None)
    if not context_path:
        return empty
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
) -> tuple[dict[str, Any] | None, int | None]:
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
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
) -> tuple[set[int], dict[int, dict[str, Any]]]:
    """Return (added bullet-id set, recommendations dict keyed by experience id) from a context file.

    Reads `composition_overrides.added` and `llm_recommendations` from the
    context file. Empty / {} when absent. _within-gated by OUTPUT_DIR.
    """
    if not context_path:
        return set(), {}
    cp = Path(context_path)
    if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
        return set(), {}
    try:
        ctx = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), {}
    added = set(int(x) for x in ((ctx.get("composition_overrides") or {}).get("added") or []))
    rec_by_exp: dict[int, dict[str, Any]] = {}
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


@applications_bp.route("/api/applications/<int:application_id>/composition", methods=["GET"])
def get_application_composition(application_id: int) -> ResponseReturnValue:
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

        experiences = (
            session.query(Experience)
            .filter_by(
                candidate_id=candidate.id,
            )
            .order_by(Experience.start_date.desc(), Experience.id.desc())
            .all()
        )

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
                    b.text,
                    bool(b.has_outcome),
                    tags,
                    jd_kw,
                    essential,
                )
                scored_bullets.append(
                    {
                        "id": b.id,
                        "text": b.text,
                        "score": round(score, 2),
                        "has_outcome": bool(b.has_outcome),
                        "is_pending_review": bool(b.is_pending_review),
                        "tags": _tag_list(b.tag_links),
                        "pinned": b.id in pinned,
                        "excluded": b.id in excluded,
                        "recommended": b.id in rec_ids,
                        "added": b.id in added,
                    }
                )
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
                t_toks = {w for w in re.split(r"[^a-z0-9]+", t.title.lower()) if len(w) > 2}
                titles.append(
                    {
                        "id": t.id,
                        "title": t.title,
                        "is_official": bool(t.is_official),
                        "score": round(
                            float(len(t_toks & (jd_kw | essential))),
                            2,
                        ),
                        "tags": _tag_list(t.tag_links),
                        # feat/compose-add-title — the user's per-JD pick for this JD.
                        "pinned": t.id == pinned_tid,
                    }
                )
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
            esi_rows = (
                session.query(ExperienceSummaryItem)
                .filter_by(
                    experience_id=exp.id,
                    is_active=1,
                )
                .order_by(
                    ExperienceSummaryItem.display_order,
                    ExperienceSummaryItem.id,
                )
                .all()
            )
            role_summary_variants: list[dict[str, Any]] = []
            for esi in esi_rows:
                role_summary_variants.append(
                    {
                        "id": esi.id,
                        "text": esi.text,
                        "label": esi.label,
                        "has_outcome": bool(esi.has_outcome),
                        "recommended": esi.id == exp_rec_id,
                        "chosen": esi.id == exp_chosen_id,
                        "rationale": exp_alt_rationale.get(esi.id, ""),
                    }
                )

            if scored_bullets or titles or role_summary_variants:
                out.append(
                    {
                        "id": exp.id,
                        "company": exp.company,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "bullets": scored_bullets,
                        "titles": titles,
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
                    }
                )
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
        si_rows = (
            session.query(SummaryItem)
            .filter_by(
                candidate_id=candidate.id,
                is_active=1,
            )
            .order_by(SummaryItem.display_order, SummaryItem.id)
            .all()
        )
        for s in si_rows:
            summary_variants.append(
                {
                    "id": s.id,
                    "text": s.text,
                    "label": s.label,
                    "has_outcome": bool(s.has_outcome),
                    "recommended": s.id == rec_id,
                    "pinned": s.id == pinned_summary_id,
                }
            )
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
        chosen_summary_id = pinned_summary_id if pinned_summary_id is not None else rec_id

        # B.5 — Skills block. The universe is the candidate's active, approved
        # skills in display order; recommend_skills (if run) flags + orders the
        # recommended ones; pin/drop overrides ride along. `chosen_ids` is the
        # effective ordered set the résumé will surface (resolve_skill_selection,
        # the same logic the preview + generate prompt use). `pending` is the
        # llm_proposed suggestions awaiting approve/deny.
        from corpus_to_json_resume import resolve_skill_selection

        skill_rows = (
            session.query(Skill)
            .filter_by(
                candidate_id=candidate.id,
                is_active=1,
                is_pending_review=0,
            )
            .order_by(Skill.display_order, Skill.id)
            .all()
        )
        rec_rank = {sid: i for i, sid in enumerate(skill_rec_ids or [])}
        skill_items_out = [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
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
        pending_skill_rows = (
            session.query(Skill)
            .filter_by(
                candidate_id=candidate.id,
                is_active=1,
                is_pending_review=1,
            )
            .order_by(Skill.display_order, Skill.id)
            .all()
        )
        pending_skills_out = [
            {"id": s.id, "name": s.name, "category": s.category, "source": s.source}
            for s in pending_skill_rows
        ]

        return jsonify(
            {
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
            }
        )
    finally:
        session.close()


@applications_bp.route("/api/applications/<int:application_id>/composition", methods=["POST"])
def save_application_composition(application_id: int) -> ResponseReturnValue:
    """Persist pin/exclude/add overrides into the application's context file so the next generate() honors them.

    Body: {context_path, pinned[], excluded[], added[]}
    `added` (Workstream I) is bullet ids the user pulled in via the
    per-experience drawer; combined with `llm_recommendations` at
    prompt-build time to form the effective corpus the LLM sees.
    Writes back in place (same pattern as /api/answer-clarifications).
    Filesystem + ownership: _safe_username is enforced inside
    _load_application_owned; _within gates context_path.
    """
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
            return jsonify(
                {"error": "bullet_order must be an object of {experience_id: [bullet_id, ...]}"}
            ), 400
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
            return jsonify(
                {"error": "pinned_title_ids must be an object of {experience_id: title_id}"}
            ), 400
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
            return jsonify(
                {
                    "error": "chosen_experience_summary_ids must be an object of {experience_id: item_id}"
                }
            ), 400
        for k, v in chosen_exp_summary_raw.items():
            try:
                chosen_experience_summary_ids[str(int(k))] = int(v)
            except (TypeError, ValueError):
                return jsonify(
                    {"error": "chosen_experience_summary_ids keys and ids must be integers"}
                ), 400

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
        if app_row is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
        cand_id = candidate.id  # capture before any self-heal rollback (below)
        for eid_str, tid in pinned_title_ids.items():
            exp = (
                session.query(Experience)
                .filter_by(
                    id=int(eid_str),
                    candidate_id=cand_id,
                )
                .first()
            )
            if exp is None:
                return jsonify({"error": f"experience {eid_str} not found for this candidate"}), 400
            eligible = eligible_titles_for(exp)
            if tid not in {t["id"] for t in eligible}:
                # Best-effort self-heal for a rare server-side visibility race
                # (carry-forward ledger #3, the positioning-pin clobber): a title
                # the client just added + pinned can intermittently be unseen by
                # THIS request's read snapshot (pooled SQLite + WAL), which would
                # 400 and drop the pin even though the client sent it correctly.
                # End the current read transaction and re-read with a fresh
                # snapshot before rejecting — a transient-visibility miss then
                # self-heals, while a genuinely stale/foreign id (still ineligible
                # after a guaranteed-fresh read) still 400s. The race resists
                # reproduction, so the heal path is covered by a deterministic
                # miss-then-hit unit test, not an end-to-end repro.
                session.rollback()
                exp = (
                    session.query(Experience)
                    .filter_by(id=int(eid_str), candidate_id=cand_id)
                    .first()
                )
                eligible = eligible_titles_for(exp) if exp is not None else []
                if tid not in {t["id"] for t in eligible}:
                    return jsonify(
                        {"error": f"title {tid} is not an eligible title of experience {eid_str}"}
                    ), 400
            resynced_titles[eid_str] = eligible

        # B.4 — validate each per-role intro pick is an active
        # ExperienceSummaryItem of an experience owned by this candidate. A bad
        # id is a 400 (not a silent drop) so the UI can't pin a stale/foreign id.
        # The sentinel 0 means "explicitly cleared — no intro for this role";
        # it's persisted (so it isn't re-defaulted on reload) but not validated.
        for eid_str, item_id in chosen_experience_summary_ids.items():
            if item_id == 0:
                continue
            exp = (
                session.query(Experience)
                .filter_by(
                    id=int(eid_str),
                    candidate_id=candidate.id,
                )
                .first()
            )
            if exp is None:
                return jsonify({"error": f"experience {eid_str} not found for this candidate"}), 400
            row = (
                session.query(ExperienceSummaryItem)
                .filter_by(
                    id=item_id,
                    experience_id=exp.id,
                    is_active=1,
                )
                .first()
            )
            if row is None:
                return jsonify(
                    {
                        "error": f"summary variant {item_id} is not an active intro of experience {eid_str}"
                    }
                ), 400

        # B.5 — validate pinned + ordered skill ids belong to this candidate's
        # active, approved skills. A foreign/stale id is a 400, not a silent
        # drop. Excluded is lenient (a stale exclusion is harmless — it just
        # excludes nothing).
        skill_ref_ids = set(skill_pinned_in) | set(skill_order_in)
        if skill_ref_ids:
            owned_skill_ids = {
                s.id
                for s in session.query(Skill)
                .filter_by(
                    candidate_id=candidate.id,
                    is_active=1,
                    is_pending_review=0,
                )
                .all()
            }
            bad_skill_ids = skill_ref_ids - owned_skill_ids
            if bad_skill_ids:
                return jsonify(
                    {
                        "error": f"skill ids not owned/active: {sorted(bad_skill_ids)}",
                    }
                ), 400

        overrides: dict[str, Any] = {
            "pinned": pinned,
            "excluded": excluded,
            "added": added,
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
        return jsonify(
            {
                "application_id": application_id,
                "pinned": pinned,
                "excluded": excluded,
                "added": added,
                "pinned_summary_id": pinned_summary_id,
                "bullet_order": bullet_order,
                "pinned_title_ids": pinned_title_ids,
                "use_experience_summaries": use_experience_summaries,
                "chosen_experience_summary_ids": chosen_experience_summary_ids,
                "pinned_skill_ids": skill_pinned_in,
                "excluded_skill_ids": skill_excluded_in,
                "skill_order": skill_order_in,
            }
        )
    finally:
        session.close()


@applications_bp.route("/api/applications/<int:application_id>/recommend", methods=["POST"])
def recommend_application_bullets(application_id: int) -> ResponseReturnValue:
    """Workstream H: pick 3-7 bullets/experience via Haiku and stash them on the context file as `llm_recommendations`.

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
            if app_row is None or not _safe_username(
                candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
            ):
                return jsonify({"error": "Application not found"}), 404

            cp = Path(context_path)
            if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
                    _get_client(),
                    ctx,
                    username=candidate.username,
                    run_id=run_id,
                )
            except anthropic.APIConnectionError as exc:
                logger.error("Recommend: Anthropic connection error: %s", exc)
                return jsonify({"error": "AI service connection failed"}), 503
            except LLMResponseError as exc:
                logger.error("Recommend: malformed LLM response: %s", exc.validation_error)
                return jsonify(
                    {
                        "error": "AI recommendation response was malformed",
                        "detail": str(exc.validation_error),
                    }
                ), 502

            # The recommend prompt explicitly tells the LLM "Use the numeric
            # ids only — do NOT prefix with 'e' or 'b'" (analyzer.py:1967),
            # but Sonnet sometimes echoes the corpus_block format back
            # ('e3' / 'b12'). Strip the prefix defensively before int() so
            # one bad row doesn't 500 the whole recommend run with
            # ValueError: invalid literal for int().
            def _to_int(v: object) -> int | None:
                """Coerce ``v`` to an int id, stripping any ``e``/``b`` prefix the LLM may echo; ``None`` if non-numeric."""
                if v is None:
                    return None
                s = str(v).strip().lstrip("eEbB")
                try:
                    return int(s)
                except (TypeError, ValueError):
                    logger.warning("recommend: dropping unparseable id %r", v)
                    return None

            by_exp: dict[str, dict[str, Any]] = {}
            for rec in result.get("recommendations", []) or []:
                eid_int = _to_int(rec.get("experience_id"))
                if eid_int is None:
                    continue
                bullet_ids_int = [
                    bi
                    for bi in (_to_int(b) for b in (rec.get("bullet_ids") or []))
                    if bi is not None
                ]
                by_exp[str(eid_int)] = {
                    "bullet_ids": bullet_ids_int,
                    "rationale": (rec.get("rationale") or "").strip(),
                }
            ctx["llm_recommendations"] = by_exp
            ctx.pop("jd_text", None)  # transient; don't leak into iteration chain
            cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
            return jsonify(
                {
                    "application_id": application_id,
                    "recommendations": by_exp,
                }
            )
        finally:
            session.close()
    except Exception as exc:
        logger.exception("recommend_application_bullets failed for app=%s", application_id)
        return jsonify(
            {
                "error": "Recommend failed",
                **_error_detail_payload(exc),
            }
        ), 500


@applications_bp.route("/api/applications/<int:application_id>/recommend-summary", methods=["POST"])
def recommend_application_summary(application_id: int) -> ResponseReturnValue:
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
        if app_row is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Load active SummaryItem variants for this candidate.
        rows = (
            session.query(SummaryItem)
            .filter_by(
                candidate_id=candidate.id,
                is_active=1,
            )
            .order_by(SummaryItem.display_order, SummaryItem.id)
            .all()
        )
        items = [
            {
                "id": r.id,
                "text": r.text,
                "label": r.label,
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
                _get_client(),
                ctx,
                username=candidate.username,
                run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-summary: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Recommend-summary: malformed LLM response: %s", exc.validation_error)
            return jsonify(
                {
                    "error": "AI summary recommendation was malformed",
                    "detail": str(exc.validation_error),
                }
            ), 502

        # Persist + strip the transient keys
        ctx["llm_summary_recommendation"] = result
        ctx.pop("summary_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify(
            {
                "application_id": application_id,
                **result,
            }
        )
    finally:
        session.close()


@applications_bp.route(
    "/api/applications/<int:application_id>/recommend-experience-summaries", methods=["POST"]
)
def recommend_application_experience_summaries(application_id: int) -> ResponseReturnValue:
    """B.4: Pick the best per-role intro variant for each role via one batched Haiku call.

    Mirrors recommend_application_summary (analyzer.recommend_experience_summaries), persists to
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
        if app_row is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
        experiences = (
            session.query(Experience)
            .filter_by(
                candidate_id=candidate.id,
            )
            .order_by(Experience.start_date.desc(), Experience.id.desc())
            .all()
        )
        groups: list[dict[str, Any]] = []
        for exp in experiences:
            rows = (
                session.query(ExperienceSummaryItem)
                .filter_by(
                    experience_id=exp.id,
                    is_active=1,
                )
                .order_by(
                    ExperienceSummaryItem.display_order,
                    ExperienceSummaryItem.id,
                )
                .all()
            )
            if not rows:
                continue
            groups.append(
                {
                    "experience_id": exp.id,
                    "company": exp.company,
                    "items": [
                        {
                            "id": r.id,
                            "text": r.text,
                            "label": r.label,
                            "has_outcome": bool(r.has_outcome),
                        }
                        for r in rows
                    ],
                }
            )

        # Stash transient context for the LLM call; strip before persisting.
        ctx["experience_summary_items"] = groups
        ctx["jd_text"] = app_row.jd_text
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = recommend_experience_summaries(
                _get_client(),
                ctx,
                username=candidate.username,
                run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-experience-summaries: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error(
                "Recommend-experience-summaries: malformed LLM response: %s", exc.validation_error
            )
            return jsonify(
                {
                    "error": "AI role-summary recommendation was malformed",
                    "detail": str(exc.validation_error),
                }
            ), 502

        ctx["llm_experience_summary_recommendations"] = result
        ctx.pop("experience_summary_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify(
            {
                "application_id": application_id,
                **result,
            }
        )
    finally:
        session.close()


@applications_bp.route("/api/applications/<int:application_id>/recommend-skills", methods=["POST"])
def recommend_application_skills(application_id: int) -> ResponseReturnValue:
    """B.5: Order and lightly curate the candidate's skills for this JD via Haiku (analyzer.recommend_skills).

    Persists to context["llm_skill_recommendations"]. Fired from the Compose step;
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
        if app_row is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
            return jsonify({"error": "Invalid context_path"}), 400
        try:
            ctx = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return jsonify({"error": "Context file unreadable"}), 400
        if ctx.get("application_id") not in (None, application_id):
            return jsonify({"error": "context_path does not match application"}), 400

        # Stage active, approved skills (+ tag display values) for the matcher.
        rows = (
            session.query(Skill)
            .filter_by(
                candidate_id=candidate.id,
                is_active=1,
                is_pending_review=0,
            )
            .order_by(Skill.display_order, Skill.id)
            .all()
        )
        ctx["skill_items"] = [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "tags": [
                    lnk.tag.display_value
                    for lnk in s.tag_links
                    if lnk.tag and (lnk.tag.display_value or "").strip()
                ],
            }
            for s in rows
        ]
        ctx["jd_text"] = app_row.jd_text
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = recommend_skills(
                _get_client(),
                ctx,
                username=candidate.username,
                run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Recommend-skills: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Recommend-skills: malformed LLM response: %s", exc.validation_error)
            return jsonify(
                {
                    "error": "AI skill recommendation was malformed",
                    "detail": str(exc.validation_error),
                }
            ), 502

        ctx["llm_skill_recommendations"] = result
        ctx.pop("skill_items", None)
        ctx.pop("jd_text", None)
        cp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        return jsonify(
            {
                "application_id": application_id,
                **result,
            }
        )
    finally:
        session.close()


@applications_bp.route("/api/applications/<int:application_id>/suggest-skills", methods=["POST"])
def suggest_application_skills(application_id: int) -> ResponseReturnValue:
    """B.5: Propose NEW canonical skills the JD wants and the candidate's corpus evidences (grounded).

    Each proposal is inserted as a PENDING Skill (source='llm_proposed',
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
        if app_row is None or not _safe_username(
            candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]
        ):
            return jsonify({"error": "Application not found"}), 404

        cp = Path(context_path)
        if not _within(cp, current_app.config["OUTPUT_DIR"]) or not cp.exists():
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
        existing_lower = {
            (s.name or "").strip().lower() for s in all_rows if (s.name or "").strip()
        }
        ctx["existing_skill_names"] = [s.name for s in all_rows if (s.name or "").strip()]
        run_id = ctx.get("run_id") or uuid.uuid4().hex[:12]
        try:
            result = suggest_skills(
                _get_client(),
                ctx,
                username=candidate.username,
                run_id=run_id,
            )
        except anthropic.APIConnectionError as exc:
            logger.error("Suggest-skills: Anthropic connection error: %s", exc)
            return jsonify({"error": "AI service connection failed"}), 503
        except LLMResponseError as exc:
            logger.error("Suggest-skills: malformed LLM response: %s", exc.validation_error)
            return jsonify(
                {
                    "error": "AI skill suggestion was malformed",
                    "detail": str(exc.validation_error),
                }
            ), 502

        # Insert each grounded proposal as a pending skill. Dedup against
        # existing names (any state) AND within this batch; the unique
        # constraint is the final backstop.
        next_order = session.query(Skill).filter_by(candidate_id=candidate.id).count()
        created: list[dict[str, Any]] = []
        for p in result.get("proposals") or []:
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
            created.append(
                {
                    **_skill_to_dict(sk, []),
                    "evidence": p.get("evidence"),
                    "rationale": p.get("rationale"),
                }
            )
            next_order += 1
        session.commit()
        return jsonify(
            {
                "application_id": application_id,
                "proposals": created,
            }
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase D.5: Candidate Memory list route
# ---------------------------------------------------------------------------


@applications_bp.route("/api/users/<username>/clarifications", methods=["GET"])
def list_clarifications(username: str) -> ResponseReturnValue:
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

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    q = (request.args.get("q") or "").strip().lower()
    kind = request.args.get("kind")
    only_outcome_rich = request.args.get("only_outcome_rich") == "1"
    include_promoted = request.args.get("include_promoted") == "1"
    limit = min(int(request.args.get("limit", 200)), 1000)
    valid_kinds = {
        "experience_probe",
        "scope_probe",
        "iteration_probe",
        "outcome_probe",
        "manual",
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
            for app_row in (
                session.query(Application)
                .filter(
                    Application.id.in_(app_ids),
                )
                .all()
            ):
                app_title_by_id[app_row.id] = app_row.title

        out = []
        for r in rows:
            if q and (q not in r.question.lower() and q not in r.answer.lower()):
                continue
            outcome_rich = bool(METRIC_RE.search(r.answer))
            if only_outcome_rich and not outcome_rich:
                continue
            out.append(
                {
                    "id": r.id,
                    "question": r.question,
                    "answer": r.answer,
                    "kind": r.kind,
                    "target_gap": r.target_gap,
                    "is_promoted_to_bullet": bool(r.is_promoted_to_bullet),
                    "outcome_rich": outcome_rich,
                    "origin_application_id": r.origin_application_id,
                    "origin_application_title": app_title_by_id.get(r.origin_application_id)
                    if r.origin_application_id
                    else None,
                    "origin_run_id": r.origin_run_id,
                    "created_at": r.created_at,
                }
            )
        return jsonify(out)
    finally:
        session.close()

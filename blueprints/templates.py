"""Templates / personas seam — persona-template CRUD + live HTML previews.

The fourth domain blueprint extracted from `app.py` (Sprint 8.3e, the app.py ->
blueprints decomposition). Owns the twelve routes that manage persona templates
(bundled + user-uploaded) and render the live WYSIWYG previews, plus their
domain-only helpers:

    GET    /api/personas/bundled                              list_bundled_personas
    GET    /api/users/<u>/personas                            list_user_personas
    POST   /api/users/<u>/personas                            upload_user_persona
    GET    /api/personas/<id>                                 get_persona
    PUT    /api/personas/<id>                                 update_persona
    DELETE /api/personas/<id>                                 delete_persona
    GET    /api/personas/<id>/download                        download_persona
    POST   /api/personas/<id>/copy                             copy_persona_to_candidate
    POST   /api/personas/<id>/preview                         preview_persona_with_resume
    GET    /api/applications/<id>/preview                     preview_application_html
    GET    /api/applications/<id>/cover-letter-preview        preview_cover_letter_html
    POST   /api/applications/<id>/preview-edited               preview_edited_html
    GET    /api/users/<u>/preview                             preview_candidate_html

Reads paths from `current_app.config[...]` at request time (never a module-global
import) and shares the security/HTTP helpers from `web_infra` — so a test isolates
the routes with `create_app(Config(base_dir=tmp_path))`, no monkeypatching of
module globals. The blueprint never imports `app.py` (leaf-ward direction only);
DB-layer imports stay lazy inside each function, as in the monolith. None of these
routes call an LLM — the render path is deterministic (`pdf_render` / `generator` /
`corpus_to_json_resume`), so this module is NOT on the egress allowlist.

Canonical home for the persona-template resolvers: `_resolve_persona_template_path`
/ `_resolve_default_persona_template_path` live here (Sprint 8.3e). The generation
seam carried a transitional duplicate from 8.3c; it now imports the pair from this
module (sibling blueprint -> blueprint is allowed). See the Carry-forward ledger.

`copy_persona_to_candidate` (Wave 2 recruiter tier — UX review F-16, 2026-07-07)
is the smallest honest fix for "house templates are per-candidate": personas stay
per-candidate (no account-level scope, no schema change), but a one-click copy
lets a recruiter plant an already-uploaded house template on another candidate
instead of re-uploading the .docx by hand every time. It touches the filesystem
(copies the .docx under a new candidate's persona dir) so it carries the full
`_safe_username` + `secure_filename` + `_within` guard sequence, same as
`upload_user_persona`.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, current_app, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from blueprints.applications import _load_application_owned
from generator import generate_resume
from web_infra import (
    _error_detail_payload,
    _get_or_provision_candidate,
    _safe_username,
    _within,
)

if TYPE_CHECKING:
    from db.models import Candidate, PersonaTemplate

logger = logging.getLogger(__name__)

templates_bp = Blueprint("templates", __name__)


# --- Persona serializers (moved with the seam) ---


def _persona_dict(template: PersonaTemplate) -> dict[str, Any]:
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


def _persona_dicts_safe(templates: list[PersonaTemplate]) -> list[dict[str, Any]]:
    """Serialize a list of persona_template rows, skipping (and logging) any row that fails serialization.

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
    out: list[dict[str, Any]] = []
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
                row_id,
                type(exc).__name__,
                exc,
            )
    return out


# --- Persona-template path resolvers (CANONICAL home, Sprint 8.3e) ---
# Reads BASE_DIR / PERSONAS_DIR from current_app.config (request-context only —
# all callers run inside a request). The generation seam (8.3c) carried a
# transitional duplicate of this pair; it now imports them from here.


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
        disk_path = (current_app.config["BASE_DIR"] / row.path).resolve()
        if not disk_path.exists() or not _within(disk_path, current_app.config["PERSONAS_DIR"]):
            logger.warning(
                "Persona template id=%s has invalid path %s",
                persona_template_id,
                row.path,
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
                    row = (
                        session.query(PersonaTemplate)
                        .filter_by(
                            candidate_id=candidate.id,
                            primary_role_tag_id=role_tag_id,
                            is_default=1,
                        )
                        .first()
                    )
                    if row is not None:
                        return _resolve_persona_template_path(row.id)

                # Priority 2: general default (no role tag)
                row = (
                    session.query(PersonaTemplate)
                    .filter_by(
                        candidate_id=candidate.id,
                        primary_role_tag_id=None,
                        is_default=1,
                    )
                    .first()
                )
                if row is not None:
                    return _resolve_persona_template_path(row.id)

        # Priority 3: bundled Classic (existing fallback)
        row = (
            session.query(PersonaTemplate)
            .filter_by(
                source="bundled",
                name="Classic Single-Column",
            )
            .first()
        )
        if row is None:
            return None
        return _resolve_persona_template_path(row.id)
    finally:
        session.close()


# --- Preview-render domain helpers (moved with the seam) ---


def _latest_generated_resume_md(candidate_id: int) -> str | None:
    """Return the most recent non-empty generated_resume_md across a candidate's application runs. None when the user hasn't generated yet."""
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


def _json_resume_has_content(doc: dict[str, Any]) -> bool:
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


def _preview_placeholder_html(html_path: Path) -> str:
    """Return self-contained HTML for the Step 6 iframe when this application has no LLM recommendations yet.

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


def _cover_letter_placeholder_html() -> str:
    """Return self-contained HTML for the Step 6 cover-letter iframe when no cover letter has been generated yet.

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


def _inline_persona_css(html_str: str, html_path: Path) -> str:
    """Replace `<link rel="stylesheet" href="*.css">` with an inline `<style>` block so the response is fully self-contained.

    Best-effort: missing CSS file is logged and left as-is.
    """
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
        html_str,
        count=1,
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
  // below does NOT cover. paged.js can throw from an internal layout sartor
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
    """Append paged.js + a small init script before `</body>` so the preview iframe renders discrete Letter-sized pages.

    Paged.js is bundled as `/static/vendor/paged.polyfill.js` (MIT,
    v0.4.3). The script auto-polyfills CSS @page rules. The init
    sartor postMessages the rendered page count to the parent
    frame so the wizard toolbar can show "Page N of M" accurately.

    The PDF render path does NOT go through this helper —
    `pdf_render.render_pdf()` uses Playwright's `page.pdf()` which
    handles @page CSS natively. Paged.js is browser-preview only.
    """
    if "</body>" not in html_str:
        return html_str + _PAGED_PREVIEW_INJECTION
    return html_str.replace("</body>", _PAGED_PREVIEW_INJECTION + "</body>", 1)


# ---------------------------------------------------------------------------
# Persona template routes (bundled + user-uploaded)
# ---------------------------------------------------------------------------


@templates_bp.route("/api/personas/bundled", methods=["GET"])
def list_bundled_personas() -> ResponseReturnValue:
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
        return jsonify(
            {
                "error": "Failed to load bundled personas",
                **_error_detail_payload(exc),
            }
        ), 500


@templates_bp.route("/api/users/<username>/personas", methods=["GET"])
def list_user_personas(username: str) -> ResponseReturnValue:
    """Return bundled + this candidate's uploaded persona templates."""
    from db.models import Candidate, PersonaTemplate
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
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
                return jsonify(
                    {
                        "bundled": [],
                        "owned": [],
                        "needs_onboarding": True,
                    }
                )
            bundled = session.query(PersonaTemplate).filter_by(source="bundled").all()
            owned = session.query(PersonaTemplate).filter_by(candidate_id=candidate.id).all()
            return jsonify(
                {
                    "bundled": _persona_dicts_safe(bundled),
                    "owned": _persona_dicts_safe(owned),
                }
            )
        finally:
            session.close()
    except Exception as exc:
        logger.exception("list_user_personas failed for user=%s", safe_user)
        return jsonify(
            {
                "error": "Failed to load personas",
                **_error_detail_payload(exc),
            }
        ), 500


@templates_bp.route("/api/users/<username>/personas", methods=["POST"])
def upload_user_persona(username: str) -> ResponseReturnValue:
    """Upload a user-owned .docx persona template.

    Multipart body: `file` (the .docx), `name` (display label, optional —
    defaults to the filename stem). The .docx is saved under
    `personas/{user}/` and a persona_template row is created with
    candidate_id=<this user> and source='user_upload'.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Multipart 'file' field is required"}), 400
    if Path(file.filename).suffix.lower() != ".docx":
        return jsonify({"error": "Only .docx persona templates are supported"}), 400

    personas_dir = current_app.config["PERSONAS_DIR"]
    init_db()
    session = get_session()
    try:
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(
                session,
                safe_user,
                configs_dir=current_app.config["CONFIGS_DIR"],
            ),
        )

        safe_name = secure_filename(file.filename)
        user_persona_dir = personas_dir / safe_user
        user_persona_dir.mkdir(parents=True, exist_ok=True)
        target = user_persona_dir / safe_name
        if not _within(target, personas_dir):
            return jsonify({"error": "Invalid persona path"}), 403
        file.save(str(target))

        # Generate the HTML+CSS preview companion so the live preview renders the
        # uploaded template's OWN typography instead of silently falling back to
        # Classic (walkthrough B2/B3). Best-effort — a failure still 201s (the
        # preview route falls back to Classic exactly as before), but the caller
        # gets a `companion_warning` in the response so the UI can surface it
        # instead of the persona previewing as Classic forever with no signal
        # (walkthrough residuals item 3). generate_companion() already logs the
        # underlying exception; None just means it happened.
        from docx_to_persona_html import generate_companion

        companion_warning: str | None = None
        if generate_companion(target) is None:
            companion_warning = "Preview will use the default style; download unaffected."
            logger.warning(
                "Persona companion generation failed for upload %s (user=%s)",
                target,
                safe_user,
            )

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
        response_body = _persona_dict(row)
        if companion_warning:
            response_body["companion_warning"] = companion_warning
        return jsonify(response_body), 201
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@templates_bp.route("/api/personas/<int:persona_id>", methods=["GET"])
def get_persona(persona_id: int) -> ResponseReturnValue:
    """Return one persona row's metadata (bundled + owned both readable for preview UI)."""
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


@templates_bp.route("/api/personas/<int:persona_id>", methods=["PUT"])
def update_persona(persona_id: int) -> ResponseReturnValue:
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


@templates_bp.route("/api/personas/<int:persona_id>", methods=["DELETE"])
def delete_persona(persona_id: int) -> ResponseReturnValue:
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

        disk_path = current_app.config["BASE_DIR"] / row.path
        if disk_path.exists() and _within(disk_path, current_app.config["PERSONAS_DIR"]):
            disk_path.unlink()

        session.delete(row)
        session.commit()
        return jsonify({"deleted": persona_id})
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@templates_bp.route("/api/personas/<int:persona_id>/download", methods=["GET"])
def download_persona(persona_id: int) -> ResponseReturnValue:
    """Stream a persona's .docx file for the preview UI."""
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        disk_path = current_app.config["BASE_DIR"] / row.path
        if not disk_path.exists():
            return jsonify({"error": "Persona file missing on disk"}), 404
        # Containment: bundled lives under personas/bundled/, user uploads
        # under personas/{user}/ — both inside PERSONAS_DIR.
        if not _within(disk_path, current_app.config["PERSONAS_DIR"]):
            return jsonify({"error": "Invalid persona path"}), 403
        return send_file(str(disk_path), as_attachment=True, download_name=f"{row.name}.docx")
    finally:
        session.close()


@templates_bp.route("/api/personas/<int:persona_id>/copy", methods=["POST"])
def copy_persona_to_candidate(persona_id: int) -> ResponseReturnValue:
    """Copy a user-uploaded persona template to another candidate (F-16 house templates).

    Body: `{username: <target candidate>}`. Personas stay per-candidate — this
    is a one-click copy, not an account-level sharing scope, so it needs no
    schema change and every existing persona route contract is untouched. Only
    `user_upload` rows are eligible sources (`bundled` templates are already
    visible to every candidate — nothing to copy). Copies the .docx into
    `personas/<target>/`, regenerates its HTML/CSS preview companion (same
    best-effort step `upload_user_persona` runs), and inserts a new
    `persona_template` row owned by the target candidate — the original is
    untouched, so the two copies can now diverge (rename/delete) independently.

    Filesystem + containment: `_safe_username` validates the target username;
    the source path is re-validated `_within` PERSONAS_DIR before it's read
    (defense-in-depth against a corrupted `path` column); the copy target is
    built from `secure_filename` and re-validated `_within` PERSONAS_DIR before
    it's written, with a numeric-suffix fallback if a same-named file already
    exists for that candidate.
    """
    import shutil

    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    data = request.json or {}
    configs_dir = current_app.config["CONFIGS_DIR"]
    safe_user = _safe_username(data.get("username", ""), configs_dir=configs_dir)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown target user"}), 400

    personas_dir = current_app.config["PERSONAS_DIR"]
    init_db()
    session = get_session()
    try:
        source = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if source is None:
            return jsonify({"error": "Persona not found"}), 404
        if source.source != "user_upload":
            return jsonify({"error": "Only uploaded templates can be copied"}), 400

        target_candidate = cast(
            "Candidate",
            _get_or_provision_candidate(session, safe_user, configs_dir=configs_dir),
        )
        if source.candidate_id == target_candidate.id:
            return jsonify({"error": f"Already belongs to {safe_user}"}), 400

        src_path = (current_app.config["BASE_DIR"] / source.path).resolve()
        if not src_path.exists() or not _within(src_path, personas_dir):
            return jsonify({"error": "Source persona file missing or invalid"}), 403

        safe_name = secure_filename(src_path.name)
        target_dir = personas_dir / safe_user
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
        # Avoid clobbering an existing file of the same name for this candidate
        # (e.g. copying the same house template to them twice).
        stem, suffix = Path(safe_name).stem, Path(safe_name).suffix
        n = 2
        while target_path.exists():
            target_path = target_dir / f"{stem}-{n}{suffix}"
            n += 1
        if not _within(target_path, personas_dir):
            return jsonify({"error": "Invalid target persona path"}), 403
        shutil.copyfile(src_path, target_path)

        # Best-effort HTML/CSS preview companion, same as upload_user_persona.
        from docx_to_persona_html import generate_companion

        generate_companion(target_path)

        row = PersonaTemplate(
            candidate_id=target_candidate.id,
            name=source.name,
            path=f"personas/{safe_user}/{target_path.name}",
            source="user_upload",
            description=source.description,
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


@templates_bp.route("/api/personas/<int:persona_id>/preview", methods=["POST"])
def preview_persona_with_resume(persona_id: int) -> ResponseReturnValue:
    """Render the user's latest generated resume through this persona template and stream the real .docx (Workstream C #6).

    Body: {username}. Touches the filesystem (writes + streams a .docx),
    so both _safe_username and _within guards apply.
    """
    from db.models import PersonaTemplate
    from db.session import get_session, init_db

    data = request.json or {}
    username = data.get("username", "")
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    output_dir = current_app.config["OUTPUT_DIR"]
    init_db()
    session = get_session()
    try:
        row = session.query(PersonaTemplate).filter_by(id=persona_id).first()
        if row is None:
            return jsonify({"error": "Persona not found"}), 404
        disk_path = (current_app.config["BASE_DIR"] / row.path).resolve()
        if not disk_path.exists() or not _within(disk_path, current_app.config["PERSONAS_DIR"]):
            return jsonify({"error": "Invalid persona path"}), 403
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(
                session,
                safe_user,
                configs_dir=current_app.config["CONFIGS_DIR"],
            ),
        )
        resume_md = _latest_generated_resume_md(candidate.id)
        if not resume_md:
            return jsonify(
                {
                    "error": "No generated resume yet — run GENERATE in an "
                    "application first, then preview a template against it.",
                }
            ), 409
    finally:
        session.close()

    out_path = generate_resume(
        resume_md,
        ".docx",
        safe_user,
        str(output_dir),
        template_path=str(disk_path),
    )
    return send_file(
        str(out_path),
        as_attachment=True,
        download_name=f"preview_{row.name}.docx",
    )


@templates_bp.route("/api/applications/<int:application_id>/preview", methods=["GET"])
def preview_application_html(application_id: int) -> ResponseReturnValue:
    """Render the candidate's résumé corpus + application-scoped overrides as a self-contained HTML page (corpus-direct live preview).

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

    output_dir = current_app.config["OUTPUT_DIR"]
    init_db()
    session = get_session()
    try:
        # _load_application_owned runs _safe_username on the owning
        # candidate; the explicit recheck just below keeps the
        # route-security-lint hook happy when scanning this block.
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or candidate is None:
            return jsonify({"error": "Application not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
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
                username=candidate.username,
                application_id=application_id,
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
            # Lazily generate the HTML+CSS companion for a persona uploaded before
            # companion generation shipped, so its preview reflects the uploaded
            # template's typography instead of falling back to Classic (B2/B3).
            from docx_to_persona_html import generate_companion

            companion = generate_companion(docx_template_path)
            html_path = companion[0] if companion else None
        if html_path is None:
            html_path = current_app.config["BUNDLED_PERSONAS_DIR"] / "classic.html"
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
        cached_json_resume: dict[str, Any] | None = None
        ctx_has_recommendations = False
        if ctx_path_raw:
            cp = Path(ctx_path_raw)
            if _within(cp, output_dir) and cp.exists():
                ctx_path_arg = str(cp)
                try:
                    ctx_data = json.loads(cp.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    ctx_data = {}
                cached = ctx_data.get("last_generated_json_resume")
                # Phase 4 — the frozen approved_composition is the single content
                # contract: serve it verbatim so preview == deterministic assemble ==
                # download (template-invariant). It wins UNLESS the user has made a
                # hand-edit (edited_resume_text) — then last_generated_json_resume,
                # recomputed from that edit by /api/save-edits, reflects the edit
                # (D6(a): the user's own edits apply directly, WYSIWYG).
                approved = ctx_data.get("approved_composition")
                edited = bool(ctx_data.get("edited_resume_text"))
                if not edited and isinstance(approved, dict) and _json_resume_has_content(approved):
                    cached_json_resume = approved
                elif isinstance(cached, dict) and _json_resume_has_content(cached):
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
                return (
                    _preview_placeholder_html(html_path),
                    200,
                    {
                        "Content-Type": "text/html; charset=utf-8",
                    },
                )
            # Build the JSON Resume directly from the candidate's corpus,
            # applying composition_overrides + chosen-summary resolution
            # scoped to THIS application.
            json_doc = build_json_resume_from_corpus(
                session,
                candidate.id,
                application_id=application_id,
                context_path=ctx_path_arg,
            )
    finally:
        session.close()

    html_str = render_html_string(json_doc, html_template_path=html_path)
    html_str = _inline_persona_css(html_str, html_path)
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}


@templates_bp.route("/api/applications/<int:application_id>/cover-letter-preview", methods=["GET"])
def preview_cover_letter_html(application_id: int) -> ResponseReturnValue:
    """Render the application's generated cover letter as a styled, self-contained business-letter HTML page (v1.0.5 — Step 6 redesign).

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

    output_dir = current_app.config["OUTPUT_DIR"]
    init_db()
    session = get_session()
    try:
        # _load_application_owned runs _safe_username on the owning candidate;
        # the explicit recheck just below keeps the route-security-lint hook
        # happy when scanning this block.
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or candidate is None:
            return jsonify({"error": "Application not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
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
                username=candidate.username,
                application_id=application_id,
            )
        css_path = Path(docx_template_path).with_suffix(".css") if docx_template_path else None
        font_family = persona_font_family(css_path)

        # Read the generated cover letter from the supplied context file,
        # validating containment under OUTPUT_DIR so a malicious caller can't
        # read outside.
        ctx_path_raw = request.args.get("context_path", "").strip()
        cover_letter_md = ""
        if ctx_path_raw:
            cp = Path(ctx_path_raw)
            if _within(cp, output_dir) and cp.exists():
                try:
                    ctx_data = json.loads(cp.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    ctx_data = {}
                # D4 (generation-experience re-architecture, item (b)): the user's
                # own hand-edit wins, mirroring the résumé preview's
                # edited_resume_text precedence above (D6(a) — a hand-edit applies
                # directly, no re-approval). Without this the styled cover-letter
                # iframe never reflected a saved edit at all — /api/save-edits
                # persisted edited_cover_letter_text but this route ignored it and
                # always re-rendered the un-edited AI text, so preview != download
                # forever after the first edit.
                cover_letter_md = (ctx_data.get("edited_cover_letter_text") or "").strip() or (
                    ctx_data.get("last_generated_cover_letter") or ""
                ).strip()
    finally:
        session.close()

    if not cover_letter_md:
        return (
            _cover_letter_placeholder_html(),
            200,
            {
                "Content-Type": "text/html; charset=utf-8",
            },
        )

    cover_template = current_app.config["PERSONAS_DIR"] / "cover_letter.html"
    html_str = render_cover_letter_html(
        cover_letter_md,
        font_family=font_family,
        template_path=cover_template,
    )
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}


@templates_bp.route("/api/applications/<int:application_id>/preview-edited", methods=["POST"])
def preview_edited_html(application_id: int) -> ResponseReturnValue:
    """Render POSTed in-app-edited text as styled preview HTML — nothing persisted.

    D4 (generation-experience re-architecture, item (b) — "in-app edits ARE the
    document"): the styled Step-6 iframes (`preview_application_html` /
    `preview_cover_letter_html`) only ever reflected an edit AFTER it was
    explicitly saved (`/api/save-edits`, gated behind the "Use edits as
    baseline" modal before a refine/iterate action). Between typing an edit and
    that unrelated action, the visible preview stayed on the pre-edit content
    while `/api/download-edited` — which reads `#resumePreview` /
    `#coverLetterPreview` directly — would already produce the NEW content:
    preview != download. This route closes that gap the same way
    `/api/download-edited` already does for the file itself: content in,
    rendered artifact out, NOTHING written to context or the DB. The frontend
    calls it on a debounced `input` from either editor and swaps the iframe's
    `srcdoc`; the existing explicit-save gate (edit-detection modal) is
    unchanged — this route never touches `edited_resume_text`.

    Body: {content, type: "resume"|"cover_letter", template_id (optional)}.
    Returns {html}.
    """
    from db.session import get_session, init_db
    from docx_to_persona_html import generate_companion
    from generator import _normalize_markdown
    from json_resume import md_to_json_resume
    from pdf_render import (
        html_template_path_for,
        persona_font_family,
        render_cover_letter_html,
        render_html_string,
    )

    personas_dir = current_app.config["PERSONAS_DIR"]
    bundled_personas_dir = current_app.config["BUNDLED_PERSONAS_DIR"]
    data = request.json or {}
    content = (data.get("content") or "").strip()
    doc_type = data.get("type", "resume")
    if not content:
        return jsonify({"error": "content required"}), 400
    if doc_type not in ("resume", "cover_letter"):
        return jsonify({"error": "type must be 'resume' or 'cover_letter'"}), 400

    init_db()
    session = get_session()
    try:
        # _load_application_owned runs _safe_username on the owning candidate;
        # the explicit recheck just below keeps the route-security-lint hook
        # happy when scanning this block (same pattern as preview_application_html
        # / preview_cover_letter_html above).
        app_row, candidate = _load_application_owned(session, application_id)
        if app_row is None or candidate is None:
            return jsonify({"error": "Application not found"}), 404
        if not _safe_username(candidate.username, configs_dir=current_app.config["CONFIGS_DIR"]):
            return jsonify({"error": "Application not found"}), 404

        template_id_raw = data.get("template_id")
        docx_template_path: str | None = None
        if template_id_raw is not None:
            try:
                template_id = int(template_id_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "template_id must be an integer"}), 400
            docx_template_path = _resolve_persona_template_path(template_id)
            if docx_template_path is None:
                return jsonify({"error": "Template not found"}), 404
        else:
            docx_template_path = _resolve_default_persona_template_path(
                username=candidate.username,
                application_id=application_id,
            )
        if docx_template_path is None:
            return jsonify({"error": "No template available"}), 500
        # Defense in depth: docx_template_path came from a trusted resolver
        # (both branches above already contain it to PERSONAS_DIR internally),
        # but re-assert containment explicitly here — same belt-and-suspenders
        # pattern as the _safe_username recheck just above, and what the
        # route-security-lint hook expects to see in a filesystem-touching route.
        if not _within(Path(docx_template_path), personas_dir):
            return jsonify({"error": "Template not found"}), 404

        if doc_type == "resume":
            html_path = html_template_path_for(docx_template_path)
            if html_path is None:
                # Same lazy-companion-generation fallback as preview_application_html.
                companion = generate_companion(docx_template_path)
                html_path = companion[0] if companion else None
            if html_path is None:
                html_path = bundled_personas_dir / "classic.html"
                if not html_path.exists():
                    return jsonify({"error": "No HTML template available"}), 500
            json_doc = md_to_json_resume(_normalize_markdown(content))
            html_str = render_html_string(json_doc, html_template_path=html_path)
            html_str = _inline_persona_css(html_str, html_path)
        else:
            css_path = Path(docx_template_path).with_suffix(".css")
            font_family = persona_font_family(css_path)
            cover_template = personas_dir / "cover_letter.html"
            html_str = render_cover_letter_html(
                content,
                font_family=font_family,
                template_path=cover_template,
            )
    finally:
        session.close()

    html_str = _inject_paged_polyfill(html_str)
    return jsonify({"html": html_str})


@templates_bp.route("/api/users/<string:username>/preview", methods=["GET"])
def preview_candidate_html(username: str) -> ResponseReturnValue:
    """Render the candidate's résumé corpus as a self-contained HTML page without an application in scope (pre-application preview).

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

    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    init_db()
    session = get_session()
    try:
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
        if candidate is None:
            return jsonify(
                {
                    "error": "Candidate not in corpus yet",
                    "needs_onboarding": True,
                }
            ), 409

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
                username=candidate.username,
                application_id=None,
            )

        if docx_template_path is None:
            return jsonify({"error": "No template available"}), 500

        html_path = html_template_path_for(docx_template_path)
        if html_path is None:
            # Lazily generate the HTML+CSS companion for a persona uploaded before
            # companion generation shipped, so its preview reflects the uploaded
            # template's typography instead of falling back to Classic (B2/B3).
            # Same fallback as preview_application_html / preview_edited_html.
            from docx_to_persona_html import generate_companion

            companion = generate_companion(docx_template_path)
            html_path = companion[0] if companion else None
        if html_path is None:
            html_path = current_app.config["BUNDLED_PERSONAS_DIR"] / "classic.html"
            if not html_path.exists():
                return jsonify({"error": "No HTML template available"}), 500

        json_doc = build_json_resume_from_corpus(
            session,
            candidate.id,
            application_id=None,
        )
    finally:
        session.close()

    html_str = render_html_string(json_doc, html_template_path=html_path)
    html_str = _inline_persona_css(html_str, html_path)
    html_str = _inject_paged_polyfill(html_str)
    return html_str, 200, {"Content-Type": "text/html; charset=utf-8"}

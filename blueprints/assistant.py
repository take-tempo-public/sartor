"""The doc-grounded assistant — the project-wiring + SSE route layer (Sprint 7.5).

This is the **Operation surface** of callback's Memory function: a Flask SSE chat route
that turns a question into a cited answer. It is the thin glue between three layers,
owning none of their logic:

  * the deterministic `recall/` substrate (retrieval + RRF fusion + scope filter +
    token-budget pack — `recall.assemble`), and
  * the single Haiku LLM call (`analyzer.avatar_answer_streaming` — charter C-6 keeps
    every model call in `analyzer.py`).

What lives *here* is the **callback-specific wiring** the substrate is too generic to
hold: the source roots (`docs/wiki`, the repo HEAD), the SCHEMA `**Audience:**` /
path→audience rules that classify each `Unit` (`docs/wiki/SCHEMA.md` blanket rules), and
the request/SSE plumbing. The generic source tiers are injected from `recall.sources`
with these bindings.

Like `dashboard/routes.py`, this module **does not import `app.py`** — it re-derives its
paths and inlines the few shared helpers (`_safe_username` / `_get_client` / `_sse`,
duplicated from `app.py` pending the Sprint 8.1 shared-helpers home). That keeps the
blueprint independently importable, so the v1.0.8 split is a move, not a rewrite.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from pathlib import Path

import anthropic
from flask import Blueprint, Response, jsonify, request
from werkzeug.utils import secure_filename

import analyzer
from recall import Audience, GitGrepSource, Scope, SessionSource, Tier, WikiSource, assemble

logger = logging.getLogger(__name__)

assistant_bp = Blueprint("assistant", __name__)

# Re-derived locally (the dashboard-blueprint precedent) — never imported from app.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
_WIKI_DIR = PROJECT_ROOT / "docs" / "wiki"
_INGEST_SHA_PATH = _WIKI_DIR / ".last_ingest_sha"

# Retrieval feed size for one avatar turn (the recall token-budget pack ~4 chars/token).
_TOKEN_BUDGET = 4000


# --- callback-specific audience bindings (the wiring the substrate can't hold) ------
#
# These encode the wiki SCHEMA's audience boundary (docs/wiki/SCHEMA.md "Audience tag")
# and are injected into the generic recall.sources tiers. They live HERE, not in
# recall/ — keeping them out of the substrate is exactly what the recall/sources/
# no-hardcoded-roots guard enforces.

_AUDIENCE_TAG_RE = re.compile(r"\*\*Audience:\*\*\s*`(user|dev)`", re.IGNORECASE)
_USER_DOC_NAMES = frozenset({"README.md", "vision.md"})
_DEV_PATH_PREFIXES = (
    "docs/dev/", "evals/", "dashboard/", "static/", "templates/", "tests/", "scripts/",
)


def _wiki_audience(stem: str, raw_text: str) -> Audience:
    """A wiki page's audience = its own `**Audience:**` tag (the canonical, drift-proof
    parse target per SCHEMA), defaulting to `dev` when a page carries no tag (safe — it
    never over-discloses to a user-scoped turn)."""
    match = _AUDIENCE_TAG_RE.search(raw_text[:1000])
    if match:
        return Audience.USER if match.group(1).lower() == "user" else Audience.DEV
    return Audience.DEV


def _path_audience(path: str) -> Audience:
    """A code/doc path's audience = the SCHEMA blanket path→audience rules
    (docs/wiki/SCHEMA.md): code + dev docs → `dev`; a few named user docs → `user`;
    everything else → `dev` (safe default)."""
    p = path.replace("\\", "/")
    if p.endswith(".py") or any(p.startswith(prefix) for prefix in _DEV_PATH_PREFIXES):
        return Audience.DEV
    if p in _USER_DOC_NAMES or p.startswith(("docs/install", "docs/walkthrough")):
        return Audience.USER
    return Audience.DEV


def _build_sources(session_turns: list) -> list:
    """Construct the three Stage-1 tiers bound to callback's roots + audience rules.

    Built per request (cheap: ~30 small wiki files + one `git rev-parse`) so live wiki
    edits are picked up without a restart. The session buffer is wired but typically
    empty in Stage 1 (S5-P1); it ingests `session_turns` when the client sends them.
    """
    wiki = WikiSource(_WIKI_DIR, _INGEST_SHA_PATH, _wiki_audience)
    git = GitGrepSource(PROJECT_ROOT, _path_audience)
    git.refresh(None)
    session = SessionSource()
    for turn in session_turns or []:
        if isinstance(turn, str):
            session.observe(turn)
        elif isinstance(turn, dict):
            session.observe(str(turn.get("text", "")), turn.get("citation"))
    return [wiki, git, session]


# --- shared helpers, duplicated from app.py (pending the Sprint 8.1 shared-helpers home) --


def _safe_username(username: str) -> str | None:
    """app.py:_safe_username — sanitize + confirm the user exists (None if invalid)."""
    safe = secure_filename(username)
    if not safe or not (CONFIGS_DIR / f"{safe}.config").exists():
        return None
    return safe


def _get_client() -> anthropic.Anthropic:
    """app.py:_get_client — Anthropic client from env or the local `.api_key` file."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        key_file = PROJECT_ROOT / ".api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    return anthropic.Anthropic(api_key=api_key)


def _sse(event: str, payload: dict) -> str:
    """app.py:_sse — one Server-Sent Event frame (trailing blank line required)."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@assistant_bp.route("/ask", methods=["POST"])
def ask():
    """Answer one question over the committed wiki + code at HEAD, streamed + cited.

    Security: `username` is sanitized via `_safe_username` (the only user-supplied value
    that reaches the filesystem — to confirm the user exists). `_within`/`secure_filename`
    path-containment is N/A here: no user-supplied string is ever resolved into a
    filesystem path — the wiki root globs `pages/*.md`, and the query reaches `git grep`
    as a `-e` operand, never a path. (The route-security-lint hook is app.py-scoped and
    does not fire on this blueprint; the gate is applied here by discipline.)
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    question = (data.get("question") or "").strip()
    allow_dev = bool(data.get("allow_dev", False))
    session_turns = data.get("session_turns") or []

    if not username or not question:
        return jsonify({"error": "username and question required"}), 400
    safe_user = _safe_username(username)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    scope = Scope(
        allow_dev=allow_dev,
        enabled_tiers=frozenset({Tier.WIKI, Tier.GIT, Tier.SESSION}),
        token_budget=_TOKEN_BUDGET,
    )
    # Deterministic retrieval runs fully before streaming begins (retrieve, then phrase).
    context = assemble(question, scope, _build_sources(session_turns))
    client = _get_client()
    run_id = uuid.uuid4().hex[:12]

    def stream():
        try:
            for kind, payload in analyzer.avatar_answer_streaming(
                client, question, context,
                allow_dev=allow_dev, username=safe_user, run_id=run_id,
            ):
                if kind == "chunk":
                    yield _sse("chunk", {"text": payload})
                elif kind == "done" and isinstance(payload, dict):
                    yield _sse("done", payload)
        except anthropic.APIConnectionError as exc:
            logger.warning("avatar LLM connection failed: %s", exc)
            yield _sse("error", {"error": f"Assistant connection failed: {exc}", "http_status": 502})
        except Exception as exc:  # noqa: BLE001 - terminal SSE error frame, never a 500 page
            logger.exception("avatar stream failed")
            yield _sse("error", {"error": str(exc), "http_status": 500})

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

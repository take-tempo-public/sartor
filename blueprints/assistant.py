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
from collections.abc import Sequence
from pathlib import Path

import anthropic
from flask import Blueprint, Response, jsonify, request
from werkzeug.utils import secure_filename

import analyzer
from recall import (
    Audience,
    GitGrepSource,
    Scope,
    SessionSource,
    Tier,
    VectorSource,
    WikiSource,
    assemble,
)
from recall.sources.vector_source import Embedder

logger = logging.getLogger(__name__)

assistant_bp = Blueprint("assistant", __name__)

# Re-derived locally (the dashboard-blueprint precedent) — never imported from app.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
_WIKI_DIR = PROJECT_ROOT / "docs" / "wiki"
_INGEST_SHA_PATH = _WIKI_DIR / ".last_ingest_sha"

# Retrieval feed size for one avatar turn (the recall token-budget pack ~4 chars/token).
_TOKEN_BUDGET = 4000

# S3 vector tier (Sprint 7.6). The static-embedding model + its rebuildable index live
# in a gitignored local sidecar built once by `scripts/build_vector_index.py`; runtime
# retrieval is fully local (no network). The tier activates automatically when BOTH the
# model and the index are present (owner: "on when available", no user-facing toggle) —
# otherwise the assistant runs on the wiki/git/session tiers alone.
_VECTOR_INDEX_DIR = PROJECT_ROOT / "db" / "vector_index"
_VECTOR_MODEL_DIR = _VECTOR_INDEX_DIR / "model"

# The embedder loads the ~30MB model once per process; cache the attempt (the success OR
# the None "not available" result) so we never re-probe the filesystem/import per request.
_EMBEDDER: Embedder | None = None
_EMBEDDER_LOADED = False


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


def _make_embedder() -> Embedder | None:
    """Load the model2vec static model from the local sidecar dir and return an
    L2-normalizing batch embedder, or None when the model isn't downloaded yet (→ the
    S3 tier stays inactive). model2vec is imported lazily HERE — the heavy, HuggingFace-
    coupled embedder is confined to this wiring layer + the build script so `recall/`
    stays embedder-agnostic and extractable. Cached per process: the model load is the
    cost; the per-query encode is a cheap static lookup.
    """
    global _EMBEDDER, _EMBEDDER_LOADED
    if _EMBEDDER_LOADED:
        return _EMBEDDER
    _EMBEDDER_LOADED = True
    if not _VECTOR_MODEL_DIR.exists():
        return None
    try:
        import numpy as np
        from model2vec import StaticModel
    except ImportError as exc:  # pragma: no cover - both are hard deps; defensive only
        logger.warning("model2vec/numpy unavailable; S3 vector tier disabled: %s", exc)
        return None
    try:
        model = StaticModel.from_pretrained(str(_VECTOR_MODEL_DIR))
    except Exception as exc:  # noqa: BLE001 - any load failure → tier inactive, never a crash
        logger.warning("could not load vector model from %s; S3 tier disabled: %s", _VECTOR_MODEL_DIR, exc)
        return None

    def _embed(texts: Sequence[str]) -> np.ndarray:
        matrix = np.asarray(model.encode(list(texts)), dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # never divide an all-zero embedding by zero
        return matrix / norms

    _EMBEDDER = _embed
    logger.info("S3 vector tier active (model loaded from %s)", _VECTOR_MODEL_DIR)
    return _EMBEDDER


def _enabled_tiers(sources: Sequence[object]) -> frozenset[Tier]:
    """The tiers a turn may surface — the free Stage-1 set, plus S3 only when the vector
    source is actually active (model + index both present)."""
    tiers = {Tier.WIKI, Tier.GIT, Tier.SESSION}
    if any(isinstance(s, VectorSource) for s in sources):
        tiers.add(Tier.VECTOR)
    return frozenset(tiers)


def _build_sources(session_turns: list) -> list:
    """Construct the retrieval tiers bound to callback's roots + audience rules.

    Built per request (cheap: ~30 small wiki files + one `git rev-parse`; the vector
    tier loads its prebuilt sidecar once, process-cached) so live wiki edits are picked
    up without a restart. The session buffer is wired but typically empty in Stage 1
    (S5-P1); it ingests `session_turns` when the client sends them. The S3 vector tier
    is appended only when its model + index are present (`_make_embedder`); otherwise the
    list is the three Stage-1 tiers.
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
    sources: list = [wiki, git, session]
    embedder = _make_embedder()
    if embedder is not None and VectorSource.index_exists(_VECTOR_INDEX_DIR):
        sources.append(VectorSource(_VECTOR_INDEX_DIR, embedder, _path_audience))
    return sources


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

    sources = _build_sources(session_turns)
    scope = Scope(
        allow_dev=allow_dev,
        enabled_tiers=_enabled_tiers(sources),
        token_budget=_TOKEN_BUDGET,
    )
    # Deterministic retrieval runs fully before streaming begins (retrieve, then phrase).
    context = assemble(question, scope, sources)
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

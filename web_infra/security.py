"""Security helpers — the route guard pair (charter C-1).

`_safe_username` + `_within` are the two guards the `route-security-lint` hook
requires on every filesystem-touching route. They moved here (Sprint 8.3a) out of
`app.py` so `app.py` and every blueprint share one definition instead of
re-inlining them (`blueprints/assistant.py` carried a duplicate copy).

`_safe_username` takes an explicit `configs_dir` (keyword-only) rather than reading
a module global — that is the seam that lets a test call it with a `tmp_path`
without any Flask app context. Blueprints pass `current_app.config["CONFIGS_DIR"]`
at the call site. `_within` is pure (path + parent args) and unchanged.

P1 Hardening boundary: deterministic, no LLM calls (charter C-6). `web_infra/` is a
leaf — it never imports `app.py`, any blueprint, or `config.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

from werkzeug.utils import secure_filename


def _safe_username(username: str, *, configs_dir: Path) -> str | None:
    """Sanitize username and confirm the user exists. Returns None if invalid.

    Prevents path traversal: secure_filename strips ``../`` and other traversal
    sequences; the config existence check ensures only real users are accepted.
    """
    safe = secure_filename(username)
    if not safe:
        return None
    if not (configs_dir / f"{safe}.config").exists():
        return None
    return safe


def _within(path: Path, parent: Path) -> bool:
    """Return True only if path resolves to within parent. Prevents traversal."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


class PathTraversalError(ValueError):
    """A candidate path resolved outside its permitted root.

    Raised by `resolve_within` so a caller can map an escape attempt to an HTTP
    response (a 400/403) at the route boundary, instead of the boolean-guard
    pattern where the raw, unvalidated path is what flows on to the sink.
    """


def resolve_within(candidate: str | Path, root: Path) -> Path:
    """Resolve `candidate` and return it ONLY if it lands within `root`.

    A validated-resolver chokepoint that folds `Path(candidate)` +
    `_within(cp, root)` into one call whose **return value is the
    resolved-and-validated path**. Callers use that returned path downstream —
    never the raw input — so the value flowing into a filesystem sink derives
    from the containment check rather than from user input directly. That is the
    difference the scattered ``cp = Path(x); if not _within(cp, root): abort``
    shape could not express: there, the boolean guard and the raw `cp` are
    separate, and it is the raw `cp` that reaches the sink (often in another
    function, e.g. `hardening.context_transaction`, where a static analyzer
    can't carry the guard across the call boundary — CodeQL `py/path-injection`,
    `docs/dev/diagnosis/codeql-path-injection-context.md`).

    Containment only — existence is a separate concern. A resolved-but-absent
    path returns normally; callers still `.exists()`-check where they need to.

    Args:
        candidate: The untrusted path (a request field, a filename, …).
        root: The permitted parent directory.

    Returns:
        `Path(candidate).resolve()`, guaranteed within `root.resolve()`.

    Raises:
        PathTraversalError: if the resolved candidate is not within `root`.

    Note (static analysis): normalization uses ``os.path.realpath`` rather than
    ``Path.resolve()`` deliberately. CodeQL's ``py/path-injection`` models
    ``realpath``/``normpath``/``abspath`` as *path normalization* but treats
    ``pathlib.Path(candidate).resolve()`` on tainted input as a *sink*; and it
    models no pathlib/``relative_to`` containment check as a barrier at all. The
    containment this function enforces is therefore re-declared to CodeQL as a
    ``barrierModel`` on this function's return value
    (``.github/codeql/sartor-python-models/``), so the returned path is a
    recognized barrier. Full rationale + the falsified alternatives:
    ``docs/dev/diagnosis/codeql-path-injection-context.md`` (F-1, F-2).
    """
    resolved = Path(os.path.realpath(candidate))
    if not resolved.is_relative_to(Path(os.path.realpath(root))):
        raise PathTraversalError(str(candidate))
    return resolved

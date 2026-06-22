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

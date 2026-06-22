"""Construction gate: `web_infra/` is leaf infrastructure.

The shared web-infra package must NEVER import `app.py`, any blueprint, or
`config.py` (design §3.3 hard rule). That one-directional import graph is what
keeps it acyclic and lets every blueprint import it freely. Enforced by an AST
walk of the whole tree (catches lazy / TYPE_CHECKING / in-function imports), not
by convention.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_INFRA_DIR = REPO_ROOT / "web_infra"

_FORBIDDEN_ROOTS = frozenset({"app", "blueprints", "dashboard", "config"})


def _imported_roots(tree: ast.AST) -> set[str]:
    """Top-level module name for every import (whole tree, incl. TYPE_CHECKING)."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import within web_infra/ — fine
                continue
            roots.add((node.module or "").split(".")[0])
    return roots


def test_web_infra_package_present() -> None:
    files = sorted(WEB_INFRA_DIR.rglob("*.py"))
    assert files, "web_infra/ package missing or empty"


def test_web_infra_imports_no_forbidden_module() -> None:
    offenders: dict[str, set[str]] = {}
    for path in sorted(WEB_INFRA_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits = _imported_roots(tree) & _FORBIDDEN_ROOTS
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert not offenders, (
        f"web_infra/ must stay a leaf — it imported {offenders}. It may never import "
        "app.py, a blueprint, dashboard, or config.py; read current_app.config or take "
        "an explicit arg instead."
    )

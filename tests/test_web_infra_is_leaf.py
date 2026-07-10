"""Construction gate: `web_infra/` is leaf infrastructure.

The shared web-infra package must NEVER import `app.py`, any blueprint, or
`config.py` (design §3.3 hard rule). That one-directional import graph is what
keeps it acyclic and lets every blueprint import it freely. Enforced by an AST
walk of the whole tree (catches lazy / TYPE_CHECKING / in-function imports), not
by convention.

Reuses the shared whole-tree AST-import walk (`tests/_ast_import_roots.py`,
PX-53 — also used by `tests/test_construction_boundary.py` and
`tests/test_recall_boundary.py`).
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests._ast_import_roots import imported_roots

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_INFRA_DIR = REPO_ROOT / "web_infra"

_FORBIDDEN_ROOTS = frozenset({"app", "blueprints", "dashboard", "config"})


def test_web_infra_package_present() -> None:
    files = sorted(WEB_INFRA_DIR.rglob("*.py"))
    assert files, "web_infra/ package missing or empty"


def test_web_infra_imports_no_forbidden_module() -> None:
    offenders: dict[str, set[str]] = {}
    for path in sorted(WEB_INFRA_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits = imported_roots(tree) & _FORBIDDEN_ROOTS
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert not offenders, (
        f"web_infra/ must stay a leaf — it imported {offenders}. It may never import "
        "app.py, a blueprint, dashboard, or config.py; read current_app.config or take "
        "an explicit arg instead."
    )

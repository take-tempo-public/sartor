"""Architectural boundary test for the `recall/` Memory substrate.

`recall/` is the reusable, refactor-immune Memory substrate: by hard rule it must
NEVER import `app.py`, `analyzer.py`, the callback DB models, Flask, or any LLM
client — it depends only on the stdlib (Stage 0). That rule
(`docs/dev/memory-architecture.md` §"Reuse boundary / extraction contract") is
what makes the v1.0.8 blueprint split a *move*, not a rewrite, and future
extraction packaging-only.

This test enforces it the same way the PX-08 egress gate
(`tests/test_egress_allowlist.py`) enforces network egress: a static AST walk over
every `recall/*.py` module (so lazy / `TYPE_CHECKING` / in-function imports are
caught too). It is the boundary-lint `memory-architecture.md` calls for — a test,
not a hook (enforcement-portability is the Sprint 8.7 work).
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECALL_DIR = REPO_ROOT / "recall"

# Importing any of these from inside recall/ breaks the substrate's independence.
# `db` covers db.models / db.session / db.build_context via prefix match.
_FORBIDDEN_ROOTS = frozenset(
    {
        "app",  # the Flask app + routes
        "analyzer",  # all LLM calls
        "db",  # callback DB models / session / context builder
        "flask",  # recall/ is framework-agnostic
        "anthropic",  # recall/ is LLM-free (charter C-6 determinism boundary)
    }
)


def _recall_py_files() -> list[Path]:
    return sorted(RECALL_DIR.rglob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    """Top-level module name for every import in a parsed module (the whole tree,
    not just module scope), e.g. ``from collections.abc import X`` → ``collections``,
    ``from recall.models import Y`` → ``recall``, ``import re`` → ``re``.
    """
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — stays within the recall package
                roots.add((node.module or "recall").split(".")[0] or "recall")
            else:
                roots.add((node.module or "").split(".")[0])
    return roots


def test_recall_package_is_present():
    """Guard against the scan silently passing on an empty/missing directory."""
    files = _recall_py_files()
    assert files, "recall/ has no .py files — the boundary scan would be vacuous."
    assert (RECALL_DIR / "__init__.py") in files


def test_recall_imports_no_forbidden_module():
    """No recall/ module imports app / analyzer / db / flask / anthropic."""
    offenders: dict[str, set[str]] = {}
    for path in _recall_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits = _imported_roots(tree) & _FORBIDDEN_ROOTS
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert not offenders, (
        f"recall/ broke its dependency boundary: {offenders}. "
        "The Memory substrate must never import app.py, analyzer.py, the DB models, "
        "Flask, or an LLM client (docs/dev/memory-architecture.md 'Reuse boundary')."
    )


def test_recall_imports_only_stdlib():
    """Every import in recall/ resolves to the stdlib or back into recall itself —
    the substrate is self-contained (Stage 0 is stdlib-only), so lifting it out
    later is packaging-only."""
    stdlib = sys.stdlib_module_names
    third_party: dict[str, set[str]] = {}
    for path in _recall_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        external = {root for root in _imported_roots(tree) if root and root != "recall"}
        outside = {root for root in external if root not in stdlib}
        if outside:
            third_party[path.relative_to(REPO_ROOT).as_posix()] = outside
    assert not third_party, (
        f"recall/ imported a non-stdlib, non-recall module: {third_party}. "
        "Stage 0 is stdlib-only; any new dependency needs a pyproject + CHANGELOG "
        "entry and a deliberate update to this test."
    )

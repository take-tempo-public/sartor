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

# Light third-party libs sanctioned for the recall/sources/ tiers ONLY (Stage 2,
# Sprint 7.6). The reuse contract permits recall/ to import "light libs"
# (docs/dev/memory-architecture.md §"Reuse boundary"); the S3 VectorSource needs
# `numpy` for brute-force cosine + the `.npy` sidecar. The CORE recall/ modules stay
# strictly stdlib-only (this allowance is scoped to recall/sources/), and the heavy,
# HuggingFace-coupled `model2vec` is deliberately NOT here — it never enters recall/
# (it lives in the wiring layer), so the substrate stays embedder-agnostic + extractable.
_SOURCES_LIGHT_LIBS = frozenset({"numpy"})


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
    """Every import in recall/ resolves to the stdlib, back into recall itself, or —
    for `recall/sources/` tiers ONLY — a sanctioned light lib (`numpy`). The core
    substrate stays stdlib-only, so lifting it out later is packaging-only; the S3
    vector tier's numpy use is the single deliberate Stage-2 (Sprint 7.6) relaxation."""
    stdlib = sys.stdlib_module_names
    third_party: dict[str, set[str]] = {}
    for path in _recall_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        extra = _SOURCES_LIGHT_LIBS if path.is_relative_to(SOURCES_DIR) else frozenset()
        external = {root for root in _imported_roots(tree) if root and root != "recall"}
        outside = {root for root in external if root not in stdlib and root not in extra}
        if outside:
            third_party[path.relative_to(REPO_ROOT).as_posix()] = outside
    assert not third_party, (
        f"recall/ imported a non-stdlib, non-recall module: {third_party}. "
        "The core substrate is stdlib-only; recall/sources/ tiers may add only the "
        f"sanctioned light libs {sorted(_SOURCES_LIGHT_LIBS)} (e.g. numpy for the S3 "
        "vector tier). Any further dependency needs a pyproject + CHANGELOG entry and a "
        "deliberate update to _SOURCES_LIGHT_LIBS here. (model2vec must NOT appear in "
        "recall/ — it stays in the wiring layer so the substrate is embedder-agnostic.)"
    )


# --- recall/sources/ project-agnosticism guard (Stage 1, Sprint 7.5) --------------
#
# The concrete tiers (S1 wiki, S2 git grep, S5-P1 session) live in `recall/sources/`,
# but they must stay PROJECT-AGNOSTIC — roots + the audience resolver are injected, so
# no module here may hardcode a callback path or audience rule. The import boundary
# above can't catch that (the coupling would be a string literal, not an import). This
# guard walks every string literal that is NOT a docstring (prose may reference design
# docs freely) and rejects callback-specific path/symbol fragments. The day a tier
# needs `"docs/wiki"` baked in, it belongs in the wiring layer, not the substrate.

SOURCES_DIR = RECALL_DIR / "sources"

# Path/symbol fragments that betray project coupling if they appear in tier CODE.
_FORBIDDEN_LITERAL_FRAGMENTS = (
    "docs/wiki",
    "docs/dev",
    "configs",
    "resumes",
    "output/",
    "REPO_ROOT",
    ".last_ingest_sha",
    "SCHEMA.md",
    "app.py",
    "analyzer",
)


def _docstring_constants(tree: ast.AST) -> set[int]:
    """`id()` of every Constant node that is a module/class/function docstring, so the
    literal scan can exclude prose (which legitimately names design docs)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def test_recall_sources_subpackage_present():
    """Guard against a vacuous pass if the sources subpackage is missing/renamed."""
    files = sorted(SOURCES_DIR.rglob("*.py"))
    assert files, "recall/sources/ has no .py files — the agnosticism scan would be vacuous."
    assert (SOURCES_DIR / "__init__.py") in files


def test_recall_sources_no_hardcoded_roots():
    """No `recall/sources/*.py` CODE literal contains a callback-specific path/symbol —
    the tiers stay generic; project bindings live in the wiring layer."""
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCES_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        doc_ids = _docstring_constants(tree)
        hits: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
                hits |= {frag for frag in _FORBIDDEN_LITERAL_FRAGMENTS if frag in node.value}
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert not offenders, (
        f"recall/sources/ hardcoded a callback-specific path/symbol: {offenders}. "
        "The tiers must stay project-agnostic — inject roots + the audience resolver "
        "from the wiring layer (blueprints/assistant.py), don't bake them into recall/."
    )

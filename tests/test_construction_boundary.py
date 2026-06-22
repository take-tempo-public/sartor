"""PX-20 — the deterministic / LLM construction boundary gate (charter C-6).

`analyzer.py` is the single home for every LLM call. The deterministic modules —
`hardening`, `parser`, `generator`, `scraper`, `json_resume`, `corpus_to_json_resume`,
`pdf_render` — must NEVER import `analyzer` or `anthropic`, so the boundary holds
by construction (a failing test), not by code review.

This reuses the whole-tree AST-import walk from `tests/test_recall_boundary.py`
(which guards `recall/`'s substrate independence) and applies it to the C-6
deterministic set. The walk catches lazy / `TYPE_CHECKING` / in-function imports,
not just top-level ones.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The modules charter C-6 names "deterministic by design" (AGENTS.md / charter).
DETERMINISTIC_MODULES = (
    "hardening.py",
    "parser.py",
    "generator.py",
    "scraper.py",
    "json_resume.py",
    "corpus_to_json_resume.py",
    "pdf_render.py",
)

# An LLM call would mean importing one of these. (scraper.py legitimately imports
# `requests` for its network egress — that is the C-2 boundary, a separate gate;
# this gate is only the deterministic <-> LLM split.)
_FORBIDDEN_ROOTS = frozenset({"analyzer", "anthropic"})


def _imported_roots(tree: ast.AST) -> set[str]:
    """Top-level module name for every import (whole tree, incl. TYPE_CHECKING)."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — never reaches analyzer/anthropic
                continue
            roots.add((node.module or "").split(".")[0])
    return roots


def test_all_deterministic_modules_present() -> None:
    """No vacuous pass: every named deterministic module must actually exist."""
    missing = [m for m in DETERMINISTIC_MODULES if not (REPO_ROOT / m).is_file()]
    assert not missing, f"deterministic module(s) missing from repo root: {missing}"


@pytest.mark.parametrize("module", DETERMINISTIC_MODULES)
def test_deterministic_module_imports_no_llm(module: str) -> None:
    """A deterministic module importing analyzer/anthropic breaks the C-6 boundary."""
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"), filename=module)
    offenders = _imported_roots(tree) & _FORBIDDEN_ROOTS
    assert not offenders, (
        f"{module} imports {sorted(offenders)} — it must stay deterministic "
        "(no LLM calls; charter C-6). All model calls live in analyzer.py."
    )

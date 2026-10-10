"""Shared-toast wait gate — item 159 (item 155's class; charter C-11).

`_toast()` (`static/app.js`) writes ONE lazily created element, `#_corpusToast` (class
`corpus-toast`), and every save in the app calls it, so its text belongs to whichever call ran
last. A UX test that synchronizes on that text can be satisfied, or defeated, by an actor
other than the action under test. Item 155 was exactly that: a notes response landing after
the company save turned "Company saved" into "Notes saved", and response order alone decided
pass or fail (`docs/dev/diagnosis/test-reliability.md` O5-O6).

This gate fails when any Python in the repo names the shared toast outside an allowlisted
test. The way through is to wait on the action's own response (`page.expect_response(...)`)
or on a state the action owns, never on the toast. A test that genuinely has to read the last
writer, after synchronizing on something else, goes in `ALLOWED_TOAST_SITES` with its reason.

How a reference is found:
- Every `.py` file in the repo (minus vendored and build directories) whose bytes match
  `corpus[-_]?toast` (any case) is parsed. A matching string constant is a site, unless it is
  a docstring (exempt), or the whole right-hand side of an assignment to a name or attribute,
  which makes that name an alias instead.
- Every load of an alias (`_TOAST`, `Sel.TOAST`) in any file is a site.
- Comments are not in the AST and are not scanned.
A site is keyed by (repo-relative path, enclosing class/function qualname or `<module>`).

Known limits (stated, not papered over — C-0):
- A wait on a toast message's text alone (`page.get_by_text("Notes saved")`) names neither the
  id nor the class, so it is not caught.
- A selector assembled at runtime (concatenation, `"".join`, `getattr`) is not caught.
- Aliases match by bare identifier across files, so an unrelated name that collides with an
  alias is reported too. That fails closed: rename it.
"""

from __future__ import annotations

import ast
import os
import re
from collections import Counter
from collections.abc import Callable, Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SELF = Path(__file__).resolve()

_TOAST_RE = re.compile(r"corpus[-_]?toast", re.IGNORECASE)
_TOAST_BYTES_RE = re.compile(rb"corpus[-_]?toast", re.IGNORECASE)

# Directory names never walked: VCS, environments, caches, vendored JS, build output.
_PRUNE_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "docs-site",
        "__pycache__",
        "build",
        "dist",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

Site = tuple[str, str]  # (repo-relative POSIX path, enclosing qualname or "<module>")

# Every sanctioned reference to the shared toast: (path, scope) -> (sites in that scope, why).
# The count is exact, so a second toast wait added inside an allowed test fails too.
ALLOWED_TOAST_SITES: dict[Site, tuple[int, str]] = {
    (
        "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py",
        "test_step5_rail_is_locked_until_compose_freezes_the_composition",
    ): (
        1,
        "waits on the synchronous refusal toast from wizardGoTo(5); the refusal is in-page "
        "with no save in flight, so nothing else writes the toast (0/112 in CI at filing)",
    ),
    (
        "tests/ux/regression/test_20260611_prior_app_resume_robustness.py",
        "test_company_save_survives_a_later_notes_response",
    ): (
        1,
        "reads the LAST writer on purpose, after synchronizing on PUT /meta, to prove the "
        "forced response order really happened (item 155's own regression test)",
    ),
}


def _iter_py_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield Path(dirpath) / name


def _repo_rels() -> list[str]:
    return [
        Path(os.path.relpath(p, REPO_ROOT)).as_posix()
        for p in _iter_py_files(REPO_ROOT)
        if p.resolve() != _SELF
    ]


def _read_repo(rel: str) -> bytes:
    return (REPO_ROOT / rel).read_bytes()


class _ScopeVisitor(ast.NodeVisitor):
    """Tracks the enclosing class/function qualname of every node it visits."""

    def __init__(self, rel: str, aliases: set[str], sites: Counter[Site]) -> None:
        self.rel = rel
        self.aliases = aliases
        self.sites = sites
        self._scope: list[str] = []

    def _site(self) -> None:
        self.sites[(self.rel, ".".join(self._scope) or "<module>")] += 1

    def _scoped(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    visit_ClassDef = _scoped
    visit_FunctionDef = _scoped
    visit_AsyncFunctionDef = _scoped


def _docstring_constants(tree: ast.Module) -> set[int]:
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                out.add(id(first.value))
    return out


class _LiteralPass(_ScopeVisitor):
    """Pass 1: string constants naming the toast are sites; a whole-RHS one makes an alias."""

    def __init__(self, rel: str, aliases: set[str], sites: Counter[Site], skip: set[int]) -> None:
        super().__init__(rel, aliases, sites)
        self.skip = skip

    def _alias_definition(self, targets: list[ast.expr], value: ast.expr | None) -> bool:
        if not (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and _TOAST_RE.search(value.value)
        ):
            return False
        names = [
            t.id if isinstance(t, ast.Name) else t.attr
            for t in targets
            if isinstance(t, ast.Name | ast.Attribute)
        ]
        if not names:
            return False
        self.aliases.update(names)
        self.skip.add(id(value))
        return True

    def visit_Assign(self, node: ast.Assign) -> None:
        self._alias_definition(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._alias_definition([node.target], node.value)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if (
            isinstance(node.value, str)
            and id(node) not in self.skip
            and _TOAST_RE.search(node.value)
        ):
            self._site()


class _AliasUsePass(_ScopeVisitor):
    """Pass 2: every load of an alias is a site."""

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in self.aliases:
            self._site()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load) and node.attr in self.aliases:
            self._site()
        self.generic_visit(node)


def _scan(read: Callable[[str], bytes], rels: list[str]) -> Counter[Site]:
    """Every reference to the shared toast in `rels`, counted per (path, scope).

    Two reads of the tree: aliases are only known once every literal has been seen, and a
    use may sit in a file with no literal. Each pass prefilters on raw bytes and parses only
    the files that match (2 of 410 today). Measured 2026-10-10 on the owner's laptop: one
    warm pass over all 410 files takes ~0.5 s; the first pass on a cold cache took 9.3 s.
    """
    aliases: set[str] = set()
    sites: Counter[Site] = Counter()
    for rel in rels:
        src = read(rel)
        if _TOAST_BYTES_RE.search(src):
            tree = ast.parse(src, filename=rel)
            _LiteralPass(rel, aliases, sites, _docstring_constants(tree)).visit(tree)
    if aliases:
        names = b"|".join(re.escape(a.encode()) for a in sorted(aliases))
        alias_re = re.compile(rb"\b(?:" + names + rb")\b")
        for rel in rels:
            src = read(rel)
            if alias_re.search(src):
                _AliasUsePass(rel, aliases, sites).visit(ast.parse(src, filename=rel))
    return sites


# --------------------------------------------------------------------------- the scanner has teeth

_SYNTHETIC = {
    "literal.py": 'def test_literal(page):\n    page.locator("#_corpusToast").wait_for()\n',
    "alias.py": '_T = ".corpus-toast"\n\n\ndef test_alias(page):\n    page.locator(_T)\n',
    "attr.py": (
        "class Sel:\n"
        '    TOAST = "#_corpusToast"\n\n\n'
        "class TestPanel:\n"
        "    def test_attr(self, page):\n"
        "        page.locator(Sel.TOAST)\n"
    ),
    "fstring.py": 'def test_fstring(page, s):\n    page.locator(f"#_corpusToast.{s}")\n',
    "imported.py": "from alias import _T\n\n\ndef test_imported(page):\n    page.locator(_T)\n",
    "quiet.py": (
        '"""Mentions #_corpusToast in a module docstring."""\n\n'
        "# and #_corpusToast in a comment\n"
        "def test_quiet(page):\n"
        '    """And #_corpusToast in a function docstring."""\n'
        '    page.locator("#notes")\n'
    ),
}


def test_scanner_finds_every_reference_shape_and_skips_prose() -> None:
    """Each shape a toast wait can take is found once, in the right scope; docstrings and
    comments are not. Runs every time, so a scanner that silently stopped matching fails
    here rather than turning the real-tree test green."""
    sites = _scan(lambda rel: _SYNTHETIC[rel].encode(), list(_SYNTHETIC))
    assert sites == Counter(
        {
            ("literal.py", "test_literal"): 1,
            ("alias.py", "test_alias"): 1,
            ("attr.py", "TestPanel.test_attr"): 1,
            ("fstring.py", "test_fstring"): 1,
            ("imported.py", "test_imported"): 1,
        }
    )


# --------------------------------------------------------------------------- the real tree


def test_toast_sites_equal_the_allowlist() -> None:
    """Every reference to `#_corpusToast` in the repo is allowlisted, at its exact count, and
    every allowlist entry is still used."""
    sites = _scan(_read_repo, _repo_rels())
    offenders = {k: n for k, n in sites.items() if k not in ALLOWED_TOAST_SITES}
    assert not offenders, (
        f"UX code references the shared toast #_corpusToast: {offenders}. Every save writes "
        "that one element and the last writer wins, so a wait on it can be satisfied or "
        "defeated by another request (item 155). Wait on the action's own response "
        "(page.expect_response) or a state the action owns. If a test truly must read the "
        "last writer after synchronizing on something else, add it to ALLOWED_TOAST_SITES in "
        "tests/test_ux_toast_wait_gate.py with its reason."
    )
    miscounted = {
        k: {"found": n, "allowed": ALLOWED_TOAST_SITES[k][0]}
        for k, n in sites.items()
        if k in ALLOWED_TOAST_SITES and n != ALLOWED_TOAST_SITES[k][0]
    }
    assert not miscounted, (
        f"Allowlisted test(s) reference the shared toast a different number of times than "
        f"allowed: {miscounted}. A new toast wait inside an allowed test needs its own review."
    )
    stale = sorted(set(ALLOWED_TOAST_SITES) - set(sites))
    assert not stale, f"Allowlist rot: no longer reference the toast: {stale}. Remove them."
    assert all(reason.strip() for _, reason in ALLOWED_TOAST_SITES.values())

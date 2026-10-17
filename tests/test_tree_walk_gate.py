"""Tree-walk gate: every recursive file walk in `tests/` and `scripts/` is on a reviewed list.

Item 172 (charter C-11). A walk rooted at the repo root reads a linked worktree under
`.claude/worktrees/` as production code, and each such test kept its own hand-written exclude
list, none with `.claude` (`docs/dev/diagnosis/gate-skips-linked-worktrees.md`). Adding `.claude`
to the lists would have left the class open for the next walker, so this gate closes it: a new
recursive walk fails here until it is either rooted below the repo root and listed with its reason,
or (for a repo-wide scan) takes its file set from `tests._repo_files.repo_files`, which asks git.

What counts as a walk: a call to `.rglob(...)`, `.walk(...)` (not `ast.walk`), `.glob("**...")`,
or `glob.glob`/`glob.iglob` with `recursive=True`.

Known limits (C-0):
- Only those spellings are found. A walk built through `getattr`, an alias of `os.walk`, a
  `subprocess` call to `find`, or `os.scandir` recursion is not.
- This gate does not check that a listed walk is really rooted below the repo root; the reason
  string says so and review holds it. A walker rooted at a *variable* that happens to be the repo
  root would pass if its file is listed.
- `[tool.interrogate].exclude` in `pyproject.toml` (a tool's own walk) is covered by
  `tests/test_docstring_coverage_gate.py`, not here.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_SCAN_DIRS = ("tests", "scripts")

# repo-relative POSIX path -> (number of walk calls in that file, why none can reach .claude/).
ALLOWED_WALK_SITES: dict[str, tuple[int, str]] = {
    "tests/test_tree_walk_gate.py": (1, "this gate's own listing of tests/ and scripts/"),
    "tests/test_annotation_routes.py": (1, "walks the annotation root of a temp-dir app"),
    "tests/test_confirm_overwrite_edits.py": (1, "walks the rig's temp output dir"),
    "tests/test_data_root.py": (1, "walks named packages below the repo root"),
    "tests/test_egress_allowlist.py": (1, "globs the template directories below the repo root"),
    "tests/test_evidence_gate.py": (1, "walks scripts/enforcement"),
    "tests/test_recall_boundary.py": (3, "walks the recall/ package and its sources dir"),
    "tests/test_route_containment_gate.py": (1, "walks blueprints/"),
    "tests/test_settings_hooks_python_direct.py": (1, "globs hooks/ for retired .sh files"),
    "tests/test_ux_stub_coverage.py": (1, "walks blueprints/"),
    "tests/test_verify_doc_template.py": (1, "walks named subdirectories of the repo"),
    "tests/test_web_infra_is_leaf.py": (2, "walks web_infra/"),
    "tests/test_wiki_relevance_classification.py": (1, "walks docs/wiki"),
    "tests/test_xfail_controls_gate.py": (
        1,
        "walks the root it is given; its caller passes tests/",
    ),
}


def _is_walk_call(node: ast.Call) -> bool:
    """True for a recursive-walk call in one of the spellings the module docstring lists."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "rglob":
        return True
    if func.attr == "walk":
        return not (isinstance(func.value, ast.Name) and func.value.id == "ast")
    if func.attr in {"glob", "iglob"}:
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str) and "**" in first.value:
            return True
        return any(
            kw.arg == "recursive" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
    return False


def count_walks(source: str) -> int:
    """Number of recursive-walk calls in `source`."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and _is_walk_call(node)
    )


def _py_files() -> list[Path]:
    out: list[Path] = []
    for top in _SCAN_DIRS:
        out.extend(p for p in (REPO_ROOT / top).rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def test_every_walk_in_tests_and_scripts_is_listed_with_its_exact_count() -> None:
    found: Counter[str] = Counter()
    for path in _py_files():
        n = count_walks(path.read_text(encoding="utf-8"))
        if n:
            found[path.relative_to(REPO_ROOT).as_posix()] = n
    expected = {rel: count for rel, (count, _why) in ALLOWED_WALK_SITES.items()}
    unlisted = {rel: n for rel, n in found.items() if expected.get(rel) != n}
    stale = {rel: n for rel, n in expected.items() if found.get(rel) != n}
    assert not unlisted and not stale, (
        "Recursive file walk(s) outside the reviewed list. A repo-wide scan must take its files "
        "from tests._repo_files.repo_files() (git-listed, so a linked worktree under "
        ".claude/worktrees is never read); a walk rooted below the repo root goes in "
        f"ALLOWED_WALK_SITES with its reason.\n  unlisted or wrong count: {unlisted}\n"
        f"  listed but absent or wrong count: {stale}"
    )


class TestDetector:
    """The detector must catch each walk spelling and skip the look-alikes (control arms)."""

    def test_rglob_is_a_walk(self) -> None:
        assert count_walks("from pathlib import Path\nPath('.').rglob('*.py')\n") == 1

    def test_os_walk_is_a_walk(self) -> None:
        assert count_walks("import os\nfor _ in os.walk('.'): pass\n") == 1

    def test_double_star_glob_is_a_walk(self) -> None:
        assert count_walks("from pathlib import Path\nPath('.').glob('**/*.sh')\n") == 1

    def test_glob_module_recursive_is_a_walk(self) -> None:
        assert count_walks("import glob\nglob.glob('x/*.py', recursive=True)\n") == 1

    def test_ast_walk_is_not_a_walk(self) -> None:
        assert count_walks("import ast\nast.walk(ast.parse(''))\n") == 0

    def test_a_single_directory_glob_is_not_a_walk(self) -> None:
        assert count_walks("from pathlib import Path\nPath('.').glob('*.md')\n") == 0

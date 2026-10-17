"""`tests/_repo_files.py` lists the repo's files from git, so a linked worktree is never part of them.

Item 172: the harness puts `EnterWorktree` checkouts at `.claude/worktrees/<name>`, inside the clone.
A whole-tree `rglob`/`os.walk` reads that copy of the repo as production code and fails the main
checkout's gate. `git ls-files --cached --others --exclude-standard` does not descend into a
nested checkout, ignored or not, and costs ~65 ms against 1.3-2.3 s for a walk that has to cross
`docs-site/node_modules` (`docs/dev/diagnosis/gate-skips-linked-worktrees.md` O8).

Each case builds a throwaway repo in `tmp_path`; nothing touches the real clone.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._repo_files import repo_files


def _git(root: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with one tracked module, one untracked module, one ignored module, and two
    linked worktrees nested inside it (one under an ignored path, one not ignored)."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    (root / ".gitignore").write_text(".claude/*\nignored.py\n", encoding="utf-8")
    (root / "tracked.py").write_text("x = 1\n", encoding="utf-8")
    (root / "notes.md").write_text("n\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    (root / "untracked.py").write_text("y = 2\n", encoding="utf-8")
    (root / "ignored.py").write_text("z = 3\n", encoding="utf-8")
    _git(root, "worktree", "add", "-q", "--detach", ".claude/worktrees/wt-ignored", "HEAD")
    _git(root, "worktree", "add", "-q", "--detach", "wt-visible", "HEAD")
    return root


def test_the_nested_worktrees_really_hold_py_files(repo: Path) -> None:
    """Control arm: without it, "excluded" below could just mean "the worktree was empty"."""
    assert (repo / ".claude/worktrees/wt-ignored/tracked.py").is_file()
    assert (repo / "wt-visible/tracked.py").is_file()


def test_linked_worktrees_are_excluded_ignored_or_not(repo: Path) -> None:
    rels = {p.relative_to(repo).as_posix() for p in repo_files(".py", root=repo)}
    assert not {r for r in rels if r.startswith((".claude/", "wt-visible"))}, rels


def test_untracked_but_not_ignored_files_are_included(repo: Path) -> None:
    rels = {p.relative_to(repo).as_posix() for p in repo_files(".py", root=repo)}
    assert rels == {"tracked.py", "untracked.py"}  # not ignored.py, not the worktrees


def test_suffix_filters_and_none_returns_every_file(repo: Path) -> None:
    every = {p.relative_to(repo).as_posix() for p in repo_files(None, root=repo)}
    assert {"tracked.py", "untracked.py", "notes.md", ".gitignore"} <= every
    assert not {r for r in every if r.endswith("/")}  # a nested checkout is not a file entry


def test_a_tracked_file_deleted_from_disk_is_not_returned(repo: Path) -> None:
    (repo / "tracked.py").unlink()
    rels = {p.relative_to(repo).as_posix() for p in repo_files(".py", root=repo)}
    assert "tracked.py" not in rels


def test_outside_a_git_repo_it_raises_rather_than_returning_nothing(tmp_path: Path) -> None:
    """A silent empty list would make every scan vacuously pass."""
    bare = tmp_path / "not-a-repo"
    bare.mkdir()
    with pytest.raises(RuntimeError):
        repo_files(".py", root=bare)

"""Regression suite for `scripts/print_handoff_pointer.py` and
`scripts/check_handoff_pointer.py` (`fix/handoff-pointer-verification`,
2026-07-18).

Full evidence: docs/dev/diagnosis/handoff-pointer-verification.md — a closing
agent's hand-typed handoff-pointer commit hash was proven fabricated (absent
from every tool call/result in that session's own transcript, present only in
the model's generated chat text). `print_handoff_pointer.py` replaces the
hand-typed hash with one read directly from git, and refuses to print a
pointer for a handoff that isn't yet committed and reachable at HEAD.
`check_handoff_pointer.py` independently re-verifies a pointer line against
git state — the "enforce the method, then check the result" half, run on
both the generation side (immediately after printing, before pasting to the
user) and the consumption side (the next agent's first action).

Subprocess-level against the real scripts (`[sys.executable, script, ...]`)
in a throwaway git repo built per test — mirrors the git-repo-fixture
convention in tests/test_plan_approval_scoping.py, simplified: neither
script depends on bash or reads HOME/CLAUDE_PROJECT_DIR, so a plain
`cwd=repo` subprocess call is enough.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRINT_SCRIPT = REPO_ROOT / "scripts" / "print_handoff_pointer.py"
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_handoff_pointer.py"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result


def _make_repo(tmp_path: Path, name: str = "repo", branch: str = "main") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(["init", "-q", "-b", branch], cwd=repo)
    _git(["config", "user.email", "test@example.com"], cwd=repo)
    _git(["config", "user.name", "Test"], cwd=repo)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], cwd=repo)
    return repo


def _add_committed_doc(repo: Path, rel_path: str, contents: str = "# handoff\n") -> None:
    doc = repo / rel_path
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(contents, encoding="utf-8")
    _git(["add", rel_path], cwd=repo)
    _git(["commit", "-q", "-m", f"add {rel_path}"], cwd=repo)


def _run_print(repo: Path, doc: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv (python + known script path), test-authored input
        [sys.executable, str(PRINT_SCRIPT), doc],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _run_check(repo: Path, line: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv (python + known script path), test-authored input
        [sys.executable, str(CHECK_SCRIPT), line],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class TestPrintNotCommitted:
    def test_uncommitted_file_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        doc = repo / "docs" / "dev" / "handoffs" / "x.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# handoff\n", encoding="utf-8")  # deliberately NOT committed

        r = _run_print(repo, "docs/dev/handoffs/x.md")
        assert r.returncode != 0
        assert r.stdout == ""
        assert "not committed at HEAD" in r.stderr

    def test_missing_file_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        r = _run_print(repo, "docs/dev/handoffs/nope.md")
        assert r.returncode != 0
        assert "not found" in r.stderr


class TestPrintCommitted:
    def test_prints_exact_pointer_format(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")
        expected_hash = _git(["rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()

        r = _run_print(repo, "docs/dev/handoffs/x.md")
        assert r.returncode == 0
        assert r.stdout.strip() == f"Handoff: docs/dev/handoffs/x.md @ main ({expected_hash})"

    def test_reflects_actual_current_branch_not_hardcoded_main(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, branch="main")
        _git(["checkout", "-q", "-b", "fix/some-branch"], cwd=repo)
        _add_committed_doc(repo, "docs/dev/handoffs/y.md")

        r = _run_print(repo, "docs/dev/handoffs/y.md")
        assert r.returncode == 0
        assert " @ fix/some-branch (" in r.stdout

    def test_commit_is_current_head_not_the_docs_own_commit(self, tmp_path: Path) -> None:
        """Printed commit is HEAD *at invocation time*, not necessarily the commit
        that introduced the doc — matches verify_doc_template.py's own `commit`
        default (git rev-parse --short HEAD)."""
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/z.md")
        _git(["commit", "-q", "--allow-empty", "-m", "later, unrelated commit"], cwd=repo)

        expected_hash = _git(["rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
        r = _run_print(repo, "docs/dev/handoffs/z.md")
        assert r.returncode == 0
        assert f"({expected_hash})" in r.stdout


class TestCheckValid:
    def test_checks_own_generated_pointer_ok(self, tmp_path: Path) -> None:
        """The end-to-end loop: print, then check the exact printed output."""
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")

        printed = _run_print(repo, "docs/dev/handoffs/x.md")
        assert printed.returncode == 0

        checked = _run_check(repo, printed.stdout.strip())
        assert checked.returncode == 0
        assert checked.stdout.startswith("check_handoff_pointer: OK")


class TestCheckRejectsBadInput:
    def test_malformed_line_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        r = _run_check(repo, "this is not a pointer line at all")
        assert r.returncode != 0
        assert "malformed pointer line" in r.stderr

    def test_nonexistent_commit_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")

        r = _run_check(repo, "Handoff: docs/dev/handoffs/x.md @ main (0d7fe1a)")
        assert r.returncode != 0
        assert "commit not found" in r.stderr

    def test_path_not_present_in_cited_commit_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        initial_commit = _git(["rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")

        # cite a real, existing commit — but one from before the doc was ever added
        r = _run_check(repo, f"Handoff: docs/dev/handoffs/x.md @ main ({initial_commit})")
        assert r.returncode != 0
        assert "is not present in commit" in r.stderr

    def test_commit_not_ancestor_of_named_branch_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")
        _git(["checkout", "-q", "-b", "other"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "diverged work"], cwd=repo)
        other_commit = _git(["rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()

        # doc is present in `other`'s tree (inherited from main), but `other`'s
        # tip commit is not reachable from `main` — the ancestry check must catch this
        r = _run_check(repo, f"Handoff: docs/dev/handoffs/x.md @ main ({other_commit})")
        assert r.returncode != 0
        assert "not an ancestor" in r.stderr

    def test_unknown_branch_is_rejected(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _add_committed_doc(repo, "docs/dev/handoffs/x.md")
        commit = _git(["rev-parse", "--short", "HEAD"], cwd=repo).stdout.strip()

        r = _run_check(repo, f"Handoff: docs/dev/handoffs/x.md @ nonexistent-branch ({commit})")
        assert r.returncode != 0
        assert "branch ref not found" in r.stderr

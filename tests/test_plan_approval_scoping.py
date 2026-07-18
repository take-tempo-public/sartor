"""Per-project scoping regression suite for the plan-approval hook trio
(`fix/plan-approval-hook-scope`, 2026-07-17).

Two confirmed, live-reproduced defects in `check-plan-approved.sh` /
`mark-plan-approved.sh` / `cleanup-plan-on-merge.sh` (full evidence:
`docs/dev/diagnosis/plan-approval-hook-scope.md`), both fixed by keying state off
`CLAUDE_PROJECT_DIR` instead of one global `$HOME/.claude/plans/.approved`:

1. **Cross-project false block / false wipe** — a concurrent, unrelated project's
   plan file (or merge close-out) could false-block or wipe THIS project's already-
   approved edits, because the marker and the "newest plan file" scan were global.
2. **Unstructured merge-detection false trigger** — `cleanup-plan-on-merge.sh`'s
   `grep -q` over the whole raw stdin JSON could fire from a Bash command whose
   TEXT merely *mentioned* the trigger phrases (e.g. echoed test data), with no
   check that a merge actually happened. Reproduced live and self-inflicted during
   this branch's own investigation (see the dossier's `## Observed` step 5) — it
   deleted a real, just-approved plan.

These tests invoke the real `.claude-plugin/hooks/*.sh` scripts as subprocesses
against a temp `HOME`, following the byte-correct-JSON-via-`json.dumps` convention
established in `tests/test_enforcement_core.py` (never echo/heredoc).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".claude-plugin" / "hooks"

CHECK = HOOKS_DIR / "check-plan-approved.sh"
MARK = HOOKS_DIR / "mark-plan-approved.sh"
CLEANUP = HOOKS_DIR / "cleanup-plan-on-merge.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="the hook scripts are bash; skip where bash is absent"
)


def _project_key(project_dir: str) -> str:
    """Mirror the scripts' own `tr -c 'A-Za-z0-9' '-'` sanitization."""
    return re.sub(r"[^A-Za-z0-9]", "-", project_dir)


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


def _make_repo(tmp_path: Path, name: str) -> Path:
    """A throwaway git repo, one commit, HEAD is NOT a merge commit."""
    repo = tmp_path / name
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], cwd=repo)
    _git(["config", "user.email", "test@example.com"], cwd=repo)
    _git(["config", "user.name", "Test"], cwd=repo)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], cwd=repo)
    return repo


def _make_merge_repo(tmp_path: Path, name: str) -> Path:
    """A throwaway git repo whose HEAD genuinely IS a merge commit (>=2 parents)."""
    repo = _make_repo(tmp_path, name)
    _git(["checkout", "-q", "-b", "feature"], cwd=repo)
    _git(["commit", "-q", "--allow-empty", "-m", "feature work"], cwd=repo)
    _git(["checkout", "-q", "main"], cwd=repo)
    _git(["merge", "--no-ff", "-q", "-m", "merge feature", "feature"], cwd=repo)
    return repo


def _run(
    script: Path,
    *,
    home: Path,
    project_dir: str,
    stdin_text: str = "",
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    return subprocess.run(  # noqa: S603 - fixed argv (bash + known script path), test-authored input
        ["bash", str(script)],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _payload_edit(file_path: str) -> str:
    return json.dumps({"tool_input": {"file_path": file_path}})


def _payload_bash(command: str, output: str = "") -> str:
    return json.dumps({"tool_input": {"command": command}, "tool_response": {"output": output}})


MERGE_TEXT_TRIGGER = "git merge feature --no-ff -m x"
MERGE_OUTPUT_TRIGGER = "Merge made by the recursive strategy."


def _approve_plan(home: Path, project_dir: str, plan_path: Path) -> None:
    """Simulate: agent writes its plan file, then calls ExitPlanMode."""
    r = _run(CHECK, home=home, project_dir=project_dir, stdin_text=_payload_edit(str(plan_path)))
    assert r.returncode == 0, f"plan-file write should always be exempt: {r.stderr}"
    plan_path.write_text("# a plan\n", encoding="utf-8")
    r = _run(MARK, home=home, project_dir=project_dir)
    assert r.returncode == 0


class TestCrossProjectIsolation:
    def test_two_projects_get_independent_markers(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project_a = str(tmp_path / "project-a")
        project_b = str(tmp_path / "project-b")

        _approve_plan(home, project_a, home / ".claude" / "plans" / "plan-a.md")

        key_a = _project_key(project_a)
        key_b = _project_key(project_b)
        assert (home / ".claude" / "plans" / f".approved-{key_a}").exists()
        assert not (home / ".claude" / "plans" / f".approved-{key_b}").exists()

    def test_unrelated_project_plan_file_never_blocks_this_project(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project_a = str(tmp_path / "project-a")
        project_b = str(tmp_path / "project-b")
        edited_file = str(tmp_path / "project-a" / "some_file.py")

        _approve_plan(home, project_a, home / ".claude" / "plans" / "plan-a.md")
        r = _run(CHECK, home=home, project_dir=project_a, stdin_text=_payload_edit(edited_file))
        assert r.returncode == 0

        # Project B (unrelated, never approves) writes its OWN plan file into the
        # same shared directory -- this alone used to false-block project A.
        r = _run(
            CHECK,
            home=home,
            project_dir=project_b,
            stdin_text=_payload_edit(str(home / ".claude" / "plans" / "plan-b.md")),
        )
        assert r.returncode == 0
        (home / ".claude" / "plans" / "plan-b.md").write_text("# unapproved plan B\n")

        # Project A retries the SAME edit -- must still be allowed (the regression).
        r = _run(CHECK, home=home, project_dir=project_a, stdin_text=_payload_edit(edited_file))
        assert r.returncode == 0, f"cross-project false block: {r.stderr}"

    def test_edit_after_approval_still_reblocks_within_one_project(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project_a = str(tmp_path / "project-a")
        plan_a = home / ".claude" / "plans" / "plan-a.md"

        _approve_plan(home, project_a, plan_a)
        edited_file = str(tmp_path / "project-a" / "some_file.py")
        assert (
            _run(
                CHECK, home=home, project_dir=project_a, stdin_text=_payload_edit(edited_file)
            ).returncode
            == 0
        )

        # Edit the plan file again (still exempt) without a fresh ExitPlanMode.
        r = _run(CHECK, home=home, project_dir=project_a, stdin_text=_payload_edit(str(plan_a)))
        assert r.returncode == 0
        plan_a.write_text("# a revised plan\n", encoding="utf-8")

        r = _run(CHECK, home=home, project_dir=project_a, stdin_text=_payload_edit(edited_file))
        assert r.returncode == 2, "editing the plan after approval must re-block until re-approved"


class TestMergeCleanupScoping:
    def test_unrelated_project_merge_never_wipes_this_project(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project_a = str(tmp_path / "project-a")
        plan_a = home / ".claude" / "plans" / "plan-a.md"
        _approve_plan(home, project_a, plan_a)

        # Project B has its OWN repo, genuinely merges (--no-ff), and its
        # own cleanup fires for real.
        repo_b = _make_merge_repo(tmp_path, "project-b-repo")
        r = _run(
            CLEANUP,
            home=home,
            project_dir=str(repo_b),
            stdin_text=_payload_bash(MERGE_TEXT_TRIGGER, MERGE_OUTPUT_TRIGGER),
        )
        assert r.returncode == 0

        # Project A's approval must be untouched.
        assert plan_a.exists()
        key_a = _project_key(project_a)
        assert (home / ".claude" / "plans" / f".approved-{key_a}").exists()

    def test_real_merge_still_cleans_up_its_own_project(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_merge_repo(tmp_path, "project-repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        r = _run(
            CLEANUP,
            home=home,
            project_dir=str(repo),
            stdin_text=_payload_bash(MERGE_TEXT_TRIGGER, MERGE_OUTPUT_TRIGGER),
        )
        assert r.returncode == 0

        key = _project_key(str(repo))
        assert not plan.exists(), "a genuine merge must still clean up its own project's plan"
        assert not (home / ".claude" / "plans" / f".approved-{key}").exists()


class TestMergeDetectionHardening:
    def test_text_only_mention_does_not_delete_without_a_real_merge_commit(
        self, tmp_path: Path
    ) -> None:
        """Regression for the live, self-inflicted incident in the diagnosis dossier:
        a Bash command whose TEXT merely contains the trigger phrases (as echoed test
        data, not a real merge) must not delete anything when HEAD is not a merge
        commit."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "ordinary-repo")  # HEAD is NOT a merge commit
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        diagnostic_command = (
            f"echo 'test payload containing {MERGE_TEXT_TRIGGER} and "
            f"{MERGE_OUTPUT_TRIGGER} as data, not a real merge'"
        )
        r = _run(
            CLEANUP,
            home=home,
            project_dir=str(repo),
            stdin_text=_payload_bash(diagnostic_command),
        )
        assert r.returncode == 0

        assert plan.exists(), "text-only false trigger must not delete the plan file"
        key = _project_key(str(repo))
        assert (home / ".claude" / "plans" / f".approved-{key}").exists(), (
            "text-only false trigger must not delete the approval marker"
        )

    def test_missing_project_dir_is_a_no_op(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "ordinary-repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        r = _run(
            CLEANUP,
            home=home,
            project_dir="",
            stdin_text=_payload_bash(MERGE_TEXT_TRIGGER, MERGE_OUTPUT_TRIGGER),
        )
        assert r.returncode == 0
        assert plan.exists()

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

These tests invoke the real `hooks/*.sh` scripts as subprocesses
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
HOOKS_DIR = REPO_ROOT / "hooks"

CHECK = HOOKS_DIR / "check-plan-approved.sh"
MARK = HOOKS_DIR / "mark-plan-approved.sh"
CLEANUP = HOOKS_DIR / "cleanup-plan-on-merge.sh"
LIB_HELPER = HOOKS_DIR / "lib" / "retire-approved-plan.sh"

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
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    if extra_env:
        env.update(extra_env)
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


#: The small set of external binaries `check-plan-approved.sh` itself needs on a
#: payload that reaches the branch-merge reconciler with git hidden. Preserving
#: exactly these (via a per-binary shim) rather than every entry in a directory
#: that happens to also hold `git` is what makes `_path_without_git` safe on a
#: platform where `git` and `bash` share one bin dir (e.g. `/usr/bin` on Linux
#: CI) — dropping that whole directory broke `bash` itself, not just hid `git`,
#: the first time this test ran there (`FileNotFoundError: 'bash'`).
_NEEDED_ALONGSIDE_GIT = ("bash", "cat", "tr", "grep", "python3", "basename", "awk")


def _path_without_git(shim_root: Path) -> str:
    """This process's PATH with `git`/`git.exe` unreachable via `command -v`,
    while `_NEEDED_ALONGSIDE_GIT` stays resolvable even if it lived alongside
    `git` on the original PATH. `shim_root` is a test-owned scratch dir (e.g.
    `tmp_path`) to build the filtered shim directory under."""
    parts = os.environ.get("PATH", "").split(os.pathsep)
    git_dirs = {p for p in parts if (Path(p) / "git.exe").is_file() or (Path(p) / "git").is_file()}
    if not git_dirs:
        return os.environ.get("PATH", "")

    shim_dir = shim_root / "no-git-path"
    shim_dir.mkdir(exist_ok=True)
    for name in _NEEDED_ALONGSIDE_GIT:
        for p in parts:
            for candidate in (Path(p) / name, Path(p) / f"{name}.exe"):
                if not candidate.is_file():
                    continue
                link = shim_dir / candidate.name
                if link.exists():
                    break
                try:
                    os.symlink(candidate, link)
                except OSError:
                    try:
                        os.link(candidate, link)
                    except OSError:
                        shutil.copy2(candidate, link)
                break
            else:
                continue
            break  # first PATH match for this binary wins, mirroring normal PATH resolution

    kept = [p for p in parts if p not in git_dirs]
    kept.insert(0, str(shim_dir))
    return os.pathsep.join(kept)


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


# --------------------------------------------------------------------------- #
# Item 45 / D3(c) — branch-merge reconciliation inside check-plan-approved.sh
# (2026-08-07). Full evidence + design:
# docs/dev/diagnosis/plan-approval-marker-pr-merge.md "D3(b) refuted" /
# "The pivot — D3(c)".
# --------------------------------------------------------------------------- #


def _edit_file(repo: Path) -> str:
    return str(repo / "some_file.py")


class TestBranchMergeReconciliation:
    def test_edit_stays_allowed_on_an_unmerged_branch(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)  # HEAD is on main at approval time

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)

        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 0, r.stderr
        key = _project_key(str(repo))
        assert (home / ".claude" / "plans" / f".approved-branch-{key}").exists()

    def test_unrelated_main_movement_does_not_disarm_the_marker(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        # Advance main via an UNRELATED branch's own merge -- fix/foo's own
        # commit never becomes part of main's history here.
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["checkout", "-q", "-b", "unrelated"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "unrelated work"], cwd=repo)
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge unrelated", "unrelated"], cwd=repo)
        _git(["checkout", "-q", "fix/foo"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 0, r.stderr
        key = _project_key(str(repo))
        assert (home / ".claude" / "plans" / f".approved-branch-{key}").exists(), (
            "marker must survive an unrelated main move"
        )

    def test_branch_with_no_commits_survives_unrelated_main_movement(self, tmp_path: Path) -> None:
        """The `base` baseline RED: without it, bare ancestry false-fires the
        instant main moves, because a zero-commit branch's tip IS main's own
        tip at fork time."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/bare"], cwd=repo)  # zero commits of its own
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        key = _project_key(str(repo))
        stamp = home / ".claude" / "plans" / f".approved-branch-{key}"
        assert stamp.exists()

        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "main moves on"], cwd=repo)
        _git(["checkout", "-q", "fix/bare"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 0, r.stderr
        assert stamp.exists(), (
            "a zero-commit branch must not be archived merely because main advanced"
        )

    def test_stamp_is_late_bound_on_the_first_production_edit(self, tmp_path: Path) -> None:
        """The D3(b) refutation, as a committed test: the stamp must never
        name `main` (which is what D3(b)'s approval-time stamp would have
        recorded, since ExitPlanMode fires while HEAD is still on main)."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)  # HEAD still on main

        key = _project_key(str(repo))
        stamp = home / ".claude" / "plans" / f".approved-branch-{key}"
        assert not stamp.exists(), "no stamp should exist right after approval (HEAD is on main)"

        _git(["checkout", "-q", "-b", "fix/late"], cwd=repo)
        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 0
        assert stamp.exists()
        first_line = stamp.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == "branch=fix/late", first_line

    def test_no_stamp_is_written_while_head_is_main(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 0
        key = _project_key(str(repo))
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists()

    def test_pr_channel_merge_blocks_the_next_edit(self, tmp_path: Path) -> None:
        """THE acceptance bar. No `gh`/`git merge` TEXT is ever fed to any
        hook here -- the merge happens as a real git operation between two
        `_run()` calls, exactly the channel-independence the design claims:
        the reconciler cannot tell a PR-channel merge from a local one."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/landed"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "the work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        _git(["checkout", "-q", "main"], cwd=repo)
        _git(
            ["merge", "-q", "--no-ff", "-m", "Merge pull request #1 from fix/landed", "fix/landed"],
            cwd=repo,
        )
        _git(["checkout", "-q", "fix/landed"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 2, r.stderr
        assert "PLAN RETIRED" in r.stderr

        key = _project_key(str(repo))
        assert not (home / ".claude" / "plans" / f".approved-{key}").exists()
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists()
        assert not plan.exists(), "the plan must be moved out of the live path, not left in place"
        archive_root = home / ".claude" / "plans" / "archive"
        assert archive_root.is_dir() and any(archive_root.iterdir())

    def test_deleted_branch_blocks_the_next_edit(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/abandoned"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "half-finished"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["branch", "-D", "fix/abandoned"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 2, r.stderr
        key = _project_key(str(repo))
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists()

    def test_detached_head_is_a_no_op(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        head_sha = _git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
        _git(["checkout", "-q", head_sha], cwd=repo)

        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 0, r.stderr
        key = _project_key(str(repo))
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists()

    def test_missing_git_is_a_no_op(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/nogit"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        key = _project_key(str(repo))
        stamp = home / ".claude" / "plans" / f".approved-branch-{key}"
        assert stamp.exists()

        # Merge so a reconciler WITH git available would archive on the next call.
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/nogit"], cwd=repo)
        _git(["checkout", "-q", "fix/nogit"], cwd=repo)

        r = _run(
            CHECK,
            home=home,
            project_dir=str(repo),
            stdin_text=_payload_edit(edited),
            extra_env={"PATH": _path_without_git(tmp_path)},
        )
        assert r.returncode == 0, r.stderr
        assert stamp.exists(), "without git on PATH the reconciler must fail open, never archive"

    def test_no_main_ref_is_a_no_op(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = tmp_path / "trunk-repo"
        repo.mkdir()
        _git(["init", "-q", "-b", "trunk"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "init"], cwd=repo)

        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/trunk-based"], cwd=repo)
        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 0, r.stderr
        key = _project_key(str(repo))
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists(), (
            "no main/master ref exists -- the mechanism must no-op, not guess"
        )

    def test_plans_dir_writes_never_trigger_reconciliation(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/foo"], cwd=repo)
        _git(["checkout", "-q", "fix/foo"], cwd=repo)

        # Writing the PLAN FILE ITSELF must stay exempt -- the exemption at
        # the top of the script must return before reconciliation ever runs.
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(str(plan)))
        assert r.returncode == 0, r.stderr
        key = _project_key(str(repo))
        assert (home / ".claude" / "plans" / f".approved-branch-{key}").exists()

    def test_non_git_project_dir_is_a_no_op(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project_dir = str(tmp_path / "not-a-repo")  # never git-inited
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, project_dir, plan)

        edited = str(tmp_path / "not-a-repo" / "some_file.py")
        r = _run(CHECK, home=home, project_dir=project_dir, stdin_text=_payload_edit(edited))
        assert r.returncode == 0, r.stderr
        key = _project_key(project_dir)
        assert not (home / ".claude" / "plans" / f".approved-branch-{key}").exists()


class TestArchiveAndReceipt:
    def test_archive_preserves_the_plan_and_writes_a_receipt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-test-13")
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/foo"], cwd=repo)
        _git(["checkout", "-q", "fix/foo"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 2

        archive_root = home / ".claude" / "plans" / "archive"
        subdirs = list(archive_root.iterdir())
        assert len(subdirs) == 1
        archived = subdirs[0]
        assert (archived / "plan.md").exists()
        assert (archived / "manifest.json").exists()
        manifest = json.loads((archived / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["approved_plan"].endswith("plan.md")

        ledger_shard = repo / "docs" / "dev" / "ledger" / "sess-test-13.jsonl"
        assert ledger_shard.exists()
        records = [
            json.loads(line) for line in ledger_shard.read_text(encoding="utf-8").splitlines()
        ]
        receipts = [rec for rec in records if rec["event"] == "plan-archived"]
        assert len(receipts) == 1
        assert receipts[0]["plan"] == "plan.md"
        assert receipts[0]["session"] == "sess-test-13"

    def test_receipt_never_contains_an_absolute_plan_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-test-14")
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/foo"], cwd=repo)
        _git(["checkout", "-q", "fix/foo"], cwd=repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 2
        )

        ledger_shard = repo / "docs" / "dev" / "ledger" / "sess-test-14.jsonl"
        record = json.loads(ledger_shard.read_text(encoding="utf-8").splitlines()[0])
        assert str(home) not in record["plan"]
        assert "/" not in record["plan"]
        assert "\\" not in record["plan"]

    def test_receipt_failure_never_wedges_the_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/foo"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/foo"], cwd=repo)
        _git(["checkout", "-q", "fix/foo"], cwd=repo)

        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 2, r.stderr  # the gate fires even though no receipt could be written

        archive_root = home / ".claude" / "plans" / "archive"
        assert archive_root.is_dir() and any(archive_root.iterdir())
        ledger_dir = repo / "docs" / "dev" / "ledger"
        assert not ledger_dir.exists() or not any(ledger_dir.glob("*.jsonl"))

    def test_cleanup_on_merge_archives_instead_of_deleting(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-test-16")
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_merge_repo(tmp_path, "repo")
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

        archive_root = home / ".claude" / "plans" / "archive"
        assert archive_root.is_dir() and any(archive_root.iterdir())
        archived_dirs = list(archive_root.iterdir())
        assert any((d / "plan.md").exists() for d in archived_dirs)

        ledger_shard = repo / "docs" / "dev" / "ledger" / "sess-test-16.jsonl"
        assert ledger_shard.exists()


class TestEfficiency:
    def test_no_git_subprocess_when_main_has_not_moved(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/steady"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)

        # First edit stamps the branch (ref-file reads only -- no git call).
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        real_git = shutil.which("git")
        assert real_git is not None, "git must be resolvable for this test to mean anything"
        shim_dir = tmp_path / "shim"
        shim_dir.mkdir()
        log_path = tmp_path / "git-calls.log"
        shim = shim_dir / "git"
        shim.write_text(
            "#!/usr/bin/env bash\n"
            f'echo "$@" >> "{log_path.as_posix()}"\n'
            f'exec "{Path(real_git).as_posix()}" "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)
        extra_path = shim_dir.as_posix() + os.pathsep + os.environ.get("PATH", "")

        # Steady state: nothing has changed since the stamp was written.
        r = _run(
            CHECK,
            home=home,
            project_dir=str(repo),
            stdin_text=_payload_edit(edited),
            extra_env={"PATH": extra_path},
        )
        assert r.returncode == 0, r.stderr
        logged = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        assert not logged, (
            f"expected zero git subprocess calls in the steady state, got: {logged!r}"
        )


class TestLibHelperExemption:
    def test_lib_helper_is_not_wired_or_classified(self) -> None:
        """hooks/lib/ is a deliberate exemption from the governance-hooks
        gate (test_governance_hooks_gate.py's `_hook_stems()` globs
        `hooks/*.sh` non-recursively) -- asserted explicitly here rather than
        left implicit, per the design dossier's own instruction."""
        settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        wired_text = json.dumps(settings.get("hooks", {}))
        assert "retire-approved-plan" not in wired_text, (
            "hooks/lib/retire-approved-plan.sh is a sourced helper, never wired directly"
        )
        hook_stems = {p.stem for p in HOOKS_DIR.glob("*.sh")}
        assert "retire-approved-plan" not in hook_stems
        assert LIB_HELPER.is_file()

"""Regression suite for the plan-approval gate (`scripts/enforcement/plan_gate.py`).

History: born as the per-project scoping suite for the shell hook trio
(`fix/plan-approval-hook-scope`, 2026-07-17; evidence
`docs/dev/diagnosis/plan-approval-hook-scope.md`). State is keyed off
`CLAUDE_PROJECT_DIR`, so a concurrent, unrelated project's plan file can never
false-block or wipe THIS project's approval. Since `fix/python-direct-hooks-plan-gate`
the gate is Python, and this suite is the port's equivalence spec: every behavioral
test below ran against the `.sh` hooks first and still holds.

The retired `cleanup-plan-on-merge` hook (a PostToolUse Bash merge witness) is gone,
by owner decision on 2026-10-06. Its output-grep false-fired live (diagnosis O2), and the
edit-time reconciler already retires a merged branch's approval through any channel.
`TestKilledHookRetirements` asserts that no PostToolUse Bash hook retires anything.

The gate runs as a real subprocess (`plan_gate.py <name>`) against a temp `HOME`, with
byte-correct JSON via `json.dumps` (never echo/heredoc). A few kill-point tests drive it
in-process with an injected interruption, because a pure-Python step cannot be stalled
by a PATH shim.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.enforcement import plan_gate

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_GATE = REPO_ROOT / "scripts" / "enforcement" / "plan_gate.py"

CHECK = "check-plan-approved"
MARK = "mark-plan-approved"
LANDED = "plan-write-landed"


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
    name: str,
    *,
    home: Path,
    project_dir: str,
    stdin_text: str = "",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop(plan_gate.PLANS_DIR_ENV, None)  # this suite builds its state under HOME
    env["HOME"] = str(home)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    if extra_env:
        env.update(extra_env)
    return subprocess.run(  # noqa: S603 - fixed argv (this interpreter + the gate), test input
        [sys.executable, str(PLAN_GATE), name],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


#: The small set of external binaries kept resolvable while `git` is hidden (the gate
#: itself runs on `sys.executable`; these keep the shared shim helper general). Preserving
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


# --------------------------------------------------------------------------- #
# Item 45 / D3(c) — branch-merge reconciliation inside the plan gate (`_reconcile`)
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

    def test_new_branch_after_merge_requires_fresh_approval(self, tmp_path: Path) -> None:
        """The ordinary "finish task, start the next one" flow, not the
        same-branch-continuation shape `test_pr_channel_merge_blocks_the_next_edit`
        covers. `require-feature-branch` never allows an edit while `HEAD == main`,
        so branching straight to a brand-new task after a merge -- never revisiting
        the just-merged branch -- is actually the ONLY shape an ordinary session
        produces. Full evidence: docs/dev/diagnosis/plan-approval-branch-switch-gap.md."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/task-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "task A work"], cwd=repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
            ).returncode
            == 0
        )

        # task A lands on main -- and is never revisited, the ordinary case.
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(
            ["merge", "-q", "--no-ff", "-m", "Merge pull request #1 from fix/task-a", "fix/task-a"],
            cwd=repo,
        )

        # A brand-new branch for the NEXT task, off the now-updated main.
        _git(["checkout", "-q", "-b", "fix/task-b"], cwd=repo)
        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 2, (
            f"a brand-new branch must never inherit a stale, already-consumed "
            f"approval (stdout={r.stdout!r} stderr={r.stderr!r})"
        )
        assert "PLAN RETIRED" in r.stderr

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


class TestEfficiency:
    def test_no_git_subprocess_when_main_has_not_moved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/steady"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        # First edit stamps the branch (ref-file reads only).
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )

        calls: list[tuple[str, ...]] = []
        real_git = plan_gate._git

        def counting_git(project_dir: str, *args: str) -> subprocess.CompletedProcess[str] | None:
            calls.append(args)
            return real_git(project_dir, *args)

        monkeypatch.setattr(plan_gate, "_git", counting_git)
        monkeypatch.setattr(subprocess, "run", _forbidden_run)
        env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(repo)}
        result = plan_gate.check(json.loads(_payload_edit(edited)), env)
        assert not result.blocked, result.messages
        assert not calls, f"expected zero git calls in the steady state, got: {calls!r}"

    def test_a_packed_branch_ref_costs_no_git_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After `git gc` packs refs the branch has no loose ref file. The shell gate read
        that as "branch missing" and paid the git calls on every edit."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        _approve_plan(home, str(repo), home / ".claude" / "plans" / "plan.md")
        _git(["checkout", "-q", "-b", "fix/packed"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["pack-refs", "--all"], cwd=repo)
        assert not (repo / ".git" / "refs" / "heads" / "fix" / "packed").exists()
        stamp = home / ".claude" / "plans" / f".approved-branch-{_project_key(str(repo))}"
        past = time.time() + 5  # the stamp postdates the pack: nothing has moved since
        os.utime(stamp, (past, past))

        calls: list[tuple[str, ...]] = []
        real_git = plan_gate._git

        def counting_git(project_dir: str, *args: str) -> subprocess.CompletedProcess[str] | None:
            calls.append(args)
            return real_git(project_dir, *args)

        monkeypatch.setattr(plan_gate, "_git", counting_git)
        env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(repo)}
        assert not plan_gate.check(json.loads(_payload_edit(edited)), env).blocked
        assert not calls, f"a packed, unmoved branch must cost no git call, got: {calls!r}"


def _forbidden_run(*args: object, **kwargs: object) -> object:
    raise AssertionError(f"unexpected subprocess in the steady state: {args!r}")


# --------------------------------------------------------------------------- #
# Item 110 -- a fresh approval retired mid-branch. Evidence:
# docs/dev/diagnosis/plan-approval-retired-mid-branch.md.
# --------------------------------------------------------------------------- #


class TestStaleStampAndKilledRetire:
    def test_fresh_approval_survives_a_stale_stamp(self, tmp_path: Path) -> None:
        """Session N merges branch A; session N+1 gets a NEW approval, then
        edits on branch B. The stamp still names A (merged), and before the
        fix it retired the approval it never belonged to (item 110, 19:53)."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        _git(["checkout", "-q", "-b", "fix/task-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "task A work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "Merge pull request #1", "fix/task-a"], cwd=repo)

        # The next session: a fresh plan, a fresh ExitPlanMode -- then a new branch.
        plan_b = home / ".claude" / "plans" / "plan-b.md"
        _approve_plan(home, str(repo), plan_b)
        _git(["checkout", "-q", "-b", "fix/task-b"], cwd=repo)
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 0, (
            f"a fresh approval must not be retired by a stale stamp "
            f"(stdout={r.stdout!r} stderr={r.stderr!r})"
        )
        assert plan_b.exists(), "the fresh plan must stay in place"

    def test_killed_retire_never_leaves_a_live_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The retire path measured 5.66-14.72 s, and later 39 s median, against its hook
        timeout. A killed hook is non-blocking. Before item 110 it left the plan moved but the
        marker live. Here the process "dies" at the archive move: the pointers must already
        be gone."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)
        _git(["checkout", "-q", "-b", "fix/task-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "work"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "merge", "fix/task-a"], cwd=repo)
        _git(["checkout", "-q", "fix/task-a"], cwd=repo)

        def killed(*args: object, **kwargs: object) -> None:
            raise _Killed

        monkeypatch.setattr(shutil, "move", killed)
        env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(repo)}
        with pytest.raises(_Killed):
            plan_gate.check(json.loads(_payload_edit(edited)), env)

        key = _project_key(str(repo))
        plans = home / ".claude" / "plans"
        assert not (plans / f".approved-{key}").exists(), (
            "a hook killed mid-retire must never leave a live marker behind"
        )
        assert not (plans / f".approved-branch-{key}").exists()

    def test_epic_sprint_boundary_late_binds_when_sprint_branch_is_kept(
        self, tmp_path: Path
    ) -> None:
        """Runbook step 9 (Epic C, continuous window): sprint A ff-merges into
        the EPIC branch, and sprint B is cut off the epic tip. While A's branch
        still exists (not pruned) and is not on main, the approval must carry
        over to B with no re-approval -- merged-to-epic is not merged-to-main."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)
        _git(["checkout", "-q", "-b", "epic/c-test"], cwd=repo)
        _git(["checkout", "-q", "-b", "fix/sprint-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "sprint A"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "epic/c-test"], cwd=repo)
        _git(["merge", "-q", "--ff-only", "fix/sprint-a"], cwd=repo)
        _git(["checkout", "-q", "-b", "feat/sprint-b"], cwd=repo)
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 0, (
            f"an epic sprint boundary must not retire the approval "
            f"(stdout={r.stdout!r} stderr={r.stderr!r})"
        )
        assert plan.exists()

    def test_epic_sprint_boundary_retires_if_sprint_branch_is_pruned(self, tmp_path: Path) -> None:
        """The hazard the Epic C runbook must avoid: pruning the ff-merged
        sprint branch before the next sprint's first edit retires the approval
        (branch gone -> archive), so sprint B's implementer hits PLAN RETIRED."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)
        _git(["checkout", "-q", "-b", "epic/c-test"], cwd=repo)
        _git(["checkout", "-q", "-b", "fix/sprint-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "sprint A"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "epic/c-test"], cwd=repo)
        _git(["merge", "-q", "--ff-only", "fix/sprint-a"], cwd=repo)
        _git(["branch", "-d", "fix/sprint-a"], cwd=repo)
        _git(["checkout", "-q", "-b", "feat/sprint-b"], cwd=repo)
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert r.returncode == 2 and "PLAN RETIRED" in r.stderr, (
            f"pruning the sprint branch is expected to retire the approval "
            f"(stdout={r.stdout!r} stderr={r.stderr!r})"
        )


# --------------------------------------------------------------------------- #
# Items 154 / 111 -- approvals retired mid-branch by hooks the harness killed.
# Evidence: docs/dev/diagnosis/python-direct-hooks-plan-gate.md (O1, O2).
# --------------------------------------------------------------------------- #


def _post_bash_commands() -> list[str]:
    """Every PostToolUse hook command wired on the Bash matcher, as settings.json
    has it -- so this test follows the wiring rather than one script name."""
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return [
        hook["command"]
        for entry in settings["hooks"].get("PostToolUse", [])
        if entry.get("matcher") == "Bash"
        for hook in entry["hooks"]
    ]


class TestKilledHookRetirements:
    @pytest.mark.skipif(shutil.which("bash") is None, reason="runs the settings commands via bash")
    def test_merge_phrases_in_tool_output_never_retire_on_a_pr_merge_head(
        self, tmp_path: Path
    ) -> None:
        """O2: a read-only `cat` printed cleanup-plan-on-merge.sh's own source.
        After a PR pull, HEAD on main IS a merge commit, so the structural check
        passed and the hook archived a live plan. No PostToolUse Bash hook may
        retire anything because of what a command PRINTED."""
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        repo = _make_merge_repo(tmp_path, "repo")  # main after a PR pull
        plan = home / ".claude" / "plans" / "plan.md"
        _approve_plan(home, str(repo), plan)

        payload = _payload_bash(
            "cat hooks/some-hook.sh",
            output=f"# pre-filter phrases: {MERGE_TEXT_TRIGGER} / {MERGE_OUTPUT_TRIGGER}\n",
        )
        env = dict(os.environ)
        env["HOME"] = str(home)
        env["CLAUDE_PROJECT_DIR"] = str(repo)
        for command in _post_bash_commands():
            resolved = command.replace("${CLAUDE_PROJECT_DIR}", REPO_ROOT.as_posix())
            subprocess.run(  # noqa: S603 - the committed settings.json command, test payload
                ["bash", "-c", resolved],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=repo,
                check=False,
            )

        key = _project_key(str(repo))
        assert plan.exists(), "printed merge phrases archived a live plan (O2)"
        assert (home / ".claude" / "plans" / f".approved-{key}").exists()

    def test_newer_unapproved_plan_blocks_edits_under_the_old_approval(
        self, tmp_path: Path
    ) -> None:
        """O1: the plan Write landed, ExitPlanMode was approved, and the
        PostToolUse `mark` hook was killed before it wrote anything. Edits then
        ran under the PREVIOUS approval (its plan is what got archived later).
        A plan written after the live approval, and not the approved one, means
        the approval no longer describes the work: the next edit must block."""
        home = tmp_path / "home"
        plans = home / ".claude" / "plans"
        plans.mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        plan_a = plans / "plan-a.md"
        _approve_plan(home, str(repo), plan_a)
        key = _project_key(str(repo))
        past = time.time() - 60
        os.utime(plans / f".approved-{key}", (past, past))
        os.utime(plan_a, (past - 1, past - 1))

        _git(["checkout", "-q", "-b", "fix/task-b"], cwd=repo)
        plan_b = plans / "plan-b.md"
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(str(plan_b)))
        assert r.returncode == 0
        plan_b.write_text("# plan B\n", encoding="utf-8")
        # ExitPlanMode approved; `mark` killed before its first write.

        r = _run(
            CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(_edit_file(repo))
        )
        assert r.returncode == 2, (
            f"edits must not proceed under an approval older than the plan being "
            f"written (stdout={r.stdout!r} stderr={r.stderr!r})"
        )

    @pytest.mark.parametrize("kill_at", ["between-unlinks", "before-replace"])
    def test_mark_killed_at_any_step_never_retires_the_fresh_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kill_at: str
    ) -> None:
        """O1's other kill point. The shell `mark` wrote the fresh marker and was then
        killed before removing the previous branch's stamp; the next edit on the new branch
        reconciled that merged stamp and archived the FRESH plan. The Python `mark` drops
        the old marker and the stamp before it writes, so an interruption at any step leaves
        "no approval", never a fresh plan that a stale stamp can retire."""
        home = tmp_path / "home"
        plans = home / ".claude" / "plans"
        plans.mkdir(parents=True)
        repo = _make_repo(tmp_path, "repo")
        _approve_plan(home, str(repo), plans / "plan-a.md")
        _git(["checkout", "-q", "-b", "fix/task-a"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "task A"], cwd=repo)
        edited = _edit_file(repo)
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited)
            ).returncode
            == 0
        )
        _git(["checkout", "-q", "main"], cwd=repo)
        _git(["merge", "-q", "--no-ff", "-m", "Merge pull request #1", "fix/task-a"], cwd=repo)

        plan_b = plans / "plan-b.md"
        assert (
            _run(
                CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(str(plan_b))
            ).returncode
            == 0
        )
        plan_b.write_text("# plan B\n", encoding="utf-8")

        env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(repo)}
        if kill_at == "between-unlinks":
            real_unlink = plan_gate._unlink

            def unlink_then_die(*paths: Path) -> None:
                real_unlink(paths[0])
                raise _Killed

            monkeypatch.setattr(plan_gate, "_unlink", unlink_then_die)
        else:

            def replace_dies(*args: object, **kwargs: object) -> None:
                raise _Killed

            monkeypatch.setattr(os, "replace", replace_dies)
        with pytest.raises(_Killed):
            plan_gate.mark(env)
        monkeypatch.undo()

        _git(["checkout", "-q", "-b", "fix/task-b"], cwd=repo)
        r = _run(CHECK, home=home, project_dir=str(repo), stdin_text=_payload_edit(edited))
        assert "PLAN RETIRED" not in r.stderr and plan_b.exists(), (
            f"a mark killed mid-write left a state that retired the fresh plan "
            f"(stdout={r.stdout!r} stderr={r.stderr!r})"
        )
        assert r.returncode == 2 and "NO EDIT APPROVAL" in r.stderr, (
            "an interrupted mark must fail closed: no approval until ExitPlanMode again"
        )


class _Killed(BaseException):
    """Stands in for the harness killing the hook process mid-step (BaseException, so no
    `except OSError` in the gate can swallow it)."""


# --------------------------------------------------------------------------- #
# Item 143 -- a witness-paused plan Write batched with ExitPlanMode approved the
# STALE plan. plan-write-landed refuses ExitPlanMode until the write lands.
# --------------------------------------------------------------------------- #


class TestPlanWriteLanded:
    def _setup(self, tmp_path: Path) -> tuple[Path, str, Path]:
        home = tmp_path / "home"
        (home / ".claude" / "plans").mkdir(parents=True)
        project = str(tmp_path / "project")
        plan = home / ".claude" / "plans" / "plan.md"
        plan.write_text("# the OLD plan\n", encoding="utf-8")
        past = time.time() - 60
        os.utime(plan, (past, past))
        return home, project, plan

    def test_a_paused_write_refuses_exit_plan_mode(self, tmp_path: Path) -> None:
        home, project, plan = self._setup(tmp_path)
        # The plan Write is attempted (the gate records it) but a later guard pauses it,
        # so the file keeps its old content and mtime.
        assert (
            _run(
                CHECK, home=home, project_dir=project, stdin_text=_payload_edit(str(plan))
            ).returncode
            == 0
        )
        r = _run(LANDED, home=home, project_dir=project, stdin_text="{}")
        assert r.returncode == 2, (r.stdout, r.stderr)
        assert "PLAN NOT SAVED (plan-write-landed)" in r.stderr
        assert "plan.md" in r.stderr

    def test_a_landed_write_allows_exit_plan_mode(self, tmp_path: Path) -> None:
        home, project, plan = self._setup(tmp_path)
        assert (
            _run(
                CHECK, home=home, project_dir=project, stdin_text=_payload_edit(str(plan))
            ).returncode
            == 0
        )
        plan.write_text("# the NEW plan\n", encoding="utf-8")
        r = _run(LANDED, home=home, project_dir=project, stdin_text="{}")
        assert r.returncode == 0, r.stderr

    def test_no_recorded_attempt_allows_exit_plan_mode(self, tmp_path: Path) -> None:
        home, project, _ = self._setup(tmp_path)
        r = _run(LANDED, home=home, project_dir=project, stdin_text="{}")
        assert r.returncode == 0, r.stderr

    def test_another_projects_attempt_never_refuses_this_one(self, tmp_path: Path) -> None:
        home, project, plan = self._setup(tmp_path)
        other = str(tmp_path / "other-project")
        assert (
            _run(
                CHECK, home=home, project_dir=other, stdin_text=_payload_edit(str(plan))
            ).returncode
            == 0
        )
        r = _run(LANDED, home=home, project_dir=project, stdin_text="{}")
        assert r.returncode == 0, r.stderr

    def test_mark_still_records_the_attempted_plan(self, tmp_path: Path) -> None:
        """The attempt record is separate from `.current`: mark keeps approving the plan the
        project was writing, exactly as before."""
        home, project, plan = self._setup(tmp_path)
        _approve_plan(home, project, plan)
        marker = home / ".claude" / "plans" / f".approved-{_project_key(project)}"
        assert marker.read_text(encoding="utf-8").strip() == str(plan).replace("\\", "/")


class TestStateCompatibility:
    def test_project_key_matches_the_shell_derivation_byte_for_byte(self) -> None:
        """`tr -c 'A-Za-z0-9' '-'` maps every non-alphanumeric BYTE: a non-ASCII character
        becomes one dash per UTF-8 byte. Pointers written by the shell hooks must keep
        resolving after the switch."""
        assert plan_gate.project_key("C:\\Dev\\sartor") == "C--Dev-sartor"
        assert plan_gate.project_key("/home/u/proj-1") == "-home-u-proj-1"
        assert plan_gate.project_key("/tmp/caf\u00e9") == "-tmp-caf--"

    def test_an_msys_home_resolves_to_its_drive_on_windows(self) -> None:
        native = plan_gate._native("/c/Users/x")
        if os.name == "nt":
            assert native == "C:/Users/x"
        else:
            assert native == "/c/Users/x"

    def test_a_marker_written_by_the_shell_hook_is_honoured(self, tmp_path: Path) -> None:
        """The exact bytes `mark-plan-approved.sh` wrote (`cp` of `.current`, which
        `check-plan-approved.sh` wrote with `echo`) keep an edit allowed."""
        home = tmp_path / "home"
        plans = home / ".claude" / "plans"
        plans.mkdir(parents=True)
        project = str(tmp_path / "not-a-repo")
        plan = plans / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8")
        past = time.time() - 60
        os.utime(plan, (past, past))
        key = _project_key(project)
        line = str(plan).replace("\\", "/") + "\n"
        (plans / f".current-{key}").write_bytes(line.encode("utf-8"))
        (plans / f".approved-{key}").write_bytes(line.encode("utf-8"))
        r = _run(
            CHECK,
            home=home,
            project_dir=project,
            stdin_text=_payload_edit(str(tmp_path / "not-a-repo" / "x.py")),
        )
        assert r.returncode == 0, r.stderr

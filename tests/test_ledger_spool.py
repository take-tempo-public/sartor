"""Hook-written provenance receipts must not dirty a trunk checkout (item 165).

`claude_context_hook.record_compaction` (PreCompact) and `plan_gate.retire` (the
`plan-archived` receipt) append to the session's tracked ledger shard
`docs/dev/ledger/<session>.jsonl`. Neither looked at the branch, so a compaction or an
approval retirement after a close-out left a tracked file modified on `main`, and the next
session had to fold it into its first commit (three commits exist only for that: `71d0d17`,
`7bcbc3a`, `2097a40`; `docs/dev/diagnosis/recurrence-guardrails.md` O3).

The rule: on `main`/`master`/a detached HEAD the receipt goes to an untracked spool under
`.claude/state/ledger/`; on any other branch it goes to the tracked shard as before. The
compaction count reads both, so the C-12 disclosure does not go quiet.

These tests drive real throwaway git repos, because the property under test is "`git status`
is clean", not "a function returned a path".
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.enforcement import plan_gate
from scripts.enforcement.adapters import claude_context_hook as ctx

_REPO_ROOT = Path(__file__).resolve().parent.parent

_SESSION = "sess-spool-1"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result.stdout


def _repo(tmp_path: Path, *, branch: str = "main") -> Path:
    """A repo on `branch` whose `.gitignore` is the real one's `.claude/*` rule."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / ".gitignore").write_text(".claude/*\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "init")
    if branch != "main":
        _git(repo, "checkout", "-q", "-b", branch)
    return repo


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _tracked(repo: Path) -> Path:
    return repo / "docs" / "dev" / "ledger" / f"{_SESSION}.jsonl"


def _spool(repo: Path) -> Path:
    return repo / ".claude" / "state" / "ledger" / f"{_SESSION}.jsonl"


def _payload(repo: Path) -> dict[str, str]:
    return {"session_id": _SESSION, "cwd": str(repo), "trigger": "auto"}


class TestCompactionReceipt:
    def test_a_compaction_on_main_leaves_the_tree_clean(self, tmp_path: Path) -> None:
        """**The RED**: on `main` this wrote the tracked shard and `git status` was dirty."""
        repo = _repo(tmp_path)
        assert ctx.record_compaction(_payload(repo))
        assert _git(repo, "status", "--porcelain") == ""
        assert not _tracked(repo).exists()
        assert [row["event"] for row in _rows(_spool(repo))] == ["compacted"]

    @pytest.mark.parametrize("branch", ["master"])
    def test_master_is_trunk_too(self, tmp_path: Path, branch: str) -> None:
        repo = _repo(tmp_path)
        _git(repo, "branch", "-m", "main", branch)
        assert ctx.record_compaction(_payload(repo))
        assert _git(repo, "status", "--porcelain") == ""
        assert _spool(repo).exists()

    def test_a_detached_head_is_trunk_too(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _git(repo, "checkout", "-q", "--detach")
        assert ctx.record_compaction(_payload(repo))
        assert _git(repo, "status", "--porcelain") == ""
        assert _spool(repo).exists()

    def test_a_compaction_on_a_feature_branch_stays_in_the_tracked_shard(
        self, tmp_path: Path
    ) -> None:
        """Branch-time receipts are committed evidence (items 84, 93, 94, 110 cite them)."""
        repo = _repo(tmp_path, branch="fix/something")
        assert ctx.record_compaction(_payload(repo))
        assert [row["event"] for row in _rows(_tracked(repo))] == ["compacted"]
        assert not _spool(repo).exists()

    def test_the_count_spans_both_locations(self, tmp_path: Path) -> None:
        """A session that compacted on a branch and again on `main` has compacted twice."""
        repo = _repo(tmp_path, branch="fix/something")
        ctx.record_compaction(_payload(repo))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "carry the receipt")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "--ff-only", "fix/something")
        ctx.record_compaction(_payload(repo))
        assert _rows(_tracked(repo))  # the branch-time row came across with the merge
        assert _rows(_spool(repo))
        assert ctx.compaction_count(_payload(repo)) == 2

    def test_a_directory_with_no_git_keeps_the_tracked_shard(self, tmp_path: Path) -> None:
        """No repo means no `git status` to dirty; this is the c12 suite's own premise."""
        payload = {"session_id": _SESSION, "cwd": str(tmp_path), "trigger": "auto"}
        assert ctx.record_compaction(payload)
        assert _tracked(tmp_path).exists()
        assert not _spool(tmp_path).exists()
        assert ctx.compaction_count(payload) == 1

    def test_the_spool_is_lf_only(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        ctx.record_compaction(_payload(repo))
        assert b"\r" not in _spool(repo).read_bytes()


class TestPlanArchivedReceipt:
    """`plan_gate.retire` writes the second hook-originated receipt."""

    @staticmethod
    def _retire(repo: Path, tmp_path: Path, branch: str) -> None:
        plans = tmp_path / "plans"
        plans.mkdir()
        plan = plans / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8")
        env = {plan_gate.PLANS_DIR_ENV: str(plans), "CLAUDE_PROJECT_DIR": str(repo)}
        state = plan_gate._State(env)
        state.marker.write_text(str(plan) + "\n", encoding="utf-8")
        state.current.write_text(str(plan) + "\n", encoding="utf-8")
        plan_gate.retire(state, branch, _SESSION)

    def test_a_retirement_on_main_leaves_the_tree_clean(self, tmp_path: Path) -> None:
        """**The RED**: this appended to `docs/dev/ledger/<session>.jsonl` on `main`."""
        repo = _repo(tmp_path)
        self._retire(repo, tmp_path, "main")
        assert _git(repo, "status", "--porcelain") == ""
        assert not _tracked(repo).exists()
        rows = _rows(_spool(repo))
        assert [row["event"] for row in rows] == ["plan-archived"]
        assert rows[0]["plan"] == "plan.md"

    def test_a_retirement_on_a_feature_branch_stays_tracked(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, branch="fix/foo")
        self._retire(repo, tmp_path, "fix/foo")
        assert [row["event"] for row in _rows(_tracked(repo))] == ["plan-archived"]
        assert not _spool(repo).exists()


class TestWritersRouteThroughTheHelper:
    """A third hook that appends a receipt by hand would reintroduce the defect silently."""

    _WRITERS = (
        "scripts/enforcement/adapters/claude_context_hook.py",
        "scripts/enforcement/plan_gate.py",
    )

    @pytest.mark.parametrize("rel", _WRITERS)
    def test_the_writer_uses_hook_shard_and_names_no_tracked_path(self, rel: str) -> None:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "hook_shard(" in text, f"{rel} no longer routes its receipt through hook_shard"
        for hand_built in ('"docs" / "dev" / "ledger"', '"docs", "dev", "ledger"', "dev/ledger"):
            assert hand_built not in text.replace("`docs/dev/ledger", ""), (
                f"{rel} builds the tracked ledger path by hand ({hand_built!r}); a hook "
                "receipt must go through scripts/enforcement/ledger_spool.hook_shard"
            )


class TestSpecNamesTheHookEvents:
    """Item 55: the SPEC's event vocabulary drifted when hooks added events without amending it."""

    def test_every_event_a_hook_writer_emits_is_named_in_the_spec(self) -> None:
        import re

        spec = (_REPO_ROOT / "docs" / "dev" / "prov" / "SPEC.md").read_text(encoding="utf-8")
        emitted: set[str] = set()
        for rel in TestWritersRouteThroughTheHelper._WRITERS:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            emitted |= set(re.findall(r'"event":\s*"([a-z][a-z-]*)"', text))
        assert emitted >= {"compacted", "plan-archived"}, (
            f"the scan found {sorted(emitted)}: the writers moved or the matcher broke, and "
            "a silent pass here would be vacuous"
        )
        missing = sorted(event for event in emitted if f"`{event}`" not in spec)
        assert missing == [], f"hook-emitted ledger event(s) {missing} are not named in SPEC.md"


class TestTheSpoolStaysUntracked:
    def test_the_real_gitignore_covers_the_spool(self) -> None:
        """If someone narrows `.claude/*`, the spool starts dirtying `git status` again."""
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".claude/state/ledger/some-session.jsonl"],
            cwd=_REPO_ROOT,
            check=False,
        )
        assert result.returncode == 0

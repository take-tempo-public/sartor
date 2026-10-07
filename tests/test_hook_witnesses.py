"""The two witness hooks added or ported by item 152: `shell-probe` (SessionStart) and
`wiki-freshness-reminder` (PostToolUse Bash). Both are fail-open: they speak or stay
silent, and they never return non-zero."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from scripts.enforcement import shell_probe
from scripts.enforcement.adapters import wiki_reminder_hook
from scripts.wiki_relevance import is_wiki_relevant


class TestShellProbe:
    def test_silent_when_every_shell_has_every_tool(self) -> None:
        assert shell_probe.report({"/usr/bin/bash": []}) == ""

    def test_python_alone_missing_is_fine_where_python3_resolves(self) -> None:
        assert shell_probe.report({"/usr/bin/bash": ["python"]}) == ""

    def test_names_the_shell_and_the_missing_tools(self) -> None:
        text = shell_probe.report({"/usr/bin/bash": ["python3", "python", "sleep", "grep"]})
        assert "/usr/bin/bash" in text
        assert "python3, python, sleep, grep" in text
        assert "Monitor" in text

    def test_a_shell_that_does_not_answer_is_reported(self) -> None:
        assert "did not answer" in shell_probe.report({"C:/x/bash.exe": None})

    def test_main_never_fails_session_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom() -> dict[str, list[str] | None]:
            raise RuntimeError("probe exploded")

        monkeypatch.setattr(shell_probe, "probe", boom)
        monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
        assert shell_probe.main(["shell_probe"]) == 0

    def test_the_real_probe_returns_one_entry_per_candidate_shell(self) -> None:
        results = shell_probe.probe()
        assert set(results) == set(shell_probe._candidate_shells())


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv, local git only
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def wiki_repo(tmp_path: Path) -> Path:
    """A repo whose wiki baseline is its first commit, then one wiki-relevant change."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@e.com")
    _git(repo, "config", "user.name", "T")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "docs" / "wiki").mkdir(parents=True)
    (repo / "docs" / "wiki" / ".last_ingest_sha").write_text(base + "\n", encoding="utf-8")
    assert is_wiki_relevant("analyzer.py")
    (repo / "analyzer.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    return repo


class TestWikiReminder:
    def test_silent_on_a_command_that_is_not_a_commit(self, wiki_repo: Path) -> None:
        payload = {"cwd": str(wiki_repo), "tool_input": {"command": "git status"}}
        assert wiki_reminder_hook.message(payload) == ""

    def test_reads_the_command_never_the_tool_output(self, wiki_repo: Path) -> None:
        """The retired merge hook grepped the output and false-fired (diagnosis O2)."""
        payload = {
            "cwd": str(wiki_repo),
            "tool_input": {"command": "cat notes.txt"},
            "tool_response": {"output": "remember to git commit later"},
        }
        assert wiki_reminder_hook.message(payload) == ""

    def test_nudges_after_a_commit_with_drift(self, wiki_repo: Path) -> None:
        payload = {"cwd": str(wiki_repo), "tool_input": {"command": "git commit -m x"}}
        text = wiki_reminder_hook.message(payload)
        assert "wiki may be stale: 1 file(s) changed" in text
        assert "/wiki-ingest" in text

    def test_escalates_at_the_threshold(
        self, wiki_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(wiki_reminder_hook, "THRESHOLD", 1)
        payload = {"cwd": str(wiki_repo), "tool_input": {"command": "git commit -m x"}}
        assert "/wiki-self-update" in wiki_reminder_hook.message(payload)

    def test_silent_without_a_real_baseline(self, wiki_repo: Path) -> None:
        (wiki_repo / "docs" / "wiki" / ".last_ingest_sha").write_text(
            "not-yet-ingested\n", encoding="utf-8"
        )
        payload = {"cwd": str(wiki_repo), "tool_input": {"command": "git commit -m x"}}
        assert wiki_reminder_hook.message(payload) == ""

    def test_main_prints_a_system_message_and_returns_0(
        self, wiki_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {"cwd": str(wiki_repo), "tool_input": {"command": "git commit -m x"}}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        assert wiki_reminder_hook.main(["x"]) == 0
        assert "systemMessage" in json.loads(capsys.readouterr().out)

    def test_main_never_fails_the_tool_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("{never json"))
        assert wiki_reminder_hook.main(["x"]) == 0

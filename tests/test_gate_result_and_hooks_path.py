"""scripts/gate.py: the hooksPath preflight (item 150) and the result file (item 151).

Item 150: `core.hooksPath` was unset on the owner's clone, so `.githooks/pre-merge-commit` and
`pre-push` never ran and nothing failed. Item 151: a background gate run was reported
`exit 0` while its log ended `exit=1`, three times; the gate wrote no result of its own, so only
the log could contradict the notification. These tests stub git and the steps — no real gate
run, no real git config read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import gate


class TestHooksPathPreflight:
    def test_skipped_under_ci_without_reading_git(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def no_git(*args: str) -> str | None:
            raise AssertionError("CI must not read git config")

        monkeypatch.setattr(gate, "_git_out", no_git)
        assert gate._check_hooks_path({"CI": "true"}) == 0

    @pytest.mark.parametrize("value", [None, "", "hooks", ".claude-plugin/hooks"])
    def test_refuses_when_not_githooks(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], value: str | None
    ) -> None:
        monkeypatch.setattr(gate, "_git_out", lambda *args: value)
        assert gate._check_hooks_path({}) == 1
        assert "git config core.hooksPath .githooks" in capsys.readouterr().err

    def test_passes_when_githooks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(gate, "_git_out", lambda *args: ".githooks")
        assert gate._check_hooks_path({}) == 0


@pytest.fixture
def stubbed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Gate with every external effect stubbed; `state` drives the fingerprint and steps."""
    state: dict[str, object] = {"fingerprint": ("abc1234", "d1"), "fail": None}
    monkeypatch.setattr(gate, "_result_path", lambda: tmp_path / "gate-result.json")
    monkeypatch.setattr(gate, "_tree_fingerprint", lambda: state["fingerprint"])
    monkeypatch.setattr(gate, "_check_hooks_path", lambda: 0)
    monkeypatch.setattr(gate, "_check_memory_preflight", lambda: 0)

    def run_step(name: str, cmd: list[str]) -> int:
        if state["fail"] == name:
            return 3
        if state["fail"] == "interrupt":
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(gate, "_run_step", run_step)
    state["path"] = tmp_path / "gate-result.json"
    return state


def _record(state: dict[str, object]) -> dict[str, object]:
    path = state["path"]
    assert isinstance(path, Path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


class TestResultFile:
    def test_pass_is_recorded_and_checks_green_on_the_same_tree(
        self, stubbed: dict[str, object]
    ) -> None:
        assert gate.main([]) == 0
        record = _record(stubbed)
        assert record["exit"] == 0 and record["failed_step"] is None
        assert record["head"] == "abc1234" and record["finished_at"]
        assert gate.main(["--result"]) == 0

    def test_a_changed_tree_makes_the_result_stale(self, stubbed: dict[str, object]) -> None:
        assert gate.main([]) == 0
        stubbed["fingerprint"] = ("abc1234", "d2")
        assert gate.main(["--result"]) == 1
        stubbed["fingerprint"] = ("fff9999", "d1")
        assert gate.main(["--result"]) == 1

    def test_a_failing_step_is_recorded_with_its_name(self, stubbed: dict[str, object]) -> None:
        stubbed["fail"] = "mypy ."
        assert gate.main([]) == 3
        record = _record(stubbed)
        assert record["exit"] == 3 and record["failed_step"] == "mypy ."
        assert gate.main(["--result"]) == 1

    def test_a_refusal_is_recorded(
        self, stubbed: dict[str, object], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(gate, "_check_hooks_path", lambda: 1)
        assert gate.main([]) == 1
        assert _record(stubbed)["failed_step"] == "hooksPath preflight"

    def test_an_interrupt_is_recorded_as_no_exit(self, stubbed: dict[str, object]) -> None:
        stubbed["fail"] = "interrupt"
        with pytest.raises(KeyboardInterrupt):
            gate.main([])
        record = _record(stubbed)
        assert record["exit"] is None and record["failed_step"] == "interrupted"
        assert gate.main(["--result"]) == 1

    def test_no_record_is_not_a_pass(self, stubbed: dict[str, object]) -> None:
        assert gate.main(["--result"]) == 1

    def test_unknown_flag_is_a_usage_error(self, stubbed: dict[str, object]) -> None:
        assert gate.main(["--fast"]) == 2

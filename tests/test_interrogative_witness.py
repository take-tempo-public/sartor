"""interrogative-prompt witness (work item 87) — classifier, state, pause, adapter.

Two fail-open witnesses share `scripts/enforcement/guards/interrogative_witness.py`:
the UserPromptSubmit heuristic (`record_prompt` + the reminder the adapter prints)
and the Edit|Write one-shot pause (`decide` / `claude_check`, dispatched by
`claude_dispatcher.py`). These tests pin the load-bearing behaviors:

* the classifier errs toward "question" exactly per the item-87 spec list;
* the pause fires ONCE per recorded prompt and self-clears by marking state
  BEFORE returning the refusal (the retry must pass);
* every failure path — no state, corrupt state, missing session id — allows
  (fail-open is the design, so it is asserted, not assumed);
* the adapter always exits 0 and only speaks when the heuristic matched.

Registry membership (dispatcher order, hook classification, enforcement reach)
is pinned by the existing gates: `tests/test_enforcement_core.py`,
`tests/test_governance_hooks_gate.py`, `tests/test_enforcement_coverage.py`.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from scripts.enforcement.adapters import claude_hook, prompt_witness_hook
from scripts.enforcement.guards import interrogative_witness as iw

# --------------------------------------------------------------------------- #
# Classifier — the item-87 heuristic, verbatim spec list.
# --------------------------------------------------------------------------- #


class TestClassifyPrompt:
    @pytest.mark.parametrize(
        "prompt",
        [
            "is the handoff for the b epic run test again with opus?",
            "should the invoking agent be opus, or is that designated in the plan?",
            "why did the gate fail",  # lead word, no question mark
            "What changed in the last commit",
            "Does the pipeline spawn agents yet",
            "whether this holds under load is unclear to me",  # errs interrogative
            "can you explain the dispatcher pattern",
            'did you mean "the epic branch"?',
            "Is it green? (asking before I close the laptop)",  # trailing ")" after "?" fails; lead word carries it
            "how does the witness clear its state?",
            "ready to merge?",  # trailing ? alone, lead word not in set
            'was it "gate: all steps passed."?',  # ? behind closing quote
        ],
    )
    def test_interrogatives_classify_true(self, prompt: str) -> None:
        assert iw.classify_prompt(prompt) is True

    @pytest.mark.parametrize(
        "prompt",
        [
            "",
            "   ",
            "fix the stale-template regen guard",
            "Handoff: docs/dev/handoffs/fix-n1-args-guard-hardening.md @ main (abc1234)",
            "build item 87 and land it before the run",
            "please rerun the gate and report the tail",
            "answer recorded; proceed with the merge",
        ],
    )
    def test_directives_classify_false(self, prompt: str) -> None:
        assert iw.classify_prompt(prompt) is False

    def test_false_negative_on_a_directive_phrased_question_is_accepted_shape(self) -> None:
        """The spec accepts false negatives; this pins one so the tolerance is
        deliberate: no '?' and a lead verb outside the set stays a directive."""
        assert iw.classify_prompt("go check if the run finished") is False


# --------------------------------------------------------------------------- #
# State + pause — once per prompt, self-clearing, fail-open everywhere.
# --------------------------------------------------------------------------- #


def _env(tmp_path: Path) -> dict[str, str]:
    return {iw.STATE_DIR_ENV: str(tmp_path)}


class TestPauseLifecycle:
    def test_pause_fires_once_then_self_clears(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "tighten the regen guard", env)
        first = iw.decide("sess-1", env)
        assert first.blocked
        assert any("PAUSE (interrogative-witness)" in line for line in first.messages)
        assert any("re-run this exact tool call" in line for line in first.messages)
        second = iw.decide("sess-1", env)
        assert not second.blocked, "the pause must self-clear — one refusal per prompt"

    def test_next_prompt_re_arms_the_pause(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "first prompt", env)
        assert iw.decide("sess-1", env).blocked
        iw.record_prompt("sess-1", "second prompt", env)
        assert iw.decide("sess-1", env).blocked, "each user prompt re-arms exactly one pause"

    def test_interrogative_classification_is_named_in_the_pause(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "is the gate green?", env)
        result = iw.decide("sess-1", env)
        assert result.blocked
        assert any("classified that prompt as a QUESTION" in line for line in result.messages)

    def test_directive_prompt_pause_omits_the_classification_line(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "apply the fix", env)
        result = iw.decide("sess-1", env)
        assert result.blocked
        assert not any("QUESTION" in line for line in result.messages if "classified" in line)

    def test_no_state_allows(self, tmp_path: Path) -> None:
        """A session started before the UserPromptSubmit hook existed (or the
        hook not firing) must never wedge an edit — fail-open by design."""
        assert not iw.decide("never-recorded", _env(tmp_path)).blocked

    def test_corrupt_state_allows(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        path = iw.state_path("sess-1", env)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        assert not iw.decide("sess-1", env).blocked

    def test_sessions_are_isolated(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-a", "prompt", env)
        assert not iw.decide("sess-b", env).blocked
        assert iw.decide("sess-a", env).blocked

    def test_session_id_is_sanitized_for_the_filename(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        path = iw.state_path("../../evil", env)
        assert path.parent == Path(str(tmp_path))
        assert path.name == "evil.json"
        assert iw.state_path("", env).name == "default.json"

    def test_claude_check_reads_session_id_from_the_payload(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "is it done?", env)
        payload = {"session_id": "sess-1", "tool_name": "Edit", "tool_input": {"file_path": "x"}}
        assert iw.claude_check(payload, env).blocked
        assert not iw.claude_check(payload, env).blocked


# --------------------------------------------------------------------------- #
# Registry integration — the guard is reachable by its dispatched name.
# --------------------------------------------------------------------------- #


class TestDispatchIntegration:
    def test_dispatch_routes_the_guard_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(iw.STATE_DIR_ENV, str(tmp_path))
        iw.record_prompt("sess-d", "is this wired?")
        result = claude_hook.dispatch("interrogative-witness", {"session_id": "sess-d"})
        assert result.blocked
        assert not claude_hook.dispatch("interrogative-witness", {"session_id": "sess-d"}).blocked


# --------------------------------------------------------------------------- #
# UserPromptSubmit adapter — speaks only on a match, exits 0 on every path.
# --------------------------------------------------------------------------- #


class TestPromptWitnessAdapter:
    def _run(
        self,
        payload: object,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> tuple[int, str]:
        monkeypatch.setenv(iw.STATE_DIR_ENV, str(tmp_path))
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
        code = prompt_witness_hook.main(["prompt_witness_hook.py"])
        return code, capsys.readouterr().out

    def test_interrogative_prompt_prints_the_reminder_and_arms_the_pause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {"session_id": "sess-1", "prompt": "is the run opt-in still required?"}
        code, out = self._run(payload, tmp_path, monkeypatch, capsys)
        assert code == 0
        assert "the deliverable is the ANSWER".casefold() in out.casefold()
        assert "overrides this reminder" in out
        assert iw.decide("sess-1", _env(tmp_path)).blocked, "receipt must arm the pause too"

    def test_directive_prompt_is_silent_but_still_arms_the_pause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {"session_id": "sess-1", "prompt": "cut the branch and run sprint B1a"}
        code, out = self._run(payload, tmp_path, monkeypatch, capsys)
        assert code == 0
        assert out == ""
        assert iw.decide("sess-1", _env(tmp_path)).blocked, (
            "the pause is per-prompt, not per-question — a directive turn still gets "
            "its one first-edit consideration"
        )

    def test_malformed_stdin_exits_zero_silently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = self._run("{never json", tmp_path, monkeypatch, capsys)
        assert code == 0
        assert out == ""

    def test_unwritable_state_dir_exits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-open half 2: an I/O failure in state recording must never wedge
        prompt submission (the adapter swallows what record_prompt propagates)."""
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("occupied", encoding="utf-8")
        monkeypatch.setenv(iw.STATE_DIR_ENV, str(blocker / "nested"))
        monkeypatch.setattr(
            sys, "stdin", io.StringIO(json.dumps({"session_id": "s", "prompt": "is it ok?"}))
        )
        assert prompt_witness_hook.main(["prompt_witness_hook.py"]) == 0

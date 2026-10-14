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
    # Window off: these lifecycle tests re-run the paused call immediately (item 164); the
    # window's own behavior is pinned in `TestBatchWindow` with explicit values.
    return {iw.STATE_DIR_ENV: str(tmp_path), iw.BATCH_WINDOW_ENV: "0"}


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
# Subagent scoping (item 94) — payload shapes copied key-for-key from the live
# trace in docs/dev/diagnosis/witness-subagent-scope.md §Observed.
# --------------------------------------------------------------------------- #


def _main_payload(session_id: str) -> dict[str, object]:
    return {
        "cwd": "C:\\Dev\\sartor",
        "effort": "high",
        "hook_event_name": "PreToolUse",
        "permission_mode": "default",
        "prompt_id": "p-1",
        "scratchpad_dir": "C:\\tmp",
        "session_id": session_id,
        "tool_input": {"file_path": "x"},
        "tool_name": "Edit",
        "tool_use_id": "toolu_1",
        "transcript_path": "C:\\t.jsonl",
    }


def _subagent_payload(session_id: str) -> dict[str, object]:
    payload = _main_payload(session_id)
    del payload["effort"]
    payload["agent_id"] = "a8910364b73771fb1"
    payload["agent_type"] = "general-purpose"
    return payload


class TestSubagentScoping:
    def test_subagent_edit_does_not_consume_the_main_agents_pause(self, tmp_path: Path) -> None:
        """Run 6's failure: the subagent ate the pause and died as hook_block."""
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "run the sprint", env)
        assert not iw.claude_check(_subagent_payload("sess-1"), env).blocked
        assert iw.claude_check(_main_payload("sess-1"), env).blocked, (
            "the pause must still be armed for the main agent after a subagent edit"
        )

    def test_main_agent_payload_still_pauses_once(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "is it done?", env)
        assert iw.claude_check(_main_payload("sess-1"), env).blocked
        assert not iw.claude_check(_main_payload("sess-1"), env).blocked

    @pytest.mark.parametrize("value", ["", None, 0])
    def test_falsy_agent_id_falls_back_to_pausing(self, tmp_path: Path, value: object) -> None:
        """Fail-open discipline: only a PRESENT agent_id skips; a blank one pauses."""
        env = _env(tmp_path)
        iw.record_prompt("sess-1", "go", env)
        payload = _main_payload("sess-1")
        payload["agent_id"] = value
        assert iw.claude_check(payload, env).blocked


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


# --------------------------------------------------------------------------- #
# Item 164 instrument (A1) — trace + transcript batch lookup.
# --------------------------------------------------------------------------- #


def _transcript_line(message_id: str, tool_use_id: str) -> str:
    """One JSONL line in the layout observed in a live transcript: one tool_use per line."""
    entry = {
        "type": "assistant",
        "message": {
            "id": message_id,
            "content": [{"type": "tool_use", "id": tool_use_id, "name": "Write", "input": {}}],
        },
    }
    return json.dumps(entry)


_NOTIFICATION = "<task-notification>\n<task-id>abc</task-id>\n<status>completed</status>"


class TestNonHumanTurnsDoNotArm:
    """Item 164, A2: a task-notification is not the owner's prompt (O6)."""

    def test_a_notification_does_not_arm_the_pause(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-n", "go", env)
        assert iw.claude_check(_main_payload("sess-n"), env).blocked  # the human prompt's pause
        iw.record_prompt("sess-n", _NOTIFICATION, env)
        assert not iw.claude_check(_main_payload("sess-n"), env).blocked, (
            "a notification re-armed the pause: the owner typed nothing"
        )

    def test_a_notification_leaves_an_unconsumed_human_arm_alone(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-n", "is it done?", env)
        iw.record_prompt("sess-n", _NOTIFICATION, env)
        result = iw.claude_check(_main_payload("sess-n"), env)
        assert result.blocked
        assert any("QUESTION" in line for line in result.messages), (
            "the human prompt's classification must survive an intervening notification"
        )

    def test_a_notification_in_a_fresh_session_leaves_no_pause(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-n", _NOTIFICATION, env)
        assert not iw.claude_check(_main_payload("sess-n"), env).blocked

    def test_a_notification_never_prints_the_question_reminder(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        assert iw.record_prompt("sess-n", _NOTIFICATION + "\nwhy did it fail?", env) is False

    def test_counters_split_events_from_arms(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        iw.record_prompt("sess-n", "go", env)
        iw.record_prompt("sess-n", _NOTIFICATION, env)
        iw.record_prompt("sess-n", _NOTIFICATION, env)
        iw.record_prompt("sess-n", "again", env)
        state = json.loads(iw.state_path("sess-n", env).read_text(encoding="utf-8"))
        assert (state["prompt_seq"], state["armed_seq"]) == (4, 2)

    @pytest.mark.parametrize(
        "text",
        ["go", "is it done?", "", "<system-reminder>x</system-reminder>", "task-notification"],
    )
    def test_everything_else_still_arms(self, tmp_path: Path, text: str) -> None:
        """Unknown shapes keep today's behavior: arm (the pause is the safe direction)."""
        assert not iw.is_non_human_prompt(text)
        env = _env(tmp_path)
        iw.record_prompt("sess-n", text, env)
        assert iw.claude_check(_main_payload("sess-n"), env).blocked

    def test_leading_whitespace_before_the_tag_is_still_a_notification(self) -> None:
        assert iw.is_non_human_prompt("\n  <task-notification>x")


class TestBatchWindow:
    """Item 164, A3 replacement: refuse a paused call's batch-mates (timing heuristic)."""

    @staticmethod
    def _armed(tmp_path: Path, window: str) -> dict[str, str]:
        env = {iw.STATE_DIR_ENV: str(tmp_path), iw.BATCH_WINDOW_ENV: window}
        iw.record_prompt("sess-w", "go", env)
        return env

    def test_a_call_inside_the_window_is_refused_as_a_sibling(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "3")
        assert iw.decide("sess-w", env, now=1000.0).blocked  # the pause itself
        sibling = iw.decide("sess-w", env, now=1001.1)
        assert sibling.blocked
        assert sibling.messages[0] == iw._SIBLING_LINES[0]

    def test_a_call_after_the_window_proceeds(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "3")
        assert iw.decide("sess-w", env, now=1000.0).blocked
        assert not iw.decide("sess-w", env, now=1003.0).blocked, "the window is half-open"
        assert not iw.decide("sess-w", env, now=1500.0).blocked

    def test_every_sibling_in_the_window_is_refused_and_none_extends_it(
        self, tmp_path: Path
    ) -> None:
        env = self._armed(tmp_path, "3")
        iw.decide("sess-w", env, now=1000.0)
        assert iw.decide("sess-w", env, now=1001.0).blocked
        assert iw.decide("sess-w", env, now=1002.9).blocked
        assert not iw.decide("sess-w", env, now=1003.5).blocked, (
            "a sibling refusal must not push the window out"
        )

    def test_window_zero_disables_it(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "0")
        assert iw.decide("sess-w", env, now=1000.0).blocked
        assert not iw.decide("sess-w", env, now=1000.1).blocked

    @pytest.mark.parametrize("raw", ["", "abc", "-5"])
    def test_a_bad_value_falls_back_without_raising(self, raw: str) -> None:
        env = {iw.BATCH_WINDOW_ENV: raw}
        assert iw.batch_window_seconds(env) in (iw.DEFAULT_BATCH_WINDOW_S, 0.0)

    def test_a_new_human_prompt_clears_the_window(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "3")
        iw.decide("sess-w", env, now=1000.0)
        iw.record_prompt("sess-w", "next", env)
        state = json.loads(iw.state_path("sess-w", env).read_text(encoding="utf-8"))
        assert "paused_at" not in state

    def test_a_notification_keeps_the_window_running(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "3")
        iw.decide("sess-w", env, now=1000.0)
        iw.record_prompt("sess-w", _NOTIFICATION, env)
        assert iw.decide("sess-w", env, now=1001.0).blocked

    def test_without_state_there_is_no_window(self, tmp_path: Path) -> None:
        env = {iw.STATE_DIR_ENV: str(tmp_path), iw.BATCH_WINDOW_ENV: "3"}
        assert not iw.decide("never-seen", env, now=1.0).blocked

    def test_a_subagent_call_is_never_refused_by_the_window(self, tmp_path: Path) -> None:
        env = self._armed(tmp_path, "3")
        iw.decide("sess-w", env, now=1000.0)
        assert not iw.claude_check(_subagent_payload("sess-w"), env).blocked


class TestBatchSiblings:
    def test_lists_every_tool_use_sharing_the_message_id(self, tmp_path: Path) -> None:
        lines = [
            _transcript_line("msg_a", "toolu_a1"),
            _transcript_line("msg_b", "toolu_b1"),
            _transcript_line("msg_b", "toolu_b2"),
            _transcript_line("msg_c", "toolu_c1"),
        ]
        transcript = tmp_path / "t.jsonl"
        transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
        got = iw.batch_siblings(str(transcript), "toolu_b1")
        assert got["found"] is True
        assert got["message_id"] == "msg_b"
        assert got["sibling_ids"] == ["toolu_b1", "toolu_b2"]

    def test_id_outside_the_tail_is_not_found(self, tmp_path: Path) -> None:
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(_transcript_line("msg_a", "toolu_a1") + "\n", encoding="utf-8")
        got = iw.batch_siblings(str(transcript), "toolu_missing")
        assert got["found"] is False
        assert got["sibling_ids"] == []

    def test_unreadable_or_blank_inputs_are_not_found_and_do_not_raise(
        self, tmp_path: Path
    ) -> None:
        assert iw.batch_siblings(str(tmp_path / "nope.jsonl"), "toolu_1")["found"] is False
        assert iw.batch_siblings("", "toolu_1")["found"] is False
        assert iw.batch_siblings(str(tmp_path), "")["found"] is False

    def test_a_cut_first_line_of_the_tail_is_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iw, "_TRANSCRIPT_TAIL_BYTES", 220)
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(
            _transcript_line("msg_old", "toolu_old") + "\n" + _transcript_line("m2", "toolu_2"),
            encoding="utf-8",
        )
        got = iw.batch_siblings(str(transcript), "toolu_2")
        assert got["found"] is True
        assert got["sibling_ids"] == ["toolu_2"]


class TestTrace:
    def test_payload_trace_never_carries_prompt_text_or_paths(self) -> None:
        fields = iw.payload_trace_fields(
            {
                "session_id": "s",
                "prompt": "secret thing the owner typed",
                "transcript_path": "/home/someone/t.jsonl",
                "cwd": "/home/someone/repo",
                "prompt_id": "p-1",
            }
        )
        dumped = json.dumps(fields)
        assert "secret thing" not in dumped
        assert "someone" not in dumped
        assert fields["prompt_head"] == "(text)"
        assert fields["meta"] == {"prompt_id": "p-1"}

    def test_a_notification_prompt_records_its_leading_tag_only(self) -> None:
        fields = iw.payload_trace_fields({"prompt": "<task-notification>\n<task-id>abc</task-id>"})
        assert fields["prompt_head"].startswith("<task-notification>")
        assert "task-id" not in fields["prompt_head"]

    def test_adapter_writes_a_prompt_record_beside_the_state_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(iw.STATE_DIR_ENV, str(tmp_path))
        payload = {"session_id": "sess-t", "prompt": "<task-notification>x", "hook_event_name": "X"}
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        assert prompt_witness_hook.main(["prompt_witness_hook.py"]) == 0
        records = [
            json.loads(line)
            for line in (tmp_path / "sess-t.trace.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert records[0]["event"] == "prompt"
        assert records[0]["prompt_head"].startswith("<task-notification>")
        assert records[0]["keys"] == ["hook_event_name", "prompt", "session_id"]

    def test_trace_into_an_unwritable_dir_does_not_raise(self, tmp_path: Path) -> None:
        blocker = tmp_path / "file"
        blocker.write_text("x", encoding="utf-8")
        env = {iw.STATE_DIR_ENV: str(blocker / "nested")}
        iw.trace("s", "prompt", {"keys": []}, env)  # must simply return

    def test_a_pause_records_the_batch_lookup(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(
            _transcript_line("msg_x", "toolu_p1") + "\n" + _transcript_line("msg_x", "toolu_p2"),
            encoding="utf-8",
        )
        iw.record_prompt("sess-p", "go", env)
        payload = _main_payload("sess-p")
        payload["tool_use_id"] = "toolu_p1"
        payload["transcript_path"] = str(transcript)
        assert iw.claude_check(payload, env).blocked
        record = json.loads((tmp_path / "sess-p.trace.jsonl").read_text(encoding="utf-8"))
        assert record["event"] == "pause"
        assert record["batch"]["sibling_ids"] == ["toolu_p1", "toolu_p2"]

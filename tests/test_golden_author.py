"""The golden-set prose generator (`evals/golden_author.py`), against a stub client. No paid call.

What is pinned: the request it sends (explicit adaptive thinking, an effort, no sampling parameters, the
author pin), the telemetry row it writes under ``dataset_author``, the checks every slot must pass, the
single bounded rewrite, the refusals it will not route around, and the command line's two guards
(``--confirm-paid`` and ``--max-spend``). The real call has never been made; these tests prove the code
around it, not the live request shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import analyzer
import hardening
from evals import golden_author as ga
from evals import golden_set as gs
from evals import runner
from tests.test_golden_set import FACTS, _built, _suite, _text_for


class _Usage:
    def __init__(self, input_tokens: int = 1000, output_tokens: int = 500) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0
        self.service_tier = "standard"
        self.speed = "standard"
        self.inference_geo = "not_available"


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(
        self, text: str, *, stop_reason: str = "end_turn", usage: _Usage | None = None, n: int = 1
    ) -> None:
        self.content = [_Block(text)]
        self.stop_reason = stop_reason
        self.usage = usage or _Usage()
        self.model = ga.AUTHOR_MODEL
        self._request_id = f"req_author_{n}"


def _good_reply(prompt: str) -> str:
    """What a model that follows every rule would answer: text built from the specs in the prompt."""
    slots = json.loads(prompt)["slots"]
    return json.dumps({"slots": {sid: _text_for(spec) for sid, spec in slots.items()}})


class _Messages:
    """Scripted replies in order; a callable reply is given the user prompt. Records every request."""

    def __init__(self, script: list[Any] | None = None, usage: _Usage | None = None) -> None:
        self.script = list(script or [])
        self.usage = usage
        self.captured: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.captured.append(kwargs)
        prompt = kwargs["messages"][0]["content"]
        step = self.script.pop(0) if self.script else _good_reply
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, _Message):
            return step
        text = step(prompt) if callable(step) else step
        return _Message(text, usage=self.usage, n=len(self.captured))


class _Client:
    def __init__(self, script: list[Any] | None = None, usage: _Usage | None = None) -> None:
        self.messages = _Messages(script, usage)


@pytest.fixture
def rows(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", captured.append)
    return captured


def _corrupt(prompt: str, slot_id: str) -> str:
    """A reply that is right except for one slot, which carries a digit it may not."""
    data = json.loads(_good_reply(prompt))
    data["slots"][slot_id] += " 99 percent"
    return json.dumps(data)


class TestConstants:
    def test_the_pin_and_the_prompt_hash(self) -> None:
        assert ga.AUTHOR_MODEL == "claude-opus-5-5"
        assert ga.author_prompt_sha() == gs.sha256_text(ga.AUTHOR_SYSTEM_PROMPT)

    def test_the_author_is_not_a_product_pin(self) -> None:
        product = {analyzer.SONNET_MODEL, analyzer.HAIKU_MODEL, runner.JUDGE_MODEL}
        assert ga.AUTHOR_MODEL not in product
        assert (
            ga.AUTHOR_MODEL not in analyzer.THINKING_POLICY
        )  # not a legal product override target

    def test_the_author_model_is_priced(self) -> None:
        assert set(hardening.MODEL_PRICING[ga.AUTHOR_MODEL]) == {
            "in",
            "out",
            "cache_write",
            "cache_read",
        }


class TestRequest:
    def test_what_is_sent(self) -> None:
        profile, _ = _built()
        client = _Client()
        ga.author_cell(client, profile)
        (sent,) = client.messages.captured
        assert sent["model"] == ga.AUTHOR_MODEL
        assert sent["system"] == ga.AUTHOR_SYSTEM_PROMPT
        assert sent["thinking"] == {"type": "adaptive"}  # Opus 5.5 rejects disabled and a budget
        assert sent["output_config"] == {"effort": ga.AUTHOR_EFFORT}
        assert sent["max_tokens"] == ga.AUTHOR_MAX_TOKENS
        assert not {"temperature", "top_p", "top_k", "tool_choice", "stream"} & set(sent)
        assert [m["role"] for m in sent["messages"]] == ["user"]

    def test_the_prompt_carries_every_slot_brief_and_no_prose(self) -> None:
        profile, prose = _built()
        client = _Client()
        ga.author_cell(client, profile)
        content = client.messages.captured[0]["messages"][0]["content"]
        data = json.loads(content)
        assert sorted(data["slots"]) == sorted(profile["slots"])
        assert all(
            data["slots"][sid]["brief"] == profile["slots"][sid]["brief"]
            for sid in profile["slots"]
        )
        assert "rewrite" not in data
        assert data["facts"]["skills"] == [s["name"] for s in profile["skills"]]
        assert not any(text in content for text in prose["slots"].values())

    def test_the_prompt_is_deterministic(self) -> None:
        profile, _ = _built()
        ids = sorted(profile["slots"])
        assert ga.build_user_prompt(profile, ids) == ga.build_user_prompt(profile, ids)


class TestAuthorCell:
    def test_a_clean_reply_makes_sound_prose_in_one_request(self) -> None:
        profile, _ = _built()
        client = _Client()
        prose = ga.author_cell(client, profile)
        assert len(client.messages.captured) == 1
        assert gs.check_prose(profile, prose) == []
        assert sorted(prose["slots"]) == sorted(profile["slots"])

    def test_the_provenance_names_who_wrote_what(self) -> None:
        profile, _ = _built()
        prose = ga.author_cell(_Client(), profile)
        prov = prose["provenance"]
        assert prov["kind"] == "generated"
        assert prov["model"] == ga.AUTHOR_MODEL
        assert prov["requested_model"] == ga.AUTHOR_MODEL
        assert prov["effort"] == ga.AUTHOR_EFFORT
        assert prov["prompt_version"] == ga.AUTHOR_PROMPT_VERSION
        assert prov["prompt_sha256"] == ga.author_prompt_sha()
        assert prov["profile_sha256"] == gs.sha256_text(gs.canonical_json(profile))
        assert prov["request_ids"] == ["req_author_1"]
        assert prov["attempts"] == 1

    def test_one_slot_that_breaks_a_rule_is_rewritten_alone(self) -> None:
        profile, _ = _built()
        client = _Client([lambda p: _corrupt(p, "r1.b2")])
        prose = ga.author_cell(client, profile)
        assert len(client.messages.captured) == 2
        second = json.loads(client.messages.captured[1]["messages"][0]["content"])
        assert list(second["slots"]) == ["r1.b2"]
        assert "99" in second["rewrite"]["r1.b2"]["previous_text"]
        assert any("number 99" in p for p in second["rewrite"]["r1.b2"]["problems"])
        assert gs.check_prose(profile, prose) == []
        assert prose["provenance"]["attempts"] == 2

    def test_slots_that_still_fail_are_rejected_and_nothing_is_returned(self) -> None:
        profile, _ = _built()
        client = _Client([lambda p: _corrupt(p, "r1.b2"), lambda p: _corrupt(p, "r1.b2")])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert len(client.messages.captured) == ga.MAX_ATTEMPTS
        assert any("r1.b2" in p and "number 99" in p for p in caught.value.problems)

    def test_a_slot_the_reply_leaves_out_counts_as_a_failure(self) -> None:
        profile, _ = _built()

        def drop_one(prompt: str) -> str:
            data = json.loads(_good_reply(prompt))
            data["slots"].pop("summary.1")
            return json.dumps(data)

        client = _Client([drop_one])
        prose = ga.author_cell(client, profile)
        second = json.loads(client.messages.captured[1]["messages"][0]["content"])
        assert list(second["slots"]) == ["summary.1"]
        assert "summary.1" in prose["slots"]

    def test_an_invention_trap_in_a_resume_slot_is_a_failure(self) -> None:
        profile, _ = _built()
        trap_skill = profile["expected"]["forbidden_inventions"][0].replace("\\", "")

        def claim(prompt: str) -> str:
            data = json.loads(_good_reply(prompt))
            data["slots"]["r1.b2"] += f" {trap_skill}"
            return json.dumps(data)

        profile["slots"]["r1.b2"]["max_words"] += 5
        client = _Client([claim, claim])
        with pytest.raises(ga.AuthorRejected) as caught:
            ga.author_cell(client, profile)
        assert any("trap" in p for p in caught.value.problems)

    def test_a_jd_may_name_a_skill_the_candidate_lacks(self) -> None:
        profile, _ = _built()
        client = _Client()
        prose = ga.author_cell(client, profile)  # the JD slots must name the absent skills
        needs = prose["slots"]["jd.hospital.needs"]
        absent = [
            s["name"]
            for s in FACTS["skills"]
            if s["name"] not in {k["name"] for k in profile["skills"]}
        ]
        assert any(a in needs for a in absent)

    @pytest.mark.parametrize(
        ("reply", "needle"),
        [
            (_Message("{}", stop_reason="refusal"), "refusal"),
            (_Message("{}", stop_reason="max_tokens"), "max_tokens"),
            (_Message("not json"), "not JSON"),
            (_Message('{"slots": [1]}'), "not {"),
            (_Message('{"slots": {"r1.b1": 5}}'), "not {"),
        ],
    )
    def test_an_unusable_reply_raises_and_is_not_retried(
        self, reply: _Message, needle: str
    ) -> None:
        profile, _ = _built()
        client = _Client([reply])
        with pytest.raises(ga.AuthorError, match=needle):
            ga.author_cell(client, profile)
        assert len(client.messages.captured) == 1

    def test_a_refusal_names_the_decision_not_to_fall_back(self) -> None:
        profile, _ = _built()
        with pytest.raises(ga.AuthorError, match="no fallback model"):
            ga.author_cell(_Client([_Message("{}", stop_reason="refusal")]), profile)

    def test_an_unsound_profile_sends_nothing(self) -> None:
        profile, _ = _built()
        profile["slots"].pop("r1.b1")
        client = _Client()
        with pytest.raises(ga.AuthorError, match="not sound"):
            ga.author_cell(client, profile)
        assert client.messages.captured == []

    def test_the_prose_writes_and_the_suite_checks_clean(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        profile, _ = _built("entry")
        prose = ga.author_cell(_Client(), profile)
        gs.write_cell(root, profile, prose)
        manifest = gs.load_manifest(root)
        manifest["author"]["prompt_versions"][ga.AUTHOR_PROMPT_VERSION] = ga.author_prompt_sha()
        gs.write_manifest(root, manifest)
        assert gs.check_suite(root, {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}) == []


class TestTelemetry:
    def test_the_row(self, rows: list[dict[str, Any]]) -> None:
        profile, _ = _built()
        ga.author_cell(_Client(), profile)
        (row,) = rows
        assert row["call"] == "dataset_author"
        assert row["model"] == ga.AUTHOR_MODEL
        assert row["answered_model"] == ga.AUTHOR_MODEL
        assert row["prompt_version"] == ga.AUTHOR_PROMPT_VERSION
        assert row["prompt_sha256"] == ga.author_prompt_sha()
        assert row["producer_id"]
        assert row["username"] == f"golden:{profile['cell']}"
        assert row["status"] == "ok"
        assert row["api_request_id"] == "req_author_1"

    def test_the_settings_record_what_ran_and_not_the_prompt(
        self, rows: list[dict[str, Any]]
    ) -> None:
        profile, _ = _built()
        ga.author_cell(_Client(), profile)
        settings = rows[0]["request_settings"]
        assert settings["thinking"] == {"type": "adaptive"}
        assert settings["output_config"] == {"effort": ga.AUTHOR_EFFORT}
        assert "system" not in settings and "messages" not in settings

    def test_a_failed_call_leaves_an_error_row_and_raises(self, rows: list[dict[str, Any]]) -> None:
        profile, _ = _built()
        with pytest.raises(RuntimeError, match="network down"):
            ga.author_cell(_Client([RuntimeError("network down")]), profile)
        (row,) = rows
        assert row["status"] == "error"
        assert row["error_type"] == "RuntimeError"
        assert row["prompt_version"] == ga.AUTHOR_PROMPT_VERSION

    def test_the_default_judge_row_keeps_the_product_prompt_version(
        self, rows: list[dict[str, Any]]
    ) -> None:
        analyzer.log_judge_call(
            call_kind="judge_grade",
            username="eval:x",
            model=runner.JUDGE_MODEL,
            request_kwargs={"model": runner.JUDGE_MODEL, "max_tokens": 5},
            response=None,
            elapsed_ms=1,
        )
        assert rows[0]["prompt_version"] == analyzer.effective_prompt_version()


class TestCost:
    def test_cost_is_priced_from_the_table(self) -> None:
        profile, _ = _built()
        prose = ga.author_cell(_Client(usage=_Usage(250_000, 50_000)), profile)
        # 250,000 input at $4/M + 50,000 output at $20/M
        assert ga.cost_of(prose) == pytest.approx(1.0 + 1.0)


class TestCommandLine:
    def _root(self, tmp_path: Path) -> Path:
        return _suite(tmp_path)

    def _args(self, root: Path, *extra: str) -> list[str]:
        return ["--root", str(root), "--profession", "demo-ops", "--max-spend", "10", *extra]

    def test_without_confirm_paid_nothing_is_sent_and_no_client_is_built(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def no_client() -> Any:
            raise AssertionError("a client was built without --confirm-paid")

        monkeypatch.setattr(runner, "_get_client", no_client)
        assert ga.main(self._args(self._root(tmp_path), "--level", "entry")) == 3
        assert "nothing was sent" in capsys.readouterr().err

    def test_max_spend_is_required_and_must_be_positive(self, tmp_path: Path) -> None:
        root = self._root(tmp_path)
        with pytest.raises(SystemExit):
            ga.main(
                [
                    "--root",
                    str(root),
                    "--profession",
                    "demo-ops",
                    "--level",
                    "entry",
                    "--confirm-paid",
                ]
            )
        complete = [
            "--root",
            str(root),
            "--profession",
            "demo-ops",
            "--level",
            "entry",
            "--confirm-paid",
        ]
        with pytest.raises(SystemExit):  # every required argument is present; only the cap is wrong
            ga.main([*complete, "--max-spend", "0"])
        with pytest.raises(SystemExit):
            ga.main([*complete, "--max-spend", "-3"])

    def test_a_cell_that_exists_is_never_touched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        monkeypatch.setattr(runner, "_get_client", lambda: _Client())
        before = (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes()
        assert ga.main(self._args(root, "--level", "mid", "--confirm-paid")) == 1
        assert (root / "cells" / "demo-ops-mid" / "prose.json").read_bytes() == before

    def test_it_writes_the_cells_and_restamps_the_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client()
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        code = ga.main(self._args(root, "--level", "entry", "--level", "lead", "--confirm-paid"))
        assert code == 0
        assert gs.cell_names(root) == ["demo-ops-entry", "demo-ops-lead", "demo-ops-mid"]
        manifest = gs.load_manifest(root)
        assert (
            manifest["author"]["prompt_versions"][ga.AUTHOR_PROMPT_VERSION]
            == ga.author_prompt_sha()
        )
        assert gs.check_suite(root, {ga.AUTHOR_PROMPT_VERSION: ga.author_prompt_sha()}) == []

    def test_the_spend_cap_stops_before_the_next_cell(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client(usage=_Usage(250_000, 0))  # $1.00 a cell
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        args = [
            "--root",
            str(root),
            "--profession",
            "demo-ops",
            "--max-spend",
            "1",
            "--confirm-paid",
        ]
        code = ga.main([*args, "--level", "entry", "--level", "lead"])
        assert code == ga.EXIT_OVER_BUDGET
        assert gs.cell_names(root) == [
            "demo-ops-entry",
            "demo-ops-mid",
        ]  # the first was written, the second was not
        assert len(client.messages.captured) == 1

    def test_a_rejected_cell_is_not_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._root(tmp_path)
        client = _Client([lambda p: _corrupt(p, "r1.b2")] * 2)
        monkeypatch.setattr(runner, "_get_client", lambda: client)
        assert ga.main(self._args(root, "--level", "entry", "--confirm-paid")) == 1
        assert gs.cell_names(root) == ["demo-ops-mid"]

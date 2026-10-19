"""Item 175 gaps 5 and 6: eval-judge calls leave a telemetry row, and eval records name real models.

The judges (`evals.runner._grade`, `_score_distinctiveness`) used to call `messages.create`
directly and discard the response, so their spend and the model that scored a fixture appeared
nowhere. They now write a `judge_*` row through `analyzer.log_judge_call`, and `_eval_cost_since`
keeps eval `cost_usd` generation-only. `test_judge_row_mirrors_every_request_kwarg` is the
fail-closed half (charter C-11), the judge-side twin of `tests/test_call_provenance.py`.

Offline: `_emit_call_log` is captured per test (and `tests/conftest.py` already redirects the
real log), so nothing reaches the developer's `logs/llm_calls.jsonl`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import analyzer
import hardening
from evals import runner
from evals.runner import JUDGE_MODEL, _eval_cost_since, _grade, _score_distinctiveness

PROMPT_SENTINEL = "SENTINEL-JUDGE-INPUT-must-never-be-logged"


class _Usage:
    input_tokens = 100
    output_tokens = 20
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0
    service_tier = "standard"
    speed = "standard"
    inference_geo = "not_available"


class _Block:
    def __init__(self, text):
        self.text = text


class _Message:
    model = JUDGE_MODEL
    stop_reason = "end_turn"
    usage = _Usage()
    _request_id = "req_judge_1"

    def __init__(self, text):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, response):
        self._response = response
        self.captured: list[dict] = []

    def create(self, **kwargs):
        self.captured.append(kwargs)
        if isinstance(self._response, BaseException):
            raise self._response
        return self._response


class _Client:
    def __init__(self, response):
        self.messages = _Messages(response)


@pytest.fixture
def rows(monkeypatch) -> list[dict]:
    captured: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", captured.append)
    return captured


@pytest.fixture
def rubric(tmp_path: Path) -> Path:
    path = tmp_path / "rubric.md"
    path.write_text(f"Grade this. {PROMPT_SENTINEL}", encoding="utf-8")
    return path


def test_grade_writes_one_judge_row_joined_to_the_verdict(rows, rubric):
    client = _Client(_Message('{"score": 4.5, "reasons": ["ok"], "failed_rules": []}'))

    grade = _grade(client, rubric, {"x": PROMPT_SENTINEL}, "fx")

    assert len(rows) == 1
    row = rows[0]
    assert row["call"] == "judge_grade"
    assert row["username"] == "eval:fx"
    assert row["model"] == JUDGE_MODEL
    assert row["answered_model"] == JUDGE_MODEL
    assert row["status"] == "ok"
    assert row["input_tokens"] == 100
    assert row["served_as"]["inference_geo"] == "not_available"
    assert row["api_request_id"] == "req_judge_1"
    assert grade["judge_request_id"] == row["api_request_id"]


def test_judge_row_mirrors_every_request_kwarg(rows, rubric):
    """C-11: a setting added to the judge call but not recorded fails here."""
    client = _Client(_Message('{"score": 4, "reasons": [], "failed_rules": []}'))

    _grade(client, rubric, {}, "fx")

    sent = client.messages.captured[0]
    settings = rows[0]["request_settings"]
    assert set(settings) == set(sent) - {"system", "messages"}
    assert settings["max_tokens"] == 1024
    assert all(settings[k] == sent[k] for k in settings)


def test_judge_row_never_carries_the_judged_text(rows, rubric):
    client = _Client(_Message('{"score": 4, "reasons": [], "failed_rules": []}'))

    _grade(client, rubric, {"x": PROMPT_SENTINEL}, "fx")

    assert PROMPT_SENTINEL not in json.dumps(rows[0])


def test_distinctiveness_writes_its_own_judge_row(rows):
    client = _Client(_Message('{"score": 3.5, "summary": "fine"}'))

    result = _score_distinctiveness(client, "resume", "jd", "fx")

    assert result["score"] == 3.5
    assert result["judge_request_id"] == "req_judge_1"
    assert [r["call"] for r in rows] == ["judge_distinctiveness"]
    assert rows[0]["request_settings"]["max_tokens"] == 128


def test_failed_judge_call_logs_an_error_row_and_still_raises_from_grade(rows, rubric):
    client = _Client(ConnectionError("upstream unavailable"))

    with pytest.raises(ConnectionError):
        _grade(client, rubric, {}, "fx")

    row = rows[0]
    assert row["status"] == "error"
    assert row["call"] == "judge_grade"
    assert row["error_type"] == "ConnectionError"
    assert row["api_request_id"] is None


def test_failed_distinctiveness_call_degrades_to_judge_error_and_logs(rows):
    client = _Client(ConnectionError("upstream unavailable"))

    result = _score_distinctiveness(client, "resume", "jd", "fx")

    assert result["summary"] == "judge_error"
    assert result["judge_request_id"] is None
    assert rows[0]["status"] == "error"


def test_magicmock_judge_response_leaves_a_parseable_log_line(rubric):
    """`test_eval_runner.py` drives `_grade` with a bare MagicMock message; the row must survive it."""
    log = analyzer.LOG_PATH  # redirected to a per-test tmp file by tests/conftest.py
    msg = MagicMock()
    msg.content = [MagicMock(text='{"score": 4, "reasons": [], "failed_rules": []}')]
    client = MagicMock()
    client.messages.create.return_value = msg

    grade = _grade(client, rubric, {}, "fx")

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["answered_model"] is None
    assert row["api_request_id"] is None
    assert grade["judge_request_id"] is None


def test_eval_cost_ignores_judge_rows_whatever_their_order(monkeypatch, tmp_path):
    t0 = datetime.now(UTC).isoformat()
    base = {
        "username": "eval:fx",
        "model": analyzer.SONNET_MODEL,
        "input_tokens": 1000,
        "output_tokens": 1000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    ts = datetime.now(UTC).isoformat()
    log = tmp_path / "llm_calls.jsonl"
    log.write_text(
        "\n".join(
            json.dumps(r)
            for r in (
                {**base, "call": "generate", "timestamp": ts},
                {**base, "model": JUDGE_MODEL, "call": "judge_distinctiveness", "timestamp": ts},
                {**base, "model": JUDGE_MODEL, "call": "judge_grade", "timestamp": ts},
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)

    cost = _eval_cost_since(t0, "fx")

    generation_only = hardening.compute_call_cost({**base, "call": "generate"})
    assert generation_only > 0
    assert cost == pytest.approx(generation_only)


def test_model_snapshots_follow_the_analyzer_pins():
    assert runner.MODEL_SNAPSHOTS["sonnet"] == analyzer.SONNET_MODEL
    assert runner.MODEL_SNAPSHOTS["haiku"] == analyzer.HAIKU_MODEL
    assert runner.MODEL_SNAPSHOTS["haiku_judge"] == runner.JUDGE_MODEL

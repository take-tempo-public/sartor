"""Tests for the per-call model selection refactor in _call_llm.

Confirms that the new `model` kwarg flows through to the Anthropic client
call and into JSONL telemetry, and that the default (no override) still
selects Sonnet so all existing call sites are unchanged.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import analyzer
from analyzer import HAIKU_MODEL, SONNET_MODEL, _call_llm


def _stub_client(captured: dict) -> MagicMock:
    """Build a mock anthropic client that records the model passed to stream()."""
    final = MagicMock()
    final.usage.input_tokens = 10
    final.usage.output_tokens = 5
    final.usage.cache_creation_input_tokens = 0
    final.usage.cache_read_input_tokens = 0
    final.stop_reason = "end_turn"

    stream = MagicMock()
    stream.text_stream = iter(["{}"])
    stream.get_final_message.return_value = final

    cm = MagicMock()
    cm.__enter__.return_value = stream
    cm.__exit__.return_value = False

    def record(**kwargs):
        captured["model"] = kwargs["model"]
        return cm

    client = MagicMock()
    client.messages.stream.side_effect = record
    return client


class TestModelKwarg:
    def test_default_uses_sonnet(self, tmp_path, monkeypatch):
        # Redirect telemetry to a temp file so we can inspect it.
        monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "calls.jsonl")
        captured: dict = {}
        client = _stub_client(captured)

        _call_llm(client, "prompt", call_kind="test", username="u", run_id="r")

        assert captured["model"] == SONNET_MODEL
        # Telemetry should also record the actual model used.
        rec = json.loads((tmp_path / "calls.jsonl").read_text(encoding="utf-8").strip())
        assert rec["model"] == SONNET_MODEL

    def test_explicit_haiku(self, tmp_path, monkeypatch):
        monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "calls.jsonl")
        captured: dict = {}
        client = _stub_client(captured)

        _call_llm(client, "prompt", call_kind="test", username="u", run_id="r", model=HAIKU_MODEL)

        assert captured["model"] == HAIKU_MODEL
        rec = json.loads((tmp_path / "calls.jsonl").read_text(encoding="utf-8").strip())
        assert rec["model"] == HAIKU_MODEL

    def test_model_none_falls_back_to_sonnet(self, tmp_path, monkeypatch):
        monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "calls.jsonl")
        captured: dict = {}
        client = _stub_client(captured)

        _call_llm(client, "prompt", call_kind="test", username="u", run_id="r", model=None)

        assert captured["model"] == SONNET_MODEL

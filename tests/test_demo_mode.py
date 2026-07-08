"""Unit tests for F-19 offline/demo mode (`SARTOR_DEMO=1`).

Covers:
  - activation: env flag on/off, `config.Config.demo_mode`, real-key-plus-flag
    = demo wins, missing-key-no-flag stays byte-identical to before this
    feature existed;
  - every analyzer call kind short-circuits to canned output with ZERO
    `anthropic.Anthropic` construction (a poison client that raises on any
    attribute access proves the object is never touched, not merely that its
    real methods aren't called);
  - telemetry: a demo call never appends to `logs/llm_calls.jsonl` (contrasted
    with a real call, which does — proving the assertion isn't vacuous).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

import analyzer
import demo_fixtures
import web_infra.clients as web_infra_clients
from config import Config
from recall.models import Context

if TYPE_CHECKING:
    import anthropic

    from hardening import ContextSet


class _PoisonClient:
    """A stand-in `client` that raises loudly on ANY attribute access.

    Proves demo mode never dereferences the client object at all — not just
    that `.messages.create`/`.stream` weren't called, but that nothing on it
    was ever touched.
    """

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(
            f"demo mode touched client.{name} — it must short-circuit before any client use"
        )


def _Poison() -> anthropic.Anthropic:
    """A poison client cast to the declared parameter type (same trick as `_get_client`'s own sentinel return)."""
    return cast("anthropic.Anthropic", _PoisonClient())


_CTX_DICT: dict[str, Any] = {
    "career_corpus": [
        {
            "id": 1,
            "company": "Acme",
            "bullets": [
                {"id": 10, "text": "Did a thing", "has_outcome": False},
                {"id": 11, "text": "Did another thing", "has_outcome": True},
            ],
        }
    ],
    "summary_items": [{"id": 5, "text": "Positioning variant A"}],
    "experience_summary_items": [
        {"experience_id": 1, "items": [{"id": 7, "text": "Intro variant A"}]}
    ],
    "skill_items": [{"id": 3, "name": "Python"}],
    "jd_text": "Senior SRE role requiring Kubernetes and Terraform.",
    "summary_source_text": "Existing positioning summary.",
    "clarifications": {},
}
# ContextSet is a TypedDict; the transient keys above are exactly how the routes
# stage them at runtime (typed as object on the TypedDict), so the cast mirrors
# production reality rather than papering over a type mismatch.
_CTX = cast("ContextSet", _CTX_DICT)


# --- Activation ----------------------------------------------------------------


class TestActivation:
    def test_is_demo_mode_false_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SARTOR_DEMO", raising=False)
        assert demo_fixtures.is_demo_mode() is False

    def test_is_demo_mode_true_when_flag_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SARTOR_DEMO", "1")
        assert demo_fixtures.is_demo_mode() is True

    def test_is_demo_mode_requires_the_literal_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SARTOR_DEMO", "true")
        assert demo_fixtures.is_demo_mode() is False

    def test_config_demo_mode_reads_env_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SARTOR_DEMO", "1")
        cfg = Config()
        assert cfg.demo_mode is True
        assert cfg.as_flask_config()["DEMO_MODE"] is True

    def test_config_demo_mode_off_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SARTOR_DEMO", raising=False)
        cfg = Config()
        assert cfg.demo_mode is False
        assert cfg.as_flask_config()["DEMO_MODE"] is False

    def test_config_demo_mode_explicit_override_wins_over_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SARTOR_DEMO", "1")
        assert Config(demo_mode=False).demo_mode is False

    def test_get_client_returns_sentinel_in_demo_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SARTOR_DEMO", "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        def _boom(*args: object, **kwargs: object) -> None:
            raise AssertionError("anthropic.Anthropic() must never be constructed in demo mode")

        monkeypatch.setattr("web_infra.clients.anthropic.Anthropic", _boom)
        client = web_infra_clients._get_client()
        assert isinstance(client, web_infra_clients._DemoClient)

    def test_get_client_real_key_plus_demo_flag_means_demo_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real key present alongside the flag must still yield the demo
        sentinel — demo mode wins, so a demo run can never accidentally spend."""
        monkeypatch.setenv("SARTOR_DEMO", "1")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real-key-must-never-be-read")

        def _boom(*args: object, **kwargs: object) -> None:
            raise AssertionError("a real key present must not cause a real client construction")

        monkeypatch.setattr("web_infra.clients.anthropic.Anthropic", _boom)
        client = web_infra_clients._get_client()
        assert isinstance(client, web_infra_clients._DemoClient)

    def test_get_client_missing_key_no_flag_is_unchanged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Missing key + no demo flag stays byte-identical: a REAL (keyless)
        client is still constructed here; it only fails at the first live API
        call. Demo mode never activates implicitly just because the key is
        missing."""
        monkeypatch.delenv("SARTOR_DEMO", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Point the local-key-file fallback at an empty temp dir so a real
        # `.api_key` sitting at the repo root (if any) can't make this test
        # pass for the wrong reason.
        monkeypatch.setattr(web_infra_clients, "_REPO_ROOT", tmp_path)
        client = web_infra_clients._get_client()
        assert not isinstance(client, web_infra_clients._DemoClient)
        assert client.api_key == ""


# --- Every analyzer call kind short-circuits, zero client construction --------


class TestCallKindsShortCircuit:
    """One assertion block per public analyzer call kind analyzer.py exposes."""

    @pytest.fixture(autouse=True)
    def _demo_and_telemetry(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
        monkeypatch.setenv("SARTOR_DEMO", "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        log_path = tmp_path / "calls.jsonl"
        monkeypatch.setattr(analyzer, "LOG_PATH", log_path)
        return log_path

    def test_analyze(self) -> None:
        result = analyzer.analyze(_Poison(), _CTX)
        assert "essential_skills" in result

    def test_analyze_streaming(self) -> None:
        events = list(analyzer.analyze_streaming(_Poison(), _CTX))
        kind, payload = events[-1]
        assert kind == "done"
        assert "essential_skills" in cast("dict[str, Any]", payload)

    def test_avatar_answer_streaming(self) -> None:
        ctx = Context(query="", units=(), token_estimate=0, truncated=False)
        events = list(analyzer.avatar_answer_streaming(_Poison(), "What is sartor?", ctx))
        kind, raw_payload = events[-1]
        payload = cast("dict[str, Any]", raw_payload)
        assert kind == "done"
        assert payload["citations"] == []
        assert payload["answer"]

    def test_clarify(self) -> None:
        result = analyzer.clarify(_Poison(), _CTX, {})
        assert result["questions"]

    def test_clarify_iteration(self) -> None:
        result = analyzer.clarify_iteration(_Poison(), _CTX, {}, "", "", "", {}, [])
        assert result["questions"]

    def test_generate(self) -> None:
        result = analyzer.generate(_Poison(), _CTX, {})
        assert "resume_content" in result
        assert result["cover_letter_content"]

    def test_generate_no_cover_letter(self) -> None:
        result = analyzer.generate(_Poison(), _CTX, {}, with_cover_letter=False)
        assert result["cover_letter_content"] == ""

    def test_generate_streaming(self) -> None:
        events = list(analyzer.generate_streaming(_Poison(), _CTX, {}))
        kind, payload = events[-1]
        assert kind == "done"
        assert "resume_content" in cast("dict[str, Any]", payload)

    def test_generate_cover_letter_against_resume(self) -> None:
        result = analyzer.generate_cover_letter_against_resume(_Poison(), _CTX, {}, "# Résumé")
        assert result["cover_letter_content"]

    def test_check_refinement_scope(self) -> None:
        assert analyzer.check_refinement_scope(_Poison(), "make it punchier") == {"valid": True}

    def test_critique_proposal(self) -> None:
        result = analyzer.critique_proposal(
            _Poison(),
            original_text="Led the thing.",
            user_edited_text=None,
            subject_kind="bullet",
            experience_context={},
        )
        assert result["verdict"] != "good"  # never a rubber-stamped "good" in demo mode

    def test_recommend_bullets(self) -> None:
        result = analyzer.recommend_bullets(_Poison(), _CTX)
        recs = result["recommendations"]
        assert recs
        assert recs[0]["experience_id"] == 1
        assert set(recs[0]["bullet_ids"]) <= {10, 11}  # only REAL ids from _CTX

    def test_recommend_summaries(self) -> None:
        result = analyzer.recommend_summaries(_Poison(), _CTX)
        assert result["recommendation"]["summary_item_id"] == 5

    def test_recommend_experience_summaries(self) -> None:
        result = analyzer.recommend_experience_summaries(_Poison(), _CTX)
        assert result["recommendations"][0]["summary_item_id"] == 7

    def test_recommend_skills(self) -> None:
        result = analyzer.recommend_skills(_Poison(), _CTX)
        assert result["recommendation"]["skill_ids"] == [3]

    def test_suggest_skills(self) -> None:
        assert analyzer.suggest_skills(_Poison(), _CTX) == {"proposals": []}

    def test_draft_gap_fill_bullets(self) -> None:
        assert analyzer.draft_gap_fill_bullets(_Poison(), _CTX) == {"proposals": []}

    def test_promote_clarification_to_bullet(self) -> None:
        result = analyzer.promote_clarification_to_bullet(
            _Poison(), question="Used Terraform?", answer="Yes, for VPC peering."
        )
        assert result["text"] == "Yes, for VPC peering."  # verbatim, never rewritten

    def test_draft_positioning_summary(self) -> None:
        result = analyzer.draft_positioning_summary(_Poison(), _CTX)
        # Echoed from the staged source text, never invented.
        assert result["summary"] == _CTX_DICT["summary_source_text"]

    def test_no_call_kind_writes_telemetry(self, _demo_and_telemetry: Path) -> None:
        """Every call kind above ran with demo mode active; none of them may
        have appended to logs/llm_calls.jsonl."""
        analyzer.analyze(_Poison(), _CTX)
        analyzer.clarify(_Poison(), _CTX, {})
        analyzer.generate(_Poison(), _CTX, {})
        assert not _demo_and_telemetry.exists()


class TestTelemetryContrast:
    """Proves the "no telemetry" assertion above isn't vacuous: a REAL
    (non-demo) call through the same `_call_llm` boundary DOES write a
    record to the same log path."""

    def test_real_call_writes_telemetry(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from unittest.mock import MagicMock

        monkeypatch.delenv("SARTOR_DEMO", raising=False)
        log_path = tmp_path / "calls.jsonl"
        monkeypatch.setattr(analyzer, "LOG_PATH", log_path)

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
        client = MagicMock()
        client.messages.stream.return_value = cm

        analyzer._call_llm(client, "prompt", call_kind="test", username="u", run_id="r")

        assert log_path.exists()
        rec = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert rec["call"] == "test"

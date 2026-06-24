"""Unit tests for the shared web-infra package (Sprint 8.3a).

Covers all six helper groups. The config-dependent helpers take an explicit
`configs_dir` so most of these need no Flask app context; the two that read
request/app context (`_error_detail_payload`, `_is_localhost_request`) use a
minimal throwaway Flask app's request context.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask

from web_infra import (
    _error_detail_payload,
    _get_client,
    _get_or_provision_candidate,
    _is_localhost_request,
    _load_config,
    _safe_username,
    _save_config,
    _sse,
    _within,
)


def _seed_config(configs_dir: Path, username: str, data: dict | None = None) -> None:
    configs_dir.mkdir(parents=True, exist_ok=True)
    (configs_dir / f"{username}.config").write_text(json.dumps(data or {}), encoding="utf-8")


class TestSecurity:
    def test_safe_username_accepts_existing_user(self, tmp_path: Path) -> None:
        _seed_config(tmp_path, "alice")
        assert _safe_username("alice", configs_dir=tmp_path) == "alice"

    def test_safe_username_rejects_unknown_user(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        assert _safe_username("ghost", configs_dir=tmp_path) is None

    def test_safe_username_strips_traversal(self, tmp_path: Path) -> None:
        # secure_filename collapses traversal; the collapsed name has no config.
        assert _safe_username("../../etc/passwd", configs_dir=tmp_path) is None

    def test_within_true_for_contained_path(self, tmp_path: Path) -> None:
        assert _within(tmp_path / "configs" / "a.config", tmp_path) is True

    def test_within_false_for_escaping_path(self, tmp_path: Path) -> None:
        assert _within(tmp_path / ".." / "outside", tmp_path) is False


class TestConfigIo:
    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        assert _load_config("alice", configs_dir=tmp_path) == {}

    def test_save_then_load_roundtrip(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        _save_config("alice", {"name": "Alice"}, configs_dir=tmp_path)
        assert _load_config("alice", configs_dir=tmp_path) == {"name": "Alice"}

    def test_load_sanitizes_traversal_at_helper(self, tmp_path: Path) -> None:
        # PX-21: containment holds at the helper, not just the call site. A config
        # sitting OUTSIDE configs_dir must be unreachable via a traversal username:
        # secure_filename collapses "../secret" -> "secret", so the read stays in
        # configs_dir and finds nothing there.
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (tmp_path / "secret.config").write_text(json.dumps({"k": "leak"}), encoding="utf-8")
        assert _load_config("../secret", configs_dir=configs_dir) == {}

    def test_save_rejects_all_stripped_username(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="unsafe username"):
            _save_config("...", {"x": 1}, configs_dir=tmp_path)


class TestClients:
    def test_get_client_uses_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        client = _get_client()
        assert client.api_key == "sk-test-key"


class TestHttp:
    def test_sse_frame_format(self) -> None:
        assert _sse("chunk", {"text": "hi"}) == 'event: chunk\ndata: {"text": "hi"}\n\n'

    def test_error_detail_debug_branch_includes_traceback(self) -> None:
        app = Flask(__name__)
        app.debug = True
        with app.test_request_context("/"):
            try:
                raise ValueError("boom")
            except ValueError as exc:
                payload = _error_detail_payload(exc)
        assert "ValueError: boom" in payload["detail"]
        assert len(payload["request_id"]) == 8

    def test_error_detail_production_branch_suppresses_detail(self) -> None:
        app = Flask(__name__)
        app.debug = False
        with app.test_request_context("/"):
            payload = _error_detail_payload(ValueError("boom"))
        assert "detail" not in payload
        assert len(payload["request_id"]) == 8


class TestRequestGates:
    # Note: the gate splits on ":" then matches the head, so an IPv6 *literal*
    # Host ("[::1]") yields "[" and does NOT pass — pre-existing behavior carried
    # verbatim from app.py; the real loopback hosts below are what callers send.
    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "127.0.0.1:5000"])
    def test_localhost_hosts_pass(self, host: str) -> None:
        app = Flask(__name__)
        with app.test_request_context("/", headers={"Host": host}):
            assert _is_localhost_request() is True

    def test_remote_host_fails(self) -> None:
        app = Flask(__name__)
        with app.test_request_context("/", headers={"Host": "evil.example.com"}):
            assert _is_localhost_request() is False


class TestProvisioning:
    def test_provisions_candidate_from_injected_configs_dir(
        self, db_session, tmp_path: Path
    ) -> None:
        from db.models import Candidate

        _seed_config(tmp_path, "alice", {"name": "Alice Example"})
        candidate = _get_or_provision_candidate(db_session, "alice", configs_dir=tmp_path)
        assert candidate is not None
        assert candidate.name == "Alice Example"
        # Idempotent: a second call returns the same row, no duplicate.
        again = _get_or_provision_candidate(db_session, "alice", configs_dir=tmp_path)
        assert again is not None
        assert again.id == candidate.id
        assert db_session.query(Candidate).filter_by(username="alice").count() == 1

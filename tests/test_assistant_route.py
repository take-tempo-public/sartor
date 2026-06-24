"""Integration tests for the assistant SSE route (`blueprints/assistant.py`).

Driven through Flask's `test_client` with retrieval + the avatar LLM stubbed — no git
grep, no API call. They exercise the route's contract: the security gate, request
validation, and the SSE framing (`event: chunk` / `event: done`).
"""

from __future__ import annotations

import pytest

import analyzer
import blueprints.assistant as ba
from app import create_app
from config import Config


def _stub_avatar(client, question, context, *, allow_dev=False, username="", run_id=""):
    yield ("chunk", "Hello ")
    yield ("chunk", "world.")
    yield (
        "done",
        {
            "answer": "Hello world [1] [2].",
            "citations": [
                {
                    "n": 1,
                    "label": "overview",
                    "href": "https://github.com/amodal1/callback/blob/main/docs/wiki/pages/overview.md",
                },
                {
                    "n": 2,
                    "label": "analyzer.py:353",
                    "href": "https://github.com/amodal1/callback/blob/abc123/analyzer.py#L353",
                },
            ],
            "truncated": False,
            "allow_dev": allow_dev,
        },
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Factory-built app: the injected Config points CONFIGS_DIR at tmp_path/configs,
    # which the route reads via current_app.config (Sprint 8.3a — replaces the old
    # monkeypatch of blueprints.assistant.CONFIGS_DIR, which no longer exists).
    cfg = tmp_path / "configs"
    cfg.mkdir()
    (cfg / "testuser.config").write_text("{}", encoding="utf-8")
    # Isolate the route from retrieval + the network. _get_client / _build_sources are
    # module-level names in blueprints.assistant (the imported binding is patchable).
    monkeypatch.setattr(ba, "_build_sources", lambda turns: [])
    monkeypatch.setattr(ba, "_get_client", lambda: None)
    monkeypatch.setattr(analyzer, "avatar_answer_streaming", _stub_avatar)
    return create_app(Config(base_dir=tmp_path)).test_client()


def test_no_username_streams_anonymous(client):
    # 7.8c: the assistant answers without a user selected — the answer is project-global,
    # so a missing username falls back to anonymous telemetry instead of a 400.
    resp = client.post("/api/assistant/ask", json={"question": "hi"})
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/event-stream")
    body = resp.get_data(as_text=True)
    assert "event: chunk" in body
    assert "event: done" in body


def test_missing_question_returns_400(client):
    resp = client.post("/api/assistant/ask", json={"username": "testuser"})
    assert resp.status_code == 400


def test_unknown_user_returns_400(client):
    resp = client.post("/api/assistant/ask", json={"username": "ghost", "question": "hi"})
    assert resp.status_code == 400


def test_valid_request_streams_event_stream(client):
    resp = client.post(
        "/api/assistant/ask",
        json={"username": "testuser", "question": "how does grounding work?"},
    )
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/event-stream")
    body = resp.get_data(as_text=True)
    assert "event: chunk" in body
    assert "event: done" in body
    assert "Hello " in body


def test_done_event_carries_citations(client):
    resp = client.post(
        "/api/assistant/ask",
        json={"username": "testuser", "question": "explain templates"},
    )
    body = resp.get_data(as_text=True)
    # The done payload carries the cited-only footer (label + client-built GitHub href).
    assert "overview" in body
    assert "analyzer.py:353" in body
    assert "github.com" in body


def test_allow_dev_passes_through(client):
    resp = client.post(
        "/api/assistant/ask",
        json={"username": "testuser", "question": "how is the analyzer built?", "allow_dev": True},
    )
    body = resp.get_data(as_text=True)
    assert '"allow_dev": true' in body

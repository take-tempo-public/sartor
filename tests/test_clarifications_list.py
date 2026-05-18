"""Tests for the Phase D.5 candidate-memory list route."""

from __future__ import annotations

import pytest


@pytest.fixture
def memory_app(tmp_path, monkeypatch):
    db_file = tmp_path / "mem.sqlite"
    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None
    import importlib

    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db
    init_db(db_file)
    return app_module


def _seed_candidate(username="alice"):
    from db.models import Candidate
    from db.session import get_session
    s = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def _seed_clarification(candidate_id, question, answer, kind="manual",
                       is_promoted=0, origin_application_id=None):
    from db.models import Clarification
    from db.session import get_session
    s = get_session()
    try:
        c = Clarification(
            candidate_id=candidate_id,
            question=question, answer=answer, kind=kind,
            is_promoted_to_bullet=is_promoted,
            origin_application_id=origin_application_id,
        )
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def _seed_application(candidate_id, title="App", jd_text="JD"):
    import hashlib

    from db.models import Application
    from db.session import get_session
    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id, title=title, jd_text=jd_text,
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


class TestListClarifications:
    def test_empty_for_candidate_with_no_memory(self, memory_app):
        _seed_candidate()
        client = memory_app.app.test_client()
        r = client.get("/api/users/alice/clarifications")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_returns_unpromoted_by_default(self, memory_app):
        cid = _seed_candidate()
        _seed_clarification(cid, "Q1", "A1 without metric")
        _seed_clarification(cid, "Q2", "Already used", is_promoted=1)
        client = memory_app.app.test_client()
        body = client.get("/api/users/alice/clarifications").get_json()
        assert len(body) == 1
        assert body[0]["question"] == "Q1"

    def test_include_promoted_returns_all(self, memory_app):
        cid = _seed_candidate()
        _seed_clarification(cid, "Q1", "A1")
        _seed_clarification(cid, "Q2", "A2", is_promoted=1)
        client = memory_app.app.test_client()
        body = client.get("/api/users/alice/clarifications?include_promoted=1").get_json()
        assert len(body) == 2

    def test_outcome_rich_filter(self, memory_app):
        cid = _seed_candidate()
        _seed_clarification(cid, "Q1", "Reduced latency by 40%")
        _seed_clarification(cid, "Q2", "Mentored peers and helped the team")
        client = memory_app.app.test_client()
        body = client.get(
            "/api/users/alice/clarifications?only_outcome_rich=1",
        ).get_json()
        assert len(body) == 1
        assert body[0]["outcome_rich"] is True
        assert "40%" in body[0]["answer"]

    def test_q_filter_matches_question_or_answer(self, memory_app):
        cid = _seed_candidate()
        _seed_clarification(cid, "Tell me about AI", "Worked on RAG systems")
        _seed_clarification(cid, "What about leadership?", "Led 5 teams")
        client = memory_app.app.test_client()
        body = client.get("/api/users/alice/clarifications?q=rag").get_json()
        assert len(body) == 1
        body = client.get("/api/users/alice/clarifications?q=leadership").get_json()
        assert len(body) == 1

    def test_kind_filter(self, memory_app):
        cid = _seed_candidate()
        _seed_clarification(cid, "Q1", "A1", kind="outcome_probe")
        _seed_clarification(cid, "Q2", "A2", kind="manual")
        client = memory_app.app.test_client()
        body = client.get(
            "/api/users/alice/clarifications?kind=outcome_probe",
        ).get_json()
        assert len(body) == 1
        assert body[0]["kind"] == "outcome_probe"

    def test_origin_application_title_resolved(self, memory_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, title="Senior PM @ Acme")
        _seed_clarification(cid, "Q", "A", origin_application_id=aid)
        client = memory_app.app.test_client()
        body = client.get("/api/users/alice/clarifications").get_json()
        assert body[0]["origin_application_title"] == "Senior PM @ Acme"
        assert body[0]["origin_application_id"] == aid

    def test_invalid_kind_returns_400(self, memory_app):
        _seed_candidate()
        client = memory_app.app.test_client()
        r = client.get("/api/users/alice/clarifications?kind=bogus")
        assert r.status_code == 400

    def test_404_when_candidate_missing(self, memory_app):
        client = memory_app.app.test_client()
        r = client.get("/api/users/alice/clarifications")
        assert r.status_code == 404

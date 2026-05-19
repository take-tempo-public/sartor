"""Tests for POST /api/users/<u>/corpus/ingest-resume (Workstream D).

The route saves the upload, then runs the shared ingest_one_resume which
calls extract_experiences (Haiku). We patch extract_experiences + the
Anthropic client so no API credit is spent; parse_resume on .md is
deterministic and runs for real.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest


@pytest.fixture
def ingest_app(tmp_path, monkeypatch):
    db_file = tmp_path / "ingest.sqlite"
    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None
    import importlib

    import app as app_module
    importlib.reload(app_module)
    for sub in ("configs", "output", "resumes"):
        (tmp_path / sub).mkdir()
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "RESUMES_DIR", tmp_path / "resumes")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db
    init_db(db_file)
    return app_module


def _seed_candidate():
    from db.models import Candidate
    from db.session import get_session
    s = get_session()
    try:
        c = Candidate(username="alice", name="Alice")
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


_FAKE_EXTRACT = [
    {
        "company": "Polaris",
        "location": "Remote",
        "start_date": "2022-01",
        "end_date": None,
        "candidate_inferred_official_title": "Staff Engineer",
        "bullets": [
            {"text": "Shipped the thing", "suggested_tags": ["infra"]},
        ],
    }
]


class TestIngestResume:
    def test_ingests_md_into_corpus_as_pending(self, ingest_app):
        _seed_candidate()
        client = ingest_app.app.test_client()
        with patch("onboarding.extract_experiences.extract_experiences",
                   return_value=_FAKE_EXTRACT), \
             patch.object(ingest_app, "_get_client", return_value=object()):
            r = client.post(
                "/api/users/alice/corpus/ingest-resume",
                data={"file": (io.BytesIO(b"# Resume\n\n## Experience\n\n"
                                          b"- Did things at Polaris"),
                               "r.md")},
                content_type="multipart/form-data",
            )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["experiences_created"] >= 1

        from db.models import Bullet, Experience
        from db.session import get_session
        s = get_session()
        try:
            exps = s.query(Experience).all()
            assert any(e.company == "Polaris" for e in exps)
            # Imported content lands pending-review
            bullets = s.query(Bullet).all()
            assert bullets and all(b.is_pending_review == 1 for b in bullets)
        finally:
            s.close()

    def test_rejects_unsupported_extension(self, ingest_app):
        _seed_candidate()
        client = ingest_app.app.test_client()
        r = client.post(
            "/api/users/alice/corpus/ingest-resume",
            data={"file": (io.BytesIO(b"x"), "evil.exe")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400

    def test_missing_candidate_returns_409_needs_onboarding(self, ingest_app):
        client = ingest_app.app.test_client()
        r = client.post(
            "/api/users/alice/corpus/ingest-resume",
            data={"file": (io.BytesIO(b"# x"), "r.md")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 409
        assert r.get_json()["needs_onboarding"] is True

    def test_unknown_user_400(self, ingest_app):
        client = ingest_app.app.test_client()
        r = client.post(
            "/api/users/ghost/corpus/ingest-resume",
            data={"file": (io.BytesIO(b"# x"), "r.md")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400

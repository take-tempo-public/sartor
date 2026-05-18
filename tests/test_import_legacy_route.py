"""Tests for POST /api/users/<u>/import-legacy (legacy-user DB bridge)."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def imp_app(tmp_path, monkeypatch):
    """Reload app.py + the importer against a temp DB + temp config/output dirs."""
    db_file = tmp_path / "imp.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import importlib

    import app as app_module
    import onboarding.import_legacy as importer
    importlib.reload(app_module)

    configs = tmp_path / "configs"
    output = tmp_path / "output"
    resumes = tmp_path / "resumes"
    for d in (configs, output, resumes):
        d.mkdir()

    monkeypatch.setattr(app_module, "CONFIGS_DIR", configs)
    monkeypatch.setattr(app_module, "OUTPUT_DIR", output)
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    # The importer reads its own module-level dir constants.
    monkeypatch.setattr(importer, "CONFIGS_DIR", configs)
    monkeypatch.setattr(importer, "OUTPUT_DIR", output)
    if hasattr(importer, "RESUMES_DIR"):
        monkeypatch.setattr(importer, "RESUMES_DIR", resumes)

    from db.session import init_db
    init_db(db_file)
    return app_module, tmp_path


def _write_config(tmp_path, username="robert", payload=None):
    cfg = {
        "name": "Robert Cooksey",
        "email": "robert@example.com",
        "linkedin_url": "https://linkedin.com/in/cooksey",
        "skills": ["product", "design"],
        "certifications": [],
        "notes": "- prefers remote",
    }
    if payload:
        cfg.update(payload)
    (tmp_path / "configs" / f"{username}.config").write_text(
        json.dumps(cfg), encoding="utf-8",
    )


class TestImportLegacyRoute:
    def test_creates_candidate_row_from_config(self, imp_app):
        app_module, tmp_path = imp_app
        _write_config(tmp_path)
        client = app_module.app.test_client()

        r = client.post("/api/users/robert/import-legacy", json={})
        assert r.status_code in (200, 201), r.get_json()
        body = r.get_json()
        assert body["candidate_id"] is not None

        # Candidate row really landed
        from db.models import Candidate
        from db.session import get_session
        s = get_session()
        try:
            row = s.query(Candidate).filter_by(username="robert").first()
            assert row is not None
            assert row.name == "Robert Cooksey"
        finally:
            s.close()

    def test_idempotent_second_call_does_not_duplicate(self, imp_app):
        app_module, tmp_path = imp_app
        _write_config(tmp_path)
        client = app_module.app.test_client()

        client.post("/api/users/robert/import-legacy", json={})
        r2 = client.post("/api/users/robert/import-legacy", json={})
        assert r2.status_code in (200, 201)

        from db.models import Candidate
        from db.session import get_session
        s = get_session()
        try:
            assert s.query(Candidate).filter_by(username="robert").count() == 1
        finally:
            s.close()

    def test_unknown_user_returns_400(self, imp_app):
        app_module, _ = imp_app
        client = app_module.app.test_client()
        r = client.post("/api/users/ghost/import-legacy", json={})
        assert r.status_code == 400

    def test_with_llm_false_does_not_call_importer_llm(self, imp_app):
        """with_llm omitted/false must not trigger resume extraction."""
        app_module, tmp_path = imp_app
        _write_config(tmp_path)
        client = app_module.app.test_client()
        r = client.post("/api/users/robert/import-legacy", json={"with_llm": False})
        assert r.status_code in (200, 201)
        body = r.get_json()
        # No resumes dir content seeded → zero experiences regardless
        assert body["experiences_created"] == 0

    def test_analyze_after_import_no_longer_409(self, imp_app, monkeypatch):
        """End-to-end: importing fixes the needs_onboarding 409 on analyze."""
        app_module, tmp_path = imp_app
        _write_config(tmp_path)
        client = app_module.app.test_client()

        # Before import: analyze should 409 needs_onboarding
        with monkeypatch.context() as m:
            m.setattr(app_module, "_get_client", lambda: object())
            pre = client.post(
                "/api/analyze",
                json={"username": "robert", "job_description": "Senior PM\nJD"},
            )
        assert pre.status_code == 409
        assert pre.get_json()["needs_onboarding"] is True

        # Import the candidate
        client.post("/api/users/robert/import-legacy", json={})

        # After import the candidate exists; analyze gets past the
        # needs_onboarding gate (it may still fail later for other reasons
        # like the mocked LLM, but it must NOT be 409 needs_onboarding).
        fake_analysis = {
            "essential_skills": [], "preferred_skills": [],
            "industry_keywords": [], "hidden_qualities": [],
            "professional_vocabulary": [], "ideal_resume_profile": "x",
            "comparison": {}, "suggestions": [], "keyword_placement": [],
            "ats_improvements": [], "overall_strategy": "x",
        }
        from unittest.mock import patch
        with patch.object(app_module, "analyze", return_value=fake_analysis), \
             patch.object(app_module, "_get_client", return_value=object()):
            post = client.post(
                "/api/analyze",
                json={"username": "robert", "job_description": "Senior PM\nJD"},
            )
        assert post.status_code != 409
        body = post.get_json()
        assert not (body or {}).get("needs_onboarding")

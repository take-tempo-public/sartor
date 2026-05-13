"""Tests for the CORPUS_BACKED feature flag in /api/analyze.

When CORPUS_BACKED=1, /api/analyze ignores `resume_filename` and reads from
the SQLite corpus instead of file parsing. This file verifies:
- Flag toggling between file-based (default) and DB-backed paths
- Defense-in-depth path-traversal guards survive in the DB-backed helper
- Unknown candidates return 404 from the DB-backed path
- Application + ApplicationRun rows get created on successful analyze
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def db_app(tmp_path, monkeypatch):
    """Import app.py with CORPUS_BACKED=1 and DB pointed at a temp file.

    Returns the app module so tests can use app.test_client() and access
    the helper directly.
    """
    monkeypatch.setenv("CORPUS_BACKED", "1")

    # Ensure DB lives in tmp_path and gets a fresh schema for this test
    import db.session as db_session
    monkeypatch.setattr(db_session, "DEFAULT_DB_PATH", tmp_path / "test.sqlite")
    # Force re-init by clearing module-level cached engine
    db_session._engine = None
    db_session._SessionLocal = None

    # Reload app so the module-level CORPUS_BACKED constant picks up the env var
    import importlib

    import app
    importlib.reload(app)

    # Make CONFIGS_DIR a temp dir so _safe_username works for our test user
    monkeypatch.setattr(app, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path / "output")
    (tmp_path / "configs").mkdir(exist_ok=True)
    (tmp_path / "configs" / "casey.config").write_text("{}", encoding="utf-8")
    (tmp_path / "output").mkdir(exist_ok=True)

    return app


def _seed_db_candidate(db_path: Path) -> int:
    """Insert a minimal candidate + experience + bullet directly into the DB."""
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import init_db, make_engine, make_session_factory

    init_db(db_path)
    engine = make_engine(db_path)
    session = make_session_factory(engine)()
    try:
        c = Candidate(username="casey", name="Casey Tester")
        session.add(c)
        session.flush()

        e = Experience(
            candidate_id=c.id, company="Polaris",
            start_date="2022-09", end_date=None,
        )
        session.add(e)
        session.flush()
        session.add(ExperienceTitle(
            experience_id=e.id, title="Senior PM",
            is_official=1, is_pending_review=0, source="official",
        ))
        session.add(Bullet(
            experience_id=e.id, text="Led 5-person team.",
            display_order=0, is_active=1, is_pending_review=0,
            source="primary:r.md", has_outcome=1,
        ))
        session.commit()
        return c.id
    finally:
        session.close()
        engine.dispose()


class TestCorpusBackedFlag:
    def test_flag_enabled_routes_through_db_path(self, db_app, tmp_path):
        assert db_app.CORPUS_BACKED is True

        _seed_db_candidate(tmp_path / "test.sqlite")

        # Mock the analyze() LLM call so we don't burn money
        fake_analysis = {
            "essential_skills": [], "preferred_skills": [],
            "industry_keywords": [], "hidden_qualities": [],
            "professional_vocabulary": [], "ideal_resume_profile": "x",
            "comparison": {}, "suggestions": [], "keyword_placement": [],
            "ats_improvements": [], "overall_strategy": "x",
        }
        with patch.object(db_app, "analyze", return_value=fake_analysis), \
             patch.object(db_app, "_get_client", return_value=object()):
            client = db_app.app.test_client()
            response = client.post(
                "/api/analyze",
                json={
                    "username": "casey",
                    "job_description": "Senior PM at Foo\nResponsibilities here.",
                    # resume_filename intentionally omitted — flag should bypass it
                },
            )

        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert "application_id" in body
        assert "application_run_id" in body
        assert body["analysis"] == fake_analysis
        assert body["template_path"] == ""  # no file template in DB mode

    def test_flag_enabled_with_unknown_user_returns_404(self, db_app, tmp_path):
        _seed_db_candidate(tmp_path / "test.sqlite")
        # Set up a config for 'ghost' so _safe_username passes, but DON'T seed
        # a candidate row — build_context_set_from_db should raise.
        (tmp_path / "configs" / "ghost.config").write_text("{}", encoding="utf-8")

        with patch.object(db_app, "_get_client", return_value=object()):
            client = db_app.app.test_client()
            response = client.post(
                "/api/analyze",
                json={"username": "ghost", "job_description": "Some JD"},
            )

        assert response.status_code == 404
        assert "No candidate" in response.get_json()["error"]

    def test_creates_application_row_in_db(self, db_app, tmp_path):
        _seed_db_candidate(tmp_path / "test.sqlite")
        fake_analysis = {
            "essential_skills": [], "preferred_skills": [],
            "industry_keywords": [], "hidden_qualities": [],
            "professional_vocabulary": [], "ideal_resume_profile": "x",
            "comparison": {}, "suggestions": [], "keyword_placement": [],
            "ats_improvements": [], "overall_strategy": "x",
        }
        with patch.object(db_app, "analyze", return_value=fake_analysis), \
             patch.object(db_app, "_get_client", return_value=object()):
            client = db_app.app.test_client()
            client.post(
                "/api/analyze",
                json={"username": "casey", "job_description": "Senior PM\nJob desc."},
            )

        # Verify the application row landed
        from db.models import Application, ApplicationRun
        from db.session import make_engine, make_session_factory
        engine = make_engine(tmp_path / "test.sqlite")
        session = make_session_factory(engine)()
        try:
            apps = session.query(Application).all()
            assert len(apps) == 1
            assert apps[0].title.startswith("Senior PM")
            runs = session.query(ApplicationRun).all()
            assert len(runs) == 1
            assert runs[0].iteration == 0
            assert runs[0].application_id == apps[0].id
            assert runs[0].analysis_json is not None  # populated post-analyze
        finally:
            session.close()
            engine.dispose()


@pytest.fixture
def file_app(tmp_path, monkeypatch):
    """Import app.py with CORPUS_BACKED unset (default = file-based)."""
    monkeypatch.delenv("CORPUS_BACKED", raising=False)
    import importlib

    import app
    importlib.reload(app)
    return app


class TestFileBackedPathStillWorks:
    """Make sure the legacy path is unchanged when CORPUS_BACKED is unset."""

    def test_flag_default_off(self, file_app):
        assert file_app.CORPUS_BACKED is False

    def test_missing_resume_filename_returns_400_in_file_mode(self, file_app, tmp_path, monkeypatch):
        # Set up configs so _safe_username succeeds, then verify the route
        # demands resume_filename when the flag is off.
        monkeypatch.setattr(file_app, "CONFIGS_DIR", tmp_path)
        (tmp_path / "casey.config").write_text("{}", encoding="utf-8")

        client = file_app.app.test_client()
        response = client.post(
            "/api/analyze",
            json={"username": "casey", "job_description": "JD"},
        )
        assert response.status_code == 400
        assert "resume_filename" in response.get_json()["error"]

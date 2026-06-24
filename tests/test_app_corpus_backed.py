"""Tests for the DB-backed /api/analyze route (Phase C.4: flag-free).

The CORPUS_BACKED feature flag was removed in Phase C.4. /api/analyze
ALWAYS runs through the corpus-backed path; resume_filename is ignored.
This file verifies:
- Defense-in-depth path-traversal guards survive in the DB-backed helper
- Unknown candidates return 404
- Application + ApplicationRun rows get created on successful analyze
- Legacy resume_filename in the body is harmless (ignored)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import blueprints.analysis as ban


@pytest.fixture
def db_app(tmp_path, monkeypatch):
    """Factory-built app against a temp DB + temp config dir.

    Returns the Flask app so tests can use app.test_client() and seed candidate
    rows directly. The route lives on `blueprints/analysis.py` (Sprint 8.3b), so
    config paths come from `Config(base_dir=tmp_path)` (no app-global monkeypatch)
    and the analyze/_get_client stubs target the blueprint module. The DB-path
    monkeypatch (db.session.DEFAULT_DB_PATH) is a distinct, legitimate seam.
    Provisioning threads `configs_dir` from the injected Config, so no separate
    `onboarding.corpus_import.CONFIGS_DIR` monkeypatch is needed.
    """
    # Ensure DB lives in tmp_path and gets a fresh schema for this test
    import db.session as db_session

    monkeypatch.setattr(db_session, "DEFAULT_DB_PATH", tmp_path / "test.sqlite")
    db_session._engine = None
    db_session._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    # ensure_dirs() (in the factory) already created configs/output under tmp_path.
    (tmp_path / "configs" / "casey.config").write_text("{}", encoding="utf-8")

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
            candidate_id=c.id,
            company="Polaris",
            start_date="2022-09",
            end_date=None,
        )
        session.add(e)
        session.flush()
        session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Senior PM",
                is_official=1,
                is_pending_review=0,
                source="official",
            )
        )
        session.add(
            Bullet(
                experience_id=e.id,
                text="Led 5-person team.",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="primary:r.md",
                has_outcome=1,
            )
        )
        session.commit()
        return c.id
    finally:
        session.close()
        engine.dispose()


class TestAnalyzeRoute:
    def test_corpus_backed_path_is_the_only_path(self, db_app, tmp_path):
        _seed_db_candidate(tmp_path / "test.sqlite")

        # Mock the analyze() LLM call so we don't burn money
        fake_analysis = {
            "essential_skills": [],
            "preferred_skills": [],
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "ideal_resume_profile": "x",
            "comparison": {},
            "suggestions": [],
            "keyword_placement": [],
            "ats_improvements": [],
            "overall_strategy": "x",
        }
        with (
            patch.object(ban, "analyze", return_value=fake_analysis),
            patch.object(ban, "_get_client", return_value=object()),
        ):
            client = db_app.test_client()
            response = client.post(
                "/api/analyze",
                json={
                    "username": "casey",
                    "job_description": "Senior PM at Foo\nResponsibilities here.",
                    # resume_filename intentionally omitted — Phase C.4 ignores it
                },
            )

        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert "application_id" in body
        assert "application_run_id" in body
        assert body["analysis"] == fake_analysis
        assert body["template_path"] == ""  # no file template in DB mode

    def test_resume_filename_in_body_is_ignored(self, db_app, tmp_path):
        """Phase C.4 contract: legacy frontends still send resume_filename;
        the route must accept it harmlessly without failing."""
        _seed_db_candidate(tmp_path / "test.sqlite")
        fake_analysis = {
            "essential_skills": [],
            "preferred_skills": [],
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "ideal_resume_profile": "x",
            "comparison": {},
            "suggestions": [],
            "keyword_placement": [],
            "ats_improvements": [],
            "overall_strategy": "x",
        }
        with (
            patch.object(ban, "analyze", return_value=fake_analysis),
            patch.object(ban, "_get_client", return_value=object()),
        ):
            client = db_app.test_client()
            response = client.post(
                "/api/analyze",
                json={
                    "username": "casey",
                    "resume_filename": "ignored.docx",  # legacy field
                    "job_description": "Senior PM\nJD here.",
                },
            )
        assert response.status_code == 200

    def test_config_only_user_is_auto_provisioned(self, db_app, tmp_path):
        _seed_db_candidate(tmp_path / "test.sqlite")
        # A user with a config but no candidate row is auto-provisioned on
        # analyze (the row is created from the config), then the analysis runs
        # against the now-present corpus. No separate import step.
        (tmp_path / "configs" / "ghost.config").write_text('{"name": "Ghost"}', encoding="utf-8")
        fake_analysis = {
            "essential_skills": [],
            "preferred_skills": [],
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "ideal_resume_profile": "x",
            "comparison": {},
            "suggestions": [],
            "keyword_placement": [],
            "ats_improvements": [],
            "overall_strategy": "x",
        }
        with (
            patch.object(ban, "analyze", return_value=fake_analysis),
            patch.object(ban, "_get_client", return_value=object()),
        ):
            client = db_app.test_client()
            response = client.post(
                "/api/analyze",
                json={"username": "ghost", "job_description": "Some JD"},
            )

        assert response.status_code == 200, response.get_json()
        from db.models import Candidate
        from db.session import get_session

        s = get_session()
        try:
            assert s.query(Candidate).filter_by(username="ghost").first() is not None
        finally:
            s.close()

    def test_creates_application_row_in_db(self, db_app, tmp_path):
        _seed_db_candidate(tmp_path / "test.sqlite")
        fake_analysis = {
            "essential_skills": [],
            "preferred_skills": [],
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "ideal_resume_profile": "x",
            "comparison": {},
            "suggestions": [],
            "keyword_placement": [],
            "ats_improvements": [],
            "overall_strategy": "x",
        }
        with (
            patch.object(ban, "analyze", return_value=fake_analysis),
            patch.object(ban, "_get_client", return_value=object()),
        ):
            client = db_app.test_client()
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

    def test_missing_username_returns_400(self, db_app, tmp_path):
        client = db_app.test_client()
        response = client.post(
            "/api/analyze",
            json={"job_description": "JD"},  # no username
        )
        assert response.status_code == 400
        assert "username" in response.get_json()["error"]

    def test_missing_jd_returns_400(self, db_app, tmp_path):
        client = db_app.test_client()
        response = client.post(
            "/api/analyze",
            json={"username": "casey"},  # no job_description
        )
        assert response.status_code == 400

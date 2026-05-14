"""Tests for the Phase D.3 application list routes."""

from __future__ import annotations

import pytest


@pytest.fixture
def app_app(tmp_path, monkeypatch):
    """Reload app.py against a fresh sqlite DB + temp config dir."""
    db_file = tmp_path / "apps.sqlite"
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


def _seed_application(candidate_id, title="Senior PM @ Foo", company="Foo Inc",
                     jd_text="Long JD text here.", status="draft"):
    import hashlib

    from db.models import Application
    from db.session import get_session
    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id, title=title, company=company,
            jd_text=jd_text, status=status,
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


def _seed_run(application_id, iteration=0, run_id="abc123def456",
              generated_resume_md=None, ats_roundtrip_json=None):
    from db.models import ApplicationRun
    from db.session import get_session
    s = get_session()
    try:
        r = ApplicationRun(
            application_id=application_id, iteration=iteration,
            run_id=run_id, prompt_version="2026-05-12.1",
            corpus_snapshot_json="{}",
            generated_resume_md=generated_resume_md,
            ats_roundtrip_json=ats_roundtrip_json,
        )
        s.add(r)
        s.commit()
        return r.id
    finally:
        s.close()


def _seed_pending_proposal(application_run_id, bullet_id=None,
                          experience_title_id=None):
    """Seed a pending proposal_review row. Requires that exactly one of
    bullet_id or experience_title_id is non-null (CHECK constraint)."""
    from db.models import ProposalReview
    from db.session import get_session
    s = get_session()
    try:
        p = ProposalReview(
            application_run_id=application_run_id,
            bullet_id=bullet_id,
            experience_title_id=experience_title_id,
            original_text="proposed text",
            decision="pending",
        )
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()


def _seed_bullet_for_proposals(candidate_id):
    """Make a bullet so proposal_review.bullet_id has a real FK target."""
    from db.models import Bullet, Experience
    from db.session import get_session
    s = get_session()
    try:
        e = Experience(candidate_id=candidate_id, company="X",
                       start_date="2020-01", display_order=0)
        s.add(e)
        s.flush()
        b = Bullet(experience_id=e.id, text="bullet", display_order=0,
                   is_active=1, source="manual", has_outcome=0)
        s.add(b)
        s.commit()
        return b.id
    finally:
        s.close()


# ---------------------------------------------------------------------------
# GET /api/users/<u>/applications
# ---------------------------------------------------------------------------


class TestListApplications:
    def test_returns_empty_for_candidate_with_no_apps(self, app_app):
        _seed_candidate()
        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_returns_all_apps_sorted_by_updated_at_desc(self, app_app):
        cid = _seed_candidate()
        a1 = _seed_application(cid, title="App 1")
        a2 = _seed_application(cid, title="App 2", jd_text="Different JD")
        _seed_run(a1, iteration=0)
        _seed_run(a1, iteration=1, run_id="abc123def457")

        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        body = r.get_json()
        assert len(body) == 2
        # Both apps present, with iteration counts
        app1 = next(a for a in body if a["id"] == a1)
        app2 = next(a for a in body if a["id"] == a2)
        assert app1["iteration_count"] == 2
        assert app1["latest_iteration"] == 1
        assert app2["iteration_count"] == 0
        assert app2["latest_iteration"] == 0

    def test_pending_proposal_count(self, app_app):
        cid = _seed_candidate()
        bid = _seed_bullet_for_proposals(cid)
        aid = _seed_application(cid)
        rid = _seed_run(aid)
        _seed_pending_proposal(rid, bullet_id=bid)
        _seed_pending_proposal(rid, bullet_id=bid)

        client = app_app.app.test_client()
        body = client.get("/api/users/alice/applications").get_json()
        assert body[0]["pending_proposals"] == 2

    def test_404_when_candidate_missing(self, app_app):
        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 404

    def test_400_when_user_unknown(self, app_app):
        client = app_app.app.test_client()
        r = client.get("/api/users/ghost/applications")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/applications/<id>
# ---------------------------------------------------------------------------


class TestGetApplication:
    def test_returns_full_detail_with_runs(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, title="Senior PM @ Foo",
                                jd_text="JD content here")
        _seed_run(aid, iteration=0, generated_resume_md="# Resume")
        _seed_run(aid, iteration=1, run_id="abc123def458",
                  ats_roundtrip_json='{"status": "pass"}')

        client = app_app.app.test_client()
        r = client.get(f"/api/applications/{aid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["title"] == "Senior PM @ Foo"
        assert body["jd_text"] == "JD content here"
        assert body["candidate_username"] == "alice"
        assert len(body["runs"]) == 2
        assert body["runs"][0]["iteration"] == 0
        assert body["runs"][0]["has_resume"] is True
        assert body["runs"][1]["ats_roundtrip_status"] == "pass"

    def test_404_for_unknown_id(self, app_app):
        client = app_app.app.test_client()
        r = client.get("/api/applications/99999")
        assert r.status_code == 404

    def test_pending_proposals_per_run(self, app_app):
        cid = _seed_candidate()
        bid = _seed_bullet_for_proposals(cid)
        aid = _seed_application(cid)
        run1 = _seed_run(aid, iteration=0)
        run2 = _seed_run(aid, iteration=1, run_id="run2id123456")
        _seed_pending_proposal(run1, bullet_id=bid)
        _seed_pending_proposal(run2, bullet_id=bid)
        _seed_pending_proposal(run2, bullet_id=bid)

        client = app_app.app.test_client()
        body = client.get(f"/api/applications/{aid}").get_json()
        assert body["runs"][0]["pending_proposals"] == 1
        assert body["runs"][1]["pending_proposals"] == 2


# ---------------------------------------------------------------------------
# PUT /api/applications/<id>/status
# ---------------------------------------------------------------------------


class TestUpdateApplicationStatus:
    def test_promotes_to_submitted(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status",
                       json={"status": "submitted"})
        assert r.status_code == 200
        assert r.get_json()["status"] == "submitted"

    def test_rejects_unknown_status(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status",
                       json={"status": "ghosted"})
        assert r.status_code == 400

    def test_404_for_unknown_id(self, app_app):
        client = app_app.app.test_client()
        r = client.put("/api/applications/99999/status", json={"status": "draft"})
        assert r.status_code == 404

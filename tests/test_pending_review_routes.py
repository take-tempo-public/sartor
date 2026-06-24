"""Tests for the Phase D.6 onboarding-review routes."""

from __future__ import annotations

import pytest


@pytest.fixture
def pr_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir (Sprint 8.3d).

    The accept / pending-counts routes moved to blueprints/corpus/curation and
    read current_app.config at request time, so create_app(Config(base_dir=tmp_path))
    replaces the old reload + monkeypatch-the-globals pattern. The DB-path
    monkeypatch stays.
    """
    db_file = tmp_path / "pr.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db

    init_db(db_file)
    return app


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


def _seed_exp_with_pending(
    candidate_id, n_pending_bullets=2, n_pending_titles=1, n_accepted_bullets=1
):
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id,
            company="Acme",
            start_date="2022-01",
            display_order=0,
        )
        s.add(e)
        s.flush()
        for i in range(n_pending_titles):
            s.add(
                ExperienceTitle(
                    experience_id=e.id,
                    title=f"Title {i}",
                    is_official=0,
                    is_pending_review=1,
                    source="llm_proposed:abc",
                )
            )
        for i in range(n_pending_bullets):
            s.add(
                Bullet(
                    experience_id=e.id,
                    text=f"Pending bullet {i}",
                    display_order=i,
                    is_active=1,
                    is_pending_review=1,
                    source="llm_proposed:abc",
                    has_outcome=0,
                )
            )
        for i in range(n_accepted_bullets):
            s.add(
                Bullet(
                    experience_id=e.id,
                    text=f"Accepted bullet {i}",
                    display_order=n_pending_bullets + i,
                    is_active=1,
                    is_pending_review=0,
                    source="manual",
                    has_outcome=0,
                )
            )
        s.commit()
        return e.id
    finally:
        s.close()


class TestAcceptBullet:
    def test_clears_pending_flag(self, pr_app):
        cid = _seed_candidate()
        eid = _seed_exp_with_pending(cid)
        from db.models import Bullet
        from db.session import get_session

        s = get_session()
        try:
            pending = (
                s.query(Bullet)
                .filter_by(
                    experience_id=eid,
                    is_pending_review=1,
                )
                .first()
            )
            bid = pending.id
        finally:
            s.close()
        client = pr_app.test_client()
        r = client.post(f"/api/bullets/{bid}/accept")
        assert r.status_code == 200
        assert r.get_json()["is_pending_review"] is False
        # confirm at DB
        s = get_session()
        try:
            assert s.query(Bullet).filter_by(id=bid).first().is_pending_review == 0
        finally:
            s.close()

    def test_404_for_unknown_bullet(self, pr_app):
        client = pr_app.test_client()
        r = client.post("/api/bullets/99999/accept")
        assert r.status_code == 404


class TestAcceptTitle:
    def test_clears_pending_flag(self, pr_app):
        cid = _seed_candidate()
        eid = _seed_exp_with_pending(cid)
        from db.models import ExperienceTitle
        from db.session import get_session

        s = get_session()
        try:
            tid = (
                s.query(ExperienceTitle)
                .filter_by(
                    experience_id=eid,
                    is_pending_review=1,
                )
                .first()
                .id
            )
        finally:
            s.close()
        client = pr_app.test_client()
        r = client.post(f"/api/experience-titles/{tid}/accept")
        assert r.status_code == 200
        assert r.get_json()["is_pending_review"] is False


class TestAcceptExperienceAll:
    def test_clears_all_pending_under_experience(self, pr_app):
        cid = _seed_candidate()
        eid = _seed_exp_with_pending(
            cid, n_pending_bullets=3, n_pending_titles=2, n_accepted_bullets=1
        )
        client = pr_app.test_client()
        r = client.post(f"/api/experiences/{eid}/accept-all")
        assert r.status_code == 200
        body = r.get_json()
        assert body["bullets_accepted"] == 3
        assert body["titles_accepted"] == 2
        # confirm no pending left
        from db.models import Bullet, ExperienceTitle
        from db.session import get_session

        s = get_session()
        try:
            pending = (
                s.query(Bullet)
                .filter_by(
                    experience_id=eid,
                    is_pending_review=1,
                    is_active=1,
                )
                .count()
            )
            assert pending == 0
            pending_titles = (
                s.query(ExperienceTitle)
                .filter_by(
                    experience_id=eid,
                    is_pending_review=1,
                )
                .count()
            )
            assert pending_titles == 0
        finally:
            s.close()

    def test_404_for_unknown_experience(self, pr_app):
        client = pr_app.test_client()
        r = client.post("/api/experiences/99999/accept-all")
        assert r.status_code == 404


class TestPendingCounts:
    def test_zero_when_no_pending(self, pr_app):
        _seed_candidate()
        client = pr_app.test_client()
        body = client.get("/api/users/alice/pending-counts").get_json()
        assert body["candidate_present"] is True
        assert body["pending_titles"] == 0
        assert body["pending_bullets"] == 0
        assert body["experiences_with_pending"] == 0

    def test_returns_aggregate_counts(self, pr_app):
        cid = _seed_candidate()
        _seed_exp_with_pending(cid, n_pending_bullets=3, n_pending_titles=2)
        _seed_exp_with_pending(cid, n_pending_bullets=1, n_pending_titles=0)
        client = pr_app.test_client()
        body = client.get("/api/users/alice/pending-counts").get_json()
        assert body["pending_bullets"] == 4
        assert body["pending_titles"] == 2
        assert body["experiences_with_pending"] == 2

    def test_missing_candidate_returns_zeros(self, pr_app):
        # config exists, no candidate row
        client = pr_app.test_client()
        body = client.get("/api/users/alice/pending-counts").get_json()
        assert body["candidate_present"] is False
        assert body["pending_bullets"] == 0

    def test_400_for_unknown_user(self, pr_app):
        client = pr_app.test_client()
        r = client.get("/api/users/ghost/pending-counts")
        assert r.status_code == 400


class TestAcceptAllPendingCorpus:
    """KW2 — corpus-wide accept-all across every experience for a candidate."""

    def test_clears_pending_across_all_experiences(self, pr_app):
        cid = _seed_candidate()
        e1 = _seed_exp_with_pending(
            cid, n_pending_bullets=3, n_pending_titles=2, n_accepted_bullets=1
        )
        e2 = _seed_exp_with_pending(cid, n_pending_bullets=1, n_pending_titles=0)
        client = pr_app.test_client()
        r = client.post("/api/users/alice/accept-all-pending")
        assert r.status_code == 200
        body = r.get_json()
        assert body["bullets_accepted"] == 4
        assert body["titles_accepted"] == 2
        # confirm nothing pending remains under either experience
        from db.models import Bullet, ExperienceTitle
        from db.session import get_session

        s = get_session()
        try:
            for eid in (e1, e2):
                assert (
                    s.query(Bullet)
                    .filter_by(
                        experience_id=eid,
                        is_pending_review=1,
                        is_active=1,
                    )
                    .count()
                    == 0
                )
                assert (
                    s.query(ExperienceTitle)
                    .filter_by(
                        experience_id=eid,
                        is_pending_review=1,
                    )
                    .count()
                    == 0
                )
        finally:
            s.close()

    def test_zero_when_nothing_pending(self, pr_app):
        _seed_candidate()
        client = pr_app.test_client()
        body = client.post("/api/users/alice/accept-all-pending").get_json()
        assert body == {"titles_accepted": 0, "bullets_accepted": 0}

    def test_missing_candidate_returns_zeros(self, pr_app):
        # config exists, no candidate row → no-op, not an error
        client = pr_app.test_client()
        r = client.post("/api/users/alice/accept-all-pending")
        assert r.status_code == 200
        assert r.get_json() == {"titles_accepted": 0, "bullets_accepted": 0}

    def test_400_for_unknown_user(self, pr_app):
        client = pr_app.test_client()
        r = client.post("/api/users/ghost/accept-all-pending")
        assert r.status_code == 400

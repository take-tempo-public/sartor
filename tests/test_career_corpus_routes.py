"""Tests for the Phase D.1 Career Corpus CRUD routes.

Covers list / create / update / delete on experiences, bullets, titles,
plus tag autocomplete. Uses the same fixture pattern as test_persona_routes.py:
in-memory SQLite + per-test app reload + tmp_path config dir.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def corpus_app(tmp_path, monkeypatch):
    """Reload app.py against a fresh sqlite DB + temp config dir."""
    db_file = tmp_path / "corpus.sqlite"

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


def _seed_candidate(username="alice", name="Alice Test"):
    """Insert a candidate row, return its id."""
    from db.models import Candidate
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username=username, name=name)
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


def _seed_experience(candidate_id, company="Polaris", start_date="2022-09",
                     end_date=None, display_order=0):
    """Insert one experience row, return its id."""
    from db.models import Experience
    from db.session import get_session
    session = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id, company=company,
            start_date=start_date, end_date=end_date,
            display_order=display_order,
        )
        session.add(e)
        session.commit()
        return e.id
    finally:
        session.close()


def _seed_title(experience_id, title="Senior PM", is_official=1,
                source="official"):
    from db.models import ExperienceTitle
    from db.session import get_session
    session = get_session()
    try:
        t = ExperienceTitle(
            experience_id=experience_id, title=title,
            is_official=is_official, is_pending_review=0, source=source,
        )
        session.add(t)
        session.commit()
        return t.id
    finally:
        session.close()


def _seed_bullet(experience_id, text="Led 5-person team.", has_outcome=1,
                 source="primary:r.md", display_order=0):
    from db.models import Bullet
    from db.session import get_session
    session = get_session()
    try:
        b = Bullet(
            experience_id=experience_id, text=text,
            display_order=display_order, is_active=1, is_pending_review=0,
            source=source, has_outcome=has_outcome,
        )
        session.add(b)
        session.commit()
        return b.id
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /api/users/<u>/experiences
# ---------------------------------------------------------------------------


class TestListExperiences:
    def test_returns_experiences_for_known_candidate(self, corpus_app):
        cid = _seed_candidate()
        e1 = _seed_experience(cid, company="Polaris", start_date="2022-09")
        e2 = _seed_experience(cid, company="Aurora", start_date="2020-01",
                              end_date="2022-08", display_order=1)
        _seed_title(e1, title="Senior PM")
        _seed_bullet(e1, text="Owned 5 teams shipping AI features.")

        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/experiences")
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        # Sorted by start_date desc — Polaris (2022-09) first
        assert [row["company"] for row in body] == ["Polaris", "Aurora"]
        assert body[0]["official_title"] == "Senior PM"
        assert body[0]["bullet_count_active"] == 1
        assert body[0]["bullet_count_pending"] == 0
        assert body[1]["id"] == e2

    def test_missing_candidate_returns_409_needs_onboarding(self, corpus_app):
        # Config exists, but no candidate row seeded — the route signals
        # needs_onboarding so the UI offers the legacy-import flow.
        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/experiences")
        assert r.status_code == 409
        body = r.get_json()
        assert "corpus" in body["error"].lower()
        assert body["needs_onboarding"] is True

    def test_400_when_user_unknown(self, corpus_app):
        client = corpus_app.app.test_client()
        r = client.get("/api/users/ghost/experiences")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/users/<u>/experiences
# ---------------------------------------------------------------------------


class TestCreateExperience:
    def test_creates_experience_returns_detail(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.post(
            "/api/users/alice/experiences",
            json={
                "company": "Stellar Co",
                "start_date": "2023-01",
                "end_date": "2024-06",
                "location": "Remote",
                "summary": "Built AI tooling",
            },
        )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["company"] == "Stellar Co"
        assert body["start_date"] == "2023-01"
        assert body["end_date"] == "2024-06"
        assert body["location"] == "Remote"
        assert body["summary"] == "Built AI tooling"
        assert body["titles"] == []
        assert body["bullets"] == []

    def test_rejects_missing_company(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.post(
            "/api/users/alice/experiences",
            json={"start_date": "2023-01"},
        )
        assert r.status_code == 400
        assert "company" in r.get_json()["error"]

    def test_rejects_bad_start_date_format(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.post(
            "/api/users/alice/experiences",
            json={"company": "X", "start_date": "January 2023"},
        )
        assert r.status_code == 400
        assert "YYYY-MM" in r.get_json()["error"]

    def test_rejects_bad_end_date_format(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.post(
            "/api/users/alice/experiences",
            json={"company": "X", "start_date": "2023-01", "end_date": "2024"},
        )
        assert r.status_code == 400

    def test_missing_candidate_returns_409_needs_onboarding(self, corpus_app):
        client = corpus_app.app.test_client()
        r = client.post(
            "/api/users/alice/experiences",
            json={"company": "X", "start_date": "2023-01"},
        )
        assert r.status_code == 409
        assert r.get_json()["needs_onboarding"] is True


# ---------------------------------------------------------------------------
# GET / PUT / DELETE /api/experiences/<id>
# ---------------------------------------------------------------------------


class TestGetExperience:
    def test_returns_detail_with_titles_and_bullets(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        _seed_title(eid, title="Senior PM")
        _seed_title(eid, title="Director, AI", is_official=0, source="user_added")
        _seed_bullet(eid, text="Led 5-person team.", display_order=0)
        _seed_bullet(eid, text="Shipped RAG eval framework.", display_order=1)

        client = corpus_app.app.test_client()
        r = client.get(f"/api/experiences/{eid}")
        assert r.status_code == 200
        body = r.get_json()
        # Official title first
        assert body["titles"][0]["is_official"] is True
        assert body["titles"][0]["title"] == "Senior PM"
        assert body["titles"][1]["title"] == "Director, AI"
        # Bullets in display order
        assert [b["text"] for b in body["bullets"]] == [
            "Led 5-person team.",
            "Shipped RAG eval framework.",
        ]

    def test_404_for_unknown_id(self, corpus_app):
        client = corpus_app.app.test_client()
        r = client.get("/api/experiences/99999")
        assert r.status_code == 404


class TestUpdateExperience:
    def test_updates_company_and_dates(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.put(
            f"/api/experiences/{eid}",
            json={"company": "Renamed Co", "end_date": "2024-12"},
        )
        assert r.status_code == 200
        assert r.get_json()["company"] == "Renamed Co"
        assert r.get_json()["end_date"] == "2024-12"

    def test_rejects_empty_company(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.put(f"/api/experiences/{eid}", json={"company": "   "})
        assert r.status_code == 400

    def test_rejects_bad_start_date(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.put(f"/api/experiences/{eid}", json={"start_date": "2024"})
        assert r.status_code == 400


class TestDeleteExperience:
    def test_soft_retires_all_bullets(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        _seed_bullet(eid, display_order=0)
        _seed_bullet(eid, text="another", display_order=1)

        client = corpus_app.app.test_client()
        r = client.delete(f"/api/experiences/{eid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["retired_bullets"] == 2

        # Confirm at DB layer
        from db.models import Bullet
        from db.session import get_session
        s = get_session()
        try:
            active = s.query(Bullet).filter_by(
                experience_id=eid, is_active=1,
            ).count()
            assert active == 0
        finally:
            s.close()


# ---------------------------------------------------------------------------
# POST /api/experiences/<id>/bullets, PUT/DELETE /api/bullets/<id>
# ---------------------------------------------------------------------------


class TestCreateBullet:
    def test_creates_bullet_auto_detects_outcome(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/bullets",
            json={"text": "Reduced latency by 40% across 3 services."},
        )
        assert r.status_code == 201
        body = r.get_json()
        assert body["text"].startswith("Reduced latency")
        assert body["has_outcome"] is True
        assert body["source"] == "manual"
        assert body["is_active"] is True

    def test_creates_bullet_without_outcome(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/bullets",
            json={"text": "Mentored teammates."},
        )
        assert r.status_code == 201
        assert r.get_json()["has_outcome"] is False

    def test_rejects_empty_text(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(f"/api/experiences/{eid}/bullets", json={"text": "   "})
        assert r.status_code == 400

    def test_rejects_unknown_pattern_kind(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/bullets",
            json={"text": "x", "pattern_kind": "bogus"},
        )
        assert r.status_code == 400

    def test_404_for_missing_experience(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.post("/api/experiences/99999/bullets", json={"text": "x"})
        assert r.status_code == 404


class TestUpdateBullet:
    def test_updates_text_and_recomputes_outcome(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        bid = _seed_bullet(eid, text="Mentored team.", has_outcome=0)
        client = corpus_app.app.test_client()
        r = client.put(
            f"/api/bullets/{bid}",
            json={"text": "Mentored team of 8 over 6 months."},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert "8" in body["text"]
        # METRIC_RE picks up "8" / "6 months"
        assert body["has_outcome"] is True

    def test_explicit_has_outcome_overrides_autodetect(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        bid = _seed_bullet(eid)
        client = corpus_app.app.test_client()
        r = client.put(
            f"/api/bullets/{bid}",
            json={"text": "Reduced latency by 40%.", "has_outcome": False},
        )
        assert r.status_code == 200
        # User explicitly overrode it to False — must respect that
        assert r.get_json()["has_outcome"] is False

    def test_rejects_empty_text(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        bid = _seed_bullet(eid)
        client = corpus_app.app.test_client()
        r = client.put(f"/api/bullets/{bid}", json={"text": ""})
        assert r.status_code == 400


class TestDeleteBullet:
    def test_soft_retires_bullet(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        bid = _seed_bullet(eid)
        client = corpus_app.app.test_client()
        r = client.delete(f"/api/bullets/{bid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False

        from db.models import Bullet
        from db.session import get_session
        s = get_session()
        try:
            row = s.query(Bullet).filter_by(id=bid).first()
            assert row is not None  # not hard-deleted
            assert row.is_active == 0
        finally:
            s.close()


# ---------------------------------------------------------------------------
# Title routes
# ---------------------------------------------------------------------------


class TestCreateExperienceTitle:
    def test_creates_non_official_title(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/titles",
            json={"title": "Director, AI Research"},
        )
        assert r.status_code == 201
        body = r.get_json()
        assert body["title"] == "Director, AI Research"
        assert body["is_official"] is False
        assert body["source"] == "user_added"

    def test_setting_is_official_clears_sibling(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        prior = _seed_title(eid, title="Senior PM", is_official=1)

        client = corpus_app.app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/titles",
            json={"title": "Director, AI", "is_official": True},
        )
        assert r.status_code == 201
        assert r.get_json()["is_official"] is True

        # Prior should now be non-official
        from db.models import ExperienceTitle
        from db.session import get_session
        s = get_session()
        try:
            prior_row = s.query(ExperienceTitle).filter_by(id=prior).first()
            assert prior_row.is_official == 0
        finally:
            s.close()

    def test_rejects_empty_title(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.app.test_client()
        r = client.post(f"/api/experiences/{eid}/titles", json={"title": "   "})
        assert r.status_code == 400


class TestUpdateExperienceTitle:
    def test_promote_clears_sibling_official(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        official = _seed_title(eid, title="Senior PM", is_official=1)
        alt = _seed_title(
            eid, title="Director, AI", is_official=0, source="user_added",
        )

        client = corpus_app.app.test_client()
        r = client.put(
            f"/api/experience-titles/{alt}",
            json={"is_official": True},
        )
        assert r.status_code == 200
        assert r.get_json()["is_official"] is True

        from db.models import ExperienceTitle
        from db.session import get_session
        s = get_session()
        try:
            old = s.query(ExperienceTitle).filter_by(id=official).first()
            assert old.is_official == 0
        finally:
            s.close()

    def test_updates_text(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        tid = _seed_title(eid)
        client = corpus_app.app.test_client()
        r = client.put(
            f"/api/experience-titles/{tid}",
            json={"title": "Lead PM, Platform"},
        )
        assert r.status_code == 200
        assert r.get_json()["title"] == "Lead PM, Platform"

    def test_rejects_empty_title(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        tid = _seed_title(eid)
        client = corpus_app.app.test_client()
        r = client.put(f"/api/experience-titles/{tid}", json={"title": ""})
        assert r.status_code == 400


class TestDeleteExperienceTitle:
    def test_marks_non_eligible(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        tid = _seed_title(eid, is_official=1)
        client = corpus_app.app.test_client()
        r = client.delete(f"/api/experience-titles/{tid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["is_official"] is False
        assert body["truthful_enough_to_use"] is False

        from db.models import ExperienceTitle
        from db.session import get_session
        s = get_session()
        try:
            row = s.query(ExperienceTitle).filter_by(id=tid).first()
            assert row is not None  # not hard-deleted
            assert row.is_official == 0
        finally:
            s.close()


# ---------------------------------------------------------------------------
# Tag autocomplete
# ---------------------------------------------------------------------------


def _seed_tag(candidate_id, kind, value, display_value=None, usage_count=0):
    from db.models import Tag
    from db.session import get_session
    s = get_session()
    try:
        t = Tag(
            candidate_id=candidate_id, kind=kind, value=value,
            display_value=display_value or value, usage_count=usage_count,
        )
        s.add(t)
        s.commit()
        return t.id
    finally:
        s.close()


class TestSuggestTags:
    def test_returns_tags_sorted_by_usage_count(self, corpus_app):
        cid = _seed_candidate()
        _seed_tag(cid, "role", "pm", "PM", usage_count=5)
        _seed_tag(cid, "role", "design-mgmt", "Design Mgmt", usage_count=12)
        _seed_tag(cid, "domain", "ai", "AI", usage_count=20)

        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/tags?kind=role")
        assert r.status_code == 200
        body = r.get_json()
        assert len(body) == 2
        # design-mgmt has higher count, should be first
        assert body[0]["value"] == "design-mgmt"
        assert body[1]["value"] == "pm"

    def test_filter_by_prefix(self, corpus_app):
        cid = _seed_candidate()
        _seed_tag(cid, "domain", "ai", "AI")
        _seed_tag(cid, "domain", "ai-platform", "AI Platform")
        _seed_tag(cid, "domain", "fintech", "Fintech")

        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/tags?kind=domain&q=ai")
        assert r.status_code == 200
        body = r.get_json()
        values = {t["value"] for t in body}
        assert values == {"ai", "ai-platform"}

    def test_returns_empty_for_unseeded_candidate(self, corpus_app):
        # Config exists, no candidate row — should return [] not 404
        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/tags")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_400_for_invalid_kind(self, corpus_app):
        _seed_candidate()
        client = corpus_app.app.test_client()
        r = client.get("/api/users/alice/tags?kind=bogus")
        assert r.status_code == 400

    def test_400_for_unknown_user(self, corpus_app):
        client = corpus_app.app.test_client()
        r = client.get("/api/users/ghost/tags")
        assert r.status_code == 400

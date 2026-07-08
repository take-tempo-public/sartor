"""Tests for the Education + Certification Corpus Item CRUD routes (F-04, UX-W1).

Education and Certification are candidate-level (no Experience hop), mirroring
Skill's shape (active / display_order / candidate-scoped CRUD) but WITHOUT the
pending-review/source lifecycle — db/models.py gives neither table a `source`
or `is_pending_review` column. Tests:
  - LIST active by default; ?include_inactive=1 includes soft-retired rows
  - CREATE happy path (display_order auto-incremented, candidate
    auto-provisioned from config on first write); required-field 400
  - UPDATE fields incl. display_order (the "reorder" semantics F-04 asked
    route/unit tests to cover); empty required-field 400; unknown id 404
  - DELETE: always soft-retires (is_active=0) — never hard-deleted
  - Ownership/containment: a row's candidate must pass _safe_username against
    the request's configs_dir, mirroring skills.py's 403 shape
"""

from __future__ import annotations

import pytest


@pytest.fixture
def career_asset_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir, mirroring skill_app
    in test_skill_corpus_item_routes.py (same seam: blueprints/corpus)."""
    db_file = tmp_path / "career_assets.sqlite"

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "casey.config").write_text("{}", encoding="utf-8")

    from db.session import init_db

    init_db(db_file)
    return app


def _seed_candidate(username="casey"):
    from db.models import Candidate
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


def _add_education(candidate_id, institution="State University", *, is_active=1, display_order=0):
    from db.models import Education
    from db.session import get_session

    session = get_session()
    try:
        ed = Education(
            candidate_id=candidate_id,
            institution=institution,
            is_active=is_active,
            display_order=display_order,
        )
        session.add(ed)
        session.commit()
        return ed.id
    finally:
        session.close()


def _add_certification(candidate_id, name="AWS SA", *, is_active=1, display_order=0):
    from db.models import Certification
    from db.session import get_session

    session = get_session()
    try:
        c = Certification(
            candidate_id=candidate_id,
            name=name,
            is_active=is_active,
            display_order=display_order,
        )
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


class TestEducationList:
    def test_active_by_default(self, career_asset_app):
        cid = _seed_candidate()
        _add_education(cid, "State University")
        _add_education(cid, "Retired College", is_active=0, display_order=1)
        client = career_asset_app.test_client()
        r = client.get("/api/users/casey/education")
        assert r.status_code == 200
        names = [e["institution"] for e in r.get_json()["education"]]
        assert names == ["State University"]

    def test_include_inactive(self, career_asset_app):
        cid = _seed_candidate()
        _add_education(cid, "State University")
        _add_education(cid, "Retired College", is_active=0, display_order=1)
        client = career_asset_app.test_client()
        r = client.get("/api/users/casey/education?include_inactive=1")
        names = {e["institution"] for e in r.get_json()["education"]}
        assert names == {"State University", "Retired College"}

    def test_unknown_user_rejected(self, career_asset_app):
        client = career_asset_app.test_client()
        r = client.get("/api/users/nobody/education")
        assert r.status_code == 400

    def test_no_candidate_row_yet_empty(self, career_asset_app):
        # A config exists ("casey") but no Candidate DB row: 200 + empty list,
        # not a 404/409 — matches the needs_onboarding pre-provision state.
        client = career_asset_app.test_client()
        r = client.get("/api/users/casey/education")
        assert r.status_code == 200
        assert r.get_json()["education"] == []


class TestEducationCreate:
    def test_happy_path_provisions_candidate(self, career_asset_app):
        # No candidate row seeded up front — POST auto-provisions via
        # _get_or_provision_candidate, matching create_skill's behavior.
        client = career_asset_app.test_client()
        r = client.post(
            "/api/users/casey/education",
            json={
                "institution": "MIT",
                "degree": "B.S. CS",
                "start_date": "2018",
                "end_date": "2022",
            },
        )
        assert r.status_code == 201, r.get_data(as_text=True)
        body = r.get_json()
        assert body["institution"] == "MIT"
        assert body["degree"] == "B.S. CS"
        assert body["display_order"] == 0
        assert body["is_active"] is True

    def test_second_entry_increments_display_order(self, career_asset_app):
        cid = _seed_candidate()
        _add_education(cid, "First University")
        client = career_asset_app.test_client()
        r = client.post("/api/users/casey/education", json={"institution": "Second College"})
        assert r.get_json()["display_order"] == 1

    def test_missing_institution_400(self, career_asset_app):
        _seed_candidate()
        client = career_asset_app.test_client()
        r = client.post("/api/users/casey/education", json={"institution": "   "})
        assert r.status_code == 400


class TestEducationUpdate:
    def test_update_fields(self, career_asset_app):
        cid = _seed_candidate()
        eid = _add_education(cid, "State University")
        client = career_asset_app.test_client()
        r = client.put(f"/api/education/{eid}", json={"degree": "M.S.", "field": "Physics"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["degree"] == "M.S."
        assert body["field"] == "Physics"

    def test_display_order_reorder_semantics(self, career_asset_app):
        cid = _seed_candidate()
        first = _add_education(cid, "First University", display_order=0)
        second = _add_education(cid, "Second College", display_order=1)
        client = career_asset_app.test_client()
        # Swap: mirrors the frontend's _reorderCorpusRow — PUT both rows'
        # new display_order values.
        r1 = client.put(f"/api/education/{first}", json={"display_order": 1})
        r2 = client.put(f"/api/education/{second}", json={"display_order": 0})
        assert r1.status_code == 200 and r2.status_code == 200
        listed = client.get("/api/users/casey/education").get_json()["education"]
        assert [e["institution"] for e in listed] == ["Second College", "First University"]

    def test_empty_institution_rejected(self, career_asset_app):
        cid = _seed_candidate()
        eid = _add_education(cid, "State University")
        client = career_asset_app.test_client()
        r = client.put(f"/api/education/{eid}", json={"institution": ""})
        assert r.status_code == 400

    def test_unknown_id_404(self, career_asset_app):
        _seed_candidate()
        client = career_asset_app.test_client()
        r = client.put("/api/education/9999", json={"institution": "X"})
        assert r.status_code == 404

    def test_ownership_check_rejects_unsafe_candidate(self, career_asset_app, tmp_path):
        # The row's candidate config no longer exists in configs_dir ->
        # _safe_username fails -> 403 (mirrors skills.py's containment check).
        cid = _seed_candidate()
        eid = _add_education(cid, "State University")
        (tmp_path / "configs" / "casey.config").unlink()
        client = career_asset_app.test_client()
        r = client.put(f"/api/education/{eid}", json={"degree": "M.S."})
        assert r.status_code == 403


class TestEducationDelete:
    def test_soft_retired_never_hard_deleted(self, career_asset_app):
        from db.models import Education
        from db.session import get_session

        cid = _seed_candidate()
        eid = _add_education(cid, "State University")
        client = career_asset_app.test_client()
        r = client.delete(f"/api/education/{eid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False
        session = get_session()
        try:
            row = session.query(Education).filter_by(id=eid).first()
            assert row is not None and row.is_active == 0  # present, just retired
        finally:
            session.close()

    def test_unknown_id_404(self, career_asset_app):
        _seed_candidate()
        client = career_asset_app.test_client()
        r = client.delete("/api/education/9999")
        assert r.status_code == 404


class TestCertificationList:
    def test_active_by_default(self, career_asset_app):
        cid = _seed_candidate()
        _add_certification(cid, "AWS SA")
        _add_certification(cid, "Retired Cert", is_active=0, display_order=1)
        client = career_asset_app.test_client()
        r = client.get("/api/users/casey/certifications")
        names = [c["name"] for c in r.get_json()["certifications"]]
        assert names == ["AWS SA"]

    def test_include_inactive(self, career_asset_app):
        cid = _seed_candidate()
        _add_certification(cid, "AWS SA")
        _add_certification(cid, "Retired Cert", is_active=0, display_order=1)
        client = career_asset_app.test_client()
        r = client.get("/api/users/casey/certifications?include_inactive=1")
        names = {c["name"] for c in r.get_json()["certifications"]}
        assert names == {"AWS SA", "Retired Cert"}


class TestCertificationCreate:
    def test_happy_path(self, career_asset_app):
        client = career_asset_app.test_client()
        r = client.post(
            "/api/users/casey/certifications",
            json={"name": "AWS Certified Solutions Architect", "issuer": "AWS", "issued": "2023"},
        )
        assert r.status_code == 201, r.get_data(as_text=True)
        body = r.get_json()
        assert body["name"] == "AWS Certified Solutions Architect"
        assert body["issuer"] == "AWS"
        assert body["display_order"] == 0

    def test_missing_name_400(self, career_asset_app):
        _seed_candidate()
        client = career_asset_app.test_client()
        r = client.post("/api/users/casey/certifications", json={"name": ""})
        assert r.status_code == 400


class TestCertificationUpdate:
    def test_display_order_reorder_semantics(self, career_asset_app):
        cid = _seed_candidate()
        first = _add_certification(cid, "First Cert", display_order=0)
        second = _add_certification(cid, "Second Cert", display_order=1)
        client = career_asset_app.test_client()
        r1 = client.put(f"/api/certifications/{first}", json={"display_order": 1})
        r2 = client.put(f"/api/certifications/{second}", json={"display_order": 0})
        assert r1.status_code == 200 and r2.status_code == 200
        listed = client.get("/api/users/casey/certifications").get_json()["certifications"]
        assert [c["name"] for c in listed] == ["Second Cert", "First Cert"]

    def test_unknown_id_404(self, career_asset_app):
        _seed_candidate()
        client = career_asset_app.test_client()
        r = client.put("/api/certifications/9999", json={"name": "X"})
        assert r.status_code == 404

    def test_ownership_check_rejects_unsafe_candidate(self, career_asset_app, tmp_path):
        cid = _seed_candidate()
        cert_id = _add_certification(cid, "AWS SA")
        (tmp_path / "configs" / "casey.config").unlink()
        client = career_asset_app.test_client()
        r = client.put(f"/api/certifications/{cert_id}", json={"issuer": "AWS"})
        assert r.status_code == 403


class TestCertificationDelete:
    def test_soft_retired_never_hard_deleted(self, career_asset_app):
        from db.models import Certification
        from db.session import get_session

        cid = _seed_candidate()
        cert_id = _add_certification(cid, "AWS SA")
        client = career_asset_app.test_client()
        r = client.delete(f"/api/certifications/{cert_id}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False
        session = get_session()
        try:
            row = session.query(Certification).filter_by(id=cert_id).first()
            assert row is not None and row.is_active == 0
        finally:
            session.close()

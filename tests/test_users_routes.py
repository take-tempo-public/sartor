"""Tests for the users/config seam routes (Sprint 8.3g, blueprints/users.py).

list_users + create_user had no dedicated unit coverage before the seam move
(create_user was only ever exercised indirectly via the wizard). These pin the two
routes on the factory app — in particular create_user's `RESUMES_DIR` write, which
the move swapped from a module global to `current_app.config["RESUMES_DIR"]` and is
the one moved line that was otherwise untested.

Factory-built (`create_app(Config(base_dir=tmp_path))`): no module-global
monkeypatching, every path under tmp_path.
"""

from __future__ import annotations

import hashlib
import json
import types

import pytest


@pytest.fixture
def users_app(tmp_path):
    """Factory app whose Config points every path under tmp_path."""
    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)  # ensure_dirs() makes configs/resumes/output
    return types.SimpleNamespace(
        app=create_app(cfg),
        configs_dir=cfg.configs_dir,
        resumes_dir=cfg.resumes_dir,
    )


class TestListUsers:
    def test_empty_returns_empty_list(self, users_app):
        client = users_app.app.test_client()
        r = client.get("/api/users")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_lists_config_stems(self, users_app):
        (users_app.configs_dir / "alice.config").write_text("{}", encoding="utf-8")
        (users_app.configs_dir / "bob.config").write_text("{}", encoding="utf-8")
        client = users_app.app.test_client()
        r = client.get("/api/users")
        assert r.status_code == 200
        assert sorted(r.get_json()) == ["alice", "bob"]


class TestCreateUser:
    def test_happy_path_writes_config_and_resumes_dir(self, users_app):
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"username": "bob", "name": "Bob"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["username"] == "bob"
        assert body["config"]["name"] == "Bob"
        # The config file lands inside the injected CONFIGS_DIR …
        assert (users_app.configs_dir / "bob.config").exists()
        # … and the per-user resumes dir is created under the injected RESUMES_DIR
        # (this is the line the seam move swapped to current_app.config).
        assert (users_app.resumes_dir / "bob").is_dir()

    def test_missing_username_returns_400(self, users_app):
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"name": "Nobody"})
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_traversal_username_sanitized_and_contained(self, users_app):
        # secure_filename flattens "../../evil" → "evil"; the config + resumes
        # dir land inside the injected dirs, never in a parent directory.
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"username": "../../evil"})
        assert r.status_code == 200
        assert r.get_json()["username"] == "evil"
        assert (users_app.configs_dir / "evil.config").exists()
        assert not (users_app.configs_dir.parent / "evil.config").exists()


# ---------------------------------------------------------------------------
# GET /api/candidates/roster (Wave 2 recruiter tier — UX review F-08 / F-17)
# ---------------------------------------------------------------------------


@pytest.fixture
def roster_app(tmp_path, monkeypatch):
    """Factory app wired to a fresh sqlite DB — candidate_roster reads Candidate
    + Application rows, so (unlike ``users_app`` above) this fixture also points
    ``db.session`` at a temp DB, mirroring ``test_application_routes.py``'s
    ``app_app`` fixture."""
    import db.session as db_session_mod
    from app import create_app
    from config import Config
    from db.session import init_db

    db_file = tmp_path / "roster.sqlite"
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    init_db(db_file)

    return types.SimpleNamespace(app=app, configs_dir=cfg.configs_dir)


def _write_roster_config(configs_dir, username, name=None):
    payload = {"name": name} if name else {}
    (configs_dir / f"{username}.config").write_text(json.dumps(payload), encoding="utf-8")


def _seed_roster_candidate(username, name=None):
    from db.models import Candidate
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username=username, name=name or username.title())
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def _seed_roster_application(
    candidate_id, title="Role", company="Co", status="draft", jd_text="jd"
):
    from db.models import Application
    from db.session import get_session

    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id,
            title=title,
            company=company,
            jd_text=jd_text,
            status=status,
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


def _set_application_column(application_id, **cols):
    """Bypass the ORM (and its onupdate default) via a raw UPDATE — used to pin
    updated_at / is_active deterministically for ordering + filter assertions."""
    from sqlalchemy import text

    from db.session import get_session

    s = get_session()
    try:
        set_clause = ", ".join(f"{k} = :{k}" for k in cols)
        # set_clause is built from **cols keyword names (test-internal callers
        # only, never request input) — not a user-controlled SQL-injection path.
        s.execute(
            text(f"UPDATE application SET {set_clause} WHERE id = :id"),  # noqa: S608
            {**cols, "id": application_id},
        )
        s.commit()
    finally:
        s.close()


_ALL_STATUS_COUNTS_ZERO = {
    "draft": 0,
    "interview": 0,
    "rejected": 0,
    "submitted": 0,
    "withdrawn": 0,
}


class TestCandidateRoster:
    def test_empty_when_no_users(self, roster_app):
        client = roster_app.app.test_client()
        r = client.get("/api/candidates/roster")
        assert r.status_code == 200
        assert r.get_json() == {"candidates": [], "applications": []}

    def test_candidate_with_no_corpus_row(self, roster_app):
        # A config-only candidate (never onboarded) still shows in the roster.
        _write_roster_config(roster_app.configs_dir, "alice", name="Alice A.")
        client = roster_app.app.test_client()
        body = client.get("/api/candidates/roster").get_json()
        assert len(body["candidates"]) == 1
        c = body["candidates"][0]
        assert c["username"] == "alice"
        assert c["name"] == "Alice A."
        assert c["has_corpus"] is False
        assert c["total_applications"] == 0
        assert c["latest_application"] is None
        assert c["status_counts"] == _ALL_STATUS_COUNTS_ZERO
        assert body["applications"] == []

    def test_status_counts_and_latest_application(self, roster_app):
        _write_roster_config(roster_app.configs_dir, "alice", name="Alice A.")
        cid = _seed_roster_candidate("alice", name="Alice A.")
        _seed_roster_application(
            cid, title="Old Role", company="OldCo", status="draft", jd_text="jd1"
        )
        newer_id = _seed_roster_application(
            cid, title="New Role", company="NewCo", status="submitted", jd_text="jd2"
        )
        # Pin the newer row's updated_at unambiguously ahead so "latest" is
        # deterministic regardless of same-second insert timing.
        _set_application_column(newer_id, updated_at="2030-01-01T00:00:00Z")

        client = roster_app.app.test_client()
        body = client.get("/api/candidates/roster").get_json()
        assert len(body["candidates"]) == 1
        c = body["candidates"][0]
        assert c["has_corpus"] is True
        assert c["total_applications"] == 2
        assert c["status_counts"]["draft"] == 1
        assert c["status_counts"]["submitted"] == 1
        assert c["latest_application"]["title"] == "New Role"
        assert c["latest_application"]["company"] == "NewCo"
        assert c["latest_application"]["status"] == "submitted"

        assert {a["title"] for a in body["applications"]} == {"Old Role", "New Role"}
        for a in body["applications"]:
            assert a["candidate_username"] == "alice"
            assert a["candidate_name"] == "Alice A."

    def test_retired_applications_excluded(self, roster_app):
        _write_roster_config(roster_app.configs_dir, "alice")
        cid = _seed_roster_candidate("alice")
        aid = _seed_roster_application(cid, status="rejected")
        _set_application_column(aid, is_active=0)

        client = roster_app.app.test_client()
        body = client.get("/api/candidates/roster").get_json()
        c = body["candidates"][0]
        assert c["total_applications"] == 0
        assert c["latest_application"] is None
        assert body["applications"] == []

    def test_avoids_n_plus_1_query_growth(self, roster_app):
        """N+1 regression guard: the SQL query count must be CONSTANT in the
        number of candidates/applications (one Candidate IN-query + one
        Application IN-query), not linear — mirrors
        test_application_routes.py::TestListApplications::test_avoids_n_plus_1_query_growth.
        """
        from sqlalchemy import event

        from db.session import get_engine

        engine = get_engine()
        counter = {"n": 0}

        def _count(*_args, **_kwargs):
            counter["n"] += 1

        def _count_request():
            counter["n"] = 0
            event.listen(engine, "after_cursor_execute", _count)
            try:
                body = roster_app.app.test_client().get("/api/candidates/roster").get_json()
            finally:
                event.remove(engine, "after_cursor_execute", _count)
            return body, counter["n"]

        def _seed_candidates(n, offset):
            for i in range(offset, offset + n):
                username = f"cand{i}"
                _write_roster_config(roster_app.configs_dir, username)
                cid = _seed_roster_candidate(username)
                _seed_roster_application(cid, title=f"Role {i}", jd_text=f"jd-{i}")

        _seed_candidates(2, 0)
        body_small, q_small = _count_request()
        _seed_candidates(4, 2)  # 6 candidates total
        body_big, q_big = _count_request()

        assert len(body_small["candidates"]) == 2
        assert len(body_big["candidates"]) == 6
        assert len(body_big["applications"]) == 6
        # The fix: query count does NOT grow with the candidate/application count.
        assert q_small == q_big, (q_small, q_big)
        assert q_big <= 6  # absolute ceiling (two IN-queries + engine overhead)

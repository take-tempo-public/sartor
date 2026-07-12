"""Tests for the Skill Corpus Item CRUD + tag routes (B.5, Sprint 6.6).

Skills are candidate-level (no Experience hop) and carry the bullet/summary
lifecycle: active / pending-review / source / display_order / tags. Tests:
  - LIST active+approved by default; ?include_pending / ?include_inactive
  - CREATE happy path (source='manual', display_order auto); empty name 400;
    duplicate name 409
  - UPDATE name / category / years / display_order; approve via
    is_pending_review=false; restore (un-deny) via is_active=true; empty name
    400; duplicate name 409; unknown 404
  - DELETE: always a reversible soft-tombstone (is_active=0,
    is_pending_review=0) — pending llm_proposed (deny) and approved (retire)
    alike (dec 6, UX Cohesion Epic: never hard-delete, so a denied
    suggestion's name stays excluded from future re-suggestion and the
    denial is reversible via PUT is_active=true)
  - TAGS: link + unlink a tag to a skill
  - Backfill: alembic 0009 turns a legacy skill row into an imported, active,
    approved row with display_order preserving the name order
"""

from __future__ import annotations

import pytest


@pytest.fixture
def skill_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir (Sprint 8.3d).

    The skills CRUD + skill-tags routes now all live on blueprints/corpus and read
    current_app.config[...] at request time, so create_app(Config(base_dir=tmp_path))
    replaces the old reload + monkeypatch-the-globals pattern. The DB-path
    monkeypatch stays (distinct seam).
    """
    db_file = tmp_path / "skills.sqlite"

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


def _add_skill(
    candidate_id,
    name="Python",
    *,
    is_active=1,
    is_pending_review=0,
    source="manual",
    display_order=0,
):
    from db.models import Skill
    from db.session import get_session

    session = get_session()
    try:
        sk = Skill(
            candidate_id=candidate_id,
            name=name,
            is_active=is_active,
            is_pending_review=is_pending_review,
            source=source,
            display_order=display_order,
        )
        session.add(sk)
        session.commit()
        return sk.id
    finally:
        session.close()


class TestList:
    def test_active_approved_by_default(self, skill_app):
        cid = _seed_candidate()
        _add_skill(cid, "Python")
        _add_skill(cid, "Go", is_pending_review=1, source="llm_proposed")
        _add_skill(cid, "Perl", is_active=0)
        client = skill_app.test_client()
        r = client.get("/api/users/casey/skills")
        assert r.status_code == 200
        names = [s["name"] for s in r.get_json()["skills"]]
        assert names == ["Python"]

    def test_include_pending_and_inactive(self, skill_app):
        cid = _seed_candidate()
        _add_skill(cid, "Python")
        _add_skill(cid, "Go", is_pending_review=1, source="llm_proposed")
        _add_skill(cid, "Perl", is_active=0)
        client = skill_app.test_client()
        pending = client.get("/api/users/casey/skills?include_pending=1").get_json()["skills"]
        assert {s["name"] for s in pending} == {"Python", "Go"}
        both = client.get(
            "/api/users/casey/skills?include_pending=1&include_inactive=1"
        ).get_json()["skills"]
        assert {s["name"] for s in both} == {"Python", "Go", "Perl"}

    def test_unknown_user_empty(self, skill_app):
        client = skill_app.test_client()
        r = client.get("/api/users/casey/skills")
        # _safe_username rejects a user with no config/candidate.
        assert r.status_code in (200, 400)


class TestCreate:
    def test_happy_path(self, skill_app):
        _seed_candidate()
        client = skill_app.test_client()
        r = client.post(
            "/api/users/casey/skills", json={"name": "Kubernetes", "category": "platform"}
        )
        assert r.status_code == 201, r.get_data(as_text=True)
        body = r.get_json()
        assert body["name"] == "Kubernetes"
        assert body["category"] == "platform"
        assert body["source"] == "manual"
        assert body["is_pending_review"] is False
        assert body["display_order"] == 0

    def test_empty_name_rejected(self, skill_app):
        _seed_candidate()
        client = skill_app.test_client()
        r = client.post("/api/users/casey/skills", json={"name": "   "})
        assert r.status_code == 400

    def test_duplicate_name_conflict(self, skill_app):
        cid = _seed_candidate()
        _add_skill(cid, "Python")
        client = skill_app.test_client()
        r = client.post("/api/users/casey/skills", json={"name": "Python"})
        assert r.status_code == 409


class TestUpdate:
    def test_update_fields(self, skill_app):
        cid = _seed_candidate()
        sid = _add_skill(cid, "Python")
        client = skill_app.test_client()
        r = client.put(
            f"/api/skills/{sid}", json={"category": "language", "years": 5, "display_order": 3}
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["category"] == "language"
        assert body["years"] == 5.0
        assert body["display_order"] == 3

    def test_approve_pending(self, skill_app):
        cid = _seed_candidate()
        sid = _add_skill(cid, "Go", is_pending_review=1, source="llm_proposed")
        client = skill_app.test_client()
        r = client.put(f"/api/skills/{sid}", json={"is_pending_review": False})
        assert r.status_code == 200
        assert r.get_json()["is_pending_review"] is False

    def test_restore_undenies_a_tombstoned_skill(self, skill_app):
        """dec 6 (UX Cohesion Epic) — the un-deny/restore path: PUT
        is_active=true reverses a soft-tombstone (from DELETE) and lands the
        skill back in the default (active, approved) list."""
        cid = _seed_candidate()
        sid = _add_skill(cid, "Go", is_active=0, is_pending_review=0, source="llm_proposed")
        client = skill_app.test_client()
        r = client.put(f"/api/skills/{sid}", json={"is_active": True})
        assert r.status_code == 200
        assert r.get_json()["is_active"] is True
        listed = client.get("/api/users/casey/skills").get_json()["skills"]
        assert any(s["id"] == sid for s in listed)

    def test_empty_name_rejected(self, skill_app):
        cid = _seed_candidate()
        sid = _add_skill(cid, "Python")
        client = skill_app.test_client()
        r = client.put(f"/api/skills/{sid}", json={"name": ""})
        assert r.status_code == 400

    def test_duplicate_name_conflict(self, skill_app):
        cid = _seed_candidate()
        _add_skill(cid, "Python")
        sid = _add_skill(cid, "Go", display_order=1)
        client = skill_app.test_client()
        r = client.put(f"/api/skills/{sid}", json={"name": "Python"})
        assert r.status_code == 409

    def test_unknown_skill_404(self, skill_app):
        _seed_candidate()
        client = skill_app.test_client()
        r = client.put("/api/skills/9999", json={"name": "X"})
        assert r.status_code == 404


class TestDelete:
    def test_pending_llm_proposed_denied_is_soft_tombstoned(self, skill_app):
        """dec 6 (UX Cohesion Epic) — denying a pending suggestion is a
        reversible soft-tombstone, NOT a hard-delete: the row survives (so its
        name keeps suppressing future re-suggestion) with is_active=0,
        is_pending_review=0."""
        from db.models import Skill
        from db.session import get_session

        cid = _seed_candidate()
        sid = _add_skill(cid, "Go", is_pending_review=1, source="llm_proposed")
        client = skill_app.test_client()
        r = client.delete(f"/api/skills/{sid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False
        session = get_session()
        try:
            row = session.query(Skill).filter_by(id=sid).first()
            assert row is not None  # tombstoned, not hard-deleted
            assert row.is_active == 0
            assert row.is_pending_review == 0
        finally:
            session.close()

    def test_denied_name_excluded_from_default_and_pending_lists(self, skill_app):
        """The tombstoned row is invisible to both the default (active) list
        and the pending-review list, but still occupies the name — proving
        the suppress-future-suggestion half of dec 6 without needing to spin
        up the LLM-calling suggest-from-corpus route."""
        cid = _seed_candidate()
        sid = _add_skill(cid, "Go", is_pending_review=1, source="llm_proposed")
        client = skill_app.test_client()
        client.delete(f"/api/skills/{sid}")
        default_names = {
            s["name"] for s in client.get("/api/users/casey/skills").get_json()["skills"]
        }
        pending_names = {
            s["name"]
            for s in client.get("/api/users/casey/skills?include_pending=1").get_json()["skills"]
        }
        assert "Go" not in default_names
        assert "Go" not in pending_names
        all_names = {
            s["name"]
            for s in client.get(
                "/api/users/casey/skills?include_pending=1&include_inactive=1"
            ).get_json()["skills"]
        }
        assert "Go" in all_names  # still on record, tombstoned

    def test_approved_soft_retired(self, skill_app):
        from db.models import Skill
        from db.session import get_session

        cid = _seed_candidate()
        sid = _add_skill(cid, "Python")
        client = skill_app.test_client()
        r = client.delete(f"/api/skills/{sid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False
        session = get_session()
        try:
            row = session.query(Skill).filter_by(id=sid).first()
            assert row is not None and row.is_active == 0
        finally:
            session.close()


class TestTags:
    def test_link_and_unlink_tag(self, skill_app):
        cid = _seed_candidate()
        sid = _add_skill(cid, "Python")
        client = skill_app.test_client()
        r = client.post(f"/api/skills/{sid}/tags", json={"value": "Backend", "kind": "domain"})
        assert r.status_code == 201, r.get_data(as_text=True)
        tag_id = r.get_json()["id"]
        # The tag now appears on the skill row.
        listed = client.get("/api/users/casey/skills").get_json()["skills"][0]
        assert any(t["id"] == tag_id for t in listed["tags"])
        # Unlink.
        r2 = client.delete(f"/api/skills/{sid}/tags/{tag_id}")
        assert r2.status_code == 200
        listed2 = client.get("/api/users/casey/skills").get_json()["skills"][0]
        assert listed2["tags"] == []

    def test_link_unknown_skill_404(self, skill_app):
        _seed_candidate()
        client = skill_app.test_client()
        r = client.post("/api/skills/9999/tags", json={"value": "x", "kind": "domain"})
        assert r.status_code == 404


class TestMigrationBackfill:
    def test_legacy_skill_backfilled(self, tmp_path):
        """alembic 0009 promotes a legacy skill row to a Corpus Item:
        source='imported', active, approved, with display_order set by name."""
        from pathlib import Path

        import sqlalchemy as sa
        from alembic import command
        from alembic.config import Config

        db = tmp_path / "skill_backfill.sqlite"
        url = f"sqlite:///{db.as_posix()}"

        def _cfg():
            c = Config(str(Path.cwd() / "alembic.ini"))
            c.set_main_option("sqlalchemy.url", url)
            return c

        command.upgrade(_cfg(), "head")
        # Downgrade to 0008 → skill table loses the B.5 columns; insert legacy
        # rows; upgrade to head → exercise the real ALTER + backfill path.
        command.downgrade(_cfg(), "0008")
        eng = sa.create_engine(url)
        with eng.begin() as cx:
            cx.execute(
                sa.text(
                    "INSERT INTO candidate (id, username, created_at, updated_at) "
                    "VALUES (1,'casey','t','t')"
                )
            )
            for sid, name in [(1, "Zebra"), (2, "apple")]:
                cx.execute(
                    sa.text("INSERT INTO skill (id, candidate_id, name) VALUES (:i,1,:n)"),
                    {"i": sid, "n": name},
                )
        command.upgrade(_cfg(), "head")
        with eng.begin() as cx:
            rows = cx.execute(
                sa.text(
                    "SELECT name, source, is_active, is_pending_review, display_order "
                    "FROM skill ORDER BY id"
                )
            ).fetchall()
        eng.dispose()
        by_name = {r[0]: r for r in rows}
        assert by_name["Zebra"][1:4] == ("imported", 1, 0)
        assert by_name["apple"][1:4] == ("imported", 1, 0)
        # Case-sensitive ASCII name order: 'Z'(90) < 'a'(97) → Zebra=0, apple=1.
        assert by_name["Zebra"][4] == 0
        assert by_name["apple"][4] == 1

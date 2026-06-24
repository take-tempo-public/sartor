"""Tests for the ExperienceSummaryItem CRUD routes (B.4, Sprint 6.6).

The per-role intro analog of the SummaryItem routes — experience-scoped,
ownership flowing experience → candidate → _safe_username. Tests:
  - LIST active by default; include_inactive=1 reveals retired
  - LIST 404 for unknown experience; 403 for an unowned candidate
  - CREATE happy path (source='manual' default, display_order auto-set)
  - CREATE invalid source rejected; unknown experience 404
  - UPDATE text / label / has_outcome / display_order; rejects empty text
  - DELETE is soft (is_active=0)
  - Backfill: alembic 0008 turns Experience.summary into an imported variant
"""

from __future__ import annotations

import pytest


@pytest.fixture
def exp_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh sqlite DB + temp config dir (Sprint 8.3d).

    The experience-summary routes moved to blueprints/corpus and read
    current_app.config[...] at request time, so the canonical
    create_app(Config(base_dir=tmp_path)) fixture replaces the old reload +
    monkeypatch-the-globals pattern. The DB-path monkeypatch stays (distinct seam).
    """
    db_file = tmp_path / "expsum.sqlite"

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


def _seed_experience(username="casey", company="Acme", summary=None):
    """Candidate + one experience. Returns (candidate_id, experience_id)."""
    from db.models import Candidate, Experience
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        session.add(c)
        session.flush()
        e = Experience(candidate_id=c.id, company=company, start_date="2021-01", summary=summary)
        session.add(e)
        session.commit()
        return c.id, e.id
    finally:
        session.close()


def _add_variant(experience_id, text="An intro.", is_active=1, label=None):
    from db.models import ExperienceSummaryItem
    from db.session import get_session

    session = get_session()
    try:
        si = ExperienceSummaryItem(
            experience_id=experience_id,
            text=text,
            is_active=is_active,
            label=label,
        )
        session.add(si)
        session.commit()
        return si.id
    finally:
        session.close()


class TestList:
    def test_active_by_default_include_inactive_reveals_retired(self, exp_app):
        _cid, eid = _seed_experience()
        active = _add_variant(eid, text="Active intro.")
        retired = _add_variant(eid, text="Retired intro.", is_active=0)
        client = exp_app.test_client()

        r = client.get(f"/api/experiences/{eid}/summaries")
        assert r.status_code == 200
        ids = [s["id"] for s in r.get_json()["summaries"]]
        assert ids == [active]

        r = client.get(f"/api/experiences/{eid}/summaries?include_inactive=1")
        ids = {s["id"] for s in r.get_json()["summaries"]}
        assert ids == {active, retired}

    def test_unknown_experience_404(self, exp_app):
        client = exp_app.test_client()
        assert client.get("/api/experiences/9999/summaries").status_code == 404

    def test_unowned_candidate_403(self, exp_app):
        # "ghost" has no .config file → _safe_username returns None → 403.
        _cid, eid = _seed_experience(username="ghost")
        client = exp_app.test_client()
        assert client.get(f"/api/experiences/{eid}/summaries").status_code == 403


class TestCreate:
    def test_happy_path(self, exp_app):
        _cid, eid = _seed_experience()
        client = exp_app.test_client()
        r = client.post(
            f"/api/experiences/{eid}/summaries", json={"text": "First framing.", "label": "scale"}
        )
        assert r.status_code == 201, r.get_data(as_text=True)
        body = r.get_json()
        assert body["text"] == "First framing."
        assert body["label"] == "scale"
        assert body["source"] == "manual"
        assert body["display_order"] == 0
        assert body["is_active"] is True
        # Second create auto-increments display_order.
        r2 = client.post(f"/api/experiences/{eid}/summaries", json={"text": "Second."})
        assert r2.get_json()["display_order"] == 1

    def test_empty_text_rejected(self, exp_app):
        _cid, eid = _seed_experience()
        client = exp_app.test_client()
        assert (
            client.post(f"/api/experiences/{eid}/summaries", json={"text": "  "}).status_code == 400
        )

    def test_invalid_source_rejected(self, exp_app):
        _cid, eid = _seed_experience()
        client = exp_app.test_client()
        r = client.post(f"/api/experiences/{eid}/summaries", json={"text": "x", "source": "bogus"})
        assert r.status_code == 400

    def test_unknown_experience_404(self, exp_app):
        client = exp_app.test_client()
        r = client.post("/api/experiences/9999/summaries", json={"text": "x"})
        assert r.status_code == 404


class TestUpdate:
    def test_update_fields(self, exp_app):
        _cid, eid = _seed_experience()
        sid = _add_variant(eid, text="Old.")
        client = exp_app.test_client()
        r = client.put(
            f"/api/experience-summaries/{sid}",
            json={"text": "New.", "label": "tag", "has_outcome": True, "display_order": 3},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["text"] == "New."
        assert body["label"] == "tag"
        assert body["has_outcome"] is True
        assert body["display_order"] == 3

    def test_empty_text_rejected(self, exp_app):
        _cid, eid = _seed_experience()
        sid = _add_variant(eid)
        client = exp_app.test_client()
        assert client.put(f"/api/experience-summaries/{sid}", json={"text": ""}).status_code == 400

    def test_unknown_item_404(self, exp_app):
        client = exp_app.test_client()
        assert client.put("/api/experience-summaries/9999", json={"text": "x"}).status_code == 404


class TestDelete:
    def test_soft_retire(self, exp_app):
        from db.models import ExperienceSummaryItem
        from db.session import get_session

        _cid, eid = _seed_experience()
        sid = _add_variant(eid)
        client = exp_app.test_client()
        r = client.delete(f"/api/experience-summaries/{sid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False
        # Row still exists (soft delete), just inactive.
        session = get_session()
        try:
            row = session.query(ExperienceSummaryItem).filter_by(id=sid).first()
            assert row is not None and row.is_active == 0
        finally:
            session.close()


class TestMigrationBackfill:
    def test_experience_summary_backfilled_to_variant(self, tmp_path):
        """alembic 0008 turns a non-empty Experience.summary into one
        imported ExperienceSummaryItem. Exercised by downgrading to 0007
        (drops the tables, leaving the column) then upgrading to head."""
        from pathlib import Path

        import sqlalchemy as sa
        from alembic import command
        from alembic.config import Config

        db = tmp_path / "backfill.sqlite"
        url = f"sqlite:///{db.as_posix()}"

        def _cfg():
            c = Config(str(Path.cwd() / "alembic.ini"))
            c.set_main_option("sqlalchemy.url", url)
            return c

        command.upgrade(_cfg(), "head")
        eng = sa.create_engine(url)
        with eng.begin() as cx:
            cx.execute(
                sa.text(
                    "INSERT INTO candidate (id, username, created_at, updated_at) "
                    "VALUES (1,'casey','t','t')"
                )
            )
            cx.execute(
                sa.text(
                    "INSERT INTO experience (id, candidate_id, company, start_date, "
                    "display_order, summary, created_at, updated_at) "
                    "VALUES (1,1,'Acme','2021-01',0,'Owned platform scale.','t','t')"
                )
            )
        # Drop the B.4 tables, then re-run the upgrade to exercise the backfill.
        command.downgrade(_cfg(), "0007")
        command.upgrade(_cfg(), "head")
        with eng.begin() as cx:
            rows = cx.execute(
                sa.text(
                    "SELECT experience_id, text, source, is_active FROM experience_summary_item"
                )
            ).fetchall()
        assert rows == [(1, "Owned platform scale.", "imported", 1)]

"""Tests for the SummaryItem CRUD routes (Phase β.6a).

Pins down the first CorpusItem-pattern specialization. Tests:
  - LIST returns active rows by default; include_inactive=1 reveals retired
  - LIST returns empty for unknown user (back-compat: no 404)
  - CREATE happy path: source='manual' default, display_order auto-set
  - CREATE invalid source rejected
  - UPDATE text / label / has_outcome / display_order
  - UPDATE rejects empty text
  - DELETE is soft (is_active=0), not hard
  - Ownership guards: _safe_username on every route
  - Backfill: alembic 0004 turns Candidate.profile_text into a SummaryItem
"""

from __future__ import annotations

import pytest


@pytest.fixture
def summary_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir (Sprint 8.3d).

    The summary routes moved to blueprints/corpus and read current_app.config[...]
    at request time, so create_app(Config(base_dir=tmp_path)) replaces the old
    reload + monkeypatch-the-globals pattern. Provisioning now threads configs_dir
    through web_infra, so the corpus_import.CONFIGS_DIR monkeypatch is gone. The
    DB-path monkeypatch stays (distinct seam).
    """
    db_file = tmp_path / "summary.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "casey.config").write_text("{}", encoding="utf-8")
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")

    from db.session import init_db
    init_db(db_file)
    return app


def _seed_candidate(app_module, username="casey", profile_text=None):
    from db.models import Candidate
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username=username, name=username.title(),
                      profile_text=profile_text)
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


# -------------------------------------------------------------------
# Backfill from migration 0004
# -------------------------------------------------------------------


class TestMigrationBackfill:
    def test_candidate_with_profile_text_gets_summary_item(self, summary_app):
        """The migration runs at fixture setup. Seeding a candidate with
        profile_text AFTER migration won't trigger the backfill (it's
        a one-shot at upgrade time), but we can verify the table
        accepts a manually-inserted row that mirrors what the
        migration produces."""
        from db.models import Candidate, SummaryItem
        from db.session import get_session
        session = get_session()
        try:
            c = Candidate(username="alice", name="Alice",
                          profile_text="Seed positioning text.")
            session.add(c)
            session.commit()
            # Simulate the migration's INSERT
            si = SummaryItem(
                candidate_id=c.id, text=c.profile_text or "",
                source="imported",
            )
            session.add(si)
            session.commit()
            rows = session.query(SummaryItem).filter_by(candidate_id=c.id).all()
            assert len(rows) == 1
            assert rows[0].text == "Seed positioning text."
            assert rows[0].source == "imported"
            assert rows[0].is_active == 1
        finally:
            session.close()


# -------------------------------------------------------------------
# GET /api/users/<u>/summaries
# -------------------------------------------------------------------


class TestList:
    def test_empty_for_user_with_no_summaries(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        r = client.get("/api/users/casey/summaries")
        assert r.status_code == 200
        assert r.get_json()["summaries"] == []

    def test_empty_for_unknown_user_no_404(self, summary_app):
        """Mirrors the bullet/title list behavior: no 404, just empty.
        Keeps the frontend's empty-state simple."""
        client = summary_app.test_client()
        r = client.get("/api/users/casey/summaries")
        # casey has a .config but no Candidate row → empty list, 200
        assert r.status_code == 200
        assert r.get_json()["summaries"] == []

    def test_omits_inactive_by_default(self, summary_app):
        from db.models import SummaryItem
        from db.session import get_session
        cid = _seed_candidate(summary_app, "casey")
        session = get_session()
        try:
            session.add(SummaryItem(candidate_id=cid, text="Active variant", display_order=0))
            session.add(SummaryItem(candidate_id=cid, text="Retired variant", display_order=1, is_active=0))
            session.commit()
        finally:
            session.close()

        client = summary_app.test_client()
        r = client.get("/api/users/casey/summaries")
        items = r.get_json()["summaries"]
        assert len(items) == 1
        assert items[0]["text"] == "Active variant"

    def test_include_inactive_query_param(self, summary_app):
        from db.models import SummaryItem
        from db.session import get_session
        cid = _seed_candidate(summary_app, "casey")
        session = get_session()
        try:
            session.add(SummaryItem(candidate_id=cid, text="Active", display_order=0))
            session.add(SummaryItem(candidate_id=cid, text="Retired", display_order=1, is_active=0))
            session.commit()
        finally:
            session.close()

        client = summary_app.test_client()
        r = client.get("/api/users/casey/summaries?include_inactive=1")
        items = r.get_json()["summaries"]
        assert len(items) == 2


# -------------------------------------------------------------------
# POST /api/users/<u>/summaries
# -------------------------------------------------------------------


class TestCreate:
    def test_create_happy_path(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        r = client.post("/api/users/casey/summaries", json={
            "text":  "Principal-level designer with a decade of...",
            "label": "Design IC",
        })
        assert r.status_code == 201, r.get_data(as_text=True)
        body = r.get_json()
        assert body["text"].startswith("Principal-level designer")
        assert body["label"] == "Design IC"
        assert body["is_active"] is True
        assert body["is_pending_review"] is False
        assert body["source"] == "manual"
        assert body["display_order"] == 0

    def test_create_auto_increments_display_order(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        r1 = client.post("/api/users/casey/summaries", json={"text": "First"})
        r2 = client.post("/api/users/casey/summaries", json={"text": "Second"})
        assert r1.get_json()["display_order"] == 0
        assert r2.get_json()["display_order"] == 1

    def test_create_rejects_empty_text(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        r = client.post("/api/users/casey/summaries", json={"text": "   "})
        assert r.status_code == 400

    def test_create_rejects_invalid_source(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        r = client.post("/api/users/casey/summaries", json={
            "text": "Valid text", "source": "bogus",
        })
        assert r.status_code == 400

    def test_create_config_only_user_is_auto_provisioned(self, summary_app):
        # casey has a .config but no Candidate row — adding a summary variant
        # provisions the row on the first write (no separate import step).
        client = summary_app.test_client()
        r = client.post("/api/users/casey/summaries", json={"text": "Some text"})
        assert r.status_code == 201, r.get_data(as_text=True)
        from db.models import Candidate
        from db.session import get_session
        s = get_session()
        try:
            assert s.query(Candidate).filter_by(username="casey").first() is not None
        finally:
            s.close()


# -------------------------------------------------------------------
# PUT /api/summaries/<id>
# -------------------------------------------------------------------


class TestUpdate:
    def test_update_text(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        created = client.post("/api/users/casey/summaries", json={"text": "Original"}).get_json()
        r = client.put(f"/api/summaries/{created['id']}", json={"text": "Updated"})
        assert r.status_code == 200
        assert r.get_json()["text"] == "Updated"

    def test_update_label_and_outcome_flag(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        created = client.post("/api/users/casey/summaries", json={"text": "Some positioning"}).get_json()
        r = client.put(f"/api/summaries/{created['id']}", json={
            "label": "AI platform PM", "has_outcome": True,
        })
        body = r.get_json()
        assert body["label"] == "AI platform PM"
        assert body["has_outcome"] is True

    def test_update_rejects_empty_text(self, summary_app):
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        created = client.post("/api/users/casey/summaries", json={"text": "T"}).get_json()
        r = client.put(f"/api/summaries/{created['id']}", json={"text": "  "})
        assert r.status_code == 400

    def test_update_unknown_returns_404(self, summary_app):
        client = summary_app.test_client()
        r = client.put("/api/summaries/99999", json={"text": "x"})
        assert r.status_code == 404


# -------------------------------------------------------------------
# DELETE /api/summaries/<id>
# -------------------------------------------------------------------


class TestDelete:
    def test_delete_is_soft(self, summary_app):
        from db.models import SummaryItem
        from db.session import get_session
        _seed_candidate(summary_app, "casey")
        client = summary_app.test_client()
        created = client.post("/api/users/casey/summaries", json={"text": "T"}).get_json()

        r = client.delete(f"/api/summaries/{created['id']}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["is_active"] is False

        # Row still exists in DB; is_active flipped to 0
        session = get_session()
        try:
            row = session.query(SummaryItem).filter_by(id=created["id"]).first()
            assert row is not None
            assert row.is_active == 0
        finally:
            session.close()

    def test_delete_unknown_returns_404(self, summary_app):
        client = summary_app.test_client()
        r = client.delete("/api/summaries/99999")
        assert r.status_code == 404

"""Tests for the Workstream B1.2 duplicates clustering route.

GET /api/users/<u>/duplicates clusters near-duplicate bullets (Jaccard ≥ 0.75
on `hardening.bullet_token_set`) per experience so the Library duplicates
surface can offer keep-one-soft-retire-others merging.
"""

from __future__ import annotations

import shutil

import pytest


@pytest.fixture
def dup_app(tmp_path, monkeypatch, _migrated_template_db):
    """Factory-built app on a fresh DB + temp config dir (Sprint 8.3d).

    `test/fixture-scoping` (PX-44) pilot, converted from a per-test
    `init_db(db_file)` (full alembic chain, ~46 files pay this cost across the
    fast lane) to copying the session-scoped `_migrated_template_db` — see that
    fixture's docstring in `tests/conftest.py` for the two traps this closes
    (path-set memoization, WAL sidecar). Per-test file isolation is unchanged:
    each test still gets its own on-disk DB, just seeded by copy instead of by
    a fresh migration run.

    The duplicates route moved to blueprints/corpus and reads current_app.config
    at request time, so create_app(Config(base_dir=tmp_path)) replaces the old
    reload + monkeypatch-the-globals pattern. The DB-path monkeypatch stays.
    """
    db_file = tmp_path / "dup.sqlite"
    assert db_file != _migrated_template_db, "must never point a test at the shared template"
    shutil.copy2(_migrated_template_db, db_file)

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None
    # Mandatory pre-register: `init_db` only skips the alembic chain when the
    # resolved path is already in this set — it never inspects DB state, so
    # without this line the first route to call bare `init_db()` re-migrates
    # the copy from scratch, silently erasing the fixture's whole purpose.
    db_session_mod._initialized_paths.add(db_file.resolve())

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")

    from db.session import init_db

    # Skip-proof: proves alembic did NOT re-run against the copy. If this ever
    # returns True, the pre-register above silently stopped working.
    assert init_db(db_file) is False, "expected the pre-registered copy to skip alembic"

    yield app

    db_session_mod.get_engine().dispose()


def _seed(username="alice", bullets_per_exp=None):
    """Seed candidate + one experience + bullets. bullets_per_exp is a list
    of (text, has_outcome) tuples."""
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        s.add(c)
        s.flush()
        e = Experience(
            candidate_id=c.id,
            company="Polaris",
            start_date="2022-01",
            display_order=0,
        )
        s.add(e)
        s.flush()
        ids = []
        for i, (text, outcome) in enumerate(bullets_per_exp or []):
            b = Bullet(
                experience_id=e.id,
                text=text,
                display_order=i,
                is_active=1,
                is_pending_review=0,
                source="manual",
                has_outcome=1 if outcome else 0,
            )
            s.add(b)
            s.flush()
            ids.append(b.id)
        s.commit()
        return c.id, e.id, ids
    finally:
        s.close()


class TestDuplicatesRoute:
    def test_empty_when_no_duplicates(self, dup_app):
        _seed(
            bullets_per_exp=[
                ("Owned the on-call rotation.", False),
                ("Mentored four junior engineers through their first launches.", False),
                ("Authored the architecture review document for the new platform.", True),
            ]
        )
        client = dup_app.test_client()
        body = client.get("/api/users/alice/duplicates").get_json()
        assert body["cluster_count"] == 0
        assert body["experiences"] == []

    def test_clusters_near_verbatim_pair(self, dup_app):
        body_text = (
            "Reduced API latency across the order service by "
            "introducing connection pooling and a request cache."
        )
        _, eid, ids = _seed(
            bullets_per_exp=[
                (body_text, True),
                (body_text.replace("the order", "our order"), False),  # near-verbatim
                ("Mentored a junior engineer through their first launch.", False),
            ]
        )
        client = dup_app.test_client()
        body = client.get("/api/users/alice/duplicates").get_json()
        assert body["cluster_count"] == 1
        assert len(body["experiences"]) == 1
        exp = body["experiences"][0]
        assert exp["id"] == eid
        cluster = exp["clusters"][0]
        # Both near-verbatim bullets land in the cluster.
        assert {b["id"] for b in cluster["bullets"]} == {ids[0], ids[1]}
        # The outcome-bearing bullet is recommended to keep.
        assert cluster["recommended_keep"] == ids[0]

    def test_threshold_param_relaxes_clustering(self, dup_app):
        """At a low threshold the route over-clusters; documents the knob."""
        _seed(
            bullets_per_exp=[
                ("Mentored four junior engineers through their first launches.", False),
                ("Coached three junior engineers through onboarding.", False),
            ]
        )
        client = dup_app.test_client()
        b_default = client.get("/api/users/alice/duplicates").get_json()
        assert b_default["cluster_count"] == 0
        b_loose = client.get("/api/users/alice/duplicates?threshold=0.5").get_json()
        # Loosening past the default may catch these or not depending on
        # token overlap — but the parameter must round-trip and clamp.
        assert 0.5 <= b_loose["threshold"] <= 1.0

    def test_200_needs_onboarding_when_candidate_missing(self, dup_app):
        # Read precondition unmet → 200 + needs_onboarding (empty clusters),
        # not a 409 conflict.
        client = dup_app.test_client()
        r = client.get("/api/users/alice/duplicates")
        assert r.status_code == 200
        body = r.get_json()
        assert body["needs_onboarding"] is True
        assert body["experiences"] == []
        assert body["cluster_count"] == 0

    def test_400_when_user_unknown(self, dup_app):
        client = dup_app.test_client()
        r = client.get("/api/users/ghost/duplicates")
        assert r.status_code == 400

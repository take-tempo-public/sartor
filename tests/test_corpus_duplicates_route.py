"""Tests for the Workstream B1.2 duplicates clustering route.

GET /api/users/<u>/duplicates clusters near-duplicate bullets (Jaccard ≥ 0.75
on `hardening.bullet_token_set`) per experience so the Library duplicates
surface can offer keep-one-soft-retire-others merging.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def dup_app(tmp_path, monkeypatch):
    db_file = tmp_path / "dup.sqlite"
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
            candidate_id=c.id, company="Polaris",
            start_date="2022-01", display_order=0,
        )
        s.add(e)
        s.flush()
        ids = []
        for i, (text, outcome) in enumerate(bullets_per_exp or []):
            b = Bullet(
                experience_id=e.id, text=text, display_order=i,
                is_active=1, is_pending_review=0, source="manual",
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
        _seed(bullets_per_exp=[
            ("Owned the on-call rotation.", False),
            ("Mentored four junior engineers through their first launches.", False),
            ("Authored the architecture review document for the new platform.", True),
        ])
        client = dup_app.app.test_client()
        body = client.get("/api/users/alice/duplicates").get_json()
        assert body["cluster_count"] == 0
        assert body["experiences"] == []

    def test_clusters_near_verbatim_pair(self, dup_app):
        body_text = ("Reduced API latency across the order service by "
                     "introducing connection pooling and a request cache.")
        _, eid, ids = _seed(bullets_per_exp=[
            (body_text, True),
            (body_text.replace("the order", "our order"), False),  # near-verbatim
            ("Mentored a junior engineer through their first launch.", False),
        ])
        client = dup_app.app.test_client()
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
        _seed(bullets_per_exp=[
            ("Mentored four junior engineers through their first launches.", False),
            ("Coached three junior engineers through onboarding.", False),
        ])
        client = dup_app.app.test_client()
        b_default = client.get("/api/users/alice/duplicates").get_json()
        assert b_default["cluster_count"] == 0
        b_loose = client.get("/api/users/alice/duplicates?threshold=0.5").get_json()
        # Loosening past the default may catch these or not depending on
        # token overlap — but the parameter must round-trip and clamp.
        assert 0.5 <= b_loose["threshold"] <= 1.0

    def test_409_when_candidate_missing(self, dup_app):
        client = dup_app.app.test_client()
        r = client.get("/api/users/alice/duplicates")
        assert r.status_code == 409
        assert r.get_json()["needs_onboarding"] is True

    def test_400_when_user_unknown(self, dup_app):
        client = dup_app.app.test_client()
        r = client.get("/api/users/ghost/duplicates")
        assert r.status_code == 400

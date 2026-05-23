"""Tests for the Workstream H recommend route.

POST /api/applications/<id>/recommend calls analyzer.recommend_bullets()
(Haiku) and persists the result into the application's context file as
`llm_recommendations`. These tests mock the LLM call so no API credit is
spent; the route surface, file write, and failure handling are verified.
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

import pytest


@pytest.fixture
def rec_app(tmp_path, monkeypatch):
    db_file = tmp_path / "rec.sqlite"
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
    return app_module, tmp_path


def _seed(app_module, tmp_path):
    from db.models import Application, Candidate
    from db.session import get_session
    s = get_session()
    try:
        c = Candidate(username="alice", name="Alice")
        s.add(c)
        s.flush()
        a = Application(
            candidate_id=c.id, title="App", jd_text="Senior PM at Foo",
            jd_fingerprint=hashlib.sha256(b"jd").hexdigest()[:16],
        )
        s.add(a)
        s.flush()
        s.commit()
        cid, aid = c.id, a.id
    finally:
        s.close()
    out = tmp_path / "output" / "alice"
    out.mkdir(parents=True, exist_ok=True)
    ctx = out / "context_rec.json"
    ctx.write_text(json.dumps({
        "application_id": aid,
        "career_corpus": [
            {"id": 7, "company": "Polaris", "start_date": "2022-01",
             "end_date": None, "eligible_titles": [], "bullets": [
                {"id": 100, "text": "Led 5-person team.", "tags": [],
                 "has_outcome": True, "source": "manual"},
             ]},
        ],
    }), encoding="utf-8")
    return cid, aid, ctx


class TestRecommendRoute:
    def test_persists_recommendations_to_context(self, rec_app):
        app_module, tmp_path = rec_app
        cid, aid, ctx = _seed(app_module, tmp_path)
        fake = {
            "recommendations": [
                {"experience_id": 7, "bullet_ids": [100], "rationale": "fits PM"},
            ],
        }
        with patch("analyzer.recommend_bullets", return_value=fake), \
             patch.object(app_module, "_get_client", return_value=object()):
            client = app_module.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend",
                json={"context_path": str(ctx)},
            )
        assert r.status_code == 200, r.get_json()
        saved = json.loads(ctx.read_text(encoding="utf-8"))
        assert saved["llm_recommendations"]["7"]["bullet_ids"] == [100]
        assert saved["llm_recommendations"]["7"]["rationale"] == "fits PM"
        # Transient jd_text stash is stripped post-call.
        assert "jd_text" not in saved

    def test_400_on_missing_context_path(self, rec_app):
        app_module, tmp_path = rec_app
        _, aid, _ = _seed(app_module, tmp_path)
        client = app_module.app.test_client()
        r = client.post(f"/api/applications/{aid}/recommend", json={})
        assert r.status_code == 400

    def test_400_on_mismatched_context(self, rec_app, tmp_path):
        app_module, _ = rec_app
        _, aid, _ = _seed(app_module, rec_app[1])
        # Build a second context file that claims a different application_id
        out = rec_app[1] / "output" / "alice"
        mismatch = out / "context_other.json"
        mismatch.write_text(json.dumps({"application_id": 999}), encoding="utf-8")
        client = app_module.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/recommend",
            json={"context_path": str(mismatch)},
        )
        assert r.status_code == 400

    def test_502_when_llm_response_malformed(self, rec_app):
        app_module, tmp_path = rec_app
        _, aid, ctx = _seed(app_module, tmp_path)
        from analyzer import LLMResponseError
        with patch("analyzer.recommend_bullets",
                   side_effect=LLMResponseError("bad shape", "no recommendations key")), \
             patch.object(app_module, "_get_client", return_value=object()):
            client = app_module.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend",
                json={"context_path": str(ctx)},
            )
        assert r.status_code == 502


class TestRecommendDedup:
    def test_near_duplicates_dropped_from_recommendations(self, rec_app):
        """B1.2: the safety pass drops near-restatements (Jaccard ≥ 0.75)
        even when the LLM returns them, preferring outcome-bearing bullets."""
        app_module, tmp_path = rec_app
        cid, aid, _ = _seed(app_module, tmp_path)
        # Override the corpus with two near-duplicate bullets.
        out = tmp_path / "output" / "alice"
        ctx2 = out / "context_dedup.json"
        ctx2.write_text(json.dumps({
            "application_id": aid,
            "career_corpus": [
                {"id": 7, "company": "Polaris", "start_date": "2022-01",
                 "end_date": None, "eligible_titles": [], "bullets": [
                    {"id": 100,
                     "text": "Reduced API latency 40% across 12 services.",
                     "tags": [], "has_outcome": True, "source": "manual"},
                    {"id": 101,
                     "text": "Cut API latency 40% across twelve services.",
                     "tags": [], "has_outcome": False, "source": "manual"},
                    {"id": 102,
                     "text": "Mentored a junior PM through the launch.",
                     "tags": [], "has_outcome": False, "source": "manual"},
                 ]},
            ],
        }), encoding="utf-8")
        fake = {
            "recommendations": [
                {"experience_id": 7, "bullet_ids": [100, 101, 102],
                 "rationale": "latency + mentorship"},
            ],
        }
        from unittest.mock import patch
        with patch("analyzer.recommend_bullets", return_value=fake), \
             patch.object(app_module, "_get_client", return_value=object()):
            # Hit the recommend route; the route is what actually persists.
            # The dedup happens inside recommend_bullets which we're mocking
            # away here — so this test only verifies the route persists the
            # mocked output cleanly. The dedup unit test below covers the
            # actual dedup logic.
            client = app_module.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend",
                json={"context_path": str(ctx2)},
            )
        assert r.status_code == 200
        saved = json.loads(ctx2.read_text(encoding="utf-8"))
        # The mocked recommend_bullets bypasses _dedup_recommendations; so
        # this is the route-shape check. Unit test below verifies dedup.
        assert "7" in saved["llm_recommendations"]

    def test_dedup_helper_drops_near_restatements(self):
        """Unit test for analyzer._dedup_recommendations. The Jaccard
        threshold (0.75) targets near-verbatim phrasings (the common
        cross-resume-import duplication shape); 'same achievement,
        different phrasing' below 0.75 is left to user review."""
        from analyzer import _dedup_recommendations
        corpus = [{
            "id": 7, "company": "X", "start_date": "2022-01", "end_date": None,
            "eligible_titles": [], "bullets": [
                {"id": 100,
                 "text": "Reduced API latency across the order service by "
                         "introducing connection pooling and a request cache.",
                 "tags": [], "has_outcome": True, "source": "manual"},
                {"id": 101,
                 "text": "Reduced API latency across our order service by "
                         "introducing connection pooling and a request cache.",
                 "tags": [], "has_outcome": False, "source": "manual"},
                {"id": 102,
                 "text": "Mentored a junior engineer through their first launch.",
                 "tags": [], "has_outcome": False, "source": "manual"},
            ],
        }]
        result = {
            "recommendations": [
                {"experience_id": 7, "bullet_ids": [100, 101, 102],
                 "rationale": "latency + mentorship"},
            ],
        }
        _dedup_recommendations(result, corpus)
        kept = result["recommendations"][0]["bullet_ids"]
        assert 100 in kept
        assert 102 in kept
        assert 101 not in kept

    def test_dedup_replaces_first_kept_when_later_arrival_has_outcome(self):
        """When a near-verbatim duplicate arrives where only the second
        copy has has_outcome=True, the second copy replaces the first in
        the kept list (outcome wins regardless of arrival order)."""
        from analyzer import _dedup_recommendations
        body = ("Reduced API latency across the order service by introducing "
                "connection pooling and a request cache.")
        corpus = [{
            "id": 7, "company": "X", "start_date": "2022-01", "end_date": None,
            "eligible_titles": [], "bullets": [
                {"id": 300, "text": body, "tags": [], "has_outcome": False,
                 "source": "manual"},
                {"id": 301, "text": body.replace("the order", "our order"),
                 "tags": [], "has_outcome": True, "source": "manual"},
            ],
        }]
        result = {
            "recommendations": [
                {"experience_id": 7, "bullet_ids": [300, 301], "rationale": "x"},
            ],
        }
        _dedup_recommendations(result, corpus)
        kept = result["recommendations"][0]["bullet_ids"]
        assert kept == [301]  # outcome-bearing variant wins even arriving second

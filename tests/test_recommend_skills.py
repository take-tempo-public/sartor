"""Tests for `analyzer.recommend_skills` + its route (B.5, Sprint 6.6).

recommend_skills orders (and lightly curates) the candidate's active, approved
skills for a JD — mirrors recommend_summaries (Haiku, id-only, short-circuit on
0/1). It selects only from the staged set, so a hallucinated id can never leak.
  - TestShortCircuit — 0 / 1 skills return without an LLM call.
  - TestNormalize — hallucinated ids dropped; dupes collapsed; order kept.
  - TestBlock — the <skills> XML block (id / category / tags).
  - TestRoute — /api/applications/<id>/recommend-skills persists to
    llm_skill_recommendations + strips transients; ownership/validation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestShortCircuit:
    def test_no_skills_returns_empty(self):
        from analyzer import recommend_skills
        result = recommend_skills(client=object(), context_set={"skill_items": []})
        assert result == {"recommendation": {"skill_ids": [], "rationale": "No skills to order."}}

    def test_single_skill_auto_picked_no_llm(self):
        from analyzer import recommend_skills
        result = recommend_skills(
            client=object(),
            context_set={"skill_items": [{"id": 7, "name": "Python"}]},
        )
        assert result["recommendation"]["skill_ids"] == [7]
        assert "only skill" in result["recommendation"]["rationale"].lower()


class TestNormalize:
    def test_drops_hallucinated_and_duplicate_ids_preserving_order(self):
        from analyzer import recommend_skills

        def _fake_parse_or_retry(*_a, **_k):
            # 99 is not in the staged set; 3 is repeated.
            return {"recommendation": {"skill_ids": [3, 99, 1, 3], "rationale": "r"}}

        ctx = {"skill_items": [
            {"id": 1, "name": "Python"},
            {"id": 2, "name": "Go"},
            {"id": 3, "name": "Kubernetes"},
        ]}
        with patch("analyzer._parse_or_retry", _fake_parse_or_retry):
            result = recommend_skills(client=object(), context_set=ctx)
        assert result["recommendation"]["skill_ids"] == [3, 1]


class TestBlock:
    def test_formats_skills_xml(self):
        from analyzer import _skills_block
        block = _skills_block([
            {"id": 1, "name": "C++ & Rust", "category": "language",
             "tags": ["systems", "backend"]},
            {"id": 2, "name": "Kubernetes"},
        ])
        assert '<skill id="1" category="language" tags="systems, backend">C++ &amp; Rust</skill>' in block
        assert '<skill id="2">Kubernetes</skill>' in block


# -------------------------------------------------------------------
# Route tests (stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def recommend_app(tmp_path, monkeypatch):
    db_file = tmp_path / "recskill.sqlite"
    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import importlib

    import app as _app
    importlib.reload(_app)

    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    output_dir.mkdir()
    configs_dir.mkdir()
    (configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()
    monkeypatch.setattr(_app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(_app, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(_app, "_get_client", lambda: object())

    from db.session import init_db
    init_db(db_file)
    return _app, output_dir


def _seed(output_dir):
    import json

    from db.models import Application, Candidate, Skill
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id, title="SRE",
            jd_text="SRE running Kubernetes at scale.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.flush()
        session.add_all([
            Skill(candidate_id=c.id, name="Python", display_order=0,
                  is_active=1, is_pending_review=0, source="imported"),
            Skill(candidate_id=c.id, name="Kubernetes", display_order=1,
                  is_active=1, is_pending_review=0, source="imported"),
            # pending + inactive must NOT be staged.
            Skill(candidate_id=c.id, name="Rust", display_order=2,
                  is_active=1, is_pending_review=1, source="llm_proposed"),
            Skill(candidate_id=c.id, name="Perl", display_order=3, is_active=0,
                  is_pending_review=0, source="imported"),
        ])
        session.commit()
        aid = a.id
    finally:
        session.close()

    ctx = {"application_id": aid, "llm_analysis": {"essential_skills": ["kubernetes"]},
           "run_id": "testrun"}
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return aid, str(ctx_path)


class TestRoute:
    def test_happy_path_persists_and_stages_only_active_approved(self, recommend_app):
        _app, output_dir = recommend_app
        aid, ctx_path = _seed(output_dir)

        seen = {}

        def _stub(client, context_set, *, username="", run_id=""):
            seen["names"] = {it["name"] for it in context_set.get("skill_items") or []}
            seen["jd"] = context_set.get("jd_text", "")
            ids = [it["id"] for it in context_set["skill_items"]]
            return {"recommendation": {"skill_ids": list(reversed(ids)), "rationale": "ok"}}

        with patch("analyzer.recommend_skills", _stub):
            client = _app.app.test_client()
            r = client.post(f"/api/applications/{aid}/recommend-skills",
                            json={"context_path": ctx_path})
        assert r.status_code == 200, r.get_data(as_text=True)
        # Only active + approved skills were staged (no Rust/Perl).
        assert seen["names"] == {"Python", "Kubernetes"}
        assert seen["jd"].startswith("SRE")

        import json
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        assert "llm_skill_recommendations" in ctx
        assert "skill_items" not in ctx  # transient stripped
        assert "jd_text" not in ctx

    def test_unknown_application_404(self, recommend_app):
        _app, _ = recommend_app
        client = _app.app.test_client()
        r = client.post("/api/applications/9999/recommend-skills",
                        json={"context_path": "/whatever"})
        assert r.status_code == 404

    def test_missing_context_path_400(self, recommend_app):
        _app, output_dir = recommend_app
        aid, _ = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{aid}/recommend-skills", json={})
        assert r.status_code == 400

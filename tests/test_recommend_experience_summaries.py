"""Tests for `analyzer.recommend_experience_summaries` + its route (B.4).

Mirrors test_recommend_summaries.py but for the batched, per-role variant:
  - TestShortCircuit — auto-picks single-variant roles + omits empty roles
    without calling the LLM; fires the LLM only when a role has 2+ variants.
  - TestBlock — the <experience_summaries> XML block groups variants per role.
  - TestDedup — per-experience Jaccard ≥ 0.75 alternate dedup.
  - TestRoute — /api/applications/<id>/recommend-experience-summaries persists
    to llm_experience_summary_recommendations + handles ownership/validation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Pure-function tests (no LLM, no DB)
# -------------------------------------------------------------------


class TestShortCircuit:
    def test_no_groups_returns_empty(self):
        from analyzer import recommend_experience_summaries
        result = recommend_experience_summaries(
            client=object(),  # never called
            context_set={"experience_summary_items": []},
        )
        assert result == {"recommendations": []}

    def test_single_variant_roles_auto_picked_no_llm(self):
        """A role with exactly one variant is auto-picked deterministically;
        a role with zero (or blank-only) variants is omitted. No LLM call."""
        from analyzer import recommend_experience_summaries
        result = recommend_experience_summaries(
            client=object(),
            context_set={"experience_summary_items": [
                {"experience_id": 5, "company": "Acme",
                 "items": [{"id": 9, "text": "Led X.", "has_outcome": True}]},
                {"experience_id": 6, "company": "Beta", "items": []},
                {"experience_id": 7, "company": "Gamma",
                 "items": [{"id": 11, "text": "   "}]},
            ]},
        )
        assert result == {"recommendations": [
            {"experience_id": 5, "summary_item_id": 9,
             "rationale": "Only variant available — no alternates to weigh.",
             "alternates": []},
        ]}

    def test_multi_variant_role_calls_llm_and_merges_with_auto(self):
        """One role has a real choice (2 variants) → the LLM fires once; a
        sibling single-variant role is auto-picked and merged in."""
        from analyzer import recommend_experience_summaries

        def _fake_parse_or_retry(*_a, **_k):
            return {"recommendations": [
                {"experience_id": 5, "summary_item_id": 91,
                 "rationale": "best fit", "alternates": [
                     {"summary_item_id": 92, "rationale": "second"}]},
            ]}

        ctx = {"experience_summary_items": [
            {"experience_id": 5, "company": "Acme", "items": [
                {"id": 91, "text": "Owned platform scale across teams."},
                {"id": 92, "text": "Drove growth experiments end to end."},
            ]},
            {"experience_id": 6, "company": "Beta", "items": [
                {"id": 80, "text": "Sole variant."},
            ]},
        ]}
        with patch("analyzer._parse_or_retry", _fake_parse_or_retry):
            result = recommend_experience_summaries(client=object(), context_set=ctx)
        recs = {r["experience_id"]: r for r in result["recommendations"]}
        assert recs[5]["summary_item_id"] == 91
        assert recs[6]["summary_item_id"] == 80  # auto-picked single variant
        assert recs[6]["rationale"].lower().startswith("only variant")


class TestBlock:
    def test_groups_variants_under_experience(self):
        from analyzer import _experience_summary_items_block
        block = _experience_summary_items_block([
            {"experience_id": 5, "company": "Acme & Co", "items": [
                {"id": 9, "text": "Led <platform> scale.", "label": "scale",
                 "has_outcome": True},
                {"id": 10, "text": "Built team."},
            ]},
        ])
        assert '<experience id="5" company="Acme &amp; Co">' in block
        assert ('<summary_item id="9" label="scale" has_outcome="true">'
                'Led &lt;platform&gt; scale.</summary_item>') in block
        assert '<summary_item id="10">Built team.</summary_item>' in block


class TestDedup:
    def test_drops_near_duplicate_alternate_per_experience(self):
        from analyzer import _dedup_experience_summary_recommendations
        groups = [{"experience_id": 5, "items": [
            {"id": 9, "text": "led platform scale program across teams"},
            {"id": 10, "text": "mentored five junior engineers"},
            {"id": 11, "text": "led platform scale program across teams"},
        ]}]
        result = {"recommendations": [
            {"experience_id": 5, "summary_item_id": 9, "alternates": [
                {"summary_item_id": 9},   # echo of recommendation → dropped
                {"summary_item_id": 10},  # distinct → kept
                {"summary_item_id": 11},  # near-dup of 9 → dropped
            ]},
        ]}
        _dedup_experience_summary_recommendations(result, groups)
        assert [a["summary_item_id"] for a in result["recommendations"][0]["alternates"]] == [10]


# -------------------------------------------------------------------
# Route tests (with stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def recommend_app(tmp_path, monkeypatch):
    import types

    db_file = tmp_path / "recexpsum.sqlite"
    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config
    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()
    # The recommend routes moved to blueprints/applications.py (Sprint 8.3f) and
    # resolve _get_client from that module's namespace — stub it there.
    monkeypatch.setattr("blueprints.applications._get_client", lambda: object())

    from db.session import init_db
    init_db(db_file)
    return types.SimpleNamespace(app=app), output_dir


def _seed(output_dir):
    """Candidate + application + two experiences (one with 2 intro variants,
    one with 1) + a context file. Returns (candidate_id, application_id, ctx)."""
    import json

    from db.models import (
        Application,
        Candidate,
        Experience,
        ExperienceSummaryItem,
    )
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id, title="Senior PM",
            jd_text="Senior PM building AI platforms.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.flush()
        e1 = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
        e2 = Experience(candidate_id=c.id, company="Beta", start_date="2018-01")
        session.add_all([e1, e2])
        session.flush()
        session.add_all([
            ExperienceSummaryItem(experience_id=e1.id, text="Platform-scale framing.",
                                  display_order=0, is_active=1),
            ExperienceSummaryItem(experience_id=e1.id, text="Growth-builder framing.",
                                  display_order=1, is_active=1),
            ExperienceSummaryItem(experience_id=e2.id, text="Sole role intro.",
                                  display_order=0, is_active=1),
        ])
        session.commit()
        cid, aid, e1id = c.id, a.id, e1.id
    finally:
        session.close()

    ctx = {
        "application_id": aid,
        "llm_analysis": {"essential_skills": ["ai-platform"]},
        "iteration": 0,
        "run_id": "testrun",
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, e1id, str(ctx_path)


class TestRoute:
    def test_happy_path_persists_recommendations(self, recommend_app):
        _app, output_dir = recommend_app
        _cid, aid, e1id, ctx_path = _seed(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            groups = context_set.get("experience_summary_items") or []
            # e1 (2 variants) + e2 (1 variant) staged; jd_text present.
            assert {g["experience_id"] for g in groups} == {e1id, e1id + 1}
            assert context_set.get("jd_text", "").startswith("Senior PM")
            return {"recommendations": [
                {"experience_id": e1id, "summary_item_id": 1,
                 "rationale": "fits", "alternates": []},
            ]}

        with patch("analyzer.recommend_experience_summaries", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend-experience-summaries",
                json={"context_path": ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["application_id"] == aid
        assert body["recommendations"][0]["experience_id"] == e1id

        import json
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        assert "llm_experience_summary_recommendations" in ctx
        assert "experience_summary_items" not in ctx  # transient stripped
        assert "jd_text" not in ctx

    def test_unknown_application_404(self, recommend_app):
        _app, _ = recommend_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/recommend-experience-summaries",
            json={"context_path": "/whatever"},
        )
        assert r.status_code == 404

    def test_missing_context_path_400(self, recommend_app):
        _app, output_dir = recommend_app
        _cid, aid, _e1id, _ = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/recommend-experience-summaries", json={})
        assert r.status_code == 400

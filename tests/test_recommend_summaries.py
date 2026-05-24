"""Tests for `analyzer.recommend_summaries` + the route (Phase β.6b).

Two test surfaces:
  - TestRecommendSummariesShortCircuit — function returns the trivial
    answer without calling the LLM when there are 0 or 1 variants.
  - TestDedupSummaryRecommendations — Jaccard ≥ 0.75 dedup on the
    alternates list, mirroring the bullet dedup.
  - TestRoute — /api/applications/<id>/recommend-summary persists the
    result + handles ownership, validation, short-circuit paths.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Pure-function tests (no LLM, no DB)
# -------------------------------------------------------------------


class TestRecommendSummariesShortCircuit:
    def test_zero_variants_returns_null_recommendation(self):
        from analyzer import recommend_summaries
        result = recommend_summaries(
            client=object(),  # never called
            context_set={"summary_items": []},
        )
        assert result == {"recommendation": None, "alternates": []}

    def test_blank_text_variants_treated_as_zero(self):
        from analyzer import recommend_summaries
        result = recommend_summaries(
            client=object(),
            context_set={"summary_items": [
                {"id": 1, "text": ""},
                {"id": 2, "text": "   "},
            ]},
        )
        assert result["recommendation"] is None
        assert result["alternates"] == []

    def test_single_variant_returns_it_unchanged(self):
        """Saves the Haiku call — there's no decision to make."""
        from analyzer import recommend_summaries
        result = recommend_summaries(
            client=object(),
            context_set={"summary_items": [
                {"id": 7, "text": "AI platform PM with a decade of leadership.",
                 "label": "AI Platform PM", "has_outcome": False},
            ]},
        )
        assert result["recommendation"]["summary_item_id"] == 7
        assert "only variant" in result["recommendation"]["rationale"].lower()
        assert result["alternates"] == []


class TestDedupSummaryRecommendations:
    def test_drops_alternate_near_duplicate_of_recommendation(self):
        from analyzer import _dedup_summary_recommendations
        items = [
            {"id": 1, "text": "Senior product manager with a decade in AI platforms."},
            {"id": 2, "text": "Senior product manager with a decade in AI platforms work."},
            {"id": 3, "text": "Early-stage builder focused on user experience and growth."},
        ]
        result = {
            "recommendation": {"summary_item_id": 1, "rationale": "primary"},
            "alternates": [
                {"summary_item_id": 2, "rationale": "near dup"},
                {"summary_item_id": 3, "rationale": "genuine alt"},
            ],
        }
        _dedup_summary_recommendations(result, items)
        kept_ids = [a["summary_item_id"] for a in result["alternates"]]
        assert 2 not in kept_ids
        assert 3 in kept_ids

    def test_drops_alternates_that_dup_each_other(self):
        from analyzer import _dedup_summary_recommendations
        items = [
            {"id": 1, "text": "Different positioning, unique phrasing entirely here."},
            {"id": 2, "text": "Senior product manager with a decade in AI platforms."},
            {"id": 3, "text": "Senior product manager with a decade in AI platforms work."},
        ]
        result = {
            "recommendation": {"summary_item_id": 1, "rationale": "primary"},
            "alternates": [
                {"summary_item_id": 2, "rationale": "alt 2"},
                {"summary_item_id": 3, "rationale": "alt 3 — near-dup of alt 2"},
            ],
        }
        _dedup_summary_recommendations(result, items)
        # Only the first of the near-dup pair survives
        kept = [a["summary_item_id"] for a in result["alternates"]]
        assert kept == [2]

    def test_preserves_distinct_alternates(self):
        from analyzer import _dedup_summary_recommendations
        items = [
            {"id": 1, "text": "AI platform PM positioning."},
            {"id": 2, "text": "Design IC positioning entirely different."},
            {"id": 3, "text": "Early-stage builder generalist framing."},
        ]
        result = {
            "recommendation": {"summary_item_id": 1, "rationale": "primary"},
            "alternates": [
                {"summary_item_id": 2, "rationale": "alt 2"},
                {"summary_item_id": 3, "rationale": "alt 3"},
            ],
        }
        _dedup_summary_recommendations(result, items)
        assert len(result["alternates"]) == 2

    def test_never_surfaces_recommendation_id_as_alternate(self):
        """If the LLM mistakenly echoes the same id as both
        recommendation + alternate, drop the alternate."""
        from analyzer import _dedup_summary_recommendations
        items = [{"id": 5, "text": "Some positioning text here."}]
        result = {
            "recommendation": {"summary_item_id": 5, "rationale": "primary"},
            "alternates": [
                {"summary_item_id": 5, "rationale": "echo"},
            ],
        }
        _dedup_summary_recommendations(result, items)
        assert result["alternates"] == []


# -------------------------------------------------------------------
# Route tests (with stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def recommend_app(tmp_path, monkeypatch):
    db_file = tmp_path / "recsum.sqlite"
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


def _seed(app_module, output_dir):
    """Seed a candidate + application + minimal context_set file +
    return (candidate, application_id, context_path)."""
    import json

    from db.models import Application, Candidate, SummaryItem
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
        # Three variants to give the LLM a real choice
        for i, text in enumerate([
            "AI platform PM with a decade of platform leadership and outcomes.",
            "Early-stage builder PM focused on zero-to-one launches and user growth.",
            "Enterprise PM with a record of cross-team alignment and shipping.",
        ]):
            session.add(SummaryItem(
                candidate_id=c.id, text=text,
                display_order=i, is_active=1,
            ))
        session.commit()
        cid = c.id
        aid = a.id
    finally:
        session.close()

    # Write a context file matching what /api/analyze would produce
    ctx = {
        "application_id": aid,
        "candidate": {"name": "Casey Rivera"},
        "resume": {"format": "md", "text": "", "filename": ""},
        "llm_analysis": {
            "essential_skills": ["ai-platform"],
            "industry_keywords": ["ml-ops"],
        },
        "iteration": 0,
        "run_id": "testrun",
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, str(ctx_path)


class TestRecommendSummaryRoute:
    def test_happy_path_persists_recommendation(self, recommend_app):
        _app, output_dir = recommend_app
        _cid, aid, ctx_path = _seed(_app, output_dir)

        # Stub the LLM call to return a deterministic recommendation
        def _stub(client, context_set, *, username="", run_id=""):
            items = context_set.get("summary_items") or []
            assert len(items) == 3  # all three variants were passed in
            assert context_set.get("jd_text", "").startswith("Senior PM")
            return {
                "recommendation": {
                    "summary_item_id": items[0]["id"],
                    "rationale": "Strong AI platform framing match.",
                },
                "alternates": [
                    {"summary_item_id": items[1]["id"],
                     "rationale": "Builder framing is a close second."},
                ],
            }

        with patch("analyzer.recommend_summaries", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend-summary",
                json={"context_path": ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["application_id"] == aid
        assert body["recommendation"]["rationale"].startswith("Strong AI")
        assert len(body["alternates"]) == 1

        # Persistence: context file contains llm_summary_recommendation,
        # and the transient summary_items + jd_text were stripped
        import json
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        assert "llm_summary_recommendation" in ctx
        assert ctx["llm_summary_recommendation"]["recommendation"]["rationale"].startswith("Strong AI")
        assert "summary_items" not in ctx
        assert "jd_text" not in ctx

    def test_returns_404_for_unknown_application(self, recommend_app):
        _app, _output_dir = recommend_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/recommend-summary",
            json={"context_path": "/whatever"},
        )
        assert r.status_code == 404

    def test_returns_400_for_missing_context_path(self, recommend_app):
        _app, output_dir = recommend_app
        _cid, aid, _ = _seed(_app, output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{aid}/recommend-summary", json={})
        assert r.status_code == 400

    def test_short_circuits_when_candidate_has_no_variants(self, recommend_app):
        """When the candidate has zero active SummaryItem rows, the
        route still returns 200 with recommendation=None — the
        function's short-circuit path."""
        _app, output_dir = recommend_app
        # Seed candidate + application but NO summary items
        import json

        from db.models import Application, Candidate
        from db.session import get_session
        session = get_session()
        try:
            c = Candidate(username="casey", name="Casey")
            session.add(c)
            session.flush()
            a = Application(
                candidate_id=c.id, title="Senior PM",
                jd_text="Test JD.",
                jd_fingerprint="g" * 16,
            )
            session.add(a)
            session.commit()
            aid = a.id
        finally:
            session.close()

        ctx_path = output_dir / "casey" / "ctx0.json"
        ctx_path.write_text(json.dumps({
            "application_id": aid,
            "llm_analysis": {},
            "iteration": 0,
        }), encoding="utf-8")

        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/recommend-summary",
            json={"context_path": str(ctx_path)},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["recommendation"] is None
        assert body["alternates"] == []

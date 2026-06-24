"""Tests for `analyzer.suggest_skills` + its route (B.5, Sprint 6.6).

suggest_skills is the grounded generator: it proposes skills the JD wants AND
the corpus evidences. Grounding is enforced by the prompt (evidence-or-nothing)
AND by the human gate — proposals land as PENDING rows the user must approve,
and pending skills never reach the recommend set, the preview, or the prompt.
  - TestFunction — empty corpus → no proposals; dedup vs existing + in-batch.
  - TestRoute — proposals inserted as pending (source='llm_proposed',
    is_pending_review=1) carrying evidence; existing names skipped; pending
    rows excluded from the default skills list (the grounding gate).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestFunction:
    def test_empty_corpus_returns_no_proposals(self):
        from analyzer import suggest_skills

        result = suggest_skills(client=object(), context_set={"career_corpus": []})
        assert result == {"proposals": []}

    def test_dedup_against_existing_and_in_batch(self):
        from analyzer import suggest_skills

        def _fake_parse_or_retry(*_a, **_k):
            return {
                "proposals": [
                    {"name": "Kubernetes", "evidence": {"bullet_id": 1, "quote": "q"}},
                    {
                        "name": "python",
                        "evidence": {"bullet_id": 2, "quote": "q"},
                    },  # existing (case-insensitive)
                    {
                        "name": "Kubernetes",
                        "evidence": {"bullet_id": 3, "quote": "q"},
                    },  # in-batch dup
                    {"name": "  ", "evidence": {}},  # blank → dropped
                ]
            }

        ctx = {
            "career_corpus": [
                {"id": 1, "company": "Acme", "bullets": [{"id": 1, "text": "Ran K8s."}]}
            ],
            "llm_analysis": {"essential_skills": ["kubernetes"]},
            "existing_skill_names": ["Python"],
        }
        with patch("analyzer._parse_or_retry", _fake_parse_or_retry):
            result = suggest_skills(client=object(), context_set=ctx)
        names = [p["name"] for p in result["proposals"]]
        assert names == ["Kubernetes"]  # python (existing) + dup + blank dropped


# -------------------------------------------------------------------
# Route tests (stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def suggest_app(tmp_path, monkeypatch):
    import types

    db_file = tmp_path / "suggskill.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    # Sprint 8.3f: the applications seam moved to blueprints/applications.py, so this
    # fully migrates onto create_app(Config(base_dir=tmp_path)) — both the route under
    # test (POST /api/applications/<id>/suggest-skills) and the test's GET
    # /api/users/<u>/skills verification call read current_app.config[...], now set by
    # the factory (no more per-route global / app.config injection).
    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()
    # suggest-skills resolves _get_client from blueprints.applications now.
    monkeypatch.setattr("blueprints.applications._get_client", lambda: object())

    from db.session import init_db

    init_db(db_file)
    return types.SimpleNamespace(app=app), output_dir


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
            candidate_id=c.id,
            title="SRE",
            jd_text="SRE running Kubernetes.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.flush()
        session.add(
            Skill(
                candidate_id=c.id,
                name="Python",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="imported",
            )
        )
        session.commit()
        cid, aid = c.id, a.id
    finally:
        session.close()

    ctx = {
        "application_id": aid,
        "career_corpus": [
            {"id": 1, "company": "Acme", "bullets": [{"id": 1, "text": "Migrated to Kubernetes."}]}
        ],
        "llm_analysis": {"essential_skills": ["kubernetes"]},
        "run_id": "testrun",
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, str(ctx_path)


class TestRoute:
    def test_proposals_inserted_as_pending_and_gated(self, suggest_app):
        _app, output_dir = suggest_app
        cid, aid, ctx_path = _seed(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            # The route stages existing names so the generator can dedup.
            assert "Python" in (context_set.get("existing_skill_names") or [])
            return {
                "proposals": [
                    {
                        "name": "Kubernetes",
                        "category": "platform",
                        "evidence": {"bullet_id": 1, "quote": "Migrated to Kubernetes."},
                        "rationale": "JD wants K8s; bullet 1 shows it.",
                    },
                    {"name": "Python", "evidence": {}},  # existing → skipped by route
                ]
            }

        with patch("analyzer.suggest_skills", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/suggest-skills", json={"context_path": ctx_path}
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        created = r.get_json()["proposals"]
        assert [p["name"] for p in created] == ["Kubernetes"]  # existing skipped
        # Proposals land as pending llm_proposed rows carrying evidence.
        assert created[0]["is_pending_review"] is True
        assert created[0]["source"] == "llm_proposed"
        assert created[0]["evidence"]["bullet_id"] == 1

        # Grounding gate: the pending skill is excluded from the default list
        # (it does NOT reach the recommend set / preview / prompt until approved).
        default = client.get("/api/users/casey/skills").get_json()["skills"]
        assert {s["name"] for s in default} == {"Python"}
        pending = client.get("/api/users/casey/skills?include_pending=1").get_json()["skills"]
        assert {s["name"] for s in pending} == {"Python", "Kubernetes"}

    def test_unknown_application_404(self, suggest_app):
        _app, _ = suggest_app
        client = _app.app.test_client()
        r = client.post("/api/applications/9999/suggest-skills", json={"context_path": "/whatever"})
        assert r.status_code == 404

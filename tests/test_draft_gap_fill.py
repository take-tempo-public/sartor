"""Tests for `analyzer.draft_gap_fill_bullets` + the /draft-gap-fill route.

Generation-experience re-architecture Phase 3 (fix/compose-frozen-composition):
at Compose, grounded gap-fill bullets are drafted (Sonnet) for JD requirements
the corpus doesn't cover, and stashed as TRANSIENT proposals on
ctx["llm_gap_fill_proposals"] (not yet Bullet rows). Two surfaces:
  - TestDraftGapFillShortCircuit — no JD / no corpus → {"proposals": []} with NO
    LLM call.
  - TestDraftGapFillRoute — POST /api/applications/<id>/draft-gap-fill normalizes
    route-side (drops foreign experiences, keys each proposal), ALWAYS writes the
    key (even []) so has_gap_fill flips, strips transient staging, handles
    ownership + validation.

The accept/retire half lives in test_gap_fill_decide.py.
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Pure-function short-circuit (no LLM, no DB)
# -------------------------------------------------------------------


class TestDraftGapFillShortCircuit:
    def test_no_jd_returns_empty_no_llm(self):
        from analyzer import draft_gap_fill_bullets

        # client=object() would raise if the LLM path ran — corpus present, JD
        # absent short-circuits first.
        result = draft_gap_fill_bullets(
            client=object(),
            context_set={"career_corpus": [{"id": 1, "company": "Acme"}]},
        )
        assert result == {"proposals": []}

    def test_no_corpus_returns_empty_no_llm(self):
        from analyzer import draft_gap_fill_bullets

        result = draft_gap_fill_bullets(
            client=object(),
            context_set={"jd_text": "Senior PM."},
        )
        assert result == {"proposals": []}

    def test_prompt_includes_corpus_and_gaps(self):
        from analyzer import draft_gap_fill_bullets

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"proposals": []}

        with patch("analyzer._parse_or_retry", _cap):
            draft_gap_fill_bullets(
                client=object(),
                context_set={
                    "career_corpus": [
                        {
                            "id": 1,
                            "company": "Acme",
                            "start_date": "2021-01",
                            "eligible_titles": [],
                            "bullets": [{"id": 10, "text": "Led the billing rewrite."}],
                        }
                    ],
                    "jd_text": "Senior PM.",
                    "llm_analysis": {
                        "essential_skills": ["Kubernetes"],
                        "preferred_skills": [],
                        "comparison": {"gaps": ["container orchestration"]},
                    },
                    "deterministic_analysis": {
                        "keyword_overlap": {"missing_from_resume": ["Terraform"]}
                    },
                },
            )
        p = captured["prompt"]
        assert "<career_corpus" in p
        assert "Kubernetes" in p
        assert "Terraform" in p
        assert "container orchestration" in p

    def test_prompt_includes_prior_clarifications(self):
        """D5 (feat/clarifications-to-corpus): cross-JD confirmed facts render
        as a distinct <prior_clarifications> block, separate from this
        application's own <clarifications>."""
        from analyzer import draft_gap_fill_bullets

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"proposals": []}

        with patch("analyzer._parse_or_retry", _cap):
            draft_gap_fill_bullets(
                client=object(),
                context_set={
                    "career_corpus": [{"id": 1, "company": "Acme", "bullets": []}],
                    "jd_text": "Senior SRE role.",
                    "prior_clarifications": [
                        {
                            "question": "Led on-call?",
                            "answer": "Led on-call for a 12-person SRE team.",
                            "kind": "experience_probe",
                        }
                    ],
                },
            )
        p = captured["prompt"]
        assert "<prior_clarifications>" in p
        assert "Led on-call for a 12-person SRE team." in p


# -------------------------------------------------------------------
# Route tests (stubbed LLM + real DB experiences)
# -------------------------------------------------------------------


@pytest.fixture
def gap_app(tmp_path, monkeypatch):
    db_file = tmp_path / "gapfill.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()
    monkeypatch.setattr("blueprints.applications._get_client", lambda: object())

    from db.session import init_db

    init_db(db_file)
    return types.SimpleNamespace(app=app), output_dir


def _seed_gap(output_dir):
    """Seed a candidate with a real Experience + Bullet + iteration-0 run, and a
    context file carrying application_run_id (the accept ledger's FK)."""
    from db.models import Application, ApplicationRun, Bullet, Candidate, Experience
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera", profile_text="A platform PM.")
        session.add(c)
        session.flush()
        e = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
        session.add(e)
        session.flush()
        b = Bullet(
            experience_id=e.id,
            text="Led the billing rewrite.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="official",
            has_outcome=0,
        )
        session.add(b)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title="Senior PM",
            jd_text="Senior PM building AI billing platforms.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.flush()
        run = ApplicationRun(
            application_id=a.id,
            iteration=0,
            run_id="testrun",
            prompt_version="test",
            corpus_snapshot_json="{}",
        )
        session.add(run)
        session.commit()
        cid, aid, eid, bid, run_pk = c.id, a.id, e.id, b.id, run.id
    finally:
        session.close()

    ctx = {
        "application_id": aid,
        "application_run_id": run_pk,
        "iteration": 0,
        "run_id": "testrun",
        "llm_analysis": {
            "essential_skills": ["billing"],
            "preferred_skills": [],
            "comparison": {"gaps": []},
        },
        "deterministic_analysis": {"keyword_overlap": {"missing_from_resume": ["Kubernetes"]}},
        "career_corpus": [
            {
                "id": eid,
                "company": "Acme",
                "start_date": "2021-01",
                "end_date": "present",
                "eligible_titles": [{"id": 1, "title": "Platform PM", "is_official": True}],
                "bullets": [{"id": bid, "text": "Led the billing rewrite."}],
            }
        ],
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return types.SimpleNamespace(
        cid=cid, aid=aid, eid=eid, bid=bid, run_pk=run_pk, ctx_path=str(ctx_path)
    )


class TestDraftGapFillRoute:
    def test_persist_writes_keyed_proposals(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_gap(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            # The route staged the JD transiently.
            assert context_set.get("jd_text", "").startswith("Senior PM")
            return {
                "proposals": [
                    {
                        "experience_id": s.eid,
                        "text": "Built Terraform IaC across 3 accounts.",
                        "pattern_kind": "xyz",
                        "requirement": "Terraform",
                        "evidence": {"bullet_id": s.bid, "quote": "..."},
                        "rationale": "reframes existing infra work",
                    }
                ]
            }

        with patch("analyzer.draft_gap_fill_bullets", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-gap-fill",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["has_gap_fill"] is True
        assert len(body["proposals"]) == 1
        assert body["proposals"][0]["key"]
        assert body["proposals"][0]["experience_id"] == s.eid

        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert "llm_gap_fill_proposals" in ctx
        assert ctx["llm_gap_fill_proposals"][0]["text"] == "Built Terraform IaC across 3 accounts."
        # Transient JD staging stripped.
        assert "jd_text" not in ctx

    def test_foreign_experience_dropped(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_gap(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "proposals": [
                    {
                        "experience_id": 999999,
                        "text": "Foreign role bullet.",
                        "pattern_kind": "manual",
                    },
                    {"experience_id": s.eid, "text": "Valid bullet.", "pattern_kind": "manual"},
                ]
            }

        with patch("analyzer.draft_gap_fill_bullets", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-gap-fill",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200
        props = r.get_json()["proposals"]
        assert len(props) == 1
        assert props[0]["experience_id"] == s.eid

    def test_empty_result_still_sets_has_gap_fill(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_gap(output_dir)

        with patch("analyzer.draft_gap_fill_bullets", lambda *a, **k: {"proposals": []}):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-gap-fill",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        # Key present even when empty → the auto-fire latch never re-loops.
        assert "llm_gap_fill_proposals" in ctx
        assert ctx["llm_gap_fill_proposals"] == []
        # GET surfaces has_gap_fill True.
        client = _app.app.test_client()
        r2 = client.get(f"/api/applications/{s.aid}/composition?context_path={s.ctx_path}")
        assert r2.get_json()["has_gap_fill"] is True

    def test_404_unknown_application(self, gap_app):
        _app, _output_dir = gap_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/draft-gap-fill",
            json={"context_path": "/whatever"},
        )
        assert r.status_code == 404

    def test_400_missing_context_path(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_gap(output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{s.aid}/draft-gap-fill", json={})
        assert r.status_code == 400

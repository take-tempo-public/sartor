"""Tests for `analyzer.draft_surgical_refinement` + the /draft-refinement route.

Generation-experience re-architecture item (a) (fix/surgical-refinement-and-loopback):
a scoped, single-item refinement drafted from a free-text note (Sonnet), targeting
exactly ONE bullet (sharpened in place via supersedes_bullet_id, or a genuinely
stronger new bullet) or the positioning summary — never a whole-document rewrite.

Two surfaces:
  - TestDraftSurgicalRefinementShortCircuit — no note / no frozen composition / no
    JD -> the "none" default with NO LLM call.
  - TestDraftRefinementRoute — POST /api/applications/<id>/draft-refinement
    re-validates any id the model returns against this candidate's own corpus
    (foreign ids downgrade the proposal to None), never writes to the context file
    (a pure read), and handles ownership + validation.

The accept half lives in test_accept_refinement.py.
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


_DEFAULT = {
    "target_kind": "none",
    "experience_id": None,
    "supersedes_bullet_id": None,
    "text": "",
    "pattern_kind": None,
    "rationale": "",
}


class TestDraftSurgicalRefinementShortCircuit:
    def test_no_note_returns_default_no_llm(self):
        from analyzer import draft_surgical_refinement

        # client=object() would raise if the LLM path ran.
        result = draft_surgical_refinement(
            client=object(),
            context_set={
                "jd_text": "Senior PM.",
                "approved_composition": {"basics": {"summary": "x"}, "work": []},
            },
        )
        assert result == _DEFAULT

    def test_no_composition_returns_default_no_llm(self):
        from analyzer import draft_surgical_refinement

        result = draft_surgical_refinement(
            client=object(),
            context_set={"jd_text": "Senior PM.", "refinement_note": "punch up bullet 2"},
        )
        assert result == _DEFAULT

    def test_no_jd_returns_default_no_llm(self):
        from analyzer import draft_surgical_refinement

        result = draft_surgical_refinement(
            client=object(),
            context_set={
                "refinement_note": "punch up bullet 2",
                "approved_composition": {"basics": {"summary": "x"}, "work": []},
            },
        )
        assert result == _DEFAULT

    def test_prompt_includes_current_resume_and_note(self):
        from analyzer import draft_surgical_refinement

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return dict(_DEFAULT)

        doc = {
            "basics": {"summary": "A platform PM."},
            "work": [
                {"name": "Acme", "position": "PM", "highlights": ["Led the billing rewrite."]}
            ],
            "meta": {
                "sartor": {
                    "work_provenance": [
                        {
                            "experience_id": 7,
                            "title_id": 1,
                            "role_intro_id": None,
                            "highlight_ids": [12],
                        }
                    ]
                }
            },
        }
        with patch("analyzer._parse_or_retry", _cap):
            draft_surgical_refinement(
                client=object(),
                context_set={
                    "jd_text": "Senior PM building AI billing platforms.",
                    "refinement_note": "make the billing bullet punchier",
                    "approved_composition": doc,
                },
            )
        p = captured["prompt"]
        assert "<current_resume>" in p
        assert "Led the billing rewrite." in p
        assert 'id="12"' in p
        assert "make the billing bullet punchier" in p

    def test_downgrades_empty_text_to_none(self):
        from analyzer import draft_surgical_refinement

        def _empty_text(client, user_prompt, **kw):
            return {"target_kind": "bullet", "experience_id": 7, "text": "   "}

        with patch("analyzer._parse_or_retry", _empty_text):
            result = draft_surgical_refinement(
                client=object(),
                context_set={
                    "jd_text": "Senior PM.",
                    "refinement_note": "note",
                    "approved_composition": {"basics": {}, "work": []},
                },
            )
        assert result["target_kind"] == "none"

    def test_invalid_target_kind_downgrades_to_none(self):
        from analyzer import draft_surgical_refinement

        def _bad_kind(client, user_prompt, **kw):
            return {"target_kind": "rewrite_everything", "text": "whatever"}

        with patch("analyzer._parse_or_retry", _bad_kind):
            result = draft_surgical_refinement(
                client=object(),
                context_set={
                    "jd_text": "Senior PM.",
                    "refinement_note": "note",
                    "approved_composition": {"basics": {}, "work": []},
                },
            )
        assert result["target_kind"] == "none"


# -------------------------------------------------------------------
# Route tests (stubbed LLM + real DB experiences)
# -------------------------------------------------------------------


@pytest.fixture
def refine_app(tmp_path, monkeypatch):
    db_file = tmp_path / "refine.sqlite"
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


def _seed_refine(output_dir):
    """Seed a candidate with a real Experience + 2 Bullets + a frozen approved_composition."""
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
        b1 = Bullet(
            experience_id=e.id,
            text="Led the billing rewrite.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="official",
            has_outcome=0,
        )
        session.add(b1)
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
        cid, aid, eid, bid, run_pk = c.id, a.id, e.id, b1.id, run.id
    finally:
        session.close()

    doc = {
        "basics": {"summary": "A platform PM who ships."},
        "work": [{"name": "Acme", "position": "PM", "highlights": ["Led the billing rewrite."]}],
        "meta": {
            "sartor": {
                "work_provenance": [
                    {
                        "experience_id": eid,
                        "title_id": None,
                        "role_intro_id": None,
                        "highlight_ids": [bid],
                    }
                ]
            }
        },
    }
    ctx = {
        "application_id": aid,
        "application_run_id": run_pk,
        "iteration": 0,
        "run_id": "testrun",
        "career_corpus": [
            {
                "id": eid,
                "company": "Acme",
                "start_date": "2021-01",
                "end_date": "present",
                "eligible_titles": [],
                "bullets": [{"id": bid, "text": "Led the billing rewrite."}],
            }
        ],
        "approved_composition": doc,
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return types.SimpleNamespace(
        cid=cid, aid=aid, eid=eid, bid=bid, run_pk=run_pk, ctx_path=str(ctx_path)
    )


class TestDraftRefinementRoute:
    def test_bullet_proposal_normalized(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            assert context_set.get("refinement_note") == "punch up the billing bullet"
            assert context_set.get("jd_text", "").startswith("Senior PM")
            return {
                "target_kind": "bullet",
                "experience_id": s.eid,
                "supersedes_bullet_id": s.bid,
                "text": "Led the billing rewrite end to end, cutting churn.",
                "pattern_kind": "xyz",
                "rationale": "Sharpens the existing bullet with the outcome already on file.",
            }

        with patch("analyzer.draft_surgical_refinement", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-refinement",
                json={"context_path": s.ctx_path, "note": "punch up the billing bullet"},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        proposal = r.get_json()["proposal"]
        assert proposal["target_kind"] == "bullet"
        assert proposal["experience_id"] == s.eid
        assert proposal["supersedes_bullet_id"] == s.bid
        assert proposal["text"] == "Led the billing rewrite end to end, cutting churn."
        assert proposal["pattern_kind"] == "xyz"

        # A pure read — the context file is untouched.
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert "refinement_note" not in ctx
        assert "jd_text" not in ctx
        assert "composition_overrides" not in ctx

    def test_summary_proposal_normalized(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "target_kind": "summary",
                "text": "A billing-platform PM who ships fast, grounded work.",
                "rationale": "Reframes the existing positioning per the note.",
            }

        with patch("analyzer.draft_surgical_refinement", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-refinement",
                json={"context_path": s.ctx_path, "note": "make the summary punchier"},
            )
        assert r.status_code == 200
        proposal = r.get_json()["proposal"]
        assert proposal["target_kind"] == "summary"
        assert proposal["experience_id"] is None
        assert proposal["text"] == "A billing-platform PM who ships fast, grounded work."

    def test_none_target_kind_returns_null_proposal(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)

        with patch(
            "analyzer.draft_surgical_refinement",
            lambda *a, **k: {"target_kind": "none", "text": ""},
        ):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-refinement",
                json={"context_path": s.ctx_path, "note": "rewrite the whole thing"},
            )
        assert r.status_code == 200
        assert r.get_json()["proposal"] is None

    def test_foreign_experience_drops_to_null_proposal(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "target_kind": "bullet",
                "experience_id": 999999,
                "text": "Foreign role bullet.",
                "pattern_kind": "manual",
            }

        with patch("analyzer.draft_surgical_refinement", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-refinement",
                json={"context_path": s.ctx_path, "note": "note"},
            )
        assert r.status_code == 200
        assert r.get_json()["proposal"] is None

    def test_foreign_supersedes_bullet_dropped_but_proposal_kept(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "target_kind": "bullet",
                "experience_id": s.eid,
                "supersedes_bullet_id": 999999,  # not this experience's bullet
                "text": "A genuinely new bullet.",
                "pattern_kind": "manual",
            }

        with patch("analyzer.draft_surgical_refinement", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-refinement",
                json={"context_path": s.ctx_path, "note": "note"},
            )
        assert r.status_code == 200
        proposal = r.get_json()["proposal"]
        assert proposal is not None
        assert proposal["supersedes_bullet_id"] is None

    def test_404_unknown_application(self, refine_app):
        _app, _output_dir = refine_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/draft-refinement",
            json={"context_path": "/whatever", "note": "note"},
        )
        assert r.status_code == 404

    def test_400_missing_context_path(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{s.aid}/draft-refinement", json={"note": "note"})
        assert r.status_code == 400

    def test_400_missing_note(self, refine_app):
        _app, output_dir = refine_app
        s = _seed_refine(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/draft-refinement",
            json={"context_path": s.ctx_path},
        )
        assert r.status_code == 400

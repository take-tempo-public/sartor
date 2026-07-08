"""Tests for the /accept-refinement route (item (a) accept half).

Generation-experience re-architecture item (a) (fix/surgical-refinement-and-loopback):
ACCEPT a surgical-refinement proposal ->
  "bullet": a real Bullet (source='llm_proposed:refine:<key>', is_pending_review=1)
    on its experience, folded into composition_overrides.accepted_generated_bullet_ids,
    and — when the proposal named a supersedes_bullet_id — that bullet excluded too
    (composition_overrides.excluded), so the composition gains exactly ONE net item.
  "summary": composition_overrides.summary_text set (fresh draft).
Idempotent on the Bullet.source key, like gap_fill_decide. RETIRE never reaches the
server (nothing was written yet) — the Compose banner dismisses it client-side, so
there is no retire route to test here.

The draft half lives in test_draft_surgical_refinement.py.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest


@pytest.fixture
def refine_app(tmp_path, monkeypatch):
    db_file = tmp_path / "acceptrefine.sqlite"
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

    from db.session import init_db

    init_db(db_file)
    return types.SimpleNamespace(app=app), output_dir


def _seed(output_dir):
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
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return types.SimpleNamespace(
        cid=cid, aid=aid, eid=eid, bid=bid, run_pk=run_pk, ctx_path=str(ctx_path)
    )


def _bullets_with_source(source):
    from db.models import Bullet
    from db.session import get_session

    session = get_session()
    try:
        return session.query(Bullet).filter_by(source=source).all()
    finally:
        session.close()


class TestAcceptRefinementBullet:
    def test_accept_new_bullet_no_supersede(self, refine_app):
        from db.models import ProposalReview
        from db.session import get_session

        _app, output_dir = refine_app
        s = _seed(output_dir)
        proposal = {
            "target_kind": "bullet",
            "experience_id": s.eid,
            "supersedes_bullet_id": None,
            "text": "Mentored 3 junior engineers on the platform team.",
            "pattern_kind": "manual",
            "rationale": "Surfaces a confirmed leadership fact.",
        }
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        new_id = body["accepted_bullet_id"]
        assert new_id in body["accepted_generated_bullet_ids"]
        assert body["superseded_bullet_id"] is None

        rows = _bullets_with_source(f"llm_proposed:refine:{_key(s.eid, proposal['text'])}")
        assert len(rows) == 1
        assert rows[0].experience_id == s.eid
        assert rows[0].is_pending_review == 1
        assert rows[0].text == proposal["text"]

        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert new_id in ctx["composition_overrides"]["accepted_generated_bullet_ids"]
        # No supersede -> nothing new in excluded.
        assert ctx["composition_overrides"].get("excluded", []) == []

        session = get_session()
        try:
            pr = session.query(ProposalReview).filter_by(bullet_id=new_id).first()
            assert pr is not None
            assert pr.application_run_id == s.run_pk
            assert pr.decision == "pending"
        finally:
            session.close()

    def test_accept_supersedes_excludes_old_bullet(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        proposal = {
            "target_kind": "bullet",
            "experience_id": s.eid,
            "supersedes_bullet_id": s.bid,
            "text": "Led the billing rewrite end to end, cutting churn.",
            "pattern_kind": "xyz",
        }
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["superseded_bullet_id"] == s.bid

        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        # Exactly ONE net item: the old bullet excluded, the new one accepted —
        # the "scoped single-item change" the design spec calls for.
        assert s.bid in ctx["composition_overrides"]["excluded"]
        assert (
            body["accepted_bullet_id"]
            in ctx["composition_overrides"]["accepted_generated_bullet_ids"]
        )

    def test_accept_is_idempotent(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        proposal = {
            "target_kind": "bullet",
            "experience_id": s.eid,
            "text": "A genuinely new bullet.",
            "pattern_kind": "manual",
        }
        client = _app.app.test_client()
        r1 = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        first_id = r1.get_json()["accepted_bullet_id"]
        r2 = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        assert r2.status_code == 200
        assert r2.get_json()["accepted_bullet_id"] == first_id

        rows = _bullets_with_source(f"llm_proposed:refine:{_key(s.eid, proposal['text'])}")
        assert len(rows) == 1
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["accepted_generated_bullet_ids"].count(first_id) == 1

    def test_foreign_experience_400(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        proposal = {
            "target_kind": "bullet",
            "experience_id": 888888,
            "text": "Foreign role bullet.",
        }
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        assert r.status_code == 400


class TestAcceptRefinementSummary:
    def test_accept_summary_persists_text(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        proposal = {"target_kind": "summary", "text": "A sharper positioning line."}
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": proposal},
        )
        assert r.status_code == 200
        assert r.get_json()["summary_text"] == "A sharper positioning line."
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["summary_text"] == "A sharper positioning line."
        assert "summary_text_edited" not in ctx["composition_overrides"]


class TestAcceptRefinementValidation:
    def test_400_missing_proposal(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path},
        )
        assert r.status_code == 400

    def test_400_bad_target_kind(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={
                "context_path": s.ctx_path,
                "proposal": {"target_kind": "rewrite_everything", "text": "x"},
            },
        )
        assert r.status_code == 400

    def test_400_missing_text(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"context_path": s.ctx_path, "proposal": {"target_kind": "summary", "text": ""}},
        )
        assert r.status_code == 400

    def test_404_unknown_application(self, refine_app):
        _app, _output_dir = refine_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/accept-refinement",
            json={"context_path": "/whatever", "proposal": {"target_kind": "summary", "text": "x"}},
        )
        assert r.status_code == 404

    def test_400_missing_context_path(self, refine_app):
        _app, output_dir = refine_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/accept-refinement",
            json={"proposal": {"target_kind": "summary", "text": "x"}},
        )
        assert r.status_code == 400


def _key(experience_id, text):
    import hashlib

    return hashlib.sha256(f"refine:{experience_id}|{text}".encode()).hexdigest()[:12]

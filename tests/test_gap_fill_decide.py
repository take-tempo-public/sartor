"""Tests for the /gap-fill-decide route (Phase 3 accept / retire).

Generation-experience re-architecture Phase 3 (fix/compose-frozen-composition):
ACCEPT a gap-fill proposal → a real Bullet (source='llm_proposed:<key>',
is_pending_review=1) on its experience, its id folded into
composition_overrides.accepted_generated_bullet_ids, and a pending ProposalReview
keyed to the iteration-0 ApplicationRun. RETIRE → the transient proposal is
dropped and no Bullet is ever created. Idempotent on the Bullet.source key.

The draft half lives in test_draft_gap_fill.py.
"""

from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path

import pytest


@pytest.fixture
def gap_app(tmp_path, monkeypatch):
    db_file = tmp_path / "gapdecide.sqlite"
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


def _seed_with_proposal(output_dir, *, experience_id_override=None):
    """Seed candidate + Experience + Bullet + iteration-0 run, plus a context file
    with ONE staged transient gap-fill proposal (as the draft route would write).
    Pass experience_id_override to stage a FOREIGN target (for the 400 path)."""
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

    target_eid = experience_id_override if experience_id_override is not None else eid
    text = "Built Terraform IaC across 3 accounts."
    key = hashlib.sha256(f"{target_eid}|{text}".encode()).hexdigest()[:12]
    ctx = {
        "application_id": aid,
        "application_run_id": run_pk,
        "iteration": 0,
        "run_id": "testrun",
        "llm_gap_fill_proposals": [
            {
                "key": key,
                "experience_id": target_eid,
                "text": text,
                "pattern_kind": "xyz",
                "requirement": "Terraform",
                "evidence": {"bullet_id": bid, "quote": "..."},
                "rationale": "reframes existing infra work",
            }
        ],
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return types.SimpleNamespace(
        cid=cid,
        aid=aid,
        eid=eid,
        bid=bid,
        run_pk=run_pk,
        key=key,
        text=text,
        ctx_path=str(ctx_path),
    )


def _bullets_with_source(source):
    from db.models import Bullet
    from db.session import get_session

    session = get_session()
    try:
        return session.query(Bullet).filter_by(source=source).all()
    finally:
        session.close()


class TestGapFillAccept:
    def test_accept_creates_bullet_and_ledger(self, gap_app):
        from db.models import ProposalReview
        from db.session import get_session

        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)

        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "accept"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        new_id = body["accepted_bullet_id"]
        assert new_id in body["accepted_generated_bullet_ids"]

        # A real pending Bullet on the right experience, keyed by source.
        rows = _bullets_with_source(f"llm_proposed:{s.key}")
        assert len(rows) == 1
        assert rows[0].id == new_id
        assert rows[0].experience_id == s.eid
        assert rows[0].is_pending_review == 1
        assert rows[0].text == s.text

        # ctx: accepted id folded in; the proposal removed from the transient list.
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert new_id in ctx["composition_overrides"]["accepted_generated_bullet_ids"]
        assert ctx["llm_gap_fill_proposals"] == []

        # A pending ProposalReview keyed to the iteration-0 run.
        session = get_session()
        try:
            pr = session.query(ProposalReview).filter_by(bullet_id=new_id).first()
            assert pr is not None
            assert pr.application_run_id == s.run_pk
            assert pr.decision == "pending"
        finally:
            session.close()

    def test_accept_is_idempotent(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)
        client = _app.app.test_client()

        r1 = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "accept"},
        )
        assert r1.status_code == 200
        first_id = r1.get_json()["accepted_bullet_id"]
        # Second accept of the SAME key (proposal already gone from the list) —
        # reuses the existing Bullet, no duplicate.
        r2 = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "accept"},
        )
        assert r2.status_code == 200
        assert r2.get_json()["accepted_bullet_id"] == first_id

        rows = _bullets_with_source(f"llm_proposed:{s.key}")
        assert len(rows) == 1
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["accepted_generated_bullet_ids"].count(first_id) == 1

    def test_accept_unknown_key_404(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": "deadbeefdead", "decision": "accept"},
        )
        assert r.status_code == 404

    def test_accept_foreign_experience_400(self, gap_app):
        _app, output_dir = gap_app
        # Stage a proposal whose experience_id is not this candidate's (a defense-
        # in-depth path the draft route already filters, re-checked on accept).
        s = _seed_with_proposal(output_dir, experience_id_override=888888)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "accept"},
        )
        assert r.status_code == 400
        assert _bullets_with_source(f"llm_proposed:{s.key}") == []


class TestGapFillRetire:
    def test_retire_drops_proposal_no_bullet(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        assert r.status_code == 200
        assert r.get_json()["retired"] is True
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        # Proposal gone; no Bullet ever created.
        assert all(p["key"] != s.key for p in ctx["llm_gap_fill_proposals"])
        assert _bullets_with_source(f"llm_proposed:{s.key}") == []

    def test_retire_then_no_redraft(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)
        client = _app.app.test_client()
        client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        # The key REMAINS on the context (now []), so has_gap_fill stays true and
        # the auto-fire latch never re-drafts the retired proposal.
        r = client.get(f"/api/applications/{s.aid}/composition?context_path={s.ctx_path}")
        assert r.get_json()["has_gap_fill"] is True

    def test_missing_key_and_decision_validation(self, gap_app):
        _app, output_dir = gap_app
        s = _seed_with_proposal(output_dir)
        client = _app.app.test_client()
        # Missing key.
        r1 = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "decision": "accept"},
        )
        assert r1.status_code == 400
        # Bad decision.
        r2 = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "maybe"},
        )
        assert r2.status_code == 400

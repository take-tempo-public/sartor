"""Tests for the regenerate-gap-fill affordance + durable `retired_gap_fill_keys`.

Generation-experience re-architecture LATER-branch remainder item (d)
(`feat/regenerate-gap-fill`, see docs/dev/generation-experience-rearchitecture.md
§4/§6 and the RELEASE_CHECKLIST ledger row). Phase 3 (fix/compose-frozen-
composition) shipped drafting + accept/retire for gap-fill bullets but the
retire was TRANSIENT — a re-draft could resurface a proposal the user had just
rejected. This branch adds:

  - `composition_overrides.retired_gap_fill_keys` — a durable set of retired
    proposal keys (sha256(eid|text)[:12]), written directly by /gap-fill-decide
    (retire) and re-sent by the client on every /composition save (the
    wholesale-rebuild clobber invariant every other override key follows).
  - POST /draft-gap-fill (the SAME route the auto-fire uses, now also the
    explicit "Regenerate suggestions" trigger) filters its normalized proposals
    against BOTH the durable retired-keys set AND any key already realized as
    an accepted Bullet (source='llm_proposed:<key>') for this candidate — so a
    regenerate never resurfaces a proposal the user already decided on, either
    way.

Covers three surfaces:
  - TestDraftGapFillExcludesRetired / TestDraftGapFillExcludesAccepted — the
    route-level exclusion filter (draft half).
  - TestGapFillDecideRetirePersistsKey — /gap-fill-decide (retire) durably
    writes the key (decide half).
  - TestPostCompositionRetiredGapFillKeys — /composition GET/POST surface +
    round-trip the field like every other composition_overrides key.
"""

from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Shared fixture (mirrors tests/test_draft_gap_fill.py + test_gap_fill_decide.py)
# -------------------------------------------------------------------


@pytest.fixture
def gap_app(tmp_path, monkeypatch):
    db_file = tmp_path / "regen_gapfill.sqlite"
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


def _seed(output_dir, *, retired_proposal_text=None, accepted_proposal_text=None):
    """Seed a candidate + Experience + Bullet + iteration-0 run + context file.

    `retired_proposal_text` pre-seeds composition_overrides.retired_gap_fill_keys
    with the key that text (on this seed's experience) hashes to — as a prior
    /gap-fill-decide retire would have left it. `accepted_proposal_text`
    additionally creates a real Bullet with source='llm_proposed:<key>' for that
    text's key — as a prior accept would have. Computed from the real (DB-
    assigned) experience id, so callers never need to pre-seed twice to learn it.
    """
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
        eid = e.id
        b = Bullet(
            experience_id=eid,
            text="Led the billing rewrite.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="official",
            has_outcome=0,
        )
        session.add(b)
        session.flush()
        accepted_key = None
        if accepted_proposal_text:
            accepted_key = hashlib.sha256(f"{eid}|{accepted_proposal_text}".encode()).hexdigest()[
                :12
            ]
            accepted_bullet = Bullet(
                experience_id=eid,
                text="Already-accepted gap-fill bullet.",
                display_order=1,
                is_active=1,
                is_pending_review=1,
                source=f"llm_proposed:{accepted_key}",
                has_outcome=0,
            )
            session.add(accepted_bullet)
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
        cid, aid, bid, run_pk = c.id, a.id, b.id, run.id
    finally:
        session.close()

    retired_key = None
    if retired_proposal_text:
        retired_key = hashlib.sha256(f"{eid}|{retired_proposal_text}".encode()).hexdigest()[:12]

    ctx: dict = {
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
    if retired_key:
        ctx["composition_overrides"] = {"retired_gap_fill_keys": [retired_key]}
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return types.SimpleNamespace(
        cid=cid,
        aid=aid,
        eid=eid,
        bid=bid,
        run_pk=run_pk,
        ctx_path=str(ctx_path),
        retired_key=retired_key,
        accepted_key=accepted_key,
    )


# -------------------------------------------------------------------
# Draft half — the regenerate-side exclusion filter
# -------------------------------------------------------------------


class TestDraftGapFillExcludesRetired:
    def test_retired_key_filtered_out_of_a_fresh_draft(self, gap_app):
        _app, output_dir = gap_app
        proposed_text = "Built Terraform IaC across 3 accounts."
        s = _seed(output_dir, retired_proposal_text=proposed_text)
        key = s.retired_key

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "proposals": [
                    {
                        "experience_id": s.eid,
                        "text": proposed_text,
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
        # The retired key never resurfaces — the proposal is filtered, not just
        # marked; has_gap_fill still flips (the draft ran).
        assert body["proposals"] == []
        assert body["has_gap_fill"] is True
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["llm_gap_fill_proposals"] == []
        # The retired set itself is untouched by a draft (only /gap-fill-decide
        # writes it).
        assert ctx["composition_overrides"]["retired_gap_fill_keys"] == [key]

    def test_unrelated_proposal_still_surfaces_alongside_a_retired_one(self, gap_app):
        _app, output_dir = gap_app
        retired_text = "Built Terraform IaC across 3 accounts."
        fresh_text = "Migrated the billing service to a new region."
        s = _seed(output_dir, retired_proposal_text=retired_text)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "proposals": [
                    {"experience_id": s.eid, "text": retired_text, "pattern_kind": "manual"},
                    {"experience_id": s.eid, "text": fresh_text, "pattern_kind": "manual"},
                ]
            }

        with patch("analyzer.draft_gap_fill_bullets", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-gap-fill",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200
        proposals = r.get_json()["proposals"]
        assert len(proposals) == 1
        assert proposals[0]["text"] == fresh_text


class TestDraftGapFillExcludesAccepted:
    def test_already_accepted_key_filtered_out_of_a_regenerate(self, gap_app):
        _app, output_dir = gap_app
        proposed_text = "Built Terraform IaC across 3 accounts."
        s = _seed(output_dir, accepted_proposal_text=proposed_text)

        def _stub(client, context_set, *, username="", run_id=""):
            return {
                "proposals": [
                    {
                        "experience_id": s.eid,
                        "text": proposed_text,
                        "pattern_kind": "xyz",
                        "requirement": "Terraform",
                    }
                ]
            }

        with patch("analyzer.draft_gap_fill_bullets", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-gap-fill",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200
        # An already-accepted bullet doesn't come back as a "new" suggestion.
        assert r.get_json()["proposals"] == []


# -------------------------------------------------------------------
# Decide half — retire durably persists the key
# -------------------------------------------------------------------


class TestGapFillDecideRetirePersistsKey:
    def _seed_with_proposal(self, output_dir):
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
            aid, eid, bid, run_pk = a.id, e.id, b.id, run.id
        finally:
            session.close()

        text = "Built Terraform IaC across 3 accounts."
        key = hashlib.sha256(f"{eid}|{text}".encode()).hexdigest()[:12]
        ctx = {
            "application_id": aid,
            "application_run_id": run_pk,
            "iteration": 0,
            "run_id": "testrun",
            "llm_gap_fill_proposals": [
                {
                    "key": key,
                    "experience_id": eid,
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
        return types.SimpleNamespace(aid=aid, eid=eid, bid=bid, key=key, ctx_path=str(ctx_path))

    def test_retire_writes_durable_key(self, gap_app):
        _app, output_dir = gap_app
        s = self._seed_with_proposal(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["retired"] is True
        assert body["retired_gap_fill_keys"] == [s.key]
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["retired_gap_fill_keys"] == [s.key]
        # The transient proposal is also gone (unchanged Phase-3 behavior).
        assert ctx["llm_gap_fill_proposals"] == []

    def test_double_retire_is_idempotent_no_duplicate_key(self, gap_app):
        _app, output_dir = gap_app
        s = self._seed_with_proposal(output_dir)
        client = _app.app.test_client()
        client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        r2 = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        assert r2.status_code == 200
        assert r2.get_json()["retired_gap_fill_keys"] == [s.key]

    def test_retire_preserves_other_already_retired_keys(self, gap_app):
        _app, output_dir = gap_app
        s = self._seed_with_proposal(output_dir)
        # Pre-seed a DIFFERENT retired key on the same context.
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {"retired_gap_fill_keys": ["priorkey1234"]}
        Path(s.ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/gap-fill-decide",
            json={"context_path": s.ctx_path, "key": s.key, "decision": "retire"},
        )
        assert r.status_code == 200
        assert set(r.get_json()["retired_gap_fill_keys"]) == {"priorkey1234", s.key}


# -------------------------------------------------------------------
# /composition GET + POST surface (mirrors TestPostComposition in
# tests/test_composition_summary.py, the accepted_generated_bullet_ids pattern)
# -------------------------------------------------------------------


class TestPostCompositionRetiredGapFillKeys:
    def test_persists_and_round_trips(self, gap_app):
        _app, output_dir = gap_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/composition",
            json={
                "context_path": s.ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "retired_gap_fill_keys": ["abc123def456"],
            },
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["retired_gap_fill_keys"] == ["abc123def456"]
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["retired_gap_fill_keys"] == ["abc123def456"]

    def test_omitting_field_does_not_persist(self, gap_app):
        """Backward-compat: an existing caller that doesn't send the new field
        never writes it — the default path stays byte-identical."""
        _app, output_dir = gap_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/composition",
            json={"context_path": s.ctx_path, "pinned": [], "excluded": [], "added": []},
        )
        assert r.status_code == 200
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert "retired_gap_fill_keys" not in ctx["composition_overrides"]

    def test_a_composition_save_without_the_field_drops_a_prior_direct_write(self, gap_app):
        """The clobber-invariant regression this branch's design note warns about:
        /gap-fill-decide writes retired_gap_fill_keys DIRECTLY, but /composition
        rebuilds composition_overrides WHOLESALE — so a save that doesn't resend
        the field silently drops it. This is the exact behavior the client-side
        `_retiredGapFillKeys` mirror + `_collectCompositionState()` inclusion (in
        static/app.js) exists to prevent; this test documents the server-side half
        of that contract."""
        _app, output_dir = gap_app
        s = _seed(output_dir)
        # Simulate the prior direct write /gap-fill-decide (retire) would have
        # made (an arbitrary literal key — no real proposal needed for this test).
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {"retired_gap_fill_keys": ["directwrite1"]}
        Path(s.ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/composition",
            json={"context_path": s.ctx_path, "pinned": [], "excluded": [], "added": []},
        )
        assert r.status_code == 200
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert "retired_gap_fill_keys" not in ctx["composition_overrides"]

    def test_rejects_non_list(self, gap_app):
        _app, output_dir = gap_app
        s = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{s.aid}/composition",
            json={
                "context_path": s.ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "retired_gap_fill_keys": "not-a-list",
            },
        )
        assert r.status_code == 400

    def test_get_surfaces_retired_keys(self, gap_app):
        _app, output_dir = gap_app
        s = _seed(output_dir)
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {"retired_gap_fill_keys": ["seededkey123"]}
        Path(s.ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.get(f"/api/applications/{s.aid}/composition?context_path={s.ctx_path}")
        assert r.status_code == 200
        assert r.get_json()["retired_gap_fill_keys"] == ["seededkey123"]

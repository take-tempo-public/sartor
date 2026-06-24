"""Tests for Phase B.4 proposal critique + decide + clarification promotion.

The LLM calls (critique_proposal, promote_clarification_to_bullet) are
mocked. We test:
- Critique helper assembles inputs correctly and surfaces output
- /api/proposals/<id>/critique persists the critique JSON on the proposal_review row
- /api/proposals/<id>/decide handles accept_original / accept_edit / reject
  for both bullet and title subjects
- Idempotency: redeciding with a different decision is rejected
- /api/clarifications/<id>/promote-to-bullet creates bullet + proposal_review
  with `source='clarification:<id>'`; clarification is flagged is_promoted=1
- Defense-in-depth: routes 404 on missing rows, 400 on bad decisions, 403 on
  cross-candidate access attempts
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from analyzer import critique_proposal

# ---------------------------------------------------------------------------
# Mock client builder
# ---------------------------------------------------------------------------


def _mock_call_llm_factory(captured: dict, response_text: str):
    """Drop-in mock for analyzer._call_llm.

    Records the prompt + kwargs and returns a canned response string.
    """

    def fake(
        client,
        prompt,
        *,
        cached_user_prefix,
        call_kind,
        username,
        run_id,
        system_prompt="",
        **kwargs,
    ):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        captured["model"] = kwargs.get("model")
        captured["call_kind"] = call_kind
        return response_text

    return fake


# ---------------------------------------------------------------------------
# critique_proposal helper
# ---------------------------------------------------------------------------


class TestCritiqueProposalHelper:
    def test_assembles_prompt_with_all_inputs(self):
        captured: dict = {}
        canned = json.dumps(
            {
                "verdict": "caution",
                "notes": "Verb downgrade from 'Owned' to 'Contributed to' aligns with source.",
                "concerns": ["minor scope-inflation residue: 'across the org' has no source"],
                "suggested_revisions": [],
            }
        )
        with patch("analyzer._call_llm", _mock_call_llm_factory(captured, canned)):
            critique = critique_proposal(
                None,
                original_text="Owned the customer interview program across the org.",
                user_edited_text="Contributed to the customer interview program.",
                subject_kind="bullet",
                experience_context={
                    "company": "Polaris",
                    "official_title": "Senior PM",
                    "start_date": "2022-09",
                    "end_date": None,
                    "location": "Remote",
                    "existing_bullets": ["Led 5-person team shipping the RAG eval framework."],
                },
                clarifications=[("Have you led customer interviews?", "Yes, weekly.")],
                jd_excerpt="Senior PM at Atrium Health Platform...",
            )
        # Output passes through
        assert critique["verdict"] == "caution"
        assert "scope-inflation" in critique["concerns"][0]
        # Inputs all present in the prompt
        assert "Owned the customer interview program" in captured["prompt"]
        assert "Contributed to the customer interview program" in captured["prompt"]
        assert "Polaris" in captured["prompt"]
        assert "Atrium" in captured["prompt"]
        assert "Have you led customer interviews?" in captured["prompt"]
        # Uses Haiku
        from analyzer import HAIKU_MODEL

        assert captured["model"] == HAIKU_MODEL

    def test_no_edit_path_says_so_in_prompt(self):
        captured: dict = {}
        canned = json.dumps(
            {
                "verdict": "risky",
                "notes": "Fabricated specifics.",
                "concerns": ["'24 clinicians' has no source"],
            }
        )
        with patch("analyzer._call_llm", _mock_call_llm_factory(captured, canned)):
            critique_proposal(
                None,
                original_text="Interviewed 24 clinicians.",
                user_edited_text=None,
                subject_kind="bullet",
                experience_context={"company": "X", "existing_bullets": []},
            )
        assert "has not edited" in captured["prompt"]

    def test_missing_required_key_triggers_validation_error(self):
        from analyzer import LLMResponseError

        captured: dict = {}
        # Response missing 'concerns'
        canned = json.dumps({"verdict": "good", "notes": "Looks fine."})
        with patch("analyzer._call_llm", _mock_call_llm_factory(captured, canned)):
            with pytest.raises(LLMResponseError):
                critique_proposal(
                    None,
                    original_text="x",
                    user_edited_text=None,
                    subject_kind="bullet",
                    experience_context={"company": "X", "existing_bullets": []},
                )


# ---------------------------------------------------------------------------
# Route tests — shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def b4_app(tmp_path, monkeypatch):
    """Factory-built app (CORPUS_BACKED=1) on a fresh DB path (Sprint 8.3d).

    The proposal critique/decide/promote routes moved to
    blueprints/corpus/proposals and read current_app.config at request time, so
    create_app(Config(base_dir=tmp_path)) replaces the old reload +
    monkeypatch-the-globals pattern. Returns the Flask app; tests seed the DB
    directly via _seed_b4 against the same tmp_path/"b4.sqlite". The DB-path
    monkeypatch stays.
    """
    monkeypatch.setenv("CORPUS_BACKED", "1")
    db_file = tmp_path / "b4.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    return app


def _seed_b4(db_path: Path) -> dict[str, int]:
    """Insert a candidate + experience + bullet (canonical) + proposed bullet
    + proposed title + application + application_run + 2 proposal_review rows.
    Returns IDs the route tests need.
    """
    from db.models import (
        Application,
        ApplicationRun,
        Bullet,
        Candidate,
        Experience,
        ExperienceTitle,
        ProposalReview,
    )
    from db.session import init_db, make_engine, make_session_factory

    init_db(db_path)
    engine = make_engine(db_path)
    session = make_session_factory(engine)()
    try:
        c = Candidate(username="alice", name="Alice")
        session.add(c)
        session.flush()
        e = Experience(
            candidate_id=c.id,
            company="Polaris",
            start_date="2022-09",
            end_date=None,
            location="Remote",
        )
        session.add(e)
        session.flush()
        official = ExperienceTitle(
            experience_id=e.id,
            title="Senior PM",
            is_official=1,
            is_pending_review=0,
            source="official",
        )
        session.add(official)
        canonical = Bullet(
            experience_id=e.id,
            text="Led 5-person eval framework team.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
            has_outcome=1,
        )
        session.add(canonical)
        # The two pending proposals
        proposed_bullet = Bullet(
            experience_id=e.id,
            text="Owned hospital ops customer interview cadence.",
            display_order=1,
            is_active=1,
            is_pending_review=1,
            source="llm_proposed:test_run",
            pattern_kind="car",
        )
        session.add(proposed_bullet)
        proposed_title = ExperienceTitle(
            experience_id=e.id,
            title="Provider Workflows PM",
            is_official=0,
            truthful_enough_to_use=0,
            is_pending_review=1,
            source="llm_proposed:test_run",
        )
        session.add(proposed_title)
        session.flush()

        app_row = Application(
            candidate_id=c.id,
            title="x",
            jd_text="JD: Senior PM, Provider Workflows. Hybrid Boston.",
            jd_fingerprint="abcd",
        )
        session.add(app_row)
        session.flush()
        run = ApplicationRun(
            application_id=app_row.id,
            iteration=0,
            run_id="test_run",
            prompt_version="2026-05-12.1",
            corpus_snapshot_json="{}",
        )
        session.add(run)
        session.flush()

        pr_bullet = ProposalReview(
            application_run_id=run.id,
            bullet_id=proposed_bullet.id,
            original_text=proposed_bullet.text,
            decision="pending",
        )
        pr_title = ProposalReview(
            application_run_id=run.id,
            experience_title_id=proposed_title.id,
            original_text=proposed_title.title,
            decision="pending",
        )
        session.add_all([pr_bullet, pr_title])
        session.commit()

        return {
            "candidate_id": c.id,
            "experience_id": e.id,
            "canonical_bullet_id": canonical.id,
            "proposed_bullet_id": proposed_bullet.id,
            "proposed_title_id": proposed_title.id,
            "official_title_id": official.id,
            "run_id": run.id,
            "pr_bullet_id": pr_bullet.id,
            "pr_title_id": pr_title.id,
        }
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# /api/proposals/<id>/critique
# ---------------------------------------------------------------------------


class TestCritiqueRoute:
    def test_critique_route_persists_response(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        fake_critique = {
            "verdict": "risky",
            "notes": "Fabricates healthcare/clinical context.",
            "concerns": ["'hospital ops' invents a domain Casey's corpus doesn't support"],
        }
        with (
            patch("analyzer.critique_proposal", return_value=fake_critique),
            patch("blueprints.corpus.proposals._get_client", return_value=object()),
        ):
            client = b4_app.test_client()
            r = client.post(
                f"/api/proposals/{ids['pr_bullet_id']}/critique",
                json={"user_edited_text": None},
            )
        assert r.status_code == 200
        body = r.get_json()
        assert body["critique"] == fake_critique
        assert body["subject_kind"] == "bullet"

        # Re-read DB and verify llm_critique_json landed
        from db.models import ProposalReview
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            pr = s.query(ProposalReview).filter_by(id=ids["pr_bullet_id"]).first()
            saved = json.loads(pr.llm_critique_json)
            assert saved["verdict"] == "risky"
        finally:
            s.close()
            engine.dispose()

    def test_critique_route_404_when_missing(self, b4_app, tmp_path):
        _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post("/api/proposals/99999/critique", json={})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# /api/proposals/<id>/decide
# ---------------------------------------------------------------------------


class TestDecideRoute:
    def test_accept_original_clears_pending_on_bullet(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "accept_original"},
        )
        assert r.status_code == 200, r.get_json()
        from db.models import Bullet, ProposalReview
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            b = s.query(Bullet).filter_by(id=ids["proposed_bullet_id"]).first()
            assert b.is_pending_review == 0
            assert b.is_active == 1
            pr = s.query(ProposalReview).filter_by(id=ids["pr_bullet_id"]).first()
            assert pr.decision == "accept_original"
            assert pr.decided_at is not None
        finally:
            s.close()
            engine.dispose()

    def test_accept_edit_updates_bullet_text(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={
                "decision": "accept_edit",
                "user_edited_text": "Established weekly customer interview cadence.",
            },
        )
        assert r.status_code == 200
        from db.models import Bullet
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            b = s.query(Bullet).filter_by(id=ids["proposed_bullet_id"]).first()
            assert b.text == "Established weekly customer interview cadence."
            assert b.is_pending_review == 0
        finally:
            s.close()
            engine.dispose()

    def test_reject_soft_deletes_bullet(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "reject"},
        )
        assert r.status_code == 200
        from db.models import Bullet
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            b = s.query(Bullet).filter_by(id=ids["proposed_bullet_id"]).first()
            assert b.is_active == 0  # soft-deleted
            assert b.is_pending_review == 0
        finally:
            s.close()
            engine.dispose()

    def test_accept_original_on_title_marks_truthful_enough(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_title_id']}/decide",
            json={"decision": "accept_original"},
        )
        assert r.status_code == 200
        from db.models import ExperienceTitle
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            t = s.query(ExperienceTitle).filter_by(id=ids["proposed_title_id"]).first()
            assert t.is_pending_review == 0
            assert t.truthful_enough_to_use == 1
            assert t.is_official == 0  # never promoted to official
        finally:
            s.close()
            engine.dispose()

    def test_reject_title_keeps_it_in_db_but_non_eligible(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_title_id']}/decide",
            json={"decision": "reject"},
        )
        assert r.status_code == 200
        from db.models import ExperienceTitle
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            t = s.query(ExperienceTitle).filter_by(id=ids["proposed_title_id"]).first()
            assert t is not None  # still in DB (audit)
            assert t.is_pending_review == 0
            assert t.truthful_enough_to_use == 0
            assert t.is_official == 0
        finally:
            s.close()
            engine.dispose()

    def test_invalid_decision_returns_400(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "rubber_stamp"},
        )
        assert r.status_code == 400

    def test_accept_edit_requires_user_edited_text(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "accept_edit", "user_edited_text": "   "},
        )
        assert r.status_code == 400

    def test_re_deciding_with_different_decision_returns_409(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "reject"},
        )
        # Try to flip
        r = client.post(
            f"/api/proposals/{ids['pr_bullet_id']}/decide",
            json={"decision": "accept_original"},
        )
        assert r.status_code == 409
        assert "already decided" in r.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# /api/clarifications/<id>/promote-to-bullet
# ---------------------------------------------------------------------------


class TestPromoteClarificationRoute:
    def test_promote_with_user_text_skips_llm(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        # Add a clarification
        from db.models import Clarification
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            clar = Clarification(
                candidate_id=ids["candidate_id"],
                question="Have you run customer interviews?",
                answer="Yes, weekly with the platform team.",
                kind="experience_probe",
            )
            s.add(clar)
            s.commit()
            clar_id = clar.id
        finally:
            s.close()
            engine.dispose()

        client = b4_app.test_client()
        r = client.post(
            f"/api/clarifications/{clar_id}/promote-to-bullet",
            json={
                "experience_id": ids["experience_id"],
                "user_text": "Ran weekly customer interviews with the platform team.",
            },
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["text"] == "Ran weekly customer interviews with the platform team."

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            from db.models import Bullet, ProposalReview

            new_b = s.query(Bullet).filter_by(id=body["bullet_id"]).first()
            assert new_b.is_pending_review == 1
            assert new_b.source == f"clarification:{clar_id}"
            assert new_b.experience_id == ids["experience_id"]
            # ProposalReview anchored to the recent run
            prs = s.query(ProposalReview).filter_by(bullet_id=new_b.id).all()
            assert len(prs) == 1
            assert prs[0].decision == "pending"
            # Clarification flagged
            c = s.query(Clarification).filter_by(id=clar_id).first()
            assert c.is_promoted_to_bullet == 1
        finally:
            s.close()
            engine.dispose()

    def test_promote_calls_llm_when_no_user_text(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        from db.models import Clarification
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            clar = Clarification(
                candidate_id=ids["candidate_id"],
                question="Yes/no — used Kubernetes?",
                answer="Yes, briefly on a side project — about 18 months ago, 3-node cluster.",
                kind="experience_probe",
            )
            s.add(clar)
            s.commit()
            clar_id = clar.id
        finally:
            s.close()
            engine.dispose()

        fake_llm = {
            "text": "Operated a 3-node Kubernetes cluster on a side project for 18 months.",
            "pattern_kind": "manual",
            "rationale": "Past-tense action verb; preserves all stated specifics.",
        }
        with (
            patch("analyzer.promote_clarification_to_bullet", return_value=fake_llm),
            patch("blueprints.corpus.proposals._get_client", return_value=object()),
        ):
            client = b4_app.test_client()
            r = client.post(
                f"/api/clarifications/{clar_id}/promote-to-bullet",
                json={"experience_id": ids["experience_id"]},
            )
        assert r.status_code == 200
        body = r.get_json()
        assert body["text"] == fake_llm["text"]
        assert body["pattern_kind"] == "manual"

    def test_promote_404_when_clarification_missing(self, b4_app, tmp_path):
        ids = _seed_b4(tmp_path / "b4.sqlite")
        client = b4_app.test_client()
        r = client.post(
            "/api/clarifications/99999/promote-to-bullet",
            json={"experience_id": ids["experience_id"], "user_text": "x"},
        )
        assert r.status_code == 404

    def test_promote_404_when_experience_belongs_to_other_candidate(self, b4_app, tmp_path):
        """Defense-in-depth: the route must verify the experience belongs to
        the same candidate as the clarification. Cross-tenant write attempt = 404."""
        ids = _seed_b4(tmp_path / "b4.sqlite")
        from db.models import Candidate, Clarification, Experience
        from db.session import make_engine, make_session_factory

        engine = make_engine(tmp_path / "b4.sqlite")
        s = make_session_factory(engine)()
        try:
            # Second candidate's experience
            c2 = Candidate(username="bob", name="Bob")
            s.add(c2)
            s.flush()
            e2 = Experience(candidate_id=c2.id, company="Other", start_date="2019-01")
            s.add(e2)
            s.flush()
            # Alice's clarification
            clar = Clarification(
                candidate_id=ids["candidate_id"],
                question="?",
                answer="x",
                kind="manual",
            )
            s.add(clar)
            s.commit()
            clar_id = clar.id
            other_exp_id = e2.id
        finally:
            s.close()
            engine.dispose()

        # Add bob.config so _safe_username doesn't preemptively 403
        (tmp_path / "configs" / "bob.config").write_text("{}", encoding="utf-8")

        client = b4_app.test_client()
        r = client.post(
            f"/api/clarifications/{clar_id}/promote-to-bullet",
            json={"experience_id": other_exp_id, "user_text": "Attempted cross-tenant."},
        )
        assert r.status_code == 404

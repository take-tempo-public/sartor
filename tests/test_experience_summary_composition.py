"""Tests for B.4 (Sprint 6.6) per-role intro wiring into composition + generate.

- GET /composition surfaces a per-experience `summary` block (variants +
  recommended + chosen) and the top-level use_experience_summaries toggle.
- POST /composition persists use_experience_summaries +
  chosen_experience_summary_ids; rejects foreign/inactive picks; accepts the
  sentinel 0 (explicitly cleared).
- _apply_chosen_experience_summaries patches the career_corpus snapshot
  (generate path), opt-in gated.
- _build_generate_prompt is byte-identical for a corpus with no chosen intros
  (the analyze→generate cache is preserved for non-users).
"""

from __future__ import annotations

import json

import pytest

# _apply_chosen_experience_summaries moved to blueprints/generation.py (8.3c);
# the /composition route tests below still exercise the un-moved compose route
# via the app module (`_app`), so only the direct helper calls retarget here.
import blueprints.generation as bgen


@pytest.fixture
def comp_app(tmp_path, monkeypatch):
    import types

    db_file = tmp_path / "expcomp.sqlite"
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

    from db.session import init_db

    init_db(db_file)
    return types.SimpleNamespace(app=app), output_dir


def _seed(output_dir, *, ctx_extra=None):
    """Candidate + application + one experience with two intro variants.
    Returns (candidate_id, application_id, experience_id, [variant_ids], ctx_path)."""
    from db.models import (
        Application,
        Candidate,
        Experience,
        ExperienceSummaryItem,
        ExperienceTitle,
    )
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title="Senior PM",
            jd_text="Senior PM building AI platforms.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.flush()
        e = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
        session.add(e)
        session.flush()
        session.add(
            ExperienceTitle(experience_id=e.id, title="Lead PM", is_official=1, source="official")
        )
        vids = []
        for i, text in enumerate(["Platform-scale framing.", "Growth-builder framing."]):
            si = ExperienceSummaryItem(experience_id=e.id, text=text, display_order=i, is_active=1)
            session.add(si)
            session.flush()
            vids.append(si.id)
        session.commit()
        cid, aid, eid = c.id, a.id, e.id
    finally:
        session.close()

    ctx = {
        "application_id": aid,
        "iteration": 0,
        "llm_analysis": {"essential_skills": ["ai-platform"]},
    }
    if ctx_extra:
        ctx.update(ctx_extra)
    ctx_path = output_dir / "casey" / "ctx0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, eid, vids, str(ctx_path)


class TestGetComposition:
    def test_surfaces_per_role_summary_block(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, eid, vids, ctx_path = _seed(output_dir)
        # Rewrite the context with a recommendation + a per-role pick (eid/vids
        # aren't known until after _seed returns).
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        ctx["llm_experience_summary_recommendations"] = {
            "recommendations": [
                {
                    "experience_id": eid,
                    "summary_item_id": vids[1],
                    "rationale": "growth fits",
                    "alternates": [],
                },
            ]
        }
        ctx["composition_overrides"] = {
            "use_experience_summaries": True,
            "chosen_experience_summary_ids": {str(eid): vids[0]},
        }
        open(ctx_path, "w", encoding="utf-8").write(json.dumps(ctx))
        client = _app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition?context_path={ctx_path}")
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["use_experience_summaries"] is True
        exp = next(e for e in body["experiences"] if e["id"] == eid)
        block = exp["summary"]
        assert block["recommended_id"] == vids[1]
        assert block["chosen_id"] == vids[0]
        by_id = {v["id"]: v for v in block["variants"]}
        assert by_id[vids[1]]["recommended"] is True
        assert by_id[vids[1]]["rationale"] == "growth fits"
        assert by_id[vids[0]]["chosen"] is True

    def test_defaults_off_no_recommendation(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, eid, vids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition?context_path={ctx_path}")
        body = r.get_json()
        assert body["use_experience_summaries"] is False
        exp = next(e for e in body["experiences"] if e["id"] == eid)
        assert exp["summary"]["chosen_id"] is None
        assert exp["summary"]["recommended_id"] is None
        assert len(exp["summary"]["variants"]) == 2


class TestPostComposition:
    def test_persists_toggle_and_picks(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, eid, vids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): vids[0]},
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        ov = ctx["composition_overrides"]
        assert ov["use_experience_summaries"] is True
        assert ov["chosen_experience_summary_ids"] == {str(eid): vids[0]}

    def test_sentinel_zero_accepted(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, eid, _vids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): 0},  # cleared
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        ctx = json.loads(open(ctx_path, encoding="utf-8").read())
        assert ctx["composition_overrides"]["chosen_experience_summary_ids"] == {str(eid): 0}

    def test_foreign_experience_rejected(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, _eid, vids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {"9999": vids[0]},
            },
        )
        assert r.status_code == 400

    def test_variant_from_other_role_rejected(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, eid, vids, ctx_path = _seed(output_dir)
        # Add a second experience + variant; pin THAT variant under eid → 400.
        from db.models import Experience, ExperienceSummaryItem
        from db.session import get_session

        session = get_session()
        try:
            other = Experience(candidate_id=_cid, company="Beta", start_date="2018-01")
            session.add(other)
            session.flush()
            foreign = ExperienceSummaryItem(experience_id=other.id, text="Foreign.", is_active=1)
            session.add(foreign)
            session.commit()
            foreign_id = foreign.id
        finally:
            session.close()
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): foreign_id},
            },
        )
        assert r.status_code == 400


class TestApplyChosenToSnapshot:
    def test_injects_chosen_text_when_opted_in(self, comp_app):
        _app, output_dir = comp_app
        _cid, _aid, eid, vids, _ctx_path = _seed(output_dir)
        ctx = {
            "application_id": _aid,
            "career_corpus": [{"id": eid, "company": "Acme", "bullets": []}],
            "composition_overrides": {
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): vids[0]},
            },
        }
        bgen._apply_chosen_experience_summaries(ctx)
        assert ctx["career_corpus"][0]["summary"] == "Platform-scale framing."

    def test_noop_when_toggle_off(self, comp_app):
        _app, output_dir = comp_app
        _cid, _aid, eid, vids, _ctx_path = _seed(output_dir)
        ctx = {
            "application_id": _aid,
            "career_corpus": [{"id": eid, "company": "Acme", "bullets": []}],
            "composition_overrides": {
                # toggle OFF — picks present but must NOT be applied
                "chosen_experience_summary_ids": {str(eid): vids[0]},
            },
        }
        bgen._apply_chosen_experience_summaries(ctx)
        assert "summary" not in ctx["career_corpus"][0]


class TestGeneratePromptByteIdentity:
    """The default (no chosen intro) generate prompt must be byte-identical —
    no <summary> element in the cached user-prefix, no role-intro guide text in
    the task prompt — so the analyze→generate cache is never disturbed for users
    who don't opt in. The <summary> element is emitted by _stable_user_prefix
    (the cached prefix); the guide rides in _build_generate_prompt's task block.
    """

    def _ctx(self, *, with_summary):
        exp = {
            "id": 1,
            "company": "Acme",
            "start_date": "2021-01",
            "end_date": None,
            "eligible_titles": [],
            "bullets": [{"id": 7, "text": "Shipped a platform.", "tags": [], "has_outcome": True}],
        }
        if with_summary:
            exp["summary"] = "Owned platform scale across teams."
        return {
            "job_description": "Senior PM.",
            "candidate": {"name": "Casey", "profile_text": ""},
            "career_corpus": [exp],
            "iteration": 0,
        }

    def test_prefix_byte_identical_when_no_summary(self):
        """A corpus with no `summary` key produces the same cached prefix as one
        where summary is empty — no leakage, cache preserved for non-users."""
        from analyzer import _stable_user_prefix

        no_key = self._ctx(with_summary=False)
        empty = self._ctx(with_summary=False)
        empty["career_corpus"][0]["summary"] = ""
        assert _stable_user_prefix(no_key) == _stable_user_prefix(empty)
        assert "<summary>" not in _stable_user_prefix(no_key)

    def test_no_summary_task_prompt_omits_guide(self):
        from analyzer import _build_generate_prompt

        prompt, _ = _build_generate_prompt(self._ctx(with_summary=False), {})
        assert "optional <summary> element" not in prompt

    def test_summary_present_emits_element_and_guide(self):
        from analyzer import _build_generate_prompt, _stable_user_prefix

        ctx = self._ctx(with_summary=True)
        assert "<summary>Owned platform scale across teams.</summary>" in _stable_user_prefix(ctx)
        prompt, _ = _build_generate_prompt(ctx, {})
        assert "optional <summary> element" in prompt

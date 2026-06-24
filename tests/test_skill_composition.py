"""Tests for B.5 skill curation in the composition GET/POST + the generate-time
apply helper (Sprint 6.6).

  - TestGetComposition — the `skills` block: active+approved items, recommend
    ordering + pin/exclude flags, the effective chosen_ids, the pending lane.
  - TestPostComposition — persists pinned/excluded/skill_order; rejects a
    foreign pinned id; omits empty fields (byte-identical default path).
  - TestApplyRecommendedSkills — patches candidate['skills'] to the curated set
    at generate time; no-op (byte-identical) when no recommendation/overrides.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# _apply_recommended_skills moved to blueprints/generation.py (8.3c); the
# /composition route tests below still exercise the un-moved compose route via
# the app module (`_app`), so only the direct helper calls retarget here.
import blueprints.generation as bgen


@pytest.fixture
def comp_app(tmp_path, monkeypatch):
    """Factory-built app (Sprint 8.3f) — the composition routes moved to
    blueprints/applications.py and read current_app.config[...]; the DB-path
    monkeypatch stays. Preserves the `(namespace, output_dir)` 2-tuple shape."""
    import types

    db_file = tmp_path / "skillcomp.sqlite"
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


def _seed(output_dir, *, overrides=None, recommendation=None):
    from db.models import Application, Candidate, Skill
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(candidate_id=c.id, title="SRE", jd_text="SRE.", jd_fingerprint="f" * 16)
        session.add(a)
        session.flush()
        ids = {}
        for i, name in enumerate(["Python", "Go", "Kubernetes"]):
            sk = Skill(
                candidate_id=c.id,
                name=name,
                display_order=i,
                is_active=1,
                is_pending_review=0,
                source="imported",
            )
            session.add(sk)
            session.flush()
            ids[name] = sk.id
        # A pending suggestion to surface in the lane.
        pend = Skill(
            candidate_id=c.id,
            name="Rust",
            display_order=3,
            is_active=1,
            is_pending_review=1,
            source="llm_proposed",
        )
        session.add(pend)
        session.flush()
        ids["Rust"] = pend.id
        session.commit()
        cid, aid = c.id, a.id
    finally:
        session.close()

    ctx = {"application_id": aid}
    if overrides is not None:
        ctx["composition_overrides"] = overrides
    if recommendation is not None:
        ctx["llm_skill_recommendations"] = {"recommendation": recommendation}
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, ids, str(ctx_path)


class TestGetComposition:
    def test_surfaces_skill_block_with_default_order(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, ids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition?context_path={ctx_path}")
        assert r.status_code == 200
        skills = r.get_json()["skills"]
        # Active+approved skills only in the items list (no pending Rust).
        assert [it["name"] for it in skills["items"]] == ["Python", "Go", "Kubernetes"]
        # No recommendation yet → chosen_ids is all-active in display order.
        assert skills["chosen_ids"] == [ids["Python"], ids["Go"], ids["Kubernetes"]]
        assert skills["has_recommendation"] is False
        # Pending suggestion surfaces in the review lane.
        assert [p["name"] for p in skills["pending"]] == ["Rust"]

    def test_reflects_recommendation_and_overrides(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, ids, ctx_path = _seed(output_dir)
        # Write a recommendation + exclusion referencing the real seeded ids.
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        ctx["llm_skill_recommendations"] = {
            "recommendation": {"skill_ids": [ids["Kubernetes"], ids["Python"]]},
        }
        ctx["composition_overrides"] = {"excluded_skill_ids": [ids["Kubernetes"]]}
        with open(ctx_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(ctx))

        client = _app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition?context_path={ctx_path}")
        skills = r.get_json()["skills"]
        assert skills["has_recommendation"] is True
        # recommended [Kubernetes, Python] minus excluded {Kubernetes} → [Python]
        assert skills["chosen_ids"] == [ids["Python"]]
        by_id = {it["id"]: it for it in skills["items"]}
        assert by_id[ids["Python"]]["recommended"] is True
        assert by_id[ids["Kubernetes"]]["excluded"] is True


class TestPostComposition:
    def test_persists_skill_overrides(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, ids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned_skill_ids": [ids["Go"]],
                "excluded_skill_ids": [ids["Python"]],
                "skill_order": [ids["Kubernetes"], ids["Go"]],
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        ov = ctx["composition_overrides"]
        assert ov["pinned_skill_ids"] == [ids["Go"]]
        assert ov["excluded_skill_ids"] == [ids["Python"]]
        assert ov["skill_order"] == [ids["Kubernetes"], ids["Go"]]

    def test_empty_fields_omitted(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, _ids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{aid}/composition", json={"context_path": ctx_path})
        assert r.status_code == 200
        ov = json.loads(Path(ctx_path).read_text(encoding="utf-8"))["composition_overrides"]
        # Byte-identical default path: no skill keys persisted.
        assert "pinned_skill_ids" not in ov
        assert "excluded_skill_ids" not in ov
        assert "skill_order" not in ov

    def test_foreign_pinned_skill_rejected(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, _ids, ctx_path = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned_skill_ids": [99999],
            },
        )
        assert r.status_code == 400


class TestApplyRecommendedSkills:
    def test_patches_candidate_skills_to_curated_set(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, ids, _ctx_path = _seed(output_dir)
        ctx = {
            "application_id": aid,
            "candidate": {"skills": ["Python", "Go", "Kubernetes"]},
            "llm_skill_recommendations": {
                "recommendation": {"skill_ids": [ids["Kubernetes"], ids["Python"]]},
            },
            "composition_overrides": {"excluded_skill_ids": [ids["Python"]]},
        }
        bgen._apply_recommended_skills(ctx)
        # recommended [K, Py] minus excluded {Py} → [Kubernetes]
        assert ctx["candidate"]["skills"] == ["Kubernetes"]

    def test_noop_when_no_recommendation_or_overrides(self, comp_app):
        _app, output_dir = comp_app
        _cid, aid, _ids, _ctx_path = _seed(output_dir)
        before = ["Python", "Go", "Kubernetes"]
        ctx = {"application_id": aid, "candidate": {"skills": list(before)}}
        bgen._apply_recommended_skills(ctx)
        # Byte-identical: untouched when nothing to apply.
        assert ctx["candidate"]["skills"] == before

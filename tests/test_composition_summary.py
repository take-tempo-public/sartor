"""Tests for the β.6c extensions to /api/applications/<id>/composition.

GET returns a `summary` block alongside `experiences`:
  {
    "variants": [{id, text, label, has_outcome, recommended, pinned, rationale}],
    "recommended_id": int | null,
    "pinned_id":      int | null,
    "chosen_id":      int | null,   # pinned wins → recommended → null
    "has_recommendation": bool,
  }

POST accepts an optional `pinned_summary_id` that persists into
`context_set["composition_overrides"]["pinned_summary_id"]`.

Helper `_read_summary_overrides` reads (summary_recommendation,
pinned_summary_id) from a context file with the same _within
guard the bullet overrides use.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def composition_app(tmp_path, monkeypatch):
    """Factory-built app (Sprint 8.3f) — the composition routes moved to
    blueprints/applications.py and read current_app.config[...]; the DB-path
    monkeypatch stays. Preserves the `(namespace, output_dir)` 2-tuple shape so the
    test bodies (`_app.app`, the passed `output_dir`) keep working."""
    import types

    db_file = tmp_path / "comp.sqlite"
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


def _seed(
    _app,
    output_dir,
    *,
    with_variants: bool = True,
    with_recommendation: bool = False,
    pinned_summary_id: int | None = None,
) -> tuple[int, int, str, list[int]]:
    """Seed candidate + application + (optionally) summary variants.
    Returns (candidate_id, application_id, context_path, [variant_ids])."""
    from db.models import Application, Candidate, SummaryItem
    from db.session import get_session

    session = get_session()
    variant_ids: list[int] = []
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
        if with_variants:
            for i, text in enumerate(
                [
                    "AI platform PM with platform-leadership outcomes.",
                    "Early-stage builder PM focused on launches.",
                    "Enterprise PM with cross-team alignment record.",
                ]
            ):
                si = SummaryItem(
                    candidate_id=c.id,
                    text=text,
                    display_order=i,
                    is_active=1,
                    label=f"Variant {i + 1}",
                )
                session.add(si)
                session.flush()
                variant_ids.append(si.id)
        session.commit()
        cid, aid = c.id, a.id
    finally:
        session.close()

    ctx: dict = {
        "application_id": aid,
        "iteration": 0,
        "llm_analysis": {"essential_skills": ["ai-platform"]},
    }
    if with_recommendation and variant_ids:
        ctx["llm_summary_recommendation"] = {
            "recommendation": {
                "summary_item_id": variant_ids[0],
                "rationale": "Strongest AI platform framing.",
            },
            "alternates": [
                {
                    "summary_item_id": variant_ids[1],
                    "rationale": "Builder framing is a close second.",
                },
            ],
        }
    if pinned_summary_id is not None:
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "pinned_summary_id": pinned_summary_id,
        }

    ctx_path = output_dir / "casey" / "ctx0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, str(ctx_path), variant_ids


# -------------------------------------------------------------------
# GET /api/applications/<id>/composition — summary block
# -------------------------------------------------------------------


class TestGetCompositionSummary:
    def test_returns_summary_block_with_variants(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, vids = _seed(_app, output_dir)

        client = _app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx_path}",
        )
        assert r.status_code == 200
        body = r.get_json()
        summary = body["summary"]
        assert len(summary["variants"]) == 3
        # Variants come back in display_order
        assert [v["id"] for v in summary["variants"]] == vids
        assert summary["has_recommendation"] is False
        assert summary["recommended_id"] is None
        assert summary["pinned_id"] is None
        assert summary["chosen_id"] is None

    def test_recommendation_flagged_on_correct_variant(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, vids = _seed(
            _app,
            output_dir,
            with_recommendation=True,
        )
        client = _app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx_path}",
        )
        body = r.get_json()
        summary = body["summary"]
        assert summary["has_recommendation"] is True
        assert summary["recommended_id"] == vids[0]
        assert summary["chosen_id"] == vids[0]  # no pin → recommendation wins
        # Variant 0 carries recommended=True; others don't
        flags = {v["id"]: v["recommended"] for v in summary["variants"]}
        assert flags[vids[0]] is True
        assert flags[vids[1]] is False
        # Variant 0 + variant 1 both carry rationales (rec + alternate)
        rationales = {v["id"]: v["rationale"] for v in summary["variants"]}
        assert rationales[vids[0]].startswith("Strongest AI")
        assert rationales[vids[1]].startswith("Builder")

    def test_pinned_overrides_recommendation(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, vids = _seed(
            _app,
            output_dir,
            with_recommendation=True,
            pinned_summary_id=None,  # will set below
        )
        # Seed with a pin on variant[1] AND a recommendation on variant[0]
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "pinned_summary_id": vids[1],
        }
        Path(ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx_path}",
        )
        body = r.get_json()
        summary = body["summary"]
        assert summary["recommended_id"] == vids[0]
        assert summary["pinned_id"] == vids[1]
        assert summary["chosen_id"] == vids[1]  # pin wins
        flags = {v["id"]: (v["recommended"], v["pinned"]) for v in summary["variants"]}
        assert flags[vids[0]] == (True, False)
        assert flags[vids[1]] == (False, True)

    def test_no_variants_returns_empty_summary(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, _ = _seed(_app, output_dir, with_variants=False)
        client = _app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx_path}",
        )
        body = r.get_json()
        assert body["summary"]["variants"] == []
        assert body["summary"]["chosen_id"] is None


# -------------------------------------------------------------------
# POST /api/applications/<id>/composition — pinned_summary_id
# -------------------------------------------------------------------


class TestPostComposition:
    def test_persists_pinned_summary_id(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, vids = _seed(_app, output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "pinned_summary_id": vids[2],
            },
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["pinned_summary_id"] == vids[2]

        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["pinned_summary_id"] == vids[2]

    def test_null_clears_pin(self, composition_app):
        _app, output_dir = composition_app
        # Seed with an existing pin we'll then clear via the POST
        _cid, aid, ctx_path, vids = _seed(
            _app,
            output_dir,
            pinned_summary_id=1,  # arbitrary positive value
        )
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "pinned_summary_id": None,
            },
        )
        assert r.status_code == 200
        assert r.get_json()["pinned_summary_id"] is None

    def test_rejects_negative_pinned_summary_id(self, composition_app):
        _app, output_dir = composition_app
        _cid, aid, ctx_path, _ = _seed(_app, output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
                "pinned_summary_id": "not-an-int",
            },
        )
        assert r.status_code == 400

    def test_omitting_pinned_summary_id_does_not_persist(self, composition_app):
        """Backward-compat: existing callers that don't send the new
        field should not have it written to the context."""
        _app, output_dir = composition_app
        _cid, aid, ctx_path, _ = _seed(_app, output_dir)
        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={
                "context_path": ctx_path,
                "pinned": [],
                "excluded": [],
                "added": [],
            },
        )
        assert r.status_code == 200
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        assert "pinned_summary_id" not in ctx["composition_overrides"]

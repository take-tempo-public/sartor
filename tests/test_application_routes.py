"""Tests for the Phase D.3 application list routes."""

from __future__ import annotations

import pytest


@pytest.fixture
def app_app(tmp_path, monkeypatch):
    """Reload app.py against a fresh sqlite DB + temp config dir."""
    db_file = tmp_path / "apps.sqlite"
    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None
    import importlib

    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")

    from db.session import init_db
    init_db(db_file)
    return app_module


def _seed_candidate(username="alice"):
    from db.models import Candidate
    from db.session import get_session
    s = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def _seed_application(candidate_id, title="Senior PM @ Foo", company="Foo Inc",
                     jd_text="Long JD text here.", status="draft"):
    import hashlib

    from db.models import Application
    from db.session import get_session
    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id, title=title, company=company,
            jd_text=jd_text, status=status,
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


def _seed_run(application_id, iteration=0, run_id="abc123def456",
              generated_resume_md=None, ats_roundtrip_json=None,
              generated_cover_letter_md=None, edited_resume_text=None,
              edited_cover_letter_text=None, persona_template_id=None):
    from db.models import ApplicationRun
    from db.session import get_session
    s = get_session()
    try:
        r = ApplicationRun(
            application_id=application_id, iteration=iteration,
            run_id=run_id, prompt_version="2026-05-12.1",
            corpus_snapshot_json="{}",
            generated_resume_md=generated_resume_md,
            generated_cover_letter_md=generated_cover_letter_md,
            edited_resume_text=edited_resume_text,
            edited_cover_letter_text=edited_cover_letter_text,
            persona_template_id=persona_template_id,
            ats_roundtrip_json=ats_roundtrip_json,
        )
        s.add(r)
        s.commit()
        return r.id
    finally:
        s.close()


def _seed_persona(candidate_id=None, name="Classic", path="classic.docx",
                  source="bundled"):
    from db.models import PersonaTemplate
    from db.session import get_session
    s = get_session()
    try:
        p = PersonaTemplate(candidate_id=candidate_id, name=name, path=path,
                            source=source)
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()


def _write_context_file(app_module, username, filename, payload):
    """Write a context_*.json under the (monkeypatched) OUTPUT_DIR/<user> dir.

    Returns the absolute path written. Used to exercise the resume-state
    context rediscovery (D.3.1)."""
    import json

    user_dir = app_module.OUTPUT_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    p = user_dir / filename
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _seed_pending_proposal(application_run_id, bullet_id=None,
                          experience_title_id=None):
    """Seed a pending proposal_review row. Requires that exactly one of
    bullet_id or experience_title_id is non-null (CHECK constraint)."""
    from db.models import ProposalReview
    from db.session import get_session
    s = get_session()
    try:
        p = ProposalReview(
            application_run_id=application_run_id,
            bullet_id=bullet_id,
            experience_title_id=experience_title_id,
            original_text="proposed text",
            decision="pending",
        )
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()


def _seed_bullet_for_proposals(candidate_id):
    """Make a bullet so proposal_review.bullet_id has a real FK target."""
    from db.models import Bullet, Experience
    from db.session import get_session
    s = get_session()
    try:
        e = Experience(candidate_id=candidate_id, company="X",
                       start_date="2020-01", display_order=0)
        s.add(e)
        s.flush()
        b = Bullet(experience_id=e.id, text="bullet", display_order=0,
                   is_active=1, source="manual", has_outcome=0)
        s.add(b)
        s.commit()
        return b.id
    finally:
        s.close()


# ---------------------------------------------------------------------------
# GET /api/users/<u>/applications
# ---------------------------------------------------------------------------


class TestListApplications:
    def test_returns_empty_for_candidate_with_no_apps(self, app_app):
        _seed_candidate()
        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_returns_all_apps_sorted_by_updated_at_desc(self, app_app):
        cid = _seed_candidate()
        a1 = _seed_application(cid, title="App 1")
        a2 = _seed_application(cid, title="App 2", jd_text="Different JD")
        _seed_run(a1, iteration=0)
        _seed_run(a1, iteration=1, run_id="abc123def457")

        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        body = r.get_json()
        assert len(body) == 2
        # Both apps present, with iteration counts
        app1 = next(a for a in body if a["id"] == a1)
        app2 = next(a for a in body if a["id"] == a2)
        assert app1["iteration_count"] == 2
        assert app1["latest_iteration"] == 1
        assert app2["iteration_count"] == 0
        assert app2["latest_iteration"] == 0

    def test_pending_proposal_count(self, app_app):
        cid = _seed_candidate()
        bid = _seed_bullet_for_proposals(cid)
        aid = _seed_application(cid)
        rid = _seed_run(aid)
        _seed_pending_proposal(rid, bullet_id=bid)
        _seed_pending_proposal(rid, bullet_id=bid)

        client = app_app.app.test_client()
        body = client.get("/api/users/alice/applications").get_json()
        assert body[0]["pending_proposals"] == 2

    def test_missing_candidate_returns_200_needs_onboarding(self, app_app):
        # Read precondition unmet → 200 + needs_onboarding (empty list), not a
        # 409 conflict, so the UI shows the import CTA without a console error.
        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        body = r.get_json()
        assert body["needs_onboarding"] is True
        assert body["applications"] == []

    def test_400_when_user_unknown(self, app_app):
        client = app_app.app.test_client()
        r = client.get("/api/users/ghost/applications")
        assert r.status_code == 400

    def test_status_filter_returns_subset(self, app_app):
        # ?status= is the programmatic query surface for the B.8 learning layer.
        cid = _seed_candidate()
        _seed_application(cid, title="Draft app")
        sub = _seed_application(cid, title="Sub app", jd_text="JD two",
                                status="submitted")
        iv = _seed_application(cid, title="Int app", jd_text="JD three",
                               status="interview")

        client = app_app.app.test_client()
        body = client.get("/api/users/alice/applications?status=interview").get_json()
        assert [a["id"] for a in body] == [iv]

        body = client.get(
            "/api/users/alice/applications?status=interview,submitted"
        ).get_json()
        assert {a["id"] for a in body} == {sub, iv}

    def test_status_filter_unknown_value_400(self, app_app):
        _seed_candidate()
        client = app_app.app.test_client()
        r = client.get("/api/users/alice/applications?status=offer")
        assert r.status_code == 400
        assert "offer" in r.get_json()["error"]


# ---------------------------------------------------------------------------
# GET /api/applications/<id>
# ---------------------------------------------------------------------------


class TestGetApplication:
    def test_returns_full_detail_with_runs(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, title="Senior PM @ Foo",
                                jd_text="JD content here")
        _seed_run(aid, iteration=0, generated_resume_md="# Resume")
        _seed_run(aid, iteration=1, run_id="abc123def458",
                  ats_roundtrip_json='{"status": "pass"}')

        client = app_app.app.test_client()
        r = client.get(f"/api/applications/{aid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["title"] == "Senior PM @ Foo"
        assert body["jd_text"] == "JD content here"
        assert body["candidate_username"] == "alice"
        assert len(body["runs"]) == 2
        assert body["runs"][0]["iteration"] == 0
        assert body["runs"][0]["has_resume"] is True
        assert body["runs"][1]["ats_roundtrip_status"] == "pass"

    def test_404_for_unknown_id(self, app_app):
        client = app_app.app.test_client()
        r = client.get("/api/applications/99999")
        assert r.status_code == 404

    def test_pending_proposals_per_run(self, app_app):
        cid = _seed_candidate()
        bid = _seed_bullet_for_proposals(cid)
        aid = _seed_application(cid)
        run1 = _seed_run(aid, iteration=0)
        run2 = _seed_run(aid, iteration=1, run_id="run2id123456")
        _seed_pending_proposal(run1, bullet_id=bid)
        _seed_pending_proposal(run2, bullet_id=bid)
        _seed_pending_proposal(run2, bullet_id=bid)

        client = app_app.app.test_client()
        body = client.get(f"/api/applications/{aid}").get_json()
        assert body["runs"][0]["pending_proposals"] == 1
        assert body["runs"][1]["pending_proposals"] == 2


# ---------------------------------------------------------------------------
# PUT /api/applications/<id>/status
# ---------------------------------------------------------------------------


class TestUpdateApplicationStatus:
    def test_promotes_to_submitted(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status",
                       json={"status": "submitted"})
        assert r.status_code == 200
        assert r.get_json()["status"] == "submitted"

    def test_rejects_unknown_status(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status",
                       json={"status": "ghosted"})
        assert r.status_code == 400

    def test_404_for_unknown_id(self, app_app):
        client = app_app.app.test_client()
        r = client.put("/api/applications/99999/status", json={"status": "draft"})
        assert r.status_code == 404

    def test_sets_sent_at_on_submitted(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "submitted"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["sent_at"] is not None
        assert body["outcome_at"] is None

    def test_sets_outcome_at_on_rejected(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "rejected"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["outcome_at"] is not None

    def test_interview_stamps_outcome_at(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "interview"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["outcome_at"] is not None

    def test_rejects_no_response(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "no_response"})
        assert r.status_code == 400

    def test_rejects_closed(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "closed"})
        assert r.status_code == 400

    def test_sets_outcome_at_on_withdrawn(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "withdrawn"})
        assert r.status_code == 200
        assert r.get_json()["outcome_at"] is not None

    def test_rejects_offer_and_accepted(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/status", json={"status": "offer"})
        assert r.status_code == 400

        aid2 = _seed_application(cid)
        r2 = client.put(f"/api/applications/{aid2}/status", json={"status": "accepted"})
        assert r2.status_code == 400



def test_no_response_backfill_migration(tmp_path):
    """Migration 0007 DML: no_response → submitted, outcome_at cleared."""
    import sqlite3

    db = tmp_path / "backfill_test.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE application ("
            "  id INTEGER PRIMARY KEY, status TEXT NOT NULL, outcome_at TEXT, "
            "  CHECK (status IN ('draft','submitted','interview','withdrawn',"
            "    'offer','accepted','rejected','no_response'))"
            ")"
        )
        conn.execute(
            "INSERT INTO application (status, outcome_at) "
            "VALUES ('no_response', '2026-05-29T10:00:00Z')"
        )
        conn.execute("INSERT INTO application (status, outcome_at) VALUES ('submitted', NULL)")
        conn.commit()

        conn.execute(
            "UPDATE application SET status = 'submitted', outcome_at = NULL "
            "WHERE status = 'no_response'"
        )
        conn.commit()

        rows = conn.execute(
            "SELECT status, outcome_at FROM application ORDER BY id"
        ).fetchall()
    assert rows[0] == ("submitted", None), "no_response row should become submitted with outcome_at cleared"
    assert rows[1] == ("submitted", None), "already-submitted row should be unchanged"


# ---------------------------------------------------------------------------
# Workstream B — GET/POST /api/applications/<id>/composition
# ---------------------------------------------------------------------------


def _seed_exp_with_bullets(candidate_id, company="Acme"):
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session
    s = get_session()
    try:
        e = Experience(candidate_id=candidate_id, company=company,
                       start_date="2021-01", display_order=0)
        s.add(e)
        s.flush()
        s.add(ExperienceTitle(experience_id=e.id, title="Staff Engineer",
                              is_official=1, is_pending_review=0, source="official"))
        # One JD-relevant bullet, one not.
        s.add(Bullet(experience_id=e.id,
                     text="Reduced Kubernetes latency 40% across 12 services",
                     display_order=0, is_active=1, is_pending_review=0,
                     source="manual", has_outcome=1))
        s.add(Bullet(experience_id=e.id, text="Attended weekly syncs",
                     display_order=1, is_active=1, is_pending_review=0,
                     source="manual", has_outcome=0))
        s.commit()
        return e.id
    finally:
        s.close()


class TestComposition:
    def test_get_ranks_relevant_bullet_first(self, app_app):
        cid = _seed_candidate()
        _seed_exp_with_bullets(cid)
        aid = _seed_application(
            cid, jd_text="Seeking Kubernetes latency optimization at scale",
        )
        client = app_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition")
        assert r.status_code == 200, r.get_json()
        exps = r.get_json()["experiences"]
        assert len(exps) == 1
        bullets = exps[0]["bullets"]
        # The Kubernetes/latency bullet must outrank "Attended weekly syncs"
        assert bullets[0]["text"].startswith("Reduced Kubernetes")
        assert bullets[0]["score"] >= bullets[1]["score"]

    def test_post_persists_overrides_to_context_file(self, app_app, tmp_path):
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid)
        # Minimal context file under OUTPUT_DIR/alice/
        import json
        out = tmp_path / "output" / "alice"
        out.mkdir(parents=True, exist_ok=True)
        ctx = out / "context_x.json"
        ctx.write_text(json.dumps({"application_id": aid}), encoding="utf-8")

        from db.models import Bullet
        from db.session import get_session
        s = get_session()
        try:
            bid = s.query(Bullet).filter_by(experience_id=eid).first().id
        finally:
            s.close()

        client = app_app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={"context_path": str(ctx), "pinned": [bid], "excluded": []},
        )
        assert r.status_code == 200, r.get_json()
        saved = json.loads(ctx.read_text(encoding="utf-8"))
        assert saved["composition_overrides"]["pinned"] == [bid]

        # GET reflects the pinned flag back
        g = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx}",
        ).get_json()
        pinned_flags = [
            b["pinned"] for e in g["experiences"] for b in e["bullets"]
        ]
        assert any(pinned_flags)

    def test_404_for_unknown_application(self, app_app):
        client = app_app.app.test_client()
        assert client.get("/api/applications/99999/composition").status_code == 404

    def test_post_rejects_missing_context_path(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.post(f"/api/applications/{aid}/composition",
                        json={"pinned": [], "excluded": []})
        assert r.status_code == 400


class TestCompositionAddedField:
    def test_post_persists_added_field(self, app_app, tmp_path):
        """Workstream I: composition POST round-trips the 'added' list."""
        cid = _seed_candidate()
        _seed_exp_with_bullets(cid)
        aid = _seed_application(cid)
        import json
        out = tmp_path / "output" / "alice"
        out.mkdir(parents=True, exist_ok=True)
        ctx = out / "context_add.json"
        ctx.write_text(json.dumps({"application_id": aid}), encoding="utf-8")

        client = app_app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={"context_path": str(ctx),
                  "pinned": [], "excluded": [], "added": [42, 43]},
        )
        assert r.status_code == 200, r.get_json()
        saved = json.loads(ctx.read_text(encoding="utf-8"))
        assert saved["composition_overrides"]["added"] == [42, 43]
        assert r.get_json()["added"] == [42, 43]

    def test_get_surfaces_recommended_and_added_flags(self, app_app, tmp_path):
        """Workstream H+I: GET composition exposes the per-bullet recommended
        + added flags so the Compose UI can default to the curated set."""
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid, jd_text="Kubernetes latency at scale")
        import json
        out = tmp_path / "output" / "alice"
        out.mkdir(parents=True, exist_ok=True)
        ctx = out / "context_flags.json"
        # Need a real bullet id to mark recommended
        from db.models import Bullet
        from db.session import get_session
        s = get_session()
        try:
            bids = [b.id for b in s.query(Bullet).filter_by(experience_id=eid).all()]
        finally:
            s.close()
        ctx.write_text(json.dumps({
            "application_id": aid,
            "llm_recommendations": {
                str(eid): {"bullet_ids": [bids[0]], "rationale": "best fit"},
            },
            "composition_overrides": {
                "pinned": [], "excluded": [], "added": [bids[1]],
            },
        }), encoding="utf-8")

        client = app_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx}",
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["any_recommendations"] is True
        exp = body["experiences"][0]
        assert exp["rationale"] == "best fit"
        flags = {b["id"]: (b["recommended"], b["added"]) for b in exp["bullets"]}
        assert flags[bids[0]] == (True, False)
        assert flags[bids[1]] == (False, True)


class TestCompositionBulletOrder:
    """feat/bullet-drag-reorder — composition_overrides.bullet_order round-trips
    through POST, drives the GET order + has_custom_order / in_custom_order
    flags, and a reset (empty order) falls back to the AI ranking."""

    def _bullet_ids(self, eid):
        """[k8s_bullet_id, syncs_bullet_id] — by display_order (k8s is the
        JD-relevant, higher-scoring bullet seeded first)."""
        from db.models import Bullet
        from db.session import get_session
        s = get_session()
        try:
            rows = (s.query(Bullet).filter_by(experience_id=eid)
                    .order_by(Bullet.display_order).all())
            return [b.id for b in rows]
        finally:
            s.close()

    def _ctx(self, tmp_path, aid, extra=None):
        import json
        out = tmp_path / "output" / "alice"
        out.mkdir(parents=True, exist_ok=True)
        ctx = out / "context_order.json"
        body = {"application_id": aid}
        if extra:
            body.update(extra)
        ctx.write_text(json.dumps(body), encoding="utf-8")
        return ctx

    def test_post_persists_bullet_order(self, app_app, tmp_path):
        import json
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid)
        ctx = self._ctx(tmp_path, aid)
        k8s, syncs = self._bullet_ids(eid)
        client = app_app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={"context_path": str(ctx), "pinned": [k8s], "excluded": [],
                  "added": [], "bullet_order": {str(eid): [syncs, k8s]}},
        )
        assert r.status_code == 200, r.get_json()
        saved = json.loads(ctx.read_text(encoding="utf-8"))["composition_overrides"]
        # Persisted with string keys; survives alongside the pin.
        assert saved["bullet_order"] == {str(eid): [syncs, k8s]}
        assert saved["pinned"] == [k8s]
        assert r.get_json()["bullet_order"] == {str(eid): [syncs, k8s]}

    def test_get_returns_saved_order_and_flags(self, app_app, tmp_path):
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid, jd_text="Kubernetes latency at scale")
        k8s, syncs = self._bullet_ids(eid)
        # Reverse the default (k8s-first) score ranking.
        ctx = self._ctx(tmp_path, aid, {
            "composition_overrides": {
                "pinned": [], "excluded": [], "added": [],
                "bullet_order": {str(eid): [syncs, k8s]},
            },
        })
        client = app_app.app.test_client()
        g = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx}",
        ).get_json()
        exp = g["experiences"][0]
        assert exp["has_custom_order"] is True
        assert [b["id"] for b in exp["bullets"]] == [syncs, k8s]
        assert all(b["in_custom_order"] for b in exp["bullets"])

    def test_get_default_order_when_absent(self, app_app, tmp_path):
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid, jd_text="Kubernetes latency at scale")
        k8s, syncs = self._bullet_ids(eid)
        ctx = self._ctx(tmp_path, aid)  # no overrides
        client = app_app.app.test_client()
        g = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx}",
        ).get_json()
        exp = g["experiences"][0]
        assert exp["has_custom_order"] is False
        assert [b["id"] for b in exp["bullets"]] == [k8s, syncs]  # score order

    def test_reset_omits_bullet_order_key(self, app_app, tmp_path):
        import json
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid)
        k8s, syncs = self._bullet_ids(eid)
        ctx = self._ctx(tmp_path, aid, {
            "composition_overrides": {
                "pinned": [], "excluded": [], "added": [],
                "bullet_order": {str(eid): [syncs, k8s]},
            },
        })
        client = app_app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/composition",
            json={"context_path": str(ctx), "pinned": [], "excluded": [],
                  "added": [], "bullet_order": {}},
        )
        assert r.status_code == 200, r.get_json()
        saved = json.loads(ctx.read_text(encoding="utf-8"))["composition_overrides"]
        assert "bullet_order" not in saved  # empty → omitted → AI ranking

    def test_added_after_order_slots_at_end(self, app_app, tmp_path):
        cid = _seed_candidate()
        eid = _seed_exp_with_bullets(cid)
        aid = _seed_application(cid, jd_text="Kubernetes latency at scale")
        k8s, syncs = self._bullet_ids(eid)
        # Saved order names ONLY syncs; k8s post-dates the order.
        ctx = self._ctx(tmp_path, aid, {
            "composition_overrides": {
                "pinned": [], "excluded": [], "added": [],
                "bullet_order": {str(eid): [syncs]},
            },
        })
        client = app_app.app.test_client()
        g = client.get(
            f"/api/applications/{aid}/composition?context_path={ctx}",
        ).get_json()
        bullets = g["experiences"][0]["bullets"]
        assert [b["id"] for b in bullets] == [syncs, k8s]  # unlisted at end
        flags = {b["id"]: b["in_custom_order"] for b in bullets}
        assert flags[syncs] is True
        assert flags[k8s] is False  # newly added → drag-to-reposition hint

    def test_post_rejects_malformed_bullet_order(self, app_app, tmp_path):
        cid = _seed_candidate()
        _seed_exp_with_bullets(cid)
        aid = _seed_application(cid)
        ctx = self._ctx(tmp_path, aid)
        client = app_app.app.test_client()
        r1 = client.post(f"/api/applications/{aid}/composition",
                         json={"context_path": str(ctx), "bullet_order": [1, 2]})
        assert r1.status_code == 400
        r2 = client.post(f"/api/applications/{aid}/composition",
                         json={"context_path": str(ctx),
                               "bullet_order": {"1": ["x"]}})
        assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Phase 2 tracker — PUT /api/applications/<id>/notes
# ---------------------------------------------------------------------------


class TestNotesEndpoint:
    def test_put_notes_saves_note(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/notes",
                       json={"notes": "Follow up on Thursday"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["notes"] == "Follow up on Thursday"

    def test_put_notes_clears_note(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        client.put(f"/api/applications/{aid}/notes",
                   json={"notes": "some note"})
        r = client.put(f"/api/applications/{aid}/notes", json={"notes": ""})
        assert r.status_code == 200
        assert r.get_json()["notes"] is None

    def test_put_notes_404_unknown(self, app_app):
        client = app_app.app.test_client()
        r = client.put("/api/applications/99999/notes", json={"notes": "x"})
        assert r.status_code == 404

    def test_put_notes_rejects_non_string(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        r = client.put(f"/api/applications/{aid}/notes", json={"notes": 42})
        assert r.status_code == 400


class TestGetApplicationDetail:
    def test_get_includes_notes_and_timestamps(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = app_app.app.test_client()
        # Seed notes via the notes endpoint
        client.put(f"/api/applications/{aid}/notes",
                   json={"notes": "Check LinkedIn"})
        # Seed sent_at / outcome_at via the status endpoint
        client.put(f"/api/applications/{aid}/status",
                   json={"status": "submitted"})
        client.put(f"/api/applications/{aid}/status",
                   json={"status": "rejected"})
        r = client.get(f"/api/applications/{aid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["notes"] == "Check LinkedIn"
        assert body["sent_at"] is not None
        assert body["outcome_at"] is not None


# ---------------------------------------------------------------------------
# D.3.1 — resume a prior application into the wizard
# ---------------------------------------------------------------------------


class TestFindContextPathForRun:
    """Unit tests for the LLM-free helper that rediscovers a run's on-disk
    context_*.json (ApplicationRun has no context_path column)."""

    def test_returns_newest_matching_by_iteration(self, app_app):
        _write_context_file(app_app, "alice", "context_a_iter1.json",
                            {"application_run_id": 7, "iteration": 1})
        newer = _write_context_file(app_app, "alice", "context_b_iter2.json",
                                    {"application_run_id": 7, "iteration": 2})
        got = app_app._find_context_path_for_run("alice", 7)
        assert got == str(newer)

    def test_ignores_files_for_other_runs(self, app_app):
        _write_context_file(app_app, "alice", "context_x_iter1.json",
                            {"application_run_id": 999, "iteration": 1})
        assert app_app._find_context_path_for_run("alice", 7) is None

    def test_none_when_user_dir_absent(self, app_app):
        # The fixture creates OUTPUT_DIR but not OUTPUT_DIR/alice.
        assert app_app._find_context_path_for_run("alice", 7) is None

    def test_skips_unparseable_json_returns_valid_match(self, app_app):
        bad = app_app.OUTPUT_DIR / "alice"
        bad.mkdir(parents=True, exist_ok=True)
        (bad / "context_broken_iter1.json").write_text("{not json",
                                                       encoding="utf-8")
        good = _write_context_file(app_app, "alice", "context_ok_iter1.json",
                                   {"application_run_id": 7, "iteration": 1})
        assert app_app._find_context_path_for_run("alice", 7) == str(good)

    def test_none_when_only_unparseable(self, app_app):
        bad = app_app.OUTPUT_DIR / "alice"
        bad.mkdir(parents=True, exist_ok=True)
        (bad / "context_broken_iter1.json").write_text("{not json",
                                                       encoding="utf-8")
        assert app_app._find_context_path_for_run("alice", 7) is None


def _analyze_ctx(run_id, **extra):
    """Minimal post-analyze context_set payload for the #4 resume-state tests
    (the keys `_build_resume_state` reads to classify a pre-generate step)."""
    ctx = {
        "application_run_id": run_id,
        "iteration": 0,
        "llm_analysis": {"essential_skills": ["Python"]},
        "deterministic_analysis": {
            "keyword_overlap": {"match_score": 0.5, "matched": [],
                                "missing_from_resume": []},
            "ats_warnings": [],
        },
    }
    ctx.update(extra)
    return ctx


class TestResumeState:
    """The `resume_state` block on GET /api/applications/<id> (D.3.1 + #4)."""

    def test_full_payload_resume_and_cover(self, app_app):
        cid = _seed_candidate()
        pid = _seed_persona()
        aid = _seed_application(cid)
        rid = _seed_run(aid, iteration=0, generated_resume_md="# Resume",
                        generated_cover_letter_md="Dear Hiring Manager,",
                        persona_template_id=pid)
        ctx = _write_context_file(
            app_app, "alice", "context_a_iter1.json",
            {"application_run_id": rid, "iteration": 1,
             "last_generated_json_resume": {"basics": {"name": "Alice"}}},
        )

        body = app_app.app.test_client().get(f"/api/applications/{aid}").get_json()
        rs = body["resume_state"]
        assert rs["resumable"] is True
        assert rs["resume_md"] == "# Resume"
        assert rs["cover_letter_md"] == "Dear Hiring Manager,"
        assert rs["persona_template_id"] == pid
        assert rs["context_path"] == str(ctx)
        assert rs["iteration"] == 1

    def test_resume_only_run_has_empty_cover(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        _seed_run(aid, iteration=0, generated_resume_md="# Resume")
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["resumable"] is True
        assert rs["resume_md"] == "# Resume"
        assert rs["cover_letter_md"] == ""

    def test_not_resumable_when_never_generated(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        _seed_run(aid, iteration=0)  # analyzed-only: no generated_resume_md
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs == {"resumable": False}

    def test_degraded_when_context_file_missing(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        _seed_run(aid, iteration=0, generated_resume_md="# Resume")
        # No context file written to disk.
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["resumable"] is True
        assert rs["resume_md"] == "# Resume"
        assert rs["context_path"] is None
        assert rs["iteration"] == 0

    def test_prefers_edited_text_over_generated(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        _seed_run(aid, iteration=0, generated_resume_md="# Generated",
                  generated_cover_letter_md="Generated CL",
                  edited_resume_text="# Edited",
                  edited_cover_letter_text="Edited CL")
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["resume_md"] == "# Edited"
        assert rs["cover_letter_md"] == "Edited CL"

    # --- #4: resume from the furthest pre-generate step (target_step) ---

    def test_step_6_payload_carries_target_step(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        _seed_run(aid, iteration=0, generated_resume_md="# Resume")
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["target_step"] == 6

    def test_resumable_at_step_1_when_only_analyzed(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        rid = _seed_run(aid, iteration=0)  # analyzed-only: no generated résumé
        _write_context_file(app_app, "alice", "context_an_iter0.json",
                            _analyze_ctx(rid))
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["resumable"] is True
        assert rs["target_step"] == 1
        assert rs["analysis"] == {"essential_skills": ["Python"]}
        assert rs["deterministic"]["ats_warnings"] == []
        assert "resume_md" not in rs  # pre-generate: no résumé payload

    def test_resumable_at_step_2_when_clarified(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        rid = _seed_run(aid, iteration=0)
        _write_context_file(
            app_app, "alice", "context_cl_iter0.json",
            _analyze_ctx(rid,
                         clarification_questions=[{"id": "q1", "text": "Ran k8s?"}],
                         clarifications={"q1": "Yes, in prod."}),
        )
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["target_step"] == 2
        assert rs["clarification_questions"][0]["id"] == "q1"
        assert rs["clarifications"] == {"q1": "Yes, in prod."}

    def test_recommendations_resume_at_step_3_over_clarify(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        rid = _seed_run(aid, iteration=0)
        _write_context_file(
            app_app, "alice", "context_co_iter0.json",
            _analyze_ctx(rid, clarifications={"q1": "Yes"},
                         llm_recommendations={"1": ["b1"]}),
        )
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["target_step"] == 3  # compose beats clarify

    def test_composition_overrides_resume_at_step_3(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        rid = _seed_run(aid, iteration=0)
        _write_context_file(
            app_app, "alice", "context_cv_iter0.json",
            _analyze_ctx(rid, composition_overrides={"pinned": [1]}),
        )
        rs = app_app.app.test_client().get(
            f"/api/applications/{aid}").get_json()["resume_state"]
        assert rs["target_step"] == 3


class TestUpdateMeta:
    """PUT /api/applications/<id>/meta — editable title + company (#24)."""

    def test_sets_title_and_company(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, title="Old", company=None)
        r = app_app.app.test_client().put(
            f"/api/applications/{aid}/meta",
            json={"title": "Staff PM", "company": "Acme Robotics"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["title"] == "Staff PM"
        assert body["company"] == "Acme Robotics"

    def test_clears_company_when_blank(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, company="Acme")
        body = app_app.app.test_client().put(
            f"/api/applications/{aid}/meta", json={"company": "  "}).get_json()
        assert body["company"] is None

    def test_company_only_leaves_title_intact(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid, title="Keep me")
        body = app_app.app.test_client().put(
            f"/api/applications/{aid}/meta", json={"company": "Acme"}).get_json()
        assert body["title"] == "Keep me"
        assert body["company"] == "Acme"

    def test_rejects_empty_title(self, app_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        r = app_app.app.test_client().put(
            f"/api/applications/{aid}/meta", json={"title": "   "})
        assert r.status_code == 400

    def test_404_for_unknown_id(self, app_app):
        _seed_candidate()
        r = app_app.app.test_client().put(
            "/api/applications/99999/meta", json={"company": "X"})
        assert r.status_code == 404

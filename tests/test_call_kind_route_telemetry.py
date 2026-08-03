"""Tier 2 for item 22 — route-level telemetry reachability, real analyzer function.

Every PRE-EXISTING route test for `recommend_experience_summary` and
`draft_surgical_refinement` (`tests/test_recommend_experience_summaries.py::TestRoute`,
`tests/test_draft_surgical_refinement.py::TestDraftRefinementRoute`) patches the
analyzer FUNCTION itself (`patch("analyzer.recommend_experience_summaries", ...)` /
`patch("analyzer.draft_surgical_refinement", ...)`) — so none of them ever drives the
real function, the real funnel, or the real `_emit_call_log`. That is a real coverage
hole (dossier `docs/dev/diagnosis/never-logged-call-kinds.md` O-4/N-4), not just a style
choice: it means "the route works" has never been tested end-to-end through telemetry.

This file drives the REAL Flask route with the REAL analyzer function, injecting a
fake client only at the `blueprints.applications._get_client` seam those same
pre-existing route tests already use — so route dispatch (b2 in the dossier's rival
list) is genuinely exercised, not assumed. Scoped to these two kinds only: Tier 1
already covers the inventory (all six zero-row kinds, function-level), so this tier's
job is narrower — proving the route *reaches* the function — and its cost scales with
DB/context fixture complexity, which is why it isn't run for all six.

The frozen `approved_composition` document is built via the REAL
`corpus_to_json_resume.freeze_approved_composition` (not hand-written) — a hand-written
doc could drift from the shape `analyzer._current_composition_block` actually consumes,
silently proving nothing.
"""

from __future__ import annotations

import json
import types
from unittest.mock import patch

import pytest

import analyzer
from tests.test_call_kind_telemetry import REAL_LOG_PATH, _QueuedFakeClient


@pytest.fixture(scope="module", autouse=True)
def _real_log_line_count_unchanged():
    """Same independent guard as tests/test_call_kind_telemetry.py — duplicated rather
    than shared across files because it's six lines and a module-scoped fixture can't
    cross a file boundary without a conftest-level promotion, which isn't worth it yet
    for two files."""
    before = REAL_LOG_PATH.read_text(encoding="utf-8").count("\n") if REAL_LOG_PATH.exists() else 0
    yield
    after = REAL_LOG_PATH.read_text(encoding="utf-8").count("\n") if REAL_LOG_PATH.exists() else 0
    assert after == before, (
        f"logs/llm_calls.jsonl grew during tests/test_call_kind_route_telemetry.py "
        f"({before} -> {after} lines)."
    )


@pytest.fixture(autouse=True)
def _telemetry(monkeypatch, tmp_path):
    """Same redirect as tests/test_call_kind_telemetry.py's `_telemetry` — duplicated
    (not imported) because ruff flags a fixture imported under its own name as an F811
    redefinition against the identically-named test-function parameter every test here
    needs; a 4-line duplicate is cheaper than fighting that."""
    logs: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", lambda rec: logs.append(rec))
    monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "llm_calls.jsonl")
    return logs


@pytest.fixture
def routed_app(tmp_path, monkeypatch, _migrated_template_db):
    """Real Flask app + real (migrated, isolated) DB. Mirrors
    tests/test_recommend_experience_summaries.py::recommend_app and
    tests/test_draft_surgical_refinement.py's route fixture — the only deliberate
    difference is that NEITHER analyzer function gets patched here."""
    from tests.conftest import _fresh_migrated_db

    db_file = _fresh_migrated_db(
        tmp_path, monkeypatch, _migrated_template_db, filename="callkindroute.sqlite"
    )

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()

    from db.session import init_db

    assert init_db(db_file) is False, "expected the pre-registered copy to skip alembic"
    return types.SimpleNamespace(app=app), output_dir


class TestRecommendExperienceSummaryRoute:
    def test_real_route_reaches_real_analyzer_function_and_logs(self, routed_app, _telemetry):
        from db.models import Application, Candidate, Experience, ExperienceSummaryItem
        from db.session import get_session

        _app, output_dir = routed_app
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
            exp = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
            session.add(exp)
            session.flush()
            item1 = ExperienceSummaryItem(
                experience_id=exp.id,
                text="Platform-scale framing.",
                display_order=0,
                is_active=1,
            )
            item2 = ExperienceSummaryItem(
                experience_id=exp.id,
                text="Growth-builder framing.",
                display_order=1,
                is_active=1,
            )
            session.add_all([item1, item2])
            session.commit()
            aid, eid, item1_id = a.id, exp.id, item1.id
        finally:
            session.close()

        ctx_path = output_dir / "casey" / "context_iter0.json"
        ctx_path.write_text(
            json.dumps({"application_id": aid, "run_id": "t2run"}), encoding="utf-8"
        )

        fake_client = _QueuedFakeClient(
            json.dumps(
                {
                    "recommendations": [
                        {
                            "experience_id": eid,
                            "summary_item_id": item1_id,
                            "rationale": "fits",
                            "alternates": [],
                        }
                    ]
                }
            )
        )

        with patch("blueprints.applications._get_client", lambda: fake_client):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/recommend-experience-summaries",
                json={"context_path": str(ctx_path)},
            )

        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["recommendations"][0]["experience_id"] == eid

        assert len(_telemetry) == 1
        assert _telemetry[0]["call"] == "recommend_experience_summary"
        assert _telemetry[0]["status"] == "ok"


class TestDraftSurgicalRefinementRoute:
    def test_real_route_reaches_real_analyzer_function_and_logs(self, routed_app, _telemetry):
        from corpus_to_json_resume import freeze_approved_composition
        from db.models import Application, Bullet, Candidate, Experience, ExperienceTitle
        from db.session import get_session

        _app, output_dir = routed_app
        session = get_session()
        try:
            c = Candidate(username="casey", name="Casey Rivera", profile_text="A platform PM.")
            session.add(c)
            session.flush()
            a = Application(
                candidate_id=c.id,
                title="Senior PM",
                jd_text="Senior PM building AI billing platforms.",
                jd_fingerprint="f" * 16,
            )
            session.add(a)
            session.flush()
            exp = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
            session.add(exp)
            session.flush()
            session.add(
                ExperienceTitle(experience_id=exp.id, title="PM", is_official=1, source="official")
            )
            session.add(
                Bullet(
                    experience_id=exp.id,
                    text="Led the billing rewrite.",
                    source="resume_import",
                )
            )
            session.commit()
            cid, aid, eid = c.id, a.id, exp.id

            # Real frozen doc — not hand-written — is exactly what the plan requires.
            doc = freeze_approved_composition(session, cid, application_id=aid)
        finally:
            session.close()

        ctx_path = output_dir / "casey" / "context_iter0.json"
        ctx_path.write_text(
            json.dumps({"application_id": aid, "approved_composition": doc, "run_id": "t2run"}),
            encoding="utf-8",
        )

        fake_client = _QueuedFakeClient(
            json.dumps(
                {
                    "target_kind": "bullet",
                    "experience_id": eid,
                    "supersedes_bullet_id": None,
                    "text": "Sharpened the billing bullet.",
                    "pattern_kind": "xyz",
                    "rationale": "punchier",
                }
            )
        )

        with patch("blueprints.applications._get_client", lambda: fake_client):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/draft-refinement",
                json={"context_path": str(ctx_path), "note": "make the billing bullet punchier"},
            )

        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["proposal"]["target_kind"] == "bullet"

        assert len(_telemetry) == 1
        assert _telemetry[0]["call"] == "draft_surgical_refinement"
        assert _telemetry[0]["status"] == "ok"

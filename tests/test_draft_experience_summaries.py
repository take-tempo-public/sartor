"""Tests for `analyzer.draft_experience_summaries` + its two Compose routes (A3).

Epic A sprint A3 (`feat/role-summary-drafting`): at Compose, a JD-fitted one-line
intro is drafted for EACH included role in ONE batched Sonnet call, stashed as
TRANSIENT drafts on `ctx["llm_experience_summary_drafts"]` (not
`ExperienceSummaryItem` rows). The user then KEEPs one — optionally after editing
it in place, which is why the decide route accepts `text` — creating a PENDING
canonical variant and choosing it for this application; or REJECTs it, creating
nothing.

Four surfaces:
  - TestDraftExperienceSummariesShortCircuit — no JD / no staged target ->
    {"drafts": []} with NO LLM call.
  - TestDraftExperienceSummariesPrompt — the three grounding sources actually
    reach the prompt, and the normalization drops what it should.
  - TestDraftExperienceSummariesRoute — POST /draft-experience-summaries keys
    each draft, ALWAYS writes the context key (even []) so the latch flips,
    strips transient staging, and enforces ownership + validation.
  - TestExperienceSummaryDecideRoute — keep/reject, edit-in-place, idempotency.

The batched-not-per-role property is asserted directly (one call, N roles in the
payload): it is the load-bearing cost property of this sprint's brief, and a
regression to per-role calls would otherwise be invisible to every other test.
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


class TestDraftExperienceSummariesShortCircuit:
    def test_no_jd_returns_empty_no_llm(self):
        from analyzer import draft_experience_summaries

        # client=object() would raise if the LLM path ran — a staged target is
        # present, so the JD gate is what short-circuits.
        result = draft_experience_summaries(
            client=object(),
            context_set={
                "experience_summary_targets": [
                    {"experience_id": 1, "company": "Acme", "bullets": [{"id": 2, "text": "x"}]}
                ]
            },
        )
        assert result == {"drafts": []}

    def test_no_targets_returns_empty_no_llm(self):
        from analyzer import draft_experience_summaries

        result = draft_experience_summaries(
            client=object(),
            context_set={"jd_text": "Senior platform engineer."},
        )
        assert result == {"drafts": []}

    def test_target_without_usable_id_is_dropped(self):
        from analyzer import draft_experience_summaries

        result = draft_experience_summaries(
            client=object(),
            context_set={
                "jd_text": "Senior platform engineer.",
                "experience_summary_targets": [{"company": "Acme"}, "not-a-dict"],
            },
        )
        assert result == {"drafts": []}


# -------------------------------------------------------------------
# Prompt shape + normalization (LLM funnel patched out)
# -------------------------------------------------------------------


def _ctx_two_roles() -> dict:
    return {
        "jd_text": "Senior platform engineer, reliability at scale.",
        "llm_analysis": {
            "essential_skills": ["Kubernetes"],
            "preferred_skills": ["Terraform"],
            "industry_keywords": ["platform"],
        },
        "clarifications": {"q1": "Owned the deploy pipeline end to end."},
        "prior_clarifications": [
            {
                "question": "Led on-call?",
                "answer": "Led on-call for a 12-person SRE team.",
                "kind": "experience_probe",
            }
        ],
        "experience_summary_targets": [
            {
                "experience_id": 7,
                "company": "Acme",
                "title": "Staff Engineer",
                "span": "2021-01–present",
                "bullets": [{"id": 12, "text": "Migrated 40 services to Kubernetes."}],
                "existing_intros": [
                    {"id": 44, "text": "Ran the platform group.", "label": "scale framing"}
                ],
            },
            {
                "experience_id": 9,
                "company": "Northwind",
                "title": "Senior Engineer",
                "span": "2018-01–2021-01",
                "bullets": [{"id": 31, "text": "Built the CI system."}],
                "existing_intros": [],
            },
        ],
    }


class TestDraftExperienceSummariesPrompt:
    def test_one_batched_call_covers_every_role(self):
        """The load-bearing cost property: ONE call, every role inside it."""
        from analyzer import draft_experience_summaries

        calls: list[str] = []

        def _cap(client, user_prompt, **kw):
            calls.append(user_prompt)
            return {"drafts": []}

        with patch("analyzer._parse_or_retry", _cap):
            draft_experience_summaries(client=object(), context_set=_ctx_two_roles())

        assert len(calls) == 1, f"expected ONE batched call, got {len(calls)} (per-role regression)"
        p = calls[0]
        assert '<role id="7"' in p
        assert '<role id="9"' in p

    def test_prompt_carries_all_three_grounding_sources(self):
        from analyzer import draft_experience_summaries

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"drafts": []}

        with patch("analyzer._parse_or_retry", _cap):
            draft_experience_summaries(client=object(), context_set=_ctx_two_roles())

        p = captured["prompt"]
        # (a) the role's own bullets, with ids
        assert '<bullet id="12">Migrated 40 services to Kubernetes.</bullet>' in p
        # (b) the role's own existing intro variants, with ids
        assert 'id="44"' in p
        assert "Ran the platform group." in p
        # (c) this application's clarifications AND the D5 cross-JD ones
        assert "Owned the deploy pipeline end to end." in p
        assert "<prior_clarifications>" in p
        assert "Led on-call for a 12-person SRE team." in p
        # heading facts the intro must not restate
        assert 'company="Acme"' in p
        assert 'title="Staff Engineer"' in p

    def test_prompt_escapes_xml_metacharacters(self):
        """A company or bullet containing `<`/`&` must not break the block."""
        from analyzer import draft_experience_summaries

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"drafts": []}

        ctx = {
            "jd_text": "Engineer.",
            "experience_summary_targets": [
                {
                    "experience_id": 1,
                    "company": "A & B <Ltd>",
                    "bullets": [{"id": 2, "text": "Cut p95 <200ms & held it."}],
                    "existing_intros": [],
                }
            ],
        }
        with patch("analyzer._parse_or_retry", _cap):
            draft_experience_summaries(client=object(), context_set=ctx)

        p = captured["prompt"]
        assert "A &amp; B &lt;Ltd&gt;" in p
        assert "Cut p95 &lt;200ms &amp; held it." in p

    def test_normalization_drops_unknown_role_duplicates_and_empties(self):
        from analyzer import draft_experience_summaries

        def _cap(client, user_prompt, **kw):
            return {
                "drafts": [
                    {"experience_id": 7, "text": "First for role 7."},
                    {"experience_id": 7, "text": "Second for role 7 — must be dropped."},
                    {"experience_id": 999, "text": "A role that was never staged."},
                    {"experience_id": 9, "text": "   "},
                    "not-a-dict",
                ]
            }

        with patch("analyzer._parse_or_retry", _cap):
            out = draft_experience_summaries(client=object(), context_set=_ctx_two_roles())

        assert [d["experience_id"] for d in out["drafts"]] == [7]
        assert out["drafts"][0]["text"] == "First for role 7."
        # A missing evidence block is filled in rather than left absent, so the
        # route and the UI never have to guard for it.
        assert out["drafts"][0]["evidence"] == {
            "bullet_id": None,
            "summary_item_id": None,
            "quote": "",
        }

    def test_uses_sonnet(self):
        """Authoring prose, not structured selection — the same routing choice
        draft_positioning_summary / draft_gap_fill_bullets make (and the opposite
        of recommend_experience_summaries, which SELECTS and uses Haiku)."""
        from analyzer import SONNET_MODEL, draft_experience_summaries

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured.update(kw)
            return {"drafts": []}

        with patch("analyzer._parse_or_retry", _cap):
            draft_experience_summaries(client=object(), context_set=_ctx_two_roles())

        assert captured["model"] == SONNET_MODEL
        assert captured["call_kind"] == "draft_experience_summary"


# -------------------------------------------------------------------
# Route tests (stubbed LLM + real DB rows)
# -------------------------------------------------------------------


@pytest.fixture
def intro_app(tmp_path, monkeypatch, _migrated_template_db):
    """Same fixture shape as tests/test_draft_gap_fill.py::gap_app (PX-44 rollout)."""
    from tests.conftest import _fresh_migrated_db

    db_file = _fresh_migrated_db(
        tmp_path, monkeypatch, _migrated_template_db, filename="roleintro.sqlite"
    )

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()
    monkeypatch.setattr("blueprints.applications._get_client", lambda: object())

    from db.session import init_db

    assert init_db(db_file) is False, "expected the pre-registered copy to skip alembic"
    return types.SimpleNamespace(app=app), output_dir


def _seed_intro(output_dir):
    """Seed a candidate with two roles — one carrying an existing intro variant,
    one carrying none — plus an iteration-0 run and a context file."""
    from db.models import (
        Application,
        ApplicationRun,
        Bullet,
        Candidate,
        Experience,
        ExperienceSummaryItem,
    )
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera", profile_text="A platform engineer.")
        session.add(c)
        session.flush()
        e1 = Experience(candidate_id=c.id, company="Acme", start_date="2021-01")
        e2 = Experience(candidate_id=c.id, company="Northwind", start_date="2018-01")
        session.add_all([e1, e2])
        session.flush()
        b1 = Bullet(
            experience_id=e1.id,
            text="Migrated 40 services to Kubernetes.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="official",
            has_outcome=1,
        )
        b2 = Bullet(
            experience_id=e2.id,
            text="Built the CI system.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="official",
            has_outcome=0,
        )
        session.add_all([b1, b2])
        session.flush()
        si = ExperienceSummaryItem(
            experience_id=e1.id,
            text="Ran the platform group.",
            label="scale framing",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="manual",
            has_outcome=0,
        )
        session.add(si)
        a = Application(
            candidate_id=c.id,
            title="Senior Platform Engineer",
            jd_text="Senior platform engineer, reliability at scale.",
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
        ids = types.SimpleNamespace(
            cid=c.id,
            aid=a.id,
            e1=e1.id,
            e2=e2.id,
            b1=b1.id,
            b2=b2.id,
            si=si.id,
            run_pk=run.id,
        )
    finally:
        session.close()

    ctx = {
        "application_id": ids.aid,
        "application_run_id": ids.run_pk,
        "iteration": 0,
        "run_id": "testrun",
        "llm_analysis": {"essential_skills": ["Kubernetes"], "preferred_skills": []},
        "career_corpus": [
            {
                "id": ids.e1,
                "company": "Acme",
                "start_date": "2021-01",
                "end_date": "present",
                "eligible_titles": [{"id": 1, "title": "Staff Engineer", "is_official": True}],
                "bullets": [{"id": ids.b1, "text": "Migrated 40 services to Kubernetes."}],
            },
            {
                "id": ids.e2,
                "company": "Northwind",
                "start_date": "2018-01",
                "end_date": "2021-01",
                "eligible_titles": [],
                "bullets": [{"id": ids.b2, "text": "Built the CI system."}],
            },
        ],
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    ids.ctx_path = str(ctx_path)
    return ids


class TestDraftExperienceSummariesRoute:
    def test_stages_targets_and_persists_keyed_drafts(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        seen: dict = {}

        def _stub(client, context_set, *, username="", run_id=""):
            seen["targets"] = context_set.get("experience_summary_targets")
            seen["jd"] = context_set.get("jd_text")
            return {
                "drafts": [
                    {
                        "experience_id": s.e1,
                        "text": "Owned the platform migration onto Kubernetes.",
                        "evidence": {"bullet_id": s.b1, "summary_item_id": None, "quote": "..."},
                        "rationale": "closest to the JD",
                    }
                ]
            }

        with patch("analyzer.draft_experience_summaries", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)

        # BOTH roles were staged in the SINGLE call — batched, not per role.
        assert [t["experience_id"] for t in seen["targets"]] == [s.e1, s.e2]
        assert seen["jd"].startswith("Senior platform engineer")
        # The role with an existing variant carries it; the one without carries [].
        by_id = {t["experience_id"]: t for t in seen["targets"]}
        assert by_id[s.e1]["existing_intros"][0]["id"] == s.si
        assert by_id[s.e2]["existing_intros"] == []
        # The pinned/official title reaches the target, so the prompt can tell the
        # model what NOT to restate.
        assert by_id[s.e1]["title"] == "Staff Engineer"

        body = r.get_json()
        assert len(body["drafts"]) == 1
        assert body["drafts"][0]["key"]

        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert "llm_experience_summary_drafts" in ctx
        assert ctx["llm_experience_summary_drafts"][0]["experience_id"] == s.e1
        # Transient staging never reaches disk.
        assert "jd_text" not in ctx
        assert "experience_summary_targets" not in ctx

    def test_empty_result_still_sets_the_latch(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)

        with patch("analyzer.draft_experience_summaries", lambda *a, **k: {"drafts": []}):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["llm_experience_summary_drafts"] == []
        r2 = _app.app.test_client().get(
            f"/api/applications/{s.aid}/composition?context_path={s.ctx_path}"
        )
        assert r2.get_json()["has_experience_summary_drafts"] is True

    def test_get_surfaces_the_draft_on_its_own_role(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            return {"drafts": [{"experience_id": s.e1, "text": "A drafted intro."}]}

        with patch("analyzer.draft_experience_summaries", _stub):
            _app.app.test_client().post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        r = _app.app.test_client().get(
            f"/api/applications/{s.aid}/composition?context_path={s.ctx_path}"
        )
        exps = {e["id"]: e for e in r.get_json()["experiences"]}
        assert exps[s.e1]["summary"]["draft"]["text"] == "A drafted intro."
        assert exps[s.e2]["summary"]["draft"] is None

    def test_excluded_bullets_do_not_ground_the_draft(self, intro_app):
        """The effective-bullet rule mirrors the frozen-composition resolver: a
        bullet the user excluded is not evidence for an intro that will sit above
        a résumé that no longer contains it."""
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {"excluded": [s.b2]}
        Path(s.ctx_path).write_text(json.dumps(ctx), encoding="utf-8")
        seen: dict = {}

        def _stub(client, context_set, *, username="", run_id=""):
            seen["targets"] = context_set.get("experience_summary_targets")
            return {"drafts": []}

        with patch("analyzer.draft_experience_summaries", _stub):
            _app.app.test_client().post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        by_id = {t["experience_id"]: t for t in seen["targets"]}
        assert by_id[s.e1]["bullets"]
        # e2's only bullet was excluded, but it has no existing intro either, so
        # the whole role drops out of the staged set — nothing to ground on.
        assert s.e2 not in by_id

    def test_recommendations_restrict_the_evidence_set(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ctx["llm_recommendations"] = {str(s.e1): {"bullet_ids": [], "rationale": "r"}}
        Path(s.ctx_path).write_text(json.dumps(ctx), encoding="utf-8")
        seen: dict = {}

        def _stub(client, context_set, *, username="", run_id=""):
            seen["targets"] = context_set.get("experience_summary_targets")
            return {"drafts": []}

        with patch("analyzer.draft_experience_summaries", _stub):
            _app.app.test_client().post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        by_id = {t["experience_id"]: t for t in seen["targets"]}
        # e1 has a recommendation naming NO bullets -> no bullets are evidence,
        # but its existing intro variant keeps the role in the staged set.
        assert by_id[s.e1]["bullets"] == []
        assert by_id[s.e1]["existing_intros"]
        # e2 has no recommendation at all -> the all-active fallback applies.
        assert [b["id"] for b in by_id[s.e2]["bullets"]] == [s.b2]

    def test_retired_role_never_reaches_the_draft_prompt(self, intro_app):
        """Item 75: a role soft-retired AFTER analyze must not be staged as a
        draft target — the frozen `career_corpus` snapshot still carries its
        bullets, and bullets alone must not carry a retired role to Sonnet.
        Mirrors the live `is_active` filter the gap-fill lane already applies
        (`cand_exp_ids`)."""
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)

        from db.models import Experience
        from db.session import get_session

        session = get_session()
        try:
            session.query(Experience).filter_by(id=s.e2).update({"is_active": 0})
            session.commit()
        finally:
            session.close()

        seen: dict = {}

        def _stub(client, context_set, *, username="", run_id=""):
            seen["targets"] = context_set.get("experience_summary_targets")
            return {"drafts": []}

        with patch("analyzer.draft_experience_summaries", _stub):
            r = _app.app.test_client().post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        staged = [t["experience_id"] for t in seen["targets"]]
        assert s.e2 not in staged, f"retired role {s.e2} reached the draft targets: {staged}"
        # The still-active role is unaffected by the filter.
        assert staged == [s.e1]

    def test_404_unknown_application(self, intro_app):
        _app, _output_dir = intro_app
        r = _app.app.test_client().post(
            "/api/applications/9999/draft-experience-summaries",
            json={"context_path": "/whatever"},
        )
        assert r.status_code == 404

    def test_400_missing_context_path(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/draft-experience-summaries", json={}
        )
        assert r.status_code == 400


class TestExperienceSummaryDecideRoute:
    def _draft_one(self, app, s, text="Owned the platform migration onto Kubernetes."):
        def _stub(client, context_set, *, username="", run_id=""):
            return {"drafts": [{"experience_id": s.e1, "text": text}]}

        with patch("analyzer.draft_experience_summaries", _stub):
            r = app.test_client().post(
                f"/api/applications/{s.aid}/draft-experience-summaries",
                json={"context_path": s.ctx_path},
            )
        return r.get_json()["drafts"][0]["key"]

    def test_keep_creates_a_pending_variant_and_chooses_it(self, intro_app):
        from db.models import ExperienceSummaryItem
        from db.session import get_session

        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)

        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key, "decision": "keep"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        item_id = r.get_json()["summary_item_id"]

        session = get_session()
        try:
            row = session.query(ExperienceSummaryItem).filter_by(id=item_id).first()
            assert row is not None
            assert row.experience_id == s.e1
            # Canonical store, pending review — never the legacy Experience.summary
            # column (work item 59).
            assert row.source == "llm_proposed"
            assert row.is_pending_review == 1
            assert row.is_active == 1
        finally:
            session.close()

        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        ov = ctx["composition_overrides"]
        assert ov["chosen_experience_summary_ids"][str(s.e1)] == item_id
        # Kept intros are useless unless the opt-in toggle is on.
        assert ov["use_experience_summaries"] is True
        # The transient draft is consumed.
        assert ctx["llm_experience_summary_drafts"] == []
        # A3 close-out (blast-radius D5) — the pending-leak guard's per-
        # application acceptance ledger: KEEP must fold the new pending item
        # into accepted_experience_summary_ids so it renders for THIS
        # application (and the response echoes it, mirroring gap-fill-decide's
        # accepted_generated_bullet_ids).
        assert ov["accepted_experience_summary_ids"] == [item_id]
        assert r.get_json()["accepted_experience_summary_ids"] == [item_id]

    def test_keep_does_not_touch_the_legacy_summary_column(self, intro_app):
        """Item 59: the corpus role card already has two summary editors. This
        lane must feed the CANONICAL one and leave the legacy denormalized cache
        exactly as it found it."""
        from db.models import Experience
        from db.session import get_session

        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)
        _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key, "decision": "keep"},
        )
        session = get_session()
        try:
            exp = session.query(Experience).filter_by(id=s.e1).first()
            assert exp.summary is None
        finally:
            session.close()

    def test_edit_in_place_text_wins(self, intro_app):
        from db.models import ExperienceSummaryItem
        from db.session import get_session

        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)

        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={
                "context_path": s.ctx_path,
                "key": key,
                "decision": "keep",
                "text": "  My own wording for this role.  ",
            },
        )
        assert r.status_code == 200
        session = get_session()
        try:
            row = (
                session.query(ExperienceSummaryItem)
                .filter_by(id=r.get_json()["summary_item_id"])
                .first()
            )
            assert row.text == "My own wording for this role."
        finally:
            session.close()

    def test_keep_is_idempotent_on_identical_text(self, intro_app):
        from db.models import ExperienceSummaryItem
        from db.session import get_session

        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)
        first = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key, "decision": "keep"},
        )
        # Re-draft the same text so the key resolves again, then keep again.
        key2 = self._draft_one(_app.app, s)
        second = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key2, "decision": "keep"},
        )
        assert first.get_json()["summary_item_id"] == second.get_json()["summary_item_id"]
        # The acceptance ledger must not accumulate a duplicate on re-accept.
        assert second.get_json()["accepted_experience_summary_ids"] == [
            first.get_json()["summary_item_id"]
        ]
        session = get_session()
        try:
            n = (
                session.query(ExperienceSummaryItem)
                .filter_by(experience_id=s.e1, source="llm_proposed")
                .count()
            )
            assert n == 1
        finally:
            session.close()

    def test_reject_drops_the_draft_and_creates_nothing(self, intro_app):
        from db.models import ExperienceSummaryItem
        from db.session import get_session

        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)

        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key, "decision": "reject"},
        )
        assert r.status_code == 200
        ctx = json.loads(Path(s.ctx_path).read_text(encoding="utf-8"))
        assert ctx["llm_experience_summary_drafts"] == []
        session = get_session()
        try:
            assert (
                session.query(ExperienceSummaryItem)
                .filter_by(experience_id=s.e1, source="llm_proposed")
                .count()
                == 0
            )
        finally:
            session.close()

    def test_stale_key_is_404_on_keep(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        self._draft_one(_app.app, s)
        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": "deadbeef1234", "decision": "keep"},
        )
        assert r.status_code == 404

    def test_bad_decision_is_400(self, intro_app):
        _app, output_dir = intro_app
        s = _seed_intro(output_dir)
        key = self._draft_one(_app.app, s)
        r = _app.app.test_client().post(
            f"/api/applications/{s.aid}/experience-summary-decide",
            json={"context_path": s.ctx_path, "key": key, "decision": "maybe"},
        )
        assert r.status_code == 400

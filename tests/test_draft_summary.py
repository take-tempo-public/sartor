"""Tests for `analyzer.draft_positioning_summary` + the /draft-summary route.

Generation-experience re-architecture (fix/compose-frozen-composition): the
2-sentence positioning summary is authored ONCE at Compose (Sonnet) instead of
at Generate. Two surfaces:
  - TestDraftSummaryShortCircuit — no JD → returns the source positioning with
    NO LLM call (a JD-less context is free).
  - TestDraftSummaryRoute — /api/applications/<id>/draft-summary persists the
    drafted text into composition_overrides.summary_text (fresh draft →
    summary_text_edited absent), strips transient keys, handles ownership +
    validation.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Pure-function short-circuit (no LLM, no DB)
# -------------------------------------------------------------------


class TestDraftSummaryShortCircuit:
    def test_no_jd_returns_source_no_llm(self):
        from analyzer import draft_positioning_summary

        # client=object() would raise if the LLM path ran — the short-circuit
        # returns before touching it.
        result = draft_positioning_summary(
            client=object(),
            context_set={"summary_source_text": "Existing positioning."},
        )
        assert result == {"summary": "Existing positioning."}

    def test_no_jd_no_source_returns_empty(self):
        from analyzer import draft_positioning_summary

        result = draft_positioning_summary(client=object(), context_set={})
        assert result == {"summary": ""}


# -------------------------------------------------------------------
# D5 (feat/clarifications-to-corpus): cross-JD prior_clarifications reuse
# -------------------------------------------------------------------


class TestDraftSummaryPriorClarifications:
    def test_prior_clarifications_render_in_prompt(self):
        from unittest.mock import patch

        from analyzer import draft_positioning_summary

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"summary": ""}

        with patch("analyzer._parse_or_retry", _cap):
            draft_positioning_summary(
                client=object(),
                context_set={
                    "summary_source_text": "Platform PM.",
                    "jd_text": "Senior SRE role.",
                    "prior_clarifications": [
                        {
                            "question": "Led on-call?",
                            "answer": "Led on-call for a 12-person SRE team, cut MTTR 40%.",
                            "kind": "experience_probe",
                        }
                    ],
                },
            )
        p = captured["prompt"]
        assert "<prior_clarifications>" in p
        assert "Led on-call for a 12-person SRE team, cut MTTR 40%." in p

    def test_absent_prior_clarifications_renders_none(self):
        from unittest.mock import patch

        from analyzer import draft_positioning_summary

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"summary": ""}

        with patch("analyzer._parse_or_retry", _cap):
            draft_positioning_summary(
                client=object(),
                context_set={"summary_source_text": "Platform PM.", "jd_text": "Senior SRE role."},
            )
        assert "<prior_clarifications>\n(none)\n</prior_clarifications>" in captured["prompt"]


# -------------------------------------------------------------------
# Route tests (stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def draft_app(tmp_path, monkeypatch):
    import types

    db_file = tmp_path / "draftsum.sqlite"
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


def _seed(output_dir, *, profile_text="A platform PM.") -> tuple[int, int, str]:
    from db.models import Application, Candidate
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera", profile_text=profile_text)
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title="Senior PM",
            jd_text="Senior PM building AI billing platforms.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.commit()
        cid, aid = c.id, a.id
    finally:
        session.close()

    ctx = {
        "application_id": aid,
        "iteration": 0,
        "run_id": "testrun",
        "llm_analysis": {"essential_skills": ["billing"], "industry_keywords": ["fintech"]},
        "career_corpus": [
            {
                "id": 1,
                "company": "Acme",
                "start_date": "2021-01",
                "end_date": "present",
                "eligible_titles": [{"id": 1, "title": "Platform PM", "is_official": True}],
                "bullets": [{"id": 10, "text": "Led the billing rewrite."}],
            }
        ],
    }
    ctx_path = output_dir / "casey" / "context_iter0.json"
    ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
    return cid, aid, str(ctx_path)


class TestDraftSummaryRoute:
    def test_happy_path_persists_summary_text(self, draft_app):
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)

        def _stub(client, context_set, *, username="", run_id=""):
            # The route staged the source positioning, career facts, and JD.
            assert context_set.get("summary_source_text") == "A platform PM."
            assert "Platform PM" in context_set.get("career_facts", "")
            assert context_set.get("jd_text", "").startswith("Senior PM")
            return {"summary": "A billing-platform PM who ships. Cut churn with a rewrite."}

        with patch("analyzer.draft_positioning_summary", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/draft-summary",
                json={"context_path": ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["summary_text"] == "A billing-platform PM who ships. Cut churn with a rewrite."
        assert body["summary_text_edited"] is False

        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["summary_text"] == (
            "A billing-platform PM who ships. Cut churn with a rewrite."
        )
        # Fresh draft → not flagged edited; transient staging keys stripped.
        assert "summary_text_edited" not in ctx["composition_overrides"]
        for transient in ("summary_source_text", "career_facts", "jd_text"):
            assert transient not in ctx

    def test_regenerate_overwrites_and_clears_edited_flag(self, draft_app):
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)
        # Pretend a prior draft was hand-edited.
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "summary_text": "Old hand-edited summary.",
            "summary_text_edited": True,
        }
        Path(ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        def _stub(client, context_set, *, username="", run_id=""):
            return {"summary": "Freshly regenerated summary."}

        with patch("analyzer.draft_positioning_summary", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/draft-summary",
                json={"context_path": ctx_path},
            )
        assert r.status_code == 200
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        assert ctx["composition_overrides"]["summary_text"] == "Freshly regenerated summary."
        assert "summary_text_edited" not in ctx["composition_overrides"]

    def test_torn_context_file_is_a_loud_400(self, draft_app):
        """A half-written context file must fail loudly — the server half of the bug.

        `fix/compose-summary-draft-settle-hole`: a concurrent NON-atomic write left
        `context_*.json` truncated, this route 400'd on the `JSONDecodeError`, and
        the Compose client swallowed the 400 — so the user sat under "Drafting your
        summary…" forever and CI saw only an empty textarea. Writes are atomic now
        (`hardening.write_context_atomic`), so the tear can no longer happen; this
        pins the contract the client is now required to surface instead of drop.
        """
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)
        # Byte-for-byte what a reader saw mid-`Path.write_text`: the file, truncated.
        Path(ctx_path).write_text('{"application_id": 1, "care', encoding="utf-8")

        client = _app.app.test_client()
        r = client.post(
            f"/api/applications/{aid}/draft-summary",
            json={"context_path": ctx_path},
        )

        assert r.status_code == 400, r.get_data(as_text=True)
        assert "unreadable" in r.get_json()["error"].lower()

    def test_get_composition_surfaces_the_draft(self, draft_app):
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)
        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "summary_text": "The drafted positioning.",
            "summary_text_edited": True,
        }
        Path(ctx_path).write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.get(f"/api/applications/{aid}/composition?context_path={ctx_path}")
        assert r.status_code == 200
        summary = r.get_json()["summary"]
        assert summary["drafted_text"] == "The drafted positioning."
        assert summary["drafted_edited"] is True
        assert summary["has_draft"] is True

    def test_404_unknown_application(self, draft_app):
        _app, _output_dir = draft_app
        client = _app.app.test_client()
        r = client.post(
            "/api/applications/9999/draft-summary",
            json={"context_path": "/whatever"},
        )
        assert r.status_code == 404

    def test_400_missing_context_path(self, draft_app):
        _app, output_dir = draft_app
        _cid, aid, _ = _seed(output_dir)
        client = _app.app.test_client()
        r = client.post(f"/api/applications/{aid}/draft-summary", json={})
        assert r.status_code == 400


# -------------------------------------------------------------------
# The falsification experiment (charter C-7)
# -------------------------------------------------------------------


class TestConcurrentContextWriters:
    """Does a concurrent `/recommend` erase `/draft-summary`'s persisted delta?

    This is the experiment specified in the evidence dossier
    (`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`, §Falsification).
    It exists to KILL a hypothesis, not to confirm one.

    What the dossier **observed** (O-2, CI run `29303444590`): `/draft-summary`
    returned 200 having persisted `summary_text`, and the very next read of the
    same context file did not have it — durably. Something overwrote the file.

    What the dossier only **inferred**: that the something was `/recommend`. The
    traffic dump records *response* order, not *write* order, so it cannot
    establish who erased it. `/recommend` is the leading candidate on shape
    alone — it has the read-modify-write-whole-dict form (O-4) and it is the
    only other context writer in the observed window.

    This test settles that by making the interleaving deterministic instead of
    lucky. It drives the one ordering the hypothesis requires:

        1. `/recommend` reads the whole context   (applications.py:1774)
        2. `/draft-summary` reads, drafts, persists `summary_text`  (:2086)
        3. `/recommend` returns from its LLM call and writes its now-stale
           whole dict back                                          (:1838)

    `/recommend` has necessarily completed its read by the time it reaches its
    LLM call, so stubbing that call is a precise, non-invasive probe of step 1.

    **What a failure proves:** the lost update is real, reachable, and
    reproducible in milliseconds. **What it does NOT prove:** that this exact
    interleaving is what happened in CI. That distinction is the point of C-7
    and is stated here so nobody launders it into a stronger claim later.

    **If this test PASSES on HEAD the hypothesis is dead — stop, do not fix,
    widen the instrument** (`/draft-gap-fill` is the next candidate, as is a
    writer outside this file).
    """

    def test_recommend_does_not_erase_a_concurrent_draft_summary(self, draft_app):
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)

        drafted = "A billing-platform PM who ships. Cut churn with a rewrite."
        recommend_has_read = threading.Event()
        draft_has_persisted = threading.Event()

        def _recommend_stub(client, context_set, *, username="", run_id=""):
            # Reaching here means /recommend already holds its in-memory copy of
            # the context (read at applications.py:1774, before this call at
            # :1787). Hold the call open — as a real multi-second Haiku call
            # would — while /draft-summary reads, drafts, and persists.
            recommend_has_read.set()
            assert draft_has_persisted.wait(timeout=20), "/draft-summary never returned"
            return {
                "recommendations": [
                    {"experience_id": 1, "bullet_ids": [10], "rationale": "billing"}
                ]
            }

        def _draft_stub(client, context_set, *, username="", run_id=""):
            # Draft only once /recommend is provably holding a pre-draft copy.
            assert recommend_has_read.wait(timeout=20), "/recommend never reached its LLM call"
            return {"summary": drafted}

        status: dict[str, int] = {}

        def _fire(name: str, endpoint: str) -> None:
            client = _app.app.test_client()
            r = client.post(f"/api/applications/{aid}/{endpoint}", json={"context_path": ctx_path})
            status[name] = r.status_code

        with (
            patch("analyzer.recommend_bullets", _recommend_stub),
            patch("analyzer.draft_positioning_summary", _draft_stub),
        ):
            t_recommend = threading.Thread(target=_fire, args=("recommend", "recommend"))
            t_draft = threading.Thread(target=_fire, args=("draft", "draft-summary"))
            t_recommend.start()
            t_draft.start()

            t_draft.join(timeout=30)
            assert not t_draft.is_alive(), "/draft-summary thread hung"
            # Its write has landed on disk; release /recommend into its write-back.
            draft_has_persisted.set()
            t_recommend.join(timeout=30)
            assert not t_recommend.is_alive(), "/recommend thread hung"

        # Asserted BEFORE the lost-update check so a threading/DB/500 failure is
        # never mistaken for the defect under test. Different failure, different line.
        assert status.get("draft") == 200, f"/draft-summary did not succeed: {status}"
        assert status.get("recommend") == 200, f"/recommend did not succeed: {status}"

        ctx = json.loads(Path(ctx_path).read_text(encoding="utf-8"))

        # /recommend's own delta must land — it wrote last, so this holds on HEAD.
        assert ctx.get("llm_recommendations"), "/recommend's delta is missing"

        # ...and it must NOT have cost us /draft-summary's. On HEAD it does.
        assert ctx.get("composition_overrides", {}).get("summary_text") == drafted, (
            "LOST UPDATE: /recommend's whole-dict write-back erased the summary "
            "that /draft-summary had already persisted."
        )

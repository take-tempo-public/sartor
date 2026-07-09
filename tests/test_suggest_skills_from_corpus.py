"""Tests for `analyzer.suggest_skills_from_corpus` + its route (fix/review-surface-and-flows).

Corpus-wide sibling of `analyzer.suggest_skills` (tests/test_suggest_skills.py) —
the owner's "Suggest skills from my corpus" feature ask, closing the
pre-F-02 "corpus has no skills" onboarding gap. Same grounded machinery and
persistence shape, but with NO job description in view: the prompt drops
`suggest_skills`'s "the JD wants X AND corpus evidences X" AND-gate down to
evidence-alone, since that AND can never fire with an empty `<analysis>`.
  - TestFunction — empty corpus -> no proposals; dedup vs existing + in-batch;
    the prompt never emits an <analysis> block (no JD gate).
  - TestRoute — proposals inserted as pending (source='llm_proposed',
    is_pending_review=1) carrying evidence; existing (incl. retired) names
    skipped; empty corpus short-circuits to {"proposals": []}; guards.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestFunction:
    def test_empty_corpus_returns_no_proposals(self):
        from analyzer import suggest_skills_from_corpus

        result = suggest_skills_from_corpus(client=object(), context_set={"career_corpus": []})
        assert result == {"proposals": []}

    def test_dedup_against_existing_and_in_batch(self):
        from analyzer import suggest_skills_from_corpus

        def _fake_parse_or_retry(*_a, **_k):
            return {
                "proposals": [
                    {"name": "Kubernetes", "evidence": {"bullet_id": 1, "quote": "q"}},
                    {
                        "name": "python",
                        "evidence": {"bullet_id": 2, "quote": "q"},
                    },  # existing (case-insensitive)
                    {
                        "name": "Kubernetes",
                        "evidence": {"bullet_id": 3, "quote": "q"},
                    },  # in-batch dup
                    {"name": "  ", "evidence": {}},  # blank -> dropped
                ]
            }

        # Deliberately NO "llm_analysis" key — this call is JD-less by design.
        ctx = {
            "career_corpus": [
                {"id": 1, "company": "Acme", "bullets": [{"id": 1, "text": "Ran K8s."}]}
            ],
            "existing_skill_names": ["Python"],
        }
        with patch("analyzer._parse_or_retry", _fake_parse_or_retry):
            result = suggest_skills_from_corpus(client=object(), context_set=ctx)
        names = [p["name"] for p in result["proposals"]]
        assert names == ["Kubernetes"]  # python (existing) + dup + blank dropped

    def test_prior_clarifications_render_in_prompt(self):
        """D5-style cross-JD confirmed facts are offered as an additional
        grounding source alongside the corpus, same as suggest_skills()."""
        from analyzer import suggest_skills_from_corpus

        captured: dict = {}

        def _cap(client, user_prompt, **kw):
            captured["prompt"] = user_prompt
            return {"proposals": []}

        ctx = {
            "career_corpus": [{"id": 1, "company": "Acme", "bullets": []}],
            "prior_clarifications": [
                {
                    "question": "Led on-call?",
                    "answer": "Led on-call rotation for a 12-person SRE team.",
                    "kind": "experience_probe",
                }
            ],
        }
        with patch("analyzer._parse_or_retry", _cap):
            suggest_skills_from_corpus(client=object(), context_set=ctx)
        p = captured["prompt"]
        assert "<prior_clarifications>" in p
        assert "Led on-call rotation for a 12-person SRE team." in p

    def test_no_jd_gate_in_prompt(self):
        """The prompt never emits an <analysis> block — this call is JD-less
        by construction, unlike suggest_skills()'s "the JD wants X AND..."
        framing (analyzer.SUGGEST_SKILLS_SYSTEM_PROMPT)."""
        from analyzer import SUGGEST_SKILLS_FROM_CORPUS_SYSTEM_PROMPT, suggest_skills_from_corpus

        captured: dict = {}

        def _cap(client, user_prompt, *, system_prompt="", **kw):
            captured["prompt"] = user_prompt
            captured["system_prompt"] = system_prompt
            return {"proposals": []}

        ctx = {"career_corpus": [{"id": 1, "company": "Acme", "bullets": []}]}
        with patch("analyzer._parse_or_retry", _cap):
            suggest_skills_from_corpus(client=object(), context_set=ctx)
        assert "<analysis>" not in captured["prompt"]
        assert captured["system_prompt"] == SUGGEST_SKILLS_FROM_CORPUS_SYSTEM_PROMPT
        assert "the JD wants" not in SUGGEST_SKILLS_FROM_CORPUS_SYSTEM_PROMPT


# -------------------------------------------------------------------
# Route tests (stubbed LLM + DB)
# -------------------------------------------------------------------


@pytest.fixture
def suggest_corpus_app(tmp_path, monkeypatch):
    db_file = tmp_path / "suggcorpus.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("blueprints.corpus.skills._get_client", lambda: object())

    from db.session import init_db

    init_db(db_file)
    return app


def _seed_candidate_with_experience_and_skill(username="casey"):
    from db.models import Bullet, Candidate, Experience, ExperienceTitle, Skill
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username=username, name="Casey Rivera")
        session.add(c)
        session.flush()
        e = Experience(candidate_id=c.id, company="Acme", start_date="2021-01", display_order=0)
        session.add(e)
        session.flush()
        session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="SRE",
                is_official=1,
                is_pending_review=0,
                source="official",
            )
        )
        session.add(
            Bullet(
                experience_id=e.id,
                text="Migrated 40 services to Kubernetes.",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="primary:r.md",
                has_outcome=1,
            )
        )
        session.add(
            Skill(
                candidate_id=c.id,
                name="Python",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="imported",
            )
        )
        # A RETIRED skill — must still be excluded from re-proposal (dedup
        # includes retired rows, mirroring _insert_pending_skills).
        session.add(
            Skill(
                candidate_id=c.id,
                name="Java",
                display_order=1,
                is_active=0,
                is_pending_review=0,
                source="imported",
            )
        )
        session.commit()
        return c.id
    finally:
        session.close()


class TestRoute:
    def test_proposals_inserted_as_pending_and_dedup_incl_retired(self, suggest_corpus_app):
        _seed_candidate_with_experience_and_skill()

        def _stub(client, context_set, *, username="", run_id=""):
            assert "Python" in (context_set.get("existing_skill_names") or [])
            assert "Java" in (context_set.get("existing_skill_names") or [])
            return {
                "proposals": [
                    {
                        "name": "Kubernetes",
                        "category": "platform",
                        "evidence": {
                            "bullet_id": 1,
                            "quote": "Migrated 40 services to Kubernetes.",
                        },
                        "rationale": "A bullet shows direct Kubernetes ownership.",
                    },
                    {"name": "Python", "evidence": {}},  # existing, active -> skipped
                    {"name": "Java", "evidence": {}},  # existing, RETIRED -> still skipped
                ]
            }

        with patch("analyzer.suggest_skills_from_corpus", _stub):
            client = suggest_corpus_app.test_client()
            r = client.post("/api/users/casey/skills/suggest-from-corpus")
        assert r.status_code == 200, r.get_data(as_text=True)
        created = r.get_json()["proposals"]
        assert [p["name"] for p in created] == ["Kubernetes"]
        assert created[0]["is_pending_review"] is True
        assert created[0]["source"] == "llm_proposed"
        assert created[0]["evidence"]["bullet_id"] == 1

        # Grounding gate: pending proposal excluded from the default list.
        default = client.get("/api/users/casey/skills").get_json()["skills"]
        assert {s["name"] for s in default} == {"Python"}
        pending = client.get("/api/users/casey/skills?include_pending=1").get_json()["skills"]
        assert {s["name"] for s in pending} == {"Python", "Kubernetes"}

    def test_empty_corpus_returns_empty_proposals_without_llm_call(self, suggest_corpus_app):
        from db.models import Candidate
        from db.session import get_session

        session = get_session()
        try:
            session.add(Candidate(username="casey", name="Casey Rivera"))
            session.commit()
        finally:
            session.close()

        with patch("analyzer.suggest_skills_from_corpus") as mock_fn:
            client = suggest_corpus_app.test_client()
            r = client.post("/api/users/casey/skills/suggest-from-corpus")
        assert r.status_code == 200
        assert r.get_json() == {"proposals": []}
        mock_fn.assert_not_called()

    def test_unknown_candidate_404(self, suggest_corpus_app):
        client = suggest_corpus_app.test_client()
        r = client.post("/api/users/casey/skills/suggest-from-corpus")
        assert r.status_code == 404

    def test_unknown_user_400(self, suggest_corpus_app):
        client = suggest_corpus_app.test_client()
        r = client.post("/api/users/ghost/skills/suggest-from-corpus")
        assert r.status_code == 400

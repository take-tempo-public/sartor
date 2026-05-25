"""Tests for `corpus_to_json_resume.build_json_resume_from_corpus`.

This module is the new architectural foundation for the live preview
(post β.6 hands-on review): the JSON Resume document is built directly
from Candidate + Experience + Bullet + SummaryItem rows instead of
parsing it back out of a `resume_*.jsonresume.json` sidecar written by
`/api/generate`. The preview now works BEFORE any generate has run.

Behaviors pinned down here:

  Identity & basics
    - Candidate name / email / phone / website appear in `basics`
    - LinkedIn URL becomes a `profiles[]` entry with extracted username
    - Empty / unset fields are omitted (no None leaks to the JSON)

  Summary resolution (priority chain)
    - composition_overrides.pinned_summary_id wins
    - llm_summary_recommendation.recommendation.summary_item_id is next
    - First-active SummaryItem is next
    - Candidate.profile_text is the final fallback
    - Soft-retired (is_active=0) variants are skipped on every step
    - The chosen source is reported in meta.callback.summary_source

  Work history
    - All experiences in start_date desc, id desc order
    - Official title preferred over first eligible
    - Active bullets included by default; excluded ones filtered;
      added ones included; pinned + recommended interact correctly
    - When llm_recommendations are present, the effective set is
      (recommended ∪ added ∪ pinned) − excluded

  Defensive shape
    - Empty / unknown candidate returns the empty document skeleton
    - meta.callback carries the correlation fields the preview needs
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def session(tmp_path, monkeypatch):
    """Fresh in-memory DB so each test can seed without bleed."""
    db_file = tmp_path / "corpus.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from db.session import get_session, init_db
    init_db(db_file)
    s = get_session()
    yield s
    s.close()


def _seed_candidate(session, *, username="casey", name="Casey Rivera",
                    profile_text="Default candidate summary.",
                    email="casey@example.com", phone=None,
                    linkedin_url=None, website_url=None) -> int:
    from db.models import Candidate
    c = Candidate(
        username=username, name=name, profile_text=profile_text,
        email=email, phone=phone,
        linkedin_url=linkedin_url, website_url=website_url,
    )
    session.add(c)
    session.flush()
    session.commit()
    return c.id


def _seed_experience(session, candidate_id: int, *,
                     company="Polaris", position="Lead PM",
                     start_date="2022-01", end_date="present",
                     bullets=(),
                     location: str | None = None) -> tuple[int, list[int]]:
    """Seed one experience with an official title + bullets. Returns
    (experience_id, [bullet_ids]) for downstream assertions."""
    from db.models import Bullet, Experience, ExperienceTitle
    exp = Experience(
        candidate_id=candidate_id, company=company,
        start_date=start_date, end_date=end_date, location=location,
    )
    session.add(exp)
    session.flush()
    session.add(ExperienceTitle(
        experience_id=exp.id, title=position,
        is_official=1, source="official",
    ))
    bids: list[int] = []
    for i, text in enumerate(bullets):
        b = Bullet(
            experience_id=exp.id, text=text,
            display_order=i, is_active=1, source="resume_import",
        )
        session.add(b)
        session.flush()
        bids.append(b.id)
    session.commit()
    return exp.id, bids


def _seed_summary_variant(session, candidate_id: int, *, text: str,
                         display_order: int = 0, is_active: int = 1) -> int:
    from db.models import SummaryItem
    si = SummaryItem(
        candidate_id=candidate_id, text=text,
        display_order=display_order, is_active=is_active,
    )
    session.add(si)
    session.flush()
    session.commit()
    return si.id


def _ctx_file(tmp_path, **fields) -> str:
    """Write a context_*.json file the builder can consume."""
    path = tmp_path / "context_test.json"
    path.write_text(json.dumps(fields), encoding="utf-8")
    return str(path)


# -------------------------------------------------------------------
# Basics / identity
# -------------------------------------------------------------------


class TestBasics:
    def test_emits_name_email_summary(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["name"] == "Casey Rivera"
        assert doc["basics"]["email"] == "casey@example.com"
        assert doc["basics"]["summary"] == "Default candidate summary."

    def test_linkedin_becomes_profile_entry(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(
            session, linkedin_url="https://linkedin.com/in/caseyrivera/",
        )
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["profiles"] == [{
            "network":  "LinkedIn",
            "url":      "https://linkedin.com/in/caseyrivera/",
            "username": "caseyrivera",
        }]

    def test_website_becomes_basics_url(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session, website_url="https://casey.dev")
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["url"] == "https://casey.dev"

    def test_unknown_candidate_returns_empty_skeleton(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        doc = build_json_resume_from_corpus(session, candidate_id=99999)
        assert doc["basics"] == {}
        assert doc["work"] == []
        assert doc["education"] == []


# -------------------------------------------------------------------
# Summary resolution priority chain
# -------------------------------------------------------------------


class TestSummaryResolution:
    def test_pinned_wins_over_recommendation(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        rec_id = _seed_summary_variant(session, cid, text="Rec variant.")
        pin_id = _seed_summary_variant(
            session, cid, text="Pin variant.", display_order=1,
        )
        ctx = _ctx_file(tmp_path,
                       composition_overrides={"pinned_summary_id": pin_id},
                       llm_summary_recommendation={
                           "recommendation": {"summary_item_id": rec_id},
                       })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        assert doc["basics"]["summary"] == "Pin variant."
        assert doc["meta"]["callback"]["summary_source"] == "pinned"
        assert doc["meta"]["callback"]["chosen_summary_id"] == pin_id

    def test_recommendation_wins_when_no_pin(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        rec_id = _seed_summary_variant(session, cid, text="Rec variant.")
        ctx = _ctx_file(tmp_path, llm_summary_recommendation={
            "recommendation": {"summary_item_id": rec_id},
        })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        assert doc["basics"]["summary"] == "Rec variant."
        assert doc["meta"]["callback"]["summary_source"] == "recommended"

    def test_first_active_variant_when_no_application_choice(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session, profile_text="Old profile_text.")
        _seed_summary_variant(session, cid, text="First active.")
        doc = build_json_resume_from_corpus(session, cid)
        # First-active variant takes precedence over profile_text fallback
        assert doc["basics"]["summary"] == "First active."
        assert doc["meta"]["callback"]["summary_source"] == "first_active"

    def test_profile_text_when_no_variants(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session, profile_text="Only profile_text.")
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["summary"] == "Only profile_text."
        assert doc["meta"]["callback"]["summary_source"] == "candidate_default"

    def test_retired_variant_skipped(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session, profile_text="Fallback profile.")
        retired = _seed_summary_variant(
            session, cid, text="Retired variant.", is_active=0,
        )
        ctx = _ctx_file(tmp_path,
                       composition_overrides={"pinned_summary_id": retired})
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        # Soft-retired pin → fall through to profile_text
        assert doc["basics"]["summary"] == "Fallback profile."


# -------------------------------------------------------------------
# Work history shape
# -------------------------------------------------------------------


class TestWorkHistory:
    def test_emits_company_position_dates(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("Shipped X.",))
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["work"] == [{
            "name":       "Polaris",
            "position":   "Lead PM",
            "startDate":  "2022-01",
            "endDate":    "present",
            "highlights": ["Shipped X."],
        }]

    def test_excluded_bullets_drop_out(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        _eid, bids = _seed_experience(session, cid, bullets=(
            "Bullet one.", "Bullet two.", "Bullet three.",
        ))
        ctx = _ctx_file(tmp_path, composition_overrides={
            "pinned": [], "excluded": [bids[1]], "added": [],
        })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        assert doc["work"][0]["highlights"] == ["Bullet one.", "Bullet three."]

    def test_recommendations_filter_to_curated_set(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        eid, bids = _seed_experience(session, cid, bullets=(
            "Bullet one.", "Bullet two.", "Bullet three.",
        ))
        # Recommend just the second bullet
        ctx = _ctx_file(tmp_path, llm_recommendations={
            str(eid): {"bullet_ids": [bids[1]]},
        })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        assert doc["work"][0]["highlights"] == ["Bullet two."]

    def test_pinned_and_added_join_recommendations(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        eid, bids = _seed_experience(session, cid, bullets=(
            "Bullet one.", "Bullet two.", "Bullet three.",
        ))
        # Recommend bullet two; pin bullet one; add bullet three
        ctx = _ctx_file(tmp_path,
                       llm_recommendations={
                           str(eid): {"bullet_ids": [bids[1]]},
                       },
                       composition_overrides={
                           "pinned": [bids[0]],
                           "excluded": [],
                           "added": [bids[2]],
                       })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        # All three end up in highlights, in display order
        assert doc["work"][0]["highlights"] == [
            "Bullet one.", "Bullet two.", "Bullet three.",
        ]

    def test_experiences_sorted_by_start_date_desc(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        _seed_experience(session, cid, company="Old Co",
                         start_date="2018-01", end_date="2020-12",
                         bullets=("Old bullet.",))
        _seed_experience(session, cid, company="New Co",
                         start_date="2022-01", end_date="present",
                         bullets=("New bullet.",))
        doc = build_json_resume_from_corpus(session, cid)
        assert [w["name"] for w in doc["work"]] == ["New Co", "Old Co"]


# -------------------------------------------------------------------
# Meta / callback envelope
# -------------------------------------------------------------------


class TestMetaCallback:
    def test_application_id_round_trips(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        doc = build_json_resume_from_corpus(
            session, cid, application_id=42,
        )
        assert doc["meta"]["callback"]["application_id"] == 42
        assert doc["meta"]["callback"]["candidate_id"] == cid

    def test_bullet_overrides_active_flag(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        _eid, bids = _seed_experience(session, cid, bullets=("X.", "Y."))
        ctx = _ctx_file(tmp_path, composition_overrides={
            "pinned": [], "excluded": [bids[0]], "added": [],
        })
        doc = build_json_resume_from_corpus(
            session, cid, context_path=ctx,
        )
        assert doc["meta"]["callback"]["bullet_overrides_active"] is True

    def test_no_overrides_false(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("X.",))
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["meta"]["callback"]["bullet_overrides_active"] is False

    def test_missing_context_path_is_safe(self, session):
        """Bogus path is silently ignored — builder falls through to
        the no-overrides path rather than erroring."""
        from corpus_to_json_resume import build_json_resume_from_corpus
        cid = _seed_candidate(session)
        doc = build_json_resume_from_corpus(
            session, cid, context_path="/does/not/exist.json",
        )
        # Identity still emits — no exception
        assert doc["basics"]["name"] == "Casey Rivera"

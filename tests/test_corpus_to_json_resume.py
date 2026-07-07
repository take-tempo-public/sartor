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
    - The chosen source is reported in meta.sartor.summary_source

  Work history
    - All experiences in start_date desc, id desc order
    - Official title preferred over first eligible
    - Active bullets included by default; excluded ones filtered;
      added ones included; pinned + recommended interact correctly
    - When llm_recommendations are present, the effective set is
      (recommended ∪ added ∪ pinned) − excluded

  Defensive shape
    - Empty / unknown candidate returns the empty document skeleton
    - meta.sartor carries the correlation fields the preview needs
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


def _seed_candidate(
    session,
    *,
    username="casey",
    name="Casey Rivera",
    profile_text="Default candidate summary.",
    email="casey@example.com",
    phone=None,
    linkedin_url=None,
    website_url=None,
) -> int:
    from db.models import Candidate

    c = Candidate(
        username=username,
        name=name,
        profile_text=profile_text,
        email=email,
        phone=phone,
        linkedin_url=linkedin_url,
        website_url=website_url,
    )
    session.add(c)
    session.flush()
    session.commit()
    return c.id


def _seed_experience(
    session,
    candidate_id: int,
    *,
    company="Polaris",
    position="Lead PM",
    start_date="2022-01",
    end_date="present",
    bullets=(),
    location: str | None = None,
) -> tuple[int, list[int]]:
    """Seed one experience with an official title + bullets. Returns
    (experience_id, [bullet_ids]) for downstream assertions."""
    from db.models import Bullet, Experience, ExperienceTitle

    exp = Experience(
        candidate_id=candidate_id,
        company=company,
        start_date=start_date,
        end_date=end_date,
        location=location,
    )
    session.add(exp)
    session.flush()
    session.add(
        ExperienceTitle(
            experience_id=exp.id,
            title=position,
            is_official=1,
            source="official",
        )
    )
    bids: list[int] = []
    for i, text in enumerate(bullets):
        b = Bullet(
            experience_id=exp.id,
            text=text,
            display_order=i,
            is_active=1,
            source="resume_import",
        )
        session.add(b)
        session.flush()
        bids.append(b.id)
    session.commit()
    return exp.id, bids


def _seed_pending_bullet(
    session,
    experience_id: int,
    *,
    text="Pending gap-fill bullet.",
    source="llm_proposed:abc123",
) -> int:
    """Seed one is_active=1, is_pending_review=1 bullet (an accepted gap-fill or a
    promoted-clarification candidate) — the case the resolver pending-leak guard
    governs. Returns its id."""
    from db.models import Bullet

    b = Bullet(
        experience_id=experience_id,
        text=text,
        display_order=99,
        is_active=1,
        is_pending_review=1,
        source=source,
    )
    session.add(b)
    session.flush()
    session.commit()
    return b.id


def _seed_summary_variant(
    session, candidate_id: int, *, text: str, display_order: int = 0, is_active: int = 1
) -> int:
    from db.models import SummaryItem

    si = SummaryItem(
        candidate_id=candidate_id,
        text=text,
        display_order=display_order,
        is_active=is_active,
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
            session,
            linkedin_url="https://linkedin.com/in/caseyrivera/",
        )
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["profiles"] == [
            {
                "network": "LinkedIn",
                "url": "https://linkedin.com/in/caseyrivera/",
                "username": "caseyrivera",
            }
        ]

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
            session,
            cid,
            text="Pin variant.",
            display_order=1,
        )
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={"pinned_summary_id": pin_id},
            llm_summary_recommendation={
                "recommendation": {"summary_item_id": rec_id},
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        assert doc["basics"]["summary"] == "Pin variant."
        assert doc["meta"]["sartor"]["summary_source"] == "pinned"
        assert doc["meta"]["sartor"]["chosen_summary_id"] == pin_id

    def test_recommendation_wins_when_no_pin(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        rec_id = _seed_summary_variant(session, cid, text="Rec variant.")
        ctx = _ctx_file(
            tmp_path,
            llm_summary_recommendation={
                "recommendation": {"summary_item_id": rec_id},
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        assert doc["basics"]["summary"] == "Rec variant."
        assert doc["meta"]["sartor"]["summary_source"] == "recommended"

    def test_first_active_variant_when_no_application_choice(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session, profile_text="Old profile_text.")
        _seed_summary_variant(session, cid, text="First active.")
        doc = build_json_resume_from_corpus(session, cid)
        # First-active variant takes precedence over profile_text fallback
        assert doc["basics"]["summary"] == "First active."
        assert doc["meta"]["sartor"]["summary_source"] == "first_active"

    def test_profile_text_when_no_variants(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session, profile_text="Only profile_text.")
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["summary"] == "Only profile_text."
        assert doc["meta"]["sartor"]["summary_source"] == "candidate_default"

    def test_retired_variant_skipped(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session, profile_text="Fallback profile.")
        retired = _seed_summary_variant(
            session,
            cid,
            text="Retired variant.",
            is_active=0,
        )
        ctx = _ctx_file(tmp_path, composition_overrides={"pinned_summary_id": retired})
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
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
        assert doc["work"] == [
            {
                "name": "Polaris",
                "position": "Lead PM",
                "startDate": "2022-01",
                "endDate": "present",
                "highlights": ["Shipped X."],
            }
        ]

    def test_excluded_bullets_drop_out(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _eid, bids = _seed_experience(
            session,
            cid,
            bullets=(
                "Bullet one.",
                "Bullet two.",
                "Bullet three.",
            ),
        )
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "pinned": [],
                "excluded": [bids[1]],
                "added": [],
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        assert doc["work"][0]["highlights"] == ["Bullet one.", "Bullet three."]

    def test_recommendations_filter_to_curated_set(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, bids = _seed_experience(
            session,
            cid,
            bullets=(
                "Bullet one.",
                "Bullet two.",
                "Bullet three.",
            ),
        )
        # Recommend just the second bullet
        ctx = _ctx_file(
            tmp_path,
            llm_recommendations={
                str(eid): {"bullet_ids": [bids[1]]},
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        assert doc["work"][0]["highlights"] == ["Bullet two."]

    def test_pinned_and_added_join_recommendations(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, bids = _seed_experience(
            session,
            cid,
            bullets=(
                "Bullet one.",
                "Bullet two.",
                "Bullet three.",
            ),
        )
        # Recommend bullet two; pin bullet one; add bullet three
        ctx = _ctx_file(
            tmp_path,
            llm_recommendations={
                str(eid): {"bullet_ids": [bids[1]]},
            },
            composition_overrides={
                "pinned": [bids[0]],
                "excluded": [],
                "added": [bids[2]],
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        # All three end up in highlights, in display order
        assert doc["work"][0]["highlights"] == [
            "Bullet one.",
            "Bullet two.",
            "Bullet three.",
        ]

    def test_experiences_sorted_by_start_date_desc(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_experience(
            session,
            cid,
            company="Old Co",
            start_date="2018-01",
            end_date="2020-12",
            bullets=("Old bullet.",),
        )
        _seed_experience(
            session,
            cid,
            company="New Co",
            start_date="2022-01",
            end_date="present",
            bullets=("New bullet.",),
        )
        doc = build_json_resume_from_corpus(session, cid)
        assert [w["name"] for w in doc["work"]] == ["New Co", "Old Co"]


# -------------------------------------------------------------------
# B.4 (Sprint 6.6) — per-role intro (ExperienceSummaryItem) → work[].summary.
# OPT-IN: emitted only when composition_overrides.use_experience_summaries is on
# AND the role has an explicit chosen_experience_summary_ids pick. No fallback
# to the legacy Experience.summary column.
# -------------------------------------------------------------------


def _seed_experience_summary(
    session, experience_id: int, *, text: str, display_order: int = 0, is_active: int = 1
) -> int:
    from db.models import ExperienceSummaryItem

    si = ExperienceSummaryItem(
        experience_id=experience_id,
        text=text,
        display_order=display_order,
        is_active=is_active,
    )
    session.add(si)
    session.flush()
    session.commit()
    return si.id


def _set_legacy_summary(session, experience_id: int, text: str) -> None:
    from db.models import Experience

    exp = session.query(Experience).filter_by(id=experience_id).first()
    exp.summary = text
    session.commit()


class TestExperienceSummary:
    def test_toggle_off_emits_no_summary(self, session, tmp_path):
        """Toggle off (default) → no work[].summary even with a chosen pick AND
        a legacy Experience.summary set (the legacy field is never auto-emitted)."""
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        sid = _seed_experience_summary(session, eid, text="Owned platform scale.")
        _set_legacy_summary(session, eid, "Legacy intro that must not leak.")
        # Picks present but toggle absent → opt-in gate closed.
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "chosen_experience_summary_ids": {str(eid): sid},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert "summary" not in doc["work"][0]

    def test_toggle_on_with_pick_emits_chosen_text(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        _seed_experience_summary(session, eid, text="First framing.", display_order=0)
        sid2 = _seed_experience_summary(session, eid, text="Chosen framing.", display_order=1)
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): sid2},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["work"][0]["summary"] == "Chosen framing."

    def test_toggle_on_no_pick_for_role_emits_nothing(self, session, tmp_path):
        """Opt-in is per-role: toggle on but no pick for this role → no summary
        (no auto-apply of a recommendation or first-active variant)."""
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        _seed_experience_summary(session, eid, text="A variant.")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert "summary" not in doc["work"][0]

    def test_cleared_sentinel_zero_emits_nothing(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        _seed_experience_summary(session, eid, text="A variant.")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): 0},  # explicitly cleared
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert "summary" not in doc["work"][0]

    def test_inactive_or_foreign_pick_skipped(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        other_eid, _ = _seed_experience(
            session, cid, company="Other", start_date="2019-01", end_date="2020-01", bullets=("Y.",)
        )
        retired = _seed_experience_summary(session, eid, text="Retired.", is_active=0)
        # A variant that belongs to eid, mis-assigned as other_eid's pick.
        foreign = _seed_experience_summary(session, eid, text="Belongs to eid.")
        # eid's pick is a retired (own) variant; other_eid's pick is a variant
        # that belongs to a DIFFERENT role — both must resolve to nothing.
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): retired, str(other_eid): foreign},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        for w in doc["work"]:
            assert "summary" not in w

    def test_meta_sartor_records_opt_in_state(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, bullets=("Shipped X.",))
        sid = _seed_experience_summary(session, eid, text="Chosen framing.")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "use_experience_summaries": True,
                "chosen_experience_summary_ids": {str(eid): sid},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        cb = doc["meta"]["sartor"]
        assert cb["use_experience_summaries"] is True
        assert cb["chosen_experience_summary_ids"] == {str(eid): sid}


# -------------------------------------------------------------------
# Meta / sartor envelope
# -------------------------------------------------------------------


class TestMetaSartor:
    def test_application_id_round_trips(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        doc = build_json_resume_from_corpus(
            session,
            cid,
            application_id=42,
        )
        assert doc["meta"]["sartor"]["application_id"] == 42
        assert doc["meta"]["sartor"]["candidate_id"] == cid

    def test_bullet_overrides_active_flag(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _eid, bids = _seed_experience(session, cid, bullets=("X.", "Y."))
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "pinned": [],
                "excluded": [bids[0]],
                "added": [],
            },
        )
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path=ctx,
        )
        assert doc["meta"]["sartor"]["bullet_overrides_active"] is True

    def test_no_overrides_false(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("X.",))
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["meta"]["sartor"]["bullet_overrides_active"] is False

    def test_missing_context_path_is_safe(self, session):
        """Bogus path is silently ignored — builder falls through to
        the no-overrides path rather than erroring."""
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        doc = build_json_resume_from_corpus(
            session,
            cid,
            context_path="/does/not/exist.json",
        )
        # Identity still emits — no exception
        assert doc["basics"]["name"] == "Casey Rivera"


class TestTitlePin:
    """feat/compose-add-title — composition_overrides.pinned_title_ids drives
    work[].position in the preview (pin → official → first); a stale/ineligible
    pin falls through so non-pinned output is unchanged."""

    def _seed_alt(self, session, exp_id, *, title="Director, AI", eligible=True):
        from db.models import ExperienceTitle

        t = ExperienceTitle(
            experience_id=exp_id,
            title=title,
            is_official=0,
            truthful_enough_to_use=1 if eligible else 0,
            is_pending_review=0,
            source="user_added",
        )
        session.add(t)
        session.flush()
        session.commit()
        return t.id

    def test_pinned_title_overrides_official(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, position="Lead PM")
        alt = self._seed_alt(session, eid, title="Director, AI")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={"pinned_title_ids": {str(eid): alt}},
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["work"][0]["position"] == "Director, AI"

    def test_unpinned_keeps_official(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, position="Lead PM")
        self._seed_alt(session, eid, title="Director, AI")
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["work"][0]["position"] == "Lead PM"

    def test_ineligible_pin_falls_back_to_official(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _ = _seed_experience(session, cid, position="Lead PM")
        # truthful_enough_to_use=0 → not an eligible pick; the resolution must
        # ignore the stale pin and fall through to the official title.
        stale = self._seed_alt(session, eid, title="Ghost Title", eligible=False)
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={"pinned_title_ids": {str(eid): stale}},
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["work"][0]["position"] == "Lead PM"


# -------------------------------------------------------------------
# B.5 (Sprint 6.6) — skill curation: skills[] reflects recommend_skills +
# pin/drop/reorder; pending/inactive excluded; default path is all-active
# in display order (the byte-identical-ish fallback).
# -------------------------------------------------------------------


def _seed_skill(session, candidate_id, name, *, display_order=0, is_active=1, is_pending_review=0):
    from db.models import Skill

    sk = Skill(
        candidate_id=candidate_id,
        name=name,
        display_order=display_order,
        is_active=is_active,
        is_pending_review=is_pending_review,
        source="imported",
    )
    session.add(sk)
    session.flush()
    session.commit()
    return sk.id


class TestSkills:
    def test_all_active_in_display_order_no_overrides(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_skill(session, cid, "Python", display_order=0)
        _seed_skill(session, cid, "Go", display_order=1)
        doc = build_json_resume_from_corpus(session, cid)
        assert [s["name"] for s in doc["skills"]] == ["Python", "Go"]

    def test_pending_and_inactive_excluded(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_skill(session, cid, "Python", display_order=0)
        _seed_skill(session, cid, "Rust", display_order=1, is_pending_review=1)
        _seed_skill(session, cid, "Perl", display_order=2, is_active=0)
        doc = build_json_resume_from_corpus(session, cid)
        assert [s["name"] for s in doc["skills"]] == ["Python"]

    def test_recommendation_curates_and_orders(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        py = _seed_skill(session, cid, "Python", display_order=0)
        _seed_skill(session, cid, "Go", display_order=1)
        k8s = _seed_skill(session, cid, "Kubernetes", display_order=2)
        ctx = _ctx_file(
            tmp_path,
            llm_skill_recommendations={
                "recommendation": {"skill_ids": [k8s, py]},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        # Recommended subset, in recommended order (Go dropped — not recommended).
        assert [s["name"] for s in doc["skills"]] == ["Kubernetes", "Python"]

    def test_exclude_and_reorder_without_recommendation(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        py = _seed_skill(session, cid, "Python", display_order=0)
        go = _seed_skill(session, cid, "Go", display_order=1)
        k8s = _seed_skill(session, cid, "Kubernetes", display_order=2)
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "excluded_skill_ids": [go],
                "skill_order": [k8s, py],
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        # No recommendation → all-active (Py, Go, K8s) minus excluded Go,
        # then reordered by skill_order [K8s, Py].
        assert [s["name"] for s in doc["skills"]] == ["Kubernetes", "Python"]

    def test_meta_records_curation_state(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        py = _seed_skill(session, cid, "Python", display_order=0)
        ctx = _ctx_file(
            tmp_path,
            llm_skill_recommendations={
                "recommendation": {"skill_ids": [py]},
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        cb = doc["meta"]["sartor"]
        assert cb["skill_curation_active"] is True
        assert cb["recommended_skill_ids"] == [py]

    def test_meta_curation_inactive_by_default(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_skill(session, cid, "Python", display_order=0)
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["meta"]["sartor"]["skill_curation_active"] is False


# -------------------------------------------------------------------
# Generation-experience re-architecture (fix/compose-frozen-composition):
# the resolver becomes the single producer of the frozen composition —
# honors bullet_order, folds in accepted gap-fill bullets, resolves the
# Compose-drafted summary text, emits order-aligned meta.sartor provenance,
# and freeze_approved_composition() stamps the value snapshot.
# -------------------------------------------------------------------


class TestBulletOrder:
    def test_bullet_order_reorders_highlights(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, bids = _seed_experience(
            session, cid, bullets=("Bullet one.", "Bullet two.", "Bullet three.")
        )
        # Explicit order: third, first — second is unlisted → keeps its place at
        # the end (by display_order), matching analyzer._stable_user_prefix.
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={"bullet_order": {str(eid): [bids[2], bids[0]]}},
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["work"][0]["highlights"] == [
            "Bullet three.",
            "Bullet one.",
            "Bullet two.",
        ]

    def test_no_bullet_order_is_display_order(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("Bullet one.", "Bullet two."))
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["work"][0]["highlights"] == ["Bullet one.", "Bullet two."]


class TestDraftedSummary:
    def test_drafted_summary_text_wins(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        # A pinned variant would normally win — the drafted text overrides even it.
        pin_id = _seed_summary_variant(session, cid, text="Pinned variant.")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "pinned_summary_id": pin_id,
                "summary_text": "A tailored two-sentence positioning summary.",
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["basics"]["summary"] == "A tailored two-sentence positioning summary."
        assert doc["meta"]["sartor"]["summary_source"] == "drafted"

    def test_edited_flag_reports_edited_source(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={
                "summary_text": "Hand-edited summary.",
                "summary_text_edited": True,
            },
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["basics"]["summary"] == "Hand-edited summary."
        assert doc["meta"]["sartor"]["summary_source"] == "edited"

    def test_blank_summary_text_falls_through(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session, profile_text="Fallback profile.")
        # No summary_text → the legacy chain (here profile_text).
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["basics"]["summary"] == "Fallback profile."
        assert doc["meta"]["sartor"]["summary_source"] == "candidate_default"


class TestAcceptedGeneratedBullets:
    def test_accepted_generated_bullet_joins_curated_set(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, bids = _seed_experience(
            session, cid, bullets=("Bullet one.", "Bullet two.", "Bullet three.")
        )
        # Recommend only bullet one; accept bullet three (as a "gap-fill" id) —
        # both survive the narrowing, bullet two drops.
        ctx = _ctx_file(
            tmp_path,
            llm_recommendations={str(eid): {"bullet_ids": [bids[0]]}},
            composition_overrides={"accepted_generated_bullet_ids": [bids[2]]},
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert doc["work"][0]["highlights"] == ["Bullet one.", "Bullet three."]
        assert doc["meta"]["sartor"]["accepted_generated_bullet_ids"] == [bids[2]]
        assert doc["meta"]["sartor"]["bullet_overrides_active"] is True


class TestPendingLeakGuard:
    """Phase 3 — a pending+active bullet (an accepted gap-fill) must render for
    THIS application (its id in accepted_generated_bullet_ids) but must NOT leak
    into another application's default all-active render. Mirrors the skills guard
    in _collect_skills (is_pending_review=0)."""

    def test_pending_active_bullet_excluded_by_default(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _bids = _seed_experience(session, cid, bullets=("Canonical bullet.",))
        _seed_pending_bullet(session, eid, text="Leaky pending bullet.")
        # No accepted_generated_bullet_ids override → the default all-active path.
        # The pending bullet must NOT appear (it would leak into every other app).
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["work"][0]["highlights"] == ["Canonical bullet."]

    def test_pending_bullet_renders_when_accepted(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        eid, _bids = _seed_experience(session, cid, bullets=("Canonical bullet.",))
        pending_id = _seed_pending_bullet(session, eid, text="Accepted gap-fill bullet.")
        ctx = _ctx_file(
            tmp_path,
            composition_overrides={"accepted_generated_bullet_ids": [pending_id]},
        )
        doc = build_json_resume_from_corpus(session, cid, context_path=ctx)
        assert "Accepted gap-fill bullet." in doc["work"][0]["highlights"]
        assert "Canonical bullet." in doc["work"][0]["highlights"]

    def test_default_path_no_pending_byte_identical(self, session):
        """A candidate with only non-pending bullets renders exactly as before the
        guard — the guard's extra term is a no-op when nothing is pending."""
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("One.", "Two.", "Three."))
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["work"][0]["highlights"] == ["One.", "Two.", "Three."]

    def test_freeze_includes_accepted_pending_bullet(self, session, tmp_path):
        """freeze_approved_composition (the resolver wrapper) must fold an accepted
        pending bullet into the frozen doc + its provenance."""
        from corpus_to_json_resume import freeze_approved_composition

        cid = _seed_candidate(session)
        eid, _bids = _seed_experience(session, cid, bullets=("Canonical bullet.",))
        pending_id = _seed_pending_bullet(session, eid, text="Accepted gap-fill bullet.")
        ctx_data = {
            "composition_overrides": {"accepted_generated_bullet_ids": [pending_id]},
        }
        doc = freeze_approved_composition(session, cid, application_id=5, context_data=ctx_data)
        assert "Accepted gap-fill bullet." in doc["work"][0]["highlights"]
        assert pending_id in doc["meta"]["sartor"]["accepted_generated_bullet_ids"]
        assert pending_id in doc["meta"]["sartor"]["work_provenance"][0]["highlight_ids"]


class TestFrozenCompositionProvenance:
    def test_work_provenance_is_order_aligned(self, session, tmp_path):
        from corpus_to_json_resume import build_json_resume_from_corpus
        from db.models import ExperienceTitle

        cid = _seed_candidate(session)
        eid, bids = _seed_experience(session, cid, bullets=("One.", "Two."))
        tid = session.query(ExperienceTitle).filter_by(experience_id=eid).first().id
        doc = build_json_resume_from_corpus(session, cid, application_id=7)
        prov = doc["meta"]["sartor"]["work_provenance"]
        assert prov == [
            {
                "experience_id": eid,
                "title_id": tid,
                "role_intro_id": None,
                "highlight_ids": [bids[0], bids[1]],
            }
        ]
        # highlight_ids align 1:1 with the emitted highlights text.
        assert len(prov[0]["highlight_ids"]) == len(doc["work"][0]["highlights"])

    def test_skill_ids_emitted(self, session):
        from corpus_to_json_resume import build_json_resume_from_corpus

        cid = _seed_candidate(session)
        py = _seed_skill(session, cid, "Python", display_order=0)
        go = _seed_skill(session, cid, "Go", display_order=1)
        doc = build_json_resume_from_corpus(session, cid)
        assert doc["meta"]["sartor"]["skill_ids"] == [py, go]


class TestFreezeApprovedComposition:
    def test_freeze_stamps_frozen_and_resolves_text(self, session):
        from corpus_to_json_resume import freeze_approved_composition

        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("Shipped X.",))
        _seed_skill(session, cid, "Python")
        doc = freeze_approved_composition(session, cid, application_id=3)
        # A valid JSON Resume with resolved text + the frozen marker.
        assert doc["meta"]["sartor"]["frozen"] is True
        assert doc["meta"]["sartor"]["application_id"] == 3
        assert doc["work"][0]["highlights"] == ["Shipped X."]
        assert [s["name"] for s in doc["skills"]] == ["Python"]

    def test_context_data_short_circuits_file_read(self, session):
        """The freeze path passes in-memory overrides (not yet on disk); the
        resolver must read them from context_data, not a (bogus) context_path."""
        from corpus_to_json_resume import freeze_approved_composition

        cid = _seed_candidate(session)
        _seed_experience(session, cid, bullets=("Shipped X.",))
        doc = freeze_approved_composition(
            session,
            cid,
            application_id=3,
            context_path="/does/not/exist.json",
            context_data={"composition_overrides": {"summary_text": "In-memory summary."}},
        )
        assert doc["basics"]["summary"] == "In-memory summary."
        assert doc["meta"]["sartor"]["summary_source"] == "drafted"

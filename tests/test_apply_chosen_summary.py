"""Tests for `app._apply_chosen_summary` (Phase β.6d).

Pins down the priority chain that picks which SummaryItem text
becomes the candidate's positioning in the generate-time context_set:

  1. composition_overrides.pinned_summary_id (user's explicit pin)
  2. llm_summary_recommendation.recommendation.summary_item_id
  3. unchanged — fallback to existing Candidate.profile_text

Plus the back-compat / defensive paths:
  - No application_id → no-op
  - Missing chosen variant → fallback
  - Inactive (soft-retired) variant → fallback
  - Blank-text variant → fallback
"""

from __future__ import annotations

import pytest


@pytest.fixture
def app_with_data(tmp_path, monkeypatch):
    """Fresh DB so we can call `_apply_chosen_summary` against a real
    SummaryItem row. The helper moved to `blueprints/generation.py` (Sprint
    8.3c); it operates on the context_set dict + DB only (no app context), so
    the fixture just sets up the tmp DB and returns the blueprint module."""
    db_file = tmp_path / "apply.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from db.session import init_db

    init_db(db_file)

    import blueprints.generation as bgen

    return bgen


def _seed(
    *, profile_text: str = "Default profile text.", variants: list[str] | None = None
) -> tuple[int, int, list[int]]:
    """Seed candidate + application + (optional) SummaryItem variants.
    Returns (candidate_id, application_id, [variant_ids])."""
    from db.models import Application, Candidate, SummaryItem
    from db.session import get_session

    session = get_session()
    vids: list[int] = []
    try:
        c = Candidate(username="casey", name="Casey", profile_text=profile_text)
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title="Senior PM",
            jd_text="Test JD.",
            jd_fingerprint="z" * 16,
        )
        session.add(a)
        session.flush()
        for i, text in enumerate(variants or []):
            si = SummaryItem(
                candidate_id=c.id,
                text=text,
                display_order=i,
                is_active=1,
            )
            session.add(si)
            session.flush()
            vids.append(si.id)
        session.commit()
        return c.id, a.id, vids
    finally:
        session.close()


def _ctx(
    application_id: int,
    profile_text: str,
    *,
    pinned_summary_id: int | None = None,
    recommended_summary_id: int | None = None,
) -> dict:
    """Build a minimal context_set for the function under test."""
    ctx: dict = {
        "application_id": application_id,
        "candidate": {
            "name": "Casey",
            "email": "casey@example.com",
            "profile_text": profile_text,
        },
    }
    if pinned_summary_id is not None:
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "pinned_summary_id": pinned_summary_id,
        }
    if recommended_summary_id is not None:
        ctx["llm_summary_recommendation"] = {
            "recommendation": {
                "summary_item_id": recommended_summary_id,
                "rationale": "stub",
            },
            "alternates": [],
        }
    return ctx


# -------------------------------------------------------------------
# Priority chain
# -------------------------------------------------------------------


class TestPriorityChain:
    def test_pinned_wins_over_recommendation(self, app_with_data):
        _cid, aid, vids = _seed(
            profile_text="Default text.",
            variants=["Variant A text.", "Variant B text.", "Variant C text."],
        )
        ctx = _ctx(aid, "Default text.", pinned_summary_id=vids[2], recommended_summary_id=vids[0])
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Variant C text."

    def test_recommendation_wins_when_no_pin(self, app_with_data):
        _cid, aid, vids = _seed(
            profile_text="Default text.",
            variants=["Variant A text.", "Variant B text."],
        )
        ctx = _ctx(aid, "Default text.", recommended_summary_id=vids[1])
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Variant B text."

    def test_fallback_to_existing_profile_text(self, app_with_data):
        """No pin + no recommendation + no variants → profile_text
        stays whatever it was when the context was loaded."""
        _cid, aid, _ = _seed(profile_text="Original profile.", variants=[])
        ctx = _ctx(aid, "Original profile.")
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Original profile."


# -------------------------------------------------------------------
# Defensive fallbacks
# -------------------------------------------------------------------


class TestDefensiveFallbacks:
    def test_no_application_id_is_noop(self, app_with_data):
        ctx = {"candidate": {"profile_text": "Untouched."}}
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Untouched."

    def test_missing_variant_falls_back(self, app_with_data):
        _cid, aid, _ = _seed(variants=[])
        ctx = _ctx(aid, "Fallback text.", pinned_summary_id=99999)  # doesn't exist
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Fallback text."

    def test_inactive_variant_falls_back(self, app_with_data):
        """Soft-retired variants are excluded from resolution; the user
        deleted this variant after pinning, so we degrade gracefully."""
        from db.models import SummaryItem
        from db.session import get_session

        _cid, aid, vids = _seed(
            profile_text="Fallback text.",
            variants=["Pinned but retired."],
        )
        # Soft-retire the variant
        session = get_session()
        try:
            si = session.query(SummaryItem).filter_by(id=vids[0]).first()
            si.is_active = 0
            session.commit()
        finally:
            session.close()

        ctx = _ctx(aid, "Fallback text.", pinned_summary_id=vids[0])
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Fallback text."

    def test_blank_variant_text_falls_back(self, app_with_data):
        from db.models import SummaryItem
        from db.session import get_session

        _cid, aid, vids = _seed(
            profile_text="Fallback text.",
            variants=["Variant text."],
        )
        # Overwrite to blank (simulates an editor mistake)
        session = get_session()
        try:
            si = session.query(SummaryItem).filter_by(id=vids[0]).first()
            si.text = "   "
            session.commit()
        finally:
            session.close()

        ctx = _ctx(aid, "Fallback text.", pinned_summary_id=vids[0])
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Fallback text."

    def test_other_candidates_variants_ignored(self, app_with_data):
        """Pin id pointing at a variant belonging to a DIFFERENT
        candidate must not leak across — the resolver scopes by
        the application's candidate_id."""
        from db.models import Application, Candidate, SummaryItem
        from db.session import get_session

        # Casey + a stranger
        _seed(profile_text="Casey default.", variants=["Casey variant."])
        session = get_session()
        try:
            stranger = Candidate(username="alice", name="Alice", profile_text="Alice default.")
            session.add(stranger)
            session.flush()
            stranger_si = SummaryItem(
                candidate_id=stranger.id,
                text="Alice's private variant.",
            )
            session.add(stranger_si)
            session.flush()
            alice_app = Application(
                candidate_id=stranger.id,
                title="X",
                jd_text="y",
                jd_fingerprint="y" * 16,
            )
            session.add(alice_app)
            session.commit()
            stranger_si_id = stranger_si.id
            casey_app_id = (
                session.query(Application)
                .join(Candidate, Application.candidate_id == Candidate.id)
                .filter(Candidate.username == "casey")
                .first()
                .id
            )
        finally:
            session.close()

        # Pin Alice's variant on Casey's application → should NOT apply
        ctx = _ctx(casey_app_id, "Casey default.", pinned_summary_id=stranger_si_id)
        app_with_data._apply_chosen_summary(ctx)
        assert ctx["candidate"]["profile_text"] == "Casey default."

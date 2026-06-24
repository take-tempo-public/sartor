"""Tests for the interactive review CLI.

The interactive loop is too painful to drive through input() mocks for
every action. Instead we test the discrete pieces:
- pending_experiences correctly filters by is_pending_review state
- accept_all clears flags on title + bullets
- drop_experience hard-deletes and cascades
- review_bullets transitions individual bullets

We seed in-memory DBs with known pending data per test.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from db.models import Bullet, Candidate, Experience, ExperienceTitle
from onboarding.review_cli import ReviewSession, iter_pending_experiences


def _seed_candidate_with_pending(session) -> Candidate:
    """Create a candidate with two experiences: one pending, one fully reviewed."""
    c = Candidate(username="testcandidate", name="Test")
    session.add(c)
    session.flush()

    # Experience 1: pending (title + 2 bullets all pending)
    e1 = Experience(
        candidate_id=c.id,
        company="PendingCo",
        start_date="2022-01",
        end_date=None,
        display_order=0,
    )
    session.add(e1)
    session.flush()
    session.add(
        ExperienceTitle(
            experience_id=e1.id,
            title="Senior PM",
            is_official=1,
            is_pending_review=1,
            source="user_added",
        )
    )
    session.add(
        Bullet(
            experience_id=e1.id,
            text="Led team of 5.",
            display_order=0,
            is_pending_review=1,
            source="primary:r.md",
        )
    )
    session.add(
        Bullet(
            experience_id=e1.id,
            text="Shipped V2.",
            display_order=1,
            is_pending_review=1,
            source="primary:r.md",
        )
    )

    # Experience 2: already-reviewed (everything is_pending_review=0)
    e2 = Experience(
        candidate_id=c.id,
        company="DoneCo",
        start_date="2018-01",
        end_date="2021-12",
        display_order=1,
    )
    session.add(e2)
    session.flush()
    session.add(
        ExperienceTitle(
            experience_id=e2.id,
            title="PM",
            is_official=1,
            is_pending_review=0,
            source="user_added",
        )
    )
    session.add(
        Bullet(
            experience_id=e2.id,
            text="Did the thing.",
            display_order=0,
            is_pending_review=0,
            source="primary:r.md",
        )
    )

    session.flush()
    return c


class TestPendingDetection:
    def test_pending_experiences_excludes_reviewed(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        pending = rs.pending_experiences()
        assert len(pending) == 1
        assert pending[0].company == "PendingCo"

    def test_iter_pending_experiences_same_filter(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        result = list(iter_pending_experiences(db_session, c.id))
        assert len(result) == 1
        assert result[0].company == "PendingCo"

    def test_experience_with_only_pending_title_is_pending(self, db_session):
        c = Candidate(username="x", name="X")
        db_session.add(c)
        db_session.flush()
        e = Experience(candidate_id=c.id, company="Co", start_date="2020-01")
        db_session.add(e)
        db_session.flush()
        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="T",
                is_pending_review=1,
                source="user_added",
            )
        )
        # No bullets at all
        db_session.flush()
        rs = ReviewSession(db_session, c)
        assert len(rs.pending_experiences()) == 1

    def test_experience_with_only_pending_bullet_is_pending(self, db_session):
        c = Candidate(username="y", name="Y")
        db_session.add(c)
        db_session.flush()
        e = Experience(candidate_id=c.id, company="Co", start_date="2020-01")
        db_session.add(e)
        db_session.flush()
        # Title is reviewed
        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="T",
                is_pending_review=0,
                source="official",
            )
        )
        # But a bullet is pending
        db_session.add(
            Bullet(
                experience_id=e.id,
                text="x",
                is_pending_review=1,
                source="primary:r.md",
            )
        )
        db_session.flush()
        rs = ReviewSession(db_session, c)
        assert len(rs.pending_experiences()) == 1


class TestAcceptAll:
    def test_accept_all_clears_all_pending_flags(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]

        # Suppress print() during the test
        with patch("sys.stdout", new_callable=StringIO):
            rs.accept_all(exp)

        assert all(t.is_pending_review == 0 for t in exp.titles)
        assert all(b.is_pending_review == 0 for b in exp.bullets)
        assert rs.accepted == 1
        # No more pending
        assert len(rs.pending_experiences()) == 0


class TestDropExperience:
    def test_drop_with_yes_deletes_experience_and_bullets(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]
        exp_id = exp.id

        with patch("builtins.input", return_value="y"), patch("sys.stdout", new_callable=StringIO):
            rs.drop_experience(exp)

        # Experience gone, bullets cascade-deleted via FK
        assert db_session.query(Experience).filter_by(id=exp_id).first() is None
        # Other experience untouched
        assert db_session.query(Experience).filter_by(company="DoneCo").first() is not None
        assert rs.dropped == 1

    def test_drop_with_no_keeps_experience(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]

        with patch("builtins.input", return_value="n"), patch("sys.stdout", new_callable=StringIO):
            rs.drop_experience(exp)

        assert db_session.query(Experience).filter_by(id=exp.id).first() is not None
        assert rs.dropped == 0


class TestReviewBullets:
    def test_accept_each_bullet_clears_pending(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]

        # 2 pending bullets → accept both
        with (
            patch("builtins.input", side_effect=["a", "a"]),
            patch("sys.stdout", new_callable=StringIO),
        ):
            rs.review_bullets(exp)

        assert all(b.is_pending_review == 0 for b in exp.bullets)
        assert rs.edited == 2

    def test_edit_replaces_bullet_text(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]

        # First bullet: edit + new text. Second bullet: accept.
        inputs = ["e", "Reworded version.", "a"]
        with (
            patch("builtins.input", side_effect=inputs),
            patch("sys.stdout", new_callable=StringIO),
        ):
            rs.review_bullets(exp)

        bullets = sorted(exp.bullets, key=lambda b: b.display_order)
        assert bullets[0].text == "Reworded version."
        assert bullets[0].is_pending_review == 0
        assert bullets[1].is_pending_review == 0

    def test_drop_soft_deletes_bullet(self, db_session):
        c = _seed_candidate_with_pending(db_session)
        rs = ReviewSession(db_session, c)
        exp = rs.pending_experiences()[0]

        with (
            patch("builtins.input", side_effect=["d", "a"]),
            patch("sys.stdout", new_callable=StringIO),
        ):
            rs.review_bullets(exp)

        bullets = sorted(exp.bullets, key=lambda b: b.display_order)
        assert bullets[0].is_active == 0  # soft-deleted
        assert bullets[0].is_pending_review == 0
        assert bullets[1].is_active == 1
        assert bullets[1].is_pending_review == 0

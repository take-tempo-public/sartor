"""Tests for scripts/backfill_application_titles.py (fix/review-surface-and-flows).

The manual, dry-run-by-default backfill for Application rows still titled
with the raw first-line inference (`_infer_application_title`) from before
`db.build_context.build_context_set_from_db` switched to `_infer_role_title`
(role-title ONLY — owner spec; company stays exclusively in the `company`
column, never prefixed into the title string). Covers the SAFETY RULE: only
rows whose CURRENT title still equals the raw first-line inference are
eligible — a hand-edited title (or any title that no longer matches that raw
form) must never be touched.

JD texts below deliberately put a boilerplate opener ("About Acme
Robotics") on line 1 and the role-shaped line ("Senior Backend Engineer") on
line 2 — the raw first-line extractor (old behavior) picks line 1; the new
role-title extractor skips the boilerplate opener and picks line 2. That gap
is what makes a row "eligible" for this backfill in the first place; a JD
whose first line already IS the role (the common case) has nothing to
backfill (see test_row_already_matching_new_extractor_is_a_noop).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def backfill_db(tmp_path, monkeypatch):
    db_file = tmp_path / "backfill_titles.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from db.session import init_db

    init_db(db_file)
    return db_file


def _seed_application(candidate_id, *, title, jd_text):
    from db.models import Application
    from db.session import get_session

    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id,
            title=title,
            jd_text=jd_text,
            jd_fingerprint=f"fp-{title}-{len(jd_text)}",
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


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


_JD_WITH_BOILERPLATE_OPENER = "About Acme Robotics\nSenior Backend Engineer\nDuties follow."


class TestComputeTitleBackfill:
    def test_eligible_row_gets_role_only_title(self, backfill_db):
        from db.build_context import _infer_application_title
        from db.session import get_session
        from scripts.backfill_application_titles import compute_title_backfill

        cid = _seed_candidate()
        raw = _infer_application_title(_JD_WITH_BOILERPLATE_OPENER)
        assert raw == "About Acme Robotics"  # sanity: the old raw-first-line shape
        aid = _seed_application(cid, title=raw, jd_text=_JD_WITH_BOILERPLATE_OPENER)

        session = get_session()
        try:
            changes = compute_title_backfill(session)
        finally:
            session.close()

        assert len(changes) == 1
        assert changes[0]["id"] == aid
        assert changes[0]["before"] == raw
        assert changes[0]["after"] == "Senior Backend Engineer"
        assert "Acme" not in changes[0]["after"]  # role-only — no company prefix
        assert "—" not in changes[0]["after"]

    def test_hand_edited_title_is_never_eligible(self, backfill_db):
        from db.session import get_session
        from scripts.backfill_application_titles import compute_title_backfill

        cid = _seed_candidate()
        _seed_application(
            cid, title="My Custom Application Name", jd_text=_JD_WITH_BOILERPLATE_OPENER
        )

        session = get_session()
        try:
            changes = compute_title_backfill(session)
        finally:
            session.close()

        assert changes == []

    def test_row_already_matching_new_extractor_is_a_noop(self, backfill_db):
        """When the raw first line IS already what the new extractor would
        produce (no boilerplate opener to skip, no role hint — the extractor
        falls open to the same cleaned first line), there's nothing to change."""
        from db.build_context import _infer_application_title
        from db.session import get_session
        from scripts.backfill_application_titles import compute_title_backfill

        cid = _seed_candidate()
        jd = "Come join our mission-driven team\nWe do great work.\nApply today."
        raw = _infer_application_title(jd)
        _seed_application(cid, title=raw, jd_text=jd)

        session = get_session()
        try:
            changes = compute_title_backfill(session)
        finally:
            session.close()

        assert changes == []

    def test_dry_run_never_writes(self, backfill_db):
        """Merely computing the backfill (no apply step) must not mutate the DB."""
        from db.build_context import _infer_application_title
        from db.models import Application
        from db.session import get_session
        from scripts.backfill_application_titles import compute_title_backfill

        cid = _seed_candidate()
        raw = _infer_application_title(_JD_WITH_BOILERPLATE_OPENER)
        aid = _seed_application(cid, title=raw, jd_text=_JD_WITH_BOILERPLATE_OPENER)

        session = get_session()
        try:
            compute_title_backfill(session)
        finally:
            session.close()

        session2 = get_session()
        try:
            row = session2.query(Application).filter_by(id=aid).first()
            assert row.title == raw  # untouched — compute is read-only
        finally:
            session2.close()


class TestApplyTitleBackfill:
    def test_apply_writes_computed_changes(self, backfill_db):
        from db.build_context import _infer_application_title
        from db.models import Application
        from db.session import get_session
        from scripts.backfill_application_titles import (
            apply_title_backfill,
            compute_title_backfill,
        )

        cid = _seed_candidate()
        raw = _infer_application_title(_JD_WITH_BOILERPLATE_OPENER)
        aid = _seed_application(cid, title=raw, jd_text=_JD_WITH_BOILERPLATE_OPENER)

        session = get_session()
        try:
            changes = compute_title_backfill(session)
            n = apply_title_backfill(session, changes)
            session.commit()
        finally:
            session.close()
        assert n == 1

        session2 = get_session()
        try:
            row = session2.query(Application).filter_by(id=aid).first()
            assert row.title == "Senior Backend Engineer"
        finally:
            session2.close()

    def test_apply_with_no_changes_is_a_noop(self, backfill_db):
        from db.session import get_session
        from scripts.backfill_application_titles import apply_title_backfill

        session = get_session()
        try:
            n = apply_title_backfill(session, [])
        finally:
            session.close()
        assert n == 0

    def test_second_pass_finds_nothing_left_to_change(self, backfill_db):
        """Idempotency: once applied, a row's title equals the new
        extractor's output, not the old raw form — re-running the compute
        step finds it no longer eligible (title != raw first-line anymore)."""
        from db.build_context import _infer_application_title
        from db.session import get_session
        from scripts.backfill_application_titles import (
            apply_title_backfill,
            compute_title_backfill,
        )

        cid = _seed_candidate()
        raw = _infer_application_title(_JD_WITH_BOILERPLATE_OPENER)
        _seed_application(cid, title=raw, jd_text=_JD_WITH_BOILERPLATE_OPENER)

        session = get_session()
        try:
            changes = compute_title_backfill(session)
            apply_title_backfill(session, changes)
            session.commit()
        finally:
            session.close()

        session2 = get_session()
        try:
            second_pass = compute_title_backfill(session2)
        finally:
            session2.close()
        assert second_pass == []

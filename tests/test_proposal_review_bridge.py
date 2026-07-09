"""Tests for the ProposalReview bridge (fix/review-surface-and-flows).

`ProposalReview.decision == "pending"` is what the applications-list "N to
review" badge counts (blueprints/applications.py). The ONLY UI-reachable
review path is the corpus accept/retire routes
(blueprints/corpus/curation.py `accept_bullet` / `accept_experience_title` /
`accept_experience_all` / `accept_all_pending`; blueprints/corpus/experiences.py
`delete_bullet` / `delete_experience_title`) — the `/api/proposals/*`
critique/decide lane has zero frontend callers. Before this fix those corpus
routes cleared `is_pending_review` / `is_active` directly and never touched
`ProposalReview.decision`, so the badge over-counted forever.

`blueprints/corpus/_shared.py:_resolve_proposal_reviews` is the bridge: every
accept route resolves any referencing ProposalReview row to
`decision="accept_original"`; every retire route resolves it to
`decision="reject"` — mirroring what `/api/proposals/<id>/decide` would have
recorded had the user gone through that lane instead (see
tests/test_proposal_critique_and_decide.py for that lane's own coverage).
These tests exercise the bridge through the real accept/retire routes
(single-row AND the two bulk routes), plus idempotency.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def bridge_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir, matching the
    established corpus-route fixture pattern (tests/test_pending_review_routes.py)."""
    db_file = tmp_path / "bridge.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db

    init_db(db_file)
    return app


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


def _seed_pending_with_proposal_reviews(candidate_id, *, n_pending_bullets=1, n_pending_titles=1):
    """One experience with N pending bullets + N pending titles, each backed
    by a pending `ProposalReview` row anchored to a shared application_run —
    the exact shape the corpus accept/retire routes (and the bridge) act on.
    """
    from db.models import (
        Application,
        ApplicationRun,
        Bullet,
        Experience,
        ExperienceTitle,
        ProposalReview,
    )
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id,
            company="Acme",
            start_date="2022-01",
            display_order=0,
        )
        s.add(e)
        s.flush()
        app_row = Application(
            candidate_id=candidate_id,
            title="x",
            jd_text="JD text",
            jd_fingerprint=f"fp-{e.id}",
        )
        s.add(app_row)
        s.flush()
        run = ApplicationRun(
            application_id=app_row.id,
            iteration=0,
            run_id=f"run-{e.id}",
            prompt_version="v1",
            corpus_snapshot_json="{}",
        )
        s.add(run)
        s.flush()

        bullet_ids = []
        for i in range(n_pending_bullets):
            b = Bullet(
                experience_id=e.id,
                text=f"Pending bullet {i}",
                display_order=i,
                is_active=1,
                is_pending_review=1,
                source="llm_proposed:test_run",
            )
            s.add(b)
            s.flush()
            s.add(
                ProposalReview(
                    application_run_id=run.id,
                    bullet_id=b.id,
                    original_text=b.text,
                    decision="pending",
                )
            )
            bullet_ids.append(b.id)

        title_ids = []
        for i in range(n_pending_titles):
            t = ExperienceTitle(
                experience_id=e.id,
                title=f"Title {i}",
                is_official=0,
                is_pending_review=1,
                source="llm_proposed:test_run",
            )
            s.add(t)
            s.flush()
            s.add(
                ProposalReview(
                    application_run_id=run.id,
                    experience_title_id=t.id,
                    original_text=t.title,
                    decision="pending",
                )
            )
            title_ids.append(t.id)

        s.commit()
        return {"experience_id": e.id, "bullet_ids": bullet_ids, "title_ids": title_ids}
    finally:
        s.close()


def _proposal_decision(*, bullet_id=None, title_id=None):
    from db.models import ProposalReview
    from db.session import get_session

    s = get_session()
    try:
        q = s.query(ProposalReview)
        q = (
            q.filter_by(bullet_id=bullet_id)
            if bullet_id is not None
            else q.filter_by(experience_title_id=title_id)
        )
        pr = q.first()
        return (pr.decision, pr.decided_at) if pr is not None else (None, None)
    finally:
        s.close()


class TestAcceptBridge:
    def test_accept_bullet_resolves_proposal_review(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        bid = ids["bullet_ids"][0]
        client = bridge_app.test_client()
        r = client.post(f"/api/bullets/{bid}/accept")
        assert r.status_code == 200
        decision, decided_at = _proposal_decision(bullet_id=bid)
        assert decision == "accept_original"
        assert decided_at is not None

    def test_accept_title_resolves_proposal_review(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        tid = ids["title_ids"][0]
        client = bridge_app.test_client()
        r = client.post(f"/api/experience-titles/{tid}/accept")
        assert r.status_code == 200
        decision, decided_at = _proposal_decision(title_id=tid)
        assert decision == "accept_original"
        assert decided_at is not None

    def test_accept_is_idempotent(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        bid = ids["bullet_ids"][0]
        client = bridge_app.test_client()
        r1 = client.post(f"/api/bullets/{bid}/accept")
        assert r1.status_code == 200
        decision1, decided_at1 = _proposal_decision(bullet_id=bid)
        # Re-accepting an already-accepted bullet must not error, and must
        # not disturb the already-resolved ProposalReview row (the bridge
        # only ever touches decision="pending" rows).
        r2 = client.post(f"/api/bullets/{bid}/accept")
        assert r2.status_code == 200
        decision2, decided_at2 = _proposal_decision(bullet_id=bid)
        assert (
            (decision1, decided_at1) == (decision2, decided_at2) == ("accept_original", decided_at1)
        )

    def test_accept_experience_all_resolves_every_pending_proposal_review(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid, n_pending_bullets=3, n_pending_titles=2)
        client = bridge_app.test_client()
        r = client.post(f"/api/experiences/{ids['experience_id']}/accept-all")
        assert r.status_code == 200
        body = r.get_json()
        assert body["bullets_accepted"] == 3
        assert body["titles_accepted"] == 2
        for bid in ids["bullet_ids"]:
            assert _proposal_decision(bullet_id=bid)[0] == "accept_original"
        for tid in ids["title_ids"]:
            assert _proposal_decision(title_id=tid)[0] == "accept_original"

    def test_accept_all_pending_corpus_resolves_across_experiences(self, bridge_app):
        cid = _seed_candidate()
        ids1 = _seed_pending_with_proposal_reviews(cid, n_pending_bullets=2, n_pending_titles=1)
        ids2 = _seed_pending_with_proposal_reviews(cid, n_pending_bullets=1, n_pending_titles=1)
        client = bridge_app.test_client()
        r = client.post("/api/users/alice/accept-all-pending")
        assert r.status_code == 200
        body = r.get_json()
        assert body["bullets_accepted"] == 3
        assert body["titles_accepted"] == 2
        for ids in (ids1, ids2):
            for bid in ids["bullet_ids"]:
                assert _proposal_decision(bullet_id=bid)[0] == "accept_original"
            for tid in ids["title_ids"]:
                assert _proposal_decision(title_id=tid)[0] == "accept_original"


class TestRetireBridge:
    def test_retire_bullet_resolves_proposal_review_as_rejected(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        bid = ids["bullet_ids"][0]
        client = bridge_app.test_client()
        r = client.delete(f"/api/bullets/{bid}")
        assert r.status_code == 200
        decision, decided_at = _proposal_decision(bullet_id=bid)
        assert decision == "reject"
        assert decided_at is not None

    def test_retire_title_resolves_proposal_review_as_rejected(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        tid = ids["title_ids"][0]
        client = bridge_app.test_client()
        r = client.delete(f"/api/experience-titles/{tid}")
        assert r.status_code == 200
        decision, decided_at = _proposal_decision(title_id=tid)
        assert decision == "reject"
        assert decided_at is not None

    def test_retire_is_idempotent(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid)
        bid = ids["bullet_ids"][0]
        client = bridge_app.test_client()
        r1 = client.delete(f"/api/bullets/{bid}")
        assert r1.status_code == 200
        r2 = client.delete(f"/api/bullets/{bid}")
        assert r2.status_code == 200
        decision, _ = _proposal_decision(bullet_id=bid)
        assert decision == "reject"


class TestBridgeScoping:
    def test_accepting_one_bullet_leaves_sibling_pending_review_untouched(self, bridge_app):
        cid = _seed_candidate()
        ids = _seed_pending_with_proposal_reviews(cid, n_pending_bullets=2, n_pending_titles=0)
        client = bridge_app.test_client()
        r = client.post(f"/api/bullets/{ids['bullet_ids'][0]}/accept")
        assert r.status_code == 200
        untouched_decision, _ = _proposal_decision(bullet_id=ids["bullet_ids"][1])
        assert untouched_decision == "pending"


# ---------------------------------------------------------------------------
# Migration 0014 — the one-off backfill for rows orphaned BEFORE the bridge
# (49 such rows on the owner's clone). db/migrations/versions/0014_backfill_
# orphaned_proposal_reviews.py; this exercises the real migration path (not
# just the route bridge above), matching the "49-orphan shape": a mix of
# bullet- and title-backed pending rows whose referenced row has since gone
# either accepted-and-still-live or retired, plus a genuinely-still-pending
# control row that must be left alone.
# ---------------------------------------------------------------------------


def _cfg(db_path):
    from pathlib import Path

    from alembic.config import Config

    c = Config(str(Path.cwd() / "alembic.ini"))
    c.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return c


def _seed_orphan_shape(db_path):
    """Seed one experience with the 4 orphan shapes (accepted/retired x
    bullet/title) + one genuinely-still-pending control row. Schema is fully
    built already (0014 adds no columns), so this runs against the ORM
    directly regardless of which revision `alembic_version` currently points
    at. Returns the 5 proposal_review ids by label."""
    from db.models import (
        Application,
        ApplicationRun,
        Bullet,
        Candidate,
        Experience,
        ExperienceTitle,
        ProposalReview,
    )
    from db.session import make_engine, make_session_factory

    engine = make_engine(db_path)
    s = make_session_factory(engine)()
    try:
        c = Candidate(username="alice", name="Alice")
        s.add(c)
        s.flush()
        e = Experience(candidate_id=c.id, company="Acme", start_date="2022-01")
        s.add(e)
        s.flush()
        app_row = Application(candidate_id=c.id, title="x", jd_text="jd", jd_fingerprint="fp")
        s.add(app_row)
        s.flush()
        run = ApplicationRun(
            application_id=app_row.id,
            iteration=0,
            run_id="r1",
            prompt_version="v1",
            corpus_snapshot_json="{}",
        )
        s.add(run)
        s.flush()

        def _pending_row(**kwargs):
            pr = ProposalReview(application_run_id=run.id, decision="pending", **kwargs)
            s.add(pr)
            s.flush()
            return pr.id

        # Orphan shape 1: bullet already ACCEPTED (is_active=1, is_pending_review=0)
        # but its ProposalReview row is still 'pending'.
        accepted_bullet = Bullet(
            experience_id=e.id,
            text="Accepted already",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="llm_proposed:r1",
        )
        s.add(accepted_bullet)
        s.flush()
        pr_accepted = _pending_row(bullet_id=accepted_bullet.id, original_text=accepted_bullet.text)

        # Orphan shape 2: bullet already RETIRED (is_active=0) but still 'pending'.
        retired_bullet = Bullet(
            experience_id=e.id,
            text="Retired already",
            display_order=1,
            is_active=0,
            is_pending_review=0,
            source="llm_proposed:r1",
        )
        s.add(retired_bullet)
        s.flush()
        pr_retired = _pending_row(bullet_id=retired_bullet.id, original_text=retired_bullet.text)

        # Orphan shapes 3 + 4: the same two shapes for a title.
        accepted_title = ExperienceTitle(
            experience_id=e.id,
            title="Accepted Title",
            is_official=0,
            is_active=1,
            is_pending_review=0,
            source="llm_proposed:r1",
        )
        s.add(accepted_title)
        s.flush()
        pr_accepted_title = _pending_row(
            experience_title_id=accepted_title.id, original_text=accepted_title.title
        )

        retired_title = ExperienceTitle(
            experience_id=e.id,
            title="Retired Title",
            is_official=0,
            is_active=0,
            is_pending_review=0,
            source="llm_proposed:r1",
        )
        s.add(retired_title)
        s.flush()
        pr_retired_title = _pending_row(
            experience_title_id=retired_title.id, original_text=retired_title.title
        )

        # Control: a GENUINELY still-pending bullet — the migration must
        # leave this one alone (its bullet is still is_pending_review=1).
        still_pending_bullet = Bullet(
            experience_id=e.id,
            text="Still pending",
            display_order=2,
            is_active=1,
            is_pending_review=1,
            source="llm_proposed:r1",
        )
        s.add(still_pending_bullet)
        s.flush()
        pr_still_pending = _pending_row(
            bullet_id=still_pending_bullet.id, original_text=still_pending_bullet.text
        )

        s.commit()
        return {
            "pr_accepted": pr_accepted,
            "pr_retired": pr_retired,
            "pr_accepted_title": pr_accepted_title,
            "pr_retired_title": pr_retired_title,
            "pr_still_pending": pr_still_pending,
        }
    finally:
        s.close()
        engine.dispose()


def _decisions(db_path, pr_ids):
    from db.models import ProposalReview
    from db.session import make_engine, make_session_factory

    engine = make_engine(db_path)
    s = make_session_factory(engine)()
    try:
        return {
            label: s.query(ProposalReview).filter_by(id=pr_id).first().decision
            for label, pr_id in pr_ids.items()
        }
    finally:
        s.close()
        engine.dispose()


class TestBackfillMigration0014:
    def test_orphan_shape_resolved_control_untouched(self, tmp_path):
        from alembic import command

        db = tmp_path / "backfill.sqlite"
        command.upgrade(_cfg(db), "head")
        # Rewind the version pointer to just before 0014 — its downgrade() is
        # a documented no-op (data-only migration, nothing to structurally
        # undo), so this only moves alembic_version, not the rows below.
        command.downgrade(_cfg(db), "0013")

        ids = _seed_orphan_shape(db)

        command.upgrade(_cfg(db), "head")

        decisions = _decisions(db, ids)
        assert decisions["pr_accepted"] == "accept_original"
        assert decisions["pr_retired"] == "reject"
        assert decisions["pr_accepted_title"] == "accept_original"
        assert decisions["pr_retired_title"] == "reject"
        assert decisions["pr_still_pending"] == "pending"  # untouched — not orphaned

    def test_rerun_is_idempotent(self, tmp_path):
        """A second pass over already-resolved rows must be a no-op — the
        migration's UPDATEs are all scoped to decision='pending'."""
        from alembic import command

        db = tmp_path / "backfill_rerun.sqlite"
        command.upgrade(_cfg(db), "head")
        command.downgrade(_cfg(db), "0013")
        ids = _seed_orphan_shape(db)
        command.upgrade(_cfg(db), "head")
        first_pass = _decisions(db, ids)

        # Re-run the migration for real a second time.
        command.downgrade(_cfg(db), "0013")
        command.upgrade(_cfg(db), "head")
        second_pass = _decisions(db, ids)

        assert first_pass == second_pass

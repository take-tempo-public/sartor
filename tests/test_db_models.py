"""Schema-level tests for the corpus models.

Focus areas:
- Required tables all materialize
- Stable enum CHECK constraints reject invalid values
- Partial unique indexes (is_official, is_default) hold
- FK CASCADE deletes work where the plan says they should
- application_bullet refuses to lose its bullet_id (NO cascade — soft-retire instead)
- proposal_review enforces the bullet_id XOR experience_title_id rule
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from db.models import (
    Application,
    ApplicationBullet,
    ApplicationRun,
    Bullet,
    Candidate,
    Clarification,
    Experience,
    ExperienceTitle,
    PersonaTemplate,
    ProposalReview,
    Tag,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(session, username="alice"):
    c = Candidate(username=username, name="Alice Example")
    session.add(c)
    session.flush()
    return c


def _make_experience(session, candidate):
    e = Experience(
        candidate_id=candidate.id,
        company="Acme",
        start_date="2020-01",
        end_date="2023-04",
    )
    session.add(e)
    session.flush()
    return e


# ---------------------------------------------------------------------------
# Stable enums (CHECK constraints)
# ---------------------------------------------------------------------------


class TestEnumConstraints:
    def test_tag_kind_rejects_unknown(self, db_session):
        c = _make_candidate(db_session)
        bad = Tag(candidate_id=c.id, kind="invalid_kind", value="x", display_value="x")
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_tag_kind_accepts_role_domain_skill_tech(self, db_session):
        c = _make_candidate(db_session)
        for k in ("role", "domain", "skill", "tech"):
            db_session.add(Tag(candidate_id=c.id, kind=k, value=k, display_value=k))
        db_session.flush()
        assert db_session.query(Tag).count() == 4

    def test_application_status_rejects_unknown(self, db_session):
        c = _make_candidate(db_session)
        bad = Application(
            candidate_id=c.id, title="x", jd_text="x", jd_fingerprint="abcd",
            status="not_a_real_status",
        )
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_clarification_kind_rejects_unknown(self, db_session):
        c = _make_candidate(db_session)
        bad = Clarification(
            candidate_id=c.id, question="?", answer="!", kind="bad_kind",
        )
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_persona_template_source_constraint(self, db_session):
        bad = PersonaTemplate(name="x", path="/tmp/x.docx", source="bogus")
        db_session.add(bad)
        with pytest.raises(IntegrityError):
            db_session.flush()


# ---------------------------------------------------------------------------
# Partial unique indexes
# ---------------------------------------------------------------------------


class TestPartialUniqueIndexes:
    def test_at_most_one_official_title_per_experience(self, db_session):
        c = _make_candidate(db_session)
        e = _make_experience(db_session, c)
        db_session.add(ExperienceTitle(
            experience_id=e.id, title="A", is_official=1, source="official",
        ))
        db_session.flush()
        # Adding a second official title should fail.
        db_session.add(ExperienceTitle(
            experience_id=e.id, title="B", is_official=1, source="official",
        ))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_non_official_titles_can_coexist(self, db_session):
        c = _make_candidate(db_session)
        e = _make_experience(db_session, c)
        for i in range(3):
            db_session.add(ExperienceTitle(
                experience_id=e.id, title=f"alt-{i}",
                is_official=0, truthful_enough_to_use=1, source="user_added",
            ))
        db_session.flush()
        assert db_session.query(ExperienceTitle).count() == 3


# ---------------------------------------------------------------------------
# FK CASCADE behaviour
# ---------------------------------------------------------------------------


class TestCascadeDeletes:
    def test_deleting_candidate_cascades_experiences_and_bullets(self, db_session):
        c = _make_candidate(db_session)
        e = _make_experience(db_session, c)
        db_session.add(Bullet(
            experience_id=e.id, text="Did the thing.", source="primary",
        ))
        db_session.flush()
        assert db_session.query(Experience).count() == 1
        assert db_session.query(Bullet).count() == 1

        db_session.delete(c)
        db_session.flush()
        assert db_session.query(Experience).count() == 0
        assert db_session.query(Bullet).count() == 0

    def test_deleting_bullet_referenced_by_application_bullet_fails(self, db_session):
        """application_bullet has NO cascade on bullet_id — see plan §application_bullet."""
        c = _make_candidate(db_session)
        e = _make_experience(db_session, c)
        b = Bullet(experience_id=e.id, text="Did the thing.", source="primary")
        db_session.add(b)
        db_session.flush()

        app = Application(
            candidate_id=c.id, title="x", jd_text="...", jd_fingerprint="abcd",
        )
        db_session.add(app)
        db_session.flush()
        run = ApplicationRun(
            application_id=app.id, iteration=0, run_id="abc123",
            prompt_version="test", corpus_snapshot_json="{}",
        )
        db_session.add(run)
        db_session.flush()
        db_session.add(ApplicationBullet(
            application_run_id=run.id, bullet_id=b.id, position=0,
        ))
        db_session.flush()

        # Hard-deleting the bullet must fail because application_bullet references it.
        db_session.delete(b)
        with pytest.raises(IntegrityError):
            db_session.flush()


# ---------------------------------------------------------------------------
# proposal_review polymorphic XOR
# ---------------------------------------------------------------------------


class TestProposalReviewXor:
    def _setup_run(self, db_session):
        c = _make_candidate(db_session)
        app = Application(
            candidate_id=c.id, title="x", jd_text="...", jd_fingerprint="abcd",
        )
        db_session.add(app)
        db_session.flush()
        run = ApplicationRun(
            application_id=app.id, iteration=0, run_id="run-1",
            prompt_version="test", corpus_snapshot_json="{}",
        )
        db_session.add(run)
        db_session.flush()
        return c, run

    def test_neither_bullet_nor_title_set_fails(self, db_session):
        _, run = self._setup_run(db_session)
        db_session.add(ProposalReview(
            application_run_id=run.id, original_text="x",
        ))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_both_bullet_and_title_set_fails(self, db_session):
        c, run = self._setup_run(db_session)
        e = _make_experience(db_session, c)
        b = Bullet(experience_id=e.id, text="Did the thing.", source="primary")
        t = ExperienceTitle(experience_id=e.id, title="T", source="official")
        db_session.add_all([b, t])
        db_session.flush()
        db_session.add(ProposalReview(
            application_run_id=run.id, original_text="x",
            bullet_id=b.id, experience_title_id=t.id,
        ))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_only_bullet_set_succeeds(self, db_session):
        c, run = self._setup_run(db_session)
        e = _make_experience(db_session, c)
        b = Bullet(experience_id=e.id, text="Did the thing.", source="primary")
        db_session.add(b)
        db_session.flush()
        db_session.add(ProposalReview(
            application_run_id=run.id, original_text="x", bullet_id=b.id,
        ))
        db_session.flush()  # no error
        assert db_session.query(ProposalReview).count() == 1

    def test_only_title_set_succeeds(self, db_session):
        c, run = self._setup_run(db_session)
        e = _make_experience(db_session, c)
        t = ExperienceTitle(experience_id=e.id, title="T", source="official")
        db_session.add(t)
        db_session.flush()
        db_session.add(ProposalReview(
            application_run_id=run.id, original_text="x", experience_title_id=t.id,
        ))
        db_session.flush()
        assert db_session.query(ProposalReview).count() == 1


# ---------------------------------------------------------------------------
# Tag uniqueness and self-reference for merge alias
# ---------------------------------------------------------------------------


class TestTagBehaviours:
    def test_tag_unique_per_candidate_kind_value(self, db_session):
        c = _make_candidate(db_session)
        db_session.add(Tag(candidate_id=c.id, kind="role", value="ai", display_value="AI"))
        db_session.flush()
        db_session.add(Tag(candidate_id=c.id, kind="role", value="ai", display_value="AI"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_tag_same_value_different_kinds_allowed(self, db_session):
        c = _make_candidate(db_session)
        db_session.add(Tag(candidate_id=c.id, kind="role", value="ai", display_value="AI"))
        db_session.add(Tag(candidate_id=c.id, kind="domain", value="ai", display_value="AI"))
        db_session.flush()
        assert db_session.query(Tag).count() == 2

    def test_tag_merge_alias_self_reference(self, db_session):
        c = _make_candidate(db_session)
        canonical = Tag(candidate_id=c.id, kind="role", value="ai", display_value="AI")
        alias = Tag(candidate_id=c.id, kind="role", value="ai-ml", display_value="AI/ML")
        db_session.add_all([canonical, alias])
        db_session.flush()
        alias.merged_into_id = canonical.id
        db_session.flush()
        assert alias.merged_into is canonical

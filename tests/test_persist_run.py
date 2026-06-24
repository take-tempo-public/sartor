"""Tests for db.persist_run.persist_corpus_generation.

Verifies that the LLM's structured output gets written to the audit chain:
- selected_bullets → application_bullet rows
- chosen_title_id → application_run_title row
- proposed_new_bullets → new bullet (pending) + proposal_review (pending)
- proposed_experience_titles → new title (pending) + proposal_review (pending)
- malformed inputs are skipped, not aborted
- hallucinated IDs (bullets/titles/experiences not in candidate's corpus) are
  logged and skipped, not silently accepted
"""

from __future__ import annotations

from db.models import (
    Application,
    ApplicationBullet,
    ApplicationRun,
    ApplicationRunTitle,
    Bullet,
    Candidate,
    Experience,
    ExperienceTitle,
    IterationLog,
    ProposalReview,
)
from db.persist_run import (
    _strip_id_prefix,
    persist_corpus_generation,
    persist_cover_letter_md,
)


def _seed_minimal_candidate_with_run(
    session,
) -> tuple[Candidate, Experience, Bullet, ExperienceTitle, ApplicationRun]:
    """Seed a candidate with one experience, one bullet, one title, plus an
    application + application_run anchor. Returns the rows for assertions."""
    c = Candidate(username="alice", name="Alice")
    session.add(c)
    session.flush()

    e = Experience(
        candidate_id=c.id,
        company="Acme",
        start_date="2020-01",
        end_date="2023-04",
    )
    session.add(e)
    session.flush()

    t = ExperienceTitle(
        experience_id=e.id,
        title="Senior PM",
        is_official=1,
        is_pending_review=0,
        source="official",
    )
    session.add(t)

    b = Bullet(
        experience_id=e.id,
        text="Led 5-person team.",
        display_order=0,
        is_active=1,
        is_pending_review=0,
        source="primary:r.md",
    )
    session.add(b)
    session.flush()

    app_row = Application(
        candidate_id=c.id,
        title="x",
        jd_text="...",
        jd_fingerprint="abcd",
    )
    session.add(app_row)
    session.flush()

    run = ApplicationRun(
        application_id=app_row.id,
        iteration=0,
        run_id="run123",
        prompt_version="test",
        corpus_snapshot_json="{}",
    )
    session.add(run)
    session.flush()
    return c, e, b, t, run


# ---------------------------------------------------------------------------
# ID prefix parsing
# ---------------------------------------------------------------------------


class TestStripIdPrefix:
    def test_strips_prefixed_string(self):
        assert _strip_id_prefix("e3", "e") == 3
        assert _strip_id_prefix("b100", "b") == 100
        assert _strip_id_prefix("t12", "t") == 12

    def test_accepts_bare_integer(self):
        assert _strip_id_prefix(42, "e") == 42

    def test_accepts_bare_digit_string(self):
        assert _strip_id_prefix("42", "e") == 42

    def test_rejects_wrong_prefix(self):
        assert _strip_id_prefix("b3", "e") is None  # wrong prefix
        # falls through to the "is it a digit string?" check; "b3" isn't digits
        assert _strip_id_prefix("xyz", "e") is None

    def test_rejects_empty_and_none(self):
        assert _strip_id_prefix(None, "e") is None
        assert _strip_id_prefix("", "e") is None
        assert _strip_id_prefix("  ", "e") is None

    def test_rejects_non_positive(self):
        assert _strip_id_prefix(0, "e") is None
        assert _strip_id_prefix(-1, "e") is None


# ---------------------------------------------------------------------------
# selected_bullets → application_bullet + application_run_title
# ---------------------------------------------------------------------------


class TestSelectedBullets:
    def test_creates_application_bullet_rows(self, db_session):
        c, e, b, t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "resume_content": "x",
            "cover_letter_content": "y",
            "selected_bullets": [
                {
                    "experience_id": f"e{e.id}",
                    "chosen_title_id": f"t{t.id}",
                    "bullet_ids_in_order": [f"b{b.id}"],
                }
            ],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        assert report.application_bullets_created == 1
        assert report.application_run_titles_created == 1

        rows = db_session.query(ApplicationBullet).filter_by(application_run_id=run.id).all()
        assert len(rows) == 1
        assert rows[0].bullet_id == b.id
        assert rows[0].position == 0

        title_rows = (
            db_session.query(ApplicationRunTitle).filter_by(application_run_id=run.id).all()
        )
        assert len(title_rows) == 1
        assert title_rows[0].experience_id == e.id
        assert title_rows[0].experience_title_id == t.id

    def test_preserves_bullet_order(self, db_session):
        c, e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        # Add 2 more bullets
        b2 = Bullet(
            experience_id=e.id, text="Bullet B", display_order=1, is_active=1, source="primary:r.md"
        )
        b3 = Bullet(
            experience_id=e.id, text="Bullet C", display_order=2, is_active=1, source="primary:r.md"
        )
        db_session.add_all([b2, b3])
        db_session.flush()

        result = {
            "selected_bullets": [
                {"experience_id": f"e{e.id}", "bullet_ids_in_order": [f"b{b3.id}", f"b{b2.id}"]}
            ],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        persist_corpus_generation(db_session, run, result, c.id)

        rows = sorted(
            db_session.query(ApplicationBullet).filter_by(application_run_id=run.id),
            key=lambda r: r.position,
        )
        # Order in the LLM's array becomes position 0, 1, ...
        assert rows[0].bullet_id == b3.id
        assert rows[0].position == 0
        assert rows[1].bullet_id == b2.id
        assert rows[1].position == 1

    def test_hallucinated_bullet_id_is_skipped(self, db_session):
        c, e, b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [
                {"experience_id": f"e{e.id}", "bullet_ids_in_order": [f"b{b.id}", "b99999"]}
            ],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        assert report.application_bullets_created == 1
        assert 99999 in report.bullets_referenced_but_missing

    def test_cross_candidate_bullet_id_is_skipped(self, db_session):
        """If the LLM names a bullet_id that belongs to a DIFFERENT candidate's
        experience, the bullet must NOT be linked."""
        c1, e1, b1, _t, run = _seed_minimal_candidate_with_run(db_session)
        # Second candidate with their own bullet
        c2 = Candidate(username="bob", name="Bob")
        db_session.add(c2)
        db_session.flush()
        e2 = Experience(candidate_id=c2.id, company="Other", start_date="2019-01")
        db_session.add(e2)
        db_session.flush()
        b_other = Bullet(
            experience_id=e2.id,
            text="Other person's bullet.",
            display_order=0,
            is_active=1,
            source="primary:r.md",
        )
        db_session.add(b_other)
        db_session.flush()

        result = {
            "selected_bullets": [
                {
                    "experience_id": f"e{e1.id}",
                    "bullet_ids_in_order": [f"b{b_other.id}"],
                }  # cross-candidate ID!
            ],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c1.id)
        # The cross-candidate bullet must not have been linked to c1's run.
        assert report.application_bullets_created == 0
        assert b_other.id in report.bullets_referenced_but_missing


# ---------------------------------------------------------------------------
# proposed_new_bullets → bullet + proposal_review
# ---------------------------------------------------------------------------


class TestProposedBullets:
    def test_creates_bullet_with_pending_review_and_proposal_row(self, db_session):
        c, e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [
                {
                    "experience_id": f"e{e.id}",
                    "text": "Proposed new bullet text.",
                    "pattern_kind": "xyz",
                    "rationale": "Fills a JD gap.",
                }
            ],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        assert report.proposed_bullets_created == 1
        assert report.proposal_reviews_created == 1

        # New bullet row exists, pending review, llm_proposed source
        new_bullets = (
            db_session.query(Bullet)
            .filter(Bullet.experience_id == e.id, Bullet.is_pending_review == 1)
            .all()
        )
        assert len(new_bullets) == 1
        assert new_bullets[0].text == "Proposed new bullet text."
        assert new_bullets[0].source == f"llm_proposed:{run.run_id}"
        assert new_bullets[0].pattern_kind == "xyz"

        # ProposalReview row references the new bullet, is pending
        reviews = db_session.query(ProposalReview).filter_by(application_run_id=run.id).all()
        assert len(reviews) == 1
        assert reviews[0].bullet_id == new_bullets[0].id
        assert reviews[0].decision == "pending"
        assert reviews[0].original_text == "Proposed new bullet text."

    def test_normalizes_pattern_kind(self, db_session):
        c, e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [
                {"experience_id": f"e{e.id}", "text": "x", "pattern_kind": "X-Y-Z"},
                {"experience_id": f"e{e.id}", "text": "y", "pattern_kind": "weird"},
            ],
            "proposed_experience_titles": [],
        }
        persist_corpus_generation(db_session, run, result, c.id)
        bullets = (
            db_session.query(Bullet)
            .filter(Bullet.experience_id == e.id, Bullet.is_pending_review == 1)
            .order_by(Bullet.id)
            .all()
        )
        # "X-Y-Z" normalizes to "xyz"
        assert bullets[0].pattern_kind == "xyz"
        # Unknown values become NULL (pattern_kind CHECK accepts NULL)
        assert bullets[1].pattern_kind is None


# ---------------------------------------------------------------------------
# proposed_experience_titles → experience_title + proposal_review
# ---------------------------------------------------------------------------


class TestProposedTitles:
    def test_creates_pending_title_and_proposal_row(self, db_session):
        c, e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [
                {
                    "experience_id": f"e{e.id}",
                    "title": "AI Product Lead",
                    "rationale": "JD asks for AI framing.",
                }
            ],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        assert report.proposed_titles_created == 1

        new_titles = (
            db_session.query(ExperienceTitle)
            .filter(
                ExperienceTitle.experience_id == e.id,
                ExperienceTitle.is_pending_review == 1,
            )
            .all()
        )
        assert len(new_titles) == 1
        assert new_titles[0].title == "AI Product Lead"
        assert new_titles[0].is_official == 0
        assert new_titles[0].truthful_enough_to_use == 0  # pending review

        reviews = db_session.query(ProposalReview).filter_by(application_run_id=run.id).all()
        assert len(reviews) == 1
        assert reviews[0].experience_title_id == new_titles[0].id
        assert reviews[0].decision == "pending"

    def test_skips_when_same_title_text_already_exists(self, db_session):
        c, e, _b, t, run = _seed_minimal_candidate_with_run(db_session)
        # t.title is "Senior PM" already
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [{"experience_id": f"e{e.id}", "title": t.title}],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        # Duplicate title text → no new row
        assert report.proposed_titles_created == 0


# ---------------------------------------------------------------------------
# iteration_log + audit
# ---------------------------------------------------------------------------


class TestIterationLogEntry:
    def test_one_iteration_log_row_per_persist_call(self, db_session):
        c, _e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        persist_corpus_generation(db_session, run, result, c.id)
        logs = db_session.query(IterationLog).filter_by(application_run_id=run.id).all()
        assert len(logs) == 1
        assert logs[0].action == "generate"


# ---------------------------------------------------------------------------
# Malformed input handling
# ---------------------------------------------------------------------------


class TestMalformedInput:
    def test_skips_non_dict_entries(self, db_session):
        c, e, b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [
                "this is a string not a dict",
                {"experience_id": f"e{e.id}", "bullet_ids_in_order": [f"b{b.id}"]},
            ],
            "proposed_new_bullets": [None, {"experience_id": "x"}],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        # Good entry processed; bad entries logged
        assert report.application_bullets_created == 1
        assert report.skipped_due_to_malformed_payload >= 2

    def test_empty_response_writes_nothing_but_logs_iteration(self, db_session):
        c, _e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        report = persist_corpus_generation(db_session, run, result, c.id)
        assert report.application_bullets_created == 0
        # Still get one iteration_log row
        assert db_session.query(IterationLog).filter_by(application_run_id=run.id).count() == 1

    def test_stores_generated_md_on_run_row(self, db_session):
        c, _e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        result = {
            "resume_content": "# Resume",
            "cover_letter_content": "Dear...",
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        persist_corpus_generation(db_session, run, result, c.id)
        db_session.refresh(run)
        assert run.generated_resume_md == "# Resume"
        assert run.generated_cover_letter_md == "Dear..."

    def test_persist_cover_letter_md_does_not_clobber_resume(self, db_session):
        # Surgical single-column write-back used by the detached cover-letter
        # route: it runs AFTER the résumé is persisted, so it must set only
        # generated_cover_letter_md and leave generated_resume_md intact.
        c, _e, _b, _t, run = _seed_minimal_candidate_with_run(db_session)
        run.generated_resume_md = "# Resume"  # résumé already persisted
        db_session.flush()
        persist_cover_letter_md(db_session, run, "Dear Hiring Manager,")
        db_session.refresh(run)
        assert run.generated_cover_letter_md == "Dear Hiring Manager,"
        assert run.generated_resume_md == "# Resume"  # NOT clobbered

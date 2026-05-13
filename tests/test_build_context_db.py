"""Tests for db.build_context.build_context_set_from_db.

Verifies that the DB-backed context builder produces a ContextSet whose
SHAPE matches the file-based output, and that it correctly creates the
application + application_run anchor rows.
"""

from __future__ import annotations

import json

import pytest

from db.build_context import (
    _infer_application_title,
    _pick_official_title,
    _select_corpus_snapshot,
    _summarize_educations,
    _synthesize_resume_markdown,
    build_context_set_from_db,
)
from db.models import (
    Bullet,
    Candidate,
    Certification,
    Education,
    Experience,
    ExperienceTitle,
    Skill,
)


def _seed_full_candidate(session) -> Candidate:
    """Build a candidate with experiences, bullets, skills, certs, education."""
    c = Candidate(
        username="casey",
        name="Casey Tester",
        email="casey@example.com",
        phone="555-0142",
        linkedin_url="https://linkedin.com/in/casey",
        notes="Open to remote.",
    )
    session.add(c)
    session.flush()

    e1 = Experience(
        candidate_id=c.id, company="Polaris",
        start_date="2022-09", end_date=None, location="Remote",
    )
    session.add(e1)
    session.flush()
    session.add(ExperienceTitle(
        experience_id=e1.id, title="Senior PM, ML Platform",
        is_official=1, is_pending_review=0, source="official",
    ))
    session.add(ExperienceTitle(
        experience_id=e1.id, title="AI Product Lead",
        is_official=0, truthful_enough_to_use=1, is_pending_review=0, source="user_added",
    ))
    session.add(Bullet(
        experience_id=e1.id, text="Led 5-person eval framework team.",
        display_order=0, is_active=1, is_pending_review=0,
        source="primary:r.md", has_outcome=1,
    ))
    session.add(Bullet(
        experience_id=e1.id, text="Defined product roadmap.",
        display_order=1, is_active=1, is_pending_review=0,
        source="primary:r.md", has_outcome=0,
    ))

    e2 = Experience(
        candidate_id=c.id, company="Acme",
        start_date="2018-05", end_date="2022-08",
    )
    session.add(e2)
    session.flush()
    session.add(ExperienceTitle(
        experience_id=e2.id, title="Design Manager",
        is_official=1, is_pending_review=0, source="official",
    ))
    session.add(Bullet(
        experience_id=e2.id, text="Built design org.",
        display_order=0, is_active=1, is_pending_review=0,
        source="primary:r.md",
    ))
    # Retired bullet should NOT appear in synthesized resume
    session.add(Bullet(
        experience_id=e2.id, text="Retired bullet.",
        display_order=1, is_active=0, is_pending_review=0,
        source="primary:r.md",
    ))

    session.add(Skill(candidate_id=c.id, name="Python"))
    session.add(Skill(candidate_id=c.id, name="TypeScript"))
    session.add(Certification(candidate_id=c.id, name="NN/g UX Master"))
    session.add(Education(
        candidate_id=c.id, institution="ExampleU", degree="BS Cog Sci",
        start_date="2010", end_date="2014",
    ))
    session.flush()
    return c


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestPickOfficialTitle:
    def test_returns_official_when_present(self):
        titles = [
            type("T", (), {"is_official": 0, "truthful_enough_to_use": 0, "title": "alt"})(),
            type("T", (), {"is_official": 1, "truthful_enough_to_use": 1, "title": "off"})(),
        ]
        assert _pick_official_title(titles) == "off"

    def test_falls_back_to_truthful_enough(self):
        titles = [
            type("T", (), {"is_official": 0, "truthful_enough_to_use": 1, "title": "alt"})(),
        ]
        assert _pick_official_title(titles) == "alt"

    def test_returns_empty_when_no_eligible(self):
        titles = [
            type("T", (), {"is_official": 0, "truthful_enough_to_use": 0, "title": "untrusted"})(),
        ]
        assert _pick_official_title(titles) == ""


class TestInferApplicationTitle:
    def test_picks_first_non_empty_line(self):
        jd = "\n\n  Senior PM at Foo Corp  \n\nResponsibilities..."
        assert _infer_application_title(jd) == "Senior PM at Foo Corp"

    def test_truncates_at_80_chars(self):
        jd = "x" * 200
        assert len(_infer_application_title(jd)) == 80

    def test_empty_jd_returns_placeholder(self):
        assert _infer_application_title("") == "Untitled application"
        assert _infer_application_title("   \n  \n") == "Untitled application"


class TestSummarizeEducations:
    def test_joins_with_semicolons(self):
        eds = [
            type("E", (), {"institution": "MIT"})(),
            type("E", (), {"institution": "Stanford"})(),
        ]
        assert _summarize_educations(eds) == "MIT; Stanford"

    def test_empty_returns_empty(self):
        assert _summarize_educations([]) == ""


class TestSelectCorpusSnapshot:
    def test_includes_active_bullets_and_eligible_titles(self, db_session):
        c = _seed_full_candidate(db_session)
        experiences = sorted(c.experiences, key=lambda e: e.start_date, reverse=True)
        snapshot_json = _select_corpus_snapshot(experiences)
        snapshot = json.loads(snapshot_json)
        # 2 active bullets in Polaris + 1 active bullet in Acme = 3
        assert len(snapshot["bullet_ids"]) == 3
        # Polaris has 2 eligible titles (official + truthful_enough); Acme has 1
        assert len(snapshot["experience_title_ids"]) == 3


# ---------------------------------------------------------------------------
# Resume markdown synthesis
# ---------------------------------------------------------------------------


class TestSynthesizeResumeMarkdown:
    def test_includes_name_and_contact(self, db_session):
        c = _seed_full_candidate(db_session)
        text = _synthesize_resume_markdown(
            experiences=list(c.experiences),
            skills=["Python"], certifications=[],
            educations=[], candidate=c,
        )
        assert "# Casey Tester" in text
        assert "casey@example.com" in text

    def test_includes_official_titles_not_alternates(self, db_session):
        c = _seed_full_candidate(db_session)
        text = _synthesize_resume_markdown(
            experiences=sorted(c.experiences, key=lambda e: e.start_date, reverse=True),
            skills=[], certifications=[],
            educations=[], candidate=c,
        )
        # Official titles shown in the synthesized headers
        assert "Senior PM, ML Platform" in text
        assert "Design Manager" in text
        # Alternate title NOT in the synthesized resume (it's in the snapshot for the LLM
        # to consider, but the synthesized markdown shows the official framing)
        assert "AI Product Lead" not in text

    def test_omits_retired_bullets(self, db_session):
        c = _seed_full_candidate(db_session)
        text = _synthesize_resume_markdown(
            experiences=list(c.experiences),
            skills=[], certifications=[],
            educations=[], candidate=c,
        )
        assert "Retired bullet." not in text
        # Active ones are present
        assert "Led 5-person eval framework team." in text
        assert "Built design org." in text

    def test_sections_emitted_when_present(self, db_session):
        c = _seed_full_candidate(db_session)
        text = _synthesize_resume_markdown(
            experiences=list(c.experiences),
            skills=["Python", "TypeScript"],
            certifications=["NN/g UX Master"],
            educations=[
                type("E", (), {
                    "institution": "MIT", "degree": "BS CS",
                    "start_date": "2010", "end_date": "2014",
                })(),
            ],
            candidate=c,
        )
        assert "## Skills" in text
        assert "Python" in text and "TypeScript" in text
        assert "## Education" in text
        assert "MIT" in text
        assert "## Certifications" in text
        assert "NN/g UX Master" in text


# ---------------------------------------------------------------------------
# End-to-end build_context_set_from_db
# ---------------------------------------------------------------------------


class TestBuildContextSetFromDb:
    def test_returns_valid_contextset_shape(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, app, run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Senior PM role at Foo\nResponsibilities here.",
            run_id="abc123def456",
        )
        # ContextSet shape — same keys as file-based build_context_set
        for required in ("timestamp", "candidate", "resume", "supplemental_resumes",
                         "job_description", "deterministic_analysis"):
            assert required in ctx, f"Missing ContextSet key: {required}"

        assert ctx["candidate"]["name"] == "Casey Tester"
        assert "Python" in ctx["candidate"]["skills"]
        assert ctx["job_description"].startswith("Senior PM role")
        assert ctx["supplemental_resumes"] == []
        assert ctx["resume"]["format"] == "md"
        assert "Casey Tester" in ctx["resume"]["text"]

    def test_creates_application_and_run_rows(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, app, run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Senior PM at Foo Corp",
            run_id="run123",
        )
        db_session.commit()

        assert app.id is not None
        assert app.title == "Senior PM at Foo Corp"
        assert app.status == "draft"
        assert app.jd_fingerprint  # populated

        assert run.id is not None
        assert run.application_id == app.id
        assert run.iteration == 0
        assert run.run_id == "run123"
        assert run.corpus_snapshot_json  # populated

        snapshot = json.loads(run.corpus_snapshot_json)
        assert "bullet_ids" in snapshot
        assert "experience_title_ids" in snapshot

    def test_unknown_username_raises(self, db_session):
        with pytest.raises(ValueError, match="No candidate"):
            build_context_set_from_db(
                db_session,
                candidate_username="ghost",
                jd_text="Some JD",
                run_id="x",
            )

    def test_keyword_extraction_runs_against_synthesized_text(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Looking for product manager with Python experience",
            run_id="run_kw",
        )
        # Synthesized resume has "Python" (from skills) → should match a keyword
        overlap = ctx["deterministic_analysis"]["keyword_overlap"]
        assert isinstance(overlap.get("match_score"), float)
        # match_score should be > 0 since Python appears in both
        assert overlap["match_score"] > 0

    def test_run_id_propagates_to_run_row(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        _ctx, _app, run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="custom_run_id_123",
        )
        assert run.run_id == "custom_run_id_123"

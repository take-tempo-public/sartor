"""Tests for db.build_context.build_context_set_from_db.

Verifies that the DB-backed context builder produces a ContextSet whose
SHAPE matches the file-based output, and that it correctly creates the
application + application_run anchor rows.
"""

from __future__ import annotations

import json

import pytest

from db.build_context import (
    _infer_application_company,
    _infer_application_title,
    _infer_role_title,
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
        candidate_id=c.id,
        company="Polaris",
        start_date="2022-09",
        end_date=None,
        location="Remote",
    )
    session.add(e1)
    session.flush()
    session.add(
        ExperienceTitle(
            experience_id=e1.id,
            title="Senior PM, ML Platform",
            is_official=1,
            is_pending_review=0,
            source="official",
        )
    )
    session.add(
        ExperienceTitle(
            experience_id=e1.id,
            title="AI Product Lead",
            is_official=0,
            truthful_enough_to_use=1,
            is_pending_review=0,
            source="user_added",
        )
    )
    session.add(
        Bullet(
            experience_id=e1.id,
            text="Led 5-person eval framework team.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
            has_outcome=1,
        )
    )
    session.add(
        Bullet(
            experience_id=e1.id,
            text="Defined product roadmap.",
            display_order=1,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
            has_outcome=0,
        )
    )

    e2 = Experience(
        candidate_id=c.id,
        company="Acme",
        start_date="2018-05",
        end_date="2022-08",
    )
    session.add(e2)
    session.flush()
    session.add(
        ExperienceTitle(
            experience_id=e2.id,
            title="Design Manager",
            is_official=1,
            is_pending_review=0,
            source="official",
        )
    )
    session.add(
        Bullet(
            experience_id=e2.id,
            text="Built design org.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
        )
    )
    # Retired bullet should NOT appear in synthesized resume
    session.add(
        Bullet(
            experience_id=e2.id,
            text="Retired bullet.",
            display_order=1,
            is_active=0,
            is_pending_review=0,
            source="primary:r.md",
        )
    )

    session.add(Skill(candidate_id=c.id, name="Python"))
    session.add(Skill(candidate_id=c.id, name="TypeScript"))
    session.add(Certification(candidate_id=c.id, name="NN/g UX Master"))
    session.add(
        Education(
            candidate_id=c.id,
            institution="ExampleU",
            degree="BS Cog Sci",
            start_date="2010",
            end_date="2014",
        )
    )
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


class TestInferApplicationCompany:
    """F-15: deterministic employer capture at application-creation time."""

    def test_picks_the_detected_company(self):
        assert _infer_application_company("About Initech\nWe make software.") == "Initech"

    def test_title_cases_multi_word_company(self):
        jd = "Senior Site Reliability Engineer\nLattice Cloud — Remote (US)\n\nDuties follow."
        assert _infer_application_company(jd) == "Lattice Cloud"

    def test_none_when_undetectable(self):
        assert _infer_application_company("Responsibilities include leading a team.") is None

    def test_empty_jd_returns_none(self):
        assert _infer_application_company("") is None

    def test_picks_longest_term_deterministically_on_multiple_signals(self):
        # "At" pattern yields "Acme"; the dash-header pattern yields the more
        # specific "Acme Robotics" — the longer term must win regardless of
        # frozenset iteration order.
        jd = "Come build robots at Acme.\nAcme Robotics — Remote\n\nDuties follow."
        assert _infer_application_company(jd) == "Acme Robotics"


class TestInferRoleTitle:
    """fix/review-surface-and-flows: the NEW deterministic role-title extractor."""

    def test_picks_first_role_shaped_line(self):
        jd = "Senior Backend Engineer\n\nWe build things."
        assert _infer_role_title(jd) == "Senior Backend Engineer"

    def test_strips_markdown_heading_markers(self):
        jd = "## Senior Software Engineer\nMore text here."
        assert _infer_role_title(jd) == "Senior Software Engineer"

    def test_strips_mojibake_artifacts(self):
        jd = "Senior Softwar�e Engineer\nMore text."
        assert _infer_role_title(jd) == "Senior Software Engineer"

    def test_skips_boilerplate_opener_for_role_shaped_line(self):
        jd = "About the Role\nSenior Backend Engineer\nWe build things at scale."
        assert _infer_role_title(jd) == "Senior Backend Engineer"

    def test_skips_who_we_are_opener(self):
        jd = "Who We Are\nStaff Data Scientist\nJoin our team."
        assert _infer_role_title(jd) == "Staff Data Scientist"

    def test_fails_open_to_cleaned_first_line_when_no_role_hint(self):
        jd = "Come join our mission-driven team\nWe do great work.\nApply today."
        assert _infer_role_title(jd) == "Come join our mission-driven team"

    def test_empty_jd_returns_empty_string(self):
        assert _infer_role_title("") == ""
        assert _infer_role_title("   \n  \n") == ""

    def test_truncates_at_80_chars(self):
        jd = "Senior Engineer " + "x" * 200
        assert len(_infer_role_title(jd)) == 80

    def test_extracts_role_from_about_the_role_at_company_boilerplate(self):
        """Real backfill evidence: 'About the X at Y:' used to be skipped
        wholesale as boilerplate, discarding the role segment sitting right
        in it (walkthrough residuals item 9a)."""
        jd = "About the Director, AI Enablement at Headspace:\nWe build things."
        assert _infer_role_title(jd) == "Director, AI Enablement"

    def test_about_role_at_company_extraction_requires_a_role_hint(self):
        """The extracted segment must itself look like a title — 'About the
        Company at a Glance:' must not yield 'Company' as a fake role. No
        role-shaped line exists anywhere, so this fails open to the cleaned
        first line (same fail-open contract as the no-role-hint case)."""
        jd = "About the Company at a Glance:\nWe build things at scale."
        assert _infer_role_title(jd) == "About the Company at a Glance:"

    def test_extracts_role_from_glued_as_the_role_you_will_pattern(self):
        """Real backfill evidence (mojibake/copy-paste glue): a JD whose lines
        never resolve to a clean title via the plain keyword scan — the raw
        'As theDirector...' prose fragment must never be picked as the title
        (walkthrough residuals item 9b). The glued article ('theDirector',
        no space) is repaired by the regex boundary, not string surgery."""
        jd = (
            "SanDisk’sProduct Innovation Teamoperates at the front end…\n"
            "As theDirector of Product Management for Product Innovation, "
            "you will lead…"
        )
        assert _infer_role_title(jd) == "Director of Product Management for Product Innovation"

    def test_never_picks_a_glued_prose_line_with_no_extractable_pattern(self):
        """When no 'About X at Y' / 'As the X, you will' pattern applies and no
        line is genuinely role-shaped, fail open to the CLEANED first line —
        never a raw prose sentence just because it contains a hint keyword."""
        jd = "We are looking for a talented Software Engineer to join our growing team.\nMore context."
        assert (
            _infer_role_title(jd)
            == "We are looking for a talented Software Engineer to join our growing team."
        )

    def test_short_sentence_with_role_keyword_is_not_mistaken_for_a_title(self):
        """A short line can still be a sentence, not a title — 'you will lead'
        must not win just because it clears the word-count cap and contains
        the role-hint keyword 'lead'."""
        jd = "You will lead the Product org.\nSenior Product Manager"
        assert _infer_role_title(jd) == "Senior Product Manager"


class TestApplicationTitleIsRoleOnly:
    """fix/review-surface-and-flows (owner spec, revised mid-branch): `Application.title`
    is the cleaned ROLE TITLE ONLY — no company prefix. Company already renders
    separately (`Application.company`, F-15) on the card / detail modal, so an
    earlier "Company — Role Title" composition would have duplicated it; that
    combinator was written, then removed on explicit owner direction before
    landing. This covers the creation-time call site in
    `build_context_set_from_db` end-to-end (not just the extractor unit, see
    `TestInferRoleTitle` above)."""

    def test_title_is_role_only_company_stays_in_its_own_column(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        jd = "Senior Backend Engineer\nAcme Robotics — Remote\n\nDuties follow."
        _ctx, app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text=jd,
            run_id="role_only_run1",
        )
        assert app.title == "Senior Backend Engineer"
        assert "—" not in app.title
        assert "Acme" not in app.title
        assert app.company == "Acme Robotics"  # unchanged F-15 channel

    def test_falls_back_to_cleaned_first_line_when_no_role_hint(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        jd = "Come join our mission-driven team\nWe do great work.\nApply today."
        _ctx, app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text=jd,
            run_id="role_only_run2",
        )
        assert app.title == "Come join our mission-driven team"

    def test_empty_jd_falls_back_to_untitled_application(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        _ctx, app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="",
            run_id="role_only_run3",
        )
        assert app.title == "Untitled application"


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
            skills=["Python"],
            certifications=[],
            educations=[],
            candidate=c,
        )
        assert "# Casey Tester" in text
        assert "casey@example.com" in text

    def test_includes_official_titles_not_alternates(self, db_session):
        c = _seed_full_candidate(db_session)
        text = _synthesize_resume_markdown(
            experiences=sorted(c.experiences, key=lambda e: e.start_date, reverse=True),
            skills=[],
            certifications=[],
            educations=[],
            candidate=c,
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
            skills=[],
            certifications=[],
            educations=[],
            candidate=c,
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
                type(
                    "E",
                    (),
                    {
                        "institution": "MIT",
                        "degree": "BS CS",
                        "start_date": "2010",
                        "end_date": "2014",
                    },
                )(),
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
        for required in (
            "timestamp",
            "candidate",
            "resume",
            "supplemental_resumes",
            "job_description",
            "deterministic_analysis",
        ):
            assert required in ctx, f"Missing ContextSet key: {required}"

        assert ctx["candidate"]["name"] == "Casey Tester"
        assert "Python" in ctx["candidate"]["skills"]
        assert ctx["job_description"].startswith("Senior PM role")
        assert ctx["supplemental_resumes"] == []
        assert ctx["resume"]["format"] == "md"
        assert "Casey Tester" in ctx["resume"]["text"]

    def test_corpus_mode_suppresses_ats_warnings(self, db_session):
        """Walkthrough G1: no ATS heading/length warnings on the corpus synthesis.

        The synthesized 'résumé' is a structured projection (not an uploaded doc,
        not the final deliverable), so the legacy uploaded-résumé ATS-format
        warnings don't apply and would only confuse.
        """
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Senior PM role at Foo\nResponsibilities here.",
            run_id="ats0000warn00",
        )
        assert ctx["deterministic_analysis"]["ats_warnings"] == []

    def test_online_profile_text_flows_into_candidate_block(self, db_session):
        """PX-02: the cached scrape (Candidate.online_profile_text) reaches the
        ContextSet candidate block — a DISTINCT channel from profile_text (the
        β.6 positioning summary)."""
        c = _seed_full_candidate(db_session)
        c.online_profile_text = "--- Linkedin ---\nScraped bio text."
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Senior PM role",
            run_id="run_opt",
        )
        assert ctx["candidate"]["online_profile_text"] == "--- Linkedin ---\nScraped bio text."

    def test_online_profile_text_defaults_empty_when_unset(self, db_session):
        """No scrape cached → empty string (not None), so the analyzer's
        conditional <candidate_web_presence> block stays absent."""
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="run_empty",
        )
        assert ctx["candidate"]["online_profile_text"] == ""

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

    def test_application_company_captured_from_jd(self, db_session):
        """F-15: the Application row's company is populated at creation time
        (not left null for the user to notice and fill in by hand)."""
        _seed_full_candidate(db_session)
        db_session.commit()
        _ctx, app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="About Lattice Cloud\nWe run a multi-region container platform.",
            run_id="run_company",
        )
        assert app.company == "Lattice Cloud"

    def test_application_company_none_when_jd_has_no_signal(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        _ctx, app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Responsibilities include leading a team.",
            run_id="run_no_company",
        )
        assert app.company is None

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


# ---------------------------------------------------------------------------
# D5 (feat/clarifications-to-corpus): cross-JD prior_clarifications reuse
# ---------------------------------------------------------------------------


class TestPriorClarifications:
    """`clarification` rows are candidate-scoped by design (cross-application
    candidate memory), so build_context_set_from_db stages every existing row
    for the candidate onto ctx["prior_clarifications"] — the just-created
    Application row can't own any of them yet, so no origin filter is needed."""

    def test_no_prior_clarifications_returns_empty_list(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="run_no_prior",
        )
        assert ctx["prior_clarifications"] == []

    def test_existing_clarifications_from_another_application_surface(self, db_session):
        from db.models import Application, Clarification

        c = _seed_full_candidate(db_session)
        earlier_app = Application(
            candidate_id=c.id,
            title="Earlier SRE role",
            jd_text="SRE role",
            jd_fingerprint="e" * 16,
        )
        db_session.add(earlier_app)
        db_session.flush()
        db_session.add(
            Clarification(
                candidate_id=c.id,
                origin_application_id=earlier_app.id,
                question="Have you led an on-call rotation?",
                answer="Led on-call for a 12-person SRE team, cut MTTR 40%.",
                kind="experience_probe",
            )
        )
        db_session.commit()

        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="Senior SRE role",
            run_id="run_with_prior",
        )
        assert len(ctx["prior_clarifications"]) == 1
        row = ctx["prior_clarifications"][0]
        assert row["question"] == "Have you led an on-call rotation?"
        assert row["answer"] == "Led on-call for a 12-person SRE team, cut MTTR 40%."
        assert row["kind"] == "experience_probe"
        assert row["origin_application_id"] == earlier_app.id

    def test_capped_and_most_recent_first(self, db_session):
        from db.build_context import _prior_clarifications_for_candidate
        from db.models import Clarification

        c = _seed_full_candidate(db_session)
        for i in range(3):
            db_session.add(
                Clarification(
                    candidate_id=c.id,
                    question=f"q{i}",
                    answer=f"a{i}",
                    kind="manual",
                )
            )
        db_session.commit()

        capped = _prior_clarifications_for_candidate(db_session, c.id, limit=2)
        assert len(capped) == 2
        # Most-recent-first: the last-inserted row (q2) comes first.
        assert capped[0]["question"] == "q2"


# ---------------------------------------------------------------------------
# Phase B.2: structured career_corpus payload
# ---------------------------------------------------------------------------


class TestCareerCorpusPayload:
    def test_career_corpus_field_present_in_contextset(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="r",
        )
        assert "career_corpus" in ctx
        assert isinstance(ctx["career_corpus"], list)
        assert len(ctx["career_corpus"]) >= 1

    def test_corpus_experience_carries_eligible_titles_official_first(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="r",
        )
        polaris = next(e for e in ctx["career_corpus"] if e["company"] == "Polaris")
        # Polaris has 2 eligible titles (official + truthful_enough alternate)
        assert len(polaris["eligible_titles"]) == 2
        # Official always first
        assert polaris["eligible_titles"][0]["is_official"] is True
        assert polaris["eligible_titles"][0]["title"] == "Senior PM, ML Platform"
        assert polaris["eligible_titles"][1]["is_official"] is False
        assert polaris["eligible_titles"][1]["title"] == "AI Product Lead"

    def test_corpus_bullets_are_active_only(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="r",
        )
        acme = next(e for e in ctx["career_corpus"] if e["company"] == "Acme")
        # Acme has 2 bullets seeded: 1 active, 1 retired (is_active=0)
        assert len(acme["bullets"]) == 1
        assert acme["bullets"][0]["text"] == "Built design org."

    def test_corpus_bullet_carries_id_and_outcome(self, db_session):
        _seed_full_candidate(db_session)
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="casey",
            jd_text="x",
            run_id="r",
        )
        polaris = next(e for e in ctx["career_corpus"] if e["company"] == "Polaris")
        bullets = polaris["bullets"]
        assert all("id" in b for b in bullets)
        assert all(isinstance(b["id"], int) for b in bullets)
        has_outcome_bullet = next(b for b in bullets if b["text"].startswith("Led 5-person"))
        assert has_outcome_bullet["has_outcome"] is True

    def test_corpus_skips_excluded_titles(self, db_session):
        """Titles flagged neither is_official nor truthful_enough_to_use must
        not appear in eligible_titles."""
        from db.models import (
            Candidate,
            Experience,
            ExperienceTitle,
        )

        c = Candidate(username="bob", name="Bob")
        db_session.add(c)
        db_session.flush()
        e = Experience(
            candidate_id=c.id,
            company="X",
            start_date="2020-01",
            end_date="2021-12",
        )
        db_session.add(e)
        db_session.flush()
        # Three titles: official, truthful_enough, and neither
        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Real PM",
                is_official=1,
                source="official",
            )
        )
        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Alt PM",
                truthful_enough_to_use=1,
                source="user_added",
            )
        )
        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Suggested but not approved",
                is_official=0,
                truthful_enough_to_use=0,
                source="llm_proposed:rN",
            )
        )
        db_session.commit()
        ctx, _app, _run = build_context_set_from_db(
            db_session,
            candidate_username="bob",
            jd_text="x",
            run_id="r",
        )
        exp_payload = ctx["career_corpus"][0]
        titles_in_payload = {t["title"] for t in exp_payload["eligible_titles"]}
        assert "Real PM" in titles_in_payload
        assert "Alt PM" in titles_in_payload
        assert "Suggested but not approved" not in titles_in_payload

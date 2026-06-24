"""Tests for the file→DB corpus importer (onboarding/corpus_import.py).

Uses a temp configs/ and output/ directory tree per test so we don't depend
on the real user's data. The importer's CONFIGS_DIR/OUTPUT_DIR are patched
in-place; pytest's monkeypatch reverts at teardown.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from db.models import (
    Candidate,
    Certification,
    Clarification,
    Education,
    Experience,
    Skill,
)
from onboarding import corpus_import
from onboarding.corpus_import import (
    ImportReport,
    _insert_or_merge_experience,
    _iter_resume_files,
    import_candidate_from_config,
    import_clarifications_from_output,
)

# ---------------------------------------------------------------------------
# Fixtures: temp PII tree
# ---------------------------------------------------------------------------


@pytest.fixture()
def legacy_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a configs/+output/ tree under tmp_path and point the importer at it."""
    configs = tmp_path / "configs"
    output = tmp_path / "output"
    configs.mkdir()
    output.mkdir()
    monkeypatch.setattr(corpus_import, "CONFIGS_DIR", configs)
    monkeypatch.setattr(corpus_import, "OUTPUT_DIR", output)
    return tmp_path


def _write_config(legacy_tree: Path, username: str, payload: dict) -> None:
    (legacy_tree / "configs" / f"{username}.config").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_context(legacy_tree: Path, username: str, filename: str, payload: dict) -> None:
    user_dir = legacy_tree / "output" / username
    user_dir.mkdir(exist_ok=True)
    (user_dir / filename).write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# import_candidate_from_config
# ---------------------------------------------------------------------------


class TestImportCandidate:
    def test_creates_candidate_with_basic_fields(self, db_session, legacy_tree):
        _write_config(
            legacy_tree,
            "alice",
            {
                "name": "Alice",
                "email": "a@x.com",
                "phone": "555-0100",
                "linkedin_url": "https://linkedin.com/in/alice",
                "website_url": "",
                "skills": [],
                "certifications": [],
                "education_summary": "",
                "notes": "Remote only.",
            },
        )
        report = import_candidate_from_config("alice", db_session)
        assert report.candidate_created is True
        assert report.candidate_id is not None

        c = db_session.query(Candidate).filter_by(username="alice").one()
        assert c.name == "Alice"
        assert c.email == "a@x.com"
        assert c.linkedin_url == "https://linkedin.com/in/alice"
        assert c.notes == "Remote only."

    def test_creates_skills_and_certifications(self, db_session, legacy_tree):
        _write_config(
            legacy_tree,
            "bob",
            {
                "name": "Bob",
                "skills": ["Python", "PostgreSQL", "  ", ""],  # whitespace + empty filtered out
                "certifications": ["AWS SA Pro", "CKAD"],
                "education_summary": "MS CS, MIT",
            },
        )
        report = import_candidate_from_config("bob", db_session)
        assert report.skills_created == 2  # whitespace/empty filtered
        assert report.certifications_created == 2
        assert report.education_created == 1

        assert db_session.query(Skill).count() == 2
        assert db_session.query(Certification).count() == 2
        assert db_session.query(Education).count() == 1

    def test_idempotent_on_rerun(self, db_session, legacy_tree):
        _write_config(
            legacy_tree,
            "carol",
            {
                "name": "Carol",
                "skills": ["A", "B"],
                "certifications": ["X"],
                "education_summary": "BSc",
            },
        )
        import_candidate_from_config("carol", db_session)
        db_session.commit()

        report = import_candidate_from_config("carol", db_session)
        assert report.candidate_created is False
        assert report.skills_created == 0
        assert report.skills_skipped == 2
        assert report.certifications_skipped == 1
        assert report.education_skipped == 1

    def test_dry_run_does_not_persist(self, db_session, legacy_tree):
        _write_config(legacy_tree, "dave", {"name": "Dave", "skills": ["Rust"]})
        import_candidate_from_config("dave", db_session, dry_run=True)
        # Report says "created 1 skill" but no actual rows committed.
        assert db_session.query(Candidate).count() == 0
        assert db_session.query(Skill).count() == 0

    def test_missing_config_raises(self, db_session, legacy_tree):
        with pytest.raises(FileNotFoundError):
            import_candidate_from_config("nobody", db_session)


# ---------------------------------------------------------------------------
# import_clarifications_from_output
# ---------------------------------------------------------------------------


def _make_context_payload(qa_pairs: list[tuple[str, str, str, str]]) -> dict:
    """qa_pairs: [(qid, qtext, atext, kind), ...]"""
    return {
        "clarification_questions": [
            {"id": qid, "text": q, "kind": k, "target_gap": ""} for qid, q, _a, k in qa_pairs
        ],
        "clarifications": {qid: a for qid, _q, a, _k in qa_pairs},
    }


class TestImportClarifications:
    def _seed_candidate(self, db_session, legacy_tree, username="alice"):
        _write_config(legacy_tree, username, {"name": username})
        rpt = import_candidate_from_config(username, db_session)
        db_session.commit()
        return rpt.candidate_id

    def test_imports_qa_pairs_with_answers(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(
            legacy_tree,
            "alice",
            "context_20260101_120000.json",
            _make_context_payload(
                [
                    (
                        "q1",
                        "Have you used K8s?",
                        "Yes, briefly on a side project.",
                        "experience_probe",
                    ),
                    (
                        "q2",
                        "Was the launch shipped?",
                        "Shipped to 50 enterprise customers.",
                        "scope_probe",
                    ),
                ]
            ),
        )
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 2
        assert report.context_files_scanned == 1
        assert db_session.query(Clarification).count() == 2

    def test_skips_unanswered_questions(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(
            legacy_tree,
            "alice",
            "context_a.json",
            {
                "clarification_questions": [
                    {"id": "q1", "text": "Asked but skipped?", "kind": "experience_probe"},
                ],
                "clarifications": {},  # user skipped
            },
        )
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 0

    def test_dedupes_across_iteration_files(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        pairs = [("q1", "Have you used K8s?", "Yes, briefly.", "experience_probe")]
        _write_context(legacy_tree, "alice", "context_a.json", _make_context_payload(pairs))
        _write_context(legacy_tree, "alice", "context_a_iter1.json", _make_context_payload(pairs))
        _write_context(legacy_tree, "alice", "context_b.json", _make_context_payload(pairs))
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 1
        assert report.clarifications_skipped == 2

    def test_dedupe_normalizes_whitespace_and_case(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(
            legacy_tree,
            "alice",
            "context_1.json",
            _make_context_payload(
                [
                    (
                        "q1",
                        "Have you used K8s?",
                        "Yes, BRIEFLY on a side project.",
                        "experience_probe",
                    ),
                ]
            ),
        )
        _write_context(
            legacy_tree,
            "alice",
            "context_2.json",
            _make_context_payload(
                [
                    (
                        "q1",
                        "  Have you used K8s?  ",
                        "yes, briefly on a side project.",
                        "experience_probe",
                    ),
                ]
            ),
        )
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 1
        assert report.clarifications_skipped == 1

    def test_unknown_kind_falls_back_to_manual(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(
            legacy_tree,
            "alice",
            "context_x.json",
            {
                "clarification_questions": [
                    {"id": "q1", "text": "What is X?", "kind": "novel_unsupported_kind"},
                ],
                "clarifications": {"q1": "An answer."},
            },
        )
        import_clarifications_from_output("alice", cid, db_session)
        row = db_session.query(Clarification).one()
        assert row.kind == "manual"

    def test_no_output_dir_is_empty_scan(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        # No output/alice/ directory at all
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.context_files_scanned == 0
        assert report.clarifications_created == 0

    def test_malformed_json_recorded_in_errors(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        user_dir = legacy_tree / "output" / "alice"
        user_dir.mkdir()
        (user_dir / "context_broken.json").write_text("{not valid json", encoding="utf-8")
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.context_files_scanned == 1
        assert report.clarifications_created == 0
        assert len(report.errors) == 1


# ---------------------------------------------------------------------------
# ImportReport.merge
# ---------------------------------------------------------------------------


class TestImportReportMerge:
    def test_merge_sums_counters(self):
        a = ImportReport(skills_created=3, clarifications_created=2)
        b = ImportReport(skills_created=1, clarifications_skipped=4, errors=["x"])
        a.merge(b)
        assert a.skills_created == 4
        assert a.clarifications_created == 2
        assert a.clarifications_skipped == 4
        assert a.errors == ["x"]


# ---------------------------------------------------------------------------
# Resume-file ordering and merge-as-alternate-title (the redesign-critical bits)
# ---------------------------------------------------------------------------


@pytest.fixture()
def resumes_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a resumes/+configs/ tree under tmp_path and point the importer at it."""
    configs = tmp_path / "configs"
    resumes = tmp_path / "resumes"
    configs.mkdir()
    resumes.mkdir()
    monkeypatch.setattr(corpus_import, "CONFIGS_DIR", configs)
    monkeypatch.setattr(corpus_import, "RESUMES_DIR", resumes)
    return tmp_path


def _write_resume(tree: Path, username: str, filename: str, content: str = "stub") -> None:
    user_dir = tree / "resumes" / username
    user_dir.mkdir(exist_ok=True)
    (user_dir / filename).write_text(content, encoding="utf-8")


class TestIterResumeFiles:
    def test_alphabetical_when_no_config(self, resumes_tree):
        _write_resume(resumes_tree, "alice", "b.md")
        _write_resume(resumes_tree, "alice", "a.md")
        _write_resume(resumes_tree, "alice", "c.md")
        result = [p.name for p in _iter_resume_files("alice")]
        assert result == ["a.md", "b.md", "c.md"]

    def test_primary_first_via_latest_resume(self, resumes_tree):
        _write_resume(resumes_tree, "alice", "alpha.md")
        _write_resume(resumes_tree, "alice", "main.md")
        _write_resume(resumes_tree, "alice", "zeta.md")
        (resumes_tree / "configs" / "alice.config").write_text(
            json.dumps({"latest_resume": "main.md"}),
            encoding="utf-8",
        )
        result = [p.name for p in _iter_resume_files("alice")]
        assert result == ["main.md", "alpha.md", "zeta.md"]

    def test_included_resumes_filters(self, resumes_tree):
        _write_resume(resumes_tree, "alice", "a.md")
        _write_resume(resumes_tree, "alice", "b.md")
        _write_resume(resumes_tree, "alice", "c.md")
        (resumes_tree / "configs" / "alice.config").write_text(
            json.dumps({"latest_resume": "a.md", "included_resumes": ["a.md", "c.md"]}),
            encoding="utf-8",
        )
        result = [p.name for p in _iter_resume_files("alice")]
        assert result == ["a.md", "c.md"]

    def test_empty_included_list_means_include_all(self, resumes_tree):
        _write_resume(resumes_tree, "alice", "a.md")
        _write_resume(resumes_tree, "alice", "b.md")
        (resumes_tree / "configs" / "alice.config").write_text(
            json.dumps({"included_resumes": []}),
            encoding="utf-8",
        )
        result = [p.name for p in _iter_resume_files("alice")]
        # Empty whitelist treated as "no whitelist" — back to alphabetical fallback.
        assert result == ["a.md", "b.md"]

    def test_malformed_config_falls_back_to_alphabetical(self, resumes_tree):
        _write_resume(resumes_tree, "alice", "a.md")
        _write_resume(resumes_tree, "alice", "b.md")
        (resumes_tree / "configs" / "alice.config").write_text("{ not json", encoding="utf-8")
        result = [p.name for p in _iter_resume_files("alice")]
        assert result == ["a.md", "b.md"]


class TestInsertOrMergeExperience:
    def _make_candidate(self, db_session, username="alice"):
        c = Candidate(username=username, name="Test")
        db_session.add(c)
        db_session.flush()
        return c

    def test_first_extraction_creates_experience_with_official_title(self, db_session):
        c = self._make_candidate(db_session)
        report = ImportReport()
        exp_data = {
            "company": "Acme",
            "start_date": "2020-01",
            "end_date": "2023-04",
            "candidate_inferred_title": "Senior PM",
            "bullets": [{"text": "Did the thing.", "has_outcome": False}],
        }
        _insert_or_merge_experience(
            exp_data,
            c.id,
            source_filename="primary.md",
            is_primary_file=True,
            session=db_session,
            dry_run=False,
            report=report,
        )
        db_session.flush()
        assert report.experiences_created == 1
        assert report.experiences_merged == 0
        exp = db_session.query(Experience).filter_by(candidate_id=c.id).one()
        assert exp.company == "Acme"
        assert len(exp.titles) == 1
        assert exp.titles[0].is_official == 1
        assert exp.titles[0].title == "Senior PM"
        assert len(exp.bullets) == 1
        assert exp.bullets[0].source == "primary:primary.md"

    def test_second_file_with_same_company_dates_adds_alternate_title(self, db_session):
        c = self._make_candidate(db_session)
        report = ImportReport()
        # Primary extraction first
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "Senior PM",
                "bullets": [{"text": "Led team.", "has_outcome": False}],
            },
            c.id,
            source_filename="primary.md",
            is_primary_file=True,
            session=db_session,
            dry_run=False,
            report=report,
        )
        # Supplemental with same dates but different title framing
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "AI Product Lead",
                "bullets": [{"text": "Owned eval framework.", "has_outcome": False}],
            },
            c.id,
            source_filename="ai_framed.md",
            is_primary_file=False,
            session=db_session,
            dry_run=False,
            report=report,
        )
        db_session.flush()

        assert report.experiences_created == 1
        assert report.experiences_merged == 1
        assert report.alternate_titles_created == 1

        exp = db_session.query(Experience).filter_by(candidate_id=c.id).one()
        assert len(exp.titles) == 2
        official = [t for t in exp.titles if t.is_official]
        alternate = [t for t in exp.titles if not t.is_official]
        assert official[0].title == "Senior PM"
        assert alternate[0].title == "AI Product Lead"
        assert alternate[0].truthful_enough_to_use == 1
        assert alternate[0].is_pending_review == 1

    def test_merge_appends_new_bullets_with_supplemental_source(self, db_session):
        c = self._make_candidate(db_session)
        report = ImportReport()
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "Senior PM",
                "bullets": [{"text": "Led team.", "has_outcome": False}],
            },
            c.id,
            source_filename="primary.md",
            is_primary_file=True,
            session=db_session,
            dry_run=False,
            report=report,
        )
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "Senior PM",  # same title — no alternate
                "bullets": [
                    {"text": "Different phrasing of similar achievement.", "has_outcome": False}
                ],
            },
            c.id,
            source_filename="other.md",
            is_primary_file=False,
            session=db_session,
            dry_run=False,
            report=report,
        )
        db_session.flush()

        # Same title → no alternate created
        assert report.alternate_titles_created == 0
        # Both bullets present, distinct source provenance
        exp = db_session.query(Experience).filter_by(candidate_id=c.id).one()
        sources = sorted(b.source for b in exp.bullets)
        assert sources == ["primary:primary.md", "supplemental:other.md"]

    def test_merge_dedupes_identical_bullet_text_across_sources(self, db_session):
        """Re-running import of the same résumé file shouldn't double-add bullets.

        The dedup key is (experience_id, normalized_text) — it ignores
        source so the same-file re-import case (where the source prefix
        flips primary→supplemental between runs) doesn't slip through.
        Same achievement phrased identically across two files is also
        treated as one bullet; the user prunes intra-file duplicates by
        editing the corpus directly.
        """
        c = self._make_candidate(db_session)
        report = ImportReport()
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "Senior PM",
                "bullets": [{"text": "Led team.", "has_outcome": False}],
            },
            c.id,
            source_filename="primary.md",
            is_primary_file=True,
            session=db_session,
            dry_run=False,
            report=report,
        )
        # Same text — should be deduped on second insert despite the
        # source prefix flipping to supplemental on the merge path.
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "AI Lead",
                "bullets": [{"text": "Led team.", "has_outcome": False}],
            },
            c.id,
            source_filename="primary.md",
            is_primary_file=False,
            session=db_session,
            dry_run=False,
            report=report,
        )
        db_session.flush()

        exp = db_session.query(Experience).filter_by(candidate_id=c.id).one()
        assert len(exp.bullets) == 1
        # The surviving bullet is the original (primary) insert.
        assert exp.bullets[0].source == "primary:primary.md"
        assert exp.bullets[0].text == "Led team."

    def test_dry_run_does_not_persist(self, db_session):
        c = self._make_candidate(db_session)
        report = ImportReport()
        _insert_or_merge_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "PM",
                "bullets": [{"text": "x", "has_outcome": False}],
            },
            c.id,
            source_filename="r.md",
            is_primary_file=True,
            session=db_session,
            dry_run=True,
            report=report,
        )
        # Counters update but nothing in DB
        assert report.experiences_created == 1
        assert report.bullets_created == 1
        assert db_session.query(Experience).count() == 0

    def test_sentinel_empty_company_skips(self, db_session):
        """_normalize_experience returns {"company": ""} for malformed rows."""
        c = self._make_candidate(db_session)
        report = ImportReport()
        _insert_or_merge_experience(
            {"company": "", "start_date": "", "candidate_inferred_title": ""},
            c.id,
            source_filename="r.md",
            is_primary_file=True,
            session=db_session,
            dry_run=False,
            report=report,
        )
        assert report.experiences_created == 0
        assert db_session.query(Experience).count() == 0

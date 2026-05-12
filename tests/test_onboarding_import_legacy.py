"""Tests for the file→DB legacy importer.

Uses a temp configs/ and output/ directory tree per test so we don't depend
on the real user's data. The importer's CONFIGS_DIR/OUTPUT_DIR are patched
in-place; pytest's monkeypatch reverts at teardown.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from db.models import Candidate, Certification, Clarification, Education, Skill
from onboarding import import_legacy
from onboarding.import_legacy import (
    ImportReport,
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
    monkeypatch.setattr(import_legacy, "CONFIGS_DIR", configs)
    monkeypatch.setattr(import_legacy, "OUTPUT_DIR", output)
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
        _write_config(legacy_tree, "alice", {
            "name": "Alice", "email": "a@x.com", "phone": "555-0100",
            "linkedin_url": "https://linkedin.com/in/alice",
            "website_url": "", "skills": [], "certifications": [],
            "education_summary": "", "notes": "Remote only.",
        })
        report = import_candidate_from_config("alice", db_session)
        assert report.candidate_created is True
        assert report.candidate_id is not None

        c = db_session.query(Candidate).filter_by(username="alice").one()
        assert c.name == "Alice"
        assert c.email == "a@x.com"
        assert c.linkedin_url == "https://linkedin.com/in/alice"
        assert c.notes == "Remote only."

    def test_creates_skills_and_certifications(self, db_session, legacy_tree):
        _write_config(legacy_tree, "bob", {
            "name": "Bob",
            "skills": ["Python", "PostgreSQL", "  ", ""],  # whitespace + empty filtered out
            "certifications": ["AWS SA Pro", "CKAD"],
            "education_summary": "MS CS, MIT",
        })
        report = import_candidate_from_config("bob", db_session)
        assert report.skills_created == 2  # whitespace/empty filtered
        assert report.certifications_created == 2
        assert report.education_created == 1

        assert db_session.query(Skill).count() == 2
        assert db_session.query(Certification).count() == 2
        assert db_session.query(Education).count() == 1

    def test_idempotent_on_rerun(self, db_session, legacy_tree):
        _write_config(legacy_tree, "carol", {
            "name": "Carol", "skills": ["A", "B"], "certifications": ["X"],
            "education_summary": "BSc",
        })
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
            {"id": qid, "text": q, "kind": k, "target_gap": ""}
            for qid, q, _a, k in qa_pairs
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
        _write_context(legacy_tree, "alice", "context_20260101_120000.json",
            _make_context_payload([
                ("q1", "Have you used K8s?", "Yes, briefly on a side project.", "experience_probe"),
                ("q2", "Was the launch shipped?", "Shipped to 50 enterprise customers.", "scope_probe"),
            ]))
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 2
        assert report.context_files_scanned == 1
        assert db_session.query(Clarification).count() == 2

    def test_skips_unanswered_questions(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(legacy_tree, "alice", "context_a.json", {
            "clarification_questions": [
                {"id": "q1", "text": "Asked but skipped?", "kind": "experience_probe"},
            ],
            "clarifications": {},  # user skipped
        })
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
        _write_context(legacy_tree, "alice", "context_1.json", _make_context_payload([
            ("q1", "Have you used K8s?", "Yes, BRIEFLY on a side project.", "experience_probe"),
        ]))
        _write_context(legacy_tree, "alice", "context_2.json", _make_context_payload([
            ("q1", "  Have you used K8s?  ", "yes, briefly on a side project.", "experience_probe"),
        ]))
        report = import_clarifications_from_output("alice", cid, db_session)
        assert report.clarifications_created == 1
        assert report.clarifications_skipped == 1

    def test_unknown_kind_falls_back_to_manual(self, db_session, legacy_tree):
        cid = self._seed_candidate(db_session, legacy_tree)
        _write_context(legacy_tree, "alice", "context_x.json", {
            "clarification_questions": [
                {"id": "q1", "text": "What is X?", "kind": "novel_unsupported_kind"},
            ],
            "clarifications": {"q1": "An answer."},
        })
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

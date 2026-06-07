"""Smoke tests for the committed dummy-user fixture (Casey Rivera).

The fixture lives at:
- configs/testuser.config
- resumes/testuser/casey_rivera_primary.md
- resumes/testuser/casey_rivera_ai_framed.md

Purpose: catch accidental damage (deleted file, malformed JSON, broken
resume markdown) before it breaks development workflows.

These tests do NOT make LLM calls — they verify file presence, JSON shape,
and that the deterministic part of the importer produces the expected
counts when pointed at the fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "testuser.config"
RESUME_DIR = REPO_ROOT / "resumes" / "testuser"


class TestFixtureFiles:
    def test_config_exists(self):
        assert CONFIG_PATH.exists(), f"Missing fixture: {CONFIG_PATH}"

    def test_config_is_valid_json(self):
        with CONFIG_PATH.open(encoding="utf-8") as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict)

    def test_config_has_required_fields(self):
        with CONFIG_PATH.open(encoding="utf-8") as f:
            cfg = json.load(f)
        for required in ("name", "email", "skills", "education_summary"):
            assert required in cfg, f"testuser.config missing {required!r}"

    def test_config_uses_safe_domain(self):
        """RFC 2606 says example.* is reserved for docs/fixtures. Belt-and-suspenders
        check against a real email accidentally landing here."""
        with CONFIG_PATH.open(encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["email"].endswith("@example.com"), (
            "testuser.config email must use example.com (RFC 2606 reserved)"
        )

    def test_resumes_directory_exists(self):
        assert RESUME_DIR.is_dir(), f"Missing fixture directory: {RESUME_DIR}"

    def test_primary_resume_exists(self):
        path = RESUME_DIR / "casey_rivera_primary.md"
        assert path.exists(), f"Missing fixture: {path}"
        assert path.stat().st_size > 500, "Primary resume looks suspiciously empty"

    def test_supplemental_resume_exists(self):
        path = RESUME_DIR / "casey_rivera_ai_framed.md"
        assert path.exists(), f"Missing fixture: {path}"

    def test_resumes_are_well_formed_markdown(self):
        """Every committed resume should have at least one ## heading section
        and several bullets — basic sanity that we didn't commit an empty stub."""
        for path in RESUME_DIR.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert "## " in text, f"{path.name} has no ## headings"
            assert text.count("\n- ") >= 5, f"{path.name} has fewer than 5 bullets"


class TestImporterAgainstFixture:
    """End-to-end smoke: the deterministic part of the importer should produce
    the same counts for testuser on every machine. Catches drift in either the
    fixture or the importer's parsing logic.
    """

    def test_dry_run_produces_expected_deterministic_counts(self, tmp_path):
        from onboarding.corpus_import import run_import

        db_path = tmp_path / "fixture_smoke.sqlite"
        report = run_import("testuser", dry_run=True, with_llm=False, db_path=db_path)

        assert report.candidate_created is True
        # Specific counts pinned to the committed fixture. If these change,
        # both this test and the fixture need to move together.
        assert report.skills_created == 9
        assert report.certifications_created == 2
        assert report.education_created == 1
        # No output/testuser/ in the repo — clarifications come in via the user's
        # own session, not the fixture.
        assert report.clarifications_created == 0

    def test_dry_run_detects_both_resume_files(self, tmp_path):
        """--with-llm in dry-run mode counts resume files but does NOT call LLM."""
        from onboarding.corpus_import import run_import

        db_path = tmp_path / "fixture_resumes.sqlite"
        report = run_import("testuser", dry_run=True, with_llm=True, db_path=db_path)
        assert report.resume_files_processed == 2

    def test_real_import_then_reimport_is_idempotent(self, tmp_path):
        """Running the deterministic importer twice should yield zero new rows
        on the second run. Validates the dedupe path for the fixture user."""
        from onboarding.corpus_import import run_import

        db_path = tmp_path / "fixture_idempotent.sqlite"

        first = run_import("testuser", dry_run=False, with_llm=False, db_path=db_path)
        assert first.skills_created == 9
        assert first.candidate_created is True

        second = run_import("testuser", dry_run=False, with_llm=False, db_path=db_path)
        assert second.candidate_created is False
        assert second.skills_created == 0
        assert second.skills_skipped == 9


class TestFixtureUsedNotRealUser:
    """Defensive: real users' configs (robert.config, etc.) MUST stay gitignored.
    If this test ever finds them in git, someone removed a gitignore entry."""

    def test_only_example_and_testuser_configs_are_tracked(self):
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "configs/"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            pytest.skip("Not in a git working tree (CI quirk or detached snapshot)")
        tracked = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
        # Allow example.config and testuser.config; everything else is a real user.
        allowed = {"configs/example.config", "configs/testuser.config"}
        leaked = [t for t in tracked if t not in allowed]
        assert not leaked, f"Real-user configs leaked into git tracking: {leaked}"

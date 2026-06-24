"""Smoke tests for the bundled persona templates.

Phase C.1 shipped 5 bundled templates. v1.0.0 curated to 4 (compact
+ hybrid_tech retired; hybrid_tech renamed to tech with a new
ATS-tested design — see migration 0005 + scripts/build_bundled_templates.py).

Verifies:
- The 4 final bundled .docx files exist on disk
- Each is readable as a .docx and round-trips through parser.parse_resume
- The PRESETS list in the build script defines exactly those 4 files
- A fresh DB migration ends at 4 bundled rows (0002 seeds 5, 0005
  deletes Compact and renames Hybrid Tech → Tech)
- Re-running migrations is idempotent
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_DIR = REPO_ROOT / "personas" / "bundled"

# v1.0.0 curated set. Compact retired (sidebar layout was ATS-unsafe);
# Hybrid Tech renamed to Tech with a rebuilt dev-ats-inspired design.
EXPECTED_FILES = [
    "classic.docx",
    "modern.docx",
    "spacious.docx",
    "tech.docx",
]

# Files that USED to ship but are intentionally gone in v1.0.0. The
# negative case is pinned so a future revert is loud.
RETIRED_FILES = [
    "compact.docx",
    "hybrid_tech.docx",
]


class TestBundledFiles:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_each_template_file_exists(self, filename):
        path = BUNDLED_DIR / filename
        assert path.exists(), f"Missing bundled template: {path}"
        # Sanity-check file size — empty / corrupt files have a known small footprint
        assert path.stat().st_size > 5000, (
            f"{filename} suspiciously small ({path.stat().st_size} bytes)"
        )

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_each_template_parses_cleanly(self, filename):
        """The bundled template must be a valid .docx that parser.py can read.
        Some text + at least the placeholder content must come out."""
        from parser import parse_resume

        path = BUNDLED_DIR / filename
        parsed = parse_resume(str(path))
        assert parsed["format"] == ".docx"
        assert len(parsed["text"]) > 100, f"{filename} parsed to suspiciously little text"
        # Every bundled template ships with the same sample content placeholders
        assert "Casey Rivera" in parsed["text"]
        assert "Sample Company" in parsed["text"]

    @pytest.mark.parametrize("filename", RETIRED_FILES)
    def test_retired_template_files_are_gone(self, filename):
        """Pinning the absence so a future commit that re-adds the retired
        templates fails this test instead of silently shipping unsafe ones."""
        path = BUNDLED_DIR / filename
        assert not path.exists(), (
            f"{filename} was retired in v1.0.0 but is back on disk. "
            "Compact had a sidebar layout that's ATS-unsafe; Hybrid Tech "
            "was renamed to tech.docx with a rebuilt design. See "
            "db/migrations/versions/0005_curate_bundled_templates.py."
        )


class TestPresetConsistency:
    """The PRESETS list defines the canonical curated set. v1.0.0
    migration 0005 deletes Compact + renames Hybrid Tech → Tech, so the
    canonical set is now exactly 4 templates."""

    def test_presets_define_the_curated_four(self):
        from scripts.build_bundled_templates import PRESETS

        preset_filenames = {p.filename for p in PRESETS}
        assert preset_filenames == set(EXPECTED_FILES), (
            f"PRESETS filenames {preset_filenames} disagree with "
            f"expected v1.0.0 curated set {set(EXPECTED_FILES)}"
        )


class TestSeedMigration:
    def test_fresh_migration_settles_at_4_bundled_rows(self, tmp_path):
        """After running all migrations (including 0005's curation pass),
        the bundled set is the 4 v1.0.0 templates."""
        from db.models import PersonaTemplate
        from db.session import init_db, make_engine, make_session_factory

        db_file = tmp_path / "seed_test.sqlite"
        init_db(db_file)
        engine = make_engine(db_file)
        try:
            session = make_session_factory(engine)()
            rows = session.query(PersonaTemplate).filter_by(source="bundled").all()
            assert len(rows) == 4
            names = sorted(r.name for r in rows)
            assert names == sorted(
                [
                    "Classic Single-Column",
                    "Modern Single-Column",
                    "Spacious (Career Changer / Junior)",
                    "Tech (ATS-optimized)",
                ]
            )
            # Every bundled row has candidate_id=NULL (visible to all candidates)
            assert all(r.candidate_id is None for r in rows)
            paths = sorted(r.path for r in rows)
            assert paths == sorted(
                [
                    "personas/bundled/classic.docx",
                    "personas/bundled/modern.docx",
                    "personas/bundled/spacious.docx",
                    "personas/bundled/tech.docx",
                ]
            )
            session.close()
        finally:
            engine.dispose()

    def test_re_running_migration_is_idempotent(self, tmp_path):
        from db.models import PersonaTemplate
        from db.session import init_db, make_engine, make_session_factory

        db_file = tmp_path / "idem_test.sqlite"
        init_db(db_file)
        init_db(db_file)  # second run should be no-op
        engine = make_engine(db_file)
        try:
            session = make_session_factory(engine)()
            count = session.query(PersonaTemplate).filter_by(source="bundled").count()
            assert count == 4
            session.close()
        finally:
            engine.dispose()

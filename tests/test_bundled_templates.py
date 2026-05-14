"""Smoke tests for the bundled persona templates (Phase C.1).

Verifies:
- All 5 bundled .docx files exist on disk
- Each is readable as a .docx and round-trips through parser.parse_resume
- The PRESETS list in the build script and the BUNDLED_SEED_ROWS in the
  migration agree on the canonical set (so adding a new preset requires
  updating both)
- A fresh DB migration seeds exactly 5 bundled rows
- Re-running migrations is idempotent (the seed doesn't double-insert)
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_DIR = REPO_ROOT / "personas" / "bundled"
EXPECTED_FILES = [
    "classic.docx",
    "modern.docx",
    "compact.docx",
    "spacious.docx",
    "hybrid_tech.docx",
]


class TestBundledFiles:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_each_template_file_exists(self, filename):
        path = BUNDLED_DIR / filename
        assert path.exists(), f"Missing bundled template: {path}"
        # Sanity-check file size — empty / corrupt files have a known small footprint
        assert path.stat().st_size > 5000, f"{filename} suspiciously small ({path.stat().st_size} bytes)"

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


class TestPresetMigrationConsistency:
    """The PRESETS list (build script) and BUNDLED_SEED_ROWS (migration) must
    stay aligned. Adding a new preset to one without the other is a
    silent-bug class — this test makes it loud."""

    def test_preset_filenames_match_migration_paths(self):
        """Filename leading-with-a-digit means we can't normal-import the
        migration module. Load it via importlib + path."""
        import importlib.util

        from scripts.build_bundled_templates import PRESETS

        migration_path = REPO_ROOT / "db" / "migrations" / "versions" / "0002_seed_bundled_templates.py"
        spec = importlib.util.spec_from_file_location("seed_migration", migration_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        preset_filenames = {p.filename for p in PRESETS}
        seed_filenames = {Path(row["path"]).name for row in module.BUNDLED_SEED_ROWS}
        assert preset_filenames == seed_filenames, (
            f"PRESETS ({preset_filenames}) and BUNDLED_SEED_ROWS "
            f"({seed_filenames}) disagree"
        )


class TestSeedMigration:
    def test_fresh_migration_seeds_5_bundled_rows(self, tmp_path):
        from db.models import PersonaTemplate
        from db.session import init_db, make_engine, make_session_factory

        db_file = tmp_path / "seed_test.sqlite"
        init_db(db_file)
        engine = make_engine(db_file)
        try:
            session = make_session_factory(engine)()
            rows = session.query(PersonaTemplate).filter_by(source="bundled").all()
            assert len(rows) == 5
            names = sorted(r.name for r in rows)
            assert names == sorted([
                "Classic Single-Column",
                "Compact (Senior)",
                "Hybrid Tech",
                "Modern Single-Column",
                "Spacious (Career Changer / Junior)",
            ])
            # Every bundled row has candidate_id=NULL (visible to all candidates)
            assert all(r.candidate_id is None for r in rows)
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
            assert count == 5  # not 10
            session.close()
        finally:
            engine.dispose()

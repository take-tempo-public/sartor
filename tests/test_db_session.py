"""Pragmas + init_db idempotency tests."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from db.session import init_db, make_engine


class TestPragmas:
    def test_fk_enforcement_engaged_on_file_db(self, tmp_path: Path) -> None:
        db_file = tmp_path / "p.sqlite"
        engine = make_engine(db_file)
        try:
            with engine.connect() as conn:
                assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        finally:
            engine.dispose()

    def test_wal_journal_engaged_on_file_db(self, tmp_path: Path) -> None:
        db_file = tmp_path / "p.sqlite"
        engine = make_engine(db_file)
        try:
            with engine.connect() as conn:
                # WAL is the engaged journal mode for file-backed SQLite.
                assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        finally:
            engine.dispose()

    def test_synchronous_is_normal(self, tmp_path: Path) -> None:
        db_file = tmp_path / "p.sqlite"
        engine = make_engine(db_file)
        try:
            with engine.connect() as conn:
                # PRAGMA synchronous returns the integer code: 1 = NORMAL.
                assert conn.execute(text("PRAGMA synchronous")).scalar() == 1
        finally:
            engine.dispose()


class TestInitDb:
    def test_first_call_returns_fresh_true(self, tmp_path: Path) -> None:
        db_file = tmp_path / "fresh.sqlite"
        assert init_db(db_file) is True
        assert db_file.exists()

    def test_second_call_returns_fresh_false(self, tmp_path: Path) -> None:
        db_file = tmp_path / "twice.sqlite"
        init_db(db_file)
        assert init_db(db_file) is False

    def test_creates_all_tables(self, tmp_path: Path) -> None:
        db_file = tmp_path / "schema.sqlite"
        init_db(db_file)
        engine = make_engine(db_file)
        try:
            with engine.connect() as conn:
                n = conn.execute(
                    text("SELECT count(*) FROM sqlite_master WHERE type='table'")
                ).scalar()
                # 30 model tables + 1 alembic_version tracking table.
                # β.6a added summary_item + summary_item_tag; B.4 (Sprint 6.6)
                # added experience_summary_item + experience_summary_item_tag;
                # B.5 (Sprint 6.6) added skill_tag; fix/corpus-import-and-curation-ux
                # added merge_dismissal.
                assert n == 31
        finally:
            engine.dispose()

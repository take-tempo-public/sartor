"""Regression coverage for the 0006/0007 CHECK-constraint data-safety fix.

`application` is a CASCADE parent of `application_run`. Before this fix,
migrations 0006 and 0007 swapped `application`'s status CHECK constraint via
``batch_alter_table("application", recreate="always")`` — a full table
rebuild that, under the app's own `PRAGMA foreign_keys=ON` connect-time
default, silently cascade-deleted every `application_run` row (and its own
children) belonging to any application on a DB that already had run history.

These tests reproduce that scenario end-to-end (build a pre-0006 schema, seed
an application + a run + a run child, upgrade to head) and assert the fix:
children survive, the chain still reaches head, and the final CHECK
constraint matches the tightened set. A second pair of tests pins the "chain
stays valid" guarantee for the other two DB shapes the task cares about:
a brand-new empty DB, and a DB that's already at head (no-op re-run).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from db.migrations._sqlite_check_constraint import rewrite_check_constraint
from db.models import Base
from db.session import make_engine, make_session_factory

_REPO_ROOT = Path(__file__).resolve().parent.parent

# The exact pre-0006 CREATE TABLE text for `application` — narrower column
# set (no sent_at/outcome_at/notes/is_active) and the original 5-value CHECK
# with 'closed' instead of 'withdrawn'+outcome values. Mirrors migration
# 0006's own documented downgrade() target, which is the authoritative record
# of what a real pre-0006 DB's schema looked like.
_PRE_0006_APPLICATION_DDL = """
CREATE TABLE application (
    id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    company VARCHAR,
    jd_text TEXT NOT NULL,
    jd_url VARCHAR,
    jd_fingerprint VARCHAR NOT NULL,
    target_role_tag_id INTEGER,
    status VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_application_status CHECK (status IN ('draft', 'submitted', 'interview', 'closed', 'withdrawn')),
    FOREIGN KEY(candidate_id) REFERENCES candidate (id) ON DELETE CASCADE,
    FOREIGN KEY(target_role_tag_id) REFERENCES tag (id) ON DELETE SET NULL
)
"""


def _alembic_config(db_path: Path) -> Config:
    cfg = Config(str(_REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


def _build_pre_0006_db(db_path: Path) -> None:
    """Build a DB shaped like it's sitting at head-of-0005: every table in its
    CURRENT (final) shape via ``create_all``, except `application`, which is
    replaced with the historical pre-0006 narrower shape above. Then stamp
    `alembic_version` at 0005 so `command.upgrade(cfg, "head")` runs 0006
    onward for real against it.
    """
    engine = make_engine(db_path)
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE application"))
            conn.execute(text(_PRE_0006_APPLICATION_DDL))
    finally:
        engine.dispose()
    command.stamp(_alembic_config(db_path), "0005")


def _seed_application_with_run(db_path: Path) -> dict[str, int]:
    """Seed one candidate + one pre-0006-shaped application ('closed' status)
    + one application_run + one run child (iteration_log). Returns the ids.
    """
    from db.models import ApplicationRun, Candidate, IterationLog

    engine = make_engine(db_path)
    try:
        Session = make_session_factory(engine)
        session = Session()
        try:
            candidate = Candidate(username="pre0006user")
            session.add(candidate)
            session.flush()

            application_id = session.execute(
                text(
                    "INSERT INTO application "
                    "(candidate_id, title, jd_text, jd_fingerprint, status, "
                    "created_at, updated_at) VALUES (:cid, 't', 'jd', 'fp', 'closed', "
                    "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z') "
                    "RETURNING id"
                ),
                {"cid": candidate.id},
            ).scalar_one()

            run = ApplicationRun(
                application_id=application_id,
                iteration=0,
                run_id="abc123def456",
                prompt_version="test",
                corpus_snapshot_json="{}",
            )
            session.add(run)
            session.flush()

            child = IterationLog(
                application_run_id=run.id,
                action="generate",
                summary="initial generation",
            )
            session.add(child)
            session.commit()
            return {
                "candidate_id": candidate.id,
                "application_id": application_id,
                "run_id": run.id,
                "iteration_log_id": child.id,
            }
        finally:
            session.close()
    finally:
        engine.dispose()


class TestRewriteCheckConstraint:
    """Focused unit coverage of the batch-free CHECK-constraint rewrite."""

    def _make_parent_child_db(self, db_path: Path) -> None:
        con = sqlite3.connect(str(db_path), isolation_level=None)
        try:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute(
                "CREATE TABLE parent (id INTEGER PRIMARY KEY, "
                "status TEXT NOT NULL CHECK (status IN ('a', 'b')))"
            )
            con.execute(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, "
                "parent_id INTEGER REFERENCES parent(id) ON DELETE CASCADE)"
            )
            con.execute("INSERT INTO parent VALUES (1, 'a')")
            con.execute("INSERT INTO child VALUES (1, 1)")
        finally:
            con.close()

    def test_rewrite_widens_constraint_without_dropping_parent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "rw.sqlite"
        self._make_parent_child_db(db_path)
        engine = make_engine(db_path)
        try:
            with engine.begin() as conn:
                changed = rewrite_check_constraint(
                    conn,
                    "parent",
                    "status IN ('a', 'b')",
                    "status IN ('a', 'b', 'c')",
                )
                assert changed is True
                # New value now accepted, in the SAME transaction.
                conn.execute(text("INSERT INTO parent VALUES (2, 'c')"))
                # Old value still accepted too (never blocked, only widened).
                conn.execute(text("INSERT INTO parent VALUES (3, 'a')"))
                # Child untouched — no DROP TABLE was ever issued.
                assert conn.execute(text("SELECT count(*) FROM child")).scalar() == 1
            with engine.connect() as conn:
                assert conn.execute(text("SELECT count(*) FROM child")).scalar() == 1
                assert conn.execute(text("SELECT count(*) FROM parent")).scalar() == 3
                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        finally:
            engine.dispose()

    def test_rejects_value_outside_new_constraint(self, tmp_path: Path) -> None:
        db_path = tmp_path / "rw2.sqlite"
        self._make_parent_child_db(db_path)
        engine = make_engine(db_path)
        try:
            with engine.begin() as conn:
                rewrite_check_constraint(
                    conn, "parent", "status IN ('a', 'b')", "status IN ('a', 'b', 'c')"
                )
            with engine.begin() as conn, pytest.raises(Exception, match="CHECK constraint"):
                conn.execute(text("INSERT INTO parent VALUES (4, 'z')"))
        finally:
            engine.dispose()

    def test_noop_when_old_clause_not_present(self, tmp_path: Path) -> None:
        db_path = tmp_path / "rw3.sqlite"
        self._make_parent_child_db(db_path)
        engine = make_engine(db_path)
        try:
            with engine.begin() as conn:
                changed = rewrite_check_constraint(
                    conn, "parent", "status IN ('x', 'y')", "status IN ('x', 'y', 'z')"
                )
                assert changed is False
        finally:
            engine.dispose()

    def test_noop_when_table_missing(self, tmp_path: Path) -> None:
        db_path = tmp_path / "rw4.sqlite"
        self._make_parent_child_db(db_path)
        engine = make_engine(db_path)
        try:
            with engine.begin() as conn:
                changed = rewrite_check_constraint(
                    conn, "nonexistent", "status IN ('a', 'b')", "status IN ('a', 'b', 'c')"
                )
                assert changed is False
        finally:
            engine.dispose()


class TestMigrationChainDataSafety:
    """Reproduces the investigator's scenario end-to-end via the real alembic chain."""

    def test_upgrade_from_pre_0006_preserves_application_run_and_child(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "pre0006.sqlite"
        _build_pre_0006_db(db_path)
        ids = _seed_application_with_run(db_path)

        # The actual regression: this must succeed AND preserve the seeded
        # application_run + its iteration_log child.
        command.upgrade(_alembic_config(db_path), "head")

        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM application_run WHERE id=:id"),
                        {"id": ids["run_id"]},
                    ).scalar()
                    == 1
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM iteration_log WHERE id=:id"),
                        {"id": ids["iteration_log_id"]},
                    ).scalar()
                    == 1
                )
                # closed -> withdrawn backfill (0006) landed.
                status = conn.execute(
                    text("SELECT status FROM application WHERE id=:id"),
                    {"id": ids["application_id"]},
                ).scalar_one()
                assert status == "withdrawn"

                # New columns + the final tightened CHECK constraint landed.
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(application)"))}
                assert {"sent_at", "outcome_at", "notes", "is_active"} <= cols

                schema_sql = conn.execute(
                    text("SELECT sql FROM sqlite_master WHERE type='table' AND name='application'")
                ).scalar_one()
                assert (
                    "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')"
                    in schema_sql
                )
                assert "closed" not in schema_sql
                assert "no_response" not in schema_sql

                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
                assert list(conn.execute(text("PRAGMA foreign_key_check"))) == []
        finally:
            engine.dispose()

    def test_upgrade_from_pre_0006_with_offer_status_still_reaches_head(
        self, tmp_path: Path
    ) -> None:
        """A row sitting in one of the transient 0006-only statuses (here:
        'offer' would be invalid pre-0006, so this exercises the plain
        'closed' -> withdrawn path with NO run history at all) — a lighter
        sibling of the main test asserting the chain reaches head with an
        empty-history application too.
        """
        from db.models import Candidate

        db_path = tmp_path / "pre0006_no_runs.sqlite"
        _build_pre_0006_db(db_path)
        engine = make_engine(db_path)
        try:
            Session = make_session_factory(engine)
            session = Session()
            try:
                candidate = Candidate(username="norun")
                session.add(candidate)
                session.flush()
                session.execute(
                    text(
                        "INSERT INTO application (candidate_id, title, jd_text, "
                        "jd_fingerprint, status, created_at, updated_at) VALUES "
                        "(:cid, 't', 'jd', 'fp2', 'draft', "
                        "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
                    ),
                    {"cid": candidate.id},
                )
                session.commit()
            finally:
                session.close()
        finally:
            engine.dispose()

        command.upgrade(_alembic_config(db_path), "head")

        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        finally:
            engine.dispose()


class TestMigrationChainStaysValid:
    """The two DB shapes the task explicitly calls out alongside the fix."""

    def test_fresh_empty_db_reaches_head(self, tmp_path: Path) -> None:
        db_path = tmp_path / "fresh.sqlite"
        command.upgrade(_alembic_config(db_path), "head")
        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(application)"))}
                assert {"sent_at", "outcome_at", "notes", "is_active"} <= cols
                schema_sql = conn.execute(
                    text("SELECT sql FROM sqlite_master WHERE type='table' AND name='application'")
                ).scalar_one()
                assert (
                    "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')"
                    in schema_sql
                )
        finally:
            engine.dispose()

    def test_already_at_head_upgrade_is_a_noop(self, tmp_path: Path) -> None:
        db_path = tmp_path / "athead.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "head")
        # Re-running against an already-at-head DB must not raise or change
        # anything (both 0006's and 0007's guards should short-circuit).
        command.upgrade(cfg, "head")
        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        finally:
            engine.dispose()


def _application_index_columns(conn: object, index_name: str) -> list[str]:
    """Column names of a sqlite index, in index-key order (PRAGMA index_info)."""
    rows = conn.execute(text(f"PRAGMA index_info('{index_name}')")).fetchall()  # type: ignore[attr-defined]
    return [row[2] for row in sorted(rows, key=lambda r: r[0])]


def _seed_current_shape_application_with_run(db_path: Path) -> dict[str, int]:
    """Seed one candidate + one CURRENT-shape application (valid 0014+ status,
    default is_active) + one application_run + one run child. Unlike
    `_seed_application_with_run` above (which deliberately inserts the
    pre-0006 'closed' status via raw SQL to match that historical DDL), this
    helper targets a DB already at/after 0014 — the CHECK constraint no
    longer accepts 'closed', so this uses the ORM with a valid status.
    """
    from db.models import Application, ApplicationRun, Candidate, IterationLog

    engine = make_engine(db_path)
    try:
        Session = make_session_factory(engine)
        session = Session()
        try:
            candidate = Candidate(username="idx0015user")
            session.add(candidate)
            session.flush()

            application = Application(
                candidate_id=candidate.id,
                title="t",
                jd_text="jd",
                jd_fingerprint="fp",
                status="draft",
            )
            session.add(application)
            session.flush()

            run = ApplicationRun(
                application_id=application.id,
                iteration=0,
                run_id="idx0015run01",
                prompt_version="test",
                corpus_snapshot_json="{}",
            )
            session.add(run)
            session.flush()

            child = IterationLog(
                application_run_id=run.id,
                action="generate",
                summary="initial generation",
            )
            session.add(child)
            session.commit()
            return {
                "candidate_id": candidate.id,
                "application_id": application.id,
                "run_id": run.id,
                "iteration_log_id": child.id,
            }
        finally:
            session.close()
    finally:
        engine.dispose()


class TestApplicationIndexAddIsActive:
    """PX-38 migration 0015: is_active added to ix_application_candidate_status_updated.

    Index rebuilds (op.create_index/op.drop_index) are metadata-only DDL in
    SQLite — no table copy, no row touch — unlike batch_alter_table, which
    would risk cascade-deleting application_run + its children (the same
    hazard test_migrations_data_safety.py's 0006/0007 tests guard). These
    tests confirm zero row loss upgrading 0014->0015 AND downgrading back,
    on a DB seeded with exactly that parent/child shape.
    """

    def test_upgrade_0014_to_head_adds_is_active_no_row_loss(self, tmp_path: Path) -> None:
        db_path = tmp_path / "up0015.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "0014")
        ids = _seed_current_shape_application_with_run(db_path)

        command.upgrade(cfg, "head")

        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM application_run WHERE id=:id"),
                        {"id": ids["run_id"]},
                    ).scalar()
                    == 1
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM iteration_log WHERE id=:id"),
                        {"id": ids["iteration_log_id"]},
                    ).scalar()
                    == 1
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM application WHERE id=:id"),
                        {"id": ids["application_id"]},
                    ).scalar()
                    == 1
                )
                cols = _application_index_columns(conn, "ix_application_candidate_status_updated")
                assert cols == ["candidate_id", "is_active", "status", "updated_at"]
                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
                assert list(conn.execute(text("PRAGMA foreign_key_check"))) == []
        finally:
            engine.dispose()

    def test_downgrade_head_to_0014_restores_original_index_no_row_loss(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "down0015.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "head")
        ids = _seed_current_shape_application_with_run(db_path)

        command.downgrade(cfg, "0014")

        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM application_run WHERE id=:id"),
                        {"id": ids["run_id"]},
                    ).scalar()
                    == 1
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM iteration_log WHERE id=:id"),
                        {"id": ids["iteration_log_id"]},
                    ).scalar()
                    == 1
                )
                assert (
                    conn.execute(
                        text("SELECT count(*) FROM application WHERE id=:id"),
                        {"id": ids["application_id"]},
                    ).scalar()
                    == 1
                )
                cols = _application_index_columns(conn, "ix_application_candidate_status_updated")
                assert cols == ["candidate_id", "status", "updated_at"]
                assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
                assert list(conn.execute(text("PRAGMA foreign_key_check"))) == []
            # And back upgrade to head again re-adds is_active cleanly (chain
            # stays valid both directions, repeatedly).
            command.upgrade(cfg, "head")
            with engine.connect() as conn:
                cols = _application_index_columns(conn, "ix_application_candidate_status_updated")
                assert cols == ["candidate_id", "is_active", "status", "updated_at"]
        finally:
            engine.dispose()


def _seed_experience_tree(db_path: Path) -> dict[str, int]:
    """Seed one candidate + one experience with a title, a bullet, and a summary item.

    Exactly the parent/child shape migration 0016 must not disturb: `experience`
    is the CASCADE parent of all three child tables, so a `batch_alter_table`
    recreate would wipe them under the app's `PRAGMA foreign_keys=ON`.
    """
    from db.models import (
        Bullet,
        Candidate,
        Experience,
        ExperienceSummaryItem,
        ExperienceTitle,
    )

    engine = make_engine(db_path)
    try:
        Session = make_session_factory(engine)
        session = Session()
        try:
            candidate = Candidate(username="exp0016user")
            session.add(candidate)
            session.flush()

            experience = Experience(
                candidate_id=candidate.id,
                company="Acme",
                start_date="2020-01",
                display_order=0,
            )
            session.add(experience)
            session.flush()

            title = ExperienceTitle(
                experience_id=experience.id,
                title="Staff Engineer",
                is_official=1,
                truthful_enough_to_use=1,
                is_pending_review=0,
                is_active=1,
                source="official",
            )
            bullet = Bullet(
                experience_id=experience.id,
                text="Shipped the thing.",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="manual",
                has_outcome=0,
            )
            summary_item = ExperienceSummaryItem(
                experience_id=experience.id,
                text="Owned platform scale.",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="imported",
                has_outcome=0,
            )
            session.add_all([title, bullet, summary_item])
            session.commit()
            return {
                "candidate_id": candidate.id,
                "experience_id": experience.id,
                "title_id": title.id,
                "bullet_id": bullet.id,
                "summary_item_id": summary_item.id,
            }
        finally:
            session.close()
    finally:
        engine.dispose()


def _assert_experience_tree_intact(db_path: Path, ids: dict[str, int]) -> None:
    engine = make_engine(db_path)
    try:
        with engine.connect() as conn:
            for table, key in (
                ("experience", "experience_id"),
                ("experience_title", "title_id"),
                ("bullet", "bullet_id"),
                ("experience_summary_item", "summary_item_id"),
            ):
                assert (
                    conn.execute(
                        text(f"SELECT count(*) FROM {table} WHERE id=:id"),  # noqa: S608
                        {"id": ids[key]},
                    ).scalar()
                    == 1
                ), f"{table} row lost"
            assert conn.execute(text("PRAGMA integrity_check")).scalar() == "ok"
            assert list(conn.execute(text("PRAGMA foreign_key_check"))) == []
    finally:
        engine.dispose()


class TestExperienceIsActive:
    """Migration 0016: experience.is_active, added with a NATIVE ADD COLUMN.

    `experience` is the CASCADE parent of experience_title, bullet AND
    experience_summary_item — one more child table than the 0011 case this
    revision copies. A `batch_alter_table` recreate would cascade-delete all
    three while FK enforcement is on; a native ADD/DROP COLUMN touches no rows.
    These tests assert exactly that, in both directions.
    """

    def test_upgrade_0015_to_head_adds_is_active_no_row_loss(self, tmp_path: Path) -> None:
        db_path = tmp_path / "up0016.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "0015")
        ids = _seed_experience_tree(db_path)

        command.upgrade(cfg, "head")

        _assert_experience_tree_intact(db_path, ids)
        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(experience)"))}
                assert "is_active" in cols
                # No backfill: every pre-existing row comes up LIVE. Inferring
                # retirement from "has no active bullets" would hide live roles.
                assert (
                    conn.execute(
                        text("SELECT is_active FROM experience WHERE id=:id"),
                        {"id": ids["experience_id"]},
                    ).scalar()
                    == 1
                )
        finally:
            engine.dispose()

    def test_downgrade_head_to_0015_drops_is_active_no_row_loss(self, tmp_path: Path) -> None:
        db_path = tmp_path / "down0016.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "head")
        ids = _seed_experience_tree(db_path)

        command.downgrade(cfg, "0015")

        _assert_experience_tree_intact(db_path, ids)
        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(experience)"))}
                assert "is_active" not in cols
            # Chain stays valid both directions, repeatedly.
            command.upgrade(cfg, "head")
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(experience)"))}
                assert "is_active" in cols
        finally:
            engine.dispose()
        _assert_experience_tree_intact(db_path, ids)

    def test_fresh_empty_db_has_experience_is_active(self, tmp_path: Path) -> None:
        """0001 is Base.metadata.create_all, so a fresh clone already has the
        column and 0016's PRAGMA guard must skip the ALTER rather than raise."""
        db_path = tmp_path / "fresh0016.sqlite"
        command.upgrade(_alembic_config(db_path), "head")
        engine = make_engine(db_path)
        try:
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(experience)"))}
                assert "is_active" in cols
        finally:
            engine.dispose()

    def test_already_at_head_upgrade_is_a_noop(self, tmp_path: Path) -> None:
        db_path = tmp_path / "athead0016.sqlite"
        cfg = _alembic_config(db_path)
        command.upgrade(cfg, "head")
        ids = _seed_experience_tree(db_path)
        command.upgrade(cfg, "head")  # guard must short-circuit
        _assert_experience_tree_intact(db_path, ids)

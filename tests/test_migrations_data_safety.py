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

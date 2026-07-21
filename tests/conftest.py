"""Shared pytest fixtures."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make project root importable so tests can `import hardening`, `import app`, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def _migrated_template_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A file-backed SQLite migrated to alembic head, built exactly ONCE per session.

    `test/fixture-scoping` (PX-44) pilot: ~46 non-UX test files each ran the full
    15-revision alembic chain via `db.session.init_db()` at FUNCTION scope — the
    single largest mechanical cost in the fast lane (`docs/dev/perf/
    TEST_SUITE_PERFORMANCE.md`). This fixture pays that cost once; per-test fixtures
    (e.g. `dup_app`, `memory_app`) copy the resulting file instead of re-migrating.

    Two traps this fixture must close, both found by reading `db/session.py`
    directly rather than assumed from `init_db`'s docstring:

    1. `init_db` memoizes on a path SET (`_initialized_paths`), not on DB state —
       it never inspects `alembic_version`. A copy of this template is therefore
       NOT auto-recognized as "already migrated"; callers must pre-register the
       copy's resolved path before the first request, or the first route that
       calls bare `init_db()` re-runs the whole chain against the copy.
    2. Every connection runs `PRAGMA journal_mode = WAL` (`db/session.py:56`), so
       the bundled-template seed rows migration 0002 inserts (and 0005 curates
       down to 4) can still be sitting in `template.sqlite-wal` when migration
       finishes. A `shutil.copy2` of only the main file would silently produce a
       schema-complete but seed-EMPTY copy. Checkpointing before the first copy
       (below) closes this.
    """
    from db.models import PersonaTemplate
    from db.session import init_db, make_engine, make_session_factory

    template = tmp_path_factory.mktemp("dbtemplate") / "template.sqlite"
    was_fresh = init_db(template)
    assert was_fresh, "template DB must be freshly migrated, not reused across sessions"

    engine = make_engine(template)
    try:
        with engine.connect() as conn:
            # Flush WAL contents into the main file so a later `shutil.copy2` of
            # just `template.sqlite` (no `-wal`/`-shm` sidecars) carries every row.
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        session = make_session_factory(engine)()
        try:
            bundled_count = session.query(PersonaTemplate).filter_by(source="bundled").count()
            # 5 seeded by migration 0002, 1 dropped by migration 0005's curation
            # pass — 4 is the head-state invariant, asserted here so a schema-only
            # (seed-empty) template fails loudly at session start, not silently in
            # whichever pilot test happens to touch persona templates first.
            assert bundled_count == 4, (
                f"expected 4 bundled persona_template rows at alembic head, "
                f"got {bundled_count} — template DB may be seed-empty (WAL not "
                f"checkpointed) or migrations 0002/0005 have drifted"
            )
        finally:
            session.close()
    finally:
        engine.dispose()

    return template


@pytest.fixture()
def app(tmp_path):
    """The canonical factory-built app (Sprint 8.3a).

    Replaces the `import app as app_module; monkeypatch.setattr(app_module,
    "CONFIGS_DIR", tmp); app_module.app.test_client()` pattern: build a fresh app
    whose injected `Config` points every path at `tmp_path`, no module globals
    touched. NOTE: a freshly-built `create_app(...)` carries the blueprints
    (assistant + dashboard) but NOT the 93 module-level `@app.route` handlers —
    those decorate the import-time `app` only. Seam tests migrate onto this fixture
    as their routes move onto factory-registered blueprints (8.3b-h).
    """
    from app import create_app
    from config import Config

    return create_app(Config(base_dir=tmp_path))


@pytest.fixture()
def client(app):
    """A test client for the canonical factory-built `app` fixture."""
    return app.test_client()


@pytest.fixture()
def db_session() -> Iterator:
    """Yield an in-memory SQLite session with the full schema created.

    Engine is disposed at fixture teardown to release the connection so
    Windows doesn't hold the file handle (matters for file-backed test DBs,
    harmless for :memory:).
    """
    from db.models import Base
    from db.session import make_engine, make_session_factory

    engine = make_engine(":memory:")
    Base.metadata.create_all(engine)
    SessionLocal = make_session_factory(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

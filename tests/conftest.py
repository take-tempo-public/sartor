"""Shared pytest fixtures."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make project root importable so tests can `import hardening`, `import app`, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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

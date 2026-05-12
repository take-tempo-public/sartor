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

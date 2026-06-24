"""Engine, session factory, and pragmas for the SQLite-backed corpus.

Pragmas every connection: `foreign_keys=ON`, `journal_mode=WAL`. WAL improves
concurrent read performance and is the right default for a local single-user
app. FK enforcement is OFF by default in SQLite (yes, really) so we turn it
on at connect time.

DB file lives at `db/resume.sqlite` under the project root (per plan; user
decision recorded 2026-05-12). Gitignored. A new clone gets a fresh empty DB
on first launch via alembic upgrade head.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Resolve repo-root relative path so `python app.py` and `pytest` see the same DB.
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = _REPO_ROOT / "db" / "resume.sqlite"


def _db_url(db_path: Path | str | None = None) -> str:
    """Return the SQLAlchemy URL for the given path (or the default)."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    # `:memory:` is special-cased for tests.
    if str(db_path) == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{Path(db_path).as_posix()}"


# _set_sqlite_pragmas is a SQLAlchemy connect-event listener: its dbapi_connection /
# _connection_record args are raw DBAPI / pool objects, dynamically typed (Any) at the
# pool boundary by design — hence the targeted ANN401 suppression (Decision-7 spirit:
# type what's typeable, suppress only the genuinely dynamic boundary).
@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:  # noqa: ANN401
    """Turn on FK enforcement and WAL on every new connection.

    SQLite defaults: foreign_keys=OFF, journal_mode=DELETE. Both are the wrong
    default for our use case. We engage these at connect-time rather than per
    session so they cover every code path (alembic migrations included).

    The check on `cursor.execute` return type works around the fact that some
    PRAGMA statements (journal_mode) return a row while others don't.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")  # safe with WAL; faster than FULL
    finally:
        cursor.close()


def make_engine(db_path: Path | str | None = None, *, echo: bool = False) -> Engine:
    """Build an engine pointing at the given DB file.

    `echo=True` logs SQL — useful in tests but never in production.
    Connection pooling is irrelevant for a single-user SQLite app; we use the
    default StaticPool for in-memory and the default pool for file DBs.
    """
    return create_engine(_db_url(db_path), echo=echo, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a sessionmaker bound to the given engine. Tests reuse this."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


# ---------------------------------------------------------------------------
# Module-level default engine + session factory (lazy-initialized)
# ---------------------------------------------------------------------------

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it lazily on first call."""
    global _engine
    if _engine is None:
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = make_engine(DEFAULT_DB_PATH)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = make_session_factory(get_engine())
    return _SessionLocal


def get_session() -> Session:
    """Open a new session. Callers are responsible for closing / committing."""
    return get_session_factory()()


_initialized_paths: set[Path] = set()
_init_lock = threading.Lock()


def init_db(db_path: Path | str | None = None) -> bool:
    """Run alembic migrations to head against the given DB.

    Returns True if the DB was freshly created (caller should kick off any
    seed-data work like bundled-template insertion), False if it was already
    at head OR was previously initialized in this process. Idempotent — safe
    to call repeatedly; alembic only runs on the FIRST call per (process,
    db_path) pair.

    Per-process cache rationale (2026-05-26): alembic's
    `command.upgrade()` mutates module-level globals via
    `EnvironmentContext.__enter__/__exit__`. Repeated invocations in the
    same Python process can leave the globals in a state where
    `_remove_proxy()`'s `del globals_[attr_name]` raises KeyError on the
    next run (observed: `KeyError: 'script'` and `KeyError: 'config'`
    cascading from corpus + templates routes). Flask's threaded dev
    server amplifies this because every request that touches the DB
    calls init_db(). Caching by resolved db_path ensures alembic runs
    once per DB the process ever sees — tests passing a fresh tmp_path
    each get their own first run; the runtime app pays the cost on
    first request and skips afterwards.

    Called from `app.py` on first launch per the plan's auto-migrate
    decision, plus defensively from each route that opens a session.
    """
    from alembic import command
    from alembic.config import Config

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    resolved = Path(db_path).resolve()
    with _init_lock:
        if resolved in _initialized_paths:
            # Already migrated in this process — alembic is at head; skip.
            # Returning False matches the "DB already at head" semantics
            # callers expect (no bundled-seed work needed).
            return False

        was_fresh = not resolved.exists()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        cfg = Config(str(_REPO_ROOT / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", _db_url(resolved))
        command.upgrade(cfg, "head")
        _initialized_paths.add(resolved)
    return was_fresh


__all__ = [
    "DEFAULT_DB_PATH",
    "get_engine",
    "get_session",
    "get_session_factory",
    "init_db",
    "make_engine",
    "make_session_factory",
]

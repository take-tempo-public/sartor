"""Shared pytest fixtures."""

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make project root importable so tests can `import hardening`, `import app`, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _default_llm_log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect `analyzer.LOG_PATH` to a per-test tmp file by default, for every
    test in the suite.

    Item 33: 9 fake-client tests in `test_extract_experiences.py` drove the real
    `_call_llm_streaming` -> `_emit_call_log` funnel without redirecting anything,
    appending synthetic rows to the developer's real `logs/llm_calls.jsonl` on
    every run (measured at 71.1% of the entire real log). `_emit_call_log` reads
    `LOG_PATH` from the module's globals at call time, so redirecting it here is
    enough to close the gap for this file and any future one, without touching
    `_emit_call_log` itself — tests that need its real write behavior
    (`test_analyzer_model_selection.py`, `test_demo_mode.py`) apply their own
    `monkeypatch.setattr(analyzer, "LOG_PATH", ...)` afterward, which simply wins.
    """
    import analyzer

    monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path / "llm_calls.jsonl")


@pytest.fixture(autouse=True)
def _default_gate_result_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect `scripts.gate`'s result file to a per-test tmp file, for every test (item
    151; same shape as `_default_llm_log_path` above).

    `gate.main()` records every run in the checkout's real git dir, and `python -m scripts.gate
    --result` trusts that record. A test that calls `main()` would otherwise overwrite the
    developer's real record with a stubbed run (observed on `fix/hook-guard-false-blocks`:
    `test_gate_memory_preflight.py` wrote a `hooksPath preflight` failure into `.git/`).
    """
    from scripts import gate

    monkeypatch.setattr(gate, "_result_path", lambda: tmp_path / "gate-result.json")


@pytest.fixture(autouse=True)
def _isolated_witness_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the interrogative-witness state dir at a per-test tmp dir, for every
    test in the suite (work item 87; same shape as `_default_llm_log_path` above).

    Without this, the tests that run the `edit-write-dispatcher` hook as a real
    subprocess (`test_enforcement_core.py`) would read whatever witness state a
    live Claude session last left under the developer's OS temp dir — a
    `witnessed: false` leftover there would make the dispatcher's pause fire
    inside an unrelated test, exactly the cross-run temp-state leak item 33
    closed for `llm_calls.jsonl`. Subprocess hooks inherit the env var; in-process
    callers that want their own dir just pass an explicit `env=` (which wins).
    """
    from scripts.enforcement.guards import interrogative_witness

    monkeypatch.setenv(interrogative_witness.STATE_DIR_ENV, str(tmp_path / "witness-state"))


@pytest.fixture(autouse=True)
def _no_live_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a test inherit the live Claude session's `CLAUDE_CODE_SESSION_ID`.

    The ledger writers (`claude_context_hook.record_compaction`, the plan gate's
    `plan-archived` receipt) name their shard after it. Run inside a Claude session, a test
    that reaches one with this repo as its project appended a **fake** `compacted` event to
    the live session's tracked shard: twice on `fix/python-direct-hooks-plan-gate`, from
    `test_context_hooks_never_gate` (`docs/dev/diagnosis/python-direct-hooks-plan-gate.md`
    O7). A test that needs a session sets one explicitly.
    """
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)


@pytest.fixture(autouse=True)
def _isolated_plan_gate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the plan gate's state dir at a per-test tmp dir, pre-approved for THIS repo
    only (`fix/python-direct-hooks-plan-gate`; same shape as `_isolated_witness_state`).

    The `edit-write-dispatcher` hook runs the plan gate first. Without this, a test that runs
    the dispatcher with `CLAUDE_PROJECT_DIR` naming this repo would read, and could
    reconcile, the developer's live approval under `~/.claude/plans` (and on CI, where there
    is none, every allow case would hit NO EDIT APPROVAL). The empty marker approves edits
    for this repo's key, so guard tests see only the guard under test. Tests of the plan gate
    itself build their own state and drop this variable (`tests/test_plan_approval_scoping.py`).
    """
    from scripts.enforcement import plan_gate

    plans = tmp_path / "plan-gate-state"
    plans.mkdir()
    (plans / f".approved-{plan_gate.project_key(str(PROJECT_ROOT))}").write_text(
        "", encoding="utf-8"
    )
    monkeypatch.setenv(plan_gate.PLANS_DIR_ENV, str(plans))


_RUN_SLOT_DRAIN_TIMEOUT_S = 15.0


@pytest.fixture(autouse=True)
def _drain_diagnostics_run_slot() -> Iterator[None]:
    """After every test, wait for the diagnostics console's run slot to be free (item 117).

    `blueprints/diagnostics.py` holds one process-wide single-flight slot that a run's
    worker frees in its own `finally`. A test that returns while its worker is still
    unwinding (`TestRunCancelDisconnect` does, by design) would otherwise hand the next
    test a held slot, and its POST a 409: a flake made by construction. This WAITS for the
    real worker; it never resets the slot. A slot still held after the bound fails here,
    naming the test that leaked it, rather than in whichever test runs next.
    """
    yield
    diagnostics = sys.modules.get("blueprints.diagnostics")
    if diagnostics is None:
        return
    slot = diagnostics._RUN_SLOT
    if not slot.acquire(timeout=_RUN_SLOT_DRAIN_TIMEOUT_S):
        pytest.fail(
            f"diagnostics run slot still held {_RUN_SLOT_DRAIN_TIMEOUT_S:.0f}s after this test: "
            "a run worker never reached its finally (item 117)"
        )
    slot.release()


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


def _fresh_migrated_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _migrated_template_db: Path,
    *,
    filename: str = "test.sqlite",
) -> Path:
    """Copy the session-scoped migrated template into `tmp_path` and point
    `db.session` at it — the per-test half of the PX-44 rollout
    (`test/fixture-scoping-rollout`), factored out once the pilot's
    hand-duplicated 4-line dance (`dup_app`, `memory_app`) needed a 3rd+
    caller. See `_migrated_template_db`'s docstring for the two traps this
    closes (path-set memoization, WAL sidecar).

    Callers still do their own `create_app(...)` call and
    `assert init_db(db_file) is False` skip-proof right after — those vary
    per file (extra Config kwargs, extra seeding) so they stay inline
    rather than folded into this helper.
    """
    db_file = tmp_path / filename
    assert db_file != _migrated_template_db, "must never point a test at the shared template"
    shutil.copy2(_migrated_template_db, db_file)

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None
    # Mandatory pre-register: `init_db` only skips the alembic chain when the
    # resolved path is already in this set — it never inspects DB state, so
    # without this line the first route to call bare `init_db()` re-migrates
    # the copy from scratch, silently erasing the fixture's whole purpose.
    db_session_mod._initialized_paths.add(db_file.resolve())
    return db_file


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

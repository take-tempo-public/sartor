"""Playwright UX harness — fixtures shared by every `tests/ux/` test.

A real **threaded** Flask server on an ephemeral port (browser tests need a
real socket; `test_client()` won't do), backed by a temp SQLite + temp dirs
(mirrors the `app_app` fixture in `tests/test_application_routes.py`); a
session Chromium browser with a skip-guard when the binary is absent; and a
console-error **sentinel** on every page. LLM-free — flows stub the analyzer
functions (see `tests/ux/stubs.py`); regression tests seed the DB directly.
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Iterator
from types import ModuleType

import pytest
from playwright.sync_api import Browser, ConsoleMessage, Page, Response


@pytest.fixture
def ux_app(tmp_path, monkeypatch) -> ModuleType:
    """Reload app.py against a fresh temp DB + temp config/output dirs."""
    db_file = tmp_path / "ux.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import app as app_module

    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    # NB: BASE_DIR is left at the real repo root (unlike app_app) so persona
    # template paths (BASE_DIR / "personas/bundled/*.docx") resolve for the
    # Step-6 WYSIWYG preview. Isolation comes from the temp DB + OUTPUT_DIR +
    # CONFIGS_DIR; nothing in the wizard flow writes via BASE_DIR directly.
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()

    from db.session import init_db

    init_db(db_file)
    return app_module


@pytest.fixture
def live_server(ux_app: ModuleType) -> Iterator[str]:
    """Serve `ux_app.app` on 127.0.0.1:<ephemeral> in a daemon thread.

    `threaded=True` is load-bearing — the personas-500 regression needs
    genuine concurrent first-select, matching production's threaded dev
    server. A single-threaded server would let that test pass trivially.
    """
    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, ux_app.app, threaded=True)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def _browser() -> Iterator[Browser]:
    """Session Chromium. Skips the whole UX tier if the binary is missing,
    so the default `pytest` stays green where Chromium isn't installed."""
    from playwright.sync_api import sync_playwright

    try:
        pw = sync_playwright().start()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Playwright unavailable: {exc}")
    try:
        browser = pw.chromium.launch()
    except Exception as exc:  # pragma: no cover - environment guard
        pw.stop()
        pytest.skip(
            "Chromium not installed — run `python -m playwright install "
            f"chromium` ({exc})"
        )
    try:
        yield browser
    finally:
        browser.close()
        pw.stop()


# NB (2026-06-04, feat/template-pagination): the paged.js `getBoundingClientRect
# of null` allowlist that used to live here is GONE. The preview routes now drive
# paged.js manually (`PagedConfig.auto=false` + `Previewer().preview()` in
# try/catch + `.catch()` in app.py `_PAGED_PREVIEW_INJECTION`), so that cosmetic
# throw can no longer escape to the console. The sentinel is now unconditional —
# any paged.js console regression fails the suite.
@pytest.fixture
def page(_browser: Browser, live_server: str) -> Iterator[Page]:
    """A fresh page with the failure sentinel attached. Fails the test on
    teardown for the bug classes we care about — uncaught JS (`pageerror`),
    app-authored `console.error`, and any HTTP **5xx** (the precise
    personas-500 / cascade signal). It deliberately ignores benign
    resource-load 4xx noise (config not-yet-saved, preview-before-generate):
    those surface in the console as "Failed to load resource" but aren't
    bugs, and real server errors are caught precisely by the response
    listener instead. This still catches the silent corpus-render failure
    (a JS exception, not a 404)."""
    context = _browser.new_context(viewport={"width": 1440, "height": 900})
    pg = context.new_page()
    js_errors: list[str] = []
    server_errors: list[str] = []

    def _on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            js_errors.append(msg.text)

    def _on_response(resp: Response) -> None:
        if resp.status >= 500:
            server_errors.append(f"{resp.status} {resp.request.method} {resp.url}")

    pg.on("console", _on_console)
    pg.on("pageerror", lambda exc: js_errors.append(f"pageerror: {exc}"))
    pg.on("response", _on_response)
    pg._ux_console_errors = js_errors  # type: ignore[attr-defined]
    pg._ux_server_errors = server_errors  # type: ignore[attr-defined]

    try:
        yield pg
    finally:
        context.close()

    assert not js_errors, f"JS console errors during test: {js_errors}"
    assert not server_errors, f"HTTP 5xx during test: {server_errors}"


# Every help block that AUTO-fires on first view (the welcome + each KW3 tour
# stop). Seeding their ``cb_help_seen:<block>`` flags models a returning user so
# the auto-modals never overlay the landing/wizard and block other tests. Panels
# that only carry an on-demand (i) (panelAnalysis/panelApplications/panelPersonas/
# panelMemory) never auto-open, so they are intentionally absent here.
_TOUR_STOP_BLOCKS = (
    "panelUser",        # welcome
    "tourAddUser",      # add-user tip
    "panelCorpus",      # post-ingest
    "panelJD",          # wizard step 1
    "panelClarify",     # wizard step 2
    "panelCompose",     # wizard step 3
    "panelTemplate",    # wizard step 4
    "panelGenerate",    # wizard step 5
    "panelOutput",      # wizard step 6
    "tourGenerating",   # first Generate click
    "tourCoverLetter",  # first cover-letter
)


@pytest.fixture(autouse=True)
def _help_welcome_default_seen(request: pytest.FixtureRequest, page: Page) -> None:
    """Default every UX test to 'first-run help already seen'.

    The Sprint-6.5 help primitive auto-opens a welcome modal on first view and
    the education branch layers the KW3 new-user tour (one once-ever modal per
    milestone), each gated by a ``cb_help_seen:<block>`` localStorage flag. Each
    test gets a fresh browser context (empty localStorage), so without this an
    auto-modal's full-screen backdrop would block the interactions every other
    test performs right after ``load()``. Seeding every auto-firing block via an
    init-script (runs before each navigation) models the common case — a
    returning user. Tests opt back in: ``@pytest.mark.show_welcome`` for just the
    welcome, ``@pytest.mark.show_tour`` for the whole new-user sequence.
    """
    if request.node.get_closest_marker("show_tour"):
        return  # tour tests drive the genuine new-user sequence
    blocks = list(_TOUR_STOP_BLOCKS)
    if request.node.get_closest_marker("show_welcome"):
        blocks.remove("panelUser")  # welcome fires; the rest stay suppressed
    sets = "".join(
        f"window.localStorage.setItem('cb_help_seen:{b}', '1');" for b in blocks
    )
    page.add_init_script(
        f"try {{ {sets} }} catch (e) {{ /* storage unavailable — help may show */ }}"
    )


@pytest.fixture
def console_errors(page: Page) -> list[str]:
    """Live JS-error list for tests that assert on it explicitly."""
    return page._ux_console_errors  # type: ignore[attr-defined]


@pytest.fixture
def server_errors(page: Page) -> list[str]:
    """Live HTTP-5xx list for tests that assert on it explicitly (the 5b
    cascade test reads this to prove no /personas 500)."""
    return page._ux_server_errors  # type: ignore[attr-defined]

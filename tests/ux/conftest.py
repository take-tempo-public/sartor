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


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Print the failure of every RERUN attempt. Reruns must not be silent.

    `pytest -m ux --reruns 2` reports a test that fails twice and passes on the third
    attempt as a plain `PASSED`, with **no traceback anywhere in the log** — the failed
    attempts are discarded. That is precisely how a test failing 64% of its attempts
    stayed invisible for 11 CI runs while turning `main` red 26% of the time, and it
    also swallowed the diagnostic the `page` fixture prints on failure (captured output
    is only surfaced for tests that actually fail).

    `ci.yml`'s flake policy heads itself "HONEST, not masking" and says a real regression
    fails all three attempts — a criterion nobody can apply to evidence they never see.
    So: surface it. A rerun we never look at is a bug we never fix.
    """
    if report.outcome != "rerun":
        return
    print(f"\n[ux] RERUN — this attempt FAILED: {report.nodeid}")
    if report.longrepr is not None:
        print(report.longrepr)
    for title, content in report.sections:
        if content.strip():
            print(f"---- {title} ----\n{content}")


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
    # Every route reads its paths from `current_app.config` (the v1.0.8 app.py→
    # blueprints decomposition completed at Sprint 8.3h — app.py no longer carries
    # path globals to monkeypatch), so isolate the suite by injecting the temp keys
    # onto the live app's config. RESUMES_DIR: create_user does
    # `(current_app.config["RESUMES_DIR"] / safe).mkdir(...)`, so without it a new-user
    # UX flow would write into the real repo `resumes/`. ANNOTATION_ROOT: the
    # diagnostics Annotate tab (annotation/bootstrap/eval/tune routes) writes under it,
    # so point it at the temp tree too. BASE_DIR / PERSONAS_DIR / BUNDLED_PERSONAS_DIR
    # are deliberately left at the live (production) config's real repo root — exactly
    # what bundled-template / persona resolution needs for the Step-6 WYSIWYG preview;
    # nothing in the wizard flow writes via BASE_DIR directly.
    app_module.app.config["CONFIGS_DIR"] = tmp_path / "configs"
    app_module.app.config["OUTPUT_DIR"] = tmp_path / "output"
    app_module.app.config["RESUMES_DIR"] = tmp_path / "resumes"
    app_module.app.config["ANNOTATION_ROOT"] = tmp_path / "annotation"
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "resumes").mkdir()
    (tmp_path / "annotation").mkdir()

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
        pytest.skip(f"Chromium not installed — run `python -m playwright install chromium` ({exc})")
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
    api_errors: list[str] = []

    def _on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            js_errors.append(msg.text)

    def _on_response(resp: Response) -> None:
        if resp.status >= 500:
            server_errors.append(f"{resp.status} {resp.request.method} {resp.url}")
        elif resp.status >= 400 and "/api/" in resp.url:
            api_errors.append(f"{resp.status} {resp.request.method} {resp.url}")

    pg.on("console", _on_console)
    pg.on("pageerror", lambda exc: js_errors.append(f"pageerror: {exc}"))
    pg.on("response", _on_response)
    pg._ux_console_errors = js_errors  # type: ignore[attr-defined]
    pg._ux_server_errors = server_errors  # type: ignore[attr-defined]
    pg._ux_api_errors = api_errors  # type: ignore[attr-defined]

    try:
        yield pg
    finally:
        context.close()
        # 4xx-on-/api/ is DIAGNOSTIC, never an assertion: some are genuinely
        # benign (config not-yet-saved, preview-before-generate — the same noise
        # the sentinel above filters out of the console), so failing on them would
        # red-line honest tests. But a *swallowed* 4xx is exactly what hid the
        # settled-but-empty positioning draft for 11 CI runs: the route 400'd, the
        # client dropped it on the floor, and a 5xx-only sentinel looked straight
        # past it — leaving a bare "textarea is empty" with no cause attached.
        # Printing them here costs nothing on a green run (pytest discards captured
        # output) and hands the next failure in this class its own root cause.
        if api_errors:
            print("\n[ux] non-2xx /api/ responses observed during this test:")
            for line in api_errors:
                print(f"  {line}")

    assert not js_errors, f"JS console errors during test: {js_errors}"
    assert not server_errors, f"HTTP 5xx during test: {server_errors}"


# Every help block that AUTO-fires on first view (the welcome + each KW3 tour
# stop + each /_dashboard per-tab explainer). Seeding their ``cb_help_seen:<block>``
# flags models a returning user so the auto-modals never overlay the landing/wizard
# or the diagnostics console and block other tests. Panels that only carry an
# on-demand (i) (panelAnalysis/panelApplications/panelPersonas/panelMemory) never
# auto-open, so they are intentionally absent here. The dashboard explainers
# (``feat/education-diagnostics-annotate``) reuse the same ``cb_help_seen:`` prefix
# (their controller is a port of the wizard's), so the same init-script seeding
# suppresses them on the ``/_dashboard/`` navigation — but only because the ported
# ``_maybeFireDashHelp`` reads these exact ids before opening.
_TOUR_STOP_BLOCKS = (
    "panelUser",  # welcome
    "tourAddUser",  # add-user tip
    "tourCorpusLanding",  # F-06 post-create corpus-landing transition
    "panelCorpus",  # post-ingest
    "panelJD",  # wizard step 1
    "panelClarify",  # wizard step 2
    "panelCompose",  # wizard step 3
    "panelTemplate",  # wizard step 4
    "panelGenerate",  # wizard step 5
    "panelOutput",  # wizard step 6
    "tourGenerating",  # first Generate click
    "tourCoverLetter",  # first cover-letter
    "dashPipeline",  # /_dashboard Pipeline tab explainer (auto on first load)
    "dashQuality",  # /_dashboard Quality tab explainer
    "dashGroundedness",  # /_dashboard Groundedness tab explainer
    "dashTuning",  # /_dashboard Tuning tab explainer
    "dashAnnotate",  # /_dashboard Annotate tab explainer
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
    sets = "".join(f"window.localStorage.setItem('cb_help_seen:{b}', '1');" for b in blocks)
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


@pytest.fixture
def api_errors(page: Page) -> list[str]:
    """Live non-2xx `/api/` list for tests that assert on it explicitly.

    Not asserted by the `page` sentinel (some 4xx here are benign — see the note
    there); a test that knows a given flow must produce NO failed API call opts in
    by reading this and asserting it empty.
    """
    return page._ux_api_errors  # type: ignore[attr-defined]

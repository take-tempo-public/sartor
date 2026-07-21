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
import os
import sys
import threading
from collections.abc import Iterator
from types import ModuleType

import pytest
from playwright.sync_api import Browser, ConsoleMessage, Page, Response

from tests.ux.rerun_report import render_annotations, render_step_summary
from ui_pages.selectors import Help

# Per-nodeid count of "rerun" outcomes this session (module-level: pytest hooks are called
# against the module, not an instance, and this suite doesn't run under pytest-xdist, so a
# plain global is safe — no cross-process aggregation needed). Fed by `pytest_runtest_logreport`
# below, consumed by `pytest_terminal_summary`'s rerun-rate alarm at session end.
_rerun_counts: dict[str, int] = {}


def _safe_print(text: str) -> None:
    """`print(text)`, but never raises `UnicodeEncodeError`.

    `report.longrepr` and a rerun's captured `report.sections` (below) can contain ANY text a
    test — or the app/browser it drives — produced, including characters a console's active code
    page can't represent. Reproduced directly (`feat/rerun-rate-alarm`, 2026-07-21): a forced
    rerun whose captured section happened to contain "β" raised `UnicodeEncodeError` on a Windows
    console still on the legacy `cp1252` code page, which pytest turned into a session-ending
    `INTERNALERROR` — losing the rerun report entirely, the opposite of this hook's whole purpose.
    Falls back to the stream's own encoding with unencodable characters backslash-escaped rather
    than losing the report over one character pytest's own capture happened to produce.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="backslashreplace") + b"\n")
        sys.stdout.flush()


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
    _rerun_counts[report.nodeid] = _rerun_counts.get(report.nodeid, 0) + 1
    _safe_print(f"\n[ux] RERUN — this attempt FAILED: {report.nodeid}")
    if report.longrepr is not None:
        _safe_print(str(report.longrepr))
    for title, content in report.sections:
        if content.strip():
            _safe_print(f"---- {title} ----\n{content}")


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    """Rerun-rate alarm (RELEASE_CHECKLIST carry-forward ledger item 1, option (a),
    decided 2026-07-20 on `docs/scroll-flake-ci-data-rerun-policy`): every test this
    session needed a retry for gets reported — a `$GITHUB_STEP_SUMMARY` table plus one
    `::warning::` checks-UI annotation each — so an absorbed-but-chronic failure can't
    hide behind a green `PASSED` the way the 64%-broken Compose test did. Deliberately
    report-only: this NEVER touches `exitstatus`, so a rerun that eventually passes still
    exits 0 — a hard gate here would collapse option (a) back into the rejected option
    (b) ("drop reruns, let load flakes go red").
    """
    del terminalreporter, config  # unused — the tally already lives in `_rerun_counts`
    del exitstatus  # never altered; see docstring
    if not _rerun_counts:
        return
    reruns = sorted(_rerun_counts.items())
    _safe_print(f"\n[ux] rerun-rate alarm: {len(reruns)} test(s) needed a retry this run:")
    for nodeid, failed in reruns:
        _safe_print(f"  {nodeid} - {failed} attempt(s) failed")
    for line in render_annotations(reruns):
        _safe_print(line)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(render_step_summary(reruns))


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


@pytest.fixture(autouse=True)
def _help_welcome_default_seen(request: pytest.FixtureRequest, page: Page) -> None:
    """Default every UX test to 'first-run help already seen'.

    The Sprint-6.5 help primitive auto-opens a welcome modal on first view and
    the education branch layers the KW3 new-user tour (one once-ever modal per
    milestone), each gated by a ``cb_help_seen:<block>`` localStorage flag (full
    block list + the seeding JS: ``ui_pages.selectors.Help`` — also consumed by
    ``scripts/capture_screenshots.py``, which hits the exact same auto-open
    problem outside the test harness). Each test gets a fresh browser context
    (empty localStorage), so without this an auto-modal's full-screen backdrop
    would block the interactions every other test performs right after
    ``load()``. Seeding every auto-firing block via an init-script (runs before
    each navigation) models the common case — a returning user. Tests opt back
    in: ``@pytest.mark.show_welcome`` for just the welcome, ``@pytest.mark.show_tour``
    for the whole new-user sequence.
    """
    if request.node.get_closest_marker("show_tour"):
        return  # tour tests drive the genuine new-user sequence
    blocks = list(Help.TOUR_STOP_BLOCKS)
    if request.node.get_closest_marker("show_welcome"):
        blocks.remove("panelUser")  # welcome fires; the rest stay suppressed
    page.add_init_script(Help.suppress_tour_init_script(blocks))


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

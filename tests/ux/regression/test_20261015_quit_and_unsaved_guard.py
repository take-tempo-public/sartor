"""Items 146/147 in the browser: Quit, the stopped state, the heartbeat, the unload guard.

The server-side arms are `tests/test_lifecycle_routes.py` and `tests/test_cli_setup.py`; this is
what the page shows and sends. `SHUTDOWN_FN` is a recorder on the live server's app, so the
real handler runs and the real `POST /api/shutdown` is answered, but nothing exits.

What each test pins:

* **Quit asks first.** Settings -> Quit Sartor opens the shared confirm dialog; Cancel sends
  nothing; Quit sends exactly one `POST /api/shutdown` and the page ends in the static
  "Sartor has stopped" state with the drawer closed and focus on its title.
* **No Quit when the server cannot stop itself.** Same selectors, no `SHUTDOWN_FN`: the control
  and the stopped dialog are not in the DOM. (The Quit test is this one's positive control: it
  shows the selectors do match when the control is rendered.)
* **The heartbeat exists only when `--idle-timeout` is on.** The default page has no meta tag
  and sends no heartbeat; with a tracker configured it sends one at load. The second arm is
  the first one's positive control — the recorder demonstrably sees a heartbeat.
* **`beforeunload` prompts only for unsaved edits.** Closing a clean page raises no dialog; a
  half-typed form field does; clearing the field back to its opening value does not; typed
  Step-6 editor text and a pending Compose autosave do; and after Quit nothing does.

Not driven here, stated rather than implied: the editor and Compose arms set the state those
predicates read (`lastGeneratedResume` + `#resumePreview`, `_composeSaveTimer`) directly instead
of walking the wizard to reach it — the wizard path to a *typed* edit is exercised by
`test_20261014_confirm_overwrite_edits.py`, and this file pins that the unload guard consults
the same variables. A rename of either would fail here with a `ReferenceError`.

Why a dialog needs a click first: Chromium shows a `beforeunload` prompt only on a page the user
has interacted with, so every close below follows a real click. Without it the "no dialog" arms
would pass for the wrong reason.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Dialog, Page, expect

import instance
from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import ConfirmModal, Help, Lifecycle, Settings

# `openFormModal` is a top-level function declaration in app.js, so it is a window global.
_OPEN_FORM_JS = """() => {
    openFormModal({ title: 'Probe', fields: [{ name: 'note', label: 'Note', type: 'text' }] });
    return true;
}"""
_FORM_FIELD = "#formModal_note"

# Same state `_detectEdits()` reads: the frozen baseline and the live editor text.
_TYPE_EDITOR_JS = """() => {
    lastGeneratedResume = 'baseline resume text';
    document.getElementById('resumePreview').textContent = 'baseline resume text, then a typed edit';
    return _detectEdits().anyEdited;
}"""

# A Compose autosave that is scheduled but not yet sent (`_scheduleCompositionSave`'s shape).
_PENDING_AUTOSAVE_JS = """() => {
    _composeSaveTimer = setTimeout(() => {}, 600000);
    return _composeSaveTimer !== null;
}"""


@pytest.fixture
def stoppable(ux_app: ModuleType) -> list[int]:
    """Make the live server look like one started by `sartor`; returns the shutdown call log."""
    calls: list[int] = []
    ux_app.app.config["SHUTDOWN_FN"] = lambda: calls.append(1)
    return calls


def _open_settings(page: Page) -> None:
    page.click(Settings.OPEN_PILL)
    page.wait_for_selector(Settings.DRAWER, state="visible", timeout=DEFAULT_TIMEOUT_MS)


def _fresh_page(page: Page, live_server: str) -> Page:
    """A second page in the same context, loaded and clicked (user activation).

    `page.close(run_before_unload=True)` consumes a page, so each arm needs its own. The
    suite's "first-run help already seen" init script is page-level, so it has to be added
    to this page too, or the welcome modal's backdrop blocks every click.
    """
    pg = page.context.new_page()
    pg.add_init_script(Help.suppress_tour_init_script(list(Help.TOUR_STOP_BLOCKS)))
    BasePage(pg, live_server).load()
    pg.click("body")
    return pg


def _close_expecting_prompt(pg: Page) -> None:
    """Close with `beforeunload` handlers run and require a `beforeunload` dialog.

    `page.close(run_before_unload=True)` returns BEFORE the dialog (or the close) arrives, so
    this waits on the event rather than asserting on what has happened by the time the call
    returns. The dialog is dismissed ("stay on this page"), so the page stays open and can be
    reused.
    """
    with pg.expect_event("dialog", timeout=DEFAULT_TIMEOUT_MS) as raised:
        pg.close(run_before_unload=True)
    dialog: Dialog = raised.value
    assert dialog.type == "beforeunload"
    dialog.dismiss()
    assert not pg.is_closed(), "dismissing the prompt must keep the page"


def _close_expecting_no_prompt(pg: Page) -> None:
    """Close with handlers run and require that the page simply closes, with no dialog."""
    seen: list[str] = []

    def _on_dialog(dialog: Dialog) -> None:
        seen.append(dialog.type)
        dialog.dismiss()

    pg.on("dialog", _on_dialog)
    with pg.expect_event("close", timeout=DEFAULT_TIMEOUT_MS):
        pg.close(run_before_unload=True)
    assert seen == [], f"unexpected dialog(s) on close: {seen}"


# ------------------------------------------------------------------ Quit


@pytest.mark.ux
def test_quit_asks_first_then_shows_the_stopped_state(
    page: Page, live_server: str, stoppable: list[int]
) -> None:
    posts: list[str] = []
    page.on(
        "request",
        lambda r: (
            posts.append(r.url) if r.method == "POST" and r.url.endswith("/api/shutdown") else None
        ),
    )
    BasePage(page, live_server).load()
    _open_settings(page)
    expect(page.locator(Settings.QUIT_BUTTON)).to_be_visible()
    expect(page.locator(Lifecycle.STOPPED)).to_be_hidden()  # in the DOM, not showing

    # Cancel: nothing is sent, nothing stops.
    page.click(Settings.QUIT_BUTTON)
    page.wait_for_selector(ConfirmModal.OPEN, timeout=DEFAULT_TIMEOUT_MS)
    expect(page.locator(ConfirmModal.TITLE)).to_have_text("Quit Sartor?")
    expect(page.locator(ConfirmModal.OK)).to_have_text("Quit")
    page.click(ConfirmModal.CANCEL)
    expect(page.locator(ConfirmModal.MODAL)).to_be_hidden()
    assert posts == []
    assert stoppable == []
    expect(page.locator(Lifecycle.STOPPED)).to_be_hidden()

    # Quit: exactly one POST, then the static end state.
    page.click(Settings.QUIT_BUTTON)
    page.wait_for_selector(ConfirmModal.OPEN, timeout=DEFAULT_TIMEOUT_MS)
    page.click(ConfirmModal.OK)
    page.wait_for_selector(Lifecycle.STOPPED_OPEN, timeout=DEFAULT_TIMEOUT_MS)
    assert len(posts) == 1
    assert stoppable == [1]
    expect(page.locator(Lifecycle.STOPPED_TITLE)).to_be_focused()
    expect(page.locator(Settings.DRAWER)).to_be_hidden()


@pytest.mark.ux
def test_no_quit_control_when_the_server_cannot_stop_itself(page: Page, live_server: str) -> None:
    """No `SHUTDOWN_FN` (a WSGI host): the button would be a lie, so it is not rendered."""
    BasePage(page, live_server).load()
    _open_settings(page)
    expect(page.locator(Settings.QUIT_BUTTON)).to_have_count(0)
    expect(page.locator(Settings.QUIT_SECTION)).to_have_count(0)
    expect(page.locator(Lifecycle.STOPPED)).to_have_count(0)


# ------------------------------------------------------------------ heartbeat


@pytest.mark.ux
def test_the_page_heartbeats_only_when_idle_shutdown_is_on(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    beats: list[str] = []
    page.on(
        "request",
        lambda r: (
            beats.append(r.url) if r.method == "POST" and r.url.endswith("/api/heartbeat") else None
        ),
    )
    meta = 'meta[name="sartor-idle-heartbeat-s"]'

    # Default run: no meta tag, no heartbeat.
    BasePage(page, live_server).load()
    assert page.locator(meta).count() == 0
    assert beats == []

    # Control arm: with a tracker configured the same recorder sees the beat at load.
    ux_app.app.config["IDLE_TRACKER"] = instance.IdleTracker(900.0)
    with page.expect_request(
        lambda r: r.method == "POST" and r.url.endswith("/api/heartbeat"),
        timeout=DEFAULT_TIMEOUT_MS,
    ):
        page.reload()
    assert page.locator(meta).get_attribute("content") == str(instance.HEARTBEAT_S)
    assert beats, "the recorder never saw a heartbeat, so the absence above proved nothing"


# ------------------------------------------------------------------ unload guard


@pytest.mark.ux
def test_closing_a_clean_page_raises_no_prompt(page: Page, live_server: str) -> None:
    pg = _fresh_page(page, live_server)
    _close_expecting_no_prompt(pg)


@pytest.mark.ux
def test_a_half_typed_form_field_raises_a_prompt_and_reverting_it_does_not(
    page: Page, live_server: str
) -> None:
    pg = _fresh_page(page, live_server)
    assert pg.evaluate(_OPEN_FORM_JS) is True
    pg.click(_FORM_FIELD)
    pg.keyboard.type("half-typed bullet")

    _close_expecting_prompt(pg)

    # Back to the value the form opened with: nothing is unsaved any more.
    pg.fill(_FORM_FIELD, "")
    pg.click(_FORM_FIELD)  # user activation after the dismissed dialog
    _close_expecting_no_prompt(pg)


@pytest.mark.ux
def test_typed_editor_text_raises_a_prompt(page: Page, live_server: str) -> None:
    pg = _fresh_page(page, live_server)
    assert pg.evaluate(_TYPE_EDITOR_JS) is True
    _close_expecting_prompt(pg)


@pytest.mark.ux
def test_a_pending_compose_autosave_raises_a_prompt(page: Page, live_server: str) -> None:
    pg = _fresh_page(page, live_server)
    assert pg.evaluate(_PENDING_AUTOSAVE_JS) is True
    _close_expecting_prompt(pg)


@pytest.mark.ux
def test_after_quit_nothing_prompts_even_with_unsaved_text(
    page: Page, live_server: str, stoppable: list[int]
) -> None:
    pg = _fresh_page(page, live_server)
    assert pg.evaluate(_OPEN_FORM_JS) is True
    pg.click(_FORM_FIELD)
    pg.keyboard.type("typed, then the server was told to stop")
    pg.evaluate("() => { _showSartorStopped(); return true; }")
    pg.wait_for_selector(Lifecycle.STOPPED_OPEN, timeout=DEFAULT_TIMEOUT_MS)

    _close_expecting_no_prompt(pg)

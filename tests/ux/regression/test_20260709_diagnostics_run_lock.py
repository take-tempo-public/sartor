"""UX regression — diagnostics round-2 #1: global paid-run single-flight lock.

Guards `dashboard/templates/dashboard.html`'s `window.sartorRunLock`: while any
one of the four paid-run buttons (eval / tune / bootstrap / grounding-score) is
in flight, the other three (and re-clicks of the live one) must be disabled and
a prominent `#runLockBanner` must be visible — then, once that run's request
resolves, all four re-enable and the banner hides.

Drives the "Run eval" control end-to-end but never lets a real eval run: a
Playwright route interceptor **holds** the `POST /api/eval/run` request open
(never fulfills it) so the click's fetch stays pending exactly like a real
in-flight SSE stream, giving a stable window to assert the lock is engaged.
Fulfilling the held route with an empty `text/event-stream` body then mirrors
the client's normal `_closed` terminal path (see `run()` in dashboard.html),
proving `releaseRunLock()` fires and un-disables all four buttons.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage

_RUN_LOCK_IDS = ("#evalRunBtn", "#tuneRunBtn", "#bsRun", "#annScore")


@pytest.mark.ux
def test_run_lock_blocks_other_buttons_and_releases(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_be_visible()

    # Auto-accept the "Run the ... eval now?" confirm() so the click proceeds
    # into run() (where acquireRunLock() fires) instead of being dismissed.
    page.on("dialog", lambda dialog: dialog.accept())

    # Hold POST /api/eval/run open — never fulfill it here — to simulate an
    # in-flight paid run without ever making a real (or even resolving) call.
    held: list[Route] = []

    def _hold(route: Route) -> None:
        held.append(route)

    page.route("**/api/eval/run", _hold)

    page.locator("#evalRunBtn").click()

    # Wait for the click's fetch to actually reach the interceptor (bounded poll).
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-eval click never issued a POST /api/eval/run"

    # Locked: all four run buttons disabled (not just evalRunBtn's own toggle),
    # and the shared banner is visible.
    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_disabled()
    expect(page.locator("#runLockBanner")).to_be_visible()

    # Resolve the held request the same way a normal successful stream ends —
    # body closes immediately, so the client's reader sees chunk.done → '_closed'.
    held[0].fulfill(status=200, content_type="text/event-stream", body="")

    # Released: all four run buttons re-enabled, banner hidden again.
    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_enabled()
    expect(page.locator("#runLockBanner")).to_be_hidden()

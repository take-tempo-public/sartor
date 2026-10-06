"""UX regression — run-lock ownership and the declined path (items 119, 120).

`window.sartorRunLock` in `dashboard/templates/dashboard.html` had two gaps:

* **Item 119.** `release()` took no token, so any completion path freed the lock
  while another run was live. And three inline handlers (tune, bootstrap,
  score-grounding) called `acquire()` and carried on even when it returned false.
* **Item 120.** `run()` set its button pending *before* the `acquire()` check, so a
  declined start left the button pulsing (`btn-pending`) forever.

These drive the real page: the lock is taken from page script (standing in for a run
already live in this tab), then each path is forced and checked. Nothing here makes a
paid call: every run POST is intercepted and recorded, never fulfilled.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard


def _record_posts(page: Page, pattern: str) -> list[str]:
    seen: list[str] = []

    def _hold(route: Route) -> None:
        seen.append(route.request.url)

    page.route(pattern, _hold)
    return seen


@pytest.mark.ux
def test_stale_release_does_not_free_a_live_run(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    DashboardConsolePage(page, live_server).load()
    state = page.evaluate(
        """() => {
          const rl = window.sartorRunLock;
          const owner = rl.acquire();
          const second = rl.acquire();       // a run is live: declined
          rl.release();                      // a token-less (stale) release
          rl.release(second);                // the declined caller's cleanup
          const stillLocked = rl.isLocked();
          rl.release(owner);
          return {owner: !!owner, second: second, stillLocked, after: rl.isLocked()};
        }"""
    )
    assert state == {"owner": True, "second": None, "stillLocked": True, "after": False}


@pytest.mark.ux
def test_declined_run_does_not_leave_its_button_pulsing(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("quality")
    posts = _record_posts(page, "**/api/eval/run")
    result = page.evaluate(
        """() => {
          const owner = window.sartorRunLock.acquire();
          const btn = document.getElementById('evalRunBtn');
          window.sartorEval.run({suite: 'synthetic'}, null, btn);
          const pending = btn.classList.contains('btn-pending');
          window.sartorRunLock.release(owner);
          return {pending, disabledAfterRelease: btn.disabled};
        }"""
    )
    page.wait_for_timeout(300)
    assert posts == []
    assert result == {"pending": False, "disabledAfterRelease": False}


@pytest.mark.ux
def test_bootstrap_click_while_locked_issues_no_post(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    from tests.ux.seeding import seed_user

    seed_user(ux_app, "alice")
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()
    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    dash.select_bs_user("alice")
    page.fill(".bs-jd-name", "jd1")
    page.fill(".bs-jd-text", "Senior PM JD body.")

    posts = _record_posts(page, "**/api/annotation/bootstrap")
    page.evaluate("() => { window.__owner = window.sartorRunLock.acquire(); }")
    # Force the governed button back on, the shape of a stray enabled button.
    page.evaluate("() => { document.getElementById('bsRun').disabled = false; }")
    page.locator(Dashboard.ANN_BS_RUN).click()
    page.wait_for_timeout(300)

    assert posts == [], "a click while another run is live started a second bootstrap"
    assert page.evaluate("() => window.sartorRunLock.isLocked()") is True
    assert "btn-pending" not in (page.locator("#bsRun").get_attribute("class") or "")
    expect(page.locator("#runLockBanner")).to_be_visible()
    page.evaluate("() => window.sartorRunLock.release(window.__owner)")
    expect(page.locator("#runLockBanner")).to_be_hidden()

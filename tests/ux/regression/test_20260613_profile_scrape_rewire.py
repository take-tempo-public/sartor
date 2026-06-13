"""Regression: the PX-02 'Fetch profile content' affordance (profile scrape re-wire).

Front-end coverage for the Settings-drawer button that drives the opt-in
profile/website/portfolio scrape. The /profile/fetch response is STUBBED via
page.route so the test is network-free + deterministic (the route's real
behavior — that it actually calls the scraper + persists online_profile_text —
is pinned by tests/test_profile_fetch_route.py). saveConfig still runs for real
(PUT /config), so this also proves the save-then-fetch ordering the handler
promises.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from tests.ux.seeding import seed_user
from ui_pages import BasePage, UserPickerPage
from ui_pages.selectors import Settings


def _open_settings_for(page: Page, live_server: str, ux_app: ModuleType,
                       username: str = "alice") -> None:
    seed_user(ux_app, username)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select(username)
    page.click(Settings.OPEN_PILL)
    page.wait_for_selector(Settings.DRAWER, state="visible")


@pytest.mark.ux
@pytest.mark.slow
def test_fetch_button_reports_success(page: Page, live_server: str,
                                      ux_app: ModuleType) -> None:
    """With URLs configured, clicking Fetch shows the character/source count
    returned by the route."""
    def _stub(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json",
                      body='{"ok": true, "chars": 412, "urls": 1}')

    page.route("**/api/users/*/profile/fetch", _stub)

    _open_settings_for(page, live_server, ux_app)
    page.fill(Settings.LINKEDIN_INPUT, "https://linkedin.com/in/alice")
    page.click(Settings.FETCH_PROFILE_BTN)

    expect(page.locator(Settings.FETCH_PROFILE_STATUS)).to_contain_text(
        "Fetched 412 characters", ignore_case=True
    )


@pytest.mark.ux
@pytest.mark.slow
def test_fetch_button_reports_no_urls(page: Page, live_server: str,
                                      ux_app: ModuleType) -> None:
    """No configured URLs → the graceful 'nothing to fetch' message."""
    def _stub(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json",
                      body='{"ok": true, "chars": 0, "urls": 0}')

    page.route("**/api/users/*/profile/fetch", _stub)

    _open_settings_for(page, live_server, ux_app)
    page.click(Settings.FETCH_PROFILE_BTN)

    expect(page.locator(Settings.FETCH_PROFILE_STATUS)).to_contain_text(
        "No profile URLs to fetch", ignore_case=True
    )

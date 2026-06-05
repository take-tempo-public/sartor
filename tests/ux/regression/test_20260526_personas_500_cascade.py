"""Regression: first user-select after a fresh server start has no 5xx.

The 5b cascade root (RELEASE_CHECKLIST / AGENT_FAILURE_PATTERNS §5b): the
first user-select fired several concurrent requests; the first to touch the
DB ran Alembic `upgrade()` while the others raced it, corrupting Alembic's
module globals → `/personas` 500 → the corpus tab loaded bad state → the
preview iframe loaded bad HTML → paged.js choked. The `threading.Lock()` in
`db/session.init_db` makes the check-and-init atomic and breaks the cascade
at its source.

This test exercises the real race: the `live_server` fixture is **threaded**
(so concurrent first-select requests genuinely overlap), and we assert no
HTTP 5xx surfaced. It guards the upstream cause, so the downstream symptoms
(corpus render, iframe, paged.js) can't recur.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_user
from ui_pages import BasePage, UserPickerPage


@pytest.mark.ux
@pytest.mark.slow
def test_first_user_select_no_server_error(page: Page, live_server: str,
                                           ux_app: ModuleType,
                                           server_errors: list[str]) -> None:
    seed_user(ux_app, "alice")

    BasePage(page, live_server).load()
    # The first select fires config/applications/personas/pending-counts/
    # summaries/experiences ~concurrently against a never-initialised DB.
    UserPickerPage(page, live_server).select("alice")
    page.wait_for_load_state("networkidle")

    assert server_errors == [], f"HTTP 5xx on first user-select: {server_errors}"

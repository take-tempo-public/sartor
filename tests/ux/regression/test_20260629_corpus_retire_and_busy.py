"""Regression: retired corpus rows are hidden until "Show retired" is ticked,
and the persistent busy banner shows/clears.

P3/P4 — soft-retired titles + bullets must be invisible by default and appear
only when the user explicitly ticks the "Show retired" box (the owner's hard
requirement). P2 — _setBusy() puts up a persistent "working…" banner that stays
until cleared. Both are LLM-free: corpus is seeded directly into the DB and the
banner helper is driven directly.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS


def _seed_exp_with_retired(candidate_id: int) -> int:
    """One experience with an active + a retired bullet, and a retired alt title."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id, company="Acme", start_date="2021-01", display_order=0
        )
        s.add(e)
        s.flush()
        s.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Staff Engineer",
                is_official=1,
                truthful_enough_to_use=1,
                is_pending_review=0,
                is_active=1,
                source="official",
            )
        )
        s.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Retired Title",
                is_official=0,
                truthful_enough_to_use=0,
                is_pending_review=0,
                is_active=0,
                source="user_added",
            )
        )
        s.add(
            Bullet(
                experience_id=e.id,
                text="Active bullet stays visible",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="manual",
                has_outcome=0,
            )
        )
        s.add(
            Bullet(
                experience_id=e.id,
                text="Retired bullet is hidden",
                display_order=1,
                is_active=0,
                is_pending_review=0,
                source="manual",
                has_outcome=0,
            )
        )
        s.commit()
        return e.id
    finally:
        s.close()


@pytest.mark.ux
@pytest.mark.slow
def test_retired_rows_hidden_until_show_retired(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    cid = seed_user(ux_app, "alice")
    _seed_exp_with_retired(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open().wait_for_cards()
    corpus.expand_card(0)

    # Default: retired rows are absent entirely (their text lives in field
    # .value, so the strong check is the row count, not get_by_text).
    assert page.locator(".corpus-row.retired").count() == 0

    # Tick "Show retired" → the retired bullet (textarea) + title (input)
    # reappear, each greyed and flagged RETIRED.
    page.check("#corpusShowRetired")
    page.wait_for_selector(".corpus-row.retired", timeout=DEFAULT_TIMEOUT_MS)
    assert page.locator(".corpus-row.retired").count() >= 2
    assert page.locator(".corpus-row-flag.retired").count() >= 2
    bullet_val = page.locator(".corpus-row.retired textarea.corpus-row-input").input_value()
    assert "Retired bullet is hidden" in bullet_val


@pytest.mark.ux
@pytest.mark.slow
def test_busy_banner_shows_and_clears(page: Page, live_server: str, ux_app: ModuleType) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()

    # Busy on → persistent banner with the label + a body.cb-busy hook.
    page.evaluate("window._setBusy(true, 'Testing busy state')")
    page.wait_for_selector("#_busyBanner.show", timeout=DEFAULT_TIMEOUT_MS)
    text = page.locator("#_busyBanner .cb-busy-text").text_content() or ""
    assert "testing busy state" in text.lower()
    assert page.locator("body.cb-busy").count() == 1

    # Busy off → banner loses .show and the body hook clears.
    page.evaluate("window._setBusy(false)")
    assert page.locator("#_busyBanner.show").count() == 0
    assert page.locator("body.cb-busy").count() == 0

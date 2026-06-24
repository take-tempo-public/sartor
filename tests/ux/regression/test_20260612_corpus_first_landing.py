"""Regression: corpus-first IA + smart landing + hand-off CTA (Sprint 6.4,
#16 + #1 + KW1).

The Career corpus tab is now tab 1 and the onboarding entry. When a user is
selected, ``onUserSelect()`` routes through ``_landingTab()``:

- empty corpus  → land on **Career corpus** (onboard: import a résumé), fixing
  KW1 (a new user used to land on JD entry with nothing to tailor from);
- populated corpus → land on **Tailor** (straight to the application workflow).

When corpus review is finished (non-empty corpus, nothing pending), the
onboarding banner flips to a ready state with a **"Start tailoring →"** CTA that
hands the user forward into Tailor — replacing the old dead-end.

LLM-free: corpus is seeded directly via ``tests/ux/seeding`` (no analyzer entry
point is hit). Active tab is asserted via ``aria-selected`` — the same idiom as
``test_20260612_logo_home_route``.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Corpus, PriorApps, TopTabs


def _wait_tab_active(page: Page, tab_id: str) -> None:
    """Block until the named top-tab button reports aria-selected=true."""
    page.wait_for_function(
        "(id) => document.getElementById(id).getAttribute('aria-selected') === 'true'",
        arg=tab_id,
        timeout=DEFAULT_TIMEOUT_MS,
    )


@pytest.mark.ux
@pytest.mark.slow
def test_empty_corpus_lands_on_corpus(page: Page, live_server: str, ux_app: ModuleType) -> None:
    # Empty corpus (no experiences) → onboard on the Career corpus tab.
    seed_user(ux_app, "alice")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    _wait_tab_active(page, "topTabCorpus")
    assert page.locator(Corpus.PANEL).is_visible()
    # Nothing to tailor from yet → no hand-off CTA.
    assert page.locator(Corpus.START_TAILORING_BUTTON).is_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_populated_corpus_lands_on_tailor(page: Page, live_server: str, ux_app: ModuleType) -> None:
    # A populated corpus → straight to the Tailor workflow.
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    _wait_tab_active(page, "topTabTailor")
    page.wait_for_selector(PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)


@pytest.mark.ux
@pytest.mark.slow
def test_ready_corpus_shows_start_tailoring_cta(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    # Non-empty corpus with everything accepted (0 pending) → the Career corpus
    # tab offers the "Start tailoring →" hand-off, which routes to Tailor.
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # title + bullets all is_pending_review=0

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    # Populated → lands on Tailor; move to the corpus tab to reach the CTA.
    corpus = CorpusPage(page, live_server).open().wait_for_cards()

    cta = corpus.start_tailoring_button()
    cta.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
    cta.click()

    _wait_tab_active(page, "topTabTailor")
    assert page.locator(TopTabs.TAILOR).get_attribute("aria-selected") == "true"

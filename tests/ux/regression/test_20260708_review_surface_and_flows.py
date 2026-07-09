"""Regression: fix/review-surface-and-flows — corpus date-rail propagation
(#4) + surgical-refinement failure resilience (#5).

#4: `_saveExperienceField` (static/app.js) PUTs a field edit (company /
location / dates / summary) but never refreshed the collapsed card header —
editing an experience's start/end date left the visible `.corpus-card-dates`
rail showing the stale value until a full page reload. Fix: the save now
also calls `refreshCorpusSummaryFor(expId)`, which now ALSO refreshes
`.corpus-card-dates` (it previously only touched company/title/meta).

#5: `_submitSurgicalRefinement` had a try/finally with NO catch — a
transient failure on `POST /api/validate-refinement` propagated uncaught and
the UI just reset silently (busy banner cleared, button re-enabled, nothing
told the user anything failed). Fix: a catch mirroring the legacy refine
path's error handling (`reportError` + a "NOT EXECUTED" entry in the shared
refinement-history panel), plus the note staying in the input box so
clicking Refine again IS the retry affordance.

Both LLM-free: #4 is pure corpus-CRUD DOM state; #5 drives
`_submitSurgicalRefinement` directly via `page.evaluate` (same technique as
test_20260706_refinement_scope_modal.py) with `/api/validate-refinement`
intercepted to fail at the network layer, so neither needs a generated
résumé or a live LLM.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Route

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Corpus


@pytest.mark.ux
@pytest.mark.slow
def test_editing_experience_dates_refreshes_card_header_rail(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    cid = seed_user(ux_app, "alice")
    exp_id = seed_exp_with_bullets(cid)  # start_date="2021-01", end_date=None

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open().wait_for_cards()
    corpus.expand_card(0)

    # Baseline: the collapsed-header date rail shows the seeded start date.
    dates_locator = page.locator(f"{Corpus.CARD} .corpus-card-dates")
    assert "2021-01" in (dates_locator.text_content() or "")

    # Edit start_date inline (the expanded body's field group) and blur to
    # fire the 'change' listener _saveExperienceField is wired to.
    date_input = page.locator(f"#exp-{exp_id}-start_date")
    date_input.fill("2020-06")
    date_input.press("Tab")

    # The header rail updates WITHOUT a page reload — this is the bug: before
    # the fix, .corpus-card-dates kept showing "2021-01" until a full reload.
    page.wait_for_function(
        "() => (document.querySelector('.corpus-card-dates')?.textContent || '').includes('2020-06')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    assert "2021-01" not in (dates_locator.text_content() or "")
    assert "2020-06" in (dates_locator.text_content() or "")
    assert "current" in (dates_locator.text_content() or "").lower()


@pytest.mark.ux
@pytest.mark.slow
def test_surgical_refinement_network_failure_surfaces_error_with_retry(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    def _fail(route: Route) -> None:
        route.abort()

    page.route("**/api/validate-refinement", _fail)

    note = "Tighten the summary."
    page.evaluate(
        "(note) => {"
        " window._composeApplicationId = 1;"
        " document.getElementById('refinementInput').value = note;"
        " document.getElementById('btnRefinement').disabled = false;"
        " window.__refineSettled = false;"
        " _submitSurgicalRefinement(note).then(() => { window.__refineSettled = true; });"
        " }",
        note,
    )
    page.wait_for_function("() => window.__refineSettled === true", timeout=DEFAULT_TIMEOUT_MS)

    # Visible error surfacing (reportError -> setStatus('ERROR') + error modal wiring).
    status_text = (page.locator("#statusPill").text_content() or "").lower()
    assert "error" in status_text

    # The refinement-history panel (shared with the legacy refine path) shows
    # a "NOT EXECUTED" entry recording the failed attempt — case-insensitive
    # per the project's CSS-uppercase UX-copy convention. state="attached" (not
    # the default "visible"): this test never navigates into the wizard step
    # that hosts the panel, so an ancestor is display:none — only the class
    # toggle on #refinementHistory itself is under test here, matching
    # test_20260706_refinement_scope_modal.py's identical pattern.
    page.wait_for_selector(
        "#refinementHistory:not(.hidden)", state="attached", timeout=DEFAULT_TIMEOUT_MS
    )
    history_text = (page.text_content("#refinementHistory") or "").lower()
    assert "not executed" in history_text
    assert note.lower() in history_text

    # Retry affordance: the note is still in the box and the button is
    # re-enabled — retrying is just clicking Refine again.
    assert page.locator("#refinementInput").input_value() == note
    assert not page.locator("#btnRefinement").is_disabled()

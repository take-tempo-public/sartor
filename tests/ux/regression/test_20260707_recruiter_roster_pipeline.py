"""Regression: Wave 2 recruiter tier — candidate roster (F-08) + cross-candidate
pipeline board (F-17), UX review 2026-07-07 (docs/dev/reviews/2026-07-ux-review/
40-friction-register.md).

Both surfaces are backed by the same aggregate GET /api/candidates/roster
(blueprints/users.py:candidate_roster) — route/query-count coverage lives in
tests/test_users_routes.py::TestCandidateRoster; this file exercises the two
frontend consumers end-to-end against a real (LLM-free) server.

Seeded directly via tests/ux/seeding (no analyzer entry point hit), mirroring
the established pattern in test_20260612_corpus_first_landing.py.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_application, seed_user
from ui_pages import BasePage, PipelinePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Pipeline, PriorApps, UserPicker


def _wait_tab_active(page: Page, tab_id: str) -> None:
    """Block until the named top-tab button reports aria-selected=true."""
    page.wait_for_function(
        "(id) => document.getElementById(id).getAttribute('aria-selected') === 'true'",
        arg=tab_id,
        timeout=DEFAULT_TIMEOUT_MS,
    )


@pytest.mark.ux
@pytest.mark.slow
def test_roster_hidden_below_threshold(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """fix/review-surface-and-flows: below the roster's visibility threshold
    (6 candidates), the searchable roster stays hidden — a couple of names
    scan fine in the plain <select>; search only earns its keep once
    there's enough to actually search (was >= 2, raised to >= 6)."""
    seed_user(ux_app, "alice")
    seed_user(ux_app, "bob")

    BasePage(page, live_server).load()
    page.wait_for_selector(UserPicker.SELECT, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert page.locator(UserPicker.ROSTER).is_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_roster_shows_target_role_and_search_filters_it(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    seed_user(ux_app, "alice")
    bob_id = seed_user(ux_app, "bob")
    seed_application(bob_id, title="Senior SRE @ Globex", company="Globex", status="submitted")
    # fix/review-surface-and-flows raised the roster's visibility threshold
    # from 2 to 6 candidates — pad with filler candidates so this test still
    # exercises the roster surface itself (see test_roster_hidden_below_threshold
    # above for the below-threshold case).
    for extra in ("carol", "dave", "erin", "frank"):
        seed_user(ux_app, extra)

    BasePage(page, live_server).load()
    picker = UserPickerPage(page, live_server)

    # 6+ candidates → the roster surface is shown above the plain <select>.
    page.wait_for_selector(UserPicker.ROSTER, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.wait_for_function(
        "(n) => document.querySelectorAll('.candidate-roster-card').length === n",
        arg=6,
        timeout=DEFAULT_TIMEOUT_MS,
    )

    # Bob's card surfaces his latest application's title/company (F-08).
    target_text = (
        page.locator(
            f"{UserPicker.roster_card('bob')} .candidate-roster-card-target"
        ).text_content()
        or ""
    )
    assert "senior sre" in target_text.lower()
    assert "globex" in target_text.lower()

    # Alice has no applications yet — the empty-state copy shows instead.
    alice_target = (
        page.locator(
            f"{UserPicker.roster_card('alice')} .candidate-roster-card-target"
        ).text_content()
        or ""
    )
    assert alice_target.strip() != ""

    # Search narrows the roster to matching candidates only.
    picker.search_roster("bob")
    page.wait_for_selector(
        UserPicker.roster_card("bob"), state="visible", timeout=DEFAULT_TIMEOUT_MS
    )
    assert page.locator(UserPicker.roster_card("alice")).count() == 0

    # Selecting the (filtered) card drives the underlying <select> — the
    # existing currentUser mechanics are unchanged, just given a front door.
    picker.select_from_roster("bob")
    assert page.locator(UserPicker.SELECT).input_value() == "bob"


@pytest.mark.ux
@pytest.mark.slow
def test_pipeline_board_groups_by_status_and_switches_candidate(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    alice_id = seed_user(ux_app, "alice")
    bob_id = seed_user(ux_app, "bob")
    seed_application(alice_id, title="Staff Eng @ Acme", company="Acme", status="draft")
    seed_application(bob_id, title="Senior SRE @ Globex", company="Globex", status="submitted")

    BasePage(page, live_server).load()
    pipeline = PipelinePage(page, live_server).open()

    # PipelinePage.open() waits for #pipelineBoard visibility but NOT for its
    # async-loaded rows; row_count() is a snapshot with no wait, so on a slower /
    # loaded CI runner the count races the fetch (the 0-vs-2 flake seen on Linux
    # CI). expect() polls until the rows populate before we assert.
    expect(page.locator(Pipeline.ROW)).to_have_count(2, timeout=DEFAULT_TIMEOUT_MS)
    assert pipeline.row_count() == 2
    board = page.locator(Pipeline.BOARD)
    assert board.locator("text=Staff Eng @ Acme").is_visible()
    assert board.locator("text=Senior SRE @ Globex").is_visible()

    count_text = page.locator(Pipeline.COUNT).text_content() or ""
    assert "2" in count_text

    # Clicking a row switches candidates, hands off to the Tailor tab, AND
    # opens that specific application's detail modal — "linking into that
    # candidate+application", not just the candidate.
    pipeline.click_row("Staff Eng @ Acme")
    page.wait_for_function(
        "(u) => document.getElementById('userSelect').value === u",
        arg="alice",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    _wait_tab_active(page, "topTabTailor")
    page.wait_for_selector(PriorApps.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    modal_title = page.locator("#appDetailModalTitle").text_content() or ""
    assert "staff eng" in modal_title.lower()

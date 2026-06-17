"""Regression: opening the new-user form clears the stale user dropdown (#4).

Bug: with a user selected, clicking "New user" revealed the new-profile fields
but left the previously-picked username sitting in the still-populated
``#userSelect`` dropdown directly above them — it read as a stale heading for the
new-user form. Fix: ``showNewUserForm()`` resets the dropdown to "-- Select User
--"; ``hideNewUserForm()`` (Cancel) restores it to the active user so the picker
stays consistent with the still-loaded context.

LLM-free: seeds a user + one experience directly; no analyzer entry points are
hit. The `page` fixture's sentinel also proves no JS error / no 5xx on the flow.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import UserPicker


@pytest.mark.ux
@pytest.mark.slow
def test_new_user_form_clears_then_restores_dropdown(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    # Non-empty corpus so selecting alice lands on Tailor (an empty corpus would
    # smart-land on Career corpus and arm the first-run tour — irrelevant here).
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    assert page.eval_on_selector(UserPicker.SELECT, "el => el.value") == "alice"

    # Open the new-user form → the dropdown must no longer show "alice".
    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_USER_FORM, state="visible",
                           timeout=DEFAULT_TIMEOUT_MS)
    assert page.eval_on_selector(UserPicker.SELECT, "el => el.value") == ""

    # Cancel → the dropdown is restored to the active user, form hidden.
    page.click(UserPicker.CANCEL_BUTTON)
    page.wait_for_selector(UserPicker.NEW_USER_FORM, state="hidden",
                           timeout=DEFAULT_TIMEOUT_MS)
    assert page.eval_on_selector(UserPicker.SELECT, "el => el.value") == "alice"

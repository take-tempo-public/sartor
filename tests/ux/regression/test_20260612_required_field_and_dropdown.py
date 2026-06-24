"""Regression: the reusable required-field marker + the auto-populatable
candidate-username dropdown (Sprint 6.3, findings #21 + #20-dropdown).

Closes the coverage gap for `feat/required-field-and-dropdown-pattern`. Two
reusable front-end conventions land together:

  #21 — required-field marker. A required input carries
        `required` + `aria-required="true"`; its visible label carries a
        decorative `.required-marker` asterisk; a cluster gets one
        `.form-required-legend`. Proven across three render paths: the static
        new-user form (index.html), the JS-rendered `openFormModal` modals
        (app.js), and the console dropdown label (dashboard.html).

  #20 (dropdown) — the diagnostics console's `#bsUser` / `#tuneUser` were
        free-text inputs; they are now `<select data-user-source>` auto-filled
        from GET /api/users on load. `.value` reads are unchanged.

LLM-free throughout — seeds config-only users (the dropdown source is the
configs glob behind /api/users) and drives the modal directly.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_user
from ui_pages import BasePage, DashboardConsolePage
from ui_pages.selectors import Dashboard, Forms, UserPicker


@pytest.mark.ux
@pytest.mark.slow
def test_new_user_form_required_markers(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """The new-user form marks username/name/email required (programmatic +
    visible) and leaves the optional fields unmarked."""
    BasePage(page, live_server).load()
    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_USERNAME, state="visible")

    for sel in (UserPicker.NEW_USERNAME, UserPicker.NEW_NAME, UserPicker.NEW_EMAIL):
        assert page.get_attribute(sel, "aria-required") == "true", f"{sel} aria-required"
        assert page.get_attribute(sel, "required") is not None, f"{sel} required attr"

    # Optional fields stay unmarked.
    assert page.get_attribute("#newPhone", "aria-required") is None
    assert page.get_attribute("#newLinkedin", "aria-required") is None

    # Visible cue: one asterisk per required field + the legend line.
    assert page.locator(f"#newUserForm {Forms.REQUIRED_MARKER}").count() >= 3
    page.wait_for_selector(f"#newUserForm {Forms.REQUIRED_LEGEND}", state="visible")


@pytest.mark.ux
@pytest.mark.slow
def test_form_modal_renders_required_marker(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """openFormModal renders the marker + aria-required for `required:true`
    fields (the reusable JS path behind add-title / add-bullet / add-experience)
    and leaves optional fields clean."""
    BasePage(page, live_server).load()

    # Fire-and-forget: openFormModal returns a Promise that resolves only on
    # submit/cancel, so the arrow must NOT return it (page.evaluate would await
    # forever). A block body returns undefined immediately; the modal stays up.
    page.evaluate(
        """() => { window.openFormModal({
            title: 'Add experience',
            fields: [
              { name: 'company', label: 'Company', type: 'text', required: true },
              { name: 'location', label: 'Location', type: 'text' },
            ],
        }); }"""
    )
    page.wait_for_selector("#formModal_company", state="visible")

    # Required field: programmatic signal + the marker in its label.
    assert page.get_attribute("#formModal_company", "aria-required") == "true"
    company_has_marker = page.eval_on_selector(
        "#formModal_company",
        "el => !!el.previousElementSibling.querySelector('.required-marker')",
    )
    assert company_has_marker, "required modal field should render a .required-marker"

    # Optional field: no signal, no marker.
    assert page.get_attribute("#formModal_location", "aria-required") is None
    location_has_marker = page.eval_on_selector(
        "#formModal_location",
        "el => !!el.previousElementSibling.querySelector('.required-marker')",
    )
    assert not location_has_marker, "optional modal field must not be marked required"

    page.keyboard.press("Escape")  # close so teardown stays clean


@pytest.mark.ux
@pytest.mark.slow
def test_console_username_dropdowns_populate(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """#bsUser / #tuneUser are <select>s auto-filled from /api/users; #bsUser
    carries the required marker (genuinely required), #tuneUser does not (its
    section is optional). Selection round-trips through `.value`."""
    seed_user(ux_app, "alice")
    seed_user(ux_app, "bob")

    dash = DashboardConsolePage(page, live_server).load()

    # --- Annotate tab: #bsUser (required) ---
    dash.activate_tab("annotate")
    page.wait_for_selector(Dashboard.pane_active("annotate"), state="visible")
    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    # <option>s are never "visible" to Playwright — wait on `attached`.
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='bob']", state="attached")

    assert page.eval_on_selector(Dashboard.ANN_BS_USER, "el => el.tagName") == "SELECT"
    assert page.get_attribute(Dashboard.ANN_BS_USER, "aria-required") == "true"
    bs_has_marker = page.eval_on_selector(
        Dashboard.ANN_BS_USER,
        "el => !!el.closest('label').querySelector('.required-marker')",
    )
    assert bs_has_marker, "#bsUser label should carry the required marker"
    dash.select_bs_user("alice")
    assert page.eval_on_selector(Dashboard.ANN_BS_USER, "el => el.value") == "alice"

    # --- Tuning tab: #tuneUser (optional section → no required marker) ---
    dash.activate_tab("tuning")
    page.wait_for_selector(Dashboard.pane_active("tuning"), state="visible")
    dash.reveal_details_for(Dashboard.TUNE_USER)
    page.wait_for_selector(f"{Dashboard.TUNE_USER} option[value='bob']", state="attached")

    assert page.eval_on_selector(Dashboard.TUNE_USER, "el => el.tagName") == "SELECT"
    assert page.get_attribute(Dashboard.TUNE_USER, "aria-required") is None
    tune_has_marker = page.eval_on_selector(
        Dashboard.TUNE_USER,
        "el => !!el.closest('label').querySelector('.required-marker')",
    )
    assert not tune_has_marker, "#tuneUser is in an optional section — no marker"
    dash.select_tune_user("bob")
    assert page.eval_on_selector(Dashboard.TUNE_USER, "el => el.value") == "bob"

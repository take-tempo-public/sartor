"""Regression: a "Start new tailoring" affordance clears the run without a refresh.

Bug: once a user walked into the tailoring wizard there was no way to start a
fresh JD run — the JD, analysis, and downstream state persisted, and the only
way to begin again was a full browser refresh (grep for
``newApplication|resetWizard|startOver`` in ``static/app.js`` returned nothing).

Fix: ``startNewTailoring()`` (button ``#btnNewTailoring`` under the wizard rail,
revealed by ``wizardInit()``) clears the JD input + analysis view, resets the
clarify/iteration state, drops the server handles, and snaps the wizard back to
Step 1 for the SAME user — corpus untouched.

LLM-free: seeds a user + one experience directly and drives only the Step-1
input; no analyzer entry points are hit. The ``page`` fixture's sentinel also
proves no JS error / no 5xx on the flow.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Wizard


@pytest.mark.ux
@pytest.mark.slow
def test_start_new_tailoring_clears_jd_and_returns_to_step_1(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    # Non-empty corpus so selecting alice lands on Tailor (engages the wizard).
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    # The wizard engaged → the reset affordance is present and visible.
    page.wait_for_selector(Wizard.NEW_TAILORING_BUTTON, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    # Type a JD (Step 1 input).
    page.fill(Wizard.JD_TEXT, "Senior Product Manager — robotics platform. Ship hardware+software.")
    assert page.eval_on_selector(Wizard.JD_TEXT, "el => el.value") != ""

    # Click "Start new tailoring" → JD cleared, wizard back on Step 1 (JD panel).
    page.click(Wizard.NEW_TAILORING_BUTTON)
    page.wait_for_function(
        "() => document.getElementById('jdText').value === ''",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    assert page.eval_on_selector(Wizard.JD_TEXT, "el => el.value") == ""

    # Step 1 is the active wizard step (its rail button carries `.active`).
    step1 = Wizard.step_button(1)
    page.wait_for_selector(f"{step1}.active", state="attached", timeout=DEFAULT_TIMEOUT_MS)
    # Forward steps are re-locked (no analysis) — Step 3 is disabled again.
    assert page.eval_on_selector(Wizard.step_button(3), "el => el.disabled") is True

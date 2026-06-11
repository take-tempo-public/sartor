"""Regression: "Continue to Clarify →" initiates clarification in one action.

Closes finding #6 (fix/clarify-double-question, 2026-06-11): the analyze→clarify
gate asked the clarify-vs-skip choice twice. The analysis panel already presents
it ("Continue to Clarify →" / "Skip to Compose →"), but clicking "Continue to
Clarify" only navigated to Step 2 and showed the #clarifyStartRow row — a SECOND
"Get clarifying questions / Skip" choice. The fix makes the CTA fetch + render
the questions directly, bypassing #clarifyStartRow on that path.

This test drives the live wizard through analyze → "Continue to Clarify" and
asserts the clarifying questions appear WITHOUT a second click, and that the
redundant #clarifyStartRow row is hidden. The clarify LLM call is stubbed
(`fake_clarify`), so the real /api/clarify route runs (persisting questions onto
the context) while staying deterministic + offline.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardClarifyPage,
    WizardJobPage,
)
from ui_pages.selectors import Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


@pytest.mark.ux
@pytest.mark.slow
def test_continue_to_clarify_initiates_clarify_directly(
    page: Page, live_server: str, ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    # ONE action: the CTA navigates to Step 2 AND fetches the questions.
    clarify = WizardClarifyPage(page, live_server)
    WizardJobPage(page, live_server).continue_to_clarify()
    clarify.wait_for_questions()  # textareas appear with no #btnClarify click

    # The questions rendered directly...
    assert page.locator(Wizard.CLARIFY_QUESTION_TEXTAREA).count() >= 2
    # ...and the redundant second clarify/skip prompt is gone (the crux of #6).
    assert page.locator(Wizard.CLARIFY_START_ROW).is_hidden()

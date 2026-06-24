"""Regression: wizard-flow polish — KW5 (auto-scroll) + KW8 (copy alignment).

fix/wizard-flow-polish (Sprint 6.1, final row; findings KW5 + KW8 from the v1.0.5
walkthrough harvest):

- KW5: clicking the post-generation "Get follow-up questions" button rendered the
  iteration-interview questions *below the fold*, so it looked like nothing
  happened. `runIterateClarify()` now scrolls `#iterateClarifyArea` into view in
  its success path.
- KW8: the button + divider used "interview" wording inconsistent with the
  clarify vocabulary. They now read "Get follow-up questions" / "Follow-up
  clarification".

Two tests, matching the suite's split between cheap copy guards and full-drive
flow tests:

1. `test_iterate_clarify_copy_uses_followup_language` — cheap, no pipeline: the
   labels are static DOM, so read them with `text_content()` compared
   case-insensitively (the labels are CSS `text-transform:uppercase`, so
   `inner_text()` would return uppercased — see the same idiom in
   `test_20260611_step4_template_copy.py`).

2. `test_iterate_clarify_questions_scroll_into_view` — full real-route drive
   (analyze → compose → template → generate → click), with the four LLM entry
   points stubbed (`install_llm_stubs` now also stubs generate + iterate-clarify).
   The scroll is verified deterministically by spying on
   `Element.prototype.scrollIntoView` — proving the fix fired on
   `#iterateClarifyArea` without depending on smooth-scroll timing or viewport
   geometry (which would make a `to_be_in_viewport` check flaky or trivially
   passing on a short page).
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
    WizardComposePage,
    WizardGeneratePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.selectors import Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


@pytest.mark.ux
def test_iterate_clarify_copy_uses_followup_language(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
) -> None:
    """KW8: the iteration-interview button + divider use the clarify vocabulary,
    not 'interview'. Static DOM, so no wizard drive is needed."""
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    # text_content() (not inner_text()) — the labels are text-transform:uppercase,
    # and these elements live inside the still-hidden #refinementArea.
    btn = (page.locator(Wizard.ITERATE_CLARIFY_BUTTON).text_content() or "").lower()
    assert "follow-up questions" in btn, f"button copy not aligned: {btn!r}"
    assert "interview" not in btn, f"stale 'interview' wording in button: {btn!r}"

    divider = (page.locator(Wizard.ITERATE_CLARIFY_DIVIDER_LABEL).text_content() or "").lower()
    assert "follow-up clarification" in divider, f"divider copy not aligned: {divider!r}"
    assert "interview" not in divider, f"stale 'interview' wording in divider: {divider!r}"


@pytest.mark.ux
@pytest.mark.slow
def test_iterate_clarify_questions_scroll_into_view(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KW5: clicking 'Get follow-up questions' scrolls the revealed section into
    view. Drives the real wizard through generate (LLM-stubbed), then verifies the
    scroll by spying on scrollIntoView."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    # analyze → Compose (skip-to-compose fires the stubbed recommend) → Template.
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open().continue_to_template()

    # Template → Generate. Mirror the proven screenshot-script sequence: pick a
    # persona and let the (deterministic) live preview render before continuing.
    template = WizardTemplatePage(page, live_server)
    template.pick_template(1)
    template.wait_live_preview()
    template.continue_to_generate()

    # Generate (stubbed LLM, but the real deterministic generate_resume + context
    # persistence run) → lands on the Output panel with iteration >= 1.
    WizardGeneratePage(page, live_server).generate()

    # Spy on scrollIntoView so the assertion is deterministic — no dependence on
    # smooth-scroll timing or page height. Records the id of every scrolled element.
    page.evaluate(
        """() => {
            window.__scrolledIds = [];
            const orig = Element.prototype.scrollIntoView;
            Element.prototype.scrollIntoView = function (opts) {
                if (this.id) window.__scrolledIds.push(this.id);
                return orig.call(this, opts);
            };
        }"""
    )

    page.click(Wizard.ITERATE_CLARIFY_BUTTON)
    page.wait_for_selector(Wizard.ITERATE_CLARIFY_QUESTION_TEXTAREA, state="visible")

    scrolled = page.evaluate("() => window.__scrolledIds")
    assert "iterateClarifyArea" in scrolled, (
        "KW5: clicking 'Get follow-up questions' must scroll the revealed "
        f"follow-up section into view; scrolled element ids were {scrolled!r}"
    )

    # KW8 in-context: the rendered section uses the follow-up wording.
    divider = (page.locator(Wizard.ITERATE_CLARIFY_DIVIDER_LABEL).text_content() or "").lower()
    assert "follow-up clarification" in divider, f"divider copy not aligned: {divider!r}"

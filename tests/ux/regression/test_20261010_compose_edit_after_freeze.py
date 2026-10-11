"""Regression: a Compose edit after Save and continue re-locks Generate (items 106/66/132).

fix/frozen-composition-staleness. The server half is pinned by
tests/test_frozen_composition_staleness.py + tests/test_composition_staleness.py; this
drives the client half the diagnosis could only read from code
(docs/dev/diagnosis/frozen-composition-staleness.md, `## Inferred`):

1. `test_post_freeze_bullet_edit_locks_generate_until_reapproved` — freeze, come back
   to Compose (no edit: Step 5 must stay open — the false-stale guard), edit a bullet
   from Compose: Step 5 locks with the "approve your changes" reason and the notice
   shows; Save and continue re-approves and unlocks.
2. `test_frozen_followup_answers_go_to_compose_not_regenerate` — item 132: on an
   approved composition the follow-up submit reads "Save answers and revise in
   Compose", lands on Compose with the answers banner, and sends no generate request.

Waits are on the elements this fix renders, never on the shared toast (item 159).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

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
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Compose, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


def _analyze_and_freeze(page: Page, live_server: str) -> WizardComposePage:
    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()
    compose.continue_to_template()
    return compose


@pytest.mark.ux
def test_post_freeze_bullet_edit_locks_generate_until_reapproved(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    compose = _analyze_and_freeze(page, live_server)
    base = BasePage(page, live_server)
    expect(base.rail_step(5)).to_be_enabled(timeout=DEFAULT_TIMEOUT_MS)

    # Back to Compose with no edit: the approval must still stand.
    compose.reload()
    expect(base.rail_step(5)).to_be_enabled()
    expect(page.locator(Compose.STALE_NOTICE)).to_be_hidden()

    # Edit a bullet's text from Compose.
    page.locator(Compose.BULLET_EDIT).first.click()
    field = page.locator(Compose.FORM_MODAL_TEXT_INPUT)
    field.fill("Reduced Kubernetes p99 latency 45% across 12 services")
    page.click(Compose.FORM_MODAL_SUBMIT)

    expect(page.locator(Compose.STALE_NOTICE)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    expect(base.rail_step(5)).to_be_disabled()
    title = (base.rail_step(5).get_attribute("title") or "").lower()
    assert "approve" in title, f"Step 5 lock should say why (re-approve): {title!r}"

    # Save and continue re-approves: Step 5 opens, the notices go away.
    compose.continue_to_template()
    expect(base.rail_step(5)).to_be_enabled(timeout=DEFAULT_TIMEOUT_MS)
    expect(page.locator(Wizard.TEMPLATE_STALE_NOTICE)).to_be_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_frozen_followup_answers_go_to_compose_not_regenerate(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    _analyze_and_freeze(page, live_server)
    template = WizardTemplatePage(page, live_server)
    template.pick_template(1)
    template.wait_live_preview()
    template.continue_to_generate()
    WizardGeneratePage(page, live_server).generate()

    page.click(Wizard.ITERATE_CLARIFY_BUTTON)
    page.wait_for_selector(Wizard.ITERATE_CLARIFY_QUESTION_TEXTAREA, state="visible")
    submit = page.locator(Wizard.SUBMIT_ITERATE_CLARIFICATIONS)
    label = (submit.text_content() or "").lower()
    assert "revise in compose" in label, f"frozen app should route answers to Compose: {label!r}"

    generate_requests: list[str] = []
    page.on(
        "request",
        lambda req: generate_requests.append(req.url) if "/api/generate" in req.url else None,
    )
    page.locator(Wizard.ITERATE_CLARIFY_QUESTION_TEXTAREA).first.fill(
        "It cut p99 latency by 45 percent."
    )
    submit.click()

    expect(page.locator(Wizard.PANEL_COMPOSE)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    expect(page.locator(Compose.ANSWERS_BANNER)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    assert generate_requests == [], f"no regenerate on an approved composition: {generate_requests}"

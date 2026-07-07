"""Regression: Compose authors the 2-sentence positioning summary (D2).

Generation-experience re-architecture (fix/compose-frozen-composition). LLM-free
(the analyzer's draft_positioning_summary is stubbed; the real routes run):

- The Compose positioning card carries an editable drafted-summary textarea.
- On arrival the summary auto-drafts once (D2) — the textarea fills with the
  stubbed 2-sentence summary via the real POST /draft-summary + GET re-read.
- A hand-edit persists through the /composition POST + GET round-trip (the
  wholesale-rebuild clobber invariant: summary_text rides along on every save)
  and survives an away-and-back reload.
"""

from __future__ import annotations

import re
from types import ModuleType

import pytest
from playwright.sync_api import Page, Response, expect

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


def _reach_compose(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_compose_summary_draft_autofills_edits_and_persists(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # D2 — the summary auto-drafts once on arrival; the textarea fills with the
    # stubbed 2-sentence draft (expect() retries until the async draft lands).
    draft = page.locator(Compose.POSITIONING_DRAFT)
    expect(draft).to_have_value(re.compile(r"Stubbed positioning summary"))

    # Hand-edit → the oninput debounced autosave POSTs the new summary_text.
    with page.expect_response(_is_composition_post):
        draft.fill("My own hand-written summary. Two concrete sentences here.")

    # Away + back: the edited draft survives (persisted in composition_overrides,
    # rehydrated by the GET). The auto-draft does NOT overwrite it (has_draft).
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    expect(page.locator(Compose.POSITIONING_DRAFT)).to_have_value(
        "My own hand-written summary. Two concrete sentences here."
    )

    # Retire clears the draft (falls back to saved positioning).
    page.locator(Compose.POSITIONING_DRAFT_RETIRE).click()
    expect(page.locator(Compose.POSITIONING_DRAFT)).to_have_value("")

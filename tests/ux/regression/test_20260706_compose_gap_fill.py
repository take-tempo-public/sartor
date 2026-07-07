"""Regression: Compose authors gap-fill bullets (Phase 3, per-role accept/retire).

Generation-experience re-architecture (fix/compose-frozen-composition). LLM-free
(analyzer.draft_gap_fill_bullets is stubbed to return ONE proposal on the first
experience; the real routes run):

- On arrival the gap-fill lane auto-drafts once (D2) — a "Suggested for this JD"
  row with Accept / Retire renders via the real POST /draft-gap-fill + GET re-read.
- Accept → the proposal becomes a real (pending) bullet folded into this
  application's composition; the lane row goes away and the bullet renders in the
  card. accepted_generated_bullet_ids rides the wholesale /composition save (the
  clobber invariant), so it survives Save-and-continue's freeze.
- Retire → the proposal is dropped and does NOT re-appear on reload (the server
  has_gap_fill key stays present, so the auto-fire latch never re-drafts it).
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
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
_STUB_TEXT = "Stubbed gap-fill bullet"


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
def test_gap_fill_autofills_accept_persists_and_freezes(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # D2 — the lane auto-fills once; the stubbed proposal renders with Accept/Retire
    # (expect() retries until the async draft + GET re-read land).
    row = page.locator(Compose.GAP_FILL_ROW).first
    expect(row).to_be_visible()
    expect(row).to_contain_text(_STUB_TEXT)

    # Accept → the proposal becomes a real bullet in the card; the lane row goes.
    row.locator(Compose.GAP_FILL_ACCEPT).click()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)
    expect(page.locator(Compose.LIST)).to_contain_text(_STUB_TEXT)

    # Survives an away-and-back reload; the retired-from-list proposal doesn't
    # re-appear (has_gap_fill key present → no re-draft).
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    expect(page.locator(Compose.LIST)).to_contain_text(_STUB_TEXT)
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # Clobber invariant: accepted_generated_bullet_ids rides the wholesale
    # /composition save (freeze on continue), so the accepted bullet is preserved.
    with page.expect_request(lambda r: "/composition" in r.url and r.method == "POST") as req_info:
        compose.continue_to_template()
    body = req_info.value.post_data_json or {}
    assert body.get("accepted_generated_bullet_ids"), body


@pytest.mark.ux
@pytest.mark.slow
def test_gap_fill_retire_drops_and_no_reappear(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    row = page.locator(Compose.GAP_FILL_ROW).first
    expect(row).to_be_visible()
    expect(row).to_contain_text(_STUB_TEXT)

    # Retire → the row goes; no bullet is created.
    row.locator(Compose.GAP_FILL_RETIRE).click()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # Away and back: the retired proposal does NOT re-appear (server has_gap_fill
    # stays true, so the auto-fire latch never re-drafts it).
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

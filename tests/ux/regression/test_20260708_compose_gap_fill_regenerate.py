"""Regression: the regenerate-gap-fill affordance + durable retirals
(feat/regenerate-gap-fill, LATER-branch remainder item (d)).

Generation-experience re-architecture. LLM-free (analyzer.draft_gap_fill_bullets
is stubbed to return ONE deterministic proposal — same experience id, same text
— on every call; the real routes run):

- The always-visible "Regenerate suggestions" control renders above the per-role
  gap-fill lanes once experiences exist.
- Retire a proposal, then click Regenerate: because the stub is deterministic
  (identical text on the same experience -> identical stable key), a naive
  re-draft would resurface the exact row that was just retired. It does NOT —
  proving the durable composition_overrides.retired_gap_fill_keys filter (not
  just the once-only auto-fire latch the existing 20260706 regression covers).
- The retired key survives a composition save (the wholesale-rebuild clobber
  invariant every other override key follows): it rides the /composition POST
  body on Save-and-continue.
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
def test_regenerate_control_visible_and_retired_row_never_resurfaces(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # The manual Regenerate control is always visible once experiences exist.
    expect(page.locator(Compose.GAP_FILL_REGEN)).to_be_visible()

    row = page.locator(Compose.GAP_FILL_ROW).first
    expect(row).to_be_visible()
    expect(row).to_contain_text(_STUB_TEXT)

    row.locator(Compose.GAP_FILL_RETIRE).click()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # Explicit Regenerate — a THIRD context-writing firing path (alongside the
    # summary draft + skills recommend), serialized through the same
    # data-compose-bg-pending counter. The stub is deterministic (same eid+text
    # -> same key every call), so a naive re-draft WOULD resurface the exact
    # retired row — the durable retired_gap_fill_keys filter is what stops it.
    page.locator(Compose.GAP_FILL_REGEN).click()
    expect(page.locator(Compose.SETTLED)).to_be_visible()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # A second regenerate for good measure — still never resurfaces.
    page.locator(Compose.GAP_FILL_REGEN).click()
    expect(page.locator(Compose.SETTLED)).to_be_visible()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # The retiral survives the wholesale-rebuild clobber: rides the /composition
    # POST body on Save-and-continue (the same invariant accepted_generated_
    # bullet_ids already proves in the 20260706 regression).
    with page.expect_request(lambda r: "/composition" in r.url and r.method == "POST") as req_info:
        compose.continue_to_template()
    body = req_info.value.post_data_json or {}
    assert body.get("retired_gap_fill_keys"), body


@pytest.mark.ux
@pytest.mark.slow
def test_regenerate_survives_reload(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    row = page.locator(Compose.GAP_FILL_ROW).first
    expect(row).to_be_visible()
    row.locator(Compose.GAP_FILL_RETIRE).click()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

    # Retire persists directly (no composition save needed) — an away-and-back
    # reload still excludes it AND a Regenerate on the reloaded page still does
    # not resurface it (retired_gap_fill_keys is server-durable, not just the
    # session-local mirror).
    compose.reload()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)
    page.locator(Compose.GAP_FILL_REGEN).click()
    expect(page.locator(Compose.SETTLED)).to_be_visible()
    expect(page.locator(Compose.GAP_FILL_ROW)).to_have_count(0)

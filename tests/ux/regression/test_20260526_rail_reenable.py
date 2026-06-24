"""Regression: the wizard rail unlocks Step 2 after a successful Analyze.

Bug (2026-05-26, RELEASE_CHECKLIST / commit aa211a2): rail step buttons
didn't re-enable after the prior step completed — the user had to click the
in-flow Continue button to refresh the rail. The fix re-renders the rail
(`_wizardRender`) in the analyze success path once `lastContextPath` is set.

LLM-free: `analyze_streaming` + `recommend_*` are stubbed; the route still
builds the context, writes the file, and creates the application row.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardJobPage

_JD = "Senior Backend Engineer — Kafka, Postgres, AWS. Lead a platform team."


@pytest.mark.ux
@pytest.mark.slow
def test_step2_rail_unlocks_after_analyze(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    job = WizardJobPage(page, live_server).open()

    rail = BasePage(page, live_server)
    assert not rail.rail_step_enabled(2), "Step 2 should be locked before analyze"

    job.analyze(_JD)

    assert rail.rail_step_enabled(2), "Step 2 should unlock after analyze (rail re-render)"

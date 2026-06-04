"""Walk A — the LLM-stubbed happy path (the v1.0.5 "≥1 happy-path-stubbed").

Walks the front half of the wizard end-to-end with the analyzer fully
stubbed: Step 1 (paste JD → Analyze) → Step 2 unlocks → Step 3 (Compose
renders the fit-ranked corpus) → Step 4 (template preview iframe loads).

It deliberately stops before Generate: the generate `done` handler drives
real document rendering + ATS + DB persist (and `.pdf` nests Chromium inside
the server) — the output surface is covered LLM-free by Walk B
(`test_output_surface_seeded.py`) via the prior-app-resume path instead.

The console + 5xx sentinel (conftest) asserts a clean walk on teardown.
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
    WizardJobPage,
    WizardTemplatePage,
)

_JD = (
    "Senior Backend Engineer, Platform. Python on Postgres + AWS with Kafka "
    "as the event backbone. Lead architecture reviews; mentor a team of 6."
)


@pytest.mark.ux
@pytest.mark.slow
def test_happy_path_through_template_preview(page: Page, live_server: str,
                                             ux_app: ModuleType,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    compose = WizardComposePage(page, live_server).open()
    assert compose.experience_card_count() >= 1

    template = WizardTemplatePage(page, live_server).open()
    assert template.template_option_count() >= 1

"""Shared, framework-free Page Object Model for the callback. wizard UI.

Single source of truth for how both the Playwright UX test suite
(`tests/ux/`) and the screenshot script (`scripts/capture_screenshots.py`)
drive the app. Navigation + selectors live here; test assertions and
screenshot capture stay in their respective callers.

`base_url` is **injected** into every POM (the test suite uses an ephemeral
port; the screenshot script uses :5000) — POMs never hardcode the host.

Redesign-resilience is a first-class constraint here (decided 2026-06-04):
selectors are centralized in `ui_pages.selectors`, anchored to stable IDs /
ARIA roles, never styling-only CSS classes or display copy. On a reskin,
`selectors.py` is the one file to edit.
"""

from __future__ import annotations

from ui_pages.base import BasePage
from ui_pages.corpus import CorpusPage
from ui_pages.dashboard_console import DashboardConsolePage
from ui_pages.prior_apps import PriorAppsPage
from ui_pages.user_picker import UserPickerPage
from ui_pages.wizard_clarify import WizardClarifyPage
from ui_pages.wizard_compose import WizardComposePage
from ui_pages.wizard_generate import WizardGeneratePage
from ui_pages.wizard_job import WizardJobPage
from ui_pages.wizard_output import WizardOutputPage
from ui_pages.wizard_template import WizardTemplatePage

__all__ = [
    "BasePage",
    "CorpusPage",
    "DashboardConsolePage",
    "PriorAppsPage",
    "UserPickerPage",
    "WizardClarifyPage",
    "WizardComposePage",
    "WizardGeneratePage",
    "WizardJobPage",
    "WizardOutputPage",
    "WizardTemplatePage",
]

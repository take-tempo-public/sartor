"""Live runtime check for the _announce() ARIA live region — PX-29 (F-expa11y-08).

The static floor (`tests/test_a11y_floor_guards.py`) proves the #srAnnounce region,
the _announce() helper, and its call sites exist in source. This adds the runtime
fidelity the review's "no test guards it" gap really wants: drive a real analysis to
completion in a browser and assert the polite live region actually receives the
announcement a screen-reader user would hear.

Chromium-gated like the rest of `tests/ux/` — skips cleanly when the binary is
absent, so the always-runs static guard remains the reliable floor.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardJobPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import LiveRegion

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


@pytest.mark.ux
def test_announce_fires_on_analysis_complete(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After Analyze renders, runAnalysis() calls _announce('Analysis complete…');
    the polite #srAnnounce region should carry that text for assistive tech.

    _announce() clears then re-sets textContent on a 16ms tick (so identical
    messages re-announce), which Playwright's auto-retrying to_contain_text absorbs.
    sr-only is visually hidden but NOT hidden for a text assertion, so no
    visibility wait is needed."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # non-empty corpus → smart-landing reaches Tailor
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    region = page.locator(LiveRegion.ANNOUNCER)
    expect(region).to_contain_text("Analysis complete", timeout=DEFAULT_TIMEOUT_MS)

"""Regression: the Résumé-templates copy must match the real bundled set.

Walk finding #8 (v1.0.5 walk-through), fixed on fix/step4-template-copy
(Sprint 6.1). Migration 0005 curated the bundled persona templates from 5 → 4
at v1.0.0 (dropped Compact — its sidebar HTML was ATS-unsafe — and renamed
Hybrid Tech → Tech), but the Résumé-templates settings copy kept claiming
"Five bundled ATS-safe templates ship with the app." The data-layer count is
already pinned by tests/test_bundled_templates.py (the migration settles at 4
bundled rows); this guards the *copy* against drifting from the rendered set —
the gap that finding #8 was about.

The Step-4 picker line "Same content, different typography and layout" was
verified accurate during this fix — the 4 templates genuinely differ (2 serif
/ 2 sans, Modern's blue header band, Tech's float two-column item rows, varied
margins and heading treatments) — and is intentionally left unchanged.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_user
from ui_pages import BasePage, UserPickerPage
from ui_pages.selectors import TopTabs

_BUNDLED_CARD = "#personaBundledGrid .persona-card"
_HINT = "#personasHint"

# The v1.0.0-curated bundled set (see migration 0005 + the canonical
# tests/test_bundled_templates.py). Kept here as the count the copy must agree
# with, so a future re-curation that changes the set fails loudly on BOTH the
# rendered cards and the prose.
_EXPECTED_BUNDLED = 4


@pytest.mark.ux
def test_personas_copy_matches_bundled_count(
    page: Page, live_server: str, ux_app: ModuleType,
) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    # Open the Résumé-templates settings tab → switchTopTab('personas')
    # fires _personaTabActivated → _loadBundledPersonas (GET /api/personas/bundled).
    page.click(TopTabs.PERSONAS)
    page.wait_for_selector(_BUNDLED_CARD, state="visible")

    rendered = page.locator(_BUNDLED_CARD).count()
    assert rendered == _EXPECTED_BUNDLED, (
        f"expected {_EXPECTED_BUNDLED} bundled templates, rendered {rendered}"
    )

    # The settings copy must state the real count — not the stale "Five".
    # Read raw DOM text (text_content) and compare case-insensitively: the
    # panel applies `text-transform: uppercase`, so inner_text would render
    # "FOUR" and the source casing is what we actually want to guard.
    hint = (page.locator(_HINT).text_content() or "").lower()
    assert "five" not in hint, f"stale bundled-template count in copy: {hint!r}"
    assert "four" in hint, (
        f"copy should state the real bundled count (four): {hint!r}"
    )

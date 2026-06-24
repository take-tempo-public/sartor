"""Regression: the Corpus tab renders experience cards on first load.

Bug (2026-05-26, RELEASE_CHECKLIST): the Corpus tab silently failed to
render cards after refresh (a JS exception in the render path, downstream of
the personas-500 thread-race). The console-error sentinel is the load-bearing
guard here — the original failure was silent, so a "cards present + no JS
error" assertion is exactly what would have caught it.

LLM-free: corpus is seeded directly into the DB.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage


@pytest.mark.ux
@pytest.mark.slow
def test_corpus_tab_renders_cards(page: Page, live_server: str, ux_app: ModuleType) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open().wait_for_cards()

    # Cards present (not a silent empty render) — and the teardown sentinel
    # proves no JS exception fired in the render path.
    assert corpus.card_count() >= 1

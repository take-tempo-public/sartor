"""Regression: the corpus import control reads "+ Import résumé".

Bug (2026-05-26, RELEASE_CHECKLIST): doc-vs-UI label drift on the corpus
import button (was "+ Drop résumé (AI extract)"). Pins the user-facing
label so a future edit can't silently drift it back.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage


@pytest.mark.ux
@pytest.mark.slow
def test_import_resume_button_label(page: Page, live_server: str,
                                    ux_app: ModuleType) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    corpus = CorpusPage(page, live_server).open()
    btn = corpus.import_button()
    expect(btn).to_be_visible()
    expect(btn).to_contain_text("Import résumé")

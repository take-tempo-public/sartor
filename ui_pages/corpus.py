"""CorpusPage — the Career Corpus tab."""

from __future__ import annotations

from playwright.sync_api import Locator

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Corpus, TopTabs


class CorpusPage(BasePage):
    def open(self) -> CorpusPage:
        self.page.click(TopTabs.CORPUS)
        self.page.wait_for_selector(
            Corpus.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        return self

    def wait_for_cards(self) -> CorpusPage:
        """Wait for the (async) corpus render to produce at least one card.
        Times out if cards never appear — which is exactly the silent
        render-failure this guards against."""
        self.page.wait_for_selector(Corpus.CARD, timeout=DEFAULT_TIMEOUT_MS)
        return self

    def card_count(self) -> int:
        return self.page.locator(Corpus.CARD).count()

    def import_button(self) -> Locator:
        return self.page.locator(Corpus.PANEL).get_by_role(
            "button", name=Corpus.IMPORT_BUTTON_NAME
        )

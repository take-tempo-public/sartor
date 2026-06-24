"""CorpusPage — the Career Corpus tab."""

from __future__ import annotations

from playwright.sync_api import Locator

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Corpus, TopTabs


class CorpusPage(BasePage):
    def open(self) -> CorpusPage:
        self.page.click(TopTabs.CORPUS)
        self.page.wait_for_selector(Corpus.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
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
        return self.page.locator(Corpus.PANEL).get_by_role("button", name=Corpus.IMPORT_BUTTON_NAME)

    # β.6e summary-variants editor (#2 — the Add-variant affordance).
    def summary_variants_section(self) -> Locator:
        return self.page.locator(Corpus.SUMMARY_VARIANTS_SECTION)

    def add_variant_button(self) -> Locator:
        return self.page.locator(Corpus.SUMMARY_VARIANTS_SECTION).get_by_role(
            "button", name=Corpus.ADD_VARIANT_BUTTON_NAME
        )

    # KW2 — onboarding banner + corpus-wide accept-all control.
    def onboarding_banner(self) -> Locator:
        return self.page.locator(Corpus.ONBOARDING_BANNER)

    def accept_all_button(self) -> Locator:
        return self.page.locator(Corpus.ONBOARDING_BANNER).get_by_role(
            "button", name=Corpus.ACCEPT_ALL_BUTTON_NAME
        )

    # Sprint 6.4 (#16/#1) — review-finished "Start tailoring →" hand-off CTA.
    def start_tailoring_button(self) -> Locator:
        return self.page.locator(Corpus.START_TAILORING_BUTTON)

    # B.4 (Sprint 6.6) — per-role intro variants editor (expand a card first).
    def expand_card(self, index: int = 0) -> CorpusPage:
        self.page.locator(Corpus.CARD).nth(index).locator(".corpus-card-header").click()
        self.page.wait_for_selector(
            Corpus.EXP_SUMMARY_SECTION, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        return self

    def exp_summary_section(self) -> Locator:
        return self.page.locator(Corpus.EXP_SUMMARY_SECTION)

    def add_intro_button(self) -> Locator:
        return self.page.locator(Corpus.EXP_SUMMARY_SECTION).get_by_role(
            "button", name=Corpus.ADD_INTRO_BUTTON_NAME
        )

    def intro_texts(self) -> list[str]:
        """The intro variant textareas' values (not inner text — they're
        <textarea>, so the text lives in .value)."""
        locs = self.page.locator(f"{Corpus.EXP_SUMMARY_SECTION} .summary-variant-text")
        return [locs.nth(i).input_value() for i in range(locs.count())]

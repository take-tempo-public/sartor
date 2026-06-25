"""DashboardConsolePage — drives the /_dashboard diagnostics console.

The console is a four-tab bento of summary tiles; clicking a tile opens one
shared right-hand drawer with that tile's detail. Selectors live in
`ui_pages.selectors.Dashboard` (one-file edit on a reskin).
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import Locator

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Dashboard, Help


class DashboardConsolePage(BasePage):
    def load(self) -> DashboardConsolePage:
        """Navigate to /_dashboard/ and wait for the tab bar."""
        self.page.goto(f"{self.base_url}/_dashboard/")
        self.page.wait_for_selector(Dashboard.TABS, timeout=DEFAULT_TIMEOUT_MS)
        return self

    # --- tabs --------------------------------------------------------------
    def tab(self, name: str) -> Locator:
        return self.page.locator(Dashboard.tab(name))

    def activate_tab(self, name: str) -> None:
        self.tab(name).click()

    def active_pane(self, name: str) -> Locator:
        return self.page.locator(Dashboard.pane_active(name))

    # --- per-tab help (Sprint 6.5 education) --------------------------------
    # The console carries its own PORT of the help primitive; each tab's
    # (i)-circle and its #helpModal reuse the wizard's ids/classes, so the shared
    # `Help` selectors apply. Maps the tab name to its help block id.
    _HELP_ID: ClassVar[dict[str, str]] = {
        "pipeline": "dashPipeline",
        "quality": "dashQuality",
        "groundedness": "dashGroundedness",
        "tuning": "dashTuning",
        "annotate": "dashAnnotate",
    }

    def help_icon(self, tab: str) -> Locator:
        return self.page.locator(Help.icon(self._HELP_ID[tab]))

    def open_help(self, tab: str) -> None:
        self.help_icon(tab).click()

    def help_modal(self) -> Locator:
        return self.page.locator(Help.MODAL)

    def close_help(self) -> None:
        self.page.locator(Help.CLOSE).click()

    # --- tiles + detail panel ----------------------------------------------
    def tile(self, detail: str) -> Locator:
        """First tile bound to a given detail block (a detail may back >1 tile)."""
        return self.page.locator(Dashboard.tile(detail)).first

    def open_tile(self, detail: str) -> None:
        self.tile(detail).click()

    def detail_panel(self) -> Locator:
        return self.page.locator(Dashboard.DETAIL_PANEL)

    def detail_panel_open(self) -> Locator:
        """Matches only while the inline detail panel is open (not `[hidden]`)."""
        return self.page.locator(Dashboard.DETAIL_PANEL_OPEN)

    def detail_title(self) -> Locator:
        return self.page.locator(Dashboard.DETAIL_TITLE)

    def detail_body(self) -> Locator:
        return self.page.locator(Dashboard.DETAIL_BODY)

    def close_detail(self) -> None:
        self.page.locator(Dashboard.DETAIL_CLOSE).click()

    # --- annotate tab (read-write surface) ----------------------------------
    def fixture_select(self) -> Locator:
        return self.page.locator(Dashboard.ANN_FIXTURE_SELECT)

    def select_fixture(self, slug: str) -> None:
        """Pick a bootstrap by slug; loads its annotations into the editor."""
        self.fixture_select().select_option(slug)

    # --- candidate-username dropdowns (Sprint 6.3 #20-dropdown) --------------
    def reveal_details_for(self, selector: str) -> None:
        """Open the <details> ancestor of a control so it renders and is interactable.

        #bsUser / #tuneUser live inside collapsed sections.
        """
        self.page.locator(selector).evaluate(
            "el => { const d = el.closest('details'); if (d) d.open = true; }"
        )

    def bs_user_select(self) -> Locator:
        return self.page.locator(Dashboard.ANN_BS_USER)

    def select_bs_user(self, username: str) -> None:
        self.reveal_details_for(Dashboard.ANN_BS_USER)
        self.bs_user_select().select_option(username)

    def tune_user_select(self) -> Locator:
        return self.page.locator(Dashboard.TUNE_USER)

    def select_tune_user(self, username: str) -> None:
        self.reveal_details_for(Dashboard.TUNE_USER)
        self.tune_user_select().select_option(username)

    def editor(self) -> Locator:
        return self.page.locator(Dashboard.ANN_EDITOR)

    def bullet_items(self) -> Locator:
        return self.page.locator(f"{Dashboard.ANN_BULLETS} {Dashboard.ANN_ITEM}")

    def first_bullet_verdict(self) -> Locator:
        return self.bullet_items().first.locator("select")

    def set_first_bullet_verdict(self, verdict: str) -> None:
        self.first_bullet_verdict().select_option(verdict)

    def save(self) -> None:
        self.page.locator(Dashboard.ANN_SAVE).click()

    def collate(self) -> None:
        self.page.locator(Dashboard.ANN_COLLATE).click()

    def status(self) -> Locator:
        return self.page.locator(Dashboard.ANN_STATUS)

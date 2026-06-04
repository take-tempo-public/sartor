"""WizardComposePage — Step 3 (fit-ranked bullets, drag/keyboard reorder).

Order is read off the first experience's `.compose-bullet-list` (drawer rows
excluded). Both the keyboard (`Move bullet up/down`) and pointer-drag paths
end in the same debounced autosave POST `/composition`, so either proves the
persistence round-trip.
"""

from __future__ import annotations

from playwright.sync_api import Locator

from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import Compose, Wizard


class WizardComposePage(BasePage):
    def open(self) -> WizardComposePage:
        """First entry from the analysis panel via 'Skip to Compose →', which
        fires recommend_bullets so the curated set renders (and a saved custom
        order displays — the no-recommendations fallback re-sorts by score)."""
        self.page.wait_for_selector(
            Wizard.SKIP_TO_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.click(Wizard.SKIP_TO_COMPOSE)
        self._wait_loaded()
        return self

    def reload(self) -> WizardComposePage:
        """Re-enter Compose via the rail (re-fetches GET /composition);
        recommendations already persisted, so this is the reload-equivalent."""
        self.goto_step(3)
        self._wait_loaded()
        return self

    def _wait_loaded(self) -> None:
        self.page.wait_for_selector(
            Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.wait_for_load_state("networkidle")
        # The skip-to-compose path renders Compose twice (loadComposition runs
        # once before recommend, once after); networkidle can resolve in the
        # gap, so we wait on a `.recommended` bullet row — which only exists
        # after the post-recommend render — as the deterministic final-render
        # signal (avoids reading mid-clear). All compose-reaching tests stub
        # recommend to return the bullets, so a recommended row always appears.
        self.page.wait_for_selector(
            Compose.RECOMMENDED_ROW, timeout=DEFAULT_TIMEOUT_MS
        )

    def wait_cards(self) -> WizardComposePage:
        """Wait for compose cards to render (used after a clarify-submit
        lands on Compose, e.g. the screenshot script's full-flow path)."""
        self.page.wait_for_selector(
            Wizard.PANEL_COMPOSE, state="visible", timeout=LLM_TIMEOUT_MS
        )
        self.page.wait_for_selector(
            Compose.EXPERIENCE_CARD, timeout=LLM_TIMEOUT_MS
        )
        return self

    def continue_to_template(self) -> None:
        self.page.click(Wizard.SAVE_CONTINUE_TEMPLATE)
        self.page.wait_for_selector(
            Wizard.PANEL_TEMPLATE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )

    def experience_card_count(self) -> int:
        return self.page.locator(Compose.EXPERIENCE_CARD).count()

    # --- first experience's visible bullet list ----------------------------
    def _bullet_list(self) -> Locator:
        return self.page.locator(Compose.BULLET_LIST).first

    def _row(self, text: str) -> Locator:
        return self._bullet_list().locator(
            f":scope > {Compose.ROW}", has_text=text
        )

    def bullet_texts(self) -> list[str]:
        """Visible bullet texts in DOM (visual) order."""
        return self._bullet_list().locator(
            f":scope > {Compose.ROW} {Compose.ROW_TEXT}"
        ).all_inner_texts()

    def has_custom_order(self) -> bool:
        return self._bullet_list().get_attribute("data-custom-order") == "true"

    # --- reorder affordances (both autosave) -------------------------------
    def move_down(self, text: str) -> None:
        self._row(text).get_by_role("button", name=Compose.MOVE_DOWN_LABEL).click()

    def move_up(self, text: str) -> None:
        self._row(text).get_by_role("button", name=Compose.MOVE_UP_LABEL).click()

    def reset_order(self) -> None:
        self.page.locator(Compose.EXPERIENCE_CARD).first.locator(
            Compose.RESET_ORDER
        ).click()

    def drag_below(self, src_text: str, target_text: str) -> None:
        """Pointer-path reorder via dispatched native HTML5 DnD with a shared
        DataTransfer (Playwright's `drag_to` is unreliable for native DnD).
        `clientY` is set into the lower half of the target row so the list's
        `dragover` handler drops the source after it."""
        src = self._row(src_text)
        target_box = self._row(target_text).bounding_box()
        assert target_box is not None
        client_y = target_box["y"] + target_box["height"] - 2
        data_transfer = self.page.evaluate_handle("() => new DataTransfer()")
        list_loc = self._bullet_list()
        src.dispatch_event("dragstart", {"dataTransfer": data_transfer})
        list_loc.dispatch_event(
            "dragover", {"dataTransfer": data_transfer, "clientY": client_y}
        )
        list_loc.dispatch_event("drop", {"dataTransfer": data_transfer})
        src.dispatch_event("dragend", {"dataTransfer": data_transfer})

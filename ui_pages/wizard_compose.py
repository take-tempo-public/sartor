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
    """Page Object for Step 3 — fit-ranked bullets with drag/keyboard reorder."""

    def open(self) -> WizardComposePage:
        """Enter Compose from the analysis panel via 'Skip to Compose →'.

        Fires recommend_bullets so the curated set renders (and a saved custom
        order displays — the no-recommendations fallback re-sorts by score).
        """
        self.page.wait_for_selector(
            Wizard.SKIP_TO_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.click(Wizard.SKIP_TO_COMPOSE)
        self._wait_loaded()
        return self

    def reload(self) -> WizardComposePage:
        """Re-enter Compose via the rail (re-fetches GET /composition).

        Recommendations already persisted, so this is the reload-equivalent.
        """
        self.goto_step(3)
        self._wait_loaded()
        return self

    def _wait_loaded(self) -> None:
        """Wait until the Compose panel and its card tree have rendered (a sound 'compose ready' signal)."""
        self.page.wait_for_selector(
            Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.wait_for_load_state("networkidle")
        # `loadComposition()` (static/app.js) sets a loading placeholder, awaits
        # the /composition fetch, then `_clearChildren` + synchronously appends
        # the whole card tree (positioning + skills + experience cards) in one
        # tick — there is no awaited gap mid-render, so a rendered card is a
        # sound "compose ready" signal. Wait on `.compose-experience-card`, NOT a
        # `.recommended` bullet row: a recommended row only exists when recommend
        # marks a bullet, which the no-recommendations fixtures deliberately do
        # not — so the old wait raced on an element that may never appear (the
        # flaky-class root cause). A card always renders when the composition has
        # ≥1 experience. (Matches `wait_cards()`.)
        self.page.wait_for_selector(Compose.EXPERIENCE_CARD, timeout=DEFAULT_TIMEOUT_MS)

    def wait_cards(self) -> WizardComposePage:
        """Wait for compose cards to render after a clarify-submit lands on Compose.

        Used e.g. by the screenshot script's full-flow path.
        """
        self.page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=LLM_TIMEOUT_MS)
        self.page.wait_for_selector(Compose.EXPERIENCE_CARD, timeout=LLM_TIMEOUT_MS)
        return self

    def continue_to_template(self) -> None:
        """Click 'Save and continue to Template' and wait for the Template panel."""
        self.page.click(Wizard.SAVE_CONTINUE_TEMPLATE)
        self.page.wait_for_selector(
            Wizard.PANEL_TEMPLATE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )

    def experience_card_count(self) -> int:
        """Return the number of rendered experience cards."""
        return self.page.locator(Compose.EXPERIENCE_CARD).count()

    # --- titles (feat/compose-add-title) -----------------------------------
    def _first_card(self) -> Locator:
        """Locator for the first real experience card (excludes the positioning card)."""
        # The β.6c positioning card also carries `.compose-experience-card`, so
        # exclude it — `_first_card` is only ever about a real experience card.
        return self.page.locator(f"{Compose.EXPERIENCE_CARD}:not(.positioning-card)").first

    def title_texts(self) -> list[str]:
        """Eligible title texts on the first experience card."""
        return (
            self._first_card()
            .locator(f"{Compose.TITLE_LIST} {Compose.ROW} {Compose.ROW_TEXT}")
            .all_inner_texts()
        )

    def add_title(self, title: str) -> None:
        """Open the '+ Add title' modal on the first card and submit `title`.

        Waits for the reloaded composition to render it (writes a sourced,
        eligible corpus row via POST /api/experiences/<id>/titles).
        """
        self._first_card().locator(Compose.ADD_TITLE_BTN).click()
        self.page.fill(Compose.FORM_MODAL_TITLE_INPUT, title)
        self.page.click(Compose.FORM_MODAL_SUBMIT)
        # loadComposition() re-renders; wait for the new title row to appear.
        self._first_card().locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=title).wait_for(
            state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.wait_for_load_state("networkidle")

    def select_title(self, text: str) -> None:
        """Check the radio of the title row matching `text` (first card)."""
        self._first_card().locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=text).locator(
            Compose.TITLE_RADIO
        ).check()

    def title_is_selected(self, text: str) -> bool:
        """Whether the title row matching `text` (first card) is the chosen one."""
        return (
            self._first_card()
            .locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=text)
            .locator(Compose.TITLE_RADIO)
            .is_checked()
        )

    # --- per-role intros (B.4, Sprint 6.6) ---------------------------------
    def role_intros_toggle(self) -> Locator:
        """Return the 'Add role intros' toggle locator."""
        return self.page.locator(Compose.ROLE_INTROS_TOGGLE)

    def enable_role_intros(self) -> None:
        """Turn on the 'Add role intros' toggle and wait for the per-role picker.

        Waits for a role to default to its (stubbed) recommendation — the
        deterministic 'applied' signal.
        """
        self.role_intros_toggle().check()
        self.page.wait_for_selector(
            Compose.ROLE_INTRO_CHOSEN, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )

    def chosen_intro_texts(self) -> list[str]:
        """Text of every chosen role-intro variant (visual order)."""
        return self.page.locator(
            f"{Compose.ROLE_INTRO_CHOSEN} {Compose.ROW_TEXT}"
        ).all_inner_texts()

    # --- first experience's visible bullet list ----------------------------
    def _bullet_list(self) -> Locator:
        """Locator for the first experience's visible bullet list."""
        return self.page.locator(Compose.BULLET_LIST).first

    def _row(self, text: str) -> Locator:
        """Locator for the bullet row in the first list whose text matches ``text``."""
        return self._bullet_list().locator(f":scope > {Compose.ROW}", has_text=text)

    def bullet_texts(self) -> list[str]:
        """Visible bullet texts in DOM (visual) order."""
        return (
            self._bullet_list()
            .locator(f":scope > {Compose.ROW} {Compose.ROW_TEXT}")
            .all_inner_texts()
        )

    def has_custom_order(self) -> bool:
        """Whether the first bullet list carries a saved custom order."""
        return self._bullet_list().get_attribute("data-custom-order") == "true"

    # --- reorder affordances (both autosave) -------------------------------
    def move_down(self, text: str) -> None:
        """Click the 'Move bullet down' button on the row matching `text`."""
        self._row(text).get_by_role("button", name=Compose.MOVE_DOWN_LABEL).click()

    def move_up(self, text: str) -> None:
        """Click the 'Move bullet up' button on the row matching `text`."""
        self._row(text).get_by_role("button", name=Compose.MOVE_UP_LABEL).click()

    def reset_order(self) -> None:
        """Click the first card's reset-order control."""
        self.page.locator(Compose.EXPERIENCE_CARD).first.locator(Compose.RESET_ORDER).click()

    def drag_below(self, src_text: str, target_text: str) -> None:
        """Reorder via dispatched native HTML5 DnD with a shared DataTransfer.

        Playwright's `drag_to` is unreliable for native DnD. `clientY` is set
        into the lower half of the target row so the list's `dragover` handler
        drops the source after it.
        """
        src = self._row(src_text)
        target_box = self._row(target_text).bounding_box()
        assert target_box is not None
        client_y = target_box["y"] + target_box["height"] - 2
        data_transfer = self.page.evaluate_handle("() => new DataTransfer()")
        list_loc = self._bullet_list()
        src.dispatch_event("dragstart", {"dataTransfer": data_transfer})
        list_loc.dispatch_event("dragover", {"dataTransfer": data_transfer, "clientY": client_y})
        list_loc.dispatch_event("drop", {"dataTransfer": data_transfer})
        src.dispatch_event("dragend", {"dataTransfer": data_transfer})

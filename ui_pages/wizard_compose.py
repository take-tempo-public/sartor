"""WizardComposePage — Step 3 (fit-ranked bullets, drag/keyboard reorder).

Order is read off the first experience's `.compose-bullet-list` (drawer rows
excluded). Both the keyboard (`Move bullet up/down`) and pointer-drag paths
end in the same debounced autosave POST `/composition`, so either proves the
persistence round-trip.
"""

from __future__ import annotations

from playwright.sync_api import Locator, expect

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
        """Wait until the Compose panel and its terminal card tree have rendered.

        Delegates to :meth:`_wait_settled`, which rides out the auto-recommend
        re-render cascade. The old implementation waited only for the first
        ``.compose-experience-card`` to appear — i.e. the *initial* render — and a
        subsequent read raced the cascade's teardown (the flaky-class root cause).
        """
        self._wait_settled()

    def _wait_settled(self) -> None:
        """Wait until ``#composeList`` reached its terminal render (deterministic).

        The settle gate is ``Compose.SETTLED`` — ``data-compose-ready`` PRESENT and
        ``data-compose-bg-pending`` ABSENT.  ``loadComposition()`` (static/app.js)
        clears ``data-compose-ready`` at entry (before its fetch) and re-sets it after
        the final synchronous append; every reload-firing background call (the
        auto-recommend / draft-summary / gap-fill / role-recommend cascade AND the
        user-action pin/accept/review/add reloads) increments a
        ``data-compose-bg-pending`` counter attribute as its first synchronous
        statement — BEFORE that marker is re-set — and decrements it in a ``finally``.

        So the ONLY state with the marker present and the counter absent is the true
        terminal render with no reload queued or in flight: a single deterministic
        ``wait_for_selector`` on that combined condition replaces the old
        ``networkidle`` + hand-rolled marker-stability poll, which could settle on a
        non-terminal render in the window between a firing pass and its reload (the
        Compose flaky-test class — e.g. the positioning-pin clobber).  ``networkidle``
        is kept as a cheap pre-drain of unrelated in-flight XHRs.
        """
        self.page.wait_for_selector(
            Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS)

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
        """Return the number of rendered experience cards (waits for the render to settle)."""
        self._wait_settled()
        return self.page.locator(Compose.EXPERIENCE_CARD).count()

    # --- titles (feat/compose-add-title) -----------------------------------
    def _first_card(self) -> Locator:
        """Locator for the first real experience card (excludes the positioning card).

        Settles the compose render first, so callers never resolve a card a late
        auto-recommend cascade is about to tear down.
        """
        self._wait_settled()
        # The β.6c positioning card also carries `.compose-experience-card`, so
        # exclude it — `_first_card` is only ever about a real experience card.
        return self.page.locator(f"{Compose.EXPERIENCE_CARD}:not(.positioning-card)").first

    def title_texts(self) -> list[str]:
        """Eligible title texts on the first experience card (settled + present)."""
        rows = self._first_card().locator(f"{Compose.TITLE_LIST} {Compose.ROW} {Compose.ROW_TEXT}")
        expect(rows.first).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
        return rows.all_inner_texts()

    def add_title(self, title: str) -> None:
        """Open the '+ Add title' modal on the first card and submit `title`.

        Waits for the reloaded composition to render it (writes a sourced,
        eligible corpus row via POST /api/experiences/<id>/titles).
        """
        self._first_card().locator(Compose.ADD_TITLE_BTN).click()
        self.page.fill(Compose.FORM_MODAL_TITLE_INPUT, title)
        self.page.click(Compose.FORM_MODAL_SUBMIT)
        # The submit triggers a full loadComposition() re-render cascade; wait for
        # the concrete new title row to land, then settle so a follow-up read sees
        # the terminal (post-cascade) DOM.
        self._first_card().locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=title).wait_for(
            state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self._wait_settled()

    def select_title(self, text: str) -> None:
        """Check the radio of the title row matching `text` (first card)."""
        self._first_card().locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=text).locator(
            Compose.TITLE_RADIO
        ).check()

    def title_is_selected(self, text: str) -> bool:
        """Whether the title row matching `text` (first card) is the chosen one (settled)."""
        radio = (
            self._first_card()
            .locator(f"{Compose.TITLE_LIST} {Compose.ROW}", has_text=text)
            .locator(Compose.TITLE_RADIO)
        )
        expect(radio).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
        return radio.is_checked()

    # --- positioning (candidate-summary) card (β.6c) -----------------------
    def pin_positioning_variant(self, index: int) -> None:
        """Pin the positioning (candidate-summary) variant at `index` (settles first).

        The positioning pin routes through `_collectCompositionState()` (app.js),
        which reads the WHOLE override set (title pins, bullet order, role intros)
        off the DOM and POSTs it wholesale — so the click must land on the terminal
        render, or a mid-cascade DOM clobbers a sibling pin (the
        title-pin-clobber race this regression guards).
        """
        self._wait_settled()
        self.page.locator(Compose.POSITIONING_VARIANT).nth(index).click()

    # --- per-role intros (B.4, Sprint 6.6) ---------------------------------
    def role_intros_toggle(self) -> Locator:
        """Return the 'Add role intros' toggle locator."""
        return self.page.locator(Compose.ROLE_INTROS_TOGGLE)

    def enable_role_intros(self) -> None:
        """Turn on the 'Add role intros' toggle and wait for the per-role picker.

        Settles before toggling (so a prior load's cascade can't tear the toggle
        out underfoot) and after (the toggle fires a `loadComposition()` re-render
        via `_maybeFireRecommendExperienceSummaries`), with the chosen role-intro
        variant as the deterministic 'applied' signal in between.
        """
        self._wait_settled()
        self.role_intros_toggle().check()
        self.page.wait_for_selector(
            Compose.ROLE_INTRO_CHOSEN, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self._wait_settled()

    def chosen_intro_texts(self) -> list[str]:
        """Text of every chosen role-intro variant (visual order), settled."""
        self._wait_settled()
        return self.page.locator(
            f"{Compose.ROLE_INTRO_CHOSEN} {Compose.ROW_TEXT}"
        ).all_inner_texts()

    # --- skills card (B.5, Sprint 6.6) -------------------------------------
    def wait_skills_card(self) -> None:
        """Wait until the candidate-level Skills card reached its terminal render (settled)."""
        self._wait_settled()
        expect(self.page.locator(Compose.SKILLS_CARD)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def drop_skill(self, name: str) -> None:
        """Drop (hide) the skill row matching `name`.

        Settles first so the row node is attached when clicked — closing the
        resolve-then-click detachment race against the auto-recommend cascade.
        """
        self._wait_settled()
        self.page.locator(Compose.SKILL_ROW, has_text=name).locator(Compose.SKILL_DROP).click()

    # --- first experience's visible bullet list ----------------------------
    def _bullet_list(self) -> Locator:
        """Locator for the first experience's visible bullet list (settles first).

        The settle here is inherited by every caller (`_row`, `bullet_texts`,
        `has_custom_order`, `move_*`, `drag_below`), so they read/act against the
        terminal post-cascade DOM.
        """
        self._wait_settled()
        return self.page.locator(Compose.BULLET_LIST).first

    def _row(self, text: str) -> Locator:
        """Locator for the bullet row in the first list whose text matches ``text``."""
        return self._bullet_list().locator(f":scope > {Compose.ROW}", has_text=text)

    def bullet_texts(self) -> list[str]:
        """Visible bullet texts in DOM (visual) order (settled + present)."""
        rows = self._bullet_list().locator(f":scope > {Compose.ROW} {Compose.ROW_TEXT}")
        expect(rows.first).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
        return rows.all_inner_texts()

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
        """Click the first EXPERIENCE card's reset-order control (settles first).

        Uses `_first_card()` (which excludes the always-present positioning card)
        rather than `EXPERIENCE_CARD.first` — the positioning card also carries
        `.compose-experience-card` but has no reset control, so `.first` resolved to
        it and the click timed out. Mirrors every other first-card helper here.
        """
        self._first_card().locator(Compose.RESET_ORDER).click()

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

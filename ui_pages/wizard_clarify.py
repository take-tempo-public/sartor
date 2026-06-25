"""WizardClarifyPage — Step 2 (optional interview questions)."""

from __future__ import annotations

from ui_pages.base import LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import Wizard


class WizardClarifyPage(BasePage):
    """Page Object for Step 2 — the optional clarifying-question interview."""

    def request_questions(self) -> None:
        """Click 'Get clarifying questions' and wait for the textareas."""
        self.page.click(Wizard.CLARIFY_BUTTON)
        self.page.wait_for_selector(
            Wizard.CLARIFY_QUESTION_TEXTAREA, state="visible", timeout=LLM_TIMEOUT_MS
        )

    def wait_for_questions(self) -> None:
        """Wait for the clarifying-question textareas without clicking.

        The "Continue to Clarify →" CTA fetches them directly (finding #6), so
        the manual #btnClarify is bypassed on that path.
        """
        self.page.wait_for_selector(
            Wizard.CLARIFY_QUESTION_TEXTAREA, state="visible", timeout=LLM_TIMEOUT_MS
        )

    def answer_first(self, text: str, delay: int = 8) -> None:
        """Type an answer into the first clarifying-question textarea."""
        first = self.page.locator(Wizard.CLARIFY_QUESTION_TEXTAREA).first
        first.click()
        first.type(text, delay=delay)

    def fill_blank_answers(self, text: str, delay: int = 4) -> None:
        """Type the same answer into every still-blank question textarea."""
        boxes = self.page.locator(Wizard.CLARIFY_QUESTION_TEXTAREA)
        for i in range(boxes.count()):
            box = boxes.nth(i)
            if not (box.input_value() or "").strip():
                box.click()
                box.type(text, delay=delay)

    def submit_to_compose(self) -> None:
        """Submit the clarifications and wait for the Compose panel."""
        self.page.click(Wizard.SUBMIT_CLARIFICATIONS)
        self.page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=LLM_TIMEOUT_MS)

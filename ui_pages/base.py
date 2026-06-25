"""BasePage — shared navigation primitives. `base_url` is injected."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from ui_pages.selectors import UserPicker, Wizard

# Analyze / generate routinely take 30-60s against the real app; the stubbed
# test server resolves fast but the same generous ceiling is harmless there.
DEFAULT_TIMEOUT_MS = 15_000
LLM_TIMEOUT_MS = 120_000


class BasePage:
    """Shared navigation primitives every wizard/console POM inherits."""

    def __init__(self, page: Page, base_url: str) -> None:
        """Bind the Playwright page and the injected base URL."""
        self.page = page
        self.base_url = base_url.rstrip("/")

    def load(self) -> BasePage:
        """Navigate to the app root and wait for the user picker."""
        self.page.goto(f"{self.base_url}/")
        self.page.wait_for_selector(UserPicker.PANEL, timeout=DEFAULT_TIMEOUT_MS)
        return self

    # --- wizard rail -------------------------------------------------------
    def rail_step(self, step: int) -> Locator:
        """Return the rail button locator for a wizard step."""
        return self.page.locator(Wizard.step_button(step))

    def rail_step_enabled(self, step: int) -> bool:
        """Check whether a rail step is reachable (its button is enabled).

        The wizard toggles `disabled` on unreachable steps.
        """
        return self.rail_step(step).is_enabled()

    def goto_step(self, step: int) -> None:
        """Click the rail button for a step (no-op if the step is locked)."""
        self.rail_step(step).click()

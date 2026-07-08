"""UserPickerPage — select or create a user on the landing panel."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import UserPicker


class UserPickerPage(BasePage):
    """Page Object for the landing user-picker panel."""

    def options(self) -> list[str]:
        """Return the usernames currently in the picker dropdown."""
        return self.page.eval_on_selector_all(
            f"{UserPicker.SELECT} option", "els => els.map(e => e.value)"
        )

    def select(self, username: str) -> None:
        """Select an existing user and wait for the dropdown to reflect it."""
        self.page.wait_for_selector(UserPicker.SELECT, timeout=DEFAULT_TIMEOUT_MS)
        self.page.select_option(UserPicker.SELECT, username)
        self.page.wait_for_function(
            "(u) => document.getElementById('userSelect').value === u",
            arg=username,
            timeout=DEFAULT_TIMEOUT_MS,
        )

    def create(self, username: str, name: str, email: str = "") -> None:
        """Open the new-user form, fill it, and submit to create the user."""
        self.page.click(UserPicker.NEW_USER_LINK)
        self.page.wait_for_selector(UserPicker.NEW_USERNAME, state="visible")
        self.page.fill(UserPicker.NEW_USERNAME, username)
        self.page.fill(UserPicker.NEW_NAME, name)
        if email:
            self.page.fill(UserPicker.NEW_EMAIL, email)
        self.page.click(UserPicker.CREATE_BUTTON)
        self.page.wait_for_function(
            "(u) => document.getElementById('userSelect').value === u",
            arg=username,
            timeout=DEFAULT_TIMEOUT_MS,
        )

    def select_or_create(self, username: str, name: str, email: str = "") -> None:
        """Select the user if present, otherwise create it."""
        if username in self.options():
            self.select(username)
        else:
            self.create(username, name, email)

    # --- candidate roster (Wave 2 recruiter tier, UX review F-08) ----------

    def search_roster(self, query: str) -> None:
        """Type into the roster search box (filters the card list client-side)."""
        self.page.wait_for_selector(UserPicker.ROSTER_SEARCH, timeout=DEFAULT_TIMEOUT_MS)
        self.page.fill(UserPicker.ROSTER_SEARCH, query)

    def select_from_roster(self, username: str) -> None:
        """Click a candidate's roster card and wait for it to drive #userSelect.

        The roster card SETS #userSelect's value and fires the same
        onUserSelect() any other selection path uses — this waits on that
        underlying select, so the assertion contract matches `select()` above.
        """
        self.page.wait_for_selector(UserPicker.roster_card(username), timeout=DEFAULT_TIMEOUT_MS)
        self.page.click(UserPicker.roster_card(username))
        self.page.wait_for_function(
            "(u) => document.getElementById('userSelect').value === u",
            arg=username,
            timeout=DEFAULT_TIMEOUT_MS,
        )

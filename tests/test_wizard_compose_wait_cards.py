"""`WizardComposePage.wait_cards` must return on Compose's settle gate, not the first card.

docs/dev/diagnosis/capture-generate-stall.md: the screenshot capture's only caller returned at
the first `.compose-experience-card`, clicked Save and continue while the arrival
`draft-summary` call was still in flight, and Step 5 then refused to open because the draft
had staled the approval. The wait is checked against a recording page, so no browser runs.
"""

from __future__ import annotations

from typing import Any, cast

from ui_pages.selectors import Compose
from ui_pages.wizard_compose import WizardComposePage


class _RecordingPage:
    """Stands in for a Playwright Page; records the selectors waited on, in order."""

    def __init__(self) -> None:
        self.waited: list[str] = []

    def wait_for_selector(self, selector: str, **_kwargs: Any) -> None:
        self.waited.append(selector)


def test_wait_cards_returns_only_after_the_settle_gate() -> None:
    page = _RecordingPage()

    WizardComposePage(cast(Any, page), "http://localhost:5000").wait_cards()

    assert Compose.EXPERIENCE_CARD in page.waited
    assert Compose.SETTLED in page.waited
    assert page.waited.index(Compose.SETTLED) > page.waited.index(Compose.EXPERIENCE_CARD)

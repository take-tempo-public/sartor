"""Regression: skill/certification names with an internal comma survive the
Settings save round trip (`fix/skill-line-parenthetical-split`, item 15).

Pre-fix, `saveConfig()` split the flat `cfgSkills`/`cfgCerts` fields on every
comma, including one nested inside a parenthetical — a skill like "Eval
Framework Design (LLM-as-judge, rubric-based)" silently became two broken
entries (`["Eval Framework Design (LLM-as-judge", "rubric-based)"]`) on save.

That corruption is invisible if you only re-read the Settings textarea: the
textarea re-renders via `(skills || []).join(', ')`, and joining the two
broken fragments back together with `', '` reconstructs the exact original
display string byte-for-byte — the field LOOKS unchanged even though the
stored array now has one extra, wrongly-split entry. The only way to observe
the real defect is to read the persisted `skills` array itself (via the
config API), not the re-rendered field text. LLM-free (`analyzer` stubbed;
the real config routes run).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import write_user_config
from ui_pages import BasePage, UserPickerPage
from ui_pages.selectors import Settings


def _open_settings(page: Page, live_server: str, username: str) -> None:
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select(username)
    page.click(Settings.OPEN_PILL)
    page.wait_for_selector(Settings.DRAWER, state="visible")


@pytest.mark.ux
@pytest.mark.slow
def test_skill_with_internal_comma_survives_settings_save_and_reload(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    parenthetical_skill = "Eval Framework Design (LLM-as-judge, rubric-based)"

    write_user_config(ux_app, "carol")
    _open_settings(page, live_server, "carol")

    page.fill(Settings.SKILLS_FIELD_ROW + " input", f"{parenthetical_skill}, Go")
    page.click("text=Save config")
    expect(page.locator("#statusPill .cb-status-text")).to_contain_text(
        "config saved", ignore_case=True
    )

    # Assert against the real persisted array via the GET route — the
    # re-rendered textarea text alone cannot distinguish "saved correctly"
    # from "saved as 3 fragments that happen to re-join to the same string".
    saved = page.evaluate(
        "fetch('/api/users/carol/config').then(r => r.json())",
    )
    assert saved["skills"] == [parenthetical_skill, "Go"], saved["skills"]

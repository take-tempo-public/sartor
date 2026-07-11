"""UX: the doc-grounded assistant, ported onto the /_dashboard console (#17,
2026-07 diagnostics round-2 findings — owner: dev-mode checkbox checked by
default on the dashboard).

Mirrors tests/ux/regression/test_20260616_assistant_panel.py's approach (same
stubbed avatar + retrieval, same real SSE route + real static/assistant.js
path) but drives it from the dashboard console instead of the wizard, and
additionally asserts the dashboard-only default: the "Dev mode" checkbox
starts CHECKED here (the wizard's copy defaults unchecked). No backend
change — blueprints/assistant.py:ask() already treats `username` as optional,
so this never needs a seeded user.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Assistant


def _fake_avatar(client, question, context, *, allow_dev=False, username="", run_id=""):
    yield ("chunk", "The eval harness lives under evals/ ")
    yield ("chunk", "and the run-lock is documented in AGENTS.md [1].")
    yield (
        "done",
        {
            "answer": "The eval harness lives under evals/ and the run-lock is documented in AGENTS.md [1].",
            "citations": [
                {
                    "n": 1,
                    "label": "AGENTS.md",
                    "href": "https://github.com/take-tempo-public/sartor/blob/main/AGENTS.md",
                },
            ],
            "truncated": False,
            "allow_dev": allow_dev,
        },
    )


@pytest.mark.ux
@pytest.mark.slow
def test_dashboard_assistant_streams_cited_answer_and_dev_mode_defaults_checked(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch
) -> None:
    import analyzer
    import blueprints.assistant as ba

    # Offline: stub the avatar + retrieval; the route + frontend run for real.
    monkeypatch.setattr(analyzer, "avatar_answer_streaming", _fake_avatar)
    monkeypatch.setattr(ba, "_build_sources", lambda turns: [])
    monkeypatch.setattr(ba, "_get_client", lambda: None)

    dash = DashboardConsolePage(page, live_server).load()

    # Pill is reachable regardless of active tab (outside any .dash-pane).
    expect(page.locator(Assistant.OPEN_PILL)).to_be_visible()
    page.click(Assistant.OPEN_PILL)
    page.wait_for_selector(Assistant.MODAL, state="visible")

    # #17 owner decision: dev mode defaults CHECKED on the dashboard (the
    # wizard's copy of this same control defaults unchecked).
    expect(page.locator(Assistant.DEV_MODE)).to_be_checked()

    page.fill(Assistant.QUESTION, "Where do the LLM calls live?")
    page.click(Assistant.ASK_BUTTON)

    page.wait_for_function(
        "() => document.getElementById('assistantAnswer').textContent.includes('run-lock')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    page.wait_for_function(
        "() => document.getElementById('assistantSources').textContent.includes('AGENTS.md')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    page.wait_for_function(
        "() => { const a = document.getElementById('assistantAnswer')"
        ".querySelector('a[href^=\"https://github.com/\"]');"
        " return a && a.textContent === '[1]'; }",
        timeout=DEFAULT_TIMEOUT_MS,
    )

    # Sanity: the tab surface underneath is unaffected — closing the modal
    # returns to a normal, functioning console (no dangling overlay/backdrop).
    page.click(Assistant.CLOSE)
    expect(page.locator(Assistant.MODAL)).to_be_hidden()
    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_be_visible()

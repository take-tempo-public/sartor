"""UX: the doc-grounded assistant answers with NO user selected (Sprint 7.8c).

7.8c removed the "Pick a user first, then ask." gate — the assistant's answer is
project-global, so the magnifier modal must stream a cited answer before any user is
chosen. This mirrors `test_20260616_assistant_panel` but deliberately skips user
selection, exercising the path the route test (`tests/test_assistant_route.py`) cannot:
the real `static/assistant.js` sending an empty username end-to-end. LLM-free — the
avatar (`analyzer.avatar_answer_streaming`) and retrieval (`_build_sources`) are stubbed
so the REAL SSE route + frontend run offline.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Assistant


def _fake_avatar(client, question, context, *, allow_dev=False, username="", run_id=""):
    # The route passes an empty username when no user is selected; the avatar is
    # anonymous by construction (username default ""), so the stub ignores it.
    yield ("chunk", "sartor tailors your resume ")
    yield ("chunk", "in six guided steps [1].")
    yield (
        "done",
        {
            "answer": "sartor tailors your resume in six guided steps [1].",
            "citations": [
                {
                    "n": 1,
                    "label": "using-sartor",
                    "href": "https://github.com/take-tempo-public/sartor/blob/main/docs/wiki/pages/using-sartor.md",
                },
            ],
            "truncated": False,
            "allow_dev": allow_dev,
        },
    )


@pytest.mark.ux
@pytest.mark.slow
def test_assistant_answers_without_user_selected(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch
) -> None:
    import analyzer
    import blueprints.assistant as ba

    # Offline: stub the avatar + retrieval; the route + frontend run for real.
    monkeypatch.setattr(analyzer, "avatar_answer_streaming", _fake_avatar)
    monkeypatch.setattr(ba, "_build_sources", lambda turns: [])
    monkeypatch.setattr(ba, "_get_client", lambda: None)

    # Deliberately NO UserPickerPage.select(...) — currentUser stays unset.
    BasePage(page, live_server).load()
    page.wait_for_selector(Assistant.OPEN_PILL, state="visible")
    page.click(Assistant.OPEN_PILL)  # the top-bar magnifier is always present
    page.wait_for_selector(Assistant.MODAL, state="visible")
    page.fill(Assistant.QUESTION, "How does sartor work?")
    page.click(Assistant.ASK_BUTTON)

    # With the gate gone, the streamed answer renders (the old gate would instead have
    # written "Pick a user first, then ask." to #assistantStatus and returned).
    page.wait_for_function(
        "() => document.getElementById('assistantAnswer').textContent.includes('six guided steps')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    page.wait_for_function(
        "() => document.getElementById('assistantSources').textContent.includes('using-sartor')",
        timeout=DEFAULT_TIMEOUT_MS,
    )

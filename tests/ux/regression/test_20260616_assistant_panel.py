"""UX: the doc-grounded assistant modal streams a cited answer (Sprint 7.5).

Drives the assistant from its top-bar magnifier (`#assistantPill`): click it to open
the floating `#assistantModal`, ask a question, and assert the streamed answer + the
cited-sources line render. LLM-free — the avatar (`analyzer.avatar_answer_streaming`)
and retrieval (`blueprints.assistant._build_sources`) are stubbed so the REAL SSE route
+ the real `static/assistant.js` / `_consumeSSE` path run offline.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import write_user_config
from ui_pages import BasePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Assistant


def _fake_avatar(client, question, context, *, allow_dev=False, username="", run_id=""):
    yield ("chunk", "sartor tailors your resume ")
    yield ("chunk", "in six guided steps [1][2].")
    yield (
        "done",
        {
            "answer": "sartor tailors your resume in six guided steps [1][2].",
            "citations": [
                {
                    "n": 1,
                    "label": "using-sartor",
                    "href": "https://github.com/take-tempo-public/sartor/blob/main/docs/wiki/pages/using-sartor.md",
                },
                {
                    "n": 2,
                    "label": "tailoring-a-resume",
                    "href": "https://github.com/take-tempo-public/sartor/blob/main/docs/wiki/pages/tailoring-a-resume.md",
                },
            ],
            "truncated": False,
            "allow_dev": allow_dev,
        },
    )


@pytest.mark.ux
@pytest.mark.slow
def test_assistant_panel_streams_cited_answer(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch
) -> None:
    import analyzer
    import blueprints.assistant as ba

    # Offline: stub the avatar + retrieval; the route + frontend run for real.
    monkeypatch.setattr(analyzer, "avatar_answer_streaming", _fake_avatar)
    monkeypatch.setattr(ba, "_build_sources", lambda turns: [])
    monkeypatch.setattr(ba, "_get_client", lambda: None)

    write_user_config(ux_app, "robert")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("robert")
    page.wait_for_load_state("networkidle")

    page.click(Assistant.OPEN_PILL)  # open the floating modal from the top-bar magnifier
    page.wait_for_selector(Assistant.MODAL, state="visible")
    page.fill(Assistant.QUESTION, "How do I tailor a resume?")
    page.click(Assistant.ASK_BUTTON)

    # The streamed answer accumulates into the answer div (textContent is unaffected
    # by any CSS transform, so an exact substring match on the JS-set text is safe).
    page.wait_for_function(
        "() => document.getElementById('assistantAnswer').textContent.includes('six guided steps')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    # The numbered "Sources" key lands in its own #assistantSources block on `done`.
    page.wait_for_function(
        "() => document.getElementById('assistantSources').textContent.includes('using-sartor')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    # The inline [n] citations re-render as clickable GitHub links (7.8d / Scheme B).
    page.wait_for_function(
        "() => { const a = document.getElementById('assistantAnswer')"
        ".querySelector('a[href^=\"https://github.com/\"]');"
        " return a && a.textContent === '[1]'; }",
        timeout=DEFAULT_TIMEOUT_MS,
    )

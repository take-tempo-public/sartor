"""Instrument — the Step 6 editors' text must not depend on which tab is showing (item 170).

`feat/confirm-before-overwriting-typed-edits`. Found by the full UX tier, not designed: wiring
the unsaved-edit gate to Generate made `test_20261012_regenerate_keeps_cover_letter.py`
(B7) time out, because with the Cover-letter tab active `_detectEdits()` reported a
résumé edit nobody typed. Evidence record: `docs/dev/work/items/0170-*.md` (2026-10-14).

The mechanism, observed: the résumé editor's DOM is text nodes joined by `<br>`.
`_readEditorText` un-hides only the element's own `hidden` class. When an *ancestor*
(`#tabResume`) is `display:none`, `innerText` of a non-rendered node is `textContent`, which
drops every `<br>`: 207 characters against 218 in `lastGeneratedResume`.

Three readers of that text are observed in one state (résumé generated, then a detached cover
letter generated, so the Cover-letter tab is active and the résumé editor is not rendered):

* `_readEditorText('resumePreview')` itself;
* `_detectEdits()`, which the Refine / Iterate / Generate gates call;
* the body `downloadResume()` actually POSTs to `/api/download-edited`. The earlier note that
  the résumé download loses its line breaks from a hidden tab was inferred from the same
  mechanism and never driven; this drives it.

A control that does not hold raises `ControlFailed`, so a broken drive fails with a distinct
error rather than being mistaken for the defect.
"""

from __future__ import annotations

import json
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page

from tests._controls import control as _control
from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardComposePage,
    WizardGeneratePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS
from ui_pages.selectors import Output

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
LETTER = "ZEBRA-LETTER first detached cover letter for the billing role"

_STATE_JS = """() => {
    const el = document.getElementById('resumePreview');
    const e = _detectEdits();
    return {
        // True only when the editor has layout. Here it must be false: that is the
        // condition under test (an ancestor tab is display:none).
        rendered: el.getClientRects().length > 0 || (() => {
            const wasHidden = el.classList.contains('hidden');
            if (wasHidden) el.classList.remove('hidden');
            const n = el.getClientRects().length;
            if (wasHidden) el.classList.add('hidden');
            return n > 0;
        })(),
        read: _readEditorText('resumePreview'),
        last: lastGeneratedResume,
        resumeEdited: e.resumeEdited,
        coverEdited: e.coverEdited,
    };
}"""


def _wait_iteration(page: Page, n: int) -> None:
    page.wait_for_function(
        "n => (document.getElementById('iterationPill')?.textContent || '').trim() === 'iter ' + n",
        arg=n,
        timeout=LLM_TIMEOUT_MS,
    )


@pytest.mark.ux
@pytest.mark.slow
def test_editor_text_does_not_depend_on_the_active_tab(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    monkeypatch.setattr(
        analyzer,
        "generate_cover_letter_against_resume",
        lambda *a, **k: {"cover_letter_content": LETTER},
    )
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open().continue_to_template()
    template = WizardTemplatePage(page, live_server)
    template.pick_template(1)
    template.wait_live_preview()
    template.continue_to_generate()
    WizardGeneratePage(page, live_server).generate()
    _wait_iteration(page, 1)

    # Control 1: with the résumé tab showing, nothing was typed and nothing is reported.
    on_resume: dict[str, Any] = page.evaluate(_STATE_JS)
    _control(on_resume["resumeEdited"] is False, on_resume)
    _control(on_resume["read"].strip() == on_resume["last"].strip(), on_resume)

    # The state under test: generating the letter activates the Cover-letter tab.
    page.click(Output.GENERATE_COVER)
    page.wait_for_selector(Output.DOWNLOAD_COVER, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    hidden_tab: dict[str, Any] = page.evaluate(_STATE_JS)
    # Control 2: the résumé editor really is not rendered now.
    _control(hidden_tab["rendered"] is False, hidden_tab)
    # Control 3: the typed text did not change (there is none).
    _control(on_resume["last"] == hidden_tab["last"], (on_resume["last"], hidden_tab["last"]))

    # What the résumé download would actually send from this state.
    with page.expect_request(
        lambda r: "/api/download-edited" in r.url, timeout=DEFAULT_TIMEOUT_MS
    ) as sent:
        page.evaluate("() => { downloadResume(); }")
    body = json.loads(sent.value.post_data or "{}")

    record = {
        "arm": "editor-text-hidden-tab",
        "read_len": len(hidden_tab["read"]),
        "last_len": len(hidden_tab["last"]),
        "read_equals_last": hidden_tab["read"].strip() == hidden_tab["last"].strip(),
        "resumeEdited": hidden_tab["resumeEdited"],
        "download_len": len(body.get("content") or ""),
        "download_equals_last": (body.get("content") or "").strip() == hidden_tab["last"].strip(),
    }
    print(json.dumps(record))
    # The invariants: the text, the edit check and the download body agree with the
    # generated résumé, whichever tab is showing.
    assert record["read_equals_last"] is True, record
    assert record["resumeEdited"] is False, record
    assert record["download_equals_last"] is True, record

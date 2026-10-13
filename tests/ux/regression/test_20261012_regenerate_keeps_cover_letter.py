"""Instrument — item 162 in the browser: a résumé regenerate blanks the cover letter (B7).

`fix/regenerate-keeps-cover-letter`. The browser arm of
`tests/test_regenerate_cover_letter.py` (B1-B6 observe the routes and the context file;
this observes what the wizard shows). Evidence record:
`docs/dev/diagnosis/regenerate-keeps-cover-letter.md` I1 / I3.

The drive is the real wizard with the LLM entry points stubbed (`install_llm_stubs`):
analyze → Compose → Template → Generate → "+ Generate cover letter" → back to Step 5 →
Generate again. In corpus mode Step 6's Refine loops back to Compose instead of
regenerating (`submitRefinement`, `_composeApplicationId != null`), so Step 5's Generate is
the user's résumé-only regenerate: the client never sends `generate_cover_letter`
(`static/app.js` `runGeneration`).

The cover-letter route imports `generate_cover_letter_against_resume` inside the function
and `install_llm_stubs` does not stub it, so this test patches it on `analyzer`.

Waits are on state, not on a toast: the iteration pill (`#iterationPill`) is written by
`_onGenerationComplete` immediately before `_renderOutput` in the same synchronous block,
so "iter N" visible means the output has been rendered.

The defect invariant was `xfail(strict=True, raises=AssertionError)` on the base tip (the
fix commit deleted only that marker); a control that does not hold raises `ControlFailed`,
so a broken drive fails with a distinct error rather than being mistaken for the defect.
"""

from __future__ import annotations

import json
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page

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
from ui_pages.base import LLM_TIMEOUT_MS
from ui_pages.selectors import Output, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
LETTER = "ZEBRA-LETTER first detached cover letter for the billing role"

# What the Step-6 cover-letter controls and editor show. `download_would_send` is exactly
# what `downloadCoverLetter()` posts as `content` (`_readEditorText('coverLetterPreview')`).
_COVER_STATE_JS = """() => {
    const hidden = (id) => {
        const el = document.getElementById(id);
        return !el || el.classList.contains('hidden');
    };
    const editor = document.getElementById('coverLetterPreview');
    return {
        editor_text: editor ? editor.textContent : null,
        generate_visible: !hidden('btnGenerateCover'),
        download_visible: !hidden('btnDownloadCover'),
        download_would_send:
            typeof _readEditorText === 'function' ? _readEditorText('coverLetterPreview') : null,
    };
}"""


class ControlFailed(Exception):
    """A drive or control step did not hold, so the arm proves nothing (not the defect)."""


def _control(ok: bool, what: object) -> None:
    if not ok:
        raise ControlFailed(str(what))


def _wait_iteration(page: Page, n: int) -> None:
    page.wait_for_function(
        "n => (document.getElementById('iterationPill')?.textContent || '').trim() === 'iter ' + n",
        arg=n,
        timeout=LLM_TIMEOUT_MS,
    )


def _cover_state(page: Page) -> dict[str, Any]:
    return dict(page.evaluate(_COVER_STATE_JS))


@pytest.mark.ux
@pytest.mark.slow
def test_b7_the_wizard_keeps_the_cover_letter_after_a_resume_regenerate(
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

    # Control 1: a résumé-only first generate leaves "+ Generate cover letter" showing.
    before_letter = _cover_state(page)
    _control(
        before_letter["generate_visible"] and not before_letter["download_visible"],
        before_letter,
    )

    # Control 2: generating the letter fills the editor and swaps in Download.
    page.click(Output.GENERATE_COVER)
    page.wait_for_selector(Output.DOWNLOAD_COVER, state="visible", timeout=LLM_TIMEOUT_MS)
    with_letter = _cover_state(page)
    _control(
        with_letter["editor_text"] == LETTER
        and with_letter["download_visible"]
        and not with_letter["generate_visible"]
        and with_letter["download_would_send"] == LETTER,
        with_letter,
    )

    # The regenerate: back to Step 5 and Generate again (résumé-only, as the client sends).
    page.click(Wizard.step_button(5))
    page.click(Wizard.GENERATE_BUTTON)
    _wait_iteration(page, 2)
    after = _cover_state(page)

    print(
        json.dumps(
            {
                "arm": "B7",
                "before_letter": before_letter,
                "with_letter": with_letter,
                "after_regenerate": after,
            }
        )
    )
    # The defect invariants: the wizard still shows the letter and still offers Download.
    assert LETTER in (after["editor_text"] or ""), after
    assert after["download_visible"] and not after["generate_visible"], after
    assert after["download_would_send"] == LETTER, after

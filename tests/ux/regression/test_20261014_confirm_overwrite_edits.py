"""Browser arm of item 170 — Generate asks before it replaces a typed edit.

`feat/confirm-before-overwriting-typed-edits`. The route-level arms are
`tests/test_confirm_overwrite_edits.py`; this is what the wizard shows and sends.

Two gates stand in front of Generate, and this drives both through the real wizard (the LLM
entry points stubbed with `install_llm_stubs`):

* **Case 4, unsaved editor text.** The Step 6 editor holds text that differs from the last
  generate. Generate now opens the same Use / Discard / Cancel dialog Refine and Iterate
  open (`_gateEditsBeforeAction`, which was not wired to Generate before). Cancel sends no
  request and leaves the editor alone.
* **Case 1, a saved résumé edit the approved composition would replace.** The server
  answers `409 edits_would_be_discarded` before any LLM call. The wizard shows
  "Replace your typed edits?" (`cbConfirm`). Cancel leaves everything as it was and sends no
  second request; Continue re-sends once with `confirm_discard_edits: true`, and the
  after-the-fact `#editsDiscardedNotice` appears.

What this does NOT drive: cases 2 and 3 (a letter edit consumed by a new letter). The shipped
client never sends `generate_cover_letter`, and `#btnGenerateCover` is hidden once a letter
exists, so neither is reachable from the UI (`docs/dev/work/items/0170-*.md`). They are pinned
at the route in `tests/test_confirm_overwrite_edits.py`.

The "typed" text is assigned to the editor's DOM node, not keystrokes: `#resumePreview` is
hidden unless the edit drawer is open, and `_detectEdits` reads it by `innerText` either way
(`_readEditorText`), which is the surface the gate looks at.

Waits are on state (the iteration pill, a dialog's own visibility), never on a toast. A control
that does not hold raises `ControlFailed`, so a broken drive fails with a distinct error.
"""

from __future__ import annotations

import json
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page, expect

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
from ui_pages.selectors import Compose, ConfirmModal, EditGateModal, Output, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
TYPED = "ZEBRA-UX-TYPED a hand edit the candidate made in the preview"

# Append the marker to the editor, as typing would. textContent, not innerText: the node is
# hidden unless the drawer is open, and `_detectEdits` normalises through `_readEditorText`.
_TYPE_JS = """marker => {
    const el = document.getElementById('resumePreview');
    el.textContent = (el.textContent || '') + '\\n\\n' + marker;
    return el.textContent.includes(marker);
}"""

_EDITOR_TEXT_JS = "() => document.getElementById('resumePreview')?.textContent || ''"


def _wait_iteration(page: Page, n: int) -> None:
    page.wait_for_function(
        "n => (document.getElementById('iterationPill')?.textContent || '').trim() === 'iter ' + n",
        arg=n,
        timeout=LLM_TIMEOUT_MS,
    )


def _pill(page: Page) -> str:
    return (page.locator("#iterationPill").text_content() or "").strip()


def _status(page: Page) -> str:
    return (page.locator("#statusPill .cb-status-text").text_content() or "").strip()


@pytest.mark.ux
@pytest.mark.slow
def test_generate_asks_before_replacing_a_typed_edit(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()
    compose.continue_to_template()
    template = WizardTemplatePage(page, live_server)
    template.pick_template(1)
    template.wait_live_preview()
    template.continue_to_generate()
    WizardGeneratePage(page, live_server).generate()
    _wait_iteration(page, 1)

    # Every generate-family request and its answer, from here on.
    sent: list[dict[str, Any]] = []
    page.on(
        "request",
        lambda req: (
            sent.append({"url": req.url, "body": req.post_data})
            if "/api/generate" in req.url
            else None
        ),
    )
    answered: list[tuple[str, int]] = []
    page.on(
        "response",
        lambda resp: (
            answered.append((resp.url, resp.status)) if "/api/generate" in resp.url else None
        ),
    )

    # ---- Case 4: unsaved text in the editor -------------------------------------------
    _control(bool(page.evaluate(_TYPE_JS, TYPED)), "the marker did not land in the editor")
    page.click(Wizard.step_button(5))
    page.click(Wizard.GENERATE_BUTTON)
    expect(page.locator(EditGateModal.OPEN)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    page.click(EditGateModal.CANCEL)
    expect(page.locator(EditGateModal.MODAL)).to_be_hidden(timeout=DEFAULT_TIMEOUT_MS)

    case4 = {
        "arm": "case4-cancel",
        "requests_sent": len(sent),
        "iteration": _pill(page),
        "status": _status(page),
        "editor_keeps_typed": TYPED in page.evaluate(_EDITOR_TEXT_JS),
    }
    print(json.dumps(case4))
    assert sent == [], case4  # Cancel sent nothing
    assert case4["iteration"] == "iter 1", case4
    assert "cancel" in str(case4["status"]).lower(), case4
    assert case4["editor_keeps_typed"] is True, case4

    # ---- Case 1: a saved résumé edit the re-approved composition would replace --------
    # Change a bullet in Compose and re-approve: the typed edit was made over a résumé
    # that no longer exists. (The edit itself is still only in the editor; the first
    # Generate saves it through the gate, which is the real user path.)
    compose.reload()  # back to Step 3 through the rail; `open()` is the analysis-panel button
    page.locator(Compose.BULLET_EDIT).first.click()
    page.locator(Compose.FORM_MODAL_TEXT_INPUT).fill(
        "Reduced Kubernetes p99 latency 45% across 12 services"
    )
    page.click(Compose.FORM_MODAL_SUBMIT)
    expect(page.locator(Compose.STALE_NOTICE)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    compose.continue_to_template()
    expect(BasePage(page, live_server).rail_step(5)).to_be_enabled(timeout=DEFAULT_TIMEOUT_MS)
    template.pick_template(1)
    template.wait_live_preview()
    template.continue_to_generate()
    _control(
        TYPED in page.evaluate(_EDITOR_TEXT_JS),
        "the typed text left the editor while moving through Compose",
    )

    # Round 1: Use edits (the gate saves them), the server asks, the user Cancels.
    sent.clear()
    answered.clear()
    page.click(Wizard.GENERATE_BUTTON)
    expect(page.locator(EditGateModal.OPEN)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    page.click(EditGateModal.USE)
    expect(page.locator(ConfirmModal.OPEN)).to_be_visible(timeout=LLM_TIMEOUT_MS)
    title = (page.locator(ConfirmModal.TITLE).text_content() or "").strip()
    body = (page.locator(ConfirmModal.BODY).text_content() or "").strip()
    ok_label = (page.locator(ConfirmModal.OK).text_content() or "").strip()
    page.click(ConfirmModal.CANCEL)
    expect(page.locator(ConfirmModal.MODAL)).to_be_hidden(timeout=DEFAULT_TIMEOUT_MS)

    gen_after_cancel = [a for a in answered if a[0].endswith("/api/generate/stream")]
    case1_cancel = {
        "arm": "case1-cancel",
        "title": title,
        "body": body,
        "ok_label": ok_label,
        "generate_answers": [s for _, s in gen_after_cancel],
        "iteration": _pill(page),
        "editor_keeps_typed": TYPED in page.evaluate(_EDITOR_TEXT_JS),
    }
    print(json.dumps(case1_cancel))
    # The server refused (409) before spending; the user's Cancel sent nothing further.
    assert case1_cancel["generate_answers"] == [409], case1_cancel
    assert title == "Replace your typed edits?", case1_cancel
    assert "résumé edits you saved" in body, case1_cancel
    assert ok_label == "Continue", case1_cancel
    assert case1_cancel["iteration"] == "iter 1", case1_cancel
    assert case1_cancel["editor_keeps_typed"] is True, case1_cancel
    expect(page.locator(Output.EDITS_DISCARDED_NOTICE)).to_be_hidden()

    # Round 2: the same again, and this time Continue.
    sent.clear()
    answered.clear()
    page.click(Wizard.GENERATE_BUTTON)
    expect(page.locator(EditGateModal.OPEN)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    page.click(EditGateModal.USE)
    expect(page.locator(ConfirmModal.OPEN)).to_be_visible(timeout=LLM_TIMEOUT_MS)
    page.click(ConfirmModal.OK)
    _wait_iteration(page, 2)

    generate_calls = [
        (r["url"], json.loads(r["body"] or "{}"))
        for r in sent
        if r["url"].endswith("/api/generate/stream")
    ]
    statuses = [s for u, s in answered if u.endswith("/api/generate/stream")]
    case1_continue = {
        "arm": "case1-continue",
        "generate_statuses": statuses,
        "confirm_flags": [c.get("confirm_discard_edits") for _, c in generate_calls],
        "iteration": _pill(page),
        "editor_keeps_typed": TYPED in page.evaluate(_EDITOR_TEXT_JS),
    }
    print(json.dumps(case1_continue))
    # First request asked (409, no flag); the re-send carried the flag and succeeded.
    assert case1_continue["generate_statuses"] == [409, 200], case1_continue
    assert case1_continue["confirm_flags"] == [None, True], case1_continue
    assert case1_continue["iteration"] == "iter 2", case1_continue
    assert case1_continue["editor_keeps_typed"] is False, case1_continue
    expect(page.locator(Output.EDITS_DISCARDED_NOTICE)).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

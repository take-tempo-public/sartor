"""Regression: Wave 4 aesthetic-coherence polish (`feat/ux-w4-aesthetic`).

Covers the five UX-review findings this branch fixes:
- F-07  browser-native `confirm()` replaced by the app's own `cbConfirm()`
        modal on every call site (10 total — see the branch report for the
        full inventory). Two representative destructive flows are exercised
        here (skill retire: Confirm AND Cancel paths); the corpus Accept-all
        flow (the register's own F-07 evidence) is covered in
        `test_20260612_corpus_affordance_polish.py::test_accept_all_pending_clears_banner`.
- F-23  the Tailor tab folds the User selection + Prior applications panels
        to a compact/collapsible summary by default so the wizard rail owns
        the viewport; the choice persists across reloads via localStorage.
- F-13  the Compose gap-fill lane carries a subdued "Optional" badge.
- F-14  the edit-detection modal ("Your edits aren't saved yet") uses plain
        language that names each choice's effect — same ids/choices/timing.
- F-18  is a server-default decision covered by unit tests in
        `tests/test_browser_open.py` (no UX-tier surface to drive).

All LLM-free (analyzer stubbed where a stub is needed; the real routes run).
"""

from __future__ import annotations

import re
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_application, seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, CorpusPage, UserPickerPage, WizardComposePage, WizardJobPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Compose, PriorApps, UserPicker, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


def _seed_skill(candidate_id: int, name: str = "Python") -> int:
    from db.models import Skill
    from db.session import get_session

    s = get_session()
    try:
        sk = Skill(
            candidate_id=candidate_id,
            name=name,
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="imported",
        )
        s.add(sk)
        s.commit()
        return sk.id
    finally:
        s.close()


# ---------------------------------------------------------------------------
# F-07 — cbConfirm() replaces native confirm() (skill retire: Cancel + Confirm)
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_skill_retire_uses_cbconfirm_cancel_path(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Canceling the app-native confirm modal leaves the skill in place — no
    native `confirm()` dialog is ever spawned (a stray one would hang the test
    without a `page.on("dialog", ...)` handler, which this test deliberately
    does not install)."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    _seed_skill(cid, "Python")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open().wait_for_cards()

    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(1)
    page.click("#skillsEditorList .skill-editor-row .corpus-action-btn.delete")

    modal = page.locator("#cbConfirmModal")
    expect(modal).to_be_visible()
    # Plain-language, app-native copy — not an OS dialog.
    expect(page.locator("#cbConfirmTitle")).to_have_text("Retire this skill?")
    # Destructive → the danger-styled confirm button (per-item affordance).
    ok_btn = page.locator("#cbConfirmOk")
    expect(ok_btn).to_have_class(re.compile(r"cb-bg-danger"))

    page.click("#cbConfirmCancel")
    expect(modal).to_be_hidden()
    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(1)


@pytest.mark.ux
@pytest.mark.slow
def test_skill_retire_uses_cbconfirm_confirm_path(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Confirming the modal retires the skill via the real DELETE route."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    _seed_skill(cid, "Python")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open().wait_for_cards()

    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(1)
    page.click("#skillsEditorList .skill-editor-row .corpus-action-btn.delete")
    page.wait_for_selector("#cbConfirmModal:not(.hidden)", timeout=DEFAULT_TIMEOUT_MS)
    page.click("#cbConfirmOk")
    expect(page.locator("#cbConfirmModal")).to_be_hidden()
    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(0)


# ---------------------------------------------------------------------------
# F-23 — Tailor tab folds the ambient panels behind the wizard
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_tailor_tab_folds_ambient_panels_by_default(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """First visit (no stored preference): User selection + Prior applications
    default to collapsed so the wizard rail is the primary surface. Every
    existing id/selector still resolves — only the collapsed posture is new."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    seed_application(cid, title="Staff Engineer", company="Acme")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.wait_for_selector(PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    assert "collapsed" in (page.get_attribute(UserPicker.PANEL, "class") or "")
    assert "collapsed" in (page.get_attribute(PriorApps.PANEL, "class") or "")
    expect(page.locator(Wizard.RAIL)).to_be_visible()


@pytest.mark.ux
@pytest.mark.slow
def test_applications_panel_expand_choice_persists_across_reload(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Expanding the applications panel is remembered (localStorage) across a
    reload — 'prior state preserved', not just this session."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.wait_for_selector(PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert "collapsed" in (page.get_attribute(PriorApps.PANEL, "class") or "")

    page.click(f"{PriorApps.PANEL} .panel-header")
    page.wait_for_selector(f"{PriorApps.PANEL}:not(.collapsed)", timeout=DEFAULT_TIMEOUT_MS)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.wait_for_selector(PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert "collapsed" not in (page.get_attribute(PriorApps.PANEL, "class") or "")


# ---------------------------------------------------------------------------
# F-13 — gap-fill lane reads as optional
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_gap_fill_lane_shows_optional_badge(
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
    WizardComposePage(page, live_server).open()

    badge = page.locator(Compose.GAP_FILL_OPTIONAL_BADGE).first
    expect(badge).to_be_visible()
    # Case-insensitive: UX copy is CSS-uppercased, so assert via text_content().
    assert "optional" in (badge.text_content() or "").lower()
    # Per-item affordances (Accept/Retire) are unchanged.
    expect(page.locator(Compose.GAP_FILL_ACCEPT).first).to_be_visible()
    expect(page.locator(Compose.GAP_FILL_RETIRE).first).to_be_visible()


# ---------------------------------------------------------------------------
# F-14 — edit-gate modal plain-language copy
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_edit_gate_modal_plain_language_copy(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Drives `_showEditModal()` directly (same approach as
    test_20260706_refinement_scope_modal.py) — no generated résumé or edit
    state needed, since the modal itself doesn't compute _detectEdits()."""
    BasePage(page, live_server).load()

    page.evaluate(
        "() => { window.__editChoice = 'PENDING';"
        " _showEditModal(null).then(r => { window.__editChoice = r; }); }"
    )
    page.wait_for_selector("#editModal:not(.hidden)", timeout=DEFAULT_TIMEOUT_MS)

    title = (page.text_content("#editModalTitle") or "").strip().lower()
    assert "edited the preview" not in title  # the old, denser heading is gone
    assert "aren't saved yet" in title

    body = (page.text_content("#editModalBody") or "").lower()
    # Plain language naming each choice's effect, not the old "ground truth" copy.
    assert "use edits as baseline" in body
    assert "discard edits" in body
    assert "ground truth" not in body

    page.click("#btnCancelRefine")
    page.wait_for_function("() => window.__editChoice === 'cancel'", timeout=DEFAULT_TIMEOUT_MS)

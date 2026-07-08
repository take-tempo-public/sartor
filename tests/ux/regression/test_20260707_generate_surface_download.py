"""Regression: F-09 honest Generate copy + F-10 server-served download (2026-07 UX review).

F-09 — the corpus-mode Generate is a deterministic assemble of the frozen
``approved_composition`` (``generation.py._frozen_composition``), but Step 5's
copy read as "another AI step". The fix is a state-aware copy pair on
``#panelGenerate``: ``#generateStepCopyFrozen`` (the deterministic-assembly
claim) shows ONLY after Compose's Save-and-continue actually froze a
composition (``_compositionFrozen`` in app.js — set from the freeze POST's
success, reset on fresh analysis / new-tailoring / prior-app resume);
``#generateStepCopyLegacy`` (the original LLM framing) shows otherwise, so the
legacy/fallback LLM path never carries a determinism claim it can't honor.

F-10 — the download used to fetch bytes into a blob and click a synthetic
anchor, which Chrome's multiple-automatic-downloads heuristic could silently
block (documented by an in-app caveat, now retired). ``/api/download-edited``
now returns ``{download_url}`` onto GET ``/api/download/<path>`` (a real
``Content-Disposition: attachment`` response — asserted at route level in
``tests/test_persona_routes.py``) and the client follows it as a plain
navigation the browser's download manager owns. A failed download surfaces in
the shared error modal — never a silent no-op.

Copy assertions use ``text_content()`` case-insensitively: ``.edit-hint`` is
CSS-uppercased (``static/style.css``), so ``inner_text`` would be SHOUTING.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import (
    bundled_persona_id,
    seed_application,
    seed_exp_with_bullets,
    seed_run,
    seed_user,
    write_context_file,
)
from ui_pages import (
    BasePage,
    PriorAppsPage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardOutputPage,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import ErrorModal, Output, Wizard

_JD = (
    "Senior Backend Engineer, Platform. Python on Postgres + AWS with Kafka "
    "as the event backbone. Lead architecture reviews; mentor a team of 6."
)

_RESUME_JSON = {
    "basics": {
        "name": "Alice Resumed",
        "label": "Staff Platform Engineer",
        "email": "alice@example.com",
    },
    "work": [
        {
            "name": "Acme Logistics",
            "position": "Staff Engineer",
            "startDate": "2021-01",
            "highlights": ["Led the Kafka migration across 12 topics"],
        }
    ],
}


def _seed_step6_state(ux_app: ModuleType) -> int:
    """Walk-B recipe: an already-generated application resumable into Step 6."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # non-empty corpus → smart landing keeps Tailor
    pid = bundled_persona_id()
    aid = seed_application(cid, title="Senior Backend @ Acme")
    rid = seed_run(
        aid,
        iteration=0,
        generated_resume_md="# Alice Resumed\n\n## Experience\n\n- Led the Kafka migration",
        persona_template_id=pid,
    )
    write_context_file(
        ux_app,
        "alice",
        "context_resume_iter1.json",
        {
            "application_run_id": rid,
            "iteration": 1,
            "last_generated_json_resume": _RESUME_JSON,
        },
    )
    return aid


# ---------------------------------------------------------------------------
# F-09 — state-aware Step 5 copy
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_frozen_composition_path_shows_deterministic_copy(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compose → Save-and-continue (freeze) → Step 5 shows the honest claim."""
    from tests.ux.stubs import install_llm_stubs

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    compose = WizardComposePage(page, live_server).open()
    assert compose.experience_card_count() >= 1
    compose.continue_to_template()  # Save-and-continue → the freeze POST

    page.click(Wizard.CONTINUE_TO_GENERATE)
    page.wait_for_selector(Wizard.PANEL_GENERATE, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    frozen = page.locator(Wizard.GENERATE_COPY_FROZEN)
    expect(frozen).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    copy = (frozen.text_content() or "").lower()
    assert "assembled instantly from your approved composition" in copy
    assert "no ai variation" in copy
    expect(page.locator(Wizard.GENERATE_COPY_LEGACY)).to_be_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_legacy_path_never_claims_deterministic_assembly(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rail-jump to Step 5 WITHOUT a freeze → the LLM framing, no determinism claim."""
    from tests.ux.stubs import install_llm_stubs

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    # Straight to Step 5 via the rail — no Compose save, nothing frozen.
    base = BasePage(page, live_server)
    base.goto_step(5)
    page.wait_for_selector(Wizard.PANEL_GENERATE, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    legacy = page.locator(Wizard.GENERATE_COPY_LEGACY)
    expect(legacy).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
    assert "the ai writes a tailored" in (legacy.text_content() or "").lower()
    frozen = page.locator(Wizard.GENERATE_COPY_FROZEN)
    expect(frozen).to_be_hidden()
    # The determinism claim is nowhere in the visible panel.
    panel_text = (page.locator(Wizard.PANEL_GENERATE).inner_text() or "").lower()
    assert "assembled instantly" not in panel_text


# ---------------------------------------------------------------------------
# F-10 — server-served download; failure feedback; caveat retired
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_download_is_server_served_attachment(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Download résumé = a navigation to /api/download/<path>, not a blob URL."""
    aid = _seed_step6_state(ux_app)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    PriorAppsPage(page, live_server).resume_application(aid)
    out = WizardOutputPage(page, live_server).wait_loaded()
    expect(out.download_resume_button()).to_be_visible()

    with page.expect_download(timeout=DEFAULT_TIMEOUT_MS * 4) as dl_info:
        out.download_resume_button().click()
    download = dl_info.value

    # Server-served: the download's source URL is the containment-gated GET
    # route on OUR server (pre-fix it was a blob: URL minted client-side), and
    # the filename came from its Content-Disposition attachment header.
    assert download.url.startswith(live_server)
    assert "/api/download/" in download.url
    assert download.suggested_filename.endswith(".docx")
    assert download.suggested_filename.startswith("resume_")

    # The attachment response downloads WITHOUT navigating the app away.
    expect(page.locator(Output.PANEL)).to_be_visible()
    assert page.url.rstrip("/") == live_server.rstrip("/")

    # The retired Chrome silent-block caveat is gone from the surface.
    body_text = (page.locator("body").inner_text() or "").lower()
    assert "silently block" not in body_text


@pytest.mark.ux
@pytest.mark.slow
def test_download_failure_surfaces_error_modal(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """A failing download POST opens the error modal — never a silent no-op."""
    aid = _seed_step6_state(ux_app)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    PriorAppsPage(page, live_server).resume_application(aid)
    out = WizardOutputPage(page, live_server).wait_loaded()
    expect(out.download_resume_button()).to_be_visible()

    # Force a deterministic server-side 400: bind the client to a user the
    # server doesn't know (top-level `let currentUser` is reassignable from
    # the page's global scope).
    page.evaluate("() => { currentUser = 'ghost'; }")

    out.download_resume_button().click()
    page.wait_for_selector(
        f"{ErrorModal.MODAL}:not(.hidden)", state="visible", timeout=DEFAULT_TIMEOUT_MS
    )
    detail = page.eval_on_selector(ErrorModal.TEXT, "el => el.value") or ""
    assert "download failed" in detail.lower()

    # And the button is re-enabled for a retry (no stuck disabled state).
    expect(page.locator(Output.DOWNLOAD_RESUME)).to_be_enabled()

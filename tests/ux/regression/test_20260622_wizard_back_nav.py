"""Regression: PX-22 — browser Back / Forward traverse wizard steps.

`refactor/app-blueprints-templates` (Sprint 8.3e rider, owner-approved). The
wizard gained a History API integration in `static/app.js`: `wizardGoTo` pushes a
`{wizardStep}` history entry on each step change, `wizardInit` / the resume-from-
prior landings stamp a baseline, and a `popstate` listener restores the step
(re-running the step-entry side-effects, never re-pushing). This drives the wizard
forward, then proves the browser **Back** button steps the rail backward (instead
of leaving the page) and **Forward** restores it — the core PX-22 contract.

Scope is deliberately session-only (no address-bar `?step=N`, no deep-link-on-load
restore), so the test stays within one navigation. The active step is read off the
`.wizard-step.active` rail button (`data-wstep`), which mirrors `_wizardStep`.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardComposePage, WizardJobPage

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."

_ACTIVE_STEP = (
    "() => { const b = document.querySelector('.wizard-step.active');"
    " return b ? parseInt(b.dataset.wstep, 10) : null; }"
)


def _active_step(page: Page) -> int | None:
    return page.evaluate(_ACTIVE_STEP)


@pytest.mark.ux
@pytest.mark.slow
def test_browser_back_forward_traverses_wizard_steps(
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

    # Drive forward: analyze (Step 1) → Compose (Step 3). Each wizardGoTo pushes a
    # history entry, so the browser back-stack now holds the earlier step(s).
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open()
    page.wait_for_function(
        "() => document.querySelector('.wizard-step.active')?.dataset.wstep === '3'"
    )
    assert _active_step(page) == 3

    # Browser Back steps the wizard backward (popstate restore), not off the page.
    page.go_back()
    page.wait_for_function(
        "() => { const b = document.querySelector('.wizard-step.active');"
        " return b && parseInt(b.dataset.wstep, 10) < 3; }"
    )
    back_step = _active_step(page)
    assert back_step is not None and back_step < 3, (
        f"PX-22: browser Back must step the wizard back, not leave it; "
        f"active step is now {back_step!r}"
    )

    # Forward returns to the step we left.
    page.go_forward()
    page.wait_for_function(
        "() => document.querySelector('.wizard-step.active')?.dataset.wstep === '3'"
    )
    assert _active_step(page) == 3, "PX-22: browser Forward must restore the wizard step"

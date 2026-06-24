"""Regression: Compose bullet reordering persists, and Reset reverts it.

Closes the coverage gap left by feat/bullet-drag-reorder (2026-06-04): the
POST contract was unit-tested but the live browser interaction had no test.

`bullet_order` round-trips through the real autosave POST `/composition` and
the GET re-read on a compose re-load — the in-process server makes this a
genuine server round-trip (the reason the flow stub fakes the LLM, not the
backend). Two paths share the same persistence: keyboard (the a11y floor,
must-pass) and the pointer drag.

Note: the app's full-page resume targets Step 6, so "persists across reload"
is verified by re-loading the Compose step (navigate away + back), which
re-fetches GET `/composition` and re-reads the saved order.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Response

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
_K8S = "Reduced Kubernetes"
_SYNCS = "Attended weekly syncs"


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


def _reach_compose(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_keyboard_reorder_persists_and_reset_reverts(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # Default AI ranking: the JD-relevant Kubernetes bullet is first.
    assert compose.bullet_texts()[0].startswith(_K8S)
    assert not compose.has_custom_order()

    # Move it down → [syncs, k8s]; the debounced autosave POSTs the order.
    with page.expect_response(_is_composition_post):
        compose.move_down(_K8S)
    assert compose.bullet_texts()[0].startswith("Attended")
    assert compose.has_custom_order()

    # Re-load Compose (away + back) → GET re-reads the saved order.
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    assert compose.bullet_texts()[0].startswith("Attended"), "order did not persist"
    assert compose.has_custom_order()

    # Reset → revert to AI (score) ranking; order cleared.
    with page.expect_response(_is_composition_post):
        compose.reset_order()
    assert compose.bullet_texts()[0].startswith(_K8S)
    assert not compose.has_custom_order()


@pytest.mark.ux
@pytest.mark.slow
def test_pointer_drag_reorders(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    assert compose.bullet_texts()[0].startswith(_K8S)

    # Drag the Kubernetes bullet below "weekly syncs"; the drop autosaves.
    with page.expect_response(_is_composition_post):
        compose.drag_below(_K8S, _SYNCS)
    assert compose.bullet_texts()[0].startswith("Attended"), "drag did not reorder"
    assert compose.has_custom_order()

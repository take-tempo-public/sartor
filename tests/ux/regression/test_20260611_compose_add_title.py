"""Regression: Compose "+ Add title" + per-JD title pin (feat/compose-add-title, #7).

In Step 3 (Compose) a user can add an alternative job title for an experience —
written into the corpus as a SOURCED, immediately-eligible ExperienceTitle
(truthful_enough_to_use=1, not a context-only override) — and then pin it as the
title this JD's résumé uses. The pin round-trips through the real autosave POST
`/composition` and the GET re-read on a Compose re-load (a genuine server
round-trip; only the LLM is stubbed).

Mirrors the bullet-drag regression's flow: stub the LLM, analyze, skip to
Compose, act, then navigate away + back to prove persistence via GET re-read.
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
_OFFICIAL = "Staff Engineer"  # seeded official title
_ALT = "Principal Engineer"  # added in Compose


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


def _is_title_post(resp: Response) -> bool:
    return "/titles" in resp.url and resp.request.method == "POST"


def _reach_compose(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # seeds the official "Staff Engineer" title
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_add_title_then_pin_persists(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # Only the seeded official title exists, and it is the chosen one.
    assert compose.title_texts() == [_OFFICIAL]
    assert compose.title_is_selected(_OFFICIAL)

    # Add an alternative title — writes a sourced, eligible corpus row, then
    # reloads composition so it appears as a selectable option.
    with page.expect_response(_is_title_post):
        compose.add_title(_ALT)
    assert set(compose.title_texts()) == {_OFFICIAL, _ALT}
    # Still defaults to the official until the user pins the alternative.
    assert compose.title_is_selected(_OFFICIAL)
    assert not compose.title_is_selected(_ALT)

    # Pin the alternative for this JD; the debounced autosave POSTs the pin.
    with page.expect_response(_is_composition_post):
        compose.select_title(_ALT)
    assert compose.title_is_selected(_ALT)
    assert not compose.title_is_selected(_OFFICIAL)

    # Re-load Compose (away + back) → GET re-reads the saved pin.
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    assert set(compose.title_texts()) == {_OFFICIAL, _ALT}
    assert compose.title_is_selected(_ALT), "title pin did not persist"

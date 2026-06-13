"""Regression: per-role intro Corpus Item (feat/experience-summary-item, B.4).

Two surfaces, both LLM-free (the analyzer is stubbed; the real routes run):
- Career corpus: an expanded experience card carries a 'Role intro variants'
  editor with a '+ Add intro' affordance; adding one persists + renders.
- Compose: the application-level 'Add role intros' opt-in toggle surfaces a
  per-role picker; turning it on defaults each role to the (stubbed)
  recommended intro, and that choice survives an away-and-back reload via the
  real /composition POST + GET round-trip.

Smart-landing gotcha (Sprint 6.4): selecting a user no longer guarantees the
Tailor surface — a non-empty corpus is seeded so the corpus tab renders cards.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Response, expect

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    CorpusPage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.selectors import Compose, Corpus

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


def _seed_two_intros(experience_id: int) -> list[int]:
    from db.models import ExperienceSummaryItem
    from db.session import get_session

    s = get_session()
    try:
        ids = []
        for i, text in enumerate(["Platform-scale framing.", "Growth-builder framing."]):
            si = ExperienceSummaryItem(
                experience_id=experience_id, text=text,
                display_order=i, is_active=1, source="manual",
            )
            s.add(si)
            s.flush()
            ids.append(si.id)
        s.commit()
        return ids
    finally:
        s.close()


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


# -------------------------------------------------------------------
# Career corpus — per-role intro editor
# -------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_corpus_role_intro_editor_add(page: Page, live_server: str,
                                      ux_app: ModuleType) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open().wait_for_cards()
    corpus.expand_card(0)

    # The editor + its affordance are present on the expanded card.
    expect(corpus.exp_summary_section()).to_be_visible()
    expect(corpus.add_intro_button()).to_be_visible()

    # Add an intro through the real POST /api/experiences/<id>/summaries.
    corpus.add_intro_button().click()
    page.fill("#formModal_text", "Owned the platform end-to-end.")
    page.click("#formModalSubmit")
    # refreshExperienceSummaries re-fetches after the POST; expect() auto-retries
    # until the new variant's textarea (the only one — the role started empty)
    # carries the added value.
    expect(
        page.locator(f"{Corpus.EXP_SUMMARY_SECTION} .summary-variant-text")
    ).to_have_value("Owned the platform end-to-end.")


# -------------------------------------------------------------------
# Compose — "Add role intros" opt-in toggle + per-role picker
# -------------------------------------------------------------------


def _reach_compose(page: Page, live_server: str, ux_app: ModuleType,
                   monkeypatch: pytest.MonkeyPatch) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    eid = seed_exp_with_bullets(cid)
    _seed_two_intros(eid)  # 2 variants → the toggle renders + recommend fires
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_compose_role_intros_toggle_defaults_and_persists(
    page: Page, live_server: str, ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # Off by default — the picker is hidden (opt-in).
    toggle = compose.role_intros_toggle()
    expect(toggle).not_to_be_checked()
    assert page.locator(f"{Compose.ROLE_INTRO}:not(.hidden)").count() == 0

    # Turn it on: defaults the role to the stubbed recommendation (first variant)
    # via the real /composition POST + recommend + GET re-read.
    with page.expect_response(_is_composition_post):
        compose.enable_role_intros()
    assert "Platform-scale framing." in compose.chosen_intro_texts()

    # Away + back: the toggle state + the defaulted choice survive the reload.
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    expect(compose.role_intros_toggle()).to_be_checked()
    assert "Platform-scale framing." in compose.chosen_intro_texts()

"""Regression: skill Corpus Item (feat/skill-group-item, B.5).

Two surfaces, both LLM-free (analyzer stubbed; real routes run):
- Career corpus: a candidate-level 'Skills' editor lists the skills and adds a
  new one through the real POST /api/users/<u>/skills.
- Compose: a candidate-level 'Skills' card renders a row per active skill;
  dropping one persists excluded_skill_ids via the real /composition POST, and
  the drop survives an away-and-back reload.

Smart-landing gotcha (Sprint 6.4): a non-empty corpus is seeded so the corpus
tab renders + the Tailor surface is reachable.
"""

from __future__ import annotations

import re
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
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes, Kafka, Postgres at scale."


def _seed_skills(candidate_id: int, names: list[str]) -> list[int]:
    from db.models import Skill
    from db.session import get_session

    s = get_session()
    try:
        ids: list[int] = []
        for i, name in enumerate(names):
            sk = Skill(
                candidate_id=candidate_id,
                name=name,
                display_order=i,
                is_active=1,
                is_pending_review=0,
                source="imported",
            )
            s.add(sk)
            s.flush()
            ids.append(sk.id)
        s.commit()
        return ids
    finally:
        s.close()


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


@pytest.mark.ux
@pytest.mark.slow
def test_corpus_skills_editor_add(page: Page, live_server: str, ux_app: ModuleType) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    _seed_skills(cid, ["Python", "Kafka"])

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open().wait_for_cards()

    # The candidate-level skills editor + seeded skills render.
    expect(page.locator("#skillsEditorSection")).to_be_visible()
    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(2)

    # Add a skill through the real POST /api/users/<u>/skills.
    page.click("#skillsEditorSection .corpus-section-header button")
    page.fill("#formModal_name", "Kubernetes")
    page.click("#formModalSubmit")
    expect(page.locator("#skillsEditorList .skill-editor-row")).to_have_count(3)
    expect(page.locator("#skillsEditorList")).to_contain_text("Kubernetes")


@pytest.mark.ux
@pytest.mark.slow
def test_compose_skills_card_drop_persists(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    _seed_skills(cid, ["Python", "Kafka", "Postgres"])
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()

    # Skills card renders a row per active skill (the auto-fired recommend-skills
    # stub returns all three, so has_recommendation settles + no refire loop).
    # wait_skills_card() settles the re-render cascade first (flaky-class fix).
    compose.wait_skills_card()
    expect(page.locator(Compose.SKILL_ROW)).to_have_count(3)

    # Drop one skill → debounced /composition POST persists excluded_skill_ids.
    # drop_skill() settles before resolving the row, so the node can't detach
    # under a late cascade between resolve and click.
    with page.expect_response(_is_composition_post):
        compose.drop_skill("Postgres")

    # Away + back: the dropped skill returns marked excluded (real GET re-read).
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    # The excluded class lands after the reload's GET re-read repaints the skills
    # card; give it the suite's standard 15s load headroom rather than expect()'s
    # default 5s, which raced the repaint under end-of-suite CI load (the
    # load-flake class this suite guards — intermittent, reproduces under CPU
    # saturation). The class DOES arrive (passes under local load) — just late.
    expect(page.locator(Compose.SKILL_ROW, has_text="Postgres")).to_have_class(
        re.compile(r"skill-excluded"), timeout=15_000
    )

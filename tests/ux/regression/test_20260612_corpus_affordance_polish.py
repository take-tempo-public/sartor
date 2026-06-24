"""Regression: Sprint 6.3 corpus-affordance polish (#2 + #5 + KW2).

Covers the four items of `fix/corpus-affordance-polish`:
- #2  the β.6e "Add variant" affordance is present (regression-lock — the
      finding was "referenced in copy but no affordance"; it has since shipped).
- empty-state copy no longer overpromises résumé import as "automatic"
      (imported items land pending review).
- KW2 the corpus-wide "Accept all pending" banner control clears every
      pending flag and self-hides the banner.
- #5  the panel collapse chevron (`.panel-header::after`) is enlarged ~50%.

LLM-free: corpus is seeded directly into the DB.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage


def _seed_pending_experience(candidate_id: int) -> int:
    """One experience with an official title + a pending alt title + two
    pending bullets — enough to light the onboarding banner and exercise the
    corpus-wide accept."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id, company="Acme", start_date="2022-01", display_order=0
        )
        s.add(e)
        s.flush()
        s.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Staff Engineer",
                is_official=1,
                is_pending_review=0,
                source="official",
            )
        )
        s.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Senior Engineer",
                is_official=0,
                is_pending_review=1,
                source="llm_proposed:ux",
            )
        )
        for i in range(2):
            s.add(
                Bullet(
                    experience_id=e.id,
                    text=f"Pending bullet {i}",
                    display_order=i,
                    is_active=1,
                    is_pending_review=1,
                    source="llm_proposed:ux",
                    has_outcome=0,
                )
            )
        s.commit()
        return e.id
    finally:
        s.close()


@pytest.mark.ux
@pytest.mark.slow
def test_add_variant_affordance_present(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """#2 — the summary-variants editor + its '+ Add variant' button are
    surfaced on the Corpus tab (locks in the β.6e affordance)."""
    seed_user(ux_app, "alice")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open()

    expect(corpus.summary_variants_section()).to_be_visible()
    expect(corpus.add_variant_button()).to_be_visible()


@pytest.mark.ux
@pytest.mark.slow
def test_empty_state_copy_is_review_honest(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Empty-state copy reflects the review step and drops the misleading
    'automatically' (imported items land pending review)."""
    seed_user(ux_app, "alice")  # no experiences → empty state

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open()

    hint = page.locator("#corpusEmptyHint")
    expect(hint).to_contain_text("review")
    # text_content() (not inner_text) — robust to casing/whitespace.
    assert "automatic" not in (hint.text_content() or "").lower()


@pytest.mark.ux
@pytest.mark.slow
def test_accept_all_pending_clears_banner(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """KW2 — the banner's 'Accept all pending' clears every pending flag. On a
    non-empty corpus the pending prompt then flips to the Sprint 6.4 ready
    hand-off ('Start tailoring →'), not a bare hide (an EMPTY corpus is what
    hides it — see test_20260612_corpus_first_landing)."""
    cid = seed_user(ux_app, "alice")
    _seed_pending_experience(cid)

    # The control guards behind a confirm(); auto-accept it.
    page.on("dialog", lambda dialog: dialog.accept())

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open()

    expect(corpus.onboarding_banner()).to_be_visible()
    corpus.accept_all_button().click()
    # After the POST clears the flags + counts refresh, the pending controls are
    # gone and the ready CTA appears (banner stays visible, now is-ready).
    expect(corpus.start_tailoring_button()).to_be_visible()
    expect(corpus.accept_all_button()).to_be_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_panel_chevron_enlarged(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """#5 — the panel collapse chevron (::after) is enlarged to 18px (~+50%
    over the old 12px). Light computed-style guard."""
    seed_user(ux_app, "alice")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open()

    size = page.eval_on_selector(
        "#panelCorpus .panel-header", "el => getComputedStyle(el, '::after').fontSize"
    )
    assert size == "18px"

"""Regression: robust prior-app resume (#4) + editable/legible cards (#24).

feat/prior-app-resume-robustness (2026-06-11):

#4 — the v1.0.5 resume path only offered "Resume in wizard" when a résumé had
been generated, so an application abandoned at analyze/clarify/compose was a
dead card. `_build_resume_state` now classifies the FURTHEST step that has data:
an analyze-only application resumes back to Step 1 with its analysis rehydrated
from the saved context file (no `/api/clarify` or `/api/generate` re-spend).

#24 — prior-app cards never showed a company (`Application.company` was never
populated) and the proposal pill read an opaque "N pending". Title + company are
now user-editable in the detail modal (PUT /meta, save-on-blur), and the pill
reads "N to review".

Both tests drive the live frontend; all state is DB-/context-seeded, so the run
is deterministic + offline (no LLM).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import (
    seed_application,
    seed_exp_with_bullets,
    seed_run,
    seed_user,
    write_context_file,
)
from tests.ux.stubs import CANNED_ANALYSIS
from ui_pages import PriorAppsPage, UserPickerPage
from ui_pages.base import BasePage
from ui_pages.selectors import PriorApps, Wizard


def _seed_analyze_only_app(ux_app: ModuleType, candidate_id: int) -> int:
    """An application that ran analyze but never generated — with a real on-disk
    context file carrying the analysis (the exact #4 gap)."""
    aid = seed_application(candidate_id, title="Senior Platform Engineer",
                           company="", jd_text="Kafka at scale.")
    rid = seed_run(aid, iteration=0)  # no generated_resume_md
    write_context_file(ux_app, "alice", "context_an_iter0.json", {
        "application_run_id": rid,
        "iteration": 0,
        "llm_analysis": dict(CANNED_ANALYSIS),
        "deterministic_analysis": {
            "keyword_overlap": {"match_score": 0.42, "matched": ["python"],
                                "missing_from_resume": ["kafka"]},
            "ats_warnings": [],
        },
    })
    return aid


def _seed_pending_proposal(candidate_id: int, application_run_id: int) -> None:
    """One pending ProposalReview tied to the run, so the card renders the pill."""
    from db.models import Bullet, Experience, ProposalReview
    from db.session import get_session

    s = get_session()
    try:
        exp = s.query(Experience).filter_by(candidate_id=candidate_id).first()
        assert exp is not None
        bullet = s.query(Bullet).filter_by(experience_id=exp.id).first()
        assert bullet is not None
        s.add(ProposalReview(
            application_run_id=application_run_id, bullet_id=bullet.id,
            original_text="proposed", decision="pending",
        ))
        s.commit()
    finally:
        s.close()


@pytest.mark.ux
@pytest.mark.slow
def test_analyze_only_application_resumes_to_step_1(
    page: Page, live_server: str, ux_app: ModuleType,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # non-empty corpus → smart landing keeps us on Tailor
    aid = _seed_analyze_only_app(ux_app, cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    prior = PriorAppsPage(page, live_server)
    prior.open_detail(aid)
    # Crux of #4: the Resume button is offered for an analyze-only app
    # (previously hidden — resume_state.resumable was False).
    assert prior.resume_visible()
    prior.resume()

    # Landed on Step 1 with the analysis rehydrated from the saved context
    # (#analysisContent is empty after a fresh user-select until resume fills it).
    expect(page.locator(f"{Wizard.ANALYSIS_CONTENT} > *").first).to_be_visible()
    expect(page.locator("#cbStatusbarStep")).to_have_text("Step 1 of 6")


@pytest.mark.ux
@pytest.mark.slow
def test_card_company_editable_and_pill_relabeled(
    page: Page, live_server: str, ux_app: ModuleType,
) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # gives the pending proposal a real bullet FK
    aid = seed_application(cid, title="Staff PM", company="",
                           jd_text="Own the roadmap.")
    rid = seed_run(aid, iteration=0)
    _seed_pending_proposal(cid, rid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    # #24: the relabeled, legible proposal pill (was "1 pending").
    expect(page.locator(PriorApps.PENDING_PILL)).to_have_text("1 to review")

    # #24: setting a company in the detail modal persists onto the card.
    prior = PriorAppsPage(page, live_server)
    prior.open_detail(aid)
    prior.set_company("Acme Robotics")
    expect(page.locator(PriorApps.card_company(aid))).to_have_text("Acme Robotics")

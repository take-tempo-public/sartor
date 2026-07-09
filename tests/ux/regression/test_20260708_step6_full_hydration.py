"""Regression: full Step-1/2/3 hydration on resume into Step 6 (#7, Option A).

feat/ux-busy-states-and-hydration (2026-07-08):

Before this fix, `_build_resume_state` (blueprints/applications.py) early-
returned at Step 6 with ONLY the résumé/cover-letter payload whenever a run
had `generated_resume_md` — discarding the `llm_analysis` / clarifications /
composition data already parsed from the SAME on-disk context file. Resuming
a generated application into the wizard therefore showed blank Step 1-3
panels on back-navigation, even though the data existed.

The fix (Option A, chosen by the owner): `_build_resume_state` ALWAYS merges
the pre-generate hydration block into the Step-6 response when the context
carries a completed analysis (`_pre_generate_hydration`), and
`_resumeIntoStep6` (static/app.js) renders it — mirroring
`_resumeIntoPreGenerateStep` — plus hydrates Compose via `loadComposition()`
when the saved context reached Step 3 (`has_composition`).

The corresponding risk: since `loadComposition()` fires the same auto-
recommend/draft/gap-fill cascade a FRESH Compose arrival does, hydration must
not "clobber" already-decided state by re-firing that cascade. The seeded
context here carries an already-persisted summary draft
(`composition_overrides.summary_text`) and an already-drafted (zero-proposal)
gap-fill pass (`llm_gap_fill_proposals: []`), so the server's own has_draft /
has_gap_fill flags — read fresh off the `/composition` GET — must already
gate the client-side auto-fire latches shut. The test asserts this directly
by tracking every request URL and requiring none of the three draft/recommend
POST routes fire.

LLM-free (`install_llm_stubs`) + fully DB-/context-seeded, so the run is
deterministic and offline.
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
from tests.ux.stubs import CANNED_ANALYSIS, install_llm_stubs
from ui_pages import PriorAppsPage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Compose, Wizard


def _seed_generated_app_with_full_context(ux_app: ModuleType, candidate_id: int) -> int:
    """A generated application (Step 6) whose context file ALSO carries a
    completed analysis, saved clarify Q&A, and a reached-Compose signal with
    already-persisted draft state (has_draft / has_gap_fill both true)."""
    aid = seed_application(
        candidate_id, title="Staff Engineer", company="Acme", jd_text="Kafka at scale."
    )
    rid = seed_run(aid, iteration=0, generated_resume_md="# Alice Resume\n\nExperience.")
    write_context_file(
        ux_app,
        "alice",
        "context_gen_iter0.json",
        {
            "application_run_id": rid,
            "iteration": 0,
            "llm_analysis": dict(CANNED_ANALYSIS),
            "deterministic_analysis": {
                "keyword_overlap": {
                    "match_score": 0.42,
                    "matched": ["python"],
                    "missing_from_resume": ["kafka"],
                },
                "ats_warnings": [],
            },
            "clarification_questions": [
                {"id": "q1", "kind": "experience_probe", "text": "Ran k8s in prod?"},
            ],
            "clarifications": {"q1": "Yes, on the platform team."},
            # has_composition=True (composition_overrides present) AND
            # has_draft=True (summary_text present) — the summary draft
            # cascade must NOT re-fire on hydration.
            "composition_overrides": {"summary_text": "Persisted positioning summary."},
            # has_gap_fill=True (key presence, even with zero proposals) — the
            # gap-fill cascade must NOT re-fire on hydration either.
            "llm_gap_fill_proposals": [],
        },
    )
    return aid


@pytest.mark.ux
@pytest.mark.slow
def test_generated_app_resume_hydrates_steps_1_to_3_without_recascading(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_llm_stubs(ux_app, monkeypatch)
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # non-empty corpus → smart landing keeps us on Tailor
    aid = _seed_generated_app_with_full_context(ux_app, cid)

    requests: list[str] = []
    page.on("request", lambda req: requests.append(req.url))

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    prior = PriorAppsPage(page, live_server)
    prior.resume_application(aid)

    # Lands on Step 6 (a résumé was generated — target_step stays 6).
    expect(page.locator("#cbStatusbarStep")).to_have_text("Step 6 of 6")

    # Compose was hydrated in the BACKGROUND as part of landing on Step 6
    # (rs.has_composition gated the loadComposition() call) — its terminal
    # render is reached even though the panel itself is still hidden.
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS)
    # EXPERIENCE_CARD also matches the always-present positioning card (and a
    # skills card, when any skill exists) — exclude both for a count scoped
    # to actual per-role cards, same pattern wizard_compose.py's _first_card
    # uses.
    role_cards = f"{Compose.EXPERIENCE_CARD}:not(.positioning-card):not(.skills-card)"
    assert page.locator(role_cards).count() == 1

    # Crux of the clobber risk: the already-persisted draft/gap-fill state
    # must have suppressed the auto-fire cascade — none of these routes fire.
    assert not any(
        u.endswith(("/draft-summary", "/recommend-summary", "/draft-gap-fill")) for u in requests
    ), f"unexpected background draft/recommend call(s): {requests}"

    # Back-navigation to Step 1 shows the analysis populated WITHOUT a fresh
    # fetch — the DOM was rendered during resume, not on this click.
    page.click(Wizard.step_button(1))
    expect(page.locator(f"{Wizard.ANALYSIS_CONTENT} > *").first).to_be_visible()

    # Step 2 shows the saved clarify Q&A, answer prefilled.
    page.click(Wizard.step_button(2))
    expect(page.locator(Wizard.CLARIFY_QUESTION_TEXTAREA).first).to_have_value(
        "Yes, on the platform team."
    )

    # Step 3 (Compose) — already rendered from the background hydration above;
    # navigating to it must not re-trigger the draft/gap-fill cascade either.
    page.click(Wizard.step_button(3))
    page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS)
    assert not any(
        u.endswith(("/draft-summary", "/recommend-summary", "/draft-gap-fill")) for u in requests
    ), f"unexpected background draft/recommend call(s) after Step-3 nav: {requests}"

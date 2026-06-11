"""Regression: Compose custom bullet order persists on reload for an
experience that has NO LLM recommendations.

Surfaced 2026-06-04 while building feat/playwright-ux-suite's drag test, fixed
on fix/compose-order-no-recommendations (Sprint 6.1). The saved
`composition_overrides.bullet_order` always round-tripped through POST/GET
`/composition` (and `generate()` honored it) — but `_renderComposeCard`
(static/app.js) routed a no-recommendations experience through `_dropoffPick`,
which re-sorted the fallback bullets by *score*, so the on-screen order
*visually reverted* after a Compose reload even though the data was intact.

The companion test_20260604_bullet_drag_reorder.py covers the common
(recommendations-present) path, where bullets land in the `visible` set and the
GET array order is preserved. This test covers the *fallback* path it can't
reach: an experience with no recommendations.

To exercise the no-recommendations path while keeping WizardComposePage's
deterministic `.recommended`-row wait (engineered to dodge the skip-to-compose
double-render race), we seed TWO experiences:
  - A — under test, NO recommendations, latest start_date so it is FIRST in the
    GET (ORDER BY start_date DESC); the page object reads `.first`.
  - B — recommended, earlier start_date; exists only so a `.recommended` row
    appears and `_wait_loaded` resolves on the real post-recommend render.
A per-test recommend stub recommends B only (skips A by company), installed
after install_llm_stubs to override its recommend-everything default.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page, Response

from tests.ux.seeding import seed_user
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

_NO_REC_CO = "NoRecCo"   # experience A — under test (no recommendations)
_REC_CO = "RecCo"        # experience B — recommended (anchors the load wait)


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


def _seed_two_experiences(candidate_id: int) -> None:
    """A (NoRecCo, latest date → first in GET) with a JD-strong + a weak bullet,
    and B (RecCo, earlier date) with one bullet so a recommended row renders."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        a = Experience(
            candidate_id=candidate_id, company=_NO_REC_CO,
            start_date="2023-01", display_order=0,
        )
        s.add(a)
        s.flush()
        s.add(ExperienceTitle(
            experience_id=a.id, title="Staff Engineer",
            is_official=1, is_pending_review=0, source="official",
        ))
        s.add(Bullet(
            experience_id=a.id,
            text="Reduced Kubernetes latency 40% across 12 services",
            display_order=0, is_active=1, is_pending_review=0,
            source="manual", has_outcome=1,
        ))
        s.add(Bullet(
            experience_id=a.id, text="Attended weekly syncs",
            display_order=1, is_active=1, is_pending_review=0,
            source="manual", has_outcome=0,
        ))

        b = Experience(
            candidate_id=candidate_id, company=_REC_CO,
            start_date="2021-01", display_order=1,
        )
        s.add(b)
        s.flush()
        s.add(ExperienceTitle(
            experience_id=b.id, title="Senior Engineer",
            is_official=1, is_pending_review=0, source="official",
        ))
        s.add(Bullet(
            experience_id=b.id,
            text="Built Kafka pipeline processing 2M events/day",
            display_order=0, is_active=1, is_pending_review=0,
            source="manual", has_outcome=1,
        ))
        s.commit()
    finally:
        s.close()


def _recommend_only_company(company: str) -> Any:
    """recommend_bullets stub: recommend every active bullet for the experience
    whose company == `company`, and NONE for the others — so the other
    experiences render via the no-recommendations fallback path under test."""
    def stub(client: Any, ctx: Any, username: str = "", run_id: str = "") -> dict[str, Any]:
        from db.models import Bullet, Candidate, Experience
        from db.session import get_session

        session = get_session()
        try:
            cand = session.query(Candidate).filter_by(username=username).first()
            if cand is None:
                return {"recommendations": []}
            recs: list[dict[str, Any]] = []
            for exp in (session.query(Experience)
                        .filter_by(candidate_id=cand.id, company=company).all()):
                bullet_ids = [
                    bl.id for bl in session.query(Bullet)
                    .filter_by(experience_id=exp.id, is_active=1)
                    .order_by(Bullet.display_order).all()
                ]
                if bullet_ids:
                    recs.append({
                        "experience_id": exp.id, "bullet_ids": bullet_ids,
                        "rationale": "stubbed: recommended experience",
                    })
            return {"recommendations": recs}
        finally:
            session.close()
    return stub


def _reach_compose(page: Page, live_server: str, ux_app: ModuleType,
                   monkeypatch: pytest.MonkeyPatch) -> WizardComposePage:
    import analyzer

    cid = seed_user(ux_app, "alice")
    _seed_two_experiences(cid)
    install_llm_stubs(ux_app, monkeypatch)
    # Override the recommend-everything default: only RecCo gets recommendations,
    # so NoRecCo (first card) renders via the no-recommendations fallback.
    monkeypatch.setattr(analyzer, "recommend_bullets", _recommend_only_company(_REC_CO))
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_no_recommendations_order_persists_on_reload(
    page: Page, live_server: str, ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)

    # First card = NoRecCo (latest start_date). No recommendations → fallback
    # render in score order: the JD-relevant Kubernetes bullet leads.
    assert compose.bullet_texts()[0].startswith(_K8S)
    assert not compose.has_custom_order()

    # Move it down → [syncs, k8s]; the debounced autosave POSTs the order.
    with page.expect_response(_is_composition_post):
        compose.move_down(_K8S)
    assert compose.bullet_texts()[0].startswith("Attended")
    assert compose.has_custom_order()

    # Re-load Compose (away + back) → GET re-reads the saved order. Pre-fix the
    # no-recommendations fallback re-sorted by score and reverted this; the fix
    # honors the GET-returned order.
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    assert compose.bullet_texts()[0].startswith("Attended"), \
        "no-recommendations custom order did not persist on reload"
    assert compose.has_custom_order()

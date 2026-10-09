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

import os
from types import ModuleType

import pytest
from playwright.sync_api import APIResponse, Page, Route, expect

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
    aid = seed_application(
        candidate_id, title="Senior Platform Engineer", company="", jd_text="Kafka at scale."
    )
    rid = seed_run(aid, iteration=0)  # no generated_resume_md
    write_context_file(
        ux_app,
        "alice",
        "context_an_iter0.json",
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
        },
    )
    return aid


@pytest.mark.ux
@pytest.mark.slow
def test_analyze_only_application_resumes_to_step_1(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
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
def test_card_company_editable_and_persists(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
) -> None:
    """#24: setting a company in the detail modal persists — reopening the
    modal shows the saved value.

    A4 (feat/prior-apps-pipeline): this used to also assert the relabeled
    proposal pill (`PriorApps.PENDING_PILL`, "N to review") and the edit
    echoing onto a card (`PriorApps.card_company()`) — both lived on the
    now-removed Applications panel's card and have no DOM home anymore
    (Pipeline rows carry neither a pending-proposals pill nor a company echo
    outside the modal — see docs/dev/blast-radius/prior-apps-pipeline.md's
    Deferred #3). The underlying `pending_proposals` VALUE stays covered at
    the route level (`tests/test_application_routes.py::test_pending_proposals_per_run`).
    """
    _company_round_trip(page, live_server, ux_app)


# --- Item 156's sibling, item 155: instrument (`docs/dev/diagnosis/test-reliability.md`) ---
#
# One CI attempt of the test above waited 5 s for "Company saved" and saw only "Notes saved".
# The attempt left no focus order and no request log, so the timeline below records both on
# ONE clock (the page's): focus moves, every fetch's start and settle, and every change to the
# shared toast. It prints on failure, and on every run when SARTOR_UX_TIMELINE=1.

_TIMELINE_JS = """
() => {
  if (window.__t155) return;
  const log = (window.__t155 = []);
  const t0 = performance.now();
  const rec = (kind, detail) => log.push([Math.round(performance.now() - t0), kind, detail]);
  const name = (el) => (el && (el.id || el.tagName)) || String(el);
  document.addEventListener('focusin', (e) => rec('focusin', name(e.target)), true);
  document.addEventListener('focusout', (e) => rec('focusout', name(e.target)), true);
  const realFetch = window.fetch;
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const what = `${(init && init.method) || 'GET'} ${url}`;
    rec('fetch>', what);
    return realFetch.apply(this, arguments).then(
      (r) => { rec('fetch<', `${what} ${r.status}`); return r; },
      (e) => { rec('fetch!', `${what} ${e}`); throw e; },
    );
  };
  const watch = () => {
    const t = document.getElementById('_corpusToast');
    if (!t) return false;
    rec('toast', `${t.className} | ${t.textContent}`);
    new MutationObserver(() => rec('toast', `${t.className} | ${t.textContent}`)).observe(
      t, { attributes: true, childList: true, characterData: true, subtree: true });
    return true;
  };
  if (!watch()) {
    const mo = new MutationObserver(() => { if (watch()) mo.disconnect(); });
    mo.observe(document.body, { childList: true });
  }
}
"""


def _print_timeline(page: Page, why: str) -> None:
    rows = page.evaluate("() => window.__t155 || []")
    print(f"\n--- item-155 timeline ({why}): ms kind detail ---")
    for ms, kind, detail in rows:
        print(f"{ms:>7} {kind:<8} {detail}")


def _company_round_trip(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """The body of `test_card_company_editable_and_persists`, shared with its probe."""
    cid = seed_user(ux_app, "alice")
    aid = seed_application(cid, title="Staff PM", company="", jd_text="Own the roadmap.")

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.evaluate(_TIMELINE_JS)

    prior = PriorAppsPage(page, live_server)
    prior.open_detail(aid)
    prior.set_company("Acme Robotics")
    # blur() triggers an async PUT; wait for its toast before re-reading, so
    # the reopen below observes the SAVED value, not a race against the fetch.
    try:
        expect(page.locator("#_corpusToast")).to_have_text("Company saved")
    except AssertionError:
        _print_timeline(page, "toast wait failed")
        raise
    if os.environ.get("SARTOR_UX_TIMELINE") == "1":
        _print_timeline(page, "passed")
    prior.open_detail(aid)  # reopen fresh — proves it round-trips through GET
    expect(page.locator(PriorApps.COMPANY_INPUT)).to_have_value("Acme Robotics")


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason=(
        "item 155 capability probe P-H1: with the notes PUT's response delivered right after "
        "the meta PUT's, the shared toast ends on 'Notes saved' and the 'Company saved' wait "
        "fails (docs/dev/diagnosis/test-reliability.md)"
    ),
)
def test_probe_notes_response_after_meta_response(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
) -> None:
    """P-H1: CAN the notes response landing after the meta response alone fail the wait?

    Holds each PUT /notes after fetching its real response, and delivers it only once the
    PUT /meta response has been delivered. Proves the ordering is SUFFICIENT for the symptom,
    not that it caused the CI failure.
    """
    held: list[tuple[Route, APIResponse]] = []

    def _hold_notes(route: Route) -> None:
        if route.request.method != "PUT":
            route.continue_()
            return
        held.append((route, route.fetch()))

    def _meta_then_notes(route: Route) -> None:
        if route.request.method != "PUT":
            route.continue_()
            return
        route.fulfill(response=route.fetch())
        while held:
            notes_route, notes_response = held.pop(0)
            notes_route.fulfill(response=notes_response)

    page.route("**/api/applications/*/notes", _hold_notes)
    page.route("**/api/applications/*/meta", _meta_then_notes)
    _company_round_trip(page, live_server, ux_app)

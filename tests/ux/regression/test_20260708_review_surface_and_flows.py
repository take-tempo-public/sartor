"""Regression: fix/review-surface-and-flows — corpus date-rail propagation
(#4) + surgical-refinement failure resilience (#5).

#4: `_saveExperienceField` (static/app.js) PUTs a field edit (company /
location / dates / summary) but never refreshed the collapsed card header —
editing an experience's start/end date left the visible `.corpus-card-dates`
rail showing the stale value until a full page reload. Fix: the save now
also calls `refreshCorpusSummaryFor(expId)`, which now ALSO refreshes
`.corpus-card-dates` (it previously only touched company/title/meta).

#5: `_submitSurgicalRefinement` had a try/finally with NO catch — a
transient failure on `POST /api/validate-refinement` propagated uncaught and
the UI just reset silently (busy banner cleared, button re-enabled, nothing
told the user anything failed). Fix: a catch mirroring the legacy refine
path's error handling (`reportError` + a "NOT EXECUTED" entry in the shared
refinement-history panel), plus the note staying in the input box so
clicking Refine again IS the retry affordance.

Both LLM-free: #4 is pure corpus-CRUD DOM state; #5 drives
`_submitSurgicalRefinement` directly via `page.evaluate` (same technique as
test_20260706_refinement_scope_modal.py) with `/api/validate-refinement`
intercepted to fail at the network layer, so neither needs a generated
résumé or a live LLM.
"""

from __future__ import annotations

import os
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, CorpusPage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Corpus


@pytest.mark.ux
@pytest.mark.slow
def test_editing_experience_dates_refreshes_card_header_rail(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    cid = seed_user(ux_app, "alice")
    exp_id = seed_exp_with_bullets(cid)  # start_date="2021-01", end_date=None

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    corpus = CorpusPage(page, live_server).open().wait_for_cards()
    corpus.expand_card(0)

    # Baseline: the collapsed-header date rail shows the seeded start date.
    dates_locator = page.locator(f"{Corpus.CARD} .corpus-card-dates")
    assert "2021-01" in (dates_locator.text_content() or "")

    # Edit start_date inline (the expanded body's field group) and blur to
    # fire the 'change' listener _saveExperienceField is wired to.
    date_input = page.locator(f"#exp-{exp_id}-start_date")
    date_input.fill("2020-06")
    date_input.press("Tab")

    # The header rail updates WITHOUT a page reload — this is the bug: before
    # the fix, .corpus-card-dates kept showing "2021-01" until a full reload.
    page.wait_for_function(
        "() => (document.querySelector('.corpus-card-dates')?.textContent || '').includes('2020-06')",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    assert "2021-01" not in (dates_locator.text_content() or "")
    assert "2020-06" in (dates_locator.text_content() or "")
    assert "current" in (dates_locator.text_content() or "").lower()


@pytest.mark.ux
@pytest.mark.slow
def test_surgical_refinement_network_failure_surfaces_error_with_retry(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    def _fail(route: Route) -> None:
        route.abort()

    page.route("**/api/validate-refinement", _fail)

    note = "Tighten the summary."
    page.evaluate(
        "(note) => {"
        " window._composeApplicationId = 1;"
        " document.getElementById('refinementInput').value = note;"
        " document.getElementById('btnRefinement').disabled = false;"
        " window.__refineSettled = false;"
        " _submitSurgicalRefinement(note).then(() => { window.__refineSettled = true; });"
        " }",
        note,
    )
    page.wait_for_function("() => window.__refineSettled === true", timeout=DEFAULT_TIMEOUT_MS)

    # Visible error surfacing (reportError -> setStatus('ERROR') + error modal wiring).
    status_text = (page.locator("#statusPill").text_content() or "").lower()
    assert "error" in status_text

    # The refinement-history panel (shared with the legacy refine path) shows
    # a "NOT EXECUTED" entry recording the failed attempt — case-insensitive
    # per the project's CSS-uppercase UX-copy convention. state="attached" (not
    # the default "visible"): this test never navigates into the wizard step
    # that hosts the panel, so an ancestor is display:none — only the class
    # toggle on #refinementHistory itself is under test here, matching
    # test_20260706_refinement_scope_modal.py's identical pattern.
    page.wait_for_selector(
        "#refinementHistory:not(.hidden)", state="attached", timeout=DEFAULT_TIMEOUT_MS
    )
    history_text = (page.text_content("#refinementHistory") or "").lower()
    assert "not executed" in history_text
    assert note.lower() in history_text

    # Retry affordance: the note is still in the box and the button is
    # re-enabled — retrying is just clicking Refine again.
    assert page.locator("#refinementInput").input_value() == note
    assert not page.locator("#btnRefinement").is_disabled()


# ---------------------------------------------------------------------------
# DIAGNOSTIC PROBES (item 31, docs/dev/diagnosis/ux-surgical-refinement-network-
# retry-flake.md `## Falsification`). NOT regression coverage for the refinement
# feature — one-shot capability experiments answering "CAN onUserSelect's stale
# async tail (static/app.js:395-452, `setStatus('READY')` at :448) clobber the
# refinement flow's `setStatus('ERROR')` (static/app.js:2383) before a caller
# reads `#statusPill`." Each OBSERVES and reports; none asserts a hypothesis
# outcome (asserting one direction would conflate "the probe ran" with "the
# theory won") — matches item 30's probe convention
# (test_20260604_bullet_drag_reorder.py:286-296). Disposition (kept, converted
# to a documented negative result, or removed) is decided from the outcome in
# the dossier, not here.
# ---------------------------------------------------------------------------

# Patches window.setStatus to log every call's raw argument + timestamp BEFORE
# _toSentence() reformats it, so 'READY' / 'ERROR' are exact string matches
# against the literal calls in static/app.js. Installed after BasePage.load()
# (setStatus is defined) and before UserPickerPage.select() (which triggers
# onUserSelect's tail) so it captures every write from that point on — nothing
# calls setStatus during page bootstrap itself (confirmed by direct read of the
# DOMContentLoaded handler, static/app.js:42-84), so the log starts empty.
_STATUS_LOG_JS = (
    "() => {"
    " window.__statusLog = [];"
    " const orig = window.setStatus;"
    " window.setStatus = function(text) {"
    "   window.__statusLog.push({ text: text, t: performance.now() });"
    "   return orig.apply(this, arguments);"
    " };"
    "}"
)

_SUBMIT_REFINEMENT_JS = (
    "(note) => {"
    " window._composeApplicationId = 1;"
    " document.getElementById('refinementInput').value = note;"
    " document.getElementById('btnRefinement').disabled = false;"
    " window.__refineSettled = false;"
    " _submitSurgicalRefinement(note).then(() => { window.__refineSettled = true; });"
    " }"
)


def _log_probe_result(tag: str, result: str) -> None:
    print(f"\n[{tag}] {result}")
    log_path = os.environ.get("SURGICAL_REFINEMENT_RACE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{result}\n")


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_baseline_status_race_ordering(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Baseline for item 31 (dossier `## Falsification` Step 1).

    Runs the exact same sequence as
    `test_surgical_refinement_network_failure_surfaces_error_with_retry`, with
    `setStatus` instrumented, WITHOUT forcing anything — reports the natural,
    unforced ordering between `onUserSelect`'s tail `setStatus('READY')`
    (static/app.js:448) and the refinement flow's `setStatus('ERROR')`
    (static/app.js:2383). Measures the ordinary case, not just the adversarial
    one (per this project's own past lesson: a worst-case fixture can be the
    fast path — seed the ordinary profile too). Not a regression assertion;
    run in isolation ~10x externally to characterize timing, per the dossier.
    """
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    page.evaluate(_STATUS_LOG_JS)
    UserPickerPage(page, live_server).select("alice")

    def _fail(route: Route) -> None:
        route.abort()

    page.route("**/api/validate-refinement", _fail)

    note = "Tighten the summary."
    page.evaluate(_SUBMIT_REFINEMENT_JS, note)
    page.wait_for_function("() => window.__refineSettled === true", timeout=DEFAULT_TIMEOUT_MS)

    status_text = (page.locator("#statusPill").text_content() or "").strip().lower()
    log = page.evaluate("() => window.__statusLog")
    _log_probe_result("baseline-probe", f"BASELINE RESULT: status_text={status_text!r} log={log}")


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p1_late_tail_release_vs_status_race(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Falsification P1 for item 31's hypothesis.

    Deterministically forces the race rather than waiting for it to happen by
    chance (same idiom as item 30's P1/P2,
    test_20260604_bullet_drag_reorder.py:299-353): HOLD `onUserSelect`'s FIRST
    tail request (`GET /api/users/*/config` — loadConfig, static/app.js:523-524)
    via `page.route()`, never continuing it. This alone blocks the whole tail —
    `onUserSelect` awaits `loadConfig()` before it ever calls `_landingTab()`
    (static/app.js:415-427: two sequential top-level `await`s, not concurrent;
    an earlier two-route version of this probe tried to hold BOTH `config` and
    `experiences` and found `experiences` never even arms, proving this
    sequential-not-concurrent shape directly rather than by re-reading alone).
    Run the refinement flow to completion (its own `setStatus('ERROR')` lands,
    uncontested, since the tail is still blocked before it ever reaches
    `_landingTab()` or `setStatus('READY')`). THEN release the held `config`
    request — letting the rest of the tail (a real, un-intercepted
    `_landingTab()` round trip) run to completion — and check whether the pill
    still reads `ready` once the tail's write actually lands.

    Pre-registered in the dossier:
    - If `post_release_status` becomes `'ready'` (the exact string recovered
      from the two historical failure artifacts): H is capability-proven — a
      late-arriving tail CAN clobber the error state.
    - If `post_release_status` still contains `'error'`: the last-writer-wins
      mechanism as understood is wrong, or another guard exists. Record the
      full `__statusLog` — it will show why.
    """
    held: list[Route] = []

    def _hold(route: Route) -> None:
        held.append(route)

    page.route("**/api/users/*/config", _hold)

    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    page.evaluate(_STATUS_LOG_JS)
    UserPickerPage(page, live_server).select("alice")

    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "probe did not arm -- the config request was never intercepted"

    def _fail(route: Route) -> None:
        route.abort()

    page.route("**/api/validate-refinement", _fail)

    note = "Tighten the summary."
    page.evaluate(_SUBMIT_REFINEMENT_JS, note)
    page.wait_for_function("() => window.__refineSettled === true", timeout=DEFAULT_TIMEOUT_MS)
    pre_release_status = (page.locator("#statusPill").text_content() or "").strip().lower()

    for route in held:
        route.continue_()
    page.wait_for_function(
        "() => window.__statusLog.some(e => e.text === 'READY')", timeout=DEFAULT_TIMEOUT_MS
    )
    post_release_status = (page.locator("#statusPill").text_content() or "").strip().lower()
    log = page.evaluate("() => window.__statusLog")

    _log_probe_result(
        "p1-probe",
        "P1 RESULT: "
        f"pre_release_status={pre_release_status!r} "
        f"post_release_status={post_release_status!r} log={log}",
    )


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p2_settled_tail_before_refinement_control(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Falsification P2 (reverse control) for item 31's hypothesis.

    The control for P1: let `onUserSelect`'s tail fully settle (wait for its
    `setStatus('READY')` to land) BEFORE firing the refinement note at all —
    strict sequencing, the race suppressed by construction. If the pill
    correctly holds `error` here, that is evidence the race is NECESSARY for
    the symptom, not just that forcing it is SUFFICIENT (P1) — ruling out an
    unrelated confound producing the same string by coincidence.
    """
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    page.evaluate(_STATUS_LOG_JS)
    UserPickerPage(page, live_server).select("alice")

    page.wait_for_function(
        "() => window.__statusLog.some(e => e.text === 'READY')", timeout=DEFAULT_TIMEOUT_MS
    )

    def _fail(route: Route) -> None:
        route.abort()

    page.route("**/api/validate-refinement", _fail)

    note = "Tighten the summary."
    page.evaluate(_SUBMIT_REFINEMENT_JS, note)
    page.wait_for_function("() => window.__refineSettled === true", timeout=DEFAULT_TIMEOUT_MS)

    status_text = (page.locator("#statusPill").text_content() or "").strip().lower()
    log = page.evaluate("() => window.__statusLog")
    _log_probe_result("p2-probe", f"P2 RESULT: status_text={status_text!r} log={log}")

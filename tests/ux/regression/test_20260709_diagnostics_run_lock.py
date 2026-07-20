"""UX regression — diagnostics round-2 #1: global paid-run single-flight lock.

Guards `dashboard/templates/dashboard.html`'s `window.sartorRunLock`: while any
one of the four paid-run buttons (eval / tune / bootstrap / grounding-score) is
in flight, the other three (and re-clicks of the live one) must be disabled and
a prominent `#runLockBanner` must be visible — then, once that run's request
resolves, all four re-enable and the banner hides.

Drives the "Run eval" control end-to-end but never lets a real eval run: a
Playwright route interceptor **holds** the `POST /api/eval/run` request open
(never fulfills it) so the click's fetch stays pending exactly like a real
in-flight SSE stream, giving a stable window to assert the lock is engaged.
Fulfilling the held route with an empty `text/event-stream` body then mirrors
the client's normal `_closed` terminal path (see `run()` in dashboard.html),
proving `releaseRunLock()` fires and un-disables all four buttons.

CW-117 (v1.1.0 debt-burn): the eval-run test above was the ONLY one of the four
hand-wired acquire/release sites with regression coverage. At the time, bootstrap
and grounding-score each had their OWN hand-rolled SSE pump (not
`window.sartorEval.stream`), so a future edit to either could silently drop its
`acquireRunLock()`/`releaseRunLock()` pair without any test noticing. The two
tests below close that gap by driving each of THOSE routes through the exact
same hold-then-release pattern, independently — kept even after
feat/diagnostics-run-cancel folded both hand-rolled pumps into
`window.sartorEval.stream()` (to get Cancel-button wiring for free), since the
per-route acquire/release call sites are still independent and worth covering
on their own.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard

_RUN_LOCK_IDS = ("#evalRunBtn", "#tuneRunBtn", "#bsRun", "#annScore")

_BOOTSTRAP_DOC = {
    "bootstrap_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "prompt_version": "2026-06-06.1",
    "jaccard_threshold": 0.75,
    "jd_count": 1,
    "per_jd": [{"jd_file": "jd1.txt", "run_id": "r1", "clarification_questions": []}],
    "dedup": {
        "bullets": {
            "cluster_count": 1,
            "clusters": [
                {
                    "representative": "Led a $5M migration",
                    "members": ["Led a $5M migration"],
                    "jd_files": ["jd1.txt"],
                    "size": 1,
                }
            ],
        },
        "skills": {"cluster_count": 0, "clusters": []},
    },
    "grounding_signals": None,
}


@pytest.mark.ux
def test_run_lock_blocks_other_buttons_and_releases(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_be_visible()

    # Auto-accept the "Run the ... eval now?" confirm() so the click proceeds
    # into run() (where acquireRunLock() fires) instead of being dismissed.
    page.on("dialog", lambda dialog: dialog.accept())

    # Hold POST /api/eval/run open — never fulfill it here — to simulate an
    # in-flight paid run without ever making a real (or even resolving) call.
    held: list[Route] = []

    def _hold(route: Route) -> None:
        held.append(route)

    page.route("**/api/eval/run", _hold)

    page.locator("#evalRunBtn").click()

    # Wait for the click's fetch to actually reach the interceptor (bounded poll).
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-eval click never issued a POST /api/eval/run"

    # Locked: all four run buttons disabled (not just evalRunBtn's own toggle),
    # and the shared banner is visible.
    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_disabled()
    expect(page.locator("#runLockBanner")).to_be_visible()

    # Resolve the held request the same way a normal successful stream ends —
    # body closes immediately, so the client's reader sees chunk.done → '_closed'.
    held[0].fulfill(status=200, content_type="text/event-stream", body="")

    # Released: all four run buttons re-enabled, banner hidden again.
    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_enabled()
    expect(page.locator("#runLockBanner")).to_be_hidden()


@pytest.mark.ux
def test_bootstrap_run_lock_blocks_other_buttons_and_releases(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """CW-117: runBootstrap() in dashboard.html independently acquires +
    releases the shared lock; this proves that release site specifically
    (now via window.sartorEval.stream() since feat/diagnostics-run-cancel,
    previously its own hand-rolled SSE pump)."""
    from tests.ux.seeding import seed_user

    seed_user(ux_app, "alice")
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()

    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    dash.select_bs_user("alice")
    # addJdRow('', '') fires once unconditionally on load — fill that row.
    page.fill(".bs-jd-name", "jd1")
    page.fill(".bs-jd-text", "Senior PM JD body.")

    held: list[Route] = []
    page.route("**/api/annotation/bootstrap", lambda route: held.append(route))
    page.locator(Dashboard.ANN_BS_RUN).click()

    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-bootstrap click never issued a POST /api/annotation/bootstrap"

    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_disabled()
    expect(page.locator("#runLockBanner")).to_be_visible()

    held[0].fulfill(status=200, content_type="text/event-stream", body="")

    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_enabled()
    expect(page.locator("#runLockBanner")).to_be_hidden()


@pytest.mark.ux
def test_score_grounding_run_lock_blocks_other_buttons_and_releases(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """CW-117: scoreGrounding() in dashboard.html independently acquires +
    releases the shared lock; this proves that release site specifically
    (now via window.sartorEval.stream() since feat/diagnostics-run-cancel,
    previously its own hand-rolled SSE pump)."""
    ann_root = ux_app.app.config["ANNOTATION_ROOT"]
    fixture_dir = ann_root / "alice-bootstrap"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP_DOC), encoding="utf-8")
    (ux_app.app.config["CONFIGS_DIR"] / "alice.config").write_text("{}", encoding="utf-8")

    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()
    dash.select_fixture("alice-bootstrap")
    expect(dash.editor()).to_be_visible()

    held: list[Route] = []
    page.route("**/api/annotation/fixture/*/*/score", lambda route: held.append(route))
    page.locator("#annScore").click()

    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Score-grounding click never issued a POST .../score"

    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_disabled()
    expect(page.locator("#runLockBanner")).to_be_visible()

    held[0].fulfill(status=200, content_type="text/event-stream", body="")

    for sel in _RUN_LOCK_IDS:
        expect(page.locator(sel)).to_be_enabled()
    expect(page.locator("#runLockBanner")).to_be_hidden()

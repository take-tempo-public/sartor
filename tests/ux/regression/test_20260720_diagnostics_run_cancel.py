"""UX regression — feat/diagnostics-run-cancel: the frontend Cancel button.

Guards `dashboard/templates/dashboard.html`'s Cancel-button wiring
(`window.sartorEval.wireCancel`/`hideCancel`, threaded through `stream()`'s
`AbortController`): while a paid/CPU-bound diagnostics run is in flight, its
Cancel button is visible; clicking it aborts the underlying `fetch`, shows the
"Cancelling…" text synchronously (no server confirmation can reach the client
once the connection drops — see
`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`'s RUN-LIFECYCLE
note), hides the Cancel button, re-enables the Run button, and releases the
shared `sartorRunLock` banner.

UX-6 (Epic C C1b): the progress line used to stay on "Cancelling…" forever —
the `_aborted` branch never set a terminal message. It now reaches a real
terminal state ("Cancelled — no further paid calls were started.") once the
abort actually lands (asserted below after "Cancelling…"'s transient text),
and stops pulsing (the Run button's `.btn-pending` class is cleared with the
rest of its pending state).

Two call sites are covered, not all four, since all four now ride the SAME
`window.sartorEval.stream()` `AbortController` wiring (post-dedup, see
`test_20260709_diagnostics_run_lock.py`'s updated docstring): the Quality tab
(`run()`, a thin wrapper over `stream()`) and the Bootstrap tab (`stream()`
called directly — the higher-risk path, since it was hand-rolled before this
branch and is the newest call site of the shared helper).

Server-side proof that a real disconnect actually stops the next paid/CPU
call lives in `tests/test_annotation_routes.py::TestRunCancelDisconnect` (one
test per route, via a simulated `GeneratorExit`) — this file only proves the
browser-side button wiring.
"""

from __future__ import annotations

import re
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard


@pytest.mark.ux
def test_eval_cancel_button_aborts_run_and_resets_ui(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_be_visible()

    page.on("dialog", lambda dialog: dialog.accept())

    held: list[Route] = []
    page.route("**/api/eval/run", lambda route: held.append(route))
    page.locator("#evalRunBtn").click()

    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-eval click never issued a POST /api/eval/run"

    cancel_btn = page.locator("#evalCancelBtn")
    expect(cancel_btn).to_be_visible()
    run_btn = page.locator("#evalRunBtn")
    expect(run_btn).to_be_disabled()
    expect(run_btn).to_have_class(re.compile(r"\bbtn-pending\b"))
    expect(page.locator("#runLockBanner")).to_be_visible()

    cancel_btn.click()

    expect(cancel_btn).to_be_hidden()
    # UX-6: reaches a terminal state, not stuck on "Cancelling…" forever.
    expect(page.locator("#evalProgress")).to_have_text(
        "Cancelled — no further paid calls were started."
    )
    expect(run_btn).to_be_enabled()
    expect(run_btn).not_to_have_class(re.compile(r"\bbtn-pending\b"))
    expect(page.locator("#runLockBanner")).to_be_hidden()


@pytest.mark.ux
def test_bootstrap_cancel_button_aborts_run_and_resets_ui(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """The Bootstrap tab's Cancel button, wired through the SAME
    window.sartorEval.stream() call runBootstrap() adopted this branch
    (previously its own hand-rolled fetch+getReader pump with no Cancel path
    at all)."""
    from tests.ux.seeding import seed_user

    seed_user(ux_app, "alice")
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()

    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    dash.select_bs_user("alice")
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

    cancel_btn = page.locator("#bsCancelBtn")
    expect(cancel_btn).to_be_visible()
    bs_run = page.locator(Dashboard.ANN_BS_RUN)
    expect(bs_run).to_be_disabled()
    expect(page.locator("#runLockBanner")).to_be_visible()

    cancel_btn.click()

    expect(cancel_btn).to_be_hidden()
    # UX-6: reaches a terminal state, not stuck on "Cancelling…" forever.
    expect(page.locator("#bsProgress")).to_have_text(
        "Cancelled — no further paid calls were started."
    )
    expect(bs_run).to_be_enabled()
    expect(page.locator("#runLockBanner")).to_be_hidden()

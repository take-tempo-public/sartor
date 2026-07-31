"""Regression: Compose bullet reordering persists, and Reset reverts it.

Closes the coverage gap left by feat/bullet-drag-reorder (2026-06-04): the
POST contract was unit-tested but the live browser interaction had no test.

`bullet_order` round-trips through the real autosave POST `/composition` and
the GET re-read on a compose re-load — the in-process server makes this a
genuine server round-trip (the reason the flow stub fakes the LLM, not the
backend). Two paths share the same persistence: keyboard (the a11y floor,
must-pass) and the pointer drag.

Note: the app's full-page resume targets Step 6, so "persists across reload"
is verified by re-loading the Compose step (navigate away + back), which
re-fetches GET `/composition` and re-reads the saved order.
"""

from __future__ import annotations

import os
import time
from types import ModuleType

import pytest
from playwright.sync_api import Page, Request, Response

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Compose, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
_K8S = "Reduced Kubernetes"
_SYNCS = "Attended weekly syncs"


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


# ---------------------------------------------------------------------------
# INSTRUMENT (charter C-7, fix/ux-keyboard-reorder-timeout). Item 30's one
# historical failure -- a Playwright 30s timeout inside
# WizardComposePage._wait_settled() -- was never captured: no traceback, no
# log line, anywhere (docs/dev/diagnosis/ux-keyboard-reorder-timeout.md, O-1).
# This test hits _wait_settled() 12 times (same dossier, O-3), and there are
# THREE candidate mechanisms for a hang (dossier ## Inferred, H1/H2/H3), not
# one -- so this instrument is scoped WIDE, per C-7 ("never scope the
# instrument to the theory you are testing"): it times all three of
# _wait_settled's sub-waits separately on every reach, tracks every network
# request/response/failure for the WHOLE test (not just around one wait, so a
# request opened earlier but still pending at a later hang still shows up),
# and dumps everything on whichever wait actually raises.
# ---------------------------------------------------------------------------

# Compose cascade + iframe state at the moment of a settle failure -- the
# once-per-application latch globals (H2) and the live-preview iframe's
# document readyState (H1), read in one round-trip alongside the settle-
# marker attributes _wait_settled itself waits on.
_READ_CASCADE_STATE_JS = r"""
() => {
  const list = document.getElementById('composeList');
  const frame = document.getElementById('livePreviewFrame');
  let previewReadyState = null;
  try {
    previewReadyState = frame && frame.contentDocument ? frame.contentDocument.readyState : null;
  } catch (e) {
    previewReadyState = 'inaccessible: ' + e.message;
  }
  return {
    composeReady: !!(list && list.hasAttribute('data-compose-ready')),
    bgPending: list ? list.getAttribute('data-compose-bg-pending') : null,
    draftSummaryFiredForApp:
      (typeof _draftSummaryFiredForApp !== 'undefined') ? _draftSummaryFiredForApp : 'undeclared',
    gapFillFiredForApp:
      (typeof _gapFillFiredForApp !== 'undefined') ? _gapFillFiredForApp : 'undeclared',
    composeApplicationId:
      (typeof _composeApplicationId !== 'undefined') ? _composeApplicationId : 'undeclared',
    previewFrameReadyState: previewReadyState,
  };
}
"""


class _NetworkCensus:
    """Live in-flight request tracker for the whole test (installed once, not
    per `_wait_settled` call -- a request that started during an EARLIER
    phase but is still open when a LATER settle hangs must still show up).
    Every Playwright request ends in exactly one of `response`/`requestfailed`
    (or never, if the page tears down mid-flight -- exactly what a
    `networkidle` hang would look like), so those two plus `request` are the
    complete event set.
    """

    def __init__(self, page: Page) -> None:
        self.hit_counts: dict[str, int] = {}
        self._pending: dict[int, tuple[str, float]] = {}
        self.finished: list[dict[str, object]] = []
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_requestfailed)

    def _on_request(self, request: Request) -> None:
        self.hit_counts[request.url] = self.hit_counts.get(request.url, 0) + 1
        self._pending[id(request)] = (request.url, time.monotonic())

    def _on_response(self, response: Response) -> None:
        self._finish(response.request, "response", response.status)

    def _on_requestfailed(self, request: Request) -> None:
        self._finish(request, "requestfailed", request.failure)

    def _finish(self, request: Request, kind: str, detail: object) -> None:
        entry = self._pending.pop(id(request), None)
        elapsed = round(time.monotonic() - entry[1], 3) if entry else None
        self.finished.append(
            {"url": request.url, "kind": kind, "detail": detail, "elapsed_s": elapsed}
        )

    def still_pending(self) -> list[dict[str, object]]:
        """Requests with no response/failure yet, and how long each has been open."""
        now = time.monotonic()
        return [
            {"url": url, "open_s": round(now - started, 3)}
            for url, started in self._pending.values()
        ]


def _install_settle_instrument(
    monkeypatch: pytest.MonkeyPatch, census: _NetworkCensus
) -> list[dict[str, object]]:
    """Replace `WizardComposePage._wait_settled` with a timed, dump-on-any-
    exception version for the duration of ONE test (monkeypatch auto-reverts
    at teardown). Returns the list this appends one record to per reach --
    inspectable regardless of pass or fail, so a baseline campaign can read
    ordinary-case timing, not just failures.
    """
    reaches: list[dict[str, object]] = []
    log_path = os.environ.get("KEYBOARD_REORDER_SETTLE_LOG")

    def _dump(record: dict[str, object]) -> None:
        print(f"\n[settle-instrument] {record}")
        if log_path:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(f"{record}\n")

    def _instrumented_wait_settled(self: WizardComposePage) -> None:
        record: dict[str, object] = {"reach": len(reaches) + 1}
        t_start = time.monotonic()
        try:
            self.page.wait_for_selector(
                Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS
            )
            record["panel_visible_s"] = round(time.monotonic() - t_start, 3)
            t_ni = time.monotonic()
            self.page.wait_for_load_state("networkidle")
            record["networkidle_s"] = round(time.monotonic() - t_ni, 3)
            t_settled = time.monotonic()
            self.page.wait_for_selector(
                Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS
            )
            record["settled_s"] = round(time.monotonic() - t_settled, 3)
        except Exception as exc:
            record["exception"] = repr(exc)
            record["elapsed_total_s"] = round(time.monotonic() - t_start, 3)
            try:
                record["cascade_state"] = self.page.evaluate(_READ_CASCADE_STATE_JS)
            except Exception as eval_exc:  # page gone mid-failure -- dump must never raise
                record["cascade_state"] = f"COULD NOT EVALUATE: {eval_exc!r}"
            record["still_pending_requests"] = census.still_pending()
            record["hit_counts"] = dict(census.hit_counts)
            reaches.append(record)
            _dump(record)
            raise
        reaches.append(record)

    monkeypatch.setattr(WizardComposePage, "_wait_settled", _instrumented_wait_settled)
    return reaches


def _dump_reaches_summary(reaches: list[dict[str, object]], census: _NetworkCensus) -> None:
    """Unconditional end-of-test dump -- ordinary-case timing across every
    `_wait_settled` reach, plus a liveness check on the census (a silently-
    dead instrument must never read the same as "nothing happened", per this
    repo's existing `_dump_scroll_spy` discipline,
    tests/ux/regression/test_20260708_busy_states_and_chip.py:351-401).
    """
    print(f"\n[settle-instrument] {len(reaches)} _wait_settled reach(es) this test:")
    for r in reaches:
        print(f"  {r}")
    if not census.hit_counts:
        print(
            "\n[settle-instrument] WARNING: zero requests observed by the network "
            "census across the whole test -- the page.on() listeners may not have "
            "installed. Do not trust an empty still_pending_requests as 'no traffic'."
        )
    if os.environ.get("SETTLE_INSTRUMENT_ALWAYS"):
        print(f"[settle-instrument] hit_counts={census.hit_counts}")
    log_path = os.environ.get("KEYBOARD_REORDER_SETTLE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"SUMMARY reaches={reaches} hit_counts={census.hit_counts}\n")


def _reach_compose(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_keyboard_reorder_persists_and_reset_reverts(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Item 30 instrument (docs/dev/diagnosis/ux-keyboard-reorder-timeout.md) --
    # installed FIRST, before any navigation, so the network census sees every
    # request from the very first page load onward.
    census = _NetworkCensus(page)
    reaches = _install_settle_instrument(monkeypatch, census)
    try:
        compose = _reach_compose(page, live_server, ux_app, monkeypatch)

        # Default AI ranking: the JD-relevant Kubernetes bullet is first.
        assert compose.bullet_texts()[0].startswith(_K8S)
        assert not compose.has_custom_order()

        # Move it down → [syncs, k8s]; the debounced autosave POSTs the order.
        with page.expect_response(_is_composition_post):
            compose.move_down(_K8S)
        assert compose.bullet_texts()[0].startswith("Attended")
        assert compose.has_custom_order()

        # Re-load Compose (away + back) → GET re-reads the saved order.
        WizardTemplatePage(page, live_server).open()
        compose.reload()
        assert compose.bullet_texts()[0].startswith("Attended"), "order did not persist"
        assert compose.has_custom_order()

        # Reset → revert to AI (score) ranking; order cleared.
        with page.expect_response(_is_composition_post):
            compose.reset_order()
        assert compose.bullet_texts()[0].startswith(_K8S)
        assert not compose.has_custom_order()
    finally:
        # Unconditional -- runs on pass, on an assertion failure, and on a
        # _wait_settled timeout alike, so a baseline campaign can read
        # ordinary-case timing even from runs that never fail.
        _dump_reaches_summary(reaches, census)


@pytest.mark.ux
@pytest.mark.slow
def test_pointer_drag_reorders(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    assert compose.bullet_texts()[0].startswith(_K8S)

    # Drag the Kubernetes bullet below "weekly syncs"; the drop autosaves.
    with page.expect_response(_is_composition_post):
        compose.drag_below(_K8S, _SYNCS)
    assert compose.bullet_texts()[0].startswith("Attended"), "drag did not reorder"
    assert compose.has_custom_order()

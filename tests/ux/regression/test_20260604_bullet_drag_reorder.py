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
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType

import pytest
from playwright.sync_api import Frame, Page, Request, Response, Route
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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


@dataclass
class _RequestRecord:
    """One request's lifecycle as the census saw it. `request` is held so the
    `id()` key can never be reused by a different request mid-test."""

    request: Request
    url: str
    resource_type: str
    frame_url: str | None
    t_request: float
    t_response: float | None = None  # `response`: status + HEADERS received
    t_finished: float | None = None  # `requestfinished`: BODY downloaded
    failure: str | None = None  # `requestfailed`


class _NetworkCensus:
    """Live in-flight request tracker for the whole test (installed once, not
    per `_wait_settled` call -- a request that started during an EARLIER
    phase but is still open when a LATER settle hangs must still show up).

    Item 30 widening (fix/reorder-networkidle-empty-census): the original
    census treated `response` (headers received) as "done", and never listened
    to `requestfinished` (body downloaded), so a request with its headers in
    and its body still streaming read as "nothing pending" while Playwright's
    `networkidle` was still withheld. The CI samples to date all show
    `still_pending_requests: []` at the timeout (item 30, 2026-10-12 and
    2026-10-14 entries). `still_pending()` keeps its original meaning, so old
    and new records stay comparable; `awaiting_body()` is the new split. The
    frame timeline is the other thing the old census could not see: a child
    frame that attaches or re-commits holds its own lifecycle, with no request
    open at all.
    """

    def __init__(self, page: Page) -> None:
        self.hit_counts: dict[str, int] = {}
        self._t0 = time.monotonic()
        self._records: dict[int, _RequestRecord] = {}
        self.frame_timeline: list[dict[str, object]] = []
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfinished", self._on_requestfinished)
        page.on("requestfailed", self._on_requestfailed)
        page.on("frameattached", lambda f: self._on_frame("attached", f))
        page.on("framenavigated", lambda f: self._on_frame("navigated", f))
        page.on("framedetached", lambda f: self._on_frame("detached", f))

    def _rel(self, t: float | None) -> float | None:
        return None if t is None else round(t - self._t0, 3)

    def _on_request(self, request: Request) -> None:
        self.hit_counts[request.url] = self.hit_counts.get(request.url, 0) + 1
        try:
            frame_url: str | None = request.frame.url
        except Exception:  # service-worker / frameless requests have no frame
            frame_url = None
        self._records[id(request)] = _RequestRecord(
            request=request,
            url=request.url,
            resource_type=request.resource_type,
            frame_url=frame_url,
            t_request=time.monotonic(),
        )

    def _on_response(self, response: Response) -> None:
        rec = self._records.get(id(response.request))
        if rec is not None:
            rec.t_response = time.monotonic()

    def _on_requestfinished(self, request: Request) -> None:
        rec = self._records.get(id(request))
        if rec is not None:
            rec.t_finished = time.monotonic()

    def _on_requestfailed(self, request: Request) -> None:
        rec = self._records.get(id(request))
        if rec is not None:
            rec.failure = str(request.failure)

    def _on_frame(self, event: str, frame: Frame) -> None:
        try:
            parent = frame.parent_frame
            parent_url = parent.url if parent is not None else None
            entry: dict[str, object] = {
                "t_s": self._rel(time.monotonic()),
                "event": event,
                "url": frame.url,
                "name": frame.name,
                "parent_url": parent_url,
            }
        except Exception as exc:  # a frame can die between the event and this read
            entry = {"t_s": self._rel(time.monotonic()), "event": event, "error": repr(exc)}
        self.frame_timeline.append(entry)

    def _open(self, rec: _RequestRecord) -> bool:
        return rec.t_finished is None and rec.failure is None

    def still_pending(self) -> list[dict[str, object]]:
        """Requests with no response and no failure yet -- the ORIGINAL meaning
        of this field, kept so records from before the widening stay comparable.
        """
        now = time.monotonic()
        return [
            {"url": r.url, "open_s": round(now - r.t_request, 3)}
            for r in self._records.values()
            if r.t_response is None and r.failure is None
        ]

    def awaiting_body(self) -> list[dict[str, object]]:
        """Requests whose headers arrived and whose body has NOT finished. The
        original census counted these as done.
        """
        now = time.monotonic()
        return [
            {
                "url": r.url,
                "resource_type": r.resource_type,
                "frame_url": r.frame_url,
                "t_request_s": self._rel(r.t_request),
                "t_response_s": self._rel(r.t_response),
                "body_open_s": round(now - (r.t_response or now), 3),
            }
            for r in self._records.values()
            if r.t_response is not None and self._open(r)
        ]

    def slowest_finished(self, n: int = 3) -> list[dict[str, object]]:
        """The `n` requests with the longest request->body-finished time. A
        finite stall (the null hypothesis) shows here with `t_finished`.
        """
        done = [r for r in self._records.values() if r.t_finished is not None]
        done.sort(key=lambda r: (r.t_finished or 0.0) - r.t_request, reverse=True)
        return [
            {
                "url": r.url,
                "resource_type": r.resource_type,
                "total_s": round((r.t_finished or 0.0) - r.t_request, 3),
                "headers_s": None if r.t_response is None else round(r.t_response - r.t_request, 3),
            }
            for r in done[:n]
        ]

    def failed(self) -> list[dict[str, object]]:
        return [{"url": r.url, "failure": r.failure} for r in self._records.values() if r.failure]


def _frame_state(page: Page) -> list[dict[str, object]]:
    """Per-frame state at a settle failure: which frame, if any, is the one
    withholding `networkidle`. Called only after a failure, so its short
    per-frame waits cost nothing on the passing path. Must never raise.
    """
    out: list[dict[str, object]] = []
    try:
        frames = list(page.frames)
    except Exception as exc:
        return [{"error": f"page.frames failed: {exc!r}"}]
    for frame in frames:
        item: dict[str, object] = {}
        try:
            parent = frame.parent_frame
            item["url"] = frame.url
            item["name"] = frame.name
            item["parent_url"] = parent.url if parent is not None else None
            item["detached"] = frame.is_detached()
        except Exception as exc:
            item["error"] = repr(exc)
        try:
            frame.wait_for_load_state("networkidle", timeout=250)
            item["networkidle"] = "reached"
        except PlaywrightTimeoutError:
            item["networkidle"] = "NOT_REACHED"
        except Exception as exc:
            item["networkidle"] = f"error: {exc!r}"
        try:
            item["readyState"] = frame.evaluate("document.readyState")
        except Exception as exc:
            item["readyState"] = f"inaccessible: {exc!r}"
        out.append(item)
    return out


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
            # Request-side first (cheap, and taken before the per-frame waits
            # below can shift timings), then the frame-side localization.
            record["still_pending_requests"] = census.still_pending()
            record["awaiting_body"] = census.awaiting_body()
            record["failed_requests"] = census.failed()
            record["slowest_finished"] = census.slowest_finished()
            record["frame_timeline"] = list(census.frame_timeline)
            record["frames"] = _frame_state(self.page)
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
    # Item 30 widening: the frame timeline and the slowest request bodies are
    # printed on EVERY run, pass or fail -- the failing attempt's output is the
    # only artifact a rerun-then-pass leaves, and an ordinary-run baseline is
    # what a failing one is read against.
    print(f"[settle-instrument] awaiting_body at end of test: {census.awaiting_body()}")
    print(f"[settle-instrument] slowest_finished: {census.slowest_finished(5)}")
    print(f"[settle-instrument] frame_timeline ({len(census.frame_timeline)} events):")
    for entry in census.frame_timeline:
        print(f"  {entry}")
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


# ---------------------------------------------------------------------------
# DIAGNOSTIC PROBES (item 30, docs/dev/diagnosis/ux-keyboard-reorder-timeout.md
# `## Falsification`). These are NOT regression coverage for the reorder
# feature -- they are one-shot capability experiments answering "CAN this
# mechanism alone produce a 30s networkidle hang," pre-registered before
# running. Each OBSERVES and reports; neither asserts a specific hypothesis
# outcome, since that is exactly what is unknown going in (asserting one
# direction would conflate "the probe ran" with "the theory won"). Disposition
# (kept as permanent regression coverage, converted to a documented negative
# result, or removed) is decided from the outcome in the dossier, not here.
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p1_stalled_live_preview_iframe_vs_compose_reload_networkidle(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falsification P1 for item 30 hypothesis H1.

    Baseline (dossier O-12/O-13) already shows the reach immediately after
    `WizardTemplatePage.open()` -- which fires an unawaited live-preview
    iframe navigation loading a 921KB `paged.polyfill.js` -- consistently
    taking ~15-20x every sibling reach's `networkidle` wait (~0.57s vs
    ~0.02-0.04s), on every one of 7 ordinary runs. This probe asks whether
    that SAME mechanism, made artificially slow via `page.route()` (never
    resolving the polyfill request -- deterministic, unlike relying on real
    load time), can push it all the way to Playwright's 30s default timeout.

    Pre-registered in the dossier:
    - Raises `TimeoutError` on `networkidle`: H1 is capability-proven -- the
      fix target is a harness/POM sequencing gap (`WizardTemplatePage.open()`
      not awaiting the iframe it triggers), not a product defect.
    - Returns normally: either `networkidle` does not count this iframe's
      sub-resources the way expected, or panel-switching aborts the
      navigation. The dossier records which, from `elapsed`.
    """
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    assert compose.bullet_texts()[0].startswith(_K8S)

    held: list[Route] = []
    page.route("**/static/vendor/paged.polyfill.js", lambda route: held.append(route))

    WizardTemplatePage(page, live_server).open()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "probe did not arm -- the polyfill request was never intercepted"

    t0 = time.monotonic()
    timed_out = False
    try:
        compose.reload()
    except PlaywrightTimeoutError:
        timed_out = True
    elapsed = round(time.monotonic() - t0, 1)

    result = f"P1 RESULT: timed_out={timed_out} elapsed_s={elapsed}"
    print(f"\n[p1-probe] {result}")
    log_path = os.environ.get("KEYBOARD_REORDER_SETTLE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{result}\n")


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p2_forced_draft_summary_400_vs_compose_cascade(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falsification P2 for item 30 hypothesis H2.

    Direct code read (dossier O-5/O-6/O-7) found `loadComposition`'s cascade
    recurses ONLY on a background fire's success -- a draft-summary failure
    releases a latch but does not itself call `loadComposition` again, and
    the one historically-cited failure trigger (a torn context-file read) is
    already fixed and regression-tested. This probe forces `draft-summary` to
    400 on every attempt (overriding the stub, which otherwise always
    succeeds) and asks whether the resulting page load ever comes close to a
    network hang, or settles quickly with an empty draft as the code read
    predicts.

    Pre-registered in the dossier:
    - `GET /composition` hit count grows unboundedly, or total elapsed
      approaches 30s: H2 is capability-proven after all -- re-open with real
      numbers, discard the "dead" framing below.
    - Settles quickly with a small, bounded hit count (expected): H2 stays
      dead as stated in `## Inferred`.
    """
    composition_gets = {"count": 0}

    def _force_400(route: Route) -> None:
        route.fulfill(status=400, content_type="application/json", body='{"error": "forced by P2"}')

    def _count_composition_gets(route: Route) -> None:
        if route.request.method == "GET":
            composition_gets["count"] += 1
        route.continue_()

    page.route("**/draft-summary", _force_400)
    page.route("**/composition*", _count_composition_gets)

    t0 = time.monotonic()
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    bullets = compose.bullet_texts()
    elapsed = round(time.monotonic() - t0, 1)

    assert bullets, "compose never rendered any bullets -- probe broke setup unexpectedly"

    result = f"P2 RESULT: elapsed_s={elapsed} composition_get_count={composition_gets['count']}"
    print(f"\n[p2-probe] {result}")
    log_path = os.environ.get("KEYBOARD_REORDER_SETTLE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{result}\n")


# ---------------------------------------------------------------------------
# DIAGNOSTIC PROBES P3/P4 (item 30, docs/dev/diagnosis/reorder-networkidle-empty-census.md
# `## Falsification`). Same status as P1/P2: capability experiments, pre-registered
# in the dossier BEFORE they ran, observe-and-report. The only assertions are on
# CONTROLS (the page was idle before arming; the widened census listed the held
# request) -- a void probe must fail loudly, a surprising outcome must not.
# Result lines go to the same KEYBOARD_REORDER_SETTLE_LOG as P1/P2.
# ---------------------------------------------------------------------------

_PROBE_NETWORKIDLE_MS = 8_000

_APPEND_HIDDEN_IFRAME_JS = """
(id) => {
  const f = document.createElement('iframe');
  f.id = id;
  f.name = id;
  f.style.display = 'none';
  document.body.appendChild(f);
}
"""

# Mirrors _refreshLivePreview's URL (static/app.js) but navigates the preview
# iframe directly, once or twice back to back, so the aborted-navigation shape
# can be tried without the app's own probe fetch in between.
_NAVIGATE_PREVIEW_FRAME_JS = """
(mode) => {
  const frame = document.getElementById('livePreviewFrame');
  const appId = (typeof _composeApplicationId !== 'undefined') ? _composeApplicationId : null;
  const url = (n) => {
    const p = new URLSearchParams({ template_id: '1', p4: String(n) });
    if (typeof lastContextPath === 'string' && lastContextPath) p.set('context_path', lastContextPath);
    return `/api/applications/${appId}/preview?${p.toString()}`;
  };
  frame.contentWindow.location.replace(url(1));
  if (mode === 'double') frame.contentWindow.location.replace(url(2));
}
"""


def _probe_networkidle(page: Page) -> tuple[bool, float]:
    """Wait for `networkidle` with a bound; return (timed_out, elapsed_s)."""
    t0 = time.monotonic()
    try:
        page.wait_for_load_state("networkidle", timeout=_PROBE_NETWORKIDLE_MS)
        timed_out = False
    except PlaywrightTimeoutError:
        timed_out = True
    return timed_out, round(time.monotonic() - t0, 3)


def _await_frame_event(
    page: Page,
    census: _NetworkCensus,
    predicate: Callable[[dict[str, object]], bool],
    timeout_s: float = 10.0,
) -> bool:
    """Poll the census's frame timeline until an event matches. A probe arm must
    not start its `networkidle` wait until the frame commit it is about has been
    SEEN: before the commit the main frame still holds its already-fired
    `networkidle` (dossier O-12), so an early wait returns instantly and the arm
    would read "returned normally" for a reason that has nothing to do with the
    mechanism under test.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if any(predicate(e) for e in census.frame_timeline):
            return True
        page.wait_for_timeout(50)
    return False


def _navigated_named(name: str) -> Callable[[dict[str, object]], bool]:
    """Frame-timeline predicate: a `framenavigated` for the frame called `name`."""

    def _match(event: dict[str, object]) -> bool:
        return event.get("event") == "navigated" and event.get("name") == name

    return _match


def _record_probe(tag: str, result: str) -> None:
    print(f"\n[{tag}] {result}")
    log_path = os.environ.get("KEYBOARD_REORDER_SETTLE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{result}\n")


class _HeldBodyServer:
    """One-shot loopback HTTP server: answers with headers and ONE chunk of a
    chunked body, then holds the body open until `release()`. The client sees
    `response` (headers) promptly and `requestfinished` (body) only on release.
    CORS-open so a page on the live_server origin can fetch it.
    """

    def __init__(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(4)
        self.url = f"http://127.0.0.1:{self._sock.getsockname()[1]}/held-body"
        self.headers_sent = threading.Event()
        self._release = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        conn: socket.socket | None = None
        try:
            conn, _ = self._sock.accept()
            conn.settimeout(10)
            buf = b""
            while b"\r\n\r\n" not in buf:
                data = conn.recv(4096)
                if not data:
                    return
                buf += data
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
                b"Access-Control-Allow-Origin: *\r\nCache-Control: no-store\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n"
            )
            self.headers_sent.set()
            self._release.wait(timeout=60)
            conn.sendall(b"0\r\n\r\n")
        except OSError:
            pass
        finally:
            if conn is not None:
                conn.close()

    def release(self) -> None:
        self._release.set()

    def close(self) -> None:
        self._release.set()
        self._sock.close()
        self._thread.join(timeout=2)


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p3_held_body_is_invisible_to_the_old_census(
    page: Page,
    live_server: str,
) -> None:
    """Falsification P3 for item 30 hypothesis I-1, isolated (one page, no app).

    The first draft of P3 ran three arms in sequence on the Compose page and was
    contaminated: arm A left the page in the stuck state P5 isolates, so arms B
    and C said nothing about a held body (dossier O-13, F-3). This version is
    only the question I-1 asks: with headers received and the body held, is
    `networkidle` withheld while the ORIGINAL census (`still_pending`) is empty
    and the widened one (`awaiting_body`) lists it? Then release and recover.
    """
    census = _NetworkCensus(page)
    page.goto(f"{live_server}/static/style.css")
    page.wait_for_load_state("networkidle", timeout=10_000)  # control: idle first
    assert census.still_pending() == [] and census.awaiting_body() == [], "probe void: not at rest"

    server = _HeldBodyServer()
    out: dict[str, object] = {}
    try:
        page.evaluate("url => { window.__p3 = fetch(url).then(r => r.text()); }", server.url)
        assert server.headers_sent.wait(10), "probe void: held server never saw the request"
        for _ in range(100):
            if census.awaiting_body():
                break
            page.wait_for_timeout(50)
        assert census.awaiting_body(), "probe void: widened census did not list the held body"
        # No lifecycle event has recalculated networkidle since the request
        # started, so an already-fired `networkidle` is retained (dossier O-12).
        out["held"] = _probe_networkidle(page)
        out["held_still_pending_old"] = census.still_pending()
        out["held_awaiting_body"] = len(census.awaiting_body())
        # Now a frame commit forces the recalculation (isolated arm C).
        page.evaluate(_APPEND_HIDDEN_IFRAME_JS, "p3c")
        assert _await_frame_event(page, census, _navigated_named("p3c")), (
            "probe void: the iframe commit was never observed"
        )
        out["held_then_commit"] = _probe_networkidle(page)
        out["held_then_commit_still_pending_old"] = census.still_pending()
        out["held_then_commit_awaiting_body"] = len(census.awaiting_body())
        server.release()
        out["after_release"] = _probe_networkidle(page)
    finally:
        server.close()

    _record_probe("p3-probe", f"P3 RESULT: {out}")


_FETCH_SAME_ORIGIN_JS = "async (n) => { const r = await fetch('/static/style.css?p5=' + n, {cache: 'no-store'}); await r.text(); }"


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.parametrize(
    "steps",
    [
        pytest.param(("commit",), id="commit_only"),
        pytest.param(("fetch", "commit"), id="fetch_then_commit"),
        pytest.param(("commit", "fetch"), id="commit_then_fetch"),
        pytest.param(("fetch", "commit", "fetch"), id="fetch_commit_fetch"),
    ],
)
def test_diagnostic_p5_networkidle_order_dependence(
    page: Page,
    live_server: str,
    steps: tuple[str, ...],
) -> None:
    """Falsification P5 for item 30 hypothesis I-8: is the main frame's
    `networkidle` order-dependent on (main-frame request finishes) vs
    (child-frame commit)? Each arm gets a FRESH page via the parametrization, so
    arms cannot contaminate each other (the defect of P3's first draft). No app
    JS runs: the page is `/static/style.css`.

    Pre-registered in the dossier (P5): `fetch_then_commit` is the arm predicted
    to hang; the other three are predicted to return in about 0.5-1 s. The only
    assertions are on controls (idle first; every action seen to complete).
    """
    census = _NetworkCensus(page)
    page.goto(f"{live_server}/static/style.css")
    page.wait_for_load_state("networkidle", timeout=10_000)  # control: idle first

    done: list[str] = []
    for i, step in enumerate(steps):
        if step == "fetch":
            page.evaluate(_FETCH_SAME_ORIGIN_JS, i)
            for _ in range(100):  # `requestfinished` trails the fetch's own resolution
                if not census.still_pending() and not census.awaiting_body():
                    break
                page.wait_for_timeout(50)
            assert not census.awaiting_body(), "probe void: the fetch never finished"
        else:
            name = f"p5c{i}"
            page.evaluate(_APPEND_HIDDEN_IFRAME_JS, name)
            assert _await_frame_event(page, census, _navigated_named(name)), (
                "probe void: the iframe commit was never observed"
            )
        done.append(step)

    timed_out, elapsed = _probe_networkidle(page)
    frames = _frame_state(page) if timed_out else None
    _record_probe(
        "p5-probe",
        f"P5 RESULT: steps={'+'.join(done)} timed_out={timed_out} elapsed_s={elapsed} "
        f"still_pending_old={census.still_pending()} awaiting_body={census.awaiting_body()} "
        f"frames={frames}",
    )


@pytest.mark.ux
@pytest.mark.slow
def test_diagnostic_p4_single_vs_double_preview_navigation_vs_networkidle(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falsification P4 for item 30 hypothesis I-3: does an aborted (superseded)
    preview-iframe navigation leave `networkidle` unreachable?

    The single `location.replace` is the control (the app's ordinary shape, reach 7
    in the instrument). The double is two back-to-back replaces, the first
    superseded before it commits.
    """
    census = _NetworkCensus(page)
    _reach_compose(page, live_server, ux_app, monkeypatch)
    page.wait_for_load_state("networkidle", timeout=10_000)
    out: dict[str, object] = {}

    def _committed(n: int) -> Callable[[dict[str, object]], bool]:
        return lambda e: (
            e.get("event") == "navigated"
            and e.get("name") == "livePreviewFrame"
            and f"p4={n}" in str(e.get("url"))
        )

    page.evaluate(_NAVIGATE_PREVIEW_FRAME_JS, "single")
    assert _await_frame_event(page, census, _committed(1)), "probe void: single nav never committed"
    out["single"] = _probe_networkidle(page)
    out["single_awaiting_body"] = census.awaiting_body()

    page.evaluate(_NAVIGATE_PREVIEW_FRAME_JS, "double")
    # The first replace is superseded; only the second is required to commit.
    assert _await_frame_event(page, census, _committed(2)), "probe void: double nav never committed"
    out["double_committed_p4"] = [
        str(e.get("url"))[-40:]
        for e in census.frame_timeline
        if e.get("event") == "navigated" and "p4=" in str(e.get("url"))
    ]
    out["double"] = _probe_networkidle(page)
    out["double_still_pending_old"] = census.still_pending()
    out["double_awaiting_body"] = census.awaiting_body()
    out["double_failed"] = census.failed()
    out["double_frames"] = _frame_state(page)

    _record_probe("p4-probe", f"P4 RESULT: {out}")

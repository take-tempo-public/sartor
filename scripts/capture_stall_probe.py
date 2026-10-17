"""Instrument the screenshot capture's Template -> Generate step (item 140, part a).

`scripts/capture_screenshots.py` stopped at `WizardTemplatePage.continue_to_generate`
(`#panelGenerate` never became visible) with no `generate` call logged and no
evidence of why. This probe runs the capture script unchanged and records, from the
outside, what the page and the network looked like around that click, so the cause
is read from an artifact rather than inferred from code.

It records WIDER than any one theory: every console / pageerror / dialog event, every
`/api/` request and response (status plus a body excerpt), and, around the click, the
wizard's state variables and the lock reason the app itself gives, which panels are
visible, the button's match count / box / what sits on top of it, and any open
modal or drawer. A snapshot is taken after a successful click too, so a stall can be
compared with a pass. It does not read the app's shared toast element (see `_STATE_JS`).

Cost: the same as the capture it wraps (about $0.11-0.27 of real API spend).
Prereqs: as `capture_screenshots` (app running, `.api_key`, Chromium installed).

Usage:
    python -m scripts.capture_stall_probe --out <events.jsonl> --headless --keep-user

Everything after `--out` is passed to `capture_screenshots`. A failure screenshot is
written beside the JSONL (`<out>.png`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    BrowserContext,
    ConsoleMessage,
    Dialog,
    Error,
    Page,
    Request,
    Response,
)

from scripts import capture_screenshots
from ui_pages import WizardTemplatePage
from ui_pages.selectors import Wizard

# Response bodies are only read for routes that decide whether Generate is reachable.
_BODY_ROUTES = ("composition", "freeze", "approve", "generate", "context")
_BODY_EXCERPT = 600

# Deliberately does NOT read the app's shared toast element: tests/test_ux_toast_wait_gate.py
# (item 159, C-11) fails any Python file that names it. The reason a refused wizardGoTo()
# gives is read from the app's own function instead (`lockReason5` below).
_STATE_JS = """
() => {
  // A ReferenceError means the app.js global does not exist; that is itself a finding.
  const call = (fn) => {
    try { return fn(); }
    catch (e) { return (e instanceof ReferenceError) ? '<undefined>' : '<error: ' + e + '>'; }
  };
  const shown = (el) => {
    const cs = getComputedStyle(el);
    return el.getClientRects().length > 0 && cs.display !== 'none' && cs.visibility !== 'hidden';
  };
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, w: r.width, h: r.height};
  };
  const panel = document.getElementById('panelGenerate');
  const overlays = Array.from(document.querySelectorAll(
    '[role="dialog"], dialog, .cb-modal, .cb-drawer, [class*="modal"], [class*="drawer"]'
  )).filter(shown).map((el) => ({
    id: el.id, cls: String(el.className).slice(0, 120), text: (el.textContent || '').trim().slice(0, 300),
  }));
  return {
    wizardStep: call(() => _wizardStep),
    lastContextPath: call(() => lastContextPath),
    compositionFrozen: call(() => _compositionFrozen),
    compositionStale: call(() => _compositionStale),
    reachable5: call(() => _wizardReachable(5)),
    lockReason5: call(() => _wizardLockReason(5)),
    panelGenerate: panel ? {
      cls: panel.className, shown: shown(panel), box: box(panel),
      display: getComputedStyle(panel).display,
    } : null,
    visiblePanels: Array.from(document.querySelectorAll('.cb-panel')).filter(shown).map((p) => p.id),
    overlays,
    scrollY: window.scrollY,
    viewport: {w: window.innerWidth, h: window.innerHeight},
  };
}
"""

_TOP_ELEMENT_JS = """
(el) => {
  const r = el.getBoundingClientRect();
  const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
  const desc = (n) => n ? (n.tagName + '#' + n.id + '.' + String(n.className).slice(0, 80)) : null;
  return {self: desc(el), onTop: desc(top), selfIsTop: top === el || el.contains(top)};
}
"""


class Recorder:
    """Appends one JSON object per line; flushes each so a killed run still leaves evidence."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.t0 = time.monotonic()
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.fh = out.open("w", encoding="utf-8")
        self.pending_bodies: list[tuple[dict[str, Any], Response]] = []

    def emit(self, kind: str, **data: Any) -> dict[str, Any]:
        rec: dict[str, Any] = {"t": round(time.monotonic() - self.t0, 3), "kind": kind, **data}
        self.fh.write(json.dumps(rec, default=str) + "\n")
        self.fh.flush()
        return rec

    def resolve_bodies(self) -> None:
        """Read the bodies of the responses worth reading; a gone body is a finding, not an error."""
        for rec, resp in self.pending_bodies:
            try:
                body = resp.text()[:_BODY_EXCERPT]
            except Exception as exc:
                body = f"<unreadable: {exc}>"
            self.emit("api_body", url=rec["url"], status=rec["status"], body=body)
        self.pending_bodies.clear()


def _attach(rec: Recorder, page: Page) -> None:

    def on_console(m: ConsoleMessage) -> None:
        rec.emit("console", level=m.type, text=m.text[:500])

    def on_pageerror(e: Error) -> None:
        rec.emit("pageerror", text=str(e)[:800])

    def on_dialog(d: Dialog) -> None:
        rec.emit("dialog", type=d.type, message=d.message[:500])

    def on_requestfailed(r: Request) -> None:
        rec.emit("requestfailed", url=r.url, failure=r.failure)

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("dialog", on_dialog)
    page.on("requestfailed", on_requestfailed)

    def on_response(resp: Response) -> None:
        if "/api/" not in resp.url:
            return
        entry = rec.emit("api", method=resp.request.method, url=resp.url, status=resp.status)
        if any(route in resp.url for route in _BODY_ROUTES):
            rec.pending_bodies.append((entry, resp))

    page.on("response", on_response)


def _snapshot(rec: Recorder, page: Page, label: str) -> None:
    try:
        state = page.evaluate(_STATE_JS)
    except Exception as exc:
        state = {"evaluate_failed": str(exc)}
    button: list[dict[str, Any]] = []
    try:
        loc = page.locator(Wizard.CONTINUE_TO_GENERATE)
        for i in range(loc.count()):
            item = loc.nth(i)
            info: dict[str, Any] = {"visible": item.is_visible(), "box": item.bounding_box()}
            info.update(item.evaluate(_TOP_ELEMENT_JS))
            button.append(info)
    except Exception as exc:
        button.append({"locate_failed": str(exc)})
    rec.emit("snapshot", label=label, url=page.url, state=state, button_matches=button)
    rec.resolve_bodies()


def _wrap_continue(rec: Recorder, out: Path) -> None:
    original: Callable[[WizardTemplatePage], None] = WizardTemplatePage.continue_to_generate

    def wrapped(self: WizardTemplatePage) -> None:
        _snapshot(rec, self.page, "before_click")
        try:
            original(self)
        except Exception as exc:
            rec.emit("continue_to_generate_failed", error=f"{type(exc).__name__}: {exc}"[:600])
            _snapshot(rec, self.page, "after_click_failed")
            shot = out.with_suffix(".png")
            try:
                self.page.screenshot(path=str(shot), full_page=True)
                rec.emit("failure_screenshot", path=str(shot))
            except Exception as shot_exc:
                rec.emit("failure_screenshot_failed", error=str(shot_exc))
            raise
        _snapshot(rec, self.page, "after_click_ok")

    WizardTemplatePage.continue_to_generate = wrapped  # type: ignore[method-assign]


def _wrap_new_page(rec: Recorder) -> None:
    original = BrowserContext.new_page

    def new_page(self: BrowserContext, *args: Any, **kwargs: Any) -> Page:
        page = original(self, *args, **kwargs)
        _attach(rec, page)
        return page

    BrowserContext.new_page = new_page  # type: ignore[method-assign]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", required=True, type=Path, help="JSONL file to write the evidence to")
    args, passthrough = ap.parse_known_args()

    rec = Recorder(args.out)
    _wrap_new_page(rec)
    _wrap_continue(rec, args.out)
    rec.emit("start", argv=passthrough)

    # capture_screenshots.main() parses sys.argv itself.
    sys.argv = [sys.argv[0], *passthrough]
    status = 1
    try:
        status = capture_screenshots.main()
    except Exception as exc:
        rec.emit(
            "capture_raised",
            error=f"{type(exc).__name__}: {exc}"[:600],
            tb=traceback.format_exc()[-1500:],
        )
    rec.emit("end", status=status)
    rec.fh.close()
    print(f"probe evidence: {args.out}")
    return status


if __name__ == "__main__":
    sys.exit(main())

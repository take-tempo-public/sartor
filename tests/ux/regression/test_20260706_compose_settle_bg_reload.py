"""Regression: the Compose settle gate waits out an in-flight background reload.

Compose flaky-test-class fix (`fix/compose-settle-bg-reload`). The settle signal is
now ``#composeList[data-compose-ready]:not([data-compose-bg-pending])`` — the render-
done marker present AND no reload-firing background call in flight. Each reloader
increments a ``data-compose-bg-pending`` counter attribute before ``loadComposition``
re-sets ``data-compose-ready`` and decrements it in a ``finally``, so the deferred
``/draft-gap-fill`` POST + reload (which lands *after* ``data-compose-ready`` is first
set) can no longer let ``_wait_settled`` return on a non-terminal render.

LLM-free (``analyzer.draft_gap_fill_bullets`` is stubbed; the real routes run). We wrap
the gap-fill stub with a server-side delay so its reload is reliably still in flight
when the first render sets ``data-compose-ready`` — the exact race the counter closes —
then assert, WITHOUT retry right after ``open()``, that the settle blocked until the
reload converged.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.ux import stubs as ux_stubs
from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardComposePage, WizardJobPage
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."

# JS installed on #composeList (a static element, index.html) BEFORE the cascade runs:
# count every time the bg-pending counter attribute turns on during load, so the test
# can prove the counter actually fired (not just that the page happened to settle).
_OBSERVE_BG_PENDING = (
    "() => { window.__bgSeen = 0;"
    " const el = document.getElementById('composeList'); if (!el) return;"
    " new MutationObserver(() => {"
    "   if (el.hasAttribute('data-compose-bg-pending')) window.__bgSeen++;"
    " }).observe(el, { attributes: true, attributeFilter: ['data-compose-bg-pending'] }); }"
)


def _delayed(fn: Callable[..., Any], seconds: float) -> Callable[..., Any]:
    """Wrap a stub so the (threaded) route handler sleeps before returning."""

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        time.sleep(seconds)
        return fn(*args, **kwargs)

    return _wrapped


@pytest.mark.ux
@pytest.mark.slow
def test_compose_settle_waits_for_inflight_gap_fill_reload(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    # Slow the (stubbed) gap-fill draft so its POST + reload is reliably in flight
    # after the first render set data-compose-ready — the race the counter closes.
    monkeypatch.setattr(
        analyzer, "draft_gap_fill_bullets", _delayed(ux_stubs.fake_draft_gap_fill_bullets, 0.4)
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    # Arm the counter observer before Compose's cascade fires (open() clicks in).
    page.evaluate(_OBSERVE_BG_PENDING)

    WizardComposePage(page, live_server).open()

    # The counter marked at least one in-flight background reload during load...
    assert page.evaluate("() => window.__bgSeen") > 0, "bg-pending counter never fired"
    # ...and open() -> _wait_settled blocked on it until the slow gap-fill reload
    # converged: the lane is present with NO further retry (an early settle would fail
    # this bare count()), the counter has drained, and the settle selector matches.
    assert page.locator(Compose.GAP_FILL_ROW).count() == 1, (
        "settle returned before the gap-fill reload"
    )
    assert page.locator("#composeList[data-compose-bg-pending]").count() == 0
    assert page.locator(Compose.SETTLED).count() == 1
    # Sanity: the terminal lane is the stubbed proposal.
    expect(page.locator(Compose.GAP_FILL_ROW).first).to_contain_text("Stubbed gap-fill bullet")

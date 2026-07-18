"""Falsification test for `docs/dev/diagnosis/compose-unawaited-reloads.md`.

`_decideGapFill` (static/app.js) brackets its own POST + reload with
``_markComposeBgReload(1)`` / ``_markComposeBgReload(-1)`` (the same settle-gate
counter `fix/ci-first-linux-run` (commit be48fec) fixed for the 5 auto-arrival
Compose cascades), but calls ``loadComposition()`` fire-and-forget instead of
``await``ing it — so ``_markComposeBgReload(-1)`` fires the instant
``loadComposition()`` is merely STARTED, not once it has actually finished
re-fetching ``/composition`` and repainting `#composeList`.

This test proves that gap, deterministically. Naive approach that does NOT
work: check whether the retired row is still in the DOM the instant the
settle-gate counter clears. It doesn't work because `loadComposition()`
synchronously wipes `#composeList` to a "Scoring corpus…" placeholder
(`_setLoadingPlaceholder` -> `_clearChildren`) the MOMENT it is called — before
its first internal `await` — regardless of whether the caller awaits the whole
function. So the old row is gone from the DOM almost immediately either way;
row-absence can't distinguish "genuinely re-settled" from "mid-load
placeholder" (confirmed empirically: an earlier version of this test asserting
on row-absence alone passed on both buggy and fixed code — a broken
instrument, not a real falsification).

The actual settle-gate CONTRACT (`ui_pages/selectors.py::Compose.SETTLED`,
consumed by `WizardComposePage._wait_settled`) is the combined selector
`#composeList[data-compose-ready]:not([data-compose-bg-pending])` —
`data-compose-ready` is removed synchronously at `loadComposition()`'s start
(same moment as the DOM wipe above) and re-added only once the WHOLE function
has finished fetching + repainting. So the precise, correct check is: at the
exact instant `data-compose-bg-pending` is cleared, is `data-compose-ready`
ALREADY back? If `loadComposition()` is awaited, the counter cannot clear
until the whole function (including the re-add) has finished, so yes. If it
is fire-and-forget, the counter clears the instant the reload is merely
kicked off — long before the delayed fetch below resolves and re-adds
`data-compose-ready` — so no. That comparison is captured synchronously
inside a single `MutationObserver` callback (no Python/Playwright round-trip
in the critical window), so there is no timing slop for the 0.5s delay to
paper over.

We delay ONLY `loadComposition()`'s own internal composition GET
(`blueprints.applications._read_composition_overrides`, called nowhere else
in the app), so the delay lands inside `loadComposition()` itself, not inside
the (undelayed) `/gap-fill-decide` POST that precedes it.

LLM-free (`analyzer.draft_gap_fill_bullets` is stubbed; the real routes run).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardComposePage, WizardJobPage
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."

# JS installed on #composeList right before the delayed retire click. The
# MutationObserver callback runs synchronously (same JS tick) whenever
# data-compose-bg-pending changes; the FIRST time it is cleared, capture
# whether data-compose-ready is ALREADY back — in the same callback, so there
# is no Python/Playwright round-trip for the 0.5s server delay to paper over.
_OBSERVE_SETTLE_RACE = (
    "() => { window.__bgClearedReadyState = null;"
    " const el = document.getElementById('composeList'); if (!el) return;"
    " new MutationObserver(() => {"
    "   if (window.__bgClearedReadyState === null && !el.hasAttribute('data-compose-bg-pending')) {"
    "     window.__bgClearedReadyState = el.hasAttribute('data-compose-ready');"
    "   }"
    " }).observe(el, { attributes: true, attributeFilter: ['data-compose-bg-pending'] }); }"
)


def _delayed(fn: Callable[..., Any], seconds: float) -> Callable[..., Any]:
    """Wrap a function so it sleeps before returning — same idiom as the other
    Compose settle-gate regression tests, applied here to a deterministic
    (non-LLM) helper instead of an analyzer stub."""

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        time.sleep(seconds)
        return fn(*args, **kwargs)

    return _wrapped


@pytest.mark.ux
@pytest.mark.slow
def test_decide_gap_fill_retire_reload_is_awaited(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import blueprints.applications as applications_module

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open()

    # Sanity: the stubbed auto-fire drafted a gap-fill proposal to retire.
    assert page.locator(Compose.GAP_FILL_ROW).count() >= 1, (
        "no gap-fill proposal rendered — nothing to retire, test setup is wrong"
    )

    # Delay ONLY loadComposition()'s own internal composition GET — NOT the
    # gap-fill-decide POST the retire click fires first. `_read_composition_overrides`
    # is called exactly once in the whole app, from get_application_composition
    # (blueprints/applications.py), so this cannot leak into the retire POST itself
    # or any other route.
    original_read_overrides = applications_module._read_composition_overrides
    monkeypatch.setattr(
        applications_module,
        "_read_composition_overrides",
        _delayed(original_read_overrides, 0.5),
    )
    page.evaluate(_OBSERVE_SETTLE_RACE)

    page.locator(Compose.GAP_FILL_ROW).first.locator(Compose.GAP_FILL_RETIRE).click()

    # Wait for the MutationObserver to have captured the first bg-pending clear
    # (captured synchronously alongside the data-compose-ready check — see
    # module docstring for why this must happen in one JS tick, not two
    # Python round-trips).
    page.wait_for_function("() => window.__bgClearedReadyState !== null")
    assert page.evaluate("() => window.__bgClearedReadyState") is True, (
        "settle gate reported 'not pending' while data-compose-ready was still "
        "absent — loadComposition() is not awaited in _decideGapFill, so the "
        "bg-pending counter cleared before the reload actually finished"
    )

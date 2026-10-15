"""Guard: Compose's ``networkidle`` pre-drain is bounded and never fails the wait (item 30).

``WizardComposePage._wait_settled`` runs ``networkidle`` only as a cheap pre-drain;
the real settle gate is ``Compose.SETTLED``. The pre-drain must therefore cost at
most ``_NETWORKIDLE_PREDRAIN_MS`` and swallow its own timeout. Without that bound a
withheld ``networkidle`` is a 30 s Playwright default, and that is the failure item 30
recorded on CI (docs/dev/diagnosis/reorder-networkidle-bound.md, O-1..O-4).

This test forces ``networkidle`` to be withheld deterministically (a request whose
headers arrived and whose body is held, then a child-frame commit that makes
Playwright recalculate; prior dossier O-18), so it does not depend on the
Playwright-internal ordering race. It fails closed if anyone makes the production
pre-drain unbounded again.

Known limit (stated, not papered over): it guards production's ``_wait_settled``. The
keyboard-reorder test's instrument is guarded by calling the same
``predrain_networkidle`` function, not by this test.
"""

from __future__ import annotations

import time
from types import ModuleType

import pytest
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.ux.regression.test_20260604_bullet_drag_reorder import (
    _HeldBodyServer,
    _reach_compose,
)
from ui_pages.wizard_compose import PREDRAIN

# Hard-coded on purpose, not derived from `_NETWORKIDLE_PREDRAIN_MS`: a mutation of
# that constant must not be able to move this assertion with it. 10 s is twice the
# production bound and a third of Playwright's 30 s default.
_HARD_BOUND_S = 10.0

# Appends a hidden about:blank iframe and resolves once it has loaded: a child-frame
# commit, which is what forces Playwright to recalculate the main frame's
# `networkidle` (prior dossier O-12, O-13).
_COMMIT_CHILD_FRAME_JS = """
() => new Promise((resolve) => {
  const f = document.createElement('iframe');
  f.id = 'predrainGuardFrame';
  f.style.display = 'none';
  f.onload = () => resolve();
  document.body.appendChild(f);
})
"""


@pytest.mark.ux
@pytest.mark.slow
def test_predrain_stall_is_bounded_and_swallowed(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    compose._wait_settled()  # at rest: networkidle has fired before the request below

    server = _HeldBodyServer()
    try:
        page.evaluate(
            "url => { window.__predrainHeld = fetch(url).then(r => r.text()); }", server.url
        )
        assert server.headers_sent.wait(10), "probe void: held server never saw the request"
        page.evaluate(_COMMIT_CHILD_FRAME_JS)

        # Control (a void probe must fail loudly): networkidle really is withheld.
        with pytest.raises(PlaywrightTimeoutError):
            page.wait_for_load_state("networkidle", timeout=1_500)

        stalls_before = len(PREDRAIN.stalls)
        t0 = time.monotonic()
        compose._wait_settled()  # must not raise, and must return inside the bound
        elapsed = time.monotonic() - t0
    finally:
        server.close()

    assert elapsed < _HARD_BOUND_S, (
        f"_wait_settled took {elapsed:.1f}s with networkidle withheld; the pre-drain is "
        f"no longer bounded (item 30)"
    )
    assert len(PREDRAIN.stalls) == stalls_before + 1, (
        "the stall was not recorded: _wait_settled no longer goes through "
        "predrain_networkidle, so the [ux] networkidle pre-drain line is blind to it"
    )

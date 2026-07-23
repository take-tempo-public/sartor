"""Falsification test for carry-forward ledger item #5 (`docs/dev/RELEASE_CHECKLIST.md`).

`fix/compose-unawaited-reloads` fixed 9 `loadComposition()` (static/app.js) call
sites that bracket their own POST + reload with `_markComposeBgReload(1)` /
`finally { _markComposeBgReload(-1); }` but fired the reload fire-and-forget
instead of `await`ing it. Three OTHER sites were excluded from that fix as having
"a materially different shape": `static/app.js` `_resumeIntoStep6` (~:6549),
`_resumeIntoPreGenerateStep` (~:6606), and `wizardGoTo`'s `step === 3` branch
(~:6932, exercised here via the wizard rail — the purest bare-call path, not
entangled with the Skip-to-Compose button's extra `skipClarifications()` cascade).

Rigorous review (this session, `chore/reduction-sprint-ledger-compose-notes`,
2026-07-22 — analysis plus an independent adversarial reviewer tasked to refute
it) concluded `await` would be the WRONG fix here: unlike the 9 sites, none of
these three wraps `loadComposition()` in a `_markComposeBgReload` bracket, so the
premature-`finally`-decrement race those 9 sites had is structurally absent. This
test proves the positive claim instead — that the bare `wizardGoTo(3)` call is
already race-free under the `Compose.SETTLED` contract (`ui_pages/selectors.py`,
`#composeList[data-compose-ready]:not([data-compose-bg-pending])`):

`loadComposition()` clears `data-compose-ready` as its own first synchronous
statement (`static/app.js`, before its first `await`) and re-sets it only at its
true terminal, after the full fetch + repaint. Because `_wizardRender()` (called
immediately before the bare `loadComposition()` call) has no `await` of its own,
the marker-clear happens in the SAME synchronous browser task as the rail click —
by the time Playwright's `click()` returns, it has already run. So (a) the marker
is reliably absent the instant we can observe it, and (b) `Compose.SETTLED`
cannot report true until the genuinely-delayed fetch below actually resolves —
proven by asserting the wall-clock time to settle is at least the injected delay,
not merely "eventually true regardless of cause".

The first (undelayed) visit to Compose lets the real auto-draft cascade run and
persist (summary draft + gap-fill, same as any fresh arrival); by the time we
leave and re-enter via the rail — the call under test — `has_draft`/`has_gap_fill`
are already true, so the cascade correctly doesn't re-fire and
`data-compose-bg-pending` never leaves zero on this second entry. That isolates
the assertion to the one signal these three sites' correctness actually depends
on: `data-compose-ready`.

LLM-free (`install_llm_stubs`; the real routes run).
"""

from __future__ import annotations

import time
from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardComposePage, WizardJobPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Compose, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."
_DELAY_SECONDS = 0.6


def _delayed_read_overrides(original, seconds):
    def _wrapped(*args, **kwargs):
        time.sleep(seconds)
        return original(*args, **kwargs)

    return _wrapped


@pytest.mark.ux
@pytest.mark.slow
def test_wizard_goto_bare_reload_settles_only_after_real_load(
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

    compose = WizardComposePage(page, live_server)
    compose.open()  # first, undelayed visit — lets the real auto-cascade persist
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS)

    # Leave Compose so the panel hides and the settle marker is stale-but-present
    # from the visit above — the scenario the reviewer's "attack vector 2" probed.
    page.click(Wizard.step_button(2))
    page.wait_for_selector(Wizard.PANEL_COMPOSE, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Delay ONLY loadComposition()'s own internal composition GET.
    original = applications_module._read_composition_overrides
    monkeypatch.setattr(
        applications_module,
        "_read_composition_overrides",
        _delayed_read_overrides(original, _DELAY_SECONDS),
    )

    start = time.monotonic()
    page.click(Wizard.step_button(3))  # the bare `if (step === 3) loadComposition();` call

    # By the time click() returns, the synchronous portion of wizardGoTo (including
    # loadComposition's own entry-time removeAttribute) has already run in the
    # browser's single JS task — no MutationObserver needed to catch this window.
    assert page.locator(Compose.LIST).get_attribute("data-compose-ready") is None, (
        "data-compose-ready was still present immediately after the rail click — "
        "the bare loadComposition() call did not clear the settle marker at entry"
    )

    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=DEFAULT_TIMEOUT_MS)
    elapsed = time.monotonic() - start
    assert elapsed >= _DELAY_SECONDS * 0.8, (
        f"Compose.SETTLED reported true after only {elapsed:.2f}s, less than the "
        f"{_DELAY_SECONDS}s injected fetch delay — the settle gate did not actually "
        "wait for the bare loadComposition() reload to finish"
    )

    # Re-fetched, fully re-rendered content — not a stale-cascade artifact of the
    # first visit — proving the reload this test forced actually landed.
    assert page.locator(Compose.EXPERIENCE_CARD).count() >= 1

"""Regression: visible working states across Clarify->Compose + the Compose
background-cascade chip + Compose/Corpus scroll preservation (owner-observed
UX gaps, feat/ux-busy-states-and-hydration).

- **#1** — `submitClarifications` / `skipClarifications` / the recommend call
  inside `_fireRecommendThenCompose` previously ran real LLM calls behind only
  a status-pill text change; the app read as frozen. All three now wrap in the
  existing `_setBusy` full-overlay idiom (`#_busyBanner`).
- **#2** — `_fireDraftSummary(force=true)` (the Positioning card's explicit
  "Regenerate" click) now disables the button + relabels it in flight,
  restoring in `finally` — the silent auto-fire on Compose arrival
  (`force=false`, no button) is unaffected.
- **#3** — the Compose background auto-cascade (summary draft / skills
  recommend / gap-fill) was invisible by design (the `data-compose-bg-pending`
  counter is test-only). A new `#composeBgChip` renders "Updating
  suggestions..." while that SAME counter is nonzero — driven off
  `_markComposeBgReload`, never a second source of truth — so the settle gate
  (`Compose.SETTLED`) and the chip can never disagree.
- **#4** — every Compose reload (`loadComposition`) and Corpus reload
  (`refreshCorpus` / `_loadCorpusDetail`) clears + rebuilds a list, which
  briefly shrinks the page and snaps window scroll toward the top. Both now
  capture/restore `window.scrollY` around the reload.

Each test delays a stubbed LLM call server-side (the same `_delayed` idiom
`test_20260706_compose_settle_bg_reload.py` established) so the in-flight
state is reliably observable before it clears. LLM-free throughout.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.ux import stubs as ux_stubs
from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardClarifyPage, WizardComposePage, WizardJobPage
from ui_pages.selectors import Compose, Wizard

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."

_BUSY_BANNER = "#_busyBanner"
_BUSY_SHOWING = re.compile(r"(^|\s)show(\s|$)")
_BUSY_LABEL = re.compile(r"integrating your answers|preparing compose", re.IGNORECASE)


def _delayed(fn: Callable[..., Any], seconds: float) -> Callable[..., Any]:
    """Wrap a stub so the (threaded) route handler sleeps before returning."""

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        time.sleep(seconds)
        return fn(*args, **kwargs)

    return _wrapped


@pytest.mark.ux
@pytest.mark.slow
def test_submit_clarifications_shows_busy_overlay_then_clears(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    # Slow the recommend call so the overlay is reliably still up when checked.
    monkeypatch.setattr(
        analyzer, "recommend_bullets", _delayed(ux_stubs.fake_recommend_bullets, 0.4)
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardJobPage(page, live_server).continue_to_clarify()
    WizardClarifyPage(page, live_server).answer_first("Yes, ran Kafka in production.")

    page.click(Wizard.SUBMIT_CLARIFICATIONS)
    # Overlay visible mid-flight, with one of the two accurate labels.
    banner = page.locator(_BUSY_BANNER)
    expect(banner).to_have_class(_BUSY_SHOWING)
    expect(banner).to_contain_text(_BUSY_LABEL)
    # Clears once Compose lands.
    page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=15_000)
    expect(banner).not_to_have_class(_BUSY_SHOWING)


@pytest.mark.ux
@pytest.mark.slow
def test_skip_clarifications_shows_busy_overlay_then_clears(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    monkeypatch.setattr(
        analyzer, "recommend_bullets", _delayed(ux_stubs.fake_recommend_bullets, 0.4)
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    # Land on Step 2 via the rail (not "Continue to Clarify", which fetches
    # questions directly) — keeps #clarifyStartRow's Skip button visible.
    page.click(Wizard.step_button(2))
    page.wait_for_selector(Wizard.PANEL_CLARIFY, state="visible")

    page.locator("#clarifyStartRow").get_by_role("button", name="Skip").click()
    banner = page.locator(_BUSY_BANNER)
    expect(banner).to_have_class(_BUSY_SHOWING)
    expect(banner).to_contain_text(re.compile("preparing compose", re.IGNORECASE))
    page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=15_000)
    expect(banner).not_to_have_class(_BUSY_SHOWING)


@pytest.mark.ux
@pytest.mark.slow
def test_regenerate_summary_button_disables_during_fetch(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    monkeypatch.setattr(
        analyzer,
        "draft_positioning_summary",
        _delayed(ux_stubs.fake_draft_positioning_summary, 0.4),
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()  # auto-drafts the summary once
    compose._wait_settled()

    regen = page.locator(Compose.POSITIONING_DRAFT_REGEN)
    expect(regen).to_be_enabled()
    expect(regen).to_have_text("Regenerate")

    regen.click()
    expect(regen).to_be_disabled()
    expect(regen).to_have_text("Regenerating…")

    compose._wait_settled()
    expect(regen).to_be_enabled()
    expect(regen).to_have_text("Regenerate")


@pytest.mark.ux
@pytest.mark.slow
def test_compose_bg_chip_visible_during_background_reload_and_settle_still_works(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    # Same race the settle-gate regression test (test_20260706) exercises:
    # slow the deferred gap-fill draft so its reload is reliably in flight.
    monkeypatch.setattr(
        analyzer, "draft_gap_fill_bullets", _delayed(ux_stubs.fake_draft_gap_fill_bullets, 0.4)
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    # Arm a MutationObserver on the chip's class BEFORE Compose's cascade
    # fires (open() clicks in), so we can prove it toggled visible at some
    # point during the reload — not just infer it from timing.
    page.evaluate(
        "() => { window.__chipShown = 0;"
        " const chip = document.getElementById('composeBgChip');"
        " if (!chip) return;"
        " new MutationObserver(() => {"
        "   if (!chip.classList.contains('hidden')) window.__chipShown++;"
        " }).observe(chip, { attributes: true, attributeFilter: ['class'] }); }"
    )

    WizardComposePage(page, live_server).open()  # blocks on _wait_settled

    # The chip toggled visible at least once during the (slowed) reload...
    assert page.evaluate("() => window.__chipShown") > 0, "chip never became visible"
    # ...and it's hidden again now that the settle gate confirms terminal render —
    # the chip and the settle gate read off the SAME counter, so they agree.
    expect(page.locator("#composeBgChip")).to_have_class(re.compile(r"(^|\s)hidden(\s|$)"))
    assert page.locator(Compose.SETTLED).count() == 1


@pytest.mark.ux
@pytest.mark.slow
def test_compose_reload_preserves_scroll_position(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepting/pinning a bullet re-enters `loadComposition()`, which clears
    + rebuilds #composeList — the owner's "scrolls to top" report. Seed enough
    experiences that the list is genuinely scrollable, scroll down, trigger a
    reload via the JS entry point itself (deterministic — no dependency on a
    specific card's on-screen position), and assert the position survives."""
    cid = seed_user(ux_app, "alice")
    for i in range(8):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open()

    page.evaluate("() => window.scrollTo(0, 400)")
    before = page.evaluate("() => window.scrollY")
    assert before > 0, "test setup didn't actually scroll the page"

    page.evaluate("() => loadComposition()")
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=15_000)
    # _restoreScrollY runs on a requestAnimationFrame after the terminal
    # render — give the browser one frame to paint before reading it back.
    page.wait_for_timeout(100)
    after = page.evaluate("() => window.scrollY")
    assert after == before, f"scroll position not preserved: {before} -> {after}"


@pytest.mark.ux
@pytest.mark.slow
def test_corpus_reload_preserves_scroll_position(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same fix, the Corpus-tab reload path (refreshCorpus) — the exact flow
    the owner hit ("accepting new bullets -> scrolls to top")."""
    cid = seed_user(ux_app, "alice")
    # Collapsed corpus cards are short — seed generously so the list is
    # reliably taller than the 900px test viewport (tests/ux/conftest.py).
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    # The tab click fires loadCorpusIfReady() fire-and-forget, so the experiences
    # fetch + _renderCorpusList() land asynchronously — under end-of-suite CPU
    # load that settle lags past a bare visibility poll (the 20 cards render but
    # paint late), the load-dependent flake class this suite guards against.
    # Await the corpus load deterministically — the same idiom as the
    # refreshCorpus() reload below — so the cards are present before we assert
    # visibility. loadCorpusIfReady() no-ops if the click's load already finished.
    page.evaluate("() => loadCorpusIfReady()")
    page.wait_for_selector("#corpusExperienceList .corpus-card", timeout=15_000)

    page.evaluate("() => window.scrollTo(0, 300)")
    before = page.evaluate("() => window.scrollY")
    assert before > 0, "test setup didn't actually scroll the page"

    page.evaluate("() => refreshCorpus()")
    page.wait_for_selector("#corpusExperienceList .corpus-card", timeout=15_000)
    page.wait_for_timeout(100)
    after = page.evaluate("() => window.scrollY")
    assert after == before, f"scroll position not preserved: {before} -> {after}"

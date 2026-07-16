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

import os
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


# ---------------------------------------------------------------------------
# INSTRUMENT (charter C-7, fix/ux-scroll-position-flake). A WIDE scroll-source
# spy for test_corpus_reload_preserves_scroll_position: records EVERY scroll
# mutation and its source (scroll event / window.scrollTo / scrollIntoView /
# focus / element scrollTop setter), each tagged with the calling stack, a
# timestamp, and the settle state. Dumped on failure so the cause prints itself
# under the RERUN reporter. Scoped WIDER than the scrollIntoView hypothesis on
# purpose: an instrument narrowed to one theory confirms it by hiding rivals.
# ---------------------------------------------------------------------------
_SCROLL_SPY_JS = r"""
(() => {
  window.__scrollSpy = [];
  const t0 = performance.now();
  const caller = () => ((new Error().stack || '').split('\n').slice(2, 5).map(l => l.trim()).join(' | '));
  const rec = (source, extra) => window.__scrollSpy.push(Object.assign({
    t: +(performance.now() - t0).toFixed(1),
    y: window.scrollY,
    h: document.documentElement.scrollHeight,
    active: document.activeElement ? (document.activeElement.id ? '#' + document.activeElement.id : document.activeElement.tagName) : null,
    source: source,
  }, extra));
  const tag = (el) => { try { return (el.id ? '#' + el.id : el.tagName) +
    (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''); }
    catch (e) { return '?'; } };
  window.addEventListener('scroll', () => rec('scroll-event', {}), {passive: true, capture: true});
  ['scrollTo', 'scroll', 'scrollBy'].forEach((fn) => { const o = window[fn].bind(window);
    window[fn] = function (...a) { rec('window.' + fn, {args: JSON.stringify(a).slice(0, 120), by: caller()}); return o(...a); }; });
  const siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (...a) { rec('scrollIntoView', {el: tag(this), args: JSON.stringify(a).slice(0, 80), by: caller()}); return siv.apply(this, a); };
  if (Element.prototype.scrollIntoViewIfNeeded) { const sivn = Element.prototype.scrollIntoViewIfNeeded;
    Element.prototype.scrollIntoViewIfNeeded = function (...a) { rec('scrollIntoViewIfNeeded', {el: tag(this), by: caller()}); return sivn.apply(this, a); }; }
  const fo = HTMLElement.prototype.focus;
  HTMLElement.prototype.focus = function (...a) { rec('focus', {el: tag(this), by: caller()}); return fo.apply(this, a); };
  const d = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop');
  if (d && d.set) Object.defineProperty(Element.prototype, 'scrollTop', {configurable: true, get: d.get,
    set: function (v) { rec('el.scrollTop=', {el: tag(this), v: v, by: caller()}); return d.set.call(this, v); }});
  // Exposed so _SCROLL_SPY_NAMED_HOOKS_JS (injected separately, post-load — see
  // that constant's own comment for why) can log identically-shaped events.
  window.__scrollSpyRec = rec;
})();
"""


# ---------------------------------------------------------------------------
# INSTRUMENT hardening (Chip 1a, charter C-7). Tags _captureScrollY /
# _restoreScrollY / refreshCorpus with a structural FIRST-vs-SECOND
# invocation id, instead of requiring a human to infer it from stack text
# and height-flatness after the fact (which is the only way mode B was
# originally identified). MUST be injected via an explicit page.evaluate(...)
# call AFTER the page has loaded (never via add_init_script): app.js has no
# wrapping IIFE, so refreshCorpus/_captureScrollY/_restoreScrollY are true
# window-scoped globals, and add_init_script runs BEFORE any of the page's
# own <script> tags — patching these names that early would just get
# silently clobbered when app.js's own top-level declarations execute
# moments later. (app.js already relies on this exact ordering itself:
# onUserSelect is declared at app.js:394 and unconditionally reassigned at
# app.js:5511-5512, and that reassignment is in effect before the `change`
# listener bound at app.js:46 can ever fire.)
#
# _restoreScrollY (app.js:5491-5493) is a fire-and-forget
# requestAnimationFrame — refreshCorpus never awaits it, so its promise
# resolves (and this wrapper's `finally` marks the invocation closed) a
# full microtask-drain before the rAF actually fires. Reading the
# "currently open" set live at fire-time would therefore NEVER see the
# invocation that scheduled it — exactly backwards from the point of this
# instrument. So the open-set is snapshotted at SCHEDULE time (still
# genuinely inside the invocation) and carried in the closure to the
# eventual "-fired" event, rather than re-read when the rAF callback runs.
# ---------------------------------------------------------------------------
_SCROLL_SPY_NAMED_HOOKS_JS = r"""
(() => {
  if (typeof window.__scrollSpyRec !== 'function') {
    window.__scrollSpyNamedHooksError = 'builtin spy missing — _SCROLL_SPY_JS must run first';
    return;
  }
  const rec = window.__scrollSpyRec;
  let _rcCounter = 0;
  // The SET of invocations open right now — not a unique "who's calling"
  // attribution. With exactly one entry that's unambiguous (the common case
  // here: this test's action sequence only ever has 0 or 1 refreshCorpus
  // invocation open, except during the deliberate 2-invocation overlap the
  // Chip 1a self-checks force). A 2+-entry set narrows candidates without
  // uniquely identifying which open invocation made THIS specific call —
  // resolve it the same way the self-check test does: find the call whose
  // set has shrunk to a singleton (unambiguous by construction) and get the
  // other one by elimination.
  const _rcOpen = new Set();

  const origCapture = window._captureScrollY;
  const origRestore = window._restoreScrollY;
  const origRefresh = window.refreshCorpus;
  if (!origCapture || !origRestore || !origRefresh) {
    window.__scrollSpyNamedHooksError = 'refreshCorpus/_captureScrollY/_restoreScrollY missing at hook time';
    return;
  }

  // NB: _captureScrollY/_restoreScrollY are also called by loadComposition()
  // and the corpus-card-expand path — neither is reachable from this test's
  // action sequence, so an empty openRC/scheduledDuring here unambiguously
  // means "not refreshCorpus", not "tagging is broken".
  window._captureScrollY = function (...a) {
    const result = origCapture.apply(this, a);
    rec('_captureScrollY', {y: result, openRC: Array.from(_rcOpen)});
    return result;
  };

  window._restoreScrollY = function (y, ...rest) {
    const scheduledDuring = Array.from(_rcOpen);   // snapshot at schedule time — see module comment above
    rec('_restoreScrollY-scheduled', {y, scheduledDuring});
    requestAnimationFrame(() => rec('_restoreScrollY-fired', {y, scheduledDuring}));
    return origRestore.call(this, y, ...rest);
  };

  window.refreshCorpus = async function (...args) {
    const id = ++_rcCounter;
    _rcOpen.add(id);
    rec('refreshCorpus-enter', {id, openRC: Array.from(_rcOpen)});
    try {
      return await origRefresh.apply(this, args);
    } finally {
      // finally, not catch: refreshCorpus is called fire-and-forget from the
      // tab-click handler, and this wrapper must stay exception-transparent —
      // altering resolve/reject semantics would change app behavior under test,
      // which an instrumentation-only chip must never do.
      _rcOpen.delete(id);
      rec('refreshCorpus-exit', {id, openRC: Array.from(_rcOpen)});
    }
  };
  window.refreshCorpus.__scrollSpyWrapped = true;  // dump-time install marker
})();
"""


def _dump_scroll_spy(page: Page, phase: str, value: object, before: object = None) -> None:
    """Print the full scroll-mutation timeline captured by ``_SCROLL_SPY_JS`` +
    ``_SCROLL_SPY_NAMED_HOOKS_JS`` (diagnostic). Never raises: this is called
    from exception handlers, so a problem here must never shadow the real
    failure. Checks BOTH instrument layers are actually alive before trusting
    "0 events" as a negative result — a silently-dead spy (the original O-4
    bug, and the different class of it this chip's own hardening found) must
    never again read the same as "nothing happened."
    """
    try:
        defined = page.evaluate("() => typeof window.__scrollSpy !== 'undefined'")
    except Exception as exc:  # page gone/crashed mid-failure
        print(
            f"\n[scroll-spy] phase={phase} value={value} before={before} "
            f"-- COULD NOT EVALUATE PAGE: {exc!r}"
        )
        return
    if not defined:
        print(
            f"\n[scroll-spy] phase={phase} -- WARNING: window.__scrollSpy is "
            f"UNDEFINED — the spy never initialized. This dump (and any others "
            f"from this run) is untrustworthy."
        )
        return
    named_ok = page.evaluate(
        "() => !!(window.refreshCorpus && window.refreshCorpus.__scrollSpyWrapped)"
    )
    if not named_ok:
        print(
            f"\n[scroll-spy] phase={phase} -- WARNING: named-fn hooks did not "
            f"install ({page.evaluate('() => window.__scrollSpyNamedHooksError || null')!r}); "
            f"FIRST/SECOND-invocation tagging is ABSENT below."
        )
    spy = page.evaluate("() => window.__scrollSpy || []")
    print(f"\n[scroll-spy] phase={phase} value={value} before={before} -- {len(spy)} events:")
    for event in spy:
        print(f"  {event}")


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

    page.add_init_script(_SCROLL_SPY_JS)  # INSTRUMENT (C-7): wide scroll-source spy

    BasePage(page, live_server).load()
    # Named-fn hooks (Chip 1a) MUST be injected here — after load() (app.js has
    # run; see _SCROLL_SPY_NAMED_HOOKS_JS's own comment for why add_init_script
    # would be unsafe) and before select() (the only pre-tab-click caller of
    # refreshCorpus, onUserSelect -> _landingTab() -> loadCorpusIfReady(), can't
    # fire until select() runs).
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    UserPickerPage(page, live_server).select("alice")

    try:
        page.click("#topTabCorpus")
        page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
        # The tab click fires loadCorpusIfReady() fire-and-forget, so the experiences
        # fetch + _renderCorpusList() land asynchronously — under end-of-suite CPU
        # load that settle lags, the load-dependent flake class this suite guards
        # against. Assert on the settled card COUNT (auto-retrying) rather than a bare
        # first-card visibility poll: expect() re-queries the DOM until all 20 cards
        # are attached, regardless of which load path filled them — the same
        # load-path-agnostic idiom that fixed the pipeline-board row race. (An explicit
        # loadCorpusIfReady() re-fire is NOT reliable here: it no-ops once
        # _corpusLoadedForUser is set, which the click's load sets optimistically
        # before its render completes.)
        corpus_cards = page.locator("#corpusExperienceList .corpus-card")
        expect(corpus_cards).to_have_count(20, timeout=15_000)
    except Exception:
        # Chip 1a (C-7): this phase previously had NO dump path at all — a
        # #panelCorpus wait-timeout under load is a confirmed, distinct failure
        # mode (diagnosis doc O-8) that used to vanish with zero diagnostics.
        _dump_scroll_spy(page, "setup", None)
        raise

    page.evaluate("() => window.scrollTo(0, 300)")
    before = page.evaluate("() => window.scrollY")
    if before <= 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "setup-before", before)
    assert before > 0, "test setup didn't actually scroll the page"

    try:
        page.evaluate("() => refreshCorpus()")
        expect(corpus_cards).to_have_count(20, timeout=15_000)
        page.wait_for_timeout(100)
    except Exception:
        # Chip 1a (C-7): same unconditional-dump treatment for the post-refresh
        # settle wait, which likewise had no dump path before this chip.
        _dump_scroll_spy(page, "after-refresh-wait", None, before=before)
        raise
    after = page.evaluate("() => window.scrollY")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "after-refresh", after, before)
    assert after == before, f"scroll position not preserved: {before} -> {after}"


def _spy_events(page: Page, source: str) -> list[dict[str, Any]]:
    """Filter the live ``window.__scrollSpy`` timeline down to one source tag."""
    spy = page.evaluate("() => window.__scrollSpy || []")
    return [e for e in spy if e.get("source") == source]


@pytest.mark.ux
def test_scroll_spy_hooks_fire_for_known_perturbers(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chip 1a self-check (charter C-7) — the hardened spy must be PROVEN to
    capture, not merely assumed to: the original spy silently recorded 0
    events for an entire diagnosis session before that was caught (`## Observed`
    O-4). Directly triggers each hook and asserts a correctly-shaped, correctly
    -tagged event lands, including that a single `refreshCorpus()` call
    produces an enter/capture/restore-scheduled/restore-fired chain that all
    share one invocation id — the FIRST-vs-SECOND attribution this chip adds."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid, company="Company 0")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    assert page.evaluate("() => window.__scrollSpyNamedHooksError || null") is None, (
        "named-fn hooks failed to install"
    )
    assert page.evaluate(
        "() => !!(window.refreshCorpus && window.refreshCorpus.__scrollSpyWrapped)"
    ), "refreshCorpus was not wrapped"

    UserPickerPage(page, live_server).select("alice")
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(1, timeout=15_000)
    # The tab click ITSELF fires loadCorpusIfReady() -> refreshCorpus() fire-
    # and-forget (same mechanism the real flaky test documents) — this is the
    # FIRST invocation, before this test ever calls refreshCorpus() itself.
    # Let it settle, then clear the timeline so the assertions below examine
    # ONLY the deliberate calls this test makes.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'refreshCorpus-exit')",
        timeout=15_000,
    )
    page.evaluate("() => { window.__scrollSpy = []; }")

    page.evaluate("() => window.scrollTo(0, 50)")
    page.evaluate("() => window.scrollBy(0, 10)")
    page.evaluate("() => document.getElementById('corpusExperienceList').scrollIntoView()")
    page.evaluate("() => refreshCorpus()")
    page.wait_for_timeout(150)  # let _restoreScrollY's requestAnimationFrame actually fire

    assert _spy_events(page, "window.scrollTo"), "no window.scrollTo event captured"
    assert _spy_events(page, "window.scrollBy"), "no window.scrollBy event captured"
    assert _spy_events(page, "scrollIntoView"), "no scrollIntoView event captured"

    enters = _spy_events(page, "refreshCorpus-enter")
    exits = _spy_events(page, "refreshCorpus-exit")
    assert len(enters) == 1 and len(exits) == 1, (
        f"expected exactly 1 refreshCorpus enter/exit pair: enters={enters} exits={exits}"
    )
    rc_id = enters[0]["id"]
    assert exits[0]["id"] == rc_id

    captures = _spy_events(page, "_captureScrollY")
    assert captures and rc_id in captures[-1]["openRC"], (
        f"_captureScrollY did not tag refreshCorpus invocation {rc_id}: {captures}"
    )
    scheduled = _spy_events(page, "_restoreScrollY-scheduled")
    fired = _spy_events(page, "_restoreScrollY-fired")
    assert scheduled and rc_id in scheduled[-1]["scheduledDuring"], (
        f"_restoreScrollY-scheduled did not tag invocation {rc_id}: {scheduled}"
    )
    assert fired and rc_id in fired[-1]["scheduledDuring"], (
        f"_restoreScrollY-fired did not tag invocation {rc_id}: {fired}"
    )


@pytest.mark.ux
def test_scroll_spy_attributes_overlapping_refresh_corpus_calls(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chip 1a self-check (charter C-7) — proves the FIRST-vs-SECOND
    invocation tagging survives the exact reordering the diagnosis's
    `## Inferred` hypothesis turns on: an EARLIER `refreshCorpus()` call's
    restore firing AFTER a LATER call's. Forces that reordering
    deterministically (a `fetch` delay on the first call's `/experiences`
    request only) instead of relying on real CPU-load timing, so this test
    is not itself flaky.

    This is the test that would FAIL against a naive "read the open-
    invocations Set live, at rAF-fire-time" design: that Set is always empty
    by fire-time, because the wrapped promise resolves via microtask a full
    frame before the rAF runs. It passes only because `_restoreScrollY`
    snapshots the open set at SCHEDULE time (see `_SCROLL_SPY_NAMED_HOOKS_JS`).
    """
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid, company="Company 0")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    UserPickerPage(page, live_server).select("alice")
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(1, timeout=15_000)
    # The tab click's own fire-and-forget refreshCorpus (same mechanism the
    # real flaky test documents) must settle BEFORE the deliberate overlap
    # below, and the timeline cleared, so it isn't conflated with the two
    # invocations this test is actually examining.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'refreshCorpus-exit')",
        timeout=15_000,
    )
    page.evaluate("() => { window.__scrollSpy = []; }")

    # Fire both invocations from ONE evaluate call, back-to-back and
    # unawaited, so they genuinely overlap rather than just running fast in
    # sequence. Invocation A's /experiences fetch is deliberately held open
    # (its promise is never resolved until this test explicitly releases it
    # below) rather than delayed by a fixed setTimeout — a fixed delay was
    # tried first and was genuinely flaky: refreshCorpus fires 4 additional
    # fire-and-forget fetches per invocation, and two overlapping invocations'
    # worth of those (10 requests total) can contend for the browser's
    # per-origin connection limit, making wall-clock delay an unreliable way
    # to force ordering. Explicitly withholding resolution makes the ordering
    # deterministic by construction instead.
    page.evaluate(
        r"""
        () => {
          const real = window.fetch;
          let expCalls = 0;
          window.__releaseFirstExperiencesFetch = null;
          window.fetch = (...a) => {
            const url = String(a[0] || '');
            if (url.includes('/experiences')) {
              expCalls++;
              if (expCalls === 1) {
                const p = real(...a);
                return new Promise((resolve, reject) => {
                  window.__releaseFirstExperiencesFetch = () => p.then(resolve, reject);
                });
              }
            }
            return real(...a);
          };
          window.refreshCorpus();  // invocation A — /experiences held open, released explicitly below
          window.refreshCorpus();  // invocation B — fetch resolves normally, should restore FIRST
        }
        """
    )
    # Invocation A cannot exit until explicitly released below, so exactly 1
    # refreshCorpus-exit event unambiguously means invocation B has finished.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).filter(e => e.source === 'refreshCorpus-exit').length === 1",
        timeout=15_000,
    )
    page.evaluate("() => window.__releaseFirstExperiencesFetch()")
    page.wait_for_function(
        "() => (window.__scrollSpy || []).filter(e => e.source === 'refreshCorpus-exit').length >= 2",
        timeout=15_000,
    )
    page.wait_for_timeout(150)  # let both _restoreScrollY rAFs actually fire

    enters = _spy_events(page, "refreshCorpus-enter")
    assert len(enters) == 2, f"expected exactly 2 refreshCorpus invocations: {enters}"
    id_a, id_b = enters[0]["id"], enters[1]["id"]  # A = first called (delayed fetch), B = second
    assert id_a != id_b

    fired = _spy_events(page, "_restoreScrollY-fired")
    assert len(fired) == 2, f"expected 2 restore-fired events: {fired}"

    # The invocation whose restore fires LAST while it is the ONLY one still
    # open (a singleton `scheduledDuring` — unambiguous even though a 2+-entry
    # set can't by itself identify which open invocation made the call; see
    # _SCROLL_SPY_NAMED_HOOKS_JS's comment) must be invocation A: its fetch
    # was the one artificially delayed, so by the time it finally restores,
    # B has already scheduled ITS restore and exited. This directly proves
    # the mechanism correctly attributes an EARLIER invocation's restore
    # firing AFTER a LATER invocation's — the exact race the diagnosis's
    # `## Inferred` hypothesis turns on.
    last_fired = fired[-1]
    assert last_fired["scheduledDuring"] == [id_a], (
        f"expected invocation A ({id_a}, the first-called/delayed one) to "
        f"restore LAST, unambiguously (singleton open-set): {fired}"
    )

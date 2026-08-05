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
from ui_pages.selectors import Compose, UserPicker, Wizard

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
# app.js:5676, and that reassignment is in effect before the `change`
# listener bound at app.js:46 can ever fire.)
#
# _restoreScrollY (app.js:5637-5657) is a fire-and-forget
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


# ---------------------------------------------------------------------------
# INSTRUMENT (charter C-7) for mode C's NEXT falsification round — see
# docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md "## Falsification".
#
# Deliberately scoped WIDER than the clamp hypothesis it was written to test
# ("never scope an instrument to the theory you are testing — it will confirm
# your theory by hiding its rivals"). It captures, per `_wizardRender()`
# invocation, in the REAL target test rather than an isolated instrument:
#
#   * a structural invocation id + count  -> settles O-3's still-open question
#     (a) "ONE call arriving late" vs (b) "a genuine SECOND call", which the
#     dossier flags as unresolved and now load-bearing;
#   * `maxScroll` (scrollHeight - innerHeight) at call time and the resolved
#     panel's true absolute top -> tests O-4's clamp reframing directly, by
#     recording whether the nominal target was even REACHABLE when it fired;
#   * the caller stack -> distinguishes wizardInit / _wizardAdvanceTo /
#     wizardGoTo / resume paths without inferring it from wall-clock order.
#
# Same post-load `page.evaluate` injection rule as _SCROLL_SPY_NAMED_HOOKS_JS
# (see that constant's comment): `_wizardRender` is a top-level *function
# declaration* (app.js:7043), so it is a genuine window-scoped global and
# reassigning `window._wizardRender` does rebind the identifier its own
# in-app callers resolve. `_wizardStep` (`let`, app.js:6943) and
# `_WIZARD_PANELS` (`const`, app.js:6947) are NOT window properties — they
# live in the global *lexical* environment — so they are read here by bare
# identifier, which a classic script evaluated later can still resolve.
# ---------------------------------------------------------------------------
_WIZARD_RENDER_SPY_JS = r"""
(() => {
  if (typeof window.__scrollSpyRec !== 'function') {
    window.__wizardRenderSpyError = 'builtin spy missing — _SCROLL_SPY_JS must run first';
    return;
  }
  const orig = window._wizardRender;
  if (typeof orig !== 'function') {
    window.__wizardRenderSpyError = '_wizardRender missing at hook time';
    return;
  }
  const rec = window.__scrollSpyRec;
  const caller = () => ((new Error().stack || '').split('\n').slice(2, 6).map(l => l.trim()).join(' | '));
  let _wrCounter = 0;
  window._wizardRender = function (...args) {
    const id = ++_wrCounter;
    // Snapshot BEFORE the real call, so the target's reachability is recorded
    // as it was when the scroll decision was made — not after the render's own
    // show()/hide() has already changed the document height under it.
    const extra = {id, y: window.scrollY,
                   maxScroll: document.documentElement.scrollHeight - window.innerHeight};
    try {
      extra.step = _wizardStep;
      const pid = (_WIZARD_PANELS[_wizardStep] || [])[0];
      extra.targetId = pid || null;
      const el = pid ? document.getElementById(pid) : null;
      // Absolute document top of the element scrollIntoView(block:'start')
      // will aim at == the scrollY it WANTS. Compare against maxScroll to see
      // whether the browser can actually honor it.
      extra.wantY = el ? +(el.getBoundingClientRect().top + window.scrollY).toFixed(1) : null;
      extra.targetHidden = el ? el.classList.contains('hidden') : null;
    } catch (e) {
      extra.resolveError = String(e && e.message || e);
    }
    extra.by = caller();
    rec('_wizardRender-enter', extra);
    const result = orig.apply(this, args);
    rec('_wizardRender-exit', {id, y: window.scrollY,
        maxScroll: document.documentElement.scrollHeight - window.innerHeight});
    return result;
  };
  window._wizardRender.__wizardSpyWrapped = true;  // dump-time install marker
})();
"""


# ---------------------------------------------------------------------------
# INSTRUMENT (charter C-7), mode-C round 5 step 0 — ATTRIBUTE the growth.
#
# O-9 established that `scrollY` shifts by exactly the document's height
# growth (`dy == dh`). Round 4 then assumed that growth was the corpus card
# list and put `overflow-anchor: none` there — and was refuted (F-6). That
# assumption was never measured. This watches `documentElement.scrollHeight`
# on every frame and, on each CHANGE, snapshots which id'd elements are tall
# enough to account for it — so the +25054px is attributed to a real element
# instead of guessed at.
#
# Deliberately does not pre-name a suspect list (that would be scoping the
# instrument to the theory again); it reports every id'd element over a size
# floor and lets the numbers pick the culprit.
# ---------------------------------------------------------------------------
_HEIGHT_ATTRIBUTION_JS = r"""
(() => {
  if (typeof window.__scrollSpyRec !== 'function') {
    window.__heightAttrError = 'builtin spy missing — _SCROLL_SPY_JS must run first';
    return;
  }
  const rec = window.__scrollSpyRec;
  let last = -1;
  const snap = () => {
    const out = [];
    document.querySelectorAll('[id]').forEach(el => {
      const h = el.offsetHeight;
      if (h > 400) out.push([el.id, h]);
    });
    // Tallest first; only the top few can plausibly explain a 25000px jump.
    return out.sort((a, b) => b[1] - a[1]).slice(0, 6);
  };
  const tick = () => {
    const h = document.documentElement.scrollHeight;
    if (h !== last) {
      rec('height-change', {from: last, to: h, delta: last < 0 ? null : h - last, tall: snap()});
      last = h;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  window.__heightAttrInstalled = true;
})();
"""

# One evaluate, one round-trip: scroll position AND document geometry read at
# the same instant. The cross-item review (docs/dev/diagnosis/
# ux-scroll-flake-cross-item-review.md "## Falsification") found that no
# capture in the whole scroll-flake family ever logged scrollHeight at the
# moment of a before/after read -- the exact datum its transient-max-scroll-
# clamp hypothesis needs. Reading y and geometry in a single call keeps the
# probe shape identical to the bare `window.scrollY` read it replaces (Round 2
# of docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md observed an
# unexplained rate drop with the spy attached, so no extra round-trips).
_READ_SCROLL_STATE_JS = r"""
() => ({
  y: window.scrollY,
  sh: document.documentElement.scrollHeight,
  ih: window.innerHeight,
  cards: document.querySelectorAll('#corpusExperienceList .corpus-card').length,
})
"""

# Same shape as _READ_SCROLL_STATE_JS (one evaluate, geometry at the same
# instant as y — kept as a SEPARATE constant rather than widening that one,
# whose probe weight is calibrated for the contention test above per Round
# 2's rate-drop concern, docs/dev/diagnosis/
# ux-restore-scroll-y-resource-contention.md). Counts Compose cards, not
# corpus cards -- item 28 (docs/dev/diagnosis/
# ux-compose-reload-scroll-restore.md), the loadComposition() call site O-13
# never had ANY geometry read attached to it.
_READ_COMPOSE_SCROLL_STATE_JS = r"""
() => ({
  y: window.scrollY,
  sh: document.documentElement.scrollHeight,
  ih: window.innerHeight,
  cards: document.querySelectorAll('#composeList .compose-experience-card').length,
})
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
    # Only meaningful in tests that inject _WIZARD_RENDER_SPY_JS; stays silent
    # elsewhere (an un-injected hook reads as None, not as a failure) but shouts
    # if it WAS injected and did not take — the same "a dead spy must never read
    # as 'nothing happened'" rule the two checks above enforce.
    wizard_hook = page.evaluate(
        "() => (window._wizardRender && window._wizardRender.__wizardSpyWrapped)"
        "        ? 'ok' : (window.__wizardRenderSpyError || null)"
    )
    if wizard_hook and wizard_hook != "ok":
        print(
            f"\n[scroll-spy] phase={phase} -- WARNING: _wizardRender hook did "
            f"not install ({wizard_hook!r}); _wizardRender-enter/-exit events "
            f"are ABSENT below."
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
    specific card's on-screen position), and assert the position survives.

    INSTRUMENT (charter C-7, fix/ux-compose-reload-scroll-restore, item 28 --
    docs/dev/diagnosis/ux-compose-reload-scroll-restore.md). This test had NO
    scroll-mutation visibility at all (O-13's single historical failure,
    before=400 after=796, carries no geometry or spy data). Reusing the same
    spy suite the O-10/O-12/O-14 test above already uses, per the same
    load-order rule (_SCROLL_SPY_NAMED_HOOKS_JS / _WIZARD_RENDER_SPY_JS /
    _HEIGHT_ATTRIBUTION_JS must be injected via page.evaluate AFTER load,
    never add_init_script -- see the comment above _SCROLL_SPY_NAMED_HOOKS_JS).
    _wizardRender's smooth scrollIntoView (app.js:7093-7095) is the ungated
    writer item 29 proved for a different call site; it is NOT gated by
    either of item 29's fixes on this path (dossier's '## Observed') -- the
    wizard-render spy is included so a live invocation would show directly in
    the timeline rather than being inferred after the fact.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(8):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)

    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_WIZARD_RENDER_SPY_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open()

    page.evaluate("() => window.scrollTo(0, 400)")
    before_read = page.evaluate(_READ_COMPOSE_SCROLL_STATE_JS)
    before = before_read["y"]
    assert before > 0, (
        f"test setup didn't actually scroll the page -- geometry at read: {before_read}"
    )

    page.evaluate("() => loadComposition()")
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=15_000)
    # _restoreScrollY runs on a requestAnimationFrame after the terminal
    # render — give the browser one frame to paint before reading it back.
    page.wait_for_timeout(100)
    after_read = page.evaluate(_READ_COMPOSE_SCROLL_STATE_JS)
    after = after_read["y"]
    print(
        f"\n[compose-reload-scroll] before={before} after={after} "
        f"before_read={before_read} after_read={after_read}"
    )
    # Durable under -n2 (pytest-xdist doesn't reliably forward a PASSING
    # test's stdout) -- written only after BOTH reads, so it cannot shift
    # their timing. Same pattern as the O-10/O-12/O-14 test above.
    read_log = os.environ.get("SCROLL_READ_LOG")
    if read_log:
        with open(read_log, "a", encoding="utf-8") as fh:
            fh.write(f"compose-reload before_read={before_read} after_read={after_read}\n")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "compose-reload-after", after, before)
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
    # Mode-C round 2 (C-7): same post-load-before-select window as the named
    # hooks above — wizardInit()'s _wizardRender() can't fire until select()
    # runs, so this is the last moment the wrapper can be in place for it.
    page.evaluate(_WIZARD_RENDER_SPY_JS)
    # Round 5 step 0 (C-7): attribute the +25054px growth to a real element
    # rather than assuming it — round 4 assumed the corpus list and was
    # refuted (F-6) partly on that unmeasured assumption.
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
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


@pytest.mark.ux
@pytest.mark.xfail(
    reason=(
        "O-15 + F-7 (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md). Two reasons, "
        "and the second is why this is not merely a flaky test: (1) F-7 established the "
        "wizard rail is not involved in mode C at all — instrumenting the REAL test found "
        "exactly one _wizardRender call in 6/6 runs, always early, and the 300->369 "
        "signature is a height-tracking shift, not a scroll to #panelJD. So this asserts "
        "a property of a NON-mechanism. (2) O-15: this instrument passes locally 5/5 but "
        "fails on CI 3/3 with NEGATIVE drift (300->245), so its assertion is "
        "environment-dependent — which is itself the finding, not a defect to tune away. "
        "strict=False so BOTH outcomes are legal and the test keeps RUNNING on every CI "
        "run: its xfail/xpass status is the live signal that caught the CI-vs-local "
        "divergence in the first place, and that signal is the reason this is marked "
        "rather than deleted. DO NOT 'fix' this by widening a tolerance or pinning the "
        "number — if the question needs answering, re-run it sampling `h` at both ends, "
        "on both environments."
    ),
    strict=False,
)
def test_wizard_render_smooth_scroll_creeps_explicit_baseline(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-7 INSTRUMENT for scroll-flake "mode C" (the last of four failure
    modes of test_corpus_reload_preserves_scroll_position above; modes A/B/D
    were fixed on fix/ux-scroll-position-flake -- see docs/dev/diagnosis/
    ux-scroll-position-flake.md "## The fix" -- and are structurally
    unrelated to this one, Inferred Sec3 there).

    Isolates whether `_wizardRender`'s own `scrollIntoView({behavior:
    'smooth'})` (app.js:7093-7095, fired by `wizardInit()` -- app.js:6969 --
    which `onUserSelect()` -- app.js:451 -- calls as its LAST statement,
    itself the tail of an async chain: loadConfig -> _landingTab ->
    _activateTab -> refreshApplications -> _loadPersonaOptions ->
    wizardInit) can still be mid-animation when an UNRELATED later explicit
    `window.scrollTo()` sets a baseline -- and whether that baseline then
    drifts, with ZERO corpus reload / refreshCorpus() / _captureScrollY /
    _restoreScrollY involved anywhere in this test. This rules out any
    interaction with the already-fixed capture/restore primitives entirely:
    if this fails, the defect is proven to live in the wizard-render /
    native-smooth-scroll path alone.

    UserPickerPage.select() only waits for `#userSelect.value` to update --
    fired SYNCHRONOUSLY by the native `change` event -- not for
    onUserSelect()'s own async chain (and therefore not for wizardInit()) to
    complete. So instead of guessing a wall-clock delay (which is exactly
    what made the original failure CPU-load-dependent, ~12-17%/attempt), this
    synchronizes on the scroll spy actually observing the wizard's own
    `scrollIntoView` call fire -- deterministic w.r.t. WHEN the race window
    opens, not IF it opens. No CPU saturation needed.

    Falsification (charter C-7): if `after == before`, the wizard's animation
    was NOT still live at this synchronization point and mode C's attributed
    mechanism is at least incomplete as stated -- widen the instrument,
    report, do not fix on this basis alone. If `after != before`, the
    mechanism is confirmed at its simplest possible reproduction.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)

    UserPickerPage(page, live_server).select("alice")
    # No tab click, no refreshCorpus call anywhere in this test -- isolates
    # wizardInit()'s own _wizardRender() scrollIntoView as the sole actor.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )

    page.evaluate("() => window.scrollTo(0, 300)")
    before = page.evaluate("() => window.scrollY")
    if before <= 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "wizard-only-before", before)
    assert before > 0, "test setup didn't actually scroll the page"

    page.wait_for_timeout(100)  # give any in-flight animation frame(s) a chance to land
    after = page.evaluate("() => window.scrollY")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "wizard-only-after", after, before)
    assert after == before, (
        f"_wizardRender's own scrollIntoView (app.js:7093-7095) creeps an "
        f"unrelated later baseline with ZERO refreshCorpus / corpus-reload "
        f"involvement: {before} -> {after}. Confirms mode C is a pure "
        f"wizard-render / native-smooth-scroll race, structurally "
        f"independent of _captureScrollY/_restoreScrollY (docs/dev/"
        f"diagnosis/ux-scroll-wizard-rail-flake.md)."
    )


@pytest.mark.ux
@pytest.mark.xfail(
    reason=(
        "F-4 (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md): this instrument "
        "forces an ordering the REAL test never takes. Instrumenting "
        "test_corpus_reload_preserves_scroll_position showed exactly ONE _wizardRender "
        "call in 6/6 runs, always ~500ms BEFORE the baseline — there is no second call "
        "and no late call in the wild. The behavior asserted here is real browser "
        "behavior but is NOT mode C, so its outcome is not a gate signal (the dossier's "
        "'## Acceptance bar' says so explicitly). Kept as negative-space coverage rather "
        "than deleted: it is the evidence that killed the late-render theory. "
        "strict=False because the underlying effect reproduces ~9/10, not 10/10, so it "
        "may legitimately xpass."
    ),
    strict=False,
)
def test_wizard_render_firing_after_baseline_creeps_it(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-7 INSTRUMENT, second experiment for mode C -- forces the OPPOSITE
    ordering from test_wizard_render_smooth_scroll_creeps_explicit_baseline
    above, after that test's own captured spy dump falsified the ordering it
    assumed (see docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md O-1/O-2):
    there, wizardInit()'s scrollIntoView fired ~61ms BEFORE this test's own
    `scrollTo(0, 300)`, and the explicit scrollTo cleanly CANCELLED the
    in-flight smooth animation with zero drift. That is the opposite of what
    a "residual, still-settling" animation implies.

    This experiment tests the reverse: does a `_wizardRender()` call (the
    same real production function, app.js:7043, called directly the same way
    Chip 2's tests called `_captureScrollY`/`_restoreScrollY` directly)
    firing AFTER an explicit baseline is already established creep that
    baseline away? Rationale for trying this ordering: under CPU load,
    wizardInit()'s OWN async chain (onUserSelect -> loadConfig ->
    _landingTab -> ... -> wizardInit -> _wizardRender, app.js:394-451) could
    plausibly be delayed past the point the corpus test has already clicked
    the tab and established its own scrollTo(0,300) baseline -- i.e.
    late-arriving, not residual-from-earlier.

    CONFIRMED (O-2): with a 100ms read-delay (matching the real corpus
    test's own `page.wait_for_timeout(100)`) this did not reproduce in 5/5
    tries -- the ~69px animation (300 -> #panelJD's ~369) hadn't progressed
    far enough to register a *different* value yet, even though the spy
    still showed it in flight past the 100ms mark on inspection. Widening
    the read-delay to 350ms -- still well under the real test's own total
    elapsed time once `refreshCorpus()`'s corpus-card re-render/settle is
    counted -- reproduces deterministically: 4/5 runs failed with the same
    "before -> partial-target" shape mode C's own captured traces show
    (`300 -> 306`, `300 -> 309`, etc. -- never `300 -> 369` exactly, because
    a fresh 69px animation is caught at whatever point its 350ms window
    lands, not necessarily its end). This is the confirmed mechanism: mode C
    requires the wizard render's scrollIntoView to fire (or still be
    animating) AFTER the baseline is read, not merely be a residual
    animation from strictly before it.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)

    UserPickerPage(page, live_server).select("alice")
    # Let the FIRST (setup) scrollIntoView fully settle before this
    # experiment's own baseline -- isolates a SECOND, later-firing render
    # call as the sole variable, rather than confounding with the first.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )
    page.wait_for_timeout(500)  # generous settle window for the first animation

    page.evaluate("() => window.scrollTo(0, 300)")
    before = page.evaluate("() => window.scrollY")
    if before <= 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "reversed-order-before", before)
    assert before > 0, "test setup didn't actually scroll the page"

    # Fire a SECOND _wizardRender() call directly -- the real production
    # function, not a simulation -- immediately after the baseline is set.
    page.evaluate("() => _wizardRender()")

    # 350ms, not the real test's own 100ms: see O-2 in the docstring above --
    # a plain 100ms window under-catches this specific ~69px animation, but
    # the real corpus test's total elapsed time (refreshCorpus's own
    # card-re-render/settle, which this isolated instrument deliberately
    # doesn't call) plausibly provides the extra margin in the wild.
    page.wait_for_timeout(350)
    after = page.evaluate("() => window.scrollY")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "reversed-order-after", after, before)
    assert after == before, (
        f"a _wizardRender() call (app.js:7043) firing AFTER an explicit "
        f"baseline creeps that baseline away within a 350ms read window: "
        f"{before} -> {after}. Confirms mode C's mechanism requires the "
        f"wizard render to fire LATE (after the baseline is set), not "
        f"merely be a residual animation from before it (docs/dev/"
        f"diagnosis/ux-scroll-wizard-rail-flake.md)."
    )


@pytest.mark.ux
@pytest.mark.parametrize("settle_before_growth", [True, False], ids=["settled", "tight"])
def test_merge_suggestions_growth_shifts_scroll_deterministically(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    settle_before_growth: bool,
) -> None:
    """C-7 PROBE for mode C, round 5 step 1 -- a MEASURING DEVICE, not an
    acceptance signal (see the dossier's "## Acceptance bar"; F-4 is what
    that distinction cost).

    Round 4 could not measure its own fix: the mechanism fires in roughly 1
    run in 6, so a 5-run arm (1/6 control vs 1/5 fixed) was evidence of
    neither improvement nor harm. This forces the SAME ordering the wild
    failures take -- document growth landing after a baseline is already
    established -- so a candidate fix can be A/B'd against a signal that
    fires every run instead of one in six.

    Admissible as an instrument only because the ordering it forces is
    directly OBSERVED in the wild (dossier O-6: control run1 and fix run4
    both captured it), and because it drives the REAL production render path
    (`refreshMergeSuggestions`, app.js:5253) rather than simulating growth.

    What round 5 step 0 established (dossier O-12), and why this test targets
    merge suggestions rather than the corpus cards: the +25054px that moves
    the scroll is `#mergeSuggestionsList` (24956px), NOT
    `#corpusExperienceList` (1308px, which never grows). Round 4 placed
    `overflow-anchor: none` on the corpus list -- an element that does not
    grow -- which is part of why it was refuted (F-6). The growth sits ABOVE
    the corpus cards in the DOM (templates/index.html:739 vs :841), the
    classic "content inserted above the anchor pushes scroll down" shape.

    Reports `dy` vs `dh` rather than a bare pass/fail, because O-9's finding
    is an EQUALITY (`dy == dh` at +69 and at +25054), and an equality is a
    far stronger signal than "the number changed."
    """
    cid = seed_user(ux_app, "alice")
    # 20 near-identical companies -> the duplicate-role scorer emits a large
    # pairwise suggestion set; that volume is what makes the growth ~25000px.
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")

    # Let onUserSelect's async chain finish BEFORE clicking the tab. select()
    # only waits for #userSelect.value (set synchronously by the native change
    # event), so without this the chain's own _landingTab() can land after our
    # click and switch the tab back out from under the probe — observed once as
    # a `dh=+0 (1206 -> 1206)` self-guard trip, the tailor tab's height. The
    # wizard's scrollIntoView is the chain's last observable act (app.js:451 ->
    # wizardInit -> _wizardRender), so the spy seeing it means the chain is done.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )

    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(20, timeout=15_000)
    # Wait for the suggestions to actually RENDER, then for the document
    # height to stop moving. O-7: card attachment and layout height are
    # different events, and gating on the former is what lets ~25000px of
    # layout land after a baseline is set.
    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    page.wait_for_function(
        """() => {
             const h = document.documentElement.scrollHeight;
             const stable = window.__probeLastH === h;
             window.__probeLastH = h;
             return stable;
           }""",
        timeout=15_000,
    )

    # Collapse the section back to its pre-render state so its growth can be
    # re-triggered ON DEMAND. This is the only synthetic step, and it only
    # undoes a render -- the growth itself is then produced by the real
    # production function below, not by injected filler.
    page.evaluate(
        """() => {
             const list = document.getElementById('mergeSuggestionsList');
             const sec = document.getElementById('mergeSuggestionsSection');
             while (list.firstChild) list.removeChild(list.firstChild);
             sec.classList.add('hidden');
           }"""
    )
    page.wait_for_timeout(150)

    # ROUND 6, single-variable arm (dossier O-13/O-14): how long after the
    # baseline scroll the growth lands. In the wild failure the growth landed
    # ~110ms after the baseline, WHILE it was still settling; the original
    # "settled" probe let ~620ms elapse and never fired. These two ids differ
    # in that one variable and nothing else, so a difference between them
    # attributes cleanly.
    if settle_before_growth:
        page.evaluate("() => window.scrollTo(0, 300)")
        page.wait_for_timeout(150)  # let the baseline fully settle
        before = page.evaluate("() => window.scrollY")
        h_before = page.evaluate("() => document.documentElement.scrollHeight")
    else:
        # Scroll, sample, and kick the growth in ONE evaluate — no Playwright
        # round-trips in between — so the render lands as early after the
        # scroll as the fetch allows.
        before, h_before = page.evaluate(
            """() => {
                 window.scrollTo(0, 300);
                 const y = window.scrollY;
                 const h = document.documentElement.scrollHeight;
                 refreshMergeSuggestions({ limit: 1000 });   // deliberately NOT awaited here
                 return [y, h];
               }"""
        )
    assert before > 0, "probe setup didn't actually scroll the page"

    # Re-render through the REAL production path (app.js:5253). Playwright
    # awaits the returned promise, so the fetch + render have completed.
    # In the "tight" arm this is a second, idempotent call — the first was
    # already kicked above; this one just guarantees a settled end state.
    # { limit: 1000 } here (and above) is deliberate, not a default: ledger
    # item 11 (docs/dev/diagnosis/merge-suggestions-render-cap.md) capped
    # refreshMergeSuggestions()'s default render to a page at a time, which
    # would drop this fixture's single-call growth below the dh > 10_000 probe
    # floor below on totally unrelated grounds. The explicit override
    # preserves this test's exact single-call, full-growth timing model.
    page.evaluate("() => refreshMergeSuggestions({ limit: 1000 })")
    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    page.wait_for_timeout(200)

    after = page.evaluate("() => window.scrollY")
    h_after = page.evaluate("() => document.documentElement.scrollHeight")
    dy, dh = after - before, h_after - h_before

    if dy != 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "merge-growth-probe", after, before)
    # Guards the probe itself: if the growth didn't happen, a dy of 0 proves
    # nothing and must NOT read as "the bug is fixed" (the exact way a dead
    # instrument lies -- see _dump_scroll_spy's own liveness checks).
    assert dh > 10_000, (
        f"PROBE DID NOT ARM: expected the merge-suggestions re-render to grow "
        f"the document by ~25000px, got dh={dh:+} ({h_before} -> {h_after}). "
        f"A dy of {dy:+} here is meaningless -- fix the probe, do not read "
        f"this as a result."
    )
    assert dy == 0, (
        f"scroll-anchoring shift reproduced deterministically: "
        f"y {before} -> {after} (dy={dy:+}) while scrollHeight "
        f"{h_before} -> {h_after} (dh={dh:+}); dy==dh is {dy == dh}. "
        f"Growth is #mergeSuggestionsList, ABOVE the corpus cards in the DOM. "
        f"See docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md O-9/O-12."
    )


@pytest.mark.ux
def test_merge_suggestions_append_with_no_preceding_shrink_shifts_scroll(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round 6 arm B (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md O-16)
    -- a MEASURING DEVICE, not an acceptance signal, same caveat as the
    growth probe above.

    Every prior probe (round 5 step 1, round 6 arm A above) clears
    `#mergeSuggestionsList` to empty and re-renders the FULL set -- a
    synthetic `-N` shrink immediately before the growth that the wild
    failure never has (O-13 lists this as one of three untested candidate
    discriminators). This probe never shrinks the list: page 1 renders once
    (the FIRST-ever render of the section, same as the wild scenario), then
    a real "Show more" click appends page 2 through the production
    `_loadMergeSuggestionsPage` path (`app.js`, ledger item 11's pagination
    fix) -- a pure growth event, nothing emptied first.
    """
    cid = seed_user(ux_app, "alice")
    # 9 near-identical companies -> C(9,2)=36 pairs -> page 1 = 25 (the
    # default MERGE_SUGGESTIONS_PAGE_SIZE), page 2 = 11. Same near-duplicate
    # shape as the growth probe above, just enough companies to guarantee a
    # second page exists.
    for i in range(9):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")

    # Same chain-completion wait as the growth probe above -- see its own
    # comment for why (_landingTab() can otherwise switch the tab back out
    # from under this probe's click).
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )

    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(9, timeout=15_000)

    # Wait for page 1's FIRST-ever render -- no clear, no shrink, unlike
    # every prior probe.
    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    more_btn = page.locator("#mergeSuggestionsMoreBtn")
    expect(more_btn).to_be_visible(timeout=15_000)
    page.wait_for_function(
        """() => {
             const h = document.documentElement.scrollHeight;
             const stable = window.__probeLastH === h;
             window.__probeLastH = h;
             return stable;
           }""",
        timeout=15_000,
    )

    before, h_before = page.evaluate(
        """() => {
             window.scrollTo(0, 300);
             const y = window.scrollY;
             const h = document.documentElement.scrollHeight;
             return [y, h];
           }"""
    )
    assert before > 0, "probe setup didn't actually scroll the page"

    # The append itself -- fires the real production onclick handler
    # (app.js's `more.onclick`, the same "Show more" path a user's click
    # would run) via page.evaluate rather than Playwright's Locator.click(),
    # which auto-scrolls the target into view BEFORE clicking and would
    # contaminate `dy` with a second, unrelated scroll source (confirmed:
    # an earlier version of this probe using .click() measured dy=+2995 for
    # dh=+1400, dy > dh, impossible under pure anchoring -- Playwright's
    # own scroll-into-view was moving the page, not the app).
    page.evaluate("() => document.getElementById('mergeSuggestionsMoreBtn').click()")
    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount >= 36",
        timeout=15_000,
    )
    page.wait_for_timeout(200)

    after = page.evaluate("() => window.scrollY")
    h_after = page.evaluate("() => document.documentElement.scrollHeight")
    dy, dh = after - before, h_after - h_before

    if dy != 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "arm-b-append-no-shrink", after, before)
    # Guards the probe itself, same as the growth probe above -- a dy of 0
    # proves nothing if the append didn't actually grow the page.
    assert dh > 500, (
        f"PROBE DID NOT ARM: expected the 'Show more' click to append page 2 "
        f"(~11 cards) and grow the document meaningfully, got dh={dh:+} "
        f"({h_before} -> {h_after}). A dy of {dy:+} here is meaningless -- "
        f"fix the probe, do not read this as a result."
    )
    assert dy == 0, (
        f"scroll-anchoring shift reproduced WITHOUT a preceding shrink: "
        f"y {before} -> {after} (dy={dy:+}) while scrollHeight "
        f"{h_before} -> {h_after} (dh={dh:+}); dy==dh is {dy == dh}. "
        f"Arm B (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md, round 6) "
        f"reproduces the shift -- the preceding shrink in prior probes was "
        f"not required for anchoring to fire."
    )


@pytest.mark.ux
def test_merge_suggestions_growth_during_active_restore_loop_shifts_scroll(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round 6 arm C (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md O-17)
    -- a MEASURING DEVICE, not an acceptance signal, same caveat as the
    growth probe above.

    Every prior probe calls `refreshMergeSuggestions()` standalone, so no
    `_captureScrollY`/`_restoreScrollY` (app.js:5628-5657) settle loop is
    ever running while the growth lands. In the wild failing run the
    dossier captured, that rAF loop was still actively ticking around the
    baseline moment (O-13's third listed candidate). This probe starts the
    REAL production loop itself (`_captureScrollY()` + `_restoreScrollY()`,
    called by name -- both are top-level function declarations, genuine
    window globals) right before firing the merge-suggestions growth, so
    the loop is genuinely active rather than never running at all.

    Everything else matches round 5/6A's probe exactly (same clear-then-
    full-regrow shape via `{ limit: 1000 }`, same ~25000px magnitude) --
    single-variable arm: only "is the loop active" differs.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    # A small, deliberate delay on the SECOND merge-suggestions request (the
    # probe's own triggered growth, not the initial page load) so its
    # arrival reliably lands inside the loop's short active window (it exits
    # after SCROLL_RESTORE_STABLE_TICKS=4 stable rAF ticks, ~64ms at 60fps,
    # once nothing else is growing) rather than racing real fetch latency,
    # which on this local threaded test server often beats that window.
    # Test-side only, via Playwright route interception -- no production/
    # Flask code touched. Counts requests so only the probe's own call (the
    # second one) is delayed, not the initial page-load fetch.
    request_count = {"n": 0}

    def _delay_second_request(route):
        request_count["n"] += 1
        if request_count["n"] >= 2:
            time.sleep(0.03)
        route.continue_()

    page.route("**/corpus/merge-suggestions*", _delay_second_request)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")

    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(20, timeout=15_000)

    # Let the FIRST (undelayed) page-load render settle fully -- this test's
    # variable is the SECOND, deliberately triggered growth below.
    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    page.wait_for_function(
        """() => {
             const h = document.documentElement.scrollHeight;
             const stable = window.__probeLastH === h;
             window.__probeLastH = h;
             return stable;
           }""",
        timeout=15_000,
    )
    # Collapse back to empty, same synthetic step round 5/6A's probe uses --
    # arm C's variable is the active loop, not the shrink (that's arm B,
    # above); reusing the collapse keeps this single-variable against the
    # ORIGINAL probe.
    page.evaluate(
        """() => {
             const list = document.getElementById('mergeSuggestionsList');
             const sec = document.getElementById('mergeSuggestionsSection');
             while (list.firstChild) list.removeChild(list.firstChild);
             sec.classList.add('hidden');
           }"""
    )
    page.wait_for_timeout(150)

    before, h_before = page.evaluate(
        """() => {
             window.scrollTo(0, 300);
             const y = window.scrollY;
             const h = document.documentElement.scrollHeight;
             // Start the REAL production settle loop right before firing
             // the (deliberately delayed) growth, so it is genuinely
             // active/ticking when the merge-suggestions response lands.
             const capture = _captureScrollY();
             _restoreScrollY(capture);
             refreshMergeSuggestions({ limit: 1000 });   // NOT awaited
             return [y, h];
           }"""
    )
    assert before > 0, "probe setup didn't actually scroll the page"

    page.wait_for_function(
        "() => (document.getElementById('mergeSuggestionsList') || {}).childElementCount > 0",
        timeout=15_000,
    )
    page.wait_for_timeout(300)  # comfortably past the loop's own settle window

    after = page.evaluate("() => window.scrollY")
    h_after = page.evaluate("() => document.documentElement.scrollHeight")
    dy, dh = after - before, h_after - h_before

    if dy != 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "arm-c-active-restore-loop", after, before)
    assert dh > 10_000, (
        f"PROBE DID NOT ARM: expected the merge-suggestions re-render to grow "
        f"the document by ~25000px, got dh={dh:+} ({h_before} -> {h_after}). "
        f"A dy of {dy:+} here is meaningless -- fix the probe, do not read "
        f"this as a result."
    )
    assert dy == 0, (
        f"scroll-anchoring shift reproduced WITH an active _restoreScrollY "
        f"loop: y {before} -> {after} (dy={dy:+}) while scrollHeight "
        f"{h_before} -> {h_after} (dh={dh:+}); dy==dh is {dy == dh}. "
        f"Arm C (docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md, round 6) "
        f"reproduces the shift -- an active settle loop does not prevent it."
    )


@pytest.mark.ux
def test_restore_scroll_y_loses_to_post_restore_growth(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chip 2 deterministic falsification, FLIPPED to a Chip 3 regression test
    once the fix landed (charter C-7; diagnosis dossier O-9's mechanism,
    distilled to its essential shape, docs/dev/diagnosis/ux-scroll-position-
    flake.md "## The fix"). Calls the REAL _captureScrollY / _restoreScrollY
    primitives (app.js:5600-5657) directly, then schedules a synthetic
    page-growth (a tall filler prepended to <body>, matching O-6's "content
    inserted above the anchor pushes scroll down" scroll-anchoring shape) in
    the animation frame immediately AFTER _restoreScrollY's own first rAF --
    the exact ordering O-9 observed in the wild (id=1's fire-and-forget
    children still growing the page after id=1's own restore had already
    fired and exited). Ordering is forced by rAF registration order
    (same-frame callbacks fire in the order requestAnimationFrame was
    called), not by wall-clock timing, so this reproduces deterministically
    with no CPU saturation and no lottery -- isolating whether the
    capture/restore PRIMITIVE itself is defenseless against post-restore
    growth, independent of which real app feature (summary variants, skills
    editor, etc.) causes that growth in production. Pre-fix this asserted
    `after != before` (proving the defect, 3/3). Post-fix the settle loop
    (mechanism #3 in "## The fix") must survive this exact growth within its
    stability/timeout budget, so the assertion below is now `after == before`
    -- a regression in either the ordinal/generation checks or the settle
    loop itself will flip this back to red.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    # Wait out the tab-click's OWN fire-and-forget refreshCorpus (the real O-9
    # "id=1") before establishing this test's baseline -- otherwise this test's
    # own scrollTo(0,300) can itself race id=1's stale _restoreScrollY (the O-10
    # mechanism), which is a DIFFERENT experiment than the one this test runs.
    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    UserPickerPage(page, live_server).select("alice")
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(20, timeout=15_000)
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'refreshCorpus-exit')",
        timeout=15_000,
    )
    page.wait_for_timeout(150)  # let id=1's _restoreScrollY rAF actually fire before proceeding

    page.evaluate("() => window.scrollTo(0, 300)")
    before = page.evaluate("() => window.scrollY")
    assert before > 0, "test setup didn't actually scroll the page"

    page.evaluate(
        r"""
        () => {
          const y = _captureScrollY();
          _restoreScrollY(y);  // registers rAF #1: scrollTo(0, y)
          requestAnimationFrame(() => {  // same frame batch, fires AFTER rAF #1
            const filler = document.createElement('div');
            filler.style.height = '20000px';
            filler.id = '__chip2FillerAboveScroll';
            document.body.insertBefore(filler, document.body.firstChild);
          });
        }
        """
    )
    page.wait_for_timeout(150)
    filler_present = page.evaluate("() => !!document.getElementById('__chip2FillerAboveScroll')")
    after = page.evaluate("() => window.scrollY")
    print(f"\n[chip2-experiment] before={before} after={after} filler_present={filler_present}")
    assert filler_present, "growth trigger didn't fire -- experiment invalid, not a defect finding"
    assert after == before, (
        f"the settle loop did not survive post-restore growth: scroll position "
        f"moved from {before} to {after}. Mechanism #3 (docs/dev/diagnosis/"
        f"ux-scroll-position-flake.md '## The fix') should keep re-asserting the "
        f"restored position until scrollHeight stabilizes -- this is a regression."
    )


@pytest.mark.ux
def test_restore_scroll_y_stale_invocation_overwrites_later_scroll(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chip 2 deterministic falsification, FLIPPED to a Chip 3 regression test
    once the fix landed -- the mode-A/B shape (diagnosis dossier O-8: a
    `_restoreScrollY` scheduled by an EARLIER, already-stale refreshCorpus
    invocation fires AFTER a legitimate later scroll and stomps it), forced
    deterministically instead of relying on CPU-load timing. Holds the
    tab-click's own fire-and-forget refreshCorpus (the real O-9 "id=1") open
    at its /experiences fetch -- so it has captured scrollY (near 0, the
    pre-scroll baseline) but not yet reached _restoreScrollY -- then sets the
    scroll position a real user/test actually wants, THEN releases the held
    fetch so id=1 completes and fires its now-stale restore. Same root defect
    as the post-restore-growth test above, from the opposite direction:
    capture/restore had no concept of "have I been superseded," so an old
    invocation's restore won just by finishing last, regardless of what
    happened in the meantime. Pre-fix this asserted `after != before`
    (proving the defect, 3/3). Post-fix (docs/dev/diagnosis/ux-scroll-
    position-flake.md "## The fix", mechanism #2 -- this test's own
    scrollTo(0,300) below is one of the wrapped explicit scroll APIs, so it
    bumps the generation counter, and id=1's later, now-stale restore sees
    the mismatch on its first tick and abandons before ever calling scrollTo)
    the assertion below is now `after == before` -- a regression in that
    mechanism will flip this back to red.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    # INSTRUMENT (charter C-7, fix/ux-restore-scroll-y-resource-contention):
    # this test had NO scroll-mutation visibility at all -- reusing the same
    # spy suite sibling tests in this file already use, rather than building a
    # new one, per the current app.js _restoreScrollY (5637-5657): the
    # abandon check is `ordinal !== _scrollCaptureOrdinal || scrollGen !==
    # _scrollInterruptGen`, and this test's own scrollTo(0,300) below bumps
    # scrollGen BEFORE the stale fetch is ever released -- so the mismatch is
    # already established before _restoreScrollY is even scheduled, making
    # the abandon check's OWN timing not the obvious race window the
    # docstring above assumes. The mode-C/D scroll-anchoring reading this
    # comment originally floated for `after` well above `before` is FALSIFIED
    # (docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md: the anchoring
    # fix, 27d349b, predates every capture in the family); the live hypothesis
    # is a transient max-scroll clamp hit while the corpus DOM is still
    # mid-render, which is why both scroll reads below capture document
    # geometry (_READ_SCROLL_STATE_JS) at the same instant as y.
    page.add_init_script(_SCROLL_SPY_JS)

    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")

    # Hold open the FIRST /experiences fetch -- the tab click below fires
    # loadCorpusIfReady() -> refreshCorpus() fire-and-forget (real O-9
    # "id=1"), which captures scrollY (near 0, pre-scroll) at its own top
    # before awaiting this exact fetch.
    page.evaluate(
        r"""
        () => {
          const real = window.fetch;
          window.__releaseExperiencesFetch = null;
          window.fetch = (...a) => {
            const url = String(a[0] || '');
            if (url.includes('/experiences') && !window.__releaseExperiencesFetch) {
              const p = real(...a);
              return new Promise((resolve, reject) => {
                window.__releaseExperiencesFetch = () => p.then(resolve, reject);
              });
            }
            return real(...a);
          };
        }
        """
    )
    page.click("#topTabCorpus")
    page.wait_for_function(
        "() => typeof window.__releaseExperiencesFetch === 'function'", timeout=15_000
    )

    # id=1 is now suspended mid-refreshCorpus, holding its stale (near-0)
    # capture. Establish the position a real user/test actually wants.
    page.evaluate("() => window.scrollTo(0, 300)")
    before_read = page.evaluate(_READ_SCROLL_STATE_JS)
    before = before_read["y"]
    assert before > 0, (
        f"test setup didn't actually scroll the page (page too short?) -- "
        f"geometry at read: {before_read}"
    )

    # Release id=1: it completes, renders, and fires its OWN _restoreScrollY
    # with the stale value it captured before `before` was ever set.
    page.evaluate("() => window.__releaseExperiencesFetch()")
    page.wait_for_function(
        "() => document.querySelectorAll('#corpusExperienceList .corpus-card').length >= 20",
        timeout=15_000,
    )
    page.wait_for_timeout(150)  # let the stale _restoreScrollY's first tick run (and abandon)
    after_read = page.evaluate(_READ_SCROLL_STATE_JS)
    after = after_read["y"]
    print(
        f"\n[chip2-experiment-stale-restore] before={before} after={after} "
        f"before_read={before_read} after_read={after_read}"
    )
    # Under pytest-xdist a PASSING test's stdout is not reliably forwarded to
    # the master log, and the cross-item review's experiment needs pass-run
    # geometry too -- append it to a durable file when the campaign asks.
    # Written only after BOTH reads completed, so it cannot shift their timing.
    read_log = os.environ.get("SCROLL_READ_LOG")
    if read_log:
        with open(read_log, "a", encoding="utf-8") as fh:
            fh.write(f"stale-restore before_read={before_read} after_read={after_read}\n")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "stale-restore-after", after, before)
    assert after == before, (
        f"the stale invocation's restore was not correctly abandoned: it overwrote "
        f"the later scroll ({before} -> {after}). Mechanism #2 (docs/dev/diagnosis/"
        f"ux-scroll-position-flake.md '## The fix') should have detected the "
        f"generation mismatch and no-op'd -- this is a regression."
    )


# Geometry + tab-visibility read for the late-smart-landing repro below. Its
# extra fields (which tab is actually visible) are what distinguish "the
# corpus DOM grew" from "the select tail flipped the tab back to Tailor" --
# deliberately NOT added to _READ_SCROLL_STATE_JS, whose probe weight in the
# contention test above is calibrated (dossier Round 2's rate-drop concern).
_LANDING_REPRO_READ_JS = r"""
() => ({
  y: window.scrollY,
  sh: document.documentElement.scrollHeight,
  ih: window.innerHeight,
  cards: document.querySelectorAll('#corpusExperienceList .corpus-card').length,
  corpusVisible: (() => {
    const p = document.getElementById('panelCorpus');
    return !!(p && p.offsetParent !== null);
  })(),
  tailorHeight: (document.getElementById('tab-tailor') || {}).offsetHeight || 0,
})
"""


@pytest.mark.ux
def test_smart_landing_tail_defers_to_user_navigation(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic reproduction of the Round 3 RUN-9 capture (item 29) --
    no contention needed. The user-select handler (app.js ~:416-441) awaits
    loadConfig() then _landingTab() before applying `_activateTab(landing)`
    and `wizardInit()`; `_landingTab()` fetches /api/users/<u>/experiences
    (app.js:2490). Holding that FIRST /experiences fetch open suspends the
    tail exactly where `-n2` contention delays it naturally. The test then
    does what the O-10 contention failures' timelines show the harness doing:
    navigates to the Corpus tab (whose own refreshCorpus /experiences fetch
    passes through the one-shot hold untouched) and scrolls. Releasing the
    held fetch lets the stale tail run: observed in the RUN-9 spy timeline as
    _activateTab('tailor') re-flipping the visible tab (document height ->
    1206, the Tailor tab's height) and _wizardRender's
    scrollIntoView(#panelJD, {behavior:'smooth', block:'start'}) animating y
    toward the clamped maxScroll (306 = 1206-900; 273/291 are mid-flight
    samples of the same animation). Wanted behavior, asserted below: an
    explicit user navigation supersedes the async landing decision -- the
    Corpus tab stays visible and the scroll position holds.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)

    # One-shot hold on the FIRST /experiences fetch. Installed BEFORE the user
    # select, so it captures _landingTab()'s smart-landing fetch, not the
    # corpus tab's refreshCorpus fetch (same URL, later).
    page.evaluate(
        r"""
        () => {
          const real = window.fetch;
          window.__releaseExperiencesFetch = null;
          window.fetch = (...a) => {
            const url = String(a[0] || '');
            if (url.includes('/experiences') && !window.__releaseExperiencesFetch) {
              const p = real(...a);
              return new Promise((resolve, reject) => {
                window.__releaseExperiencesFetch = () => p.then(resolve, reject);
              });
            }
            return real(...a);
          };
        }
        """
    )
    # NOT UserPickerPage.select() -- item 31 (docs/dev/diagnosis/
    # ux-surgical-refinement-network-retry-flake.md) hardened it to wait for
    # onUserSelect's full cascade (UserPicker.SELECT_READY), which would
    # deadlock here: this test holds part of that same cascade
    # (_landingTab's /experiences fetch) open on purpose, by design, to
    # reproduce the exact suspended-tail state item 29 documented. Drives the
    # raw value-only wait select() used before that hardening instead.
    page.wait_for_selector(UserPicker.SELECT, timeout=15_000)
    page.select_option(UserPicker.SELECT, "alice")
    page.wait_for_function(
        "(u) => document.getElementById('userSelect').value === u",
        arg="alice",
        timeout=15_000,
    )
    page.wait_for_function(
        "() => typeof window.__releaseExperiencesFetch === 'function'", timeout=15_000
    )

    # The user's explicit navigation, while the select tail is suspended:
    # onto the Corpus tab, scrolled to 300.
    page.click("#topTabCorpus")
    page.wait_for_function(
        "() => document.querySelectorAll('#corpusExperienceList .corpus-card').length >= 20",
        timeout=15_000,
    )
    page.evaluate("() => window.scrollTo(0, 300)")
    page.wait_for_timeout(200)  # settle our own scroll (RUN 9 showed it lands ~75ms late)
    before_read = page.evaluate(_LANDING_REPRO_READ_JS)
    before = before_read["y"]
    assert before > 0 and before_read["corpusVisible"], (
        f"test setup failed -- expected a scrolled, visible Corpus tab before the "
        f"release; got {before_read}"
    )

    # Release the landing fetch: the suspended select tail now runs with its
    # stale decision. 700ms covers the smooth-scroll animation window (RUN 9:
    # release->final scroll-event was ~380ms).
    page.evaluate("() => window.__releaseExperiencesFetch()")
    page.wait_for_timeout(700)
    after_read = page.evaluate(_LANDING_REPRO_READ_JS)
    after = after_read["y"]
    print(
        f"\n[late-landing-repro] before={before} after={after} "
        f"before_read={before_read} after_read={after_read}"
    )
    read_log = os.environ.get("SCROLL_READ_LOG")
    if read_log:
        with open(read_log, "a", encoding="utf-8") as fh:
            fh.write(f"late-landing before_read={before_read} after_read={after_read}\n")
    if after != before or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "late-landing-after", after, before)
    assert after_read["corpusVisible"], (
        f"the select handler's stale smart-landing decision overrode the user's "
        f"explicit navigation: the Corpus tab was flipped back to Tailor after "
        f"release (tailorHeight={after_read['tailorHeight']}, sh={after_read['sh']})"
    )
    assert after == before, (
        f"the select tail's wizard render moved the scroll position the user set "
        f"({before} -> {after}, sh={after_read['sh']}): _wizardRender's smooth "
        f"scrollIntoView fired against a navigation it should have known was "
        f"superseded (see the dossier's Round 3 timeline)"
    )


@pytest.mark.ux
def test_tab_switch_cancels_inflight_smooth_scroll(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase-2 deterministic bench (item 29, dossier Round 3 R3-5/R3-6): an
    explicit tab switch must cancel any in-flight smooth-scroll animation --
    fixed-arm batch A showed a wizard smooth scroll launched legitimately
    BEFORE a navigation surviving it and moving the viewport afterward
    (`59 -> 0` / `59 -> 31`, no attributed API write). A choreographed repro of
    that exact contention ordering does not reproduce un-contended (3/3 pass:
    the animation completes before the read window opens -- consistent with the
    downward family appearing only under `-n2` load), so this bench removes
    timing entirely: launch a smooth scroll and call `switchTopTab` in the SAME
    JS task, guaranteeing the animation is in flight at switch time, then
    require the viewport to stay frozen. The target tab is Candidate memory,
    which -- unlike Corpus -- has no scroll capture/restore of its own
    (`_memoryTabActivated` only fetches and renders), so nothing masks a
    surviving animation's writes. The fix under test: `switchTopTab` cancels
    in-flight animations via the raw `_scrollRestoreNative` path (no
    interrupt-generation bump, so pending capture/restore semantics are
    untouched).
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    page.evaluate(_HEIGHT_ATTRIBUTION_JS)
    UserPickerPage(page, live_server).select("alice")

    # Let the select tail (and its own wizardInit smooth scroll) fully settle,
    # then normalize to a known position.
    page.wait_for_function(
        "() => (window.__scrollSpy || []).some(e => e.source === 'scrollIntoView')",
        timeout=15_000,
    )
    page.wait_for_timeout(1200)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(150)
    assert page.evaluate("() => window.scrollY") == 0, "bench setup: could not normalize y"

    # Same task: start a smooth scroll toward y=50 (small enough that no
    # tab-height clamp interferes: every tab's maxScroll here is >= 59), then
    # immediately switch tabs. The animation is in flight by construction --
    # zero timing sensitivity.
    page.evaluate(
        r"""
        () => {
          window.scrollTo({ top: 50, behavior: 'smooth' });
          switchTopTab('memory', document.getElementById('topTabMemory'));
        }
        """
    )
    # A 50px smooth scroll completes in well under 900ms; whatever survives
    # the switch has finished by now.
    page.wait_for_timeout(900)
    y = page.evaluate("() => window.scrollY")
    print(f"\n[tab-switch-cancel-bench] y_after_900ms={y}")
    if y != 0 or os.environ.get("SCROLL_SPY_ALWAYS"):
        _dump_scroll_spy(page, "tab-switch-cancel", y, 0)
    assert y == 0, (
        f"a smooth-scroll animation survived the explicit tab switch and moved "
        f"the viewport afterward (y={y}): switchTopTab must cancel in-flight "
        f"scroll animations (dossier Round 3 R3-5/R3-6)"
    )


@pytest.mark.ux
def test_restore_scroll_y_ordinal_defers_to_newer_capture(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chip 3 regression -- outcome-level proof of the invocation-ordinal
    mechanism (docs/dev/diagnosis/ux-scroll-position-flake.md, "## The fix").
    The Chip 1a self-check test_scroll_spy_attributes_overlapping_refresh_corpus_calls
    (below) forces the same two-overlapping-captures shape but only asserts the
    spy's attribution bookkeeping (`scheduledDuring`) -- never window.scrollY --
    so nothing before this test could catch a bug in the ordinal check itself
    (wrong variable, inverted comparison, off-by-one). Two captures in a row,
    a distinct position established via the `scrollTop` property setter
    (deliberately NOT window.scrollTo/scroll/scrollBy/scrollIntoView, so this
    isolates the ordinal check from the separate explicit-scroll-API
    generation check O-10 already exercises), restores the OLDER
    (now-superseded) capture LAST, and asserts it is a provable no-op.
    """
    cid = seed_user(ux_app, "alice")
    for i in range(20):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(20, timeout=15_000)
    page.wait_for_timeout(200)  # let the tab-click's own fire-and-forget refreshCorpus settle

    page.evaluate(
        r"""
        () => {
          window.__older = _captureScrollY();
          document.documentElement.scrollTop = 500;
          window.__newer = _captureScrollY();
        }
        """
    )
    newer_y = page.evaluate("() => window.__newer.y")
    assert newer_y > 0, "test setup didn't actually scroll the page"

    page.evaluate("() => _restoreScrollY(window.__newer)")
    page.wait_for_timeout(150)
    after_newer = page.evaluate("() => window.scrollY")
    print(f"\n[chip3-ordinal] newer_y={newer_y} after_newer={after_newer}")
    assert after_newer == newer_y, "the newer capture's own restore should hold"

    # Fire the OLDER, already-superseded capture's restore LAST. Its ordinal no
    # longer matches the current _scrollCaptureOrdinal (the newer capture
    # bumped it), so this must be a provable no-op.
    page.evaluate("() => _restoreScrollY(window.__older)")
    page.wait_for_timeout(150)
    after_older = page.evaluate("() => window.scrollY")
    print(f"\n[chip3-ordinal] after_older={after_older}")
    assert after_older == after_newer, (
        f"the OLDER, superseded capture's restore should have been a no-op "
        f"(stale ordinal) but scroll moved: {after_newer} -> {after_older}"
    )


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


# ---------------------------------------------------------------------------
# INSTRUMENT (charter C-7, board item 44). Forces the ONE ordering item 44's
# recorded CI timelines are consistent with but never actually pinned down:
# invocation 1's `_restoreScrollY-fired` record landing AFTER the timeline was
# cleared, so it is counted against the two invocations a later test tracks.
#
# Holds ONLY the first `_restoreScrollY` call's own rAFs, by swapping
# `requestAnimationFrame` for the synchronous body of that single call. Playwright's
# polling (`wait_for_function` polls on rAF) is scheduled outside that window and
# keeps its normal cadence — this instrument manipulates the RELATIVE ordering of
# the two, and slowing both equally would manipulate nothing.
#
# This models the degraded-frame-cadence regime a 4-core `ubuntu-latest` runner
# exhibits while running a threaded Flask server + headless Chromium + pytest at
# once, without depending on real load timing (the same "force it by construction
# rather than by luck" method that closed O-10/O-11 in
# docs/dev/diagnosis/ux-scroll-position-flake.md).
# ---------------------------------------------------------------------------
_RESTORE_HOLD_MS = 800
"""Wall-clock hold applied to invocation 1's restore rAFs by the item-44 probe.

Long enough to comfortably outlast the settle gate's clear round-trip (measured at
~140-250ms on this machine), short enough that the fixed gate — which waits the hold
out by design — stays far inside its own 15s timeout.
"""


_SCROLL_SPY_HOLD_FIRST_RESTORE_RAF_JS = r"""
(holdMs) => {
  const inner = window._restoreScrollY;
  if (!inner) { window.__holdFirstRestoreError = '_restoreScrollY missing at hold time'; return; }
  // Control-arm bookkeeping. A probe that asserts "nothing leaked" is worthless
  // unless it can also prove there was something to leak and that the forced
  // ordering was actually achieved — the O-4 inert-instrument trap in
  // docs/dev/diagnosis/ux-scroll-position-flake.md, where an uninvoked arrow
  // function made every dump read "0 events" for an entire session.
  window.__holdStats = {engaged: false, calls: 0, scheduledAt: null, releasedAt: null, ticks: 0};
  let armed = true;
  window._restoreScrollY = function (...a) {
    window.__holdStats.calls++;
    if (!armed) return inner.apply(this, a);
    armed = false;
    window.__holdStats.engaged = true;
    window.__holdStats.scheduledAt = performance.now();
    const realRaf = window.requestAnimationFrame.bind(window);
    // Wall-clock, not a frame count. Frame cadence is exactly the variable this
    // instrument cannot assume: headless Chromium was measured at ~11-13fps here,
    // where a 20-frame hold runs ~1.8s, while the same count is ~330ms at 60fps.
    // The hold has to reliably outlast the clear round-trip, so bound it in the
    // units the clear is measured in.
    window.requestAnimationFrame = (cb) => realRaf((ts) => {
      const until = performance.now() + holdMs;
      const step = (t2) => {
        window.__holdStats.ticks++;
        if (performance.now() >= until) {
          window.__holdStats.releasedAt = performance.now();
          cb(t2);
        } else { realRaf(step); }
      };
      step(ts);
    });
    try { return inner.apply(this, a); }
    finally { window.requestAnimationFrame = realRaf; }
  };
}
"""


def _settle_and_clear_spy_timeline(page: Page) -> None:
    """Wait out the Corpus tab click's own fire-and-forget ``refreshCorpus``, then
    clear the timeline — so that invocation is not conflated with the ones the
    calling test is actually examining.

    The gate this waits on is load-bearing, not incidental. ``refreshCorpus-exit``
    is NOT sufficient: ``_SCROLL_SPY_NAMED_HOOKS_JS``'s own header records that
    ``_restoreScrollY`` is a fire-and-forget ``requestAnimationFrame`` which
    ``refreshCorpus`` never awaits, so the invocation is marked closed "a full
    microtask-drain before the rAF actually fires". Clearing on ``-exit`` therefore
    leaves that invocation's ``_restoreScrollY-fired`` record still pending, free to
    land in the freshly-emptied timeline and be counted against a later test's
    invocations. That is board item 44.
    """
    page.wait_for_function(
        """() => {
          const spy = window.__scrollSpy || [];
          return spy.some(e => e.source === 'refreshCorpus-exit')
              && spy.some(e => e.source === '_restoreScrollY-fired');
        }""",
        timeout=15_000,
    )
    page.evaluate("() => { window.__clearAt = performance.now(); window.__scrollSpy = []; }")


@pytest.mark.ux
def test_settle_gate_clears_the_timeline_without_leaking_a_pending_restore(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-7 falsification probe for board item 44.

    Isolates the leak itself: no overlapping invocations, no assertions about
    ordering or attribution — just "after the settle gate clears the timeline, is
    the timeline actually clear, or does a restore scheduled before the clear still
    land after it?"

    Deliberately narrower than the test it explains
    (``test_scroll_spy_attributes_overlapping_refresh_corpus_calls``) so that a
    failure here cannot be confused with a supersede-guard or attribution defect:
    nothing in this test schedules a second capture, so ``_restoreScrollY``'s
    ordinal/scrollGen guard (``static/app.js:5703``) has nothing to supersede and
    cannot be implicated either way.
    """
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid, company="Company 0")
    install_llm_stubs(ux_app, monkeypatch)

    page.add_init_script(_SCROLL_SPY_JS)
    BasePage(page, live_server).load()
    page.evaluate(_SCROLL_SPY_NAMED_HOOKS_JS)
    UserPickerPage(page, live_server).select("alice")
    # Arm AFTER user-select and BEFORE the tab click, so the held call is
    # unambiguously the tab click's own fire-and-forget refreshCorpus (id 1).
    page.evaluate(_SCROLL_SPY_HOLD_FIRST_RESTORE_RAF_JS, _RESTORE_HOLD_MS)
    page.click("#topTabCorpus")
    page.wait_for_selector("#panelCorpus", state="visible", timeout=15_000)
    expect(page.locator("#corpusExperienceList .corpus-card")).to_have_count(1, timeout=15_000)

    _settle_and_clear_spy_timeline(page)

    # Comfortably longer than the 800ms hold, so a leaked record has certainly
    # landed by the time it is read. A pass here means "no record arrived", never
    # "the read was too early" — and the releasedAt control below proves which.
    page.wait_for_timeout(2_500)

    assert page.evaluate("() => window.__holdFirstRestoreError || null") is None
    stats = page.evaluate("() => window.__holdStats || null")
    clear_at = page.evaluate("() => window.__clearAt || null")
    timeline = page.evaluate("() => window.__scrollSpy || []")
    # Always dump, never only on failure: a silently-inert instrument reads
    # exactly like a genuine negative result otherwise (O-4).
    print(f"\n[item-44 probe] holdStats={stats} clearAt={clear_at}")
    print(f"[item-44 probe] post-clear timeline ({len(timeline)} events): {timeline}")

    # --- CONTROL ARM: prove the forced ordering actually happened ------------
    # Without these, `leaked == []` below passes vacuously whenever the hold
    # failed to engage — proving nothing while looking like a clean result.
    assert stats is not None, "hold instrument never installed — nothing was measured"
    assert stats["engaged"], (
        "the hold never engaged: _restoreScrollY was not called during the armed "
        f"window, so no restore was ever pending and this test proves nothing "
        f"about leakage: {stats}"
    )
    assert stats["releasedAt"] is not None, (
        f"the held rAF never ran — the hold outlived the test, so whether a record "
        f"would have leaked is untested, not disproven: {stats}"
    )
    assert clear_at is not None, "the settle gate never cleared the timeline"
    assert stats["releasedAt"] - stats["scheduledAt"] >= _RESTORE_HOLD_MS, (
        "the hold did not actually delay anything — the record was free to land "
        "before the clear on its own, so a clean result below would say nothing "
        f"about the gate: held for {stats['releasedAt'] - stats['scheduledAt']:.1f}ms, "
        f"expected >= {_RESTORE_HOLD_MS}ms"
    )
    # Deliberately NOT asserted: whether releasedAt precedes clearAt. That ordering
    # is exactly what the settle gate decides, and therefore what this test measures
    # rather than requires — asserting it would hard-code the pre-fix behaviour and
    # the test could never go green. Printed above for the record.

    # --- SUBJECT -------------------------------------------------------------
    leaked = _spy_events(page, "_restoreScrollY-fired")
    assert leaked == [], (
        "a _restoreScrollY scheduled BEFORE the timeline was cleared landed AFTER "
        f"it, leaving {len(leaked)} stale record(s) in a timeline the caller is "
        f"entitled to treat as empty: {leaked}"
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
    _settle_and_clear_spy_timeline(page)

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

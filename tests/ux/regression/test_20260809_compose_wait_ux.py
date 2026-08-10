"""Regression: sprint A2 (`feat/compose-wait-ux`) — the Compose arrival wait
gate, the labelled background chip, and two affordance fixes on the same surface.

What each test pins, and why it is not covered by an existing module:

- **#1 — the "Composing…" wait gate.** `wizardGoTo(3)` makes the Compose panel
  visible at the moment it *fires* `loadComposition()`, which is when the
  background volley (positioning draft → skills recommend → gap-fill → role
  intros) STARTS. The step therefore read as finished while its cards were still
  being torn down and rebuilt. A hold now spans that volley — the `_setBusy`
  banner plus an in-panel `#composePending` block on the analyze/generate
  streaming-panel idiom — and releases at the terminal render.
  `test_20260708_busy_states_and_chip.py` covers the banner half on the two
  clarify paths; this covers the in-panel block and the skip-to-compose path.
- **#2 — the chip now names the call.** `#composeBgChip` said "Updating
  suggestions…" for all five legs of the volley. `_markComposeBgReload` takes an
  optional label; the counter behind `data-compose-bg-pending` is unchanged, so
  the settle gate and the chip still read off one source of truth.
- **#3 — Skills pin/drop are word buttons.** They were 📌/📍 and ✕/↩ glyphs whose
  meaning lived in a `title` tooltip. The load-bearing half of this fix is in the
  TOGGLERS, not the renderer: both used to hand-write the glyph back on every
  click, so a renderer-only change would have been undone by the first toggle.
- **#4 — in-place Edit on every compose bullet.** It existed only on
  `is_pending_review` rows; every other suggested bullet required leaving the
  tailor flow for the Career Corpus tab.

LLM-free throughout (analyzer functions stubbed; the real Flask routes run).
Enumeration for the settle-contract half: docs/dev/blast-radius/compose-wait-ux.md.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page, Response, expect

from tests.ux import stubs as ux_stubs
from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardComposePage, WizardJobPage
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."

_HIDDEN = re.compile(r"(^|\s)hidden(\s|$)")
_SHOWING = re.compile(r"(^|\s)show(\s|$)")
_ON = re.compile(r"(^|\s)on(\s|$)")


def _delayed(fn: Callable[..., Any], seconds: float) -> Callable[..., Any]:
    """Wrap a stub so the (threaded) route handler sleeps before returning.

    Same idiom as `test_20260708_busy_states_and_chip.py` — kept local rather
    than imported so a rename there cannot silently disarm the delay here.
    """

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        time.sleep(seconds)
        return fn(*args, **kwargs)

    return _wrapped


def _seed_skills(candidate_id: int, names: list[str]) -> list[int]:
    from db.models import Skill
    from db.session import get_session

    s = get_session()
    try:
        ids: list[int] = []
        for i, name in enumerate(names):
            sk = Skill(
                candidate_id=candidate_id,
                name=name,
                display_order=i,
                is_active=1,
                is_pending_review=0,
                source="imported",
            )
            s.add(sk)
            s.flush()
            ids.append(sk.id)
        s.commit()
        return ids
    finally:
        s.close()


# Observe the wait block's own class attribute rather than sampling it: the
# volley can be sub-100ms against stubs, and a poll that misses the window would
# read exactly like "the hold was never raised" — the dead-instrument failure
# `_dump_scroll_spy` guards against in the sibling module.
_PENDING_SPY_JS = """
() => {
  window.__composePendingShown = 0;
  const el = document.getElementById('composePending');
  if (!el) { window.__composePendingSpyError = '#composePending missing'; return; }
  new MutationObserver(() => {
    if (!el.classList.contains('hidden')) window.__composePendingShown++;
  }).observe(el, { attributes: true, attributeFilter: ['class'] });
}
"""

# Record the chip's TEXT every time it mutates while visible, so the assertion
# is over the whole label sequence rather than whichever one happened to be up
# at a sampling instant.
_CHIP_LABEL_SPY_JS = """
() => {
  window.__chipLabels = [];
  const chip = document.getElementById('composeBgChip');
  if (!chip) { window.__chipLabelSpyError = '#composeBgChip missing'; return; }
  new MutationObserver(() => {
    if (!chip.classList.contains('hidden')) {
      window.__chipLabels.push((chip.textContent || '').trim());
    }
  }).observe(chip, { attributes: true, childList: true, characterData: true, subtree: true });
}
"""


@pytest.mark.ux
@pytest.mark.slow
def test_composing_wait_gate_spans_the_arrival_volley_and_clears_at_settle(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1 — the in-panel wait block is up during the volley and down at settle.

    The release is deliberately synchronous and ordered BEFORE whichever DOM
    mutation makes `Compose.SETTLED` observable (see `_flushComposeSettleWaiters`
    in static/app.js), so `_wait_settled()` returning is itself the proof that the
    overlay is already gone — this is an ordering assertion, not a poll-until-quiet.
    """
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    page.evaluate(_PENDING_SPY_JS)
    assert page.evaluate("() => window.__composePendingSpyError || null") is None

    # open() clicks "Skip to Compose →" (wizardGoTo(3); skipClarifications())
    # and blocks on _wait_settled().
    WizardComposePage(page, live_server).open()

    assert page.evaluate("() => window.__composePendingShown") > 0, (
        "#composePending never became visible — the Composing… hold was not "
        "raised across the arrival volley"
    )
    # Settled: BOTH halves of the hold are down, and the terminal render is real.
    expect(page.locator(Compose.PENDING)).to_have_class(_HIDDEN)
    expect(page.locator(Compose.BUSY_BANNER)).not_to_have_class(_SHOWING)
    assert page.locator(Compose.SETTLED).count() == 1


@pytest.mark.ux
@pytest.mark.slow
def test_compose_bg_chip_names_the_call_in_flight(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#2 — the chip label is per-call, and the settle gate still agrees with it.

    The gap-fill leg is slowed (the same `_delayed` idiom the chip's original
    regression test uses) so its label is reliably on screen; the assertion is
    over the recorded sequence, so a fast leg cannot produce a false negative.
    """
    import analyzer

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    monkeypatch.setattr(
        analyzer, "draft_gap_fill_bullets", _delayed(ux_stubs.fake_draft_gap_fill_bullets, 0.4)
    )

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    page.evaluate(_CHIP_LABEL_SPY_JS)
    assert page.evaluate("() => window.__chipLabelSpyError || null") is None

    WizardComposePage(page, live_server).open()

    labels = page.evaluate("() => window.__chipLabels")
    assert labels, "the chip never became visible during the arrival volley"
    # At least one leg named itself rather than falling back to the generic text.
    assert any("gap" in label.lower() for label in labels), (
        f"the gap-fill leg did not label the chip; captured labels: {labels}"
    )
    # The chip and the settle gate still read off ONE counter: settled ⇒ hidden.
    expect(page.locator("#composeBgChip")).to_have_class(_HIDDEN)
    assert page.locator(Compose.SETTLED).count() == 1


@pytest.mark.ux
@pytest.mark.slow
def test_skills_pin_and_drop_are_word_buttons_that_survive_a_toggle(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#3 — words, not glyphs, in the renderer AND after a click.

    The second half is the point. Both togglers used to write the emoji back
    into `textContent` on every click, so a renderer-only change would render
    "Pin" once and then flip to 📌 the moment anyone used it.
    """
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    _seed_skills(cid, ["Python", "Kafka"])
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()
    compose.wait_skills_card()

    row = page.locator(Compose.SKILL_ROW, has_text="Python").first
    pin = row.locator(Compose.SKILL_PIN)
    drop = row.locator(Compose.SKILL_DROP)

    expect(pin).to_have_text("Pin")
    expect(drop).to_have_text("Drop")

    pin.click()
    expect(pin).to_have_text("Pinned")
    expect(pin).to_have_class(_ON)

    # Dropping clears the pin — and BOTH buttons must repaint as words.
    drop.click()
    expect(drop).to_have_text("Dropped")
    expect(drop).to_have_class(_ON)
    expect(pin).to_have_text("Pin")
    expect(pin).not_to_have_class(_ON)


@pytest.mark.ux
@pytest.mark.slow
def test_every_compose_bullet_has_in_place_edit(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#4 — Edit on a NON-pending compose bullet, persisting through the real PUT.

    The seeded bullets are `is_pending_review=0`, i.e. exactly the rows that had
    no Edit affordance before this sprint.
    """
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    compose = WizardComposePage(page, live_server).open()
    compose._wait_settled()

    bullet_list = page.locator(Compose.BULLET_LIST).first
    rows = bullet_list.locator(f":scope > {Compose.ROW}")
    expect(rows.first).to_be_visible()
    n_rows = rows.count()
    assert n_rows > 0, "no compose bullet rows rendered"
    # Every row carries Edit now — not just a pending-review subset (there are
    # none in this fixture, so pre-A2 this count was 0).
    assert bullet_list.locator(Compose.BULLET_EDIT).count() == n_rows, (
        f"{bullet_list.locator(Compose.BULLET_EDIT).count()} Edit buttons for "
        f"{n_rows} bullet rows — Edit is still gated on is_pending_review"
    )
    # ...and Approve is still pending-only (approving a non-proposal is a no-op).
    assert bullet_list.locator(Compose.BULLET_APPROVE).count() == 0

    new_text = "Cut Kubernetes p99 latency 40% across 12 services"
    first_row = rows.first
    first_row.locator(Compose.BULLET_EDIT).click()
    page.fill(Compose.FORM_MODAL_TEXT_INPUT, new_text)

    def _is_bullet_put(resp: Response) -> bool:
        return "/api/bullets/" in resp.url and resp.request.method == "PUT"

    with page.expect_response(_is_bullet_put) as put:
        page.click(Compose.FORM_MODAL_SUBMIT)
    assert put.value.ok, f"PUT /api/bullets returned {put.value.status}: {put.value.text()}"

    expect(first_row.locator(Compose.ROW_TEXT).first).to_have_text(new_text)

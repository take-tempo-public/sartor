"""Regression + instrument: item 20 — the Step-5 wizard rail must be hard-gated
on a frozen composition (`fix/wizard-rail-frozen-composition-gate`, Epic A).

**What was wrong.** `_wizardReachable` (static/app.js) gated every step from 2
upward on nothing but `lastContextPath`, so a user who analyzed and then clicked
Step 5 on the rail landed on Generate having never passed through Compose. With
no `approved_composition` on the context, `blueprints/generation.py`'s
`_frozen_composition` returns `None` and `/api/generate` runs the legacy full-LLM
`generate()` — the path the frozen-composition re-architecture retired for
corpus-mode users.

**The instrument is deliberately wider than that one step.** The truth-table test
below reads the reachability of ALL SIX rail buttons at three moments (after
analyze, after the freeze, and on a resumed application), rather than only the
step under suspicion — an instrument scoped to the hypothesis would have hidden
the rival this module also pins: `_compositionFrozen` is a session-only client
flag that a prior-application resume used to reset to `false` unconditionally, so
a naive client-side gate would have stranded a genuinely-frozen resumed
application at Step 6 with Generate greyed out.

Diagnosis dossier: docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md.

LLM-free throughout (analyzer functions stubbed; the real Flask routes run).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import (
    bundled_persona_id,
    seed_application,
    seed_exp_with_bullets,
    seed_run,
    seed_user,
    write_context_file,
)
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    PriorAppsPage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Compose, Output, Wizard

_JD = (
    "Senior Backend Engineer, Platform. Python on Postgres + AWS with Kafka "
    "as the event backbone. Lead architecture reviews; mentor a team of 6."
)

# The toast element `_toast()` lazily appends to <body> (static/app.js). Kept
# local rather than added to `ui_pages/selectors.py`: that file is a gated C-10
# surface and this module needs no new shared selector.
_TOAST = "#_corpusToast"

# Reads BOTH halves of the rail's state for every step in one round-trip: the
# predicate (`_wizardReachable`, a top-level function declaration, so it is on
# the page's global scope) and the rendered `disabled` attribute the user
# actually meets. Capturing both is the point — a predicate that says "no" while
# the button renders enabled is a distinct defect from either alone.
_RAIL_TRUTH_TABLE_JS = """
() => {
  const steps = {};
  for (let s = 1; s <= 6; s++) {
    const btn = document.querySelector(`button.wizard-step[data-wstep='${s}']`);
    steps[String(s)] = {
      reachable: _wizardReachable(s),
      disabled: btn ? btn.disabled : null,
      title: btn ? (btn.getAttribute('title') || '') : null,
    };
  }
  return {
    steps: steps,
    step: _wizardStep,
    frozen: _compositionFrozen,
    contextPath: !!lastContextPath,
    resumePath: !!lastResumePath,
  };
}
"""


def _rail(page: Page) -> dict:
    """Dump the whole rail truth table (all six steps + the flags behind them)."""
    return page.evaluate(_RAIL_TRUTH_TABLE_JS)


def _analyze_only(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seed a corpus user and drive Step 1 only — Compose deliberately skipped."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)


@pytest.mark.ux
@pytest.mark.slow
def test_step5_rail_is_locked_until_compose_freezes_the_composition(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Item 20 — analyze alone must NOT unlock Generate; the freeze must.

    Both halves matter. The lock alone could be satisfied by a rail that never
    opens Step 5 at all, so the same test drives the composition freeze and
    asserts the step opens immediately afterwards.
    """
    _analyze_only(page, live_server, ux_app, monkeypatch)

    before = _rail(page)
    assert before["contextPath"] is True, "precondition: analysis landed"
    assert before["frozen"] is False, "precondition: nothing frozen yet"
    assert before["steps"]["5"]["reachable"] is False, (
        f"Step 5 was reachable with no frozen composition; rail state: {before}"
    )
    assert before["steps"]["5"]["disabled"] is True, (
        f"the Step-5 rail button rendered enabled with nothing frozen; rail state: {before}"
    )
    # A disabled button swallows its own click, so the refusal is also driven
    # through the in-flow control that calls wizardGoTo(5) directly.
    page.evaluate("() => wizardGoTo(5)")
    expect(page.locator(Wizard.PANEL_GENERATE)).to_be_hidden()
    expect(page.locator(_TOAST)).to_contain_text("Compose", timeout=DEFAULT_TIMEOUT_MS)

    # Now go through Compose properly: Save-and-continue freezes the composition.
    compose = WizardComposePage(page, live_server).open()
    assert compose.experience_card_count() >= 1
    compose.continue_to_template()

    after = _rail(page)
    assert after["frozen"] is True, f"the freeze POST did not land; rail state: {after}"
    assert after["steps"]["5"]["reachable"] is True, (
        f"Step 5 stayed locked after the freeze: {after}"
    )
    assert after["steps"]["5"]["disabled"] is False, f"the Step-5 button stayed disabled: {after}"

    page.click(Wizard.CONTINUE_TO_GENERATE)
    page.wait_for_selector(Wizard.PANEL_GENERATE, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    expect(page.locator(Wizard.GENERATE_COPY_FROZEN)).to_be_visible()


@pytest.mark.ux
@pytest.mark.slow
def test_rail_truth_table_after_analyze_gates_only_step5_and_step6(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The widened instrument: what the rail gates on, for every step at once.

    Pinned as a table so a future change that quietly locks (or unlocks) some
    OTHER step while satisfying item 20 fails here rather than in the field.
    """
    _analyze_only(page, live_server, ux_app, monkeypatch)

    table = _rail(page)
    reachable = {int(s): v["reachable"] for s, v in table["steps"].items()}
    assert reachable == {1: True, 2: True, 3: True, 4: True, 5: False, 6: False}, (
        f"rail reachability changed shape; full table: {table}"
    )
    # The lock has to explain itself — a greyed step with no reason reads as a bug.
    step5_title = table["steps"]["5"]["title"] or ""
    assert "compose" in step5_title.lower(), (
        f"the locked Step-5 button carries no explanation; title={step5_title!r}"
    )


def _latest_context_file(ux_app: ModuleType, username: str) -> Path:
    """Newest `context_*.json` the app wrote for `username` (the analyze/freeze one)."""
    user_dir = Path(ux_app.app.config["OUTPUT_DIR"]) / username
    files = sorted(user_dir.glob("context_*.json"))
    assert files, f"no context file under {user_dir}"
    return files[-1]


def _retire_experience(experience_id: int) -> None:
    """Soft-retire a whole role, exactly as the Career Corpus panel's retire does.

    Out-of-band rather than driven through the Corpus UI: the point of the test
    below is what Compose's freeze RESOLVES TO once no active role remains, not how
    the role got retired. `Experience.is_active = 0` IS the corpus-level retire
    (Epic A, A1b); `corpus_to_json_resume.build_json_resume_from_corpus` filters on
    it, which is what empties `work[]`.
    """
    from db.models import Experience
    from db.session import get_session

    s = get_session()
    try:
        exp = s.query(Experience).filter_by(id=experience_id).one()
        exp.is_active = 0
        s.commit()
    finally:
        s.close()


@pytest.mark.ux
@pytest.mark.slow
def test_freezing_a_composition_the_server_wont_assemble_leaves_step5_locked(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adversarial-review finding 1, driven end to end.

    The freeze SUCCEEDS and writes a real `approved_composition` dict — but the
    document it wrote is contentless (no work, no summary, no skills), so
    `blueprints/generation.py::_frozen_composition` returns `None` and
    `/api/generate` hands the run to the retired full-LLM `generate()`. "An
    `approved_composition` key is present" is therefore the wrong question; "will
    the server assemble deterministically" is the right one, because that is what
    the Step-5 copy claims ("Assembled instantly ... no AI variation").

    Driven with real user actions: analyze, retire the positioning draft in
    Compose, then Save-and-continue. The role is soft-retired between analyze and
    the freeze (the Corpus panel's own action — Epic A, A1b), which is what empties
    `work[]` while the analyze-time `career_corpus` snapshot stays populated.

    Before the fix this fails on the first assertion: the freeze POST returned
    2xx, `_compositionFrozen` flipped true, and the rail opened Generate.
    """
    cid = seed_user(ux_app, "alice")
    eid = seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    compose = WizardComposePage(page, live_server).open()
    assert compose.experience_card_count() >= 1, "precondition: Compose rendered the role"
    # Drop the auto-drafted positioning summary — otherwise basics.summary alone
    # keeps the frozen document non-empty.
    page.click(Compose.POSITIONING_DRAFT_RETIRE)
    expect(page.locator(Compose.POSITIONING_DRAFT)).to_have_value("")
    _retire_experience(eid)
    compose.continue_to_template()  # the real Save-and-continue → freeze: true

    # Precondition, read off the server's OWN gate rather than assumed: the freeze
    # landed (an `approved_composition` dict is on the context) AND
    # `_frozen_composition` refuses it, so /api/generate would run the LLM path.
    # Without this the assertions below could pass because the freeze silently
    # failed, which is a different bug wearing the same green.
    from blueprints.generation import _frozen_composition

    ctx = json.loads(_latest_context_file(ux_app, "alice").read_text(encoding="utf-8"))
    assert isinstance(ctx.get("approved_composition"), dict), "precondition: the freeze landed"
    assert ctx.get("career_corpus"), "precondition: the analyze-time corpus snapshot is populated"
    assert _frozen_composition(ctx) is None, (
        "precondition: the server refuses to assemble this frozen document; "
        f"approved_composition={ctx.get('approved_composition')}"
    )

    table = _rail(page)
    assert table["frozen"] is False, (
        "_compositionFrozen claims a freeze the server's own assemble gate rejects; "
        f"rail state: {table}"
    )
    assert table["steps"]["5"]["reachable"] is False, (
        "Step 5 opened on a freeze the server will not assemble deterministically; "
        f"rail state: {table}"
    )
    assert table["steps"]["5"]["disabled"] is True, (
        f"the Step-5 rail button rendered enabled on a non-assemblable freeze: {table}"
    )
    # The determinism claim must be nowhere the user can read it.
    expect(page.locator(Wizard.PANEL_GENERATE)).to_be_hidden()
    expect(page.locator(Wizard.GENERATE_COPY_FROZEN)).to_be_hidden()
    assert "assembled instantly" not in (page.locator("body").inner_text() or "").lower()

    # Not walled out: Compose (Step 3) stays reachable off `lastContextPath`, so
    # the way through is to go back and put content in the composition.
    assert table["steps"]["3"]["reachable"] is True, f"Compose became unreachable: {table}"
    assert table["steps"]["3"]["disabled"] is False, f"the Step-3 button was greyed: {table}"
    BasePage(page, live_server).goto_step(3)
    page.wait_for_selector(Wizard.PANEL_COMPOSE, state="visible", timeout=DEFAULT_TIMEOUT_MS)


def _seed_frozen_step6_application(ux_app: ModuleType) -> int:
    """A generated application whose saved context DOES carry a frozen composition."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    pid = bundled_persona_id()
    aid = seed_application(cid, title="Senior Backend @ Acme")
    rid = seed_run(
        aid,
        iteration=0,
        generated_resume_md="# Alice Resumed\n\n## Experience\n\n- Led the Kafka migration",
        persona_template_id=pid,
    )
    write_context_file(
        ux_app,
        "alice",
        "context_resume_iter1.json",
        {
            "application_run_id": rid,
            "iteration": 1,
            "llm_analysis": {"comparison": {"strengths": [], "gaps": [], "title_alignment": ""}},
            # Load-bearing, not decoration: every real analyze goes through
            # `db.build_context.build_context_set_from_db`, and the ONE frozen
            # predicate (`hardening.frozen_composition_doc`) answers None without a
            # corpus snapshot — because /api/generate would run the LLM path.
            "career_corpus": [
                {"id": 1, "company": "Acme", "titles": ["Staff Engineer"], "bullets": []}
            ],
            "composition_overrides": {"pinned": [], "excluded": [], "added": []},
            "approved_composition": {
                "basics": {"name": "Alice Resumed", "summary": "Platform engineer."},
                "work": [{"name": "Acme", "position": "Staff Engineer", "highlights": ["Kafka"]}],
                "skills": [{"name": "Python"}],
                "meta": {"sartor": {"frozen": True, "work_provenance": []}},
            },
        },
    )
    return aid


@pytest.mark.ux
@pytest.mark.slow
def test_resumed_application_with_a_frozen_composition_can_reach_step5(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rival the widened instrument exists to catch.

    A prior-application resume rebuilds client state from the server's
    `resume_state` payload. It used to reset `_compositionFrozen` to `false`
    unconditionally ("the resume payload doesn't say whether this context carries
    a frozen approved_composition"), which is harmless while Step 5 is ungated
    and a lock-out the moment it isn't. The payload now carries the fact.
    """
    aid = _seed_frozen_step6_application(ux_app)
    # Not optional here, despite this test never asserting on an LLM result: the
    # resume drives `loadComposition()`, whose once-per-application positioning
    # auto-fire POSTs `/draft-summary` and reached the REAL Sonnet call. On a dev
    # machine with `.api_key` that billed (7 confirmed rows for `alice` in
    # `logs/llm_calls.jsonl`); in CI, with no key, it 500'd and red-lined the
    # `page` fixture's `assert not server_errors`.
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    PriorAppsPage(page, live_server).resume_application(aid)
    page.wait_for_selector(Output.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    table = _rail(page)
    assert table["frozen"] is True, (
        f"a resumed application with a frozen composition read as unfrozen: {table}"
    )
    assert table["steps"]["5"]["reachable"] is True, (
        f"Generate was locked on a resumed frozen run: {table}"
    )
    assert table["steps"]["5"]["disabled"] is False, f"the Step-5 button stayed greyed: {table}"

    BasePage(page, live_server).goto_step(5)
    page.wait_for_selector(Wizard.PANEL_GENERATE, state="visible", timeout=DEFAULT_TIMEOUT_MS)

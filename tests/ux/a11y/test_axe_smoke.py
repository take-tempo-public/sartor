"""axe-core accessibility smoke gate — the never-shipped a11y arbiter.

RELEASE_ARC §Sprint 6.3 lands this gate first because it guards every later
v1.0.6 branch. Each test navigates to a reachable panel, injects the vendored
axe-core engine, and asserts **no serious/critical violations** on the live DOM
(the arbiter for finding #3's "missing label / autofill association").

**axe-core is vendored**, not a pip dependency
([`vendor/axe.min.js`](vendor/axe.min.js)) — injected into the page via
Playwright, so the gate runs wherever the UX-tier Chromium already runs and can
never silently skip from a missing extra. It rides the existing
[`tests/ux/conftest.py`](../conftest.py) harness (the `page` fixture's Chromium
graceful-skip + console-error/5xx sentinel) and the `ui_pages/` POMs.

Marked `ux` + `a11y` (+ `slow`): runs inside `pytest -m ux` and is addressable
alone via `pytest -m a11y`.

Scope notes:
- `axe.run` scans the whole top document; the SPA hides inactive tabs/panels
  via `display:none`, and **axe excludes hidden controls** — so scanning while
  on a given tab effectively scans only that visible panel (no cross-panel
  false positives, and the three `display:none` file inputs are correctly not
  flagged).
- iframes are excluded from the axe context: the Compose/Template/Output live
  preview iframes are same-origin renders of generated résumé HTML, out of
  scope for the app's own form-label gate.
- We gate on `serious`/`critical` only — `moderate`/`minor` best-practice noise
  is out of scope for this first cut.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    CorpusPage,
    DashboardConsolePage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import (
    Dashboard,
    Help,
    Memory,
    Personas,
    Settings,
    TopTabs,
    UserPicker,
)

_AXE_JS = (Path(__file__).resolve().parent / "vendor" / "axe.min.js").read_text(
    encoding="utf-8"
)

# Run axe over the whole top document EXCEPT iframes; only populate the
# violations array (faster). Returns a compact, JSON-serializable summary.
_AXE_CALL = """
async () => {
  const results = await axe.run(
    { exclude: [['iframe']] },
    { resultTypes: ['violations'] }
  );
  return results.violations.map(v => ({
    id: v.id,
    impact: v.impact,
    help: v.help,
    targets: v.nodes.map(n => (n.target || []).join(' ')),
  }));
}
"""

_GATED_IMPACTS = {"serious", "critical"}

_JD = (
    "Senior Backend Engineer, Platform. Python on Postgres + AWS with Kafka "
    "as the event backbone. Lead architecture reviews; mentor a team of 6."
)


def _axe_serious(page: Page) -> list[dict[str, Any]]:
    """Inject vendored axe-core into the current document and return only the
    serious/critical violations. Re-injects every call — each navigation is a
    fresh document."""
    page.add_script_tag(content=_AXE_JS)
    raw: list[dict[str, Any]] = page.evaluate(_AXE_CALL)
    return [v for v in raw if v.get("impact") in _GATED_IMPACTS]


def _assert_clean(found: dict[str, list[dict[str, Any]]]) -> None:
    """Fail with a per-panel breakdown of every serious/critical violation."""
    flagged = {panel: vs for panel, vs in found.items() if vs}
    if not flagged:
        return
    lines: list[str] = ["axe serious/critical a11y violations:"]
    for panel, violations in flagged.items():
        lines.append(f"  [{panel}]")
        for v in violations:
            lines.append(f"    - {v['impact']} · {v['id']}: {v['help']}")
            for target in v["targets"]:
                lines.append(f"        @ {target}")
    raise AssertionError("\n".join(lines))


@pytest.mark.ux
@pytest.mark.a11y
@pytest.mark.slow
def test_axe_landing_and_new_user(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """User-picker landing + the revealed new-user form."""
    seed_user(ux_app, "alice")  # populate the user dropdown

    BasePage(page, live_server).load()
    found = {"landing": _axe_serious(page)}

    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_USERNAME, state="visible")
    found["new-user form"] = _axe_serious(page)

    # Sprint 6.5 help primitive — open the shared #helpModal via the injected
    # (i)-circle and scan its open state (dialog aria, no color-only meaning).
    # The first-view auto-open is suppressed for this test, so opening it
    # explicitly makes the scan independent of the localStorage gate.
    page.click(Help.icon("panelUser"))
    page.wait_for_selector(Help.MODAL, state="visible")
    found["help-modal"] = _axe_serious(page)

    _assert_clean(found)


@pytest.mark.ux
@pytest.mark.a11y
@pytest.mark.slow
def test_axe_main_tabs_and_settings(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """The four top tabs (seeded corpus) + the Settings drawer."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")

    found: dict[str, list[dict[str, Any]]] = {}

    WizardJobPage(page, live_server).open()
    found["tailor-step1"] = _axe_serious(page)

    CorpusPage(page, live_server).open().wait_for_cards()
    found["corpus"] = _axe_serious(page)

    page.click(TopTabs.MEMORY)
    page.wait_for_selector(Memory.PANEL, state="visible")
    found["memory"] = _axe_serious(page)

    page.click(TopTabs.PERSONAS)
    page.wait_for_selector(Personas.PANEL, state="visible")
    found["personas"] = _axe_serious(page)

    page.click(Settings.OPEN_PILL)
    page.wait_for_selector(Settings.DRAWER, state="visible")
    found["settings-drawer"] = _axe_serious(page)

    _assert_clean(found)


@pytest.mark.ux
@pytest.mark.a11y
@pytest.mark.slow
def test_axe_compose_and_template_stubbed(
    page: Page, live_server: str, ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive analyze → Compose → Template (LLM stubbed) so the dynamically
    rendered Compose controls (bullet rows, title radios) are scanned — that's
    where any JS-generated label gaps live."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    found: dict[str, list[dict[str, Any]]] = {}

    WizardComposePage(page, live_server).open()
    found["compose"] = _axe_serious(page)

    WizardTemplatePage(page, live_server).open()
    found["template"] = _axe_serious(page)

    _assert_clean(found)


@pytest.mark.ux
@pytest.mark.a11y
@pytest.mark.slow
def test_axe_dashboard_console(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Each /_dashboard tab (Tuning holds the `#tuneCandidate` textarea).

    Seeds a candidate so the auto-populated `#bsUser` / `#tuneUser`
    `<select data-user-source>` dropdowns (Sprint 6.3 #20-dropdown) are scanned
    in their *revealed + populated* state — the real control with its label,
    asterisk, and options — not just an empty placeholder."""
    seed_user(ux_app, "alice")  # GET /api/users → ["alice"] populates the dropdowns

    dash = DashboardConsolePage(page, live_server).load()

    found: dict[str, list[dict[str, Any]]] = {}
    for tab in ("pipeline", "quality", "groundedness", "tuning", "annotate"):
        dash.activate_tab(tab)
        page.wait_for_selector(
            Dashboard.pane_active(tab), state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        # Open the collapsed sub-panel that holds each username dropdown and wait
        # for the fetched option, so axe scans the populated control.
        # <option> elements are never "visible" to Playwright, so wait on
        # `attached` to confirm the fetch-populated option landed.
        if tab == "annotate":
            dash.reveal_details_for(Dashboard.ANN_BS_USER)
            page.wait_for_selector(
                f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached"
            )
        elif tab == "tuning":
            dash.reveal_details_for(Dashboard.TUNE_USER)
            page.wait_for_selector(
                f"{Dashboard.TUNE_USER} option[value='alice']", state="attached"
            )
        found[f"dashboard:{tab}"] = _axe_serious(page)

    _assert_clean(found)

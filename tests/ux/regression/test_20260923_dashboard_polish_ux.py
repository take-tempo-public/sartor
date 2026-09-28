"""UX regression -- Epic C C1b (`feat/dashboard-polish`): UX-2, UX-3, UX-4, UX-5, UX-24.

Diagnosis/scope: `docs/dev/handoffs/epic-c-c1b-brief.md`,
`docs/dev/reviews/epic-c-console-ux-audit.md` (UX-2..UX-6, UX-24). UX-6 (the
Cancel terminal state) is covered by updates to the existing
`test_20260720_diagnostics_run_cancel.py` rather than a new test here, since
that file already drives the exact code path the fix touches.

Guards `dashboard/templates/dashboard.html`:

- UX-2: `.dash-tabs` is `position: sticky` and stacks below `#runLockBanner`
  (also sticky) via the `body:has(#runLockBanner:not([hidden])) .dash-tabs`
  rule, instead of overlapping it.
- UX-3 / UX-24: no page copy claims the console (or any one tab) is
  "Read-only" or the "only write surface" -- Quality, Tuning and Annotate all
  read/write/spend, and the header + Annotate's own copy now say so.
- UX-4: `#runLockBanner` is fully opaque (was 14%-alpha `var(--warning-soft)`)
  and carries a `cb-status-pulse-strong` animation, silenced by
  `static/style.css`'s global `prefers-reduced-motion` override.
- UX-5: every async control (the four streamed runs, Save, Collate, Export
  seed, fixture Load) gets the shared `.btn-pending` disabled+pulsing state
  for the whole request, via the new `window.sartorEval.setBtnPending()` /
  `clearBtnPending()` pair.
"""

from __future__ import annotations

import json
import re
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard

_PENDING = re.compile(r"\bbtn-pending\b")

_BOOTSTRAP = {
    "bootstrap_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "prompt_version": "2026-06-06.1",
    "jaccard_threshold": 0.75,
    "jd_count": 1,
    "jd_labels": [{"jd_file": "jd1.txt", "title": "Senior PM", "company": "Acme Robotics"}],
    "per_jd": [{"jd_file": "jd1.txt", "run_id": "r1", "clarification_questions": []}],
    "dedup": {
        "bullets": {
            "cluster_count": 1,
            "clusters": [
                {
                    "representative": "Led a $5M platform migration",
                    "members": ["Led a $5M platform migration"],
                    "jd_files": ["jd1.txt"],
                    "size": 1,
                },
            ],
        },
        "skills": {"cluster_count": 0, "clusters": []},
    },
    "grounding_signals": None,
}


def _seed_bootstrap(ux_app: ModuleType, slug: str = "alice-bootstrap") -> None:
    ann_root = ux_app.app.config["ANNOTATION_ROOT"]
    fixture_dir = ann_root / slug
    (fixture_dir / "jds").mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP), encoding="utf-8")
    (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")
    (ux_app.app.config["CONFIGS_DIR"] / "alice.config").write_text("{}", encoding="utf-8")


@pytest.mark.ux
def test_no_read_only_or_single_write_surface_claims(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-3 / UX-24: no copy anywhere claims the console -- or any one tab --
    is read-only, or that Annotate is the ONLY write surface (Quality and
    Tuning also write eval-result files)."""
    dash = DashboardConsolePage(page, live_server).load()

    body_text = page.locator("body").inner_text()
    assert "Read-only" not in body_text, "page copy still claims the console is read-only"
    assert "only write surface" not in body_text, "page copy still claims a single write surface"

    # The header explicitly names which tabs read vs. write/spend -- Quality
    # is grouped with the paid/write tabs (it has its own "Run eval" control
    # that spends and writes), not with the pure-read ones. A substring check
    # for "Tuning and Annotate are read-write" alone would still pass even if
    # Quality were wrongly left out of that group (it's a literal substring
    # of the correct sentence too), so assert the full grouping directly and
    # assert the stale grouping is gone.
    meta = page.locator("p.meta")
    meta_text = meta.inner_text()
    assert "Quality, Tuning and Annotate are read-write" in meta_text, (
        "the header does not classify Quality alongside the other paid/write tabs"
    )
    assert "Pipeline, Quality and Groundedness read" not in meta_text, (
        "the header still groups Quality with the pure-read tabs"
    )
    assert "Quality/Tuning/Annotate controls" in meta_text, (
        "the trailing clause doesn't name Quality's own Run-eval control"
    )

    # The Annotate tab's own intro line no longer claims exclusivity either.
    # (`.dash-pane-intro` exists once per tab pane, all present in the DOM
    # even when inactive -- scope to Annotate's own pane specifically.)
    dash.activate_tab("annotate")
    annotate_intro = page.locator(f"{Dashboard.pane('annotate')} {Dashboard.PANE_INTRO}")
    expect(annotate_intro).to_contain_text("read-write surface")

    # The Annotate help-modal body (checked via its help-registry string, not
    # rendered until opened) also dropped the "only" claim.
    dash.open_help("annotate")
    expect(dash.help_modal()).to_be_visible()
    expect(dash.help_modal()).to_contain_text("read-write surface")
    assert "only write surface" not in dash.help_modal().inner_text()


@pytest.mark.ux
def test_dash_tabs_sticky_and_stacks_below_run_banner(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-2: the tab bar stays visible + clickable after scrolling several
    screens down, and stacks below the run-lock banner (rather than
    overlapping it) once a run is live."""
    _seed_bootstrap(ux_app)
    dash = DashboardConsolePage(page, live_server).load()
    # The sticky container is `nav.dash-tabs` -- distinct from `Dashboard.TABS`
    # (`.dash-tab`), which selects the individual tab buttons inside it.
    tabs = page.locator("nav.dash-tabs")

    # Sticky by default, flush to the top while no run is live.
    assert tabs.evaluate("el => getComputedStyle(el).position") == "sticky"
    assert tabs.evaluate("el => getComputedStyle(el).top") == "0px"

    # Scroll deep into the long Annotate pane; the tab bar stays visible. A
    # spacer forces enough scrollable height deterministically, regardless of
    # how tall this one seeded fixture happens to render (the acceptance
    # check's own scenario is "3 screens down").
    dash.activate_tab("annotate")
    dash.select_fixture("alice-bootstrap")
    expect(dash.editor()).to_be_visible()
    page.evaluate(
        "() => { const d = document.createElement('div'); "
        "d.style.height = '4000px'; document.body.appendChild(d); }"
    )
    page.mouse.wheel(0, 3000)
    expect(tabs).to_be_in_viewport()

    # Start a live run; the banner appears and the tabs stack below it
    # (their computed `top` grows to clear it) instead of overlapping.
    dash.activate_tab("quality")
    page.on("dialog", lambda dialog: dialog.accept())
    held: list[Route] = []
    page.route("**/api/eval/run", lambda route: held.append(route))
    page.locator("#evalRunBtn").click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-eval click never issued a POST /api/eval/run"

    banner = page.locator("#runLockBanner")
    expect(banner).to_be_visible()
    tabs_top_while_live = tabs.evaluate("el => getComputedStyle(el).top")
    assert tabs_top_while_live != "0px", (
        "tab bar did not shift to stack below the visible run-lock banner"
    )
    banner_box = banner.bounding_box()
    tabs_box = tabs.bounding_box()
    assert banner_box is not None and tabs_box is not None
    assert banner_box["y"] + banner_box["height"] <= tabs_box["y"] + 1, (
        "the sticky tab bar overlaps the sticky run-lock banner"
    )

    held[0].fulfill(status=200, content_type="text/event-stream", body="")
    expect(banner).to_be_hidden()


@pytest.mark.ux
def test_run_lock_banner_opaque_and_pulses_unless_reduced_motion(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-4: the banner's computed background is fully opaque (was 14%-alpha)
    and it carries a pulsing animation, silenced under
    `prefers-reduced-motion: reduce`."""
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("quality")
    page.on("dialog", lambda dialog: dialog.accept())

    held: list[Route] = []
    page.route("**/api/eval/run", lambda route: held.append(route))
    page.locator("#evalRunBtn").click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the Run-eval click never issued a POST /api/eval/run"

    banner = page.locator("#runLockBanner")
    expect(banner).to_be_visible()
    alpha = banner.evaluate(
        "el => { "
        "const m = getComputedStyle(el).backgroundColor.match(/[\\d.]+/g); "
        "return m.length > 3 ? parseFloat(m[3]) : 1; "
        "}"
    )
    assert alpha == 1, f"#runLockBanner background is not fully opaque (alpha={alpha})"
    anim_name = banner.evaluate("el => getComputedStyle(el).animationName")
    assert anim_name != "none", "#runLockBanner carries no animation"

    held[0].fulfill(status=200, content_type="text/event-stream", body="")
    expect(banner).to_be_hidden()

    # Reduced motion: the SAME rule (static/style.css's global
    # `*,*::before,*::after{animation:none!important}` override) must silence it.
    page.emulate_media(reduced_motion="reduce")
    held2: list[Route] = []
    page.route("**/api/eval/run", lambda route: held2.append(route))
    page.locator("#evalRunBtn").click()
    for _ in range(100):
        if held2:
            break
        page.wait_for_timeout(50)
    assert held2, "the second Run-eval click never issued a POST /api/eval/run"
    expect(banner).to_be_visible()
    anim_name_reduced = banner.evaluate("el => getComputedStyle(el).animationName")
    assert anim_name_reduced == "none", (
        "#runLockBanner still animates under prefers-reduced-motion: reduce"
    )
    held2[0].fulfill(status=200, content_type="text/event-stream", body="")


@pytest.mark.ux
def test_save_and_collate_get_pending_state_for_whole_request(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-5: Save and Collate were not disabled while their own fetch was in
    flight (a double-click could post twice); both now get the shared
    disabled+pulsing `.btn-pending` state for the whole request."""
    _seed_bootstrap(ux_app)
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    dash.select_fixture("alice-bootstrap")
    expect(dash.editor()).to_be_visible()
    dash.set_first_bullet_verdict("keep")

    save_btn = page.locator(Dashboard.ANN_SAVE)
    held: list[Route] = []
    page.route(
        "**/api/annotation/fixture/*/*",
        lambda route: held.append(route) if route.request.method == "POST" else route.continue_(),
    )
    save_btn.click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "Save never issued its POST"
    expect(save_btn).to_be_disabled()
    expect(save_btn).to_have_class(_PENDING)
    held[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"bullets": 1, "skills": 0}),
    )
    expect(save_btn).to_be_enabled()
    expect(save_btn).not_to_have_class(_PENDING)
    expect(dash.status()).to_contain_text("Saved")
    # collate() below calls save() internally first -- unroute so that inner
    # save's own POST goes through for real instead of being held again.
    page.unroute("**/api/annotation/fixture/*/*")

    # Collate: save() runs first (unheld, so it completes normally), then the
    # collate POST itself is held -- #annCollate's own pending state is set
    # at the very top of collate() and must survive across both requests.
    collate_btn = page.locator(Dashboard.ANN_COLLATE)
    held2: list[Route] = []
    page.route("**/api/annotation/fixture/*/*/collate", lambda route: held2.append(route))
    collate_btn.click()
    for _ in range(100):
        if held2:
            break
        page.wait_for_timeout(50)
    assert held2, "Collate never issued its POST"
    expect(collate_btn).to_be_disabled()
    expect(collate_btn).to_have_class(_PENDING)
    held2[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"must_keywords": 0, "forbidden_inventions": 0, "jd_written": True}),
    )
    expect(collate_btn).to_be_enabled()
    expect(collate_btn).not_to_have_class(_PENDING)


@pytest.mark.ux
def test_export_seed_and_fixture_load_get_pending_state(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-5: Export seed and the fixture picker's own Load also get a
    disabled+pulsing state for the duration of their request."""
    from tests.ux.seeding import seed_user

    _seed_bootstrap(ux_app)
    seed_user(ux_app, "alice")
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")

    # Export seed.
    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    dash.select_bs_user("alice")
    export_btn = page.locator("#bsExportSeed")
    held: list[Route] = []
    page.route("**/api/annotation/seed/export", lambda route: held.append(route))
    export_btn.click()
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "Export seed never issued its POST"
    expect(export_btn).to_be_disabled()
    expect(export_btn).to_have_class(_PENDING)
    held[0].fulfill(
        status=409, content_type="application/json", body=json.dumps({"error": "no corpus"})
    )
    expect(export_btn).to_be_enabled()
    expect(export_btn).not_to_have_class(_PENDING)

    # Fixture Load: the <select> itself gets the pending state for the GET.
    fixture_select = dash.fixture_select()
    expect(fixture_select.locator("option")).to_have_count(2)
    held2: list[Route] = []
    page.route(
        "**/api/annotation/fixture/*/*",
        lambda route: held2.append(route) if route.request.method == "GET" else route.continue_(),
    )
    dash.select_fixture("alice-bootstrap")
    for _ in range(100):
        if held2:
            break
        page.wait_for_timeout(50)
    assert held2, "the fixture-select change never issued its GET"
    expect(fixture_select).to_be_disabled()
    expect(fixture_select).to_have_class(_PENDING)
    held2[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {
                "annotations": {"bullets": [], "skills": [], "clarification_ratings": []},
                "vocab": {"verdicts": ["keep"], "failed_rules": []},
                "has_annotations": False,
            }
        ),
    )
    expect(fixture_select).to_be_enabled()
    expect(fixture_select).not_to_have_class(_PENDING)

"""UX walk — the /_dashboard "Annotate" read-write tab.

Seeds a bootstrap.json under the temp ANNOTATION_ROOT the conftest injects onto the
live app config (so the threaded server sees it) plus a configs/<user>.config so
_safe_username passes, then drives the tab: pick the bootstrap, fill every
verdict, Save (fail-closed write), and Collate → fixture + brief. The
unconditional console-error / 5xx sentinel (conftest `page`) proves the
write surface renders + round-trips clean.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard

_BOOTSTRAP = {
    "bootstrap_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "prompt_version": "2026-06-06.1",
    "jaccard_threshold": 0.75,
    "jd_count": 1,
    "per_jd": [
        {
            "jd_file": "jd1.txt",
            "run_id": "r1",
            "clarification_questions": [
                {
                    "id": "q1",
                    "text": "What was the scope of your ownership?",
                    "kind": "scope_probe",
                },
            ],
        }
    ],
    "dedup": {
        "bullets": {
            "cluster_count": 2,
            "clusters": [
                {
                    "representative": "Led a $5M platform migration",
                    "members": ["Led a $5M platform migration"],
                    "jd_files": ["jd1.txt"],
                    "size": 1,
                },
                {
                    "representative": "Built CI/CD pipelines",
                    "members": ["Built CI/CD pipelines"],
                    "jd_files": ["jd1.txt"],
                    "size": 1,
                },
            ],
        },
        "skills": {
            "cluster_count": 1,
            "clusters": [
                {
                    "representative": "Python",
                    "members": ["Python"],
                    "jd_files": ["jd1.txt"],
                    "size": 1,
                },
            ],
        },
    },
    "grounding_signals": None,
}


@pytest.mark.ux
def test_annotation_tab_save_and_collate(page: Page, live_server: str, ux_app: ModuleType) -> None:
    # The conftest injects a temp ANNOTATION_ROOT onto the live app config; seed the
    # bootstrap fixture under it so the already-running server thread finds it (the
    # diagnostics routes read current_app.config["ANNOTATION_ROOT"] per request).
    ann_root = ux_app.app.config["ANNOTATION_ROOT"]
    fixture_dir = ann_root / "alice-bootstrap"
    (fixture_dir / "jds").mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP), encoding="utf-8")
    (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")
    # _safe_username needs a configs/<user>.config (CONFIGS_DIR is the ux temp dir).
    (ux_app.app.config["CONFIGS_DIR"] / "alice.config").write_text("{}", encoding="utf-8")

    dash = DashboardConsolePage(page, live_server).load()

    # Annotate tab present + activates.
    expect(dash.tab("annotate")).to_be_visible()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()

    # The seeded bootstrap shows up in the picker (blank option + the fixture).
    expect(dash.fixture_select().locator("option")).to_have_count(2)
    dash.select_fixture("alice-bootstrap")

    # Editor renders the two bullet clusters + one skill cluster.
    expect(dash.editor()).to_be_visible()
    expect(dash.bullet_items()).to_have_count(2)

    # Fill every verdict (fail-closed Save needs them all).
    for sel in page.locator(f"{Dashboard.ANN_BULLETS} .ann-item select").all():
        sel.select_option("keep")
    page.locator(f"{Dashboard.ANN_SKILLS} .ann-item select").first.select_option("keep")

    # Save → annotations.json written.
    dash.save()
    expect(dash.status()).to_contain_text("Saved")
    assert (fixture_dir / "annotations.json").exists()

    # Collate → expected.json + improvement_brief.md + jd.txt.
    dash.collate()
    expect(dash.status()).to_contain_text("Collated")
    assert (fixture_dir / "expected.json").exists()
    assert (fixture_dir / "improvement_brief.md").exists()
    assert (fixture_dir / "jd.txt").read_text(encoding="utf-8") == "Senior PM JD body."


@pytest.mark.ux
def test_bootstrap_done_loads_editor_without_manual_repick(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Fix (2026-07-08): the bootstrap-`done` handler used to set
    `$('fixtureSelect').value = slug` directly — a plain `.value =`
    assignment never fires `change`, so the editor never rendered until the
    user manually re-picked the option (which can't fire `change` on a
    second pick of the SAME already-selected value either). The fix calls
    `loadFixture(slug, user)` directly instead of relying on the `change`
    listener.

    The paid `POST /api/annotation/bootstrap` SSE pipeline is intercepted via
    `page.route` with a canned SSE stream ending in the real `done` event
    shape (`web_infra.http._sse`'s wire format) — this targets the CLIENT
    behavior the bug lived in; the server pipeline itself is already covered
    by `TestBootstrapStream` in `tests/test_annotation_routes.py`.
    """
    from tests.ux.seeding import seed_user
    from web_infra.http import _sse

    seed_user(ux_app, "alice")
    ann_root = ux_app.app.config["ANNOTATION_ROOT"]
    fixture_dir = ann_root / "alice-bootstrap"
    (fixture_dir / "jds").mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP), encoding="utf-8")
    (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")

    def _stub(route: Route) -> None:
        body = (
            _sse("start", {"total": 1, "slug": "alice-bootstrap", "candidate": "alice"})
            + _sse("jd_start", {"index": 0, "total": 1, "jd_file": "jd1"})
            + _sse(
                "done",
                {
                    "slug": "alice-bootstrap",
                    "candidate": "alice",
                    "jd_count": 1,
                    "bullet_clusters": 2,
                    "skill_clusters": 1,
                    "grounded": False,
                },
            )
        )
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/annotation/bootstrap", _stub)

    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    expect(dash.active_pane("annotate")).to_be_visible()

    dash.reveal_details_for(Dashboard.ANN_BS_USER)
    page.wait_for_selector(f"{Dashboard.ANN_BS_USER} option[value='alice']", state="attached")
    dash.select_bs_user("alice")
    page.fill(Dashboard.ANN_BS_SLUG, "alice-bootstrap")
    # addJdRow('', '') fires once unconditionally on load, so one empty JD
    # row already exists — fill it rather than adding another.
    page.fill(".bs-jd-name", "jd1")
    page.fill(".bs-jd-text", "Senior PM JD body.")
    page.locator(Dashboard.ANN_BS_RUN).click()

    # The bug: without the fix, nothing below renders — the fixture <select>
    # gets its `.value` set but the editor stays hidden, and this test never
    # touches the <select> itself to work around it.
    expect(dash.editor()).to_be_visible()
    expect(dash.bullet_items()).to_have_count(2)
    expect(page.locator(Dashboard.ANN_FIXTURE_SELECT)).to_have_value("alice-bootstrap")

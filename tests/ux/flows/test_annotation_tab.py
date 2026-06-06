"""UX walk — the /_dashboard "Annotate" read-write tab.

Seeds a bootstrap.json under a temp ANNOTATION_ROOT (monkeypatched on the live
app module so the threaded server sees it) plus a configs/<user>.config so
_safe_username passes, then drives the tab: pick the bootstrap, fill every
verdict, Save (fail-closed write), and Collate → fixture + brief. The
unconditional console-error / 5xx sentinel (conftest `page`) proves the
write surface renders + round-trips clean.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard

_BOOTSTRAP = {
    "bootstrap_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "prompt_version": "2026-06-06.1",
    "jaccard_threshold": 0.75,
    "jd_count": 1,
    "per_jd": [{
        "jd_file": "jd1.txt", "run_id": "r1",
        "clarification_questions": [
            {"id": "q1", "text": "What was the scope of your ownership?", "kind": "scope_probe"},
        ],
    }],
    "dedup": {
        "bullets": {"cluster_count": 2, "clusters": [
            {"representative": "Led a $5M platform migration",
             "members": ["Led a $5M platform migration"], "jd_files": ["jd1.txt"], "size": 1},
            {"representative": "Built CI/CD pipelines",
             "members": ["Built CI/CD pipelines"], "jd_files": ["jd1.txt"], "size": 1},
        ]},
        "skills": {"cluster_count": 1, "clusters": [
            {"representative": "Python", "members": ["Python"], "jd_files": ["jd1.txt"], "size": 1},
        ]},
    },
    "grounding_signals": None,
}


@pytest.mark.ux
def test_annotation_tab_save_and_collate(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    # Temp ANNOTATION_ROOT visible to the already-running live server thread.
    ann_root = tmp_path / "annroot"
    fixture_dir = ann_root / "alice-bootstrap"
    (fixture_dir / "jds").mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP), encoding="utf-8")
    (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")
    monkeypatch.setattr(ux_app, "ANNOTATION_ROOT", ann_root)
    # _safe_username needs a configs/<user>.config (CONFIGS_DIR is the ux temp dir).
    (ux_app.CONFIGS_DIR / "alice.config").write_text("{}", encoding="utf-8")

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

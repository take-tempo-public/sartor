"""UX regression — Epic C C1a / UX-1: `#annCollate` + its collate-time run button escape
the diagnostics run lock.

Diagnosis: `docs/dev/diagnosis/dashboard-run-lock-gaps.md`.

Two mechanisms, proven separately:

1. `#annCollate` (the "Collate -> fixture + brief" button) was missing from
   `LOCK_BTN_IDS` in `dashboard/templates/dashboard.html`, so it stayed clickable while
   another paid diagnostics run was live. Covered by adding it to the existing
   `_RUN_LOCK_IDS` tuple in `tests/ux/regression/test_20260709_diagnostics_run_lock.py`
   (all three of that module's tests independently prove it, one per run entry point).
2. `renderCollateResult()` builds a fresh `#annCollateRunBtn` on every Collate with no
   lock-awareness, so a Collate that manages to fire while a run is already live (the
   normal path is blocked by #1 above; this test forces past that to prove the deeper,
   defense-in-depth mechanism independently) used to produce an ENABLED run button —
   which is the button whose click starts the second paid run UX-1 named.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage

_BOOTSTRAP = {
    "bootstrap_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "prompt_version": "2026-06-06.1",
    "jaccard_threshold": 0.75,
    "jd_count": 1,
    "jd_labels": [{"jd_file": "jd1.txt", "title": "Senior PM", "company": "Acme Robotics"}],
    "per_jd": [
        {
            "jd_file": "jd1.txt",
            "run_id": "r1",
            "clarification_questions": [],
        }
    ],
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


@pytest.mark.ux
def test_collate_run_btn_created_during_live_run_renders_disabled(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    ann_root = ux_app.app.config["ANNOTATION_ROOT"]
    fixture_dir = ann_root / "alice-bootstrap"
    (fixture_dir / "jds").mkdir(parents=True)
    (fixture_dir / "bootstrap.json").write_text(json.dumps(_BOOTSTRAP), encoding="utf-8")
    (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")
    (ux_app.app.config["CONFIGS_DIR"] / "alice.config").write_text("{}", encoding="utf-8")

    dash = DashboardConsolePage(page, live_server).load()

    # Start (and hold) a paid eval run from the Quality tab BEFORE any Collate has
    # happened, so #annCollateRunBtn does not exist yet when the lock is acquired --
    # this is the exact ordering UX-1 named (a button created AFTER acquireRunLock()
    # already ran, so its own forEach never touches it).
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
    expect(page.locator("#runLockBanner")).to_be_visible()

    # Now drive Annotate -> Save -> Collate while the run above is still live.
    dash.activate_tab("annotate")
    dash.select_fixture("alice-bootstrap")
    expect(dash.editor()).to_be_visible()
    for sel in page.locator("#annBullets .ann-item select").all():
        sel.select_option("keep")
    dash.save()
    expect(dash.status()).to_contain_text("Saved")

    # #annCollate is disabled by the lock fix (proven separately in
    # test_20260709_diagnostics_run_lock.py); force it enabled here to isolate and
    # prove the SECOND, defense-in-depth mechanism -- renderCollateResult() itself must
    # not hand back an enabled run button just because it was reachable.
    page.locator("#annCollate").evaluate("el => { el.disabled = false; }")
    dash.collate()
    expect(dash.status()).to_contain_text("Collated")

    expect(page.locator("#annCollateRunBtn")).to_be_disabled()

    # Release the held eval run; the new run button should re-enable like the rest of
    # the lock-governed set.
    held[0].fulfill(status=200, content_type="text/event-stream", body="")
    expect(page.locator("#runLockBanner")).to_be_hidden()
    expect(page.locator("#annCollateRunBtn")).to_be_enabled()

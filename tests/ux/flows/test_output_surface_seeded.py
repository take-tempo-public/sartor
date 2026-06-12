"""Walk B — the Step-6 WYSIWYG output surface, seeded + LLM-free.

Covers the v1.0.5 output surface (WYSIWYG preview = download) by reusing the
just-shipped prior-app-resume feature: seed an already-generated application
(run + a context file carrying `last_generated_json_resume`), click the prior
app → "Resume in wizard" → Step 6, and assert the styled résumé renders in
the preview iframe and the download control is present.

No LLM and no generate machinery (no doc render, no ATS, no nested Chromium):
the preview route serves the cached JSON Resume directly (the recommendations
gate doesn't apply once a generate has run). The persona is a DB-seeded
bundled template so it resolves on disk.
"""

from __future__ import annotations

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
from ui_pages import BasePage, PriorAppsPage, UserPickerPage, WizardOutputPage

_RESUME_JSON = {
    "basics": {"name": "Alice Resumed", "label": "Staff Platform Engineer",
               "email": "alice@example.com"},
    "work": [{
        "name": "Acme Logistics", "position": "Staff Engineer",
        "startDate": "2021-01",
        "highlights": ["Led the Kafka migration across 12 topics"],
    }],
}


@pytest.mark.ux
@pytest.mark.slow
def test_resume_prior_application_renders_step6(page: Page, live_server: str,
                                                ux_app: ModuleType) -> None:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)  # non-empty corpus → smart landing keeps us on Tailor
    pid = bundled_persona_id()
    aid = seed_application(cid, title="Senior Backend @ Acme")
    rid = seed_run(aid, iteration=0, generated_resume_md="# Alice\n- Led migration",
                   persona_template_id=pid)
    write_context_file(ux_app, "alice", "context_resume_iter1.json", {
        "application_run_id": rid, "iteration": 1,
        "last_generated_json_resume": _RESUME_JSON,
    })

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    PriorAppsPage(page, live_server).resume_application(aid)

    out = WizardOutputPage(page, live_server).wait_loaded()
    expect(out.download_resume_button()).to_be_visible()
    # WYSIWYG: the styled résumé (from the cached JSON Resume) renders in the
    # preview iframe — the download serves the same content.
    expect(out.preview_body()).to_contain_text("Alice Resumed")

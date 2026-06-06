"""Regression: all four bundled templates paginate cleanly — no blank pages.

Closes the v1.0.5 `feat/template-pagination` work (2026-06-04). modern / spacious
/ tech carried `section { page-break-inside: avoid; }` (Classic did not), so
paged.js refused to break *inside a whole section* and shoved any Experience
section taller than the remaining page wholesale onto the next page — leaving a
blank/short page. The fix drops the section-level rule (keeping the correct
per-entry `article { break-inside: avoid }`) and matches Classic's break model.

This test renders a deliberately multi-page résumé through each bundled template
via the real preview route (`/api/applications/<id>/preview`, which injects
paged.js) and asserts every rendered `.pagedjs_page` carries content — i.e. no
blank page. If the section-level break-avoidance is ever reintroduced, an empty
page reappears and this fails.

It also pins the decisive paged.js console-error fix: the route now drives
paged.js manually (`PagedConfig.auto=false` + `Previewer().preview()` in
try/catch + `.catch()`), so the cosmetic "getBoundingClientRect of null" can no
longer escape. The `page` fixture's sentinel (no JS console error / no 5xx) runs
with NO allowlist, so a paged.js leak would fail this test.

LLM-free: the preview serves a seeded `last_generated_json_resume` directly (the
WYSIWYG cached-JSON path; recommendations gate doesn't apply once a generate has
run), so no analyzer, no doc render, no nested Chromium.
"""

from __future__ import annotations

from types import ModuleType
from urllib.parse import quote

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import (
    bundled_persona_id_by_path,
    seed_application,
    seed_user,
    write_context_file,
)
from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage

# One bundled template per row: the `path` column (DB) → a human label for
# failure messages. Classic is the known-good control; the other three carried
# the section-break bug.
_BUNDLED = [
    ("classic", "personas/bundled/classic.docx"),
    ("modern", "personas/bundled/modern.docx"),
    ("spacious", "personas/bundled/spacious.docx"),
    ("tech", "personas/bundled/tech.docx"),
]


def _multi_page_resume() -> dict:
    """A résumé large enough to span multiple pages in every template — the
    Experience section alone exceeds a page, which is exactly what the old
    `section { break-inside: avoid }` rule choked on."""
    work = [
        {
            "name": f"Company {i + 1}",
            "position": "Staff Software Engineer",
            "startDate": f"20{10 + i:02d}-01",
            "endDate": f"20{11 + i:02d}-01",
            "summary": ("Owned platform reliability and developer-experience "
                        "initiatives across multiple product teams."),
            "highlights": [
                "Reduced p99 API latency 42% via read-through caching and "
                "connection pooling across 18 services",
                "Led the migration from a monolith to event-driven "
                "microservices on Kafka with zero customer downtime",
                "Cut cloud spend $1.2M/yr by right-sizing compute and "
                "adopting spot instances for batch workloads",
                "Mentored 6 engineers; two were promoted to senior within the year",
                "Built the CI/CD pipeline that took deploys from weekly to "
                "30+ per day with automated canary analysis",
            ],
        }
        for i in range(7)
    ]
    return {
        "basics": {
            "name": "Jordan Multi-Page",
            "label": "Staff Software Engineer",
            "email": "jordan@example.com",
            "summary": ("Staff engineer with 12 years building distributed "
                        "systems at scale, specializing in reliability, "
                        "developer experience, and cost-efficient platform "
                        "architecture."),
        },
        "work": work,
        "skills": [
            {"name": "Languages",
             "keywords": ["Python", "Go", "TypeScript", "Rust", "Java"]},
            {"name": "Infrastructure",
             "keywords": ["Kubernetes", "Kafka", "Postgres", "Terraform", "AWS"]},
            {"name": "Practices",
             "keywords": ["SRE", "CI/CD", "Observability", "Incident response"]},
        ],
    }


# Wait until paged.js has finished laying out: the `.pagedjs_page` count is
# > 0 and unchanged across two polls (paged.js builds pages incrementally).
_SETTLE_JS = """() => {
    const n = document.querySelectorAll('.pagedjs_page').length;
    if (n > 0 && window.__pgN === n) return true;
    window.__pgN = n;
    return false;
}"""

# Per-page content text, so we can spot a blank page (empty content area).
_BLANK_PAGES_JS = """() => {
    const pages = Array.from(document.querySelectorAll('.pagedjs_page'));
    const blank = [];
    pages.forEach((p, i) => {
        const c = p.querySelector('.pagedjs_page_content');
        const txt = (c ? c.innerText : p.innerText || '').trim();
        if (txt.length === 0) blank.push(i);
    });
    return {total: pages.length, blank: blank};
}"""


@pytest.mark.ux
@pytest.mark.slow
def test_bundled_templates_have_no_blank_pages(
    page: Page, live_server: str, ux_app: ModuleType,
    console_errors: list[str],
) -> None:
    cid = seed_user(ux_app, "jordan")
    aid = seed_application(cid, title="Staff Engineer @ Scale")
    ctx_path = write_context_file(
        ux_app, "jordan", "context_resume_iter1.json",
        {"iteration": 1, "last_generated_json_resume": _multi_page_resume()},
    )

    base = BasePage(page, live_server).base_url

    for label, path in _BUNDLED:
        pid = bundled_persona_id_by_path(path)
        url = (f"{base}/api/applications/{aid}/preview"
               f"?template_id={pid}&context_path={quote(ctx_path)}")
        resp = page.goto(url)
        assert resp is not None and resp.status == 200, (
            f"{label}: preview route returned {resp.status if resp else 'no response'}")

        page.wait_for_selector(".pagedjs_page", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_function(_SETTLE_JS, timeout=DEFAULT_TIMEOUT_MS, polling=300)

        result = page.evaluate(_BLANK_PAGES_JS)
        # The fixture is genuinely multi-page, so paged.js must have split it —
        # a 1-page result would mean the render collapsed, not that pagination
        # is "perfect".
        assert result["total"] >= 2, (
            f"{label}: expected a multi-page render, got {result['total']} page(s)")
        assert result["blank"] == [], (
            f"{label}: blank page(s) at index {result['blank']} of "
            f"{result['total']} — section-level break-avoidance regressed?")

    # The decisive paged.js console-error fix: no getBoundingClientRect (or any
    # other) JS error leaked across all four renders. The `page` fixture's
    # teardown asserts the same with no allowlist; this is the explicit signal.
    assert console_errors == [], f"paged.js / JS console errors: {console_errors}"

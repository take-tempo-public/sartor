"""F-19 — one end-to-end demo-mode journey (feat/ux-w3-demo-mode).

Deliberately the ODD ONE OUT among the UX flow tests: every other flow calls
`install_llm_stubs()` to replace the analyzer entry points with test doubles.
This test does NOT — the whole point is to prove the REAL `analyzer.py`
demo-mode short-circuit (SARTOR_DEMO=1) renders a real analysis through the
real `/api/analyze` SSE route, with no `.api_key` anywhere and no Anthropic
client ever constructed. If this test used `install_llm_stubs()` it would
prove nothing about the actual demo-mode code path.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, UserPickerPage, WizardJobPage
from ui_pages.selectors import DemoMode, Wizard

_JD = (
    "Senior Site Reliability Engineer. Own the control plane: Kubernetes, "
    "Terraform, Prometheus/Grafana, SLOs, and postmortem-driven incident response."
)


@pytest.mark.ux
@pytest.mark.slow
def test_demo_mode_analyze_renders_canned_analysis_with_banner(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No real key anywhere — analyzer.py's own demo check short-circuits before
    # web_infra._get_client() would ever read one, so this is a genuine
    # "no API key present" run, not merely an unused one.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("SARTOR_DEMO", "1")
    # Drives the banner: `ux_app` already reloaded `app.py` (building its
    # `Config()`/`app.config["DEMO_MODE"]`) before this test's SARTOR_DEMO=1
    # took effect, so set it directly on the live app — the same
    # already-established isolation pattern the `ux_app` fixture itself uses
    # for CONFIGS_DIR/OUTPUT_DIR/etc.
    ux_app.app.config["DEMO_MODE"] = True

    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()

    # The banner is visible from the very first paint, before any user is
    # even selected — case-insensitive text match (CSS may uppercase copy
    # elsewhere in this app; this banner's own rule sets text-transform:none,
    # but assert defensively regardless).
    banner = page.locator(DemoMode.BANNER)
    assert banner.is_visible()
    assert "demo mode" in (banner.text_content() or "").strip().lower()
    assert "no api calls" in (banner.text_content() or "").strip().lower()

    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    # The REAL analyzer.analyze_streaming() ran and short-circuited to the
    # canned SRE-themed analysis (demo_fixtures.CANNED_ANALYSIS) — spot-check
    # a distinctive essential skill it always carries.
    analysis_text = page.locator(Wizard.ANALYSIS_CONTENT).text_content() or ""
    assert "kubernetes" in analysis_text.lower()

    # Still visible after navigating into the wizard — persistent, not a
    # one-shot toast.
    assert banner.is_visible()

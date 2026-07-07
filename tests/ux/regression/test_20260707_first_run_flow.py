"""Regression: Wave-1 first-run flow (UX review F-12 / F-06 / F-05 / F-15).

Four first-session fixes land together on ``feat/ux-w1-first-run-flow``:

- **F-12** — the Analyze screen leads with a short verdict + top-3 actions
  (derived deterministically from the payload — no new LLM call) and folds the
  deep analysis behind a native ``<details>`` "Show full analysis" disclosure,
  collapsed by default. The F-01 reframe (the "JD Keyword Coverage" heading,
  its ``.score-note`` explainer, and the "Keywords You Could Add" heading) is
  preserved verbatim.
- **F-06** — the post-create smart-landing jump (Tailor → Career corpus) gets a
  one-time explanatory help modal (``tourCorpusLanding``), reusing the existing
  ``_HELP_REGISTRY`` + ``cb_help_seen:`` primitive — no new modal machinery.
- **F-05** — the new-user form is display-name-first: the full name leads, the
  username slug auto-derives from it (visible + editable, same storage key and
  APIs), and a manual username edit stops the auto-derive for that form session.
- **F-15** — applications capture the employer at creation time
  (``_infer_application_company`` → ``hardening.extract_company_terms``,
  deterministic + fail-open), so the tracker card shows a company instead of
  null.

LLM-free throughout (``install_llm_stubs`` where the wizard runs). UX copy may
be CSS-uppercased, so text assertions compare ``text_content()``
case-insensitively.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import BasePage, UserPickerPage, WizardJobPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Help, UserPicker, Wizard

_JD = (
    "Senior Backend Engineer, Platform. Python on Postgres + AWS with Kafka "
    "as the event backbone. Lead architecture reviews; mentor a team of 6."
)


def _lower_texts(page: Page, selector: str) -> list[str]:
    """All matching elements' text_content(), lowercased (CSS may uppercase)."""
    texts: list[str] = page.eval_on_selector_all(
        selector, "els => els.map(e => e.textContent || '')"
    )
    return [t.strip().lower() for t in texts]


# ---------------------------------------------------------------------------
# F-12 — progressive disclosure on the Analyze screen
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_analysis_leads_with_verdict_and_folds_details(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verdict + ≤3 actions lead; the deep read is collapsed by default and
    expandable; the F-01 reframe survives verbatim."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)

    # F-01 preserved: coverage heading + its explainer note stay above the fold.
    first_heading = (
        page.locator(f"{Wizard.ANALYSIS_CONTENT} h3").first.text_content() or ""
    ).lower()
    assert "jd keyword coverage" in first_heading
    assert page.locator(f"{Wizard.ANALYSIS_CONTENT} .score-note").is_visible()

    # F-12: the verdict block leads with a line + 1..3 deterministic actions.
    assert page.locator(f"{Wizard.ANALYSIS_VERDICT} .analysis-verdict-line").is_visible()
    action_count = page.locator(f"{Wizard.ANALYSIS_VERDICT} .analysis-top-actions li").count()
    assert 1 <= action_count <= 3, f"expected 1..3 top actions, got {action_count}"

    # The disclosure exists, is collapsed by default, and hides the deep read.
    assert page.locator(Wizard.ANALYSIS_DETAILS).count() == 1
    assert page.get_attribute(Wizard.ANALYSIS_DETAILS, "open") is None
    assert page.locator(f"{Wizard.ANALYSIS_DETAILS} .tag-matched").first.is_hidden()
    summary_text = (page.locator(Wizard.ANALYSIS_DETAILS_SUMMARY).text_content() or "").lower()
    assert "show full analysis" in summary_text

    # Expanding reveals the deep sections — incl. the F-01 "Keywords You Could
    # Add" heading, verbatim inside the fold.
    page.click(Wizard.ANALYSIS_DETAILS_SUMMARY)
    page.wait_for_selector(
        f"{Wizard.ANALYSIS_DETAILS}[open]", state="attached", timeout=DEFAULT_TIMEOUT_MS
    )
    headings = _lower_texts(page, f"{Wizard.ANALYSIS_DETAILS} h3")
    assert "keywords you could add" in headings
    assert "essential skills" in headings
    assert page.locator(f"{Wizard.ANALYSIS_DETAILS} .tag-matched").first.is_visible()


# ---------------------------------------------------------------------------
# F-06 + F-05 — display-name-first create, explained corpus landing
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_post_create_corpus_landing_explained_once(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Creating a user via the display-name-first path lands on Career corpus
    with the one-time transition modal; it never re-fires (cb_help_seen)."""
    # The autouse fixture suppresses every auto-firing stop; un-suppress ONLY
    # the F-06 stop (this init script runs after the fixture's, so it wins).
    page.add_init_script(
        "try { window.localStorage.removeItem('cb_help_seen:tourCorpusLanding'); } catch (e) {}"
    )
    BasePage(page, live_server).load()

    # F-05 end-to-end: fill ONLY name + email — the username slug auto-derives
    # and is what actually gets created (storage key unchanged).
    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_NAME, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.fill(UserPicker.NEW_NAME, "New Bie")
    assert page.input_value(UserPicker.NEW_USERNAME) == "new-bie"
    page.fill(UserPicker.NEW_EMAIL, "new@bie.dev")
    page.click(UserPicker.CREATE_BUTTON)
    page.wait_for_function(
        "() => document.getElementById('userSelect').value === 'new-bie'",
        timeout=DEFAULT_TIMEOUT_MS,
    )

    # F-06: the smart-landing jump to Career corpus is explained in the moment.
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    title = (page.locator(Help.MODAL_TITLE).text_content() or "").lower()
    assert "corpus" in title
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Once-ever: a re-fire attempt (still armed, flag now set) stays closed.
    page.evaluate("() => _maybeFireTourStop('tourCorpusLanding', null)")
    assert page.locator(Help.MODAL).is_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_display_name_first_with_slug_suggestion(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """Name leads the form (order + focus), the slug derives live (diacritics
    stripped), and a manual username edit stops the auto-derive."""
    BasePage(page, live_server).load()
    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_NAME, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    # Display name is the FIRST field (DOM order) and receives focus.
    assert page.eval_on_selector(
        UserPicker.NEW_USER_FORM,
        "f => { const ids = [...f.querySelectorAll('input')].map(i => i.id);"
        " return ids.indexOf('newName') < ids.indexOf('newUsername'); }",
    )
    assert page.evaluate("() => document.activeElement && document.activeElement.id") == "newName"

    # Typing a name live-derives the slug (lowercase, hyphenated, de-accented).
    page.fill(UserPicker.NEW_NAME, "Áda Lovelace O'Brien")
    assert page.input_value(UserPicker.NEW_USERNAME) == "ada-lovelace-o-brien"

    # The hint is visible and the username keeps its required validation.
    hint = (page.locator(UserPicker.NEW_USERNAME_HINT).text_content() or "").lower()
    assert "edit" in hint
    assert page.get_attribute(UserPicker.NEW_USERNAME, "aria-required") == "true"

    # A manual username edit wins — further name typing no longer clobbers it.
    page.fill(UserPicker.NEW_USERNAME, "ada")
    page.fill(UserPicker.NEW_NAME, "Ada L")
    assert page.input_value(UserPicker.NEW_USERNAME) == "ada"

    # Cancel re-arms the auto-derive for the next form session.
    page.click(UserPicker.CANCEL_BUTTON)
    page.wait_for_selector(UserPicker.NEW_USER_FORM, state="hidden", timeout=DEFAULT_TIMEOUT_MS)
    page.click(UserPicker.NEW_USER_LINK)
    page.wait_for_selector(UserPicker.NEW_NAME, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.fill(UserPicker.NEW_NAME, "Grace Hopper")
    assert page.input_value(UserPicker.NEW_USERNAME) == "grace-hopper"


# ---------------------------------------------------------------------------
# F-15 — application card shows the captured employer
# ---------------------------------------------------------------------------


@pytest.mark.ux
@pytest.mark.slow
def test_application_card_shows_company_from_analyze(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Analyzing a JD with a detectable employer stamps it on the Application
    row, and the applications card renders it (was: null company)."""
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze("About Initech\n" + _JD)

    # KW7: analyze re-renders the applications block; the fresh card carries
    # the deterministically captured, title-cased employer.
    page.wait_for_selector(
        ".application-card-company", state="attached", timeout=DEFAULT_TIMEOUT_MS
    )
    company = (page.locator(".application-card-company").first.text_content() or "").lower()
    assert "initech" in company

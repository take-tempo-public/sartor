"""Regression: F-03/F-04 (UX-W1, `feat/ux-w1-skills-education`, 2026-07-07).

Two surfaces, both LLM-free (analyzer stubbed; real routes run):

- Settings drawer mode-split (F-03): the flat Skills/Certifications/Education
  fields are a ONE-TIME seed into the corpus (onboarding/corpus_import.py).
  `seed_user()` (tests/ux/seeding.py) creates a Candidate row up front — i.e.
  "corpus already provisioned" — so it doubles as the F-03 fixture: those
  three fields must show the labeled pointer, not the live input, and a
  config-only user (no Candidate row — `write_user_config` alone) must show
  the live input.
- Education + Certifications corpus editors (F-04): candidate-level Corpus
  Items, same row chrome as the existing Skills editor. add -> appears ->
  reorder -> persists through the real POST/PUT routes.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from tests.ux.seeding import seed_user, write_user_config
from ui_pages import BasePage, CorpusPage, UserPickerPage
from ui_pages.selectors import Corpus, Settings

_POINTER_ROWS = (
    Settings.SKILLS_CORPUS_ROW,
    Settings.CERTS_CORPUS_ROW,
    Settings.EDUCATION_CORPUS_ROW,
)
_FIELD_ROWS = (Settings.SKILLS_FIELD_ROW, Settings.CERTS_FIELD_ROW, Settings.EDUCATION_FIELD_ROW)


def _open_settings(page: Page, live_server: str, username: str = "alice") -> None:
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select(username)
    page.click(Settings.OPEN_PILL)
    page.wait_for_selector(Settings.DRAWER, state="visible")


@pytest.mark.ux
@pytest.mark.slow
def test_settings_pointer_shown_once_corpus_provisioned(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """seed_user() creates a Candidate row -> needs_onboarding=False -> the
    three flat fields show the labeled pointer, not the live input."""
    seed_user(ux_app, "alice")
    _open_settings(page, live_server, "alice")

    for pointer_sel, field_sel in zip(_POINTER_ROWS, _FIELD_ROWS, strict=True):
        expect(page.locator(pointer_sel)).to_be_visible()
        expect(page.locator(field_sel)).to_be_hidden()

    expect(page.locator(Settings.SKILLS_CORPUS_ROW)).to_contain_text(
        "career corpus", ignore_case=True
    )

    # The pointer's "Go to Career corpus" button closes the drawer and
    # switches to the Corpus tab.
    page.locator(Settings.SKILLS_CORPUS_ROW).get_by_role(
        "button", name=Settings.GO_TO_CORPUS_BUTTON_NAME
    ).click()
    expect(page.locator(Settings.DRAWER)).to_be_hidden()
    expect(page.locator(Corpus.PANEL)).to_be_visible()


@pytest.mark.ux
@pytest.mark.slow
def test_settings_live_field_shown_before_corpus_provisioned(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """A config-only user (no Candidate row yet) still shows the live,
    editable flat fields — this is the true "legacy" pre-provision state,
    and saving through it must keep working unchanged."""
    write_user_config(ux_app, "bob")
    _open_settings(page, live_server, "bob")

    for pointer_sel, field_sel in zip(_POINTER_ROWS, _FIELD_ROWS, strict=True):
        expect(page.locator(field_sel)).to_be_visible()
        expect(page.locator(pointer_sel)).to_be_hidden()

    page.fill(Settings.SKILLS_FIELD_ROW + " input", "Python, Kubernetes")
    page.click("text=Save config")
    expect(page.locator("#statusPill .cb-status-text")).to_contain_text(
        "config saved", ignore_case=True
    )


@pytest.mark.ux
@pytest.mark.slow
def test_education_editor_add_and_reorder_persists(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open()

    section = page.locator(Corpus.EDUCATION_SECTION)
    expect(section).to_be_visible()
    expect(page.locator(Corpus.EDUCATION_LIST).locator(".education-editor-row")).to_have_count(0)

    def _add(institution: str) -> None:
        section.get_by_role("button", name=Corpus.ADD_EDUCATION_BUTTON_NAME).click()
        page.fill("#formModal_institution", institution)
        page.click("#formModalSubmit")

    _add("First University")
    expect(page.locator(Corpus.EDUCATION_LIST).locator(".education-editor-row")).to_have_count(1)
    _add("Second College")
    rows = page.locator(Corpus.EDUCATION_LIST).locator(".education-editor-row")
    expect(rows).to_have_count(2)
    # Insertion order: First University then Second College.
    expect(rows.nth(0)).to_contain_text("First University")
    expect(rows.nth(1)).to_contain_text("Second College")

    # Reorder: move the second row up one slot via the real PUT route.
    rows.nth(1).locator(".reorder-btn", has_text="↑").click()
    expect(rows.nth(0)).to_contain_text("Second College")
    expect(rows.nth(1)).to_contain_text("First University")

    # Persistence: a fresh load re-fetches from the real GET route.
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open()
    reloaded = page.locator(Corpus.EDUCATION_LIST).locator(".education-editor-row")
    expect(reloaded).to_have_count(2)
    expect(reloaded.nth(0)).to_contain_text("Second College")
    expect(reloaded.nth(1)).to_contain_text("First University")


@pytest.mark.ux
@pytest.mark.slow
def test_certifications_editor_add_and_retire(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    seed_user(ux_app, "alice")
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    CorpusPage(page, live_server).open()

    section = page.locator(Corpus.CERTIFICATIONS_SECTION)
    expect(section).to_be_visible()

    section.get_by_role("button", name=Corpus.ADD_CERTIFICATION_BUTTON_NAME).click()
    page.fill("#formModal_name", "AWS Certified Solutions Architect")
    page.click("#formModalSubmit")

    rows = page.locator(Corpus.CERTIFICATIONS_LIST).locator(".certification-editor-row")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("AWS Certified Solutions Architect")

    # Retire (soft-delete, never hard-deleted): confirm() dialog -> accept.
    page.once("dialog", lambda d: d.accept())
    rows.first.get_by_role("button", name="Retire").click()
    expect(
        page.locator(Corpus.CERTIFICATIONS_LIST).locator(".certification-editor-row")
    ).to_have_count(0)

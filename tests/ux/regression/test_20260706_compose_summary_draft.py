"""Regression: Compose authors the 2-sentence positioning summary (D2).

Generation-experience re-architecture (fix/compose-frozen-composition). LLM-free
(the analyzer's draft_positioning_summary is stubbed; the real routes run):

- The Compose positioning card carries an editable drafted-summary textarea.
- On arrival the summary auto-drafts once (D2) — the textarea fills with the
  stubbed 2-sentence summary via the real POST /draft-summary + GET re-read.
- A hand-edit persists through the /composition POST + GET round-trip (the
  wholesale-rebuild clobber invariant: summary_text rides along on every save)
  and survives an away-and-back reload.
"""

from __future__ import annotations

import re
from types import ModuleType

import pytest
from playwright.sync_api import Page, Response, expect

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from tests.ux.stubs import install_llm_stubs
from ui_pages import (
    BasePage,
    UserPickerPage,
    WizardComposePage,
    WizardJobPage,
    WizardTemplatePage,
)
from ui_pages.selectors import Compose

_JD = "Senior Backend Engineer — Kubernetes latency at scale, Kafka, Postgres."


def _is_composition_post(resp: Response) -> bool:
    return "/composition" in resp.url and resp.request.method == "POST"


def _is_draft_summary_post(resp: Response) -> bool:
    return "/draft-summary" in resp.url and resp.request.method == "POST"


def _dump_traffic(traffic: list[Response]) -> str:
    """Render every composition/draft response, so a failure names WHERE the draft went.

    The whole reason this test cost 11 red CI runs to diagnose is that its only evidence
    was "the textarea is empty" — which is compatible with a 400, a lost update, and a
    stale render alike. Each `has_draft` below is the SERVER's own view at that render.
    """
    lines = ["--- composition / draft-summary traffic (server's view at each render) ---"]
    for resp in traffic:
        try:
            body = resp.json()
        except Exception as exc:
            lines.append(f"  {resp.request.method} {resp.status} {resp.url}  <unreadable: {exc}>")
            continue
        summary = body.get("summary") or {}
        detail = (
            f"has_draft={summary.get('has_draft')!r} "
            f"drafted_text={str(summary.get('drafted_text') or '')[:48]!r}"
            if "summary" in body
            else f"summary_text={str(body.get('summary_text') or '')[:48]!r}"
        )
        lines.append(f"  {resp.request.method} {resp.status} {resp.url.split('?')[0]}  {detail}")
    return "\n".join(lines)


def _reach_compose(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> WizardComposePage:
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)
    install_llm_stubs(ux_app, monkeypatch)
    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    return WizardComposePage(page, live_server).open()


@pytest.mark.ux
@pytest.mark.slow
def test_compose_summary_draft_autofills_edits_and_persists(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep every composition/draft response so a failure can say WHERE the summary was
    # lost instead of only "the textarea is empty". Bodies are read lazily in the
    # handler below (reading them inside a sync event handler can deadlock).
    traffic: list[Response] = []
    page.on(
        "response",
        lambda r: (
            traffic.append(r) if ("/composition" in r.url or "/draft-summary" in r.url) else None
        ),
    )

    # D2 fires the draft POST during Compose arrival. Assert the ROUTE, not just its
    # effect: a non-OK response here used to be swallowed by the client and surfaced
    # only as a still-empty textarea five seconds later — an unfalsifiable "it didn't
    # fill in" that took 11 red CI runs to trace back to a 400.
    with page.expect_response(_is_draft_summary_post) as draft_post:
        compose = _reach_compose(page, live_server, ux_app, monkeypatch)
    assert draft_post.value.ok, (
        f"POST /draft-summary returned {draft_post.value.status}: {draft_post.value.text()}"
    )
    # A 200 is not enough: the route pops summary_text when the draft comes back empty,
    # so "persisted nothing" also looks like success. Assert it actually persisted.
    assert draft_post.value.json().get("summary_text"), (
        f"POST /draft-summary was 200 but persisted an EMPTY summary_text: "
        f"{draft_post.value.json()}"
    )

    # D2 — the summary auto-drafts once on arrival; the textarea fills with the
    # stubbed 2-sentence draft (expect() retries until the async draft lands).
    draft = page.locator(Compose.POSITIONING_DRAFT)
    try:
        expect(draft).to_have_value(re.compile(r"Stubbed positioning summary"))
    except AssertionError as exc:  # pragma: no cover - only on the flake under diagnosis
        # The POST persisted the summary (asserted above) but the rendered composition
        # does not have it. Print the server's own view at every render so the next
        # reader can see exactly which response dropped it — a lost update on the
        # context file, or a stale render winning the race.
        raise AssertionError(f"{exc}\n\n{_dump_traffic(traffic)}") from exc

    # Hand-edit → the oninput debounced autosave POSTs the new summary_text.
    with page.expect_response(_is_composition_post):
        draft.fill("My own hand-written summary. Two concrete sentences here.")

    # Away + back: the edited draft survives (persisted in composition_overrides,
    # rehydrated by the GET). The auto-draft does NOT overwrite it (has_draft).
    WizardTemplatePage(page, live_server).open()
    compose.reload()
    expect(page.locator(Compose.POSITIONING_DRAFT)).to_have_value(
        "My own hand-written summary. Two concrete sentences here."
    )

    # Retire clears the draft (falls back to saved positioning).
    page.locator(Compose.POSITIONING_DRAFT_RETIRE).click()
    expect(page.locator(Compose.POSITIONING_DRAFT)).to_have_value("")

"""The UI must not offer PDF on a machine that cannot render one (item 103).

Observed 2026-09-02, macOS 12.7.4: `python -m playwright install chromium` failed
(current Playwright ships no Chromium build for macOS 12). Setup reported it as a
warning and continued -- correctly, since `docs/install.md` states PDF is optional.
The gap was everything after: Chromium's absence was a *warning* at setup time and
an *exception* at use time, with nothing in between. Both PDF buttons stayed
selectable, and a user who accepted the setup warning had no way to know which of
the offered output formats would actually work.

These tests drive the real shell route with the capability flag forced both ways.
They never launch a browser and never touch a real Playwright install -- the point
of `preflight.pdf_available()` is that it is a cheap, patchable boolean.

Evidence: `docs/dev/diagnosis/install-onboarding-preflight.md`.
"""

from __future__ import annotations

import pytest

import preflight
from blueprints import users as users_bp_module


@pytest.fixture(autouse=True)
def _clear_probe_cache():
    preflight.pdf_available.cache_clear()
    yield
    preflight.pdf_available.cache_clear()


def _shell(client, monkeypatch, *, available: bool) -> str:
    """Render the app shell with `pdf_available` forced to `available`."""
    monkeypatch.setattr(users_bp_module, "pdf_available", lambda: available)
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


class TestPdfOfferedWhenAvailable:
    def test_both_pdf_buttons_are_live(self, client, monkeypatch):
        html = _shell(client, monkeypatch, available=True)
        assert "setOutputFormat('.pdf', this)" in html
        assert "setCoverFormat('.pdf', this)" in html

    def test_no_unavailability_hint_is_shown(self, client, monkeypatch):
        html = _shell(client, monkeypatch, available=True)
        assert "pdfUnavailableHint" not in html
        assert "coverPdfUnavailableHint" not in html


class TestPdfWithheldWhenUnavailable:
    def test_resume_pdf_button_is_disabled_not_merely_hidden(self, client, monkeypatch):
        """Disabled, not removed: the format is real, this machine just can't render it.

        Removing the button would leave a user wondering whether Sartor does PDF at
        all; disabling it with a reason says 'yes, but not here, and here is why'.
        """
        html = _shell(client, monkeypatch, available=False)
        assert 'id="fmtPdf"' in html
        assert "disabled" in html
        assert "setOutputFormat('.pdf', this)" not in html

    def test_cover_letter_pdf_button_is_disabled_too(self, client, monkeypatch):
        """Item 103 names both surfaces; fixing only the resume one leaves half the bug."""
        html = _shell(client, monkeypatch, available=False)
        assert 'id="coverFmtPdf"' in html
        assert "setCoverFormat('.pdf', this)" not in html

    def test_a_visible_reason_is_rendered_not_just_a_tooltip(self, client, monkeypatch):
        """A title attribute is invisible to anyone not hovering exactly the right pixel."""
        html = _shell(client, monkeypatch, available=False)
        assert 'id="pdfUnavailableHint"' in html
        assert "sartor --setup" in html

    def test_the_hint_points_at_the_outputs_that_do_work(self, client, monkeypatch):
        """The documented posture is 'degrade to DOCX/Markdown'; the UI should say so."""
        html = _shell(client, monkeypatch, available=False)
        assert "DOCX/Markdown" in html

    def test_disabled_state_is_exposed_to_assistive_tech(self, client, monkeypatch):
        html = _shell(client, monkeypatch, available=False)
        assert 'aria-disabled="true"' in html

    def test_docx_and_markdown_stay_selectable(self, client, monkeypatch):
        """Losing PDF must not degrade the formats that never needed Chromium."""
        html = _shell(client, monkeypatch, available=False)
        assert "setOutputFormat('.docx', this)" in html
        assert "setOutputFormat('.md', this)" in html
        assert "setCoverFormat('.docx', this)" in html


class TestProbeIsNotCalledPerRequest:
    def test_the_shell_route_uses_the_cached_probe(self, client, monkeypatch):
        """The capability cannot change while the process lives; probing per page load
        would put a filesystem walk in the request path for a constant."""
        calls: list[int] = []
        monkeypatch.setattr(preflight, "chromium_capability", lambda: calls.append(1) or _AVAILABLE)
        preflight.pdf_available.cache_clear()
        for _ in range(5):
            client.get("/")
        assert len(calls) <= 1, f"probed {len(calls)} times across 5 page loads"


_AVAILABLE = preflight.Capability("chromium", "Chromium (PDF output)", True, "installed")

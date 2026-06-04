"""Tests for `pdf_render` (Phase β.3).

Two test classes:

  - TestHtmlRender (fast): exercises render_html_string + the
    html_template_path_for resolver. No browser launch; runs in
    milliseconds. Covers the contract that the Jinja2 template
    consumes: which JSON Resume keys it reads, how missing fields
    are handled, what the resolver returns for various inputs.

  - TestPdfRenderEndToEnd (slow, network-dep marker): actually
    launches Chromium and writes a real PDF. Marked `slow` so
    `pytest -m "not slow"` skips it locally; CI is configured to
    run it. Requires `python -m playwright install chromium` to
    have run on the host.

The Chromium binary is ~150MB; it lives in the OS user cache
(NOT in the repo); see pyproject.toml dependencies for the install
command.
"""

from __future__ import annotations

import pytest

# -------------------------------------------------------------------
# HTML render — fast, no browser
# -------------------------------------------------------------------


@pytest.fixture
def classic_template_path():
    """Resolve the bundled Classic HTML template path."""
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "personas" / "bundled" / "classic.html"


class TestHtmlTemplatePathFor:
    def test_resolves_docx_to_html_sibling(self, classic_template_path):
        from pdf_render import html_template_path_for
        docx = classic_template_path.with_suffix(".docx")
        result = html_template_path_for(str(docx))
        assert result is not None
        assert result.suffix == ".html"
        assert result.exists()

    def test_returns_none_for_persona_without_html_companion(self, tmp_path):
        from pdf_render import html_template_path_for
        lonely_docx = tmp_path / "no_companion.docx"
        lonely_docx.write_bytes(b"")  # empty file so .exists() returns True
        result = html_template_path_for(str(lonely_docx))
        assert result is None

    def test_returns_none_for_nonexistent_docx(self, tmp_path):
        from pdf_render import html_template_path_for
        # Even if the docx itself is missing, the sibling resolver
        # only cares about the html sibling — which also won't exist.
        result = html_template_path_for(str(tmp_path / "nope.docx"))
        assert result is None


class TestHtmlRender:
    """The HTML render is the source of truth that feeds BOTH the PDF
    output and the live in-app preview. These tests pin down what
    the Jinja2 template reads from the JSON Resume document so that
    template changes are caught by tests, not by user reports."""

    def test_renders_basics_block(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {
            "basics": {
                "name":  "Casey Rivera",
                "label": "Principal Product Designer",
                "email": "casey@example.com",
                "phone": "555-0142",
            },
        }
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Casey Rivera" in html
        assert "Principal Product Designer" in html
        assert "casey@example.com" in html
        assert "555-0142" in html

    def test_renders_summary(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {"basics": {"name": "X", "summary": "Senior designer with a decade of experience."}}
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Senior designer with a decade of experience." in html
        # Summary section header should appear
        assert "Summary" in html

    def test_renders_work_with_highlights(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {
            "basics": {"name": "X"},
            "work": [{
                "name":       "Polaris Cognition",
                "position":   "Senior Designer",
                "startDate":  "2022-09",
                "endDate":    "present",
                "summary":    "Player-coach across product design.",
                "highlights": [
                    "Shipped a thing.",
                    "Led another thing.",
                ],
            }],
        }
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Polaris Cognition" in html
        assert "Senior Designer" in html
        assert "2022-09" in html
        assert "present" in html
        assert "Shipped a thing." in html
        assert "Led another thing." in html

    def test_renders_skills_flat(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {
            "basics": {"name": "X"},
            "skills": [
                {"name": "Python"},
                {"name": "TypeScript"},
                {"name": "Figma"},
            ],
        }
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Python" in html
        assert "TypeScript" in html
        assert "Figma" in html
        # Flat (no keywords) form uses the · separator
        assert " · " in html

    def test_renders_skills_grouped(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {
            "basics": {"name": "X"},
            "skills": [
                {"name": "Languages", "keywords": ["Python", "TypeScript", "Rust"]},
                {"name": "Infra",     "keywords": ["Kubernetes", "Terraform"]},
            ],
        }
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "<strong>Languages:</strong>" in html
        assert "Python, TypeScript, Rust" in html
        assert "<strong>Infra:</strong>" in html

    def test_renders_education_certificates(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {
            "basics":       {"name": "X"},
            "education":    [{"institution": "Polytechnic", "area": "MS HCI",
                              "startDate": "2014", "endDate": "2016"}],
            "certificates": [{"name": "Nielsen Norman UX Master"}],
        }
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Polytechnic" in html
        assert "MS HCI" in html
        assert "Nielsen Norman UX Master" in html

    def test_handles_missing_sections_gracefully(self, classic_template_path):
        from pdf_render import render_html_string
        doc = {"basics": {"name": "Just a Name"}}
        html = render_html_string(doc, html_template_path=classic_template_path)
        assert "Just a Name" in html
        # No work section should render
        assert "Experience" not in html
        # No skills section
        assert "Skills" not in html

    def test_raises_when_template_missing(self, tmp_path):
        from pdf_render import render_html_string
        with pytest.raises(FileNotFoundError):
            render_html_string({"basics": {"name": "X"}},
                               html_template_path=tmp_path / "missing.html")


# -------------------------------------------------------------------
# Cover-letter render — fast, no browser (v1.0.5 Step 6 redesign)
# -------------------------------------------------------------------


@pytest.fixture
def cover_letter_template_path():
    """Resolve the shared business-letter cover-letter template path."""
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "personas" / "cover_letter.html"


@pytest.fixture
def bundled_css_dir():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "personas" / "bundled"


class TestPersonaFontFamily:
    """`persona_font_family` extracts the base body font from a persona CSS so
    the cover-letter preview can match the résumé (plainly)."""

    def test_extracts_single_line_stack(self, bundled_css_dir):
        from pdf_render import persona_font_family
        value = persona_font_family(bundled_css_dir / "classic.css")
        assert "Helvetica Neue" in value
        assert value.endswith("sans-serif")
        assert "\n" not in value

    def test_collapses_multiline_value(self, bundled_css_dir):
        # modern.css and spacious.css wrap the font-family value across lines.
        from pdf_render import persona_font_family
        modern = persona_font_family(bundled_css_dir / "modern.css")
        assert "Roboto" in modern
        assert "Liberation Sans" in modern
        assert modern.endswith("sans-serif")
        assert "\n" not in modern  # newline collapsed

        spacious = persona_font_family(bundled_css_dir / "spacious.css")
        assert "Georgia" in spacious
        assert spacious.endswith("serif")
        assert "\n" not in spacious

    def test_falls_back_when_none(self):
        from pdf_render import _DEFAULT_COVER_LETTER_FONT, persona_font_family
        assert persona_font_family(None) == _DEFAULT_COVER_LETTER_FONT

    def test_falls_back_when_missing_file(self, tmp_path):
        from pdf_render import _DEFAULT_COVER_LETTER_FONT, persona_font_family
        assert persona_font_family(tmp_path / "nope.css") == _DEFAULT_COVER_LETTER_FONT

    def test_falls_back_when_no_rule(self, tmp_path):
        from pdf_render import _DEFAULT_COVER_LETTER_FONT, persona_font_family
        css = tmp_path / "blank.css"
        css.write_text("body { color: #111; }", encoding="utf-8")
        assert persona_font_family(css) == _DEFAULT_COVER_LETTER_FONT


class TestCoverLetterRender:
    """`render_cover_letter_html` renders generated cover-letter text into a
    styled business-letter HTML string. Deterministic — no LLM, no browser."""

    def test_renders_body_text(self, cover_letter_template_path):
        from pdf_render import render_cover_letter_html
        md = (
            "June 4, 2026\n"
            "Hiring Manager, Acme Corp\n\n"
            "Dear Hiring Manager,\n\n"
            "I rebuilt three distributed systems after scaling a platform to 4M users.\n\n"
            "Sincerely,\nPriya Patel"
        )
        html = render_cover_letter_html(
            md, font_family='"Helvetica Neue", Helvetica, sans-serif',
            template_path=cover_letter_template_path,
        )
        assert "Hiring Manager, Acme Corp" in html
        assert "distributed systems" in html
        assert "Priya Patel" in html

    def test_injects_font_family_unescaped(self, cover_letter_template_path):
        # The font stack carries double-quotes; they must survive into the
        # <style> block (autoescaping them to &#34; would break the CSS).
        from pdf_render import render_cover_letter_html
        html = render_cover_letter_html(
            "Hello.", font_family='"Helvetica Neue", Helvetica, sans-serif',
            template_path=cover_letter_template_path,
        )
        assert '"Helvetica Neue", Helvetica, sans-serif' in html
        assert "&#34;Helvetica Neue&#34;" not in html
        assert "&quot;Helvetica Neue&quot;" not in html

    def test_addressee_lines_break_inline(self, cover_letter_template_path):
        # Single newlines in the header block become <br> (nl2br) so the date /
        # addressee / salutation flow inline with the body — not a styled block.
        from pdf_render import render_cover_letter_html
        md = "June 4, 2026\nHiring Manager\nAcme Corp\n\nDear Hiring Manager,"
        html = render_cover_letter_html(
            md, font_family="serif", template_path=cover_letter_template_path,
        )
        assert "<br" in html  # nl2br emitted line breaks within the block

    def test_blank_lines_make_paragraphs(self, cover_letter_template_path):
        from pdf_render import render_cover_letter_html
        md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        html = render_cover_letter_html(
            md, font_family="serif", template_path=cover_letter_template_path,
        )
        assert html.count("<p>") >= 3

    def test_empty_markdown_does_not_crash(self, cover_letter_template_path):
        from pdf_render import render_cover_letter_html
        html = render_cover_letter_html(
            "", font_family="serif", template_path=cover_letter_template_path,
        )
        # Shell still renders; the cover-letter container is present.
        assert "cover-letter" in html

    def test_raises_when_template_missing(self, tmp_path):
        from pdf_render import render_cover_letter_html
        with pytest.raises(FileNotFoundError):
            render_cover_letter_html(
                "Hi.", font_family="serif",
                template_path=tmp_path / "missing.html",
            )


# -------------------------------------------------------------------
# End-to-end PDF render — slow, requires Chromium installed
# -------------------------------------------------------------------


def _chromium_available() -> bool:
    """Detect whether the Playwright browser binary is installed."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


@pytest.mark.slow
@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium not installed — run `python -m playwright install chromium`",
)
class TestPdfRenderEndToEnd:
    def test_writes_real_pdf(self, classic_template_path, tmp_path):
        from pdf_render import render_pdf

        doc = {
            "basics": {
                "name":  "Test Resume",
                "label": "Engineer",
                "email": "test@example.com",
            },
            "work": [{
                "name":       "Acme Cloud",
                "position":   "SRE",
                "startDate":  "2023",
                "endDate":    "present",
                "highlights": ["Built something deterministic."],
            }],
        }

        output = tmp_path / "out.pdf"
        result = render_pdf(doc,
                            html_template_path=classic_template_path,
                            output_pdf_path=output)
        assert result.exists()
        assert result.stat().st_size > 1000  # something more than an empty PDF
        # Verify the PDF magic bytes
        assert result.read_bytes()[:4] == b"%PDF"

    def test_pdf_contains_resume_text(self, classic_template_path, tmp_path):
        """Round-trip: render PDF, re-extract text via pdfplumber,
        verify the candidate name + a highlight are in the rendered text."""
        import pdfplumber

        from pdf_render import render_pdf

        doc = {
            "basics": {"name": "Roundtrip Candidate", "label": "Engineer"},
            "work": [{
                "name":       "Test Co",
                "position":   "SRE",
                "startDate":  "2023",
                "endDate":    "present",
                "highlights": ["Stamped this exact sentence into a PDF."],
            }],
        }
        output = tmp_path / "rt.pdf"
        render_pdf(doc,
                   html_template_path=classic_template_path,
                   output_pdf_path=output)

        with pdfplumber.open(str(output)) as pdf:
            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)

        assert "Roundtrip Candidate" in full_text
        assert "Stamped this exact sentence into a PDF." in full_text


@pytest.mark.slow
@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium not installed — run `python -m playwright install chromium`",
)
class TestCoverLetterPdfRenderEndToEnd:
    """The cover-letter `.pdf` output (feat/cover-letter-formats). Renders
    through the SAME `personas/cover_letter.html` shell that feeds the Step-6
    preview, so the download is byte-faithful to what the user previewed."""

    def test_writes_real_pdf(self, cover_letter_template_path, tmp_path):
        from pdf_render import render_cover_letter_pdf

        md = (
            "June 4, 2026\n"
            "Hiring Manager, Acme Corp\n\n"
            "Dear Hiring Manager,\n\n"
            "I rebuilt three distributed systems after scaling a platform to 4M users.\n\n"
            "Sincerely,\nPriya Patel"
        )
        output = tmp_path / "cover.pdf"
        result = render_cover_letter_pdf(
            md,
            font_family='"Helvetica Neue", Helvetica, sans-serif',
            template_path=cover_letter_template_path,
            output_pdf_path=output,
        )
        assert result.exists()
        assert result.stat().st_size > 1000
        assert result.read_bytes()[:4] == b"%PDF"

    def test_pdf_contains_cover_letter_text(self, cover_letter_template_path, tmp_path):
        """Round-trip: render, re-extract via pdfplumber, verify the addressee
        and a body sentence survived into the rendered PDF."""
        import pdfplumber

        from pdf_render import render_cover_letter_pdf

        md = (
            "June 4, 2026\n"
            "Hiring Manager, Test Co\n\n"
            "Dear Hiring Manager,\n\n"
            "Stamped this exact cover-letter sentence into a PDF.\n\n"
            "Sincerely,\nRoundtrip Candidate"
        )
        output = tmp_path / "cover_rt.pdf"
        render_cover_letter_pdf(
            md,
            font_family="serif",
            template_path=cover_letter_template_path,
            output_pdf_path=output,
        )

        with pdfplumber.open(str(output)) as pdf:
            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)

        assert "Hiring Manager, Test Co" in full_text
        assert "Stamped this exact cover-letter sentence into a PDF." in full_text
        assert "Roundtrip Candidate" in full_text

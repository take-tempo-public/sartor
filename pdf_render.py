"""PDF rendering — Playwright (headless Chromium) + Jinja2.

Phase β.3 per docs/PRODUCT_SHAPE.md §6.3. The decision was reassessed
mid-build: WeasyPrint requires GTK3 / Pango system libraries on Windows
+ macOS (the "pip-installable, no system deps" claim was incorrect),
so we switched to Playwright + headless Chromium. The Chromium binary
is a one-time ~150MB download via `python -m playwright install
chromium`; it's stored OUTSIDE the repo (per-OS user cache path).

Why Chromium-via-Playwright:
  - Perfect CSS support — anything that renders in Chromium renders
    identically in the PDF, including modern flex/grid (which ATS-safe
    layouts avoid anyway) and web fonts.
  - The SAME HTML+CSS template that produces the PDF also feeds the
    in-app live preview (β.4) — true WYSIWYG.
  - No system-level dependency beyond the one-time Chromium download.
  - Pip-installable and cross-platform (Windows, macOS, Linux).

Why not WeasyPrint:
  - GTK3 + Pango required on Windows/macOS. Acceptable for a hosted
    product; awkward for a local-first single-tenant dev tool that
    users install via `pip install callback`.

Render pipeline:
  json_resume_doc + persona_html_template + persona_css
    → Jinja2 renders HTML string
    → Playwright loads the HTML (file URL so the CSS link resolves)
    → page.pdf() emits the PDF bytes
    → write to disk

The Jinja2 template is the SOURCE OF TRUTH for both the PDF and the
live preview. Adding a new persona means: drop classic.html +
classic.css next to the .docx file in personas/bundled/ (or
personas/{candidate_id}/ for user uploads).
"""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Neutral business-letter fallback when a persona CSS has no readable
# font-family rule. Matches the Classic persona's stack.
_DEFAULT_COVER_LETTER_FONT = (
    '"Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif'
)

# First `font-family:` declaration in a CSS file, captured up to its `;`
# (values may wrap across lines — see modern.css / spacious.css).
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;{}]+)", re.IGNORECASE)


def html_template_path_for(docx_template_path: str | Path) -> Path | None:
    """Resolve the HTML template that companions a given persona .docx.

    Convention: `personas/bundled/classic.docx` →
    `personas/bundled/classic.html` + `personas/bundled/classic.css`.
    Returns the .html path if it exists on disk, else None.
    """
    docx = Path(docx_template_path)
    html = docx.with_suffix(".html")
    return html if html.exists() else None


def render_pdf(
    json_resume: dict[str, Any],
    *,
    html_template_path: str | Path,
    output_pdf_path: str | Path,
    chromium_args: list[str] | None = None,
) -> Path:
    """Render a JSON Resume document to PDF via Jinja2 + Playwright.

    Args:
        json_resume: A JSON Resume v1.0 dict (as produced by
            `json_resume.md_to_json_resume`). The template consumes
            top-level keys: basics / work / skills / education /
            certificates / projects.
        html_template_path: Path to the Jinja2 HTML template. The
            template's CSS reference (e.g. `<link rel="stylesheet"
            href="classic.css">`) is resolved RELATIVE to this path,
            so the .css must live next to the .html on disk.
        output_pdf_path: Where to write the resulting PDF.
        chromium_args: Optional override of the launch args for tests
            or sandboxed environments. Default empty (Playwright's
            built-in defaults).

    Returns:
        The output path as a Path object.

    Raises:
        FileNotFoundError if the HTML template is missing.
        RuntimeError if Playwright fails to launch (Chromium not
        installed → user must run `python -m playwright install
        chromium`).
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from playwright.sync_api import sync_playwright

    html_path = Path(html_template_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(
            f"HTML persona template not found at {html_path}. "
            f"PDF rendering requires an .html + .css pair alongside the .docx."
        )

    out_path = Path(output_pdf_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Render the template to a string via Jinja2
    env = Environment(
        loader=FileSystemLoader(str(html_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    template = env.get_template(html_path.name)
    html_str = template.render(**json_resume)

    # Write the rendered HTML to a temp file in the SAME directory as the
    # template so relative `<link href="classic.css">` resolves correctly.
    # Playwright loads this via file:// so Chromium's same-origin policy
    # applies — same-dir + file:// gives us local CSS access without
    # data:// URI escaping headaches.
    tmp_html: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", dir=str(html_path.parent),
            delete=False, encoding="utf-8",
        ) as tmp:
            tmp.write(html_str)
            tmp_html = Path(tmp.name)

        with sync_playwright() as p:
            browser = p.chromium.launch(args=chromium_args or [])
            try:
                page = browser.new_page()
                page.goto(tmp_html.as_uri(), wait_until="load")
                page.pdf(
                    path=str(out_path),
                    format="Letter",
                    margin={"top": "0.6in", "bottom": "0.6in",
                            "left": "0.65in", "right": "0.65in"},
                    print_background=True,
                )
            finally:
                browser.close()
    finally:
        if tmp_html is not None and tmp_html.exists():
            try:
                tmp_html.unlink()
            except OSError as exc:
                logger.warning("Could not remove temp HTML %s: %s", tmp_html, exc)

    return out_path


def render_html_string(
    json_resume: dict[str, Any],
    *,
    html_template_path: str | Path,
) -> str:
    """Render the Jinja2 template to a string without invoking Chromium.

    Used by β.4 (live in-app preview) where the browser already does the
    final render. Cheap — no subprocess, no PDF cost. Shape-identical to
    what `render_pdf` would print, so the in-app preview IS the future
    PDF (WYSIWYG).
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    html_path = Path(html_template_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(
            f"HTML persona template not found at {html_path}."
        )

    env = Environment(
        loader=FileSystemLoader(str(html_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    template = env.get_template(html_path.name)
    return template.render(**json_resume)


def persona_font_family(css_path: str | Path | None) -> str:
    """Extract the base `font-family` declaration from a persona's CSS.

    The cover-letter preview matches the chosen résumé persona's font (plainly)
    per the 2026-05-26 styling decisions. The first `font-family` rule in each
    bundled persona CSS is its base body font (verified across classic / modern
    / spacious / tech). Values that wrap across lines are normalized to a single
    line. Falls back to a neutral business stack when the CSS is missing,
    unreadable, or has no rule.

    Deterministic — no LLM, no I/O beyond reading the given CSS.
    """
    if css_path is None:
        return _DEFAULT_COVER_LETTER_FONT
    p = Path(css_path)
    if not p.exists():
        return _DEFAULT_COVER_LETTER_FONT
    try:
        css = p.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read persona CSS %s for font: %s", p, exc)
        return _DEFAULT_COVER_LETTER_FONT
    match = _FONT_FAMILY_RE.search(css)
    if not match:
        return _DEFAULT_COVER_LETTER_FONT
    # Collapse internal whitespace (incl. the newlines of wrapped values) so
    # the result is a single, valid `font-family` value.
    value = " ".join(match.group(1).split())
    return value or _DEFAULT_COVER_LETTER_FONT


def render_cover_letter_html(
    cover_letter_markdown: str,
    *,
    font_family: str,
    template_path: str | Path,
) -> str:
    """Render cover-letter text into a styled business-letter HTML string.

    The mirror of `render_html_string` for the cover letter: the shared
    `personas/cover_letter.html` shell + the chosen persona's font, used by the
    Step 6 cover-letter live preview. The generated cover letter is plain text
    (date / addressee / salutation / paragraphs / close); it is converted to
    HTML with the `nl2br` extension so the header lines keep their single-line
    breaks and flow inline with the body, while blank-line-separated paragraphs
    become `<p>` blocks.

    Deterministic — no LLM. PDF/Markdown cover-letter OUTPUT is a separate
    concern (the cover-letter-formats branch); this is preview-only.
    """
    import markdown as _markdown
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    html_path = Path(template_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(
            f"Cover-letter HTML template not found at {html_path}."
        )

    body_html = _markdown.markdown(cover_letter_markdown or "", extensions=["nl2br"])

    env = Environment(
        loader=FileSystemLoader(str(html_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    template = env.get_template(html_path.name)
    return template.render(body_html=body_html, font_family=font_family)

"""Tests for docx_to_persona_html — the uploaded-persona HTML+CSS companion generator.

Deterministic module (charter C-6). Covers:
  - round-trip extraction: each bundled .docx re-yields its TypographyPreset knobs
    (clean oracle — the presets ARE the ground truth the .docx was built from);
  - companion emit: .html (skeleton contract preserved, CSS href swapped) + .css
    (uploaded typography) + fidelity sidecar;
  - honest fidelity fallback on non-single-column sources (tables);
  - the integration invariant that makes the preview stop falling back to Classic:
    after generation, `pdf_render.html_template_path_for` resolves the companion.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

import docx_to_persona_html as d
from scripts.build_bundled_templates import PRESETS

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BUNDLED = _REPO_ROOT / "personas" / "bundled"


@pytest.mark.parametrize("preset", PRESETS, ids=lambda p: p.filename)
def test_extract_matches_bundled_preset(preset) -> None:
    """Extracting a bundled .docx reconstructs the TypographyPreset it was built from."""
    knobs = d.extract_persona_style(_BUNDLED / preset.filename)

    assert knobs["font_family"] == preset.font_family
    assert knobs["name_pt"] == pytest.approx(preset.name_pt)
    assert knobs["heading_pt"] == pytest.approx(preset.section_heading_pt)
    assert knobs["base_font_pt"] == pytest.approx(preset.body_pt)
    assert knobs["line_spacing"] == pytest.approx(preset.line_spacing)
    assert knobs["heading_uppercase"] is preset.section_heading_uppercase
    assert knobs["heading_small_caps"] is preset.section_heading_small_caps
    assert knobs["heading_underline"] is preset.section_heading_underline
    assert knobs["margin_left_in"] == pytest.approx(preset.margin_inches)
    # All bundled templates are single-column running text.
    assert knobs["layout_fidelity"] == "full"


def test_generate_companion_writes_html_css_sidecar(tmp_path) -> None:
    """generate_companion emits .html + .css + fidelity sidecar next to the .docx."""
    docx = tmp_path / "mine.docx"
    shutil.copy(_BUNDLED / "tech.docx", docx)  # Georgia + underlined headings

    result = d.generate_companion(docx)
    assert result is not None
    html_path, css_path = result
    assert html_path == tmp_path / "mine.html"
    assert css_path == tmp_path / "mine.css"

    css = css_path.read_text(encoding="utf-8")
    # The uploaded template's OWN font reaches the preview CSS (not Classic's stack).
    assert "Georgia" in css
    assert "text-decoration: underline" in css  # tech's underlined headings

    # HTML preserves the classic.html Jinja2 contract, swapping only the CSS href.
    html = html_path.read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="mine.css">' in html
    skeleton = (_BUNDLED / "classic.html").read_text(encoding="utf-8")
    assert html == skeleton.replace('href="classic.css"', 'href="mine.css"')

    sidecar = tmp_path / "mine.persona.json"
    assert '"layout_fidelity": "full"' in sidecar.read_text(encoding="utf-8")


def test_generate_companion_resolvable_via_html_template_path_for(tmp_path) -> None:
    """After generation the preview route resolves the companion (no Classic fallback).

    `preview_application_html` / `_render_pdf_from_json` fall back to Classic only
    when `html_template_path_for` returns None. This asserts the fallback no longer
    fires for an uploaded template once its companion exists (walkthrough B2/B3).
    """
    from pdf_render import html_template_path_for

    docx = tmp_path / "owned.docx"
    shutil.copy(_BUNDLED / "spacious.docx", docx)
    assert html_template_path_for(docx) is None  # nothing before generation

    d.generate_companion(docx)
    resolved = html_template_path_for(docx)
    assert resolved == tmp_path / "owned.html"


def test_generate_companion_idempotent(tmp_path) -> None:
    """A second call is a no-op cache hit (companion newer than the .docx)."""
    docx = tmp_path / "mine.docx"
    shutil.copy(_BUNDLED / "modern.docx", docx)

    first = d.generate_companion(docx)
    assert first is not None
    mtime = first[1].stat().st_mtime_ns

    second = d.generate_companion(docx)
    assert second == first
    assert second[1].stat().st_mtime_ns == mtime  # not rewritten


def test_detect_layout_fidelity_flags_tables(tmp_path) -> None:
    """A .docx with a table is not single-column-representable → typography_only."""
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # name role
    run = p.add_run("Casey Rivera")
    run.font.size = Pt(18)
    doc.add_table(rows=2, cols=2)
    docx = tmp_path / "fancy.docx"
    doc.save(str(docx))

    assert d.detect_layout_fidelity(Document(str(docx))) == "typography_only"
    knobs = d.extract_persona_style(docx)
    assert knobs["layout_fidelity"] == "typography_only"
    # Even on a fancy source we still extract typography for a clean single-column
    # preview (matches what _write_docx produces on download).
    result = d.generate_companion(docx)
    assert result is not None
    assert '"layout_fidelity": "typography_only"' in (
        tmp_path / "fancy.persona.json"
    ).read_text(encoding="utf-8")


def test_generate_companion_missing_docx_returns_none(tmp_path) -> None:
    """Best-effort: an unreadable .docx yields None (caller falls back to Classic)."""
    assert d.generate_companion(tmp_path / "does-not-exist.docx") is None

"""Document output generation — P1 Hardening.

Deterministic conversion of LLM-generated content into downloadable documents.
When the primary resume is .docx, it is opened as a style template so the
output inherits the original's fonts, margins, heading styles, and list
formatting exactly. For PDF or Markdown originals, clean defaults are used.
"""

import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Matches any common bullet prefix: -, *, •, –, —, ·
BULLET_RE = re.compile(r"^[-*\u2022\u2013\u2014\u00b7]\s+")


def generate_resume(
    content: str,
    output_format: str,
    username: str,
    base_dir: str = "output",
    template_path: str = None,
) -> str:
    """Generate the tailored resume in the requested format."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == ".md":
        path = out_dir / f"resume_{ts}.md"
        path.write_text(content, encoding="utf-8")
    else:
        path = out_dir / f"resume_{ts}.docx"
        _write_docx(content, path, template_path=template_path)

    return str(path)


def generate_cover_letter(content: str, username: str, base_dir: str = "output") -> str:
    """Generate the cover letter as .docx (always — no template needed)."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"cover_letter_{ts}.docx"
    _write_docx(content, path, is_cover_letter=True)
    return str(path)


def _extract_list_numPr(doc: docx.Document):
    """Return a deep copy of the numPr element from the first List Paragraph, or None."""
    for p in doc.paragraphs:
        if p.style.name == "List Paragraph":
            pPr = p._element.find(qn("w:pPr"))
            if pPr is not None:
                numPr = pPr.find(qn("w:numPr"))
                if numPr is not None:
                    return deepcopy(numPr)
    return None


def _clear_body(doc: docx.Document) -> None:
    """Remove all paragraph and table elements from the document body.

    Preserves the final w:sectPr (section/margin properties) which Word
    stores as a direct child of w:body — it is not a w:p or w:tbl element.
    """
    body = doc.element.body
    for child in list(body):
        tag = child.tag.split("}")[-1]
        if tag in ("p", "tbl"):
            body.remove(child)


def _apply_numPr(paragraph, numPr_template) -> None:
    """Attach list numbering properties to a paragraph element."""
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        paragraph._element.insert(0, pPr)
    # Remove any existing numPr before inserting
    existing = pPr.find(qn("w:numPr"))
    if existing is not None:
        pPr.remove(existing)
    # Insert at position 0 so it precedes other pPr children
    pPr.insert(0, deepcopy(numPr_template))


def _write_docx(
    content: str,
    path: Path,
    template_path: str = None,
    is_cover_letter: bool = False,
) -> None:
    """Write LLM content to .docx, using the original file as a style template
    when it is a .docx. Falls back to clean built-in defaults otherwise.

    Markdown heading levels:
      # Name / title line  →  large bold Normal (centered for resume)
      ## Section heading   →  Heading 1 style (from template) or bold 13pt
      ### Job/company line →  bold Normal
      - / • / – bullet     →  List Paragraph + numbering (from template) or List Bullet
    """
    tp = Path(template_path) if template_path else None
    use_template = bool(tp and tp.exists() and tp.suffix.lower() == ".docx")

    if use_template:
        doc = docx.Document(str(tp))
        # Capture the list numPr before clearing content
        orig_numPr = _extract_list_numPr(doc)
        _clear_body(doc)
    else:
        orig_numPr = None
        doc = docx.Document()
        # Sensible defaults for non-docx originals
        normal = doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(11)
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.85)
            section.right_margin = Inches(0.85)

    for line in content.split("\n"):
        stripped = line.strip()

        if not stripped:
            doc.add_paragraph("")
            continue

        # ── # Name / header line ──────────────────────────────────────────
        if stripped.startswith("# "):
            text = stripped[2:]
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
            if use_template:
                # Inherit template font; bump to a readable title size
                run.font.size = Pt(16)
            else:
                run.font.size = Pt(16)
            if not is_cover_letter:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # ── ## Section heading ────────────────────────────────────────────
        elif stripped.startswith("## "):
            text = stripped[3:]
            if use_template:
                # Use the original document's Heading 1 style exactly
                p = doc.add_paragraph(text, style="Heading 1")
            else:
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.bold = True
                run.font.size = Pt(13)
                p.paragraph_format.space_after = Pt(2)

        # ── ### Job title / company line ──────────────────────────────────
        elif stripped.startswith("### "):
            text = stripped[4:]
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
            if not use_template:
                run.font.size = Pt(11)

        # ── Bullet point (any common marker) ─────────────────────────────
        elif BULLET_RE.match(stripped):
            text = BULLET_RE.sub("", stripped)
            if use_template and orig_numPr is not None:
                p = doc.add_paragraph(text, style="List Paragraph")
                _apply_numPr(p, orig_numPr)
            else:
                doc.add_paragraph(text, style="List Bullet")

        # ── Plain body text ───────────────────────────────────────────────
        else:
            doc.add_paragraph(stripped)

    doc.save(str(path))

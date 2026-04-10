"""Document output generation — P1 Hardening.

Deterministic conversion of LLM-generated content into downloadable documents.
Matches the original resume format where possible.
"""

from datetime import datetime
from pathlib import Path

import docx
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


def generate_resume(content: str, original_format: str, username: str, base_dir: str = "output") -> str:
    """Generate the tailored resume in the original format."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if original_format == ".md":
        path = out_dir / f"resume_{ts}.md"
        path.write_text(content, encoding="utf-8")
    else:
        # Default to .docx for both .docx and .pdf inputs
        path = out_dir / f"resume_{ts}.docx"
        _write_docx(content, path)

    return str(path)


def generate_cover_letter(content: str, username: str, base_dir: str = "output") -> str:
    """Generate the cover letter as .docx."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"cover_letter_{ts}.docx"
    _write_docx(content, path, is_cover_letter=True)
    return str(path)


def _write_docx(content: str, path: Path, is_cover_letter: bool = False):
    """Write content to a .docx file with clean professional formatting."""
    doc = docx.Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    # Set margins
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

        # Detect markdown headings
        if stripped.startswith("# "):
            p = doc.add_paragraph()
            run = p.add_run(stripped[2:])
            run.bold = True
            run.font.size = Pt(16)
            if not is_cover_letter:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif stripped.startswith("## "):
            p = doc.add_paragraph()
            run = p.add_run(stripped[3:])
            run.bold = True
            run.font.size = Pt(13)
            # Add a subtle bottom border effect via spacing
            p.paragraph_format.space_after = Pt(2)
        elif stripped.startswith("### "):
            p = doc.add_paragraph()
            run = p.add_run(stripped[4:])
            run.bold = True
            run.font.size = Pt(11)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(stripped[2:], style="List Bullet")
        else:
            doc.add_paragraph(stripped)

    doc.save(str(path))

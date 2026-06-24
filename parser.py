"""Deterministic resume parsing — P1 Hardening.

Extracts text and structure from .docx, .pdf, and .md files.
Returns structured data for LLM context assembly.
"""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import docx
import pdfplumber
from docx.document import Document
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


def parse_resume(filepath: str) -> dict:
    """Parse a resume file and return structured content."""
    path = Path(filepath)
    ext = path.suffix.lower()
    parsers = {
        ".docx": _parse_docx,
        ".pdf": _parse_pdf,
        ".md": _parse_markdown,
    }
    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"Unsupported format: {ext}. Use .docx, .pdf, or .md")
    text, sections = parser(path)
    return {
        "text": text,
        "format": ext,
        "sections": sections,
        "filename": path.name,
        "filepath": str(path),
    }


def _iter_block_items(parent: Document | _Cell) -> Iterator[Any]:
    """Yield Paragraph and Table children of `parent` in document order.

    `Document.paragraphs` skips anything inside a table, so a résumé laid out
    as a table (very common — single-table or sidebar layouts) parses to empty
    text. Walking the body's child elements in order — and recursing into table
    cells in `_parse_docx` — recovers that text. `parent` is a Document or a
    table `_Cell`. Mirrors the canonical python-docx block-iterator recipe.
    """
    parent_elm = parent._tc if isinstance(parent, _Cell) else parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _parse_docx(path: Path) -> tuple[str, list]:
    """Extract text and sections from a Word document, including table cells."""
    doc = docx.Document(str(path))
    sections: list[dict] = []
    current_section: dict = {"heading": "Header", "content": []}
    full_text: list[str] = []
    seen_cells: set[int] = set()

    def _handle_paragraph(para: Paragraph) -> None:
        nonlocal current_section
        text = para.text.strip()
        if not text:
            return
        full_text.append(text)
        style_name = para.style.name if para.style else None
        if style_name and style_name.startswith("Heading"):
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"heading": text, "content": []}
        else:
            current_section["content"].append(text)

    def _walk(parent: Document | _Cell) -> None:
        for block in _iter_block_items(parent):
            if isinstance(block, Paragraph):
                _handle_paragraph(block)
            elif isinstance(block, Table):
                for row in block.rows:
                    for cell in row.cells:
                        # Merged cells repeat the same underlying <w:tc>; dedupe
                        # so we don't emit their text more than once.
                        key = id(cell._tc)
                        if key in seen_cells:
                            continue
                        seen_cells.add(key)
                        _walk(cell)

    _walk(doc)

    if current_section["content"]:
        sections.append(current_section)

    return "\n".join(full_text), sections


def _parse_pdf(path: Path) -> tuple[str, list]:
    """Extract text from a PDF, page by page."""
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

    full_text = "\n\n".join(pages)
    sections = _infer_sections(full_text)
    return full_text, sections


def _parse_markdown(path: Path) -> tuple[str, list]:
    """Parse a markdown resume into sections."""
    text = path.read_text(encoding="utf-8")
    sections = _infer_sections(text)
    return text, sections


def _infer_sections(text: str) -> list:
    """Infer sections from text using common resume headings."""
    heading_pattern = re.compile(
        r"^(?:#{1,3}\s+)?("
        r"summary|objective|experience|employment|work history|education|"
        r"skills|certifications|projects|awards|publications|references|"
        r"professional experience|technical skills|core competencies|"
        r"professional summary|career highlights"
        r").*$",
        re.IGNORECASE | re.MULTILINE,
    )
    sections = []
    last_end = 0
    last_heading = "Header"

    for match in heading_pattern.finditer(text):
        if last_end > 0 or match.start() > 0:
            content = text[last_end : match.start()].strip()
            if content:
                sections.append(
                    {
                        "heading": last_heading,
                        "content": [line for line in content.split("\n") if line.strip()],
                    }
                )
        last_heading = match.group(0).strip().lstrip("#").strip()
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        sections.append(
            {
                "heading": last_heading,
                "content": [line for line in remaining.split("\n") if line.strip()],
            }
        )

    return sections

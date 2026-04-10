"""Deterministic resume parsing — P1 Hardening.

Extracts text and structure from .docx, .pdf, and .md files.
Returns structured data for LLM context assembly.
"""

import re
from pathlib import Path

import docx
import pdfplumber


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


def _parse_docx(path: Path) -> tuple[str, list]:
    """Extract text and sections from a Word document."""
    doc = docx.Document(str(path))
    sections = []
    current_section = {"heading": "Header", "content": []}
    full_text = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        full_text.append(text)
        if para.style and para.style.name.startswith("Heading"):
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"heading": text, "content": []}
        else:
            current_section["content"].append(text)

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
                sections.append({
                    "heading": last_heading,
                    "content": [line for line in content.split("\n") if line.strip()],
                })
        last_heading = match.group(0).strip().lstrip("#").strip()
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        sections.append({
            "heading": last_heading,
            "content": [line for line in remaining.split("\n") if line.strip()],
        })

    return sections

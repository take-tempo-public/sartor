"""ATS round-trip self-check for generated .docx output.

Phase C.3: every generate writes a .docx via `generator._write_docx` →
this module parses that .docx back through `parser.parse_resume` and
compares against the markdown we asked the generator to emit. Mismatches
are surfaced as warnings/failures on the application_run row, the
dashboard, and the /api/generate response.

The check is **best-effort, not certified** — real ATS systems require
commercial access to test against. The round-trip catches GROSS failures
(lost sections, mis-parsed bullets, scrambled text) and is fast (no LLM
calls, no network). It's not a fidelity guarantee.

Findings shape (the value persisted as JSON on application_run.ats_roundtrip_json):
{
  "status": "pass" | "warning" | "fail",
  "bullet_count_emitted": int,
  "bullet_count_recovered": int,
  "sections_emitted": [str, ...],
  "sections_recovered": [str, ...],
  "notes": [str, ...],              # human-readable diagnostics
  "checked_at": "YYYY-MM-DDTHH:MM:SSZ"
}
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from parser import parse_resume

logger = logging.getLogger(__name__)

# Match markdown bullets in the source content. Mirrors hardening.py:BULLET_LINE_RE
# but compiled here to keep this module independent.
_BULLET_RE = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)

# Match markdown ## section headings.
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# Known ATS-friendly section labels (matches parser._infer_sections list).
_KNOWN_SECTIONS = frozenset(
    {
        "summary",
        "objective",
        "experience",
        "employment",
        "work history",
        "education",
        "skills",
        "certifications",
        "projects",
        "awards",
        "publications",
        "references",
        "professional experience",
        "technical skills",
        "core competencies",
        "professional summary",
        "career highlights",
    }
)


def run_ats_roundtrip(docx_path: str | Path, resume_content_md: str) -> dict:
    """Parse the generated .docx back through parser.py and diff against what the generator was asked to emit.

    Returns a findings dict with a status verdict (pass/warning/fail) and
    counts/notes for human inspection. Never raises — even when parser.py
    fails outright the result has status='fail' with the exception in notes.
    """
    findings: dict = {
        "status": "pass",
        "bullet_count_emitted": 0,
        "bullet_count_recovered": 0,
        "sections_emitted": [],
        "sections_recovered": [],
        "notes": [],
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Count what we asked the generator to emit.
    emitted_bullets = _BULLET_RE.findall(resume_content_md)
    emitted_sections = [m.group(1).strip() for m in _SECTION_RE.finditer(resume_content_md)]
    findings["bullet_count_emitted"] = len(emitted_bullets)
    findings["sections_emitted"] = emitted_sections

    # Parse the .docx back. parser.parse_resume returns
    # {text, sections, format, filename, filepath}.
    docx_path = Path(docx_path)
    if not docx_path.exists():
        findings["status"] = "fail"
        findings["notes"].append(f"docx file missing on disk: {docx_path}")
        return findings

    try:
        parsed = parse_resume(str(docx_path))
    except Exception as exc:
        findings["status"] = "fail"
        findings["notes"].append(f"parser.parse_resume raised: {exc}")
        return findings

    recovered_text = parsed.get("text", "")
    recovered_sections = _scan_known_sections(recovered_text)

    # Bullet recovery has two paths: text-stream (`-` / `*` / `•` prefixes)
    # OR docx structure (Word's "List Bullet" style on a paragraph). The
    # generator uses List Bullet style, so the text-stream count alone
    # would undercount — most ATS systems read the structural list, not
    # raw text. We take the MAX of both to reflect what an ATS would see.
    text_bullets = len(_BULLET_RE.findall(recovered_text))
    structural_bullets = _count_list_bullet_paragraphs(docx_path)
    recovered_bullet_count = max(text_bullets, structural_bullets)

    findings["bullet_count_recovered"] = recovered_bullet_count
    findings["sections_recovered"] = recovered_sections

    # Bullet count tolerance: text-stream + structural counts both checked
    # above. Allow generous wiggle but flag big gaps. The "lost" delta
    # measures the worst-case scenario (emitted minus recovered).
    bullet_loss = len(emitted_bullets) - recovered_bullet_count
    if len(emitted_bullets) > 0:
        loss_ratio = max(0, bullet_loss) / max(1, len(emitted_bullets))
        if loss_ratio > 0.5:
            findings["status"] = "fail"
            findings["notes"].append(
                f"bullet loss too high: emitted {len(emitted_bullets)}, "
                f"recovered {recovered_bullet_count} (lost {bullet_loss})"
            )
        elif loss_ratio > 0.2:
            findings["status"] = _escalate_status(findings["status"], "warning")
            findings["notes"].append(
                f"some bullets lost in round-trip: emitted {len(emitted_bullets)}, "
                f"recovered {recovered_bullet_count}"
            )

    # Section presence: every emitted section heading (matching a known label)
    # should appear in the recovered text. Custom headings outside the known
    # set are allowed but not checked (the parser doesn't recognize them as
    # sections anyway).
    #
    # Compare on the CANONICAL JSON-Resume key, not the raw label: the .docx
    # writer renders from md_to_json_resume() and canonicalizes headings (e.g.
    # "Professional Experience" → "Experience", "Core Competencies" → "Skills").
    # Diffing raw labels would flag those equivalent sections as "missing" even
    # though the content survived — so normalize both sides through the same
    # _SECTION_MAP the renderer uses.
    from json_resume import _SECTION_MAP

    def _canon(label: str) -> str:
        key = label.strip().lower()
        return _SECTION_MAP.get(key, key)

    emitted_known = [s for s in emitted_sections if s.lower() in _KNOWN_SECTIONS]
    recovered_canon = {_canon(s) for s in recovered_sections}
    missing_sections = [s for s in emitted_known if _canon(s) not in recovered_canon]
    if missing_sections:
        findings["status"] = _escalate_status(findings["status"], "fail")
        findings["notes"].append(f"sections missing from recovered text: {missing_sections}")

    # Empty parse output is a fail
    if len(recovered_text.strip()) < 50:
        findings["status"] = _escalate_status(findings["status"], "fail")
        findings["notes"].append(f"recovered text suspiciously short ({len(recovered_text)} chars)")

    if findings["status"] == "pass" and not findings["notes"]:
        findings["notes"].append("Round-trip clean — all bullets + sections recovered.")
    return findings


_STATUS_RANK = {"pass": 0, "warning": 1, "fail": 2}


def _escalate_status(current: str, candidate: str) -> str:
    """Take the more severe of two statuses (pass < warning < fail)."""
    if _STATUS_RANK.get(candidate, 0) > _STATUS_RANK.get(current, 0):
        return candidate
    return current


def _count_list_bullet_paragraphs(docx_path: Path) -> int:
    """Count paragraphs styled as 'List Bullet' (or any list style) in the .docx XML.

    This is the structural-bullet path — what an ATS sees when
    it parses paragraph numPr rather than raw text.

    Returns 0 if python-docx can't open the file (defensive — never raise).
    """
    try:
        from docx import Document

        doc = Document(str(docx_path))
    except Exception as exc:
        logger.debug("Could not open .docx for structural bullet count: %s", exc)
        return 0

    count = 0
    for paragraph in doc.paragraphs:
        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if "list" in style_name and "bullet" in style_name:
            count += 1
            continue
        # Word can also store list status as a direct numPr property without
        # the style being named "List Bullet". Check the underlying XML.
        pPr = paragraph._p.pPr
        if (
            pPr is not None
            and pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr")
            is not None
        ):
            count += 1
    return count


def _scan_known_sections(text: str) -> list[str]:
    """Find lines whose normalized content matches a known section label.

    Mirrors parser._infer_sections but returns the display strings only.
    Permissive: matches whether the line is bare ALL CAPS, `## Title`,
    or any other capitalization.
    """
    out: list[str] = []
    for raw in text.splitlines():
        cleaned = raw.strip().lstrip("#").strip()
        if not cleaned:
            continue
        # Drop trailing punctuation/tabs/dates so "EXPERIENCE\tdates" works
        candidate = re.split(r"[\s\t]{2,}|\t", cleaned, maxsplit=1)[0].strip().rstrip(":")
        if candidate.lower() in _KNOWN_SECTIONS:
            out.append(candidate)
    return out


__all__ = ["run_ats_roundtrip"]

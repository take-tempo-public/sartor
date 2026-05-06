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
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

# Matches any common bullet prefix used by LLMs:
# -, *, •, –, —, ·, ◆, ●, ▪, ›, ‣
BULLET_RE = re.compile(
    r"^[-*\u2022\u2013\u2014\u00b7\u25c6\u25cf\u25aa\u2023\u2043\u203a]\s+"
)

# Inline markdown: ***bold+italic***, **bold**, *italic*
_INLINE_RE = re.compile(r"(\*\*\*[^*\n]+?\*\*\*|\*\*[^*\n]+?\*\*|\*[^*\n]+?\*)")


def generate_resume(
    content: str,
    output_format: str,
    username: str,
    base_dir: str = "output",
    template_path: str | None = None,
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


def _add_inline_runs(paragraph, text: str, base_bold: bool = False) -> None:
    """Parse inline **bold** and *italic* markers and add styled runs.

    Handles: ***bold+italic***, **bold**, *italic*, and plain text segments.
    Leaves the paragraph's style intact — only run-level formatting is set.
    """
    segments = _INLINE_RE.split(text)
    for seg in segments:
        if not seg:
            continue
        if seg.startswith("***") and seg.endswith("***"):
            run = paragraph.add_run(seg[3:-3])
            run.bold = True
            run.italic = True
        elif seg.startswith("**") and seg.endswith("**"):
            run = paragraph.add_run(seg[2:-2])
            run.bold = True
        elif seg.startswith("*") and seg.endswith("*"):
            run = paragraph.add_run(seg[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(seg)
            if base_bold:
                run.bold = True


def _extract_list_numPr(doc: "docx.document.Document"):
    """Return a deep copy of the numPr element from the first List Paragraph, or None."""
    for p in doc.paragraphs:
        if p.style and p.style.name == "List Paragraph":
            pPr = p._element.find(qn("w:pPr"))
            if pPr is not None:
                numPr = pPr.find(qn("w:numPr"))
                if numPr is not None:
                    return deepcopy(numPr)
    return None


def _clear_body(doc: "docx.document.Document") -> None:
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
    existing = pPr.find(qn("w:numPr"))
    if existing is not None:
        pPr.remove(existing)
    pPr.insert(0, deepcopy(numPr_template))


# ── Template style capture ──────────────────────────────────────────────────
# Many resumes do not use Word's named heading styles — they apply direct
# formatting (alignment, run sizes, tab stops) to Normal paragraphs. To
# faithfully reproduce these layouts, we walk the template's paragraphs and
# build a dict of role-to-prototype, then apply those prototypes when writing
# the corresponding markdown elements.

def _capture_proto(p) -> dict:
    """Capture a paragraph's formatting into a serializable prototype.

    Captures alignment, vertical spacing, tab stops, and the primary run's
    bold/size. Run italic and color are intentionally not captured — they
    are typically inline (`*text*`) rather than role-based.
    """
    run0 = p.runs[0] if p.runs else None
    pf = p.paragraph_format
    return {
        "alignment": p.alignment,
        "space_before_pt": pf.space_before.pt if pf.space_before else None,
        "space_after_pt": pf.space_after.pt if pf.space_after else None,
        "tab_stops": [
            (t.position.pt, t.alignment) for t in (pf.tab_stops or [])
        ],
        "run_bold": bool(run0.bold) if (run0 and run0.bold is not None) else None,
        "run_size_pt": run0.font.size.pt if (run0 and run0.font.size) else None,
    }


def _capture_template_styles(doc: "docx.document.Document") -> dict:
    """Walk the template's first ~30 paragraphs; classify each by role.

    Heuristics:
    - Centered paragraphs at the very top, in order: name, subtitle, contact.
    - Bold paragraph with a right tab stop: job_title (## job-row).
    - Bold paragraph without tab stops: section_heading.
    - Non-bold paragraph immediately after a job_title: job_subtitle.
    - First non-bold paragraph that isn't header / job_subtitle: body.

    Returns a dict keyed by role; missing roles fall back to the writer's
    built-in defaults so a partial capture still yields a clean output.
    """
    styles: dict = {}
    centered_seen = 0
    last_was_job_title = False

    for p in doc.paragraphs:
        if not p.text.strip():
            continue

        proto = _capture_proto(p)
        is_centered = p.alignment == WD_ALIGN_PARAGRAPH.CENTER
        any_bold = any(r.bold for r in p.runs)
        has_right_tab = any(
            t.alignment == WD_TAB_ALIGNMENT.RIGHT
            for t in (p.paragraph_format.tab_stops or [])
        )

        # Header zone: centered paragraphs at the top, in order
        if (
            is_centered
            and centered_seen < 3
            and "section_heading" not in styles
        ):
            role = ("name", "subtitle", "contact")[centered_seen]
            styles.setdefault(role, proto)
            centered_seen += 1
            continue

        # Bold + right tab stop = job title with right-aligned date
        if any_bold and has_right_tab:
            styles.setdefault("job_title", proto)
            last_was_job_title = True
            continue

        # Bold without tab stops = section heading
        if any_bold:
            styles.setdefault("section_heading", proto)
            last_was_job_title = False
            continue

        # Non-bold immediately after a job title = job subtitle (smaller font)
        if last_was_job_title:
            styles.setdefault("job_subtitle", proto)
            last_was_job_title = False
            continue

        # Default body paragraph
        styles.setdefault("body", proto)
        last_was_job_title = False

    return styles


def _apply_para_proto(p, proto: dict | None) -> None:
    """Apply paragraph-level formatting from a proto. Skips runs."""
    if not proto:
        return
    if proto.get("alignment") is not None:
        p.alignment = proto["alignment"]
    if proto.get("space_before_pt") is not None:
        p.paragraph_format.space_before = Pt(proto["space_before_pt"])
    if proto.get("space_after_pt") is not None:
        p.paragraph_format.space_after = Pt(proto["space_after_pt"])
    for pos_pt, align in proto.get("tab_stops", []):
        p.paragraph_format.tab_stops.add_tab_stop(Pt(pos_pt), alignment=align)


def _apply_run_proto(run, proto: dict | None) -> None:
    """Apply run-level formatting (bold, font size) from a proto."""
    if not proto:
        return
    if proto.get("run_bold") is not None:
        run.bold = proto["run_bold"]
    if proto.get("run_size_pt"):
        run.font.size = Pt(proto["run_size_pt"])


def _add_inline_runs_with_proto(paragraph, text: str, proto: dict | None) -> None:
    """Like _add_inline_runs but also applies the proto's run-level format
    to every emitted run as a baseline (inline ** / * still wins over base bold).
    Tab characters in `text` are preserved; the paragraph's tab stops handle them.
    """
    segments = _INLINE_RE.split(text)
    for seg in segments:
        if not seg:
            continue
        if seg.startswith("***") and seg.endswith("***"):
            run = paragraph.add_run(seg[3:-3])
            run.bold = True
            run.italic = True
            _apply_run_proto(run, {"run_size_pt": (proto or {}).get("run_size_pt")})
        elif seg.startswith("**") and seg.endswith("**"):
            run = paragraph.add_run(seg[2:-2])
            run.bold = True
            _apply_run_proto(run, {"run_size_pt": (proto or {}).get("run_size_pt")})
        elif seg.startswith("*") and seg.endswith("*"):
            run = paragraph.add_run(seg[1:-1])
            run.italic = True
            _apply_run_proto(run, {"run_size_pt": (proto or {}).get("run_size_pt")})
        else:
            run = paragraph.add_run(seg)
            _apply_run_proto(run, proto)


def _write_docx(
    content: str,
    path: Path,
    template_path: str | None = None,
    is_cover_letter: bool = False,
) -> None:
    """Write LLM content to .docx, using the original file as a style template
    when it is a .docx. Falls back to clean built-in defaults otherwise.

    When a template is supplied, paragraph formatting (alignment, run sizes,
    tab stops) is captured per-role from the template and applied to the
    matching markdown elements. Roles: name (`# `), subtitle/contact (lines
    after `# ` and before the first `## `), section_heading (`## `), job_title
    (`### `, with right tab stop preserved if the template has one),
    job_subtitle (the line directly after `### `), bullet (`-` etc.).
    """
    tp = Path(template_path) if template_path else None
    use_template = bool(tp and tp.exists() and tp.suffix.lower() == ".docx")

    if use_template:
        doc = docx.Document(str(tp))
        styles = _capture_template_styles(doc)
        orig_numPr = _extract_list_numPr(doc)
        _clear_body(doc)
    else:
        styles = {}
        orig_numPr = None
        doc = docx.Document()
        normal = doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(11)
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.85)
            section.right_margin = Inches(0.85)

    # State for "header zone" tracking: lines after `# ` and before first `## `
    # get the centered subtitle/contact treatment from the template.
    in_header = False
    header_subline = 0  # 0 = subtitle slot, 1+ = contact slot
    last_was_job_title = False

    for line in content.split("\n"):
        stripped = line.strip()

        if not stripped:
            doc.add_paragraph("")
            continue

        # ── # Name ────────────────────────────────────────────────────────
        if stripped.startswith("# "):
            text = stripped[2:]
            p = doc.add_paragraph()
            if use_template and "name" in styles:
                _apply_para_proto(p, styles["name"])
                _add_inline_runs_with_proto(p, text, styles["name"])
            else:
                _add_inline_runs(p, text, base_bold=True)
                for run in p.runs:
                    run.font.size = Pt(16)
                if not is_cover_letter:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            in_header = not is_cover_letter
            header_subline = 0
            last_was_job_title = False

        # ── ## Section heading ────────────────────────────────────────────
        elif stripped.startswith("## "):
            text = stripped[3:]
            p = doc.add_paragraph()
            if use_template and "section_heading" in styles:
                _apply_para_proto(p, styles["section_heading"])
                _add_inline_runs_with_proto(p, text, styles["section_heading"])
            else:
                _add_inline_runs(p, text, base_bold=True)
                for run in p.runs:
                    run.font.size = Pt(13)
                p.paragraph_format.space_after = Pt(2)
            in_header = False
            last_was_job_title = False

        # ── ### Job title / company / role line ───────────────────────────
        elif stripped.startswith("### "):
            text = stripped[4:]
            p = doc.add_paragraph()
            if use_template and "job_title" in styles:
                _apply_para_proto(p, styles["job_title"])
                _add_inline_runs_with_proto(p, text, styles["job_title"])
            else:
                _add_inline_runs(p, text, base_bold=True)
                if not use_template:
                    for run in p.runs:
                        run.font.size = Pt(11)
            in_header = False
            last_was_job_title = True

        # ── Bullet point ──────────────────────────────────────────────────
        elif BULLET_RE.match(stripped):
            text = BULLET_RE.sub("", stripped)
            if use_template and orig_numPr is not None:
                p = doc.add_paragraph(style="List Paragraph")
                _apply_numPr(p, orig_numPr)
                for run in list(p.runs):
                    run._element.getparent().remove(run._element)
                _add_inline_runs(p, text)
            else:
                p = doc.add_paragraph(style="List Bullet")
                for run in list(p.runs):
                    run._element.getparent().remove(run._element)
                _add_inline_runs(p, text)
            in_header = False
            last_was_job_title = False

        # ── Plain body text — context-sensitive ───────────────────────────
        else:
            p = doc.add_paragraph()
            if in_header and use_template:
                # First plain line under # → subtitle; subsequent → contact
                role = "subtitle" if header_subline == 0 else "contact"
                proto = styles.get(role) or styles.get("contact") or styles.get("subtitle")
                _apply_para_proto(p, proto)
                _add_inline_runs_with_proto(p, stripped, proto)
                header_subline += 1
            elif last_was_job_title and use_template and "job_subtitle" in styles:
                _apply_para_proto(p, styles["job_subtitle"])
                _add_inline_runs_with_proto(p, stripped, styles["job_subtitle"])
                last_was_job_title = False
            else:
                proto = styles.get("body") if use_template else None
                if proto:
                    _apply_para_proto(p, proto)
                    _add_inline_runs_with_proto(p, stripped, proto)
                else:
                    _add_inline_runs(p, stripped)
                last_was_job_title = False

    doc.save(str(path))

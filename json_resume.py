"""JSON Resume v1.0 intermediate format — canonical structured shape.

Per docs/PRODUCT_SHAPE.md §6.4, sartor. adopts JSON Resume v1.0
(jsonresume.org) as the canonical intermediate between the LLM's
markdown emit and the downstream renderers (.md, .docx, .pdf, HTML).

The LLM continues to emit markdown (preserves the existing prompt +
the no-near-duplicate rule + the markdown normalizer at
`generator._normalize_markdown`). This module lifts that markdown
into a structured JSON Resume document via deterministic parsing —
no LLM call.

Reference schema: https://jsonresume.org/schema/

Our corpus-specific fields (tags, scores, has_outcome, is_active,
variants) live under `meta.sartor.*` so the resulting document
still validates against the standard JSON Resume schema; themes that
don't know about sartor. extensions ignore them, our own renderers
read them.

Design constraints
------------------
- Best-effort and forgiving. Missing sections produce empty arrays
  rather than KeyErrors. Malformed lines fall through to
  `meta.sartor.unparsed` so nothing is silently dropped.
- Deterministic: same markdown in → same JSON out. No LLM, no
  network, no clock dependencies.
- Idempotent: re-parsing the markdown derived from emitting this
  document back produces an equivalent structure.
- Tolerant of the markdown normalizer's output (per
  `generator._normalize_markdown` — blank lines before headers,
  newlines before bullets, h2-title-on-its-own-line).
"""

from __future__ import annotations

import re
from typing import Any

# JSON Resume v1.0 schema URI — included on every document we emit so
# downstream validators / theme renderers can self-identify.
SCHEMA_URI = "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json"

# Contact-line patterns
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Phone: tolerates "(555) 010-2200", "555-0142", "+1 555 010 2200"
_PHONE_RE = re.compile(r"\+?\d?[\s\-.]?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}")
# URL: full http(s), bare domain with a known TLD, or linkedin/github-style path
_URL_RE = re.compile(
    r"https?://[^\s|·]+"
    r"|(?:[a-z0-9\-]+\.)+(?:com|net|io|dev|me|app|org|co|ai)(?:/[^\s|·]*)?",
    re.IGNORECASE,
)

# Heading detectors
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_H3_RE = re.compile(r"^###\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s+(.+?)\s*$")

# Skills section item separator — sentence-case skill names, separated
# by ` · ` (sartor. brand), `, `, or one-per-line bullets.
_SKILLS_SPLIT_RE = re.compile(r"\s*[·•|,]\s+")

# Map h2 title text → JSON Resume top-level key. Lowercased for matching.
#
# Aliases matter for FIDELITY, not just tidiness: any h2 title NOT in this map
# lands in `meta.sartor.unparsed` and is silently dropped from the HTML/PDF
# preview (the `.docx` writer now renders from this same parse, so an off-map
# heading would drop from BOTH — still consistent, but the user loses their
# Summary/Skills). A résumé that titles its sections "Professional Summary" or
# "Core Competencies" (very common) must map to the canonical keys so the
# content survives. Additions here are purely widening — they can only rescue a
# title that would otherwise be dropped, never re-route a canonical one.
_SECTION_MAP = {
    # — Summary —
    "summary": "_summary",
    "professional summary": "_summary",
    "summary of qualifications": "_summary",
    "career summary": "_summary",
    "executive summary": "_summary",
    "profile": "_summary",
    "professional profile": "_summary",
    "about": "_summary",
    "about me": "_summary",
    "objective": "_summary",
    # — Experience —
    "experience": "work",
    "work experience": "work",
    "professional experience": "work",
    "relevant experience": "work",
    "work history": "work",
    "employment": "work",
    "employment history": "work",
    "career history": "work",
    # — Skills —
    "skills": "skills",
    "technical skills": "skills",
    "core competencies": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "areas of expertise": "skills",
    "competencies": "skills",
    "technical expertise": "skills",
    "technical proficiencies": "skills",
    "proficiencies": "skills",
    "skills & expertise": "skills",
    "skills and expertise": "skills",
    "expertise": "skills",
    # — Education —
    "education": "education",
    "education & training": "education",
    "education and training": "education",
    "academic background": "education",
    # — Certifications —
    "certifications": "certificates",
    "certificates": "certificates",
    "certification": "certificates",
    "licenses & certifications": "certificates",
    "licenses and certifications": "certificates",
    "credentials": "certificates",
    # — Projects —
    "projects": "projects",
    "key projects": "projects",
    "selected projects": "projects",
    "notable projects": "projects",
    # — Other standard sections —
    "publications": "publications",
    "selected publications": "publications",
    "awards": "awards",
    "awards & honors": "awards",
    "awards and honors": "awards",
    "honors & awards": "awards",
    "honors and awards": "awards",
    "languages": "languages",
    "interests": "interests",
    "volunteer": "volunteer",
    "volunteering": "volunteer",
    "volunteer experience": "volunteer",
    "community involvement": "volunteer",
    "references": "references",
}


def md_to_json_resume(markdown: str) -> dict[str, Any]:
    """Parse a normalized résumé markdown into a JSON Resume v1.0 dict.

    Best-effort: missing or malformed sections produce empty arrays;
    nothing is silently dropped (unparseable content lands under
    `meta.sartor.unparsed`).
    """
    doc: dict[str, Any] = {
        "$schema": SCHEMA_URI,
        "basics": {},
        "work": [],
        "education": [],
        "skills": [],
        "certificates": [],
        "projects": [],
        "meta": {
            "sartor": {
                "version": "1.0",
                "unparsed": [],
            },
        },
    }

    if not markdown or not markdown.strip():
        return doc

    lines = markdown.splitlines()
    # Step 1 — header block: everything before the first ##
    header_end = _find_first_h2_index(lines)
    _parse_header(lines[:header_end], doc)

    # Step 2 — walk sections by ##
    section_ranges = _section_ranges(lines, header_end)
    for title, start, end in section_ranges:
        section_body = lines[start + 1 : end]
        _parse_section(title, section_body, doc)

    return doc


# ---------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------


def _find_first_h2_index(lines: list[str]) -> int:
    """Return the index of the first ``##`` heading line, or ``len(lines)`` if none."""
    for i, line in enumerate(lines):
        if _H2_RE.match(line):
            return i
    return len(lines)


def _section_ranges(lines: list[str], start_after: int) -> list[tuple[str, int, int]]:
    """Yield (title, start_line_index, end_line_index_exclusive) per h2."""
    ranges: list[tuple[str, int, int]] = []
    current_start: int | None = None
    current_title: str | None = None
    for i in range(start_after, len(lines)):
        m = _H2_RE.match(lines[i])
        if m:
            if current_start is not None and current_title is not None:
                ranges.append((current_title, current_start, i))
            current_title = m.group(1).strip()
            current_start = i
    if current_start is not None and current_title is not None:
        ranges.append((current_title, current_start, len(lines)))
    return ranges


# ---------------------------------------------------------------------
# Header (basics)
# ---------------------------------------------------------------------


def _parse_header(lines: list[str], doc: dict[str, Any]) -> None:
    """Pull # Name + the 1-2 subtitle/contact lines into doc['basics']."""
    basics: dict[str, Any] = doc["basics"]
    profiles: list[dict[str, str]] = []
    label_set = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        h1 = _H1_RE.match(stripped)
        if h1:
            basics["name"] = h1.group(1).strip()
            continue
        # Subsequent lines are subtitle and/or contact
        email_match = _EMAIL_RE.search(stripped)
        phone_match = _PHONE_RE.search(stripped)
        url_matches = _URL_RE.findall(stripped)

        if email_match:
            basics["email"] = email_match.group(0)
        if phone_match:
            basics["phone"] = phone_match.group(0)
        for url in url_matches:
            normalized = url if url.startswith("http") else f"https://{url}"
            network = _network_from_url(url)
            if network == "Website":
                basics["url"] = normalized
            else:
                profiles.append(
                    {
                        "network": network,
                        "url": normalized,
                        "username": _username_from_url(url),
                    }
                )

        # Treat a line with NO email / phone / URL as the label
        # (subtitle). The 1-2 lines after # Name are the typical
        # subtitle + contact split per the prompt's example.
        if not label_set and not email_match and not phone_match and not url_matches:
            basics["label"] = stripped
            label_set = True

    if profiles:
        basics["profiles"] = profiles


def _network_from_url(url: str) -> str:
    """Map a profile URL to its JSON Resume network label (LinkedIn/GitHub/Twitter/Mastodon, else ``"Website"``)."""
    u = url.lower()
    if "linkedin.com" in u:
        return "LinkedIn"
    if "github.com" in u:
        return "GitHub"
    if "twitter.com" in u or "x.com" in u:
        return "Twitter"
    if "mastodon" in u:
        return "Mastodon"
    return "Website"


def _username_from_url(url: str) -> str:
    """Best-effort username extraction from a profile URL."""
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else ""


# ---------------------------------------------------------------------
# Section dispatch
# ---------------------------------------------------------------------


def _parse_section(title: str, body: list[str], doc: dict[str, Any]) -> None:
    """Dispatch one résumé section (``title`` + ``body`` lines) into the JSON Resume ``doc`` by its mapped key."""
    key = _SECTION_MAP.get(title.strip().lower())
    if key == "_summary":
        doc["basics"]["summary"] = _collapse_paragraph(body)
    elif key == "work":
        doc["work"] = _parse_h3_entries(body, kind="work")
    elif key == "education":
        doc["education"] = _parse_h3_entries(body, kind="education")
    elif key == "skills":
        doc["skills"] = _parse_skills(body)
    elif key == "certificates":
        doc["certificates"] = _parse_simple_list(body, name_key="name")
    elif key == "projects":
        doc["projects"] = _parse_h3_entries(body, kind="project")
    elif key in {"publications", "awards", "languages", "interests", "volunteer", "references"}:
        doc[key] = _parse_simple_list(body, name_key="name")
    else:
        # Unknown section — log under meta.sartor.unparsed so nothing
        # is silently dropped, but don't crash.
        doc["meta"]["sartor"]["unparsed"].append(
            {
                "section": title,
                "raw": "\n".join(body).strip(),
            }
        )


def _collapse_paragraph(body: list[str]) -> str:
    """Join body lines into a single paragraph, preserving blank-line splits."""
    chunks: list[list[str]] = [[]]
    for line in body:
        if not line.strip():
            if chunks[-1]:
                chunks.append([])
        else:
            chunks[-1].append(line.strip())
    paragraphs = [" ".join(c) for c in chunks if c]
    return "\n\n".join(paragraphs).strip()


# ---------------------------------------------------------------------
# Experience / Education / Project — h3-delimited entries
# ---------------------------------------------------------------------


def _parse_h3_entries(body: list[str], kind: str) -> list[dict[str, Any]]:
    """Split body on `### `; parse each entry into a JSON Resume work/education/project dict."""
    entries: list[dict[str, Any]] = []
    current: list[str] | None = None
    for line in body:
        if _H3_RE.match(line):
            if current is not None:
                entries.append(_entry_from_chunk(current, kind))
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        entries.append(_entry_from_chunk(current, kind))
    return entries


def _entry_from_chunk(chunk: list[str], kind: str) -> dict[str, Any]:
    """Parse one h3-led chunk into a JSON Resume entry."""
    header_line = chunk[0] if chunk else ""
    h3 = _H3_RE.match(header_line)
    header_text = h3.group(1) if h3 else header_line.lstrip("# ").strip()

    entry: dict[str, Any] = {}
    name, position, start, end = _split_h3_header(header_text)

    if kind == "work":
        # name → company, position → role title
        if name:
            entry["name"] = name
        if position:
            entry["position"] = position
    elif kind == "education":
        # name → institution; position used as 'studyType / area' fallback
        if name:
            entry["institution"] = name
        if position:
            entry["area"] = position
    else:  # project
        if name:
            entry["name"] = name
        if position:
            entry["description"] = position

    if start:
        entry["startDate"] = start
    if end:
        entry["endDate"] = end

    # Body lines that follow until next h3:
    #   - bare paragraph lines = role summary
    #   - "- " lines = highlights / bullets
    summary_parts: list[str] = []
    highlights: list[str] = []
    for line in chunk[1:]:
        s = line.strip()
        if not s:
            continue
        bm = _BULLET_RE.match(s)
        if bm:
            highlights.append(bm.group(1).strip())
        else:
            summary_parts.append(s)
    if summary_parts and kind != "project":
        entry["summary"] = " ".join(summary_parts)
    if highlights:
        entry["highlights"] = highlights

    return entry


def _split_h3_header(text: str) -> tuple[str, str, str, str]:
    r"""Split `Company, Position\\tStart – End` (or variants) into 4 strings.

    Returns (name, position, start, end). Any field may be empty.
    Tolerates: TAB separator before date; ", " separator between
    name and position; " — " separator as a position/name fallback;
    en-dash / em-dash / hyphen between dates.
    """
    name = position = start = end = ""

    # Date suffix: split on TAB if present, else nothing
    if "\t" in text:
        left, date_part = text.split("\t", 1)
    else:
        left = text
        date_part = ""

    # name / position split: prefer ", " (the prompt's canonical form);
    # fall back to " — " or " - " if no comma.
    if ", " in left:
        name, position = left.split(", ", 1)
    elif " — " in left:
        name, position = left.split(" — ", 1)
    else:
        name = left

    name = name.strip()
    position = position.strip()

    if date_part:
        # Date-range separator: en/em dash with optional surrounding
        # whitespace, OR hyphen-minus with REQUIRED surrounding whitespace.
        # The stricter rule on `-` prevents splitting inside ISO dates
        # like `2022-09` (which contain a hyphen with no spaces).
        parts = re.split(r"\s*[–—]\s*|\s+-\s+", date_part.strip(), maxsplit=1)
        if parts:
            start = parts[0].strip()
        if len(parts) > 1:
            end = parts[1].strip()

    return name, position, start, end


# ---------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------


def _parse_skills(body: list[str]) -> list[dict[str, Any]]:
    """Parse a Skills section into JSON Resume skills[].

    Accepts three shapes:
      1. Single paragraph with `·` / `,` / `|` separators
      2. Bullet list (`- Skill`)
      3. Bullet list with grouped skills (`- Group: a, b, c`)

    Output: list of {"name": "...", ...} dicts. For shape 3, the group
    becomes the skill name and the comma-list becomes `keywords`.
    """
    if not body:
        return []

    # Pre-detect bullet-list shape
    has_bullets = any(_BULLET_RE.match(line.strip()) for line in body)
    skills: list[dict[str, Any]] = []

    if has_bullets:
        for line in body:
            m = _BULLET_RE.match(line.strip())
            if not m:
                continue
            text = m.group(1).strip()
            if ":" in text:
                # Grouped form
                group, items = text.split(":", 1)
                keywords = [k.strip() for k in re.split(r"\s*,\s*", items) if k.strip()]
                skills.append({"name": group.strip(), "keywords": keywords})
            else:
                skills.append({"name": text})
        return skills

    # Single-paragraph form
    text = " ".join(line.strip() for line in body if line.strip())
    if not text:
        return []
    items = [s.strip() for s in _SKILLS_SPLIT_RE.split(text) if s.strip()]
    return [{"name": item} for item in items]


# ---------------------------------------------------------------------
# Generic single-line entries (certifications, awards, etc.)
# ---------------------------------------------------------------------


def _parse_simple_list(body: list[str], name_key: str) -> list[dict[str, Any]]:
    """One non-empty line = one entry, mapped under `name_key`."""
    entries: list[dict[str, Any]] = []
    for line in body:
        s = line.strip()
        if not s:
            continue
        # Drop bullet markers if present
        bm = _BULLET_RE.match(s)
        if bm:
            s = bm.group(1).strip()
        entries.append({name_key: s})
    return entries


# ---------------------------------------------------------------------
# Inverse: JSON Resume dict → normalized résumé markdown
# ---------------------------------------------------------------------


def _format_date_range(start: object, end: object) -> str:
    """`start – end` (en-dash, the separator `md_to_json_resume` splits on), or a single date."""
    s = str(start).strip() if start else ""
    e = str(end).strip() if end else ""
    if s and e:
        return f"{s} – {e}"
    return s or e


def json_resume_to_markdown(doc: dict[str, Any]) -> str:
    """Serialize a JSON Resume v1.0 dict back to normalized résumé markdown.

    The deterministic inverse of `md_to_json_resume` for the fields sartor.
    populates (basics, work, skills, education, certificates). Generation-
    experience re-architecture Phase 4: the corpus-mode deterministic assemble
    uses this to derive an editable markdown representation of the frozen
    ``approved_composition`` (for the edit surface, the ``generated_resume_md``
    audit column, and the cover-letter résumé context) WITHOUT an LLM — the
    styled preview + download render the ``approved_composition`` dict directly,
    so this text is a secondary, editable view. Round-trips: re-parsing this
    output through ``md_to_json_resume`` reproduces the same core fields.
    ``meta.sartor.*`` provenance is intentionally NOT emitted (it is not part of
    the rendered résumé). Deterministic: no LLM, no clock, no randomness.
    """
    basics = doc.get("basics") or {}
    lines: list[str] = []
    name = str(basics.get("name") or "").strip()
    lines.append(f"# {name}".rstrip())
    label = str(basics.get("label") or "").strip()
    if label:
        lines.append(label)
    contact_bits: list[str] = []
    for key in ("email", "phone", "url"):
        if basics.get(key):
            contact_bits.append(str(basics[key]).strip())
    for p in basics.get("profiles") or []:
        if isinstance(p, dict) and p.get("url"):
            contact_bits.append(str(p["url"]).strip())
    if contact_bits:
        lines.append(" · ".join(contact_bits))

    summary = str(basics.get("summary") or "").strip()
    if summary:
        lines.extend(["", "## Summary", "", summary])

    work = doc.get("work") or []
    if work:
        lines.extend(["", "## Experience"])
        for w in work:
            if not isinstance(w, dict):
                continue
            lines.append("")
            company = str(w.get("name") or "").strip()
            position = str(w.get("position") or "").strip()
            header = f"{company}, {position}" if (company and position) else (company or position)
            dates = _format_date_range(w.get("startDate"), w.get("endDate"))
            if dates:
                header = f"{header}\t{dates}" if header else dates
            lines.append(f"### {header}")
            role_summary = str(w.get("summary") or "").strip()
            if role_summary:
                lines.extend(["", role_summary])
            for h in w.get("highlights") or []:
                if str(h).strip():
                    lines.append(f"- {str(h).strip()}")

    skill_names = [
        str(s["name"]).strip()
        for s in (doc.get("skills") or [])
        if isinstance(s, dict) and str(s.get("name") or "").strip()
    ]
    if skill_names:
        lines.extend(["", "## Skills", "", " · ".join(skill_names)])

    education = doc.get("education") or []
    if education:
        lines.extend(["", "## Education"])
        for e in education:
            if not isinstance(e, dict):
                continue
            lines.append("")
            inst = str(e.get("institution") or "").strip()
            area = str(e.get("area") or "").strip()
            header = f"{inst}, {area}" if (inst and area) else (inst or area)
            dates = _format_date_range(e.get("startDate"), e.get("endDate"))
            if dates:
                header = f"{header}\t{dates}" if header else dates
            lines.append(f"### {header}")
            for h in e.get("highlights") or []:
                if str(h).strip():
                    lines.append(f"- {str(h).strip()}")

    cert_names = [
        str(c["name"]).strip()
        for c in (doc.get("certificates") or [])
        if isinstance(c, dict) and str(c.get("name") or "").strip()
    ]
    if cert_names:
        lines.extend(["", "## Certifications"])
        lines.extend(f"- {n}" for n in cert_names)

    return "\n".join(lines).strip() + "\n"

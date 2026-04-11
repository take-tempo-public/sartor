"""Deterministic analysis tools — P1 Hardening, P2 Context Hygiene.

These replace what would otherwise be unreliable LLM work:
keyword extraction, ATS format checks, context assembly.
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Common English stop words to exclude from keyword extraction
STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it that this with as by from are was "
    "were be been being have has had do does did will would shall should may might can "
    "could not no nor so yet also very too quite rather just only even still already "
    "about above after again all any between both each few more most other some such "
    "than them then there these those through under until up we what when where which "
    "while who whom why you your i me my he him his she her they their our its".split()
)

# Standard ATS-friendly section headings
ATS_HEADINGS = {
    "summary", "professional summary", "objective", "career objective",
    "experience", "professional experience", "work experience", "employment",
    "work history", "education", "skills", "technical skills",
    "core competencies", "certifications", "projects", "awards",
    "publications", "references", "volunteer",
}


def extract_keywords(text: str, top_n: int = 50) -> dict:
    """Extract keyword frequencies from text. Deterministic — no LLM needed."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z+#.-]{1,}\b", text.lower())
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    counts = Counter(filtered)

    # Also extract multi-word phrases (bigrams/trigrams)
    tokens = text.lower().split()
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            phrase = " ".join(tokens[i : i + n])
            clean = re.sub(r"[^\w\s+#.-]", "", phrase).strip()
            if clean and all(w not in STOP_WORDS for w in clean.split()):
                counts[clean] += 1

    return {
        "keywords": dict(counts.most_common(top_n)),
        "total_unique": len(counts),
    }


def compute_keyword_overlap(resume_kw: dict, jd_kw: dict) -> dict:
    """Compare keyword sets between resume and JD. Pure set math."""
    resume_set = set(resume_kw.get("keywords", {}).keys())
    jd_set = set(jd_kw.get("keywords", {}).keys())

    matched = resume_set & jd_set
    missing = jd_set - resume_set
    extra = resume_set - jd_set

    score = len(matched) / max(len(jd_set), 1)

    return {
        "matched": sorted(matched),
        "missing_from_resume": sorted(missing),
        "only_in_resume": sorted(extra),
        "match_score": round(score, 2),
        "jd_keyword_count": len(jd_set),
        "resume_keyword_count": len(resume_set),
    }


def check_ats_format(parsed_resume: dict) -> list[str]:
    """Flag ATS-hostile patterns in a parsed resume. Deterministic checks."""
    warnings = []
    text = parsed_resume.get("text", "")
    sections = parsed_resume.get("sections", [])
    fmt = parsed_resume.get("format", "")

    # Check for standard section headings
    found_headings = {s["heading"].lower().strip() for s in sections}
    if not found_headings & ATS_HEADINGS:
        warnings.append(
            "No standard ATS section headings detected. "
            "Use headings like: Experience, Education, Skills, Summary"
        )

    # Check for contact info patterns
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        warnings.append("No email address detected")
    if not re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text):
        warnings.append("No phone number detected")

    # Check for problematic formatting
    if text.count("|") > 5:
        warnings.append(
            "Multiple pipe characters detected — may indicate table layout "
            "that ATS systems struggle to parse"
        )
    if text.count("\t") > 10:
        warnings.append(
            "Many tab characters detected — may indicate column layout "
            "that ATS systems misread"
        )

    # Check resume length
    word_count = len(text.split())
    if word_count < 150:
        warnings.append(f"Resume appears very short ({word_count} words)")
    elif word_count > 1200:
        warnings.append(
            f"Resume is quite long ({word_count} words). "
            "Consider trimming to 1-2 pages for ATS compatibility"
        )

    # PDF-specific warning
    if fmt == ".pdf":
        warnings.append(
            "PDF resumes may lose formatting in ATS parsing. "
            "Consider submitting as .docx when possible"
        )

    return warnings


def validate_config(config: dict) -> list[str]:
    """Validate a user config for required fields and well-formed URLs."""
    errors = []
    if not config.get("name"):
        errors.append("Missing required field: name")

    for url_field in ("linkedin_url", "website_url"):
        url = config.get(url_field, "")
        if url:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Invalid URL in {url_field}: {url}")

    for url in config.get("portfolio_urls", []):
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"Invalid portfolio URL: {url}")

    return errors


def build_context_set(
    jd_text: str,
    parsed_resume: dict,
    config: dict,
    profile_text: str,
    jd_keywords: dict,
    resume_keywords: dict,
    keyword_overlap: dict,
    ats_warnings: list[str],
    supplemental_resumes: list[dict] | None = None,
    original_resume_path: str = "",
) -> dict:
    """Assemble the optimized context payload for LLM calls.

    P2 Context Hygiene: compact, structured, only what the LLM needs.
    P3 Living Documentation: machine-readable JSON.
    P4 Disposable Blueprint: saved to disk, versioned by timestamp.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "candidate": {
            "name": config.get("name", ""),
            "email": config.get("email", ""),
            "phone": config.get("phone", ""),
            "linkedin_url": config.get("linkedin_url", ""),
            "website_url": config.get("website_url", ""),
            "skills": config.get("skills", []),
            "certifications": config.get("certifications", []),
            "education_summary": config.get("education_summary", ""),
            "notes": config.get("notes", ""),
        },
        "resume": {
            "format": parsed_resume.get("format", ""),
            "sections": parsed_resume.get("sections", []),
            "text": parsed_resume.get("text", ""),
            "filename": parsed_resume.get("filename", ""),
            "path": original_resume_path,
        },
        "supplemental_resumes": [
            {
                "filename": r.get("filename", ""),
                "text": r.get("text", ""),
                "sections": r.get("sections", []),
            }
            for r in (supplemental_resumes or [])
        ],
        "job_description": jd_text,
        "deterministic_analysis": {
            "jd_keywords": jd_keywords,
            "resume_keywords": resume_keywords,
            "keyword_overlap": keyword_overlap,
            "ats_warnings": ats_warnings,
        },
    }


def save_context_set(context_set: dict, username: str, base_dir: str = "output") -> str:
    """Save context set to disk as timestamped JSON. P4 Disposable Blueprint."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"context_{ts}.json"
    path.write_text(json.dumps(context_set, indent=2), encoding="utf-8")
    return str(path)

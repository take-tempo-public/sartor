"""LLM-assisted experience + bullet extraction from a parsed resume.

One Haiku call per resume. Returns structured experiences ready for user
review and DB insertion. Used by `corpus_import.py --with-llm` and (later)
by the `/onboard` wizard.

Per the plan §Onboarding step 3:
- ONE candidate-inferred title per experience initially (alternates added
  lazily at first-use friction, not eagerly during onboarding).
- Bullets are extracted verbatim where possible; suggested tags are
  proposed with `confidence < 1.0` until user confirms.
- `has_outcome` flag set deterministically by METRIC_RE post-extraction;
  the LLM doesn't decide this.

Cost: ~$0.01-0.03 per import run (Haiku, no cached prefix since this is
one-shot). Reuses `analyzer._parse_or_retry` for telemetry parity and
retry-on-malformed-JSON behavior.
"""

from __future__ import annotations

import logging
import re
from typing import Any, TypedDict

import anthropic
from pydantic import BaseModel, ConfigDict

from analyzer import HAIKU_MODEL, _parse_or_retry
from hardening import METRIC_RE

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class ExtractedBullet(TypedDict, total=False):
    """One résumé bullet extracted by the LLM — verbatim text plus suggested tags."""

    text: str
    suggested_tags: list[str]
    has_outcome: bool


class ExtractedExperience(TypedDict, total=False):
    """One job/role extracted by the LLM — company, dates, title, summary, and bullets."""

    company: str
    location: str
    start_date: str  # YYYY-MM or YYYY
    end_date: str | None  # None = current
    candidate_inferred_title: str
    summary: str | None  # role-intro paragraph (distinct from bullets), if present
    suggested_role_tags: list[str]
    bullets: list[ExtractedBullet]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


EXTRACT_REQUIRED_KEYS = frozenset({"experiences"})


class ExtractResponse(BaseModel):
    """Permissive response schema for the experience-extraction LLM call (extra keys allowed)."""

    model_config = ConfigDict(extra="allow")
    experiences: Any


EXTRACT_EXPERIENCES_SYSTEM_PROMPT = """You are a resume parser converting unstructured resume text into a structured career corpus.

Your job: identify each distinct job/role the candidate has held and extract the company, dates, role title, and bullets EXACTLY as written. You preserve the candidate's voice and the literal text of each bullet — you do not rewrite, expand, or summarize.

OUTPUT SHAPE: JSON object with one key, "experiences", whose value is an array. Each experience is an object with these fields:
- "company" (string, required) — the employer/organization name
- "location" (string, optional) — city/state if shown
- "start_date" (string, required) — "YYYY-MM", or just "YYYY" when only the year is shown (year-only is fine — many résumés list years only)
- "end_date" (string or null) — "YYYY-MM", "YYYY", or null for current/ongoing
- "candidate_inferred_title" (string, required) — ONE title that best describes the role as the candidate wrote it. If multiple titles appear (promotions within the same company over time), pick the most recent / highest. Alternate framings will be added later by the user.
- "summary" (string or null, optional) — the role's INTRO / SCOPE paragraph if one appears under the title (a prose sentence or two describing the role, team, or mandate — NOT an achievement). This is distinct from bullets. If the role has no intro paragraph, use null. Do NOT put this text in "bullets".
- "suggested_role_tags" (array of strings) — 1-3 short lowercase hyphenated tags from this controlled vocabulary when applicable: pm, ic-design, design-mgmt, eng-mgmt, sre, ai-product, ai-research, spatial, physical-compute, marketing, sales, ops, founder, generalist. Use what fits; don't invent.
- "bullets" (array) — each bullet is an object:
    - "text" (string, required) — VERBATIM text from the resume. Strip leading bullet glyphs (•, -, *) and surrounding whitespace, but preserve every word, number, and punctuation mark inside.
    - "suggested_tags" (array of strings) — 0-3 short tags identifying domains/skills/tech mentioned (e.g. "kubernetes", "leadership", "user-research"). Lowercase, hyphenated.

RULES:
- NEVER invent companies, dates, titles, or bullets. If the source is ambiguous, leave the field empty or null.
- NEVER rephrase bullets. Copy them as written — that's the candidate's voice and the grounding signal for the whole pipeline. If the bullet runs over multiple lines in the source, join them with a single space; otherwise preserve verbatim.
- A role INTRO / SCOPE paragraph (prose describing the role, not an achievement) goes in "summary", NEVER in "bullets". Achievement lines go in "bullets".
- Multiple roles at the same company become MULTIPLE experiences (one per distinct title + date range). Don't merge them.
- If a section is non-experience (Skills, Education, Projects, Publications) — IGNORE IT. This call returns experiences only. Other extractors handle the rest.
- If you cannot identify even a start YEAR for an experience, OMIT THE WHOLE EXPERIENCE rather than guessing. A bare year is enough to keep the role. Dates anchor the audit trail.
- Output JSON only — no markdown fences, no preamble, no commentary."""


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_experiences(
    client: anthropic.Anthropic,
    resume_text: str,
    *,
    username: str = "",
    run_id: str = "",
) -> list[ExtractedExperience]:
    """Extract structured experiences from a parsed resume.

    Returns an empty list if the resume contains no recognizable
    experience section. Raises LLMResponseError if the model can't produce
    valid JSON after retries.

    The resume_text should be the full plaintext (from parser.parse_resume),
    not just one section — the LLM does its own section identification.
    """
    if not resume_text.strip():
        return []

    user_prompt = (
        "<task>Extract experiences from the resume below. "
        "Return JSON with 'experiences' array. "
        "Preserve bullet text verbatim.</task>\n\n"
        "<resume>\n"
        f"{resume_text}\n"
        "</resume>"
    )

    data = _parse_or_retry(
        client,
        user_prompt,
        cached_user_prefix="",  # one-shot call; no prefix worth caching
        response_model=ExtractResponse,
        call_kind="extract_experiences",
        username=username,
        run_id=run_id,
        system_prompt=EXTRACT_EXPERIENCES_SYSTEM_PROMPT,
        model=HAIKU_MODEL,
    )

    raw_experiences = data.get("experiences") or []
    if not isinstance(raw_experiences, list):
        logger.warning(
            "extract_experiences: 'experiences' field is not a list, got %r", type(raw_experiences)
        )
        return []

    return [_normalize_experience(exp) for exp in raw_experiences if isinstance(exp, dict)]


# ---------------------------------------------------------------------------
# Post-extraction normalization (deterministic)
# ---------------------------------------------------------------------------


# Accept "YYYY-MM" or a bare "YYYY" — many résumés list years only, and a
# year-only stamp is fine for a résumé + more ATS-tolerant (walkthrough F3).
# Year-only is stored verbatim; downstream renders the date string as-is.
_DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")


def _normalize_experience(raw: dict) -> ExtractedExperience:
    """Clean up an LLM-extracted experience, dropping fields that don't validate.

    Outcome-detection (has_outcome) is computed deterministically here rather
    than trusting the LLM — METRIC_RE in hardening.py is the project's
    canonical "does this bullet contain a verbatim quantity" check.
    """
    exp: ExtractedExperience = {
        "company": _clean_str(raw.get("company")),
        "start_date": _clean_str(raw.get("start_date")),
        "candidate_inferred_title": _clean_str(raw.get("candidate_inferred_title")),
        "bullets": [],
        "suggested_role_tags": _clean_tag_list(raw.get("suggested_role_tags")),
    }

    location = _clean_str(raw.get("location"))
    if location:
        exp["location"] = location

    summary = _clean_str(raw.get("summary"))
    exp["summary"] = summary or None

    end_date = raw.get("end_date")
    exp["end_date"] = None if end_date is None else _clean_str(end_date) or None

    # Drop experiences whose start date isn't a year (optionally with a month).
    if not exp["start_date"] or not _DATE_RE.match(exp["start_date"]):
        return {"company": "", "start_date": "", "candidate_inferred_title": "", "bullets": []}

    raw_bullets = raw.get("bullets") or []
    if isinstance(raw_bullets, list):
        exp["bullets"] = [_normalize_bullet(b) for b in raw_bullets if isinstance(b, dict)]
        # Drop any bullet with empty text after normalization.
        exp["bullets"] = [b for b in exp["bullets"] if b.get("text")]

    return exp


def _normalize_bullet(raw: dict) -> ExtractedBullet:
    """Normalize a raw bullet dict into an ``ExtractedBullet`` (clean text, tags, derived outcome flag)."""
    text = _clean_str(raw.get("text"))
    return {
        "text": text,
        "suggested_tags": _clean_tag_list(raw.get("suggested_tags")),
        "has_outcome": bool(METRIC_RE.search(text)) if text else False,
    }


def _clean_str(value: object) -> str:
    """Return ``value`` stripped if it is a ``str``, else ``""``."""
    return value.strip() if isinstance(value, str) else ""


def _clean_tag_list(value: object) -> list[str]:
    """Lowercase, hyphenate-spaces, dedupe; drop non-string entries."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, str):
            continue
        normalized = re.sub(r"\s+", "-", raw.strip().lower())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


__all__ = [
    "EXTRACT_EXPERIENCES_SYSTEM_PROMPT",
    "EXTRACT_REQUIRED_KEYS",
    "ExtractedBullet",
    "ExtractedExperience",
    "extract_experiences",
]

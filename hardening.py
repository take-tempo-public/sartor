"""Deterministic analysis tools — P1 Hardening, P2 Context Hygiene.

These replace what would otherwise be unreliable LLM work:
keyword extraction, ATS format checks, context assembly, plus four
post-generation metrics that act as a deterministic safety net for the
fuzzy LLM output (verb diversity, specificity density, n-gram source
overlap, per-call cost).
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CandidateInfo(TypedDict):
    name: str
    email: str
    phone: str
    linkedin_url: str
    website_url: str
    skills: list[str]
    certifications: list[str]
    education_summary: str
    notes: str
    profile_text: str


class ResumeInfo(TypedDict):
    format: str
    sections: list[dict]
    text: str
    filename: str
    path: str


class SupplementalResume(TypedDict):
    filename: str
    text: str
    sections: list[dict]


class DeterministicAnalysisBlock(TypedDict):
    jd_keywords: dict
    resume_keywords: dict
    keyword_overlap: dict
    ats_warnings: list[str]


class _ContextSetRequired(TypedDict):
    timestamp: str
    candidate: CandidateInfo
    resume: ResumeInfo
    supplemental_resumes: list[SupplementalResume]
    job_description: str
    deterministic_analysis: DeterministicAnalysisBlock


class ClarificationQuestion(TypedDict, total=False):
    id: str
    text: str
    target_gap: str
    kind: str  # "experience_probe" | "scope_probe"


class ContextSet(_ContextSetRequired, total=False):
    # Added by app.py after analyze(); not present at build_context_set time
    llm_analysis: dict
    run_id: str
    # The full set of questions surfaced by /api/clarify. Persisted (not cleared
    # by /api/answer-clarifications) so generate() can pair each answer with
    # its question text in the prompt.
    clarification_questions: list[ClarificationQuestion]
    # Question-id -> user's free-form answer. Skipped questions are absent.
    # Treated as first-person ground truth by generate() and may be cited in
    # output even when absent from the resume.
    clarifications: dict[str, str]

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

# Bullet-line detector. Permissive: matches `-`, `*`, `•`, or numbered
# bullets at the start of a line (after optional whitespace).
BULLET_LINE_RE = re.compile(r"^\s*[-*•]\s+(.*)$", re.MULTILINE)

# Pattern that matches a quantity inside a bullet. Captures percentages,
# currency, plain integers with optional `+`, and scale words. Tuned to
# match the kinds of numbers candidates legitimately put on resumes.
METRIC_RE = re.compile(
    r"(?:\d+%"                                # percentages: 50%
    r"|\$\s?\d[\d,]*(?:\.\d+)?[kKmMbB]?"      # currency: $2.4M, $500k
    r"|\b\d[\d,]*\+?\b"                       # plain ints: 30+, 12000
    r"|\b\d+(?:\.\d+)?\s?(?:k|m|b|million|billion|thousand|users|customers|clients|countries|teams?|reports|requests)\b"
    r")",
    re.IGNORECASE,
)

# Pricing per million tokens (USD). Source: anthropic.com pricing as of
# 2026-05-09. Update via PR (and bump CHANGELOG.md) when prices change.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "in": 3.00,
        "out": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4-5-20251001": {
        "in": 0.80,
        "out": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
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


def compute_verb_diversity(resume_text: str) -> dict:
    """Measure leading-verb variety across resume bullets.

    Repeated verbs signal lack of depth — already called out in
    SYSTEM_PROMPT. This metric makes the signal actionable by giving us a
    number we can chart and gate on.

    Operational range:
      - diversity_ratio >= 0.6: healthy
      - 0.4 <= ratio < 0.6: borderline; check top_repeated for offenders
      - ratio < 0.4: monotonous; the LLM is recycling verbs
    """
    bullets = BULLET_LINE_RE.findall(resume_text or "")
    if not bullets:
        return {
            "unique_verbs": 0,
            "total_bullets": 0,
            "diversity_ratio": 0.0,
            "top_repeated": [],
        }

    verbs: list[str] = []
    for body in bullets:
        first = body.strip().split()
        if not first:
            continue
        verb = first[0].lower().strip(".,;:()[]{}\"'")
        if verb:
            verbs.append(verb)

    counts = Counter(verbs)
    unique = len(counts)
    total = len(verbs)
    ratio = unique / total if total else 0.0
    repeated = [(v, c) for v, c in counts.most_common() if c > 1][:5]

    return {
        "unique_verbs": unique,
        "total_bullets": total,
        "diversity_ratio": round(ratio, 3),
        "top_repeated": repeated,
    }


def compute_specificity_density(resume_text: str) -> dict:
    """Fraction of bullets that contain at least one quantifiable metric.

    Pairs with the grounding metric: high specificity + low grounding =
    invented numbers. Low specificity is also a signal — the candidate or
    the LLM is hiding behind qualitative language.

    Operational range:
      - 0.4 <= density <= 0.8: healthy mix of qualitative and quantified
      - density > 0.8: number-stuffing; check grounding score
      - density < 0.4: under-quantified; likely missing real metrics from source
    """
    bullets = BULLET_LINE_RE.findall(resume_text or "")
    if not bullets:
        return {
            "total_bullets": 0,
            "bullets_with_metric": 0,
            "density": 0.0,
            "metric_count": 0,
        }

    bullets_with = 0
    metric_count = 0
    for body in bullets:
        matches = METRIC_RE.findall(body)
        if matches:
            bullets_with += 1
            metric_count += len(matches)

    density = bullets_with / len(bullets) if bullets else 0.0

    return {
        "total_bullets": len(bullets),
        "bullets_with_metric": bullets_with,
        "density": round(density, 3),
        "metric_count": metric_count,
    }


def _ngrams(text: str, n: int) -> list[tuple[str, ...]]:
    """Tokenize and emit n-grams. Lowercase, alphanumeric-only tokens."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_grounding_overlap(
    generated_text: str,
    source_texts: list[str],
    n: int = 3,
) -> dict:
    """Deterministic backstop for the LLM grounding rubric.

    Computes the fraction of n-grams in the generated output that also
    appear (verbatim) in any source text. n-grams composed entirely of
    stopwords are ignored as they generate noise without signal.

    The actionable output is `missing_samples`: up to 10 generated 3-grams
    absent from every source. Items containing technology names, domain
    nouns, or company-specific phrasing are strong evidence of fabrication.

    Operational range (empirically calibrated against the synthetic suite,
    where LLM-judged grounding scores 4.6+):
      - overlap_ratio >= 0.20: typical for healthy paraphrase
      - ratio < 0.15: inspect missing_samples — likely high invention
      - The ratio alone is NOT a pass/fail signal because legitimate
        rewriting reduces verbatim overlap. Treat missing_samples as the
        primary actionable evidence, not the ratio.
    """
    if not generated_text or not source_texts:
        return {
            "overlap_ratio": 0.0,
            "matched_ngrams": 0,
            "total_ngrams": 0,
            "missing_samples": [],
            "n": n,
        }

    source_set: set[tuple[str, ...]] = set()
    for src in source_texts:
        source_set.update(_ngrams(src, n))

    generated_ngrams = _ngrams(generated_text, n)
    if not generated_ngrams:
        return {
            "overlap_ratio": 0.0,
            "matched_ngrams": 0,
            "total_ngrams": 0,
            "missing_samples": [],
            "n": n,
        }

    matched = 0
    missing: list[str] = []
    for ng in generated_ngrams:
        if ng in source_set:
            matched += 1
        else:
            # Skip n-grams that are entirely stopwords — pure noise.
            if all(tok in STOP_WORDS for tok in ng):
                continue
            sample = " ".join(ng)
            if sample not in missing:
                missing.append(sample)
            if len(missing) >= 10:
                # Keep collecting matched count, stop appending samples
                pass

    return {
        "overlap_ratio": round(matched / len(generated_ngrams), 3),
        "matched_ngrams": matched,
        "total_ngrams": len(generated_ngrams),
        "missing_samples": missing[:10],
        "n": n,
    }


def compute_call_cost(record: dict) -> float:
    """Per-call USD cost given a telemetry record from logs/llm_calls.jsonl.

    Pure function: takes the record's model + token counts and returns
    USD rounded to 6 decimals. Unknown model returns 0.0 with a logged
    warning so dashboards don't silently undercount.

    Cost = (input * in_rate
          + output * out_rate
          + cache_creation * cache_write_rate
          + cache_read * cache_read_rate) / 1_000_000
    """
    model = record.get("model", "")
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        if model:
            logger.warning("compute_call_cost: unknown model %r — returning 0.0", model)
        return 0.0

    in_tok = record.get("input_tokens") or 0
    out_tok = record.get("output_tokens") or 0
    cache_w = record.get("cache_creation_input_tokens") or 0
    cache_r = record.get("cache_read_input_tokens") or 0

    cost = (
        in_tok * pricing["in"]
        + out_tok * pricing["out"]
        + cache_w * pricing["cache_write"]
        + cache_r * pricing["cache_read"]
    ) / 1_000_000.0
    return round(cost, 6)


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
) -> ContextSet:
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
            "profile_text": profile_text,
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


def save_context_set(context_set: ContextSet, username: str, base_dir: str = "output") -> str:
    """Save context set to disk as timestamped JSON. P4 Disposable Blueprint."""
    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"context_{ts}.json"
    path.write_text(json.dumps(context_set, indent=2), encoding="utf-8")
    return str(path)

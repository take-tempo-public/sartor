"""Deterministic analysis tools — P1 Hardening, P2 Context Hygiene.

These replace what would otherwise be unreliable LLM work:
keyword extraction, ATS format checks, context assembly, plus four
post-generation metrics that act as a deterministic safety net for the
fuzzy LLM output (verb diversity, specificity density, n-gram source
overlap, per-call cost).
"""

import difflib
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


class CorpusBullet(TypedDict, total=False):
    id: int
    text: str
    tags: list[str]
    has_outcome: bool
    source: str  # provenance: 'primary:<file>' | 'supplemental:<file>' | etc.


class CorpusEligibleTitle(TypedDict, total=False):
    id: int
    title: str
    is_official: bool


class CorpusExperience(TypedDict, total=False):
    id: int
    company: str
    location: str
    start_date: str
    end_date: str | None
    eligible_titles: list[CorpusEligibleTitle]
    bullets: list[CorpusBullet]


class ClarificationQuestion(TypedDict, total=False):
    id: str
    text: str
    target_gap: str
    kind: str  # "experience_probe" | "scope_probe" | "iteration_probe"


class IterationNote(TypedDict, total=False):
    timestamp: str
    action: str  # "generate" | "save_edits" | "iterate_clarify" | "answer_iteration"
    summary: str


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
    # --- Iteration loop (Phase 1) ----------------------------------------------
    # 0 = analyze-only; 1+ = state AFTER the Nth generation. The condition
    # context_set.get("iteration", 0) >= 1 controls whether the next generate
    # treats the original primary + supplementals as historical references and
    # treats the current draft (edited or last_generated) as the <resume> block.
    iteration: int
    # Path to the context file this one was derived from. Forms the audit chain.
    parent_context_path: str
    # When set by /api/save-edits, replaces the <resume>/<cover_letter> block
    # for the NEXT generate() call. Consumed (cleared) on the new iteration
    # context that generate() writes.
    edited_resume_text: str
    edited_cover_letter_text: str
    # Per-iteration metadata appended by routes. Useful for the dashboard to
    # reconstruct the user's path through the loop. Append-only; never rewritten.
    iteration_notes: list[IterationNote]
    # Frozen-at-generation snapshot of what the LLM produced. The frontend
    # diffs the live preview against this to detect user edits.
    last_generated_resume: str
    last_generated_cover_letter: str
    # Phase B.2: when populated by db.build_context.build_context_set_from_db,
    # the LLM prompt emits a structured <career_corpus> XML block instead of
    # the legacy <resume> block, and the generate output schema requires
    # selected_bullets / proposed_new_bullets / proposed_experience_titles.
    # When absent, the file-based path runs unchanged.
    career_corpus: list[CorpusExperience]
    # Phase B.3: DB anchor IDs persisted across the analyze→generate boundary.
    # /api/analyze (corpus-backed) stashes them; /api/generate reads them and
    # writes application_bullet / proposal_review rows to record the LLM's
    # selections and proposals. Absent on file-based contexts.
    application_id: int
    application_run_id: int
    # Wizard "Compose" step (Workstream B + H + I): user overrides on the
    # per-application fit-ranked corpus.
    #   {"pinned":   [bullet_id...],   # must-include
    #    "excluded": [bullet_id...],   # drop from prompt entirely
    #    "added":    [bullet_id...]}   # pulled in via the per-experience drawer (I)
    # generate() drops excluded bullets, marks pinned ones must-include,
    # and when llm_recommendations is also present restricts the corpus to
    # (recommended ∪ added ∪ pinned) − excluded. total=False so older
    # contexts round-trip unchanged.
    composition_overrides: dict
    # Workstream H: the recommend_bullets() output keyed by experience id
    # (str or int). {"<exp_id>": {"bullet_ids": [<int>...], "rationale": str}}
    # When present, the corpus block restricts to the curated effective set.
    # total=False — applications generated before the recommendation step
    # ran (or whose call failed) keep the prior full-corpus behavior.
    llm_recommendations: dict

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


_DEDUP_TOKEN_RE = re.compile(r"\b[a-zA-Z][a-zA-Z+#.-]{1,}\b")


def bullet_token_set(text: str) -> frozenset[str]:
    """Tokenize a bullet for near-duplicate detection.

    Lowercase, drop stopwords + tokens <3 chars. Returns a frozenset so
    the result is cheap to compare across bullets. Used by
    `bullet_jaccard()` and the corpus-duplicates clusterer (B1.2)."""
    return frozenset(
        w for w in _DEDUP_TOKEN_RE.findall((text or "").lower())
        if w not in STOP_WORDS and len(w) > 2
    )


def bullet_jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two bullet texts on `bullet_token_set`.
    Returns 0.0 when both are empty (degenerate)."""
    sa = bullet_token_set(a)
    sb = bullet_token_set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


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


def summarize_recent_edits(context_set: ContextSet) -> str:
    """Compact text summary of what the candidate edited since last generation.

    Used by both /api/iterate-clarify (live route) and the eval runner
    (simulated iteration). Output is a short unified diff per document,
    capped to keep prompt tokens predictable. Returns "" when no edits exist.
    """
    parts: list[str] = []
    for label, before_key, after_key in (
        ("resume", "last_generated_resume", "edited_resume_text"),
        ("cover_letter", "last_generated_cover_letter", "edited_cover_letter_text"),
    ):
        # Values come from JSON-loaded TypedDict fields whose value type mypy
        # widens to object — coerce to str via fallback before .strip().
        before_raw = context_set.get(before_key) or ""
        after_raw = context_set.get(after_key) or ""
        before = str(before_raw).strip()
        after = str(after_raw).strip()
        if not after or before == after:
            continue
        diff = list(difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"prior_{label}", tofile=f"edited_{label}",
            lineterm="", n=2,
        ))
        if not diff:
            continue
        # Cap at first ~60 diff lines — covers most bullet-level edits without
        # blowing prompt tokens for users who rewrote whole sections.
        snippet = "\n".join(diff[:60])
        if len(diff) > 60:
            snippet += f"\n... [{len(diff) - 60} more diff lines truncated]"
        parts.append(f"## {label} edits\n{snippet}")
    return "\n\n".join(parts)


def compute_iteration_signals(
    context_set: ContextSet,
    current_resume_text: str,
) -> dict:
    """Compute the four deterministic signal sources for the iteration clarifier.

    Each signal is independently informative — the LLM uses them to target
    questions at concrete weaknesses rather than guessing. Names match the
    metric functions above so the dashboard can correlate iteration-time
    signals with the post-generation metrics that ride along on every
    eval result.
    """
    overlap = (context_set.get("deterministic_analysis", {}) or {}).get("keyword_overlap", {}) or {}
    jd_kw_set = set(overlap.get("matched", [])) | set(overlap.get("missing_from_resume", []))

    # Recompute keyword coverage against the CURRENT draft. The analyzer's
    # original overlap was vs the original primary; the diff (original missing
    # minus current missing) tells the LLM whether a recent revision actually
    # closed any keyword gaps.
    current_kw = extract_keywords(current_resume_text or "")
    current_kw_set = set(current_kw.get("keywords", {}).keys())
    still_missing = sorted(set(overlap.get("missing_from_resume", [])) - current_kw_set)

    # Sources for grounding overlap mirror what generate() considers ground
    # truth: original primary, supplementals, clarification answers.
    source_texts: list[str] = []
    primary_text = (context_set.get("resume", {}) or {}).get("text", "")
    if primary_text:
        source_texts.append(primary_text)
    for s in context_set.get("supplemental_resumes", []) or []:
        if s.get("text"):
            source_texts.append(s["text"])
    for ans in (context_set.get("clarifications") or {}).values():
        if ans:
            source_texts.append(ans)

    return {
        "verb_diversity": compute_verb_diversity(current_resume_text),
        "specificity_density": compute_specificity_density(current_resume_text),
        "grounding_overlap": compute_grounding_overlap(current_resume_text, source_texts),
        "keyword_coverage": {
            "jd_total": len(jd_kw_set),
            "still_missing_from_current_draft": still_missing[:20],
            "still_missing_count": len(still_missing),
        },
    }


def save_iteration_context(
    parent_context: ContextSet,
    parent_path: str,
    last_generated_resume: str,
    last_generated_cover_letter: str,
    username: str,
    base_dir: str = "output",
    action: str = "generate",
    summary: str = "",
) -> str:
    """Persist a new iteration context derived from a parent context.

    Used by /api/generate to record each iteration as its own immutable file
    rather than mutating the prior one. The chain of `parent_context_path`
    pointers is the audit trail; the dashboard can walk it to render iteration
    progression.

    Behavior:
      - Deep-copies parent_context (avoid aliasing surprises if the caller
        keeps reading from it after this call returns).
      - Increments `iteration` by 1 (parent default 0 → child 1).
      - Sets `parent_context_path` to parent_path.
      - Sets `last_generated_resume` / `last_generated_cover_letter` to the
        freshly generated text (used by the frontend to diff against the live
        preview for edit detection on the NEXT iteration).
      - Clears `edited_resume_text` / `edited_cover_letter_text` — those were
        consumed by generate() to build the prompt; carrying them forward
        would cause double-application on the next iteration.
      - Appends an IterationNote so dashboards can reconstruct the path.
      - Writes to `context_{ts}_iter{N}.json` to keep the iteration count
        visible at the filename level. Pre-iteration files (`context_{ts}.json`,
        no iter suffix) remain on disk untouched.
    """
    child: ContextSet = json.loads(json.dumps(parent_context))  # deep copy via JSON round-trip
    child["iteration"] = int(parent_context.get("iteration", 0)) + 1
    child["parent_context_path"] = parent_path
    child["last_generated_resume"] = last_generated_resume
    child["last_generated_cover_letter"] = last_generated_cover_letter
    # Consume edits — they fed the prompt that produced this generation; they
    # must not re-apply on the next iteration's generate() call.
    child.pop("edited_resume_text", None)
    child.pop("edited_cover_letter_text", None)

    notes: list[IterationNote] = list(child.get("iteration_notes") or [])
    notes.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "summary": summary or f"iteration {child['iteration']}",
    })
    child["iteration_notes"] = notes

    out_dir = Path(base_dir) / username
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"context_{ts}_iter{child['iteration']}.json"
    path.write_text(json.dumps(child, indent=2), encoding="utf-8")
    return str(path)

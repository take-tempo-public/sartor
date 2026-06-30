"""Deterministic experience-similarity scoring (no LLM).

Decides whether two job experiences are the SAME role wearing different
framings/dates or two genuinely distinct roles. Used by the merge-suggestion
endpoint to surface "possible duplicate roles" for a human merge/keep-separate
decision — the importer keeps auto-merging only EXACT `(company, start_date)`
matches, so everything fuzzy routes through here and is asked, never merged
silently.

Pure stdlib (`difflib` + `re`); no Anthropic client, no network. That keeps it
inside the P1 hardening boundary (charter C-6 — deterministic modules never call
an LLM) and makes every band decision unit-testable.

Bands:
- ``EXACT``    — normalized company equal AND ``start_date`` equal. The importer
  already folds these automatically; included for completeness + tests.
- ``SIMILAR``  — same company, score at/above :data:`SIMILAR_THRESHOLD` but not
  exact. Surface a merge SUGGESTION and let the user decide.
- ``DISTINCT`` — companies differ, or score below threshold. Separate roles.

The four signals the scorer combines — company, title, dates, bullets — are the
ones the product owner named for "is this the same job?".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# --- tuning knobs (locked by tests; revisit against real fixtures) -----------
COMPANY_GATE = 0.6
"""Below this normalized-company similarity, the pair is DISTINCT outright.

Different employers are almost never the same role, so company gates the whole
score — no amount of title/bullet overlap rescues a company mismatch.
"""

SIMILAR_THRESHOLD = 0.55
"""Combined score at/above which a same-company pair becomes a SIMILAR suggestion."""

ADJACENT_MONTHS = 3
"""Date ranges within this gap (months) count as adjacent (e.g. a promotion)."""

_W_COMPANY, _W_TITLE, _W_DATES, _W_BULLETS = 0.40, 0.20, 0.15, 0.25
_OPEN_END_MONTHS = 1200  # treat a NULL end_date as ~100 years out (still "current")
_FUZZY_BULLET_RATIO = 0.85  # a lightly reworded bullet still counts as shared

# Legal-form suffixes stripped before comparing company names. Only unambiguous
# corporate forms — NOT meaningful name words like "group" / "holdings".
_LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "corp",
        "corporation",
        "ltd",
        "limited",
        "co",
        "company",
        "gmbh",
        "plc",
        "llp",
        "lp",
        "sa",
        "ag",
        "pte",
        "pty",
    }
)

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")
_YM_RE = re.compile(r"(\d{4})-(\d{2})")


@dataclass(frozen=True, slots=True)
class ExperienceLike:
    """Plain-value view of one experience for scoring (decoupled from the ORM)."""

    company: str
    start_date: str
    end_date: str | None
    titles: tuple[str, ...]
    bullets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchScore:
    """The verdict for one experience pair: band, total, and per-signal scores."""

    band: str  # "EXACT" | "SIMILAR" | "DISTINCT"
    score: float
    company: float
    title: float
    dates: float
    bullets: float
    matched_signals: tuple[str, ...]


def _norm_text(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", s.lower())).strip()


def normalize_company(company: str) -> str:
    """Normalize a company name: lowercase, depunctuate, drop legal suffixes."""
    tokens = [t for t in _norm_text(company).split(" ") if t]
    while tokens and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def company_similarity(a: str, b: str) -> float:
    """Similarity of two company names after normalization (0..1)."""
    na, nb = normalize_company(a), normalize_company(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def title_similarity(a: str, b: str) -> float:
    """Similarity of two titles — max of edit-ratio and token-set Jaccard (0..1)."""
    na, nb = _norm_text(a), _norm_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    union = ta | tb
    jaccard = len(ta & tb) / len(union) if union else 0.0
    return max(ratio, jaccard)


def _best_title_similarity(titles_a: tuple[str, ...], titles_b: tuple[str, ...]) -> float:
    """Best title-pair similarity across two experiences' title lists."""
    best = 0.0
    for ta in titles_a:
        for tb in titles_b:
            best = max(best, title_similarity(ta, tb))
    return best


def _ym_ordinal(s: str | None) -> int | None:
    """Parse 'YYYY-MM' to a month ordinal (year*12 + month), or None if unparseable."""
    if not s:
        return None
    m = _YM_RE.fullmatch(s.strip())
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return None
    return year * 12 + (month - 1)


def date_similarity(start_a: str, end_a: str | None, start_b: str, end_b: str | None) -> float:
    """Similarity of two date ranges: 1.0 same start, overlap coefficient, else adjacency (0..1)."""
    osa, osb = _ym_ordinal(start_a), _ym_ordinal(start_b)
    if osa is None or osb is None:
        return 0.0
    if osa == osb:
        return 1.0
    oea, oeb = _ym_ordinal(end_a), _ym_ordinal(end_b)
    end_a_ord = oea if oea is not None else osa + _OPEN_END_MONTHS
    end_b_ord = oeb if oeb is not None else osb + _OPEN_END_MONTHS
    lo, hi = max(osa, osb), min(end_a_ord, end_b_ord)
    overlap = hi - lo + 1
    if overlap > 0:
        span = min(end_a_ord - osa + 1, end_b_ord - osb + 1)
        return overlap / span if span > 0 else 0.0
    gap = -overlap  # months between the two ranges
    if gap <= ADJACENT_MONTHS:
        return 0.5 * (1 - gap / (ADJACENT_MONTHS + 1))
    return 0.0


def _normalized_bullets(bullets: tuple[str, ...]) -> list[str]:
    """Normalized, non-empty bullet texts for overlap comparison."""
    return [t for t in (_norm_text(b) for b in bullets) if t]


def shared_bullet_count(bullets_a: tuple[str, ...], bullets_b: tuple[str, ...]) -> int:
    """Count bullets shared between two sets (exact-normalized or lightly reworded)."""
    na, nb = _normalized_bullets(bullets_a), _normalized_bullets(bullets_b)
    if not na or not nb:
        return 0
    small, large = (na, nb) if len(na) <= len(nb) else (nb, na)
    large_set = set(large)
    shared = 0
    for s in small:
        if s in large_set or any(
            SequenceMatcher(None, s, big).ratio() >= _FUZZY_BULLET_RATIO for big in large
        ):
            shared += 1
    return shared


def bullet_overlap(bullets_a: tuple[str, ...], bullets_b: tuple[str, ...]) -> float:
    """Fraction of the smaller bullet set shared with the larger (exact or lightly reworded)."""
    na, nb = _normalized_bullets(bullets_a), _normalized_bullets(bullets_b)
    if not na or not nb:
        return 0.0
    return shared_bullet_count(bullets_a, bullets_b) / min(len(na), len(nb))


def score_experiences(a: ExperienceLike, b: ExperienceLike) -> MatchScore:
    """Score one experience pair across all four signals and assign a band.

    Company gates the verdict: below :data:`COMPANY_GATE` the pair is DISTINCT
    regardless of other overlap. Above it, an exact normalized-company +
    start-date match is EXACT; otherwise the weighted score decides SIMILAR vs
    DISTINCT at :data:`SIMILAR_THRESHOLD`.
    """
    comp = company_similarity(a.company, b.company)
    title = _best_title_similarity(a.titles, b.titles)
    dates = date_similarity(a.start_date, a.end_date, b.start_date, b.end_date)
    bullets = bullet_overlap(a.bullets, b.bullets)
    score = _W_COMPANY * comp + _W_TITLE * title + _W_DATES * dates + _W_BULLETS * bullets

    norm_company = normalize_company(a.company)
    is_exact = (
        bool(norm_company)
        and norm_company == normalize_company(b.company)
        and (a.start_date == b.start_date)
    )

    if comp < COMPANY_GATE:
        band = "DISTINCT"
    elif is_exact:
        band = "EXACT"
    elif score >= SIMILAR_THRESHOLD:
        band = "SIMILAR"
    else:
        band = "DISTINCT"

    signals: list[str] = []
    if comp >= COMPANY_GATE:
        signals.append("company")
    if title >= 0.6:
        signals.append("title")
    if dates >= 0.5:
        signals.append("dates")
    if bullets > 0:
        signals.append("bullets")

    return MatchScore(
        band=band,
        score=round(score, 4),
        company=round(comp, 4),
        title=round(title, 4),
        dates=round(dates, 4),
        bullets=round(bullets, 4),
        matched_signals=tuple(signals),
    )

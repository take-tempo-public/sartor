"""`assemble()` — the RETRIEVE → ASSEMBLE seam, and the package's one entry point.

Stage 0 skeleton (Sprint 7.4). Given a query, a `Scope`, and a set of injected
`Source`s, produce the bounded, cited `Context` that feeds ONE avatar turn:

    search each source  →  fuse (Reciprocal Rank Fusion)  →  access-filter
    →  token-budget pack  →  Context

Fusion and packing are pure, deterministic, project-agnostic algorithms — the
genuine reusable value of the skeleton. They never rewrite a unit's text, so the
provenance stamp survives into the `Context` (the grounding plane holds). The
canonical 2-arg form `assemble(query, scope)` documented in
`docs/dev/memory-architecture.md` is the thin project-wired convenience 7.5 adds
once it registers the real wiki/git sources via config; here the sources are
injected explicitly so `recall/` stays project-agnostic (it imports no tier).

Stage 0 ships no real tier — the S1 wiki + S2 `git grep` sources are 7.5, the S3
vector tier is 7.6. Deterministic + stdlib-only — P1 Hardening boundary (charter
C-6).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from recall.models import Context, Scope, Unit
from recall.planes import filter_units
from recall.source import Source

# Reciprocal Rank Fusion damping constant. 60 is the value from the original
# Cormack et al. RRF paper and the de-facto default; large enough that the
# fused score is dominated by *agreement across sources*, not any single rank.
_RRF_K = 60

# Deterministic token-size heuristic (~4 chars per token). Intentionally crude:
# the budget is a guardrail, not an accountant. The real tokenizer is an avatar
# concern (7.5), kept out of the dependency-free substrate.
_CHARS_PER_TOKEN = 4


def assemble(query: str, scope: Scope, sources: Iterable[Source] = ()) -> Context:
    """Build the cited, budgeted feed for one avatar turn.

    Searches every source, fuses the ranked pools with RRF, drops units that
    exceed `scope` (the access/disclosure plane), then packs the highest-scoring
    survivors up to `scope.token_budget`. The returned `Context.units` are in
    final presentation order (best first), each still carrying its stamp.
    """
    pools = [tuple(source.search(query, scope)) for source in sources]
    fused = _rrf_fuse(pools)
    allowed = filter_units(fused, scope)
    packed, tokens, truncated = _pack_to_budget(allowed, scope.token_budget)
    return Context(query=query, units=tuple(packed), token_estimate=tokens, truncated=truncated)


def _rrf_fuse(pools: Sequence[Sequence[Unit]]) -> list[Unit]:
    """Fuse per-source ranked pools into one ranking by Reciprocal Rank Fusion.

    A unit's fused score is the sum over the pools it appears in of
    `1 / (_RRF_K + rank)` (1-based rank). Units are deduplicated by their
    `(source_id, citation)` stamp, so the same source unit surfacing in several
    pools accumulates evidence. The result is sorted best-first with a stable
    `(source_id, citation)` tiebreak so the ordering is fully deterministic.
    """
    contributions: dict[tuple[str, str], float] = {}
    first_seen: dict[tuple[str, str], Unit] = {}
    for pool in pools:
        for rank, unit in enumerate(pool):
            key = (unit.source_id, unit.citation)
            contributions[key] = contributions.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
            first_seen.setdefault(key, unit)
    fused = [replace(first_seen[key], score=score) for key, score in contributions.items()]
    fused.sort(key=lambda u: (-u.score, u.source_id, u.citation))
    return fused


def _pack_to_budget(units: Sequence[Unit], budget: int) -> tuple[list[Unit], int, bool]:
    """Take the highest-scoring prefix of `units` that fits within `budget`.

    Units are already in score order. Each costs `_estimate_tokens(text)`; the
    first unit that would overflow the budget stops the pack (a strict
    score-ordered prefix — predictable and easy to reason about) and marks the
    `Context` truncated. Returns `(packed, total_tokens, truncated)`.
    """
    packed: list[Unit] = []
    total = 0
    truncated = False
    for unit in units:
        cost = _estimate_tokens(unit.text)
        if total + cost > budget:
            truncated = True
            break
        packed.append(unit)
        total += cost
    return packed, total, truncated


def _estimate_tokens(text: str) -> int:
    """Deterministic ~tokens estimate for `text` (≥ 1 for any non-empty unit)."""
    return max(1, len(text) // _CHARS_PER_TOKEN)

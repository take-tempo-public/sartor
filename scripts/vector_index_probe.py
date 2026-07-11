"""Measure what the S3 vector tier adds over the lexical tiers — the eval-gate probe.

Stage 2 (Sprint 7.6). The vector tier was built ahead of the formal v1.0.8 labeled eval
loop at owner direction (the Stage-1 assistant tested "too literal / lacking semantic
flexibility"). This probe is the lightweight, reproducible corroboration: for a set of
real dev/code-vocabulary questions, it runs `recall.assemble` with the Stage-1 tiers
(wiki + git grep + session) and again with the S3 vector tier added, and reports:

  * LEXICAL MISS  — questions where `git grep` (S2) returned nothing (the salient token
    isn't a literal match) — the vocabulary gap the wiki may also not cover;
  * VECTOR RECOVERED — of those, how many the vector tier answered with ≥1 code chunk;
  * the new `path:line` citations the vector tier surfaced that the lexical pass missed.

It needs a built index — run `python -m scripts.build_vector_index` first. With no model
+ index it reports that and exits 0 (the harness still documents the methodology).

Usage:
    python -m scripts.build_vector_index        # one-time, builds the index
    python -m scripts.vector_index_probe        # then measure
"""

from __future__ import annotations

import logging

from blueprints.assistant import _VECTOR_INDEX_DIR, _build_sources, _make_embedder
from recall import Scope, Tier, VectorSource
from recall.models import Unit
from recall.source import Source

logger = logging.getLogger(__name__)

# Real dev questions phrased the way a human asks them — deliberately NOT using the exact
# code identifier, so the lexical S2 tier (longest-token `git grep`) often misses and the
# semantic S3 tier has to bridge the vocabulary gap.
QUESTIONS = [
    "how does the app stop someone reading files outside the user folder",
    "where do we keep the assistant from making up facts it can't cite",
    "how is a retrieved snippet tagged as user-facing versus internal",
    "how do we fuse results from several retrieval sources into one ranking",
    "what keeps the memory package from depending on the web framework",
    "how does the index avoid recomputing embeddings for unchanged files",
    "where is the cover letter opening tone handled",
    "how does the resume keep the original document styling",
    "what stops a network call from leaking data during a test",
    "how does the wizard remember answers between the steps",
    "where do we turn a job description into ranked keywords",
    "how is the streamed chat answer sent to the browser",
]

_TOP = 3  # show at most this many new vector citations per question


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sources = _build_sources([])
    has_vector = any(isinstance(s, VectorSource) for s in sources)
    if not has_vector:
        embedder = _make_embedder()
        reason = "model not downloaded" if embedder is None else "index not built"
        logger.info(
            "S3 vector tier inactive (%s). Run `python -m scripts.build_vector_index` "
            "first, then re-run this probe. Index dir: %s",
            reason,
            _VECTOR_INDEX_DIR,
        )
        return 0

    base_tiers = frozenset({Tier.WIKI, Tier.GIT, Tier.SESSION})
    vec_tiers = base_tiers | {Tier.VECTOR}

    lexical_miss = 0
    vector_recovered = 0
    logger.info("question | git(S2) hits | vector new cites")
    logger.info("-" * 72)
    for q in QUESTIONS:
        base = assemble_units(q, base_tiers, sources)
        withvec = assemble_units(q, vec_tiers, sources)
        git_hits = sum(1 for u in base if u.tier is Tier.GIT)
        base_keys = {(u.source_id, u.citation) for u in base}
        new_vec = [
            u
            for u in withvec
            if u.tier is Tier.VECTOR and (u.source_id, u.citation) not in base_keys
        ]
        if git_hits == 0:
            lexical_miss += 1
            if new_vec:
                vector_recovered += 1
        cites = ", ".join(u.citation for u in new_vec[:_TOP]) or "-"
        logger.info("%-52s | %2d | %s", q[:52], git_hits, cites)

    logger.info("-" * 72)
    logger.info(
        "%d/%d questions had NO git-grep hit (lexical miss); the vector tier recovered "
        "%d of those with a cited code chunk.",
        lexical_miss,
        len(QUESTIONS),
        vector_recovered,
    )
    return 0


def assemble_units(query: str, tiers: frozenset[Tier], sources: list[Source]) -> list[Unit]:
    """Retrieve for `query` with `tiers` enabled (allow_dev so code chunks are admitted)."""
    from recall import assemble

    scope = Scope(allow_dev=True, enabled_tiers=tiers, token_budget=4000)
    return list(assemble(query, scope, sources).units)


if __name__ == "__main__":
    raise SystemExit(main())

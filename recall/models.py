"""Value types for the `recall/` Memory substrate — the provenance plane.

Stage 0 skeleton (Sprint 7.4). These four types ARE the public contract the
avatar (7.5) and the self-documenting wiki loop build against:

    Unit     — one provenance-stamped source unit (never a rewritten fact)
    Tier     — which source family produced it (S1 wiki … S5 session)
    Audience — the access/disclosure tag (user | dev)
    Scope    — the caller's allowed window (toggle + enabled tiers + budget)
    Context  — the assembled, budgeted, cited feed for ONE avatar turn

The **provenance / grounding plane** lives here: every `Unit` is stamped with
`(tier, source_id, citation, audience, sha)` and cannot be constructed without
its stamp (see `Unit.__post_init__`). Retrieval returns source units, assembly
only filters / reorders / truncates them — the text is never rewritten, so the
stamp survives end to end. See `docs/dev/memory-architecture.md` §"The two
cross-cutting planes".

Deterministic + stdlib-only by design — P1 Hardening boundary (charter C-6).
This module never imports `app.py`, `analyzer.py`, the DB models, or Flask;
`tests/test_recall_boundary.py` enforces that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    """Source family a `Unit` came from, matching the S1…S5 labels in memory-architecture.md.

    Values match `docs/dev/memory-architecture.md` §"Tiers". Stage 0 implements no real
    tier; these name the slots the 7.5/7.6 sources fill.
    """

    WIKI = "S1"  # committed docs/wiki synthesis (answer-shaped prose)
    GIT = "S2"  # files on disk + `git grep` (native path:line citation)
    VECTOR = "S3"  # static-embedding semantic search (deferred → 7.6)
    STRUCTURE = "S4"  # symbol graph / "what calls X" (deferred tier)
    SESSION = "S5"  # interaction memory — the avatar's memory of you


class Audience(str, Enum):
    """The access/disclosure tag carried by every `Unit`.

    Path-derived per the wiki SCHEMA's blanket rules (code / docs/dev / evals → `dev`;
    user-facing docs → `user`). The `Scope` toggle decides which a caller may see.
    """

    USER = "user"
    DEV = "dev"


@dataclass(frozen=True, slots=True)
class Unit:
    """One retrieved, provenance-stamped source unit.

    The stamp `(tier, source_id, citation, audience, sha)` is mandatory: a
    `Unit` with empty `text` or empty `citation` is a contradiction (an
    uncitable fact) and raises at construction. `citation` is either a code
    cite (`path:line` / `path:symbol`) or a wiki cite (`[[page-slug]]`) —
    whatever the avatar must show so a reader can verify at source.
    """

    text: str
    tier: Tier
    source_id: str
    citation: str
    audience: Audience
    sha: str  # provenance sha of the source; "" is the pre-ingest sentinel
    score: float = 0.0

    def __post_init__(self) -> None:
        """Reject an uncitable unit: empty `text` or `citation` raises `ValueError`."""
        if not self.text.strip():
            raise ValueError("Unit.text must be non-empty — a unit carries a quotable fact.")
        if not self.citation.strip():
            raise ValueError(
                "Unit.citation must be non-empty — the provenance stamp is mandatory "
                "(path:line / path:symbol code cite, or [[page-slug]] wiki cite)."
            )


@dataclass(frozen=True, slots=True)
class Scope:
    """The access/disclosure plane's input — the caller's allowed window.

    `allow_dev` is the user/dev toggle: off → only `user`-audience units are
    surfaced; on → `dev` units are admitted too. `enabled_tiers` bounds which
    source families may contribute (default: the free Stage-1 tiers). Model-
    detected progressive disclosure *proposes* depth, but this plane *disposes*
    — it never crosses into dev content unless `allow_dev` says so.
    """

    allow_dev: bool = False
    enabled_tiers: frozenset[Tier] = field(default=frozenset({Tier.WIKI, Tier.GIT}))
    token_budget: int = 4000


@dataclass(frozen=True, slots=True)
class Context:
    """The output of `assemble()` — the bounded, cited feed for ONE avatar turn.

    `units` are in final presentation order (highest fused score first), each
    still carrying its provenance stamp. `token_estimate` is the deterministic
    packed-size estimate; `truncated` is True when the budget dropped units that
    would otherwise have qualified.
    """

    query: str
    units: tuple[Unit, ...]
    token_estimate: int
    truncated: bool

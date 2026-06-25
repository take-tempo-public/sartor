"""`SessionSource` — the S5-P1 interaction-memory tier (session buffer).

Stage 1 (Sprint 7.5). The avatar's memory of the *current* conversation: a growing
buffer of this session's turns, surfaced into retrieval through the same `Source`
interface as the corpus tiers, so it fuses identically without `assemble()` knowing
anything special about it. This is S5 **step P1 only** — durable cross-session recall,
importance/forgetting, and provenance tags (P2–P4) stay held pending the retention
policy (see `docs/dev/memory-architecture.md` §"S5 staircase").

It is the `InMemorySource` shape made grow-by-append: `observe(turn)` adds one stamped
turn; `search` ranks held turns by query-token overlap (delegated to the backing
`InMemorySource`). Every turn is stamped `tier=SESSION, audience=user` — a session turn
is the user's own, never dev-tier. Deterministic + stdlib-only — P1 Hardening boundary
(charter C-6).
"""

from __future__ import annotations

from collections.abc import Sequence

from recall.memory_source import InMemorySource
from recall.models import Audience, Scope, Tier, Unit


class SessionSource:
    """A `Source` over the current conversation's turns, growing as the avatar observes them.

    `refresh` is a no-op (no derived index); `search` delegates to a backing
    `InMemorySource` rebuilt on each `observe`.
    """

    def __init__(self, source_id: str = "session") -> None:
        self.source_id = source_id
        self._units: tuple[Unit, ...] = ()
        self._backing = InMemorySource(source_id, ())

    def observe(self, turn_text: str, citation: str | None = None) -> None:
        """Append one conversation turn as a stamped `Unit`.

        `citation` defaults to a stable `session:turn-<n>` (1-based). Blank text is
        ignored — a `Unit` must carry a quotable fact (its construction would raise).
        The backing `InMemorySource` takes an immutable tuple, so it is rebuilt with
        the appended unit; fine for the handful of turns a session holds.
        """
        if not turn_text.strip():
            return
        cite = citation or f"{self.source_id}:turn-{len(self._units) + 1}"
        unit = Unit(
            text=turn_text,
            tier=Tier.SESSION,
            source_id=self.source_id,
            citation=cite,
            audience=Audience.USER,
            sha="",
        )
        self._units = (*self._units, unit)
        self._backing = InMemorySource(self.source_id, self._units)

    def refresh(self, since_sha: str | None) -> None:
        """No-op — the session buffer has no derived index to rebuild."""
        return None

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Rank held turns by query-token overlap via the backing source.

        Scope is filtered centrally by `assemble()`.
        """
        return self._backing.search(query, scope)

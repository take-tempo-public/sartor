"""`InMemorySource` — the reference `Source` implementation.

Stage 0 skeleton (Sprint 7.4). A minimal, deterministic `Source` backed by an
in-memory list of pre-stamped `Unit`s. It exists for two reasons:

  1. **Worked example.** It is the smallest complete thing that satisfies the
     `Source` protocol — the template a 7.5 author copies when wiring the real
     S1 wiki / S2 `git grep` tiers.
  2. **The S5-P1 shape.** Interaction memory's first step (a session buffer of
     the current conversation's turns) is exactly an in-memory source that grows
     as the avatar observes turns — so this is the shape that slot will take.

It is **not** a real tier: matching is deterministic token overlap, not semantic
search, and there is no index to rebuild (so `refresh` is a no-op). Scope is NOT
applied here — the access/disclosure plane is applied centrally by `assemble()`,
which a source may rely on. Deterministic + stdlib-only — P1 Hardening boundary
(charter C-6).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import replace

from recall.models import Scope, Unit

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class InMemorySource:
    """A `Source` over a fixed set of `Unit`s, ranked by query-token overlap."""

    def __init__(self, source_id: str, units: Iterable[Unit]) -> None:
        self.source_id = source_id
        self._units: tuple[Unit, ...] = tuple(units)

    def refresh(self, since_sha: str | None) -> None:
        """No-op — an in-memory source has no derived index to rebuild."""
        return None

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Return held units ranked best-first by query-token overlap count.

        Uses a stable `citation` tiebreak so the order is deterministic.
        Scope is filtered centrally by `assemble()`.
        """
        wanted = _tokens(query)
        scored: list[Unit] = []
        for unit in self._units:
            overlap = len(wanted & _tokens(unit.text))
            if overlap:
                scored.append(replace(unit, score=float(overlap)))
        scored.sort(key=lambda u: (-u.score, u.citation))
        return scored

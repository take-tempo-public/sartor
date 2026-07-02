"""`recall/` — sartor's reusable Memory substrate (Stage 0 skeleton, Sprint 7.4).

The deterministic retrieval/assembly layer that *feeds* the doc-grounded avatar
(7.5) and the self-documenting wiki loop: hybrid retrieval over a common `Source`
interface, fused and budgeted into a cited `Context` for one small-LLM turn. The
substrate itself is the only non-LLM half — it knows nothing about résumés, and
by hard rule imports neither `app.py`, `analyzer.py`, the DB models, nor Flask
(`tests/test_recall_boundary.py` enforces this), so lifting it into a standalone
package later is packaging-only.

The whole public API is the four types + one entry point below; see
[`docs/dev/memory-architecture.md`](../docs/dev/memory-architecture.md) for the
tier model, the two cross-cutting planes, and the staged build. The real source
tiers (S1 `WikiSource`, S2 `GitGrepSource`, S5-P1 `SessionSource`) landed in 7.5
under `recall.sources`; the S3 `VectorSource` (static-embedding semantic search,
the one numpy-using tier) landed in 7.6.
"""

from __future__ import annotations

from recall.assemble import assemble
from recall.memory_source import InMemorySource
from recall.models import Audience, Context, Scope, Tier, Unit
from recall.source import Source
from recall.sources import Document, GitGrepSource, SessionSource, VectorSource, WikiSource

__all__ = [
    "Audience",
    "Context",
    "Document",
    "GitGrepSource",
    "InMemorySource",
    "Scope",
    "SessionSource",
    "Source",
    "Tier",
    "Unit",
    "VectorSource",
    "WikiSource",
    "assemble",
]

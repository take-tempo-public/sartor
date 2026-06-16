"""`recall/` — callback's reusable Memory substrate (Stage 0 skeleton, Sprint 7.4).

The deterministic retrieval/assembly layer that *feeds* the doc-grounded avatar
(7.5) and the self-documenting wiki loop: hybrid retrieval over a common `Source`
interface, fused and budgeted into a cited `Context` for one small-LLM turn. The
substrate itself is the only non-LLM half — it knows nothing about résumés, and
by hard rule imports neither `app.py`, `analyzer.py`, the DB models, nor Flask
(`tests/test_recall_boundary.py` enforces this), so lifting it into a standalone
package later is packaging-only.

The whole public API is the four types + one entry point below; see
[`docs/dev/memory-architecture.md`](../docs/dev/memory-architecture.md) for the
tier model, the two cross-cutting planes, and the staged build. Real source tiers
(S1 wiki, S2 `git grep`) land in 7.5; the S3 vector tier in 7.6.
"""

from __future__ import annotations

from recall.assemble import assemble
from recall.models import Audience, Context, Scope, Tier, Unit
from recall.source import Source

__all__ = [
    "Audience",
    "Context",
    "Scope",
    "Source",
    "Tier",
    "Unit",
    "assemble",
]

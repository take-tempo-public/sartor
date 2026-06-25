"""The `Source` interface — the common seam every retrieval tier plugs into.

Stage 0 skeleton (Sprint 7.4). One `Protocol` with two methods is the whole
contract a tier must satisfy to enter `assemble()`. The S1 wiki + S2 `git grep`
tiers (7.5), the S3 vector tier (7.6), and the S5 session buffer (Stage 1) all
implement this same interface, so they fuse identically without `assemble()`
knowing anything about them — "project specifics are injected via config, never
imported by `recall/`" (`docs/dev/memory-architecture.md` §"Reuse boundary").

`refresh(since_sha)` is the `$0`, no-LLM index-refresh hook that rides
`docs/wiki/.last_ingest_sha`: a tier rebuilds its index incrementally from the
diff since that sha (or cold when it is the empty sentinel). `recall/` *reads*
that checkpoint; it never *writes* it — advancing the checkpoint stays the wiki
ingest loop's job.

Deterministic + stdlib-only — P1 Hardening boundary (charter C-6).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from recall.models import Scope, Unit


@runtime_checkable
class Source(Protocol):
    """A retrieval tier with ranked provenance-stamped search and incremental refresh.

    `search` returns ranked, provenance-stamped `Unit`s for a query within a `Scope`;
    `refresh` brings the tier's index up to a sha.
    """

    source_id: str

    def refresh(self, since_sha: str | None) -> None:
        """Bring the tier's index up to date.

        `since_sha` is the last-ingested commit (from `.last_ingest_sha`), or
        `None` to signal a cold/full rebuild. Implementations do this with no
        LLM call and no network — the embedder, if any, is a static lookup.
        """
        ...

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Return ranked candidate `Unit`s for `query`, honoring `scope`.

        The returned units must already be sorted best-first within this source
        (fusion uses their rank). They must carry full provenance stamps; the
        access/disclosure filter is applied centrally by `assemble()`, so a
        source MAY pre-filter by `scope` but is not required to.
        """
        ...

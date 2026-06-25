"""`WikiSource` — the S1 committed-wiki retrieval tier.

Stage 1 (Sprint 7.5). Reads a markdown wiki (one concept per `pages/<slug>.md`) and
emits provenance-stamped `Unit`s the avatar can cite as `[[slug]]`. The wiki is
*answer-shaped synthesis* — the vocabulary-bridge tier (`docs/dev/memory-architecture.md`
§"Tiers") — so it is the primary tier for "how does X work" questions.

**Project-agnostic by construction:** the wiki directory, the provenance-sha file, and
the **audience resolver** are all injected — this module hardcodes no project path and
no project audience rule, so it stays inside the stdlib-only `recall/` substrate (the
`recall/sources/` no-hardcoded-roots guard in `tests/test_recall_boundary.py`). The
`**Audience:**`-tag convention lives in the injected resolver (the wiring layer), not
here.

Chunking is per-page: `search` returns at most one `Unit` per page — the best-matching
paragraph — so each `[[slug]]` citation is unique in the result set (the substrate's
RRF fusion dedups on `(source_id, citation)`). Deterministic + stdlib-only — P1
Hardening boundary (charter C-6).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from recall.memory_source import _tokens
from recall.models import Audience, Scope, Tier, Unit

# A blank line separates paragraphs — the retrieval-chunk granularity for wiki prose.
_PARA_SPLIT = re.compile(r"\n\s*\n")
# A 40-char lowercase-hex git sha; anything else in the sha file is a pre-ingest sentinel.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class _Page:
    """One indexed wiki page: its display citation, audience, sha, and paragraphs."""

    citation: str
    audience: Audience
    sha: str
    paragraphs: tuple[str, ...]


class WikiSource:
    """A `Source` over a markdown wiki's `pages/*.md`, ranked by query-token overlap."""

    source_id: str = "wiki"

    def __init__(
        self,
        wiki_dir: Path,
        ingest_sha_path: Path,
        audience_for_page: Callable[[str, str], Audience],
    ) -> None:
        """Bind the wiki dir and provenance-sha path, then build the initial page index."""
        self._wiki_dir = wiki_dir
        self._ingest_sha_path = ingest_sha_path
        self._audience_for_page = audience_for_page
        self._pages: tuple[_Page, ...] = ()
        self.refresh(None)

    def _read_sha(self) -> str:
        """The 40-char sha from the provenance file, or "" (the pre-ingest sentinel)."""
        try:
            text = self._ingest_sha_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
        return text if _SHA_RE.match(text) else ""

    def refresh(self, since_sha: str | None) -> None:
        """Rebuild the in-memory page index from `pages/*.md`.

        `since_sha` is accepted for `Source` conformance but ignored: a full rebuild
        over the handful of small pages is cheap, and incremental diff is the vector
        tier's concern (7.6). Infra files (`index`/`log`/`SCHEMA`/`overview`) live
        outside `pages/`, so the glob excludes them — they are wiki meta, not Units.
        """
        sha = self._read_sha()
        pages: list[_Page] = []
        for page in sorted((self._wiki_dir / "pages").glob("*.md")):
            raw = page.read_text(encoding="utf-8")
            paragraphs = tuple(p.strip() for p in _PARA_SPLIT.split(raw) if p.strip())
            if not paragraphs:
                continue
            pages.append(
                _Page(
                    citation=f"[[{page.stem}]]",
                    audience=self._audience_for_page(page.stem, raw),
                    sha=sha,
                    paragraphs=paragraphs,
                )
            )
        self._pages = tuple(pages)

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Return at most one `Unit` per page — the highest-token-overlap paragraph.

        Results are best-first by overlap (stable `citation` tiebreak). Pages with zero
        overlap are dropped. Scope is filtered centrally by `assemble()`.
        """
        wanted = _tokens(query)
        scored: list[Unit] = []
        for page in self._pages:
            best_para = ""
            best_overlap = 0
            for para in page.paragraphs:
                overlap = len(wanted & _tokens(para))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_para = para
            if best_overlap:
                scored.append(
                    Unit(
                        text=best_para,
                        tier=Tier.WIKI,
                        source_id=self.source_id,
                        citation=page.citation,
                        audience=page.audience,
                        sha=page.sha,
                        score=float(best_overlap),
                    )
                )
        scored.sort(key=lambda u: (-u.score, u.citation))
        return scored

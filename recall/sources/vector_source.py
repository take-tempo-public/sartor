"""`VectorSource` — the S3 static-embedding semantic retrieval tier.

Stage 2 (Sprint 7.6). Brute-force cosine over a rebuildable embedding sidecar — the
*vocabulary-bridge* tier (`docs/dev/memory-architecture.md` §"Tiers") that finds the
right code/doc **semantically**, when the question's words don't match the source's
words and the lexical S2 `git grep` tier misses. Added ahead of the formal v1.0.8
eval gate at owner direction (Stage-1 lexical retrieval tested too literal); see
`docs/dev/RELEASE_ARC.md` §Phase 4.7.

**Project-agnostic by construction.** The index location, the **embedder**, the
**audience resolver**, and (for builds) the **document provider** are all injected, so
this module hardcodes no project path, no audience rule, and — crucially — no embedding
model. The embedder is a plain `Callable[[Sequence[str]], ndarray]`, so the substrate
stays model-agnostic and extractable: callback wires `model2vec` in the project layer
(`blueprints/assistant.py` + `scripts/build_vector_index.py`), but `recall/` never
imports it. The one third-party import here is **`numpy`** (the brute-force cosine + the
`.npy` sidecar) — a *light lib*, the single sanctioned step past Stage-0's stdlib-only
floor (`docs/dev/memory-architecture.md` §"Reuse boundary"; the deliberate update to
`tests/test_recall_boundary.py::test_recall_imports_only_stdlib`).

**Build vs. search are split.** `refresh()` (re)builds the sidecar from the injected
document provider — an explicit, offline step run by `scripts/build_vector_index.py`,
never per request; it re-embeds only chunks whose *content* changed (content-hash reuse
→ the incremental, $0-on-unchanged rebuild the arc calls for, robust to a missing/stale
checkpoint). `search()` loads the prebuilt sidecar (process-cached so a per-request
source doesn't reload it), embeds the query, and returns the top-k cosine matches as
`path:line`-cited Units. No sidecar (the build step never ran) / an embedder error → `[]`,
so the assistant degrades gracefully to the other tiers. No LLM, no network at search
time — P1 Hardening boundary (charter C-6); the embedder is a static lookup.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from recall.models import Audience, Scope, Tier, Unit

logger = logging.getLogger(__name__)

# Sidecar filenames inside the injected index_dir (derived + rebuildable — kept out of
# db/resume.sqlite so it never inherits the corpus DB's migrations or PII).
_EMBEDDINGS_FILE = "embeddings.npy"
_CHUNKS_FILE = "chunks.json"

# An embedder maps a batch of texts to an (n, dim) float32 matrix whose ROWS ARE
# L2-NORMALIZED — so a plain dot product is cosine similarity. Injected, model-agnostic.
Embedder = Callable[[Sequence[str]], np.ndarray]


@dataclass(frozen=True, slots=True)
class Document:
    """One source document to index: its repo-relative path, full text, and sha."""

    path: str
    text: str
    sha: str


# A document provider yields the FULL current set of indexable documents (the wiring
# enumerates the tracked tree). `refresh()` re-embeds only chunks whose content changed,
# so handing it the whole set every build is still incremental ($0 on unchanged content).
DocumentProvider = Callable[[], Iterable[Document]]


@dataclass(frozen=True, slots=True)
class _Chunk:
    """One indexed chunk: its `path:line` citation, text, source path, sha, and a
    content hash (the reuse key that keeps rebuilds incremental)."""

    citation: str
    text: str
    path: str
    sha: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class _LoadedIndex:
    """A sidecar loaded into memory: parallel chunks + their embedding matrix."""

    chunks: tuple[_Chunk, ...]
    embeddings: np.ndarray  # (len(chunks), dim) float32, L2-normalized rows
    dim: int


# Process-wide cache so a per-request `VectorSource` doesn't reload the sidecar each turn.
# Keyed by (resolved index dir, embeddings-file mtime-ns) → invalidates on rebuild.
_INDEX_CACHE: dict[tuple[str, int], _LoadedIndex] = {}


def _hash_text(text: str) -> str:
    """A stable content hash for chunk reuse across incremental rebuilds."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class VectorSource:
    """A `Source` doing brute-force cosine retrieval over a static-embedding sidecar."""

    source_id: str = "vector"

    def __init__(
        self,
        index_dir: Path,
        embedder: Embedder,
        audience_for_path: Callable[[str], Audience],
        *,
        document_provider: DocumentProvider | None = None,
        top_k: int = 20,
        min_score: float = 0.0,
        chunk_lines: int = 40,
        chunk_overlap: int = 10,
    ) -> None:
        if chunk_lines <= 0:
            raise ValueError("chunk_lines must be positive")
        if not 0 <= chunk_overlap < chunk_lines:
            raise ValueError("chunk_overlap must be in [0, chunk_lines)")
        self._index_dir = index_dir
        self._embedder = embedder
        self._audience_for_path = audience_for_path
        self._document_provider = document_provider
        self._top_k = top_k
        self._min_score = min_score
        self._chunk_lines = chunk_lines
        self._chunk_overlap = chunk_overlap

    # --- build side (refresh) — run offline by scripts/build_vector_index.py ----------

    def refresh(self, since_sha: str | None) -> None:
        """(Re)build the embedding sidecar from the injected document provider.

        No provider (the per-request/runtime construction) → no-op: `search` reads
        whatever the build step last wrote. `since_sha` is accepted for `Source`
        conformance but unused — the rebuild is incremental by CONTENT (only chunks
        whose text changed are re-embedded), which subsumes a sha diff and survives a
        missing/stale checkpoint.
        """
        if self._document_provider is None:
            return
        chunks = self._chunk_documents(self._document_provider())
        reuse = self._existing_embeddings_by_hash()
        embeddings = self._embed_chunks(chunks, reuse)
        self._write_sidecar(chunks, embeddings)

    def _chunk_documents(self, documents: Iterable[Document]) -> list[_Chunk]:
        """Split each document into overlapping line-windows → citable `_Chunk`s.

        Line-windows are deliberately format-agnostic (code and prose alike) so the
        substrate stays generic. Each chunk cites `path:<1-based start line>`, unique
        within a file (so RRF's `(source_id, citation)` dedup never collapses two
        distinct chunks)."""
        step = self._chunk_lines - self._chunk_overlap
        chunks: list[_Chunk] = []
        for doc in documents:
            lines = doc.text.splitlines()
            if not lines:
                continue
            for start in range(0, len(lines), step):
                window = lines[start : start + self._chunk_lines]
                text = "\n".join(window).strip()
                if text:
                    chunks.append(
                        _Chunk(
                            citation=f"{doc.path}:{start + 1}",
                            text=text,
                            path=doc.path,
                            sha=doc.sha,
                            content_hash=_hash_text(text),
                        )
                    )
                if start + self._chunk_lines >= len(lines):
                    break  # this window reached the end; later starts only re-cover the tail
        return chunks

    def _existing_embeddings_by_hash(self) -> dict[str, np.ndarray]:
        """Map content_hash → embedding row from the current sidecar, for reuse.

        Lets a rebuild skip re-embedding unchanged chunks (the $0 incremental path). A
        missing/corrupt/inconsistent sidecar yields an empty map → full re-embed, never
        a crash."""
        loaded = self._load_index(use_cache=False)
        if loaded is None:
            return {}
        return {chunk.content_hash: loaded.embeddings[i] for i, chunk in enumerate(loaded.chunks)}

    def _embed_chunks(
        self, chunks: Sequence[_Chunk], reuse: dict[str, np.ndarray]
    ) -> np.ndarray:
        """Embed `chunks`, reusing cached rows for unchanged content. Returns an
        (len(chunks), dim) float32 matrix aligned to `chunks`."""
        if not chunks:
            return np.empty((0, 0), dtype=np.float32)
        missing = {c.content_hash: c.text for c in chunks if c.content_hash not in reuse}
        fresh: dict[str, np.ndarray] = {}
        if missing:
            hashes = list(missing)
            matrix = np.asarray(self._embedder([missing[h] for h in hashes]), dtype=np.float32)
            fresh = {h: row for h, row in zip(hashes, matrix, strict=True)}
        # A model/dimensionality change invalidates every reused row — re-embed all.
        if reuse and fresh:
            reuse_dim = int(next(iter(reuse.values())).shape[-1])
            fresh_dim = int(next(iter(fresh.values())).shape[-1])
            if reuse_dim != fresh_dim:
                logger.warning("vector index dim changed (%d→%d); full re-embed", reuse_dim, fresh_dim)
                return self._embed_chunks(chunks, {})
        rows = [reuse[c.content_hash] if c.content_hash in reuse else fresh[c.content_hash] for c in chunks]
        return np.asarray(rows, dtype=np.float32)

    def _write_sidecar(self, chunks: Sequence[_Chunk], embeddings: np.ndarray) -> None:
        """Persist the rebuilt index (embeddings + parallel chunk metadata) and drop
        the process cache so the next `search` reloads the fresh sidecar."""
        self._index_dir.mkdir(parents=True, exist_ok=True)
        np.save(self._embeddings_path, embeddings)
        payload = {
            "dim": int(embeddings.shape[1]) if embeddings.size else 0,
            "count": len(chunks),
            "chunks": [
                {
                    "citation": c.citation,
                    "text": c.text,
                    "path": c.path,
                    "sha": c.sha,
                    "content_hash": c.content_hash,
                }
                for c in chunks
            ],
        }
        self._chunks_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cache_key = self._cache_key()
        if cache_key is not None:
            _INDEX_CACHE.pop(cache_key, None)

    # --- search side — runs per request (cheap: load-once cache + one matmul) ---------

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Return up to `top_k` `path:line` Units most cosine-similar to `query`.

        Loads the prebuilt sidecar (process-cached). No sidecar / empty index / an
        embedder error → `[]` (a logged warning), so a vector miss never breaks a turn —
        the wiki/git/session tiers carry it. Scope is filtered centrally by `assemble()`.
        """
        if not query.strip():
            return []
        index = self._load_index()
        if index is None or not index.chunks:
            return []
        try:
            qvec = np.asarray(self._embedder([query]), dtype=np.float32)
        except Exception as exc:  # noqa: BLE001 - a degraded tier returns [], never breaks the turn
            logger.warning("vector query embedding failed: %s", exc)
            return []
        if qvec.ndim != 2 or qvec.shape[0] != 1 or qvec.shape[1] != index.dim:
            logger.warning("vector query embedding shape %s != index dim %d", qvec.shape, index.dim)
            return []
        scores = index.embeddings @ qvec[0]
        units: list[Unit] = []
        for i in np.argsort(-scores, kind="stable"):
            score = float(scores[int(i)])
            if score < self._min_score:
                break  # descending order → everything after is below the floor too
            chunk = index.chunks[int(i)]
            units.append(
                Unit(
                    text=chunk.text,
                    tier=Tier.VECTOR,
                    source_id=self.source_id,
                    citation=chunk.citation,
                    audience=self._audience_for_path(chunk.path),
                    sha=chunk.sha,
                    score=score,
                )
            )
            if len(units) >= self._top_k:
                break
        return units

    # --- sidecar I/O -----------------------------------------------------------------

    @staticmethod
    def index_exists(index_dir: Path) -> bool:
        """True when a built sidecar is present — the cheap activation check the wiring
        layer uses to decide whether the S3 tier is ready (model + index both present)."""
        return (index_dir / _EMBEDDINGS_FILE).exists()

    @property
    def _embeddings_path(self) -> Path:
        return self._index_dir / _EMBEDDINGS_FILE

    @property
    def _chunks_path(self) -> Path:
        return self._index_dir / _CHUNKS_FILE

    def _cache_key(self) -> tuple[str, int] | None:
        """`(resolved index dir, embeddings mtime-ns)` — None if the sidecar is absent."""
        try:
            mtime = self._embeddings_path.stat().st_mtime_ns
        except OSError:
            return None
        return (str(self._index_dir.resolve()), mtime)

    def _load_index(self, *, use_cache: bool = True) -> _LoadedIndex | None:
        """Load the sidecar (chunks + embeddings), or None if absent/corrupt/inconsistent.

        Process-cached by `(dir, mtime)` so per-request searches don't reload; the cache
        invalidates automatically when a rebuild rewrites `embeddings.npy`."""
        key = self._cache_key()
        if key is None:
            return None
        if use_cache and key in _INDEX_CACHE:
            return _INDEX_CACHE[key]
        try:
            raw = json.loads(self._chunks_path.read_text(encoding="utf-8"))
            embeddings = np.load(self._embeddings_path)
        except (OSError, ValueError) as exc:
            logger.warning("vector sidecar unreadable at %s: %s", self._index_dir, exc)
            return None
        chunks = tuple(
            _Chunk(
                citation=c["citation"],
                text=c["text"],
                path=c["path"],
                sha=c["sha"],
                content_hash=c["content_hash"],
            )
            for c in raw.get("chunks", [])
        )
        if len(chunks) != int(embeddings.shape[0]):
            logger.warning(
                "vector sidecar inconsistent (%d chunks, %d rows) at %s — ignoring",
                len(chunks), int(embeddings.shape[0]), self._index_dir,
            )
            return None
        dim = int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.size else 0
        loaded = _LoadedIndex(
            chunks=chunks,
            embeddings=np.ascontiguousarray(embeddings, dtype=np.float32),
            dim=dim,
        )
        if use_cache:
            _INDEX_CACHE[key] = loaded
        return loaded

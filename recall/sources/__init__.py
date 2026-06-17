"""`recall.sources` — the concrete retrieval tiers (Stage 1, Sprint 7.5).

The S1 wiki, S2 `git grep`, S5-P1 session-buffer, and S3 `VectorSource` `Source`
implementations that turn the Stage-0 substrate into a working assistant. Each is
**project-agnostic by construction** — roots, the audience resolver, and (for the
vector tier) the embedder are injected at construction, so no module here hardcodes a
project path, a project audience rule, or an embedding model. That keeps `recall/`
refactor-immune (`tests/test_recall_boundary.py`, including the `recall/sources/`
no-hardcoded-roots guard). The core substrate is stdlib-only; the S3 vector tier adds
the single sanctioned *light lib* — `numpy` (the brute-force cosine + the `.npy`
sidecar) — `model2vec` and every other project binding stay in the wiring layer
(`blueprints/assistant.py` + `scripts/build_vector_index.py`), never here.

See `docs/dev/memory-architecture.md` §"Tiers" for the family model and §"Reuse
boundary" for why the generic tiers ship inside `recall/`.
"""

from __future__ import annotations

from recall.sources.git_grep_source import GitGrepSource
from recall.sources.session_source import SessionSource
from recall.sources.vector_source import Document, VectorSource
from recall.sources.wiki_source import WikiSource

__all__ = [
    "Document",
    "GitGrepSource",
    "SessionSource",
    "VectorSource",
    "WikiSource",
]

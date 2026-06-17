"""Build / refresh the S3 vector-index sidecar for the doc-grounded assistant.

Stage 2 (Sprint 7.6). The one explicit, offline step that powers the semantic retrieval
tier: it downloads the static-embedding model ONCE into a gitignored local sidecar
(`db/vector_index/model/`), enumerates the repo's tracked code + docs, chunks + embeds
them, and writes the index (`db/vector_index/embeddings.npy` + `chunks.json`). After this
runs, the assistant's S3 tier activates automatically and retrieval is fully local — no
network at request time. Re-running is incremental: only chunks whose CONTENT changed are
re-embedded (content-hash reuse in `VectorSource`), so a refresh after a few edits is ~$0.

This is the project-wiring layer for the vector tier: `model2vec` lives HERE (+ the
blueprint), never in `recall/`, so the substrate stays embedder-agnostic + extractable.

Added ahead of the formal v1.0.8 eval gate at owner direction (Stage-1 lexical retrieval
tested too literal); see `docs/dev/RELEASE_ARC.md` §Phase 4.7.

Usage:
    python -m scripts.build_vector_index               # incremental (re-embed changed only)
    python -m scripts.build_vector_index --full        # cold rebuild (clear the sidecar first)
    python -m scripts.build_vector_index --model minishlab/potion-base-2M
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from recall import Audience, Document, VectorSource
from recall.sources.vector_source import Embedder

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "minishlab/potion-base-8M"
VECTOR_INDEX_DIR = REPO_ROOT / "db" / "vector_index"
VECTOR_MODEL_DIR = VECTOR_INDEX_DIR / "model"
# Tracked files to index: code + docs (the vocabulary-bridge corpus the lexical tiers miss).
_INDEX_SUFFIXES = (".py", ".md")


def _git(args: list[str]) -> str:
    """Run a local `git` subcommand from the repo root; exit on failure."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _tracked_files() -> list[str]:
    """Repo-relative paths of tracked code + docs (POSIX separators, straight from git)."""
    return [
        line.strip()
        for line in _git(["ls-files"]).splitlines()
        if line.strip().endswith(_INDEX_SUFFIXES)
    ]


def _documents(head_sha: str) -> Iterable[Document]:
    """Yield one `Document` per indexable tracked file (text decoded permissively)."""
    for rel in _tracked_files():
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("skip %s: %s", rel, exc)
            continue
        yield Document(path=rel, text=text, sha=head_sha)


def _load_model(model_id: str, model_dir: Path) -> Any:
    """Load the static model from the local sidecar dir, downloading it ONCE if absent.

    The download (HuggingFace) is the single deliberate network step — like
    `playwright install chromium`. Once saved locally, every build AND every runtime
    query loads from disk with no network.
    """
    from model2vec import StaticModel

    if model_dir.exists():
        logger.info("loading model from local sidecar %s", model_dir)
        return StaticModel.from_pretrained(str(model_dir))
    logger.info("downloading model %s (one-time, ~30MB) ...", model_id)
    model = StaticModel.from_pretrained(model_id)
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(model_dir))
    logger.info("saved model to %s -- runtime retrieval is now fully local", model_dir)
    return model


def _embedder_from(model: Any) -> Embedder:
    """Wrap a loaded model in an L2-normalizing batch embedder (so dot == cosine)."""

    def _embed(texts: Sequence[str]) -> np.ndarray:
        matrix = np.asarray(model.encode(list(texts)), dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # never divide an all-zero embedding by zero
        return matrix / norms

    return _embed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build/refresh the S3 vector index sidecar.")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help="model2vec model id (first build only; thereafter loaded from the local sidecar)",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="cold rebuild: clear the sidecar index and re-embed everything (model is kept)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.full:
        for name in ("embeddings.npy", "chunks.json"):
            (VECTOR_INDEX_DIR / name).unlink(missing_ok=True)
        logger.info("--full: cleared the existing sidecar index (model kept)")

    model = _load_model(args.model, VECTOR_MODEL_DIR)
    embedder = _embedder_from(model)
    head_sha = _git(["rev-parse", "HEAD"]).strip()

    source = VectorSource(
        VECTOR_INDEX_DIR,
        embedder,
        lambda _path: Audience.DEV,  # unused at build — search applies the live SCHEMA resolver
        document_provider=lambda: _documents(head_sha),
    )
    source.refresh(None)

    meta = json.loads((VECTOR_INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    logger.info(
        "vector index built: %d chunks (dim %d) at %s",
        meta["count"], meta["dim"], VECTOR_INDEX_DIR,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""`GitGrepSource` — the S2 lexical code/doc retrieval tier (`git grep`).

Stage 1 (Sprint 7.5). Exact-match lexical search over a git repository's **tracked**
files, emitting `Unit`s the avatar can cite as `path:line` — the native code-citation
target. Because `git grep` only sees tracked files, untracked/ignored content never
enters retrieval (a free provenance + privacy property: a local app's ignored user
data is structurally excluded).

**Project-agnostic by construction:** the repo root and the **audience resolver** are
injected, so this tier hardcodes no project path and no path→audience rule — it stays
inside the stdlib-only `recall/` substrate (the `recall/sources/` guard in
`tests/test_recall_boundary.py`). `git` is a *local* subprocess: no network egress, so
it is outside the PX-08 egress allowlist's concern. Deterministic + stdlib-only — P1
Hardening boundary (charter C-6).
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from recall.models import Audience, Scope, Tier, Unit

logger = logging.getLogger(__name__)

# Trivial query tokens to drop so a natural-language question greps on its salient term.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "how",
        "what",
        "why",
        "where",
        "when",
        "does",
        "do",
        "did",
        "i",
        "it",
        "this",
        "that",
        "with",
        "can",
        "my",
        "me",
        "you",
        "work",
        "works",
        "use",
        "used",
        "get",
        "got",
        "make",
        "made",
    }
)
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


class GitGrepSource:
    """A `Source` running one `git grep` per query over a repo's tracked files."""

    source_id: str = "git"

    def __init__(
        self,
        repo_root: Path,
        audience_for_path: Callable[[str], Audience],
        *,
        max_results: int = 20,
    ) -> None:
        self._repo_root = repo_root
        self._audience_for_path = audience_for_path
        self._max_results = max_results
        self._head_sha = ""

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess[str] | None:
        """Run a local `git` subcommand, returning None if git is absent/unrunnable.

        Fixed argv (list form, no shell) — the query reaches `git grep` as a `-e`
        operand, never an interpolated command — so injection is structurally
        impossible. `git` is resolved from PATH by design; both flagged by ruff's
        bandit rules and suppressed with justification.
        """
        try:
            return subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
                ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # tracked files may hold non-UTF-8 bytes; never crash on decode
                check=False,
            )
        except (OSError, ValueError) as exc:
            logger.warning("git invocation failed (%s): %s", args, exc)
            return None

    def refresh(self, since_sha: str | None) -> None:
        """Cache the repo HEAD sha for provenance stamping.

        There is no index to build — `git grep` reads the working tree live on each `search`.
        """
        result = self._run_git(["rev-parse", "HEAD"])
        if result is not None and result.returncode == 0:
            self._head_sha = result.stdout.strip()

    def _query_token(self, query: str) -> str:
        """Pick the most salient single token to grep on (longest non-stopword).

        Returns "" when the query carries no salient term — a stopword-only query
        (e.g. "how do i") would only flood lexical noise, so it greps nothing and
        the wiki/session tiers carry that turn instead.
        """
        salient = [t for t in _WORD_RE.findall(query) if t.lower() not in _STOPWORDS]
        return max(salient, key=len) if salient else ""

    def search(self, query: str, scope: Scope) -> Sequence[Unit]:
        """Return up to `max_results` `path:line` Units matching the query's salient token.

        Matching is case-insensitive. No match → `[]`; a git error → `[]` + a warning.
        """
        token = self._query_token(query)
        if not token:
            return []
        result = self._run_git(
            ["grep", "-n", "-i", f"--max-count={self._max_results}", "-e", token]
        )
        if result is None:
            return []
        if result.returncode == 1:  # git grep: 1 == no matches (not an error)
            return []
        if result.returncode != 0:
            logger.warning("git grep failed (rc=%d): %s", result.returncode, result.stderr.strip())
            return []
        return self._parse(result.stdout)

    def _parse(self, stdout: str) -> list[Unit]:
        """Parse `git grep -n` output (`path:line:text` per match) into Units."""
        units: list[Unit] = []
        for line in stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3 or not parts[1].isdigit():
                continue
            rel = parts[0].replace("\\", "/")
            units.append(
                Unit(
                    text=parts[2].strip() or "(matched blank line)",
                    tier=Tier.GIT,
                    source_id=self.source_id,
                    citation=f"{rel}:{parts[1]}",
                    audience=self._audience_for_path(rel),
                    sha=self._head_sha,
                    score=1.0,
                )
            )
            if len(units) >= self._max_results:
                break
        return units

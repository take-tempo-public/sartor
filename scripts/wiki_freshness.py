#!/usr/bin/env python3
"""Deterministic, stdlib-only wiki-freshness checker — the merge=publish gate item 5.

**Why this exists.** `docs/dev/documentation-architecture.md` ("Gates — merge = publish")
lists "wiki-freshness: the wiki is staler than threshold vs HEAD" as a merge-blocking check,
with an explicit "freshness nuance": CI *checks* `docs/wiki/.last_ingest_sha` vs HEAD and
warns/blocks past a threshold — it does **not** run the LLM `/wiki-ingest` (cost + manual by
`docs/wiki/SCHEMA.md`). This script is that check, deterministic and LLM-free (no
`anthropic` import, no network) — the same drift computation
`.claude-plugin/hooks/wiki-freshness-reminder.sh` already does for its non-blocking
post-commit nudge, reused here as the actual gate.

**Two thresholds, two jobs, deliberately distinct:**
  - `wiki-freshness-reminder.sh`'s `THRESHOLD=10` is a soft, non-blocking nudge fired after
    every `git commit` — cheap to trip often, meant to keep drift visible.
  - `BLOCK_THRESHOLD` here is a hard, merge-blocking gate — calibrated well above the nudge
    threshold (2026-07 efficiency review F-doc-08: a nudge threshold of 10 alarm-fatigued on
    every commit once real drift reached 119-434 files) but well below the drift level that
    actually went unblocked for ~7 weeks before the 2026-07-10 catch-up ingest
    (`docs/dev/RELEASE_CHECKLIST.md` Carry-forward ledger, "Wiki ingest refresh"). The gate
    exists to catch exactly that failure mode before it recurs, not to fire on ordinary
    multi-file branches.

**Where this is wired:**
  1. `tests/test_wiki_freshness_gate.py` re-runs this CLI as a pytest gate (rides the existing
     `pytest` run — no new CI job).
  2. `scripts/enforcement/guards/block_merge_to_main.py` imports `check()` directly and
     blocks a confirmed `git merge`/`git push` onto `main` when the wiki is stale past
     `BLOCK_THRESHOLD` — this is the actual "merge = publish" enforcement point, since a
     merge to `main` is the moment the site would republish a stale wiki. Unlike the
     `CLAUDE_CONFIRM_MERGE=1` escape hatch (which confirms the merge *target*), this check has
     no bypass token — the only way through is running `/wiki-self-update` (or `/wiki-ingest`)
     to genuinely advance the checkpoint, matching the `DOC-STATUS` gate's no-escape-hatch
     design.

**Silent-by-design cases** (mirrors `wiki-freshness-reminder.sh`): no `.last_ingest_sha` file,
or it holds the sentinel (no 40-char SHA) — "not yet ingested" is a known state, not staleness.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SHA_RE = re.compile(r"[0-9a-f]{40}")

# See module docstring "Two thresholds, two jobs" for the rationale. Comfortably above
# ordinary branch-scale drift (a single lane touches tens of files, not 75+) and comfortably
# below the historical 119-434 file drift this gate exists to catch before it recurs.
BLOCK_THRESHOLD = 75


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def last_ingest_sha(repo_root: Path = REPO_ROOT) -> str | None:
    """The 40-char checkpoint SHA in `docs/wiki/.last_ingest_sha`, or None (no real baseline
    yet — absent file or sentinel content)."""
    sha_file = repo_root / "docs" / "wiki" / ".last_ingest_sha"
    if not sha_file.is_file():
        return None
    try:
        text = sha_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = _SHA_RE.search(text)
    return m.group(0) if m else None


def drift_count(repo_root: Path = REPO_ROOT, sha: str | None = None) -> int | None:
    """Tracked files changed since the checkpoint, excluding `docs/wiki/` and `docs-site/`.

    `docs-site/` is the Fumadocs static export — an L3 *projection* of the wiki (like
    `docs/wiki/` itself), not a wiki source. Its churn (generated/build-adjacent files)
    must not count as wiki drift, so it is excluded alongside `docs/wiki/` (Carry-forward
    ledger #1, `docs-site/` over-count).

    None when there is no real baseline (see `last_ingest_sha`) or the git diff itself fails
    (not a git checkout, checkpoint SHA not reachable) — callers treat None as "can't judge,
    don't block", mirroring every other guard's fail-open-on-uncertainty convention in this
    enforcement core.
    """
    resolved_sha = sha if sha is not None else last_ingest_sha(repo_root)
    if resolved_sha is None:
        return None
    result = _run_git(["diff", "--name-only", resolved_sha, "HEAD"], cwd=repo_root)
    if result.returncode != 0:
        return None
    return sum(
        1
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("docs/wiki/") and not line.startswith("docs-site/")
    )


def check(repo_root: Path = REPO_ROOT) -> tuple[bool, int | None]:
    """`(ok, drift)`. `ok=True` means fresh enough (or no baseline yet — `drift=None`)."""
    drift = drift_count(repo_root)
    if drift is None:
        return True, None
    return drift < BLOCK_THRESHOLD, drift


def main() -> int:
    # Resolve against the invocation's own cwd, not this file's on-disk location — the same
    # "invocation cwd, never the process's ambient/install location" discipline
    # `block_merge_to_main.py` documents as "defect (ii)" for the parallel-worktree case (W-1):
    # this script must judge whichever repo/worktree it was actually run from.
    ok, drift = check(Path.cwd())
    if drift is None:
        print(
            "wiki_freshness: OK — no ingest baseline yet (docs/wiki/.last_ingest_sha is "
            "absent or the sentinel); nothing to measure drift against."
        )
        return 0
    if ok:
        print(
            f"wiki_freshness: OK — {drift} file(s) changed since the last ingest "
            f"(< {BLOCK_THRESHOLD}-file block threshold)."
        )
        return 0
    print(
        f"wiki_freshness: STALE — {drift} file(s) changed since the last ingest "
        f"(>= {BLOCK_THRESHOLD}-file block threshold). Run /wiki-self-update (bounded "
        "Haiku diff-pass) or /wiki-ingest (full cold pass) to advance "
        "docs/wiki/.last_ingest_sha before merging to main; /wiki-lint for the drift report."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""CI backstop for the enforcement core (`feat/portable-enforcement-core`).

Local guards are opt-in twice over: the Claude PreToolUse hooks only run
inside a Claude Code session, and the git-native hooks in `.githooks/`
require the one-time `git config core.hooksPath .githooks`
(`.githooks/README.md`) — nobody auto-activates either for a contributor.
This script is the server-side net: a repo-wide secrets scan over every
tracked file, independent of what a contributor's local hooks did or didn't
catch.

Wired into `.github/workflows/ci.yml`'s `quality` job. Per
`docs/governance/enforcement.md` ("CI is committed but latent until the git
remote activates"), this step is authored now and starts running for real
only once `main` is pushed to a GitHub remote (Sprint 8.7) — it is not a new
latency mechanism, just another step inside the already-latent workflow file.

Usage: python -m scripts.enforcement.ci_backstop
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.guards import block_secrets  # noqa: E402


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    """Scan every tracked file for secret-shaped content; exit 1 if any is found."""
    tracked = _tracked_files()
    offenders: list[str] = []
    for rel_path in tracked:
        path = _REPO_ROOT / rel_path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = block_secrets.decide("Write", {"content": text, "file_path": rel_path})
        if result.blocked:
            offenders.append(rel_path)

    if offenders:
        print("BLOCKED (ci_backstop): secret-shaped content committed in:", file=sys.stderr)
        for offender in offenders:
            print(f"  {offender}", file=sys.stderr)
        return 1

    print(f"ci_backstop: {len(tracked)} tracked files scanned, clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

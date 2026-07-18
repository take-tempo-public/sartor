"""Print the handoff pointer line — the one line of copyable chat text a
closing agent hands the user at the end of a branch (AGENTS.md "Branch
close-out checklist" step 5; docs/dev/AGENT_HANDOFF_TEMPLATE.md Close-out
checklist step 5; docs/dev/handoffs/README.md "The pointer").

Exists because that line's commit hash was, until now, hand-typed from
memory with nothing forcing or checking it — and was proven fabricated at
least once: a closing agent ran `git merge --no-ff` (whose stdout is a
diffstat, no commit hash) then typed a plausible-looking but entirely
made-up short hash into its closing chat summary. Full evidence:
docs/dev/diagnosis/handoff-pointer-verification.md.

Verifies the doc path is committed and reachable at the current HEAD (not
just present on disk) before printing anything — this also guards against
citing a pointer before its own merge has actually landed. Reads branch and
commit from git directly, never hardcoded.

Pair with `scripts/check_handoff_pointer.py`, which independently
re-verifies a pointer line against git state — run it immediately after
this script, on this script's own output, before pasting the line to the
user (enforce the generation method, then check its result).

Usage:
    python scripts/print_handoff_pointer.py docs/dev/handoffs/<branch-slug>.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def _git(*args: str) -> str | None:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["git", *args],  # noqa: S607 -- git on PATH, not attacker-controlled
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def build_pointer(doc: str) -> str:
    """Return the pointer line for `doc`, or raise ValueError with a clear reason."""
    top = _git("rev-parse", "--show-toplevel")
    if not top:
        raise ValueError("not inside a git repository (git rev-parse --show-toplevel failed)")
    repo_root = Path(top).resolve()

    doc_path = (repo_root / doc).resolve()
    if repo_root != doc_path and repo_root not in doc_path.parents:
        raise ValueError(f"doc is not inside the repo root ({repo_root}): {doc_path}")
    if not doc_path.is_file():
        raise ValueError(f"doc not found: {doc_path}")

    committed = _git("log", "-1", "--format=%H", "--", doc)
    if not committed:
        raise ValueError(
            f"{doc} is not committed at HEAD — commit the handoff before generating its pointer"
        )

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        raise ValueError("could not determine current branch (git rev-parse --abbrev-ref HEAD)")
    commit = _git("rev-parse", "--short", "HEAD")
    if not commit:
        raise ValueError("could not determine current commit (git rev-parse --short HEAD)")

    return f"Handoff: {doc} @ {branch} ({commit})"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the pointer line for the given handoff doc path; nonzero exit on any failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "doc",
        help="repo-relative path to the committed handoff, e.g. docs/dev/handoffs/<branch-slug>.md",
    )
    args = parser.parse_args(argv)

    try:
        print(build_pointer(args.doc))
    except ValueError as exc:
        print(f"print_handoff_pointer: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

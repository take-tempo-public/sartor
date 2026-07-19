"""Mechanically re-verify a handoff pointer line against real git state.

A handoff pointer (`scripts/print_handoff_pointer.py`'s output — see
docs/dev/handoffs/README.md "The pointer") is the one line of chat text that
crosses from a closing session into the next one. Generating it correctly
is not the same as it *arriving* correctly: an agent could still retype or
paraphrase it instead of pasting the exact stdout, the same way a hand-typed
hash was fabricated once before (docs/dev/diagnosis/handoff-pointer-verification.md).
"Enforce the method, then check the result" — this script is the check,
run on BOTH ends:

  - By the closing agent, immediately after `print_handoff_pointer.py`,
    against that script's own output, before pasting the line to the user.
  - By the next agent, as its literal first action on receiving a pointer,
    BEFORE reading the handoff file or trusting anything else about it.

Verifies, independently of how the line was produced: the commit exists;
the doc path is present in that commit's tree; the commit is reachable from
(an ancestor of, or equal to) the named branch. A failure here is a blocked
gate (charter C-9) — surface it and stop; never guess the "real" path,
branch, or hash and proceed as if the pointer had said that instead.

Usage:
    python scripts/check_handoff_pointer.py "Handoff: docs/dev/handoffs/<slug>.md @ main (abc1234)"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence

_POINTER_RE = re.compile(
    r"^Handoff:\s+(?P<path>\S+)\s+@\s+(?P<branch>\S+)\s+\((?P<commit>[0-9a-fA-F]{4,40})\)\s*$"
)


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


def _git_ok(*args: str) -> bool:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["git", *args],  # noqa: S607 -- git on PATH, not attacker-controlled
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return result.returncode == 0


def check_pointer(line: str) -> str:
    """Return a human-readable confirmation, or raise ValueError with the specific failure."""
    match = _POINTER_RE.match(line.strip())
    if not match:
        raise ValueError(
            "malformed pointer line — expected exactly "
            "'Handoff: <path> @ <branch> (<short-hash>)', got: "
            f"{line!r}"
        )
    path, branch, commit = match.group("path"), match.group("branch"), match.group("commit")

    if _git("cat-file", "-t", commit) != "commit":
        raise ValueError(
            f"commit not found: {commit!r} does not resolve to a commit object — "
            "this pointer may be fabricated or stale; do not trust it"
        )

    if not _git_ok("cat-file", "-e", f"{commit}:{path}"):
        raise ValueError(
            f"{path} is not present in commit {commit} — pointer does not match reality"
        )

    resolved_ref = None
    for candidate in (branch, f"origin/{branch}"):
        if _git("rev-parse", "--verify", "--quiet", candidate):
            resolved_ref = candidate
            break
    if resolved_ref is None:
        raise ValueError(
            f"branch ref not found: {branch!r} (checked local and origin/) — cannot verify ancestry"
        )

    if not _git_ok("merge-base", "--is-ancestor", commit, resolved_ref):
        raise ValueError(
            f"commit {commit} is not an ancestor of {branch!r} (resolved {resolved_ref!r}) — "
            "pointer may be stale or wrong"
        )

    tip = _git("rev-parse", "--short", resolved_ref) or "?"
    return f"check_handoff_pointer: OK — {path} @ {commit} is present and an ancestor of {branch} (resolved {resolved_ref}, tip {tip})"


def main(argv: Sequence[str] | None = None) -> int:
    """Check the given pointer line; nonzero exit on any failure, message on stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "line", help='the exact pointer line, e.g. "Handoff: <path> @ <branch> (<hash>)"'
    )
    args = parser.parse_args(argv)

    try:
        print(check_pointer(args.line))
    except ValueError as exc:
        print(f"check_handoff_pointer: BLOCKED — {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Every tracked file must have a decided line-ending policy.

Charter C-11 mechanism for the CRLF invocation-blocker class (third recorded
instance; see docs/dev/diagnosis/n1-args-guard-hardening.md). A tracked file
whose ``text``/``eol`` attributes fall through to ``* text=auto`` checks out
CRLF under ``core.autocrlf=true`` on Windows; any consumer that inlines the
file and rejects ``\\r`` -- the Workflow permission validator that blocked
Epic B run 1 twice -- then fails on that clone only. The committed blob is LF
either way, so CI structurally cannot see the defect; only a gate on the
attribute coverage itself can.

The check asks git itself (``git check-attr``), so it exercises the exact
matching that checkout uses -- no reimplementation of .gitattributes
semantics that could drift from git's own.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_every_tracked_file_has_a_decided_eol_policy() -> None:
    tracked = [
        f
        for f in subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout.split("\0")
        if f
    ]
    probe = subprocess.run(
        ["git", "check-attr", "--stdin", "-z", "text", "eol"],
        cwd=REPO,
        input="\0".join(tracked) + "\0",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    # -z output is a flat sequence of (path, attr, value) triples.
    fields = probe.stdout.split("\0")
    attrs: dict[str, dict[str, str]] = {}
    for i in range(0, len(fields) - 2, 3):
        path, attr, value = fields[i], fields[i + 1], fields[i + 2]
        attrs.setdefault(path, {})[attr] = value

    # Covered: an explicit eol, or text unset (the `binary` macro). Everything
    # else -- text=auto, text=set, or no text attribute at all -- follows
    # core.autocrlf on checkout, which is exactly the per-clone drift this
    # gate exists to forbid. Fail closed on the unknown.
    offenders = sorted(
        path
        for path, a in attrs.items()
        if a.get("eol", "unspecified") == "unspecified" and a.get("text") != "unset"
    )
    assert not offenders, (
        f"{len(offenders)} tracked file(s) have no decided line-ending policy and "
        "will check out per-clone (CRLF under core.autocrlf=true) -- the class "
        "that blocked Epic B run 1. Add an explicit `eol=lf` (or `binary`) rule "
        "to .gitattributes for each:\n  " + "\n  ".join(offenders)
    )

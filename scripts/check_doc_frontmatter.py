#!/usr/bin/env python3
"""Deterministic, stdlib-only Purpose/Audience/Authoritative-for header checker.

**Why this exists.** `docs/dev/documentation-architecture.md` ("Gates — merge = publish")
defines the L1 doc convention: every canonical front-door doc opens with a
``> **Purpose:** ... > **Audience:** ... > **Authoritative for:** ...`` blockquote header —
the source of the Fumadocs `title`/`description`/`audience`/`authoritativeFor` frontmatter
(see that doc's "Fumadocs sourcing" table). A page missing the header has no machine-readable
identity for the projection step and is invisible to the "which ICP front door" / "leak check"
logic. This script is the gate the merge=publish plan proposes ("frontmatter + audience").

**Scope: the publication registry.** `PUBLISHED_DOC_FILES` is derived from
`scripts/doc_registry.py` `PUBLISHED`, the single definition of what the site publishes
(`docs/dev/docs-ia-design.md` §5.1). It used to be a hand-listed set here that disagreed with
what the projector actually published (DX-05). The name is kept because
`check_doc_links.py` and `check_doc_single_home.py` import it.

**Audience token (design §5.2).** Every registered doc's `**Audience:**` value must start
with a backtick tier token (`` `user` ``, `` `dev` ``, or both), and the registry's tier for
that doc must be one of those tokens. This retires the projector's path-based fallback: the
tier is declared in the doc and in the registry, and the two must agree. A record path in the
registry is also a violation (records are never published, design §3.1).

**What counts as "has the header."** The three bolded field labels
(``**Purpose:**``, ``**Audience:**``, ``**Authoritative for:**``) must all appear within the
first `_HEADER_SCAN_CHARS` characters of the file — the opening blockquote block, per the
convention's own worked examples (`AGENTS.md`, the system model, etc.). Beyond the
audience token above, this is a presence check: it does not verify that Purpose or
Authoritative-for say anything true. That is an editorial judgment (D5's single-home gate is the sibling check for restated-vs-linked content).

Exit 0 clean; exit 1 with the list of registered files missing one or more header fields.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from doc_registry import PUBLISHED, PUBLISHED_PATHS, Entry, is_record

REPO_ROOT = Path(__file__).resolve().parent.parent

PUBLISHED_DOC_FILES: frozenset[str] = PUBLISHED_PATHS

# The three documented header fields (documentation-architecture.md "Fumadocs sourcing").
_REQUIRED_MARKERS = ("**Purpose:**", "**Audience:**", "**Authoritative for:**")

# Generous window: the header sits in the opening blockquote block, but that block can run
# to a dozen-plus lines on the denser docs (e.g. documentation-architecture.md's own header).
_HEADER_SCAN_CHARS = 4000

# `**Audience:**` followed by one or more backtick tier tokens, e.g. "`user` · `dev` — ...".
_AUDIENCE_RE = re.compile(r"\*\*Audience:\*\*\s*((?:`(?:user|dev)`\s*(?:[·,+/&]|and)?\s*)+)")
_TOKEN_RE = re.compile(r"`(user|dev)`")

# Teeth: the registry must name a real, non-trivial surface (guards against an emptied
# PUBLISHED_DOC_FILES silently making this gate vacuous).
_MIN_REGISTERED_FILES = 10


class MissingHeader:
    """One registered file missing one or more required header fields."""

    def __init__(self, path: str, missing: list[str]) -> None:
        self.path = path
        self.missing = missing

    def __str__(self) -> str:
        return f"{self.path} -> missing {', '.join(self.missing)}"


def check_frontmatter(entries: tuple[Entry, ...] = PUBLISHED) -> list[MissingHeader]:
    """Every registered doc must be a non-record, carry all three header fields near its top,
    and open its Audience with tier token(s) that include its registry tier."""
    violations: list[MissingHeader] = []
    for entry in sorted(entries, key=lambda e: e.path):
        if is_record(entry.path):
            violations.append(MissingHeader(entry.path, ["registered, but it is a record path"]))
            continue
        abs_path = REPO_ROOT / entry.path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.append(MissingHeader(entry.path, [f"unreadable: {exc}"]))
            continue
        head = text[:_HEADER_SCAN_CHARS]
        missing = [marker for marker in _REQUIRED_MARKERS if marker not in head]
        if "**Audience:**" in head:
            m = _AUDIENCE_RE.search(head)
            tokens = set(_TOKEN_RE.findall(m.group(1))) if m else set()
            if not tokens:
                missing.append("a leading `user`/`dev` Audience token")
            elif entry.tier not in tokens:
                missing.append(f"Audience token for its registry tier `{entry.tier}`")
        if missing:
            violations.append(MissingHeader(entry.path, missing))
    return violations


def main() -> int:
    if len(PUBLISHED_DOC_FILES) < _MIN_REGISTERED_FILES:
        print(
            f"check_doc_frontmatter: FAILED — PUBLISHED_DOC_FILES only names "
            f"{len(PUBLISHED_DOC_FILES)} file(s) (< {_MIN_REGISTERED_FILES}); the registry "
            "looks emptied/misconfigured, which would make this gate vacuously pass."
        )
        return 1

    violations = check_frontmatter()
    if not violations:
        print(
            f"check_doc_frontmatter: OK — {len(PUBLISHED_DOC_FILES)} published doc(s), "
            "all carry Purpose/Audience/Authoritative-for."
        )
        return 0

    print(f"check_doc_frontmatter: FAILED — {len(violations)} doc(s) missing header field(s):\n")
    for v in violations:
        print(str(v))
    return 1


if __name__ == "__main__":
    sys.exit(main())

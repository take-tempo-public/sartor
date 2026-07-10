#!/usr/bin/env python3
"""Deterministic, stdlib-only Purpose/Audience/Authoritative-for header checker.

**Why this exists.** `docs/dev/documentation-architecture.md` ("Gates — merge = publish")
defines the L1 doc convention: every canonical front-door doc opens with a
``> **Purpose:** ... > **Audience:** ... > **Authoritative for:** ...`` blockquote header —
the source of the Fumadocs `title`/`description`/`audience`/`authoritativeFor` frontmatter
(see that doc's "Fumadocs sourcing" table). A page missing the header has no machine-readable
identity for the projection step and is invisible to the "which ICP front door" / "leak check"
logic. This script is the gate the merge=publish plan proposes ("frontmatter + audience").

**Scope (`PUBLISHED_DOC_FILES` below) — deliberately an explicit registry, not
"every file under docs/".** `documentation-architecture.md`'s own L0/L1 diagram lists
`dev/**` as carrying the header too, but at HEAD only the repo-root canonical docs +
`docs/*.md` (top-level) + `docs/governance/*.md` narrative pages actually carry the full
triad — `docs/dev/**` is a heterogeneous mix of live design docs, frozen review artifacts,
and perf-benchmark logs, most of which predate (and were never meant to carry) this
convention, and `CHANGELOG.md` / `docs/wiki/log.md` / `docs/governance/compliance-log.md`
are append-only logs, not narrative front-door pages. Widening this registry to `docs/dev/**`
verbatim would false-positive on ~12 existing files with no content decision made here (see
the `ci/doc-merge-gate` lane report). This registry is the same idea as
`check_doc_links.py`'s `CITE_CHECK_FILES`/`CITE_CHECK_DIRS` — a reviewed, explicit surface
that widens by deliberate addition (a doc opting into the L1 convention), not by directory
sweep. **Widen when `scripts/project_docs_to_mdx.py` (the `feat/fumadocs-site` lane) lands
and defines the actual published-page set** — this registry should converge with that
script's scope rather than duplicate it as a second definition.

**What counts as "has the header."** The three bolded field labels
(``**Purpose:**``, ``**Audience:**``, ``**Authoritative for:**``) must all appear within the
first `_HEADER_SCAN_CHARS` characters of the file — the opening blockquote block, per the
convention's own worked examples (`AGENTS.md`, `docs/system-model.md`, etc.). This is a
presence check, not a grammar/content check: it does not verify the audience value is a
known token or that Purpose/Authoritative-for say anything true — that is an editorial
judgment (D5's single-home gate is the sibling check for restated-vs-linked content).

Exit 0 clean; exit 1 with the list of registered files missing one or more header fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The current L1 "published front door" surface — see module docstring for the scope
# rationale. Repo-root canonical docs:
_ROOT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "ACCESSIBILITY.md",
    "vision.md",
)
# docs/*.md top-level narrative pages (not docs/dev/**, docs/ux/**, docs/wiki/**):
_DOCS_TOP_LEVEL_FILES = (
    "docs/architecture.md",
    "docs/PRODUCT_SHAPE.md",
    "docs/system-model.md",
    "docs/install.md",
    "docs/walkthrough.md",
    "docs/walkthrough_example.md",
)
# docs/governance/*.md narrative pages (compliance-log.md is an append-only log, excluded):
_GOVERNANCE_FILES = (
    "docs/governance/charter.md",
    "docs/governance/enforcement.md",
    "docs/governance/metrics.md",
)

PUBLISHED_DOC_FILES: frozenset[str] = frozenset(
    _ROOT_FILES + _DOCS_TOP_LEVEL_FILES + _GOVERNANCE_FILES
)

# The three documented header fields (documentation-architecture.md "Fumadocs sourcing").
_REQUIRED_MARKERS = ("**Purpose:**", "**Audience:**", "**Authoritative for:**")

# Generous window: the header sits in the opening blockquote block, but that block can run
# to a dozen-plus lines on the denser docs (e.g. documentation-architecture.md's own header).
_HEADER_SCAN_CHARS = 4000

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


def check_frontmatter(files: frozenset[str] = PUBLISHED_DOC_FILES) -> list[MissingHeader]:
    """Every registered file must carry all three header fields near its top."""
    violations: list[MissingHeader] = []
    for rel_path in sorted(files):
        abs_path = REPO_ROOT / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.append(MissingHeader(rel_path, [f"unreadable: {exc}"]))
            continue
        head = text[:_HEADER_SCAN_CHARS]
        missing = [marker for marker in _REQUIRED_MARKERS if marker not in head]
        if missing:
            violations.append(MissingHeader(rel_path, missing))
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

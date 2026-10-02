#!/usr/bin/env python3
"""The publication registry: the single definition of which docs the site publishes.

**Why this exists.** Before Epic D, "published" had two definitions that disagreed. The
projector (`scripts/project_docs_to_mdx.py`) published any tracked `.md` with a full
Purpose/Audience/Authoritative-for header, which put handoff briefs, a diagnosis dossier,
reviews and perf records on the site. Separately, `check_doc_frontmatter.PUBLISHED_DOC_FILES`
hand-listed 16 files (DX-05 in `docs/dev/reviews/2026-09-docs-ia/20-dx.md`). This module
replaces both (`docs/dev/docs-ia-design.md` §5.1, pulled into D2 by owner decision O-4):

- `PUBLISHED` is the ordered list of every published doc with its tier. Its order is the
  site nav order within each tier. The projector publishes only these;
  `check_doc_frontmatter` checks only these; `meta.json` is generated from them.
- `RECORD_PREFIXES` is the single home of the record-path classes (design §3.1). Records are
  frozen history: they are never published, never link-rewritten by `scripts/docs_move.py`,
  and their links to moved docs resolve through `docs/dev/moved-paths.json` in
  `scripts/check_doc_links.py`.

Data only, stdlib only, no I/O at import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["user", "dev"]

# Record classes (design §3.1). A path is a record if it starts with any of these.
# `CHANGELOG*.md` is matched by `is_record` separately (a basename pattern, not a prefix).
RECORD_PREFIXES: tuple[str, ...] = (
    "docs/dev/handoffs/",
    "docs/dev/ledger/",
    "docs/dev/diagnosis/",
    "docs/dev/blast-radius/",
    "docs/dev/reviews/",
    "docs/dev/perf/",
    "docs/dev/excellence-walk/",
    "docs/dev/flake-rates/",
    "docs/dev/work/",
    "docs/dev/archive/",
    "docs/ux/onboarding_audit_",
    "docs/wiki/log.md",
)

# Files under a record prefix that are live docs, each with the owner's reason.
LIVE_EXCEPTIONS: frozenset[str] = frozenset(
    {
        # Owner, 2026-09-28: the project's performance history is kept and published as
        # living project history. It sits beside the frozen perf run records it summarizes.
        "docs/dev/perf/PERFORMANCE_HISTORY.md",
    }
)


def is_record(path: str) -> bool:
    """True when `path` (repo-relative POSIX) is a frozen record (design §3.1)."""
    if path in LIVE_EXCEPTIONS:
        return False
    if path.startswith("CHANGELOG") and "/" not in path and path.endswith(".md"):
        return True
    return path.startswith(RECORD_PREFIXES)


@dataclass(frozen=True)
class Entry:
    """One published doc: its repo-relative path and the site tier it appears under."""

    path: str
    tier: Tier


# Site nav order: "Using Sartor" (user tier) first, then "Building on Sartor" (dev tier).
# README.md is the site home (`index`) and is always first.
PUBLISHED: tuple[Entry, ...] = (
    # --- user tier: the user ladder (design §4) ---
    Entry("README.md", "user"),
    Entry("docs/user/README.md", "user"),
    Entry("vision.md", "user"),
    Entry("docs/user/install.md", "user"),
    Entry("docs/user/walkthrough.md", "user"),
    Entry("docs/user/walkthrough-example.md", "user"),
    Entry("docs/user/iterating.md", "user"),
    Entry("docs/user/coaching.md", "user"),
    Entry("docs/user/templates.md", "user"),
    Entry("ACCESSIBILITY.md", "user"),
    # --- dev tier: the dev ladder (design §4), then reference ---
    Entry("docs/dev/README.md", "dev"),
    Entry("CONTRIBUTING.md", "dev"),
    Entry("docs/dev/architecture.md", "dev"),
    Entry("docs/dev/system-model.md", "dev"),
    Entry("docs/dev/PRODUCT_SHAPE.md", "dev"),
    Entry("AGENTS.md", "dev"),
    Entry("CLAUDE.md", "dev"),
    Entry("SECURITY.md", "dev"),
    Entry("docs/governance/charter.md", "dev"),
    Entry("docs/governance/enforcement.md", "dev"),
    Entry("docs/governance/metrics.md", "dev"),
    Entry("docs/dev/doc-style-guide.md", "dev"),
    Entry("docs/dev/documentation-architecture.md", "dev"),
    Entry("docs/dev/docs-ia-design.md", "dev"),
    Entry("docs/dev/docs-site-deploy.md", "dev"),
    Entry("docs/dev/releasing.md", "dev"),
    Entry("docs/dev/maintainer-lane.md", "dev"),
    Entry("docs/dev/diagnostics.md", "dev"),
    Entry("docs/dev/tooling.md", "dev"),
    Entry("docs/dev/bundled-templates.md", "dev"),
    Entry("docs/dev/screenshot-capture.md", "dev"),
    Entry("docs/dev/EXTRACTION.md", "dev"),
    Entry("docs/dev/keep-ledger.md", "dev"),
    Entry("docs/dev/memory-architecture.md", "dev"),
    Entry("docs/dev/nursery.md", "dev"),
    Entry("docs/dev/RELEASE_CHECKLIST.md", "dev"),
    Entry("docs/dev/perf/PERFORMANCE_HISTORY.md", "dev"),
    Entry("docs/dev/epic-a-chain-design-corrections.md", "dev"),
    Entry("docs/dev/handoff-integrity-design.md", "dev"),
)

PUBLISHED_PATHS: frozenset[str] = frozenset(e.path for e in PUBLISHED)

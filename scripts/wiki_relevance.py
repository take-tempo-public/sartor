#!/usr/bin/env python3
"""Wiki-relevance classification — the single source of truth for "does this changed
path count toward wiki-staleness drift."

**Why this exists.** `scripts/wiki_freshness.py`'s drift counter and
`hooks/wiki-freshness-reminder.sh`'s post-commit nudge both used to count every
changed file except `docs/wiki/` and `docs-site/` themselves. That silently counted
process/provenance churn — `docs/dev/handoffs/`, `docs/dev/ledger/`,
`docs/dev/work/items/`, `docs/dev/diagnosis/`, `tests/`, `ui_pages/` — none of which a
wiki page ever cites, as real drift. This project's own `docs/wiki/log.md` records the
same false-positive shape tripping the 75-file merge-blocking gate twice before
(`chore/wiki-refresh-v109` 2026-07-30, `feat/context-structure-review-skill`
2026-07-24), each time patched with a one-off manual triage instead of a structural
fix — guaranteeing a third recurrence, which is what surfaced this module
(`docs/dev/diagnosis/wiki-freshness-relevance-classification.md`).

**Design, mirrored from `tests/test_egress_allowlist.py`'s `SANCTIONED_EGRESS_FILES`**
— the only existing precedent in this repo for a maintained classification list that
cannot silently rot: a directory or file matching here is EXPLICITLY accounted for,
and `tests/test_wiki_relevance_classification.py` fails the moment a new top-level
entry appears that isn't (forcing a conscious decision) or a listed entry no longer
exists (forcing cleanup) — never a silent default in either direction for anything
this module doesn't already know about.

**Classification is not exhaustive to the individual-file level everywhere** — most of
the repo falls under a directory-prefix rule. Two directories are known MIXED (mostly
irrelevant, but containing specific files a wiki page genuinely cites): `scripts/`
(dev tooling, but `generate_openapi_spec.py` / `route_security_lint.py` /
`perf_baseline.py` / `export_corpus_seed.py` are cited) and `docs/dev/perf/` (one-off
performance investigations, but `PERFORMANCE_HISTORY.md` is cited). Everything not
explicitly classified as irrelevant or mixed defaults to relevant — production code
and canonical docs are the common case, not the exception.
"""

from __future__ import annotations

# Directories (repo-relative POSIX, trailing slash) wholesale wiki-irrelevant: never
# a wiki source, by construction — process/provenance/test-infrastructure directories
# that generate many files per branch.
IRRELEVANT_PREFIXES = frozenset(
    {
        "docs/wiki/",  # the artifact itself
        "docs-site/",  # the Fumadocs projection of the wiki
        "docs/dev/handoffs/",  # session handoffs — process record
        "docs/dev/ledger/",  # provenance ledger — process record
        "docs/dev/diagnosis/",  # evidence dossiers — process record
        "docs/dev/blast-radius/",  # C-10 consumer enumerations — process record
        "docs/dev/reviews/",  # review archive — provenance model, never ingested
        "docs/dev/prov/",  # provenance spec — process meta, not wiki-cited
        "docs/dev/work/items/",  # per-item filings — BOARD.md is generated FROM these
        "docs/dev/flake-rates/",  # CI flake-rate measurement store — process/telemetry
        # record (per-run JSONL shards), never a wiki source; see
        # docs/dev/blast-radius/flake-rate-measurement.md
        "docs/screenshots/",  # image assets, not text a wiki page cites
        "docs/ux/",  # one-off UX audit / capture-process docs, not wiki-cited
        "tests/",  # the wiki documents production modules, never test files
        "ui_pages/",  # UX test page-object infrastructure
        ".claude/",  # Claude Code local settings
        ".claude-plugin/",  # the sartor plugin manifest
        ".githooks/",
        ".github/",
        "hooks/",  # PreToolUse/PostToolUse guard scripts (agent tooling, not product)
        "commands/",  # plugin slash-command definitions
        "agents/",  # plugin subagent definitions
        "skills/",  # plugin skill definitions
        "configs/",  # gitignored per-user data (near-empty in git, .gitkeep only)
        "resumes/",  # gitignored per-user data
        "output/",  # gitignored per-user data
        "logs/",  # gitignored telemetry log
    }
)

# Specific files (repo-relative POSIX) wholesale irrelevant despite not falling under
# an IRRELEVANT_PREFIXES directory.
IRRELEVANT_FILES = frozenset(
    {
        "docs/dev/work/BOARD.md",  # generated FROM docs/dev/work/items/ — not itself a source
        "CHANGELOG.md",  # release notes, not a wiki source
        "CHANGELOG-archive.md",
        "docs/bundled_templates_LICENSE.md",
    }
)

# Directories that are MOSTLY irrelevant (dev tooling / one-off investigation docs)
# but contain specific files a wiki page genuinely cites — default irrelevant, the
# RELEVANT_OVERRIDES entries below are the exception.
MIXED_PREFIXES = frozenset({"scripts/", "docs/dev/perf/"})

# Files inside a MIXED_PREFIXES directory that DO count toward drift.
RELEVANT_OVERRIDES = frozenset(
    {
        "scripts/generate_openapi_spec.py",
        "scripts/enforcement/guards/route_security_lint.py",
        "scripts/perf_baseline.py",
        "scripts/export_corpus_seed.py",
        "docs/dev/perf/PERFORMANCE_HISTORY.md",
    }
)

# Top-level entries (repo root, `docs/`'s immediate children, `docs/dev/`'s immediate
# children) this module has consciously classified as RELEVANT — i.e. not itself an
# irrelevant/mixed prefix, but explicitly acknowledged rather than an unreviewed gap.
# `test_wiki_relevance_classification.py` asserts every CURRENT top-level entry at
# these three levels is in this set OR accounted for by one of the frozensets above —
# never silently defaulted without a decision having been made.
KNOWN_RELEVANT_TOP_LEVEL = frozenset(
    {
        # repo root — production code
        "app.py",
        "analyzer.py",
        "config.py",
        "corpus_to_json_resume.py",
        "demo_fixtures.py",
        "docx_to_persona_html.py",
        "generator.py",
        "hardening.py",
        "json_resume.py",
        "parser.py",
        "pdf_render.py",
        "scraper.py",
        "db",
        "dashboard",
        "recall",
        "blueprints",
        "onboarding",
        "web_infra",
        "static",
        "templates",
        "personas",
        "evals",
        # repo root — canonical docs / project-identity files
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "vision.md",
        "alembic.ini",
        "pyproject.toml",
        "llms.txt",
        # repo root — config/meta files, low-volume, safe to count by default
        "ACCESSIBILITY.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
        "LICENSES",
        "REUSE.toml",
        ".dockerignore",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".git-blame-ignore-revs",
        "Dockerfile",
        "promptfooconfig.yaml",
        # container directories (their own children are classified individually below/
        # elsewhere; the container itself still needs an explicit acknowledgment so the
        # audit's top-level enumeration has no unreviewed gap)
        "docs",
        "docs/dev",
        "docs/dev/work",  # SCHEMA.md defaults relevant; items/ and BOARD.md carved out separately
        # docs/ immediate children
        "docs/PRODUCT_SHAPE.md",
        "docs/architecture.md",
        "docs/install.md",
        "docs/system-model.md",
        "docs/template_authoring.md",
        "docs/walkthrough.md",
        "docs/walkthrough_example.md",
        "docs/governance",
        # docs/dev/ immediate children (subdirectories not already in the prefix sets,
        # and every loose top-level docs/dev/*.md file)
        "docs/dev/excellence-walk",  # the wiki's excellence-walk pages are built FROM this
        "docs/dev/AGENT_FAILURE_PATTERNS.md",
        "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
        "docs/dev/COMPOSE_REWRITE_DIAL.md",
        "docs/dev/EXTRACTION.md",
        "docs/dev/GROUNDING_METRIC.md",
        "docs/dev/ORCHESTRATION_PLAYBOOK.md",
        "docs/dev/RELEASE_ARC.md",
        "docs/dev/RELEASE_CHECKLIST.md",
        "docs/dev/V1_0_5_VERIFICATION.md",
        "docs/dev/app-blueprints-design.md",
        "docs/dev/avatar-citation-format-guidance.md",
        "docs/dev/avatar-voice-tone-guidance.md",
        "docs/dev/decisions.md",
        "docs/dev/dependency-triage-pre-v1.1.0.md",
        "docs/dev/doc-style-guide.md",
        "docs/dev/docs-site-deploy.md",
        "docs/dev/documentation-architecture.md",
        "docs/dev/generation-experience-rearchitecture.md",
        "docs/dev/governance-extraction-design.md",
        "docs/dev/handoff-integrity-design.md",
        "docs/dev/keep-ledger.md",
        "docs/dev/kit-adoption-design.md",
        "docs/dev/memory-architecture.md",
        "docs/dev/nursery.md",
        "docs/dev/pagedjs-preview-spike.md",
        "docs/dev/self-documenting-loop-design.md",
        "docs/dev/window-8.5-findings.md",
        "docs/dev/window-8.5-walkthrough.md",
    }
)


def is_wiki_relevant(path: str) -> bool:
    """True if a repo-relative POSIX path should count toward wiki-staleness drift."""
    if path in IRRELEVANT_FILES:
        return False
    if path in RELEVANT_OVERRIDES:
        return True
    if any(path.startswith(prefix) for prefix in IRRELEVANT_PREFIXES):
        return False
    # Mixed prefix and not in RELEVANT_OVERRIDES (checked above) -> irrelevant;
    # otherwise default: relevant (production code, canonical docs, etc.).
    return not any(path.startswith(prefix) for prefix in MIXED_PREFIXES)


def filter_relevant(paths: list[str]) -> list[str]:
    """The subset of `paths` that count toward wiki-staleness drift."""
    return [p for p in paths if is_wiki_relevant(p)]

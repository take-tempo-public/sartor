"""Invariants of the publication registry, `scripts/doc_registry.py`.

WHY: the registry is the single definition of what the docs site publishes
(`docs/dev/docs-ia-design.md` §5.1). The projector, `check_doc_frontmatter.py`, the links
gate's cite check and the single-home gate all read it, so a bad entry breaks all of them at
once. These tests pin the rules those consumers assume: a record path can't be registered,
every entry exists, tiers are valid, and slugs don't collide.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import doc_registry as reg  # noqa: E402 - path insert must precede this import
import project_docs_to_mdx as pdm  # noqa: E402


def test_readme_is_first_and_user_tier() -> None:
    assert reg.PUBLISHED[0] == reg.Entry("README.md", "user")


def test_no_duplicate_entries() -> None:
    paths = [e.path for e in reg.PUBLISHED]
    assert len(paths) == len(set(paths))


def test_every_entry_exists() -> None:
    missing = [e.path for e in reg.PUBLISHED if not (REPO_ROOT / e.path).is_file()]
    assert not missing, f"registered docs missing on disk: {missing}"


def test_tiers_are_valid_and_user_tier_comes_first() -> None:
    tiers = [e.tier for e in reg.PUBLISHED]
    assert set(tiers) == {"user", "dev"}
    first_dev = tiers.index("dev")
    assert all(t == "dev" for t in tiers[first_dev:]), "nav order must be user tier, then dev"


def test_no_record_path_is_registered() -> None:
    records = [e.path for e in reg.PUBLISHED if reg.is_record(e.path)]
    assert not records, f"records are never published (design §3.1): {records}"


def test_slugs_are_unique() -> None:
    slugs = [pdm.make_slug(e.path) for e in reg.PUBLISHED]
    assert len(slugs) == len(set(slugs))


def test_is_record_classes() -> None:
    assert reg.is_record("docs/dev/handoffs/docs-ia-design.md")
    assert reg.is_record("docs/dev/archive/kit-adoption-design.md")
    assert reg.is_record("docs/wiki/log.md")
    assert reg.is_record("docs/ux/onboarding_audit_2026-05-25.md")
    assert reg.is_record("CHANGELOG.md")
    assert reg.is_record("CHANGELOG-archive.md")
    assert not reg.is_record("docs/wiki/index.md")
    assert not reg.is_record("docs/dev/RELEASE_ARC.md")
    assert not reg.is_record("docs/dev/CHANGELOG.md")


def test_live_exceptions_are_under_a_record_prefix() -> None:
    # An exception that isn't under a record prefix is dead weight — and a sign the
    # prefix list drifted.
    for path in reg.LIVE_EXCEPTIONS:
        assert path.startswith(reg.RECORD_PREFIXES), path
        assert not reg.is_record(path)

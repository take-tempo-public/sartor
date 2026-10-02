"""Help bubbles link to real doc pages — the in-app -> docs-site link check (D4).

WHY: every help bubble in the wizard (`_HELP_REGISTRY`, `static/app.js`) and the diagnostics
console (`_DASH_HELP`, `dashboard/templates/dashboard.html`) carries a `learnMore` target: a
docs-site page slug, optionally `#anchor`. `static/help-modal.js` turns it into a link to
the published site. Nothing in the browser can tell that a slug or anchor no longer exists,
so the link would just 404 or land at the top of the page. This test resolves each one
against the publication registry (`scripts/doc_registry.py`), the projector's slug rule
(`project_docs_to_mdx.make_slug`) and the target doc's headings, and fails the gate instead.
It also requires every bubble to carry a link, so a new bubble can't ship without one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_links as cdl  # noqa: E402 - path insert must precede this import
import project_docs_to_mdx as pdm  # noqa: E402
from doc_registry import PUBLISHED  # noqa: E402

REGISTRIES = {
    "static/app.js": ("_HELP_REGISTRY = {", "\n};"),
    "dashboard/templates/dashboard.html": ("var _DASH_HELP = {", "\n  };"),
}
_ENTRY_RE = re.compile(r"^\s+(\w+): \{\n\s+title:", re.M)
_LEARN_RE = re.compile(r"^\s+(\w+): \{\n\s+title: [^\n]*\n\s+learnMore: '([^']+)',", re.M)
SLUG_TO_PATH = {pdm.make_slug(e.path): e.path for e in PUBLISHED}
DOCS_BASE = "https://sartor-docs.taketempo.com/docs/"


def _registry_text(path: str) -> str:
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    start_marker, end_marker = REGISTRIES[path]
    start = text.index(start_marker)
    return text[start : text.index(end_marker, start)]


def _targets() -> list[tuple[str, str, str]]:
    return [
        (path, key, target)
        for path in REGISTRIES
        for key, target in _LEARN_RE.findall(_registry_text(path))
    ]


@pytest.mark.parametrize("path", REGISTRIES)
def test_every_bubble_has_a_learn_more_link(path: str) -> None:
    text = _registry_text(path)
    entries = set(_ENTRY_RE.findall(text))
    linked = {key for key, _ in _LEARN_RE.findall(text)}
    assert entries, f"no help entries parsed from {path}"
    assert entries == linked, f"{path}: bubbles without learnMore: {sorted(entries - linked)}"


@pytest.mark.parametrize(("path", "key", "target"), _targets(), ids=lambda v: str(v))
def test_learn_more_resolves_to_a_published_heading(path: str, key: str, target: str) -> None:
    slug, _, anchor = target.partition("#")
    assert slug in SLUG_TO_PATH, f"{path}:{key} -> {slug!r} is not a published page"
    if anchor:
        doc = (REPO_ROOT / SLUG_TO_PATH[slug]).read_text(encoding="utf-8").splitlines()
        assert anchor in cdl.slugs_for(doc), (
            f"{path}:{key} -> #{anchor} not in {SLUG_TO_PATH[slug]}"
        )


def test_docs_base_is_the_documented_site() -> None:
    """One base URL, in the shared opener, matching the deploy doc's published host."""
    js = (REPO_ROOT / "static" / "help-modal.js").read_text(encoding="utf-8")
    assert f"var DOCS_BASE = '{DOCS_BASE}';" in js
    deploy = (REPO_ROOT / "docs" / "dev" / "docs-site-deploy.md").read_text(encoding="utf-8")
    assert DOCS_BASE.split("/docs/")[0].removeprefix("https://") in deploy

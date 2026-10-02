"""The docs-site checks added in D4: the projection stamp (item 126) and the diagram count.

WHY: `scripts/check_docs_site_mermaid.py` needs a built site and a browser, so the gate
can't run it (CI's docs-deploy job does). What the gate *can* pin is the pure logic both
checks rest on:
- every projected page carries the commit it came from;
- the freshness verdict reads that stamp correctly;
- the expected diagram count per page matches the source docs.
A wrong expected count would make the browser check pass while diagrams are missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_docs_projection_fresh as fresh  # noqa: E402 - path insert must precede this import
import check_docs_site_mermaid as mer  # noqa: E402
import project_docs_to_mdx as pdm  # noqa: E402
from doc_registry import PUBLISHED  # noqa: E402

HEAD = "a" * 40


# --- the stamp ------------------------------------------------------------------------


def test_frontmatter_carries_source_commit_when_given() -> None:
    fm = pdm.build_frontmatter("T", "d", "dev", "x", source_commit=HEAD)
    assert f'sourceCommit: "{HEAD}"' in fm.splitlines()
    assert "sourceCommit" not in pdm.build_frontmatter("T", "d", "dev", "x")


def test_every_projected_page_is_stamped() -> None:
    pages = pdm.collect_pages(commit=HEAD)
    assert len(pages) == len(PUBLISHED)
    for page in pages:
        assert f'sourceCommit: "{HEAD}"' in page.body.split("\n---\n", 1)[0], page.slug
        assert f"Projected from commit {HEAD}." in page.body, page.slug


def test_source_commit_reads_head() -> None:
    stamp = pdm.source_commit()
    assert re.fullmatch(r"[0-9a-f]{40}(\+uncommitted)?", stamp), stamp


# --- the freshness verdict --------------------------------------------------------------


def test_verdict_fresh_only_when_every_page_is_from_head() -> None:
    assert fresh.verdict({"a.mdx": HEAD, "b.mdx": HEAD}, HEAD)[0]
    assert not fresh.verdict({}, HEAD)[0]
    assert not fresh.verdict({"a.mdx": HEAD, "b.mdx": None}, HEAD)[0]
    assert not fresh.verdict({"a.mdx": HEAD, "b.mdx": "b" * 40}, HEAD)[0]
    assert not fresh.verdict({"a.mdx": "b" * 40}, HEAD)[0]
    stale, why = fresh.verdict({"a.mdx": HEAD + "+uncommitted"}, HEAD)
    assert not stale and "uncommitted" in why


def test_stamps_reads_a_long_frontmatter(tmp_path: Path) -> None:
    long_purpose = "x" * 5000
    (tmp_path / "p.mdx").write_text(
        pdm.build_frontmatter("T", long_purpose, "dev", "x", source_commit=HEAD) + "body\n",
        encoding="utf-8",
    )
    (tmp_path / "old.mdx").write_text(pdm.build_frontmatter("T", "d", "dev", "x"), encoding="utf-8")
    assert fresh.stamps(tmp_path) == {"old.mdx": None, "p.mdx": HEAD}


# --- the diagram count ------------------------------------------------------------------


def test_routes_follow_the_static_export() -> None:
    assert mer.route_for("index") == "/docs/"
    assert mer.route_for("dev-diagnostics") == "/docs/dev-diagnostics/"


def test_expected_diagrams_match_the_source_fences() -> None:
    """Re-derived independently: count ```mermaid fence lines in each registered doc."""
    expected = mer.expected_diagrams()
    assert len(expected) == len(PUBLISHED)
    for entry in PUBLISHED:
        lines = (REPO_ROOT / entry.path).read_text(encoding="utf-8").splitlines()
        count = sum(1 for line in lines if line.strip() == "```mermaid")
        assert expected[mer.route_for(pdm.make_slug(entry.path))] == count, entry.path
    assert sum(expected.values()) > 0, "no diagrams found: the check would be vacuous"


# --- local images point at the copies the projector makes ---------------------------------


def test_projected_images_point_at_the_copied_screenshots() -> None:
    """D4 observed the docs-site build failing on all 10 local images: the projector copied
    them to `content/docs/screenshots/` but left the source's `../screenshots/` links. Each
    projected local image must now point at `./screenshots/<name>`."""
    pages = {p.rel_posix: p for p in pdm.collect_pages()}
    image_re = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")

    def unfenced(body: str) -> str:
        kept, in_fence = [], False
        for line in body.splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
            elif not in_fence:
                kept.append(line)
        return "\n".join(kept)

    local = [
        (path, target)
        for path, page in pages.items()
        for target in image_re.findall(unfenced(page.body))
        if not target.startswith(("http://", "https://", "data:"))
    ]
    assert local, "no local images projected: this test would be vacuous"
    wrong = [(path, t) for path, t in local if not t.startswith("./screenshots/")]
    assert not wrong, wrong
    copied = {src.name for page in pages.values() for src in page.local_images}
    missing = [(path, t) for path, t in local if t.removeprefix("./screenshots/") not in copied]
    assert not missing, missing


def test_image_in_fenced_code_is_left_alone() -> None:
    lines = ["```", "![x](../screenshots/install_setup_user-picker.png)", "```"]
    assert pdm.rewrite_local_images("docs/user/install.md", lines) == lines

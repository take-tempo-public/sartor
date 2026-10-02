"""Focused unit tests for `scripts/project_docs_to_mdx.py` — the deterministic,
stdlib-only L1 -> Fumadocs MDX projection adapter (`feat/fumadocs-site`).

Scope, per the module's own docstring: the Purpose/Audience/Authoritative-for
-> frontmatter mapping, registry-driven selection and tiering
(`scripts/doc_registry.py`), slug generation, and the MDX-safety escaper (including the `<!-- -->` -> `{/* */}` rewrite).
Tests exercise pure, read-only functions only (`collect_pages()` reads the
real repo tree but writes nothing — `write_pages()`/`write_meta_json()`, which
DO write into `docs-site/content/docs/`, are deliberately not called here;
that side effect is proven by actually running the script + the JS build,
not by this gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import project_docs_to_mdx as pdm  # noqa: E402 - path insert must precede this import
from doc_registry import PUBLISHED, Entry  # noqa: E402

# ---------------------------------------------------------------------------
# Header parsing -> frontmatter fields
# ---------------------------------------------------------------------------


def test_parse_header_fields_extracts_purpose_audience_authoritative_for() -> None:
    lines = [
        "# A title",
        "",
        "> **Purpose:** what this doc is for, across",
        "> two lines.",
        "> **Audience:** `dev` — some humans.",
        "> **Authoritative for:** the one true fact,",
        "> also across two lines.",
        "",
        "body text",
    ]
    fields = pdm.parse_header_fields(lines)
    assert fields["Purpose"] == "what this doc is for, across two lines."
    assert fields["Audience"] == "`dev` — some humans."
    assert fields["Authoritative for"] == "the one true fact, also across two lines."


def test_has_full_header_true_for_l1_shape() -> None:
    fields = {"Purpose": "x", "Audience": "y", "Authoritative for": "z"}
    assert pdm.has_full_header(fields)


def test_has_full_header_false_for_wiki_shape() -> None:
    # docs/wiki/ pages use Purpose/Audience/**Grounding** — no Authoritative-for
    # line — which is exactly the signal that excludes L2 wiki pages from the
    # L1 projection without a path special-case. See module docstring "Scope".
    fields = {"Purpose": "x", "Audience": "y", "Grounding": "z"}
    assert not pdm.has_full_header(fields)


def test_has_full_header_false_when_incomplete() -> None:
    assert not pdm.has_full_header({"Purpose": "x", "Audience": "y"})
    assert not pdm.has_full_header({})


# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------


def test_make_slug_readme_is_index() -> None:
    assert pdm.make_slug("README.md") == "index"


def test_make_slug_examples() -> None:
    assert pdm.make_slug("vision.md") == "vision"
    assert pdm.make_slug("AGENTS.md") == "agents"
    assert pdm.make_slug("docs/PRODUCT_SHAPE.md") == "product-shape"
    # Slugs follow paths (owner, 2026-09-28): the tier directory is part of the slug.
    assert pdm.make_slug("docs/user/install.md") == "user-install"
    assert pdm.make_slug("docs/dev/architecture.md") == "dev-architecture"
    assert pdm.make_slug("docs/user/README.md") == "user-readme"
    assert pdm.make_slug("docs/governance/charter.md") == "governance-charter"
    assert pdm.make_slug("docs/dev/perf/PERF_ANALYZE.md") == "dev-perf-perf-analyze"


def test_make_slug_is_unique_over_the_registry() -> None:
    slugs = [pdm.make_slug(e.path) for e in PUBLISHED]
    assert len(slugs) == len(set(slugs)), "make_slug() produced a collision over the registry"


# ---------------------------------------------------------------------------
# MDX-safety escaping
# ---------------------------------------------------------------------------


def test_escape_mdx_unsafe_escapes_stray_angle_bracket_in_prose() -> None:
    out = pdm.escape_mdx_unsafe(["Run it as <username> on the box."])
    assert out == ["Run it as &lt;username> on the box."]


def test_escape_mdx_unsafe_leaves_inline_code_untouched() -> None:
    out = pdm.escape_mdx_unsafe(["See `<username>` for the placeholder."])
    assert out == ["See `<username>` for the placeholder."]


def test_escape_mdx_unsafe_leaves_fenced_code_untouched() -> None:
    lines = ["```python", "safe_user = _safe_username(username)  # <not-escaped>", "```"]
    assert pdm.escape_mdx_unsafe(lines) == lines


def test_escape_mdx_unsafe_rewrites_html_comment_to_mdx_comment() -> None:
    # Note the double space before `*/}`: the original comment body's own
    # trailing space (before `-->`) is preserved verbatim, and the closing
    # token itself is prefixed with a space too — cosmetic only, since an MDX
    # comment renders invisibly either way.
    out = pdm.escape_mdx_unsafe(["<!-- DOC-STATUS(x): claim state -->"])
    assert out == ["{/* DOC-STATUS(x): claim state  */}"]


def test_escape_mdx_unsafe_html_comment_spans_multiple_lines() -> None:
    lines = ["<!-- line one", "line two -->", "after"]
    out = pdm.escape_mdx_unsafe(lines)
    assert out[0] == "{/* line one"
    assert out[1] == "line two  */}"
    assert out[2] == "after"


def test_escape_mdx_unsafe_escapes_bare_curly_braces() -> None:
    out = pdm.escape_mdx_unsafe(["a bare {expression} in prose"])
    assert out == ["a bare &#123;expression&#125; in prose"]


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def test_build_frontmatter_shape_and_quoting() -> None:
    fm = pdm.build_frontmatter(
        title='A "quoted" title',
        description="a description",
        audience="dev",
        authoritative_for="the fact",
    )
    lines = fm.splitlines()
    assert lines[0] == "---"
    assert lines[1] == 'title: "A \\"quoted\\" title"'
    assert lines[2] == 'description: "a description"'
    assert lines[3] == 'audience: ["dev"]'
    assert lines[4] == 'authoritativeFor: "the fact"'
    assert lines[5] == "---"


# ---------------------------------------------------------------------------
# End-to-end (read-only): collect_pages() over the real repo tree
# ---------------------------------------------------------------------------


def test_collect_pages_over_real_repo_includes_readme_as_user_tier_index() -> None:
    pages = pdm.collect_pages()
    by_rel = {p.rel_posix: p for p in pages}
    assert "README.md" in by_rel
    readme = by_rel["README.md"]
    assert readme.slug == "index"
    assert readme.audience == "user"
    assert readme.title  # non-empty
    assert readme.body.startswith("---\n")


def test_collect_pages_projects_exactly_the_registry_in_order() -> None:
    pages = pdm.collect_pages()
    assert [p.rel_posix for p in pages] == [e.path for e in PUBLISHED]
    assert [p.audience for p in pages] == [e.tier for e in PUBLISHED]


def test_collect_pages_has_both_audience_tiers() -> None:
    pages = pdm.collect_pages()
    audiences = {p.audience for p in pages}
    assert audiences == {"user", "dev"}


def test_collect_pages_rejects_a_registered_doc_without_the_header() -> None:
    # A registered path that exists but has no Purpose/Audience/Authoritative-for
    # header must stop the build, not be silently skipped.
    with pytest.raises(pdm.ProjectionError, match="lacks the full"):
        pdm.collect_pages((Entry("LICENSE", "dev"),))


def test_collect_pages_rejects_a_missing_registered_doc() -> None:
    with pytest.raises(pdm.ProjectionError, match="unreadable"):
        pdm.collect_pages((Entry("docs/no-such-doc.md", "dev"),))


def test_meta_pages_order_is_index_then_user_tier_then_dev_tier() -> None:
    pages = pdm.collect_pages()
    order = pdm.build_meta_pages_order(pages)
    user_slugs = [p.slug for p in pages if p.audience == "user" and p.slug != "index"]
    dev_slugs = [p.slug for p in pages if p.audience == "dev"]
    assert order == [
        "index",
        pdm.USER_SEPARATOR,
        *user_slugs,
        pdm.DEV_SEPARATOR,
        *dev_slugs,
    ]


def test_meta_separators_use_fumadocs_separator_syntax() -> None:
    # fumadocs-core's loader matches /^---(?:\[(?<icon>[^\]]+)])?(?<name>.+)---|^---$/.
    for sep in (pdm.USER_SEPARATOR, pdm.DEV_SEPARATOR):
        assert sep.startswith("---") and sep.endswith("---") and len(sep) > 6


def test_meta_pages_order_follows_registry_within_user_tier() -> None:
    # The user ladder (design §4): vision before install before walkthrough, which
    # is registry order, not alphabetical (which would put "install" first).
    order = pdm.build_meta_pages_order(pdm.collect_pages())
    assert order.index("vision") < order.index("user-install") < order.index("user-walkthrough")


# ---------------------------------------------------------------------------
# Cross-document link rewriting
#
# The projected site is served from /docs/<slug> routes; the SOURCE docs link
# each other as repo-relative markdown paths (`vision.md`, `../architecture.md`).
# Before the rewrite pass those shipped verbatim and 404'd — ~490 dead links
# across 33 of 35 pages. These pin the two halves of the fix: a link to a
# projected doc becomes its site route, and a link to anything the site does not
# carry becomes the GitHub URL where that content really lives.
# ---------------------------------------------------------------------------

SLUG_MAP = {
    "README.md": "index",
    "vision.md": "vision",
    "docs/architecture.md": "architecture",
    "docs/dev/RELEASE_ARC.md": "dev-release-arc",
}


def test_rewrite_link_to_projected_doc_becomes_site_route() -> None:
    assert pdm.rewrite_link_target("README.md", "vision.md", SLUG_MAP) == "/docs/vision"
    # resolved relative to the LINKING doc's own directory, per markdown rules
    assert (
        pdm.rewrite_link_target("docs/dev/RELEASE_ARC.md", "../architecture.md", SLUG_MAP)
        == "/docs/architecture"
    )


def test_rewrite_link_preserves_anchor_fragment() -> None:
    assert (
        pdm.rewrite_link_target("README.md", "docs/architecture.md#llm-routing", SLUG_MAP)
        == "/docs/architecture#llm-routing"
    )


def test_rewrite_link_to_readme_targets_docs_root_not_docs_index() -> None:
    assert pdm.rewrite_link_target("vision.md", "README.md", SLUG_MAP) == "/docs"


def test_rewrite_link_to_unprojected_file_becomes_github_blob_url() -> None:
    # Source files and L2 wiki pages are not on the site — GitHub is their real home.
    assert pdm.rewrite_link_target("README.md", "analyzer.py", SLUG_MAP) == (
        f"{pdm.GITHUB_BASE}/blob/main/analyzer.py"
    )
    assert pdm.rewrite_link_target("docs/architecture.md", "wiki/SCHEMA.md", SLUG_MAP) == (
        f"{pdm.GITHUB_BASE}/blob/main/docs/wiki/SCHEMA.md"
    )


def test_rewrite_link_to_directory_becomes_github_tree_url() -> None:
    assert pdm.rewrite_link_target("README.md", "docs/governance/", SLUG_MAP) == (
        f"{pdm.GITHUB_BASE}/tree/main/docs/governance"
    )


def test_rewrite_link_leaves_external_and_anchor_targets_untouched() -> None:
    for target in ("https://example.com", "mailto:a@b.c", "#same-page", "/already/absolute"):
        assert pdm.rewrite_link_target("README.md", target, SLUG_MAP) is None


def test_rewrite_cross_doc_links_skips_fenced_code_and_images() -> None:
    lines = [
        "See [vision](vision.md).",
        "```markdown",
        "[vision](vision.md)",  # sample text, not navigation — must not be rewritten
        "```",
        "![shot](screenshots/x.png)",  # image: the static-import path, not a URL
    ]
    out = pdm.rewrite_cross_doc_links("README.md", lines, SLUG_MAP)
    assert out[0] == "See [vision](/docs/vision)."
    assert out[2] == "[vision](vision.md)"
    assert out[4] == "![shot](screenshots/x.png)"


def test_no_projected_page_body_ships_a_raw_repo_relative_md_link() -> None:
    # The end-to-end invariant: after projection, no page BODY may carry a bare
    # `.md` link — that is precisely what 404'd on the live site.
    for page in pdm.collect_pages():
        body = page.body.split("---", 2)[-1]  # drop the YAML frontmatter block
        for match in pdm._LINK_RE.finditer(body):
            target = match.group(2)
            if target.startswith(("http", "#", "/")):
                continue
            assert not target.endswith(".md"), f"{page.rel_posix}: unrewritten link {target}"

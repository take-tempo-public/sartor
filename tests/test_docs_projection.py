"""Focused unit tests for `scripts/project_docs_to_mdx.py` — the deterministic,
stdlib-only L1 -> Fumadocs MDX projection adapter (`feat/fumadocs-site`).

Scope, per the module's own docstring: the Purpose/Audience/Authoritative-for
-> frontmatter mapping, the audience classification (SCHEMA backtick-token
parse + blanket-path fallback + conservative `dev` default), slug generation,
and the MDX-safety escaper (including the `<!-- -->` -> `{/* */}` rewrite).
Tests exercise pure, read-only functions only (`collect_pages()` reads the
real repo tree but writes nothing — `write_pages()`/`write_meta_json()`, which
DO write into `docs-site/content/docs/`, are deliberately not called here;
that side effect is proven by actually running the script + the JS build,
not by this gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import project_docs_to_mdx as pdm  # noqa: E402 - path insert must precede this import

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
# Audience classification
# ---------------------------------------------------------------------------


def test_classify_audience_prefers_backtick_token() -> None:
    # SCHEMA.md's own convention wins even for a path the blanket rule would
    # otherwise call `dev` (docs/dev/**).
    assert pdm.classify_audience("docs/dev/documentation-architecture.md", "`dev`") == "dev"
    assert pdm.classify_audience("docs/dev/anything.md", "`user` — see below") == "user"


def test_classify_audience_blanket_path_fallback_user() -> None:
    for rel, prose in (
        ("README.md", "the one place all three audiences meet"),
        ("docs/install.md", "humans installing sartor. for the first time."),
        ("docs/walkthrough.md", "humans using the app for the first time"),
        ("docs/walkthrough_example.md", "humans reading the walkthrough"),
        ("vision.md", "humans evaluating whether to use or contribute"),
    ):
        assert pdm.classify_audience(rel, prose) == "user", rel


def test_classify_audience_blanket_path_fallback_dev() -> None:
    assert pdm.classify_audience("docs/dev/nursery.md", "humans + LLM agents") == "dev"
    assert pdm.classify_audience("docs/dev/perf/PERF_ANALYZE.md", "humans deciding") == "dev"


def test_classify_audience_conservative_default_is_dev() -> None:
    # A path the blanket table doesn't mention and with no backtick token —
    # e.g. AGENTS.md, docs/governance/charter.md, docs/architecture.md in the
    # real corpus — must not be silently promoted to the simple `user` front
    # door.
    assert pdm.classify_audience("AGENTS.md", "AI coding agents AND humans") == "dev"
    assert pdm.classify_audience("docs/governance/charter.md", "every contributor") == "dev"
    assert pdm.classify_audience("docs/architecture.md", "humans contributing PRs") == "dev"


# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------


def test_make_slug_readme_is_index() -> None:
    assert pdm.make_slug("README.md") == "index"


def test_make_slug_examples() -> None:
    assert pdm.make_slug("vision.md") == "vision"
    assert pdm.make_slug("AGENTS.md") == "agents"
    assert pdm.make_slug("docs/PRODUCT_SHAPE.md") == "product-shape"
    assert pdm.make_slug("docs/governance/charter.md") == "governance-charter"
    assert pdm.make_slug("docs/dev/perf/PERF_ANALYZE.md") == "dev-perf-perf-analyze"


def test_make_slug_is_globally_unique_over_real_l1_set() -> None:
    slugs = [pdm.make_slug(p) for p in pdm.list_repo_md_files()]
    assert len(slugs) == len(set(slugs)), "make_slug() produced a collision over the real repo tree"


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


def test_collect_pages_excludes_wiki_pages() -> None:
    pages = pdm.collect_pages()
    assert all(not p.rel_posix.startswith("docs/wiki/") for p in pages)


def test_collect_pages_has_both_audience_tiers() -> None:
    pages = pdm.collect_pages()
    audiences = {p.audience for p in pages}
    assert audiences == {"user", "dev"}


def test_meta_pages_order_is_index_then_user_tier_then_dev_tier() -> None:
    pages = pdm.collect_pages()
    readme_lines = (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    doc_map_order = pdm.parse_doc_map_order(readme_lines)
    assert doc_map_order, "README's Documentation-map block should parse at least one link"
    in_scope = [p.rel_posix for p in pages]
    priority = pdm.build_priority_index(doc_map_order, in_scope)

    slug_order = pdm.build_meta_pages_order(pages, priority)
    by_slug = {p.slug: p for p in pages}

    assert slug_order[0] == "index"
    tiers = [by_slug[slug].audience for slug in slug_order]
    # Once a `dev` slug appears, every remaining slug must also be `dev` — i.e.
    # the array is exactly [index, user..., dev...], never interleaved.
    first_dev = tiers.index("dev")
    assert all(t == "dev" for t in tiers[first_dev:])
    assert all(t == "user" for t in tiers[1:first_dev])


def test_meta_pages_order_follows_readme_doc_map_within_user_tier() -> None:
    # The README Documentation-map lists vision.md before docs/install.md
    # before docs/walkthrough.md — the ICP-ladder ordering should be literal,
    # not alphabetical (which would put "install" before "vision").
    pages = pdm.collect_pages()
    readme_lines = (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    doc_map_order = pdm.parse_doc_map_order(readme_lines)
    in_scope = [p.rel_posix for p in pages]
    priority = pdm.build_priority_index(doc_map_order, in_scope)
    slug_order = pdm.build_meta_pages_order(pages, priority)

    assert slug_order.index("vision") < slug_order.index("install")
    assert slug_order.index("install") < slug_order.index("walkthrough")


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

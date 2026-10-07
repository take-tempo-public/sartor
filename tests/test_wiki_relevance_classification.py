"""Wiki-relevance classification audit — keeps `scripts/wiki_relevance.py` honest.

Mirrors `tests/test_egress_allowlist.py`'s `test_static_egress_allowlist` shape (the
only existing precedent in this repo for a maintained classification list that cannot
silently rot): enumerate the CURRENT top-level repo entries (root, `docs/`'s immediate
children, `docs/dev/`'s immediate children — the three levels where wiki-relevance
actually varies) and assert every one of them is accounted for by
`scripts/wiki_relevance.py`, in both directions — `offenders` (a new, unclassified
entry appeared) and `stale` (a classified entry no longer exists). See
`docs/dev/diagnosis/wiki-freshness-relevance-classification.md` for why this exists:
the un-classified drift count tripped the merge-blocking wiki-freshness gate on
false-positive process/provenance churn twice before this module existed.
"""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path

from scripts import wiki_relevance

REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = REPO_ROOT / "docs" / "wiki"


def _git_tree_entries(rel_dir: str) -> list[str]:
    """Immediate git-TRACKED children of `rel_dir` (repo-relative POSIX, "" for root),
    as repo-relative POSIX strings. `git ls-tree` (not filesystem iteration) so
    gitignored/untracked local artifacts (`.mypy_cache`, `.vscode`, `CLAUDE.local.md`,
    `.api_key`, IDE/tool caches, ...) never need classifying — they can never appear
    in a `git diff` in the first place, so they are outside this classifier's domain.

    Uses the `<tree-ish>:<path>` colon form (not a bare pathspec argument) — a bare
    `git ls-tree HEAD docs` returns `docs` itself as the one matching top-level entry,
    not its children; `HEAD:docs` addresses the subtree object directly.
    """
    tree_ish = f"HEAD:{rel_dir}" if rel_dir else "HEAD"
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "ls-tree", "--name-only", tree_ish],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    prefix = f"{rel_dir}/" if rel_dir else ""
    return [f"{prefix}{name}" for name in result.stdout.splitlines() if name.strip()]


_ALL_KNOWN_DIR_PREFIXES = wiki_relevance.IRRELEVANT_PREFIXES | wiki_relevance.MIXED_PREFIXES


def _classified(entry_rel_posix: str, *, is_dir: bool) -> bool:
    """True if `entry_rel_posix` (a top-level or docs/*, docs/dev/* entry) is
    accounted for by any of the four classification containers."""
    candidate = f"{entry_rel_posix}/" if is_dir else entry_rel_posix
    if any(candidate.startswith(p) or entry_rel_posix + "/" == p for p in _ALL_KNOWN_DIR_PREFIXES):
        return True
    if entry_rel_posix in wiki_relevance.IRRELEVANT_FILES:
        return True
    if entry_rel_posix in wiki_relevance.RELEVANT_OVERRIDES:
        return True
    return entry_rel_posix in wiki_relevance.KNOWN_RELEVANT_TOP_LEVEL


def test_every_top_level_entry_is_classified() -> None:
    """No unreviewed root / docs/ / docs/dev/ entry — every one is explicitly
    irrelevant, mixed, or acknowledged relevant. A new directory of either shape
    (a fresh process-doc bucket like `docs/dev/handoffs/` once was, or a fresh
    production module) must be a deliberate edit to `scripts/wiki_relevance.py`,
    never a silent default.
    """
    root_entries = _git_tree_entries("")
    docs_entries = _git_tree_entries("docs")
    docs_dev_entries = _git_tree_entries("docs/dev")

    unclassified = []
    for rel in root_entries:
        is_dir = (REPO_ROOT / rel).is_dir()
        if not _classified(rel, is_dir=is_dir):
            unclassified.append(rel)
    for rel in docs_entries:
        is_dir = (REPO_ROOT / rel).is_dir()
        if not _classified(rel, is_dir=is_dir):
            unclassified.append(rel)
    for rel in docs_dev_entries:
        is_dir = (REPO_ROOT / rel).is_dir()
        if not _classified(rel, is_dir=is_dir):
            unclassified.append(rel)

    assert not unclassified, (
        f"Unclassified top-level entr(y/ies) for wiki-relevance: {sorted(unclassified)}. "
        "Add each to one of scripts/wiki_relevance.py's IRRELEVANT_PREFIXES / "
        "IRRELEVANT_FILES / MIXED_PREFIXES / KNOWN_RELEVANT_TOP_LEVEL on purpose — "
        "never let it fall through unreviewed."
    )


def test_no_stale_classification_entries() -> None:
    """Every classified prefix/file still exists — a renamed or removed directory
    left behind in `scripts/wiki_relevance.py` is dead weight that hides the next
    person's ability to tell what's actually been reviewed."""
    stale_dirs = [
        prefix
        for prefix in sorted(wiki_relevance.IRRELEVANT_PREFIXES | wiki_relevance.MIXED_PREFIXES)
        if not (REPO_ROOT / prefix.rstrip("/")).is_dir()
    ]
    stale_files = [
        path
        for path in sorted(wiki_relevance.IRRELEVANT_FILES | wiki_relevance.RELEVANT_OVERRIDES)
        if not (REPO_ROOT / path).is_file()
    ]
    stale_known_relevant = [
        entry
        for entry in sorted(wiki_relevance.KNOWN_RELEVANT_TOP_LEVEL)
        if not (REPO_ROOT / entry).exists()
    ]
    assert not stale_dirs, f"Classified directories no longer exist: {stale_dirs}"
    assert not stale_files, f"Classified files no longer exist: {stale_files}"
    assert not stale_known_relevant, (
        f"KNOWN_RELEVANT_TOP_LEVEL entries no longer exist: {stale_known_relevant}"
    )


def test_relevant_overrides_live_inside_a_mixed_prefix() -> None:
    """A RELEVANT_OVERRIDES entry that doesn't sit under a MIXED_PREFIXES directory
    is dead code — it would already default to relevant with no override needed."""
    stray = [
        path
        for path in sorted(wiki_relevance.RELEVANT_OVERRIDES)
        if not any(path.startswith(prefix) for prefix in wiki_relevance.MIXED_PREFIXES)
    ]
    assert not stray, (
        f"RELEVANT_OVERRIDES entr(y/ies) not under any MIXED_PREFIXES directory: {stray} "
        "— either move the entry's directory into MIXED_PREFIXES or drop the override."
    )


def test_is_wiki_relevant_matches_known_shapes() -> None:
    """Capability check: the classifier gives the right verdict for one example of
    each container, so the containers above are proven load-bearing, not just present."""
    assert wiki_relevance.is_wiki_relevant("analyzer.py") is True  # default relevant
    assert (
        wiki_relevance.is_wiki_relevant("docs/dev/handoffs/fix-x.md") is False
    )  # irrelevant prefix
    assert wiki_relevance.is_wiki_relevant("docs/dev/work/BOARD.md") is False  # irrelevant file
    assert (
        wiki_relevance.is_wiki_relevant("scripts/an_uncited_tool.py") is False
    )  # mixed, not overridden
    assert (
        wiki_relevance.is_wiki_relevant("scripts/generate_openapi_spec.py") is True
    )  # mixed, overridden
    # mixed, wiki-cited 26 times — item 153: this was False, so a gate.py change never
    # counted as drift
    assert wiki_relevance.is_wiki_relevant("scripts/gate.py") is True
    assert wiki_relevance.is_wiki_relevant("docs/wiki/pages/x.md") is False
    assert wiki_relevance.is_wiki_relevant("docs-site/content/x.mdx") is False


def test_filter_relevant_preserves_order_and_drops_irrelevant() -> None:
    paths = ["analyzer.py", "docs/dev/ledger/a.jsonl", "tests/test_x.py", "hardening.py"]
    assert wiki_relevance.filter_relevant(paths) == ["analyzer.py", "hardening.py"]


# A path-like token ending in an extension a wiki page cites, and a dotted module
# reference (`python -m scripts.gate`). `\b` keeps `x.json` from matching inside `x.jsonl`.
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|md|sh|mjs|json|toml|ya?ml)\b")
_DOTTED_MODULE_RE = re.compile(r"\bscripts(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


def _resolve_token(token: str, tracked: frozenset[str], by_name: dict[str, list[str]]) -> list[str]:
    """Every tracked file `token` can denote: an exact repo path, a relative link with its
    leading `../` / `./` segments stripped, or a bare name / partial path matched as a
    `/`-anchored suffix. More than one result is an ambiguous cite."""
    if token in tracked:
        return [token]
    stripped = token
    while stripped.startswith(("../", "./")):
        stripped = stripped.split("/", 1)[1]
    stripped = stripped.lstrip("/")
    if stripped in tracked:
        return [stripped]
    return [p for p in by_name.get(stripped.rsplit("/", 1)[-1], []) if p.endswith("/" + stripped)]


def _resolve_dotted(token: str, tracked: frozenset[str]) -> list[str]:
    """`scripts.a.b.attr` -> the longest `scripts/a/b.py` prefix that is a tracked file."""
    parts = token.split(".")
    for k in range(len(parts), 1, -1):
        candidate = "/".join(parts[:k]) + ".py"
        if candidate in tracked:
            return [candidate]
    return []


def _wiki_cited_mixed_paths() -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Derive, from what the wiki actually cites, the MIXED_PREFIXES files that must count
    as drift. Returns `(cited, ambiguous)`: `cited` maps each cited mixed-prefix file to
    the wiki files citing it; `ambiguous` maps a non-full-path cite that could denote more
    than one tracked file (at least one of them mixed-prefix) to its candidates.

    Reads every `docs/wiki/**/*.md` except `log.md` — the append-only operation log names
    paths as history, not as current sources. One `git ls-files` for the whole tree, and a
    basename index, so resolution is a dict lookup per token, not a scan per token.
    """
    listing = subprocess.run(
        ["git", "ls-files"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    tracked = frozenset(line for line in listing.stdout.splitlines() if line.strip())
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in tracked:
        by_name[path.rsplit("/", 1)[-1]].append(path)

    def _is_mixed(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in wiki_relevance.MIXED_PREFIXES)

    cited: dict[str, set[str]] = defaultdict(set)
    ambiguous: dict[str, list[str]] = {}
    for page in sorted(WIKI_DIR.rglob("*.md")):
        if page.name == "log.md":
            continue
        text = page.read_text(encoding="utf-8")
        page_rel = page.relative_to(REPO_ROOT).as_posix()
        resolved = [_resolve_token(t, tracked, by_name) for t in set(_PATH_TOKEN_RE.findall(text))]
        resolved += [_resolve_dotted(t, tracked) for t in set(_DOTTED_MODULE_RE.findall(text))]
        for token_hits in resolved:
            mixed_hits = [p for p in token_hits if _is_mixed(p)]
            if not mixed_hits:
                continue
            if len(token_hits) > 1:
                ambiguous.setdefault(f"{page_rel}: {token_hits}", sorted(token_hits))
                continue
            cited[mixed_hits[0]].add(page_rel)
    return dict(cited), ambiguous


def test_relevant_overrides_equal_wiki_cited_mixed_files() -> None:
    """RELEVANT_OVERRIDES is exactly the set of MIXED_PREFIXES files the wiki cites — in
    both directions (item 153). A hand list with no derivation behind it rotted: 13 of
    the files wiki pages cite (`scripts/gate.py` 26 times) classified as irrelevant, so a
    change to them never counted as drift, while two overrides no page had ever cited
    stayed listed. The list stays explicit — no wiki scan at classification time — and
    this test is what keeps it equal to the wiki.
    """
    cited, ambiguous = _wiki_cited_mixed_paths()
    assert not ambiguous, (
        "Wiki cite(s) that could denote more than one tracked file, at least one under a "
        f"MIXED_PREFIXES directory: {sorted(ambiguous)}. Cite the full repo path instead."
    )
    missing = {
        path: sorted(pages)
        for path, pages in sorted(cited.items())
        if path not in wiki_relevance.RELEVANT_OVERRIDES
    }
    stale = sorted(wiki_relevance.RELEVANT_OVERRIDES - cited.keys())
    # Both directions in one failure, so a single run shows the whole correction.
    assert not missing and not stale, (
        "scripts/wiki_relevance.py RELEVANT_OVERRIDES disagrees with what the wiki cites.\n"
        f"  MISSING (cited by the wiki, but is_wiki_relevant() is False, so a change never "
        f"counts as drift) - add each: {missing}\n"
        f"  STALE (listed, but no wiki page cites it) - drop each: {stale}"
    )

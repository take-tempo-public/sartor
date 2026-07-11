#!/usr/bin/env python3
"""Deterministic, stdlib-only cross-document link + cite checker.

**Why this exists.** `wiki-lint` (see `commands/wiki-lint.md`) only checks
`docs/wiki/` structural integrity ([[backlinks]], `path:line` cite
*drift*, index coherence). The extract-don't-restate move that produced
`docs/governance/` multiplied plain `[text](path)` pointers across the
contract docs (`AGENTS.md`/`CLAUDE.md`) and the rest of the doc set with no
gate checking them — pointer rot risk. This script is that periodic gate.
It rides the existing `pytest` gate via `tests/test_doc_links.py` (see that
file) rather than adding a new CI job — the pytest job already runs on every
PR, so wiring in there IS the "periodic" mechanism.

**Scope**

1. Link check (ALL tracked `*.md` files, repo-wide — see `list_md_files()`).
   Resolves every relative markdown link `[text](path)` /
   `[text](path#anchor)` against the file that contains it, verifies the
   target exists, and — for `.md` targets with a `#fragment` — verifies a
   matching heading exists in the target (or the current file, for
   fragment-only `#anchor` links). This intentionally INCLUDES
   `docs/wiki/*.md` pages: they use the identical plain relative-link
   convention as every other doc in the tree, so validating their
   `[text](path)` links here is free. Their `[[backlink]]` graph and
   `path:line` cite *drift* stay `wiki-lint`'s job — untouched here.

2. Cite check (SCOPED — `docs/governance/*.md` + the L1 "published front door"
   registry `check_doc_frontmatter.PUBLISHED_DOC_FILES`, widened from the
   original `AGENTS.md`/`CLAUDE.md`-only scope by `ci/doc-merge-gate`'s
   merge=publish "cite-resolution" gate — see that module's docstring for the
   registry's scope rationale). These docs use inline `` `path:SYMBOL` `` /
   `` `path:LINE` `` cites (e.g. `` `analyzer.py:SYSTEM_PROMPT` ``,
   `` `RELEASE_CHECKLIST.md:64` ``). This checker verifies the **file** named
   by the cite exists somewhere in the tracked tree — the same "cheap
   existence check, not a line/symbol resolution check" scope `/wiki-lint`
   documents for `path:line` cites inside `docs/wiki/` pages (deeper
   quote-matching is `/wiki-audit`'s job there; there is no deeper checker for
   L1 docs, by the same reasoning). `docs/governance/` stays a directory-wide
   prefix (not folded into the file registry) so `compliance-log.md` — an
   append-only log, deliberately excluded from `PUBLISHED_DOC_FILES` (gate 2's
   header check does not apply to logs) — keeps its pre-existing cite
   coverage unchanged.

**Exclusions (by design, not oversight)**

- External links (`http://`, `https://`, `mailto:`, any other URI scheme).
- Content inside fenced code blocks (``` / ~~~) — parsed and skipped so a
  code sample containing `[text](path)`-shaped text never false-positives.
- A `` `[text](path)` `` link written as a literal backtick-quoted example
  (both the leading `` ` `` before `[` and the trailing `` ` `` after `)`
  present) — several docs show the link *syntax* itself as an example.
- Targets that don't exist on disk but ARE gitignored (checked via
  `git check-ignore`) — e.g. a doc pointing at `output/` or `.api_key` as
  an illustrative path. These are expected to be absent in a fresh clone
  and are not broken links.

**Anchor slugger — conservative, GitHub-slug-shaped, documented limits**

`_github_slug()` approximates GitHub's heading-to-anchor algorithm (verified
against real anchors in this repo, including double-hyphen cases from
stripped punctuation like `&`/`—`/`→`). Known limitations:

- Only ATX headings (`#`..`######`) are recognized; Setext (`===`/`---`)
  headings are not.
- Duplicate slugs on one page get GitHub's `-1`, `-2`, ... suffixes, but the
  de-dup only reflects headings this script actually parses (i.e. also
  ATX-only).
- Heading text is lightly de-markdowned (inline code unwrapped, `[text](url)`
  reduced to `text`, `*`/`**` emphasis markers stripped) before slugging.
  Nested/unusual constructs (e.g. a link *inside* inline code inside a
  heading) may not exactly match GitHub's real renderer. None of the
  anchors actually used in this repo hit that edge at the time of writing.
- Anchor verification only runs for `.md` targets. Non-md fragments (e.g.
  `../../static/app.js#L3404`, a GitHub UI line-highlight anchor, not a
  markdown heading) are accepted without verification — there is no
  markdown heading to check them against.

Exit 0 clean; exit 1 with a `file:line -> broken-target` listing.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

from check_doc_frontmatter import PUBLISHED_DOC_FILES

REPO_ROOT = Path(__file__).resolve().parent.parent

# Cite check is scoped to the governance dir (kept directory-wide — see module
# docstring) plus the L1 "published front door" registry (gate 2's
# PUBLISHED_DOC_FILES, reused here rather than restated — D5 applied to this
# gate's own code). Line-drift checking elsewhere is out of scope (wiki-lint's
# job for docs/wiki/; docs/dev/** review/design prose is out of scope for the
# same reason gate 2 excludes it — see check_doc_frontmatter's docstring).
CITE_CHECK_FILES: frozenset[str] = PUBLISHED_DOC_FILES
CITE_CHECK_DIRS = ("docs/governance/",)

_URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
_FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
_ATX_RE = re.compile(r"^#{1,6}\s+(.*)$")
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_MD_INLINE_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_CODE_RE = re.compile(r"`([^`]*)`")
_MD_EMPHASIS_RE = re.compile(r"\*{1,3}")
_SLUG_STRIP_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_CITE_RE = re.compile(
    r"`([\w./\\-]+\.(?:py|md|js|jsx|ts|tsx|html|mmd|txt|json|ya?ml|sh|toml|cfg|ini)):([A-Za-z0-9_]+)`"
)

# Narrow, documented exclusions for link SHAPES the checker cannot validate
# reliably without misrepresenting content (see module docstring policy: "add
# a narrow documented exclusion rather than weakening the whole check").
#
# 1. The literal placeholder idiom `[text](path)` — used repeatedly across
#    this repo's meta-documentation as generic prose shorthand for "a
#    markdown link" (not a real link). Most instances are already
#    backtick-quoted (and so already skipped); this catches the bare form.
_PLACEHOLDER_LINK = ("text", "path")

# 2. docs/dev/governance-extraction-design.md's "Generic pointer block" +
#    per-doc "Pointer:" sections (lines ~99-129) are VERBATIM INSERTION
#    TEMPLATES meant to be pasted into other docs at OTHER, VARYING depths
#    (SECURITY.md/CONTRIBUTING.md/AGENTS.md/vision.md at repo root;
#    PRODUCT_SHAPE.md one level deep; RELEASE_ARC.md two levels deep) — the
#    template block is explicitly labeled for multiple destinations at once,
#    so no single relative depth is "correct" for all of them, and the one
#    already-landed copy (AGENTS.md, confirmed against git history) proves
#    the template's un-prefixed `docs/governance/...` form is right for ITS
#    repo-root destinations. Adding `../` would fix the link as read from
#    this file's own location but would misrepresent the template for the
#    (majority) repo-root destinations it was actually written for — a
#    content judgment call, not a mechanical path fix. The governance
#    extraction this design doc specifies has already landed (see
#    docs/governance/compliance-log.md CW-01), so this is a frozen design
#    artifact, not live navigation. Excluded by exact (file, target) pair.
_TEMPLATE_QUOTE_LINKS: set[tuple[str, str]] = {
    ("docs/dev/governance-extraction-design.md", "docs/governance/"),
    ("docs/dev/governance-extraction-design.md", "docs/governance/charter.md"),
    ("docs/dev/governance-extraction-design.md", "docs/governance/enforcement.md"),
}


def _run_git(args: list[str]) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def list_md_files() -> list[Path]:
    """All tracked *.md files, repo-wide (relative Paths from repo root)."""
    out = _run_git(["ls-files", "*.md"])
    return [Path(line) for line in out.splitlines() if line.strip()]


def list_tracked_files() -> set[str]:
    """Basenames -> set of tracked repo-relative paths (for cite/basename lookup)."""
    out = _run_git(["ls-files"])
    return {line.strip() for line in out.splitlines() if line.strip()}


def _is_gitignored(path: Path) -> bool:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "check-ignore", "-q", str(path)],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def _iter_unfenced_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (1-based lineno, line) for lines NOT inside a fenced code block."""
    in_fence = False
    fence_char = None
    for lineno, line in enumerate(lines, start=1):
        m = _FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            char = marker[0]
            if not in_fence:
                in_fence = True
                fence_char = char
            elif char == fence_char:
                in_fence = False
                fence_char = None
            continue
        if in_fence:
            continue
        yield lineno, line


def _plain_text(heading_text: str) -> str:
    t = _MD_INLINE_LINK_RE.sub(r"\1", heading_text)
    t = _MD_CODE_RE.sub(r"\1", t)
    t = _MD_EMPHASIS_RE.sub("", t)
    return t


def _github_slug(heading_text: str) -> str:
    t = _plain_text(heading_text).strip().lower()
    t = re.sub(r"\s+#+\s*$", "", t)  # trailing ATX closing hashes, e.g. "## Foo ##"
    t = _SLUG_STRIP_RE.sub("", t)
    return t.replace(" ", "-")


def extract_headings(lines: list[str]) -> list[str]:
    """ATX heading text, in document order, from non-fenced lines."""
    headings = []
    for _, line in _iter_unfenced_lines(lines):
        m = _ATX_RE.match(line)
        if m:
            headings.append(m.group(1))
    return headings


def slugs_for(lines: list[str]) -> set[str]:
    """The full set of GitHub-style anchor slugs a file's headings produce,
    including the `-1`, `-2`, ... suffixes GitHub assigns to duplicates."""
    seen: dict[str, int] = {}
    slugs: set[str] = set()
    for text in extract_headings(lines):
        base = _github_slug(text)
        if base in seen:
            seen[base] += 1
            slugs.add(f"{base}-{seen[base]}")
        else:
            seen[base] = 0
            slugs.add(base)
    return slugs


class Violation:
    def __init__(self, file: Path, line: int, target: str, reason: str):
        self.file = file
        self.line = line
        self.target = target
        self.reason = reason

    def __str__(self) -> str:
        posix = self.file.as_posix()
        return f"{posix}:{self.line} -> {self.target}  ({self.reason})"


def _split_target(target: str) -> tuple[str, str | None]:
    if "#" in target:
        path_part, _, frag = target.partition("#")
        return path_part, frag
    return target, None


def check_links(md_files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    # Cache heading-slug sets per resolved target file, computed lazily.
    slug_cache: dict[Path, set[str]] = {}

    def slugs_of(abs_path: Path) -> set[str]:
        if abs_path not in slug_cache:
            try:
                text = abs_path.read_text(encoding="utf-8")
            except OSError:
                slug_cache[abs_path] = set()
            else:
                slug_cache[abs_path] = slugs_for(text.splitlines())
        return slug_cache[abs_path]

    for rel_path in md_files:
        abs_path = REPO_ROOT / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.append(Violation(rel_path, 0, str(rel_path), f"unreadable: {exc}"))
            continue
        lines = text.splitlines()

        for lineno, line in _iter_unfenced_lines(lines):
            for m in _LINK_RE.finditer(line):
                start, end = m.span()
                # Skip a link written as a literal backtick-quoted example:
                # `[text](path)` — backtick immediately wraps the whole thing.
                before = line[start - 1] if start > 0 else ""
                after = line[end] if end < len(line) else ""
                if before == "`" and after == "`":
                    continue

                text_part = m.group(1)
                target = m.group(2)
                if (text_part, target) == _PLACEHOLDER_LINK:
                    continue  # generic "a markdown link looks like this" idiom

                if (rel_path.as_posix(), target) in _TEMPLATE_QUOTE_LINKS:
                    continue  # destination-relative insertion template; see module docstring

                if _URI_SCHEME_RE.match(target) or target.startswith("mailto:"):
                    continue  # external

                path_part, frag = _split_target(target)

                if path_part == "":
                    # Same-file fragment-only link, e.g. (#some-heading).
                    if frag:
                        if _github_slug_lookup(frag, slugs_of(abs_path)):
                            continue
                        violations.append(
                            Violation(rel_path, lineno, target, "anchor not found in this file")
                        )
                    continue

                resolved = (abs_path.parent / path_part).resolve()
                if not resolved.exists():
                    if _is_gitignored(resolved):
                        continue  # expected-absent user-data / ignored path
                    violations.append(Violation(rel_path, lineno, target, "target does not exist"))
                    continue

                if (
                    frag
                    and resolved.suffix.lower() == ".md"
                    and resolved.is_file()
                    and not _github_slug_lookup(frag, slugs_of(resolved))
                ):
                    violations.append(
                        Violation(rel_path, lineno, target, "anchor not found in target file")
                    )
                # Non-.md fragments (e.g. #L3404 GitHub line anchors) are
                # accepted without verification — see module docstring.

    return violations


def _github_slug_lookup(fragment: str, slugs: set[str]) -> bool:
    # Fragments in links are already GitHub-slug-shaped in this repo's
    # convention (lowercase, hyphenated); compare directly.
    return fragment in slugs


def check_cites(md_files: list[Path], tracked: set[str]) -> list[Violation]:
    violations: list[Violation] = []
    basename_index: dict[str, list[str]] = {}
    for t in tracked:
        basename_index.setdefault(Path(t).name, []).append(t)

    in_scope = [
        p
        for p in md_files
        if p.as_posix() in CITE_CHECK_FILES
        or any(p.as_posix().startswith(d) for d in CITE_CHECK_DIRS)
    ]

    for rel_path in in_scope:
        abs_path = REPO_ROOT / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()

        for lineno, line in _iter_unfenced_lines(lines):
            for m in _CITE_RE.finditer(line):
                cited_path = m.group(1)
                root_relative = REPO_ROOT / cited_path
                if root_relative.exists():
                    continue
                if Path(cited_path).name in basename_index:
                    continue  # resolvable by basename elsewhere in the tree
                violations.append(
                    Violation(
                        rel_path, lineno, f"{cited_path}:{m.group(2)}", "cited file not found"
                    )
                )

    return violations


def main() -> int:
    md_files = list_md_files()
    tracked = list_tracked_files()

    violations = check_links(md_files)
    violations += check_cites(md_files, tracked)

    if not violations:
        print(
            f"check_doc_links: OK — {len(md_files)} tracked markdown files, no broken links or cites."
        )
        return 0

    violations.sort(key=lambda v: (v.file.as_posix(), v.line))
    print(f"check_doc_links: FAILED — {len(violations)} broken link(s)/cite(s):\n")
    for v in violations:
        print(str(v))
    return 1


if __name__ == "__main__":
    sys.exit(main())

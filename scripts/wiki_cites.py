#!/usr/bin/env python3
"""Deterministic cite checker for `docs/wiki/` pages (item 166). Stdlib only, no LLM, no network.

**Why this exists.** The wiki loop (`/wiki-self-update`) pairs a Haiku scribe with a Haiku
auditor, and three consecutive passes (`docs/wiki/log.md`) show orchestrator review catching
what the auditor passed. Most of those misses were semantic and no script can catch them. A
few were mechanical: a line cite added against the convention, a cite the scribe removed
outside its brief, a symbol that the cited file does not contain. This is the check for the
mechanical class, so the human review is spent on the semantic one
(`docs/dev/diagnosis/recurrence-guardrails.md` O4).

**What it checks** (over `docs/wiki/pages/*.md`, `overview.md` and `index.md`; fenced code
blocks are skipped):

* **E1 line cites are ratcheted.** A `path.ext:123` / `path.ext:123-130` cite, or prose
  `line 123` / `lines 123-130` on the same or the preceding line as a code path, is a
  pointer that rots on the next edit
  (`docs/wiki/SCHEMA.md`: prefer a symbol). Existing ones are listed in `ALLOWED_LINE_CITES`
  with an exact per-page count: one more fails, and so does one fewer until the entry is
  lowered, which is what makes it a ratchet and not a grandfather clause.
* **E2 a line cite must point inside the file.** `path.ext:900` against a 400-line file is
  certainly wrong. No allowlist.
* **E3 a symbol cite must name something the file contains.** `[`foo`](../x.py)` and
  `x.py:foo` need `foo` (the last component of a dotted name) as a whole word in `x.py`.
  `ALLOWED_MISSING_SYMBOLS` holds reviewed exceptions, each with its reason.
* **E4 a removed cite is surfaced** (`--base REF`, and `--strict-removed` to fail on it). A
  symbol cite on the base page that is gone from the current page, while its file and symbol
  still exist, is what a scribe does when it overreaches its brief. It is not part of the
  merge gate: a deliberate removal there has no way through. The `/wiki-self-update` loop
  runs it, where the orchestrator is the reviewer who can restore the cite or log the removal.

**What it cannot check (C-0).** A `lines N-M` reference with no path on its own or the
preceding line is not seen. Nor is whether a sentence is *true*: a behavior claim on a branch the
code can take, an inverted effect, an intent, a UI placement, or a false piece of evidence. All
five were passed by the auditor and caught by review in the logged passes. The word-presence
check in E3 is also weaker than "this symbol is defined here": a name that merely occurs in a
comment passes.

Usage::

    python -m scripts.wiki_cites                        # E1-E3 over the tree; exit 1 on a hit
    python -m scripts.wiki_cites --base origin/main     # also list removed cites (E4)
    python -m scripts.wiki_cites --base HEAD --strict-removed
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = "docs/wiki"

#: Reviewed per-page counts of bare line cites that existed when the check was introduced
#: (item 166). Exact, in both directions. Lower an entry when a cite is converted to a symbol;
#: delete it at zero. `tests/test_wiki_cites.py` fails on a stale or over-count entry.
ALLOWED_LINE_CITES: dict[str, int] = {
    "docs/wiki/pages/diagnostics-console.md": 2,
    "docs/wiki/pages/document-rendering.md": 3,
    "docs/wiki/pages/education-degree-field-rendering.md": 12,
    "docs/wiki/pages/governance-extraction.md": 2,
    "docs/wiki/pages/non-dependency-downloads.md": 2,
    "docs/wiki/pages/openapi-api-reference.md": 1,
    "docs/wiki/pages/route-surface.md": 2,
}

#: `(page, "path:symbol") -> reason` for a symbol cite that is correct although the file does
#: not contain the name as a whole word (a computed attribute, say). Empty by default.
ALLOWED_MISSING_SYMBOLS: dict[tuple[str, str], str] = {}

#: Extensions whose files are checked for a cited symbol (E3).
_SYMBOL_EXTS = (".py", ".js", ".mjs", ".html", ".css", ".sh", ".toml", ".yml", ".yaml")
_PATH_EXT = r"(?:py|js|mjs|html|css|sh|toml|ya?ml|json|md)"

_COLON_RE = re.compile(
    rf"(?<![\w/.-])([A-Za-z0-9_][A-Za-z0-9_./-]*\.{_PATH_EXT}):"
    r"(\d+(?:\s*[-–]\s*\d+)?|[A-Za-z_][\w.]*(?:\(\))?)"
)
_LINK_RE = re.compile(r"\[(`?)([^\]`]+)\1\]\(([^)\s#]+)(?:#[^)]*)?\)")
_IDENT_RE = re.compile(r"^[A-Za-z_][\w.]*(?:\(\))?$")
#: A label that is itself a file name (`parser.py`) is a path label, not a symbol.
_FILENAME_LABEL_RE = re.compile(rf"\.{_PATH_EXT}$")
_LINE_TOKEN_RE = re.compile(r"^(\d+)(?:\s*[-–]\s*(\d+))?$")
_PROSE_LINE_RE = re.compile(r"\blines?\s+(\d+)(?:\s*[-–]\s*(\d+))?\b")
_PATHISH_RE = re.compile(rf"[A-Za-z0-9_][A-Za-z0-9_./-]*\.{_PATH_EXT}\b")


@dataclass(frozen=True)
class Cite:
    """One cite found on a page. `path` is the resolved repo path, or None if unresolved."""

    page: str
    lineno: int
    kind: str  # "line", "symbol" or "prose-line"
    path: str | None
    token: str  # the symbol, or the line spec as written

    @property
    def key(self) -> str:
        return f"{self.path or '?'}:{self.token}"


@dataclass(frozen=True)
class Violation:
    rule: str
    page: str
    lineno: int
    message: str

    def __str__(self) -> str:
        return f"{self.page}:{self.lineno}: {self.rule}: {self.message}"


class Tree:
    """The tracked files plus a read-once text cache, so each cited file is read at most once."""

    def __init__(self, tracked: Iterable[str], root: Path = REPO_ROOT) -> None:
        self.tracked = frozenset(tracked)
        self.root = root
        self._by_name: dict[str, list[str]] = {}
        for path in self.tracked:
            self._by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)
        self._text: dict[str, str | None] = {}

    def resolve_link(self, page: str, target: str) -> str | None:
        """A relative link target, as written on `page`, to a tracked repo path."""
        if "://" in target or target.startswith(("mailto:", "#")):
            return None
        joined = PurePosixPath(page).parent / target
        parts: list[str] = []
        for part in joined.parts:
            if part == "..":
                if not parts:
                    return None
                parts.pop()
            elif part != ".":
                parts.append(part)
        candidate = "/".join(parts)
        return candidate if candidate in self.tracked else None

    def resolve_bare(self, token: str) -> str | None:
        """A bare `path` cite: an exact repo path, else a unique `/`-anchored suffix match."""
        if token in self.tracked:
            return token
        hits = [
            p for p in self._by_name.get(token.rsplit("/", 1)[-1], []) if p.endswith("/" + token)
        ]
        return hits[0] if len(hits) == 1 else None

    def text(self, path: str) -> str | None:
        if path not in self._text:
            try:
                self._text[path] = (self.root / path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._text[path] = None
        return self._text[path]


def _unfenced_lines(text: str) -> Iterable[tuple[int, str]]:
    """`(1-based line number, line)` for every line outside a fenced code block."""
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def extract_cites(page: str, text: str, tree: Tree) -> list[Cite]:
    """Every checkable cite on `page`, de-duplicated within a line."""
    cites: list[Cite] = []
    previous = ""
    for number, line in _unfenced_lines(text):
        context, previous = f"{previous} {line}", line
        found: list[tuple[str, str | None, str]] = []  # (kind, resolved path, token)
        for match in _COLON_RE.finditer(line):
            path = tree.resolve_bare(match.group(1))
            token = match.group(2)
            if _LINE_TOKEN_RE.match(token):
                found.append(("line", path, re.sub(r"\s+", "", token)))
            else:
                found.append(("symbol", path, token.removesuffix("()")))
        for match in _LINK_RE.finditer(line):
            label, target = match.group(2).strip(), match.group(3)
            path = tree.resolve_link(page, target)
            if path is not None and _IDENT_RE.match(label) and not _FILENAME_LABEL_RE.search(label):
                found.append(("symbol", path, label.removesuffix("()")))
        # A wrapped sentence puts `(lines 9-12)` on the line after the path, so the path may
        # be on this line or the one before it.
        if _PATHISH_RE.search(context):
            for match in _PROSE_LINE_RE.finditer(line):
                spec = match.group(1) + (f"-{match.group(2)}" if match.group(2) else "")
                found.append(("prose-line", None, spec))
        # `dict.fromkeys` de-duplicates within the line and keeps first-seen order.
        cites.extend(
            Cite(page, number, kind, path, token) for kind, path, token in dict.fromkeys(found)
        )
    return cites


def _has_word(text: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None


def check_page(page: str, text: str, tree: Tree) -> tuple[list[Violation], int]:
    """E2 and E3 violations for one page, and the page's count of bare line cites (E1 input)."""
    violations: list[Violation] = []
    line_cites = 0
    for cite in extract_cites(page, text, tree):
        if cite.kind in ("line", "prose-line"):
            line_cites += 1
        if cite.path is None:
            continue
        body = tree.text(cite.path)
        if body is None:
            continue
        if cite.kind == "line":
            matched = _LINE_TOKEN_RE.match(cite.token)
            if matched:
                last = int(matched.group(2) or matched.group(1))
                total = len(body.splitlines())
                if last > total:
                    violations.append(
                        Violation(
                            "E2",
                            page,
                            cite.lineno,
                            f"{cite.path}:{cite.token} is past the end of the file ({total} lines)",
                        )
                    )
        elif cite.kind == "symbol" and cite.path.endswith(_SYMBOL_EXTS):
            name = cite.token.rsplit(".", 1)[-1]
            if not _has_word(body, name) and (page, cite.key) not in ALLOWED_MISSING_SYMBOLS:
                violations.append(
                    Violation(
                        "E3",
                        page,
                        cite.lineno,
                        f"{cite.path} does not contain {name!r} (cited as {cite.token!r})",
                    )
                )
    return violations, line_cites


def ratchet(counts: Mapping[str, int], allowed: Mapping[str, int]) -> list[Violation]:
    """E1: exact per-page counts, in both directions."""
    out: list[Violation] = []
    for page in sorted(set(counts) | set(allowed)):
        have, may = counts.get(page, 0), allowed.get(page, 0)
        if have > may:
            out.append(
                Violation(
                    "E1",
                    page,
                    0,
                    f"{have} bare line cite(s), {may} allowed: cite a symbol "
                    "(or a heading) instead of a line number",
                )
            )
        elif have < may:
            out.append(
                Violation(
                    "E1",
                    page,
                    0,
                    f"{have} bare line cite(s) but ALLOWED_LINE_CITES says {may}: lower the "
                    "entry (a ratchet only tightens)",
                )
            )
    return out


def wiki_pages(tracked: Iterable[str]) -> list[str]:
    """The pages this check covers: `pages/*.md`, `overview.md` and `index.md`."""
    keep = {f"{WIKI_DIR}/overview.md", f"{WIKI_DIR}/index.md"}
    return sorted(
        p
        for p in tracked
        if p in keep or (p.startswith(f"{WIKI_DIR}/pages/") and p.endswith(".md"))
    )


def check_tree(
    tree: Tree, pages: Iterable[str] | None = None
) -> tuple[list[Violation], Counter[str]]:
    """E1-E3 over the tracked wiki pages. Returns the violations and the per-page line counts."""
    violations: list[Violation] = []
    counts: Counter[str] = Counter()
    for page in pages if pages is not None else wiki_pages(tree.tracked):
        text = tree.text(page)
        if text is None:
            continue
        page_violations, line_cites = check_page(page, text, tree)
        violations.extend(page_violations)
        if line_cites:
            counts[page] = line_cites
    violations.extend(ratchet(counts, ALLOWED_LINE_CITES))
    return violations, counts


def removed_symbol_cites(
    page: str, base_text: str, current_text: str, tree: Tree
) -> list[Violation]:
    """E4: symbol cites on the base page that are gone now though file and symbol still exist."""
    now = {c.key for c in extract_cites(page, current_text, tree) if c.kind == "symbol"}
    out: list[Violation] = []
    reported: set[str] = set()
    for cite in extract_cites(page, base_text, tree):
        if cite.kind != "symbol" or cite.path is None or cite.key in now or cite.key in reported:
            continue
        body = tree.text(cite.path)
        if body is None or not _has_word(body, cite.token.rsplit(".", 1)[-1]):
            continue  # the target is gone: removing the cite is the right edit
        reported.add(cite.key)
        out.append(Violation("E4", page, cite.lineno, f"cite {cite.key} was removed"))
    return out


def _git(args: list[str]) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    parser.add_argument("--base", help="compare against this ref and list removed symbol cites")
    parser.add_argument(
        "--strict-removed", action="store_true", help="exit 1 when a cite was removed (E4)"
    )
    parser.add_argument("--summary", action="store_true", help="print per-page line-cite counts")
    args = parser.parse_args(argv)

    tracked = [line for line in _git(["ls-files"]).splitlines() if line.strip()]
    tree = Tree(tracked)
    violations, counts = check_tree(tree)
    removed: list[Violation] = []
    if args.base:
        changed = _git(["diff", "--name-only", args.base, "--", f"{WIKI_DIR}/"]).splitlines()
        for page in wiki_pages(changed):
            if page not in tree.tracked:
                continue
            try:
                base_text = _git(["show", f"{args.base}:{page}"])
            except RuntimeError:
                continue  # a new page has no base
            current = tree.text(page)
            if current is not None:
                removed.extend(removed_symbol_cites(page, base_text, current, tree))
    if args.summary:
        for page, count in sorted(counts.items()):
            print(f"{count:3d}  {page}")
    for violation in [*violations, *removed]:
        print(violation)
    failed = bool(violations) or (args.strict_removed and bool(removed))
    print(
        f"wiki_cites: {'FAILED' if failed else 'OK'} "
        f"({len(violations)} violation(s), {len(removed)} removed cite(s) listed)"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

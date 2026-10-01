#!/usr/bin/env python3
"""The shared doc corpus: tracked paths, file text and unfenced lines, each computed once.

`docs/dev/docs-ia-design.md` §5 (intro) specifies one shared pass for every doc lint instead
of one scan per lint. This module is that pass. `check_doc_links.py`,
`check_doc_frontmatter.py`, `check_doc_single_home.py` and the §5 lints in
`scripts/doc_lints.py` all read through a `DocCorpus`.

**Lazy by default.** Nothing is listed or read at construction. Each property or file is
computed on first use and cached, so a lint scoped to the 39 registered docs never pays for
the repo-wide `git ls-files`, and a registry-only checker never reads the other ~540 files.

**Link targets are answered lexically.** `exists()` normalizes a repo-relative path with
`posixpath.normpath` and looks it up in the tracked set (files, plus every directory that
holds one). The profile in the D4 dossier (`docs/dev/blast-radius/docs-assets-enforcement.md`,
step 1 addendum) put ~5.7 s of an 8.5 s link check in per-link `Path.resolve()` +
`Path.exists()`. Only a miss touches the filesystem: an untracked-but-present file still
counts as existing (so a doc linking a new file before `git add` is not a false failure), and
the caller decides about gitignored paths. That keeps the old checker's answers exactly.

**Deleted-but-indexed files.** `git ls-files` lists index entries, including ones deleted in
the working tree. Those are subtracted from the tracked set (`git ls-files --deleted`), so a
link to a file that is gone from disk still fails, as it did with `Path.exists()`.

Stdlib only, no I/O at import.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
from collections.abc import Iterator
from functools import cached_property
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")


def iter_unfenced(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (1-based lineno, line) for lines NOT inside a fenced code block."""
    in_fence = False
    fence_char = None
    for lineno, line in enumerate(lines, start=1):
        m = FENCE_RE.match(line)
        if m:
            char = m.group(2)[0]
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


class DocCorpus:
    """One repo's tracked docs, read at most once each. Paths are repo-relative POSIX strings."""

    def __init__(self, root: Path = REPO_ROOT) -> None:
        self.root = root
        self._text: dict[str, str] = {}
        self._unfenced: dict[str, list[tuple[int, str]]] = {}

    def _git(self, *args: str) -> list[str]:
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
            ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]

    @cached_property
    def index_paths(self) -> list[str]:
        """Every path in the git index, in `git ls-files` order (one subprocess)."""
        return self._git("ls-files")

    @cached_property
    def md_paths(self) -> list[str]:
        """Every indexed `*.md` path, the same list `git ls-files '*.md'` prints."""
        return [p for p in self.index_paths if p.endswith(".md")]

    @cached_property
    def tracked(self) -> frozenset[str]:
        """Indexed files that are present in the working tree."""
        deleted = set(self._git("ls-files", "--deleted"))
        return frozenset(p for p in self.index_paths if p not in deleted)

    @cached_property
    def tracked_dirs(self) -> frozenset[str]:
        """Every directory that holds at least one tracked file (no trailing slash)."""
        dirs: set[str] = set()
        for path in self.tracked:
            parent = posixpath.dirname(path)
            while parent and parent not in dirs:
                dirs.add(parent)
                parent = posixpath.dirname(parent)
        return frozenset(dirs)

    def read(self, path: str) -> str:
        """The file's text, read once. Raises OSError like `Path.read_text`."""
        text = self._text.get(path)
        if text is None:
            text = (self.root / path).read_text(encoding="utf-8")
            self._text[path] = text
        return text

    def lines(self, path: str) -> list[str]:
        return self.read(path).splitlines()

    def unfenced(self, path: str) -> list[tuple[int, str]]:
        """(lineno, line) pairs outside fenced code blocks, computed once per file."""
        cached = self._unfenced.get(path)
        if cached is None:
            cached = list(iter_unfenced(self.lines(path)))
            self._unfenced[path] = cached
        return cached

    def head(self, path: str, chars: int) -> str:
        return self.read(path)[:chars]

    @staticmethod
    def join(src: str, target: str) -> str:
        """Resolve `target` as written in file `src`, lexically. '' means the repo root."""
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(src), target))
        return "" if joined == "." else joined

    def kind(self, path: str) -> str | None:
        """'file', 'dir' or None. Lexical first; the filesystem only on a miss."""
        if path in self.tracked:
            return "file"
        if path == "" or path in self.tracked_dirs:
            return "dir"
        full = self.root / path
        if full.is_file():
            return "file"
        if full.exists():
            return "dir"
        return None

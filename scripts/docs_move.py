#!/usr/bin/env python3
"""Move docs and rewrite live links to them, in one scripted step (Epic D sprint D2).

**Why this exists.** `docs/dev/docs-ia-design.md` §3 is the link policy for moving docs:
- live docs are rewritten by script, in the same commit as the move, with no hand-edited link
  rewrites
- records are never rewritten; their links to moved docs resolve through the moved-paths map
  that `scripts/check_doc_links.py` consults

When `vision.md` moved without a script, about 490 references broke (`RELEASE_ARC.md` §"Epic
D"). This script makes the move and the rewrite one operation.

**What it does**, driven by `MOVES` (old repo path → new repo path, design §2.1/§2.2 as data):
1. Reads every live tracked `*.md` once. Live means not a record per
   `doc_registry.is_record`, judged by the file's path *after* the move. In each file it
   rewrites:
   - relative markdown link and image targets that resolve to a moved path, or whose source
     file itself moved
   - exact repo-relative path strings (for example `` `docs/install.md` ``) that name a moved
     path

   Bare basenames (`install.md`) are ambiguous, so they are left alone. Links immediately
   wrapped in backticks and links in fenced code are sample text (the same rule
   `check_doc_links.py` uses), so they are also left alone. Exact paths inside fences are
   current-state references and are rewritten.
2. `git mv`s every entry in `MOVES`.
3. Inserts the one-time archive banner into each file moved into `docs/dev/archive/`. This is
   the only edit an archived record gets, so its links stay as they were written, and
   `check_doc_links.py` resolves them against the file's old directory.
4. Writes `docs/dev/moved-paths.json` (old → new, sorted), merged with any existing map.
5. Reports, without rewriting, exact old-path mentions in tracked non-markdown files, for the
   C-10 dossier to decide by hand.

`--dry-run` (the default) prints the plan and every rewrite, and touches nothing. `--apply`
acts. Stdlib only. The file pass is O(files × links), with a dict lookup per link.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from doc_registry import is_record

REPO_ROOT = Path(__file__).resolve().parent.parent
MOVED_PATHS_FILE = "docs/dev/moved-paths.json"
ARCHIVE_DIR = "docs/dev/archive/"

_ARCHIVED = (
    "COMPOSE_REWRITE_DIAL",
    "app-blueprints-design",
    "avatar-voice-tone-guidance",
    "avatar-citation-format-guidance",
    "board-forge-sync-review",
    "gate-window-class-study",
    "governance-extraction-design",
    "kit-adoption-design",
    "pagedjs-preview-spike",
    "self-documenting-loop-design",
    "generation-experience-rearchitecture",
    "dependency-triage-pre-v1.1.0",
    "ORCHESTRATION_PLAYBOOK",
    "V1_0_5_VERIFICATION",
    "window-8.5-findings",
    "window-8.5-walkthrough",
)

# Design §2.1 (live moves) + §2.2 (archive moves; owner decisions O-3/O-3a, 2026-09-28).
MOVES: dict[str, str] = {
    "docs/install.md": "docs/user/install.md",
    "docs/walkthrough.md": "docs/user/walkthrough.md",
    "docs/walkthrough_example.md": "docs/user/walkthrough-example.md",
    "docs/template_authoring.md": "docs/user/templates.md",
    "docs/architecture.md": "docs/dev/architecture.md",
    "docs/system-model.md": "docs/dev/system-model.md",
    "docs/PRODUCT_SHAPE.md": "docs/dev/PRODUCT_SHAPE.md",
    "docs/ux/screenshot_capture.md": "docs/dev/screenshot-capture.md",
    **{f"docs/dev/{name}.md": f"{ARCHIVE_DIR}{name}.md" for name in _ARCHIVED},
}

ARCHIVE_BANNER = (
    "> **Archived 2026-09-28 (Epic D, D2).** A historical record kept for its rationale, and no\n"
    "> longer maintained. Its links are as they were when it was written; see\n"
    "> [`docs/dev/moved-paths.json`](../moved-paths.json) for where moved docs went.\n"
)

# Same link shape `check_doc_links.py` validates (images included — they move with docs).
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
_URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
_H1_RE = re.compile(r"^#\s")


def _exact_path_re(paths: list[str]) -> re.Pattern[str]:
    # A path mention bounded so `docs/architecture.md` never matches inside
    # `docs/dev/architecture.md` or `mydocs/architecture.md`.
    alternation = "|".join(re.escape(p) for p in sorted(paths, key=len, reverse=True))
    return re.compile(rf"(?<![\w./-])(?:{alternation})(?![\w])")


@dataclass
class FileRewrite:
    """The planned edit to one live markdown file."""

    path_before: str
    path_after: str
    changes: list[str] = field(default_factory=list)
    new_text: str = ""


def _in_backticks(line: str, start: int, end: int) -> bool:
    # The exact skip rule `check_doc_links.check_links` uses: a link immediately wrapped in
    # backticks is a quoted example. Anything it checks, this rewrites, and vice versa.
    return start > 0 and line[start - 1] == "`" and end < len(line) and line[end] == "`"


def rewrite_link_target(
    target: str, src_before: str, src_after: str, moves: Mapping[str, str]
) -> str | None:
    """The new relative target for one link, or None when it needs no change.

    `target` is resolved against the source's OLD directory (that's where it was written),
    mapped through `moves`, then re-expressed relative to the source's NEW directory.
    """
    if target.startswith(("#", "/")) or _URI_SCHEME_RE.match(target):
        return None
    path_part, sep, fragment = target.partition("#")
    if not path_part:
        return None
    trailing_slash = path_part.endswith("/")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(src_before), path_part))
    if resolved.startswith("../"):
        return None  # escapes the repo — not ours
    new_resolved = moves.get(resolved, resolved)
    if new_resolved == resolved and src_before == src_after:
        return None
    new_rel = posixpath.relpath(new_resolved, posixpath.dirname(src_after) or ".")
    if trailing_slash and not new_rel.endswith("/"):
        new_rel += "/"
    new_target = new_rel + (sep + fragment if sep else "")
    return None if new_target == target else new_target


def rewrite_text(
    text: str, src_before: str, src_after: str, moves: Mapping[str, str]
) -> tuple[str, list[str]]:
    """Rewrite one live doc's links and exact path mentions. Returns (text, change notes)."""
    exact_re = _exact_path_re(list(moves))
    changes: list[str] = []
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for lineno, line in enumerate(text.split("\n"), start=1):
        m = _FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if not in_fence:
                in_fence, fence_marker = True, marker[:3]
            elif marker.startswith(fence_marker):
                in_fence, fence_marker = False, ""
        elif not in_fence:

            def _link(match: re.Match[str], ln: str = line, n: int = lineno) -> str:
                if _in_backticks(ln, match.start(), match.end()):
                    return match.group(0)
                new = rewrite_link_target(match.group(2), src_before, src_after, moves)
                if new is None:
                    return match.group(0)
                changes.append(f"{n}: link {match.group(2)} -> {new}")
                return f"[{match.group(1)}]({new})"

            line = _LINK_RE.sub(_link, line)

        def _exact(match: re.Match[str], n: int = lineno) -> str:
            new = moves[match.group(0)]
            changes.append(f"{n}: path {match.group(0)} -> {new}")
            return new

        line = exact_re.sub(_exact, line)
        out.append(line)
    return "\n".join(out), changes


def insert_archive_banner(text: str) -> str:
    """Insert `ARCHIVE_BANNER` after the first H1 (or at the top when there is none)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if _H1_RE.match(line):
            return "\n".join([*lines[: i + 1], "", ARCHIVE_BANNER, *lines[i + 1 :]])
    return ARCHIVE_BANNER + "\n" + text


def _git(*args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def _tracked(pattern: str | None = None) -> list[str]:
    args = ["ls-files", "-z"] + ([pattern] if pattern else [])
    return [p for p in _git(*args).split("\0") if p]


def plan_rewrites(moves: Mapping[str, str]) -> list[FileRewrite]:
    """Every live markdown file that needs an edit, with its new text."""
    plans: list[FileRewrite] = []
    for before in _tracked("*.md"):
        after = moves.get(before, before)
        if is_record(after):
            continue
        text = (REPO_ROOT / before).read_text(encoding="utf-8")
        new_text, changes = rewrite_text(text, before, after, moves)
        if changes:
            plans.append(FileRewrite(before, after, changes, new_text))
    return plans


def non_markdown_mentions(moves: Mapping[str, str]) -> Iterator[str]:
    """`path:line: old-path` for each exact old-path mention in a tracked non-markdown file."""
    exact_re = _exact_path_re(list(moves))
    for path in _tracked():
        if path.endswith(".md") or path == MOVED_PATHS_FILE:
            continue
        try:
            text = (REPO_ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — no path mentions to report
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in exact_re.finditer(line):
                yield f"{path}:{lineno}: {m.group(0)}"


def apply(moves: Mapping[str, str], plans: list[FileRewrite]) -> None:
    """Perform the moves, write the rewrites and banners, and update the moved-paths map."""
    missing = [old for old in moves if not (REPO_ROOT / old).is_file()]
    if missing:
        raise SystemExit(f"docs_move: FAILED — sources missing: {missing}")
    for new in moves.values():
        (REPO_ROOT / new).parent.mkdir(parents=True, exist_ok=True)
    # One `git mv` per destination directory keeps the subprocess count to a handful.
    by_dir: dict[str, list[tuple[str, str]]] = {}
    for old, new in moves.items():
        by_dir.setdefault(posixpath.dirname(new), []).append((old, new))
    for pairs in by_dir.values():
        renames = [(o, n) for o, n in pairs if posixpath.basename(o) != posixpath.basename(n)]
        same_name = [o for o, n in pairs if posixpath.basename(o) == posixpath.basename(n)]
        if same_name:
            _git("mv", *same_name, posixpath.dirname(pairs[0][1]) + "/")
        for old, new in renames:
            _git("mv", old, new)

    for plan in plans:
        (REPO_ROOT / plan.path_after).write_text(plan.new_text, encoding="utf-8", newline="")
    for new in moves.values():
        if new.startswith(ARCHIVE_DIR):
            path = REPO_ROOT / new
            path.write_text(
                insert_archive_banner(path.read_text(encoding="utf-8")),
                encoding="utf-8",
                newline="",
            )

    map_path = REPO_ROOT / MOVED_PATHS_FILE
    existing: dict[str, str] = (
        json.loads(map_path.read_text(encoding="utf-8")) if map_path.is_file() else {}
    )
    merged = {**existing, **moves}
    map_path.write_text(
        json.dumps(dict(sorted(merged.items())), indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--apply", action="store_true", help="act (default: dry run)")
    args = parser.parse_args(argv)

    plans = plan_rewrites(MOVES)
    print(f"docs_move: {len(MOVES)} moves")
    for old, new in MOVES.items():
        print(f"  {old} -> {new}")
    total = sum(len(p.changes) for p in plans)
    print(f"docs_move: {total} rewrite(s) in {len(plans)} live markdown file(s)")
    for plan in plans:
        label = plan.path_before
        if plan.path_after != plan.path_before:
            label += f" (-> {plan.path_after})"
        print(f"  {label}")
        for change in plan.changes:
            print(f"    {change}")
    mentions = list(non_markdown_mentions(MOVES))
    print(f"docs_move: {len(mentions)} old-path mention(s) in non-markdown files (not rewritten)")
    for mention in mentions:
        print(f"  {mention}")

    if args.apply:
        apply(MOVES, plans)
        print("docs_move: applied.")
    else:
        print("docs_move: dry run; nothing changed (pass --apply to act).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

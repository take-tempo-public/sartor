#!/usr/bin/env python3
"""Deterministic, stdlib-only L1 -> Fumadocs MDX projection adapter.

**Why this exists.** Per `docs/dev/documentation-architecture.md`, the hosted
Fumadocs site (L3) must be a *pure projection* of the governed L1 source —
never a second source of truth. This script is that projection: it reads the
L1 doc set (see "Scope" below) at the current git working tree, converts each
page's existing `Purpose / Audience / Authoritative-for` blockquote header
(the SAME convention every L1 doc already carries) into MDX frontmatter, and
writes the MDX content tree + a `meta.json` under `docs-site/content/docs/`.
No LLM, no new Python dependency, stdlib only — a build step, not synthesis.

**Scope — the publication registry.** A doc is projected if and only if it is
listed in `scripts/doc_registry.py` `PUBLISHED` (`docs/dev/docs-ia-design.md`
§5.1, pulled into Epic D sprint D2). Before the registry, any tracked `.md` with
a full Purpose/Audience/Authoritative-for header was projected, which put handoff
briefs, a diagnosis dossier, reviews and perf records on the site. A registered
doc must still carry the full header (it supplies the frontmatter); one that
doesn't is a build-stopping error here and a gate failure in
`scripts/check_doc_frontmatter.py`.

**The frontmatter map (documentation-architecture.md "Fumadocs sourcing").**

| Header line            | -> frontmatter        | Drives                          |
|-------------------------|------------------------|----------------------------------|
| `**Purpose:**`          | `description`         | page identity / SEO description |
| (first `# H1` heading)  | `title`                | page identity                   |
| `**Audience:**`         | `audience: [...]`      | which ICP front door it appears under |
| `**Authoritative for:**`| `authoritativeFor`     | the canonical-home marker       |

**Audience tier and nav order come from the registry.** Each entry's `tier`
(`user`/`dev`) sets the page's `audience` frontmatter, and `meta.json`'s `pages`
array is `index`, a "Using Sartor" separator, the user-tier pages, a "Building on
Sartor" separator, then the dev-tier pages, each in registry order. The old
path fallback table and the README "Documentation map" parse are gone: one
definition, not three (design §5.1/§5.2).

**MDX safety escaping.** MDX compiles markdown through an (S)JSX-ish parser:
a bare `<` outside a fenced code block / inline code span looks like a tag
open and can fail the build (several L1 docs use inline placeholders like
`<username>` in prose); a raw `<!-- -->` HTML comment fails outright (MDX
has no HTML-comment syntax). `escape_mdx_unsafe()` (`_MdxEscaper`) is a
fence/inline-code-aware state machine that: HTML-entity escapes stray `<`
and bare `{`/`}` in plain prose; rewrites `<!-- ... -->` to MDX's own
`{/* ... */}` comment form (see the class docstring — this is the one place
the projection changes syntax, not just escapes it, to keep e.g. the README
`DOC-STATUS` markers invisible on the rendered site); and leaves fenced code
blocks and inline code spans byte-identical.

**Local images.** MDX rewrites markdown `![alt](relative.png)` into a static
`import`, resolved relative to the MDX file's own directory — so a
referenced local image must physically exist next to the projected page or
the Next.js build fails with `Module not found`. The user-tier
walkthrough and install docs reference `docs/screenshots/*.png` this way. Because every
projected page lives flat in `docs-site/content/docs/`, this script mirrors
those referenced images (byte-copy, unchanged filenames — no link rewrite
needed) into a shared `docs-site/content/docs/screenshots/` directory that
sits alongside them; a same-basename collision from two different source
paths is a build-stopping error, not a silent overwrite.

**Cross-doc links are rewritten (2026-07-13).** This was originally a documented
non-goal — the SOURCE docs stay plain markdown that degrades correctly on GitHub
(`documentation-architecture.md` "Portability"), so links were projected
byte-identical. The consequence only became visible once the site was public:
`/docs/vision.md` is not a route, so ~490 cross-references across 33 of 35 pages
404'd. The rewrite pass (see `rewrite_cross_doc_links`) resolves that WITHOUT
touching the source: a link to a projected doc becomes its site route, and a link
to anything the site doesn't carry becomes a GitHub URL. It is a pure function of
this script's own slug map, so it cannot invent a route.

**Non-goals (deliberate, documented — not oversights).**
- No L2 (`docs/wiki/**`) content — that is Search/"Ask" territory, not
  this static projection (this lane ships a static export only).

Exit 0 on success, printing a one-line summary. Exit 1 when a registered doc
is missing or lacks the full header.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from doc_registry import PUBLISHED, Entry

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "docs-site" / "content" / "docs"

_GENERATED_BANNER = (
    "{/* GENERATED by scripts/project_docs_to_mdx.py — do not hand-edit. "
    "Edit the cited source doc and re-run the projection. */}\n"
)

# Item 126: this output directory is gitignored, so a local copy can be months old and still
# look like the live site. Every page carries the commit it was projected from, in its
# frontmatter (`sourceCommit`) and in a visible comment. `scripts/check_docs_projection_fresh.py`
# compares the stamp to HEAD.
DIRTY_SUFFIX = "+uncommitted"


def source_commit(entries: tuple[Entry, ...] = PUBLISHED) -> str:
    """HEAD's full SHA, with `+uncommitted` when a registered source has local edits (the
    projection reads the working tree, so that projection matches no commit). `unknown`
    outside a git checkout. Two git calls per projection run, not per page."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 - `git` resolved from PATH
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain", "--", *(e.path for e in entries)],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + DIRTY_SUFFIX if dirty else head


def generated_banner(commit: str | None) -> str:
    if commit is None:
        return _GENERATED_BANNER
    return _GENERATED_BANNER + f"{{/* Projected from commit {commit}. */}}\n"


# ---------------------------------------------------------------------------
# Header parsing (Purpose / Audience / Authoritative for)
# ---------------------------------------------------------------------------

_HEADER_START_RE = re.compile(r"^> \*\*Purpose:\*\*")
_HEADER_LABEL_RE = re.compile(r"\*\*([A-Za-z][A-Za-z0-9 /'\-]*):\*\*")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
_WS_RE = re.compile(r"\s+")

REQUIRED_FIELDS = ("Purpose", "Audience", "Authoritative for")


class ProjectionError(Exception):
    """A registered doc can't be projected (missing or lacking the full header)."""


def find_header_block(lines: list[str]) -> list[str]:
    """The contiguous `> `-prefixed block starting at the `**Purpose:**` line."""
    start = None
    for i, line in enumerate(lines):
        if line.startswith(">") and _HEADER_START_RE.match(line):
            start = i
            break
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start:]:
        if not line.startswith(">"):
            break
        block.append(line)
    return block


def parse_header_fields(lines: list[str]) -> dict[str, str]:
    """Parse the Purpose/Audience/Authoritative-for (etc.) labeled fields from a doc's header."""
    block = find_header_block(lines)
    if not block:
        return {}
    # Strip the leading "> " (or bare ">") from each line, then rejoin so a
    # field's value can span multiple continuation lines.
    stripped = []
    for line in block:
        rest = line[1:]
        stripped.append(rest[1:] if rest.startswith(" ") else rest)
    text = "\n".join(stripped)

    matches = list(_HEADER_LABEL_RE.finditer(text))
    fields: dict[str, str] = {}
    for idx, m in enumerate(matches):
        label = m.group(1).strip()
        value_start = m.end()
        value_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        value = _WS_RE.sub(" ", text[value_start:value_end]).strip()
        # Only keep the FIRST occurrence of a label (headers don't repeat one).
        fields.setdefault(label, value)
    return fields


def has_full_header(fields: dict[str, str]) -> bool:
    return all(k in fields and fields[k] for k in REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# Slug + title
# ---------------------------------------------------------------------------


def make_slug(rel_posix: str) -> str:
    """Deterministic, flat, globally-unique slug from a repo-relative .md path."""
    if rel_posix == "README.md":
        return "index"
    stem = rel_posix[:-3] if rel_posix.endswith(".md") else rel_posix
    if stem.startswith("docs/"):
        stem = stem[len("docs/") :]
    return stem.replace("/", "-").replace("_", "-").lower()


def first_h1(lines: list[str]) -> str | None:
    for line in lines:
        m = _H1_RE.match(line)
        if m:
            return m.group(1).strip()
    return None


def strip_first_h1(lines: list[str]) -> list[str]:
    """Drop the first H1 line (Fumadocs renders `title` from frontmatter as the H1)."""
    out = list(lines)
    for i, line in enumerate(out):
        if _H1_RE.match(line):
            del out[i]
            # Also drop one immediately-following blank line, if present.
            if i < len(out) and out[i].strip() == "":
                del out[i]
            break
    return out


# ---------------------------------------------------------------------------
# MDX-safety escaping
# ---------------------------------------------------------------------------

_HTML_COMMENT_START = "<!--"
_HTML_COMMENT_END = "-->"
_MDX_COMMENT_OPEN = "{/*"
_MDX_COMMENT_CLOSE = " */}"


def _escape_prose_segment(segment: str) -> str:
    return segment.replace("<", "&lt;").replace("{", "&#123;").replace("}", "&#125;")


def _sanitize_comment_body(text: str) -> str:
    # Defuse a literal "*/" inside the comment body, which would otherwise
    # early-close the MDX `{/* ... */}` comment it's being rewritten into.
    return text.replace("*/", "* /")


class _MdxEscaper:
    """A small single-pass state machine over the WHOLE document (state carries
    across lines) with three states: fenced code block, HTML comment (being
    REWRITTEN to an MDX comment — see below), and plain prose (the default).
    Inline code spans (`` `...` ``) are detected within a single line
    (CommonMark inline code doesn't meaningfully wrap across a line in this
    corpus). Fenced code and inline code spans pass through byte-identical.

    **HTML comments are rewritten, not merely protected.** MDX has no concept
    of a raw HTML comment (`<!-- ... -->` is invalid MDX/JSX — `<!` isn't a
    valid tag-name start) — despite `documentation-architecture.md`'s
    "Plain markdown (GitHub + Fumadocs both hide it)" claim for the
    `DOC-STATUS` convention, a bare `<!-- -->` fails the Fumadocs MDX build.
    The nearest honest equivalent that keeps the marker invisible on the
    rendered site (matching the intent, if not the literal syntax) is MDX's
    own comment form, `{/* ... */}` — so `<!--`/`-->` are rewritten to
    `{/*`/` */}` and the body is scanned for a literal `*/` that would
    otherwise close the MDX comment early."""

    def __init__(self) -> None:
        self.in_fence = False
        self.fence_char: str | None = None
        self.in_comment = False

    def process_lines(self, lines: list[str]) -> list[str]:
        return [self._process_line(line) for line in lines]

    def _process_line(self, line: str) -> str:
        if not self.in_comment:
            m = _FENCE_RE.match(line)
            if m:
                char = m.group(2)[0]
                if not self.in_fence:
                    self.in_fence = True
                    self.fence_char = char
                elif char == self.fence_char:
                    self.in_fence = False
                    self.fence_char = None
                return line  # fence marker line itself, untouched
        if self.in_fence:
            return line
        return self._scan_prose_line(line)

    def _scan_prose_line(self, line: str) -> str:
        out: list[str] = []
        i = 0
        n = len(line)
        while i < n:
            if self.in_comment:
                end_idx = line.find(_HTML_COMMENT_END, i)
                if end_idx == -1:
                    out.append(_sanitize_comment_body(line[i:]))
                    i = n
                else:
                    out.append(_sanitize_comment_body(line[i:end_idx]))
                    out.append(_MDX_COMMENT_CLOSE)
                    i = end_idx + len(_HTML_COMMENT_END)
                    self.in_comment = False
                continue

            comment_idx = line.find(_HTML_COMMENT_START, i)
            backtick_idx = line.find("`", i)
            candidates = [x for x in (comment_idx, backtick_idx) if x != -1]
            if not candidates:
                out.append(_escape_prose_segment(line[i:]))
                i = n
                continue

            nxt = min(candidates)
            out.append(_escape_prose_segment(line[i:nxt]))

            if nxt == comment_idx:
                out.append(_MDX_COMMENT_OPEN)
                i = nxt + len(_HTML_COMMENT_START)
                self.in_comment = True
                continue

            # Inline code span: a run of backticks, closed by an equal-length
            # run later on the SAME line. If unclosed on this line, fall back
            # to escaping it as prose (safe default) and keep scanning.
            j = nxt
            while j < n and line[j] == "`":
                j += 1
            run_len = j - nxt
            fence_marker = "`" * run_len
            close_idx = line.find(fence_marker, j)
            if close_idx == -1:
                out.append(_escape_prose_segment(line[nxt:j]))
                i = j
            else:
                end = close_idx + run_len
                out.append(line[nxt:end])  # whole inline code span, untouched
                i = end
        return "".join(out)


def escape_mdx_unsafe(lines: list[str]) -> list[str]:
    """Fence/inline-code/HTML-comment-aware MDX-safety escaper — see `_MdxEscaper`."""
    return _MdxEscaper().process_lines(lines)


# ---------------------------------------------------------------------------
# Local images — MDX rewrites `![alt](relative.png)` into a static `import`
# resolved relative to the MDX file's own directory, so a referenced local
# image must physically sit next to the projected page.
# ---------------------------------------------------------------------------

_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SCREENSHOTS_DIR = CONTENT_DIR / "screenshots"


def find_local_image_targets(lines: list[str]) -> list[str]:
    """Relative image paths referenced via `![alt](path)`, excluding remote URLs."""
    targets: list[str] = []
    for line in lines:
        for m in _IMAGE_RE.finditer(line):
            target = m.group(1)
            if target.startswith(("http://", "https://", "data:")):
                continue
            targets.append(target)
    return targets


def rewrite_local_images(rel_posix: str, lines: list[str]) -> list[str]:
    """Point each local image at the copy `copy_local_images` makes, `./screenshots/<name>`.

    The source keeps the path that works on GitHub, relative to its own directory, which
    for a doc under `docs/user/` is `../screenshots/x.png`. Every projected page sits flat
    in `content/docs/`, so that path resolved outside it and broke the site build (D4,
    observed: 10 "Module not found" errors). The basename-collision guard in
    `copy_local_images` keeps `screenshots/<name>` unambiguous. Lines inside fenced code
    are left alone: an image there is an example, not a reference.
    """
    doc_dir = (REPO_ROOT / rel_posix).parent

    def _point_at_copy(m: re.Match[str]) -> str:
        target = m.group(1)
        if target.startswith(("http://", "https://", "data:")):
            return m.group(0)
        source = (doc_dir / target).resolve()
        if not source.is_file():
            return m.group(0)
        whole, offset = m.group(0), m.start(0)
        start, end = m.start(1) - offset, m.end(1) - offset
        return whole[:start] + f"./screenshots/{source.name}" + whole[end:]

    out: list[str] = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        if in_fence or "![" not in line:
            out.append(line)
            continue
        out.append(_IMAGE_RE.sub(_point_at_copy, line))
    return out


def resolve_local_images(rel_posix: str, lines: list[str]) -> list[Path]:
    """Resolve each local image target (relative to the SOURCE doc's own
    directory, per markdown convention) to an absolute Path; skip targets that
    don't exist on disk (nothing to copy, nothing to break)."""
    doc_dir = (REPO_ROOT / rel_posix).parent
    resolved = []
    for target in find_local_image_targets(lines):
        candidate = (doc_dir / target).resolve()
        if candidate.is_file():
            resolved.append(candidate)
    return resolved


# ---------------------------------------------------------------------------
# Cross-document link rewriting
#
# The L1 docs link each other the way a repo does — `[vision.md](vision.md)`,
# `[architecture](../architecture.md)`, `[app.py](../../app.py)`. Those resolve on
# GitHub and on disk, which is exactly the portability the source chain wants. On
# the projected SITE they resolved to nothing: `/docs/vision.md` is not a route,
# so ~490 cross-references across 33 of 35 pages 404'd. (This was a documented
# non-goal of the first projection — "a follow-up cross-doc link rewrite pass" —
# and this is that pass.)
#
# The rewrite is a pure function of the projection's OWN slug map, so it cannot
# invent a route: a link to a projected doc becomes its site route; a link to
# anything else the site doesn't carry (docs/wiki/**, source files, CHANGELOG,
# LICENSE) becomes a GitHub URL, which is where that content actually lives. The
# SOURCE markdown is never touched — it keeps working on GitHub, unchanged.
# ---------------------------------------------------------------------------

GITHUB_BASE = "https://github.com/take-tempo-public/sartor"

# Inline markdown links, minus images (the `(?<!!)` lookbehind) — images are the
# static-import path handled above and must not be rewritten to a URL.
_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(\s+\"[^\"]*\")?\)")


def _site_route(slug: str) -> str:
    return "/docs" if slug == "index" else f"/docs/{slug}"


def rewrite_link_target(rel_posix: str, target: str, slug_map: dict[str, str]) -> str | None:
    """The rewritten href for one link target, or None to leave it untouched.

    `rel_posix` is the SOURCE doc's repo-relative path — markdown resolves a
    relative link against the linking file's own directory, so that is the base.
    """
    if target.startswith(("http://", "https://", "mailto:", "#", "/")):
        return None  # absolute, external, or a same-page anchor — already correct

    path_part, _, fragment = target.partition("#")
    if not path_part:
        return None

    doc_dir = Path(rel_posix).parent
    try:
        resolved = (doc_dir / path_part).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None  # escapes the repo — not ours to rewrite

    suffix = f"#{fragment}" if fragment else ""

    if resolved in slug_map:
        return _site_route(slug_map[resolved]) + suffix

    # Not a projected page: point at the real home on GitHub. A trailing slash (or
    # an extension-less path that is a real directory) is a tree, not a blob.
    abs_path = REPO_ROOT / resolved
    kind = "tree" if (path_part.endswith("/") or abs_path.is_dir()) else "blob"
    return f"{GITHUB_BASE}/{kind}/main/{resolved}{suffix}"


def rewrite_cross_doc_links(
    rel_posix: str, lines: list[str], slug_map: dict[str, str]
) -> list[str]:
    """Rewrite every in-repo markdown link on a page to a site route or a GitHub
    URL. Fenced code blocks are left alone — a link inside a code sample is
    sample text, not navigation."""
    out: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in lines:
        m = _FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if not in_fence:
                in_fence, fence_marker = True, marker[:3]
            elif marker.startswith(fence_marker):
                in_fence, fence_marker = False, ""
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        def _sub(match: re.Match[str]) -> str:
            text, target, title = match.group(1), match.group(2), match.group(3) or ""
            new_target = rewrite_link_target(rel_posix, target, slug_map)
            return match.group(0) if new_target is None else f"[{text}]({new_target}{title})"

        out.append(_LINK_RE.sub(_sub, line))

    return out


# ---------------------------------------------------------------------------
# Frontmatter + orchestration
# ---------------------------------------------------------------------------


def _yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def build_frontmatter(
    title: str,
    description: str,
    audience: str,
    authoritative_for: str,
    source_commit: str | None = None,
) -> str:
    lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"description: {_yaml_quote(description)}",
        f"audience: [{_yaml_quote(audience)}]",
        f"authoritativeFor: {_yaml_quote(authoritative_for)}",
    ]
    if source_commit is not None:
        lines.append(f"sourceCommit: {_yaml_quote(source_commit)}")
    lines += ["---", ""]
    return "\n".join(lines)


class Page:
    def __init__(
        self,
        rel_posix: str,
        slug: str,
        title: str,
        description: str,
        audience: str,
        body: str,
        local_images: list[Path],
    ):
        self.rel_posix = rel_posix
        self.slug = slug
        self.title = title
        self.description = description
        self.audience = audience
        self.body = body
        self.local_images = local_images


def collect_pages(entries: tuple[Entry, ...] = PUBLISHED, commit: str | None = None) -> list[Page]:
    """Render every registered doc, in registry order. Raises `ProjectionError` for a
    registered doc that is missing or lacks the full header. `commit`, when given, is
    stamped into every page (item 126)."""
    # Two phases: the link rewriter needs the FULL set of projected pages (a page can
    # link to any other) before any body is rendered, so every entry is read and
    # validated first, and the slug map handed to phase two.
    loaded: list[tuple[Entry, list[str], dict[str, str]]] = []
    for entry in entries:
        abs_path = REPO_ROOT / entry.path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProjectionError(f"registered doc {entry.path} is unreadable: {exc}") from exc
        lines = text.splitlines()
        fields = parse_header_fields(lines)
        if not has_full_header(fields):
            raise ProjectionError(
                f"registered doc {entry.path} lacks the full "
                "Purpose/Audience/Authoritative-for header"
            )
        loaded.append((entry, lines, fields))

    slug_map = {entry.path: make_slug(entry.path) for entry, _, _ in loaded}

    pages: list[Page] = []
    for entry, lines, fields in loaded:
        rel_posix = entry.path
        title = first_h1(lines) or rel_posix
        local_images = resolve_local_images(rel_posix, lines)
        body_lines = strip_first_h1(lines)
        body_lines = rewrite_local_images(rel_posix, body_lines)
        body_lines = rewrite_cross_doc_links(rel_posix, body_lines, slug_map)
        body_lines = escape_mdx_unsafe(body_lines)
        body = "\n".join(body_lines).rstrip() + "\n"
        frontmatter = build_frontmatter(
            title=title,
            description=fields["Purpose"],
            audience=entry.tier,
            authoritative_for=fields["Authoritative for"],
            source_commit=commit,
        )
        # YAML frontmatter must be the very first bytes of the file (`---` on
        # line 1) or fumadocs-mdx silently fails to parse it — the banner
        # comment goes AFTER the frontmatter block, not before it.
        content = frontmatter + generated_banner(commit) + body
        pages.append(
            Page(
                rel_posix=rel_posix,
                slug=slug_map[rel_posix],
                title=title,
                description=fields["Purpose"],
                audience=entry.tier,
                body=content,
                local_images=local_images,
            )
        )
    return pages


def copy_local_images(pages: list[Page]) -> None:
    """Mirror every referenced local image (byte-copy, unchanged filename) into
    the shared `screenshots/` dir alongside the projected pages. A same-basename
    collision from two different source paths is a hard error — silently
    overwriting one doc's screenshot with another's would be a correctness bug,
    not a warning."""
    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    by_basename: dict[str, Path] = {}
    for page in pages:
        for src in page.local_images:
            existing = by_basename.get(src.name)
            if existing is not None and existing != src:
                raise SystemExit(
                    f"project_docs_to_mdx: FAILED — image basename collision: "
                    f"{existing} vs {src} both map to screenshots/{src.name}"
                )
            by_basename[src.name] = src
    if not by_basename:
        return
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, src in by_basename.items():
        shutil.copy2(src, SCREENSHOTS_DIR / name)


def write_pages(pages: list[Page]) -> None:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    # Clean previously generated pages (this dir is fully derived) — never touches
    # meta.json until write_meta_json() below, and never touches anything outside
    # CONTENT_DIR.
    for existing in CONTENT_DIR.glob("*.mdx"):
        existing.unlink()
    for page in pages:
        (CONTENT_DIR / f"{page.slug}.mdx").write_text(page.body, encoding="utf-8", newline="\n")
    copy_local_images(pages)


USER_SEPARATOR = "---Using Sartor---"
DEV_SEPARATOR = "---Building on Sartor---"


def build_meta_pages_order(pages: list[Page]) -> list[str]:
    """The `meta.json` `pages` array: `index`, then the user tier under a "Using Sartor"
    separator, then the dev tier under "Building on Sartor" (Fumadocs `---Title---`
    separator syntax). Pages keep registry order within a tier. Pure, so it's directly
    testable."""
    index_pages = [p.slug for p in pages if p.slug == "index"]
    user_pages = [p.slug for p in pages if p.audience == "user" and p.slug != "index"]
    dev_pages = [p.slug for p in pages if p.audience == "dev" and p.slug != "index"]
    return [*index_pages, USER_SEPARATOR, *user_pages, DEV_SEPARATOR, *dev_pages]


def write_meta_json(pages: list[Page]) -> None:
    meta = {
        "title": "sartor. docs",
        "pages": build_meta_pages_order(pages),
    }
    (CONTENT_DIR / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def project() -> list[Page]:
    pages = collect_pages(commit=source_commit())
    write_pages(pages)
    write_meta_json(pages)
    return pages


def main() -> int:
    try:
        pages = project()
    except ProjectionError as exc:
        print(f"project_docs_to_mdx: FAILED — {exc}", file=sys.stderr)
        return 1
    user_count = sum(1 for p in pages if p.audience == "user")
    dev_count = sum(1 for p in pages if p.audience == "dev")
    print(
        f"project_docs_to_mdx: OK — {len(pages)} pages projected to "
        f"{CONTENT_DIR.relative_to(REPO_ROOT).as_posix()} "
        f"({user_count} user-tier, {dev_count} dev-tier)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

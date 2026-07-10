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

**Scope — what counts as "L1".**
Per the source-chain diagram in `documentation-architecture.md`, L1 is the
*authored* doc set (README + top-level contract docs + `docs/**` EXCLUDING
`docs/wiki/**`, which is L2 — compiled/synthesized substrate that feeds
Search + the in-product "Ask" avatar, not this static projection). Within
that tree, a file is in scope only if it carries the FULL three-line header
(`**Purpose:**` + `**Audience:**` + `**Authoritative for:**` all present) —
the same deterministic signal that already distinguishes an L1 "single home"
doc from an L2 wiki page (wiki pages use `**Purpose:**` / `**Audience:**` /
`**Grounding:**` instead — no `**Authoritative for:**` line — so they are
excluded by this parse without needing a path special-case).

**The frontmatter map (documentation-architecture.md "Fumadocs sourcing").**

| Header line            | -> frontmatter        | Drives                          |
|-------------------------|------------------------|----------------------------------|
| `**Purpose:**`          | `description`         | page identity / SEO description |
| (first `# H1` heading)  | `title`                | page identity                   |
| `**Audience:**`         | `audience: [...]`      | which ICP front door it appears under |
| `**Authoritative for:**`| `authoritativeFor`     | the canonical-home marker       |

**Audience classification — reuses the SCHEMA backtick-token parse, with a
documented fallback.** `docs/wiki/SCHEMA.md` defines the machine-parseable
`` `user` ``/`` `dev` `` backtick token immediately after `**Audience:**` —
but empirically only 2 of the 30 in-scope L1 files (`README.md`,
`docs/dev/documentation-architecture.md`) actually use that exact token; the
rest predate it and write free-form prose (e.g. "humans installing sartor.
for the first time"). This script therefore: (1) tries the SCHEMA backtick
parse first; (2) falls back to SCHEMA's own documented "blanket path->audience
rule" table (`README.md` / `docs/install.md` / `docs/walkthrough*.md` /
`vision.md` -> `user`; `docs/dev/**` -> `dev`); (3) if neither resolves,
defaults to `dev` — a conservative choice: it nests the page under the
fuller "developer" tier (never a mis-promotion of internal content to the
simple front door) rather than silently guessing "user".

**The ICP-ladder ordering (`meta.json`).** The README's own "Documentation
map" blockquote (the line beginning `**Documentation map.**`) already states
the canonical doc ordering as a sequence of markdown links — this script
parses THAT block (no hand-maintained priority table duplicated here) to get
a base ordering, expands any directory-shaped link (e.g. `docs/governance/`)
to the in-scope files under it, and appends any in-scope file the map doesn't
mention (alphabetically, by slug) after the mapped ones. `meta.json`'s
`pages` array is then: `index` first, then every `user`-tier page in that
order, then every `dev`-tier page in that order — the "job seeker/coach
before developer" ICP ladder, made literal.

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
the Next.js build fails with `Module not found`. `docs/walkthrough.md` and
`docs/install.md` reference `docs/screenshots/*.png` this way. Because every
projected page lives flat in `docs-site/content/docs/`, this script mirrors
those referenced images (byte-copy, unchanged filenames — no link rewrite
needed) into a shared `docs-site/content/docs/screenshots/` directory that
sits alongside them; a same-basename collision from two different source
paths is a build-stopping error, not a silent overwrite.

**Non-goals (deliberate, documented — not oversights).**
- No internal link rewriting: an in-repo relative link like
  `docs/install.md` is projected byte-identical. Portability
  (`documentation-architecture.md` "Portability") deliberately keeps every
  L1 doc plain markdown that degrades correctly on GitHub; teaching this
  script to rewrite links to site slugs would make the MDX a second,
  diverging representation of the same fact. A follow-up cross-doc link
  rewrite pass is a separate, explicitly out-of-scope enhancement.
- No L2 (`docs/wiki/**`) content — that is Search/"Ask" territory, not
  this static projection (this lane ships a static export only).

Exit 0 on success, printing a one-line summary. Exit 1 on an unrecoverable
error (e.g. no `git` / not a repo).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "docs-site" / "content" / "docs"

_GENERATED_BANNER = (
    "{/* GENERATED by scripts/project_docs_to_mdx.py — do not hand-edit. "
    "Edit the cited source doc and re-run the projection. */}\n"
)

# ---------------------------------------------------------------------------
# Header parsing (Purpose / Audience / Authoritative for)
# ---------------------------------------------------------------------------

_HEADER_START_RE = re.compile(r"^> \*\*Purpose:\*\*")
_HEADER_LABEL_RE = re.compile(r"\*\*([A-Za-z][A-Za-z0-9 /'\-]*):\*\*")
_BACKTICK_AUDIENCE_RE = re.compile(r"`(user|dev)`")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
_WS_RE = re.compile(r"\s+")

REQUIRED_FIELDS = ("Purpose", "Audience", "Authoritative for")

# SCHEMA.md "Blanket path->audience rules" (docs/wiki/SCHEMA.md) — the
# documented fallback for L1 docs that predate the backtick-token audience
# convention. Directory prefixes are POSIX-relative to the repo root.
_USER_TIER_EXACT = {"README.md", "docs/install.md", "vision.md"}
_USER_TIER_PREFIXES = ("docs/walkthrough",)
_DEV_TIER_PREFIXES = ("docs/dev/",)


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


def list_repo_md_files() -> list[str]:
    """All tracked *.md files (repo-relative POSIX paths), excluding docs/wiki/** (L2)."""
    out = _run_git(["ls-files", "*.md"])
    paths = [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]
    return [p for p in paths if not p.startswith("docs/wiki/")]


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
# Audience classification
# ---------------------------------------------------------------------------


def classify_audience(rel_posix: str, audience_text: str) -> str:
    """`user` or `dev` — SCHEMA backtick-token parse first, then SCHEMA's blanket
    path rule, then a conservative `dev` default. See module docstring."""
    m = _BACKTICK_AUDIENCE_RE.search(audience_text or "")
    if m:
        return m.group(1)
    if rel_posix in _USER_TIER_EXACT or rel_posix.startswith(_USER_TIER_PREFIXES):
        return "user"
    if rel_posix.startswith(_DEV_TIER_PREFIXES):
        return "dev"
    return "dev"


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
# ICP-ladder ordering — parsed from README's own "Documentation map" block
# ---------------------------------------------------------------------------

_DOC_MAP_ANCHOR = "**Documentation map.**"
_DOC_MAP_LINK_RE = re.compile(r"\[`?([^`\]]+)`?\]\(([^)\s]+)\)")


def parse_doc_map_order(readme_lines: list[str]) -> list[str]:
    """The ordered list of repo-relative link targets in README's Documentation-map
    blockquote. Directory-shaped targets (e.g. `docs/governance/`) are returned as-is;
    callers expand them to the in-scope files they contain."""
    start = None
    for i, line in enumerate(readme_lines):
        if line.startswith(">") and _DOC_MAP_ANCHOR in line:
            start = i
            break
    if start is None:
        return []
    block: list[str] = []
    for line in readme_lines[start:]:
        if not line.startswith(">"):
            break
        block.append(line)
    text = "\n".join(block)
    targets: list[str] = []
    for m in _DOC_MAP_LINK_RE.finditer(text):
        target = m.group(2)
        if target.startswith(("http://", "https://", "#")):
            continue
        targets.append(target)
    return targets


def build_priority_index(doc_map_order: list[str], in_scope_paths: list[str]) -> dict[str, int]:
    """Map each in-scope repo-relative path -> a priority rank following the README
    Documentation-map order (directory links expand to their in-scope members, sorted
    alphabetically among themselves); paths the map doesn't mention sort after, also
    alphabetically, in their own trailing block."""
    priority: dict[str, int] = {}
    rank = 0
    seen: set[str] = set()
    for target in doc_map_order:
        if target.endswith("/"):
            members = sorted(p for p in in_scope_paths if p.startswith(target) and p not in seen)
        else:
            members = [target] if target in in_scope_paths and target not in seen else []
        for p in members:
            priority[p] = rank
            seen.add(p)
            rank += 1
    for p in sorted(in_scope_paths):
        if p not in seen:
            priority[p] = rank
            rank += 1
    return priority


# ---------------------------------------------------------------------------
# Frontmatter + orchestration
# ---------------------------------------------------------------------------


def _yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def build_frontmatter(title: str, description: str, audience: str, authoritative_for: str) -> str:
    lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"description: {_yaml_quote(description)}",
        f"audience: [{_yaml_quote(audience)}]",
        f"authoritativeFor: {_yaml_quote(authoritative_for)}",
        "---",
        "",
    ]
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


def collect_pages() -> list[Page]:
    pages: list[Page] = []
    for rel_posix in list_repo_md_files():
        abs_path = REPO_ROOT / rel_posix
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        fields = parse_header_fields(lines)
        if not has_full_header(fields):
            continue
        title = first_h1(lines) or rel_posix
        audience = classify_audience(rel_posix, fields["Audience"])
        local_images = resolve_local_images(rel_posix, lines)
        body_lines = strip_first_h1(lines)
        body_lines = escape_mdx_unsafe(body_lines)
        body = "\n".join(body_lines).rstrip() + "\n"
        frontmatter = build_frontmatter(
            title=title,
            description=fields["Purpose"],
            audience=audience,
            authoritative_for=fields["Authoritative for"],
        )
        # YAML frontmatter must be the very first bytes of the file (`---` on
        # line 1) or fumadocs-mdx silently fails to parse it — the banner
        # comment goes AFTER the frontmatter block, not before it.
        content = frontmatter + _GENERATED_BANNER + body
        pages.append(
            Page(
                rel_posix=rel_posix,
                slug=make_slug(rel_posix),
                title=title,
                description=fields["Purpose"],
                audience=audience,
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


def build_meta_pages_order(pages: list[Page], priority: dict[str, int]) -> list[str]:
    """The `meta.json` `pages` slug order: `index` first, then every `user`-tier
    page, then every `dev`-tier page — each group internally sorted by the
    README ICP-ladder `priority` rank. Pure (no I/O) so it's directly testable."""
    ordered = sorted(pages, key=lambda p: priority.get(p.rel_posix, 1_000_000))
    index_pages = [p for p in ordered if p.slug == "index"]
    user_pages = [p for p in ordered if p.audience == "user" and p.slug != "index"]
    dev_pages = [p for p in ordered if p.audience == "dev" and p.slug != "index"]
    return [p.slug for p in (index_pages + user_pages + dev_pages)]


def write_meta_json(pages: list[Page], priority: dict[str, int]) -> None:
    meta = {
        "title": "sartor. docs",
        "pages": build_meta_pages_order(pages, priority),
    }
    (CONTENT_DIR / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def project() -> list[Page]:
    pages = collect_pages()
    readme_lines = (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    doc_map_order = parse_doc_map_order(readme_lines)
    in_scope_paths = [p.rel_posix for p in pages]
    priority = build_priority_index(doc_map_order, in_scope_paths)
    write_pages(pages)
    write_meta_json(pages, priority)
    return pages


def main() -> int:
    try:
        pages = project()
    except subprocess.CalledProcessError as exc:
        print(f"project_docs_to_mdx: FAILED — git error: {exc}", file=sys.stderr)
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

#!/usr/bin/env python3
"""The §5 doc lints (`docs/dev/docs-ia-design.md` §5, rows 5.3–5.9), over the shared corpus.

Each lint is one function `(corpus) -> list[Finding]`. A finding is a **block** (fails the
gate) or a **warn** (printed, never fails). `tests/test_doc_lints.py` runs every lint on the
real tree and gives each one a seeded violation it must catch. That test is how the lints
ride the gate (`python -m scripts.gate`, the `pytest -m "not ux"` step); this file adds no
gate step of its own.

| Row | Lint | Scope | Fails closed? |
|---|---|---|---|
| 5.3 | `lint_type_header` | user tier | presence yes; correctness of the type **unenforced** |
| 5.4 | `lint_wordmark` | registry, minus wiki/reviews/records/CHANGELOG | block; warn on the end-of-sentence form |
| 5.5 | `lint_enumeration_drift` | live docs | yes, within the limits stated at each check |
| 5.5 | `lint_tooling_roster` | `docs/dev/tooling.md` vs the tree | yes, both directions |
| 5.6 | `lint_banned_words` | user tier | block list yes; warn list is a report |
| 5.7 | `lint_jargon_and_ids` | user tier | yes |
| 5.8 | `lint_wikilinks`, `lint_charter_clauses` | live docs; the charter | yes |
| 5.9 | `report_single_home_widened` | registry vs `docs/wiki/pages/` | **unenforced**: a report, never a block |

5.1 and 5.2 live in `check_doc_frontmatter.py` / `doc_registry.py` (shipped in D2); 5.8's
link and anchor checks are `check_doc_links.py`.

**Scope is filtered before any body is read** (lazy by scope, §5 intro). The user-tier lints
read the 10 user-tier docs; the registry lints read the 39 registered docs. Only 5.5 and
5.8 read every live doc, because an enumeration or a wikilink can sit in any of them; they
share the one cached read.

Run `python scripts/doc_lints.py` for the block/warn listing, `--report` to add the 5.9
single-home report. Exit 1 on any block. Stdlib only.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from doc_corpus import DocCorpus
from doc_registry import PUBLISHED, is_record

# ---------------------------------------------------------------------------------------
# Findings and shared scopes


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    message: str
    block: bool = True

    def __str__(self) -> str:
        level = "BLOCK" if self.block else "warn"
        return f"[{self.rule} {level}] {self.path}:{self.line} -> {self.message}"


USER_TIER: tuple[str, ...] = tuple(e.path for e in PUBLISHED if e.tier == "user")
REGISTRY: tuple[str, ...] = tuple(e.path for e in PUBLISHED)

# Wordmark exclusions (design 5.4; RELEASE_ARC D1 bullet: "must inherit item 2's
# exclusions"). Records are excluded through `is_record`.
_WORDMARK_EXCLUDE_PREFIXES = ("docs/wiki/", "docs/dev/reviews/")


def live_docs(corpus: DocCorpus) -> list[str]:
    """Every tracked doc that is not a record, a wiki page or a changelog. Records keep their
    historical lists (design 5.5); the wiki has its own lint (`/wiki-lint`)."""
    return [
        p
        for p in corpus.md_paths
        if not is_record(p)
        and not p.startswith("docs/wiki/")
        and not Path(p).name.startswith("CHANGELOG")
    ]


# ---------------------------------------------------------------------------------------
# Prose extraction: unfenced lines with HTML comments, inline code and link URLs removed

# A code span opens with N backticks and closes with exactly N (CommonMark), so
# "`` `user` ``" is one span.
_CODE_SPAN_RE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")
_LINK_URL_RE = re.compile(r"\]\([^)]*\)")
_COMMENT_RE = re.compile(r"<!--.*?-->")


def prose(corpus: DocCorpus, path: str) -> list[tuple[int, str]]:
    """(lineno, text) for the doc's rendered prose. Fenced code, `<!-- -->` comments (one- or
    multi-line), inline code spans and link URLs are blanked. Cached on the corpus itself,
    so the cache lives and dies with it. A module-level cache keyed by `id(corpus)` served
    stale text when a collected corpus's id was reused (observed under pytest-xdist)."""
    cache: dict[str, list[tuple[int, str]]] = corpus.__dict__.setdefault("_doc_lints_prose", {})
    cached = cache.get(path)
    if cached is not None:
        return cached
    out: list[tuple[int, str]] = []
    in_comment = False
    in_code = False  # an inline code span left open at the end of the previous line
    # YAML frontmatter (agents/*.md, commands/*.md) is metadata, not rendered prose.
    raw = corpus.lines(path)
    frontmatter_end = 0
    if raw and raw[0].strip() == "---":
        frontmatter_end = next((i + 1 for i in range(1, len(raw)) if raw[i].strip() == "---"), 0)
    for lineno, line in corpus.unfenced(path):
        if lineno <= frontmatter_end:
            continue
        text = line
        if not text.strip():
            in_code = False  # a code span never crosses a blank line
        if in_code:
            close = text.find("`")
            if close == -1:
                out.append((lineno, ""))
                continue
            text = text[close + 1 :]
            in_code = False
        if in_comment:
            end = text.find("-->")
            if end == -1:
                continue
            text = text[end + 3 :]
            in_comment = False
        # Code spans first: `<!-- lint-allow -->` written as code is not a comment.
        text = _CODE_SPAN_RE.sub("", text)
        text = _COMMENT_RE.sub("", text)
        start = text.find("<!--")
        if start != -1:
            text = text[:start]
            in_comment = True
        tick = text.find("`")
        if tick != -1:
            text = text[:tick]
            in_code = True
        text = _LINK_URL_RE.sub("]", text)
        out.append((lineno, text))
    cache[path] = out
    return out


def _header_lines(corpus: DocCorpus, path: str) -> set[int]:
    """Line numbers of the Purpose/Audience/Authoritative-for header blockquote (the one that
    opens with `**Purpose:**`). It is metadata, so 5.7 doesn't count a first use there."""
    lines = corpus.lines(path)
    for i, line in enumerate(lines):
        if line.startswith("> **Purpose:**"):
            end = i
            while end + 1 < len(lines) and lines[end + 1].startswith(">"):
                end += 1
            return set(range(i + 1, end + 2))
    return set()


# ---------------------------------------------------------------------------------------
# 5.3 Diátaxis type

_TYPE_RE = re.compile(r"\*\*Type:\*\*\s*(tutorial|how-to|reference|explanation)\b")


def lint_type_header(corpus: DocCorpus, paths: Iterable[str] = USER_TIER) -> list[Finding]:
    """Every user-tier doc carries `**Type:**` (tutorial / how-to / reference / explanation)
    in its header. Whether the type is the right one is judgment, and unenforced."""
    found = []
    for path in paths:
        try:
            head = corpus.head(path, 4000)
        except OSError as exc:
            found.append(Finding("5.3", path, 0, f"unreadable: {exc}"))
            continue
        if not _TYPE_RE.search(head):
            found.append(
                Finding("5.3", path, 1, "user-tier doc has no `**Type:**` Diátaxis header")
            )
    return found


# ---------------------------------------------------------------------------------------
# 5.4 Wordmark

# `sartor.` mid-sentence: followed by `'s`, `-`, or whitespace + a lowercase letter.
_WM_BLOCK_RE = re.compile(r"(?<![\w/.-])sartor\.(?='s|-|\s+[a-z])")
# Ambiguous: a sentence that may end on the wordmark ("through sartor.").
_WM_WARN_RE = re.compile(r"(?<![\w/.-])sartor\.(?=\s+[A-Z]|\s*$|[,;:)])")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s")


def lint_wordmark(corpus: DocCorpus, paths: Iterable[str] = REGISTRY) -> list[Finding]:
    """`Sartor` in sentences, `sartor.` only standing alone (style guide §1; owner O-1).
    A heading may end on the wordmark (`# Vision — sartor.`)."""
    found = []
    for path in paths:
        if is_record(path) or path.startswith(_WORDMARK_EXCLUDE_PREFIXES):
            continue
        if Path(path).name.startswith("CHANGELOG"):
            continue
        lines = prose(corpus, path)
        for i, (lineno, text) in enumerate(lines):
            is_heading = bool(_HEADING_RE.match(text))
            if _reviewed(path, "wordmark", text):
                continue
            for m in _WM_BLOCK_RE.finditer(text):
                found.append(
                    Finding(
                        "5.4", path, lineno, f"`sartor.` mid-sentence: {_snip(text, m.start())}"
                    )
                )
            for m in _WM_WARN_RE.finditer(text):
                rest = text[m.end() :].strip()
                if is_heading and not rest:
                    continue  # the title form
                if not rest and i + 1 < len(lines):
                    nxt = lines[i + 1][1].lstrip()
                    if nxt[:1].islower():
                        found.append(
                            Finding(
                                "5.4",
                                path,
                                lineno,
                                f"`sartor.` runs into the next line: {_snip(text, m.start())}",
                            )
                        )
                        continue
                found.append(
                    Finding(
                        "5.4",
                        path,
                        lineno,
                        f"`sartor.` may end a sentence: {_snip(text, m.start())}",
                        block=False,
                    )
                )
    return found


def _snip(text: str, at: int) -> str:
    return text[max(0, at - 30) : at + 40].strip()


# ---------------------------------------------------------------------------------------
# 5.5 Enumeration drift

# Reviewed exceptions: (path, rule key, substring of the paragraph or line, reason). Each one
# was read and judged not to be a current-state enumeration.
_REVIEWED_ENUMERATIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "docs/dev/epic-a-chain-design-corrections.md",
        "deterministic-modules",
        "`Experience.retired`",
        "a consumer list for the retired-flag change, not a list of the deterministic modules",
    ),
    (
        "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
        "deterministic-modules",
        "No LLM calls in",
        "a gated verbatim template; changing it is the owner's decision (item 135's class), and "
        "every in-flight handoff is validated against it byte-for-byte",
    ),
    (
        "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
        "gate-steps",
        "Quality gate",
        "item 135: the template's verbatim gate line is the owner's decision; every in-flight "
        "handoff is validated against it byte-for-byte",
    ),
    (
        "docs/dev/RELEASE_ARC.md",
        "gate-steps",
        "Verified live: full quality gate green",
        "a log of one past gate run, taken before the gate had a work_items step",
    ),
    (
        "docs/dev/RELEASE_CHECKLIST.md",
        "gate-steps",
        "~~Quality gate~~",
        "a closed, struck-through row recording a 2026-05-28 gate run",
    ),
    (
        "docs/dev/docs-ia-design.md",
        "wordmark",
        "Ask how sartor. works",
        "quotes the shipped UI string as it read then (the O-1 decision it records)",
    ),
    (
        "docs/dev/RELEASE_CHECKLIST.md",
        "charter-range",
        "design/governance-extraction",
        "a closed [x] row recording the range as it stood when that branch shipped",
    ),
    (
        "docs/dev/docs-ia-design.md",
        "charter-range",
        "Fix the stale",
        "the D1 design quoting the stale text it scheduled for a fix",
    ),
)


def _reviewed(path: str, key: str, text: str) -> bool:
    return any(p == path and k == key and s in text for p, k, s, _ in _REVIEWED_ENUMERATIONS)


_ITEM_START_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s|^\s*\|")


def _paragraphs(corpus: DocCorpus, path: str) -> list[tuple[int, str]]:
    """(first lineno, text) of each block of unfenced text: a paragraph, one list item (with
    its continuation lines) or one table row. Inline code is kept: module and agent names are
    usually written as code. Splitting per item keeps a long list of unrelated items from
    reading as one enumeration."""
    paras: list[tuple[int, str]] = []
    start = 0
    buf: list[str] = []
    for lineno, text in corpus.unfenced(path):
        if buf and (not text.strip() or _ITEM_START_RE.match(text)):
            paras.append((start, "\n".join(buf)))
            buf = []
        if text.strip():
            if not buf:
                start = lineno
            buf.append(text)
    if buf:
        paras.append((start, "\n".join(buf)))
    return paras


def _code_sets(root: Path) -> dict[str, tuple[str, ...]]:
    """The code-enumerated sets, read from their single homes. The module tuple is read as a
    literal (`ast`), so the lint never imports a test module."""
    source = (root / "tests" / "test_construction_boundary.py").read_text(encoding="utf-8")
    modules: tuple[str, ...] = ()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DETERMINISTIC_MODULES" for t in node.targets
        ):
            modules = tuple(ast.literal_eval(node.value))
    if not modules:
        raise RuntimeError("DETERMINISTIC_MODULES not found in tests/test_construction_boundary.py")
    return {
        "deterministic-modules": modules,
        "subagents": tuple(sorted(p.stem for p in (root / "agents").glob("*.md"))),
    }


# The tools the gate runs, one token per tool (`scripts/gate.py:_STEPS` runs pytest twice).
# `tests/test_doc_lints.py` asserts every `_STEPS` label maps to one of these, so a new gate
# step without a token fails there.
GATE_STEP_TOKENS: dict[str, re.Pattern[str]] = {
    "ruff check": re.compile(r"\bruff check\b"),
    "ruff format": re.compile(r"\bruff format\b"),
    "mypy": re.compile(r"\bmypy\b"),
    "pytest": re.compile(r"\bpytest\b"),
    "work_items": re.compile(r"\bwork_items\b"),
}
# A block describes the gate only if it says so; a log of what a past branch ran is not a
# description of the gate, and the tokens alone can't tell the two apart.
_GATE_DESCRIPTION_RE = re.compile(
    r"quality gate|\bscripts\.gate\b|\bgate\.py\b|\bthe gate (?:runs|is)\b", re.IGNORECASE
)

_CHARTER = "docs/governance/charter.md"
_CLAUSE_HEADING_RE = re.compile(r"^###\s+C-(\d+)\s+—\s+\S")
_RANGE_RE = re.compile(r"\bC-0\s*(?:…|\.\.\.|–|—|-|to|through)\s*C-(\d+)\b")


def charter_clauses(corpus: DocCorpus) -> list[int]:
    """Clause numbers that have their own `### C-n — Title` heading in the charter."""
    nums = []
    for _, line in corpus.unfenced(_CHARTER):
        m = _CLAUSE_HEADING_RE.match(line)
        if m:
            nums.append(int(m.group(1)))
    return nums


def lint_enumeration_drift(
    corpus: DocCorpus,
    paths: Iterable[str] | None = None,
    code_sets: dict[str, tuple[str, ...]] | None = None,
    gate_step_count: int | None = None,
) -> list[Finding]:
    """A doc that enumerates what code enumerates must match it, or link instead (design 5.5).

    - **Named sets** (deterministic modules, subagents): a paragraph naming all but at most
      two members is read as an enumeration and must name every member. *Limit:* a list
      shorter than that is indistinguishable from prose about a subset and is not checked.
    - **Gate steps:** a block that describes the quality gate and names three or more of
      its tools must name all of them, or cite `scripts/gate.py` without listing.
    - **Charter range:** `C-0…C-n` must end at the charter's last clause heading. Dated
      `[src: …]` provenance notes are history and are skipped.
    """
    paths = list(paths) if paths is not None else live_docs(corpus)
    code_sets = code_sets if code_sets is not None else _code_sets(corpus.root)
    if gate_step_count is None:
        gate_step_count = len(GATE_STEP_TOKENS)
    clauses = charter_clauses(corpus) if _CHARTER in corpus.tracked else []
    last_clause = max(clauses) if clauses else None

    # One alternation per set, compiled once: a per-member search per block was 5.3 s of a
    # 9.5 s run (cProfile, 190k searches over ~7.7k blocks).
    set_res = {
        key: re.compile(r"(?<![\w/-])(" + "|".join(map(re.escape, members)) + r")(?![\w-])")
        for key, members in code_sets.items()
    }
    found = []
    for path in paths:
        try:
            paras = _paragraphs(corpus, path)
        except OSError:
            continue
        for lineno, para in paras:
            for key, members in code_sets.items():
                hits = set(set_res[key].findall(para))
                if len(members) - 2 <= len(hits) < len(members) and len(hits) >= 3:
                    if _reviewed(path, key, para):
                        continue
                    missing = ", ".join(sorted(set(members) - hits))
                    found.append(
                        Finding(
                            "5.5",
                            path,
                            lineno,
                            f"lists {len(hits)} of {len(members)} {key}; missing {missing}. List all or link the code instead",
                        )
                    )
            steps = (
                [k for k, rx in GATE_STEP_TOKENS.items() if rx.search(para)]
                if _GATE_DESCRIPTION_RE.search(para)
                else []
            )
            if 3 <= len(steps) < gate_step_count and not _reviewed(path, "gate-steps", para):
                missing = ", ".join(k for k in GATE_STEP_TOKENS if k not in steps)
                found.append(
                    Finding(
                        "5.5",
                        path,
                        lineno,
                        f"describes {len(steps)} of the gate's {gate_step_count} steps (missing {missing}); cite scripts/gate.py instead",
                    )
                )
            if last_clause is not None and "C-0" in para and "[src:" not in para:
                for m in _RANGE_RE.finditer(para):
                    if int(m.group(1)) != last_clause and not _reviewed(
                        path, "charter-range", para
                    ):
                        found.append(
                            Finding(
                                "5.5",
                                path,
                                lineno,
                                f"`{m.group(0)}` but the charter runs to C-{last_clause}",
                            )
                        )
    return found


# The roster in docs/dev/tooling.md, section by section, against the tree.
_TOOLING = "docs/dev/tooling.md"
_FIRST_CELL_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def tooling_tree(root: Path) -> dict[str, set[str]]:
    """What the tree says each tooling.md section must list."""
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = {
        Path(h["command"].split()[0]).name
        for matchers in settings.get("hooks", {}).values()
        for m in matchers
        for h in m.get("hooks", [])
    }
    guards = {
        p.stem.replace("_", "-")
        for p in (root / "scripts" / "enforcement" / "guards").glob("*.py")
        if p.stem not in {"__init__", "result"}
    }
    return {
        "Claude Code hooks": hooks,
        "Enforcement guards": guards,
        "Slash commands": {p.stem for p in (root / "commands").glob("*.md")},
        "Subagents": {p.stem for p in (root / "agents").glob("*.md")},
        "Skills": {p.parent.name for p in (root / "skills").glob("*/SKILL.md")},
    }


def lint_tooling_roster(
    corpus: DocCorpus, tree: dict[str, set[str]] | None = None
) -> list[Finding]:
    """`docs/dev/tooling.md` lists exactly what the tree has: every name present, no name
    left after its file is gone. Checked per section, both directions."""
    tree = tree if tree is not None else tooling_tree(corpus.root)
    listed: dict[str, dict[str, int]] = {}
    section = None
    for lineno, line in corpus.unfenced(_TOOLING):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = _FIRST_CELL_RE.match(line)
        if section in tree and m:
            listed.setdefault(section, {})[m.group(1)] = lineno
    found = []
    for name, expected in tree.items():
        rows = listed.get(name, {})
        if not rows and expected:
            found.append(
                Finding("5.5", _TOOLING, 0, f"section `## {name}` is missing or has no rows")
            )
            continue
        for missing in sorted(expected - set(rows)):
            found.append(
                Finding(
                    "5.5",
                    _TOOLING,
                    0,
                    f"`## {name}` does not list `{missing}`, which exists in the tree",
                )
            )
        for stale in sorted(set(rows) - expected):
            found.append(
                Finding(
                    "5.5",
                    _TOOLING,
                    rows[stale],
                    f"`## {name}` lists `{stale}`, which is not in the tree",
                )
            )
    return found


# ---------------------------------------------------------------------------------------
# 5.6 Banned words

_BAN_BLOCK_RE = re.compile(
    r"\b(simply|easy|easily|obviously|powerful|seamless(?:ly)?|revolutionary|sanity[- ]checks?"
    r"|chok(?:e|es|ing)|crippl(?:e|es|ed|ing)|blind to)\b",
    re.IGNORECASE,
)
# `just` + an imperative blames the reader ("just run it"). Bare `just` is not banned
# (design 5.6). Closed verb list; a verb outside it is not caught (stated limit).
_JUST_IMPERATIVE_RE = re.compile(
    r"\bjust\s+(run|click|add|use|type|open|paste|pick|set|do|go|press|select|copy|edit|make"
    r"|enter|drop|upload|follow|install|restart|delete|change|re-?run|start|try|read)\b",
    re.IGNORECASE,
)
_BAN_WARN_RE = re.compile(
    r"\b(honest(?:ly)?|genuinely|actually|clearly|first-class|load-bearing|under the hood)\b",
    re.IGNORECASE,
)
_ALLOW_OPEN, _ALLOW_CLOSE = "<!-- lint-allow -->", "<!-- /lint-allow -->"
_ALLOW_HOME = "docs/dev/doc-style-guide.md"


def lint_banned_words(corpus: DocCorpus, paths: Iterable[str] = USER_TIER) -> list[Finding]:
    """User tier: block the reader-blaming, hype and figurative list; warn on the softer list.
    `<!-- lint-allow -->` regions are honored only in the style guide's own examples."""
    found = []
    for path in paths:
        raw = corpus.read(path)
        allowed: set[int] = set()
        if _ALLOW_OPEN in raw:
            if path != _ALLOW_HOME:
                found.append(
                    Finding("5.6", path, 0, f"`{_ALLOW_OPEN}` is honored only in {_ALLOW_HOME}")
                )
            else:
                inside = False
                for lineno, line in enumerate(raw.splitlines(), start=1):
                    if _ALLOW_OPEN in line:
                        inside = True
                    if inside:
                        allowed.add(lineno)
                    if _ALLOW_CLOSE in line:
                        inside = False
        for lineno, text in prose(corpus, path):
            if lineno in allowed:
                continue
            for rx in (_BAN_BLOCK_RE, _JUST_IMPERATIVE_RE):
                for m in rx.finditer(text):
                    found.append(
                        Finding("5.6", path, lineno, f"banned on the user tier: {m.group(0)!r}")
                    )
            for m in _BAN_WARN_RE.finditer(text):
                found.append(
                    Finding("5.6", path, lineno, f"soft word: {m.group(0)!r}", block=False)
                )
    return found


# ---------------------------------------------------------------------------------------
# 5.7 Jargon first use and tracker IDs

ACRONYMS: dict[str, str] = {
    "LLM": "large language model",
    "JD": "job description",
    "ATS": "applicant tracking system",
    "SSE": "server-sent events",
    "API": "application programming interface",
}
_TRACKER_ID_RE = re.compile(r"\b(PX-\d+|F-[a-z]+-\d+|Sprint \d+|C-\d+|[Ii]tem \d+)\b")


def lint_jargon_and_ids(corpus: DocCorpus, paths: Iterable[str] = USER_TIER) -> list[Finding]:
    """User tier: each listed acronym is expanded at or before its first use in the doc (an
    acronym block near the top counts), and internal tracker IDs never appear in rendered
    text. The opening Purpose/Audience header is metadata and is skipped."""
    found = []
    for path in paths:
        header = _header_lines(corpus, path)
        lines = [(n, t) for n, t in prose(corpus, path) if n not in header]
        for lineno, text in lines:
            for m in _TRACKER_ID_RE.finditer(text):
                found.append(
                    Finding(
                        "5.7", path, lineno, f"internal tracker ID on the user tier: {m.group(0)!r}"
                    )
                )
        # Paragraph by paragraph, so an acronym block that wraps ("**LLM** =" on one line,
        # "large language model" on the next) counts as the expansion.
        seen_text = ""
        pending = dict(ACRONYMS)
        para: list[tuple[int, str]] = []
        for lineno, text in [*lines, (0, "")]:
            if text.strip():
                para.append((lineno, text))
                continue
            if not para:
                continue
            seen_text += " " + " ".join(t for _, t in para).lower()
            for acr in list(pending):
                first = next((n for n, t in para if re.search(rf"\b{acr}s?\b", t)), None)
                if first is None:
                    continue
                if pending[acr] not in seen_text:
                    found.append(
                        Finding(
                            "5.7",
                            path,
                            first,
                            f"first use of {acr} before its expansion ({pending[acr]!r})",
                        )
                    )
                del pending[acr]
            para = []
            if not pending:
                break
    return found


# ---------------------------------------------------------------------------------------
# 5.8 Wikilinks and charter clause anchors

_WIKILINK_RE = re.compile(r"\[\[[^\]\n]+\]\]")


def lint_wikilinks(corpus: DocCorpus, paths: Iterable[str] | None = None) -> list[Finding]:
    """`[[wikilink]]` syntax renders only inside `docs/wiki/`; anywhere else it is a dead
    link. Written as code (in backticks) it is an example and is fine."""
    paths = list(paths) if paths is not None else live_docs(corpus)
    found = []
    for path in paths:
        try:
            lines = prose(corpus, path)
        except OSError:
            continue
        for lineno, text in lines:
            for m in _WIKILINK_RE.finditer(text):
                found.append(
                    Finding("5.8", path, lineno, f"wikilink outside docs/wiki/: {m.group(0)}")
                )
    return found


_CLAUSE_REF_RE = re.compile(r"\bC-(\d+)\b")


def lint_charter_clauses(corpus: DocCorpus, paths: Iterable[str] = REGISTRY) -> list[Finding]:
    """Every charter clause C-0…C-n has its own `### C-n — Title` heading, numbered without
    gaps, so a citation can deep-link to it. A registered doc citing a clause number past
    the last heading cites a clause that does not exist."""
    clauses = charter_clauses(corpus)
    found = []
    if not clauses:
        return [Finding("5.8", _CHARTER, 0, "no `### C-n — Title` clause headings found")]
    expected = list(range(max(clauses) + 1))
    if sorted(clauses) != expected:
        found.append(
            Finding(
                "5.8",
                _CHARTER,
                0,
                f"clause headings {sorted(clauses)} are not C-0…C-{max(clauses)} without gaps",
            )
        )
    last = max(clauses)
    for path in paths:
        if path == _CHARTER:
            continue
        for lineno, text in prose(corpus, path):
            for m in _CLAUSE_REF_RE.finditer(text):
                if int(m.group(1)) > last:
                    found.append(
                        Finding(
                            "5.8",
                            path,
                            lineno,
                            f"cites C-{m.group(1)}; the charter ends at C-{last}",
                        )
                    )
    return found


# ---------------------------------------------------------------------------------------
# 5.9 Single-home, widened (report only)

_WORD_RE = re.compile(r"[a-z0-9']+")
SHINGLE = 25


def _shingles(corpus: DocCorpus, path: str) -> set[int]:
    words = _WORD_RE.findall(" ".join(t for _, t in prose(corpus, path)).lower())
    return {hash(tuple(words[i : i + SHINGLE])) for i in range(len(words) - SHINGLE + 1)}


def report_single_home_widened(
    corpus: DocCorpus, l1: Iterable[str] = REGISTRY, wiki: Iterable[str] | None = None
) -> list[Finding]:
    """Wiki pages that share a run of 25+ words with a registered doc. **Report only and
    unenforced** (design 5.9): the wiki is meant to synthesize L1, so overlap is expected and
    the false-positive rate is high. Never a block."""
    if wiki is None:
        wiki = [p for p in corpus.md_paths if p.startswith("docs/wiki/pages/")]
    l1_sh = {p: _shingles(corpus, p) for p in l1}
    found = []
    for page in wiki:
        sh = _shingles(corpus, page)
        for doc, dsh in l1_sh.items():
            shared = len(sh & dsh)
            if shared:
                found.append(
                    Finding(
                        "5.9",
                        page,
                        0,
                        f"shares {shared} {SHINGLE}-word run(s) with {doc}",
                        block=False,
                    )
                )
    return found


# ---------------------------------------------------------------------------------------

GATED_LINTS: tuple[Callable[[DocCorpus], list[Finding]], ...] = (
    lint_type_header,
    lint_wordmark,
    lint_enumeration_drift,
    lint_tooling_roster,
    lint_banned_words,
    lint_jargon_and_ids,
    lint_wikilinks,
    lint_charter_clauses,
)


def run(corpus: DocCorpus | None = None, report: bool = False) -> list[Finding]:
    corpus = corpus or DocCorpus()
    found = [f for lint in GATED_LINTS for f in lint(corpus)]
    if report:
        found += report_single_home_widened(corpus)
    return found


def main(argv: list[str]) -> int:
    found = run(report="--report" in argv)
    blocks = [f for f in found if f.block]
    for f in sorted(found, key=lambda f: (not f.block, f.rule, f.path, f.line)):
        print(f)
    if blocks:
        print(
            f"\ndoc_lints: FAILED — {len(blocks)} block(s), {len(found) - len(blocks)} warning(s)."
        )
        return 1
    print(f"doc_lints: OK — 0 blocks, {len(found)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

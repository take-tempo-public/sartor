#!/usr/bin/env python3
"""Deterministic, stdlib-only near-duplicate-paragraph heuristic — the D5 "single-home" gate.

**Why a heuristic, and why it is documented as one.** `docs/dev/documentation-architecture.md`
("Gates — merge = publish") lists "single-home (D5): a page restates a fact owned elsewhere
instead of linking" as a merge-blocking check. The `ci/doc-merge-gate` lane task itself names
this gate the hardest to automate — genuinely verifying "is this restated or does it just
happen to share a sentence" requires understanding *meaning*, which is exactly the kind of
judgment this deterministic, LLM-free gate is not allowed to make (`hardening.py`/`parser.py`/
etc.'s C-6 boundary applies to this doc-tooling script too: no LLM call here). What IS
mechanically checkable is a narrower, honest proxy: **near-verbatim duplicated prose blocks
across distinct L1 canonical docs** are a strong signal of restatement, since a genuine
cite-don't-restate link never reproduces the cited paragraph's own wording at length. This
script implements exactly that proxy and nothing more — it is a heuristic lint, not a fact
checker, and it says so in its own output.

**What it checks.** For every doc in `check_doc_frontmatter.PUBLISHED_DOC_FILES` (the same
L1 registry gate 2 uses — see that module's docstring for the scope rationale), split the
body into paragraphs (blank-line-separated blocks, fenced code excluded), normalize
whitespace/case, and flag any normalized paragraph of at least `_MIN_PARAGRAPH_CHARS`
characters that appears **byte-identical** (after normalization) in two or more *distinct*
files. Scope is deliberately the small, already-curated L1 registry, not the whole doc tree —
`docs/dev/**`'s review/design corpus legitimately reuses boilerplate (headers, evidence
citation formats, template language) across dozens of files with no restatement judgment made
here; widening this heuristic there would drown the real signal in noise.

**What it deliberately does NOT do** (documented limitation, not an oversight):
  - No near-*miss* matching (paraphrase, reordered clauses, a sentence split differently) —
    only exact-after-normalization matches. A restatement that changes even a few words slips
    through; this is a floor, not a ceiling.
  - No cross-file semantic linking check (whether the "restating" file actually should have
    linked instead) — a human reviews every flagged pair; the gate only narrows attention to
    genuine duplicate text.
  - A short, generic, or structurally-required blockquote (e.g. two files' Purpose/Audience
    header lines happening to phrase something identically) can still slip under
    `_MIN_PARAGRAPH_CHARS` deliberately — the threshold is tuned high enough that only
    substantive multi-sentence duplication trips it (see `_MIN_PARAGRAPH_CHARS`'s rationale).

**Reviewed exclusions** (mirrors `check_doc_links.py`'s `_TEMPLATE_QUOTE_LINKS` idiom — a
narrow, documented (file, file, normalized-paragraph-prefix) allowlist for a duplication a
human has already reviewed and judged intentional, not a general opt-out):
see `_REVIEWED_DUPLICATE_PAIRS` below. Empty at authoring time — the current
`PUBLISHED_DOC_FILES` scope has no reviewed exception; add one only after reading the actual
duplicate pair and confirming it is a deliberate, non-restatement duplication (e.g. a shared
boilerplate line that itself IS the canonical wording, not a copy of it).

Exit 0 clean; exit 1 with the list of duplicated-paragraph pairs found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from check_doc_frontmatter import PUBLISHED_DOC_FILES

REPO_ROOT = Path(__file__).resolve().parent.parent

_FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
_WHITESPACE_RE = re.compile(r"\s+")

# A paragraph must be at least this long (post-normalization) to count as a genuine
# restatement signal rather than a short, structurally-shared phrase (a heading, a single
# cross-reference sentence, a shared boilerplate line). Calibrated against this repo's L1
# docs at authoring time: real prose paragraphs run 200-2000+ chars; anything shorter is
# reliably a heading, list item, or short pointer sentence, not a restated fact.
_MIN_PARAGRAPH_CHARS = 240

# Reviewed, documented exceptions: (file_a, file_b, normalized-paragraph-prefix) tuples a
# human has read and judged an intentional non-restatement duplication. Order-independent
# (checked both ways). Empty at authoring time.
_REVIEWED_DUPLICATE_PAIRS: set[tuple[str, str, str]] = set()


def _iter_unfenced_paragraphs(text: str) -> list[str]:
    """Blank-line-separated blocks, with fenced code blocks skipped entirely."""
    lines = text.splitlines()
    kept: list[str] = []
    in_fence = False
    fence_char: str | None = None
    for line in lines:
        m = _FENCE_RE.match(line)
        if m:
            char = m.group(2)[0]
            if not in_fence:
                in_fence, fence_char = True, char
            elif char == fence_char:
                in_fence, fence_char = False, None
            continue
        if in_fence:
            continue
        kept.append(line)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in kept:
        if line.strip() == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _normalize(paragraph: str) -> str:
    return _WHITESPACE_RE.sub(" ", paragraph).strip().lower()


class DuplicateBlock:
    """One normalized paragraph found verbatim in two or more distinct files."""

    def __init__(self, normalized: str, locations: list[str]) -> None:
        self.normalized = normalized
        self.locations = locations

    def __str__(self) -> str:
        preview = self.normalized[:100] + ("…" if len(self.normalized) > 100 else "")
        return f'{" <-> ".join(self.locations)} :: "{preview}"'


def _is_reviewed_exception(file_a: str, file_b: str, normalized: str) -> bool:
    for a, b, prefix in _REVIEWED_DUPLICATE_PAIRS:
        pair_matches = {a, b} == {file_a, file_b}
        if pair_matches and normalized.startswith(prefix):
            return True
    return False


def check_single_home(files: frozenset[str] = PUBLISHED_DOC_FILES) -> list[DuplicateBlock]:
    """Find normalized paragraphs shared verbatim across 2+ distinct registered files."""
    # normalized paragraph -> list of (file, raw) that contain it
    seen: dict[str, list[str]] = {}
    for rel_path in sorted(files):
        abs_path = REPO_ROOT / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for paragraph in _iter_unfenced_paragraphs(text):
            normalized = _normalize(paragraph)
            if len(normalized) < _MIN_PARAGRAPH_CHARS:
                continue
            seen.setdefault(normalized, [])
            if rel_path not in seen[normalized]:
                seen[normalized].append(rel_path)

    violations: list[DuplicateBlock] = []
    for normalized, locations in seen.items():
        if len(locations) < 2:
            continue
        # Drop reviewed pairs: only flag if at least one non-reviewed pairing remains.
        pairs = [
            (locations[i], locations[j])
            for i in range(len(locations))
            for j in range(i + 1, len(locations))
        ]
        unreviewed = [(a, b) for a, b in pairs if not _is_reviewed_exception(a, b, normalized)]
        if unreviewed:
            violations.append(DuplicateBlock(normalized, locations))
    return violations


def main() -> int:
    violations = check_single_home()
    if not violations:
        print(
            f"check_doc_single_home: OK — {len(PUBLISHED_DOC_FILES)} published doc(s), "
            "no near-verbatim duplicated paragraph found across distinct files."
        )
        return 0

    print(
        f"check_doc_single_home: FAILED — {len(violations)} duplicated paragraph(s) across "
        "distinct L1 docs (D5 single-home — link to the canonical home instead of restating):\n"
    )
    for v in violations:
        print(str(v))
    return 1


if __name__ == "__main__":
    sys.exit(main())

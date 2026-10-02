"""The §5 doc lints — `scripts/doc_lints.py` (docs IA design §5, D4).

WHY: the D4 done criterion (`docs/dev/docs-ia-design.md`, "Verification this design carries
forward") is that every §5 row has a test that **fails on a seeded violation**. A lint that
passes the real tree proves nothing on its own: an empty rule passes too. So each lint gets
two tests here. One runs it on the real tree and expects zero blocks. The other hands it a
small in-memory corpus (`DocCorpus.from_texts`) holding one violation and expects exactly that
finding back.

This module is how the lints ride the gate (`python -m scripts.gate`, the
`pytest -m "not ux"` step); `scripts/gate.py` needs no step of its own for them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_frontmatter as cdf  # noqa: E402 - path insert must precede this import
import doc_lints as dl  # noqa: E402
from doc_corpus import DocCorpus  # noqa: E402
from doc_registry import Entry  # noqa: E402

HEADER = (
    "# T\n\n> **Purpose:** p.\n> **Audience:** `user` — a.\n> **Authoritative for:** x.\n"
    "> **Type:** how-to\n\n"
)
CHARTER = "docs/governance/charter.md"
CHARTER_OK = "".join(f"### C-{n} — Clause {n}\n\nText.\n\n" for n in range(3))


def corpus(texts: dict[str, str]) -> DocCorpus:
    return DocCorpus.from_texts(texts)


def blocks(found: list[dl.Finding], rule: str) -> list[dl.Finding]:
    return [f for f in found if f.rule == rule and f.block]


@pytest.fixture(scope="module")
def real() -> DocCorpus:
    return DocCorpus(REPO_ROOT)


# --- the real tree ---------------------------------------------------------------------


@pytest.mark.parametrize("lint", dl.GATED_LINTS, ids=lambda f: f.__name__)
def test_real_tree_has_no_blocks(real: DocCorpus, lint) -> None:
    found = [f for f in lint(real) if f.block]
    assert not found, "doc lint blocks:\n" + "\n".join(map(str, found))


def test_single_home_widened_never_blocks(real: DocCorpus) -> None:
    """5.9 is report-only (unenforced by design); it must never produce a block."""
    pages = [p for p in real.md_paths if p.startswith("docs/wiki/pages/")][:5]
    assert not [f for f in dl.report_single_home_widened(real, wiki=pages) if f.block]


def test_gate_step_tokens_cover_every_gate_step() -> None:
    """5.5's gate-step tokens are a hand list; a new `scripts/gate.py` step without a token
    would make the drift check blind to it. Every `_STEPS` label must match a token."""
    from scripts.gate import _STEPS

    labels = [label for label, _argv in _STEPS]
    assert labels, "scripts/gate.py has no _STEPS"
    unmatched = [
        lbl for lbl in labels if not any(rx.search(lbl) for rx in dl.GATE_STEP_TOKENS.values())
    ]
    assert not unmatched, f"gate steps with no 5.5 token: {unmatched}"


def test_reviewed_exceptions_still_match_something(real: DocCorpus) -> None:
    """A reviewed exception whose text is gone is dead weight that could later hide a real
    finding in the same doc. Each one must still name text present in its doc."""
    stale = [
        (path, sub)
        for path, _key, sub, _why in dl._REVIEWED_ENUMERATIONS
        if sub not in real.read(path)
    ]
    assert not stale, f"reviewed exceptions whose text is gone: {stale}"


# --- 5.2 audience token (shipped in D2; its seeded test lands here) ----------------------


def test_5_2_audience_token_seeded() -> None:
    doc = "# T\n\n> **Purpose:** p.\n> **Audience:** humans.\n> **Authoritative for:** x.\n"
    found = cdf.check_frontmatter(
        (Entry("docs/user/x.md", "user"),), corpus({"docs/user/x.md": doc})
    )
    assert len(found) == 1 and "Audience token" in str(found[0])


def test_5_2_wrong_tier_seeded() -> None:
    doc = "# T\n\n> **Purpose:** p.\n> **Audience:** `dev` — x.\n> **Authoritative for:** x.\n"
    found = cdf.check_frontmatter(
        (Entry("docs/user/x.md", "user"),), corpus({"docs/user/x.md": doc})
    )
    assert len(found) == 1 and "registry tier `user`" in str(found[0])


# --- 5.3 type ----------------------------------------------------------------------------


def test_5_3_type_seeded() -> None:
    doc = HEADER.replace("> **Type:** how-to\n", "")
    found = dl.lint_type_header(corpus({"a.md": doc, "b.md": HEADER}), ["a.md", "b.md"])
    assert [f.path for f in blocks(found, "5.3")] == ["a.md"]


# --- 5.4 wordmark ------------------------------------------------------------------------


def test_5_4_wordmark_seeded() -> None:
    doc = (
        "# Vision — sartor.\n\n"  # title form: allowed
        "Use sartor. to tailor.\n"  # block
        "The `sartor.` mark and sartor.py are code.\n"  # code: allowed
        "We built sartor.\n\n"  # end of sentence: warn
        "It runs on sartor.\nand more.\n"  # runs into a lowercase line: block
    )
    found = dl.lint_wordmark(corpus({"x.md": doc}), ["x.md"])
    assert [f.line for f in blocks(found, "5.4")] == [3, 7]
    assert [f.line for f in found if not f.block] == [5]


def test_5_4_wordmark_skips_excluded_paths() -> None:
    doc = "Use sartor. to tailor.\n"
    paths = ["docs/wiki/pages/x.md", "docs/dev/reviews/x.md", "CHANGELOG.md"]
    assert not dl.lint_wordmark(corpus({p: doc for p in paths}), paths)


# --- 5.5 enumeration drift ---------------------------------------------------------------


SETS = {"modules": ("a.py", "b.py", "c.py", "d.py", "e.py")}


def test_5_5_named_set_seeded() -> None:
    doc = "- `a.py`, `b.py`, `c.py`, `d.py` make no LLM calls.\n\n- `a.py` and `b.py` parse.\n"
    found = dl.lint_enumeration_drift(corpus({"x.md": doc}), ["x.md"], SETS)
    assert [(f.line, "e.py" in f.message) for f in blocks(found, "5.5")] == [(1, True)]


def test_5_5_gate_steps_seeded() -> None:
    doc = "The quality gate runs `ruff check .` + `mypy .` + `pytest`.\n"
    found = dl.lint_enumeration_drift(corpus({"x.md": doc}), ["x.md"], {})
    assert len(blocks(found, "5.5")) == 1
    ok = "The quality gate is `python -m scripts.gate`; its steps live in `scripts/gate.py`.\n"
    assert not dl.lint_enumeration_drift(corpus({"x.md": ok}), ["x.md"], {})


def test_5_5_charter_range_seeded() -> None:
    texts = {CHARTER: CHARTER_OK, "x.md": "Clauses C-0…C-1 bind.\n\n*[src: once C-0…C-1.]*\n"}
    found = dl.lint_enumeration_drift(corpus(texts), ["x.md"], {})
    assert [f.line for f in blocks(found, "5.5")] == [1]


def test_5_5_tooling_roster_seeded() -> None:
    doc = "## Slash commands\n\n| Command | For |\n|---|---|\n| `eval` | x |\n| `gone` | x |\n"
    tree = {"Slash commands": {"eval", "bench"}}
    found = dl.lint_tooling_roster(corpus({"docs/dev/tooling.md": doc}), tree)
    msgs = sorted(f.message for f in blocks(found, "5.5"))
    assert len(msgs) == 2
    assert "`bench`" in msgs[0] and "exists in the tree" in msgs[0]
    assert "`gone`" in msgs[1] and "not in the tree" in msgs[1]


# --- 5.6 banned words --------------------------------------------------------------------


def test_5_6_banned_words_seeded() -> None:
    doc = "It is simply done. Just run it. It's just a file. We were honest.\n"
    found = dl.lint_banned_words(corpus({"x.md": doc}), ["x.md"])
    assert sorted(f.message for f in blocks(found, "5.6")) == [
        "banned on the user tier: 'Just run'",
        "banned on the user tier: 'simply'",
    ]
    assert [f.message for f in found if not f.block] == ["soft word: 'honest'"]


def test_5_6_lint_allow_only_in_style_guide() -> None:
    doc = "<!-- lint-allow -->\nSimply.\n<!-- /lint-allow -->\n"
    guide = dl._ALLOW_HOME
    found = dl.lint_banned_words(corpus({guide: doc, "x.md": doc}), [guide, "x.md"])
    assert {f.path for f in blocks(found, "5.6")} == {"x.md"}


# --- 5.7 jargon and tracker IDs ----------------------------------------------------------


def test_5_7_acronym_seeded() -> None:
    late = HEADER + "Paste the JD here.\n\nA JD (job description) is the posting.\n"
    early = HEADER + "Acronyms: **JD** =\njob description.\n\nPaste the JD here.\n"
    found = dl.lint_jargon_and_ids(corpus({"a.md": late, "b.md": early}), ["a.md", "b.md"])
    assert [(f.path, "JD" in f.message) for f in blocks(found, "5.7")] == [("a.md", True)]


def test_5_7_tracker_id_seeded() -> None:
    doc = HEADER + "See item 12 and C-3.\n\n<!-- DOC-STATUS: PX-9 -->\n`item 4` is code.\n"
    found = dl.lint_jargon_and_ids(corpus({"x.md": doc}), ["x.md"])
    assert sorted(f.message.split(": ")[1] for f in blocks(found, "5.7")) == ["'C-3'", "'item 12'"]


# --- 5.8 wikilinks and charter clauses ---------------------------------------------------


def test_5_8_wikilink_seeded() -> None:
    doc = "---\ndescription: uses [[backlinks]]\n---\nSee [[page]]. Written as code: `[[page]]`.\n"
    found = dl.lint_wikilinks(corpus({"x.md": doc, "docs/wiki/pages/y.md": "[[page]]\n"}))
    assert [(f.path, f.line) for f in blocks(found, "5.8")] == [("x.md", 4)]


def test_5_8_charter_clauses_seeded() -> None:
    gap = "### C-0 — A\n\n### C-2 — C\n"
    found = dl.lint_charter_clauses(corpus({CHARTER: gap}), [])
    assert len(blocks(found, "5.8")) == 1 and "without gaps" in found[0].message
    texts = {CHARTER: CHARTER_OK, "x.md": "Per C-2 and C-7.\n"}
    found = dl.lint_charter_clauses(corpus(texts), ["x.md"])
    assert [f.message for f in blocks(found, "5.8")] == ["cites C-7; the charter ends at C-2"]


# --- 5.9 single-home widened (report only) -----------------------------------------------


def test_5_9_report_seeded() -> None:
    shared = " ".join(f"w{i}" for i in range(30))
    texts = {"l1.md": shared + "\n", "docs/wiki/pages/p.md": "intro " + shared + "\n"}
    found = dl.report_single_home_widened(corpus(texts), ["l1.md"], ["docs/wiki/pages/p.md"])
    assert len(found) == 1 and not found[0].block and "l1.md" in found[0].message

"""`scripts/wiki_cites.py`: the deterministic cite check for wiki pages (item 166).

Each rule has a synthetic arm that must fire and a clean arm that must not; a checker never
shown to reject a bad input is not evidence of anything. The last class runs the check over the
real tree, which is how it rides the existing `pytest` run as a merge gate (the same shape as
`tests/test_wiki_freshness_gate.py`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

from scripts import wiki_cites as wc

PAGE = "docs/wiki/pages/example.md"


def _tree(tmp_path: Path, files: dict[str, str]) -> wc.Tree:
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return wc.Tree(files, root=tmp_path)


def _violations(tmp_path: Path, page_text: str, extra: dict[str, str] | None = None) -> list[str]:
    files = {
        "mod.py": "def real_symbol():\n    pass\n\n\nclass Thing:\n    def method(self): ...\n"
    }
    files.update(extra or {})
    files[PAGE] = page_text
    tree = _tree(tmp_path, files)
    violations, _ = wc.check_page(PAGE, page_text, tree)
    return [v.rule for v in violations]


class TestE3SymbolCites:
    def test_a_link_labelled_with_a_present_symbol_is_clean(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See [`real_symbol`](../../../mod.py).\n") == []

    def test_a_link_labelled_with_a_missing_symbol_fails(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See [`ghost_symbol`](../../../mod.py).\n") == ["E3"]

    def test_a_path_colon_symbol_cite_is_checked(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See `mod.py:real_symbol` and `mod.py:ghost`.\n") == ["E3"]

    def test_a_dotted_name_is_checked_by_its_last_component(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See `mod.py:Thing.method`.\n") == []
        assert _violations(tmp_path, "See `mod.py:Thing.gone`.\n") == ["E3"]

    def test_a_trailing_call_is_stripped(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See `mod.py:real_symbol()`.\n") == []

    def test_a_substring_is_not_a_match(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See `mod.py:real`.\n") == ["E3"], (
            "`real` occurs inside `real_symbol` but is not the symbol"
        )

    def test_a_filename_label_is_a_path_not_a_symbol(self, tmp_path: Path) -> None:
        """Real tree: 6 false positives before this rule (`[`parser.py`](../../../parser.py)`)."""
        assert _violations(tmp_path, "The [`mod.py`](../../../mod.py) module.\n") == []

    def test_a_fenced_example_is_not_checked(self, tmp_path: Path) -> None:
        page = "```\nmod.py:ghost_symbol\n```\n"
        assert _violations(tmp_path, page) == []

    def test_a_non_code_target_is_not_symbol_checked(self, tmp_path: Path) -> None:
        extra = {"notes.md": "# Heading\n"}
        assert _violations(tmp_path, "See `notes.md:Whatever`.\n", extra) == []


class TestE2LineRange:
    def test_a_line_inside_the_file_is_in_range(self, tmp_path: Path) -> None:
        assert _violations(tmp_path, "See `mod.py:5`.\n") == []

    def test_a_line_past_the_end_fails(self, tmp_path: Path) -> None:
        assert "E2" in _violations(tmp_path, "See `mod.py:900`.\n")

    def test_the_end_of_a_range_is_what_counts(self, tmp_path: Path) -> None:
        assert "E2" in _violations(tmp_path, "See `mod.py:2-900`.\n")
        assert "E2" not in _violations(tmp_path, "See `mod.py:2-5`.\n")

    def test_an_en_dash_range_is_read(self, tmp_path: Path) -> None:
        assert "E2" in _violations(tmp_path, "See `mod.py:2–900`.\n")


class TestE1LineCitesAreCounted:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("See `mod.py:5`.\n", 1),
            ("See `mod.py:2-5`.\n", 1),
            ("See [`mod.py:5`](../../../mod.py) and `mod.py:2`.\n", 2),
            ("In `mod.py`, line 4.\n", 1),
            ("In [`mod.py`](../../../mod.py)\n(lines 2–4).\n", 1),
            ("A sentence about line 4 of nothing.\n", 0),
            ("See `mod.py:real_symbol`.\n", 0),
        ],
    )
    def test_counts(self, tmp_path: Path, text: str, expected: int) -> None:
        files = {"mod.py": "def real_symbol():\n    pass\n\n\nclass Thing: ...\n", PAGE: text}
        tree = _tree(tmp_path, files)
        _, count = wc.check_page(PAGE, text, tree)
        assert count == expected

    def test_an_exact_count_passes_and_one_more_fails(self) -> None:
        assert wc.ratchet({PAGE: 2}, {PAGE: 2}) == []
        assert [v.rule for v in wc.ratchet({PAGE: 3}, {PAGE: 2})] == ["E1"]

    def test_one_fewer_fails_until_the_entry_is_lowered(self) -> None:
        """The ratchet only tightens: fixing a cite forces the allowlist down."""
        violations = wc.ratchet({PAGE: 1}, {PAGE: 2})
        assert [v.rule for v in violations] == ["E1"]
        assert "lower" in violations[0].message

    def test_a_new_page_has_no_allowance(self) -> None:
        assert [v.rule for v in wc.ratchet({"docs/wiki/pages/new.md": 1}, {})] == ["E1"]

    def test_an_entry_for_a_page_with_no_cites_left_is_stale(self) -> None:
        assert [v.rule for v in wc.ratchet({}, {PAGE: 1})] == ["E1"]


class TestE4RemovedCites:
    FILES: ClassVar[dict[str, str]] = {"mod.py": "def real_symbol(): ...\n\n\ndef other(): ...\n"}

    def _removed(self, tmp_path: Path, base: str, current: str) -> list[str]:
        tree = _tree(tmp_path, {**self.FILES, PAGE: current})
        return [v.message for v in wc.removed_symbol_cites(PAGE, base, current, tree)]

    def test_a_dropped_symbol_cite_is_listed(self, tmp_path: Path) -> None:
        base = "See [`real_symbol`](../../../mod.py) and [`other`](../../../mod.py).\n"
        current = "See [`other`](../../../mod.py).\n"
        assert self._removed(tmp_path, base, current) == ["cite mod.py:real_symbol was removed"]

    def test_a_kept_cite_is_not_listed_even_if_it_moved(self, tmp_path: Path) -> None:
        base = "First [`real_symbol`](../../../mod.py).\n"
        current = "Moved: `mod.py:real_symbol`.\n"
        assert self._removed(tmp_path, base, current) == []

    def test_a_cite_whose_target_is_gone_may_be_removed(self, tmp_path: Path) -> None:
        base = "See `mod.py:vanished_symbol`.\n"
        assert self._removed(tmp_path, base, "Nothing now.\n") == []

    def test_a_line_cite_converted_to_a_symbol_is_not_a_removal(self, tmp_path: Path) -> None:
        base = "See `mod.py:1`.\n"
        current = "See `mod.py:real_symbol`.\n"
        assert self._removed(tmp_path, base, current) == []


class TestResolution:
    def test_a_relative_link_resolves_from_the_page_directory(self, tmp_path: Path) -> None:
        tree = _tree(tmp_path, {"a/b.py": "x = 1\n", "docs/wiki/pages/p.md": ""})
        assert tree.resolve_link("docs/wiki/pages/p.md", "../../../a/b.py") == "a/b.py"
        assert tree.resolve_link("docs/wiki/pages/p.md", "../../../missing.py") is None

    def test_a_link_that_escapes_the_repo_is_unresolved(self, tmp_path: Path) -> None:
        tree = _tree(tmp_path, {"a.py": "x = 1\n"})
        assert tree.resolve_link("docs/p.md", "../../../../a.py") is None

    def test_an_ambiguous_bare_name_is_unresolved(self, tmp_path: Path) -> None:
        tree = _tree(tmp_path, {"a/util.py": "x\n", "b/util.py": "y\n"})
        assert tree.resolve_bare("util.py") is None
        assert tree.resolve_bare("a/util.py") == "a/util.py"


class TestTheRealTree:
    """The merge gate: E1-E3 hold over the shipped wiki."""

    @staticmethod
    def _tracked() -> list[str]:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=wc.REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return [line for line in out.stdout.splitlines() if line.strip()]

    def test_the_shipped_wiki_has_no_cite_violations(self) -> None:
        violations, _ = wc.check_tree(wc.Tree(self._tracked()))
        assert violations == [], "\n".join(str(v) for v in violations)

    def test_the_scan_is_not_vacuous(self) -> None:
        """A silent zero would pass the test above with nothing checked."""
        tree = wc.Tree(self._tracked())
        pages = wc.wiki_pages(tree.tracked)
        assert len(pages) > 20, f"only {len(pages)} wiki pages found"
        cites = [c for p in pages for c in wc.extract_cites(p, tree.text(p) or "", tree)]
        symbols = [c for c in cites if c.kind == "symbol" and c.path]
        assert len(symbols) > 200, f"only {len(symbols)} resolved symbol cites"

    def test_every_allowlist_entry_names_a_real_page(self) -> None:
        tracked = set(self._tracked())
        stale = [page for page in wc.ALLOWED_LINE_CITES if page not in tracked]
        assert stale == []

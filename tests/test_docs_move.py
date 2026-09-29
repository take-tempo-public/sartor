"""Tests for `scripts/docs_move.py` and the moved-paths lookup in `scripts/check_doc_links.py`.

WHY: `docs/dev/docs-ia-design.md` §3 is the Epic D link policy. Live docs are rewritten by
script in the move commit, records are never rewritten, and a record's link to a moved doc
resolves through `docs/dev/moved-paths.json`, but only for links whose SOURCE is a record. A
live doc still linking an old path must fail, or the map would hide a missed rewrite. The
pure rewrite functions are tested directly. The end-to-end cases run in a throwaway git repo
with the modules' `REPO_ROOT` pointed at it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_doc_links as cdl  # noqa: E402 - path insert must precede this import
import docs_move as dm  # noqa: E402

MOVES = {
    "docs/install.md": "docs/user/install.md",
    "docs/dev/old-design.md": "docs/dev/archive/old-design.md",
}


# ---------------------------------------------------------------------------
# Pure rewrite functions
# ---------------------------------------------------------------------------


def test_link_to_moved_target_is_rewritten_relative_to_source() -> None:
    assert dm.rewrite_link_target("install.md#setup", "docs/a.md", "docs/a.md", MOVES) == (
        "user/install.md#setup"
    )
    assert dm.rewrite_link_target("docs/install.md", "README.md", "README.md", MOVES) == (
        "docs/user/install.md"
    )


def test_moved_source_rewrites_its_own_outbound_links() -> None:
    # docs/install.md -> docs/user/install.md: its link to ../README.md gains a level.
    assert dm.rewrite_link_target(
        "../README.md", "docs/install.md", "docs/user/install.md", MOVES
    ) == ("../../README.md")


def test_unaffected_links_are_left_alone() -> None:
    for target in ("https://x.test/a.md", "#anchor", "/abs.md", "vision.md", "mailto:a@b.c"):
        assert dm.rewrite_link_target(target, "README.md", "README.md", MOVES) is None


def test_rewrite_text_handles_links_paths_fences_and_backtick_quotes() -> None:
    text = "\n".join(
        [
            "See [install](docs/install.md) and `docs/install.md`.",
            "Quoted: `[x](docs/install.md)` stays.",
            "```",
            "[in fence](docs/install.md) stays; python docs/install.md is rewritten",
            "```",
            "Not a match: docs/install.mdx, mydocs/install.md, docs/dev/install.md.",
        ]
    )
    new, changes = dm.rewrite_text(text, "README.md", "README.md", MOVES)
    lines = new.split("\n")
    assert lines[0] == "See [install](docs/user/install.md) and `docs/user/install.md`."
    # Immediately backtick-wrapped link: the link rule skips it, the exact-path rule does not.
    assert lines[1] == "Quoted: `[x](docs/user/install.md)` stays."
    assert lines[3] == (
        "[in fence](docs/user/install.md) stays; python docs/user/install.md is rewritten"
    )
    assert lines[5] == "Not a match: docs/install.mdx, mydocs/install.md, docs/dev/install.md."
    assert changes


def test_archive_banner_goes_after_the_h1() -> None:
    out = dm.insert_archive_banner("# Title\n\nBody\n")
    assert out.startswith("# Title\n\n> **Archived")
    assert out.endswith("\nBody\n")


# ---------------------------------------------------------------------------
# End-to-end in a throwaway git repo
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    files = {
        "README.md": "# R\n\n[install](docs/install.md#setup)\n",
        "docs/install.md": "# Install\n\n## Setup\n\nBack to [readme](../README.md).\n",
        "docs/dev/old-design.md": "# Old\n\nSee [install](../install.md).\n",
        "docs/dev/handoffs/h.md": "# H\n\nRead [install](../../install.md#setup).\n",
    }
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    monkeypatch.setattr(dm, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cdl, "REPO_ROOT", tmp_path)
    return tmp_path


def _apply(root: Path) -> None:
    dm.apply(MOVES, dm.plan_rewrites(MOVES))
    _git(root, "add", "-A")


def _link_violations() -> list[str]:
    return [str(v) for v in cdl.check_links(cdl.list_md_files())]


def test_apply_moves_rewrites_live_docs_and_leaves_records(repo: Path) -> None:
    _apply(repo)
    assert (repo / "docs/user/install.md").is_file()
    assert not (repo / "docs/install.md").exists()
    assert "(docs/user/install.md#setup)" in (repo / "README.md").read_text(encoding="utf-8")
    assert "(../../README.md)" in (repo / "docs/user/install.md").read_text(encoding="utf-8")
    # Records: the handoff is untouched; the archived doc gets only the banner.
    assert (
        (repo / "docs/dev/handoffs/h.md")
        .read_text(encoding="utf-8")
        .endswith("(../../install.md#setup).\n")
    )
    archived = (repo / "docs/dev/archive/old-design.md").read_text(encoding="utf-8")
    assert "> **Archived" in archived and "(../install.md)" in archived
    assert json.loads((repo / "docs/dev/moved-paths.json").read_text(encoding="utf-8")) == MOVES


def test_record_links_resolve_through_the_map(repo: Path) -> None:
    _apply(repo)
    # The handoff and the archived doc both still carry old-path links, and both pass,
    # including the handoff's #setup anchor, checked against the NEW file.
    assert _link_violations() == []


def test_live_link_to_old_path_still_fails(repo: Path) -> None:
    _apply(repo)
    (repo / "vision.md").write_text("# V\n\n[install](docs/install.md)\n", encoding="utf-8")
    _git(repo, "add", "-A")
    assert any("vision.md" in v and "does not exist" in v for v in _link_violations())


def test_record_link_with_bad_anchor_fails_against_new_target(repo: Path) -> None:
    _apply(repo)
    (repo / "docs/dev/handoffs/h2.md").write_text(
        "# H2\n\n[install](../../install.md#no-such-heading)\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    assert any("h2.md" in v and "anchor not found" in v for v in _link_violations())

"""Wiki-freshness gate — `ci/doc-merge-gate` merge=publish item 5.

WHY: `docs/dev/documentation-architecture.md` ("Gates — merge = publish") lists
"wiki-freshness: the wiki is staler than threshold vs HEAD" as a merge-blocking check, with
the explicit nuance that it *checks* the checkpoint, never runs the LLM ingest itself.
`scripts/wiki_freshness.py` is that deterministic (stdlib + git only, no LLM, no network)
checker — see its module docstring for the threshold rationale and the merge-hook wiring in
`scripts/enforcement/guards/block_merge_to_main.py`. This test (a) exercises `drift_count`/
`check` against synthetic `tmp_path` git repos so the block/allow boundary has real teeth,
then (b) re-runs the real gate as a subprocess against this repo's actual HEAD, matching the
`tests/test_doc_links.py` pattern so it rides the existing `pytest` gate with no new CI job.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "wiki_freshness.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import wiki_freshness as _wiki_freshness  # noqa: E402 - path insert must precede this


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result


def _make_repo_with_wiki(tmp_path: Path, drift_file_count: int) -> tuple[Path, str]:
    """A throwaway repo with a `docs/wiki/.last_ingest_sha` checkpoint, then
    `drift_file_count` additional non-wiki commits after it. Returns (repo, checkpoint_sha)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], cwd=repo)
    _git(["config", "user.email", "test@example.com"], cwd=repo)
    _git(["config", "user.name", "Test"], cwd=repo)

    wiki_dir = repo / "docs" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("wiki placeholder\n", encoding="utf-8")
    _git(["add", "."], cwd=repo)
    _git(["commit", "-q", "-m", "seed wiki"], cwd=repo)
    checkpoint_sha = _git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    (wiki_dir / ".last_ingest_sha").write_text(f"{checkpoint_sha}\n", encoding="utf-8")
    _git(["add", "."], cwd=repo)
    _git(["commit", "-q", "-m", "record checkpoint"], cwd=repo)

    # One commit carrying all N drift files — drift_count() counts changed FILES, not
    # commits, and batching keeps this fixture fast (a 75-commit sequential loop measurably
    # slows the suite; 75 files in a single commit produces an identical git-diff result).
    if drift_file_count:
        for i in range(drift_file_count):
            (repo / f"drift_{i}.md").write_text(f"drift file {i}\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-q", "-m", f"{drift_file_count} drift file(s)"], cwd=repo)

    return repo, checkpoint_sha


class TestWikiFreshnessUnit:
    """`drift_count`/`check` block/allow matrix against synthetic repos."""

    def test_no_baseline_file_is_ok(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(["init", "-q", "-b", "main"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test"], cwd=repo)
        _git(["commit", "-q", "--allow-empty", "-m", "init"], cwd=repo)

        ok, drift = _wiki_freshness.check(repo)
        assert ok
        assert drift is None

    def test_sentinel_baseline_is_ok(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "docs" / "wiki").mkdir(parents=True)
        # The real sentinel convention (docs/wiki/SCHEMA.md "Source model", the literal
        # content of docs/wiki/.last_ingest_sha before the first real /wiki-ingest): prose
        # with no 40-char hex substring at all.
        (repo / "docs" / "wiki" / ".last_ingest_sha").write_text(
            "# no code ingest yet — first /wiki-ingest performs a full cold pass\n",
            encoding="utf-8",
        )
        _git(["init", "-q", "-b", "main"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test"], cwd=repo)
        _git(["add", "."], cwd=repo)
        _git(["commit", "-q", "-m", "init"], cwd=repo)

        assert _wiki_freshness.last_ingest_sha(repo) is None
        ok, drift = _wiki_freshness.check(repo)
        assert ok
        assert drift is None

    def test_small_drift_is_ok(self, tmp_path: Path) -> None:
        repo, _sha = _make_repo_with_wiki(tmp_path, drift_file_count=3)
        ok, drift = _wiki_freshness.check(repo)
        assert ok
        assert drift == 3

    def test_drift_at_or_above_threshold_is_stale(self, tmp_path: Path) -> None:
        repo, _sha = _make_repo_with_wiki(
            tmp_path, drift_file_count=_wiki_freshness.BLOCK_THRESHOLD
        )
        ok, drift = _wiki_freshness.check(repo)
        assert not ok
        assert drift == _wiki_freshness.BLOCK_THRESHOLD

    def test_wiki_only_changes_excluded_from_drift(self, tmp_path: Path) -> None:
        repo, _sha = _make_repo_with_wiki(tmp_path, drift_file_count=0)
        (repo / "docs" / "wiki" / "another_page.md").write_text("more wiki\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-q", "-m", "wiki-only edit"], cwd=repo)

        ok, drift = _wiki_freshness.check(repo)
        assert ok
        assert drift == 0

    def test_docs_site_changes_excluded_from_drift(self, tmp_path: Path) -> None:
        """`docs-site/` is the Fumadocs static export — an L3 projection of the wiki, not a
        wiki source (Carry-forward ledger #1). Its churn must not count as wiki drift, same
        as `docs/wiki/` itself."""
        repo, _sha = _make_repo_with_wiki(tmp_path, drift_file_count=0)
        docs_site = repo / "docs-site" / "content"
        docs_site.mkdir(parents=True)
        for i in range(10):
            (docs_site / f"page_{i}.mdx").write_text(f"projected page {i}\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-q", "-m", "docs-site regeneration"], cwd=repo)

        ok, drift = _wiki_freshness.check(repo)
        assert ok
        assert drift == 0


class TestWikiFreshnessMain:
    """The CLI's exit code follows `check()`."""

    def test_main_exits_zero_when_fresh(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        repo, _sha = _make_repo_with_wiki(tmp_path, drift_file_count=1)
        result = subprocess.run(  # noqa: S603 - static, trusted argv
            [sys.executable, str(CHECKER)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_main_exits_one_when_stale(self, tmp_path: Path) -> None:
        repo, _sha = _make_repo_with_wiki(
            tmp_path, drift_file_count=_wiki_freshness.BLOCK_THRESHOLD
        )
        result = subprocess.run(  # noqa: S603 - static, trusted argv
            [sys.executable, str(CHECKER)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "STALE" in result.stdout


def test_checker_script_exists() -> None:
    """Sanity teeth: a moved/deleted checker script fails loudly, not silently."""
    assert CHECKER.is_file(), f"{CHECKER} is missing — the wiki-freshness gate has nothing to run."


def test_this_repos_wiki_is_fresh_enough_to_merge() -> None:
    """Re-run the bare CLI against this repo's actual HEAD, exactly as CI/the merge hook do.

    Exit 0 = fresh enough (or no baseline yet); exit 1 = run /wiki-self-update or
    /wiki-ingest before merging to main (see scripts/wiki_freshness.py's module docstring).
    """
    result = subprocess.run(  # noqa: S603 - static, trusted argv (sys.executable + a repo-relative path)
        [sys.executable, str(CHECKER)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        "scripts/wiki_freshness.py reports the wiki is stale past the merge-blocking "
        "threshold — run /wiki-self-update (or /wiki-ingest) to advance "
        "docs/wiki/.last_ingest_sha before merging to main:\n" + output
    )

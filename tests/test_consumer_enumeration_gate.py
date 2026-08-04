"""C-10 consumer-enumeration gate — behavior and wiring.

Mirrors `tests/test_evidence_gate.py`'s shape for the C-7 gate: the ceremony primitive,
the guard's decisions, and the wiring that makes it actually run. The classification
registry's own anti-rot audit lives separately in
`tests/test_blast_radius_classification.py`, mirroring the
`wiki_relevance` / `test_wiki_relevance_classification` split.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.enforcement.adapters import claude_dispatcher
from scripts.enforcement.adapters.claude_hook import _GUARD_NAMES
from scripts.enforcement.guards import require_consumer_enumeration as guard

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = _REPO_ROOT / "docs" / "dev" / "blast-radius" / "TEMPLATE.md"
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"

_PLACEHOLDER_ROW = "| 1 | _`path/to/file.py:123`_ | _update / no change / deferred_ | _why_ |"
_REAL_ROW = (
    "| 1 | `db/session.py:41` | update | passes the new column through to every query |\n"
    "| 2 | `db/models.py:88` | update | the column is declared here |"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )


@pytest.fixture
def gated_repo(tmp_path: Path) -> Path:
    """A git repo on `feat/some-change` with TEMPLATE.md, a gated file, and no dossier.

    The initial commit is load-bearing for the same reason `test_evidence_gate.py`'s
    `fix_repo` documents: `git rev-parse --abbrev-ref HEAD` fails on an unborn branch, so a
    repo with no commits reports no branch and every branch-aware guard goes inert.

    The branch is `feat/*`, not `fix/*`, on purpose — C-10 gates every branch type, and a
    `fix/*` fixture would let a `fix/`-only regression pass unnoticed.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    _git(tmp_path, "checkout", "-q", "-b", "feat/some-change")

    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "models.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "blueprints").mkdir()
    (tmp_path / "blueprints" / "applications.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n", encoding="utf-8")
    blast = tmp_path / "docs" / "dev" / "blast-radius"
    blast.mkdir(parents=True)
    shutil.copy(_TEMPLATE, blast / "TEMPLATE.md")
    return tmp_path


def _write_dossier(repo: Path, body: str) -> None:
    dossier = repo / "docs" / "dev" / "blast-radius" / "some-change.md"
    dossier.write_text(
        _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER_ROW, body),
        encoding="utf-8",
    )


def _blocked(repo: Path, relative: str) -> bool:
    """True if the guard BLOCKS an edit to `relative` inside `repo`."""
    env = {"CLAUDE_PROJECT_DIR": str(repo)}
    return guard.decide(str(repo / relative), env).blocked


class TestEnumerationPrimitive:
    def test_untouched_template_does_not_satisfy_the_gate(self) -> None:
        """A `cp` must not buy you the right to edit a contract."""
        text = _TEMPLATE.read_text(encoding="utf-8")
        assert not guard.has_consumer_enumeration(text, "db/models.py", text)
        # ...and not even without the template comparison: the guidance prose lives in
        # HTML comments precisely so the character floor alone still rejects it.
        assert not guard.has_consumer_enumeration(text, "db/models.py")

    def test_filled_consumers_naming_the_surface_satisfies_the_gate(self) -> None:
        text = _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER_ROW, _REAL_ROW)
        assert guard.has_consumer_enumeration(
            text, "db/models.py", _TEMPLATE.read_text(encoding="utf-8")
        )

    def test_a_dossier_for_another_surface_does_not_count(self) -> None:
        """The whole point: one enumeration must not rubber-stamp an unrelated contract."""
        text = _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER_ROW, _REAL_ROW)
        assert not guard.has_consumer_enumeration(text, "ui_pages/selectors.py")

    def test_basename_mention_is_enough(self) -> None:
        """A table row written `models.py:88` still names the surface."""
        text = _TEMPLATE.read_text(encoding="utf-8").replace(
            _PLACEHOLDER_ROW, "| 1 | `models.py:88` | update | declared here, ripples outward |"
        )
        assert guard.has_consumer_enumeration(text, "db/models.py")

    def test_dossier_path_strips_the_type_prefix(self) -> None:
        assert (
            guard.dossier_path(Path("/repo"), "feat/a-b")
            .as_posix()
            .endswith("docs/dev/blast-radius/a-b.md")
        )


class TestRequireConsumerEnumerationGuard:
    def test_blocks_a_gated_surface_with_no_dossier(self, gated_repo: Path) -> None:
        assert _blocked(gated_repo, "db/models.py")

    def test_blocks_when_the_dossier_is_an_untouched_template(self, gated_repo: Path) -> None:
        shutil.copy(_TEMPLATE, gated_repo / "docs/dev/blast-radius/some-change.md")
        assert _blocked(gated_repo, "db/models.py")

    def test_allows_once_consumers_is_filled_in(self, gated_repo: Path) -> None:
        _write_dossier(gated_repo, _REAL_ROW)
        assert not _blocked(gated_repo, "db/models.py")

    def test_blocks_a_different_gated_surface_the_dossier_never_names(
        self, gated_repo: Path
    ) -> None:
        """Filling in one surface must not unlock every other gated file on the branch."""
        (gated_repo / "ui_pages").mkdir()
        (gated_repo / "ui_pages" / "selectors.py").write_text("x = 1\n", encoding="utf-8")
        _write_dossier(gated_repo, _REAL_ROW)
        assert _blocked(gated_repo, "ui_pages/selectors.py")

    def test_allows_an_unclassified_file(self, gated_repo: Path) -> None:
        """The gate must be quiet on ordinary work, or it becomes noise people route around."""
        assert not _blocked(gated_repo, "blueprints/applications.py")

    @pytest.mark.parametrize(
        "relative",
        [
            "docs/dev/blast-radius/some-change.md",  # the remedy itself
            "tests/test_x.py",  # proving a consumer still works
        ],
    )
    def test_allows_what_you_need_to_produce_the_enumeration(
        self, gated_repo: Path, relative: str
    ) -> None:
        assert not _blocked(gated_repo, relative)

    def test_the_blast_radius_template_is_not_exempted_by_its_own_directory(
        self, gated_repo: Path
    ) -> None:
        """A blanket `docs/dev/blast-radius/` exemption would make TEMPLATE.md's registry
        entry dead code — the dossier stays writable, the template does not."""
        assert _blocked(gated_repo, "docs/dev/blast-radius/TEMPLATE.md")

    def test_gates_on_a_feat_branch_not_only_fix(self, gated_repo: Path) -> None:
        """C-10's departure from C-7: schema changes normally land on `feat/*`."""
        assert _git_branch(gated_repo) == "feat/some-change"
        assert _blocked(gated_repo, "db/models.py")

    def test_gates_a_migration_by_prefix(self, gated_repo: Path) -> None:
        versions = gated_repo / "db" / "migrations" / "versions"
        versions.mkdir(parents=True)
        (versions / "0012_x.py").write_text("x = 1\n", encoding="utf-8")
        assert _blocked(gated_repo, "db/migrations/versions/0012_x.py")

    def test_never_wedges_outside_a_git_repo(self, tmp_path: Path) -> None:
        env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
        assert not guard.decide(str(tmp_path / "db" / "models.py"), env).blocked

    def test_block_message_names_the_file_to_write_and_why(self, gated_repo: Path) -> None:
        env = {"CLAUDE_PROJECT_DIR": str(gated_repo)}
        result = guard.decide(str(gated_repo / "db" / "models.py"), env)
        joined = "\n".join(result.messages)
        assert "docs/dev/blast-radius/some-change.md" in joined
        assert "C-10" in joined
        assert "Why this file is gated:" in joined
        # ASCII only -- hook stderr lands on a cp1252 console on Windows.
        joined.encode("ascii")


def _git_branch(repo: Path) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


class TestWiring:
    """A guard nobody runs is a paragraph with extra steps."""

    def test_guard_is_registered_in_the_claude_adapter(self) -> None:
        assert "require-consumer-enumeration" in _GUARD_NAMES

    def test_guard_is_dispatched_on_edit_write(self) -> None:
        assert "require-consumer-enumeration" in claude_dispatcher._GUARD_ORDER

    def test_dispatcher_is_wired_in_settings(self) -> None:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in settings["hooks"]["PreToolUse"]
            if entry["matcher"] == "Edit|Write"
            for hook in entry["hooks"]
        ]
        assert any("edit-write-dispatcher.sh" in command for command in commands)

    def test_template_exists_where_the_block_message_says_it_does(self) -> None:
        assert _TEMPLATE.is_file()

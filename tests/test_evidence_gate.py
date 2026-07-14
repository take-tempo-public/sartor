"""The C-7 / C-8 enforcement must not rot — the guidance already did once.

`docs/dev/AGENT_FAILURE_PATTERNS.md` §5a/5b/5e told an agent to instrument before fixing. It
read them, judged them inapplicable, and burned a day shipping two confidently-wrong fixes for
a bug it had never observed. Advice that an agent may overrule is not a control. So the rule
became a hook — and a hook nobody tests is just advice with more steps.

This module is the committed gate on the gate:

- the three enforcement points are **wired** in `.claude/settings.json` and their scripts exist;
- the guard **blocks** production edits on a `fix/*` branch with no evidence, and **allows** the
  very things you need in order to produce that evidence (docs, tests, prose);
- **an untouched copy of `TEMPLATE.md` does not satisfy the gate** — hand-testing caught it
  doing exactly that, and a gate a `cp` can satisfy is theater;
- the SessionStart replay carries `## Observed` + `## Falsified` and **never `## Inferred`** —
  an unproven mechanism re-injected as context reads as established fact within a few turns,
  which is the rot the whole clause exists to prevent.

See `docs/dev/diagnosis/compose-summary-draft-settle-hole.md` for the worked failure.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.enforcement.adapters import claude_context_hook
from scripts.enforcement.adapters.claude_hook import _GUARD_NAMES
from scripts.enforcement.evidence import (
    branch_slug,
    diagnosis_path,
    has_observed_evidence,
    replay_text,
    section,
    template_text,
)
from scripts.enforcement.guards import require_evidence_before_fix as guard

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = _REPO_ROOT / "docs" / "dev" / "diagnosis" / "TEMPLATE.md"

#: The dossier's `## Observed` placeholder, replaced to simulate "an agent actually looked".
_PLACEHOLDER = (
    "_(Nothing yet. Instrument first. If you cannot fill this in, you have not looked — and that_\n"
    "_is the finding, not an obstacle to it.)_"
)
_REAL_EVIDENCE = "- CI run 29303444590: POST /draft-summary returned 200 and persisted nothing."


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S607


@pytest.fixture
def fix_repo(tmp_path: Path) -> Path:
    """A git repo on `fix/some-bug` with a real HEAD, TEMPLATE.md, and no dossier.

    The initial commit is load-bearing: `git rev-parse --abbrev-ref HEAD` fails on an unborn
    branch, so a repo with no commits reports no branch at all and every branch-aware guard
    goes inert. (Learned the hard way while hand-testing this guard — the first run "passed"
    only because nothing was being checked.)
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S607
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    _git(tmp_path, "checkout", "-q", "-b", "fix/some-bug")

    (tmp_path / "blueprints").mkdir()
    (tmp_path / "blueprints" / "applications.py").write_text("x = 1\n", encoding="utf-8")
    diagnosis = tmp_path / "docs" / "dev" / "diagnosis"
    diagnosis.mkdir(parents=True)
    shutil.copy(_TEMPLATE, diagnosis / "TEMPLATE.md")
    return tmp_path


def _decide(repo: Path, relative: str) -> bool:
    """True if the guard BLOCKS an edit to `relative` inside `repo`."""
    env = {"CLAUDE_PROJECT_DIR": str(repo)}
    return guard.decide(str(repo / relative), env).blocked


class TestEvidencePrimitive:
    def test_untouched_template_does_not_satisfy_the_gate(self) -> None:
        """A `cp` must not buy you the right to edit production code."""
        text = _TEMPLATE.read_text(encoding="utf-8")
        assert not has_observed_evidence(text, text)
        # ...and not even without the template comparison: the guidance prose lives in HTML
        # comments precisely so the character floor alone still rejects it.
        assert not has_observed_evidence(text)

    def test_filled_observed_satisfies_the_gate(self) -> None:
        text = _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER, _REAL_EVIDENCE)
        assert has_observed_evidence(text, _TEMPLATE.read_text(encoding="utf-8"))

    def test_branch_slug_strips_the_type_prefix(self) -> None:
        assert branch_slug("fix/compose-summary-draft-settle-hole") == (
            "compose-summary-draft-settle-hole"
        )
        assert diagnosis_path(Path("/repo"), "fix/a-b").as_posix().endswith(
            "docs/dev/diagnosis/a-b.md"
        )

    def test_section_extraction_is_bounded_by_the_next_heading(self) -> None:
        text = "## Observed\n\nseen it\n\n## Inferred\n\nguessed it\n"
        assert section(text, "Observed").strip() == "seen it"
        assert section(text, "Inferred").strip() == "guessed it"


class TestRequireEvidenceBeforeFixGuard:
    def test_blocks_production_code_with_no_dossier(self, fix_repo: Path) -> None:
        assert _decide(fix_repo, "blueprints/applications.py")

    def test_blocks_when_the_dossier_is_an_untouched_template(self, fix_repo: Path) -> None:
        shutil.copy(_TEMPLATE, fix_repo / "docs/dev/diagnosis/some-bug.md")
        assert _decide(fix_repo, "blueprints/applications.py")

    def test_allows_once_observed_is_filled_in(self, fix_repo: Path) -> None:
        dossier = fix_repo / "docs/dev/diagnosis/some-bug.md"
        dossier.write_text(
            _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER, _REAL_EVIDENCE),
            encoding="utf-8",
        )
        assert not _decide(fix_repo, "blueprints/applications.py")

    @pytest.mark.parametrize(
        "relative",
        [
            "docs/dev/diagnosis/some-bug.md",  # the dossier itself
            "tests/test_repro.py",  # the instrument / the reproduction
            "CHANGELOG.md",  # prose
        ],
    )
    def test_allows_what_you_need_to_produce_the_evidence(
        self, fix_repo: Path, relative: str
    ) -> None:
        """The guard must never forbid its own remedy — that would be a wedge, not a gate."""
        assert not _decide(fix_repo, relative)

    def test_allows_on_a_non_fix_branch(self, fix_repo: Path) -> None:
        _git(fix_repo, "checkout", "-q", "-b", "chore/deps")
        assert not _decide(fix_repo, "blueprints/applications.py")

    def test_block_message_names_the_file_to_write(self, fix_repo: Path) -> None:
        messages = guard.decide(
            str(fix_repo / "blueprints/applications.py"), {"CLAUDE_PROJECT_DIR": str(fix_repo)}
        ).messages
        joined = "\n".join(messages)
        assert "docs/dev/diagnosis/some-bug.md" in joined
        assert "C-7" in joined
        # ASCII only: hook stderr hits a cp1252 console on Windows, where anything else
        # arrives as replacement characters.
        assert joined.isascii(), "guard messages must be ASCII"


class TestSessionStartReplay:
    def test_replays_observed_and_falsified_but_never_inferred(self) -> None:
        text = (
            "## Observed\n\nthe POST persisted, the GET did not have it\n\n"
            "## Falsified\n\ndependency float: byte-identical package sets\n\n"
            "## Inferred\n\n/recommend is probably the eraser\n"
        )
        replay = replay_text(text)
        assert "the POST persisted" in replay
        assert "dependency float" in replay
        assert "probably the eraser" not in replay, (
            "an unproven mechanism re-injected as context reads as fact within a few turns"
        )

    def test_stays_silent_on_a_branch_with_no_dossier(self, fix_repo: Path) -> None:
        payload = {"hook_event_name": "SessionStart", "cwd": str(fix_repo)}
        assert claude_context_hook.restore_evidence(payload) == ""

    def test_precompact_warns_only_when_evidence_is_missing(self, fix_repo: Path) -> None:
        payload = {"hook_event_name": "PreCompact", "cwd": str(fix_repo)}
        assert "no captured evidence" in claude_context_hook.capture_before_compact(payload)

        dossier = fix_repo / "docs/dev/diagnosis/some-bug.md"
        dossier.write_text(
            _TEMPLATE.read_text(encoding="utf-8").replace(_PLACEHOLDER, _REAL_EVIDENCE),
            encoding="utf-8",
        )
        assert claude_context_hook.capture_before_compact(payload) == ""


class TestEnforcementIsWired:
    """A guard nobody calls is a comment. Assert the wiring, not just the logic."""

    def test_guard_is_registered_in_the_claude_adapter(self) -> None:
        assert "require-evidence-before-fix" in _GUARD_NAMES

    @pytest.mark.parametrize(
        ("event", "script"),
        [
            ("PreToolUse", "require-evidence-before-fix.sh"),
            ("SessionStart", "restore-evidence.sh"),
            ("PreCompact", "capture-before-compact.sh"),
        ],
    )
    def test_hook_is_wired_in_settings_and_exists_on_disk(self, event: str, script: str) -> None:
        settings = json.loads((_REPO_ROOT / ".claude" / "settings.json").read_text("utf-8"))
        wired = json.dumps(settings["hooks"][event])
        assert script in wired, f"{script} is not wired under {event} in .claude/settings.json"
        assert (_REPO_ROOT / ".claude-plugin" / "hooks" / script).is_file()

    def test_session_start_matches_compact_not_just_startup(self) -> None:
        """The `compact` matcher is the whole point — it is what survives a compaction."""
        settings = json.loads((_REPO_ROOT / ".claude" / "settings.json").read_text("utf-8"))
        matchers = [entry["matcher"] for entry in settings["hooks"]["SessionStart"]]
        assert any("compact" in m for m in matchers)

    def test_template_exists_where_the_block_message_says_it_does(self) -> None:
        assert _TEMPLATE.is_file()
        assert template_text(_REPO_ROOT) != ""

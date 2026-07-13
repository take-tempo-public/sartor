"""Portable-enforcement-core equivalence + regression suite (`feat/portable-
enforcement-core`, 2026-07-08).

Two layers:

1. **Unit matrix** — each guard's pure `decide()` (or nearest equivalent)
   exercised directly with a block/allow/edge matrix (>=3 cases per guard).
   Fast; no subprocesses.
2. **OLD-vs-NEW equivalence** — the pre-migration standalone
   `.claude-plugin/hooks/*.sh` scripts (extracted from git history at
   `OLD_SHA`, the merge-train-4 base / `main` tip at authoring time) run
   side-by-side with the migrated wrappers (which now exec the shared
   `scripts/enforcement/` core) against byte-correct PreToolUse JSON (built
   with `json.dumps`, never echo/heredoc — see `docs/dev/AGENT_FAILURE_
   PATTERNS.md` precedent), asserting matching exit codes + block-message
   substance. Includes the two dedicated regression cases for the defects
   fixed while lifting `block-merge-to-main` (RELEASE_CHECKLIST.md
   "Portable-enforcement-core migration" ledger row, Train-1 note,
   2026-07-07): the `merge-base`/`merge-tree` false positive, and resolving
   HEAD against the invocation's own cwd instead of the hook process's
   ambient cwd.

Both layers matter: layer 1 is what keeps working after `OLD_SHA` eventually
scrolls out of easy reach; layer 2 is the actual migration proof this branch
needs to land safely (CRITICAL SAFETY: a behavior regression here governs
every future agent session in this repo).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.enforcement.guards import (
    block_merge_to_main,
    block_secrets,
    require_feature_branch,
    route_security_lint,
    ruff_changed,
    validate_context,
)
from scripts.wiki_freshness import BLOCK_THRESHOLD as WIKI_BLOCK_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".claude-plugin" / "hooks"
# The merge-train-4 base this branch forked from (env block: "isolated git
# worktree of this repo at main b2c83d2") — the last commit before this
# migration, so `git show OLD_SHA:<path>` is the pre-migration standalone hook.
OLD_SHA = "b2c83d2"

GUARD_FILES = {
    "require-feature-branch": "require-feature-branch.sh",
    "block-merge-to-main": "block-merge-to-main.sh",
    "block-secrets": "block-secrets.sh",
    "route-security-lint": "route-security-lint.sh",
    "ruff-changed": "ruff-changed.sh",
    "validate-context": "validate-context.sh",
}


def _git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
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


def _make_repo(tmp_path: Path, name: str, branch: str) -> Path:
    """A throwaway git repo checked out to `branch`, one empty commit."""
    repo = tmp_path / name
    repo.mkdir()
    _git(["init", "-q", "-b", branch], cwd=repo)
    _git(["config", "user.email", "test@example.com"], cwd=repo)
    _git(["config", "user.name", "Test"], cwd=repo)
    _git(["commit", "-q", "--allow-empty", "-m", "init"], cwd=repo)
    return repo


def _add_wiki_checkpoint(repo: Path, drift_file_count: int = 0) -> None:
    """Layer a `docs/wiki/.last_ingest_sha` checkpoint onto a `_make_repo` repo (checkpoint =
    current HEAD), then optionally commit `drift_file_count` more tracked files after it —
    `ci/doc-merge-gate`'s wiki-freshness extension to `block_merge_to_main` fixture helper."""
    wiki_dir = repo / "docs" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_sha = _git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    (wiki_dir / ".last_ingest_sha").write_text(f"{checkpoint_sha}\n", encoding="utf-8")
    _git(["add", "."], cwd=repo)
    _git(["commit", "-q", "-m", "record wiki checkpoint"], cwd=repo)
    if drift_file_count:
        for i in range(drift_file_count):
            (repo / f"drift_{i}.md").write_text(f"drift {i}\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-q", "-m", f"{drift_file_count} drift file(s)"], cwd=repo)


@pytest.fixture(scope="module")
def old_hooks(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Extract the pre-migration standalone hook scripts at OLD_SHA.

    OLD_SHA is a historical commit (pre hook-modularization). A shallow clone
    (GitHub Actions' default ``fetch-depth: 1``, or a contributor's ``git clone
    --depth``) doesn't fetch that object, so ``git show`` would hard-fail with
    "invalid object name". CI sets ``fetch-depth: 0`` so these equivalence tests
    run there; anywhere the object is genuinely unreachable, skip gracefully
    rather than fail.
    """
    probe = subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", "cat-file", "-e", f"{OLD_SHA}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(
            f"OLD_SHA {OLD_SHA} not reachable (shallow clone) — "
            "these pre-migration hook-equivalence checks need full git history"
        )
    out_dir = tmp_path_factory.mktemp("old_hooks")
    paths: dict[str, Path] = {}
    for name, filename in GUARD_FILES.items():
        result = _git(["show", f"{OLD_SHA}:.claude-plugin/hooks/{filename}"], cwd=REPO_ROOT)
        dest = out_dir / filename
        dest.write_text(result.stdout, encoding="utf-8", newline="\n")
        paths[name] = dest
    return paths


def _run_hook(
    script_path: Path,
    payload: dict,
    *,
    subprocess_cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Run one hook script (old or new) against a PreToolUse-shaped payload.

    `subprocess_cwd` is the hook PROCESS's own ambient cwd — this is
    deliberately a separate knob from `payload["cwd"]` (the PreToolUse
    hook-input field) so the equivalence tests can prove the two only matter
    to the OLD script (which conflates them) and not the NEW one (which reads
    `payload["cwd"]` explicitly) — see the defect-ii regression test below.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDE_ALLOW_MAIN_EDITS", "CLAUDE_CONFIRM_MERGE")
    }
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(  # noqa: S603 - fixed argv (bash + a known script path), test-authored input
        ["bash", str(script_path)],
        input=json.dumps(payload),
        cwd=str(subprocess_cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    return result.returncode, result.stderr


def _run_old(old_hooks: dict[str, Path], name: str, payload: dict, **kwargs) -> tuple[int, str]:
    return _run_hook(old_hooks[name], payload, **kwargs)


def _run_new(name: str, payload: dict, **kwargs) -> tuple[int, str]:
    return _run_hook(HOOKS_DIR / GUARD_FILES[name], payload, **kwargs)


def _assert_equivalent(
    old_result: tuple[int, str],
    new_result: tuple[int, str],
    *,
    message_substrings: tuple[str, ...] = (),
) -> None:
    old_code, old_err = old_result
    new_code, new_err = new_result
    assert old_code == new_code, (
        f"exit code mismatch: old={old_code!r} new={new_code!r}\nold stderr={old_err!r}\nnew stderr={new_err!r}"
    )
    for substring in message_substrings:
        assert substring in old_err, f"OLD stderr missing {substring!r}: {old_err!r}"
        assert substring in new_err, f"NEW stderr missing {substring!r}: {new_err!r}"


# --------------------------------------------------------------------------- #
# 1. Unit matrix — pure decide() functions, >=3 cases each (block/allow/edge)
# --------------------------------------------------------------------------- #


class TestRequireFeatureBranchUnit:
    def test_block_on_main(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "on_main", "main")
        result = require_feature_branch.decide(str(repo / "app.py"), {})
        assert result.blocked
        assert "require-feature-branch" in result.messages[0]

    def test_allow_on_feature_branch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "on_feature", "feat/x")
        result = require_feature_branch.decide(str(repo / "app.py"), {})
        assert not result.blocked

    def test_allow_escape_hatch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "on_main_hatch", "main")
        result = require_feature_branch.decide(
            str(repo / "app.py"), {"CLAUDE_ALLOW_MAIN_EDITS": "1"}
        )
        assert not result.blocked

    def test_allow_plans_dir_exempt(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "on_main_plans", "main")
        result = require_feature_branch.decide(str(repo / ".claude" / "plans" / "x.md"), {})
        assert not result.blocked

    def test_allow_not_a_repo(self, tmp_path: Path) -> None:
        stray = tmp_path / "not_a_repo"
        stray.mkdir()
        result = require_feature_branch.decide(str(stray / "app.py"), {})
        assert not result.blocked


class TestBlockMergeToMainUnit:
    def test_block_merge_command_on_main(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_main", "main")
        result = block_merge_to_main.decide("git merge feature-x --no-ff", str(repo))
        assert result.blocked

    def test_allow_merge_command_on_feature_branch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_feature", "feat/y")
        result = block_merge_to_main.decide("git merge other-branch --no-ff", str(repo))
        assert not result.blocked

    def test_allow_confirm_escape_hatch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_confirm", "main")
        result = block_merge_to_main.decide(
            "CLAUDE_CONFIRM_MERGE=1 git merge feature-x --no-ff", str(repo)
        )
        assert not result.blocked

    def test_block_push_to_main_directly(self, tmp_path: Path) -> None:
        # Direct regex match — doesn't need branch resolution at all.
        result = block_merge_to_main.decide("git push origin main", str(tmp_path))
        assert result.blocked

    def test_allow_push_to_feature_branch(self, tmp_path: Path) -> None:
        result = block_merge_to_main.decide("git push origin feature-x", str(tmp_path))
        assert not result.blocked

    def test_allow_unrelated_command(self, tmp_path: Path) -> None:
        result = block_merge_to_main.decide("git status", str(tmp_path))
        assert not result.blocked

    # --- defect (i): merge-base / merge-tree false positive -----------------
    def test_defect_i_merge_base_is_not_a_merge(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_base_main", "main")
        result = block_merge_to_main.decide("git merge-base main HEAD", str(repo))
        assert not result.blocked, "read-only `git merge-base` must never block"

    def test_defect_i_merge_tree_is_not_a_merge(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_tree_main", "main")
        result = block_merge_to_main.decide("git merge-tree main feature-x", str(repo))
        assert not result.blocked, "read-only `git merge-tree` must never block"

    def test_defect_i_real_merge_still_caught(self, tmp_path: Path) -> None:
        # The tightened regex must still catch the real thing right next to the
        # plumbing command it now excludes.
        repo = _make_repo(tmp_path, "merge_base_then_real", "main")
        result = block_merge_to_main.decide("git merge feature-x --no-ff", str(repo))
        assert result.blocked

    # --- defect (ii): cwd resolved in the invocation's own worktree ---------
    def test_defect_ii_resolves_invocation_cwd_not_ambient(self, tmp_path: Path) -> None:
        main_repo = _make_repo(tmp_path, "defect_ii_main", "main")
        feature_repo = _make_repo(tmp_path, "defect_ii_feature", "feat/z")
        # A command with no literal "main"/"master" token, so only the
        # dominant-direction (cwd-based) branch check can possibly fire.
        command = "git merge other-branch --no-ff"
        assert not block_merge_to_main.decide(command, str(feature_repo)).blocked
        assert block_merge_to_main.decide(command, str(main_repo)).blocked

    # --- wiki-freshness extension (ci/doc-merge-gate, merge=publish gate 5) --
    def test_wiki_freshness_blocks_even_with_confirm_hatch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_confirm_stale_wiki", "main")
        _add_wiki_checkpoint(repo, drift_file_count=WIKI_BLOCK_THRESHOLD)
        result = block_merge_to_main.decide(
            "CLAUDE_CONFIRM_MERGE=1 git merge feature-x --no-ff", str(repo)
        )
        assert result.blocked, "stale wiki must block even with the merge-target confirm hatch"
        assert "wiki" in " ".join(result.messages).lower()

    def test_wiki_freshness_allows_confirm_hatch_when_fresh(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "merge_confirm_fresh_wiki", "main")
        _add_wiki_checkpoint(repo, drift_file_count=1)
        result = block_merge_to_main.decide(
            "CLAUDE_CONFIRM_MERGE=1 git merge feature-x --no-ff", str(repo)
        )
        assert not result.blocked

    def test_wiki_freshness_allows_when_no_baseline_yet(self, tmp_path: Path) -> None:
        # No docs/wiki/ dir at all — same repo shape every other test in this class uses.
        repo = _make_repo(tmp_path, "merge_confirm_no_wiki", "main")
        result = block_merge_to_main.decide(
            "CLAUDE_CONFIRM_MERGE=1 git merge feature-x --no-ff", str(repo)
        )
        assert not result.blocked

    def test_wiki_freshness_not_reached_without_confirm_hatch(self, tmp_path: Path) -> None:
        # Missing-confirm blocks first, on its own message — the wiki check is never reached
        # (and if it were, this fixture's stale wiki would block too, so this also proves
        # ordering: the cheaper/simpler check short-circuits first).
        repo = _make_repo(tmp_path, "merge_no_confirm_stale_wiki", "main")
        _add_wiki_checkpoint(repo, drift_file_count=WIKI_BLOCK_THRESHOLD)
        result = block_merge_to_main.decide("git merge feature-x --no-ff", str(repo))
        assert result.blocked
        assert result.messages == block_merge_to_main._MESSAGE_LINES

    def test_git_operation_check_blocks_on_stale_wiki(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "op_stale_wiki", "main")
        _add_wiki_checkpoint(repo, drift_file_count=WIKI_BLOCK_THRESHOLD)
        result = block_merge_to_main.git_operation_check(
            "main", env={"CLAUDE_CONFIRM_MERGE": "1"}, repo_root=str(repo)
        )
        assert result.blocked

    def test_git_push_check_blocks_on_stale_wiki(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "push_stale_wiki", "main")
        _add_wiki_checkpoint(repo, drift_file_count=WIKI_BLOCK_THRESHOLD)
        result = block_merge_to_main.git_push_check(
            "refs/heads/main", env={"CLAUDE_CONFIRM_MERGE": "1"}, repo_root=str(repo)
        )
        assert result.blocked


class TestBlockSecretsUnit:
    def test_block_api_key_in_command(self) -> None:
        result = block_secrets.decide("Bash", {"command": "echo sk-ant-" + "a" * 30})
        assert result.blocked
        assert "Anthropic API key" in result.messages[0]

    def test_allow_ordinary_edit(self) -> None:
        result = block_secrets.decide("Edit", {"file_path": "app.py", "new_string": "x = 1"})
        assert not result.blocked

    def test_block_write_to_dotenv(self) -> None:
        result = block_secrets.decide(
            "Write", {"file_path": "configs/.env.local", "content": "X=1"}
        )
        assert result.blocked
        assert "secret file" in result.messages[0]

    def test_allow_write_to_lookalike_path(self) -> None:
        # "app.env" doesn't match the anchored secret-path pattern (must be
        # exactly `.env`/`.env.<suffix>`/`.api_key`/... as the whole basename).
        result = block_secrets.decide("Write", {"file_path": "configs/app.env", "content": "X=1"})
        assert not result.blocked

    def test_allow_read_of_secret_path(self) -> None:
        # Pattern 2 (secret-file path) only applies to Edit/Write.
        result = block_secrets.decide("Read", {"file_path": ".api_key"})
        assert not result.blocked

    def test_block_hardcoded_env_assignment(self) -> None:
        result = block_secrets.decide(
            "Bash", {"command": "ANTHROPIC_API_KEY=" + "b" * 20 + " python app.py"}
        )
        assert result.blocked
        assert "env-var assignment" in result.messages[0]


class TestRouteSecurityLintUnit:
    _GOOD = "_safe_username(u)\n_within(p, OUTPUT_DIR)\nopen(p)"
    _BAD = "p = OUTPUT_DIR / u\nopen(p)"

    def test_block_unguarded_fs_route(self) -> None:
        content = f'@bp.route("/x/<u>")\ndef f(u):\n    {self._BAD}'
        result = route_security_lint.decide("blueprints/foo.py", content)
        assert result.blocked
        assert "_safe_username()" in result.messages[1]
        assert "_within()" in result.messages[1]

    def test_allow_guarded_fs_route(self) -> None:
        content = f'@bp.route("/x/<u>")\ndef f(u):\n    {self._GOOD}'
        result = route_security_lint.decide("blueprints/foo.py", content)
        assert not result.blocked

    def test_allow_non_route_file(self) -> None:
        content = f'@bp.route("/x/<u>")\ndef f(u):\n    {self._BAD}'
        result = route_security_lint.decide("utils.py", content)
        assert not result.blocked

    def test_allow_route_without_fs_indicator(self) -> None:
        content = '@bp.route("/x")\ndef f():\n    return jsonify({})'
        result = route_security_lint.decide("blueprints/foo.py", content)
        assert not result.blocked

    def test_allow_partially_guarded_reports_only_missing(self) -> None:
        content = f'@bp.route("/x/<u>")\ndef f(u):\n    _safe_username(u)\n    {self._BAD}'
        result = route_security_lint.decide("blueprints/foo.py", content)
        assert result.blocked
        assert "_safe_username()" not in result.messages[1]
        assert "_within()" in result.messages[1]


class TestRuffChangedUnit:
    def test_allow_no_staged_files(self) -> None:
        result = ruff_changed.check_files([])
        assert not result.blocked

    def test_block_lint_violation(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.py"
        bad.write_text("import os\nx=1\n", encoding="utf-8")  # unused import + no-space-around-=
        result = ruff_changed.check_files([str(bad)])
        assert result.blocked
        assert "ruff-changed" in result.messages[-2] or "ruff-changed" in "".join(result.messages)

    def test_allow_clean_formatted_file(self, tmp_path: Path) -> None:
        good = tmp_path / "good.py"
        good.write_text('"""Module."""\n\nx = 1\n', encoding="utf-8")
        result = ruff_changed.check_files([str(good)])
        assert not result.blocked

    def test_claude_check_skips_non_commit_commands(self) -> None:
        result = ruff_changed.claude_check({"tool_input": {"command": "git status"}})
        assert not result.blocked


class TestValidateContextUnit:
    def test_block_invalid_json(self) -> None:
        result = validate_context.decide("output/alex/context_1.json", "{not valid", REPO_ROOT)
        assert result.blocked
        assert "not valid JSON" in result.messages[0]

    def test_allow_valid_json(self) -> None:
        result = validate_context.decide(
            "output/alex/context_1.json", json.dumps({"resume_text": "x"}), REPO_ROOT
        )
        assert not result.blocked

    def test_allow_non_context_path(self) -> None:
        result = validate_context.decide("output/alex/resume.md", "{not valid", REPO_ROOT)
        assert not result.blocked

    def test_allow_empty_content(self) -> None:
        result = validate_context.decide("output/alex/context_1.json", "", REPO_ROOT)
        assert not result.blocked


# --------------------------------------------------------------------------- #
# 2. OLD-vs-NEW equivalence — real subprocess execution through the real
#    `.claude-plugin/hooks/*.sh` wrappers, byte-correct JSON via json.dumps.
# --------------------------------------------------------------------------- #


class TestRequireFeatureBranchEquivalence:
    def test_clear_block_on_main(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "eq_rfb_main", "main")
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(repo / "app.py")}}
        old = _run_old(old_hooks, "require-feature-branch", payload, subprocess_cwd=repo)
        new = _run_new("require-feature-branch", payload, subprocess_cwd=repo)
        _assert_equivalent(old, new, message_substrings=("BLOCKED (require-feature-branch)",))
        assert old[0] == 2

    def test_clear_allow_on_feature_branch(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path, "eq_rfb_feature", "feat/thing")
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(repo / "app.py")}}
        old = _run_old(old_hooks, "require-feature-branch", payload, subprocess_cwd=repo)
        new = _run_new("require-feature-branch", payload, subprocess_cwd=repo)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_allow_hatch_env(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "eq_rfb_hatch", "main")
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(repo / "app.py")}}
        old = _run_old(
            old_hooks,
            "require-feature-branch",
            payload,
            subprocess_cwd=repo,
            extra_env={"CLAUDE_ALLOW_MAIN_EDITS": "1"},
        )
        new = _run_new(
            "require-feature-branch",
            payload,
            subprocess_cwd=repo,
            extra_env={"CLAUDE_ALLOW_MAIN_EDITS": "1"},
        )
        _assert_equivalent(old, new)
        assert old[0] == 0


class TestBlockMergeToMainEquivalence:
    def test_clear_block_dominant_direction(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path, "eq_bmtm_main", "main")
        payload = {"tool_input": {"command": "git merge feature-x --no-ff"}, "cwd": str(repo)}
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=repo)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=repo)
        _assert_equivalent(old, new, message_substrings=("BLOCKED (block-merge-to-main)",))
        assert old[0] == 2

    def test_clear_allow_unrelated_command(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        payload = {"tool_input": {"command": "git status"}, "cwd": str(tmp_path)}
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=tmp_path)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_allow_confirm_hatch(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "eq_bmtm_hatch", "main")
        payload = {
            "tool_input": {"command": "CLAUDE_CONFIRM_MERGE=1 git merge feature-x --no-ff"},
            "cwd": str(repo),
        }
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=repo)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=repo)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_block_push_to_main(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_input": {"command": "git push origin main"}, "cwd": str(tmp_path)}
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=tmp_path)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new, message_substrings=("BLOCKED (block-merge-to-main)",))
        assert old[0] == 2

    # --- defect (i) regression: OLD wrongly blocks, NEW correctly allows ----
    def test_defect_i_regression_merge_base(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path, "eq_defect_i", "main")
        payload = {"tool_input": {"command": "git merge-base main HEAD"}, "cwd": str(repo)}
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=repo)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=repo)
        assert old[0] == 2, "documents the pre-fix false positive on a read-only command"
        assert new[0] == 0, "the fixed guard must not block git merge-base"

    # --- defect (ii) regression: OLD misresolves via ambient cwd, NEW uses the
    #     PreToolUse `cwd` field ------------------------------------------------
    def test_defect_ii_regression_cross_worktree_cwd(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        main_repo = _make_repo(tmp_path, "eq_defect_ii_main", "main")
        feature_repo = _make_repo(tmp_path, "eq_defect_ii_feature", "feat/somewhere")
        # No literal "main"/"master" token in the command — only the
        # dominant-direction cwd-based branch check can fire.
        command = "git merge other-branch --no-ff"
        # The invoking agent's own worktree (the PreToolUse `cwd` field) is the
        # FEATURE repo; the hook PROCESS's ambient cwd is (simulating the
        # defect) the MAIN checkout.
        payload = {"tool_input": {"command": command}, "cwd": str(feature_repo)}
        old = _run_old(old_hooks, "block-merge-to-main", payload, subprocess_cwd=main_repo)
        new = _run_new("block-merge-to-main", payload, subprocess_cwd=main_repo)
        assert old[0] == 2, "documents the pre-fix cross-worktree misfire"
        assert new[0] == 0, (
            "the fixed guard resolves branch from payload['cwd'], not the ambient process cwd"
        )


class TestBlockSecretsEquivalence:
    def test_clear_block_api_key(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "echo sk-ant-" + "a" * 30}}
        old = _run_old(old_hooks, "block-secrets", payload, subprocess_cwd=tmp_path)
        new = _run_new("block-secrets", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new, message_substrings=("Anthropic API key",))
        assert old[0] == 2

    def test_clear_allow_ordinary_edit(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "app.py", "new_string": "x = 1"},
        }
        old = _run_old(old_hooks, "block-secrets", payload, subprocess_cwd=tmp_path)
        new = _run_new("block-secrets", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_block_secret_file_write(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_name": "Write", "tool_input": {"file_path": ".api_key", "content": "sk-x"}}
        old = _run_old(old_hooks, "block-secrets", payload, subprocess_cwd=tmp_path)
        new = _run_new("block-secrets", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new, message_substrings=("secret file",))
        assert old[0] == 2


class TestRouteSecurityLintEquivalence:
    _BAD_ROUTE = '@bp.route("/x/<u>")\ndef f(u):\n    p = OUTPUT_DIR / u\n    open(p)'
    _GOOD_ROUTE = '@bp.route("/x/<u>")\ndef f(u):\n    _safe_username(u)\n    _within(p, OUTPUT_DIR)\n    open(p)'

    def test_clear_block_unguarded_route(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_input": {"file_path": "blueprints/foo.py", "new_string": self._BAD_ROUTE}}
        old = _run_old(old_hooks, "route-security-lint", payload, subprocess_cwd=tmp_path)
        new = _run_new("route-security-lint", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new, message_substrings=("route-security-lint",))
        assert old[0] == 2

    def test_clear_allow_guarded_route(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_input": {"file_path": "blueprints/foo.py", "new_string": self._GOOD_ROUTE}}
        old = _run_old(old_hooks, "route-security-lint", payload, subprocess_cwd=tmp_path)
        new = _run_new("route-security-lint", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_allow_non_route_file(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_input": {"file_path": "utils.py", "new_string": self._BAD_ROUTE}}
        old = _run_old(old_hooks, "route-security-lint", payload, subprocess_cwd=tmp_path)
        new = _run_new("route-security-lint", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0


class TestValidateContextEquivalence:
    def test_clear_block_invalid_json(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {
            "tool_input": {"file_path": "output/alex/context_1.json", "new_string": "{not valid"}
        }
        old = _run_old(old_hooks, "validate-context", payload, subprocess_cwd=tmp_path)
        new = _run_new("validate-context", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new, message_substrings=("not valid JSON",))
        assert old[0] == 2

    def test_clear_allow_valid_json(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {
            "tool_input": {"file_path": "output/alex/context_1.json", "new_string": '{"a": 1}'}
        }
        old = _run_old(old_hooks, "validate-context", payload, subprocess_cwd=tmp_path)
        new = _run_new("validate-context", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_edge_allow_non_context_path(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        payload = {"tool_input": {"file_path": "resumes/alex.docx", "new_string": "{not valid"}}
        old = _run_old(old_hooks, "validate-context", payload, subprocess_cwd=tmp_path)
        new = _run_new("validate-context", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0


class TestRuffChangedEquivalence:
    def test_edge_allow_non_commit_command(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        payload = {"tool_input": {"command": "git status"}}
        old = _run_old(old_hooks, "ruff-changed", payload, subprocess_cwd=tmp_path)
        new = _run_new("ruff-changed", payload, subprocess_cwd=tmp_path)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_clear_allow_no_staged_python(self, old_hooks: dict[str, Path], tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "eq_ruff_none", "feat/x")
        (repo / "README.md").write_text("hello\n", encoding="utf-8")
        _git(["add", "README.md"], cwd=repo)
        payload = {"tool_input": {"command": "git commit -m x"}}
        old = _run_old(old_hooks, "ruff-changed", payload, subprocess_cwd=repo)
        new = _run_new("ruff-changed", payload, subprocess_cwd=repo)
        _assert_equivalent(old, new)
        assert old[0] == 0

    def test_clear_block_staged_lint_violation(
        self, old_hooks: dict[str, Path], tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path, "eq_ruff_bad", "feat/x")
        (repo / "bad.py").write_text("import os\nx=1\n", encoding="utf-8")
        _git(["add", "bad.py"], cwd=repo)
        payload = {"tool_input": {"command": "git commit -m x"}}
        old = _run_old(old_hooks, "ruff-changed", payload, subprocess_cwd=repo)
        new = _run_new("ruff-changed", payload, subprocess_cwd=repo)
        # ruff's exact diagnostic transcript is environment-dependent (line/col
        # noise), so compare exit code + the fixed guidance text, not the full
        # stderr byte-for-byte.
        assert old[0] == new[0] == 2
        assert "ruff-changed" in old[1]
        assert "ruff-changed" in new[1]


# --------------------------------------------------------------------------- #
# 3. Native git-hook adapters (no OLD equivalent — new surface).
# --------------------------------------------------------------------------- #


def _run_git_hook(
    event: str, *args: str, cwd: Path, stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, test-authored input
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "enforcement" / "adapters" / "git_hook.py"),
            event,
            *args,
        ],
        cwd=str(cwd),
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class TestGitHookAdapter:
    def test_pre_commit_blocks_on_main(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_main", "main")
        result = _run_git_hook("pre-commit", cwd=repo)
        assert result.returncode != 0
        assert "require-feature-branch" in result.stderr

    def test_pre_commit_allows_on_feature_branch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_feature", "feat/thing")
        result = _run_git_hook("pre-commit", cwd=repo)
        assert result.returncode == 0

    def test_pre_merge_commit_blocks_on_main(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_merge_main", "main")
        result = _run_git_hook("pre-merge-commit", cwd=repo)
        assert result.returncode != 0
        assert "block-merge-to-main" in result.stderr

    def test_pre_merge_commit_allows_with_confirm_hatch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_merge_hatch", "main")
        env = dict(os.environ)
        env["CLAUDE_CONFIRM_MERGE"] = "1"
        result = subprocess.run(  # noqa: S603 - fixed argv, test-authored env
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "enforcement" / "adapters" / "git_hook.py"),
                "pre-merge-commit",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        assert result.returncode == 0

    def test_pre_push_blocks_main_ref(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_push_main", "feat/x")
        stdin = "refs/heads/feat/x abc123 refs/heads/main def456\n"
        result = _run_git_hook(
            "pre-push", "origin", "https://example.invalid/repo.git", cwd=repo, stdin=stdin
        )
        assert result.returncode != 0

    def test_pre_push_allows_feature_ref(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, "git_hook_push_feature", "feat/x")
        stdin = "refs/heads/feat/x abc123 refs/heads/feat/x abc123\n"
        result = _run_git_hook(
            "pre-push", "origin", "https://example.invalid/repo.git", cwd=repo, stdin=stdin
        )
        assert result.returncode == 0

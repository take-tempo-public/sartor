# Blast radius — hook-guard-false-blocks

> **Branch:** `fix/hook-guard-false-blocks`
> **Status:** enumeration complete, written before the first edit to `scripts/enforcement/gitutil.py`.

---

## Surface

- `scripts/enforcement/gitutil.py` (gated: helper, 9 non-test importers). **Additive only:** a new
  `repo_root(start, env)` function. The existing `_run`, `git_branch`, `staged_files` and
  `staged_content` keep their signatures and behavior.
- Not gated, but consumed by others and so enumerated here as well:
  - `_split_top_level` moves from `scripts/enforcement/guards/verify_binary_on_path.py:174` to a
    new shared module, `scripts/enforcement/shell_split.py`. `verify_binary_on_path` re-imports
    it under the same name.
  - `block_merge_to_main.targets_main` (`:126`) keeps its signature `(command, invocation_cwd) -> bool`.
  - `scripts/gate.py` gets a new step and a `--result` mode. Its existing CLI keeps working.

---

## Enumeration

Run with the Grep tool (ripgrep) over the whole tree on 2026-10-05, at `main` c384fad plus this
branch's test commit:

- `gitutil|_split_top_level|targets_main|_leading_binary_token` over `*.{py,sh,md}` found these
  production importers of `gitutil`:
  `guards/block_secrets.py:15`, `guards/validate_context.py:19`, `guards/block_merge_to_main.py:81`,
  `guards/ruff_changed.py:18`, `guards/route_security_lint.py:22`, `adapters/git_hook.py:26`,
  `adapters/claude_context_hook.py:56`, `guards/require_feature_branch.py:23`,
  `guards/require_evidence_before_fix.py:47` and `guards/require_consumer_enumeration.py:56`.
  The other hits are docs and history.
- `_split_top_level` is used only in `verify_binary_on_path.py` (`:28` docstring, `:174` def,
  `:325` call). `tests/` has 0 direct imports of the private name.
- `targets_main` has one production caller, `block_merge_to_main.py:152`, and is used in tests.
- `CLAUDE_PROJECT_DIR|_repo_root_for` over production code (excluding `tests/`):
  - `guards/require_evidence_before_fix.py:57-61,137`
  - `guards/require_consumer_enumeration.py:107-110,178`
  - `adapters/claude_context_hook.py:82-83`
  - `adapters/claude_hook.py:106` (validate-context)
  - `hooks/*.sh` (exec path and plan-marker keys)
  - `.claude/settings.json`
- Tests that pass `CLAUDE_PROJECT_DIR` in `env`: `test_evidence_gate.py`,
  `test_consumer_enumeration_gate.py`, `test_c12_disclosure_gate.py:117,126`,
  `test_enforcement_core.py:190` and `test_plan_approval_scoping.py`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/enforcement/gitutil.py` | update | Add `repo_root(start, env)`: walk up from the nearest existing directory to the one holding `.git`; fall back to `CLAUDE_PROJECT_DIR`, then `.`. |
| 2 | `guards/require_evidence_before_fix.py:57,137` | update | `_repo_root_for` delegates to `gitutil.repo_root`. Item 148. |
| 3 | `guards/require_consumer_enumeration.py:107,178` | update | Same as row 2. Item 148. |
| 4 | `adapters/claude_context_hook.py:82` | update | `_project_dir` uses `gitutil.repo_root(payload cwd)`, so `restore-evidence` and `capture-before-compact` follow a worktree session. |
| 5 | `guards/block_secrets.py`, `validate_context.py`, `ruff_changed.py`, `route_security_lint.py`, `adapters/git_hook.py`, `require_feature_branch.py`, `block_merge_to_main.py` (gitutil importers) | no change | They use only `git_branch`/`staged_*`, which are untouched. |
| 6 | `verify_binary_on_path.py:174,325` | update | Imports `_split_top_level` from `shell_split`; behavior is byte-identical (a move). |
| 7 | `block_merge_to_main.py:126,152` | update | `targets_main` gains a segment parser; signature unchanged. |
| 8 | `scripts/gate.py` | update | Adds the `hooksPath` step and the result file / `--result`. Consumers: CI's `quality` job, `CONTRIBUTING.md`, `maintainer-lane.md` and `AGENTS.md` all run `python -m scripts.gate` with no arguments, which still works. |
| 9 | tests passing `CLAUDE_PROJECT_DIR` for a target inside a real repo | no change | The walk-up finds the same repo they name, so the result is unchanged. Tests for a target outside any repo still get the env fallback. |

---

## Deferred

- `adapters/claude_hook.py:106` (validate-context reads `CLAUDE_PROJECT_DIR` for its repo root).
  This is not one of this branch's items. It judges **staged** files, and git resolves those
  against the process cwd, so the worktree mismatch of item 148 has not been observed there.
  The new static test covers `scripts/enforcement/guards/`, `claude_context_hook.py` and the
  Edit|Write path only; it names this file as the one deliberate exception.
- `hooks/*.sh` and `.claude/settings.json` use `CLAUDE_PROJECT_DIR` to locate the hook scripts and
  key plan markers. That is the correct use (where the hooks live, not which repo is edited).

---

## Verification

- An exact-set static test lists every file under `scripts/enforcement/` that contains the
  string `CLAUDE_PROJECT_DIR`. A new direct reader fails it.
- The three files of guard tests run unchanged, plus the e2e `git worktree add` test, which
  calls the real dispatcher.
- `mypy` (strict on `scripts/enforcement`) catches a signature drift in any `gitutil` importer.

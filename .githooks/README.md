# Portable git-native hooks (opt-in)

> **Purpose:** the git-native consumer of the portable enforcement core
> (`scripts/enforcement/`) — the same guard logic the Claude Code plugin runs
> as PreToolUse hooks, wired instead to git's own hook points so the rules
> hold for plain `git commit`/`git merge`/`git push` too, with no Claude Code
> session required. See [`docs/governance/enforcement.md`](../docs/governance/enforcement.md)
> for the gate/witness/tribal split this implements the "gate" side of.

## What's here

| Hook | Guards run | git event |
|---|---|---|
| [`pre-commit`](pre-commit) | `require-feature-branch`, `block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context` | before an ordinary commit is created |
| [`pre-merge-commit`](pre-merge-commit) | `block-merge-to-main` | before a non-fast-forward merge commit is created (git ≥ 2.24) |
| [`pre-push`](pre-push) | `block-merge-to-main` | before a push updates a remote ref |

Each hook is a thin bash wrapper that execs `python3
scripts/enforcement/adapters/git_hook.py <event>`; the guard decisions
themselves live once in `scripts/enforcement/guards/` and are shared with the
Claude Code PreToolUse adapter (`scripts/enforcement/adapters/claude_hook.py`,
invoked via wrappers in root `hooks/*.sh` — since PX-37 (`chore/hook-dispatcher`),
five of them run through one consolidated `hooks/edit-write-dispatcher.sh`
entry rather than each having their own file).

**Not covered here:** the plan-mode lifecycle hooks (`check-plan-approved`,
`mark-plan-approved`, `cleanup-plan-on-merge`) are Claude-only by design —
there is no git-native equivalent of "has this session's plan been approved
via `ExitPlanMode`", so they stay standalone scripts under root `hooks/`,
untouched by this migration.

## Activation (one-time, per clone — NOT automatic)

Git only runs hooks from `.git/hooks/` by default; this repo ships its hooks
under version control at `.githooks/` instead (so they can be reviewed,
diffed, and shared — `.git/hooks/` is never tracked). Point git at them:

```bash
git config core.hooksPath .githooks
```

This is a **local, per-clone git config setting** — it is not committed and
does not propagate to other clones or contributors automatically (deliberate:
a contributor's own git-hook execution is their choice, same posture as the
Claude Code plugin's hooks only running inside a Claude Code session). Each
teammate who wants the local git-level enforcement (in addition to, or
instead of, the Claude Code plugin hooks) runs the command above once.

To deactivate:

```bash
git config --unset core.hooksPath
```

## Escape hatches

Same environment-variable opt-ins as the Claude Code plugin hooks:

- `CLAUDE_CONFIRM_MERGE=1` — allow a merge/push that targets `main`/`master`
  (`pre-merge-commit` / `pre-push`).
- `CLAUDE_ALLOW_MAIN_EDITS=1` — allow a commit while `HEAD` is `main`/`master`
  (`pre-commit`'s `require-feature-branch` check).

Example: `CLAUDE_CONFIRM_MERGE=1 git merge feature-branch --no-ff -m '...'`.

## Windows

These are POSIX shell scripts with a `#!/usr/bin/env bash` shebang — Git for
Windows already runs its own hooks this way (via the bundled `sh`), so no
`.sh`/`.bat` variant is needed; the same three files work unmodified on
Windows Git Bash and on Linux/macOS. Requires `python3` on `PATH` (already a
project prerequisite — see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).

## CI backstop

`scripts/enforcement/ci_backstop.py` runs a repo-wide secrets scan in
`.github/workflows/ci.yml`'s `quality` job — it does not depend on
`core.hooksPath` activation, so it catches anything a contributor's local
hooks (git-native or Claude) missed or bypassed.

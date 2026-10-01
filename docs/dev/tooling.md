# Tooling roster — hooks, guards, commands, subagents, skills

> **Purpose:** one list of the development tooling this repo ships for Claude Code and for
> plain git: every wired hook, every enforcement guard and where it runs, every slash
> command, subagent and skill. It shows what exists and where it lives. How each one
> behaves is in its own file.
> **Audience:** `dev` — contributors and agents who need to know what will block them, what
> only warns, and which workflows already exist before building a new one.
> **Authoritative for:** the roster (what is wired, and where). The binding rules the guards
> enforce live in [`../governance/charter.md`](../governance/charter.md); what each guard
> catches, and what it can't, is in [`../governance/enforcement.md`](../governance/enforcement.md);
> the agent-facing behavior notes live in [`CLAUDE.md`](../../CLAUDE.md) "Plugin commands +
> agents + hooks".

The roster is derived, not remembered. It reflects `feat/dev-docs` (2026-09-30), re-derived
from:
- `.claude/settings.json` (`hooks`) and the `hooks/` directory;
- the two dispatchers' `_GUARD_ORDER`
  ([`bash_dispatcher.py`](../../scripts/enforcement/adapters/bash_dispatcher.py),
  [`claude_dispatcher.py`](../../scripts/enforcement/adapters/claude_dispatcher.py));
- [`git_hook.py`](../../scripts/enforcement/adapters/git_hook.py);
- `commands/`, `agents/` and `skills/`.

When you add or remove one, change this page in the same commit.
Two tests already check part of it:
- [`tests/test_governance_hooks_gate.py`](../../tests/test_governance_hooks_gate.py) checks
  that every hook is classified and that the wiring matches settings;
- [`tests/test_enforcement_coverage.py`](../../tests/test_enforcement_coverage.py) checks
  that every guard on disk is classified.

[`tests/test_doc_lints.py`](../../tests/test_doc_lints.py) checks this page against the
tree, section by section and in both directions (`doc_lints.lint_tooling_roster`): a name
missing from a table, or a row whose file is gone, fails the gate.

## Claude Code hooks

All nine are wired in `.claude/settings.json`, not in the plugin manifest. Each lives in
[`hooks/`](../../hooks/).

| Hook | Event (matcher) | Kind | What it does | Escape hatch |
|---|---|---|---|---|
| `check-plan-approved.sh` | PreToolUse (`Edit\|Write`) | **blocks** | No edit outside `~/.claude/plans/` without an approved plan. It also retires an approval once its branch has merged, through `hooks/lib/retire-approved-plan.sh` | none; only `ExitPlanMode` creates the marker |
| `edit-write-dispatcher.sh` | PreToolUse (`Edit\|Write`) | **blocks** | Runs the seven Edit/Write guards below in one process | per guard |
| `bash-dispatcher.sh` | PreToolUse (`Bash`) | **blocks** | Runs the five Bash guards below in one process | per guard |
| `mark-plan-approved.sh` | PostToolUse (`ExitPlanMode`) | lifecycle | Writes the per-project approval marker for the plan just approved | — |
| `cleanup-plan-on-merge.sh` | PostToolUse (`Bash`) | lifecycle | After a local `--no-ff` merge command, archives the plan and clears its approval. Every other merge channel is caught on the next edit by `check-plan-approved.sh` | — |
| `wiki-freshness-reminder.sh` | PostToolUse (`Bash`) | witness | After a commit, says when `docs/wiki/` may be stale. Always exits 0 | — |
| `interrogative-prompt-witness.sh` | UserPromptSubmit | witness | Reminds that a question's deliverable is the answer. Always exits 0 | — |
| `restore-evidence.sh` | SessionStart (`startup\|resume\|compact`) | context | Replays a `fix/*` branch's `## Observed` + `## Falsified` into the new context (charter C-8) | — |
| `capture-before-compact.sh` | PreCompact (`auto\|manual`) | witness (to the user) | Warns before compaction when a `fix/*` branch has no captured evidence | — |

`hooks/lib/retire-approved-plan.sh` is a helper that the two plan hooks source, not a hook.

## Enforcement guards

One implementation per rule in
[`scripts/enforcement/guards/`](../../scripts/enforcement/guards/). The same guard can run
under several adapters: the Claude dispatchers above, the opt-in git hooks in
[`.githooks/`](../../.githooks/) (`git config core.hooksPath .githooks`), and the CI backstop.

| Guard | Claude adapter | `.githooks/` | CI | What it blocks | Escape hatch |
|---|---|---|---|---|---|
| `require-feature-branch` | Edit/Write | yes | — | edits while on `main`/`master` | `CLAUDE_ALLOW_MAIN_EDITS=1`, user-directed only |
| `require-evidence-before-fix` | Edit/Write | — | — | production edits on `fix/*` before the diagnosis dossier has `## Observed` (C-7) | none |
| `require-consumer-enumeration` | Edit/Write | — | — | edits to a gated surface before the blast-radius dossier names it (C-10) | none |
| `block-secrets` | Edit/Write and Bash | yes | yes ([`ci_backstop.py`](../../scripts/enforcement/ci_backstop.py), repo-wide) | API keys, and writes to `.api_key` / `.env*` / `*.pem` / `*.key` | none |
| `validate-context` | Edit/Write | yes | — | malformed `output/**/context_*.json` | none |
| `route-security-lint` | Edit/Write | yes | — | a new route without `_safe_username` + `_within` (C-1) | none |
| `interrogative-witness` | Edit/Write | — | — | nothing: a one-time, self-clearing pause on the first edit after each prompt (item 87) | re-run the same call |
| `block-merge-to-main` | Bash | yes | — | a local `git merge` or `git push` targeting `main`/`master`, and a push to `main` while the wiki is stale | `CLAUDE_CONFIRM_MERGE=1`, user-directed only (not for the wiki arm) |
| `ruff-changed` | Bash | yes | — | a commit with ruff errors in staged Python | none |
| `verify-binary-on-path` | Bash | — | — | a command whose leading binary isn't on `PATH` | none (fail-open on anything it can't parse) |
| `block-subagent-git-stash` | Bash | — | — | a state-changing `git stash` from a subagent | none |

Plan approval (`check-plan-approved.sh`) is a hook, not a guard, so it has no row here.

## Slash commands

These load as the `sartor` plugin (`/sartor:<name>`). Each is defined in
[`commands/`](../../commands/).

| Command | For |
|---|---|
| `eval` | run the eval harness on synthetic or real fixtures |
| `replay` | re-run `generate()` against a saved context file |
| `prompt-tune` | A/B a system-prompt edit through the prompt-override primitive |
| `tune-from-annotations` | the annotations-driven tuning loop, from brief to promoted edit |
| `bench` | cache-hit rate, latency and cost from the LLM call log |
| `inspect-context` | pretty-print and validate a saved `context_set` |
| `wiki-ingest` | compile changed sources into `docs/wiki/` |
| `wiki-self-update` | the bounded, cost-aware wiki repair loop |
| `wiki-query` | answer a question from the wiki, with citations |
| `wiki-lint` | the read-only wiki drift and coverage report |
| `wiki-audit` | fact-check one wiki page against its sources |
| `compliance-witness` | the read-only governance drift report |

## Subagents

These load as `sartor:<name>`. Each is defined in [`agents/`](../../agents/), and its
`model:` field is the pin.

| Subagent | Model | Used by |
|---|---|---|
| `eval-judge` | `claude-haiku-4-5-20251001` | the eval harness; interactive rubric grading |
| `wiki-scribe` | `claude-haiku-4-5-20251001` | `/wiki-self-update` (writes one page) |
| `wiki-grounding-auditor` | `claude-haiku-4-5-20251001` | `/wiki-self-update` (audits one page; never its own) |
| `prompt-archaeologist` | `claude-sonnet-5` | eval regressions: proposes a prompt diff, never applies it |
| `tune-drafter` | `claude-sonnet-5` | `/tune-from-annotations` (drafts a candidate constant) |
| `headhunter` | `claude-sonnet-5` | recruiting-domain review of questions, bullets and rubric outcomes |
| `git-flow` | `claude-sonnet-5` | branch, commit and PR tasks under the project's rules |
| `ux-onboarding-designer` | `claude-sonnet-5` | onboarding audits of the user docs |
| `compliance-witness` | `claude-sonnet-5` | `/compliance-witness` |
| `n1-refuter` | `claude-sonnet-5` | the N=1 baseline pipeline ([`n1-baseline-pipeline.md`](n1-baseline-pipeline.md)) |
| `n1-judge` | `claude-opus-5` | the N=1 baseline pipeline |

Why some pins are dated snapshots and others undated aliases: `CLAUDE.md`, "Model-pin
convention".

## Skills

| Skill | Where | For |
|---|---|---|
| `context-structure-review` | [`skills/context-structure-review/`](../../skills/context-structure-review/) | auditing a repository's markdown and agent-instruction files against context-engineering practice (see [`skills/README.md`](../../skills/README.md)) |

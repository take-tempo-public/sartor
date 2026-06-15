# callback. — Claude Code specifics

> **Purpose:** Claude-Code-specific overrides and tool integrations.
> The universal AI agent contract — branch conventions, security
> guardrails, the test/ruff/mypy gate, what NOT to do — lives in
> [`AGENTS.md`](AGENTS.md). This file imports it and layers on the
> Claude-Code-specific bits (skill catalog, plan-mode hook,
> machine-local override file).
> **Audience:** Claude Code agents (CLI and IDE extensions) working
> in this repo; the harness auto-loads this file at session start.
> **Authoritative for:** Claude-Code-specific behavior — the
> `.claude-plugin/` hook semantics, the `CLAUDE.local.md`
> override file, the plan-mode workflow. For everything else, see
> AGENTS.md.

@AGENTS.md

---

## Read AGENTS.md first

Universal rules — branch conventions, the security guard pattern,
the dev loop, the LLM call boundary, what NOT to do — live in
[`AGENTS.md`](AGENTS.md). The `@AGENTS.md` line above asks Claude
Code to inline that content; this file adds only Claude-specific
overrides on top.

If you're not Claude Code and you're reading this file by
accident, jump straight to [`AGENTS.md`](AGENTS.md).

---

## Claude-Code-specific overrides

### `CLAUDE.local.md` machine-local file

For per-clone, per-machine notes (paths, shell quirks, personal
workflow preferences), use `CLAUDE.local.md` at the repo root.
This file is gitignored. Claude Code auto-loads it alongside
this file and treats it as overriding any conflicting guidance
in AGENTS.md or CLAUDE.md.

Common contents:
- OS + shell version (Git Bash vs PowerShell on Windows)
- Python path or virtualenv hints
- Per-clone API key location if you've moved `.api_key`
- Plan-mode enforcement preferences

### Plan-mode workflow

When the harness says **"Plan mode is active"**, Claude Code must:

1. First action MUST be to write or update the plan file at
   `~/.claude/plans/<slug>.md`.
2. Do NOT call `Edit` or `Write` on any file other than the
   plan file.
3. Do NOT run state-changing Bash commands (`git checkout -b`,
   `git commit`, `git merge`).
4. Call `ExitPlanMode` ONLY after the plan file is complete
   and ready for user review.

The PreToolUse hook at `.claude/hooks/check-plan-approved.sh`
enforces rules 2 and 4. Once Step 4 of the v1.0 release arc
lands, this moves to `.claude-plugin/hooks/`.

### Plugin commands + agents + hooks

This project ships a Claude Code plugin (`callback`): the manifest +
local marketplace live in [`.claude-plugin/`](.claude-plugin/),
commands in [`commands/`](commands/), and subagents in
[`agents/`](agents/). Commands, subagents, and hooks are listed in
[`README.md`](README.md#claude-code-plugin).
**Activation:** the commands + subagents load as the `callback`
plugin via the local `callback-tools` marketplace
(`extraKnownMarketplaces` + `enabledPlugins` committed in
[`.claude/settings.json`](.claude/settings.json)), so they appear
namespaced (`/callback:…`, `callback:…`). The **hooks are wired
directly in the same `settings.json`** — deliberately not in the
plugin manifest, pending the tool-agnostic-enforcement decision
slated for the v1.0.7 governance pass (see README). Important
hooks for any agent writing code here:

- `block-secrets` — blocks API keys + writes to
  `.api_key` / `.env*` / `*.pem` / `*.key`.
- `ruff-changed` — runs `ruff check` on staged Python before
  `git commit`. Fix issues or use `--fix` before re-staging.
- `route-security-lint` — requires `_safe_username` + `_within`
  on new Flask routes (per AGENTS.md "Key patterns").
- `validate-context` — JSON-syntax + schema check on
  `output/**/context_*.json` writes.
- `block-merge-to-main` — blocks merge/push to main without
  explicit `CLAUDE_CONFIRM_MERGE=1`.
- `wiki-freshness-reminder` — non-blocking nudge after
  `git commit` when `docs/wiki/` may be stale (silent until the
  first `/wiki-ingest` sets a baseline; never auto-ingests).

### Skill catalog

The plugin's slash commands load **namespaced under the plugin
name** (`/callback:<command>`) once the `callback-tools`
marketplace + `enabledPlugins` entry in
[`.claude/settings.json`](.claude/settings.json) are active (on a
fresh clone this is a one-time marketplace-trust + reload). Prefer
them over reinventing the workflow inline:

- `/callback:eval` — run the eval harness against synthetic or
  real fixtures.
- `/callback:replay` — re-run `generate()` on a saved
  `context_*.json`.
- `/callback:prompt-tune` — A/B test a `SYSTEM_PROMPT` edit
  against the eval suite.
- `/callback:tune-from-annotations` — read an
  `improvement_brief.md`, draft a candidate via the
  `callback:tune-drafter` subagent, A/B it against the
  `--suite real` fixture (+ anchor canary), promote on approval.
- `/callback:bench` — aggregate `logs/llm_calls.jsonl` for cache
  hit rate, latency, cost.
- `/callback:inspect-context` — pretty-print + schema-validate a
  saved `context_set`.
- `/callback:wiki-ingest` — compile changed sources into
  `docs/wiki/` pages (diff-driven off `.last_ingest_sha`;
  sentinel or `--full` = a full cold pass); advances the
  checkpoint, appends to `log.md`.
- `/callback:wiki-query` — answer a question from the wiki with
  `[[citations]]`; offer to file the answer back as a page.
- `/callback:wiki-lint` — severity-tiered drift/coverage report
  on the wiki (periodic + pre-release gate).
- `/callback:wiki-audit` — fact-check one wiki page against its
  cited sources.

See [`commands/`](commands/) for
each command's full definition.

### Subagent catalog

The plugin's subagents load namespaced as `callback:<name>`.
Delegate to them rather than doing the work inline:

- `callback:eval-judge` (Haiku) — grade one (artifact × rubric)
  → strict JSON verdict; used by the eval harness + interactive
  grading.
- `callback:prompt-archaeologist` — trace an eval regression to
  the prompt rule that caused it and propose a minimal
  unified-diff fix (does NOT apply it).
- `callback:tune-drafter` — read-only: draft a full candidate
  system-prompt constant from an `improvement_brief.md` for the
  `/callback:tune-from-annotations` A/B.
- `callback:headhunter` — recruiter-domain check when a clarify
  question / suggestion / rubric outcome reads "technically
  correct but unlikely to generate a callback."
- `callback:git-flow` — autonomous git workflow under the
  project's branch/commit conventions.
- `callback:ux-onboarding-designer` — audit user-facing docs
  from a first-time-user lens → sequenced rewrite ladder.

See [`agents/`](agents/) for each
subagent's full definition.

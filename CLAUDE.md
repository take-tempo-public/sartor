# sartor. — Claude Code specifics

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

The *binding* governance home is [`docs/governance/`](docs/governance/)
(`charter.md` + `enforcement.md` + `metrics.md`); AGENTS.md keeps the
operational rules inline and points to it, and the `@AGENTS.md` import
above carries that pointer into this file.

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

The PreToolUse hook at `.claude-plugin/hooks/check-plan-approved.sh`
enforces rules 2 and 4.

### Plugin commands + agents + hooks

This project ships a Claude Code plugin (`sartor`): the manifest +
local marketplace live in [`.claude-plugin/`](.claude-plugin/),
commands in [`commands/`](commands/), and subagents in
[`agents/`](agents/). Commands, subagents, and hooks are listed in
[`README.md`](README.md#architecture--developer-reference).
**Activation:** the commands + subagents load as the `sartor`
plugin via the local `sartor-tools` marketplace
(`extraKnownMarketplaces` + `enabledPlugins` committed in
[`.claude/settings.json`](.claude/settings.json)), so they appear
namespaced (`/sartor:…`, `sartor:…`). The **hooks are wired
directly in the same `settings.json`** — deliberately not in the
plugin manifest, pending the tool-agnostic-enforcement decision
slated for the v1.0.7 governance pass (see README). Important
hooks for any agent writing code here:

- `require-evidence-before-fix` — on a `fix/*` branch, blocks
  `Edit`/`Write` to production code until
  `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section (charter **C-7**). **No escape hatch, and none is needed:**
  `docs/**`, `tests/**` and `*.md` stay writable, so the way through is
  always to write down what you saw. Start from
  [`docs/dev/diagnosis/TEMPLATE.md`](docs/dev/diagnosis/TEMPLATE.md).
- `restore-evidence` (SessionStart) — replays the current `fix/*`
  branch's `## Observed` + `## Falsified` into every fresh context,
  **including the one rebuilt after a compaction** (charter **C-8**).
  `## Inferred` is deliberately withheld — an unproven mechanism
  re-injected as context reads as established fact within a few turns.
- `capture-before-compact` (PreCompact) — warns the **user** when a
  context window is about to be discarded while a `fix/*` branch has no
  captured evidence. It cannot reach Claude (PreCompact has no context
  injection) and deliberately does not block compaction.
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

### Skill + subagent catalog

Full definitions — description, argument shape, exact behavior — live
in the files themselves; this section is a **directory**, not a
restatement. Prefer delegating to these over reinventing the workflow
inline.

- **Commands** (`/sartor:<name>`, namespaced under the plugin) — one
  file per command in [`commands/`](commands/): `eval`, `replay`,
  `prompt-tune`, `tune-from-annotations`, `bench`, `inspect-context`,
  `wiki-ingest`, `wiki-query`, `wiki-lint`, `wiki-audit`,
  `wiki-self-update`, `compliance-witness`.
- **Subagents** (`sartor:<name>`) — one file per subagent in
  [`agents/`](agents/): `eval-judge`, `prompt-archaeologist`,
  `tune-drafter`, `headhunter`, `git-flow`, `ux-onboarding-designer`,
  `wiki-scribe`, `wiki-grounding-auditor`, `compliance-witness`. The
  `compliance-witness` pair's distinguishing facts (default cap 12,
  the FLAG/WATCH/AFFIRM disposition taxonomy, the read-only tool
  grant *as* the enforcement) live in its own frontmatter/body —
  read there rather than restated here.

They load namespaced once the `sartor-tools` marketplace +
`enabledPlugins` entry in [`.claude/settings.json`](.claude/settings.json)
are active (fresh clone: one-time marketplace-trust + reload). Until
then, read the definition file directly — the workflow still
applies, just un-namespaced.

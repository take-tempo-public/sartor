# sartor. — Claude Code specifics

> **Purpose:** Claude-Code-specific overrides and tool integrations.
> The universal AI agent contract — branch conventions, security
> guardrails, the test/ruff/mypy gate, what NOT to do — lives in
> [`AGENTS.md`](AGENTS.md). This file imports it and layers on the
> Claude-Code-specific bits (skill catalog, plan-mode hook,
> machine-local override file).
> **Audience:** `dev` — Claude Code agents (CLI and IDE extensions) working
> in this repo; the harness auto-loads this file at session start.
> **Authoritative for:** Claude-Code-specific behavior — the
> `.claude-plugin/` hook semantics, the `CLAUDE.local.md`
> override file, the plan-mode workflow. For everything else, see
> AGENTS.md.

@AGENTS.md

@docs/dev/maintainer-lane.md

---

## Read AGENTS.md first

Universal rules — branch conventions, the security guard pattern,
the dev loop, the LLM call boundary, what NOT to do — live in
[`AGENTS.md`](AGENTS.md). The owner's session protocol (taking over
a handoff, the branch close-out checklist) lives in
[`docs/dev/maintainer-lane.md`](docs/dev/maintainer-lane.md). The two
`@` lines above ask Claude Code to inline both; every Claude Code
session in this repo works for the owner, so both bind. This file adds
only Claude-specific overrides on top.

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

The plan gate (`check-plan-approved`, in
`scripts/enforcement/plan_gate.py`, run by the Edit|Write dispatcher)
enforces rules 2 and 4.

### Plugin commands + agents + hooks

This project ships a Claude Code plugin (`sartor`): the manifest +
local marketplace live in [`.claude-plugin/`](.claude-plugin/),
commands in [`commands/`](commands/), and subagents in
[`agents/`](agents/). The full roster of hooks, guards, commands,
subagents and skills, with where each one runs, is
[`docs/dev/tooling.md`](docs/dev/tooling.md).
**Activation:** the commands + subagents load as the `sartor`
plugin via the local `sartor-tools` marketplace
(`extraKnownMarketplaces` + `enabledPlugins` committed in
[`.claude/settings.json`](.claude/settings.json)), so they appear
namespaced (`/sartor:…`, `sartor:…`). The **hooks are wired
directly in the same `settings.json`**, not in the plugin manifest:
the guard logic lives once in the tool-agnostic `scripts/enforcement/`
core, which the Claude hooks, the opt-in `.githooks/` and CI all call.
Important hooks for any agent writing code here:

- `check-plan-approved` / `mark-plan-approved` / `plan-write-landed`
  — the plan gate (`scripts/enforcement/plan_gate.py`). No `Edit`/`Write`
  outside `~/.claude/plans/` until `ExitPlanMode` approves a plan, and a
  plan written after the live approval blocks edits until it is approved
  in turn. The approval is retired (archived) once that plan's branch has
  merged or is gone. `ExitPlanMode` is refused while the plan file's
  last Write/Edit has not landed (item 143). Write the plan and call
  `ExitPlanMode` in separate messages. Only `ExitPlanMode` creates the
  marker; never create it by hand.
- `require-feature-branch` — blocks `Edit`/`Write` while on
  `main`/`master`. The hatch, `CLAUDE_ALLOW_MAIN_EDITS=1`, is used only
  when the user directs it.

- `require-evidence-before-fix` — on a `fix/*` branch, blocks
  `Edit`/`Write` to production code until
  `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section (charter **C-7**). **No escape hatch, and none is needed:**
  `docs/**`, `tests/**` and `*.md` stay writable, so the way through is
  always to write down what you saw. Start from
  [`docs/dev/diagnosis/TEMPLATE.md`](docs/dev/diagnosis/TEMPLATE.md).
- `require-consumer-enumeration` — blocks `Edit`/`Write` to a **gated
  surface** (schema / shared contract / widely-consumed helper — registry +
  per-entry rationale in [`scripts/enforcement/blast_radius.py`](scripts/enforcement/blast_radius.py))
  until `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section
  **naming that surface** (charter **C-10**). **No escape hatch, and none is
  needed:** the dossier's own directory and `tests/**` stay writable, so the way
  through is always to write down who consumes it. Start from
  [`docs/dev/blast-radius/TEMPLATE.md`](docs/dev/blast-radius/TEMPLATE.md).
  Unlike `require-evidence-before-fix` it fires on **every** branch type (schema
  changes land on `feat/*`, not `fix/*`) and does **not** blanket-exempt `*.md`
  (the handoff template and the SCHEMA docs *are* contracts).
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
- `verify-binary-on-path` — blocks a Bash command whose leading
  binary is not on `PATH` ("'X' not found on PATH"), so multi-step
  commands fail at the gate instead of deep inside. Deliberately
  fail-open on anything it cannot parse with certainty (substitutions,
  heredocs, MSYS `/c/` paths, `||`-guarded segments) — the block
  message limits its claim to the PATH lookup (C-0).
- `block-subagent-git-stash` — blocks a state-changing `git stash`
  (anything but `list`/`show`) in a Bash command issued by a **subagent**
  (the payload carries `agent_id`); the main agent is not gated. The C-11
  guard for a pipeline refuter stashing the shared tree mid-review
  (Epic C C1c). Reads the command string only, so an indirect stash
  is not caught (C-0).
- `wiki-freshness-reminder` — non-blocking nudge after
  `git commit` when `docs/wiki/` may be stale (silent until the
  first `/wiki-ingest` sets a baseline; never auto-ingests).
- `interrogative-prompt-witness` + the `interrogative-witness` pause
  (item 87) — two fail-open witnesses against the
  question-treated-as-work-order failure class. On UserPromptSubmit, a
  heuristic (trailing `?` or an interrogative lead word) injects a
  non-blocking "the deliverable is the ANSWER" reminder. On the first
  `Edit`/`Write` after each user prompt, the Edit|Write dispatcher
  refuses ONCE with the interrogative-vs-directive question and
  self-clears — re-run the same call to proceed. Subagent edits
  (payload carries `agent_id`) are skipped, so a subagent can't eat
  the main agent's pause (item 94). Witness, not gate
  (C-0: intent classification is not deterministic); every failure
  path fails open.

**Wiring note (`fix/python-direct-hooks-plan-gate`, item 152):** every
settings.json hook is exactly
`python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>`.
No shell wrapper sits in between, and `tests/test_settings_hooks_python_direct.py`
fails on any other shape. The five Bash-matcher guards (`block-secrets`,
`block-merge-to-main`, `ruff-changed`, `verify-binary-on-path`,
`block-subagent-git-stash`) run in the `bash-dispatcher` process. The plan gate and
the seven Edit|Write guards run in the `edit-write-dispatcher` process (PX-37). That
is one process per matcher, with no-short-circuit aggregation. A hook that outruns its
timeout is cancelled by the harness, and a cancelled PreToolUse hook does **not**
block: on this machine a slow gate is an open gate
(`docs/dev/diagnosis/python-direct-hooks-plan-gate.md`).

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
  `wiki-scribe`, `wiki-grounding-auditor`, `compliance-witness`, and the
  N=1 pipeline pair `n1-refuter` and `n1-judge` (dispatched only by
  `.claude/workflows/n1-baseline.mjs`). The
  `compliance-witness` pair's distinguishing facts (default cap 12,
  the FLAG/WATCH/AFFIRM disposition taxonomy, the read-only tool
  grant *as* the enforcement) live in its own frontmatter/body —
  read there rather than restated here.
- **Skills** — [`skills/`](skills/): `context-structure-review`, `doc-writing`.

They load namespaced once the `sartor-tools` marketplace +
`enabledPlugins` entry in [`.claude/settings.json`](.claude/settings.json)
are active (fresh clone: one-time marketplace-trust + reload). Until
then, read the definition file directly — the workflow still
applies, just un-namespaced.

**Model-pin convention.** Each subagent's frontmatter `model:` field is
either a dated snapshot or an undated alias, and the split is
intentional and provider-imposed, not drift: `eval-judge`,
`wiki-grounding-auditor`, and `wiki-scribe` pin the dated Haiku
snapshot `claude-haiku-4-5-20251001` because Anthropic publishes one;
seven subagents use the undated alias `claude-sonnet-5`, and `n1-judge`
the undated alias `claude-opus-5`, because no dated Sonnet-5 or Opus-5
snapshot exists on the API. Revisit this note if/when Anthropic ships
dated snapshots for those families — until then, do not "fix" the
split by re-pinning.

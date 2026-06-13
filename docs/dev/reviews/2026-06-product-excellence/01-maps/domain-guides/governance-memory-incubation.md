---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Governance, memory & incubation

> Lens, not survey. Severity anchors to the SIGNED charter; a gap matters
> only if it blocks a charter clause. Written under C-0: mechanisms and
> effort, no absolutes, no marketing register.

## 1. What mastery means here

This domain is the charter's **Working model** (W-1..W-4) plus **E-1** and
the **amendment ceremony**. Mastery is not "more process" — the owner's own
verdict is that ceremony has *net-accelerated* the work by removing thrash
(interview Q19/S15). Mastery here means three things specific to callback.:

- **The written governance matches the practiced one.** W-1/R2-11 is explicit:
  multi-altitude parallelism is the real model and the serial-session framing
  is stale. Mastery is codifying isolation rules (worktree-per-session,
  global-state ownership, branch ownership) that a *concurrent* agent can obey,
  and retiring CONTRIBUTING's "Future:" framing — not documenting a model the
  owner already contradicts daily (S16; this review is itself a parallel
  instance).
- **Enforceable governance is honestly separated from tribal knowledge.** Under
  C-0, a rule that only a deterministic test can enforce gets stated
  categorically; everything else is effort-language. Applied to *process*: a
  rule a hook enforces is governance; a rule that lives only in prose is a
  convention an agent can silently downgrade — the exact failure
  `feedback_hook_discipline` and the charter's "no escape hatch" paragraph
  exist to prevent.
- **Incubation has observable extraction gates.** W-4/Q23 names the trigger set
  (maturity / second-project need / attention economics) but leaves the
  maturity *metric* "TBD — review to propose." Mastery is a per-system,
  observable readiness signal for each of the five incubants, plus the W-2
  operator-stack triad (memory→context, governance→posture, operator-LLM) wired
  into the v1.0.7 assistant at build time (R2-10).

External best practice (policy-as-code, "governance as witness not blocker")
is welcome context, but the charter outranks it: P-3/D-4's soft-commitments
posture means human-promise governance stays best-effort; only machine gates
may be categorical (E-1, T-C).

## 2. Current state — strengths and gaps

**Enforced governance is real and well-wired.** Seven blocker-class hooks fire
PreToolUse with `exit 2` and are registered in `.claude/settings.json:15-95`:
`check-plan-approved`, `require-feature-branch`, `block-secrets`,
`validate-context`, `route-security-lint` (Edit|Write) and `block-merge-to-main`,
`ruff-changed` (Bash). These are blockers, not nudges. By contrast
`wiki-freshness-reminder.sh:59` *always* exits 0 — it is **witness-class** (a
`systemMessage` nudge, never a gate), and `mark-plan-approved.sh` /
`cleanup-plan-on-merge.sh` are PostToolUse state-managers, not gates. This
witness/blocker split is the compliance-agent's evidence base: the freshness
reminder is the precedent for a "flag, don't approve" drift report (amendment
ceremony, charter L344: "witness, not approver").

**Read-only subagents are precedents for the compliance agent.**
`prompt-archaeologist.md:1-66` and `tune-drafter` carry `tools: [Read, Grep,
Glob]` and explicitly "do NOT call Edit or Write" — diagnosis/diff only.
`git-flow.md:21-31` asks before every visible act. A compliance agent that
witnesses without merging has three in-repo precedents.

**The seven-functions self-model is a genuine strength** (`docs/system-model.md`):
Regulation (hooks/gate) and Governance (vision/principles) are named distinct
layers with a one-way dependency law, and the doc honestly flags Governance as
the one *prescribed* (not emergent) layer (system-model.md:104-108).

**Gaps blocking charter clauses:**
- *W-1 / R2-11 — the two live collisions are still in the code at c6e0437.*
  (a) `require-feature-branch.sh:36` reads `git rev-parse --abbrev-ref HEAD`
  with no worktree awareness (the worktree-blind branch hook). (b) The
  plan-marker is a **global** path: `check-plan-approved.sh:6`
  (`$HOME/.claude/plans/.approved`) and `cleanup-plan-on-merge.sh:28`
  (`rm -f`) — a concurrent merge in one session wipes the approval the other
  session is mid-edit under. Both are documented in the interview record
  (R2-11, project-plan-approved-marker memory) but neither has an isolation
  rule written into governance yet.
- *W-1 — CONTRIBUTING.md:219 still titles the multi-agent section "Future:"* —
  the stale framing R2-11 directed be retired.
- *W-4 — no maturity metric exists* for any of the five incubants; extraction
  is trigger-language only.
- *Tribal-only rules* (no hook): `PROMPT_VERSION` bump-in-same-commit, new-dep →
  pyproject+CHANGELOG, the close-out pre-sweep, the handoff-template
  reproduction. All are prose-enforced (AGENTS.md, AGENT_HANDOFF_TEMPLATE.md).

## 3. Rubric

- **BOOST** — An isolation rule-set is written as governance and the two
  collisions are structurally closed (worktree-aware branch detection; a
  per-session/per-worktree-scoped approval marker), with a witness-class drift
  report flagging amendment-ceremony violations. The operator-stack triad has a
  named governance interface in the v1.0.7 assistant design.
- **KEEP** — The blocker hooks and their `.claude/settings.json` wiring; the
  read-only subagent pattern (prompt-archaeologist/tune-drafter); the
  seven-functions self-model with its honest "prescribed" seam; the
  witness-class freshness reminder as compliance-agent precedent.
- **FIX** — Worktree-blind `require-feature-branch.sh:36`; the global plan
  marker (`check-plan-approved.sh:6` / `cleanup-plan-on-merge.sh:28`);
  CONTRIBUTING.md:219 "Future:" framing; the missing W-4 maturity signal.
- **DEBUFF** — Any new categorical *process* claim in docs that no hook
  enforces (C-0 violation in the governance prose itself); any escape-hatch
  (`CLAUDE_ALLOW_MAIN_EDITS`, hand-created `.approved`) used on agent
  initiative rather than explicit owner direction.
- **WATCH** — Tribal rules with no witness (PROMPT_VERSION, new-dep);
  extraction friction (W-4 reintegration is hoped-for, friction-dependent);
  agent-station dependency (W-3 canary) landing before v1.1.0.

## 4. Sharpest questions

(See structured output for the question bank with charter traces and
where-to-look pointers.)

```toml
schema = 1
id = 84
kind = "item"
title = "Build the N=1 baseline of the proposed chain-orchestration pipeline, pending owner authorization"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "implementer->refuter->judge->closer as a Workflow script, N=1; provably >= robust as today's process per the design."
```

**What this is.** The smallest buildable version of the architecture proposed
in `docs/dev/epic-a-chain-design-corrections.md` §16: a fresh implementer,
Sonnet refuter, judge, and closer, run for exactly one ordinary sprint (N=1)
as a Workflow script. At N=1 this pipeline **is** the current normal
handoff process, plus the refuter step (proven valuable — caught the item-20
defect — but currently absent from `AGENT_HANDOFF_TEMPLATE.md`) and a real,
correlated audit trail. §16.5.1 argues this is provably at least as robust as
today's process, since the boundary reviewer is still the owner, exactly as
today.

**Explicitly blocked, not merely deferred.** §16.7 names three decision
points for the owner: whether to pursue the design at all; whether, if
pursued, to authorize N=1 as the first step; and — not decided by this item
or implied by its filing — whether to ever widen N past 1, retire or merge
`AGENT_HANDOFF_TEMPLATE.md`, or resume any Epic B chain under the old §11
envelope. This item exists to make the next concrete build step legible and
trackable once authorized, not to authorize it.

## Updates

### 2026-08-11 — BUILT on `feat/n1-baseline-pipeline`; watching until the first authorized run

The authorized build landed: `.claude/workflows/n1-baseline.mjs` (the pipeline
script — two stages bracketing the invoking session's gate runs, escalation
primitive with a no-reviewer short-circuit for §11.5 halt points and hook
blocks, drift layer inert at N=1 by construction), `agents/n1-refuter.md` +
`agents/n1-judge.md` (read-only role definitions), the contract/runbook at
`docs/dev/n1-baseline-pipeline.md`, and the structural gate
`tests/test_n1_pipeline.py` (29 tests, RED-fixture scanner teeth first).

**Status `watching`, not `closed` — owner decision this session, taken on an
adversarial reviewer's finding:** the structural tests certify
self-consistency with the design docs, not harness compatibility — the
Workflow API the script targets has zero committed instances in this repo and
the script has never been executed (running is its own owner opt-in,
§16.5.2.3). Closing on `verified_by = ["tests/test_n1_pipeline.py"]` would be
exactly the "closure resting on weaker evidence than it claims" pattern the
closure bar exists for. Close when the first authorized run supplies real run
evidence.

### 2026-08-11 — owner resolved §16.7: pursue the design; N=1 baseline authorized

The owner answered §16.7's decision points in-session (branch
`fix/retired-roles-a3-prompt`, asked directly per the pre-Epic-B handoff's
"First move" step 3): **(1) pursue the C+drift design** rather than shelving
it as reference material, and **(2) the N=1 baseline build is authorized** as
the next concrete step. Status flips `blocked` → `open` accordingly. Decision
point (3) is unchanged — nothing here widens N past 1, retires or merges
`AGENT_HANDOFF_TEMPLATE.md`, builds the ledger extension (§16.5.2.2), or
resumes any Epic B chain under the old §11 envelope; each stays its own
later, owner-gated decision. Building the pipeline is a full-session piece of
work and was NOT taken on this branch (this session's one branch is item 75's
fix, per the one-branch-per-session rule) — it is the natural next-session
candidate.

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed as the concrete next-step pointer for the design pass's own
recommendation, `status = "blocked"` from the moment of filing since the
owner's decision has not yet been made.

```toml
schema = 1
id = 97
kind = "item"
title = "Owner direction: evaluate moving chain orchestration OUT of sartor to an external, user-configurable task system, with sartor syncing its dev mapping to it"
status = "blocked"
blocked_on = "owner design decision — this is a strategic redirect the owner raised; the tool choice and the scope of any sync layer are the owner's"
decision_owner = "user"
branches = ["feat/ats-conformance"]
refs = [
  "docs/dev/work/items/0084-build-n1-baseline-pipeline.md",
  "docs/dev/work/items/0093-epic-c-invoker-session-shape-decision.md",
  "docs/dev/work/items/0094-interrogative-witness-kills-pipeline-runs.md",
  "docs/dev/n1-baseline-pipeline.md",
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "Orchestration may belong outside the project; sartor's job becomes keeping ARC/CHECKLIST/ledger/BOARD in sync."
```

**The owner's direction, verbatim (2026-08-14, on screen, at run 6's close — the single
source for this item's intent; cite it, never restate it):**

> this experiment is proving that our iterative development may not be solvable at this
> point. I might need to incorporate a specific set of open source tools for running
> this sort of development. Perhaps leveraging something like github issues tracking to
> have a fresh agent poll the issues/task list and then run the next item in the hcain,
> thereby getting the desired outcome without requiring a specialized solution in sartor
> itself. this seems like it should lie outside the project to be honest and be managed
> by an external management system that can be user configurable and manage any such
> project. the job would then be to maintain our development mapping as we have with the
> arc, checklist, ledger, and board to sync with an external task list.

**Nothing here is decided.** This item exists so the direction is on the board before
Epic C planning, not to authorize a build. The tool choice, whether to adopt at all, and
the scope of any sync layer are the owner's.

## Why the run evidence supports the reframing

The N=1 pipeline has now produced six runs, and the pattern in the failures is that
**almost none of them were about the sprint work**. Runs died at, or were crippled by,
the *invocation and session boundary*:

| run | outcome | cause class |
|---|---|---|
| 1 (`wf_9bb80d14-c94`) | died at refuter spawn, 169k tokens, sprint discarded | harness contract (bare `agentType`) |
| 3 | epic silently stopped after one sprint of three | session/ceremony boundary |
| 4 | scope guess | contradictory scope records |
| 5 | boundary stop on doubled compaction | invoker context accumulation (item 93) |
| 6 | `escalated_to_owner`, zero code written | mid-run hook re-arm (item 94) |

The recurring shape is a **long-lived invoking session** that accumulates context, holds
per-session hook state, and must be talked to by the owner mid-flight. Every mitigation
so far has been a reducer against that shape rather than a removal of it.

**A fresh agent per task item structurally dissolves several open items rather than
fixing them:**

- **Item 93** (per-sprint fresh sessions vs continuous window) becomes moot — the
  external runner defines the boundary.
- **Item 94** (mid-run witness re-arm) largely stops existing — with no long-lived
  invoker being prompted mid-run, there is no armed pause for a subagent to eat.
- **Item 95**'s resume trap matters less — a fresh agent per item re-reads state from
  the task list instead of replaying a cached run.

That is the strongest argument for the redirect: it removes failure classes by
construction instead of adding another guard to each one, which is exactly the C-11
preference applied one level up.

## Open questions the evaluation must answer (not answered here)

1. **What is authoritative?** Today `docs/dev/work/BOARD.md` is generated from
   `docs/dev/work/items/*.md` and gate-checked. If an external list becomes the task
   source, one of the two is canonical and the other is a projection — deciding which
   is the whole design. A bidirectional sync with two writers is the drift class this
   repo's schema was built to remove (`docs/dev/work/SCHEMA.md`: "Two files agreeing on
   a child list is exactly the drift class this schema exists to remove").
2. **What survives extraction?** The governance that makes this repo's agents behave —
   C-7 evidence gating, C-10 consumer enumeration, C-11 closure bar, the handoff
   ceremony — is enforced by *in-repo* hooks and gates. An external runner does not
   inherit them; a fresh agent polling an issue still has to land inside this repo's
   guardrails. This argues the external system owns **sequencing and dispatch**, while
   the repo keeps **enforcement** — not a wholesale move.
3. **Which tools?** Deliberately unanswered. The owner named GitHub Issues as an
   example, not a selection.
4. **What does "user configurable / manage any such project" imply?** If the runner is
   meant to be generic across projects, the sync layer is a separate product surface,
   not a sartor feature — which is the owner's own framing ("this seems like it should
   lie outside the project").

## What this would make sartor's job

Per the owner's direction: maintain the development mapping already carried by
`RELEASE_ARC.md`, `RELEASE_CHECKLIST.md`, the provenance ledger, and `BOARD.md`, and
keep it **in sync with an external task list**. That is a narrower and more durable
responsibility than hosting an orchestrator, and it plays to what the repo already does
well — the mapping artifacts exist, are gate-checked, and have survived six runs intact
while the orchestration around them kept failing.

## Updates

### 2026-08-14 — filed at the close of run 6 (`feat/ats-conformance`)

Filed at the owner's direction to document run 6 for the next agent. The direction was
given after the run-6 `hook_block` stop and after the blast-radius analysis of fixing
item 94 in-project was presented. **Epic B is NOT complete** — B2 remains unimplemented
— so this item does not supersede the epic; it reframes how the *remaining* work might
be driven.

```toml
schema = 1
id = 89
kind = "item"
title = "n1-baseline.mjs's closer prompt hardcodes the full AGENT_HANDOFF_TEMPLATE.md ceremony every sprint, contradicting the epic's own declared lighter cadence"
status = "watching"
decision_owner = "agent"
branches = ["fix/b1-stale-template-companions"]
refs = [
  ".claude/workflows/n1-baseline.mjs",
  "docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md",
  "docs/dev/handoffs/epic-b-design-brief.md",
  "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
]
summary = "n1-baseline.mjs hardcodes the full handoff ceremony every sprint; the design brief declared a lighter per-sprint one."
```

**Origin.** Found by the B1a closer while writing the inter-sprint handoff, before
choosing a template — a member of a known class already on this board (items
54, 65, 81, 82, 86: a declared design/doc statement drifting from the actual
code/mechanism, per C-11's own thesis that undeclared drift between the two is
counted as protection by whoever reads next).

**The two sources, quoted.**

1. `docs/dev/handoffs/epic-b-design-brief.md` ("Close-out intervals",
   owner-approved 2026-08-11): *"Per-sprint floor (non-negotiable, §15.2's
   list): C-7/C-10 dossiers where triggered (hook-gated), a substantive commit
   message, **the next sprint's brief (from `EPIC_SPRINT_BRIEF_TEMPLATE.md`,
   written by that run's closer — this is the inter-sprint handoff under
   test)**... **Deferred to the epic close** (scheduled, not skipped): ...
   **the full `AGENT_HANDOFF_TEMPLATE.md` ceremony with `verify_doc_template.py`
   validation**, `BOARD.md` regeneration..."*
2. `.claude/workflows/n1-baseline.mjs:441-446` (the closer role's own hardcoded
   prompt text, verified by direct grep this session): unconditionally directs
   *every* closer invocation — sprint or epic — to write from
   `docs/dev/AGENT_HANDOFF_TEMPLATE.md` and validate with
   `scripts/verify_doc_template.py ... --event generated`. No branch in the
   script's prompt text distinguishes an intra-epic sprint transition from a
   genuine session close.

`EPIC_SPRINT_BRIEF_TEMPLATE.md`'s own header is explicit about the intended
split: *"Do not use this in place of `docs/dev/AGENT_HANDOFF_TEMPLATE.md`. That
template is the session-to-session handoff at a branch close... It is still
required at the epic close-out, and any time a session genuinely ends."* — i.e.
the design's own contract already names the discriminator (session-end vs.
intra-epic transition); the pipeline script just never got the conditional.

**Why not fixed here.** `n1-baseline.mjs` is the pipeline mechanism itself,
mid-run, on B1a's closing turn — editing it now is a scope change to the
pipeline under active test, matching
`docs/dev/epic-a-chain-design-corrections.md` §11.6.5 ("a C-11 recurrence whose
fail-closed mechanism would be a new enforcement surface — that is itself a
scope change, and the owner decides") almost exactly. No mechanism authored on
this branch; declared plainly per C-11's own explicit allowance for that case.

**What this branch actually did, and why it is not a violation either way.**
This closer followed the literal, current, machine-sourced instruction (which
matches `n1-baseline.mjs` verbatim) and wrote the full
`docs/dev/AGENT_HANDOFF_TEMPLATE.md` ceremony for the B1a → B1b transition —
the more conservative of the two valid readings (more ceremony, not less), and
explicitly permitted by `EPIC_SPRINT_BRIEF_TEMPLATE.md`'s own text ("This is a
floor, not a form"). The cost is efficiency, not correctness: every Epic B
sprint transition pays the full ceremony's token/time cost that the epic's own
close-out-interval design argued against paying more than once (three sprints
× full ceremony is exactly the "wrong end of the trade" the design brief
itself warns against, `epic-b-design-brief.md` §"Close-out intervals").

**Fix, when scheduled:** add a branch in `n1-baseline.mjs`'s closer prompt —
epic-internal sprint transition (there is a next sprint in the same epic,
stacked on the same epic branch) uses `EPIC_SPRINT_BRIEF_TEMPLATE.md`; a
terminal close (epic finish, or a standalone non-epic branch) uses
`AGENT_HANDOFF_TEMPLATE.md`. Needs the epic's own post-run review (§12 of the
corrections doc) to decide whether the extra rigor observed this run (a
first-live-fire pipeline, three infra fixes needed) is itself evidence the
heavier cadence was worth the cost this time — record, don't retrofit mid-epic
(the design brief's own stated policy for cadence changes).

## Updates

### 2026-08-12 — filed during `fix/b1-stale-template-companions` close-out (B1a closer)

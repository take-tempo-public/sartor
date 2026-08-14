```toml
schema = 1
id = 96
kind = "item"
title = "Sprint briefs prescribe an implementer model in prose while their copy-paste First-move block omits the arg, so the script default silently wins"
status = "open"
decision_owner = "agent"
branches = ["feat/ats-conformance"]
refs = [
  "docs/dev/handoffs/epic-b-b2-brief.md",
  "docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md",
  ".claude/workflows/n1-baseline.mjs",
  "docs/dev/RELEASE_ARC.md",
]
summary = "Following a brief's First-move block exactly produces a model the same brief's prose forbids."
```

**The defect.** `epic-b-b2-brief.md` §"Sprint identity" prescribes a **Sonnet**
implementer for B2 (from `epic-b-design-brief.md` row 3 / `RELEASE_ARC.md` §"Session
models"). Its own §"First move" block — the one an invoker is told to copy verbatim —
passes **no model args at all**. The script then applies its defaults
(`.claude/workflows/n1-baseline.mjs:309-311`: `implementerModel: 'opus'`,
`closerModel: 'sonnet'`, `reviewerModel: 'opus'`).

**So following the brief exactly produces the model the same brief forbids**, silently,
with nothing anywhere in the run reporting the discrepancy. Observed live: Epic B run 6
executed with an **Opus** implementer against a brief prescribing Sonnet, and the
divergence was only caught because the owner's invocation message happened to mention a
model and the invoker went looking for what "as is" resolved to.

**Generalizes.** The First-move block shape is inherited from
`EPIC_SPRINT_BRIEF_TEMPLATE.md`, so every intra-epic brief the pipeline's own closer
writes carries the same hole. Epic C repeats the experiment and would inherit it.

**Candidate mechanisms (C-11 — pick one, do not leave this as prose).**

1. **Require the model args in the pipeline.** Make `implementerModel` a required arg
   on the sprint stage rather than a defaulted one, the same way `closeoutKind` was
   removed as a caller arg and `epicSprintIndex`/`epicSprintCount` were made required.
   A brief that omits it then fails loudly at invocation instead of silently
   downgrading. Strongest option: it fails closed, and the precedent already exists in
   this script.
2. **Make the template's First-move block carry the args its prose prescribes**, plus a
   structural test asserting that any brief naming a model in prose also passes it in
   its fenced invocation block. Weaker (a text check over prose), but it catches the
   authoring error at the source.

Option 1 is preferred; option 2 is the fallback if a required arg proves too rigid for
standalone (1-of-1) branches.

**Related but distinct:** the *invoking* session's model has its own, separate
ambiguity — "running on opus" is the literal phrasing the authorization record uses for
the invoker, and run 6 read it as the implementer. That is a wording collision in the
authorization record, not this template defect; both bit the same run.

## Updates

### 2026-08-14 — filed at the close of run 6 (`feat/ats-conformance`)

Run 6 executed with **both** model slots off their prescribed values in opposite
directions — invoker Fable (owner wanted Opus; not restartable mid-session) and
implementer Opus (brief prescribes Sonnet). The owner accepted both rather than restart,
so B2's eventual results are **not a clean read of the prescribed configuration** — a
fact that belongs with any epic-level conclusion drawn from this run.

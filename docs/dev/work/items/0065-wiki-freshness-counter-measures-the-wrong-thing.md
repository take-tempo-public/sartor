```toml
schema = 1
id = 65
kind = "item"
title = "The wiki freshness counter measures \"files changed since checkpoint\", not \"coverage current\" — a scoped pass can never honestly advance it"
status = "watching"
decision_owner = "user"
refs = [
  "scripts/wiki_freshness.py",
  "scripts/wiki_relevance.py",
  "docs/wiki/.last_ingest_sha",
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "Drift = files-since-checkpoint assumes periodic catch-up passes; under a per-branch workflow it self-perpetuates."
```

**Full analysis: `docs/dev/epic-a-chain-design-corrections.md` §11.11.** Not restated
here (schema §3 — an item points, it does not copy).

**The class, in one paragraph.** `docs/wiki/.last_ingest_sha` is a single repo-wide
"everything up to here is ingested" marker, and the freshness gate computes drift as *files
changed since that marker*. That definition assumes periodic full catch-up passes. Item 35
(2026-08-04) made small per-branch incremental updates the norm instead — and under that
workflow a correctly-executed scoped pass **cannot honestly advance the checkpoint**,
because advancing it would assert that the whole backlog, not just this branch's slice, had
been ingested. So correctly-ingested work still inflates the counter, every honest agent
declines the advance, the backlog grows, and the next refusal is more certain. A ratchet
that is never zeroed cannot engage.

**Sprint A1b is the worked instance:** it wrote 7 pages, verified 3 no-edit, repaired 4
auditor findings — and correctly declined the advance under C-12, saying so in
`docs/wiki/log.md`. Its diligence and the growing counter were the same event.

**What this sprint did, and what it did not do.** A2's closer ran the pass widened to the
full `65b0f88`→HEAD delta and advanced `.last_ingest_sha` to `2a0b37a`, taking drift from
36 to 0. **That fixed the instance, not the class.** The counter will re-diverge the moment
a pass is scoped narrower than the checkpoint gap again — which is exactly what happens if
any single sprint's closer skips or scopes its pass, or if work lands outside the sprint
chain. Nothing structural prevents the recurrence; only the zeroed starting point and a
standing expectation that each sprint advances the checkpoint.

**No mechanism was authored (C-11, stated plainly).** A fix here means changing what the
gate *measures* — coverage currency rather than commit distance — which is a redesign of an
existing enforcement surface, not a note. Landing that at a sprint close-out is a flag stop
under the Epic A authorization envelope (`docs/dev/epic-a-chain-design-corrections.md`
§11.6.5): new or redesigned enforcement is the owner's decision, not a closer's.
`decision_owner = "user"` records that.

**Sketch of the options, for whoever takes it** (none evaluated, none endorsed):

1. Redefine drift as *wiki-relevant files changed since the checkpoint that no wiki page
   cites* — coverage-shaped, so an ingested file stops counting whether or not the marker
   moved.
2. Keep the commit-distance metric but make the checkpoint **per-path** rather than
   repo-wide, so a scoped pass can advance exactly the slice it covered, truthfully.
3. Keep everything and rely on the standing per-sprint expectation, accepting that the
   counter is a tripwire for "nobody has run a pass lately" rather than a coverage measure
   — and say so in the gate's own output, which currently reads as the latter.

## Updates

### 2026-08-09 — filed at `feat/compose-wait-ux` close-out (Epic A, sprint A2)

Filed by the A2 closer, per §11.11's own "to file as a work item" instruction. The
checkpoint advance to `2a0b37a` landed on this branch; this item tracks the structural
question that advance does not answer.

# Compliance log

> Append-only record of [`/compliance-witness`](../../commands/compliance-witness.md)
> governance-drift runs. **Newest entry last.** Each run records the pinned-sha window,
> the per-tier flag counts (FLAG / WATCH / AFFIRM, plus withheld over the cap), and the
> gate verdict. The witness **reports; it never edits, blocks, or commits** — the
> read-only subagent is [`agents/compliance-witness.md`](../../agents/compliance-witness.md).
> Severity anchor: [`charter.md`](charter.md).

## 2026-06-16 — pilot run (`feat/compliance-agent-pilot`)

- **Window:** `e299ac8` (v1.0.6 tag) → HEAD `1741ab1`. Primary surface: the
  freshly-graduated `docs/governance/` (charter / enforcement / metrics, added 7.2).
- **Counts:** FLAG 1 · WATCH 2 · AFFIRM 3 · 0 withheld (cap 12).
- **Gate verdict:** **needs attention** (1 FLAG-tier).
- **FLAG — CW-01:** [`RELEASE_CHECKLIST.md:64`](../dev/RELEASE_CHECKLIST.md) marks Sprint
  7.2 (`feat/governance-extraction`) `[ ]` "feat/ half pending", but the branch merged
  (`2b35551`), `docs/governance/` exists at HEAD, and `CHANGELOG.md` records it landed.
  Plan vs. repo + git + changelog. Surfaced for the owner; the witness does not fix it.
- **WATCH:** CW-02 (a wiki page anticipates a `raw/` that governance-extraction merged
  without — already self-noted in [`../wiki/log.md`](../wiki/log.md)); CW-03 (an
  enforcement-vocabulary count is loose — definitional, reconcilable).
- **AFFIRM:** the charter's "lands this branch" self-claims are accurate in code/docs —
  PX-24 (`block-merge-to-main.sh`), PX-28 (`check-plan-approved.sh`), and the W-1 reframe
  (cited in `RELEASE_ARC.md`).
- **Rubric outcome (owner-scored 2026-06-16):** CW-01 = **true drift** →
  **flag-precision 1/1 = 1.0 ≥ 0.66 → pilot PASSES.** CW-01 corrected at owner direction
  (the 7.2 plan row flipped to `[x]`/DONE on this branch); the witness surfaced, the human
  decided. Per the design's Arc, a passing pilot graduates the witness toward the standing
  pre-tag companion at v1.1.x.
- **Note:** first run; the registered `/sartor:compliance-witness` surfaces on the next
  Claude Code reload — this pilot reproduced the Sonnet subagent in-session (the
  registered Task-delegated path is contract-identical).

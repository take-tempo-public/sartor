# Wiki index — `docs/wiki/`

> One-line summary per page. Doubles as the map the root
> [`llms.txt`](../../llms.txt) points at. Pages are added as they are ingested —
> see [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5.

## Pages

### Front door

- [`overview.md`](overview.md) — what callback. is and how the whole system is shaped
  (seeded from, and deferring to, [`../system-model.md`](../system-model.md)).

### From the excellence walk (ingested by `wiki/ingest-excellence-walk`, WS-4a step 4)

- [`pages/excellence-walk.md`](pages/excellence-walk.md) — what the 2026-06-07 excellence
  walk was; the provenance hub mapping to every page below.
- [`pages/system-model-derivation.md`](pages/system-model-derivation.md) — how the
  seven-functions self-model was form-found (defers to [`../system-model.md`](../system-model.md)).
- [`pages/project-self-assessment.md`](pages/project-self-assessment.md) — the Q5
  state-of-the-work: strengths, watch-outs, ambiguous calls, with presentation flags.
- [`pages/consistency-tracks-enforcement.md`](pages/consistency-tracks-enforcement.md) —
  the Q2 finding: the code is consistent exactly where a hook or linter enforces it.
- [`pages/non-dependency-downloads.md`](pages/non-dependency-downloads.md) — the Q3
  provenance of everything `pip install` does not hand you (the eval-stack input).
- [`pages/engineering-workstreams.md`](pages/engineering-workstreams.md) — the WS-1…WS-4
  backlog (blueprints · strict typing · test-suite pass · the wiki) + phase mapping.
- [`pages/llm-wiki-design.md`](pages/llm-wiki-design.md) — why this wiki is shaped as it
  is (the WS-4 design rationale; defers to [`SCHEMA.md`](SCHEMA.md) for the conventions).
- [`pages/governance-extraction.md`](pages/governance-extraction.md) — the planned
  canonical-Governance extraction that resolves the mixed-doc crux (design only).

## Wiki infrastructure

- [`SCHEMA.md`](SCHEMA.md) — wiki conventions, the one grounding rule, the
  git-as-engine source model.
- [`log.md`](log.md) — append-only record of ingest / lint runs.

## Reserved / planned (not yet ingested)

- The **code architecture** (module map, the P1 deterministic/LLM boundary, the
  `context_set` contract, pipeline flows, routes, the eval harness) is **not yet
  ingested** — that is the whole-repo cold pass `wiki/cold-ingest-code` (WS-4b), which
  also advances `.last_ingest_sha` from its sentinel. See
  [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5 (WS-4b).

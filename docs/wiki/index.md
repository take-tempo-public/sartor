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

### From the code cold-ingest (`wiki/cold-ingest-code`, WS-4b)

All `audience: dev`; every code claim `path:line`-grounded against HEAD.

- [`pages/code-module-map.md`](pages/code-module-map.md) — the top-level module
  inventory + the inward-dependency shape; the hub for every code page.
- [`pages/deterministic-llm-boundary.md`](pages/deterministic-llm-boundary.md) — the P1
  boundary: all LLM in `analyzer.py`, the rest deterministic by contract.
- [`pages/prompt-version-discipline.md`](pages/prompt-version-discipline.md) — the
  `PROMPT_VERSION` bump rule + the eval prompt-override primitive.
- [`pages/context-set-contract.md`](pages/context-set-contract.md) — the `context_set`
  JSON contract every pipeline stage reads + writes; the containment guard.
- [`pages/iteration-audit-chain.md`](pages/iteration-audit-chain.md) — per-generate
  child context files; `parent_context_path` as the immutable audit trail.
- [`pages/corpus-data-model.md`](pages/corpus-data-model.md) — the SQLite corpus schema
  + the unified Corpus-Item lifecycle; alembic head 0010.
- [`pages/corpus-to-output-reach.md`](pages/corpus-to-output-reach.md) — how curation
  reaches the deliverable: JSON-Resume build + the `composition_overrides` shape.
- [`pages/application-audit-chain.md`](pages/application-audit-chain.md) — the per-apply
  DB record: `Application` / `ApplicationRun` / the proposal-review trail.
- [`pages/pipeline-stages.md`](pages/pipeline-stages.md) — the end-to-end apply-run:
  analyze → clarify → compose → generate → iterate.
- [`pages/llm-call-catalog.md`](pages/llm-call-catalog.md) — the LLM call kinds, model
  routing (Sonnet/Haiku), and the two-pass analyze.
- [`pages/generation-and-grounding.md`](pages/generation-and-grounding.md) — `generate`
  + the deterministic post-generation grounding metrics that score it.
- [`pages/route-surface.md`](pages/route-surface.md) — the `app.py` Flask routes, the
  security gate, and the B.4/B.5 corpus-completer routes.
- [`pages/frontend-wizard.md`](pages/frontend-wizard.md) — the six-step wizard, the
  Compose cards, the live preview, and smart landing.
- [`pages/document-rendering.md`](pages/document-rendering.md) — the deterministic
  markdown → JSON-Resume → docx/pdf/md render path.
- [`pages/eval-harness.md`](pages/eval-harness.md) — the offline eval system: suites,
  rubric judges, baseline/anchors, bootstrap, prompt-override A/B.
- [`pages/diagnostics-console.md`](pages/diagnostics-console.md) — the localhost
  `/_dashboard` console + the SSE eval/tune/annotation loop.

## Wiki infrastructure

- [`SCHEMA.md`](SCHEMA.md) — wiki conventions, the one grounding rule, the
  git-as-engine source model.
- [`log.md`](log.md) — append-only record of ingest / lint runs.

## Reserved / planned (not yet authored)

- **User-facing education pages** (`audience: user`) are **reserved for the Sprint 6.5
  education sweep**, which authors them INTO this wiki. They do not exist yet — there is
  no `[[link]]` to them, and "no `user`-tier pages under `pages/`" is a lint INFO, not an
  error (see [`SCHEMA.md`](SCHEMA.md) "Audience tag"). Today the only `user`-tier page is
  the front-door [`overview.md`](overview.md). See
  [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5 (Sprint 6.5) and
  [`../dev/memory-architecture.md`](../dev/memory-architecture.md) (the access plane
  these tags gate).

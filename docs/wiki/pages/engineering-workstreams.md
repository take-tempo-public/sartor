# Engineering workstreams (WS-1…WS-4)

> **Concept:** the engineering-excellence backlog the walk produced — four workstreams
> toward "a polished production codebase," with what / why / status and where each lands
> in the release arc.
> **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "PART B" · [`../../dev/RELEASE_ARC.md`](../../dev/RELEASE_ARC.md) (§Phase 4.5, §4.8,
> post-public) for the phase mapping.
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); sequencing claims cite RELEASE_ARC,
> which is authoritative and may move — re-check it, not this page, for the live plan.

---

## WS-1 — decompose `app.py` into Flask blueprints
- **What:** split the 6,290-line / 75-route monolith into domain blueprints (candidate
  seams: analysis, generation/cover-letter, corpus, dashboard, user/config, templates),
  preserving the `_safe_username`/`_within` gate + the hook that lints it.
- **Why:** navigability + parallel future development; the single biggest *structural*
  gap to polished production (see [[project-self-assessment]],
  [[consistency-tracks-enforcement]]).
- **Status / where:** design-pending — needs its own session; it rewrites routes nearly
  every branch touches, so it must run in a dedicated low-churn window. Lands as
  **v1.0.8** (RELEASE_ARC §Phase 4.8), after the product is feature-complete and before
  the public cut.

## WS-2 — tighten typing toward strict + model the data contracts
- **What:** move mypy toward `strict=true` (per-module ratchet); model `context_set` and
  the `dict`-typed request/response payloads as TypedDict/dataclass/Pydantic.
- **Why:** turns runtime-only guarantees into edit-time ones; the `context_set` contract
  deserves to be a *type*, not prose + JSON-schema (the "data-contract typing" gap in
  [[consistency-tracks-enforcement]]).
- **Status / where:** the modest first increment (annotate route returns / flip
  `check_untyped_defs` — "PV-4") is **absorbed into v1.0.8** as the routes move; the full
  `mypy --strict` ratchet + a typed `context_set` spine is the post-public **WS-2-full**
  (1.1.x recurring). Reconcile with the release plan's PV-4 type scan so the work isn't
  done twice `[synthesis]`.

## WS-3 — test-suite engineering-design pass
- **What:** a periodic design review of the ~955-test suite for efficiencies,
  redundancies, slow tests, coverage gaps, fixture duplication.
- **Why:** stay "90%-in-spirit" *and keep getting better* — prevent the suite from
  accreting cost/redundancy as it grows.
- **Status / where:** recurring / future; a post-public continuing workstream
  (RELEASE_ARC "post-public 1.1.x series"). Define cadence + what "good" looks like.

## WS-4 — the LLM-wiki knowledge architecture
- **What:** adopt the LLM-wiki pattern (codebase variant: git HEAD as source,
  diff-driven ingest) as a committed `docs/wiki/` layer, with `ingest/query/lint/audit`
  ops as Claude Code skills + a root `llms.txt`.
- **Why:** Q4 — context-management for the agent, discoverability for humans + LLMs, and
  the substrate for the post-v1.1.0 doc-grounded assistant; the Sprint 6.5 education
  sweep authors *into* it. Its design rationale is **[[llm-wiki-design]]**; its follow-on,
  lifting the prescriptive rules into one canonical home, is **[[governance-extraction]]**.
- **Status / where:** **active — landing across v1.0.6** (RELEASE_ARC §Phase 4.5). WS-4a
  (the substrate) is front-loaded; this very wiki page is part of WS-4a step 4. WS-4b
  (the code cold-ingest) follows after Sprint 6.4 when route-churn settles.

## Related

- [[excellence-walk]] — the walk this backlog belongs to.
- [[system-model-derivation]] — the lenses that surfaced these gaps.
- [[consistency-tracks-enforcement]] · [[project-self-assessment]] — where WS-1/WS-2 are
  diagnosed.
- [[llm-wiki-design]] — the WS-4 design in depth.

# Engineering workstreams (WS-1…WS-4)

> **Audience:** `dev`
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
- **What:** split the (walk-era) 6,290-line / 75-route monolith into domain blueprints
  (analysis, generation/cover-letter, corpus, dashboard, user/config, templates),
  preserving the `_safe_username`/`_within` gate + the hook that lints it.
- **Why:** navigability + parallel future development; the single biggest *structural*
  gap to polished production (see [[project-self-assessment]],
  [[consistency-tracks-enforcement]]).
- **Status / where: ✅ SHIPPED.** Landed as Sprint 8.3a–h (`refactor/app-factory-and-infra`
  foundation + one domain seam per branch), tagged **v1.0.8**. `app.py` is now a
  ~296-line composition root (`create_app()` factory + `register_blueprints()` +
  `main()`) with **zero** `@app.route` decorators; every route lives on one of eight
  domain blueprints under [`blueprints/`](../../../blueprints/) (`analysis.py`,
  `generation.py`, `corpus/` — a 7-submodule sub-package, `templates.py`,
  `applications.py`, `users.py`, `diagnostics.py`, `assistant.py`) — 117 route
  decorators total, each monolith-origin seam registering with no `url_prefix` so
  every URL stayed byte-identical. The `_safe_username`/`_within` gate moved to the
  new leaf package [`web_infra/security.py`](../../../web_infra/security.py); the
  `route-security-lint` hook and the PX-29 `tests/test_route_containment_gate.py`
  gate both widened to cover `blueprints/**.py`. Full inventory: [[route-surface]] +
  [[code-module-map]]. The structural gap this workstream targeted is closed
  `[synthesis]`.

## WS-2 — tighten typing toward strict + model the data contracts
- **What:** move mypy toward `strict=true` (per-module ratchet); model `context_set` and
  the `dict`-typed request/response payloads as TypedDict/dataclass/Pydantic.
- **Why:** turns runtime-only guarantees into edit-time ones; the `context_set` contract
  deserves to be a *type*, not prose + JSON-schema (the "data-contract typing" gap in
  [[consistency-tracks-enforcement]]).
- **Status / where:** the modest first increment (annotate route returns / flip
  `check_untyped_defs` — "PV-4") landed with v1.0.8 as the routes moved. The **strict
  half is also now shipped**: the `mypy --strict` ratchet reached its **§6 exit**
  (2026-07-10, the `chore/kit-mypy-strict-*` branch stack, ratchet rungs 4–8) — every
  non-exempt production module (all 81) carries the strict override; only the
  Decision-7 exempt set stayed permissive, and the exit is enforced **by
  construction** via
  [`tests/test_mypy_strict_roster_gate.py`](../../../tests/test_mypy_strict_roster_gate.py)
  rather than a one-time proof (closes compliance-witness CW-118). **The exempt set
  then narrowed further** (2026-07-10, `chore/mypy-strict-tooling`, owner-directed
  v1.0.9 tooling-slice pull-in): `scripts/`, `evals/`, and `db/migrations/versions/`
  were brought to full `--strict` too (72 measured errors fixed — bare-generic
  `dict`/`list` parametrization, missing param annotations, `cast(...)`-wrapped
  `no-any-return`s; zero behavior change), leaving **`tests/` as the only remaining
  exempt prefix** — the roster gate's `_EXEMPT_PREFIXES` narrowed to match, and a
  new `test_migrations_versions_is_strict_rostered` asserts the versions tree
  stays covered `[synthesis]`. The typed `context_set` spine (a typed model, not
  just strict-checked `dict`s) is the remaining, still-open half — that stays the
  post-public **WS-2-full** (1.1.x recurring; see
  [`docs/dev/kit-adoption-design.md`](../../dev/kit-adoption-design.md) §6)
  `[synthesis]`.

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
  the substrate for the now-shipped doc-grounded assistant (v1.0.7; `blueprints/assistant.py:POST /api/assistant/ask` `[synthesis]`); the Sprint 6.5 education
  sweep authors *into* it. Its design rationale is **[[llm-wiki-design]]**; its follow-on,
  lifting the prescriptive rules into one canonical home, is **[[governance-extraction]]**.
- **Status / where:** **active — landing across v1.0.6** (RELEASE_ARC §Phase 4.5). WS-4a
  (the substrate) is front-loaded; this very wiki page is part of WS-4a step 4. WS-4b
  (the code cold-ingest) follows after Sprint 6.4 when route-churn settles.

## Related

- [[excellence-walk]] — the walk this backlog belongs to.
- [[system-model-derivation]] — the lenses that surfaced these gaps.
- [[consistency-tracks-enforcement]] · [[project-self-assessment]] — where WS-1/WS-2 were
  originally diagnosed as gaps; both are now closed (see above).
- [[llm-wiki-design]] — the WS-4 design in depth.
- [[code-module-map]] — the post-WS-1 `blueprints/` + `web_infra/` module inventory
  (the single-file `app.py` monolith WS-1 decomposed); the code cold-ingest is WS-4
  realized.
- [[route-surface]] — the `blueprints/` route inventory WS-1 produced.

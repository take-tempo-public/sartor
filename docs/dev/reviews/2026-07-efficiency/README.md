---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# 2026-07 Efficiency & Optimization Review

> **Review artifact — not canonical.** Nothing in this folder states current
> project policy; it is a point-in-time witness record pinned at
> `evidence_sha: 4196d0c` (HEAD of `main`, 2026-07-03). The canonical homes
> remain the charter, AGENTS.md, and the living docs. **Never wiki-ingest
> this folder.** Prescriptions graduate into the release arc through normal
> dev branches, not by copying text out of here.

## Scope

A witness-style efficiency/optimization review of the whole project across
four areas, hunting efficiency, speed, reliability, and simplification wins
in accordance with project goals and UX/DX:

| Area | Domain tag | Deep-scope surfaces |
|---|---|---|
| A — Agent-process & governance DX | `adx` | hooks, plugin commands/subagents, session-start context tax, memory, close-out ceremony |
| B — Runtime performance & reliability | `run` | LLM routing/caching/telemetry, code hotspots, DB, frontend assets |
| C — Docs & wiki processes | `doc` | canonical-doc overlap, wiki ingest lag, DOC-STATUS, ledger hygiene |
| D — Tests, CI & gates | `tci` | suite shape/runtime, gate tests, CI matrix/cost, tooling ratchets |

The review **reports and prescribes only** — no code, hook, config, prompt,
or living-doc edits ride in this pass. Every prescription lands later in its
own branch with owner sign-off.

## Method

Standard multi-agent, budget-bound (Max 5x): 8 survey finders (sonnet/haiku)
→ 2 scribes → adversarial verification of every P0/P1 finding (refute-framed,
main-loop ratification) → prescriptions with a 2-judge band panel
(Throughput-Value + Stability-Risk lenses; CONTESTED on >1-band spread).
Deviation from the 2026-06 review's 3-judge panel is deliberate (budget) and
documented in [`prescriptions.md`](prescriptions.md). Finders carried a
shared exclusion brief (the 8 open carry-forward ledger items + PX-01..36)
to avoid re-reporting tracked work, and a PII prohibition (paths citable,
content never, for `evals/fixtures/real/`, `configs/`, `resumes/`, `output/`).

## Stage status

| Stage | Status |
|---|---|
| 1 — setup (branch, pin, scaffold, exclusion brief) | IN PROGRESS |
| 2 — survey (8 finders) | pending |
| 3 — draft (findings files + register rows) | pending |
| 4 — verify (P0/P1 adversarial) | pending |
| 5 — prescribe (PX-37+, banding) | pending |
| 6 — seal (consistency check, CHANGELOG, ledger) | pending |

## Files

- [`findings-register.md`](findings-register.md) — master 9-column register
- [`findings/`](findings/) — per-area detail (a-process-dx, b-runtime, c-docs-wiki, d-tests-ci)
- [`verification-log.md`](verification-log.md) — falsification record for every P0/P1 verdict
- [`prescriptions.md`](prescriptions.md) — PX-37+ action layer, banded

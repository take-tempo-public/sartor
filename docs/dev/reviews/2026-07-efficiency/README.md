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

Standard multi-agent, budget-bound (Max 5x): 8 survey finders (5 sonnet +
3 haiku, shared exclusion brief) → orchestrator-drafted findings files →
adversarial verification of every P0/P1 finding (3 sonnet verifiers,
refute-framed, mixed-area batches, main-loop ratification against primary
evidence) → prescriptions with a 2-judge band panel (Throughput-Value +
Stability-Risk lenses + orchestrator tiebreak; CONTESTED on >1-band spread —
none occurred). Finders carried the 8 open carry-forward ledger items +
PX-01..36 as a dedup brief, and a PII prohibition (paths citable, content
never, for `evals/fixtures/real/`, `configs/`, `resumes/`, `output/`).

**Method deviations from the 2026-06 review, all budget-driven and
documented in place:** 2 band judges instead of 3
([`prescriptions.md`](prescriptions.md) preamble); the planned scribe stage
was cut (the orchestrator held all finder output in context and wrote the
findings files directly — no fidelity loss, ~240k tokens saved); one finder
(A2 session-tax) returned a degenerate structured-output stub and was
re-run as a standalone agent. Verification materially changed the record:
1 finding REFUTED outright (F-run-01), 9 WEAKENED (including the headline
P0's serial-execution premise — hooks run in parallel), and one claim
escalated (F-tci-05: the 3.10 floor is actively broken, not just untested).
One measurement dispute (F-tci-01) was resolved by an idle re-measurement
recorded in the [`verification-log.md`](verification-log.md) addendum.

## Stage status

| Stage | Status |
|---|---|
| 1 — setup (branch, pin, scaffold, exclusion brief) | complete (ccddb9a) |
| 2 — survey (8 finders + 1 re-run) | complete — 43 findings |
| 3 — draft (findings files + register rows) | complete (b016efb) |
| 4 — verify (P0/P1 adversarial, 14 verdicts) | complete — 4 CONFIRMED / 9 WEAKENED / 1 REFUTED |
| 5 — prescribe (PX-37..56, banding) | complete — 20 rows, 0 CONTESTED |
| 6 — seal (consistency check, CHANGELOG, ledger) | complete |

## Files

- [`findings-register.md`](findings-register.md) — master 9-column register
- [`findings/`](findings/) — per-area detail (a-process-dx, b-runtime, c-docs-wiki, d-tests-ci)
- [`verification-log.md`](verification-log.md) — falsification record for every P0/P1 verdict
- [`prescriptions.md`](prescriptions.md) — PX-37+ action layer, banded

# sartor. — Decision index

> **Purpose:** a single chronological log of **architectural / design decisions** —
> one line each, pointing to the full record where the rationale lives. This is the
> *thin index* (charter D5 cite-don't-restate): it closes the "no one place to browse
> all decisions" gap **without** duplicating or competing with the existing homes.
> **Audience:** any agent or human who needs to know *what was decided and where to
> read why*, without grepping the roadmap.
> **Scope boundary (what lives where):**
> - **Binding rules** → [`../governance/charter.md`](../governance/charter.md) (with the
>   amendment ceremony). Not logged here.
> - **Roadmap / sequencing** → [`RELEASE_ARC.md`](RELEASE_ARC.md) +
>   [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). Not logged here.
> - **Architectural / design decisions** → logged here as one line + a pointer to the
>   design doc / checklist entry / charter clause that holds the full record.
>
> **How to add a row:** newest at the top of its section. State the decision + the
> resolution in one line; point to the record; never restate the rationale (it lives in
> the pointed-to doc). Decisions are *superseded*, not edited — add a new row that links
> the one it replaces.

---

## Open decisions

_(none tracked here yet — open questions live in their design doc's "open items" section
or the Carry-forward ledger until resolved.)_

---

## Settled decisions

### 2026-07-11 — Subagent model-pin split: dated Haiku snapshot vs undated Sonnet alias (doc-only half of PX-47)

Full record + rationale:
[`reviews/2026-07-efficiency/px-staleness-reverify-2026-07-07.md`](reviews/2026-07-efficiency/px-staleness-reverify-2026-07-07.md)
PX-47 §(2), cross-linked from
[`reviews/2026-07-efficiency/prescriptions.md`](reviews/2026-07-efficiency/prescriptions.md)
PX-47 row. **Document-only — no re-pin executed.**

| # | Decision | Resolution |
|---|---|---|
| PX-47b | Model-pin convention: dated-vs-undated split across the 9 subagents | **Intentional and provider-imposed, not drift.** The 3 Haiku subagents (`agents/eval-judge.md`, `agents/wiki-grounding-auditor.md`, `agents/wiki-scribe.md`) pin the **dated** snapshot `claude-haiku-4-5-20251001` (matches `analyzer.py:HAIKU_MODEL`); the 6 Sonnet subagents (`agents/compliance-witness.md`, `agents/git-flow.md`, `agents/headhunter.md`, `agents/prompt-archaeologist.md`, `agents/tune-drafter.md`, `agents/ux-onboarding-designer.md`) pin the **undated alias** `claude-sonnet-5` (matches `analyzer.py:SONNET_MODEL`) because Sonnet 5 has **no dated snapshot ID** on the Anthropic API as of this writing — "apply one convention" (a dated pin everywhere) is not currently achievable. **Revisit trigger:** if/when Anthropic ships a dated Sonnet-5 snapshot, reconsider either dated-pinning the 6 Sonnet agents to it, or flipping the 3 Haiku agents to the undated `claude-haiku-4-5` alias for uniformity — an owner call each time, not a mechanical re-pin. |

### 2026-07-10 — mypy `--strict` exempt set narrowed (supersedes KIT-7)

Full record + rationale: [`kit-adoption-design.md`](kit-adoption-design.md) §6 (the
2026-07-10 amendment record — `chore/mypy-strict-tooling`, owner-directed v1.0.9
tooling-slice pull-in).

| # | Decision | Resolution |
|---|---|---|
| KIT-7a | mypy `--strict` exempt set — **supersedes KIT-7** (2026-06-23, below) | Exempt set narrows from `tests/`/`evals/`/`scripts/`/`db/migrations/versions` to **`tests/` only**; the `scripts/`/`evals/`/`db/migrations/versions/` trees are now strict-rostered |

### 2026-06-23 — Agent-coding-practices kit adoption (8 decisions)

Full record + rationale: [`kit-adoption-design.md`](kit-adoption-design.md) §3.

| # | Decision | Resolution |
|---|---|---|
| KIT-1 | Flask validation + OpenAPI extension | **spectree** (least invasive to the 8.3 factory + PX-29 gate; Pydantic-native) |
| KIT-2a | HTTP API docs (Layer B) | **Generate from OpenAPI** → Fumadocs (later) |
| KIT-2b | Python code reference (Layer C) | **Skip the generated site**; keep docstrings + coverage gate |
| KIT-3 | Gate vehicle | **Fold kit gates into `feat/portable-enforcement-core`**; local pre-commit half now, CI-blocking at 8.7 |
| KIT-4 | ADRs | **Thin `decisions.md` index** (this file) over existing records |
| KIT-5 | `context-structure-review` packaging | **Committed plugin skill in a root `skills/` dir** (mirrors `commands/`/`agents/`) |
| KIT-6 | Gate hardness | **Ratchet-then-block** (unambiguous gates block day one; strict families ratchet warn→block per-module; noisy heuristics warn-only forever) |
| KIT-7 | mypy `--strict` end-state | **Strict everywhere except a named exempt set** (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`) |
| KIT-8 | `uv` migration | **Out of scope** (stay pip/setuptools; translate commands) |

Framing: **implement Sartor's deltas + flag what's promotable to `amodal-open`**
(Sartor is the donor, not a blank canary) — [`kit-adoption-design.md`](kit-adoption-design.md) §1, §7.

### 2026-06-15 — Enforcement portability (security/quality hooks)

Decision: **SPLIT** — portable rules (`require-feature-branch`, `block-merge-to-main`,
`block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context`) migrate to a
tool-agnostic **shared enforcement core** invoked by both committed git-hooks and the Claude
plugin, with CI as the server-side backstop; plan-mode lifecycle + `wiki-freshness` stay
Claude-only. Implementation deferred to **8.7** (`feat/portable-enforcement-core`), gated on the
GitHub remote/CI landing.
Full record: [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) (8.7 + the `[x]` decision entry) +
[`governance-extraction-design.md`](governance-extraction-design.md) §5. *(Backfill entry, added
2026-06-23 to seed this log — demonstrates the cite-don't-restate pattern over an existing record.)*

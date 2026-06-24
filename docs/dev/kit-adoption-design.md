# Agent-coding-practices kit adoption — design + arc (captured 2026-06-23)

> **Purpose:** the settled evaluation + sequenced plan for adopting the lichen
> `agent-coding-practices-kit` (context / documentation / strict-typing practices +
> the `context-structure-review` skill) into callback. Produced as an
> **evaluation** (no code changed); this doc is the durable record the
> implementation branches execute against, so they re-decide nothing.
> **Audience:** the owner (Robert) reviewing the plan, and any agent implementing a
> phase of it. Precedent for a captured design-doc deliverable:
> [`governance-extraction-design.md`](governance-extraction-design.md).
> **Authoritative for:** the eight adoption decisions (§3), the phase sequencing
> (§4), the temporal map onto the existing roadmap (§5), and the ratchet exit
> criterion (§6). On conflict with an older plan, this doc governs for the
> kit-adoption scope only. Decision index: [`decisions.md`](decisions.md).
> **Source of record (read-only, outside this repo):** the kit lives at
> `C:\Dev\lichen\projects\agent-coding-practices-kit\` — `markdown-for-llm-apps.md`
> (context), `doc-discipline-for-coding-agents.md` (docs),
> `strict-typing-and-style.md` (typing), and `context-structure-review/`. The
> handoff that seeded this evaluation is a Callback-trimmed synthesis of those.

---

## 0. What this is, in one paragraph

The lichen kit is three practices — **context** (what the agent loads) → **documentation**
(what it records) → **types** (what it can't get wrong) — sharing one premise (structure,
docs, and types are *inputs to agent reliability*, not hygiene) and one method (**mechanism,
not instruction**: judgment lives in AGENTS.md/skills, the mechanizable subset lives in
blocking gates). The handoff framed Callback as a greenfield "canary" whose AGENTS.md needs
*seeding*. It isn't: Callback is a mature v1.0.7 repo that already practices ~60% of the kit,
often better than the kit describes (governance charter, hooks-as-mechanism, the AGENTS.md
`@import` design, the self-documenting wiki). So adoption is **reconcile + close specific
deltas + flag what's promotable to `amodal-open`** — not author-from-zero. Callback is the
**donor**, not the blank canary.

---

## 1. The frame (canary → donor)

The kit's stated end-goal (its §5) is an adoption arc: settle the conventions on Callback (the
"canary"), then promote them to a shared `amodal-open` location later repos inherit. The
correction this evaluation makes: for the governance philosophy, the hook model, the
`@import` instruction-file design, and the wiki doc-drift loop, **Callback already holds the
best-in-class version** — so the shared layer is *extracted from* Callback, and only the
genuinely-missing pieces (strict typing, request-boundary parsing, doc generation) are
*imported from* the kit. Framing chosen (Decision-framing, 2026-06-23): **implement Callback's
deltas now + flag promotable practices as we go** (don't build the shared layer yet). The
promotable shortlist is §7.

---

## 2. Current-state survey (what's done vs the real gaps)

Verified against `main` at capture (2026-06-23). Legend: ✅ done/exceeded · 🟡 partial ·
❌ gap.

| Kit ask | Callback today | |
|---|---|---|
| Exclude aggressively (ignore surface) | `.gitignore` covers `.venv`/caches/build/secrets/PII; pip-based, no lockfile to exclude | ✅ |
| One canonical instruction file | `AGENTS.md` canonical (168 lines) + `CLAUDE.md` (190) `@import`s it | ✅ exceeds |
| Copy-pasteable exact commands | AGENTS.md carries the ruff/mypy/pytest + eval loop (pip, not `uv`) | ✅ |
| Progressive disclosure / ≤500-line files | Instruction files small; wiki + recall embody it | ✅ |
| Permission boundaries | Six enforcing PreToolUse hooks (mechanism) | ✅ exceeds |
| Treat instructions as code / audit cadence | governance + `wiki-lint` + `compliance-witness` | ✅ exceeds |
| Doc-drift detection | wiki-freshness hook + `/wiki-self-update` | ✅ exceeds |
| "Why not what" comments | Cultural norm (D5 cite-don't-restate); not *enforced* | 🟡 |
| No commented-out code (ruff `ERA`) | `ERA` not in ruff `select` — evaluated 2026-06-23: 8/8 hits false-positive → stays warn-only per Decision 6 (§4 progress note) | 🟡 |
| Docstring coverage (ruff `D` / `interrogate`) | `D` not selected; no `interrogate` | ❌ |
| Generated reference docs | none | ❌ (see Decision 2) |
| OpenAPI from Flask | none | ❌ (see Decisions 1, 2) |
| DoD checklist + PR template | `RELEASE_CHECKLIST` + AGENTS.md close-out + a rich PR template already exist | 🟡 reconcile |
| mypy `--strict` | mypy runs but is **deliberately permissive** (`ignore_missing_imports`, `follow_imports=silent`, no `disallow_untyped_defs`/`warn_unreachable`) | ❌ **big** |
| ruff `ANN`/`D`/`ERA`/`SIM`/`RUF` | only `E,W,F,I,B,UP,S` selected (`S`/bandit already on — kit omits it) | ❌ |
| Pydantic + SQLAlchemy mypy plugins | `pydantic.mypy` enabled 2026-06-23 (mypy green); SQLAlchemy plugin dropped — `db/models.py` uses 2.0 native `Mapped[]` typing, plugin deprecated/unneeded | ✅ |
| Parse at request boundary | **all ~30 body routes do raw `request.json`** across 7 blueprints | ❌ **big** |
| `pydantic-settings` config | `config.py` is a clean typed `frozen dataclass` (path injection, not env parsing) | 🟡 skip (Decision-revision) |
| `ruff format` | lints only; `ruff format --check` not wired | ❌ small |
| `context-structure-review` skill | not installed | 🟡 (Decision 5) |
| Worktree isolation / explicit staging / re-read | branch discipline + concurrent-agent-worktree practice; no `decisions/` dir | ✅ mostly |

**Structural mismatches in the handoff (revisions of record):** (1) `uv` assumption is wrong —
Callback is pip/setuptools; translate commands (Decision 8 = out of scope). (2) greenfield
framing inverted (§1). (3) don't flatten `CLAUDE.md` to "Follow ./AGENTS.md" — the `@import`
design is better. (4) PR-template/DoD assume a PR-review workflow; Callback merges locally —
fold DoD into existing checklists. (5) doc-drift SaaS (Dosu/DeepDocs) redundant with the wiki
loop. (6) `pydantic-settings` is low-value churn (`config.py` already typed). (7) markdown
oversized-file gate is a future-guard, not a current fix.

---

## 3. The eight decisions (settled 2026-06-23, owner-gated)

| # | Decision | Resolution | Why |
|---|---|---|---|
| 1 | Flask validation + OpenAPI extension | **spectree** | Least invasive to the 8.3 factory + PX-29 containment gate; Pydantic-native; rendered docs artifact is identical to apiflask's once fed to Fumadocs, and the lighter touch signals better judgment than importing a public-API framework onto an internal seam |
| 2a | HTTP API docs (Layer B) | **Generate from OpenAPI** → Fumadocs (later) | One source of truth; can't drift; spectree emits the spec for free |
| 2b | Python code reference (Layer C) | **Skip the generated site** | Callback is an app, not a library; the wiki + recall + assistant already navigate internals better than a signature dump. Keep docstrings + the coverage gate |
| 3 | Gate vehicle | **Fold kit gates into `feat/portable-enforcement-core`**; stand up the local pre-commit half **now** (no remote needed), CI-blocking flips on at 8.7 | The tool-agnostic-enforcement decision was already DECIDED (SPLIT, 2026-06-15) and scheduled at 8.7 — the kit's Gate 1 *is* that branch; don't build a parallel pre-commit track |
| 4 | ADRs | **Thin `decisions.md` index** over existing records | Closes the "no single chronological decision log" gap with zero duplication or competing home (cite-don't-restate / D5) |
| 5 | `context-structure-review` packaging | **Committed plugin skill in a root `skills/` dir** | `.claude/skills/` is gitignored → unshipped/unpromotable. Root `skills/` mirrors the `commands/`/`agents/` convention, stays close to the kit format for easy upstream sync, and is committed + promotable |
| 6 | Gate hardness | **Ratchet-then-block** | Hard-block unambiguous gates day one (gitleaks, `ruff format`, mypy on covered modules); strict families (`D`/`ANN`/`--strict`) ratchet warn→block per-module, locking each gain; known-noisy heuristics (oversized-file, any commented-out grep) stay **warn-only forever** (the kit's false-positive→route-around caveat) |
| 7 | mypy `--strict` end-state | **Strict everywhere except a named exempt set** (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`) | Professional default; named + justified exemptions satisfy "audit the escape hatches"; gives the ratchet a finite finish line |
| 8 | `uv` migration | **Out of scope** | Stay pip/setuptools; translate the kit's commands |

Full rationale for Decisions 1, 2, 3, and 5 (the ones that turned on Callback-specific facts —
Fumadocs consuming OpenAPI, the latent-CI/no-remote state, the component packaging) is in the
conversation of record; the one-line "why" above is the durable summary.

---

## 4. The sequenced arc

Each item tagged **[J]** judgment (→ AGENTS.md/skill) or **[M]** mechanism (→ gate). Every
branch keeps the (latent) gate green at every commit.

**Phase 0 — Documentation-first (this doc + decisions.md + roadmap entries).** Done at capture.
Anchors everything downstream; nothing else starts until the record exists.

**Phase 1 — Cheap mechanizable wins** (~1–2 sessions): `ruff format` normalize + `--check`
wired **[M]**; ruff `ERA` **[M]**; ruff `SIM`/`RUF` (land per-family if noisy) **[M]**; Pydantic
+ SQLAlchemy mypy plugins **[M]**. These ride the local pre-commit half of
`feat/portable-enforcement-core`; unambiguous ones hard-block locally day one (Decision 6).

> **Phase 1 progress — first branch `chore/kit-phase1-pydantic-mypy` (2026-06-23, owner-selected
> "lint+typing wins, defer format" subset).** Landed: **`pydantic.mypy` enabled** (`[tool.mypy]
> plugins`) — mypy stays green ("no issues found in 227 source files"; the plugin ships inside the
> existing `pydantic` dep, so **no new dependency**). **Two Phase-1 items revised against the real
> code:** (1) **ERA dropped, not enabled** — all 8 `ERA001` hits are **false positives** on legitimate
> documentation prose (JSON-shape examples, TypedDict shape docs, `# Section (name)` dividers, an
> `(i)-circle` reference), the exact case **Decision 6** marks *warn-only forever*; enabling it blocking
> would clutter docs with `# noqa: ERA001` and block every future prose comment containing a
> paren/pipe/dict-example, and there is no advisory lane until the 8.7 pre-commit core — so ERA stays
> unenabled (revisit only if that core gains a warn-only lane). (2) **SQLAlchemy mypy plugin dropped** —
> `db/models.py` uses native SQLAlchemy 2.0 typing (`DeclarativeBase` + `Mapped[...]` + `mapped_column`),
> for which `sqlalchemy.ext.mypy.plugin` is deprecated/unneeded; only `pydantic.mypy` applies. **Still
> owed in Phase 1 (own branch):** `SIM`/`RUF` per-family triage (228 hits, of which 117 are
> RUF001–003 ambiguous-unicode false-positives to ignore). (`ruff format` landed on its own branch —
> see the next note.)

> **Phase 1 progress — second branch `chore/kit-phase1-ruff-format` (2026-06-23, owner-confirmed
> style).** Landed: **`ruff format` applied tree-wide** — 161 of 217 files reformatted (56 already
> clean), pure formatter output (hand-packed collection literals exploded one item per line; no hand
> edits). Proven **prompt-inert**: every `analyzer.py` prompt constant + the `PROMPT_VERSION` /
> `AVATAR_PROMPT_VERSION` *value* + the `_BASE_SYSTEM_PROMPTS` registry are byte-identical pre/post
> (sha256 dump-diff, 31 entries, zero differences) — ruff format never edits inside string literals,
> so **no `PROMPT_VERSION` bump and no paid eval run**. The gate is **wired + hard-blocks day one**
> (Decision 6 / KIT-6): `pyproject.toml` `[tool.ruff.format]` declares the style
> (`quote-style`/`indent-style`; matches defaults so output is unchanged), and
> `.claude-plugin/hooks/ruff-changed.sh` now runs `ruff format --check` on staged Python alongside
> `ruff check`; `.git-blame-ignore-revs` lists the reformat commit so blame skips it. Gate green:
> ruff check . ✓ · mypy (227) ✓ · pytest 1391 passed. **Phase 1 now has one item left:** the
> `SIM`/`RUF` per-family triage named above.

**Phase 2 — Strictness ratchet** (~3–5 sessions; this is WS-2-full made concrete): ruff `ANN`
**[M+J]**; ruff `D` + pinned `google` pydocstyle convention **[M+J]**; `interrogate` coverage
gate at measured-current, ratcheted up **[M]**; mypy `--strict` + `warn_unreachable`, per-module
overrides keep green, tightened module-by-module toward the Decision-7 end-state **[M+J]**. The
big item; `analyzer.py` (3,648 lines) and `applications.py` (1,847) are each likely their own
tightening branch. **Tracked by a per-module coverage surface + the §6 exit criterion.**

**Phase 3 — Request-boundary typing + OpenAPI** (~4–6 sessions): pick is settled (spectree,
Decision 1); convert ~30 endpoints to parse `request.json` into Pydantic models, blueprint by
blueprint, each reconciled with `_safe_username`/`_within` + the PX-29 containment gate **[M+J]**;
emit the OpenAPI spec **[M]**. **Lighter than the handoff's plan** — Sphinx/mkdocstrings are out
(Decision 2b); the Fumadocs *rendering* of the spec is a separate later project.

**Phase 4 — DoD + governance reconcile** (~1 session): extend the existing PR template +
AGENTS.md "Key patterns" with only the net-new DoD lines (docstrings/docs-build, no
commented-out code, comments-updated-in-same-change, decision-recorded) **[J]**; seed/maintain
`decisions.md` **[J]**.

**Phase 5 — Skill + promotable flagging** (~1 session): install `context-structure-review` in a
root `skills/` dir (Decision 5) **[M+J]**; record the §7 promotable shortlist **[J]**.

Estimate: a v1.0.8-scale arc (~10–15 sessions). Real cost concentrates in Phase 2d (mypy
`--strict`) and Phase 3 (spectree boundary). Everything else is hours or reconcile-don't-build.

---

## 5. Temporal map (how the arc threads the existing roadmap)

The kit-adoption arc is **not free-floating** — it overlays planned work:

- **Now / current window:** Phase 0 (done) → Phase 1 quick wins → Phase 2 ratchet begins →
  Phase 3 boundary refactor. The local pre-commit gates run today (no remote needed).
- **At 8.7 (`feat/portable-enforcement-core` + `release/public-prep`):** the kit's gates fold
  into the shared enforcement core; **CI-blocking activates when the GitHub remote lands**
  (today there is no remote — `ci.yml` is committed but dormant); hooks re-home out of
  `.claude-plugin/` and the `commands/ agents/ skills/ hooks/` families reach the clean
  four-parallel end-state. See `RELEASE_CHECKLIST.md` 8.7 + Carry-forward ledger.
- **WS-2-full (recurring):** the Phase 2 strict ratchet *is* WS-2-full; the full strict
  end-state lands across the v1.0.8 tail → 1.1.x.
- **Post-8.7 (separate project):** Fumadocs renders the OpenAPI spec + the wiki markdown into
  the public docs site (`callback-docs.taketempo.com`).

---

## 6. The ratchet exit criterion (coherence teeth)

The cautionary example is in-repo: the hooks split-home (scripts in `.claude-plugin/hooks/`,
wiring in `settings.json`) has been a decided-but-unexecuted half-migration since 7.1 — *fine
because it's tracked*. A strict ratchet with no tracking + no finish line is how you get a
*permanent* half-strict codebase. So the ratchet is bounded, not open-ended:

- **Tracking surface:** a per-module coverage record (which modules are at full strict / `D` /
  `ANN`, which still carry an override).
- **Exit criterion (done):** no module carries a strictness override **except** the named exempt
  set (`tests/`, `evals/`, `scripts/`, `db/migrations/versions`; Decision 7). When the only
  remaining overrides are those four, the ratchet is complete and the gate blocks everywhere
  non-exempt.

---

## 7. Promotable to `amodal-open` (the "flag" half of the framing)

Extraction candidates — practices Callback already does best, to seed the shared layer later
(do **not** build the shared layer in this arc):

- The **governance philosophy** (charter C-0…C-6 / D-1…D-6 / W-1 + amendment ceremony).
- The **hooks-as-mechanism** model (post-8.7 shared enforcement core = the cleanest form).
- The **AGENTS.md `@import` + layered-overrides** instruction-file design.
- The **wiki doc-drift loop** (`/wiki-self-update` + `wiki-lint` + author≠auditor).
- The **eval-gate discipline** (`PROMPT_VERSION` attribution, the smoke-gate exit-2 contract).
- The **`.pre-commit-config.yaml`** the kit adds (the single most directly-inheritable artifact).

---

## 8. Open / owner-gated items

- Scheduling: the arc consolidates with `feat/portable-enforcement-core` (8.7) + WS-2-full; the
  pre-public phases (1–3) can begin in the current window at owner direction.
- spectree OpenAPI 3.1 + Pydantic v2 output to re-verify when Phase 3 starts (perishable).
- Fumadocs spec enrichment (per-route summaries/descriptions/examples) is budgeted into the
  later Fumadocs documentation pass, not this arc.
- Stale-doc fix owed (not this branch's scope): `CLAUDE.md:83` says the tool-agnostic-enforcement
  decision is "pending the v1.0.7 governance pass" — it was DECIDED 2026-06-15; what's pending is
  *implementation* at 8.7. Fix next time `CLAUDE.md` is touched.

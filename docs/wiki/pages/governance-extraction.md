# Governance extraction (the mixed-doc crux)

> **Audience:** `dev`
> **Concept:** the extraction of a single canonical **Governance** home — the
> design that resolves the "mixed-doc" problem (prescriptive rules tangled into
> descriptive docs). Design is settled; the build LANDED in Sprint 7.2 (v1.0.7) at
> `docs/governance/`. **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "mixed-doc crux RESOLVED" · [`../../dev/RELEASE_ARC.md`](../../dev/RELEASE_ARC.md) §Phase 4.7
> (Governance extraction + the ⚠ HARD CONSTRAINT) · the three files now canonical:
> [`../../governance/charter.md`](../../governance/charter.md),
> [`../../governance/enforcement.md`](../../governance/enforcement.md),
> [`../../governance/metrics.md`](../../governance/metrics.md) · [`../SCHEMA.md`](../SCHEMA.md) (page structure).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md). This page describes the *design* and
> **references** the rule-bearing docs ([`AGENTS.md`](../../../AGENTS.md),
> [`vision.md`](../../../vision.md), …); per fork D5 it does **not** restate the rules
> themselves — those stay canonical in their homes. Conclusions tagged `[synthesis]`.

---

## The crux

A handful of docs each blend **prescriptive rules** with **descriptive content** in one
file — the agent contract, the contributing guide, the security doc, the product-shape
doc, the release arc. The seven-functions language ([[system-model-derivation]])
dissolved the puzzle: the docs are mostly **Memory** (living-source / synthesized-wiki /
frozen-archive strata), the constitutional layer is **Governance**, and the crux is
**separating Governance from the Memory it is embedded in** `[synthesis]`.

## The decision: extract, don't register-in-place

Prescriptive / Governance content is **lifted into one canonical home and stated once**;
each mixed doc keeps its descriptive (Memory) content + a **pointer** to the canonical
rule. (This overrode an earlier "register-in-place" lean.) DRY, applied to governance:
each rule lives in exactly one place; everything else references it.

**What extracts into Governance** (referenced, not restated here):
- the [`vision.md`](../../../vision.md) core + the 10 Principles (frozen);
- the hard rules scattered across [`AGENTS.md`](../../../AGENTS.md) (the security gate,
  the `PROMPT_VERSION`-bump discipline, the deterministic/LLM boundary, the "what NOT to
  do" list, branch conventions), [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) (the
  ruff + mypy + pytest bar, commit/branch conventions), [`SECURITY.md`](../../../SECURITY.md)
  (API-key rules, the `_safe_username`/`_within` mandate),
  [`../../PRODUCT_SHAPE.md`](../../PRODUCT_SHAPE.md) (the prescriptive v1→v2 ladder +
  Corpus-Item rules), and [`../../dev/RELEASE_ARC.md`](../../dev/RELEASE_ARC.md) (the
  "hard constraints, all phases" + the "do not edit without sign-off" gate).

## ⚠ The critical constraint

[`AGENTS.md`](../../../AGENTS.md) / [`CLAUDE.md`](../../../CLAUDE.md) are
**harness-auto-loaded** — they are the agent's operating instructions at session start.
Extraction **MUST preserve agent rule-access** via `@import` (CLAUDE.md already does
`@AGENTS.md`) or an explicit canonical pointer — **or every future agent loses its
guardrails.** `AGENTS.md` stays the entry point; it *imports/links* Governance, it does
not lose the rules. This is the load-bearing safety condition on the whole extraction.

## Why it pays off

- **Vision-alignment auditing reads ONE canonical constitution** — `/wiki-lint` /
  `/wiki-audit` can check whether the descriptive layer (code, synthesized wiki) has
  drifted from the prescriptive layer: *does what we built still match what we said we'd
  build?*
- **The constitutional layer gets a real guard.** Per the `raw/` reasoning, the
  qualifying trait is *prescriptive/constitutional, not low-churn* — "vision is the most
  raw thing in the repo" because the code is derived from it, not the reverse. Friction
  must be **mechanized** (a Regulation-style hook on the Governance home), not just a
  folder.
- **"Consistency tracks enforcement"** ([[consistency-tracks-enforcement]]) then extends
  to the vision itself `[synthesis]`.

## Status + resolved sub-decisions

**Design complete; build LANDED in Sprint 7.2 (v1.0.7).** The three implementation sub-decisions
were resolved on 2026-06-15 (per RELEASE_ARC §Phase 4.7 governance extraction section):

1. **Governance home name / location — RESOLVED → `docs/governance/`** 
   A directory (not `raw/`, not root `GOVERNANCE.md`) containing three files:
   [`charter.md`](../../governance/charter.md) (the binding rules),
   [`enforcement.md`](../../governance/enforcement.md) (gate vs witness), and
   [`metrics.md`](../../governance/metrics.md) (success criteria + review rubric).
   See RELEASE_ARC §Phase 4.7 (the governance-home-location sub-decision) `[synthesis]`.

2. **Per-doc extraction boundaries — RESOLVED**
   Each source doc retains descriptive content + adds a pointer to the canonical rule home.
   The extraction boundaries are codified in `charter.md`'s citation map — not a table, but
   the inline `[src: …]` tag carried by every clause (`charter.md`'s "Evidence base" preamble:
   "Every clause is tagged `[src: …]` so the extraction is a verifiable citation map") —
   six source docs (vision.md, AGENTS.md, SECURITY.md, CONTRIBUTING.md, PRODUCT_SHAPE.md, RELEASE_ARC.md)
   now reference rather than restate the rules `[synthesis]`.

3. **`AGENTS.md` shape — RESOLVED → critical-rules-inline-with-pointer**
   NOT a pure shell that imports (which would break non-Claude agents reading it raw).
   Confirmed in AGENTS.md's "Canonical governance" note: it keeps the rules inline + adds
   an explicit canonical pointer to `docs/governance/charter.md` (**F-gov-05**; RELEASE_ARC
   §Phase 4.7, the AGENTS.md-shape sub-decision) `[synthesis]`.

## Working model (W-1/W-2) + amendment ceremony — landed 2026-07-23

The charter grew past its original C-0…C-6 clause set: `charter.md` now carries
**C-7…C-12** (evidence-before-mechanism, durable-before-deep, corrupted-input-is-a-
blocked-gate, enumerate-consumers-before-changing-a-contract, enforcement-before-
discipline, declare-the-gap) and a full
**"Working model (W-1/W-2)"** section — [`charter.md`
§Working model](../../governance/charter.md#working-model-w-1w-2) — plus a formal
**Amendment ceremony** section governing how the charter itself changes. Per this
page's own grounding rule, the clauses are not restated here; the durable home is
`charter.md`. `[synthesis]`

- **W-1** states the parallel-session isolation construction (worktree-per-session,
  session-scoped plan-approval state, branch ownership, the cumulative carry-forward
  ledger) plus an explicit **posture paragraph**: the construction is available, but
  the operative default is still **serial** — one branch, one session — until Claude
  Code's reliability is re-established ([[engineering-workstreams]] tracks that
  posture call).
- **W-2** names governance itself as the constitution-building extraction vehicle
  this page describes — closing the loop between this page's design account and the
  charter's own self-description.
- The **amendment ceremony** section formalizes, after the fact, the citation
  discipline this page's own history already practiced (a dated `[src: adopted …]`
  tag per amendment) — see `enforcement.md`'s "Parallel-session isolation (W-1)" row,
  which tracked the W-1 citation gap (**F-gov-03**) as open until this landed.

## The extraction checklist nobody had: enforcement reach (2026-08-05)

This page's whole premise is that governance can be lifted out of descriptive docs into
a portable constitutional home. `enforcement.md` now carries the section that says what
*travels* when you do it — [`enforcement.md` §"Enforcement reach — WHICH agents each
gate actually binds"](../../governance/enforcement.md) — and it is explicitly framed as
**the extraction checklist**, "read this before extracting governance."

The load-bearing fact: **a clause enforced only by a Claude Code hook does not travel**
— not to Codex, Cursor or Aider today, and not into a governance package extracted
into another project tomorrow. Guards route through three adapters with very different
coverage (per [`enforcement.md` §"Enforcement reach"](../../governance/enforcement.md) — a tool-agnostic opt-in git-hook path; a CI/`gate.py` path that binds everyone;
and a Claude-Code-only PreToolUse path). C-7's `require_evidence_before_fix`, C-10's
`require_consumer_enumeration`, `interrogative_witness`, the C-8/C-12 context hooks, and `verify_binary_on_path`
are all on the third. `verify_binary_on_path` has **no planned git-native
path** — it parses a Bash command string, a shape a `pre-commit` hook never sees, so
there is no equivalent input to route it from. `interrogative_witness`, by contrast, is Claude Code only **by nature, not by gap** `[synthesis]` — it enforces a pause based on whether the user prompt is a question or directive, a property of Claude *sessions* that git hooks do not have, so extraction closes nothing here.

The split was invisible from any single file, which is exactly why it went unrecorded
until 2026-08-05. It is now declared as a **stated limit rather than papered over**
(C-0), tracked by work item 50, and held in place by
`tests/test_enforcement_coverage.py`, which derives the routing from `git_hook.py` at
runtime — so a future branch that closes the gap, widens it, or adds a new Claude-only
guard has to say so in the diff `[synthesis]`.

## Related

- [[llm-wiki-design]] — the wiki design; this extraction is where the earlier `raw/`
  question got resolved — `raw/` was rejected in favor of `docs/governance/` (§Status
  above), so it stays unbuilt.
- [[engineering-workstreams]] — this is WS-4's follow-on; also tracks the W-1 serial-
  vs-parallel posture call.
- [[system-model-derivation]] — the seven-functions language that dissolved the crux.
- [[consistency-tracks-enforcement]] — the finding this extends to the vision.
- [[excellence-walk]] — the walk this design belongs to.

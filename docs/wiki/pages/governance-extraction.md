# Governance extraction (the mixed-doc crux)

> **Audience:** `dev`
> **Concept:** the planned extraction of a single canonical **Governance** home — the
> design that resolves the "mixed-doc" problem (prescriptive rules tangled into
> descriptive docs). Design is settled; the build is a separate, later, gated branch.
> **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "mixed-doc crux RESOLVED" + the `raw/` constitutional sections ·
> [`../../dev/RELEASE_ARC.md`](../../dev/RELEASE_ARC.md) §Phase 4.5 (Governance extraction
> + the ⚠ HARD CONSTRAINT) · [`../SCHEMA.md`](../SCHEMA.md) ("The `raw/` constitutional
> layer").
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

## Status + open sub-decisions

**Design complete; build deferred** to its own carefully-gated branch *after the wiki
proves out* — explicitly **not this ingest branch**, which only introduces the synthesis
layer, not `raw/` or the Governance home. Three implementation sub-decisions remain open
(per RELEASE_ARC §Phase 4.5):

1. **Governance home name / location** — `raw/` vs a self-describing `docs/governance/`
   vs a root `GOVERNANCE.md`. *Lean: name it for its function (`docs/governance/`).*
2. **Per-doc extraction boundaries** — the exact spans to lift from each mixed doc.
3. **`AGENTS.md` shape** — critical-rules-inline-with-pointer vs a pure shell that
   imports.

## Related

- [[llm-wiki-design]] — the wiki design; `raw/` is introduced by this extraction.
- [[engineering-workstreams]] — this is WS-4's follow-on.
- [[system-model-derivation]] — the seven-functions language that dissolved the crux.
- [[consistency-tracks-enforcement]] — the finding this extends to the vision.
- [[excellence-walk]] — the walk this design belongs to.

---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/dev/EXTRACTION.md (v1.0.7+)
---

# Extraction playbook — when an incubated system graduates to a product

> **Purpose:** the good-practice contract for sartor.'s seedbed posture
> (charter P-6/W-4): how to incubate a system in-repo, and the *observable*
> event that says "extract now" — never a feeling. Severity anchors to the
> SIGNED charter; written under C-0 (mechanisms and effort, no absolutes about
> LLM behavior, no marketing register).
> **Audience:** the owner and any agent deciding whether to break a system out.
> **Authoritative for:** the per-incubant extraction gates, the single missing
> maturity metric (F-gov-08), and the three good practices.

W-4 names the trigger set — *a system is mature, a second project needs it, or
attention economics warrant breakout* — but leaves the **maturity metric "TBD —
review to propose"** (F-gov-08). Today exactly one of five incubants carries an
observable readiness signal (`recall/`); the other four have only
trigger-language. This playbook closes that gap. Re-introduction after
extraction is **friction-dependent** (W-4, Q24): the post-extraction
relationship is chosen per system, not assumed.

---

## The single maturity metric (F-gov-08 — proposed)

The `recall/` extraction-readiness condition is the template
(`memory-architecture.md:216-219`): *"lifting into a standalone package should
be packaging-only — IF the boundary [no import of `app.py`/`analyzer.py`/DB
models] stays clean."* Generalize it to one **checkable** metric every incubant
carries — **extraction-readiness = boundary-clean ∧ contract-frozen ∧
second-consumer**:

1. **Boundary-clean** — the system imports only its declared inward
   dependencies; a boundary-lint (the kind F-arch-01/F-qe-rel-04 prescribe for
   C-6) passes. *Machine-checkable* — the P-3/D-4-preferred gate, not a promise.
2. **Contract-frozen** — its public surface (entry point + types) has not
   changed for **N release cycles** (propose N=2), read from the CHANGELOG/git
   history of the seam files — observable, not felt.
3. **Second-consumer** — a real second caller (another project, or a second
   in-repo surface) exercises the seam. W-4's "second project needs it," as a
   yes/no.

A system is **harvest-ready** when all three hold; until then it stays
modularized in place. Extraction becomes a status the gates report, not a
judgment call — the discipline F-gov-04 affirms for the hook layer
(machine-categorical where a test enforces; effort-language everywhere else).

---

## Per-incubant assessment (at the pin)

### (a) recall/ — memory substrate

- **Coupling:** lowest. A *design invariant* with a written dependency rule:
  `recall/` may import stdlib + light libs, **never** `app.py`, `analyzer.py`, or
  the DB models (`memory-architecture.md:204-219`). The avatar (an Operation
  surface) depends on it; it depends only inward on Substrate.
- **Readiness signal:** the only one that exists — the extraction-readiness
  condition above (F-gov-08). But **F-arch-09** (WEAKENED → revised): at the pin
  `recall/` is **design-only, not committed**; the landed in-place evidence is
  `run_suite()`. Readiness is *specified*, not yet *measurable against code*.
- **Extraction gate:** boundary-lint green on the committed package **+** a
  second consumer imports `recall.assemble()` without touching sartor
  internals — cannot fire until the package + its lint exist.
- **Harvest moment:** post-v1.1.0 — Stage 0/1 ship inside v1.0.7; physical
  extraction is "packaging only" once boundary-clean holds across N cycles.
- **Relationship:** **dependency** (W-4 intent: recall → product). sartor.
  becomes a consumer; the seam is already a contract built for this.

### (b) governance rulebook + compliance agent

- **Coupling:** the rulebook is *embedded* in mixed docs (AGENTS.md,
  CONTRIBUTING, SECURITY, PRODUCT_SHAPE, RELEASE_ARC) — the "mixed-doc crux." The
  compliance agent **does not exist** at the pin; its precedent is the read-only
  subagent pattern (F-gov-09: `prompt-archaeologist` carries `tools: [Read, Grep,
  Glob]`, "Does NOT apply the diff").
- **Readiness signal:** trigger-language only (F-gov-08). The design home
  (`docs/governance/`) is the v1.0.7 graduation target; `@import` is named the
  load-bearing safety condition (F-gov-05).
- **Extraction gate:** **second project needs it** — W-2 states governance
  "spans the owner's projects." The gate: a second repo adopts the extracted
  constitution **and** the witness-class compliance agent runs against it (the
  amendment-ceremony precedent, F-gov-06: `wiki-freshness-reminder`, always exit
  0, sentinel-honest). Prerequisite: the "machine-enforced" claim must be honest
  first — F-gov-01 shows `block-merge-to-main` misses the dominant merge
  direction, leaving the layer convention-only for the common path until fixed.
- **Harvest moment:** **after** the in-repo extraction lands (v1.0.7 relocates
  rules to one home with `@import` preserved) and the agent-station lane (W-3)
  gives it a second home. Do not extract before the in-repo "extract-don't-
  restate" step (F-gov-05) — that step *is* the modularize-in-place move.
- **Relationship:** **dependency**, required not optional. AGENTS.md/CLAUDE.md
  stay harness-auto-loaded, so they must `@import` or canonically point at the
  extracted home, "or every future agent loses its guardrails"
  (governance-extraction.md). A frozen copy would break that live link.

### (c) LLM-wiki + self-documenting loop

- **Coupling to host:** the wiki is committed (`docs/wiki/`, git-as-engine; the
  cite/backlink/synthesis convention genuinely practiced, F-docs-07); the loop is
  the `/wiki-*` ops + the freshness witness. W-4 places this **inside the memory
  product** — its host is really (a), not sartor. directly.
- **Readiness signal:** trigger-language only (F-gov-08). The sentinel honesty
  (F-docs-08: `.last_ingest_sha` left at sentinel, no false code-pass claim) is
  a working maturity *seam*, but no readiness *condition* is written.
- **Observable extraction gate:** graduates **with `recall/`** (the wiki is S1
  in the stack), plus: the code cold-ingest (WS-4b) has fired ≥1 time and
  rot-detection has run (F-docs-10: never fired at the pin).
- **Harvest moment:** folded into the memory-product harvest, post-v1.1.0.
- **Post-extraction relationship:** **dependency on the memory product** (it
  travels *inside* recall). sartor. consumes its own wiki through the same
  substrate it would consume any project's.

### (d) doc-grounded assistant (operator stack)

- **Coupling to host:** the assistant is the **avatar** — a callback Operation
  surface (Flask SSE + one Haiku call) consuming `recall.assemble()`. It is the
  LLM in the stack; `recall/` is its deterministic feed. W-4 intent: product
  **within the operator stack**.
- **Readiness signal:** trigger-language only (F-gov-08). The **memory→context**
  leg is richly designed; the **governance→posture** leg has **no design home**
  (F-gov-10) — the assistant retrieves memory but is not wired to read the
  extracted constitution at build time (R2-10/W-2). A *maturity blocker*, not
  just a doc gap: an assistant that reads no governance is not extraction-ready
  as the operator-stack triad defines it.
- **Observable extraction gate:** the triad is complete — memory feeds context
  (recall), governance directs posture (the assistant reads the extracted
  constitution, closing F-gov-10), the operator LLM occupies that space (W-2).
  Concretely: a second project's assistant boots from the same `recall/` + the
  same governance home with config changes only.
- **Harvest moment:** after extraction of both (a) and (b) — it depends on both.
  v1.0.7 builds it in-repo; breakout follows recall + governance.
- **Post-extraction relationship:** **dependency** on recall **and** the
  governance home. As the triad's join point, a frozen copy would desync from
  both substrates — dependency per Q24.

### (e) grounding-metric three-tier pattern (L0 / L1 / L2)

- **Coupling to host:** highest, deliberately. L0 is the deterministic,
  hot-path-safe fabricated-specifics detector; L1/L2 are model-based and stay
  **eval-only** behind `--grounding-signals`, never imported by production
  (F-eval-08). The sharpened typed L0 is eval/display-only; the hot path still
  uses a lossy proto-L0 (F-eval-09). The pattern is woven through
  `analyzer.py`/`hardening.py`/`evals/` — not a clean package.
- **Readiness signal:** trigger-language only — W-4 itself calls this one
  **"still research,"** not product. The UNCALIBRATED stamp (F-eval-08) and the
  never-run real loop (F-eval-02: L1/L2 precision/recall unmeasured) are the
  maturity gaps. The **least mature** of the five.
- **Observable extraction gate:** **research-resolved first**, then the standard
  metric. Research-resolved: the real loop has produced labels, L1/L2 are
  calibrated (precision/recall per detector against human labels), and the
  hot-path/eval-path L0 split is reconciled (F-eval-09).
- **Harvest moment:** not on the v1.x arc. Calibration is v1.0.7 pre-public
  (PV-2); extraction is post-v2 at the earliest, gated on research closure.
- **Post-extraction relationship:** undetermined — most likely a **frozen copy**
  (a reference pattern others re-implement), not a live dependency, because the
  hot-path L0 must stay co-located with the generation it guards (C-6). The
  pattern travels; the code may not. Confirm with the owner per Q24.

---

## Summary table

| Incubant | Coupling | Readiness today | Extraction gate (observable) | Harvest | Relationship |
|---|---|---|---|---|---|
| (a) recall/ | lowest (design invariant) | condition written; **design-only at pin** (F-arch-09) | boundary-lint green on committed pkg + 2nd consumer | post-v1.1.0 | dependency |
| (b) governance + compliance agent | embedded in mixed docs; agent absent | trigger-language (F-gov-08) | 2nd project adopts constitution + witness agent runs | after in-repo extract (v1.0.7) + agent-station | dependency (`@import` link required) |
| (c) LLM-wiki + loop | committed; lives *inside* (a) | sentinel-honest seam, no condition | recall's gate + ≥1 code cold-ingest fired (F-docs-10) | with (a) | dependency on memory product |
| (d) doc-grounded assistant | avatar = Operation surface on recall | memory leg designed; **governance leg has no home** (F-gov-10) | triad complete; 2nd project boots on same recall + gov | after (a)+(b) | dependency on both |
| (e) grounding three-tier | highest (hot-path L0 woven in) | **"still research"**; UNCALIBRATED (F-eval-08) | research-resolved (calibrated, F-eval-09 reconciled) *then* standard | post-v2 | likely frozen copy |

---

## Good practices (the harvest discipline)

- **Modularize in place — don't pre-abstract.** Hold a clean seam from day one;
  defer physical extraction to second-use (`memory-architecture.md` decision #6).
  `run_suite()` (F-arch-09) and the C-6 deterministic core are the landed
  evidence this is genuinely practiced — cite *those*, not the uncommitted
  `recall/`, when the pattern graduates to governance.
- **Extraction contracts as written invariants.** Each incubant declares its
  public surface + inward-only dependency rule as a contract future agents build
  against — the way AGENTS.md governs. recall's is the model (one entry point,
  four types, hard import rule). The contract makes "packaging only" true; every
  PR touching the seam must respect it — *that discipline is the cost of keeping
  extraction free.* Back it with a boundary-lint (F-arch-01) so it is
  machine-held, not vigilance-held (P-3/D-4).
- **Preserve provenance across the seam.** Every crossing unit keeps its stamp —
  `(tier, source_id, path:line, audience, sha)` for recall; `[[backlinks]]` +
  `[synthesis]` tags for the wiki (F-docs-07); `PROMPT_VERSION` for eval records.
  Extraction must not strip the audit trail (D-5); a frozen copy must record the
  source SHA it forked from, or the lineage C-2/S-1 honesty depends on is lost.

## Sequencing note (P-3/D-4)

None of these gates is a recurring human-labor obligation. Each resolves to a
machine-checkable event (lint green, a committed second consumer, a fired
ingest, calibration numbers reported) — chosen so extraction stays an observable
status, never an SLA. Phase 5 reconciles any drift between this playbook and
`main` (Sprint 6.4/6.6 landed past the pin). The graduation target is
`docs/dev/EXTRACTION.md` (v1.0.7+), where this contract becomes the home agents
build against.

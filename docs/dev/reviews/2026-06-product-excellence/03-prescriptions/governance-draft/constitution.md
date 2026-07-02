---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/governance/charter.md (v1.0.7)
---

# Constitution — sartor. (draft for `docs/governance/charter.md`)

> **What this is.** The constitutional draft for sartor., written *as*
> the v1.0.7 input to `docs/governance/charter.md` — the single canonical
> Governance home into which the rule-bearing clauses now scattered across
> six docs consolidate. This is a **citation map, not a rewrite**: each
> clause names its source doc(s) and lifts the rule once; the source keeps
> its descriptive content and a pointer back here (F-gov-05; extract-don't-
> restate, below).
>
> **Severity anchor + writing contract.** The SIGNED Product Charter
> ([`../../00-interview/product-charter.md`](../../00-interview/product-charter.md))
> governs both the review and this draft. It honors **C-0 claims
> discipline**: categorical ("never / only / always") wording appears only
> where a deterministic test can enforce it by construction; anywhere a
> claim rests on LLM behavior, this document describes **mechanisms and
> effort**, not absolutes — and carries no marketing language.
>
> **Evidence base.** Findings are cited by `F-id` rather than re-derived
> ([`../../02-assessment/findings-register.md`](../../02-assessment/findings-register.md)
> + [`../../02-assessment/verification-log.md`](../../02-assessment/verification-log.md)).
> WEAKENED findings are used with their **revised** claim. Assessed at the
> pin `c6e0437`; main has since moved (Sprint 6.4 + 6.6 landed) — Phase 5
> reconciles that drift, not this draft.

---

## How to read this document (extract-don't-restate)

The decision of record is **extract, don't register-in-place**
(`docs/wiki/pages/governance-extraction.md`; affirmed register-grade by
**F-gov-05**): each constitutional rule lives in **exactly one** canonical
home and everything else **references** it. So this document does not
duplicate the prose of `vision.md`, `SECURITY.md`, or the others — it
states the binding rule once and **cites the source** for the mechanics.
Every clause below is tagged `[src: …]` so the v1.0.7 extraction is a
verifiable citation map.

**Load-bearing safety condition (F-gov-05).** `AGENTS.md` / `CLAUDE.md` are
harness-auto-loaded — the agent's operating instructions at session start.
Extraction MUST preserve agent rule-access via `@import`
(`CLAUDE.md` already does `@AGENTS.md`) or an explicit canonical pointer,
or future agents lose their guardrails. `AGENTS.md` stays the entry point;
it imports/links Governance, it does not surrender the rules.

---

## Constitutional clauses

*Each clause is owner-voiced or machine-enforceable per the signed charter.
Tier intent: a clause stating a categorical is one a deterministic gate can
enforce by construction (or is named below as a gate still owed); a clause
resting on LLM behavior is written as mechanism-and-effort. The flat
"won't-cross" list in `vision.md` is replaced by this enforceability
tiering — **F-vision-01** (WEAKENED: six sub-sections, no "C-8" clause).*

**C-0 — Claims discipline.** Categorical claims are made only where a
deterministic test enforces them by construction (network egress, module
boundary, shipped-template properties). Where a claim depends on LLM
behavior, describe mechanisms and effort, never absolutes. *[src: charter
C-0 (signed); enforced against existing docs by **F-vision-02**, **F-docs-03**
— "the LLM cannot invent facts" is a barred absolute at `vision.md:50`,
`overview.md:26`, `llms.txt:4`, to be reworded to mechanism-and-effort.]*

**C-1 — Local and yours.** sartor. is a local tool under the control of a
single unauthenticated user; all user artifacts stay on the user's disk,
never uploaded; there is no hosted service. The loopback bind is the
construction that makes this categorical true. *[src: charter C-1; `vision.md`
"Local-first, single-tenant"; `SECURITY.md` "Scope". Owed gate: the
127.0.0.1 bind is implicit (Flask default), neither pinned nor asserted by a
test — **F-sec-02** (`app.py:6988 app.run()` has no `host=`; `SERVER_NAME` a
third silent-flip vector). The "single-tenant **by design / as a value**"
framing is demoted to a threat-model statement only — **F-vision-04**
(`list_users()`/multi-profile UI contradict the value claim; the
single-unauthenticated-user threat model is preserved).]*

**C-2 — Egress.** Outbound traffic is confined to an enumerable destination
set; because it is enumerable, this clause is machine-verifiable. The
sanctioned classes are exactly two: **(a)** the configured LLM provider, and
**(b)** the optional profile/website scrape when the user supplies
LinkedIn/portfolio URLs. JDs are pasted text — no JD-URL fetch exists. No
telemetry, analytics, or error reporting leaves the machine. *[src: charter
C-2; `vision.md` "Local-first"; `SECURITY.md` threat model. **Owed gate +
open corrections at the pin:** C-2 was verified by a one-time audit, not a
committed test — **F-qe-rel-02 / F-sec-01** (P0/P1; no egress/socket
falsifiability test; E-2 names this badge). Live divergences ruled at the
pin: the diagnostics dashboard fetches Chart.js from a CDN
(`dashboard/templates/dashboard.html:15`) — **F-vision-05 / F-sec-03 /
F-docs-02**, PX-01 vendor (v1.0.6); the profile scrape is dead code —
**F-docs-04**, PX-02 re-wire; `SECURITY.md` enumerates a phantom third
JD-URL egress class — **F-sec-04 / F-docs-01**, PX-03 docs-correct to the
two-class enumeration. The eval-grounding model download (~3.2GB from
huggingface.co) is a sanctioned power-user opt-in under D-6, not a third
egress class — **F-sec-10**.]*

**C-3 — Grounding mechanisms; grounded synthesis is the feature.**
sartor. works to keep the LLM grounded in real experience through stated
mechanisms — grounding rules in the prompts (with worked OK/NOT-OK
examples), clarifying questions that extend ground truth, human review at
each step, corpus approval of LLM-generated bullets, and a candidate memory.
Grounded synthesis — abstracting useful bullets from corpus + clarifications
toward a JD — is the feature; the violation is asserting beyond that ground,
not synthesizing within it. Grounding tightening that suppresses useful
grounded synthesis is a regression (lead AL-1). *[src: charter C-3;
`vision.md` "No invention, ever" (to be reworded off the absolute per C-0,
**F-vision-02**); `AGENTS.md` "LLM prompts"; `system-model.md` "What it is".
The deterministic source-union metric folds **three** sources — primary +
supplementals + clarification answers — not typed edits; `GROUNDING_METRIC.md`
overstates a four-part union (**F-eval-04**, WEAKENED AFFIRM). AL-1
over-suppression is uninstrumented in eval data today — **F-eval-01**.]*

**C-4 — The candidate stays in control.** Human review gates sit along the
pipeline; the user can edit anything before using it, and the tool produces
documents rather than submitting them. *[src: charter C-4; `vision.md` goal 3
+ P8 Human Gates; `system-model.md` "Production". Affirmed surfaces to
protect: keyboard bullet-reorder alternative (**F-expa11y-07**), live-region
announcements (**F-expa11y-08**), manual-promote annotation contract
(**F-eval-06**).]*

**C-5 — Everything sartor. ships is ATS-safe.** All bundled templates are
single-column, plain-bullet, standard-font; non-ATS templates are retired.
Users who want non-ATS output edit the document they produced. This
categorical is enforceable on shipped-template properties (a deterministic
domain under C-0). *[src: charter C-5; `vision.md` goal 2 + "ATS-safety is
the product". The escape hatch ("edit the document you produced") is not yet
named in `vision.md` — **F-vision-07** (P2).]*

**C-6 — The deterministic–LLM boundary.** Deterministic modules make no LLM
calls; one module (`analyzer.py`) owns all LLM calls. *[src: charter C-6;
`vision.md` "Deterministic where possible"; `AGENTS.md` "Architecture at a
glance" + "What NOT to do"; `system-model.md` "Production" + "the one law".
At the pin the boundary **holds by behavior** (7 modules clean, AST-verified
— **F-arch-04**) but by **convention only**: no import-lint/boundary test
fails on a regression — **F-arch-01 / F-qe-rel-04** (the "Inviolable"
categorical is owed the by-construction gate C-0 prescribes; ~15-line AST
test or import-linter contract, v1.0.8 WS-1).]*

### Defaults (binding until changed; changeable in normal flow with a written rationale)

- **D-1 — Minimal dependencies.** New dep = `pyproject.toml` + `CHANGELOG.md`
  + "couldn't reasonably be done in pure Python or an existing dep." *[src:
  charter D-1; `vision.md` "Minimal dependencies"; `CONTRIBUTING.md`;
  `AGENTS.md` "What NOT to do".]*
- **D-2 — Anthropic as sole LLM client**, with a planned amendment to
  provider-agnostic + local models post-public; C-2 amends by ceremony then.
  *[src: charter D-2.]*
- **D-3 — No accounts, no auth** — the current shape, explicitly negotiable.
  *[src: charter D-3; `SECURITY.md` "Out of scope".]*
- **D-4 — Commitments hygiene.** Public docs make no response-time SLAs and
  no recurring human-labor promises; machine-enforced gates are exempt. *[src:
  charter D-4. Two hard human SLAs still ship at the pin — **F-qe-rel-08 /
  F-sec-07** (`SECURITY.md:134-135` 5-day/30-day; `CODE_OF_CONDUCT.md:15`);
  soften to best-effort, v1.0.6.]*
- **D-5 — Open-standards + auditable-iterations mechanics** (JSON Resume
  intermediate; standard fonts, offline render; MIT-compatible licensing with
  vendored headers; per-generation timestamped child context as the audit
  trail). *[src: charter D-5; `vision.md`; `system-model.md`. Audit-trail
  spine affirmed — **F-arch-07**. Vendored axe is MPL-2.0, under-declared in a
  MIT-only LICENSE — **F-sec-08**.]*
- **D-6 — Per-system tool bundling, progressively disclosed.** Capabilities
  needing extra installs (grounding-scorer models, Chromium) bundle per
  system; install docs are progressive. *[src: charter D-6. Chromium
  classification is inconsistent across docs (basic-tool vs dev-only) —
  **F-docs-05** (WEAKENED to ~P3: reconcile the classification, not a clean
  D-6 contradiction).]*

---

## Working-model governance (W-1)

The real working model is **multi-altitude agent parallelism** — multiple
agent sessions at different altitudes, concurrently. The serial-session
framing still authoritative in the docs is stale and is retired here.
*[src: charter W-1; `system-model.md` "Operation". The stale framing:
**F-gov-03** (`RELEASE_ARC:390/863` "one branch per session"; two live
worktrees contradict it daily).]*

The isolation rules below are the review's **proposal** (W-1 directs the
reviewer to propose them), grounded in the **two live collisions
F-gov-02 documents in production hook code at the pin** — not hypotheticals:

1. **Worktree-per-session.** Each concurrent agent session runs in its own
   git worktree; sessions never share a working tree. This is the structural
   precondition that makes the ownership rules below enforceable rather than
   advisory.

2. **Global-state ownership — session-scoped, not global.**
   `~/.claude/plans/` and its `.approved` marker are a **single global
   path**: a second session writing a newer `*.md` invalidates the first
   session's approval, and `cleanup-plan-on-merge` deletes **all** `*.md`
   plus the marker (**F-gov-02 collision #1 + #2**). The rule: plan state and
   approval markers MUST be **session-scoped** (per-session or per-worktree
   namespace), so one session's plan lifecycle cannot trip or wipe another's.
   No session hand-creates the marker a hook checks for — only the sanctioned
   path (`ExitPlanMode`) creates `.approved` (**F-gov-07**, DEBUFF: the
   `check-plan-approved.sh:31-33` hint to hand-create the marker contradicts
   the never-hand-create rule and is removed).

3. **Branch ownership.** One branch per session; a session owns its branch
   end-to-end. The `block-merge-to-main` hook misses the dominant direction —
   the routine `--no-ff` feature-merge **passes unblocked**; only the reverse
   direction blocks (**F-gov-01**). The witness-class fix (detect
   `HEAD==main` via `git rev-parse --abbrev-ref HEAD`, which F-gov-02
   confirms is worktree-local) closes the common path so branch ownership is
   gate-backed, not vigilance-backed.

**Soft-commitments posture (charter P-3 / D-4).** Each isolation rule above
is written to prefer a **machine-enforced gate** over a human-promise SLA:
session-scoped paths and a worktree-local branch check are construction, not
recurring labor. No rule here obliges recurring human attention as a hard
commitment. The seven enforced blocker hooks are real and honestly separated
from witness/tribal rules (**F-gov-04**); the witness-class freshness
reminder + honest sentinel are a working precedent for a gate that nudges
without taxing the owner (**F-gov-06**).

**W-2 — Governance is constitution-building.** This document *is* the
extraction vehicle: one canonical home the descriptive layer is audited
against (does what we built still match what we said?). The operator-stack
triad — memory supplies context, governance directs posture, the operator
LLM occupies that space — is the extraction architecture; the v1.0.7
doc-grounded assistant receives its governance interface at build time.
A governance→assistant design home does not yet exist (**F-gov-10**, WATCH).
*[src: charter W-2; `docs/wiki/pages/governance-extraction.md`;
`system-model.md` "Governance".]*

---

## Amendment ceremony

Amending a **constitutional clause (C-0..C-6)** requires, in order:

1. a dated amendment entry **in this document**, with rationale;
2. a `CHANGELOG.md` entry;
3. explicit **owner sign-off** at merge; and
4. once the compliance agent exists, a flag in its next drift report —
   **witness, not approver** (it records the change, it does not gate it).

**Defaults (D-1..D-6)** change in normal branch flow with a single written
rationale line — no full ceremony. *[src: charter "Amendment ceremony"
(reviewer proposal, confirmed at sign-off). The witness-class precedent is
real today — `wiki-freshness-reminder` + the honestly-left
`.last_ingest_sha` sentinel, **F-gov-06 / F-docs-08**; per C-0 / D-4 the
drift report is a witness gate, never a recurring manual-audit promise.]*

---

## Citation map — where each rule was extracted from

| Clause | Canonical source(s) the rule is lifted from |
|---|---|
| C-0 | charter C-0 |
| C-1 | charter C-1 · `vision.md` · `SECURITY.md` |
| C-2 | charter C-2 · `vision.md` · `SECURITY.md` |
| C-3 | charter C-3 · `vision.md` · `AGENTS.md` · `system-model.md` |
| C-4 | charter C-4 · `vision.md` · `system-model.md` |
| C-5 | charter C-5 · `vision.md` |
| C-6 | charter C-6 · `vision.md` · `AGENTS.md` · `system-model.md` |
| D-1..D-6 | charter D-1..D-6 · `vision.md` · `CONTRIBUTING.md` · `SECURITY.md` · `PRODUCT_SHAPE.md` |
| W-1 (isolation) | charter W-1 · `system-model.md` · grounded in **F-gov-02** |
| W-2 | charter W-2 · `governance-extraction.md` |
| Amendment | charter "Amendment ceremony" |

Each source doc retains its descriptive content and gains a **pointer** to
the clause here; per F-gov-05 the rule is stated **once**, in this home. The
graduation target is `docs/governance/charter.md` (v1.0.7), preserving the
`@AGENTS.md` import chain so agent rule-access survives the move.

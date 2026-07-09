# Constitution — sartor.

> **Purpose:** the single canonical home for sartor.'s *binding* governance —
> the constitutional clauses (C-0…C-6), the defaults (D-1…D-6), the parallel-session
> working model (W-1/W-2), and the amendment ceremony. Each rule is stated **once**,
> here; the descriptive docs that used to carry it now keep their prose and point back.
> **Audience:** every contributor and every AI agent (Claude Code, Cursor, Codex,
> Aider, …) making a non-trivial change; the future compliance agent that audits
> drift against this home.
> **Authoritative for:** the rule-bearing constitution. On any conflict between this
> charter and a restatement in a descriptive doc (`vision.md`, `AGENTS.md`,
> `SECURITY.md`, `CONTRIBUTING.md`, `docs/PRODUCT_SHAPE.md`, `docs/dev/RELEASE_ARC.md`),
> **the charter governs.** Enforcement detail (what is a gate vs witness vs tribal)
> lives in [`enforcement.md`](enforcement.md); success criteria + the eval ride-along
> + the review rubric live in [`metrics.md`](metrics.md).

---

## What this is

This is the constitution sartor. is built and audited against. It graduated
(Sprint 7.2, v1.0.7) from the SIGNED Product Charter that governed the 2026-06
product-excellence review
([`../dev/reviews/2026-06-product-excellence/00-interview/product-charter.md`](../dev/reviews/2026-06-product-excellence/00-interview/product-charter.md))
and the four-file governance-draft the review pre-authored. The decision of record is
**extract, don't register-in-place**
([`../wiki/pages/governance-extraction.md`](../wiki/pages/governance-extraction.md);
affirmed register-grade by **F-gov-05**): each rule lives in **exactly one** canonical
home and everything else **references** it. So this document does not duplicate the
prose of `vision.md`, `SECURITY.md`, or the others — it states the binding rule once and
**cites the source** for the mechanics. Every clause is tagged `[src: …]` so the
extraction is a verifiable citation map.

**Writing contract (C-0).** Categorical wording ("never / only / always") appears
only where a deterministic test can enforce it by construction; anywhere a claim rests
on LLM behavior, this document describes **mechanisms and effort**, not absolutes — and
carries no marketing language.

**Evidence base.** Findings are cited by `F-id` rather than re-derived
([`../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md`](../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md)
+ the verification log alongside it). The `F-id` evidence base is pinned at the review
SHA `c6e0437`; **the `[src: …]` tags below are reconciled to current `main`** — where a
correction the draft "owed" has since landed (the v1.0.6 PX batch), the tag cites it as
**already corrected**, not as still-owed. Only two gates stay forward-sequenced to
v1.0.8 (C-1 bind, C-6 boundary); both are marked inline.

**Load-bearing safety condition (F-gov-05).** `AGENTS.md` / `CLAUDE.md` are
harness-auto-loaded — the agent's operating instructions at session start. Extraction
preserves agent rule-access via `@import` (`CLAUDE.md` already does `@AGENTS.md`) or an
explicit canonical pointer, or future agents lose their guardrails. `AGENTS.md` stays
the entry point and keeps its rules **inline** (non-Claude agents read it raw); it
links this charter, it does not surrender the rules.

---

## Constitutional clauses

*Each clause is owner-voiced or machine-enforceable. Tier intent: a clause stating a
categorical is one a deterministic gate can enforce by construction (or is named below
as a gate still owed); a clause resting on LLM behavior is written as
mechanism-and-effort. The flat "won't-cross" list in `vision.md` is replaced by this
enforceability tiering — **F-vision-01**.*

**C-0 — Claims discipline.** Categorical claims are made only where a deterministic
test enforces them by construction (network egress, module boundary, shipped-template
properties). Where a claim depends on LLM behavior, describe mechanisms and effort,
never absolutes. *[src: charter C-0 (signed). The LLM-behavior absolutes flagged by
**F-vision-02** / **F-docs-03** — "the LLM cannot invent facts", the "No invention,
ever" heading, the "without inventing anything" / "may not fabricate" copy — were
reworded to mechanism-and-effort in v1.0.6 (**PX-09**): `vision.md` goal 1 + "Grounding
mechanism, not a guarantee", and the wiki overview / `llms.txt` copy. Cited as
corrected; not re-fixed.]*

**C-1 — Local and yours.** sartor. is a local tool under the control of a single
unauthenticated user; all user artifacts stay on the user's disk, never uploaded; there
is no hosted service. The loopback bind is the construction that makes this categorical
true. *[src: charter C-1; `../../vision.md` "Local-first, single-tenant"; `../../SECURITY.md`
"Scope". The "single-tenant **by design / as a value**" framing is demoted to a
threat-model statement (**F-vision-04**: `list_users()` / multi-profile UI contradict
the value claim; the single-unauthenticated-user threat model is preserved) — the
demotion lands in `vision.md` on this branch (PX-27). **Gate shipped — v1.0.8 Sprint
8.3a (PX-19):** the 127.0.0.1 bind is now pinned + asserted by a test (was implicit,
neither pinned nor asserted — **F-sec-02**, `app.py app.run()` had no `host=`;
`SERVER_NAME` a silent-flip vector) — see [`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md)
Sprint 8.3a. Owner-approved factual reconcile, 2026-07-09, witness CW-102.]*

**C-2 — Egress.** Outbound traffic is confined to an enumerable destination set;
because it is enumerable, this clause is machine-verifiable. The sanctioned classes are
exactly two: **(a)** the configured LLM provider, and **(b)** the optional
profile/website scrape when the user supplies LinkedIn/portfolio URLs. JDs are pasted
text — no JD-URL fetch exists. No telemetry, analytics, or error reporting leaves the
machine. *[src: charter C-2; `../../vision.md` "Local-first"; `../../SECURITY.md` threat
model. The egress falsifiability gate C-0 requires is **SHIPPED** (**PX-08**;
[`../../tests/test_egress_allowlist.py`](../../tests/test_egress_allowlist.py) —
**F-qe-rel-02** P0 / **F-sec-01**). The pin-era divergences are resolved: Chart.js
vendored + SRI-pinned, no runtime CDN (**PX-01**; **F-vision-05** / **F-sec-03** /
**F-docs-02**); the dead profile scrape re-wired (**PX-02**; **F-docs-04**); SECURITY's
phantom third JD-URL egress class corrected to the two-class enumeration (**PX-03**;
**F-sec-04** / **F-docs-01**). The eval-grounding model download (~3.2GB from
huggingface.co) is a sanctioned power-user opt-in under D-6, not a third egress class —
**F-sec-10**.]*

**C-3 — Grounding mechanisms; grounded synthesis is the feature.** sartor. works to
keep the LLM grounded in real experience through stated mechanisms — grounding rules in
the prompts (with worked OK/NOT-OK examples), clarifying questions that extend ground
truth, human review at each step, corpus approval of LLM-generated bullets, and a
candidate memory. Grounded synthesis — abstracting useful bullets from corpus +
clarifications toward a JD — is the feature; the violation is asserting beyond that
ground, not synthesizing within it. Grounding tightening that suppresses useful grounded
synthesis is a regression (lead AL-1). *[src: charter C-3; `../../vision.md` goal 1 +
"Grounding mechanism, not a guarantee" (already C-0-corrected, PX-09 — cited, do not
edit); `../../AGENTS.md` "LLM prompts"; `../system-model.md` "What it is". The
deterministic source-union metric folds **three** sources — primary + supplementals +
clarification answers — not typed edits; `GROUNDING_METRIC.md` states the three-source
union as of **PX-14** (**F-eval-04**, WEAKENED AFFIRM — cited as corrected). AL-1
over-suppression is uninstrumented in eval data today (**F-eval-01**) — tracked in
[`metrics.md`](metrics.md) §2.]*

**C-4 — The candidate stays in control.** Human review gates sit along the pipeline;
the user can edit anything before using it, and the tool produces documents rather than
submitting them. *[src: charter C-4; `../../vision.md` goal 3 + P8 Human Gates;
`../system-model.md` "Production". Affirmed surfaces to protect: keyboard
bullet-reorder alternative (**F-expa11y-07**), live-region announcements
(**F-expa11y-08**), manual-promote annotation contract (**F-eval-06**).]*

**C-5 — Everything sartor. ships is ATS-safe.** All bundled templates are
single-column, plain-bullet, standard-font; non-ATS templates are retired. Users who
want non-ATS output edit the document they produced. This categorical is enforceable on
shipped-template properties (a deterministic domain under C-0). *[src: charter C-5;
`../../vision.md` goal 2 + "ATS-safety is the product". The escape hatch ("users who
want non-ATS output edit the document they produced") is named in `vision.md` goal 2 as
of this branch's PX-27 edit (**F-vision-07**). The shipped-template property gate is
forward-sequenced to v1.1.0 — see [`enforcement.md`](enforcement.md) §A.]*

**C-6 — The deterministic–LLM boundary.** Deterministic modules make no LLM calls; one
module (`analyzer.py`) owns all LLM calls. *[src: charter C-6; `../../vision.md`
"Deterministic where possible"; `../../AGENTS.md` "Architecture at a glance" + "What NOT
to do"; `../system-model.md` "Production" + "the one law". The boundary **holds by
behavior** (7 modules clean, AST-verified — **F-arch-04**) but by **convention only**:
no import-lint/boundary test fails on a regression. **Gate shipped — v1.0.8 Sprint
8.3a (PX-20, WS-1):** an AST-walk boundary test,
[`../../tests/test_construction_boundary.py`](../../tests/test_construction_boundary.py)
(**F-arch-01** / **F-qe-rel-04**) — see [`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md)
Sprint 8.3a. Owner-approved factual reconcile, 2026-07-09, witness CW-102.]*

### Defaults (binding until changed; changeable in normal flow with a written rationale)

- **D-1 — Minimal dependencies.** New dep = `pyproject.toml` + `CHANGELOG.md` +
  "couldn't reasonably be done in pure Python or an existing dep." *[src: charter D-1;
  `../../vision.md` "Minimal dependencies"; `../../CONTRIBUTING.md`; `../../AGENTS.md`
  "What NOT to do".]*
- **D-2 — Anthropic as sole LLM client**, with a planned amendment to provider-agnostic
  + local models post-public; C-2 amends by ceremony then. *[src: charter D-2.]*
- **D-3 — No accounts, no auth** — the current shape, explicitly negotiable. *[src:
  charter D-3; `../../SECURITY.md` "Out of scope".]*
- **D-4 — Commitments hygiene.** Public docs make no response-time SLAs and no recurring
  human-labor promises; machine-enforced gates are exempt. *[src: charter D-4. The two
  hard human SLAs flagged by **F-qe-rel-08** / **F-sec-07** (`SECURITY.md` 5-day/30-day;
  `CODE_OF_CONDUCT.md`) were softened to best-effort in v1.0.6 (**PX-05/07**) — both now
  state no guaranteed timeline. Cited as corrected; do not re-soften.]*
- **D-5 — Open-standards + auditable-iterations mechanics** (JSON Resume intermediate;
  standard fonts, offline render; MIT-compatible licensing with vendored headers;
  per-generation timestamped child context as the audit trail). *[src: charter D-5;
  `../../vision.md`; `../system-model.md`. Audit-trail spine affirmed — **F-arch-07**.
  Vendored axe is MPL-2.0, under-declared in a MIT-only LICENSE — **F-sec-08**; a
  REUSE/SPDX manifest is planned for the public release (v1.1.0).]*
- **D-6 — Per-system tool bundling, progressively disclosed.** Capabilities needing
  extra installs (grounding-scorer models, Chromium) bundle per system; install docs are
  progressive. *[src: charter D-6. Chromium's docs classification (was inconsistent
  across docs, basic-tool vs dev-only — **F-docs-05**) was reconciled in v1.0.7
  (**PX-31**): reclassified PDF-output-only across `docs/install.md`'s Prerequisites +
  all 3 OS sequences, correcting the "renders every PDF and the live preview"
  conflation (the live preview is browser-side paged.js, Chromium-free). Cited as
  corrected; do not re-flag. Owner-approved factual reconcile, 2026-07-09, witness
  CW-104.]*

---

## Working-model governance (W-1)

The real working model is **multi-altitude agent parallelism** — multiple agent
sessions at different altitudes, concurrently — each isolated in its own git worktree.
The serial-session framing still echoed in some docs ("one branch per session", "one at
a time") is retired here: branch ownership and worktree isolation are the rule, not
global serialization. *[src: charter W-1; `../system-model.md` "Operation". The stale
framing **F-gov-03** (`RELEASE_ARC.md` "one branch per session" + the hard-constraint
line) is reframed on this branch to cite this section; two live worktrees contradict the
serial framing daily.]*

The isolation rules below are grounded in the **two live collisions F-gov-02 documents
in production hook code** — not hypotheticals:

1. **Worktree-per-session.** Each concurrent agent session runs in its own git
   worktree; sessions never share a working tree. This is the structural precondition
   that makes the ownership rules below enforceable rather than advisory. *(See
   [[feedback-concurrent-agents-worktree]] for the lived failure: a shared tree lets one
   session's `git add` sweep another's edits and its merge wipe the global marker.)*

2. **Global-state ownership — session-scoped, not global.** `~/.claude/plans/` and its
   `.approved` marker are a **single global path**: a second session writing a newer
   `*.md` invalidates the first session's approval, and `cleanup-plan-on-merge` deletes
   **all** `*.md` plus the marker (**F-gov-02** collision #1 + #2). The rule: plan state
   and approval markers MUST be **session-scoped** (per-session or per-worktree
   namespace), so one session's plan lifecycle cannot trip or wipe another's. No session
   hand-creates the marker a hook checks for — only the sanctioned path (`ExitPlanMode`)
   creates `.approved` (**F-gov-07**); the `check-plan-approved.sh` hint to hand-create
   the marker is **removed on this branch (PX-28)**, retiring the contradiction with the
   never-hand-create rule.

3. **Branch ownership.** One branch per session; a session owns its branch end-to-end
   (concurrency comes from *separate* sessions in separate worktrees, not from one
   session juggling branches). The `block-merge-to-main` hook missed the dominant
   direction — the routine `--no-ff` feature-merge passed unblocked; only the reverse
   blocked (**F-gov-01**). The witness-class fix (detect `HEAD == main` via
   `git rev-parse --abbrev-ref HEAD`, which F-gov-02 confirms is worktree-local) **lands
   on this branch (PX-24)**, closing the common path so branch ownership is gate-backed,
   not vigilance-backed.

4. **Carry-forward discipline (cumulative open ledger).** Tracked-deferred observations
   live in **one physical authoritative ledger** — the "Carry-forward ledger" in
   [`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md) — not scattered across
   per-stream sections joined by unchecked pointers. **Every handoff renders the full
   *still-open* subset** (cumulative, not a this-session delta), so items cannot fall out
   of attention; at **~8–10 open items**, a reduction sprint is scheduled. This is the
   same one-canonical-home discipline this charter applies to rules, applied to the
   loose-ends ledger — small pieces stop getting lost in a mess of references. *[src:
   owner direction 2026-06-15; mirrored in `../../AGENTS.md` "Branch close-out
   checklist" step 0 + [`AGENT_HANDOFF_TEMPLATE.md`](../dev/AGENT_HANDOFF_TEMPLATE.md);
   see [[feedback-cumulative-open-ledger]].]*

**Soft-commitments posture (P-3 / D-4).** Each isolation rule above prefers a
**machine-enforced gate** over a human-promise SLA: session-scoped paths and a
worktree-local branch check are construction, not recurring labor. No rule here obliges
recurring human attention as a hard commitment. The seven enforced blocker hooks are
real and honestly separated from witness/tribal rules (**F-gov-04**); the witness-class
freshness reminder + honest sentinel are a working precedent for a gate that nudges
without taxing the owner (**F-gov-06**).

**W-2 — Governance is constitution-building.** This document *is* the extraction
vehicle: one canonical home the descriptive layer is audited against (does what we built
still match what we said?). The operator-stack triad — memory supplies context,
governance directs posture, the operator LLM occupies that space — is the extraction
architecture; the v1.0.7 doc-grounded assistant receives its governance interface at
build time. A governance→assistant design home does not yet exist (**F-gov-10**, WATCH).
*[src: charter W-2; `../wiki/pages/governance-extraction.md`; `../system-model.md`
"Governance".]*

---

## Amendment ceremony

Amending a **constitutional clause (C-0..C-6)** requires, in order:

1. a dated amendment entry **in this document**, with rationale;
2. a `CHANGELOG.md` entry;
3. explicit **owner sign-off** at merge; and
4. once the compliance agent exists, a flag in its next drift report — **witness, not
   approver** (it records the change, it does not gate it).

**Defaults (D-1..D-6)** change in normal branch flow with a single written rationale
line — no full ceremony. *[src: charter "Amendment ceremony" (reviewer proposal,
confirmed at sign-off). The witness-class precedent is real today —
`wiki-freshness-reminder` + the honestly-left `.last_ingest_sha` sentinel, **F-gov-06**
/ **F-docs-08**; per C-0 / D-4 the drift report is a witness gate, never a recurring
manual-audit promise.]*

---

## The 10 Principles backbone (frozen)

sartor. follows the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/);
the codebase is annotated with principle references (P1, P2, P5, P6, P8, P9). Five are
**load-bearing** and are frozen here as part of the constitution — a change that
conflicts with one of these usually loses. The descriptive write-up (with code anchors)
stays in [`../../vision.md`](../../vision.md) "Principles backbone".

- **P1 Hardening** — deterministic Python for mechanical work; the LLM only for fuzzy
  reasoning. This is the construction behind **C-6** and the deterministic-file list.
- **P2 Context Hygiene** — `context_set` is the structured JSON contract between
  pipeline stages; iteration state round-trips safely (`total=False`).
- **P5 Institutional Memory** — ALWAYS / NEVER rules in `analyzer.py:SYSTEM_PROMPT`;
  tuning history in `evals/TUNING_LOG.md`; release reasoning in the durable docs. This
  charter is itself a P5 artifact.
- **P8 Human Gates** — two required review checkpoints plus optional clarification
  interviews; skipping a clarification step never degrades output below prior behavior.
  This is the construction behind **C-4**.
- **P9 Observability** — JSONL telemetry per LLM call (model, tokens, latency, cost);
  the read-only `/_dashboard` aggregates trends; eval records carry `prompt_version`.

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
| W-1 (carry-forward) | owner direction 2026-06-15 · `AGENTS.md` · `AGENT_HANDOFF_TEMPLATE.md` |
| W-2 | charter W-2 · `governance-extraction.md` |
| Amendment | charter "Amendment ceremony" |

Each source doc retains its descriptive content and gains a **pointer** to the clause
here; per F-gov-05 the rule is stated **once**, in this home, preserving the `@AGENTS.md`
import chain so agent rule-access survives the move.

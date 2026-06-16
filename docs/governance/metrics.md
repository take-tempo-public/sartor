# Metrics & rubrics — callback. governance

> **Purpose:** the quantified success criteria `vision.md` states in prose (made
> testable), the deterministic product metrics that ride every eval, and the per-domain
> review rubric — the standing rubric the future compliance agent and future reviews
> apply. Companion to [`charter.md`](charter.md) (the binding rules) and
> [`enforcement.md`](enforcement.md) (gate vs witness).
> **Audience:** the owner cutting v1.1.0; eval/tuning contributors; the compliance agent.
> **Authoritative for:** the v1.1.0 tag checklist (SC-1..SC-5), the eval ride-along
> contract, and the review rubric.
> Written under **C-0**: where a number depends on LLM behavior it is **measured and
> tracked**, never a guaranteed floor; categorical thresholds appear only where a
> deterministic test enforces them by construction. Under **P-3/D-4**, every standing
> obligation is a machine-run gate, not a recurring human-labor promise. Evidence cited
> by `F-id` ([`../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md`](../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md));
> `F-id` pinned at `c6e0437`, claims reconciled to current `main`.

---

## 1. Success criteria — the v1.1.0 tag-evidence checklist

M-2 is the charter's written v1.1.0 tag evidence, in prose. Below it is a checklist of
decidable items — evidence to **produce** once, not a recurring promise. T-D names the
gap they close: the machinery has been measured on synthetic fixtures, never a real
corpus (F-eval-02; F-qe-rel-07 WEAKENED — already a named, sequenced, release-blocking
task set, so this *tracks* the work).

**SC-1 — The 10-application matrix.** ≥10 real applications submitted via callback. with
**zero release-blocking bugs**, spanning, as a coverage matrix: ≥3 with a clarify round
· ≥2 iterating after first generate · ≥2 cover letters · ≥2 distinct templates · both
output formats · ≥1 prior-app reuse. The Application rows + `parent_context_path` chains
are the audit trail (F-vision-03 confirms the status funnel ships UI→route→DB; F-arch-07
confirms the chain is inspectable); a report tallying the six dimensions is the artifact.

**SC-2 — Tuning loop exercised end-to-end.** The annotate→tune→verify loop run once
against `--suite real` + the anchor canary, metrics readable at a glance. *Blocked* by
an empty `evals/fixtures/real/` (F-eval-02: `.gitkeep` only; L1/L2 UNCALIBRATED).
Decidable form: a committed `bootstrap.json`/`annotations.json` seed exists and the run
yields a **measured** L0 (then L1/L2) precision/recall number — tracked, not asserted
(F-eval-08 KEEP: the UNCALIBRATED state is already surfaced honestly).

**SC-3 — Two first-run bars.** (a) fresh-clone skip-clarify smoke **< 5 min** — a
wall-clock measurement a CI job could time once Chromium installs (F-qe-rel-01, P0); (b)
full clarify-inclusive first run **~15 min**, quality evidenced by a one-time
**owner-blind comparison** against a hand-tailored resume (recorded with provenance, not
a standing SLA). Both unbuilt (F-expa11y-10 WATCH).

**SC-4 — Explainability artifacts (v1.0.7).** Three shipped: the user-facing "how
callback. grounds, clarifies, and tunes" wiki page; a **lay metrics legend** in
diagnostics; the planned diagnostics improvements. The lay legend and lay-register
console copy are the open work (F-expa11y-04 / F-eval-03; S-3 is the owner's weakest
area); ACCESSIBILITY.md as an honest-status page is the adjacent E-2 artifact
(F-expa11y-03). "Shipped" = the file exists and a non-coding power user (A-2) can read
it.

**SC-5 — Interviews: weighed, not gating.** ≥1 interview from a callback-written resume
is a written criterion **weighed as evidence, not a hard gate** (M-1; the reviewer's
split, accepted in sign-off). Market-dependent and, by C-2/T-A, unobservable in
aggregate — only the user's own instance captures the local outcome (F-vision-03
confirms `status=interview` is captured locally). Recorded as evidence-if-present; never
blocks the tag alone.

---

## 2. Deterministic product metrics — the eval ride-along set + floors

Deterministic post-generation measurements (no LLM call to compute) that ride every eval
result, plus one proposed addition. Per C-0 the LLM-dependent ones carry a **tracked
floor** (a regression alarm vs the committed baseline), not an absolute guarantee.

| Metric | Measures | Floor / gate | Provenance |
|---|---|---|---|
| `grounding_overlap` | Draft attribution vs the **three-source** union (résumé + supplementals + clarification answers) | Eval gate: any rubric drop > 0.5 vs baseline → exit 2, fails `eval-smoke` (exit-2 path guarded, PX-13) | F-qe-rel-05 KEEP; F-eval-04 WEAKENED |
| `grounding_overlap.missing_samples` | The actionable fabrication signal | Tracked over `prompt_version`; investigate on rise | C-3; charter eval-obs |
| `verb_diversity` | Verb variety | Tracked vs baseline; no absolute floor | charter ride-along |
| `specificity_density` | Concrete detail per bullet | Tracked vs baseline; no absolute floor | charter ride-along |
| `cost_usd` | Per-generation API cost | Tracked; perf-floor candidate (below) | F-qe-rel-06 WATCH |
| **`suggested_bullet_count` (proposed, AL-1)** | `recommend`-step suggested bullets, over `prompt_version` | Tracked; alarm on sustained drop | F-eval-01 CONFIRMED |

**C-3 carve-out + gate scope.** `grounding_overlap` distinguishes "asserted beyond
ground" (violation) from "synthesized within ground" (feature); its union folds
**three** sources, **not** first-person typed edits. `GROUNDING_METRIC.md` states the
three-source union as of **PX-14** (F-eval-04 WEAKENED — cited as corrected, do not
re-fix). In CI the gate runs `--subset smoke` = the **grounding rubric only across the 3
synthetic fixtures**, not the full 4-rubric matrix (manual `--suite synthetic`) and not
real data (F-qe-rel-05 / F-qe-rel-07 WEAKENED; F-eval-10 FIX: corpus-mode uncovered). A
real machine gate (exit 2 → fail), correctly scoped.

**AL-1 instrument (`suggested_bullet_count`).** The open over-suppression suspicion —
grounding tightening may have cut suggested-bullet counts (T-B; S-3) — is
**unfalsifiable from data** today: the ride-along set omits any bullet count;
`bullet_count` counts *final-resume* bullets behind the `--grounding-signals` opt-in;
`selected_bullets` is hand-counted in `TUNING_LOG`; the eval pipeline never invokes
`recommend`/`_dropoffPick` (F-eval-01, CONFIRMED). Chart the `recommend`-step count over
`PROMPT_VERSION`. Per C-0 a **tracked trend with an alarm on sustained drop**, never an
absolute floor — strictness legitimately trades against count (C-3/T-B), so it surfaces
for human judgement, not a hard-block (scope it as its own small add, not opt-in
`bullet_count` reuse).

**Perf floor (F-qe-rel-06 WATCH).** No automated perf gate exists; perf is a
provenance-traced narrative + a manual PR checkbox. The machine replacement, off existing
telemetry ([`../dev/perf/PERFORMANCE_HISTORY.md`](../dev/perf/PERFORMANCE_HISTORY.md),
sourced to `logs/llm_calls.jsonl`): anchor-suite **p50 latency + `cost_usd`** vs a
committed floor, alarming on a silent cache break (the `.2→.3` regression once caught by
hand) — D-4-clean, no human promise.

---

## 3. Per-domain review rubric (reusable)

Lifted from the eight domain guides, normalized so the compliance agent and future
reviews apply one rubric. **BOOST** = makes a charter promise more enforceable by
construction; **KEEP** = an at-bar mechanism to protect through refactor; **FIX** = a
doc/code-vs-charter conflict with a known landing; **DEBUFF** = reject on sight (C-0
absolutes; unauthorized escape-hatch use); **WATCH** = drift-prone, not yet a conflict.
Cells cite F-ids; WEAKENED findings carry their revised claim.

| Domain | BOOST | KEEP | FIX | DEBUFF | WATCH |
|---|---|---|---|---|---|
| **Vision & definition** | tier constraints by enforceability (C-0); tie a success criterion to a user-instance-observable mechanism (M-1) | non-marketing identity; ordered three goals; seven-functions self-model + honesty seams; Corpus-Item asymmetry matrix | flat won't-cross tier (F-vision-01 WEAKENED); success under-stated (F-vision-03); ATS hatch (F-vision-07) + admitted audiences (F-vision-10) **landed PX-27** | any LLM-behavior absolute (F-vision-02 / F-docs-03) | identity drift as new audiences emerge |
| **Architecture & code health** | a structural C-6 enforcer (import-lint / AST test failing on a deterministic-module LLM import) | directional import rule; `_within` containment; per-edge cascade rationale; idempotent migrations (F-arch-04/06/07) | blast-radius numbers re-measured (F-arch-02, **landed PX-10**); route-security-lint scope for blueprints (F-arch-03 WEAKENED — latent P2/P3) | a blueprint split that changes behavior or drops a guard | long-lived-DB drift; no data-bearing migration test (F-arch-08 / F-qe-rel-09) |
| **Experience & a11y** | a taxonomy line local-only → machine-checked in CI (E-2); a lay power-user explainer (S-3); cold no-key user guided (F-expa11y-02) | `_announce()` discipline (F-expa11y-08); keyboard-reorder floor (F-expa11y-07); modal trap/Escape/focus-return (F-expa11y-09 WEAKENED — not yet test-covered); vendored axe gate | CI not running the a11y/UX tier (F-expa11y-01 / F-qe-rel-01 P0); dev-register legends (F-expa11y-04) | WCAG-conformance language or a tag gate (E-2 forbids both); a11y tightening breaking C-5 ATS / C-4 edits | unbuilt Sprint bars the M-2 criteria ride on (F-expa11y-10); zero History API (F-expa11y-06) |
| **Quality eng & release** | committed egress-falsifiability test (F-qe-rel-02 / F-sec-01, **landed PX-08**); CI Chromium job making the a11y/PDF tier required (F-qe-rel-01); a data-bearing migration test | py3.11–3.13 matrix; deterministic-module test set; eval-quality regression gate (F-qe-rel-05); least-privilege CI perms (F-qe-rel-10) | wire `pytest -m ux` into CI; add E-2 machine badges (F-qe-rel-03 / F-sec-09); the two human SLAs softened (F-qe-rel-08 / F-sec-07, **landed PX-05/07**) | any badge enforcing nothing (coverage-%, SLSA, "ATS-score" checkers) | green-CI-but-real-data-untested (F-qe-rel-07 WEAKENED); the perf gate (F-qe-rel-06) |
| **Eval / grounding / tuning** | real loop run end-to-end with a measured L0/L1/L2 precision-recall number (closes SC-2 + T-D); the AL-1 instrument (§2) | three-tier attribution reframe; three-source union scoring; candidate-quarantine (F-eval-05); fail-closed annotation contract (F-eval-06); manual promote; hot-path discipline | lay metrics legend (F-eval-03); corpus-mode uncovered by the synthetic suite (F-eval-10) | uncalibrated L1/L2 treated as trustworthy (F-eval-08); grounding tightening shipped without checking suggested-bullet impact (re-opens AL-1) | paraphrase/implication false positives (F-eval-09) |
| **OSS readiness, security & privacy** | committed egress-allowlist test (**landed**); SPDX/REUSE declaring axe (MPL-2.0) + Chart.js; PVR live before day one | `_safe_username`/`_within` + lint hook (F-sec-05 — helper-usage density, not per-route proof); thorough gitignore; synthetic-only fixtures (F-sec-06); preserved license headers | pin+assert the loopback bind (F-sec-02, v1.0.8); C-2 ruling work (PX-01/02/03 **landed**); license under-declaration (F-sec-08); wrong-repo disclosure channel (F-sec-11 **landed**) | any new human-response SLA or recurring manual-audit promise (D-4/P-3); any "never leaks" without a deterministic test (C-0); a route without the guard pair | badges becoming solo-owner obligations (E-1); FLASK_DEBUG if ever proxied |
| **Docs & wiki** | stranger follows `llms.txt`/README → wiki to an accurate self-description with working `path:line` cites; egress story identical across docs and matching code | one grounding rule + `[synthesis]`/`path:line`/`[[backlinks]]` (F-docs-07); sentinel-honesty (F-docs-08); D5 cite-don't-restate (F-docs-09); `llms.txt` front door | reconcile egress enumeration across docs (F-docs-01 **landed PX-03**); vendor Chart.js (F-docs-02 **landed PX-01**); strike the dead-scrape description (F-docs-04 **landed PX-02**) | any doc asserting a capability code lacks; a C-0-barred absolute | inconsistent Chromium classification (F-docs-05 WEAKENED — ~P3 nit) |
| **Governance, memory & incubation** | isolation rule-set written as governance closing the two W-1 collisions structurally (worktree-aware branch detection **PX-24**; per-session/worktree-scoped marker) + a witness-class drift report | seven blocker hooks + settings wiring (F-gov-04); read-only subagent pattern (F-gov-09); seven-functions self-model; witness-class freshness reminder (F-gov-06) | worktree-blind branch hook + global plan marker (F-gov-02; PX-24 closes the branch-hook half); serial-session framing (F-gov-03 **reframed this branch**); hand-create-marker hint (F-gov-07 **removed PX-28**) | a categorical *process* claim no hook enforces (F-gov-01); an escape hatch on agent initiative, not owner direction | tribal rules with no witness (PROMPT_VERSION bump, new-dep); extraction-reintegration friction |

---

## 4. Graduation note

This is the graduated home (Sprint 7.2, v1.0.7) of the review's metrics-and-rubrics
draft: SC-1..SC-5 are the v1.1.0 tag checklist; §2 is the eval ride-along contract (the
AL-1 instrument + perf floor are tracked-gate additions); §3 is the compliance agent's
standing review rubric. Per C-0 nothing here promises LLM behavior — floors are tracked
alarms; categorical gates are only those a deterministic test holds by construction. Per
P-3/D-4 every standing item is a machine gate, never a recurring human SLA.

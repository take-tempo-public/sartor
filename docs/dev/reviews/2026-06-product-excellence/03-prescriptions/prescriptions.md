---
status: review-artifact
evidence_sha: c6e0437
graduation: none (action layer; feeds RELEASE_ARC via normal dev branches)
---

# Master Prescription Set — 2026-06 product-excellence review

> The action layer. Every actionable CONFIRMED or WEAKENED finding in the
> [findings register](../02-assessment/findings-register.md) becomes a
> prescription here; KEEP/BOOST findings become affirm-and-protect guard
> notes; the one DEBUFF becomes a correction. Severity anchor: the SIGNED
> [Product Charter](../00-interview/product-charter.md). Evidence pinned at
> `c6e0437`; WEAKENED findings are carried with the REVISED claim from the
> [verification log](../02-assessment/verification-log.md), never the
> original overstatement.
>
> **Soft-commitments posture (P-3/D-4/E-1).** Where a fix could be a
> human-promise SLA or a recurring manual-audit obligation, the
> prescription prefers a machine-enforced gate or a one-time bounded pass.
> No prescription here proposes a recurring human-labor commitment as a
> hard gate.
>
> **The review is witness-only** — it cannot edit `RELEASE_ARC.md`. Each
> prescription names exactly ONE landing spot; a normal dev session applies
> it. NOTE: main has moved past the pin (Sprint 6.4 + 6.6 landed); landings
> are stated against the arc as it stood at `c6e0437`. Phase 5 reconciles
> drift.

## Panel method (how the final band was set)

Each prescription's **Band** column is the reconciled output of a
three-judge panel. The judges band against three independent lenses:

- **Release-Risk** — will this land safely before its tag without
  destabilizing in-flight sprints? Weighted by the S-1 fear ordering
  (PII/egress leak first; amateurish-miss visible to an A-4 reader
  second; unusable third). A band is too LAX if it lets an S-1-class or
  signed-charter violation reach the v1.1.0 public tag; too AGGRESSIVE if
  it crowds a doc/refactor sprint and risks the tag's stability.
- **Portfolio-Mastery** — does it earn the A-4 "whoa, this is robust"
  reaction and protect the three exhibits (eval/tuning loop, grounding
  performance, wiki/memory + docs-with-git)? Rewards falsifiability,
  penalizes ceremony-without-craft.
- **Governance-Durability** — does it strengthen the
  constitution/enforcement so it survives the owner stepping away?
  Rewards machine-enforced gates over human-promise SLAs; penalizes
  recurring human-labor obligations (P-3/D-4/E-1).

**Reconciliation rule.** Where all three lenses agree, that band stands.
Where the three spread **more than one band**, the prescription is marked
**CONTESTED**, the final band is set to the **most conservative
defensible** position (a charter-violation-fixing item never lands softer
than `v1.1.0-gate`), and the three lenses' positions plus a one-line
resolution rationale are recorded in a callout box beside the row.

**Panel outcome for this set.** The three lenses converged: every
prescription was banded identically by all three judges (PX-29 was banded
by Portfolio-Mastery and Governance-Durability — both `v1.0.8` — and not
separately re-banded by Release-Risk, which raised no objection to its
WS-1 home). **No prescription spread more than one band; no
disagreements were registered; there are zero CONTESTED items.** The
convergence is not an accident of leniency — it reflects that the draft
banding already mirrors the soft-commitments posture all three lenses
share: every machine-enforcement gate (PX-08, PX-20, PX-24, PX-25,
PX-26, PX-29) sits at or near its earliest feasible coupling point, and
every deferral (PX-33/34/35) is trigger-gated with the interim
explicitly NOT a recurring human SLA. Two soft directional leans were
logged but did NOT cross a band boundary and so do not move the final
bands (both noted under their rows): pulling **PX-24** and **PX-28**
(tiny, self-contained convention→machine / constitution-integrity fixes)
into the `now-v1.0.6` batch rather than the v1.0.7 governance epic; and
decoupling **PX-20** (the C-6 construction gate, the single
highest-durability item) to land earlier if WS-1 slips. The bands below
hold the draft positions; the leans are recorded so a later sequencing
decision can act on them without re-running the panel.

## Relationship to the early prescriptions (PX-01..PX-07)

Seven prescriptions were issued ahead of Phase 4 (owner-directed during
Phase 1) in [`early-prescriptions.md`](early-prescriptions.md). They are
**already issued — not renumbered, not duplicated here.** This set
continues at **PX-08** and covers everything the early seven did not. For
reference, the early seven and their source findings:

- **PX-01** — vendor Chart.js → `F-vision-05`, `F-sec-03`, `F-docs-02`.
- **PX-02** — re-wire the profile/website scrape → `F-docs-04`.
- **PX-03** — two-class egress doc enumeration → `F-sec-04`, `F-docs-01`.
- **PX-04** — per-system tool bundling + progressive install docs →
  `F-docs-06` (+ the reconcilable half of `F-docs-05`).
- **PX-05** — fix the wrong-repo disclosure channel → `F-sec-11`.
- **PX-06** — declare vendored axe MPL-2.0 → `F-sec-08`.
- **PX-07** — soften the two human SLAs to best-effort → `F-qe-rel-08`,
  `F-sec-07`.

Where a new prescription is adjacent to an early one (same surface, same
branch), it says so and flags COORDINATE.

## The two P0s

Both P0 findings are CONFIRMED and both become prescriptions here:
`F-qe-rel-02` (no machine-falsifiable egress test) → **PX-08**;
`F-qe-rel-01` (UX/a11y/PDF tier silently skips in CI) → **PX-25**. PX-08 is
banded to v1.0.6 (it is the gate that keeps PX-01's vendoring honest);
PX-25 is the v1.1.0 fresh-clone gate.

---

## Prescription table (sorted by band, then leverage)

| PX-id | Title | Finding refs | Disposition of source | Landing | Band | Gist |
|---|---|---|---|---|---|---|
| PX-08 | Commit a network-egress falsifiability test | F-qe-rel-02 (P0), F-sec-01 (P1) | CONFIRMED ×2 | new-branch: `test/egress-falsifiability` @ v1.0.6 (after PX-01) | now-v1.0.6 | A pytest-socket / allowlist test that fails on any destination outside the two sanctioned classes. |
| PX-09 | Reconcile the no-invention absolutes to C-0 mechanism language | F-vision-02, F-docs-03 | CONFIRMED ×2 | new-branch: `docs/c0-claims-discipline` @ v1.0.6 doc batch | now-v1.0.6 | Reword "the LLM cannot invent facts" / "No invention, ever" across vision/overview/llms.txt/system-model to mechanism-and-effort. |
| PX-10 | Correct stale v1.0.8 blast-radius numbers in RELEASE_ARC | F-arch-02 | CONFIRMED | existing-branch: `chore/version-bump-v1.0.6` (doc pass) — COORDINATE | now-v1.0.6 | Update the 6290-LOC/75-route/67-test figures to actual 6992/78/24 so the v1.0.8 epic isn't argued on ~2.8x-overstated coupling. |
| PX-11 | Reconcile shipped outcome funnel vs PRODUCT_SHAPE "(Future v2)" | F-vision-03 | CONFIRMED | existing-branch: Sprint 6.6 (B.8) — COORDINATE | now-v1.0.6 | Update the six "(Future v2)" refs to "shipped"; the sent_at/outcome_at/status=interview chain is live. |
| PX-12 | Reschedule the Corpus-Item ladder in vision.md Learnings | F-vision-06 | CONFIRMED (P2) | existing-branch: Sprint 6.6 (B.4/B.5) — COORDINATE | now-v1.0.6 | Align vision.md:222-229 "v1.1/v1.2" with the PRODUCT_SHAPE superseded-banner → v1.0.6 disposition. |
| PX-13 | Affirm + guard the eval-quality regression gate | F-qe-rel-05 | KEEP/CONFIRMED | new-branch: `test/eval-gate-guard` @ v1.0.6 (rides PX-08) | now-v1.0.6 | Do-not-regress note + a meta-test that exit-code 2 still fails eval-smoke; record CI covers grounding-rubric-only ×3 fixtures. |
| PX-14 | Fix GROUNDING_METRIC.md four-part-union overstatement | F-eval-04 | KEEP/WEAKENED | existing-branch: `docs/c0-claims-discipline` (PX-09) — COORDINATE | now-v1.0.6 | Correct the doc to the THREE-source metric union (primary+supplementals+clarifications); typed edits are prompt-side, not a source-union element. |
| PX-15 | Lay metrics legend on groundedness + tuning panes | F-expa11y-04, F-eval-03 | CONFIRMED ×2 | existing-branch: Sprint 6.5 (education sweep) — COORDINATE | v1.0.7 | Author a plain-language legend for the dev-register diagnostics labels (S-3, the owner's self-named weakest area; M-2 criterion). |
| PX-16 | Guide the cold no-API-key first run instead of 500-dumping | F-expa11y-02 | CONFIRMED | existing-branch: Sprint 6.5 (KW3 onboarding) — COORDINATE | v1.0.7 | Detect empty/missing key before any LLM call and/or add an `except AuthenticationError` arm; replace the bare 500/traceback with guidance. |
| PX-17 | Instrument the AL-1 suggested-bullet count for falsifiability | F-eval-01 | CONFIRMED | existing-branch: `eval/grounding-calibration` (PV-2) @ v1.0.7 — COORDINATE | v1.0.7 | Add the compose-recommendation bullet count (minKeep/maxKeep/ratio) to ride-along metrics so over-suppression is visible in data. |
| PX-18 | Author ACCESSIBILITY.md honest-status page | F-expa11y-03 | CONFIRMED | existing-branch: v1.0.7 pre-public hardening — COORDINATE | v1.0.7 | A status page (no conformance claim, no recurring-audit promise) per E-2; machine-checked taxonomy vs known gaps. |
| PX-19 | Pin the loopback bind by construction | F-sec-02 | CONFIRMED | existing-branch: v1.0.8 blueprint split (`refactor/app-blueprints-*`) — COORDINATE | v1.0.8 | Set `host="127.0.0.1"` explicitly at the run/bind site + a test; note SERVER_NAME as a third silent-flip vector. |
| PX-20 | Commit the C-6 deterministic-LLM boundary gate | F-arch-01, F-qe-rel-04 | CONFIRMED ×2 | existing-branch: v1.0.8 WS-1 — COORDINATE | v1.0.8 | A ~15-line AST test or import-linter contract that fails when a deterministic module imports analyzer/anthropic. |
| PX-21 | Extend route-security-lint beyond app.py when blueprints land | F-arch-03 (WEAKENED→P2/P3), F-sec-05 (KEEP) | WEAKENED + KEEP | existing-branch: v1.0.8 WS-1 — COORDINATE | v1.0.8 | Widen the hook matcher past `app.py`/`@app.route`; scope SECURITY.md:211 to app.py-resident routes; add route-level traversal tests + close the `_load_config`/`_save_config` secure_filename gap. |
| PX-22 | Add a History API entry so Back doesn't discard wizard state | F-expa11y-06 | WATCH/CONFIRMED-adjacent | existing-branch: v1.0.8 back-nav item — COORDINATE | v1.0.8 | pushState/popstate so browser Back navigates wizard steps instead of exiting the SPA (E-2 back/history line). |
| PX-23 | Codify the parallel-session isolation model as governance | F-gov-02, F-gov-03 | CONFIRMED ×2 | existing-branch: v1.0.7 governance extraction — COORDINATE | v1.0.7 | Author per-session/worktree scope rules (plan marker + cleanup are global today); retire the "one branch per session" serial framing. |
| PX-24 | Close the block-merge-to-main common-path seam | F-gov-01 | CONFIRMED | existing-branch: v1.0.7 governance extraction — COORDINATE | v1.0.7 | Detect HEAD==main via `git rev-parse --abbrev-ref HEAD` so the routine feature-merge direction is also gated (witness-class fix, machine-enforced). |
| PX-25 | Run the UX/a11y/PDF tier in CI as a required check | F-qe-rel-01 (P0), F-expa11y-01, F-expa11y-05 | CONFIRMED ×2 + FIX | existing-branch: v1.1.0 fresh-clone (`release/fresh-clone-v1-1-0`) — COORDINATE | v1.1.0-gate | A dedicated CI job that installs Chromium and runs `pytest -m ux`; add reflow/tab-order/history axe assertions. |
| PX-26 | Land the E-2 machine badge set | F-qe-rel-03, F-sec-09 | CONFIRMED + WATCH | new-branch: `chore/e2-machine-badges` @ v1.1.0 (before `chore/release-v1.1.0`) | v1.1.0-gate | Dependabot + lockfile, OpenSSF Scorecard, REUSE/SPDX (+ axe MPL-2.0 machine-readable), the egress test as a badge, one-time PVR setup. |
| PX-27 | Name the charter-admitted audiences in public identity | F-vision-01 (WEAKENED), F-vision-04, F-vision-07, F-vision-10 | WEAKENED + CONFIRMED ×2 + WATCH | existing-branch: v1.0.7 charter extraction — COORDINATE | v1.0.7 | Tier vision.md constraints by enforceability (six sub-sections; drop the "C-8" trace); demote single-tenant-as-value; name the ATS escape hatch + the A-2/A-3/A-5 audiences. |
| PX-28 | Correct the check-plan-approved hand-create-the-marker hint | F-gov-07 | DEBUFF | existing-branch: v1.0.7 governance extraction — COORDINATE | v1.0.7 | Remove the hint that contradicts the never-hand-create-the-marker rule. |
| PX-29 | Affirm + protect the security/PII KEEP ledger through the splits | F-sec-05, F-sec-06, F-expa11y-07, F-expa11y-08, F-gov-04, F-gov-05 | KEEP ×6 | new-branch: `test/keep-ledger-guards` @ v1.0.8 (rides WS-1) | v1.0.8 | Convert the load-bearing affirmations (route containment, zero-PII clone, bullet-reorder, live-region, hook count) into do-not-regress guard tests so the blueprint split + public tag can't quietly weaken them. |
| PX-30 | Cover the corpus-mode generate path in the eval suite | F-eval-10 | FIX (P2) | existing-branch: `eval/live-shakedown-labels` (PV-1) @ v1.0.7 — COORDINATE | v1.0.7 | Add a corpus-mode (DB-backed) fixture so CI exercises the path the legacy synthetic suite skips. |
| PX-31 | Reconcile the inconsistent Chromium classification across docs | F-docs-05 (WEAKENED→~P3) | WEAKENED | existing-branch: Sprint 6.5 install docs (rides PX-04) — COORDINATE | v1.0.7 | Gate the Chromium step behind "if you want PDF output"; reconcile D-6 shorthand vs the wiki/README basic-tool classification (DOCX + preview are Chromium-free). |
| PX-32 | Affirm the eval/governance KEEP+BOOST design ledger | F-eval-05, F-eval-06, F-eval-07 (BOOST), F-eval-08, F-eval-09, F-gov-06, F-gov-08, F-gov-09, F-gov-10, F-docs-07, F-docs-08, F-docs-09 | KEEP ×11 + BOOST ×1 | new-branch: `docs/keep-ledger-affirmations` @ v1.0.7 | v1.0.7 | One affirmation pass: record the cost/consent-gating (BOOST), non-polluting A/B, sentinel-honesty, @import safety, and the governance→assistant design-home gap (F-gov-10) as do-not-regress notes; add the F-gov-08 W-4 maturity-signal as a deferred design item. |
| PX-33 | WS-4b cold-ingest grounding + rot-detection at module scale | F-vision-08 (KEEP), F-arch-09 (WATCH), F-docs-08 (KEEP), F-docs-10 (WATCH) | KEEP ×2 + WATCH ×2 | existing-branch: WS-4b (wiki cold-ingest of code) — COORDINATE | post-public | When WS-4b runs the code cold-ingest, exercise grounding at module scale + fire the sha→HEAD rot-detection; seed overview.md from system-model.md. |
| PX-34 | Add an automated migration upgrade/downgrade test on a data-bearing DB | F-arch-08, F-qe-rel-09 | WATCH ×2 | new-branch: `test/migration-data-bearing` @ post-public (1.1.x) — trigger: first migration touching a populated table | post-public | Replace the fresh-only / table-count migration test with a populated-DB upgrade→downgrade round-trip. |
| PX-35 | Add an automated perf-regression gate | F-qe-rel-06 | WATCH | defer: v1.1.x (trigger: a perf-sensitive change lands without the manual PR checkbox catching a regression) | post-public | Promote the PERFORMANCE_HISTORY telemetry + manual checklist into a machine gate; until then the manual checkbox stands (no recurring human SLA). |
| PX-36 | Tighten the all-LLM-in-analyzer prompt-locus precision | F-arch-05 | WATCH (P3) | reject (rationale below) | reject | The prompt-template-locus looseness is convention drift with no defect; PX-20's boundary gate + AGENTS.md already cover the load-bearing call boundary. |

---

## now-v1.0.6 band

Small, dependency-light fixes that ride the v1.0.6 doc batch / fix branches
already in flight. These keep PX-01..07 honest and clear the
docs-accuracy and claims-discipline debt before it propagates.

- **PX-08 — egress falsifiability test.** The missing gate behind both P0s
  (`F-qe-rel-02`) and `F-sec-01`. A `pytest-socket`-style test (disable
  sockets, allowlist the two sanctioned destination classes) that would
  have caught PX-01's CDN fetch and keeps C-2 machine-verifiable after
  vendoring. Lands on its own branch after PX-01 so the allowlist asserts
  the post-vendor reality. This is the construction C-0 prescribes for the
  "leave the machine, ever" categorical.
- **PX-09 — C-0 claims discipline (docs).** `F-vision-02` + `F-docs-03`:
  the absolute "the LLM cannot invent facts" / "No invention, ever."
  register across vision.md:50/:151, overview.md:26, llms.txt:4,
  system-model.md is a signed-C-0 violation on the highest-audience
  surfaces. Reword to mechanism-and-effort. (Owner recanted the exact
  strings, R2-4.2/R2-4.4.)
- **PX-10 — stale blast-radius numbers.** `F-arch-02`: a docs-accuracy P1
  — the v1.0.8 epic's coupling rationale overstates by ~2.8x. Correct to
  6992/78/24 in the same doc pass as the version bump. COORDINATE: lands
  wherever the v1.0.6 RELEASE_ARC doc edits happen.
  - **Resolved on `chore/version-bump-v1.0.6` (2026-06-15).** Implemented as
    **current-accurate `8251 LOC / 93 routes / 32 test-files`**, not the
    review-era `6992/78/24` — those targets were exact only at the review
    commit `93ecc95` and had since drifted (B.4/B.5/PX-02 added route
    families + LOC), so writing them would have re-introduced the very
    inaccuracy PX-10 exists to fix. Re-verified against HEAD (`wc -l app.py`
    = 8251; `grep -c @app.route app.py` = 93; 32 test files import `app`).
    Owner-approved deviation from the literal figures; the doc-accuracy
    intent (don't argue the v1.0.8 epic on stale coupling) is preserved.
- **PX-11 / PX-12 — Corpus-Item + outcome-funnel doc reconciliation.**
  `F-vision-03` (shipped funnel still framed "(Future v2)" in six places)
  and `F-vision-06` (vision.md Learnings drift). COORDINATE with Sprint 6.6
  (B.4/B.5/B.8), which is the surface that ships the reconciled state.
- **PX-13 — affirm the eval regression gate.** `F-qe-rel-05` KEEP: a real
  machine gate that forces exit-2 on a grounding drop near/past 0.5 vs the
  committed baseline. Add a do-not-regress note + a cheap meta-test;
  record the scope (CI = grounding-rubric-only across 3 synthetic
  fixtures, label-gated).
- **PX-14 — GROUNDING_METRIC.md union correction.** `F-eval-04` WEAKENED:
  affirm that the metric distinguishes asserted-beyond from
  synthesized-within (C-3), but fix the doc's four-part-union claim to the
  actual THREE sources so the AFFIRM doesn't lock in an inaccurate claim.
  Rides PX-09's doc branch.

## v1.0.7 band

Education/explainability, hardening, governance extraction, and grounding
calibration — the surfaces the charter ties to M-2 explainability and S-3
(the owner's self-named weakest area).

- **PX-15 — lay metrics legend.** `F-expa11y-04` + `F-eval-03`: same
  diagnostics surface from two domains; S-3 + M-2 v1.0.7 criterion. Sprint
  6.5 education sweep authors it.
- **PX-16 — cold no-key first-run guidance.** `F-expa11y-02`: today an
  empty key surfaces a bare 500/traceback mid-analyze (non-stream) or a
  generic 500 (stream). Detect the empty key pre-call and guide. Sprint 6.5
  KW3 onboarding is the home.
- **PX-17 — AL-1 instrumentation.** `F-eval-01`: the over-suppression
  signal is unfalsifiable from data because the compose-recommendation
  bullet count never rides along. Add it under PV-2 calibration. (Note: the
  signal is the recommendation count, not the opt-in final-resume
  bullet_count — slightly more than trivial reuse.)
- **PX-18 — ACCESSIBILITY.md.** `F-expa11y-03`: no honest-status page
  exists at the pin and it is scheduled nowhere in the arc. Author it under
  v1.0.7 pre-public hardening, per E-2 (status page, not conformance
  claim; no recurring-audit promise).
- **PX-23 / PX-24 / PX-28 — governance.** `F-gov-02`/`F-gov-03` (codify the
  parallel-session isolation model; retire the serial framing — the
  extraction epic only relocates existing rules, it does not author this),
  `F-gov-01` (close the block-merge common-path seam, machine-enforced),
  `F-gov-07` DEBUFF (drop the hand-create-the-marker hint). All ride the
  v1.0.7 governance-extraction epic.
  - *Panel lean (does not move the band):* the Governance-Durability lens
    would happily see **PX-24** (detect `HEAD==main`, convert a
    convention-only gate to machine-enforced on the dominant merge
    direction) and **PX-28** (DEBUFF the hand-create-the-marker hint) ride
    the `now-v1.0.6` batch — both are tiny and self-contained. All three
    lenses agree bundling them with the governance extraction is a
    legitimate sequencing call, so the band stays `v1.0.7`; the lean is
    logged for a later sequencing decision.
- **PX-27 — public identity + constraint tiering.** `F-vision-01`
  (WEAKENED: six sub-sections, drop the "C-8" trace), `F-vision-04`
  (demote single-tenant-as-value, keep the single-unauthenticated-user
  threat model), `F-vision-07` (name the ATS escape hatch), `F-vision-10`
  (name the A-2/A-3/A-5 audiences). Charter extraction to
  `docs/governance/charter.md` is the natural home.
- **PX-30 — corpus-mode eval coverage.** `F-eval-10`: the committed
  synthetic suite exercises only the legacy generate path. Add a DB-backed
  corpus-mode fixture under PV-1. (Per memory: corpus-mode prompt changes
  aren't exercised by `--suite synthetic`; this closes that gap.)
- **PX-31 — Chromium doc classification.** `F-docs-05` WEAKENED (~P3):
  reconcile D-6 shorthand vs the wiki/README basic-tool classification and
  gate the install step behind "if you want PDF output." Rides PX-04's
  Sprint 6.5 install-docs work.
- **PX-32 — eval/governance affirmation ledger.** The KEEP/BOOST design
  surfaces (`F-eval-05`..`09`, `F-gov-06`/`08`/`09`/`10`,
  `F-docs-07`/`08`/`09`): one pass that records do-not-regress notes,
  affirms the cost/consent gating BOOST (`F-eval-07`), and logs the two
  open design items — the governance→assistant design home (`F-gov-10`,
  which the v1.0.7 assistant needs) and the W-4 maturity signal for the
  four un-metriced incubants (`F-gov-08`).

## v1.0.8 band

The blueprint split (WS-1) — the right window to install the
construction-level gates that hold by convention today, and to protect the
KEEP ledger through the refactor.

- **PX-19 — pin the loopback bind.** `F-sec-02`: the blueprint split moves
  `main()`/the bind site — pin `host="127.0.0.1"` then, with a test, and
  neutralize the SERVER_NAME flip vector.
- **PX-20 — C-6 boundary gate.** `F-arch-01` + `F-qe-rel-04`: an AST test
  or import-linter contract so a deterministic-module LLM import fails by
  construction, not by convention. WS-1 is the named home.
  - *Panel lean (does not move the band):* the Governance-Durability lens
    names PX-20 the single highest-durability item in the set — the
    construction C-0 prescribes to back C-6's "Inviolable" clause, which
    holds only by convention at the pin. It is correctly coupled to WS-1,
    but if WS-1 slips this is the one item all three lenses would most want
    decoupled and pulled forward. The band stays `v1.0.8` (coupled to the
    bind/boundary stress of the split); the lean is logged.
- **PX-21 — route-security-lint + containment coverage.** `F-arch-03`
  WEAKENED (latent until blueprints land) + `F-sec-05` KEEP: widen the hook
  past `app.py`, scope SECURITY.md:211, add route-level traversal tests,
  close the `_load_config`/`_save_config` secure_filename gap.
- **PX-22 — back-nav History API.** `F-expa11y-06`: already a named v1.0.8
  back-nav item; pushState/popstate so Back navigates wizard steps.
- **PX-29 — protect the KEEP ledger through the split.** `F-sec-05`,
  `F-sec-06`, `F-expa11y-07`, `F-expa11y-08`, `F-gov-04`, `F-gov-05`:
  guard tests for the load-bearing affirmations that the split (and the
  v1.1.0 tag) must not quietly weaken — several (live-region, modal-trap,
  containment density) are affirmed by static reading only and have no test
  today (see `F-expa11y-08`/`F-expa11y-09`).

## v1.1.0-gate band

The two items the public tag genuinely gates on — the CI honesty gap and
the machine-badge package.

- **PX-25 — UX/a11y/PDF tier in CI (P0).** `F-qe-rel-01` + `F-expa11y-01` +
  `F-expa11y-05`: a dedicated CI job installs Chromium and runs
  `pytest -m ux` as a required check, closing the "machine-checked in CI,
  free forever" gap; extend the axe scope with reflow/tab-order/history
  assertions. Rides the fresh-clone release branch.
- **PX-26 — E-2 machine badges.** `F-qe-rel-03` + `F-sec-09`: Dependabot +
  lockfile, OpenSSF Scorecard, REUSE/SPDX (folding in PX-06's axe MPL-2.0
  as the machine-readable form), the PX-08 egress test as a falsifiability
  badge, and one-time Private Vulnerability Reporting setup. All
  machine-run or one-time — no recurring human-promise badge (E-1/D-4).

## post-public band

Deferrals with explicit promotion triggers — no recurring human-labor
obligation among them.

- **PX-33 — WS-4b cold-ingest at module scale.** `F-vision-08`,
  `F-arch-09`, `F-docs-08`, `F-docs-10`: when WS-4b runs the code
  cold-ingest, exercise grounding at module scale and fire the never-yet-
  fired sha→HEAD rot-detection; seed overview.md from system-model.md.
  Trigger: WS-4b begins (after Sprint 6.6, route-churn settled).
- **PX-34 — data-bearing migration test.** `F-arch-08` + `F-qe-rel-09`: the
  migration test is fresh-only / table-count today. Trigger: the first
  migration touching a populated table; add a populated-DB
  upgrade→downgrade round-trip then.
- **PX-35 — automated perf gate.** `F-qe-rel-06`: promote the
  PERFORMANCE_HISTORY telemetry + manual PR checkbox into a machine gate.
  Trigger: a perf-sensitive change lands that the manual checkbox misses.
  Until then the manual checkbox stands — deliberately NOT a recurring
  human SLA.

## reject band

- **PX-36 — all-LLM-in-analyzer prompt-locus precision.** `F-arch-05`
  WATCH/P3: the "precise for call code, looser for prompts" observation is
  convention drift with no realized defect — the load-bearing call boundary
  is covered by PX-20's gate and AGENTS.md. Rejected as a standalone
  prescription; if a prompt template ever migrates out of the documented
  loci, PX-20's gate scope is the place to extend, not a new branch.

---

## Coverage check

Every actionable register row is dispositioned. CONFIRMED/WEAKENED FIX
findings each map to a PX (this set or PX-01..07); KEEP/BOOST findings are
either affirmed in PX-13/PX-29/PX-32 guard-and-protect prescriptions or
ride a fix that touches the same surface; the one DEBUFF (`F-gov-07`) is
PX-28; the WATCH findings are banded (in-scope WATCHes ride a fix; the rest
defer with triggers). No prescription sources from a REFUTED finding (there
are none) or from a verdict-trimmed sub-claim — WEAKENED findings
(`F-arch-03`, `F-vision-01`, `F-expa11y-09`, `F-qe-rel-07`, `F-eval-04`,
`F-docs-05`) are carried with their revised claims.

`F-qe-rel-07` (WEAKENED) is intentionally NOT given a standalone PX: per its
revised claim it is already a named, sequenced, release-blocking task set
(PV-1/PV-2/PV-3 → v1.0.7 + the permanent `--suite real` set + M-2's
ten-real-applications gate); `F-eval-02` (the real-loop calibration it
depends on) is likewise the body of the PV-1/PV-2 work that PX-17/PX-30
ride. They are tracked, not re-prescribed — re-issuing them as new
prescriptions would manufacture duplicate scheduling against work the arc
already owns.

---

## Panel reconciliation — final band tally

29 prescriptions (PX-08..PX-36), reconciled by the three-judge panel
([panel method](#panel-method-how-the-final-band-was-set)). The three
lenses converged on every row; **zero CONTESTED items** (no spread
exceeded one band, no disagreements registered). Final bands:

| Band | Count | PX-ids |
|---|---|---|
| now-v1.0.6 | 7 | PX-08, PX-09, PX-10, PX-11, PX-12, PX-13, PX-14 |
| v1.0.7 | 11 | PX-15, PX-16, PX-17, PX-18, PX-23, PX-24, PX-27, PX-28, PX-30, PX-31, PX-32 |
| v1.0.8 | 5 | PX-19, PX-20, PX-21, PX-22, PX-29 |
| v1.1.0-gate | 2 | PX-25, PX-26 |
| post-public | 3 | PX-33, PX-34, PX-35 |
| reject | 1 | PX-36 |
| **Total** | **29** | |

**Highest-leverage now-v1.0.6 items (owner checkpoint).** PX-08 commits
the network-egress falsifiability test — the machine gate behind both P0s
(`F-qe-rel-02`/`F-sec-01`) and the #1 S-1 fear; it turns C-2's
"leave the machine, ever" prose into a by-construction check and keeps
the vendoring honest. PX-09 reconciles the no-invention absolutes
("the LLM cannot invent facts" / "No invention, ever.") to C-0
mechanism-and-effort language on the highest-audience A-4 surfaces —
docs-only, but a live signed-charter violation the owner already recanted.

**The v1.1.0-gate items.** PX-25 runs the UX/a11y/PDF tier in CI as a
required check (P0 `F-qe-rel-01`), closing the "machine-checked in CI,
free forever" gap that is maintainer-local at the pin. PX-26 lands the
E-2 machine badge set (Dependabot + lockfile, OpenSSF Scorecard,
REUSE/SPDX, the PX-08 egress test as a badge, one-time PVR) — all
machine-run or one-time, no recurring human-promise badge.

**Soft leans logged but not band-moving.** PX-24 + PX-28 (tiny
convention→machine / constitution-integrity governance fixes) could ride
`now-v1.0.6` rather than the v1.0.7 governance epic; PX-20 (the C-6
construction gate, the single highest-durability item) would be the first
to decouple and pull earlier if WS-1 slips. Recorded under their rows for
a later sequencing decision; the panel left the bands at the draft
positions.

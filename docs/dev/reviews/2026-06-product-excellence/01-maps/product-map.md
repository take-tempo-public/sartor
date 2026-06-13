---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Product map — callback.

> The terrain for the 2026-06 product-excellence review. Built read-only from
> git history (399 commits, init `ce150e0` 2026-04-10 → pin `c6e0437`
> 2026-06-12), `CHANGELOG.md`, `docs/dev/RELEASE_ARC.md` (authoritative for
> sequencing), `docs/PRODUCT_SHAPE.md` (v1→v2 ladder), and
> `docs/dev/excellence-walk/README.md`. Severity anchor: the signed charter
> (`00-interview/product-charter.md`). Honors charter **C-0** — categorical
> claims only where deterministic; mechanisms-and-effort elsewhere.

---

## 1. Timeline — the eras

Commit counts are `git rev-list` ranges between tags (to the pin for the
in-flight era). Dates are commit dates.

| Era | Span | Commits | Theme |
|---|---|---|---|
| **Genesis** | 2026-04-10 → 05-06 (`ce150e0`..`v0.2.0`) | 48 | Multi-resume source, source-selection whitelist, eval-docs + model review. The pre-product prototype. |
| **The v1.0.0/v1.0.1 build-out** | 05-06 → 05-28 (`v0.2.0`..`v1.0.1`) | 162 | The single largest era — the corpus/wizard product takes shape; the UI redesign largely lands; the security gate, deterministic/LLM boundary, and `context_set` contract solidify. v1.0.1 = "solid app," tagged `49f2ac9`. |
| **Eval apparatus (v1.0.2)** | 05-28 → 05-30 (`v1.0.1`..`v1.0.2`) | 31 | Pydantic response models, schema_v3 baseline, anchor/exploration split, Promptfoo + PR gate, callback rubric + deterministic metrics, applications tracker, Pareto dashboard. Tagged `2398f4e`. |
| **R1 Phase 2 (v1.0.3)** | 05-30 → 06-02 (`v1.0.2`..`v1.0.3`) | 26 | Analyze quality recovery (typed `hidden_qualities`, parse-time `context_probe`) then the two-pass split for speed (≤72s) via `analyze-split-cache-reclaim`. Tagged `59b6d9c`. |
| **Eval tuning loop (v1.0.4)** | 06-02 (`v1.0.3`..`v1.0.4`) | 19 | Prompt-override primitive, corpus-seed export, bootstrap engine, annotation contract, `/tune-from-annotations`. Internal/dev tooling. Tagged `072e290`. |
| **UI/UX redesign + console (v1.0.5)** | 06-02 → 06-07 (`v1.0.4`..`v1.0.5`) | 50 | WYSIWYG, Step-6 redesign, cover-letter formats, prior-app resume, bullet drag-reorder, Playwright UX suite, template pagination, L0 grounding metric, the tabbed diagnostics+tuning+annotation console + the "finish the faceplate" browser-driven loop. Establishes the `cb-*` design system. Tagged `2e3e110`. |
| **Walkthrough polish + knowledge substrate (v1.0.6, IN FLIGHT)** | 06-07 → 06-12 (`v1.0.5`..`c6e0437`) | 57 | E2E-walkthrough-driven UX sprints (6.0–6.6), the WS-4a wiki substrate (`docs/system-model.md` + `docs/wiki/` skeleton both landed), corpus-item completers B.4/B.5, B.8 Part 1 outcome capture. **Not yet tagged.** |

Activity is bursty and intense: peak days reach 39 commits (05-24), 31
(05-26), 29 (05-28) — consistent with multi-altitude agent parallelism (W-1),
not a single serial author.

### Version milestones

| Tag | Date | Commit | Theme | Public? |
|---|---|---|---|---|
| v1.0.1 | 2026-05-28 | `49f2ac9` | Solid app | No |
| v1.0.2 | 2026-05-30 | `2398f4e` | Eval apparatus | No |
| v1.0.3 | 2026-06-02 | `59b6d9c` | R1 Phase 2 (analyze split, ≤72s) | No |
| v1.0.4 | 2026-06-02 | `072e290` | Eval tuning loop | No |
| v1.0.5 | 2026-06-07 | `2e3e110` | UI/UX redesign + console | No (internal) |
| v1.0.6 | — | *(in flight, opens at `1b97e82`-era sprints)* | Walkthrough polish + wiki substrate + corpus completion | No (internal) |

**Versioning model (RELEASE_ARC, 2026-06-08):** patch digit = a bounded epic
of one-branch-per-session sprints; minor digit = a significant/public tag
marker. **v1.1.0 is the public release, user-owned** — completeness and polish
gate the tag, not a clock.

---

## 2. Current position — the pin

The review is pinned at **`c6e0437`** (2026-06-12, "Merge
docs/schedule-open-items-clean") — the last product/planning commit before the
review branch was cut. The five review-only commits (`17690f7`..`f78fc5f`,
charter scaffold → SIGNED) sit on top in `review/2026-06-product-excellence`;
they touch only `review/` and do not move the product.

**Main moves in parallel.** `c6e0437` is the worktree pin, but `main` continues
to advance during the review (the `feat/experience-summary-item` branch — B.4 —
already exists locally, mid-flight). Any divergence between what this map
describes and the live `main` is **deliberately deferred to review Phase 5
(drift reconciliation)**; the map is true as of the pinned SHA.

v1.0.6 is mid-epic at the pin: Sprints 6.0 (kickoff harvest), 6.1 (wizard
correctness — all rows resolved), 6.2 (diagnostics charts), and 6.3 (a11y gate
+ contrast + required-field/dropdown) have merged; Sprints 6.4 (IA/onboarding),
6.5 (in-app education), 6.6 (corpus completers B.4/B.5), and WS-4b (code
cold-ingest) remain.

---

## 3. The road ahead

### v1.0.6 remaining (charter deps in **bold**)
- **Sprint 6.4** — logo-home route; corpus-first tab order + smart landing
  (Kickoff KW1). Addresses **S-3** discoverability.
- **Sprint 6.6** — `feat/experience-summary-item` (B.4) + `feat/skill-group-item`
  (B.5): finish the unified Corpus-Item vision. **PRODUCT_SHAPE §7** ladder; in
  flight at the pin.
- **WS-4b** — `wiki/cold-ingest-code` (after 6.6, so it captures B.4/B.5 cards),
  with the `audience:` tag convention authored once. Feeds **A-4** exhibit #3
  (wiki/memory/docs system) and the v1.0.7 assistant.
- **Sprint 6.5** — the in-app education sweep (help primitive + per-tab/per-panel
  summaries + install guide), authored *into* the wiki. Directly targets the
  owner's self-named furthest-below-bar area (**S-3**: explain grounding/tuning/
  clarify through the UI + diagnostics) and **M-2** explainability artifacts.
- **C-2 v1.0.6 fixes (ruled 2026-06-12, not yet in arc sprint text):** PX-01
  vendor Chart.js (CDN violation at `dashboard/templates/dashboard.html:15` —
  note v1.0.5 only added SRI, did not vendor), PX-02 re-wire the dead
  profile/website scrape, PX-03 correct `jd_url` docs to the two-class egress
  enumeration. These are the **S-1** "glaring miss / PII-adjacent" prescriptions.

### v1.0.7 — "the app knows itself"
- Governance extraction (moved here 2026-06-12): lift the scattered hard rules
  into one canonical home (`docs/governance/charter.md` is the charter's own
  graduation target) **preserving agent rule-access via `@import`** — directly
  serves **W-2** (governance as constitution-building) and is the charter's own
  graduation vehicle.
- The self-documenting wiki loop (Haiku, bounded triggers) + the doc-grounded
  **assistant** (Haiku, reuses user's key) — **P-3** ("a project that sources and
  describes every part of itself") and **A-2/A-4** (the user→power-user→dev
  continuum; exhibit #3).
- Pre-public hardening: PV-1 live-shakedown labels, PV-2 grounding calibration
  (closes the deferred "B" metric), PV-3 cover-letter opener tune. PV-1/PV-2
  consume the **M-2** real-corpus + annotation labels the v1.0.6 walkthrough
  produces; PV-2 advances **C-3**/lead **AL-1** (grounding-vs-usefulness balance).

### v1.0.8 — monolith → blueprints (WS-1)
- Decompose the 6,290-LOC / 75-route `app.py` into Flask blueprints; absorb the
  route-return type scan (PV-4). Pure refactor, no behavior change. **W-4**
  (modularize-in-place until extraction warrants) and the **A-4** "this is
  robust" reaction; ships public on clean blueprints.

### v1.1.0 — public release (user-owned tag)
- Criteria: visual assets; fresh-clone < 5 min; GitHub live; type scan verified;
  **user judges it showcase-ready.** Gated by **M-2**'s written self-imposed
  evidence (≥10 real applications across the matrix; tuning loop exercised
  end-to-end; ≥1 interview weighed-not-gated; the two first-run time bars;
  explainability artifacts shipped). **T-D**: the M-2 bar exists precisely
  because "functionally complete at v1.1.0" rides on machinery never yet
  exercised on real data.

### Post-public lanes (1.1.x epics)
- 1.1.1 candidates: paged.js engine replacement (B.13, design-spike); **local +
  alternative LLM providers** (the **D-2** planned amendment — provider-agnostic
  + local models, with C-2's wording amended by ceremony); B.8 Part 2
  outcome-weighted recommend.
- Recurring: WS-2-full strict-typing ratchet + typed `context_set`; WS-3 periodic
  test-suite engineering pass.
- **W-3 agent-station** (build starts the week after 2026-06-12) runs post-public
  ops; **v1.1.0's GitHub integration is its canary project** — set-up flow,
  template containers, CI build-out, on a couple-hours/week owner budget.

---

## 4. Pattern inventory (CANDIDATES — Phase 3 verifies)

> Prescriptive core. Each line carries one evidence pointer. **All are
> candidates** — Phase 3 confirms, edits, or strikes before any rubric/governance
> graduation. They are not findings yet.

### BOOST candidates — practices working well

1. **Design-docs-precede-code.** `GROUNDING_METRIC.md` and `memory-architecture.md`
   merged as design artifacts *before* their feature branches
   (`2c805bf`, `87267d8`); RELEASE_ARC mandates a `design/*` session first for
   self-documenting-loop and app-blueprints. Reduces churn on hard levers.
2. **Walkthrough-driven sprints.** v1.0.5 produced 24 findings → topical sprints;
   v1.0.6 opens with an E2E kickoff harvesting KW1–KW13 (`docs/sprint6-walkthrough-findings`),
   each finding tracing to a named branch in RELEASE_ARC §4.5. Real use drives
   the backlog.
3. **PROMPT_VERSION discipline.** Every prompt change bumps the version in the
   same commit (`fix/generate-date-grounding` → `2026-06-10.1`; `feat/compose-add-title`
   → `2026-06-11.1`) and logs `TUNING_LOG.md`; UI-only branches loudly state "no
   PROMPT_VERSION bump." Keeps eval telemetry attributable.
4. **Modularize-in-place before extraction (W-4).** `run_suite()` extracted from
   `runner.main()` byte-identical (`3a91bea`); `recall/` package form-found in the
   memory-architecture design; blueprint split deferred until a dedicated low-churn
   window. Maturity gates the breakout.
5. **Deterministic/LLM boundary held by construction (C-6).** Every CHANGELOG
   entry asserts "the persist module stays deterministic / no LLM call";
   `analyzer.py` is the sole caller. A machine-enforceable invariant, not a hope.
6. **Defect-vs-expected settled first.** Sprint 6.x rows repeatedly verify the bug
   reproduces before fixing — #8 templates "genuinely differ" (only the *count*
   was stale), #11 cost-chart "does not reproduce as stated," ~150 a11y fields
   "already clean." Avoids fixing phantom bugs.
7. **Every fix ships a regression test.** Each 6.x branch lands a dated
   `tests/ux/regression/test_YYYYMMDD_*.py` pinning the specific bug
   (`test_20260611_clarify_no_double_prompt.py`, etc.). The walkthrough findings
   become permanent guards.
8. **Audit-trail-by-default (D-5).** Each generation writes a new timestamped
   child `context_set`; the `parent_context_path` chain is the iteration audit
   trail — a durable, inspectable provenance spine.
9. **Cost/consent gating on paid surfaces.** Browser eval/tune routes are
   localhost-only with a `confirm()` cost-band gate before any paid call, and
   eager 4xx validation before spend (`/api/tune/run`, `/api/eval/run`). Respects
   the local-and-yours posture.

### DEBUFF candidates — patterns that may hurt

1. **Gates that silently skip.** `tests/ux/conftest.py:80,85` `pytest.skip`s the
   entire UX tier — including the new vendored axe a11y gate — when Chromium is
   absent, so default `pytest` stays green with a11y/UX *unchecked*. CI coverage
   of these gates is unverified from history.
2. **Doc-enumeration drift across vision/SECURITY/README.** Charter C-2(iv) rules
   `jd_url` is provenance-only yet docs imply a JD-URL fetch; bundled-template
   *count* drifted (5→4) in settings copy + `bundled_templates_LICENSE.md`
   (`fix/step4-template-copy`); the v1→v2 "version labels superseded" note
   (PRODUCT_SHAPE §7) patches a stale enumeration in place. Repeated count/list
   drift between parallel docs.
3. **Serial-session framing vs practiced parallelism.** RELEASE_ARC "Hard
   constraints" and AGENTS.md say "one branch per agent session," but peak-day
   commit bursts (39/31/29) and W-1 explicitly call the serial framing "stale."
   Docs lag the real working model.
4. **CDN/no-CDN promise drift.** The v1.0.5 console added Chart.js **SRI**
   (`6eab70b`) rather than vendoring, leaving the runtime CDN load that C-2(i)
   later ruled a confirmed no-CDN violation (PX-01). A near-miss the eval/security
   surface didn't catch until the charter audit.
5. **Dead code shipped as "working."** The profile/website scrape is dead at the
   pin (C-2(iii), PX-02) and run-row cover-letter persistence was never wired
   (`fix/run-cover-letter-persistence`). Features can present as complete while
   their write/fetch path is silently inert.
6. **Real-data machinery unexercised before its release.** `evals/fixtures/real/`
   is empty at the pin; the v1.0.4 live tuning loop "was never run" (RELEASE_ARC
   re-sequence note); grounding calibration "B" deferred for want of labels. T-D
   names this; the risk is shipping tooling validated only on synthetic fixtures.
7. **Planning-doc sprawl as load-bearing memory.** Sequencing lives across
   RELEASE_ARC + RELEASE_CHECKLIST + PRODUCT_SHAPE §10/§11 + nursery + memory
   notes, with cross-references and "moved 2026-06-12" annotations. Powerful, but
   the truth-source requires triangulation (the memory index itself flags one
   pointer STALE).
8. **Scope creep via "user-approved extension."** Several 6.x rows expand beyond
   the stated finding mid-branch (compose-add-title gained per-JD title pinning +
   a PROMPT_VERSION bump; a11y gained a design-system color change). Each is
   blessed, but the pattern widens single-session blast radius.

---

## 5. Gaps & unknowns (what history alone cannot determine)

- **Whether the CI runs the UX/a11y/eval gates.** History shows the gates exist
  and skip locally without Chromium; it does not show the CI matrix actually
  installs Chromium or runs `pytest -m ux`. Phase 3 must read the workflow files.
- **Live `main` state vs the pin.** B.4/B.5 may have partly landed past `c6e0437`;
  the map cannot see post-pin commits. Reconciled in Phase 5.
- **Real-world quality/grounding performance.** No real-corpus eval results exist
  at the pin (`evals/fixtures/real/` empty); the C-3/AL-1 "over-tight grounding"
  suspicion and the M-2 quality bars are unmeasured. Charter exhibit #2 (grounding
  performance) is unevidenced by history.
- **Actual cost/latency footprints.** RELEASE_ARC cites targets (≤72s analyze,
  ~$0.03 clarify-on-Haiku) but `logs/llm_calls.jsonl` is gitignored; the map
  cannot confirm achieved figures. Needs a live `/bench` or dashboard read.
- **Test-suite health.** Counts referenced (632 → 1072 → ~955) but redundancy,
  flakiness, and coverage gaps (WS-3's remit) are invisible from commit messages.
- **Security posture beyond the enumerated egress.** The charter verified egress
  at `c6e0437`; the broader threat model (PII at rest, the localhost guards on
  every new route) needs a code-level Phase 3 audit, not a history read.
- **Whether deferred items stay alive or rot.** nursery.md, the post-v1.0.5
  deferrals, and "B (deferred)" notes are tracked, but history can't tell which
  are genuinely scheduled vs quietly abandoned.

---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Product vision & definition

> Domain assessor output for the 2026-06 product-excellence review.
> Severity anchor: the SIGNED Product Charter
> (`../../00-interview/product-charter.md`). Honors C-0 claims discipline.
> Evidence cited as `path:line@c6e0437` (verified identical between
> `c6e0437` and the review-branch HEAD by `git diff --stat c6e0437 HEAD`
> on the product docs — see Dynamic checks).

## Domain verdict

sartor. *knows what it is* at the level of instinct: the identity is
crisp and refreshingly non-marketing, the no-invention thesis is
load-bearing across every doc, and `system-model.md` is a genuinely
strong self-model that a skeptical engineer (A-4) can navigate. The gap
is not vision — it is **vision-doc-vs-signed-charter divergence**: the
public vision docs (`vision.md` especially) still carry the pre-charter
register the owner explicitly walked back on 2026-06-12 — absolute
no-invention claims (C-0 bars these), "single-tenant / one person, one
machine, one job at a time" as a value (R2-4.1 demoted it), a flat
"lines we won't cross" constraint tier (C-0/C-8 want enforceability
tiering), an ATS rule with no escape hatch, and a success definition that
never names interviews even though the `Application` outcome model is
already in the schema. None of these are vision *defects*; they are docs
that lag a vision the owner has already sharpened in the charter. The
fixes are bounded doc edits with a known landing — appropriate to close
before the v1.1.0 public tag because they sit in the first docs a hostile
cloner reads.

---

## Register findings (highest leverage first)

### F-vision-01 — Constraints are a flat "won't-cross" tier; the charter wants enforceability tiering
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-0, C-1, C-6 (brief C8)
- **question-refs:** QB-vision-01
- **evidence:** `vision.md:75-77@c6e0437` ("Self-imposed constraints …
  These are the lines sartor. won't cross") then seven sub-sections
  (`vision.md:81-174`) — local-first, open-standards, minimal-deps,
  determinism boundary, no-invention, auditable-iterations — all under
  one uniform header with no enforceability label.
- **finding:** The charter's central epistemic move (C-0) is that
  categorical claims are made *only* where a deterministic test enforces
  them (egress C-2, module boundary C-6, template properties C-5), and
  everything LLM-dependent is described as mechanism+effort. vision.md
  presents all ~7 constraint families as one undifferentiated "won't
  cross" set, so a reader cannot tell the two truly-inviolable
  machine-enforced clauses from the negotiable defaults (D-1 minimal deps,
  D-3 no-auth — both marked negotiable by the owner at Q10). This is the
  single largest vision-doc divergence from the signed charter. Fix:
  tier the section (machine-enforced-inviolable vs negotiable-default),
  which also makes the identity *more* falsifiable — a BOOST shape.
- **coordinate:** v1.0.7 governance extraction (charter graduates to
  `docs/governance/charter.md`; tiering should land coherently with it)

### F-vision-02 — Absolute no-invention register in vision.md + system-model.md violates C-0
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-0, C-3, A-4
- **question-refs:** QB-vision-05
- **evidence:** `vision.md:50@c6e0437` "The LLM cannot invent facts.";
  `vision.md:151` heading "### No invention, ever"; `vision.md:152`
  "Three layers of defense against LLM hallucination"; `system-model.md:31`
  "**without inventing anything about you**"; `system-model.md:33`
  "grounded entirely in your actual history"; `system-model.md:38-41`
  "it may not **fabricate** — no invented titles, numbers, or dates."
- **finding:** C-0 (signed "Confirm") bars categorical claims wherever
  they depend on LLM behavior; the owner explicitly recanted exactly
  these at R2-4.2 ("'LLM cannot invent' is a bold claim") and R2-4.4
  ("no invention ever is over-stated"). The charter's replacement is
  mechanism+effort language ("we do our best, and here is exactly how").
  vision.md:50/151 and system-model.md:31-41 still state the guarantee in
  absolute register. system-model.md's own "Open revision points"
  (`system-model.md:162@c6e0437`) flags the no-invention opening as
  unresolved — so this is acknowledged-but-not-yet-fixed. This is the
  charter's *cardinal sin* (categorical claim without a deterministic
  enforcer) sitting in the two highest-traffic vision docs; for the
  A-4 "whoa, robust" reader an overclaim that the eval harness cannot
  guarantee is a credibility risk, not a strength.
- **coordinate:**

### F-vision-03 — Interviews never stated as a success criterion; the outcome loop is already in the schema but docs call it "(Future v2)"
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** P-4, M-1, C-6 (success-loop)
- **question-refs:** QB-vision-02
- **evidence:** "interview" appears in `vision.md` only as the
  *clarification interview* feature (`vision.md:68,196@c6e0437`) and in
  `README.md:119` likewise — never as success. Yet the `Application`
  model exists at the pin with `sent_at`/`outcome_at` and a status enum
  including `'interview'` (`db/models.py:505-506,516@c6e0437`), while
  `PRODUCT_SHAPE.md:133-139@c6e0437` still labels "Mark sent + outcome"
  a "(Future v2)" feature and `PRODUCT_SHAPE.md:458-459` "no … signal
  today. v2."
- **finding:** P-4/M-1 elevate "an interview from a sartor-written
  resume" to *the* success measure — and it is the product's literal
  name. No public-facing vision doc states it as a success criterion;
  it surfaces only as a deferred-v2 feature. Worse, the deferral is now
  stale: the outcome-capture spine (Application + status='interview' +
  sent_at/outcome_at) is committed at the pin (map: "B.8 Part 1 outcome
  capture" in-flight), so the docs under-describe a capability the code
  already has. Fix: vision.md gains the outcome-level goal (honestly
  scoped to what C-2/T-A let the user's own instance observe — never the
  aggregate), and PRODUCT_SHAPE's "(Future v2)" framing reconciles with
  the shipped Application model.
- **coordinate:** v1.0.6 Sprint 6.6 / B.8 (outcome capture); v1.0.7 M-2
  explainability artifacts

### F-vision-04 — "One person, one machine, one job at a time" + single-tenant-as-value contradicts the signed identity ("local and yours")
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-1, P-2, A-2
- **question-refs:** QB-vision-08
- **evidence:** `vision.md:33` "single-tenant local-first web app";
  `vision.md:42` "The scope is narrow on purpose: one person, one
  machine, one job at a time."; `vision.md:81` header "Local-first,
  single-tenant"; `vision.md:278-280` "Multi-user / multi-tenant —
  sartor. is single-tenant by design. Adding auth would change the
  threat model fundamentally; we won't." Counter-evidence the app is
  multi-profile: `app.py:180 list_users()`; `templates/index.html:74`
  `userSelect` dropdown.
- **finding:** R2-4.1 (owner, signed into P-2/C-1) explicitly **rejected**
  the sentence "one person, one machine, one job at a time" ("paints us
  into a corner without actually saying anything about what we care
  about") and **demoted single-tenancy from a value** ("single-tenant
  isn't necessary. my partner and i can use the same installation"). The
  charter's identity is "local and yours"; the values are trust, control,
  capability. vision.md still leads with the rejected sentence and treats
  single-tenant as a load-bearing constraint — and the multi-profile user
  picker shows the app already supports household sharing, so the doc
  contradicts both the charter *and* the code. Fix: re-voice the identity
  to "local and yours"; demote single-tenancy from value to
  implementation note (no-auth stays a negotiable default per D-3, not an
  identity pillar).
- **coordinate:**

### F-vision-05 — vision.md:92 asserts "no third-party CDN fetches at runtime"; false at the pin
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-0, C-2, P-3
- **question-refs:** QB-vision-07 (adjacent; PX-01 ruled)
- **evidence:** `vision.md:89-93@c6e0437` "No telemetry, no analytics, no
  error reporting, no third-party CDN fetches at runtime"; contradicted at
  the pin by `dashboard/templates/dashboard.html:15@c6e0437`
  `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/...">` loaded
  on every `/_dashboard` open.
- **finding:** This is a categorical vision claim ("no … CDN fetches at
  runtime") that is false at the assessed state — exactly what C-0
  forbids and a direct hit on S-1 fear #2 (glaring miss). The CDN load
  itself is the **already-ruled PX-01 fix (vendor Chart.js, v1.0.6)** — I
  do not re-litigate it; I verify it is **not yet landed at the pin** (CDN
  line still present). The vision-domain residue is the doc wording: even
  after PX-01 vendors Chart.js, this sentence is the kind of unqualified
  absolute C-0 wants replaced with the enumerable-class form
  ("the two sanctioned egress classes"). Note this is the *only* egress
  spot where vision.md drifts — vision.md:89-90's two-class enumeration
  ("(a) the Anthropic API, (b) the optional LinkedIn / portfolio URL
  scrape") is otherwise correct and ahead of SECURITY.md's stale
  three-class list (QB-docs-01's home). Fix the line in lockstep with
  PX-01.
- **coordinate:** v1.0.6 PX-01 (vendor Chart.js)

### F-vision-06 — Corpus-Item ladder: vision.md Learnings drift from PRODUCT_SHAPE's current disposition
- **disposition:** FIX
- **leverage:** P2
- **charter-trace:** P-6, S-2
- **question-refs:** QB-vision-04
- **evidence:** `vision.md:222-229@c6e0437` describes "the v1.1 / v1.2
  plan to extend it to `ExperienceSummaryItem`, `SkillGroupItem`,
  `CoverLetterChunkItem`." `PRODUCT_SHAPE.md:410-417@c6e0437` (superseded
  banner, 2026-06-08) reschedules ExperienceSummaryItem + SkillGroupItem
  to **v1.0.6** under the epic/tag versioning model and dispositions the
  rest in §10/nursery.
- **finding:** The thesis (Corpus-Item unification) is genuinely still
  load-bearing and **converging, not stalled** — PRODUCT_SHAPE carries an
  explicit, dated re-disposition banner (a model of how to keep a ladder
  honest; see F-vision-09). The drift is one-directional: PRODUCT_SHAPE
  was reconciled to the epic/tag versioning model on 2026-06-08;
  vision.md's Learnings still cite the old "v1.1 / v1.2" stage labels as
  forward-looking, so a reader landing in vision.md gets a schedule that
  the authoritative doc has already superseded. Low-risk, bounded fix:
  point vision.md's Learnings at PRODUCT_SHAPE §7 disposition instead of
  restating a schedule.
- **coordinate:** v1.0.6 Sprint 6.6 (B.4 `feat/experience-summary-item` /
  B.5 `feat/skill-group-item`)

### F-vision-07 — ATS framing is categorical; the charter's escape hatch is not named in vision.md
- **disposition:** FIX
- **leverage:** P2
- **charter-trace:** C-5
- **question-refs:** QB-vision-03
- **evidence:** `vision.md:57-63@c6e0437` "Templates that *aren't*
  ATS-safe are retired — even when they look prettier." `vision.md:250-259`
  heading "### ATS-safety is the product" + "Templates that look prettier
  but don't parse don't ship." `vision.md:284-290` out-of-scope. No
  mention of the C-5 hatch.
- **finding:** C-5 grants a real, owner-voiced escape hatch (R2-3): "those
  users can edit the document they produce if they want non-ATS. i don't
  need to solve every problem." vision.md states ATS-safety categorically
  with no hatch named, so a reader concludes non-ATS output is impossible
  rather than user-reachable-by-editing. This one is *narrow*: R2-3 ruled
  the categorical ATS-safe stance and the no-bundled-non-ATS-templates
  decision **stand** (the flag-semantics question is decided/cut), so the
  fix is purely additive — one sentence naming the edit-the-produced-doc
  hatch, not a softening of the ATS-safe commitment.
- **coordinate:**

### F-vision-08 — system-model.md seven-functions self-model with visible honesty seams (affirm; do not pitch-ify)
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** A-4, P-3, C-0
- **question-refs:** QB-vision-05 (KEEP half)
- **evidence:** `docs/system-model.md:60-126@c6e0437` (seven functions +
  the one law); honesty seams flagged at `system-model.md:106-108`
  (Governance "deliberately prescribed rather than emergent") and the
  "Open revision points" block `system-model.md:148-164`; provenance
  block `system-model.md:167-174` traces it to the settled excellence-walk.
- **finding:** This is the A-4 "whoa, robust" exhibit working as intended:
  a legible whole-system map that lets a reader place any file, states its
  own dependency law as the codebase's actual rule (not an imported
  metaphor), and — rare — flags its own unresolved framing calls instead
  of papering over them. It is the strongest single vision asset and the
  WS-4 wiki `overview.md` seed. Affirm it so it is not "improved" into
  pitch copy (C-0). The one carve-out: its opening no-invention absolutes
  are F-vision-02's concern; fixing those must not flatten the rest.
- **coordinate:** WS-4b (system-model.md seeds wiki `overview.md`)

### F-vision-09 — Corpus-Item asymmetry matrix as the falsifiable diagnosis of record (affirm)
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** P-6, S-2
- **question-refs:** QB-vision-04 (KEEP half)
- **evidence:** `docs/PRODUCT_SHAPE.md:31-42@c6e0437` (the asymmetry
  matrix with per-property `db/models.py` line cites); dated
  re-disposition banners `PRODUCT_SHAPE.md:410-417` (§7) and `:481-490`
  (§10) keeping the ladder honest as versions shift.
- **finding:** The matrix is a falsifiable diagnosis (each cell cites a
  model line), not a slogan — exactly the discipline the domain guide
  names as mastery for the thesis. The §7/§10 "superseded 2026-06-08"
  banners are a model for how to retire stale stage labels in place
  without losing rationale. Keep both as the diagnosis of record; the only
  hygiene debt is the vision.md side that lags them (F-vision-06).
- **coordinate:**

### F-vision-10 — Charter-admitted audiences (A-2 continuum, A-3 builders, A-5 blocked-ATS) absent from the public identity
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** A-2, A-3, A-5
- **question-refs:** QB-vision-06
- **evidence:** `vision.md:16-19@c6e0437` audience block ("humans
  evaluating whether to use or contribute … LLM agents proposing
  changes") names neither the user→power-user→dev continuum (A-2) nor
  builders-wanting-patterns (A-3). `vision.md:97-101` frames JSON Resume
  as "portable to any jsonresume.org-compatible tool" but not as the A-5
  "ready if a direct [ATS] path ever opens" aspiration; `vision.md:39-42`
  out-of-scope lists "not an applicant tracking system" without naming
  direct structured-data submission as *wanted but blocked by the
  industry*.
- **finding:** Not yet a charter conflict — these audiences are admitted
  by the charter as future/continuum, and the owner ruled the commercial
  multi-client channel out of scope (R2-2). But as the public release
  nears, "one person, one machine, one job at a time" (F-vision-04)
  structurally narrows the identity past what the charter admits, and the
  A-5 blocked-ATS aspiration is a *distinctive* portfolio hook (it
  explains why JSON Resume is the canonical intermediate) that the vision
  doc leaves on the table. WATCH: fold A-2's power-user continuum and the
  A-5 "clean implied structure, ready if a path opens" framing into the
  identity when F-vision-04 re-voices it; do not enumerate the
  out-of-scope coach channel.
- **coordinate:** v1.0.7 (assistant serves the A-2 continuum)

---

## Appendix (beyond the register cap)

### F-vision-A1 — Crisp non-marketing identity sentence (BOOST candidate, confirmed)
- **disposition:** BOOST · **leverage:** P3 · **charter-trace:** P-1, P-2, C-0
- **evidence:** `vision.md:3-7@c6e0437` "sartor. answers one question,
  honestly: 'What résumé and (optional) cover letter should I send for
  this specific job?'"; the ordered three goals `vision.md:48-72`.
- **finding:** The product-map / domain-guide BOOST candidate (crisp,
  non-marketing identity; ordered concrete goals) is **confirmed**. The
  opening question framing is plain and falsifiable, and the three goals
  are ordered by priority and concrete. This register is the asset every
  FIX above must preserve — the corrections re-voice the *claims*
  (absolutes → mechanism+effort, single-tenant → local-and-yours) without
  touching this plainspoken spine. Amplify by carrying the same register
  into the constraint-tiering rewrite (F-vision-01).

### F-vision-A2 — vision.md egress two-class enumeration is correct and ahead of SECURITY.md (affirm)
- **disposition:** KEEP · **leverage:** P2 · **charter-trace:** C-2, C-0
- **evidence:** `vision.md:89-90@c6e0437` "(a) the Anthropic API,
  (b) the optional LinkedIn / portfolio URL scrape" (two classes, matches
  the charter C-2 enumeration); `README.md:127@c6e0437` likewise
  two-class. Contrast the stale three-class list at `SECURITY.md:57-59`
  (includes the non-existent pasted-JD-URL fetch) — that drift is
  QB-docs-01's home, not this domain's.
- **finding:** On the most-scrutinized clause (C-2), vision.md is already
  at the correct two-class enumeration — affirm it so the SECURITY.md
  reconciliation (PX-03) converges *up* to vision.md's wording, not the
  reverse. The only vision.md egress defect is the separate CDN absolute
  (F-vision-05).

---

## Notes on scope discipline

- **PX-01/PX-02/PX-03 and the four C-2 rulings are decided** — I verified
  only landing-at-pin where it touches vision (PX-01 CDN still present →
  F-vision-05) and did not re-litigate any prescription.
- **No paid LLM / eval / Anthropic calls were made.** All findings are
  static doc-vs-charter-vs-code reasoning plus read-only git/grep/AST
  inspection.

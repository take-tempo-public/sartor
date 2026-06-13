---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Eval / grounding / tuning as product

> Severity anchor: the signed Product Charter. A gap matters only insofar as it
> blocks a charter clause. Claims here follow C-0 — mechanisms-and-effort
> language, no absolutes about LLM behavior. All evidence is at the pinned SHA
> `c6e0437` (the worktree HEAD `b85be08` carries only `review/` commits on top of
> the pin; the product files read are byte-identical to `c6e0437`). Dynamic
> checks (214 eval-domain unit tests + direct L0/override probes) were run in the
> read-only worktree with no writes inside the repo and no paid/LLM calls.

## Domain verdict

This domain is the strongest-engineered surface in the review and earns the A-4
"whoa, this is robust" reaction it is named for: a sharp attribution reframe, a
deterministic hot-path-safe L0 detector with an honest precision caveat, a
fail-closed LLM-free annotation contract, non-polluting candidate A/B via
`prompt_overrides`, manual-by-design promotion, and cost/consent-gated paid
routes — 214 eval-domain unit tests pass locally and the C-0 claims discipline
is honored throughout the design notes. The load-bearing gaps are all
**evidence-of-exercise**, not design defects: `evals/fixtures/real/` is empty so
L1/L2 are uncalibrated and the loop has never produced labels (blocks M-2/T-D);
the over-suppression suspicion (AL-1) has no instrument and is unfalsifiable from
data; the groundedness/tuning panes speak dev-register with no lay legend
(blocks S-3 and the M-2 v1.0.7 criterion); and the committed synthetic suite
exercises only the legacy generate path, leaving corpus-mode by-construction
grounding unexercised by CI. Crucially, the calibration gap is **tracked** as
named release tasks (PV-1/PV-2), not hidden — the right C-0 posture.

---

## Register findings (highest leverage first)

### F-eval-01 — AL-1 over-suppression is uninstrumented and unfalsifiable from data
- **disposition:** FIX (instrument it) — also the domain's named BOOST opportunity
- **leverage:** P1
- **charter-trace:** AL-1, C-3, T-B, S-2, M-2
- **question_refs:** QB-eval-01
- **coordinate:** v1.0.7 (PV-2 advances AL-1)
- **evidence:** suggested-bullet count is jointly shaped by (a) the client-side
  `_dropoffPick` cut (`static/app.js:4495`, `minKeep=3, maxKeep=7, ratio=0.65`)
  and (b) the prompt-side "quality over quantity / return fewer questions
  (minimum 3)" rule (`analyzer.py:439`); `PROMPT_VERSION` is now `2026-06-11.1`
  (`analyzer.py:268`) after many moves. The per-generation deterministic metrics
  riding along on every eval result are `verb_diversity`, `specificity_density`,
  `grounding_overlap`, `top_third_density`, `quantification_rate`,
  `fabricated_specifics`, `groundedness` (`evals/runner.py:292-300`) — **none
  counts suggested or selected bullets**.
- **finding:** The owner's recorded report (R2-4.4 / AL-1) of a significant
  reduction in suggested bullets after grounding tightening currently cannot be
  confirmed or refuted from data — no metric tracks bullet count over
  PROMPT_VERSION history. The runner already extracts bullets per generation
  (`evals/grounding_signals.py:extract_bullets`; `BULLET_LINE_RE`, `hardening.py`),
  so adding a `suggested_bullet_count` to the ride-along set and charting it on the
  existing score-over-time-by-prompt-version surface is a small, label-free add.
  Until it exists, the C-3 usability-vs-purity balance is steered by anecdote, and
  any future grounding tightening risks re-opening the regression invisibly.

### F-eval-02 — The real loop has never been exercised; L1/L2 uncalibrated (M-2/T-D)
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** M-2, T-D, C-3
- **question_refs:** QB-eval-02, QB-eval-08 (relates)
- **coordinate:** v1.0.7 (PV-1 `eval/live-shakedown-labels`, PV-2 `eval/grounding-calibration`); gates v1.1.0
- **evidence:** `evals/fixtures/real/` contains only `.gitkeep`
  (`git ls-files evals/fixtures/real/` → one entry); no `bootstrap.json` /
  `annotations.json` / `seed.json` anywhere. `GROUNDING_METRIC.md:93-98`
  ("Blocker, verified 2026-06-05 … the live run was never executed"). The numeric
  tolerance is stamped `UNCALIBRATED` (`hardening.py:591-593`,
  `_NUMERIC_REL_TOL = 0.05`). Tracked as PV-1/PV-2 in `RELEASE_ARC.md:712-713`.
- **finding:** The v1.0.4 machinery shipped but its live run was never executed,
  so L1/L2 precision/recall against human labels is unmeasured and L0 tolerance
  bands are untuned. This blocks M-2 ("the tuning/annotation loop exercised
  end-to-end by the owner with metrics readable at a glance") and is the concrete
  form of T-D. The gap is **honestly tracked and sequenced** (PV-1 produces labels,
  PV-2 calibrates and reports per-detector precision/recall) rather than hidden —
  that scheduling is the correct response. Act-on point: PV-1/PV-2 sit in v1.0.7
  while the M-2 exercise is a v1.1.0 tag criterion, so this is on the critical path
  to the public tag, not optional.

### F-eval-03 — No lay metrics legend on the groundedness / tuning panes (S-3)
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** S-3, M-2 (v1.0.7 "lay metrics legend"), A-2
- **question_refs:** QB-eval-04
- **coordinate:** Sprint 6.5 (in-app education sweep — targets exactly S-3)
- **evidence:** the groundedness pane surfaces raw technical labels with no
  plain-language gloss — "groundedness (L0)", "fabricated rate", "N flagged", the
  layer string (`L0`), a bare `prompt_version` code
  (`dashboard/templates/dashboard.html:300-318`); the tuning banner is dev-register
  ("copy a winner into the `analyzer.py` constant, bump `PROMPT_VERSION`, log
  `TUNING_LOG.md` by hand", `dashboard.html:322-330`).
- **finding:** These are power-user surfaces in the explainability scope (R2-12.2,
  E-2), and S-3 (the owner's furthest-below-bar area) is precisely legibility of
  grounding/tuning through the UI + diagnostics. A non-coding power user (A-2)
  reading "fabricated rate 12.3% · L0 · candidate:9f3a…" gets no anchor for what
  the number means, that L0 is an uncalibrated flag-for-review signal (not a
  verdict), or what action it implies. The M-2 v1.0.7 criterion names a "lay
  metrics legend in diagnostics" as shipped tag evidence; absent at the pin.
  Sprint 6.5 is the natural home.

### F-eval-04 — Dynamic source-union scoring distinguishes "asserted beyond" from "synthesized within" (C-3)
- **disposition:** KEEP
- **leverage:** P1 (affirm so it is not churned)
- **charter-trace:** C-3, R2-4.4
- **question_refs:** QB-eval-03
- **coordinate:** (none)
- **evidence:** `assemble_source_union` assembles primary + supplementals +
  clarification answers as one shared union (`hardening.py:1154-1179`), reused by
  the iteration clarifier and the L0 check so they never diverge. The generate-time
  GROUNDING CHECK widens to accept clarification answers AND first-person typed
  edits as ground truth (`analyzer.py:1966-1969`), with worked OK/NOT-OK examples
  teaching synthesis-within-ground vs invention-beyond-ground
  (`analyzer.py:1971-1995`). Corpus mode is grounded by construction: every emitted
  bullet must be a verbatim `<bullet>` id OR a reviewable `proposed_new_bullets`
  entry (`analyzer.py:1870-1871`).
- **finding:** Metric and prompt both score against the dynamic union, not the
  original résumé alone — the C-3 resolution of R2-4.4 ("the violation is asserting
  beyond that ground, not synthesizing within it"). Scoring against the original
  primary only would over-report, flagging legitimately-clarified facts as
  fabrication; the code avoids that and documents why
  (`GROUNDING_METRIC.md:24-31`). This is the load-bearing correctness of the
  domain — affirm it so a future "tighten grounding" pass does not narrow it back
  to the original-résumé-only frame.

### F-eval-05 — Candidate A/B is non-polluting; default path byte-identical (KEEP-verified)
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** A-2, C-4
- **question_refs:** QB-eval-05
- **coordinate:** (none)
- **evidence:** `prompt_overrides()` + `_BASE_SYSTEM_PROMPTS` registry
  (`analyzer.py:289-309, 2873`) scoped to exactly the 8 named system-prompt
  constants; `effective_prompt_version()` returns `PROMPT_VERSION` verbatim on the
  default path and `candidate:<sha256[:12]>` only under override
  (`analyzer.py:312-324`). Dynamically verified: `effective_prompt_version()` ==
  `PROMPT_VERSION` ("2026-06-11.1") with no override; registry keys =
  {`SYSTEM_PROMPT`, `EXTRACTION_`, `CLARIFY_`, `CLARIFY_ITERATION_`, `RECOMMEND_`,
  `RECOMMEND_SUMMARIES_`, `PROMOTE_CLARIFICATION_`, `PROPOSAL_CRITIQUE_`}. The loop
  is browser-driveable (`/_dashboard` Tuning tab, `dashboard.html:991+`).
- **finding:** Candidate runs are quarantined from score-over-time and the
  analyze→generate cache is untouched on the default path (the resolver returns the
  identical constant object). A power user can A/B a prompt edit from the browser
  without editing persona constants. Verified as the charter/guide describe — a
  strength to preserve under any analyzer refactor.

### F-eval-06 — Manual promote + fail-closed, LLM-free annotation contract (KEEP-verified)
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-4
- **question_refs:** QB-eval-06
- **coordinate:** (none)
- **evidence:** promotion is manual — no auto-write of a winning candidate into
  `analyzer.py` exists; banner says "Promote stays manual"
  (`dashboard.html:327-329`; `evals/README.md:279`). The annotation contract
  validates fail-closed (`validate_annotations`, `annotation.py:203-235`):
  unsupported schema version, unknown verdict/slug, or a verdict missing its
  required payload (`fix` without `honest_rewrite`, `fabricated` without a
  compilable `forbidden_pattern`) is rejected, not half-collated; LLM-free by
  design (`annotation.py:16`). `_scorer_disagreements` (`annotation.py:487-509`)
  operationalizes "annotations validate the automated scorers". 43 annotation
  tests pass.
- **finding:** Promotion is a deliberate human gate consistent with C-4, and the
  annotation seam fails closed rather than emitting a silently-degraded fixture.
  Both correct; should not be "automated for convenience" later.

### F-eval-07 — Paid eval/tune routes are cost- and consent-gated (BOOST-verified)
- **disposition:** BOOST
- **leverage:** P2
- **charter-trace:** C-1, D-6
- **question_refs:** QB-eval-07
- **coordinate:** (none)
- **evidence:** `/api/eval/run` and `/api/tune/run` 403 on non-localhost
  (`_is_localhost_request()`, `app.py:6683-6684, 6790+`); all eager validation
  (bad suite, unknown user, missing seed) returns JSON 4xx **before** the worker
  spends (`app.py:6687-6721`); the seed path is contained under `ANNOTATION_ROOT`
  with `secure_filename` + `_within` (`app.py:6697, 6708-6712`). The UI shows a
  cost-band `confirm()` before POSTing ("≈ $0.10 smoke / ≈ $0.30 full … paid
  Sonnet + Haiku", live-updating, `dashboard.html:973-987`).
- **finding:** Confirms product-map BOOST-9 in this domain: the paid surfaces are
  localhost-only, eager-4xx-before-spend, gated by an explicit cost-band
  confirmation — respecting C-1 (local-and-yours) and the D-6 progressive-
  disclosure intent (spend opt-in and disclosed). A model for fencing paid actions
  on a power-user surface.

### F-eval-08 — Uncalibrated L1/L2 state is surfaced and tracked, not silently trusted (DEBUFF averted)
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-0, M-2
- **question_refs:** QB-eval-08
- **coordinate:** v1.0.7 (PV-2 closes it)
- **evidence:** L1/L2 stay eval-only behind `--grounding-signals`
  (`evals/grounding_signals.py` docstring "Never imported by the production
  pipeline"; flag-gated in `evals/runner.py`); the L0 tolerance is stamped
  `UNCALIBRATED` in code (`hardening.py:591-593`); the precision caveat is spelled
  out "honest by design" in the docstring (`hardening.py:762-766`), CHANGELOG
  (`CHANGELOG.md:840-846`), and `GROUNDING_METRIC.md:104-108`. PV-2
  (`RELEASE_ARC.md:713`) reports per-detector precision/recall.
- **finding:** The guide's DEBUFF ("treating L1/L2 numbers as trustworthy before
  calibration") is **not** committed: the uncalibrated state is disclosed in code,
  docs, and CHANGELOG, L0 is presented as flag-for-review (not a gate), and
  calibration is a tracked obligation. Correct C-0 posture (mechanism + effort, no
  false trust). Keep it — do not let a dashboard polish pass present the L1/L2
  numbers as verdicts before PV-2 lands.

### F-eval-09 — The sharpened L0 detector is eval/display-only; the hot path still uses the lossy proto-L0
- **disposition:** WATCH (claims-precision in the design doc)
- **leverage:** P2
- **charter-trace:** C-0, C-3
- **question_refs:** QB-eval-03 (relates), QB-eval-08 (relates)
- **coordinate:** v1.0.7 (PV-2 / explainability)
- **evidence:** `compute_fabricated_specifics` (the sharpened typed L0) is called
  only from `evals/runner.py:289` and surfaced read-only in `dashboard/routes.py`;
  it has **no caller in `app.py`** (grep of `app.py` for the name is empty). The
  iteration path uses `compute_iteration_signals` (`app.py:1097`), which carries
  the **older lossy n-gram** `compute_grounding_overlap` (`hardening.py:1212`), not
  the typed detector. Yet `GROUNDING_METRIC.md:70-73` describes L0 as "safe to run
  in the hot path and to log per generate call" and "a *per-call* production
  signal".
- **finding:** The capability is real and hot-path-safe (deterministic, no
  weights), but at the pin it is not wired into the generation request path — it is
  eval-time + dashboard-display only. The design doc's "per-call production signal"
  reads present-tense when it is a not-yet-wired option. Low severity (no
  user-facing false claim; it is an internal design note), but worth a one-line
  precision edit so a follow-up agent does not assume `/api/generate` already logs
  the typed L0. If per-call production logging is wanted for S-3, it is a small
  wiring task.

### F-eval-10 — The committed synthetic suite exercises only the legacy generate path; corpus-mode grounding is uncovered by CI fixtures
- **disposition:** FIX (coverage gap)
- **leverage:** P2
- **charter-trace:** C-3, M-2, A-4
- **question_refs:** QB-eval-02 (relates), QB-eval-03
- **coordinate:** v1.0.7 (PV-1 produces the first corpus-backed real fixtures)
- **evidence:** the three committed synthetic fixtures
  (`evals/fixtures/synthetic/{data-scientist-junior,pm-senior,sre-mid-level}`) run
  through the file-parsed `_build_context` (`evals/runner.py:179-199`), which builds
  a context_set with **no corpus DB** — the legacy generate path. Corpus mode (the
  strongest grounding mechanism, verbatim-bullet-or-proposed by construction,
  `analyzer.py:1870-1871`) is reached only via `_build_context_from_seed`
  (`evals/runner.py:202`) under `--seed`, which needs a real `seed.json` — none
  committed (F-eval-02).
- **finding:** The committed/CI-runnable suite validates legacy-mode grounding; the
  by-construction corpus-mode path the live app actually uses is unexercised by
  committed fixtures and depends entirely on the not-yet-created real seeds. For the
  A-4 grounding-performance exhibit (#2) and the M-2 end-to-end exercise, at least
  one corpus-backed fixture (the PV-1 output) needs to exist so the corpus-mode
  grounding contract is regression-guarded, not just unit-tested in isolation. This
  sharpens F-eval-02: even after labels exist, a committed corpus-backed regression
  fixture is what closes the coverage gap.

---

## Appendix (beyond the register cap)

### A-eval-01 — Residual "no invention ever" register in legacy resume_rules #2 (minor C-3 tension)
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** C-3, R2-4.4 · **question_refs:** QB-eval-03
- **evidence:** `analyzer.py:1998` (legacy `<resume_rules>` #2): "Do NOT invent
  experience. **Every bullet must trace directly to the original resume.** Reframe
  language; never invent facts." — sits directly below the widened GROUNDING CHECK
  (`analyzer.py:1966-1969`) that accepts clarification answers + typed edits as
  ground truth beyond the original résumé.
- **finding:** The #2 wording is narrower than (and in mild tension with) the
  widened check above it — a residual of the "no invention ever" register the owner
  flagged in R2-4.4. Bounded to the legacy (non-corpus) path and the worked examples
  teach the synthesis distinction, so unlikely to dominate; but if F-eval-01's
  instrument later confirms over-suppression, this line is a first place to look. A
  surgical rewording to "trace to the source union (original résumé, supplementals,
  clarifications, or typed edits)" would align it without loosening grounding.
  Flagged for the PV-2 tuner.

### A-eval-02 — TUNING_LOG.md is genuine institutional memory (BOOST, supports product-map BOOST-3)
- **disposition:** BOOST · **leverage:** P3 · **charter-trace:** A-4, E-1 · **question_refs:** QB-eval-01 (relates)
- **evidence:** `evals/TUNING_LOG.md` (2,152 lines): dated entries with
  what-changed / why / before-after scores / lessons (the
  `2026-06-06 eval/grounding-metric-l0` ride-along entry at L346; the
  `2026-06-10 fix/generate-date-grounding` entry at L260; v1.0.1/v1.0.2 baselines
  with run metadata and per-(fixture×rubric) mean±stdev).
- **finding:** PROMPT_VERSION discipline (every prompt change bumps the version and
  logs the rationale; metric-only branches state "no PROMPT_VERSION bump") is
  practiced and durably recorded — the artifact the A-4 exhibit #1 rests on.
  Confirms product-map BOOST-3.

### A-eval-03 — Test depth on the eval domain (supports product-map BOOST-7)
- **disposition:** KEEP · **leverage:** P3 · **charter-trace:** A-4 · **question_refs:** QB-eval-03/06 (relate)
- **evidence:** dynamic run — 214 eval-domain tests pass locally in ~12s
  (`tests/test_hardening.py`, `test_hardening_iteration.py`, `test_annotation.py`,
  `test_bootstrap.py`, `test_seed_import.py`, `test_grounding_signals.py`,
  `test_eval_runner.py`), all LLM-free and Chromium-free (grounding_signals tests
  inject mocked pipelines → no model download). Dynamically confirmed documented L0
  behaviors: paraphrase false-positive ("4-person" from "small team" → rate 0.667,
  "4" flagged), `k8s`≡`Kubernetes` alias grounded (rate 0.0).
- **finding:** The deterministic eval substrate is well-tested and the documented
  caveats are observable, not aspirational — the depth that earns the A-4 reaction.

### A-eval-04 — Chart.js CDN still loaded on the diagnostics surface at the pin (already-ruled, verify-landed)
- **disposition:** FIX (already ruled PX-01 / C-2(i)) · **leverage:** P1 · **charter-trace:** C-2(i) · **question_refs:** (verify-landed, x-ref QB-sec-04)
- **evidence:** `dashboard/templates/dashboard.html:15` loads
  `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/...` at runtime (SRI-pinned).
- **finding:** Noted only because the diagnostics surface is in this domain's
  scope. The fix is ruled (vendor, v1.0.6) and owned by the security/OSS domain
  (QB-sec-04) — recorded here as **not yet landed at `c6e0437`**, not re-litigated.

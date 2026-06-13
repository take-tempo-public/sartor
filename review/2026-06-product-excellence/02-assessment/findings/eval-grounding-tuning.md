---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Eval / grounding / tuning as product

> Severity anchor: the signed Product Charter. Claims follow C-0 (mechanisms +
> effort, no absolutes about LLM behavior). Evidence is `path:line@c6e0437`
> read via `git show c6e0437:<path>` in the read-only worktree
> `C:\Dev\callback-review` (HEAD `269ac27`; the five review commits touch only
> `review/`, so every non-review file is byte-identical to the pin — verified
> by `git diff --name-only c6e0437 HEAD`).

## Domain verdict

This is a genuinely strong domain and the owner's named exhibit #1 — the
three-tier attribution reframe, the dynamic-source-union scoring, the
candidate-quarantine A/B primitive, the fail-closed LLM-free annotation
contract, the manual-promote human gate, and the cost/consent gating on paid
browser routes are all real at the pin and back the "whoa, this is robust"
reaction (A-4). The load-bearing gaps are exactly the two the charter predicts:
the real loop has **never been exercised end-to-end** (`evals/fixtures/real/`
is `.gitkeep`-only, so L1/L2 are uncalibrated — M-2/T-D), and the surface is
**dev-register, not lay-legible** (no plain-language metrics legend; no
user-facing "how it grounds/clarifies/tunes" page — S-3/M-2-v1.0.7). One
sharper gap the guide flagged is confirmed: **AL-1 has no instrument** — the
`recommend` call that produces suggested bullets is not exercised by the eval
suite and no metric counts recommended-bullet output over PROMPT_VERSION, so
the owner's reported suppression is unfalsifiable from data.

---

## Register findings (highest leverage first)

### F-eval-01 — The real loop was never run; L1/L2 stay uncalibrated (blocks M-2 + T-D)
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** M-2, T-D, C-3, A-4
- **question-refs:** QB-eval-02, QB-eval-08
- **coordinate:** v1.0.7 (PV-1 live-shakedown labels, PV-2 grounding calibration)
- **evidence:** `evals/fixtures/real/` contains only `.gitkeep@c6e0437`
  (`git ls-tree`); no `bootstrap.json`/`annotations.json`/`seed.json` anywhere.
  `docs/dev/GROUNDING_METRIC.md:93` "**Blocker (verified 2026-06-05):** there
  are no labels yet … the v1.0.4 loop shipped the machinery but its live run was
  never executed." Calibration ("measure each detector's precision/recall
  against those labels") is the explicit v1.0.4 tag criterion and is unmet.
- **finding:** The annotate→tune→verify machinery is built and unit-tested, but
  no human labels exist, so L1/L2 (NLI + MiniCheck) precision/recall against
  human verdicts is unmeasured. This directly blocks the M-2 tag evidence ("loop
  exercised end-to-end with metrics readable at a glance") and is the numeric
  form of T-D ("machinery never yet exercised on real data"). The mitigating
  facts: the label-producing path is browser-driven now (one click-through, not
  a CLI chore), and L0 is correctly designed to ship uncalibrated (a novel
  specific absent from the source union is high-precision on the highest-severity
  class). The gap is the calibration run, not the code. This is exhibit #2
  (grounding performance) being currently unevidenced — the charter's own
  T-D/M-2 are the gate that exists precisely to close it before the public tag.

### F-eval-02 — AL-1 has no instrument: `recommend` output count is untracked and uneval'd
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** AL-1, C-3, T-B, S-2, M-2
- **question-refs:** QB-eval-01
- **coordinate:** v1.0.7 (PV-2 advances C-3/AL-1)
- **evidence:** The eval runner imports `analyze, clarify, clarify_iteration,
  generate` but **not** `recommend_bullets` (`evals/runner.py:44-49@c6e0437`);
  suggested bullets come from `analyzer.recommend_bullets` (`analyzer.py:2488`)
  and are then cut client-side by `_dropoffPick` (`static/app.js:4495`,
  `minKeep:3,maxKeep:7,ratio:0.65`). The per-record `deterministic_metrics`
  block (`evals/runner.py:293-300`) carries `verb_diversity`,
  `specificity_density`, `grounding_overlap`, `top_third_density`,
  `quantification_rate`, `fabricated_specifics`, `groundedness` — no
  recommended-bullet *count*. `_groundedness_trend` plots only the L0 score over
  PROMPT_VERSION (`dashboard/routes.py:591`); `total_bullets` is captured
  per-run in `_latest_groundedness_detail` but is the *generated-resume* bullet
  count, not the *recommend* output, and is not trended. `TUNING_LOG.md:1054`
  only says to "watch the eval suite's grounding + keyword_coverage rubrics" for
  `recommend_bullets` quality — neither measures count.
- **finding:** The owner reported "a significant reduction in suggested
  bullets … one of the main features of clarification" (R2-4.4 → AL-1). Across
  PROMPT_VERSION's ~dozen moves since 2026-05-09, nothing in the instrumented
  data measures how many bullets `recommend` proposes per analyze, so the
  suspected over-suppression is currently decidable only by anecdote. The cheap
  fix is a deterministic per-analyze recommended-bullet count (and pre-`_dropoffPick`
  candidate count) stamped with PROMPT_VERSION and trended on the existing
  by-version chart — turning the suspicion into a falsifiable signal. Until then
  C-3's "synthesis within ground is the feature, suppressing it is a regression"
  has no enforcement against the very regression the owner flagged.

### F-eval-03 — No lay metrics legend; the groundedness/diagnostics surface is dev-register
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** S-3, M-2 (v1.0.7 lay-legend criterion), A-2
- **question-refs:** QB-eval-04
- **coordinate:** Sprint 6.5 (in-app education sweep) / v1.0.7
- **evidence:** The groundedness pane surfaces raw labels with no plain-language
  translation: "groundedness (L0) … / 5", "fabricated rate {{…}}%",
  "{{flagged_count}} flagged", "{{layers|join('+')}}", `prompt_version`
  (`dashboard/templates/dashboard.html:300-318, :671@c6e0437`). The one `.legend`
  line present (`:693`) is an honest *developer* caveat ("L0 is a flag-for-review
  signal … will false-positive on paraphrase … Uncalibrated until labels exist —
  see `docs/dev/GROUNDING_METRIC.md`"), not a lay translation. No "what this
  means" / glossary text exists in the template (grep for legend/plain-language/
  glossary returns only the CSS rule). The user-facing "how callback. grounds,
  clarifies, and tunes" wiki page is absent — `docs/wiki/pages/@c6e0437` has no
  such page (the eight pages are dev/system docs).
- **finding:** S-3 is the owner's self-named furthest-below-bar area
  (explainability of grounding/tuning/clarify through the UI + diagnostics), and
  R2-9 made a lay metrics legend + the user-facing page explicit v1.0.7 tag
  criteria. At the pin a non-coding power user (A-2) reading the groundedness
  pane meets "fabricated rate", "L0", `candidate:<hash>` with no in-surface
  explanation of what a number means or what to do about it. The technical
  caveat at :693 is a strength to preserve (see F-eval-08) — the gap is the lay
  layer on top of it.

### F-eval-04 — Three-tier attribution reframe + dynamic source-union scoring (exhibit #1 core)
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** C-3, A-4, S-2
- **question-refs:** QB-eval-03
- **coordinate:** (none)
- **evidence:** `compute_fabricated_specifics` (`hardening.py:733@c6e0437`)
  scores generated specifics against `assemble_source_union` (`hardening.py:1154`
  = primary résumé + supplementals + clarification answers), with numeric
  tolerance (`~30/30/30+` grounded; `~30→100+` flagged) and entity aliasing
  (`k8s ≡ kubernetes`); severity-weighted (number/date > tool). The docstring is
  explicit that it distinguishes "asserted beyond ground" from "synthesized
  within ground" and carries a PRECISION CAVEAT naming paraphrase false
  positives as a flag-for-review, not a hard gate. The detector ladder
  (`GROUNDING_METRIC.md §detector-ladder`) splits L0 (deterministic, hot-path-
  safe) from L1/L2 (eval-only behind `--grounding-signals`,
  `evals/grounding_signals.py` "Never imported by the production pipeline").
- **finding:** The reframe of hallucination as *attribution against a closed
  source union* is the sharp move the guide names, and it is faithfully
  implemented: scored against the dynamic union (not the original résumé alone,
  which would over-report clarified facts), severity-split, and honest about its
  precision killer. This is the technical spine of charter exhibit #1 and #2 —
  affirm it so it is not churned in the v1.0.7 calibration work.

### F-eval-05 — Candidate A/B quarantine is non-polluting and the default path is byte-identical
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** A-2, C-4, C-0
- **question-refs:** QB-eval-05
- **coordinate:** (none)
- **evidence:** `analyzer.prompt_overrides()` (`analyzer.py:290@c6e0437`) sets a
  ContextVar over `_BASE_SYSTEM_PROMPTS` (registry `:2873`), resolved per-call by
  `_resolve_system_prompt` (`:2885`). `effective_prompt_version` (`:312`) returns
  `PROMPT_VERSION` verbatim on the default path and `candidate:<sha256[:12]>`
  when overrides are active, stamped on telemetry + eval records (`:1003`). An
  unknown override key raises `ValueError` (fail-loud, so a typo can't mislabel a
  baseline as a candidate). `evals/README.md:275` "The default path (no flag) is
  byte-identical: the resolver returns the identical constant object."
- **finding:** Candidate runs are quarantined from the score-over-time chart by
  construction, and the no-override path is byte-identical (the analyze→generate
  cache is untouched). This lets a power user A/B a prompt edit from the browser
  without writing code (A-2) and without corrupting baseline telemetry — a clean
  primitive that honors C-0's "categorical only where enforced by construction."

### F-eval-06 — Cost/consent gating on paid browser routes (local-and-yours, eager 4xx before spend)
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** C-1, D-6, C-4
- **question-refs:** QB-eval-07
- **coordinate:** (none)
- **evidence:** `/api/eval/run` (`app.py:6664`) and `/api/tune/run`
  (`app.py:6790`) return `403 "localhost only"` unless `_is_localhost_request()`
  (`app.py:151`, host-header loopback check); all suite/user/seed validation
  returns JSON 4xx "BEFORE the worker spends anything" (docstring + body).
  The UI gates every paid POST behind `window.confirm()` with an explicit dollar
  band — "≈ $0.10 … paid Sonnet + Haiku" / "≈ $0.30 …"
  (`dashboard/templates/dashboard.html:982`) and the A/B "≈ $0.20 / ≈ $0.60 …
  TWO eval suites" (`:1045`). LLM-free actions are labelled as such ("Export seed
  (no LLM)" `:439`; "Score grounding … no paid LLM calls" `:475`).
- **finding:** Paid surfaces are localhost-gated server-side, cost-banded with an
  explicit confirm client-side, and eagerly validated before any spend, with
  paid-vs-free clearly disclosed. This respects the local-and-yours posture and
  the D-6 power-user opt-in framing — a strength to keep through the v1.0.8
  blueprint split (verify the host-header guard moves intact with the routes).

### F-eval-07 — Fail-closed, LLM-free annotation contract operationalizes the M-2 "annotations validate scorers" criterion
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-4, C-6, M-2
- **question-refs:** QB-eval-06
- **coordinate:** (none)
- **evidence:** `validate_annotations` (`evals/annotation.py:203@c6e0437`) is
  fail-closed (unsupported version / unknown verdict / a `fix` without an
  `honest_rewrite` / a `fabricated` without a compilable `forbidden_pattern` is
  rejected, not half-collated). The module imports no `anthropic`/`analyzer`
  (`annotation.py:49-67`) and is documented "deterministic and LLM-free (P1
  hardening posture)". `_scorer_disagreements` (`:487`) emits the lines where a
  human verdict disagrees with MiniCheck/NLI — "the v1.0.4 tag criterion
  'annotations validate the automated scorers' lives here." Promote is manual by
  design (`evals/README.md:725` "Promote — not a console affordance, by design").
- **finding:** The annotation contract is the calibration substrate done right —
  deterministic, fail-closed, and it already encodes the exact human-vs-scorer
  disagreement signal M-2 needs. Promote staying a manual `Edit`-the-constant
  step is a deliberate human gate consistent with C-4. (98 eval/annotation/
  grounding unit tests pass locally — see dynamic checks.) The latent value is
  unrealized only because F-eval-01's labels don't exist yet.

### F-eval-08 — The uncalibrated state is surfaced honestly (no silent overclaim) — C-0 in practice
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-0, M-2
- **question-refs:** QB-eval-08
- **coordinate:** (none)
- **evidence:** The L0 docstring carries "Operational range (UNCALIBRATED — see
  CHANGELOG / evals/TUNING_LOG.md)" and a PRECISION CAVEAT
  (`hardening.py:760-770@c6e0437`). The dashboard legend states "L0 is a
  flag-for-review signal … Uncalibrated until labels exist"
  (`dashboard/templates/dashboard.html:693`). `_enrich_groundedness` notes "L1/L2
  behavior itself is read, never re-tuned (calibration is deferred-B)"
  (`evals/runner.py`). The empty groundedness pane points the user at the exact
  command to populate it (`dashboard.html:303`).
- **finding:** Nowhere does the surface treat L1/L2 numbers as trustworthy, or
  L0 as a hard verdict — the uncalibrated status is stamped in code, in the
  metric docstring, and on the dashboard, with the precision killer named. This
  is C-0 ("mechanisms and effort, never absolutes") honored in the riskiest
  place. Keep this discipline; the only thing missing is the *lay* register of
  the same honesty (F-eval-03).

### F-eval-09 — Sharpened L0 does not yet run per-generate in production (design intent ahead of code)
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** C-3, S-3, C-6
- **question-refs:** QB-eval-03 (boundary), QB-eval-04 (surfacing)
- **coordinate:** v1.0.7 (explainability) / v1.0.8 (blueprint split — keep hot path L0-only)
- **evidence:** `compute_fabricated_specifics` (the sharpened L0) is called only
  from `evals/runner.py:289@c6e0437` — no `app.py` caller (`git grep`). The
  production iteration path calls `compute_iteration_signals` (`app.py:1097`),
  which still uses the older lossy-n-gram `compute_grounding_overlap`
  (`hardening.py:511`), not the typed extractor. `GROUNDING_METRIC.md:53` frames
  L0 as "safe to run in the hot path and to log per generate call" and "can
  become a per-call production signal" — i.e. aspirational.
- **finding:** The deterministic L0 metric is hot-path-*safe* but is currently
  eval-only; the per-generate production grounding signal the design note
  envisions is not wired. This is not a defect (C-6's discipline of keeping the
  hot path cheap is honored, and shipping it eval-first is the staged plan), but
  it is a gap between the design narrative and the running product that bears on
  S-3 (a per-generation grounding readout would be the most legible
  explainability surface for the candidate). Watch: if v1.0.7 surfaces grounding
  to users per-generate, route it through the sharpened L0, and keep it L0-only
  on the hot path through the v1.0.8 split.

### F-eval-10 — Diagnostics is the loop's only home; its a11y/lay-legibility bar is in scope and not yet met
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** E-2 (diagnostics in scope, R2-12.2), S-3, A-2
- **question-refs:** QB-eval-04 (legend), cross-ref QB-exp-a11y-07
- **coordinate:** Sprint 6.5 / v1.0.7
- **evidence:** The entire annotate→tune→verify loop is driveable only from
  `/_dashboard` (`evals/README.md:678` "The in-browser tuning console"); the
  charter puts diagnostics explicitly in the a11y scope as a power-user surface
  (E-2 final bullet; R2-12.2). The pane labels are dev-register (F-eval-03), and
  the dashboard loads Chart.js from a CDN (`dashboard.html:15@c6e0437`) — the
  C-2(i)/PX-01 violation already ruled (fix v1.0.6); confirmed still-present at
  the pin, noted because this is the surface that hosts this domain.
- **finding:** The tuning loop's product surface and the diagnostics a11y/legend
  obligations are the same screen. Two charter-traced gaps converge here: the
  lay-legend (F-eval-03) and the ruled-but-unlanded CDN Chart.js (handed to the
  `sec` domain for verify-landed under QB-sec-04). Cross-coordinate with
  `exp-a11y` (QB-exp-a11y-07) so the legend + the axe scope over `/_dashboard`
  land together rather than as two passes over the same template.

---

## Appendix (beyond the register cap)

### A1 — `recommend`-only behavior is structurally outside the synthetic eval suite (coverage note)
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** C-3, M-2 · **question-refs:** QB-eval-01 (supports)
- **evidence:** `--suite synthetic` runs `analyze→clarify→generate`
  (`evals/runner.py:44-49@c6e0437`); `recommend_bullets`/`recommend_summaries`
  (`analyzer.py:2488,2633`) are corpus/UI-flow calls never invoked by the runner.
  This matches the memory note that corpus-mode-only prompt changes aren't
  exercised by `--suite synthetic`.
- **finding:** Beyond F-eval-02's missing count metric, the `recommend` call kind
  has no eval coverage at all — any future tuning of bullet selection is
  invisible to the score-over-time chart. A targeted unit/UX cover (not a paid
  smoke run) is the proportionate response, consistent with the corpus-mode
  coverage pattern already in memory.

### A2 — `seed_import.py` / `bootstrap.py` machinery is built but unexercised on real data (T-D residue)
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** T-D, M-2 · **question-refs:** QB-eval-02 (supports)
- **evidence:** `GROUNDING_METRIC.md:96` names `evals/annotation.py`,
  `evals/bootstrap.py`, `evals/seed_import.py`, `evals/grounding_signals.py` as
  shipped machinery whose "live run was never executed." Unit-tested (98 tests
  pass) but no `seed.json` exists under `evals/fixtures/real/`.
- **finding:** Same root cause as F-eval-01 (no real run), tracked separately
  because it is the *bootstrap/seed* half of the loop (label *production*) vs the
  *calibration* half (label *consumption*). Surfacing the empty-real-fixtures
  state as a tracked v1.0.7 release task (PV-1) rather than a silent gap is the
  guide's FIX prescription; confirm it appears on the arc, not only in the design
  note.

### A3 — TUNING_LOG is a deep institutional artifact but never recorded an AL-1 investigation
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** AL-1, A-4 · **question-refs:** QB-eval-01 (supports)
- **evidence:** `evals/TUNING_LOG.md@c6e0437` is ~2,136 lines with
  per-PROMPT_VERSION entries; PROMPT_VERSION discipline is real
  (`analyzer.py:268` = `2026-06-11.1`, bumped in-commit per map-BOOST-3). No
  entry investigates the owner-reported suggested-bullet reduction with data;
  `:1054` defers it to "watch the eval suite" rubrics that don't measure count.
- **finding:** The tuning log is a genuine exhibit-#1 strength (BOOST-adjacent),
  but the one regression the owner explicitly named (AL-1) was never closed in
  it — reinforcing F-eval-02. When the F-eval-02 instrument lands, the closing
  TUNING_LOG entry is the natural home for the before/after evidence (per the
  performance-metrics-provenance memory).

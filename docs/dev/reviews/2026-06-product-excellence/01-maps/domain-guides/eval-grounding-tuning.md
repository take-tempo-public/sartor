---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Eval / grounding / tuning as product

> Lens, not survey. Severity anchor: the signed Product Charter
> (`00-interview/product-charter.md`). A gap matters only if it blocks a
> charter clause. Claims here follow C-0: mechanisms and effort language, no
> absolutes about LLM behavior.

## 1. What mastery means here

For sartor., the eval/grounding/tuning system is not back-office QA — it is
**product surface and exhibit #1**. Three charter clauses make it load-bearing:

- **C-3 — grounded synthesis is the feature.** Mastery is keeping the LLM
  attributable to the dynamic source union (résumé + supplementals +
  clarifications + typed edits) *without* suppressing the useful synthesis that
  clarification exists to enable. The metric must distinguish "asserted beyond
  ground" (the violation) from "synthesized within ground" (the feature).
- **S-3 — the owner's self-named weakest area** is exactly explainability of the
  grounding/tuning/clarify pipelines through the UI and diagnostics. Mastery is
  legibility to a non-coding power user (A-2), not just correctness of internals.
- **M-2 — the v1.1.0 tag evidence** requires the loop "exercised end-to-end by
  the owner with metrics readable at a glance," plus a lay metrics legend and a
  user-facing "how sartor. grounds, clarifies, and tunes" page (v1.0.7).
- **A-2 / A-4** — power users tune without writing code; engineers reading the
  repo should think "whoa, this is robust." The eval/tuning loop is named the
  first of three A-4 exhibits.
- **Lead AL-1** — the open over-suppression regression: grounding tightening is
  suspected to have cut suggested-bullet counts. Detecting and measuring that is
  a domain obligation, not an optional nicety.

Generic best practice (FActScore-style claim decomposition, NLI faithfulness,
human-label calibration) is already reflected in the design
(`docs/dev/GROUNDING_METRIC.md`). Where best practice and the charter differ,
the charter wins: e.g. T-A/M-1 deliberately choose *per-user* tuning on one
corpus over population averages — so a "more fixtures, more generality" instinct
is the wrong frame here.

## 2. Current state pointers

**Strengths (name them).**
- The three-tier detector ladder is a genuinely sharp reframe: hallucination as
  *attribution against a closed source*, split by class with severity-weighting
  (`docs/dev/GROUNDING_METRIC.md` §reframe + §detector-ladder@c6e0437). L0 is
  deterministic, hot-path-safe, and ships uncalibrated by design; L1/L2 stay
  eval-only behind `--grounding-signals` (`evals/grounding_signals.py@c6e0437`).
- The annotate→tune→verify loop is built and **driveable from the browser** —
  bootstrap → annotate → "Score grounding" → A/B (`dashboard/routes.py`,
  `evals/README.md` §"in-browser tuning console"@c6e0437). The annotation
  contract is fail-closed and LLM-free (`evals/annotation.py:203`), and
  `_scorer_disagreements` (`annotation.py:487`) operationalizes the M-2 criterion
  "annotations validate the automated scorers."
- A/B is non-polluting: candidate runs stamp `prompt_version=candidate:<hash>`
  via `analyzer.prompt_overrides()` (`analyzer.py:290`, registry at `:2873`);
  the default path is byte-identical, so the analyze→generate cache is untouched.
- Promote stays manual by design (`evals/README.md` §6; dashboard tuning banner)
  — a deliberate human gate consistent with C-4.

**Gaps (charter-traced).**
- **`evals/fixtures/real/` is empty** (`.gitkeep` only@c6e0437); no
  `bootstrap.json` / `annotations.json` / seed exists anywhere. The v1.0.4
  machinery's *live run was never executed* (`GROUNDING_METRIC.md` §calibration).
  This directly blocks M-2 ("loop exercised end-to-end") and T-D ("machinery
  never yet exercised on real data"), and means L1/L2 are **uncalibrated** —
  their precision/recall against human labels is unmeasured.
- **No lay metrics legend.** The groundedness pane surfaces raw technical labels
  — "fabricated rate", "flagged", "L0", `prompt_version`
  (`dashboard/templates/dashboard.html:300-318@c6e0437`) — with no plain-language
  legend. Blocks S-3 and the M-2 v1.0.7 "lay metrics legend" criterion.
- **AL-1 has no instrument.** Suggested-bullet count is shaped by the
  `recommend` drop-off rule (`TUNING_LOG.md` 2026-05-24 entry; `_dropoffPick` in
  `static/app.js`), and PROMPT_VERSION moved ~20 times since 2026-05-09
  (git log on `analyzer.py`), but no metric tracks bullet *count* over
  PROMPT_VERSION history — so the suspected over-suppression is currently
  unfalsifiable from data.
- The dashboard loads Chart.js from CDN (`dashboard.html:15`) — a C-2 violation
  already ruled (fix v1.0.6, PX-01); noted because the diagnostics surface is in
  scope here.

## 3. Rubric

- **BOOST** — A run of the real loop end-to-end producing labels, then a measured
  L0/L1/L2 precision-recall number against those labels (closes M-2 + T-D); an
  AL-1 instrument (suggested-bullet count charted over PROMPT_VERSION) that turns
  the suspicion into a decidable signal.
- **KEEP** — The three-tier attribution reframe; the dynamic source-union scoring;
  candidate-quarantine via `prompt_overrides`; fail-closed annotation contract;
  manual promote; hot-path discipline (only L0 in production).
- **FIX** — Lay metrics legend in the groundedness/diagnostics panes (S-3); the
  user-facing "how it grounds/clarifies/tunes" page (M-2 v1.0.7); CDN Chart.js
  (C-2). Surface the empty-real-fixtures state as a tracked release task, not a
  silent gap.
- **DEBUFF** — Treating L1/L2 numbers as trustworthy before calibration; any
  grounding tightening shipped without checking suggested-bullet impact (re-opens
  AL-1); marketing-register or absolute claims about grounding (C-0).
- **WATCH** — Paraphrase/implication false positives (the precision killer,
  `GROUNDING_METRIC.md` §hard-parts); entity aliasing; whether the dashboard's
  power-user surfaces meet the same a11y bar as the wizard (E-2, R2-12.2).

## 4. Sharpest questions

(Carried to the assessment question bank — see structured output.)

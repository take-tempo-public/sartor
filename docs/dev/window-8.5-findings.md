# v1.0.8 gated test window — findings backlog (Sprint 8.5, PV-1)

> **Purpose:** the **one numbered, triaged findings backlog** produced by the
> v1.0.8 gated test window (RELEASE_ARC §"Gated test window + correction"). It is
> the **single authoritative hand-off to 8.6** (`fix/window-findings-*`): 8.5
> *generates* this list; 8.6 *burns* it. Findings come from three sources — the
> E2E user+dev walkthrough, the PV-1 real-data eval/annotation loop, and the S3
> vector-tier before/after eval.
> **Audience:** the 8.6 correction-sprint agent; the owner.
> **Companion:** the walkthrough runbook
> [`window-8.5-walkthrough.md`](window-8.5-walkthrough.md). Scoring + tuning
> provenance is in [`../../evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md).
> **Status:** GROUNDING SLICE BURNED on 8.6 `fix/window-findings-grounding`
> (2026-06-23) — EV-1 / EV-2 / EV-3 / S3-1 resolved; PV-1 labels + PV-2 calibration
> **staged** (owner-gated). PV-3 cover-letter tone → sibling `fix/window-findings-tone`;
> the `/wiki-ingest` app.py-cite re-anchor → folded into 8.6a. See the **Resolution**
> section at the foot of this file. Findings were observed/triaged here on 8.5; **no
> fixes landed on 8.5** (the window did not burn its own backlog).

---

## Boundaries (do not violate when filling this in)

- **PII-free.** Finding text describes behavior, never résumé/JD content. The raw
  run evidence stays in the separate E2E clone (memory `project-e2e-instance-location`)
  / gitignored `evals/fixtures/real/`.
- **Observe, don't fix.** Each row is a triaged observation. Fixes are 8.6.
- **One row per finding**, numbered. Walkthrough findings keep the `KW#` prefix;
  eval/annotation findings use `EV#`; S3 verdict is a single `S3` note.

Severity: **HIGH** (blocks flow / data loss / security) · **Med** (degraded but
survivable) · **Low** (copy/polish). Bucket: **8.6** (correction sprint) · **8.6a**
(assistant doc-coverage) · **8.7** (public-prep) · **defer** (conscious v1.0.9+).

---

## 1. E2E walkthrough findings (KW#)

**Status: DEFERRED (owner decision, 2026-06-23).** The E2E user+dev walkthrough (R2
verified live) is the one 8.5 generation deliverable not yet run — it is owner-manual in
the separate E2E clone (memory `project-e2e-instance-location`). Per the close-out decision, 8.5's completed work (flaky fix, S3
verdict, the PV-1 shakedown findings) merges now; the walkthrough is carried forward as a
tracked 8.5-remainder item (RELEASE_CHECKLIST 8.5 + Carry-forward ledger). It can be run
against `main` (the decomposed code is already there) using
[`window-8.5-walkthrough.md`](window-8.5-walkthrough.md); KW findings get appended to this
table and triaged into 8.6.

| KW# | Finding | Area (step/seam) | Severity | → bucket |
|---|---|---|---|---|
| _(walkthrough not yet run — deferred)_ | | | | |

## 2. PV-1 real-data eval / annotation findings (EV#)

First real-data run, 2026-06-23: candidate `testuser` (real corpus: 5 exp / 66 bullets
/ 9 skills / 4 summaries), 3 JDs (the synthetic `data-scientist-junior`, `pm-senior`,
`sre-mid-level` against the real corpus). **Positive result: the real
corpus→context→generate path works end-to-end** — all 3 pipelines completed
(analyze→clarify→generate) and produced bullets+skills (19/13, 23/13, 21/12). The
window's purpose-built failures surfaced at the *grounding* + *seed-export* edges,
exactly the so-far-unexercised paths.

| EV# | Finding | Stage | Severity | → bucket |
|---|---|---|---|---|
| EV-1 | **L2/MiniCheck grounding scorer broken by an unpinned git dep.** `minicheck @ git+https://github.com/Liyan06/MiniCheck.git` (pyproject `eval-grounding`) is **unpinned**, so a fresh install pulled a drifted incompatible major version: default model is now `Bespoke-MiniCheck-7B` (vLLM/`tensor_parallel_size`), and `MiniCheck.__init__` no longer accepts `device` or `flan-t5-large`. `evals/grounding_signals.py:75` passes `device="cpu"` → `TypeError` → the `--grounding-signals` bootstrap aborts. Also: installed `transformers` is **5.10.2**, violating the `transformers>=4.40,<5.0` pin; CONTRIBUTING.md:125 still documents the stale `flan-t5-large`. The "never-run v1.0.4 live loop" latent breakage. **Blocks the #4 L1/L2 labels.** | bootstrap (grounding) | **HIGH** | 8.6 (PV-2) |
| EV-2 | **An optional `--grounding-signals` failure discards the completed paid pipeline work.** `build_bootstrap_document` (`evals/bootstrap.py:251`) calls `grounding_fn(...)` with **no try/except**, so the EV-1 crash aborted the whole bootstrap *after* ~$0.60 of analyze→clarify→generate had run — `bootstrap.json` was never written. The optional enhancement should fail soft (log, `grounding=None`, still persist the doc). | bootstrap | Med | 8.6 |
| EV-3 | **`export_corpus_seed.py` crashes on its success print (Windows).** `UnicodeEncodeError` on the `→` char (cp1252 console) *after* the seed wrote — exits non-zero, breaking any chaining script. Workaround: `PYTHONIOENCODING=utf-8`. The seed itself is fine. | seed export | Low | 8.6 |

### PV-1 run summary (scores only — no PII)

Bootstrap pipelines (production prompt `PROMPT_VERSION` unchanged): data-scientist-junior
→ 19 bullets / 13 skills / 5 clarify Qs; pm-senior → 23 / 13 / 5; sre-mid-level → 21 /
12 / 5. The real-suite **eval run (`runner.py --suite real`) is pending the annotation
+ collate** (blocked below). Full provenance to TUNING_LOG.md once it runs.

### #4 grounding-calibration labels — provenance for 8.6 PV-2

**Status: partially blocked by EV-1.** The L0 deterministic layer
(`hardening.compute_fabricated_specifics`) is always available; the L1 NLI scorer
(DeBERTa) loaded fine in this run; **L2/MiniCheck is broken (EV-1)**, so a full
L0+L1+L2 pre-scored label set cannot be produced until 8.6 reconciles the minicheck
dependency. 8.5 will produce the **L0-pre-scored + human-verdict** labels (the
annotation surface); 8.6 PV-2 fixes minicheck, backfills L1/L2, and calibrates. Labels
live in gitignored `evals/fixtures/real/testuser/`.

## 3. S3 vector tier — before/after relevance verdict (ledger #2)

The gate-override validation owed at this window: does the S3 `VectorSource` tier earn
its `numpy` + `model2vec` footprint? Measured 2026-06-23 on the decomposed code with a
freshly-rebuilt index, via `scripts/vector_index_probe.py` (qualitative) +
`scripts/vector_before_after_eval.py` (judge-scored). Retrieval corpus = committed
wiki+code (project-global, no PII); run JSONL in gitignored `evals/results/`.

**Judge-scored before/after relevance** (12 dev-vocab questions, top-k=6, Haiku judge):

| Metric | Base (wiki+git+session) | +S3 vector | Delta |
|---|---|---|---|
| Mean judge relevance (0–5) | 1.12 | 2.58 | **+1.46 (+130%)** |
| Questions improved | — | — | 8/12 |
| Questions regressed | — | — | 1/12 |
| S3 added a lexical-missed cite | — | — | 12/12 |

**Verdict: KEEP.** S3 more than doubles judge-scored retrieval relevance (1.12 → 2.58)
and surfaces a relevant cite the lexical tiers missed on every question. The qualitative
probe's "0/12 lexical misses" is *not* evidence against S3: `git grep` returns hits on
all 12, but the judge scores those lexical-only sets at 1.12/5 — many hits, few relevant;
the semantic tier is what supplies relevance. The `numpy`+`model2vec` deps earn their
keep; **no demote at 8.6.** _Caveat: directional signal on a small N=12 dev-vocab set, not
a precision/recall study; absolute relevance (2.58) is still only "partially relevant",
so retrieval quality remains a longer-term improvement area._

### S3-1 — vector index is stale after the blueprint split (→ 8.6) · Med

The committed-code index (built 2026-06-16, `feat/doc-assistant-vector`) cited
**pre-blueprint `app.py` line numbers** (`app.py:301/721/991/3421/4921`) that no longer
hold those routes after the 8.3 split (landed 06-22). Rebuilding
(`python -m scripts.build_vector_index`, free/LLM-free) re-anchored every cite onto the
decomposed code (`blueprints/corpus/curation.py:241`, `blueprints/analysis.py:541`,
`recall/sources/vector_source.py:331`). The rebuild is **local + gitignored**, so it does
not persist — the index has no committed rebuild trigger and silently staled with the
split. **→ 8.6:** pair an index rebuild with the planned `/wiki-ingest` re-anchor pass;
consider a freshness check (index sha vs HEAD) so the assistant never cites moved lines.

---

## Triage roll-up (for 8.6 planning)

As of branch close (2026-06-23), pre-walkthrough:

- **→ 8.6 (correction sprint): 4** — EV-1 (minicheck dep drift, HIGH; gates PV-2),
  EV-2 (grounding-abort discards work, Med), EV-3 (seed-export unicode crash, Low),
  S3-1 (vector index stale post-split, Med).
- **→ 8.6 PV-2 (blocked-then-do):** PV-1 L1/L2 label production — blocked on EV-1; do the
  full bootstrap+annotate+eval in one pass after the minicheck fix.
- **Resolved on 8.5:** S3 vector tier KEEP verdict (Carry-forward #2); the flaky
  Compose-wizard UX race (ledger #3, test-only).
- **Deferred (8.5 remainder):** the E2E walkthrough + R2-live verification (§1) — owner
  runs it against `main`; its KW findings append here and triage into 8.6.

Net: the highest-leverage item for 8.6 is **EV-1** — it must be fixed before PV-2 can
produce calibratable L1/L2 labels, so it should lead the correction sprint.

---

## Resolution — 8.6 `fix/window-findings-grounding` (2026-06-23)

The **grounding slice** of this backlog burned on the first 8.6 sub-branch
(`fix/window-findings-grounding`, owner-confirmed split). PV-3 cover-letter tone → sibling
`fix/window-findings-tone`; the `/wiki-ingest` `app.py`-cite re-anchor → folded into **8.6a**
(`docs/assistant-wiki-coverage`, which already rewrites wiki pages).

- **EV-1 — RESOLVED.** `minicheck` pinned to `b58b9fa…` in `pyproject.toml` (was an unpinned
  `git+` ref). **Correction to this finding's root-cause text** (verified against the installed
  package, a `reference-prescription-metrics-can-restale`-class drift): `flan-t5-large` was **NOT
  dropped** — it is still a valid `model_name` routing through the non-vLLM CPU `Inferencer`; and
  `MiniCheck.score()` still returns the **4-tuple** the code already unpacked (its `-> List[float]`
  annotation is simply wrong). The **actual** breaks were (a) the dropped `device` kwarg
  (`grounding_signals.py`) and — surfaced only by running it end-to-end — (b) `transformers>=5`
  needs **`accelerate`** for the `device_map="auto"` the loader uses, and (c) NLTK's **`punkt_tab`**
  tokenizer data isn't auto-present. **Fix:** drop `device`; add `accelerate>=1.0` + declare
  `nltk>=3.9`; auto-ensure `punkt_tab` in `_load_minicheck_scorer`; widen the transformers cap to
  `<6.0` (validated on the installed 5.10.2). **Validated end-to-end on CPU** — L1 NLI mean 0.995,
  L2 MiniCheck mean 0.973.
- **EV-2 — RESOLVED.** `build_bootstrap_document` now wraps the optional `grounding_fn` call in
  `try/except` (log + `grounding=None` + still return the doc), so a scorer failure never discards
  the completed (paid) pipeline work. The browser bootstrap route was reconciled (its now-redundant
  try/except folded into an outcome-derived note) and a unit test added
  (`test_grounding_fn_failure_is_soft_doc_still_built`).
- **EV-3 — RESOLVED.** Both `export_corpus_seed.py` and `capture_screenshots.py` reconfigure
  `stdout`/`stderr` to UTF-8 at entry. (The per-char ASCII approach the finding implied missed the
  `--help`/`__doc__` argparse path **and** ~30 progress prints in `capture_screenshots.py`; the
  reconfigure fixes the whole class.) Verified exit 0 — success print **and** `--help` — under a
  forced cp1252 console. **Correction + fix (2026-06-23, PV-3):** "the whole class" was scoped to
  those **two scripts** — `evals/runner.py` was **not** reconfigured and crashed on `--help` (the
  `→` epilog) / any `→` print under cp1252. Surfaced while running the PV-3 validation harness
  (worked around with `PYTHONIOENCODING=utf-8`); **the owner directed folding the 1-line fix in
  before the merge**, so `runner.main()` now carries the same
  `sys.stdout`/`sys.stderr.reconfigure(encoding="utf-8")` loop — verified exit 0 on `--help` plain
  **and** under forced `PYTHONIOENCODING=cp1252`. Resolved (RELEASE_CHECKLIST Carry-forward ledger).
- **S3-1 — RESOLVED.** `scripts/build_vector_index.py` now writes a `manifest.json`
  (`built_at_sha`) on build and has a `--check` staleness mode (manifest sha vs HEAD) + a unit
  test. The local index was rebuilt (`--full`, 3239 chunks re-anchored onto `blueprints/**`). The
  index stays gitignored/local; the **freshness check is the committed durable guard** against
  silent re-staling.
- **PV-1 labels + PV-2 calibration — STAGED (owner-gated).** EV-1 unblocked the loop and the L0+L1+L2
  scorers are proven to run on CPU. Full label production + calibration is owner-gated (manual
  browser annotation) and **may spill to v1.0.9** per RELEASE_ARC §4.8. The `testuser` seed is
  ready at the gitignored `evals/fixtures/real/testuser/seed.json`. Remaining steps: bootstrap
  (`--grounding-signals`) → owner annotate → collate → `runner.py --suite real --seed …` → PV-2
  metric calibration.

## Resolution — 8.6 `fix/window-findings-tone` (PV-3 cover-letter tone, 2026-06-23)

The **second 8.6 sub-branch** (sibling to the grounding slice). PV-3 is a RELEASE_ARC §4.8
deliverable, **not** an EV/S3 finding from this backlog — recorded here only because the sub-branch
series lives under `fix/window-findings-*`.

- **PV-3 — DONE.** Reinforced the existing throat-clearing/hedging cover-letter bans (the v1.0.3
  `tone` 2.1 was an *adherence* slip) by adding a `WORKED EXAMPLES` OK/NOT-OK opener+close sub-block
  to `_COVER_LETTER_RULES_BLOCK` and **de-cloning** the single Para-3 close example the model was
  copying near-verbatim into the lapse. **`PROMPT_VERSION 2026-06-13.1 → 2026-06-23.1`** (the only
  prompt bump in the v1.0.7/v1.0.8 epics; `AVATAR_PROMPT_VERSION` untouched, no new dep). Validated
  with a paired before/after `--suite synthetic --subset full` n=3: **tone held at the 4.2 floor,
  no regression on any rubric**; the opener/close fix is judge-confirmed adopted; the one sub-4.0
  after-sample (pm 3.2) was a scenario-specific gap-admission hedge — a *different* tone failure
  mode (logged as a future-tuning learning, not folded in). New deterministic test
  `TestCoverLetterWorkedExamples`. Full tables + lessons: [`../../evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md)
  (2026-06-23 PV-3 entry). A latent `evals/runner.py` cp1252 crash (EV-3 class, not covered by the
  grounding fix) was surfaced + filed to the Carry-forward ledger (see the EV-3 correction above).

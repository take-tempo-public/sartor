# Full-system verification — everything since the v1.0.1 end-to-end

> **Purpose:** a human-driven, real-corpus walkthrough that verifies the **cumulative
> change set across v1.0.2 → v1.0.5** — i.e. everything built since the last
> full end-to-end test at v1.0.1. It is structured so the v1.0.5 release cut can
> use it as evidence, but it deliberately re-verifies the three internal releases
> (v1.0.2/v1.0.3/v1.0.4) that never got a hands-on E2E because they were dev/eval
> tooling. Tick items off; record results in the sign-off block.
> **Audience:** the human cutting the release (and any agent asked to re-verify).
> **Authoritative for:** nothing — it is *evidence*, not contract. Branch sequence
> + tag criteria live in [`RELEASE_ARC.md`](RELEASE_ARC.md); open/deferred items in
> [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md); per-release detail in
> [`../../CHANGELOG.md`](../../CHANGELOG.md).
> **Companion:** [`AGENT_FAILURE_PATTERNS.md`](AGENT_FAILURE_PATTERNS.md) (5a — get
> the real data point before assuming a bug).

---

## What this covers

| Release | Theme | Verified in |
|---|---|---|
| **v1.0.2** | Eval apparatus + applications tracker | Part A |
| **v1.0.3** | R1 Phase 2 — two-pass analyze, clarify→Haiku | Part B |
| **v1.0.4** | Eval tuning loop (export → bootstrap → annotate → collate → tune) | Part C |
| **v1.0.5** | UI/UX redesign + diagnostics console + annotation tab | Part D |

Per-release branch lists are in [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 1–4 and
the dated [`CHANGELOG.md`](../../CHANGELOG.md) sections.

## How to use this

- Work **top to bottom** — Part A/B populate `logs/llm_calls.jsonl` and
  `evals/results/*.jsonl` that the dashboard (D §7), grounding (D §8), and
  annotation (D §9) steps read.
- **💲** marks steps that spend real Anthropic credits. Rough budget for one full
  pass: a wizard run ≈ $0.30–0.60; a synthetic eval ≈ $0.10–1.50; the same eval
  `--grounding-signals` adds only local CPU time; an annotation bootstrap over
  3 JDs ≈ $0.40 + ~4 min.
- Keep **browser DevTools → Console** open throughout. The UX suite's sentinel is
  unconditional (any `console.error` / `pageerror` / HTTP 5xx fails CI), so the
  console should stay clean during the manual walk too.
- A failure matching the **Known-deferred** list at the bottom is **not** a
  regression — it is already tracked.

---

## Setup — clean copy

A fresh `git clone` of the local repo gives a pristine tree with **none** of your
gitignored real data (DB, `.api_key`, `configs/*.config`, `output/`, `logs/`,
`evals/fixtures/real/`) — so you exercise the true first-run state with a fresh
corpus, and validate the install path (risk-register D.4) at the same time.

```powershell
# 0. Stop the original server first — both bind :5000 (app.run port is hardcoded).
#    Run from INSIDE your working clone; this creates a sibling throwaway `sartor-clean`.
git clone . ..\sartor-clean
Copy-Item .\.api_key ..\sartor-clean\.api_key
cd ..\sartor-clean
python app.py            # → http://localhost:5000  (fresh DB created on first request)
```

Notes (verified on a machine that already builds/runs the app):

- **No venv needed.** The base app, the full `pytest`/`pytest -m ux` gate, and the
  Chromium binary are already in your global Python; the clone is isolated by
  *folder* for all data. A venv would force reinstalling the whole stack — more
  work, no benefit here.
- **Grounding stack is the only thing missing** (`torch`, `transformers`,
  `minicheck`). Install it **into your existing Python, by name** (installing
  `-e ".[eval-grounding]"` from the clone would repoint your editable `sartor`
  at the clone):
  ```powershell
  python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  python -m pip install transformers "minicheck @ git+https://github.com/Liyan06/MiniCheck.git"
  python -c "import torch, transformers, minicheck; print('grounding ready')"
  ```
  First `--grounding-signals` run downloads ~3.2 GB of weights to
  `%USERPROFILE%\.cache\huggingface\` (outside any repo; shared; one-time).
- A committed **`testuser`** fixture (synthetic "Casey Rivera") is present — ignore
  it for real-corpus testing; create your own user.
- To tear down: delete the `sartor-clean` sibling folder. Self-contained; touches nothing in
  your original clone (the HF model cache survives, by design).

---

## 0. Pre-flight

- [ ] `python app.py` → http://localhost:5000 loads; DevTools console clean.
- [ ] `git log --oneline -3` shows the v1.0.5 merges on `main`.
- [ ] Baseline gate green before touching anything: `python -m pytest -q` and
      `python -m pytest -m ux -q`.

---

# Part A — v1.0.2 (eval apparatus + applications tracker)

## A1. Applications tracker (the user-facing half) — `eval/applications-tracker`, `feat/tracker-notes-and-timestamps`, `chore/tracker-status-schema-cleanup`

In Step 1's **Prior applications** panel (you'll have cards after Part B runs an
application; or use an existing app):

- [ ] Status semantics render per the canonical 5-status model:

      | DB status | Chip label | Timestamp |
      |---|---|---|
      | draft | DRAFT | updated_at |
      | submitted | NO RESPONSE | "Sent · X ago" |
      | interview | INTERVIEW | "Outcome · X ago" |
      | rejected | REJECTED | "Outcome · X ago" |
      | withdrawn | WITHDRAWN | "Outcome · X ago" |

- [ ] A **submitted** card shows inline outcome buttons: **Got Interview /
      Got Rejection / Withdrew**. Click one → chip + timestamp update to the
      outcome state.
- [ ] Click a card body → the **application detail modal** opens (title, company,
      status chip, sent/outcome timestamps, **notes textarea**) — not a toast.
- [ ] Type in the notes textarea, click elsewhere → **saves on blur** (reload →
      the note persists; `GET /api/applications/<id>` returns it).
- [ ] No `offer` / `accepted` / `no_response` statuses appear anywhere (removed in
      migration 0007).

## A2. Eval apparatus — `eval/pydantic-response-models`, `eval/baseline-v1-0-2`, `eval/anchor-and-pr-gate`, `eval/sartor-metrics`, `eval/pareto-dashboard`, `eval/grounding-signals` — 💲

- [ ] **Anchor suite + schema v3 + sartor metrics + composite:**
      `python evals/runner.py --suite anchor --subset smoke` runs clean. Inspect
      the newest `evals/results/*.jsonl`: records carry `schema_version: 3`,
      `suite: "anchor"`, `anchor_version`, `phase_latencies_ms`,
      `baseline_comparison`; a `callback_likelihood` rubric row and an
      `eval_composite` record are present; deterministic metrics include
      `top_third_density` + `quantification_rate`.
- [ ] **Baseline + PR-gate behavior:** the run compares against
      `evals/results/baseline_v1.json` (schema 3, 5-run mean/stdev). A regression
      > 0.5 makes `runner.py` **exit code 2** (`echo $LASTEXITCODE` in PowerShell);
      a clean run within tolerance exits 0. (`.github/PULL_REQUEST_TEMPLATE.md`
      documents the gate; Promptfoo via `promptfooconfig.yaml` is optional and
      needs the Node `promptfoo` CLI — skip unless installed.)
- [ ] **Pydantic models** (transparent): no `_parse_or_retry` "missing keys" errors
      in the run; a malformed model response would surface a Pydantic error in the
      retry — nothing to do but confirm runs don't error.
- [ ] **Pareto dashboard panel:** `/_dashboard` → **Quality** tab → **Pareto**
      tile → drawer shows the quality-vs-latency bubble scatter + latency/cost
      trends + a most-recent-change verdict (Pareto-improving / On frontier /
      Dominated). (Needs ≥1 `eval_composite` record from the run above; ≥2
      prompt_versions for the verdict.)
- [ ] **Grounding signal scorers** (now installed): re-run with
      `python evals/runner.py --suite anchor --subset smoke --grounding-signals`.
      Records gain a non-null `grounding_signals` block (NLI + MiniCheck per
      bullet); the **Groundedness** tab composite enriches to **L0+L1+L2** (see
      D §8). First run downloads the weights (~3.2 GB, one-time).

---

# Part B — v1.0.3 (R1 Phase 2: two-pass analyze + clarify→Haiku) — 💲

Run one real application (this also feeds the dashboard in Part D). Most of R1 is
internal, but it is observable:

- [ ] **Two-pass analyze, streamed:** on Analyze, the status label swaps
      **"Extracting JD signals…" → "Analyzing positioning…"** (the
      extraction→synthesis `phase` sentinel).
- [ ] **Trace shows both passes:** after the run, `/_dashboard` → **Pipeline** →
      **Trace** tile → the waterfall lists **`analyze_extraction`** (Haiku) **and**
      **`analyze_synthesis`** (Sonnet) as separate spans, then `generate`.
- [ ] **Speed budget:** combined analyze **p50 ≤ 72s** — eyeball the Trace total /
      Latency tile, or `python -m scripts.perf_baseline` against `logs/llm_calls.jsonl`.
- [ ] **clarify on Haiku:** `/_dashboard` → **Pipeline** → **Cost** tile →
      cost-by-call-kind shows `clarify` on the Haiku model and materially cheaper
      than the Sonnet calls (~$0.007/call).
- [ ] **Typed hidden_qualities:** Step 1 analysis renders each hidden quality as
      **`[category] signal`** (operating_context / scope_of_ownership /
      stakeholder_gravity / resilience) — never `[object Object]`.
- [ ] **context_probe:** when hidden_qualities are present, the Step 2 clarify set
      contains **≥1** context/scope probe.
- [ ] **No regressions from removed keys:** analysis renders fully (the removed
      `ats_improvements` / `ideal_resume_profile` keys had no consumer — nothing
      should be missing in the UI).

---

# Part C — v1.0.4 (eval tuning loop — CLI / headless + prompt-override) — 💲

The loop's polished UI is the v1.0.5 Annotate tab (D §9); here, verify the
underlying CLI/headless machinery and the override primitive.

- [ ] **Corpus seed export:** `python -m scripts.export_corpus_seed --user <name>`
      → writes `seed.json` under `evals/fixtures/real/<name>/` (deterministic,
      LLM-free). The write-path guard refuses any target outside
      `evals/fixtures/real/`.
- [ ] **Corpus-backed runner:** with a fixture that has an `expected.json` (produce
      one via D §9 collate, or the annotation CLI below),
      `python evals/runner.py --suite real --seed evals/fixtures/real/<slug>/seed.json`
      builds context from the imported corpus (the real corpus→context path) and
      grades against the fixture. Absent `--seed`, the file-based path is unchanged.
- [ ] **Bootstrap engine (CLI, with grounding pre-scores):**
      `python -m evals.bootstrap --seed <seed.json> --jd-dir <dir-of-JDs> --grounding-signals`
      → `bootstrap.json` whose `grounding_signals` is populated (NLI/MiniCheck per
      cluster). Opening this fixture in the Annotate tab (D §9) shows the
      pre-scores the browser-produced bootstrap leaves blank.
- [ ] **Annotation contract (CLI):**
      `python -m evals.annotation --bootstrap <bootstrap.json> --emit-template` →
      blank `annotations.json`; fill verdicts; `… --collate --annotations <…> --jd-dir <…>`
      → `expected.json` + anchor `jd.txt` + `improvement_brief.md`. (The browser
      tab in D §9 wraps this same contract — same file format.)
- [ ] **Prompt-override primitive (A/B):** create `cand.json`
      (e.g. `{"SYSTEM_PROMPT": "<edited persona text>"}`) and run
      `python evals/runner.py --suite anchor --subset smoke --prompt-overrides cand.json`.
      Verify the result records + telemetry stamp `prompt_version=candidate:<hash>`
      (quarantined from score-over-time), and that a **default** run (no flag) still
      logs the real `PROMPT_VERSION` and is byte-identical (cache_read unchanged).
- [ ] **Delta helper:** `python -m evals.tune --baseline <A.jsonl> --candidate <B.jsonl>`
      prints per-(fixture×rubric) baseline-vs-candidate deltas with regression flags.
- [ ] *(Optional, Claude Code only)* the `/prompt-tune` and `/tune-from-annotations`
      skills drive the above interactively; not required for system verification.

---

# Part D — v1.0.5 (UI/UX redesign + console + annotation tab)

## 1. Onboarding + real corpus

- [ ] Create/select a real user; **+ Import résumé** with a real `.docx`/`.pdf`/`.md`.
- [ ] Corpus tab renders cards with bullets on **first** load (no blank list, no
      console error).
- [ ] Import a **second** résumé → identical bullets dedupe; new bullets survive.

## 2. Wizard end-to-end — 💲

**Step 1 — Analyze** (also covers B's phase sentinel + typed hidden_qualities).
- [ ] Paste JD → Analyze: streams; phase label swaps; analysis populates; rail
      re-enables Step 2 immediately.

**Step 2 — Clarify**
- [ ] **Get interview questions** → 3–5 questions incl. ≥1 context/scope probe;
      answer + submit.

**Step 3 — Compose** (`feat/bullet-drag-reorder`)
- [ ] Instructional line + grab handle (≡) present.
- [ ] **Drag** a bullet to reorder — it moves and stays.
- [ ] **Keyboard:** Move up / Move down buttons reorder without a mouse.
- [ ] **Reset to AI ranking** restores score order; disabled when no custom order.
- [ ] Pin / exclude / add a bullet; pick a summary variant.

**Step 4 — Template** (`feat/template-pagination`)
- [ ] Cycle **all four** personas (Classic, Modern, Spacious, Tech) — preview
      renders for each.
- [ ] **No blank/short pages** between sections on any template (real long content
      is the real test); page-count chip looks right.

**Step 5 — Generate**
- [ ] 💲 **Generate** streams; Step 6 opens.

**Step 6 — Output redesign** (`feat/step6-redesign`)
- [ ] Preview at the **top**; old raw/rendered tabs + toggle **gone**; **Changes**
      is an info-icon modal; cover letter is a single **+ Generate** button until
      generated. Edit-raw modal edit → preview updates.

## 3. WYSIWYG parity (`feat/wysiwyg-option1`)
- [ ] Compare Step 6 **preview** vs **downloaded** file (same persona); download
      **.docx / .pdf / .md** (allow Chrome's multi-download prompt).
- [ ] **.pdf == preview** (same bullets, wording, order — incl. your §3 reorder);
      **.docx** matches the persona's style. Divergence here is the headline catch.

## 4. Cover letter formats (`feat/cover-letter-formats`) — 💲
- [ ] **+ Generate cover letter** → download **.docx / .pdf / .md**.
- [ ] Business-letter styling: terser header (no name banner), dense/near-single
      spacing, **inline** addressee block; fonts match the chosen template.

## 5. Iterate loop
- [ ] Edit preview → **Refine / Iterate-clarify** 💲 → answer → **Generate again**.
- [ ] New child context (parent_context_path chain); output reflects edits +
      answers without inventing facts.

## 6. Prior-application resume (`feat/prior-app-resume`)
- [ ] Step 1 **Prior applications** → click a card → detail modal (A1) →
      **Resume** → loads context + persona + last résumé/cover letter and jumps to
      the most advanced step with data (typically Step 6). Not the old toast.

## 7. Diagnostics console (`feat/diagnostics-console-redesign`) — `/_dashboard`
- [ ] Tabs render: **Pipeline · Quality · Groundedness · Tuning · Annotate**;
      switching works; console clean.
- [ ] **Pipeline:** each tile (Cost, Throughput, Reliability, Trace, Latency)
      opens the shared drawer; charts render; **Trace** shows your real run's
      `analyze_extraction → analyze_synthesis → generate` waterfall + `run_id`;
      Esc / ✕ close.
- [ ] **Quality / Groundedness** populate after Part A's eval; **Tuning** shows the
      read-only scaffold banner.
- [ ] **Localhost guard:** request with `Host: evil.example` → **403**.

## 8. L0 (+L1/L2) grounding metric (`eval/grounding-metric-l0` + `eval/grounding-signals`) — 💲
- [ ] After Part A's `--grounding-signals` eval, `/_dashboard` → **Groundedness**:
      score tile (0–5) + trend, fabricated-specifics rate, **flagged-samples** +
      per-bullet evidence in the drawer; the layers read **L0+L1+L2** (vs L0-only
      without the flag).
- [ ] (Optional) `python -m pytest tests/test_hardening.py -k Fabricated -q`.

## 9. Annotation tab + browser bootstrap wrapper (`feat/annotation-tab`) — 💲
`/_dashboard` → **Annotate**.

**① Bootstrap wrapper (paid live pipeline)**
- [ ] Real candidate username, optional slug, **2–3 real JDs** (name + text) →
      **Run bootstrap**. Progress streams per JD; ends "Bootstrap written"; no
      console error / 5xx. On disk: `evals/fixtures/real/<slug>/bootstrap.json` +
      `jds/`.

**② Pick + ③ Annotate**
- [ ] New fixture appears in the picker; select → editor renders bullet/skill
      clusters + clarification questions. *(NLI/MiniCheck pre-scores blank — the
      browser wrapper skips `--grounding-signals`; for pre-scores use the CLI
      bootstrap in Part C.)*
- [ ] Set a mix of verdicts: `keep`; `fix` (+ honest_rewrite); `fabricated`
      (+ forbidden_pattern regex); `omit`; add a `failed_rules` slug (autocompletes
      from the rubric vocabulary); rate a clarification question.

**Fail-closed Save + Collate**
- [ ] Save with blank verdicts → inline validation error; **no** file written.
- [ ] Fill every bullet/skill verdict → **Save** → `annotations.json` written;
      reload → verdicts round-trip.
- [ ] **Collate** → status reports must_keywords / forbidden_inventions;
      `expected.json` + `improvement_brief.md` + `jd.txt` written. (Run it via the
      corpus-backed runner — Part C — to close the loop.)

**Security spot-check**
- [ ] Nothing written outside `evals/fixtures/real/`; a traversal-y slug sanitizes
      to a safe name.

---

## Final regression gate

- [ ] `python -m ruff check .` → clean
- [ ] `python -m mypy .` → Success (only pre-existing `annotation-unchecked` route
      notes, deferred to the v1.1.0 type scan)
- [ ] `python -m pytest -q` → green (grounding tests mock the models — no
      torch/transformers needed for the gate)
- [ ] `python -m pytest -m ux -q` → green

---

## Known-deferred — do NOT flag as new regressions

Tracked in [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) / [`../PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md):

1. **Compose bullet order visually reverts on reload** *only* for an experience
   with **no LLM recommendations** (`_dropoffPick` re-sorts by score). Persisted
   order is correct and `generate()` honors it — render-path cosmetic on that path.
2. **paged.js console throws are contained, not eliminated** — render completes
   correctly; the vendored polyfill throw is caught. No blank pages = working.
3. **Calibrated-B grounding** is intentionally **not** built — §9's annotation tab
   produces the labels that unblock it pre-v1.1.0; blank NLI/MiniCheck pre-scores
   in the browser path are expected.
4. **`evals/fixtures/real/` starts empty** — until §9/Part-C bootstrap runs, the
   Annotate picker shows its empty-state hint (not an error).
5. **Known below-threshold eval scores** at the v1.0.2 baseline (recovery targets,
   not new regressions): `data-scientist-junior × clarification_quality`,
   `sre-mid-level × iteration_quality` (fixture fragility). See
   [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md).

---

## Sign-off

| Field | Value |
|---|---|
| Verifier | <!-- name --> |
| Date | <!-- YYYY-MM-DD --> |
| Candidate / corpus used | <!-- username --> |
| Commit verified | <!-- git rev-parse HEAD --> |
| Releases exercised | <!-- v1.0.2 / v1.0.3 / v1.0.4 / v1.0.5 --> |
| Result | <!-- PASS / PASS-with-notes / FAIL --> |

**Notes / anomalies (with the real data point per failure-pattern 5a):**

<!-- record any console error, response body, or screenshot here; if it matches a
     Known-deferred item, say so and move on -->

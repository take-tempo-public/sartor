# v1.0.5 — full-system verification checklist

> **Purpose:** a human-driven, real-corpus walkthrough that verifies the **entire
> v1.0.5 change set** (the UI/UX redesign stream) end-to-end before the v1.0.5
> tag is cut. Tick items off and record results in the sign-off block — this file
> doubles as the v1.0.5 release-cut evidence.
> **Audience:** the human cutting the release (and any agent asked to re-verify).
> **Authoritative for:** nothing — it is *evidence*, not contract. The branch
> sequence + tag criteria live in [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4;
> open/deferred items live in [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).
> **Companion:** [`AGENT_FAILURE_PATTERNS.md`](AGENT_FAILURE_PATTERNS.md) (5a — ask
> for the real data point before assuming a bug).

---

## What this covers

The ten merged v1.0.5 branches (RELEASE_ARC §Phase 4):

| Branch | Verified in section |
|---|---|
| `feat/wysiwyg-option1` | §3 |
| `feat/step6-redesign` | §2 (Step 6) |
| `feat/cover-letter-formats` | §4 |
| `feat/prior-app-resume` | §6 |
| `feat/bullet-drag-reorder` | §2 (Step 3) |
| `feat/playwright-ux-suite` | §10 |
| `feat/template-pagination` | §2 (Step 4) |
| `eval/grounding-metric-l0` | §8 |
| `feat/diagnostics-console-redesign` | §7 |
| `feat/annotation-tab` | §9 |

## How to use this

- Work **top to bottom** — earlier steps populate the telemetry/eval/bootstrap
  data that the dashboard (§7), grounding (§8), and annotation (§9) steps read.
- **💲** marks steps that spend real Anthropic credits. Rough budget for one full
  pass: a wizard run (§2/§4/§5) ≈ $0.30–0.60; a synthetic eval (§8) ≈ $0.10–1.50;
  an annotation bootstrap over 3 JDs (§9) ≈ $0.40 + ~4 min.
- Keep **browser DevTools → Console** open throughout. The UX suite's sentinel is
  unconditional (any `console.error` / `pageerror` / HTTP 5xx fails CI), so the
  console should stay clean during the manual walk too.
- A failure that matches the **"Known-deferred"** list at the bottom is **not** a
  regression — it is already tracked.

---

## 0. Pre-flight

- [ ] `.api_key` at repo root (or `ANTHROPIC_API_KEY` set).
- [ ] `python app.py` → http://localhost:5000 loads.
- [ ] `git log --oneline -3` shows merge `8593f99` (feat/annotation-tab) on `main`.
- [ ] Baseline gate green before touching anything: `python -m pytest -q` and
      `python -m pytest -m ux -q`.
- [ ] DevTools console open and clean on first load.

---

## 1. Onboarding + real corpus

- [ ] Create/select a real user; **+ Import résumé** with a real `.docx`/`.pdf`/`.md`.
- [ ] Corpus tab renders experience cards with bullets on **first** load (no blank
      list, no console error).
- [ ] Import a **second** résumé → identical bullets dedupe; genuinely new bullets
      survive.

---

## 2. Wizard end-to-end (the applicant flow) — 💲

**Step 1 — Analyze** (R2 streaming + two-pass split)
- [ ] Paste a real JD → **Analyze**: status swaps **extraction → synthesis**;
      analysis populates; `hidden_qualities` render as `[category] signal`.
- [ ] Rail re-enables Step 2 immediately after analyze.

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
- [ ] Cycle **all four** personas (Classic, Modern, Spacious, Tech) — live preview
      renders for each.
- [ ] **No blank/short pages** between sections on any template (real long content
      is the real test); page-count chip looks right.

**Step 5 — Generate**
- [ ] 💲 **Generate** streams tokens; Step 6 opens.

**Step 6 — Output redesign** (`feat/step6-redesign`)
- [ ] Preview at the **top**; old raw/rendered tabs + toggle **gone**; **Changes**
      is an info-icon modal; cover letter is a single **+ Generate** button until
      generated.
- [ ] **Edit-raw modal** edit → preview updates.

---

## 3. WYSIWYG parity (`feat/wysiwyg-option1`)

- [ ] Compare Step 6 **preview** vs **downloaded** file for the same persona.
- [ ] Download **.docx / .pdf / .md** (allow Chrome's multi-download prompt).
- [ ] **.pdf == preview** (same bullets, wording, order — incl. your §2 reorder);
      **.docx** matches the original persona's style. Divergence here is the
      headline thing to catch with real content.

---

## 4. Cover letter formats (`feat/cover-letter-formats`) — 💲

- [ ] **+ Generate cover letter** → download **.docx / .pdf / .md**.
- [ ] Business-letter styling: terser header (no name banner), dense/near-single
      spacing, **inline** addressee block; fonts match the chosen template.

---

## 5. Iterate loop

- [ ] Edit preview → **Refine / Iterate-clarify** 💲 → answer → **Generate again**.
- [ ] New child context written (parent_context_path chain); output reflects edits
      + answers without inventing facts.

---

## 6. Prior-application resume (`feat/prior-app-resume`)

- [ ] Step 1 **Prior applications** → click a card → loads context + persona +
      last résumé/cover letter and jumps to the most advanced step with data
      (not the old one-line toast).

---

## 7. Diagnostics console (`feat/diagnostics-console-redesign`) — `/_dashboard`

(§2/§5 have populated `logs/llm_calls.jsonl` with real telemetry.)

- [ ] Tabs render: **Pipeline · Quality · Groundedness · Tuning · Annotate**;
      switching works; console clean.
- [ ] **Pipeline:** each tile (Cost, Throughput, Reliability, Trace, Latency)
      opens the shared drawer; charts render; **Trace** shows your real run's
      `analyze_extraction → analyze_synthesis → generate` waterfall + `run_id`;
      Esc / ✕ close.
- [ ] **Quality / Groundedness** sparse until §8 (empty-state, not error);
      **Tuning** shows the read-only scaffold banner.
- [ ] **Localhost guard:** request with `Host: evil.example` → **403**.

---

## 8. L0 grounding metric (`eval/grounding-metric-l0`) — 💲

- [ ] `python evals/runner.py --suite synthetic --subset smoke` (cheap) — or full
      `--suite synthetic` for richer data.
- [ ] Reload `/_dashboard` → **Groundedness**: L0 score (0–5) tile + trend,
      fabricated-specifics rate, **flagged-samples** + per-bullet evidence in the
      drawer. **Quality** now shows pass-rate / heatmap / score-trend / health.
- [ ] (Optional) `python -m pytest tests/test_hardening.py -k Fabricated -q`.

---

## 9. Annotation tab + browser bootstrap wrapper (`feat/annotation-tab`) — 💲

`/_dashboard` → **Annotate**.

**① Bootstrap wrapper (paid live pipeline)**
- [ ] **① Produce a bootstrap**: real candidate username, optional slug, **2–3 real
      JDs** (name + text) → **Run bootstrap**.
- [ ] Progress streams per JD (`analyzing → clarifying → generating → done`); ends
      with "Bootstrap written"; no console error / 5xx.
- [ ] On disk: `evals/fixtures/real/<slug>/bootstrap.json` + `jds/` written.

**② Pick + ③ Annotate**
- [ ] New fixture appears in the picker; select it → editor renders bullet/skill
      clusters + clarification questions with span/size meta. *(NLI/MiniCheck
      pre-scores are blank — the browser wrapper doesn't run the heavy
      `--grounding-signals` scorers; expected.)*
- [ ] Set a mix of verdicts: `keep`; `fix` (+ honest_rewrite); `fabricated`
      (+ forbidden_pattern regex); `omit`; add a `failed_rules` slug (autocompletes
      from the rubric vocabulary); rate a clarification question.

**Fail-closed Save**
- [ ] Save with blank verdicts → inline validation error; **no** file written.
- [ ] Fill every bullet/skill verdict → **Save** succeeds; `annotations.json`
      written; reload → verdicts round-trip.

**Collate**
- [ ] **Collate** → status reports must_keywords / forbidden_inventions; `expected.json`
      + `improvement_brief.md` + `jd.txt` written. Read the brief.
- [ ] (Optional, deeper) export a seed into the same fixture dir
      (`python -m scripts.export_corpus_seed --user <name>`), then
      `python evals/runner.py --suite real --seed evals/fixtures/real/<slug>/seed.json`
      — watch for a slug/path mismatch between the collated dir and the seed dir.

**Security spot-check**
- [ ] Nothing written outside `evals/fixtures/real/`; a traversal-y slug sanitizes
      to a safe name (does not escape).

---

## 10. Final regression gate (`feat/playwright-ux-suite` + the rest)

- [ ] `python -m ruff check .` → clean
- [ ] `python -m mypy .` → Success (only pre-existing `annotation-unchecked` route
      notes, deferred to the v1.1.0 type scan)
- [ ] `python -m pytest -q` → green
- [ ] `python -m pytest -m ux -q` → green

---

## Known-deferred — do NOT flag as new regressions

Tracked in [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) / [`../PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md):

1. **Compose bullet order visually reverts on reload** *only* for an experience
   with **no LLM recommendations** (`_dropoffPick` re-sorts by score). The
   persisted order is correct and `generate()` honors it — render-path cosmetic on
   that one path.
2. **paged.js console throws are contained, not eliminated** — the render
   completes correctly; the vendored polyfill throw is caught. No blank pages =
   working as designed.
3. **Calibrated-B grounding (L1/L2)** is intentionally **not** built — the
   annotation tab (§9) is what produces the labels that unblock it pre-v1.1.0;
   blank NLI/MiniCheck pre-scores in the browser path are expected.
4. **`evals/fixtures/real/` starts empty** — until §9's bootstrap (or the CLI)
   runs, the Annotate picker shows its empty-state hint (not an error).

---

## Sign-off

| Field | Value |
|---|---|
| Verifier | <!-- name --> |
| Date | <!-- YYYY-MM-DD --> |
| Candidate / corpus used | <!-- username --> |
| Commit verified | <!-- git rev-parse HEAD --> |
| Result | <!-- PASS / PASS-with-notes / FAIL --> |

**Notes / anomalies (with the real data point per failure-pattern 5a):**

<!-- record any console error, response body, or screenshot here; if it matches a
     Known-deferred item, say so and move on -->

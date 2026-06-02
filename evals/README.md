# callback. — Eval Harness

A regression-detection system for the project's two-call LLM pipeline. Runs the full `analyze()` + `generate()` flow against fixture inputs with known properties, grades each output against rubrics, and writes results as JSONL for the dashboard and CI.

> If you change a prompt template, upgrade a model, or downstream model behavior shifts, the eval harness tells you whether output quality moved before a real user notices.

---

## Why this exists

The two-call LLM pipeline (`analyzer.analyze` → `analyzer.generate`) is the only fuzzy work in the codebase. Everything else — keyword extraction, ATS checks, document writing — is deterministic Python. A change that subtly degrades the LLM output (a tightened prompt that suppresses good behavior, a model upgrade with a new failure mode, a refactored prompt that loses important framing) is invisible without evals.

The harness fixes this by:
- Running the full pipeline against fixture inputs designed to stress specific failure modes
- Grading each output against rubrics that encode quality criteria
- Emitting structured results so trends are visible across prompt revisions and model versions

This is a **regression detector**, not an absolute benchmark. A score of 5 on a fixture means "no regression detected on this dimension," not "this output is perfect."

---

## Conceptual model

Five things compose an eval run:

| Piece | Lives in | Role |
|---|---|---|
| **Fixture** | `evals/fixtures/{synthetic,real}/{slug}/` | A `(JD, resume, expected.json)` triple. The inputs to grade against. |
| **Rubric** | `evals/rubrics/*.md` | Markdown describing how to score one dimension of output quality. |
| **Runner** | `evals/runner.py` | Orchestrator. Loads fixtures, runs pipeline, dispatches grading, writes results. |
| **Judge** | Claude Haiku 4.5, called from `runner.py` or via `eval-judge` subagent | Reads rubric + payload, emits JSON verdict. |
| **Result** | `evals/results/{timestamp}.jsonl` | One line per `(fixture × rubric)`, structured for the dashboard. |

---

## Quick start

```bash
pip install -e ".[dev]"  # if you haven't already
python evals/runner.py --suite synthetic --subset smoke
```

Runs the 3 committed synthetic fixtures × 1 rubric (`grounding`) — ~9 LLM calls, ~$0.10. Exit code is `0` if every rubric scored ≥4, otherwise `2`.

Results land in `evals/results/{timestamp}.jsonl` and surface in the dashboard at `http://localhost:5000/_dashboard` while the app is running.

---

## Anatomy of a fixture

A fixture lives in `evals/fixtures/synthetic/{slug}/` (committed, public-safe) or `evals/fixtures/real/{slug}/` (gitignored, your own data).

```
evals/fixtures/synthetic/sre-mid-level/
├── jd.txt          ← the job description (plain text)
├── resume.md       ← the candidate's existing resume (markdown, .docx, or .pdf)
└── expected.json   ← what success looks like for THIS fixture
```

### `jd.txt`

Plain-text job description. Length typically 200–500 words. The pipeline treats it the same way it treats any JD pasted into the running app. Synthetic fixtures use fictional companies and roles; real fixtures use your actual JDs.

### `resume.md` (or `.docx` / `.pdf`)

The candidate's source resume. The same `parser.parse_resume()` that the running app uses reads this file and extracts text + section structure.

Markdown is preferred for synthetic fixtures because diffs are reviewable in `git diff`. Real fixtures often use `.docx` because that's what you actually have on disk.

### `expected.json`

Declarative criteria for grading. Schema:

```json
{
  "candidate_name": "Alex Chen",
  "must_keywords": ["sre", "slo", "incident", "observability"],
  "forbidden_inventions": [
    "managed [0-9]+ engineers",
    "saved \\$[0-9]+M",
    "10\\+ years",
    "PhD"
  ],
  "min_grounding_score": 4.0,
  "min_keyword_coverage_score": 4.0,
  "min_ats_format_score": 4.0,
  "min_tone_score": 3.0,
  "notes": "Mid-level SRE, real metrics in source are deliberately qualitative. Watch for invented headcount or dollar figures."
}
```

| Field | Purpose |
|---|---|
| `candidate_name` | Display only; passed into the candidate profile during `_build_context()` |
| `must_keywords` | Strings that MUST appear in the generated `resume_content`. Each absent keyword degrades the `keyword_coverage` score |
| `forbidden_inventions` | Regex patterns that MUST NOT appear in the generated artifacts. Each match degrades the `grounding` score |
| `min_*_score` | Per-rubric pass thresholds (0.0–5.0 scale, one-decimal precision). A score below the threshold = fixture fails that rubric |
| `notes` | Free-form description of why this fixture exists and what failure mode it stresses. Read this first when triaging a failure |

### The three committed synthetic fixtures

Each stresses a different failure mode of the LLM pipeline. They aren't variety for its own sake — each one tells you something specific when it fails.

| Fixture | Persona | Failure mode it stresses |
|---|---|---|
| `sre-mid-level` | Alex Chen, 4-year mid-level SRE, qualitative source metrics | **Metric invention.** Source has no hard numbers. Tests whether the model fabricates "$2.4M saved" or "12 engineers managed" to make bullets sound stronger. |
| `pm-senior` | Priya Mehta, 7-year B2B SaaS PM, **no healthcare experience**, JD is healthtech | **Domain fabrication.** Tests whether the model invents EHR/HIPAA/clinical experience to fit, or correctly positions transferable B2B-workflow PM skills. |
| `data-scientist-junior` | Jordan Park, 1-year data analyst, recent CS grad | **Level inflation.** Tests whether the model claims senior-DS work, advanced degrees, or tools (PyTorch, Kubernetes, deep learning) not present in source. |

When you add a new synthetic fixture, ask: "What failure mode does this surface that the existing three don't?"

---

## Anatomy of a rubric

A rubric is a markdown file in `evals/rubrics/` describing how the judge should score one dimension. The judge receives the entire rubric verbatim as instructions, then receives the materials to grade as a JSON payload.

### Structure

Every rubric has six sections:

1. **Title** — `# {Dimension} Rubric`
2. **Purpose** — one paragraph: what this dimension measures and why it matters
3. **Inputs** — what fields of the payload to read
4. **Checks / Scoring criteria** — the specific criteria, often as a numbered list
5. **Scoring scale** — 0–5 with concrete descriptions per band
6. **Output format** — JSON shape the judge must produce, including allowed `failed_rules` slugs

### The four shipped rubrics

| Rubric | What it scores |
|---|---|
| [`grounding.md`](rubrics/grounding.md) | Does the generated resume contain claims that don't trace back to source? Single most important rubric — fabrication is the worst failure mode. |
| [`keyword_coverage.md`](rubrics/keyword_coverage.md) | Did the JD's essential keywords appear in the generated resume? ATS systems gate on this first. |
| [`ats_format.md`](rubrics/ats_format.md) | Is the generated resume's structure ATS-parseable (standard headings, plain bullets, no tables/columns, sane length)? |
| [`tone.md`](rubrics/tone.md) | Does the cover letter match the prescribed VP-level voice (no throat-clearing, no banned phrases, three-paragraph structure)? |

### Scoring convention

All four rubrics use the same **0.0–5.0 scale with one-decimal precision** (since 2026-05-09 / `schema_version: 2`). The anchor bands are unchanged from the prior integer scale; rubrics now invite the judge to emit fractional scores between bands when the work sits on a boundary.

| Score | Meaning |
|---|---|
| 5.0 | Clean. No issues found. |
| 4.7 | Borderline-passing-as-5; one trivial nit. |
| 4.0 | Minor issue on the boundary; reasonable reader could accept it. |
| 3.5 | One clear issue plus a wobble; not quite to the "multiple issues" band. |
| 3.0 | One clear issue, rest is fine. |
| 2.0 | Multiple issues, mostly minor. |
| 1.0 | Major problem (one egregious finding or several serious ones). |
| 0.0 | Output is unusable for the dimension being scored. |

Default pass threshold is `4.0` (set per-fixture in `expected.json`). The runner coerces ints to floats at the judge boundary so old (`schema_version=1`) integer results still load correctly through the dashboard's normalize helper.

**Why fractional?** Integer 0–5 collapses real differences. The same fixture may genuinely score "stronger than 4 but not yet 5" on consecutive runs; the integer scale forces both into the same bucket and hides progress during prompt tuning. The float scale gives ~10× the granularity and is essential for tuning iterations to be observable.

### `failed_rules` slugs

Each rubric defines a vocabulary of machine-friendly failure slugs. The judge tags each finding with one or more slugs. Slugs are stable across runs so you can grep your way to "every fixture × run that triggered `invented_metric` in the last month."

Examples:
- `grounding.md`: `invented_metric`, `invented_role`, `invented_company`, `invented_credential`, `forbidden_pattern_match`, `scope_inflation`, `verb_overreach`
- `keyword_coverage.md`: `missing_must_keyword:$keyword`, `low_coverage`, `keyword_stuffing`, `forced_phrasing`
- `ats_format.md`: `missing_heading:$name`, `length_overflow`, `table_layout`, `missing_contact`
- `tone.md`: `throat_clearing_opener`, `banned_phrase:$word`, `hedging:$phrase`, `length_under`, `generic_hook`

---

## How the runner works

```
python evals/runner.py [--suite synthetic|real|all] [--subset smoke|full]
                       [--fixture NAME] [--out-dir PATH]
                       [--prompt-overrides PATH]
```

Per fixture:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Load fixture │ → │ Build        │ → │ Run analyze  │ → │ Run generate │
│ (3 files)    │   │ context_set  │   │ (Sonnet)     │   │ (Sonnet)     │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                                 ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Append JSONL │ ← │ Parse JSON   │ ← │ Send rubric  │ ← │ For each     │
│ result line  │   │ verdict      │   │ to Haiku     │   │ rubric...    │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

Key implementation details:

- `_build_context()` calls the same `parse_resume`, `extract_keywords`, `compute_keyword_overlap`, `check_ats_format`, `build_context_set` helpers the Flask app uses. **No fixture-specific shortcuts** — eval traffic exercises the same code path as live traffic.
- The `analyze()` and `generate()` calls go through the same `_call_llm` instrumentation as the live app — telemetry lands in `logs/llm_calls.jsonl` with `username="eval:{fixture}"`. The dashboard's user filter lets you isolate eval traffic from real traffic.
- The judge call uses `client.messages.create` (not stream) because the judge response is small (~1024 max tokens).
- Prompt caching from `_call_llm` applies: subsequent fixtures can reuse cached SYSTEM_PROMPT (system block is identical across all calls).

### Flag semantics

| Flag | Meaning |
|---|---|
| `--suite synthetic\|real\|all` | Which fixture directories to read. Default `synthetic`. |
| `--subset smoke\|full` | `smoke` runs only the `grounding` rubric (cheapest, most important signal); `full` runs all four. Default `full`. |
| `--fixture NAME` | Override `--suite` to run a single named fixture. Looks in `synthetic/` first, then `real/`. |
| `--out-dir PATH` | Override the default `evals/results/` output location. |
| `--prompt-overrides PATH` | Inject a candidate system prompt for this run only (A/B a prompt without editing `analyzer.py`). See [Candidate prompt overrides](#candidate-prompt-overrides---prompt-overrides) below. |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Every rubric scored ≥ its fixture's threshold |
| `1` | Configuration error (missing fixture, missing API key, etc.) |
| `2` | At least one rubric scored below threshold |

CI uses exit `2` to fail the build, distinguishing rubric failures from setup errors.

### Regression alerting

At the start of each run the runner reads every prior result file and builds a `{(fixture, rubric): most_recent_record}` baseline. After each grading it compares the new score to baseline and logs a `WARNING` when the drop exceeds `REGRESSION_DELTA` (default 0.5, override via env var). End-of-run summary lists improvements and regressions:

```
WARNING: REGRESSION: data-scientist-junior × tone dropped 4.8 → 4.2 (Δ=-0.6) vs prior run (prompt_version=2026-05-09.1, 2026-05-09T23:49:27)
...
--- Regression check vs previous runs (delta=0.5) ---
  ✗ data-scientist-junior × tone: 4.8 → 4.2 (Δ=-0.6)
  ✓ pm-senior × tone: 4.2 → 4.7 (Δ=+0.5)
WARNING: Found 1 regression(s) ≥0.5 points.
```

Regressions are informational — they don't change the runner's exit code (rubric pass/fail is still the gating signal). The default delta of 0.5 is calibrated for Haiku judge variance: tighter and you'll see noise; looser and you'll miss real drops. Override with `REGRESSION_DELTA=0.3` for stricter tracking during prompt iteration.

### Candidate prompt overrides (`--prompt-overrides`)

A/B a candidate system prompt against the suite **without editing `analyzer.py`**.
Point the flag at a JSON file mapping a system-prompt constant name to its full
replacement text:

```json
{
  "SYSTEM_PROMPT": "You are a seasoned hiring manager ... (full candidate text)"
}
```

```bash
python evals/runner.py --suite anchor --prompt-overrides candidate.json
```

Valid keys are the named persona constants in `analyzer._BASE_SYSTEM_PROMPTS`:
`SYSTEM_PROMPT`, `EXTRACTION_SYSTEM_PROMPT`, `CLARIFY_SYSTEM_PROMPT`,
`CLARIFY_ITERATION_SYSTEM_PROMPT`, `PROPOSAL_CRITIQUE_SYSTEM_PROMPT`,
`RECOMMEND_SYSTEM_PROMPT`, `RECOMMEND_SUMMARIES_SYSTEM_PROMPT`,
`PROMOTE_CLARIFICATION_SYSTEM_PROMPT`. Override values are **full prompt text**,
not diffs. A bad JSON file, the wrong shape, or an unknown key exits non-zero
*before* any paid LLM call.

What it does:

- Every `analyze` / `clarify` / `generate` call in the run sends the candidate
  prompt instead of the constant; `analyzer.py` is never touched.
- The whole run is stamped `prompt_version=candidate:<hash>` (a stable sha256 of
  the override mapping) on both telemetry (`logs/llm_calls.jsonl`) and eval
  result records — so a candidate run is **quarantined from the score-over-time
  chart** and never mistaken for a baseline revision. The runner logs the
  `candidate:<hash>` it chose at startup.
- **The default path (no flag) is byte-identical:** the resolver returns the
  identical constant object and records stamp the real `PROMPT_VERSION`, so the
  analyze→generate prompt cache and version attribution are unchanged.

To promote a winning candidate, copy its text into the constant in `analyzer.py`,
bump `PROMPT_VERSION` in the same commit, and log the before/after in
[`TUNING_LOG.md`](TUNING_LOG.md). The [`/prompt-tune`](../.claude-plugin/commands/prompt-tune.md)
skill automates the whole baseline → candidate → diff → promote loop on top of
this flag.

---

## Adding a synthetic fixture

A four-step process. Most of the work is in step 1.

### 1. Choose a failure mode this fixture should stress

Don't add a fixture just for variety. The eval suite is most useful when each fixture exists to catch a specific failure pattern. Look at the three existing fixtures and ask: "What would I need to test that they don't?"

Examples worth a fixture:
- A career-transition candidate (e.g., teacher → data analyst) — does the model overclaim transferable skills?
- A long-tenured senior with one company — does the model preserve scope language without inflating?
- A consultant with 12 short engagements — does the model handle dense employment history?
- A non-US candidate with international company names — does the model preserve them or substitute familiar ones?
- A candidate with an employment gap — does the model invent activity to fill it?

### 2. Write `jd.txt`

200–400 words. Use a fictional company name. Include enough detail that the analyze step has something to chew on (essential skills, nice-to-haves, responsibilities). Use realistic phrasing — copy patterns from real JDs in your industry.

### 3. Write `resume.md`

Match the persona you want to test. Use markdown structure (`## Experience`, `### Title — Company\tDate`). Include realistic-sounding bullets without inventing real companies' specifics. Length 250–500 words.

If your fixture stresses a specific failure mode, deliberately leave the source somewhat sparse on the dimension you want the model NOT to fabricate around. (E.g., a junior fixture should have only one ML side project, not five — so any "extensive ML experience" claim in the output is clearly invented.)

### 4. Write `expected.json`

The hardest part. Two key fields:

- **`must_keywords`** — what does the JD require that the generated resume ABSOLUTELY needs to integrate? Pick 4–6 high-signal terms.
- **`forbidden_inventions`** — what would be a lie if the model produced it? Use regex. Common patterns:
  - Quantitative claims: `"managed [0-9]+ engineers"`, `"saved \\$[0-9]+M"`
  - Domain-expertise terms not in source: `"HIPAA"`, `"FAANG"`, `"Series A"`
  - Inflated credentials: `"PhD"`, `"Master'?s? in"`, `"5\\+ years"` (when source is junior)
  - Fabricated affiliations: `"MIT|Stanford|CMU"` (when not in source)

Set per-rubric thresholds. Default to 4 for grounding/keyword/ATS, 3 for tone (tone is the most subjective).

### 5. Run it

```bash
python evals/runner.py --fixture {your-slug} --subset full
```

Iterate until the scores stabilize. If a fixture consistently scores 5 on every rubric, it's not stressing the pipeline enough — strengthen the JD/resume mismatch.

---

## Using real fixtures

`evals/fixtures/real/` is gitignored. Drop your actual JDs and resumes there.

Why bother with real fixtures when synthetic exist?

- Synthetic fixtures are smoothed by deliberate fictionalization. Real JDs have idiosyncratic phrasing, your actual resume has your specific voice.
- Real fixtures let you tune prompts against YOUR target distribution before stress-testing on synthetic.
- A regression that doesn't show up on synthetic but shows up on real is a real-distribution shift worth investigating.

The directory structure is identical to synthetic. `expected.json` describes what's true and what would be a lie for YOUR specific case (e.g., your `forbidden_inventions` should include companies you've never worked at, technologies you've never used, etc.).

```bash
python evals/runner.py --suite real
```

---

## Writing a custom rubric

Add a new file at `evals/rubrics/{slug}.md`. The runner picks it up automatically (`--subset full` runs every `*.md` in `evals/rubrics/`).

Conventions for a new rubric file:

1. **Title** at the top: `# {Name} Rubric`
2. **One-paragraph purpose** — what dimension this scores
3. **Inputs section** — name the fields of the payload the judge should read
4. **Checks section** — concrete criteria. Numbered list works well.
5. **Scoring scale** — 0–5 with concrete descriptions per band
6. **Output format** — must be JSON, document the schema explicitly. Tell the judge "no markdown fences, no commentary outside the JSON."

The judge receives your rubric verbatim as the user message. Be precise; ambiguity in the rubric becomes inconsistency in the scores.

To include a new rubric in the smoke subset, edit `_select_rubrics()` in `evals/runner.py`. Default smoke is `grounding` only.

---

## Interpreting results

Each line in `evals/results/{timestamp}.jsonl` (schema_version 2):

```json
{
  "schema_version": 2,
  "score_max": 5.0,
  "timestamp": "2026-05-09T23:46:57.472+00:00",
  "source": "eval",
  "fixture": "data-scientist-junior",
  "rubric": "grounding",
  "score": 4.8,
  "reasons": [
    "All company names, dates, titles, and core credentials trace directly to original resume",
    "Reframing of experience bullets is legitimate paraphrase",
    "..."
  ],
  "failed_rules": [],
  "status": "ok",
  "prompt_version": "2026-05-09.1",
  "deterministic_metrics": {
    "verb_diversity":      {"unique_verbs": 12, "total_bullets": 12, "diversity_ratio": 1.0,  "top_repeated": []},
    "specificity_density": {"total_bullets": 12, "bullets_with_metric": 1, "density": 0.083, "metric_count": 1},
    "grounding_overlap":   {"overlap_ratio": 0.21, "matched_ngrams": 138, "total_ngrams": 664, "missing_samples": ["..."], "n": 3}
  },
  "cost_usd": 0.1179,
  "pipeline_latency_ms": 130212
}
```

| Field | Meaning |
|---|---|
| `schema_version` | `1` = legacy integer-score records; `2` = float-score records with deterministic_metrics. Dashboard normalizes both. |
| `score_max` | Always `5.0` for current rubrics; here for forward-compat if a future rubric adopts a different scale. |
| `score` | 0.0–5.0 per the rubric's scale. Compared against `expected.json:min_{rubric}_score` |
| `reasons` | Specific quoted evidence the judge cited. Each reason should reference a phrase from the generated artifact |
| `failed_rules` | Machine-friendly slugs from the rubric's vocabulary. Useful for grepping across many runs |
| `status` | `ok` (graded successfully), `judge_error` (judge response unparseable), `pipeline_error` (analyze/generate threw) |
| `prompt_version` | The `analyzer.PROMPT_VERSION` at run time. Lets the dashboard's score-over-time chart attribute regressions to a specific prompt revision. |
| `run_id` | 12-hex UUID shared by the analyze + generate calls that produced this output. Match against `logs/llm_calls.jsonl` to find the specific LLM calls behind any graded result. |
| `deterministic_metrics.verb_diversity` | Unique leading verbs / total bullets in generated resume. See `hardening.compute_verb_diversity`. |
| `deterministic_metrics.specificity_density` | Fraction of bullets containing at least one quantifier. See `hardening.compute_specificity_density`. |
| `deterministic_metrics.grounding_overlap` | 3-gram overlap between generated and source. **`missing_samples`** is the actionable signal for fabrication detection, not the ratio. See `hardening.compute_grounding_overlap`. |
| `cost_usd` | Sum of all `analyze` + `generate` calls for this fixture, derived from `logs/llm_calls.jsonl` via `hardening.compute_call_cost`. |
| `pipeline_latency_ms` | End-to-end pipeline time excluding judge calls. |

The dashboard at `/_dashboard` reads `evals/results/*.jsonl`, normalizes legacy records, and renders four aggregations described in [How to read the dashboard](#how-to-read-the-dashboard) below.

### Deterministic post-generation metrics — ideal ranges

These ride along on every eval result and surface in the dashboard's recent-eval table. They're cheap to compute, LLM-free, and orthogonal to the LLM-judged scores — use them as a sanity check on the rubric verdicts.

| Metric | Healthy range | Action when out of range |
|---|---|---|
| `verb_diversity.diversity_ratio` | ≥ 0.6 | < 0.5: inspect `top_repeated`. SYSTEM_PROMPT already discourages verb repetition; if it persists, strengthen with a worked example like the grounding one. |
| `specificity_density.density` | 0.30–0.80 | < 0.30: LLM under-quantified — likely paraphrasing real numbers from source into qualitative language. > 0.80: number-stuffing risk — cross-check grounding score. |
| `grounding_overlap.overlap_ratio` | 0.20–0.50 | The ratio alone is NOT a pass/fail signal. Always read `missing_samples` for items containing technology names, domain nouns, or company-specific phrases — those are the fabrication candidates. Pure-stopword n-grams are filtered out automatically. |
| `cost_usd` (per fixture) | $0.10–$0.15 (Sonnet 4.6 + 1× Haiku judge call) | A spike usually means a longer-than-usual generation — check `pipeline_latency_ms` and the corresponding `logs/llm_calls.jsonl` entry's `output_tokens`. |

### How to read the dashboard

`http://localhost:5000/_dashboard` (only when `python app.py` is running locally).

Five views, top to bottom:

1. **LLM Calls — Summary** cards: count, errors, mean latency, cache-hit ratio, total tokens, **total cost USD**, **mean cost per call**. Cost is computed via `hardening.compute_call_cost` using the same `MODEL_PRICING` table the eval runner uses.
2. **LLM Calls — Recent**: per-call telemetry table. Filterable by date, user (use `eval:{fixture}` to isolate eval traffic), and model.
3. **Eval Quality — Aggregations**:
   - **Per-rubric pass rate** (bar chart): green ≥80%, amber 50-80%, red <50%. Quick health check.
   - **Score over time by rubric** (line chart): each point's tooltip labels its `prompt_version`. Use this to attribute score swings to specific prompt revisions.
   - **Rubric × fixture heatmap**: shows the most-recent score per (rubric, fixture) pair. Color is `hsl(120 * score/5, 60%, 30%)` — red for fail, green for pass. Hover for `prompt_version` and timestamp.
   - **Top failure modes** table: top-20 `failed_rules` slugs by record count (per-record dedup). The first two or three slugs tell you what the next prompt iteration should target.
4. **Eval Results — Recent**: per-rubric verdict rows including `prompt_version`, score, status, failed_rules. Most recent 200.

When a tuning iteration is in progress: read the heatmap to find the red cell, the failure-mode table to identify the slug class, and the failing record's `deterministic_metrics.grounding_overlap.missing_samples` for the specific phrases to rule out in the next prompt edit. Then bump `PROMPT_VERSION`, re-run, and watch the score-over-time chart confirm the move.

See [`TUNING_LOG.md`](TUNING_LOG.md) for the running record of prompt iterations and what each one taught us.

### What to do with a failed rubric

Read `failed_rules` first — it tells you which class of failure occurred. Common patterns and where to look:

| Pattern | Likely cause | Where to fix |
|---|---|---|
| `scope_inflation` + `verb_overreach` | The model is overstating what's in source. Especially common on junior fixtures. | Tighten the GROUNDING rule in `analyzer.py:SYSTEM_PROMPT`. The `prompt-archaeologist` subagent is built for this. |
| `missing_must_keyword:X` | The model isn't integrating keyword X. | Often a prompt issue (output_format example doesn't show keyword integration well). Sometimes the keyword is genuinely irrelevant to the candidate's experience and shouldn't be required — re-evaluate the fixture's `must_keywords`. |
| `throat_clearing_opener` | Tone rubric caught a banned cover-letter opening | Adjust `cover_letter_rules` in `generate()`'s prompt. |
| `forbidden_pattern_match` | Grounding caught a regex from `expected.json:forbidden_inventions` | Inspect what was generated and trace back. Sometimes the regex is too broad and needs tightening; sometimes the model is genuinely hallucinating. |
| `length_overflow` / `length_under` | Generated artifact outside expected band | Check the output_format rules for length guidance; generate prompt may need a tighter bound. |
| Always-failing rubric | Rubric is too strict, or model is consistently failing this dimension | Re-read the rubric. If the criteria are right but the model can't meet them, that's a real prompt-engineering problem. |

The [`prompt-archaeologist`](../.claude-plugin/agents/prompt-archaeologist.md) subagent is purpose-built for this triage — feed it the failed result and it traces back to the specific SYSTEM_PROMPT rule that should have prevented the failure. It outputs a unified diff (does not apply changes).

---

## CI integration

`.github/workflows/ci.yml` runs the smoke subset on PRs labeled `eval`:

```yaml
eval-smoke:
  if: contains(github.event.pull_request.labels.*.name, 'eval')
  steps:
    - run: python evals/runner.py --suite synthetic --subset smoke
```

The `eval` label is opt-in because each labeled PR run costs ~$0.10 in API calls. Maintainers add the label when a PR touches `analyzer.py`, prompts, or anything that could affect output quality.

`ANTHROPIC_API_KEY` must be configured as a repo secret (Settings → Secrets and variables → Actions) for the eval-smoke job to authenticate. Without the secret the job fails with a clear error.

---

## Cost considerations

Per-run cost (Claude Sonnet 4 + Haiku 4.5 pricing as of early 2026):

| Subset | Pipeline calls | Grading calls | Total LLM calls | Approx. cost |
|---|---|---|---|---|
| `--subset smoke` (3 fixtures × 1 rubric) | 6 (3 analyze + 3 generate) | 3 | 9 | ~$0.10 |
| `--subset full` (3 fixtures × 4 rubrics) | 6 | 12 | 18 | ~$0.30 |

Each new fixture adds 2 pipeline calls + N grading calls (where N = number of rubrics). The pipeline calls are the dominant cost (Sonnet input + output). Grading calls are cheap (Haiku, structured output, ~1024 max tokens).

To reduce cost:
- Use `--subset smoke` for routine PR runs; only use `--subset full` for prompt-engineering iterations
- Run `--fixture {single}` for targeted iteration on one failure mode
- Local-only runs of `--suite real` should be limited — don't run the full suite every iteration

---

## Troubleshooting

### `RuntimeError: ANTHROPIC_API_KEY not set`

Either `export ANTHROPIC_API_KEY=...` before the run, or place the key in `.api_key` at the project root (gitignored). Both are checked.

### `Fixture load failed: ... — No resume file in fixture {name}`

Fixture directory is missing `resume.md`, `resume.docx`, or `resume.pdf`. The runner checks all three extensions in order; provide at least one.

### `Fixture load failed: ... — [Errno 2] No such file or directory: '.../expected.json'`

Add `expected.json` to the fixture directory. Even a minimal one works:

```json
{"must_keywords": [], "forbidden_inventions": [], "min_grounding_score": 4}
```

### `Pipeline failed for {fixture}: ...`

The `analyze()` or `generate()` call threw. Common causes:
- `parse_resume` choking on a malformed `resume.md` (check the file for unbalanced markdown)
- API rate limit (429) — the runner doesn't auto-retry; re-run after a moment
- Network timeout — `_call_llm` uses streaming so very long generations shouldn't time out, but check `logs/llm_calls.jsonl` for the failed entry's `latency_ms`

### Judge returns score `null`

The judge's response wasn't valid JSON. Check the result file's `raw` field — that's the judge's actual output. Often the judge added explanatory prose around the JSON; tighten the rubric's "Output format" section to forbid that. Also consider explicitly telling the judge "no markdown code fences."

### All scores are 5

Either the model is genuinely doing great work (possible) or the rubrics are too lenient. The fact that the project's `data-scientist-junior` fixture currently scores 2 on grounding suggests the rubrics ARE tuned conservatively enough — if you see all 5s, look hard at your rubrics' scoring bands.

### CI eval-smoke job fails on a PR you didn't expect

Check the eval result file in the GitHub Actions log. The runner prints the JSONL path; the failed rubrics' `reasons` will show what the judge flagged. Common: a refactoring PR that reordered text in a prompt template can shift the model's output enough to fail grounding even though no rule changed.

---

## Future extensions

Several enhancements are scoped but not yet built:

- **Trend tracking** — aggregate scores by `prompt_version` over time so prompt regressions are visible on the dashboard
- **Auto-invocation of `eval-judge` from `/replay`** — for ad-hoc grading of a single regenerated output without a full eval run
- **Structured failure analysis** — group `failed_rules` slugs across runs to identify systemic issues
- ~~**A/B prompt comparison**~~ — **shipped** (v1.0.4) as the [`--prompt-overrides`](#candidate-prompt-overrides---prompt-overrides) flag + `analyzer.prompt_overrides()`; the [`/prompt-tune`](../.claude-plugin/commands/prompt-tune.md) skill drives the capture-baseline → candidate → diff → promote loop on top of it
- **Custom judge model** — `--judge-model` flag to override the default Haiku, useful for experimentation with Sonnet-as-judge

---

## Related files

| File | Role |
|---|---|
| [`analyzer.py:SYSTEM_PROMPT`](../analyzer.py) | The persona + ALWAYS/NEVER rules the eval ultimately measures |
| [`analyzer.py:_call_llm`](../analyzer.py) | Shared instrumentation; eval traffic appears in `logs/llm_calls.jsonl` with `username="eval:{fixture}"` |
| [`dashboard/routes.py`](../dashboard/routes.py) | Reads `evals/results/*.jsonl` for the dashboard's bottom table |
| [`.claude-plugin/agents/eval-judge.md`](../.claude-plugin/agents/eval-judge.md) | Interactive subagent variant of the grading function |
| [`.claude-plugin/agents/prompt-archaeologist.md`](../.claude-plugin/agents/prompt-archaeologist.md) | Failure-triage subagent for failed rubrics |
| [`.claude-plugin/commands/eval.md`](../.claude-plugin/commands/eval.md) | Slash-command wrapper around `runner.py` |
| [`.claude-plugin/commands/prompt-tune.md`](../.claude-plugin/commands/prompt-tune.md) | A/B prompt comparison built on the harness |
| [`vision.md`](../vision.md) | Project-level reasoning for why eval is needed (deterministic-first, LLM-only-when-needed) |

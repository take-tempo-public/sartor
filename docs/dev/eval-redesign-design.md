# Eval redesign — one scheme for single-call, group and full evaluation

> **Purpose:** the gap map of Sartor's evals as they stand on 2026-10-20, and one proposed
> redesign to land before the public release: every model call evaluated on its own, calls
> grouped into runs of a chosen size, a full run for the whole system, one standard dataset,
> one record format, and a dashboard that drills from a call kind down to a single case.
> **Audience:** `dev` — the owner deciding what to build, and the agents who will build it.
> **Authoritative for:** the 2026-10-20 gap map and the proposed scheme. **Status: proposed;
> the owner answered the eight decisions in section 8 on 2026-10-20. Nothing in section 5 or
> later is built.** The build order is filed as epic 180. It defers to
> [`../governance/charter.md`](../governance/charter.md) (claims discipline C-0 governs) and to
> [`evals/README.md`](../../evals/README.md) for how the harness works today.
> **Source of record:** item 137's updates in
> [`work/items/0137-review-models-and-settings-for-performance-and-cost.md`](work/items/0137-review-models-and-settings-for-performance-and-cost.md);
> the A/B that item proposes is held until this scheme exists (section 9).

---

## 1. Why this, and why now

Item 137's A/B asks one question: should `HAIKU_MODEL` move from `claude-haiku-4-5-20251001`
to `claude-haiku-5-5`? Planning it showed the harness cannot answer that for most of what
Haiku does. Of the 13 call kinds on the Haiku pin, the runner fires 3 (`analyze_extraction`,
`clarify`, `recommend`) and scores 1 of them (`clarify`) against a rubric aimed at its own
output. The rest are scored through the final résumé, or not at all.

The product has one user, so changing the scheme costs little now and costs a migration after
release. The owner's direction (chat, 2026-10-20) was: map the gaps; propose the one redesign
worth doing before release; make it a model of eval design for other projects; cover every
model call; let tests be run singly, in groups or in full; and chart all of it with
drill-downs.

## 2. What exists today

Facts below were read at source on 2026-10-20 unless marked *(reported)*, which means a
research pass found it and this doc did not re-read it.

- **One runner**, [`evals/runner.py`](../../evals/runner.py): `--suite` synthetic, real, all,
  anchor, exploration; `--subset` smoke (grounding rubric only) or full (all seven rubrics);
  `--mode` generate or assemble; `--fixture`; `--seed`; `--prompt-overrides`;
  `--model-override`. Selection is at `runner.py:2107-2179`.
- **Seven rubrics** in [`evals/rubrics/`](../../evals/rubrics/): grounding, keyword_coverage,
  ats_format, tone, callback_likelihood, clarification_quality, iteration_quality. Five grade
  the finished résumé or letter; `clarification_quality` and `iteration_quality` grade the
  output of `clarify` and `iterate_clarify`.
- **Three synthetic personas** (data scientist junior, product manager senior, site
  reliability engineer mid-level), each a résumé, a job description (JD) and an
  `expected.json`. `anchor-v1` holds byte-identical copies of the same three (`diff -rq` shows
  only `corpus/` unique to the synthetic directory). One committed corpus seed,
  `evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json`, serves `--seed` runs.
  `evals/exploration/` holds no fixtures *(reported)*.
- **One judge**, `JUDGE_MODEL = "claude-haiku-4-5-20251001"` (`runner.py:119`), the same
  model as the product's Haiku pin.
- **Telemetry:** every product call writes one JSONL row from one place
  (`analyzer.py:1889-1921`), with model, tokens, cache tokens, latency, stop reason, status and,
  since item 175, the answering model, request id, settings sent, thinking tokens and attempt.
  A call that raises still writes a row (the `finally` block adds the error type and message).
- **Dashboard:** Pipeline, Quality, Groundedness and Tuning tabs and a run-detail modal
  *(reported)*. Cost and reliability are shown per call kind; scores never are.
- **Two inventories already fail closed.** `tests/test_call_kind_telemetry.py` scans the
  production source for `call_kind="..."` literals and fails if the set differs from
  `EXPECTED_CALL_KINDS` (`:74-155`): 21 product kinds and 2 judge kinds. The
  `_BASE_SYSTEM_PROMPTS` registry holds 17 prompt constants (`analyzer.py:5549-5567`).

## 3. Gap map

### 3.1 Coverage — what reaches each call kind

Row counts are `logs/llm_calls.jsonl` rows on the two current pins, 1,564 rows to
2026-10-18, retries counted separately. "Product" means `username` not starting `eval:`;
the owner's own use is included.

| Call kind | Pin | Product / eval rows | Reached by | Scored |
|---|---|---|---|---|
| `clarify` | Haiku | 37 / 88 | both flows | **directly**: `clarification_quality` (full subset) |
| `iterate_clarify` | Sonnet | 4 / 1 | full subset, sre persona only | **directly**: `iteration_quality` |
| `analyze_extraction` | Haiku | 45 / 119 | both flows | through the final document only |
| `analyze_synthesis` | Sonnet | 40 / 42 | both flows | through the final document only |
| `generate` | Sonnet | 5 / 20 | generate mode | through the final document only |
| `generate_cover_letter` | Sonnet | 6 / 22 | assemble mode (`runner.py:1190`); inside `generate` otherwise | through the final document only |
| `recommend` | Haiku | 75 / 22 | assemble mode | through the assembled document only |
| `recommend_summary` | Haiku | 42 / **0** | assemble mode calls it, but it makes **no LLM call below two summary variants** (`analyzer.py:3978-3989`) and the committed seed has one | not at all under committed data |
| `draft_experience_summary` | Sonnet | 2 / 0 | `evals/corpus_drafting_probe.py` *(reported)* | deterministic probe, off the runner |
| `extract_experiences` | Haiku | 87 / 0 | nothing | not at all |
| `avatar_answer` | Haiku | 73 / 0 | nothing | not at all |
| `draft_summary` | Sonnet | 51 / 0 | nothing | not at all |
| `draft_gap_fill` | Sonnet | 24 / 0 | nothing | not at all |
| `recommend_skill` | Haiku | 10 / 0 | nothing | not at all |
| `suggest_skill` | Haiku | 2 / 0 | nothing | not at all |
| `critique_proposal` | Haiku | 2 / 0 | nothing | not at all |
| `draft_surgical_refinement` | Sonnet | 1 / 0 | nothing | not at all |
| `recommend_experience_summary` | Haiku | 1 / 0 | nothing | not at all |
| `check_refinement_scope` | Haiku | 1 / 0 | nothing | not at all |
| `suggest_skill_from_corpus` | Haiku | 0 / 0 | nothing | not at all |
| `promote_clarification_to_bullet` | Haiku | 0 / 0 | nothing | not at all |

Reading the table: **2 of 21 kinds are scored on their own output; 5 are scored only through
the finished document; 1 has an off-runner probe; 1 is unreachable under the committed data;
12 have no eval of any kind.** Those 12 carry 260 of the 524 product rows (about half),
including three of the four busiest kinds by product rows: `extract_experiences` (87),
`avatar_answer` (73) and `draft_summary` (51).

Two limits on reach that are decisions, not oversights, and are worth reopening:

- **The avatar prompt is deliberately outside the eval path.** `analyzer.py:1192-1193` says
  it is "intentionally NOT in `_BASE_SYSTEM_PROMPTS` (not an eval target)" and it carries its
  own `AVATAR_PROMPT_VERSION`. The prompt behind `extract_experiences` is also outside the
  override registry *(reported)*. Neither can be A/B-tested with `--prompt-overrides`.
- **`PROMPT_VERSION` is one string for 17 prompts** (`analyzer.py:665`). A score cannot say
  which prompt changed, and a prompt edit that forgets the bump is caught only by a reviewer
  (`docs/governance/enforcement.md:127` classes it "convention + witness").

### 3.2 Attribution

A score lands on the finished document, so it carries the variance of every call before it.
A `clarify` regression and an `analyze_extraction` regression look the same on the dashboard.
No score row names a call kind, so the dashboard cannot chart one.

### 3.3 Dataset

Three personas cover three professions at one level each. `anchor-v1` is a copy of them, so
the "anchor" adds no breadth. The one corpus seed has 3 experiences, 2 skills and 1 summary
variant; that thinness is what makes `recommend_summary` unreachable. No persona exists in
both a legacy form (a résumé file) and a corpus form (a seed), so the two flows are never
compared on the same person. The seeds under `evals/fixtures/real/` are gitignored, so
nobody else can reproduce a result on them; a result on a personal seed is not a standard
result.

### 3.4 Statistics

- Judge noise on a single grading is recorded as up to ±0.6 against a 0.5 regression
  threshold (`evals/TUNING_LOG.md:97`), and n = 3 is recorded as too thin to separate that
  from a real change (`:554-555`).
- `evals/results/baseline_v1.json` aggregates one run (`runs_aggregated: 1`) at prompt
  version `2026-07-08.4`; the current version is `2026-10-17.2`.
- Exit code 2 means any score below 4.0 or any regression past 0.5 (`runner.py:2072`), and the
  TUNING_LOG calls it the expected result on full runs, so the exit code carries little signal.
- The ds-junior persona scores bimodally (0.0 or 1.2 against 4.8 to 5.0 in assemble mode,
  `TUNING_LOG.md:3328-3330`), so means mislead on it.
- A run's cost is the sum of telemetry rows for one username after a start time
  (`runner.py:545-575`). Two runs overlapping on the same fixture would be summed together;
  that follows from the filter and has not been tested.

### 3.5 Judge

The judge is Haiku 4.5: the model being swapped in item 137 is also the model grading, and
Haiku 4.5 is past its earliest retirement date (item 137, 2026-10-17 update). The judge's JSON
is parsed by hand and has no gold labels to measure it against; `docs/governance/metrics.md:124`
lists "uncalibrated L1/L2 treated as trustworthy" among the eval debuffs. Judge cost is left
out of a record's `cost_usd` by design (`runner.py:564-566`), so spend has to be read from
telemetry. Over-suppression — a grounding rule that deletes grounded synthesis — is the
direction C-3 names as uninstrumented (`docs/governance/charter.md:123`).

The call log holds no judge rows. That is expected: judge logging merged on 2026-10-18
(`2ae0dd7`), the newest row is from 2026-10-18T00:24Z, and no paid eval has run since.

### 3.6 Telemetry and dashboard

- No trace structure: `run_id` is one per fixture (`runner.py:1402`), there is no id for a
  whole run, and judge rows carry `run_id ""` and join to a record only through
  `judge_request_id` *(reported)*.
- The judge's `reasons` text is stored in each record and never displayed: the only mention in
  the dashboard code is a `setdefault` (`dashboard/routes.py:104`).
- Cache figures are global, not per call kind (`dashboard/routes.py:197-215`).
- 102 rows have an empty `username`; the kinds responsible (`extract_experiences`,
  `avatar_answer`, `check_refinement_scope`) are *(reported)*.
- 195 `analyze` rows come from a call kind no code produces any more; the single-pass analyze
  was split in two on 2026-06-01 *(reported)*.
- Telemetry is not OpenTelemetry-shaped (section 7).

### 3.7 Tooling and documentation

`evals/tune.py` compares scores only, one file per side *(reported)*. `--model-override` is
command-line only. Nothing estimates or caps spend before a run. `evals/README.md` says four
rubrics ship (seven do) and gives contradictory cost figures *(reported)*. The `eval-smoke`
job runs only on a pull request labelled `eval` and is not a required check *(reported)*.

## 4. Principles the scheme answers to

The five load-bearing principles are listed in [`vision.md`](../../vision.md) under
"Principles backbone" (the pointer in `AGENTS.md` to a charter section by that name is
stale). The scheme leans on these:

- **P1 Hardening:** deterministic checks run first; the judge is last, and only where a rule
  cannot be written.
- **P2 Context hygiene:** each single-call eval takes a fixed `context_set` as input, the same
  contract the pipeline uses between stages.
- **P5 Institutional memory:** every comparison leaves a record in an item update and
  `evals/TUNING_LOG.md`.
- **P8 Human gates:** a model or prompt change is promoted by the owner, on a result the
  scheme computed; the scheme never moves a pin.
- **P9 Observability:** one record per call, one id per run, drill-downs on the dashboard.
- **C-0 and C-7:** a result states what was measured and its noise; a causal claim cites an
  observation. **C-11:** every rule below that matters is a gate that fails closed, or is
  labelled unenforced. **D-1:** no new dependency without a recorded reason.

## 5. The redesign

The unit of evaluation becomes **the call**, not the finished document. Everything else —
the three run sizes, the dataset, the record, the dashboard — follows from that.

### 5.1 The eval catalog

One file per call kind under `evals/catalog/`, for example `evals/catalog/recommend.toml`.
Each entry names:

| Field | Meaning |
|---|---|
| `kind` | the `call_kind` string, as in `EXPECTED_CALL_KINDS` |
| `prompt_const` | the system-prompt constant, so a prompt edit maps to the kinds it affects |
| `pin` | which model pin the call uses |
| `cases` | the case files, each a fixed input and its expectations |
| `checks` | deterministic checks, in order (schema valid, handle-leak guard, no invented figures, length and format limits, expected-set overlap, refusal when expected) |
| `rubric` | the judge rubric, or none when the checks are enough |
| `lean` | which error is worse for this call, false positive or false negative, and why |
| `n` | repeats per case, fixed in advance |
| `cost` | measured dollars per case, refreshed by each run |
| `groups` | the groups it belongs to |

**The gate.** A new test beside `test_call_kind_inventory_is_exactly_expected` fails if any
kind in `EXPECTED_CALL_KINDS` has no catalog entry, or an entry points at a missing case or
rubric. An entry may carry `exempt = "<reason>"` with an owner-named approval, so the answer
"this call is not evaluated" is written down rather than silent. The catalog is read lazily:
the gate lists file names, and the runner parses only the entries it was asked to run. That is
deliberate, not a shortcut: a run of one kind should not parse twenty, and a pull request that
changes one call should touch one file.

### 5.2 Three run sizes, one runner

| Size | Command shape | Use it to | Selects |
|---|---|---|---|
| **Single** | `--eval <kind>` | tune one call's prompt or settings | one catalog entry, its cases, its checks and rubric |
| **Group** | `--group <name>`, `--affected-by <PROMPT_CONST>` | check an area, or the blast radius of a scope change | every kind in the group |
| **Full** | `--full` | evaluate the whole setup; gate a release; judge a model swap | every call eval, plus the end-to-end flows |

Proposed groups, drawn from how the calls are used together in the routes and in past tuning
runs:

| Group | Kinds | Why together |
|---|---|---|
| `analyze-clarify` | `analyze_extraction`, `analyze_synthesis`, `clarify`, `iterate_clarify` | the intake pass; they share one `context_set` |
| `compose` | `recommend`, `recommend_summary`, `recommend_experience_summary`, `recommend_skill`, `suggest_skill`, `suggest_skill_from_corpus`, `draft_summary`, `draft_gap_fill`, `draft_experience_summary`, `draft_surgical_refinement`, `check_refinement_scope` | the corpus-mode drafting area |
| `generate-letter` | `generate`, `generate_cover_letter` | the document-producing calls |
| `ingest` | `extract_experiences` | résumé import |
| `assistant` | `avatar_answer` | the documentation assistant |
| `proposals` | `critique_proposal`, `promote_clarification_to_bullet` | the proposal review calls |
| `flows` | end-to-end generate mode and assemble mode, scored on the finished document by today's rubrics | does the chain still produce a good résumé |
| `sentinel` | one case per kind | the cheapest "is any call broken" run; the label-gated CI job |

`--affected-by SYSTEM_PROMPT` reads each entry's `prompt_const` and runs the kinds that use
it, so a change to a shared prompt says which calls to re-run. Every run prints an estimated
spend from each entry's measured `cost` and refuses to start above `--max-spend`.

**Cost of the cheapest tier, measured.** One call per kind at the mean cost of that kind on
the current pins (product rows, else eval rows) sums to **$0.30** for 19 of the 21 kinds. The
other two, `suggest_skill_from_corpus` and `promote_clarification_to_bullet`, have no row on
the current pins, so their cost is unmeasured; judge calls are not included. This is arithmetic
on logged rows, not a quote, and it is a floor: a catalog case is a fixed input, so its real
cost is measured on the first catalog run.

**Cache effect.** Item 137 recorded that 20 of 20 eval `generate` calls within 300 s of their
synthesis read the cache. The runner should order a group's cases by kind so a shared prefix
is read, not rewritten, and the report shows cache tokens beside dollars.

### 5.3 What a call eval looks like — deterministic first

The ladder for each call is the same: **schema, then rules, then reference comparison, then
judge.** The judge runs only on what the first three cannot decide. Examples:

| Call | Deterministic part | Judged part |
|---|---|---|
| `extract_experiences` | roles, dates and employers against an expected list: precision and recall | none needed to start |
| `check_refinement_scope` | accuracy on labelled in-scope and out-of-scope edits | none |
| `suggest_skill`, `recommend_skill` | overlap with the expected skill list; nothing outside the corpus and JD | relevance, if wanted |
| `avatar_answer` | cited paths resolve (`_resolve_cited`); an unanswerable question must be refused | answer quality |
| `recommend`, `recommend_summary` | chosen ids exist; handle-leak guard clean | rationale quality |
| `draft_*`, `critique_proposal`, `promote_clarification_to_bullet` | grounding overlap against the source union; leak guard; length | tone and fit |
| `analyze_*`, `clarify`, `iterate_clarify`, `generate*` | schema, leak guard, grounding overlap, today's metrics | today's rubrics |

The assistant's questions can come from the repository's own documentation at a pinned commit:
that data is already public and needs no authoring beyond the questions and their expected
citations.

**Isolating the call.** A single-call case takes a captured upstream state as input (a
`context_set` as the previous stage left it), so `recommend` is never re-run behind a fresh
`analyze`. Each captured input records which producer made it and the schema it validates
against; a test fails when the current input type no longer accepts it.

### 5.4 The standard dataset

Section 6 gives the research behind this. The requirements, whatever the source:

- **Committed or fetched reproducibly**, versioned, content-hashed. No personal data.
  The owner chose the committed synthetic matrix **plus** a public set fetched on demand
  (decision 1). A fetch is an outbound connection, and charter C-2 names exactly two
  destinations (`../governance/charter.md:91-100`); the one precedent for another is the
  grounding-model download, an opt-in install under D-6 (`../governance/charter.md:108-110`).
  So the fetch takes that route and passes `tests/test_egress_allowlist.py`, or it returns to
  the owner as a C-2 amendment. Nothing fetched is committed.
- **A profession by level matrix**, sampled rather than crossed, with every persona in
  **both** forms: a résumé file for the legacy flow and a seed for the corpus flow.
- **Each persona carries:** one or two JDs (a strong match and a stretch), expected signals,
  the invention traps it tests, and where relevant an iteration scenario.
- **Rich enough to fire every call.** A seed must have at least two summary variants, enough
  skills for `recommend_skill`, and so on. A **reachability check** runs each flow with a
  recording stub in place of the API client and asserts the set of call kinds that fired equals
  the set the catalog expects. It costs nothing and would have caught the `recommend_summary`
  gap.
- **Two roles, never mixed (proposal, 6.4):** a **golden set** (the committed, authored matrix:
  frozen inputs, ground truth written by code, the only set that gates a release or a model swap,
  versioned so a later version adds cells and never edits one in place) and an **exploration set** (a
  fetched real-posting draw, or a fresh seeded draw from the matrix, pinned by a manifest of source
  revision and sha256; its result is a lead and never moves a pin). Candidates are promoted by the
  rule already written in `evals/exploration/README.md` *(reported)*. The fetched set cannot be the
  golden set: it can change or vanish upstream, it cannot be committed, and every public set found is
  IT or government only (6.1 to 6.3).

### 5.5 Identity and versioning

Today `PROMPT_VERSION` is a human label for 17 prompts. Add, without removing it:

- **A content hash per prompt constant**, computed over the text as sent, recorded on every
  call row next to the version. A committed file lists each constant's hash; the gate recomputes
  them and fails if a hash changed and `PROMPT_VERSION` did not. That turns the
  "convention + witness" rule at `enforcement.md:127` into a mechanism (C-11).
- **A producer id** for each call: a short hash over the call kind, the prompt hash, the
  answering model's snapshot name and the canonical settings sent. Baselines, comparisons and
  the dashboard key on it, so two producers are never averaged. That replaces the population
  problem in `_load_baseline_scores` by construction: a baseline is for one producer.
- **Ids that tie a run together:** a trace id for the run, a span id per call, a case id, and a
  parent span id so the judge's call is a child of the case it graded (formats in section 7).
- **A parse outcome** on the call row (accepted first try, accepted after retry, refused), which
  the call log lacks because parsing happens after the send.

### 5.6 Protocol and decision rule

A comparison is **pre-registered** in a small spec file before any paid call: the arms, the
cases, N, the spend cap and the decision rule. The runner reads it, prints the estimate, runs
the arms **interleaved** (alternating which goes first), and writes one result file.

- **Noise floor.** Repeat the baseline producer on a sample of cases and report the spread
  beside every delta. A change smaller than the floor is reported as inside it.
- **Paired deltas.** Compare the same case under both arms, not arm means.
- **An arithmetic rule, no model in it.** For each arm pair, count cases where the candidate
  passes and the baseline fails, and the reverse; report the exact binomial probability; require
  the candidate to hold on every deterministic check. Outcomes are PROMOTE, HOLD, REJECT or
  **INCONCLUSIVE** (too few cases to decide). The rule replaces the single 0.5 threshold.
- **Spend** is read from telemetry for the run's trace id, judge calls included, not from
  `cost_usd`.
- A passing result never moves a pin. The owner does, on a branch (P8).

### 5.7 The judge

Pin it on its own, separate from the product pins, so a product swap cannot move the grader.
Parse its output against a schema rather than by hand. Measure it: a small set of
human-labelled gradings per rubric, kept disjoint from any set a rubric was tuned on, gives an
agreement figure shown beside every judged score. The repository already has an annotation flow
(`evals/annotation.py`, `commands/tune-from-annotations.md`, *(reported)*) to produce labels.
Add an over-suppression check for C-3 (a grounded sentence the grader or the guard wrongly
removed). Choosing the judge model is the owner's decision (section 8).

**Owner decision 5 (2026-10-20): no human-labelled gold set.** Calibration therefore rests on
deterministic checks and on agreement between judges. Agreement between judges shows that they
are consistent with each other, not that either is right, so a judged score carries weaker
evidence than the gold-set design above would give. The agreement figure beside a judged score
must be labelled "judge-to-judge", never "human agreement".

### 5.8 Telemetry and dashboard

**Record.** The house JSONL row stays primary and gains the fields in 5.5. The case result
record gains `case_id`, `kind`, `producer_id`, `dataset_version`, `catalog_entry_hash`,
`trace_id`, and its deterministic check outcomes. A result is written in the local data
directory; nothing leaves the machine.

**Dashboard.** A *Catalog* tab with one row per call kind: latest pass rate, trend, noise
floor, p50 latency, cost per call, cache share, the date of the last run, and the producer id.
A kind whose producer id changed since its last run is marked **needs eval**; a kind with no
catalog run is marked **never evaluated**. This is the attention view: it names the gaps in
this document as they open. Drilling down:

1. **Kind** → the case list with pass or fail per case across the last runs.
2. **Case** → the trace: the call spans on a waterfall, the judge span as a child.
3. **Judge span** → the judge's reasons text, the deterministic check outcomes, and the input
   and output kept locally in the result file.

A second view compares two arms with the noise floor beside each delta. The existing Quality
and Pipeline tabs stay; the end-to-end `flows` group feeds the Quality tab as it does now.

## 6. The standard dataset — research

A research pass on 2026-10-20 read dataset cards and licence pages and downloaded nothing. It
used a summarizing fetch tool, so quotes are near-verbatim. "Licence" below is what the page
declares, not a legal opinion, and every row is *(reported)*.

> **Updated 2026-10-20 (branch `docs/eval-dataset-research`):** a second, deeper pass is in 6.1 to 6.3,
> with each row marked *(reported)* or **raw-read**, and 6.4 is a matrix proposal that **replaces the
> "Recommended standard set" paragraph below, including its Job Zone to level mapping** (Job Zones are
> now four and do not separate seniority inside a profession; see 6.3). The first-pass table and
> paragraphs below are kept as the record of what the first pass found.

**Result: no public dataset found is both redistributable and broad across professions and
levels, with résumés and JDs.** Every large résumé set is scraped, real and not clearly
anonymized, or of unclear origin.

| Source | Declared licence | Provenance and PII | Covers | Verdict |
|---|---|---|---|---|
| `ahmedheakl/resume-atlas` | MIT (card) | scraped from image search and LiveCareer; names, phones, emails present; no anonymization described | 13,389 rows, 43 categories; no JDs or levels | reject |
| `opensporks/resumes` (mirror of a Kaggle set) | CC0 (uploader's tag) | scraped from LiveCareer; no PII statement; rights doubtful | 2,484 rows; no JDs or levels | reject for committing |
| `datasetmaster/resumes` | MIT | real "anonymized" rows mixed with Faker-synthetic rows, ratio unstated | about 4,817 rows; no JDs | reject; schema shape only |
| `sukhrobnurali/resume-parsing-vision` | CC-BY-4.0 | fully synthetic: code fixes the structured fields, a model writes the prose; "no real personal data" | 1,000 résumés, 32 software roles, 0 to 25 years; no JDs | the pattern to copy; fetch on demand |
| `netsol/resume-score-details` | "cc", version not visible | GPT-4o JDs over résumés of unnamed origin | 1,031 with JD | reject until clarified |
| `cnamuangtoun/resume-job-description-fit` and derivatives | unknown, "other" or unresolved | unverified, or LiveCareer-derived | 1K to 10K pairs, IT-heavy | reject |
| `anatiagent/resume-posting-pairs` | "other", each source its own terms | real résumés against real postings; labels by an LLM judge | 16,440 pairs, 7 IT domains | reject |
| Djinni (`lang-uk`) CVs and JDs | MIT (cards) | real; "anonymized", method undescribed | 210,250 CVs, 141,897 JDs, mostly IT | CVs no; JD wording only, fetched on demand, nothing committed |
| O\*NET database | CC BY 4.0 (page text) | US Department of Labor occupational data | occupations, tasks, skills, Job Zones 1 to 5; no résumés | **use**: a committed extract with attribution |
| ESCO | licence not stated on its download page | EU taxonomy | occupations and skills | unverified; inspiration only |
| OpenResume; Kaggle LinkedIn postings; LiveCareer terms | not read | not read | not read | unverified |

O\*NET's terms, as the page states them: credit USDOL/ETA, link CC BY 4.0, indicate changes,
cite the version, say that USDOL/ETA has not endorsed any modification, and follow its trademark
rules. It covers the downloadable files only.

**Recommended standard set: a synthetic matrix on O\*NET.** Professions, Job Zone (which maps
to level), tasks and skills come from a small committed O\*NET extract. The structured facts of
each candidate — roles, dates, skills, bullets with figures — are authored by code, and a model
writes the prose around them once. The generated text is committed with the generating model's
id, the prompt version and a content hash. This is the pattern of the public synthetic set above
("labels are exact by construction"), and it fits Sartor's own check: a generated résumé may
state only facts in the profile.

Spec for the matrix:

- **Axes.** Profession (about 12, spanning healthcare, trades, finance, education, sales,
  engineering, creative, legal, operations) by level (junior, mid, senior, lead, mapped to Job
  Zones 2 to 5 and to years of experience). The three existing personas become three cells. The
  first dataset branch picks which cells v1 contains; the full matrix is about 48.
- **Each cell holds:** a structured profile as ground truth (fictional name, `example.com`
  email, `555-01xx` phone, roles, dates, skills); the résumé text for the legacy flow; the same
  profile as a corpus seed with at least two summary variants; one or two JDs; and the set of
  facts a generated résumé may state.
- **Determinism.** A cell's id comes from (profession, level, variant). All structured facts
  derive from that id and the extract, never from a model. Each cell is serialized as canonical
  JSON (sorted keys, normalized newlines) with a sha256 per cell and one for the manifest; CI
  verifies them and fails on drift. Regenerating prose needs a new prompt version and a new hash.
- **Budgeted draws.** A seeded stratified draw over the matrix gives the group-size runs.

**What public data lacks:** paired résumé and JD sets with a documented non-IT spread, explicit
seniority labels, clean licences, and human fit judgments. The fit labels that exist come from
an LLM or a score.

**Not verified:** Kaggle licences and LiveCareer's terms of use; the licence, origin and PII
status of `cnamuangtoun/resume-job-description-fit`; ESCO's licence text; OpenResume's size and
licence; the Djinni CV-to-JD join key; whether LiveCareer-derived rows are real people; O\*NET's
occupation count and file layout.

### 6.1 Second pass, résumé sets (2026-10-20, in progress)

Added on branch `docs/eval-dataset-research` after the owner found the first pass too shallow and the
current golden set too narrow (three personas, all tech, one level each: `evals/fixtures/synthetic/`).
This subsection is a **working record of one subagent's report**, written the turn it arrived (C-8).
The agent says its fetch tool summarized pages, so every row is *(reported)* unless it says
**raw-read**. A row moves to verified only when the orchestrator reads the primary page raw. The
job-description and taxonomy passes are still running; section 6's table and the matrix proposal are
rewritten from all three once they land.

| Source | Declared licence | Provenance | Covers | Committable (desk view) | Status |
|---|---|---|---|---|---|
| `ahmedheakl/resume-atlas` | `mit` (front matter, **raw-read**) | images from Google, Bing and LiveCareer, OCR'd; warns of names, phones, emails | 13,389 rows, 43 categories; no levels, no JDs | no | provenance reported |
| `opensporks/resumes` (Kaggle mirror) | CC0 (uploader's tag) | scraped from livecareer.com; PII section empty | 2,484 rows, 24 categories; no levels, no JDs | fetch-only | Kaggle page unreadable; reported |
| `datasetmaster/resumes` | `mit` | real "anonymized" CVs mixed with Faker rows, not flagged per row | 4,817 rows; technical roles only | no | viewer crashed; reported |
| `sukhrobnurali/resume-parsing-vision` | `cc-by-4.0` | fully synthetic, code authors fields, a model writes prose | 1,000 résumés, 32 software-industry roles (top 12 listed on the card include System Administrator, Support Specialist, Networking, Data Scientist, Mobile Developer, Scrum Master, Security Specialist, DB Administrator, Architect, Product Owner, ML Engineer), 0 to 25 years, English prose; no JDs | yes, IT only | **raw-read 2026-10-20** (README via `/raw/main/README.md`: licence, "no real personal data", `example.com`, `555-01xx`, structured-first generation, frozen splits). `DATASHEET.md` not read |
| `netsol/resume-score-details` | `cc`, no version | GPT-4o JDs over résumés of undisclosed origin | 1,031 samples | no | reported |
| `cnamuangtoun/resume-job-description-fit` | none stated, no README | not found | 1K to 10K pairs | no | reported |
| `anatiagent/resume-posting-pairs` | `other`, each source its own terms | real résumés from Indeed and Reddit; LLM-judge labels | 17,187 pairs, IT | no | reported |
| Djinni (`lang-uk`) CVs | `mit` (card and paper abstract) | real, "anonymized", method not found | 210,250 CVs, IT, years 0 to 11 | fetch-only | reported |
| **PopResume** (`sumin-yu/PopResume`) *(new)* | `cc-by-4.0` | synthetic from aggregate population statistics (ACS PUMS, PSID, SSA names); "No real individual's data is included" | 60,884 résumés, **5 occupations**: accountants, construction laborers, teachers, registered nurses, software developers; seniority unconfirmed | fetch-only until the repo gate is read | **partly raw-read 2026-10-20:** HF API metadata gives `license: cc-by-4.0`, `gated: auto`, file names for five occupations; the paper (arXiv 2603.22714, abstract raw-read) says "population-representative", 60.8K résumés, five occupations, built for fairness auditing. The README body returns HTTP 401, so "No real individual's data is included" is **not verified**. It is a fairness benchmark with demographic attributes, not a level-labelled set |
| CareerCorpus (Mendeley) *(new)* | CC-BY-4.0 | derived from the LiveCareer scrape and LinkedIn profiles | 302 résumés, 6 categories | no | reported |
| ResumeBench (EMNLP 2025) *(new)* | not found | synthetic | per a search snippet: 2,500 résumés, 30 career fields, 5 languages | unknown | page 404; **no release or licence found** |
| Seniority paper, arXiv 2509.09229 *(new)* | paper is CC BY 4.0 (the data's is not found) | real plus synthetic "hard examples" | seniority-labelled résumés; size not found | no, until the licence and split are known | the only seniority-labelled résumé set found; short link not followed |
| arXiv 2508.21179, SynthResume 2510.09722, TalentCLEF 2026 | n/a | n/a | no data release found, or a sample of a few kB | no | reported |

**What the agent concluded (reported):** no résumé source is both committable and broad across
professions and levels. `sukhrobnurali/resume-parsing-vision` is the only one that clears licence and
provenance today, and it is tech only. PopResume is the only one that crosses sectors and may qualify.
The gap is non-tech professions with seniority labels and a clean licence; closing it means generating
those cells, using these sets as schema and style references.

**Not yet done:** PopResume's gate terms and a sample row (needs an authenticated read, which the
orchestrator has not done), the `resume-parsing-vision` `DATASHEET.md`, ResumeBench's paper and the
seniority paper's dataset link.

**What the raw reads change (2026-10-20):** `resume-parsing-vision` is broader inside IT than "software
roles" suggests (administration, networking, security, support, data, mobile, scrum, product owner), so
for the owner's IT sub-roles it is a usable schema and style reference and a committable source of
tech-side résumés. It has no non-IT professions, no level names (years only) and no JDs.

### 6.2 Second pass, job-description sources (2026-10-20, in progress)

A working record of the second subagent's report, written the turn it arrived (C-8). The agent used the
same summarizing fetch tool, so "verified" in its report means the tool returned the quoted fragment, not
that raw text was seen. Every row is *(reported)* unless marked **raw-read**. Why this matters: job
descriptions are the half that might be real **and** committable, which résumés are not (6.1).

| Source | Declared terms (as returned) | Provenance | Covers | Committable (desk view) | Status |
|---|---|---|---|---|---|
| **USAJOBS** API and Historic JOA | "OPM provides Public Data under an open license"; "Prior OPM approval is not required"; "may be copied, stored, reformatted, adapted, analyzed, published, redistributed" (sentence cut off); "does not include content separately identified in accompanying metadata or notice" | government-authored announcements; contact names and emails may need scrubbing | search API returns duties, summary, qualifications, requirements, grade range, series; **GS grade and a supervisory flag are the level signal**; live search is a 0 to 60 day window; Historic JOA is metadata only | yes for API text, desk view | **terms reportedly revised days ago** (a news item dated 2026-10-13; older wording barred redistribution). A plain `curl` of the terms page returned HTTP 403 "Access Denied" (edge filter, 2026-10-20) and the browser extension was not connected, so the orchestrator has **not** raw-read them. A second, independent `WebFetch` (tool-mediated, still a summary) returned the same quotes plus: modified data must not be presented as official or imply endorsement; OPM keeps no archive of copies; attribution is encouraged, not required; the page shows **no effective or last-updated date**. Must be read raw (a browser, or a person) before any reliance |
| **JobSet** (`Crisp-Unimib/JobSet`) | CC BY 4.0 | LLM-generated ads shaped by real EU ads and ESCO; the real ads are not in the set | 15,469 English ads, about 215 words, 396 ESCO occupations (non-tech included), no level field | yes, desk view | **raw-read 2026-10-20** (README via `/raw/main/README.md`): `license: cc-by-4.0`, "synthetic", "396 ESCO IV digit-level occupations ... 15,469 unique job postings", about 39 per occupation, English; the card warns against use in automated hiring decisions. The generating model is not named in the part read, so its terms are unchecked |
| **NYC Jobs Postings** (Socrata `kpav-sd4t`) | no licence field in metadata; NYC Admin Code 23-502(d): public data sets available "without any ... license requirement or restrictions" on use; the city's general terms say "All rights are reserved" | municipal government | `level`, `career_level`, `civil_service_title`, `job_description`; municipal roles (IT, health, engineering, legal, trades, admin); finance and sales thin | probably, desk view | **metadata raw-read 2026-10-20** (`/api/views/kpav-sd4t.json`): `licenseId` and `license` are null, attribution "Department of Citywide Administrative Services (DCAS)", weekly updates, current postings only. `career_level` counts: Experienced (non-manager) 2,013, Entry-Level 270, Manager 214, Student 61, Executive 36. `job_category` top values: Engineering/Architecture/Planning 352, Legal 213, Public Safety 173, Health 160, Administration/HR 140, Technology/Data/Innovation 128, Finance/Accounting/Procurement 120, so finance is not thin. No licence statement was found on the dataset; the statute and the "All rights are reserved" tension are unresolved |
| Djinni English JDs (`lang-uk`) | `mit` (card and paper abstract) | posts from the Djinni IT board, 2020 to 2023; employer consent not stated | 141,897 JDs, IT only, experience-years classes and Junior/Middle/Senior titles | tech only, with caution | consent unverified |
| Canada Job Bank open data | Open Government Licence, Canada | federal | monthly CSVs; NOC codes, wages, requirements; **no description text** | licence yes, little use | text of the licence not read |
| SkillSpan (`jjzha/skillspan`) | `cc-by-4.0` | "usually from job ads", method unstated | 11,543 annotated sentences, not whole postings | low utility | reported |
| Web Data Commons JobPosting and Common Crawl | WDC: "for research purposes only"; Common Crawl: content "may be subject to separate terms" | scraped employer and board pages | 189.8M quads, 61,024 hosts, 7.57 GB | **no** | quotes returned by the tool |
| LinkedIn Job Postings (Kaggle, `arshkon`) and its HF copy | Kaggle page unreadable; HF copy tagged `mit` by the uploader | scraped from LinkedIn | has `formatted_experience_level` | **no** | Kaggle blocked |
| Remotive API | "Please do not submit Remotive jobs to third Party websites" | board | remote tech | no | reported |
| Arbeitnow API | no terms found | ATS pages | European | fetch-only, terms unknown | reported |
| UK Civil Service Jobs, EURES, Australia, JobBERT, other Kaggle sets | not found or page blocked | n/a | n/a | treat as no until read | not read |
| O\*NET database | "licensed under a Creative Commons Attribution 4.0 International License"; attribution to O\*NET and USDOL/ETA | US Department of Labor | occupation descriptions and tasks, **not postings**; the agent did not read an occupation count or Job Zones | yes, with attribution | reported (6.3 re-reads it) |

**What the agent concluded (reported):** the union of USAJOBS, JobSet and NYC comes closest to broad and
level-labelled. Real private-sector postings for healthcare, trades, sales and finance under an open
licence were **not found**.

### 6.3 Second pass, taxonomies and level frameworks (2026-10-20, in progress)

A working record of the third subagent's report, written the turn it arrived (C-8). Same caveat: the
fetch tool summarizes; every row is *(reported)* unless marked **raw-read**. This is the source for a
profession by level matrix's structured facts, not for postings or résumés.

| Source | Declared terms (as returned) | Content | Level information | Committable (desk view) | Status |
|---|---|---|---|---|---|
| **O\*NET 31.0** | page titled "O\*NET 31.0 Database Content License", CC BY 4.0; credit O\*NET and USDOL/ETA, link the licence, indicate changes; "O\*NET" is a trademark | August 2026 release per the what's-new page; **923 occupations with Job Zone ratings**, 1,016 rows in Occupation Data; Task Statements 18,838; Task Ratings 165,780; Software Skills 31,821; Work Activities 74,702; Excel, CSV, JSON, SQL, RDF. A file called "Technology Skills" is no longer listed (now "Software Skills") | **Job Zones are now four (1-2, 3, 4, 5)**, merged in the 30.2 release (Feb 2026). A zone is a property of the occupation, not a career stage: Software Developers is one zone for every seniority. Zone text: 5 = "Many require more than five years of experience" | yes, with attribution | **raw-read 2026-10-20** (`onetcenter.org/license_db.html`, `database.html`, `onetonline.org/help/online/zones`): licence text "licensed under a Creative Commons Attribution 4.0 International License ... credit the O\*NET 31.0 Database and the U.S. Department of Labor ... link to the license ... indicate where any changes were made"; the stated credit line for verbatim use and for edits; trademark rule ("O\*NET" as an adjective). Job Zones file "923 rows updated in 31.0"; Job Zone Reference "4 rows"; the four zones read as "Job Zone 1-2 ... 3 ... 4 ... 5". The licence says "Except as noted below", and the exception text was not read. The page's release date and the old-to-new zone mapping were not read |
| **UK DDaT Capability Framework** | footer: "All content is available under the Open Government Licence v3.0, except where otherwise stated"; "© Crown copyright" (returned as raw) | 8 families, 53 roles: Architecture, Chief digital and data, Data, IT operations, Product and delivery (product manager, delivery manager, business analyst, programme delivery manager), Quality assurance testing, Software development (DevOps engineer, frontend, software developer), User-centred design (8 roles). No cyber security family | **software developer has 9 levels** (Apprentice, Junior, Developer, Senior, Senior-management, Lead, Lead-management, Principal, Principal-management); skills rated Awareness, Working, Practitioner, Expert by level. **Only the software-developer ladder was read** | yes, with OGL attribution | **home page raw-read 2026-10-20** (`understand-digital-data-roles-skills.service.gov.uk`): footer "All content is available under the Open Government Licence v3.0, except where otherwise stated / © Crown copyright"; role list includes Test engineer, Quality assurance test analyst, Interaction designer, User researcher, Service designer, DevOps engineer; links "Download framework content" and "Civil Service job grades in this framework". The OGL text, the download file and every role's ladder except software developer (read via summary) were not read |
| NIST NICE Framework Components v2.2.0 | NIST licence page: works by NIST employees "not subject to Copyright protection within the United States"; third-party parts may be | work roles with task, knowledge and skill statements; XLSX, JSON; new supply-chain role and DevSecOps competency in v2.2.0 | none in the components | likely yes, with credit | the v2.2.0 date conflicts (April 28, 2026 on the news page, 2025 on the versions page); work-role count not stated by NIST |
| ESCO v1.2.x | FAQ: "can be downloaded, used, reproduced and reused for any purpose"; services must carry an ESCO statement; modified versions "clearly indicated" | about 3,039 occupations and 13,939 skills (snippet) | none | unclear, leaning yes | the licence page 404'd; the acknowledgement page not read |
| `jorgef/engineeringladders` | Apache-2.0 (licence file read) | Developer, Tech Lead, TPM and Engineering Manager ladders; levels D1 to D3 and 4 to 7 | yes, tech | yes, with notice | via summary |
| `sdras/career-ladders`, Enova, GitLab handbook | MIT per page / snippet / not found | ladder content not seen | levels exist | unclear | not verified beyond the label |
| UK SOC 2020 | OGL v3.0 (page footer) | 412 unit groups (snippet) | skill level 1 to 4 not described on the page read | yes, with attribution | dataset files not checked |
| Canada NOC 2021 | Statistics Canada Open Licence | 516 unit groups (snippet); TEER categories | TEER 0 to 5 | likely yes | licence terms not read |
| **SFIA 9** | "you need a licence to use SFIA"; "All use of SFIA is under licence" | seven levels of responsibility | the best IT level scale found | **no** | licensed |
| Lightcast Open Skills | "excluding commercial or for-profit purposes" | skills only | none | **no** | updated 2026-10-01 |
| ISCO-08 | page 403; copyright page 404 | n/a | skill levels 1 to 4 are from memory | unclear | not verified |

**What the agent concluded (reported):** O\*NET for content across all fields, UK DDaT for tech title
ladders, with NICE adding security detail. **Gaps it states:** O\*NET has no seniority inside a profession
and no Product Manager occupation (IT project managers 15-1299.09 and Project Management Specialists
13-1082.00 exist; no SRE/DevOps code; UX is thin at 15-1255.00); nothing verified gives seniority ladders for
non-tech fields, so the level axis there must be constructed.

**Consequence for 6's earlier line "Job Zone (which maps to level)":** that mapping is weaker than written.
Zones are four, they describe an occupation's preparation, and they do not separate a junior from a staff
developer. Levels need a second source (DDaT ladders for tech; a stated rule elsewhere).

### 6.4 Proposal: the golden matrix (for the owner to choose; nothing here is decided)

**Why the current set is too thin.** `evals/fixtures/synthetic/` holds three personas: `data-scientist-junior`,
`pm-senior`, `sre-mid-level`. All three are tech, one level each. The owner's requirement (2026-10-20): the
v1 set becomes the ground truth for later releases, so it must vary across IT and development, security,
administration, project management, product management, design and UX, and across seniority, **and** (owner's
answer the same day) across sectors as section 6 first proposed.

**What the research settles.**

| Question | Answer from 6.1 to 6.3 |
|---|---|
| Can any existing résumé set be committed as ground truth? | **No** outside IT. `sukhrobnurali/resume-parsing-vision` (CC-BY-4.0, synthetic, 32 IT roles incl. sysadmin, networking, security, support, data, mobile, scrum, product owner) is raw-read and committable but is IT only, has no level names and no JDs. PopResume has five sectors but is a fairness benchmark and its README is behind a gate |
| Can real JDs be committed? | **Possibly.** USAJOBS (open licence reported, **terms not raw-read**) and NYC Jobs (no licence field; statute vs "All rights are reserved" unresolved) carry level labels. Both are government postings, so their language skews public-sector. JobSet (CC BY 4.0, raw-read) is synthetic and has no level field |
| What licensed source gives each profession's facts? | O\*NET 31.0 (CC BY 4.0, raw-read): tasks, software skills, work activities, titles, for 923 occupations across all sectors. No Product Manager occupation, no SRE/DevOps code, thin UX |
| What gives levels? | **Tech:** UK DDaT (OGL v3.0, footer raw-read): nine levels for software developer (that ladder read via summary); other roles' ladders unread. **Non-tech:** nothing verified; levels would be an authored rule. O\*NET Job Zones are four and per occupation, so they do not give levels |
| What is not usable? | SFIA (licensed), Lightcast Open Skills (non-commercial), Web Data Commons, Common Crawl, the scraped LinkedIn and LiveCareer sets |

**Proposed design.**

1. **Golden set: authored, committed, frozen.** Every committed résumé and JD is generated from a
   structured profile authored by code from O\*NET facts and a level ladder, with a model writing only the
   prose (the pattern the CC-BY set above documents). No third-party posting text is committed, so no
   licence question rests on a posting. The generating model id, prompt version and a sha256 per cell are
   recorded; CI fails on drift. Ground truth is exact by construction, which keeps decision 5 (no human
   labels) intact.
2. **Exploration set: fetched, real, never committed.** Real JDs from USAJOBS and NYC Jobs (and JobSet for
   breadth) fetched on demand, pinned by a manifest of source revision and sha256, used for "does this hold on
   real text?". This is where the C-2 route question lives. A result there is a lead and never gates.
3. **Why not commit real postings into the golden set:** the terms are unsettled for both sources, they skew
   to government, and a posting can be edited or withdrawn upstream. The cost of authoring is one generation
   run in step 3, which is already capped paid spend.

**Profession axis: three options for the owner.**

| Option | Professions | Tech coverage | Cost / risk |
|---|---|---|---|
| **A. Section 6 as first written** | about 12, tech as one "engineering" row | the existing three personas only | does not answer the owner's objection |
| **B. 12 professions, tech split (recommended)** | **6 tech:** software engineering (QA as a sub-variant), SRE / DevOps / IT operations, security, data / ML, product management, design / UX. **1 cross-sector:** project / program management. **5 non-tech:** healthcare, skilled trades, finance, education, sales / operations | six tech families, each a profession | 12 by 4 levels fully crossed is exactly 48 cells, so no sampling is needed; creative and legal are left out of v1 |
| **C. 16 professions** | 8 tech (B's six plus IT administration / support and QA as their own rows) + project management + 7 non-tech | eight tech families | 16 by 3 sampled levels is 48 cells, but each profession loses a level, which weakens within-profession level comparison |

**Level axis (proposal).** Four levels: **entry** (about 0 to 2 years), **mid** (3 to 5), **senior** (6 to 10),
**lead or manager** (10+, or a people-lead or staff scope). Tech cells take their rung names and skill
expectations from DDaT where read; non-tech cells take them from a short rule written in the dataset's
manifest (years, scope of responsibility), **marked as authored, not sourced**. A fifth rung (staff or
principal) for tech only is possible and would add cells.

**Industry axis.** A JD-side variant, not a crossed axis: each cell has one or two JDs for the same role in
different industries (for example a security analyst at a hospital and at a bank). That keeps the set at 48
cells and still varies the context.

**The existing personas become cells:** `data-scientist-junior` (data / ML, entry), `sre-mid-level` (SRE,
mid), `pm-senior` (product management, senior). They stay as they are in `evals/fixtures/synthetic/` until
step 3 replaces them; no fixture is edited by this proposal.

**Versioning.** `v1` is frozen when step 3 lands. A later version adds cells or a new level; it never
edits a `v1` cell in place, and a result states which version it ran on. This is what makes the set a
ground truth across releases.

**Size tiers (proposal; sizes are a decision for step 3, set from measured cost).**

| Tier | Cases | Draw | Use |
|---|---|---|---|
| Sentinel | about 21 | one per call kind | "is any call broken"; the arithmetic floor in 5.2 is $0.30 |
| Day-to-day | about 12 | one per profession, level rotated, seeded | tuning one prompt or one area |
| Full golden | 48 | all cells | release gates, model swaps, pre-registered comparisons |

The full set's size follows from 5.6. The exact binomial rule needs at least 5 discordant cases, all in
one direction, for a one-sided p below 0.05 (6 for a two-sided test). If a change flips 15 to 20 percent of
cases, that needs about 30 to 40 cases, so below about 20 cases most comparisons return INCONCLUSIVE. A cost
for 48 cases is a guess: `AGENTS.md` says the 3-fixture synthetic suite costs about $0.30 to $0.40, about
$0.10 to $0.13 per fixture, which scales to roughly $5 to $6 per arm per pass. Not run; step 3's calibration
run measures it.

**What the research did not settle (each blocks something, none blocks the others):**

- USAJOBS terms: not raw-read (HTTP 403 to `curl`; the browser extension was not connected). Blocks only
  *committing* federal text; the exploration fetch can still be planned.
- NYC Jobs: whether the city's open-data statute overrides "All rights are reserved" for this dataset.
- PopResume's gate terms and a sample row; ResumeBench's release; the seniority paper (arXiv 2509.09229)
  dataset link and licence. None is needed for the golden set as proposed.
- DDaT ladders for every role except software developer; the OGL v3.0 text; the downloadable framework
  file's own terms.
- O\*NET's "Except as noted below" exception text, and the old-to-new Job Zone mapping.
- ESCO's licence page (404) if ESCO occupations are ever used.
- Non-tech seniority ladders: none found, so they are authored (above).

## 7. OpenTelemetry

**Finding: there is no released version to pin.** The GenAI semantic conventions moved out of
the main OpenTelemetry semantic-conventions repository. The pages on opentelemetry.io say so,
and the old repository's v1.42.0 (2026-06-12) lists "Move Generative AI semantic conventions to
a dedicated repository" as a breaking change. The new repository,
`open-telemetry/semantic-conventions-genai`, shows no releases and a schema URL marked TODO.
Every page read carries "Status: Development" *(reported; fetched 2026-10-20 through a
summarizing fetch tool, so quotes are near-verbatim — re-read the pages before pinning)*.

**Decision this supports:** the house record is primary and OpenTelemetry is a *projection* of
it, a pure function from a row to a span (and an evaluation event). Pin the projection to one
commit of the conventions repository in one mapping module, so a vocabulary change is a one-file
edit.

**Mapping** *(reported; names as read on 2026-10-20)*:

| Sartor row field | OpenTelemetry name | Note |
|---|---|---|
| `call` | custom `sartor.call` | `gen_ai.operation.name` takes a fixed set (`chat`, ...) |
| `model` | `gen_ai.request.model` | |
| `answered_model` | `gen_ai.response.model` | |
| `prompt_version`, prompt hash | `gen_ai.prompt.version` (needs `gen_ai.prompt.name`) | the hash as a custom attribute |
| `input_tokens` | `gen_ai.usage.input_tokens` | OpenTelemetry's value **includes** cache tokens; Anthropic's raw figure does not, so the projection adds them |
| `output_tokens` | `gen_ai.usage.output_tokens` | includes thinking tokens |
| `cache_creation_input_tokens`, `cache_read_input_tokens` | `gen_ai.usage.cache_write.input_tokens`, `gen_ai.usage.cache_read.input_tokens` | |
| `thinking_tokens` | `gen_ai.usage.reasoning.output_tokens` | already inside output tokens |
| `stop_reason` | `gen_ai.response.finish_reasons` | array of strings |
| `api_request_id` | `gen_ai.response.id` | which Anthropic id belongs here is not confirmed |
| `request_settings` | `gen_ai.request.max_tokens`, `.temperature`, `.top_p`, ... | split the dict |
| `latency_ms` | span duration | OpenTelemetry uses seconds |
| `status`, `error_type` | span status and `error.type` | |
| `username`, `attempt` | none | keep local; never exported |
| (new) provider | `gen_ai.provider.name` = `anthropic` | required attribute |
| (new) operation | `gen_ai.operation.name` = `chat` | required attribute |
| (new) run and call ids | `trace_id` (32 hex), `span_id` (16 hex) | W3C Trace Context sizes; reject all-zero values |

**Evaluation results** have a defined event, `gen_ai.evaluation.result`, with
`gen_ai.evaluation.name`, `.score.value`, `.score.label`, `.explanation` and
`gen_ai.response.id` linking to the output evaluated; it should be parented to the evaluated
call's span. A catalog case result maps onto it directly. An eval run as a whole has no
dedicated span; `invoke_workflow` fits, and using it for that is this doc's inference, not the
convention's wording.

**Content.** The conventions say prompts, completions and instructions are sensitive and are
not captured by default. That agrees with the rule here: content stays in the local result
file, never in a span attribute.

**Dependency.** With only `opentelemetry-api` installed and no SDK, tracing calls are no-ops
(the Trace API specification's absent-SDK section). `opentelemetry-api` 1.45.1 is Apache-2.0,
needs Python 3.10 or later, and depends on `typing-extensions` (wheel about 60 kB; the
dependency list may be longer than the listing showed). The specification does not speak to
network use; that there is no egress without an exporter is an inference. Two options under D-1:

1. **No dependency.** Write the projection as a pure function and emit OpenTelemetry-shaped
   JSON lines locally. Anyone who wants to export runs them through their own collector.
2. **`opentelemetry-api` as an optional extra**, for users who configure an exporter.

Recommendation: start with option 1, which needs no dependency and no `CHANGELOG` entry under
D-1. Ids come from `secrets.token_hex(16)` and `secrets.token_hex(8)`.

**Owner decision 4 (2026-10-20): option 1, with the projection pinned to one commit** of
`open-telemetry/semantic-conventions-genai`. Step 10 re-reads the primary pages and records the
commit before the mapping is written.

## 8. Owner decisions

**Answered by the owner in chat on 2026-10-20.** Each question stays, followed by the answer.
Where the answer is not the recommendation the question carried, it says so.

1. **Dataset:** adopt the O\*NET-based synthetic matrix (section 6), fetch a public set on
   demand, or both. No public résumé set found is cleared for committing.
   **Answer: both.** The committed matrix is the standard set; a public set may be fetched on
   demand and is never committed. *(Not the recommendation: the recommendation was the matrix
   alone.)* The fetch is an outbound connection and must satisfy charter C-2; see 5.4.
2. **Release scope:** does v1.1.0 wait for any of the build order below? Recommendation: wait
   for steps 1 to 3 and for a deterministic-check call eval on every kind; calibrate judged
   rubrics after release.
   **Answer: wait for steps 1 to 3 and for a deterministic-check call eval on every kind.**
   The deterministic parts of steps 4 to 6 are therefore release-blocking; their judged parts
   are not. Item 10 now depends on steps 1 to 6 (items 181 to 186).
3. **Judge model:** keep Haiku 4.5 (past its earliest retirement date), move to a newer Haiku,
   or use a Sonnet-class pin that stays fixed across arms. A stronger judge costs more per case
   and is unmeasured here.
   **Answer: decide at step 9, with data.** Haiku 4.5 stays the judge until then. With decision
   5 answered "no", that data is judge-to-judge agreement (5.7), which is weaker than the gold
   set the question assumed. Whether Haiku 4.5 is still Active was not re-checked.
4. **OpenTelemetry:** option 1 or 2 in section 7; and whether the projection pins to a commit.
   **Answer: option 1 (no dependency), pinned to one commit.**
5. **Gold labels:** one-time human labelling for judge calibration (5.7). D-4 says no recurring
   human labour; a one-time set is the question.
   **Answer: no human labels.** *(Not the recommendation.)* See 5.7 for what that costs.
6. **The avatar prompt:** it was left out of the eval path on purpose (`analyzer.py:1193`).
   Keep that, or bring it in with the documentation-question set (5.3).
   **Answer: bring it in, catalog only.** It gets a catalog entry at step 6; it stays out of
   `_BASE_SYSTEM_PROMPTS` and keeps `AVATAR_PROMPT_VERSION`.
7. **Epic or items:** the board is over its ceiling (24 open against 10). File the build order
   as one epic, as separate items, or hold.
   **Answer: one epic.** Epic 180 holds steps 1 to 10 as items 181 to 190: step 1 open, each
   later step blocked on the one before. Step 11 is item 137, re-parented under the epic.
8. **Publication:** the doc is left out of `PUBLISHED` in `scripts/doc_registry.py`, so it is not
   published to the docs site. Register it when you want the scheme public, or keep it repo-only.
   **Answer: repo-only for now.** Revisit after steps 1 to 3 land.

### Raised after the answers above (2026-10-20, unanswered)

The owner asked that the v1 ground truth be broadened before release and that the open-source research be
deeper first. 6.1 to 6.4 are that research. The questions it leaves, for the owner:

9. **Profession axis:** option A, B or C in 6.4. B (recommended) splits tech into six families, adds
   project management and keeps five non-tech sectors, giving 12 professions by 4 levels, 48 cells.
10. **Golden set composition:** all-authored from O\*NET and a level ladder (recommended), or some committed
    real postings. If real, USAJOBS needs its terms read raw, and NYC Jobs needs a ruling on its statute
    against "All rights are reserved".
11. **Levels outside tech:** no open ladder was found, so the rule is authored in the manifest. Accept,
    or hold the non-tech cells until a source is found.
12. **Whether the exploration fetch targets USAJOBS and NYC Jobs** (the C-2 route question in 5.4
    applies to either).

## 9. Build order

Each step is its own branch with its own plan, consumer enumeration and gate run. None is
started by this doc. Filed on 2026-10-20 as epic 180: steps 1 to 10 are items 181 to 190 in
order, and step 11 is item 137. Per decision 2, steps 1 to 3 and the deterministic parts of
steps 4 to 6 block the v1.1.0 cut. Per decision 1, step 3's on-demand fetch must clear charter
C-2 (5.4). Per decision 5, step 9 calibrates against judge-to-judge agreement (5.7).

| # | Branch | What | Paid spend |
|---|---|---|---|
| 1 | `feat/eval-record-identity` | prompt hashes and the version gate; producer id; trace, span and case ids; parse outcome; judge cost into run totals; fix the cost-by-window leak | none |
| 2 | `feat/eval-catalog-skeleton` | catalog format, lazy loader, the all-kinds gate, `--list`, `--estimate`, `--max-spend`; entries for the kinds already covered | none |
| 3 | `feat/eval-dataset-v1` | the standard dataset, captured upstream inputs, the reachability check; the on-demand public fetch only if it clears charter C-2 | one calibration run, capped |
| 4 | `feat/eval-calls-ingest-analyze` | call evals for `extract_experiences`, `analyze_*`, `clarify`, `iterate_clarify` | capped |
| 5 | `feat/eval-calls-compose` | call evals for the 11 `compose` kinds | capped |
| 6 | `feat/eval-calls-assistant-proposals` | `avatar_answer`, `critique_proposal`, `promote_clarification_to_bullet` | capped |
| 7 | `feat/eval-compare-protocol` | pre-registered spec, noise floor, arithmetic rule; replaces `evals/tune.py` | none |
| 8 | `feat/eval-dashboard-catalog` | Catalog tab, drill-downs, attention view, arm comparison | none |
| 9 | `feat/eval-judge-calibration` | pinned judge, schema parse, judge-to-judge agreement (no gold set, decision 5), over-suppression check; the judge-model choice (decision 3) | capped |
| 10 | `feat/otel-projection` | the pure projection and its mapping module (section 7) | none |
| 11 | item 137's A/B | the Haiku 5.5 comparison, pre-registered, on the full run | capped |

Steps 1 and 2 are the base: they turn the existing `EXPECTED_CALL_KINDS` inventory into a
catalog gate and give every later step an identity to key on. Step 11 is what the owner asked
for first; it comes last because its result is only as good as steps 1 to 9.

## 10. What this doc does not verify

- Every figure marked *(reported)* was found by a research pass and not re-read here.
- The dashboard's full view list and its drill-downs were not re-read; section 3.6 states only
  what was grepped.
- No paid call was made. The $0.30 figure is arithmetic on logged rows.
- The OpenTelemetry names and every dataset row come from a summarizing fetch tool and need a
  re-read before any code or licence decision relies on them.
- Which Anthropic id `api_request_id` holds, and so whether it maps to `gen_ai.response.id`,
  was not checked.

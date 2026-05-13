# Eval Tuning Log

A chronological record of prompt iterations and what each one taught us. The
goal is institutional memory (P5) for human and synthetic agents who tune
this system in the future.

Each entry should answer four questions:

1. **What changed?** (concrete edit, file paths, prompt_version diff)
2. **Why?** (failure mode observed in the dashboard or eval results)
3. **What was the result?** (scores before/after, deterministic metrics)
4. **What did we learn?** (rule of thumb that should bias future tuning)

If a change was neutral or negative, document that too. Failed experiments
prevent re-running them.

---

## 2026-05-12 — `2026-05-11.3` → `2026-05-12.1`: Phase B.2 `<career_corpus>` prompt block

### What changed

- `analyzer.py:_stable_user_prefix` now branches: when `context_set["career_corpus"]` is populated (DB-backed path with CORPUS_BACKED=1), the user prefix emits a structured `<career_corpus iteration="N">` XML block with `<experience>` / `<eligible_title>` / `<bullet>` children carrying stable IDs from the corpus DB. The legacy `<resume>` + `<supplemental_resumes>` blocks are OMITTED in this mode. When `career_corpus` is absent (file-based path), the prefix is byte-identical to `2026-05-11.3`.
- `analyzer.py:generate()` adds a `<corpus_mode>` instruction block when the input carries `<career_corpus>`. The block tells the LLM that each `<bullet>` must be quoted verbatim (selected by ID), and adds three new output schema fields: `selected_bullets`, `proposed_new_bullets`, `proposed_experience_titles`.
- `analyzer.py:GENERATE_CORPUS_REQUIRED_KEYS` — new frozenset extending `GENERATE_REQUIRED_KEYS`. `_parse_or_retry` is invoked with this set when corpus mode is active; the legacy set remains in use otherwise.
- `db/build_context.py:_build_career_corpus_payload` — new helper producing the structured corpus payload. Eligible titles are sorted official-first; only `is_active=1` bullets ship.
- `hardening.py` — new TypedDicts: `CorpusBullet`, `CorpusEligibleTitle`, `CorpusExperience`. `ContextSet` gains an optional `career_corpus` field.
- `PROMPT_VERSION` bumped to `2026-05-12.1`.

### Why

Phase B.1 brought DB content into the pipeline but kept the prompt structure unchanged. The legacy `<resume>` block forced us to synthesize markdown from DB rows — useful as a transitional bridge but throwing away the per-bullet IDs the downstream phases need. Phase B.2 makes IDs first-class in the prompt:

1. **B.3 needs them.** `application_bullet` rows record which bullets the LLM chose; without IDs in the prompt the LLM can't tell us which selection it made.
2. **Multi-framing needs them.** Each experience carries multiple `<eligible_title>` elements. The LLM picks one per JD via `selected_bullets[].chosen_title_id`. The synthesized markdown of B.1 could only carry one title per experience.
3. **Grounding can move from heuristic to structural.** Every output bullet must equal a corpus bullet (lookup by ID). B.3 enforces this; B.2 sets up the data.

### Result

Smoke (DB-backed, testuser corpus, pm-senior JD; 2026-05-12 run):

| Metric | B.1 (`2026-05-11.3`) | B.2 (`2026-05-12.1`) | Δ |
|---|---|---|---|
| Total cost | $0.1465 | $0.1652 | **+13%** (extra output schema fields) |
| cache_read tokens (generate) | 2748 | **3420** | **+24% (improvement)** |
| Output bullets | 22 | 19 | -3 (more disciplined selection) |
| Suspicious bullets (heuristic) | 4/22 | **0/19** | **100% trivially grounded** |
| Required keys in response | 4 (legacy) | 7 (legacy + 3 corpus fields) | — |
| Errors | none | none | — |

Two headline findings:
1. **Cache_read tokens went UP, not down.** The fear from Reviewer Risk #2 (the prompt-cache might collapse under the new prefix shape) didn't materialize. The structured `<career_corpus>` block is just as byte-stable across analyze→generate within an iteration as the legacy `<resume>` was, AND its larger size means more cached tokens to read.
2. **Grounding tightened substantially.** Every output bullet substring-matched a corpus bullet — zero "suspicious" entries (B.1 had 4/22 the heuristic flagged, though those turned out to be legitimate paraphrases on inspection). The LLM appears to have taken the "treat each bullet as immutable, select by ID" instruction seriously. Sets up B.3 (structural enforcement via `application_bullet` rows) to be straightforward.

File-based path (CORPUS_BACKED unset): byte-identical to `2026-05-11.3`. The 247/247 prior tests still pass; the 12 new B.2 tests pass; legacy mock prompts received no corpus_mode block; required-key set defaulted to GENERATE_REQUIRED_KEYS (4 keys).

### What we learned

1. **Cache discipline survives structural prefix changes — when the new structure is itself byte-stable.** The cached prefix block is larger now (more tokens to cache) and the `cache_read_input_tokens` went UP rather than down. Reviewer Risk #2 (cache collapse) doesn't bite when the new prefix is just as deterministic as the old one was.
2. **Structured presentation reduces fabrication temptation.** Telling the LLM "each `<bullet id="bN">` is immutable, record IDs in `selected_bullets`" produced 19/19 trivially-grounded bullets vs the legacy prompt's 18/22. The framing change matters more than the words on the page.
3. **Sonnet trims aggressively when given structure.** Output bullets dropped from 22 to 19 with cleaner selection. The LLM appears to be using the structured corpus to be more disciplined about what to include rather than reaching for completeness.

### Open questions / future tuning targets

- Should `<bullet tags="...">` carry actual tag values? B.2 leaves the attribute empty pending B.3's tag join. Surfacing tags helps the LLM filter by role family but adds tokens; the deterministic JD-aware pre-filter (also B.3) may make this unnecessary.
- `proposed_new_bullets` `pattern_kind` — does the LLM reliably distinguish xyz vs car? Spot-check after a few smoke runs; if it always picks one or the other, drop the field.
- Should `clarify()` and `clarify_iteration()` also gain corpus-mode instructions? They consume the same prefix so they SEE `<career_corpus>` but their output (questions) doesn't need IDs. Probably defer until we see specific rubric regressions.

---

## 2026-05-11 — `2026-05-11.2` → `2026-05-11.3`: iteration-probe worked examples

### What changed

Two follow-up fixes after the first iteration_quality eval pass surfaced a 3.2 score (below the 4.0 threshold) and a clear failure-mode diagnosis:

- **Fixture refinement** (fix 1): `evals/fixtures/synthetic/sre-mid-level/expected.json` — the `edit_target_substring` was extended from `"error budget burn"` to `"error budget burn by tightening retry semantics in the ingress layer"` and the `edit_replacement` was rewritten as a noun-phrase that fits the surrounding `"Reduced control-plane X; rewrote..."` clause structure. This eliminates the malformed-bullet artifact that the original mid-substring substitution produced.
- **Prompt tightening** (fix 2): `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT` — added a WORKED EXAMPLES block with two OK/NOT-OK pairs for iteration probes. Pattern: when a recent edit introduces a substantive claim (named numbers, ownership words, framework names), probe DEPTH (who/which/how-many/cadence). Avoid asking why (motivation isn't source material) or whether (yes/no dichotomies yield no detail).
- `PROMPT_VERSION` bump 2026-05-11.2 → 2026-05-11.3 in the same commit per CLAUDE.md.

### Why

Run 2 of the iteration_quality eval (the one with PROMPT_VERSION 2026-05-11.2 + the original fixture) scored 3.2, with grader reasoning showing the iteration_probe correctly noticed the malformed bullet in the iter-0 generated resume but answered the wrong question — "is this grammatical?" instead of "what is the substantive claim?". Two distinct failure modes were entangled: a fixture artifact (malformed substitution) AND a prompt gap (no guidance on what makes a substantive iteration probe vs a copy-editing one).

### Result

Four runs total on `sre-mid-level`:

| Run | Time (UTC)              | Prompt | Fixture          | iteration_quality | Failed rules                                                         |
|-----|-------------------------|--------|------------------|-------------------|----------------------------------------------------------------------|
| 1   | 2026-05-11T22:56:08Z    | .2     | original         | 2.1               | (not analyzed)                                                       |
| 2   | 2026-05-11T23:53:39Z    | .2     | original         | 3.2               | missing_expected_theme — substring substitution broke bullet grammar |
| 3   | 2026-05-12T00:22:05Z    | .2     | refined (fix 1)  | 3.2               | leading + fabricated + compound + missing_theme                      |
| 4   | 2026-05-12T00:32:58Z    | .3     | refined (fix 1)  | 3.2               | compound + missing_theme                                             |

**Fix 1 (fixture)** moved the failure mode from "iteration_probe asks about syntax" to "iteration_probe asks about cause/effect (was that deliberate or accidental?)". Substantively cleaner question but still not on-target. Grader cited "leading_question" and "missing_expected_theme" with the SLO ownership themes specifically uncovered.

**Fix 2 (prompt)** moved the iteration_probe to substance-of-claim (q1 explicitly probed SLO ownership scope, hitting the expected theme). Grader called this out as a direct hit. **The numeric score didn't move (still 3.2)** because other questions in the 5-question batch tripped different rules: q4 was compound ("before/after MTTR figure or percentage improvement" combines two asks), q3 was speculative (probed scheduling pipeline work for an API-edge SRE — borderline fabricated), and the scope_probe theme (incident commander vs writer-up) wasn't covered by any question.

So fix 2 succeeded on its targeted dimension but didn't reach the 4.0 threshold because the rubric compounds across multiple per-question dimensions and the LLM keeps producing 1-2 borderline questions per 5-question batch.

### What we learned

1. **The Haiku judge applies multi-dimensional strictness.** Hitting 4.0 requires near-perfect composition across 7+ rubric criteria simultaneously. A single substantive improvement (iteration_probe quality) doesn't lift the aggregate when other dimensions stay borderline.
2. **Prompt fixes land on their targeted dimension.** Run 3 → run 4 lost `leading_question` and `fabricated_gap` on the iteration_probe specifically, gained nothing new on that question. The targeted improvement is real even when the score doesn't move.
3. **Single-fixture eval has unhelpful variance.** Four runs at 2.1 / 3.2 / 3.2 / 3.2 — the first run is an outlier that may have been judge noise, may have been a Sonnet generation that produced a worse question set. Without 2-3 fixtures producing iteration_quality samples, attribution to "this prompt change helped" vs "this run's generation was lucky" is hard.
4. **Substring-mid-bullet substitution is a fragile fixture mechanic.** Fixtures that simulate user edits should use whole-line targets OR noun-phrase substitutions that fit the surrounding clause structure. The refined fixture works because the new replacement reads as a clean grammatical clause within the existing bullet.

### Per-question prompt tightening — plan for next iteration

**Target version:** `2026-05-11.4` (bundle prompt revisions 1–4 below into ONE commit; do not land them piecemeal — see "Considered and rejected" for why).

The 4.0 threshold isn't reachable by chasing single failure modes one at a time when the rubric strictness compounds. Next iteration should bundle four prompt revisions plus four structural follow-ups, then re-baseline.

**Prompt revisions (`analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`, lines ~107–146; consider also `CLARIFY_SYSTEM_PROMPT` at ~136 for shared rules like #1 and #3):**

1. **Compound-question worked-example pair.** The "no compound questions" rule is in the prompt but the LLM keeps producing borderline-compound ones (q5 run 3, q4 run 4). Add an OK/NOT-OK pair:
   - NOT OK: "What was the before/after MTTR figure or percentage improvement?" (combines absolute and relative asks)
   - OK: "What was the MTTR before and after?" (single comparative ask) OR "What percentage MTTR reduction did you measure?" (single ratio ask)
   - Pattern: split "X or Y" forms into a single ask; prefer the more specific framing.

2. **Speculative-probe guard rule.** The iteration clarifier reaches for adjacent JD keywords without checking whether they fit the candidate's title/role (q3 run 4 asked an API-edge SRE about scheduling-pipeline work). Add a rule:
   - "Do NOT probe for skills the candidate's job title/role doesn't naturally encompass. If the JD lists 'scheduling pipeline' but the candidate's role is 'API edge SRE', the probability of relevant experience is low — these probes feel out-of-touch and risk grader-fabricated_gap flags."
   - Worked example aligned to the actual run-4 failure.

3. **Leading-tone worked-example pair** for iteration_probe specifically:
   - NOT OK: "Was the SLO definition deliberate or reactive?" (yes/no dichotomy, leading)
   - OK: "What process drove the SLO targets — service-level analysis, customer commitment, error-budget tracking?" (lists concrete options without bias)
   - Already partially covered by the WORKED EXAMPLES block from fix 2 but worth promoting a leading-tone-specific example to the same prominence as the substance-of-claim example.

4. **Scope-probe coverage rule.** The current prompt biases toward experience+iteration probes (≥50% combined), which de-prioritizes scope_probe. When the fixture's `expected_iteration_themes.scope_probes` is non-empty, the eval grades against scope coverage anyway. Either:
   - (a) Change the prompt to require at least one scope_probe when current-draft ambiguities exist (most drafts have some), OR
   - (b) Relax the rubric's `missing_expected_theme` to not require scope_probe coverage if the prompt didn't mandate one.
   - (a) is the cleaner fix because scope_probes ARE useful and the current bias is just an artifact of optimizing for ground-truth sourcing.

**Structural follow-ups (not prompt changes; do these BEFORE the prompt revisions to unblock variance attribution):**

5. **Add `iteration_scenarios` to pm-senior and data-scientist-junior fixtures.** Three samples per run lets us reason about iteration_quality with a 3-sample mean rather than treating each run as a singular signal. Without this, we can't confidently attribute prompt changes to score movements vs Sonnet/Haiku non-determinism. Reference schema: `evals/fixtures/synthetic/sre-mid-level/expected.json` lines 35–57. Each fixture needs an `edit_target_substring` (must survive Sonnet's rewriting — pick a distinctive phrase known to appear in the source resume), an `edit_replacement` (noun-phrase that grammatically fits the surrounding clause; do NOT use a standalone sentence per fix 1's lesson), `clarification_answers` keyed by the iteration question id the runner will produce, and `expected_iteration_themes` with `iteration_probes` / `experience_probes` / `scope_probes` lists.

6. **Re-generate from the iteration context and grade against grounding/keyword_coverage.** Currently the eval iteration phase (`evals/runner.py:_run_iteration_phase`, lines ~340–460) grades only the iteration_quality of the new questions; it does NOT verify that the iteration generation respects the `<historical_resumes>` demotion language and the typed-edits-as-ground-truth carve-out. This was deferred for cost reasons. Implementation sketch: after grading iteration_questions, call `generate(client, iter_context, analysis, ...)` again to produce iter-2 output, compute `_post_generation_metrics` on it, then run the grounding and keyword_coverage rubrics against the iter-2 result and emit those records with `iteration_scenario` set. Adds ~$0.50/scenario/run.

7. **[USER-FLAGGED, 2026-05-11 session]** **Clarification-as-grounding worked example** in the GENERATE prompt's grounding block (`analyzer.py:generate()` worked-examples block, currently around lines ~770–810 covering source-bullet variants and the typed-edits pair). The user raised this concern: a candidate's clarification answer is treated as first-person ground truth and citable in the resume, but there is NO worked example specifically modeling extension-vs-citation for clarifications. A candidate who answers "Yes, used K8s briefly on a side project" could in principle have the LLM extend that to "Led K8s migration to production" — the no-invention rule forbids it but no example trains the pattern. Mirror the typed-edits pair:
   - Source: candidate clarification answer = "Yes, used K8s briefly on a side project."
   - OK to write: "Familiar with Kubernetes from side-project work."
   - NOT OK: "Led K8s migration to production." (extends scope and seniority beyond what the candidate stated)

8. **Rubric/judge calibration.** Run 3's grader called q2 (multi-region) `fabricated_gap` even though `expected_iteration_themes.experience_probes` explicitly lists "multi-region control plane work not yet covered". Multi-region is in `preferred_skills` (not `essential_skills`) and the grader treated preferred ≠ legitimate gap. The `iteration_quality.md` rubric's `fabricated_gap` definition says "cites a signal-source value that doesn't match" — preferred_skills IS a signal source, so the grader was being stricter than the rubric documents. Either tighten the rubric language to spell out that preferred_skills count as legitimate signal sources, OR add an explicit "preferred-skill probes are valid" example. Track whether this manifests on other fixtures or is sre-specific noise.

**Recommended sequencing:**

| Step | Action | Cost     | Outcome |
|------|--------|----------|---------|
| A    | Items 5 + 7 (fixture work + grounding worked example, no prompt-numbered version bump for #5 alone; bump for #7 to 2026-05-11.3a or fold into 2026-05-11.4) | $0 API  | More fixtures + closes the user-flagged grounding gap |
| B    | Run `python evals/runner.py --suite synthetic` ×3 at PROMPT_VERSION 2026-05-11.3 (with item 7 applied) | ~$4.50  | Establishes 3-fixture × 3-run baseline mean for iteration_quality |
| C    | Bundle prompt revisions 1–4 into ONE commit, PROMPT_VERSION → 2026-05-11.4 | $0 API  | Single attribution event for the prompt change |
| D    | Run `python evals/runner.py --suite synthetic` ×3 at 2026-05-11.4 | ~$4.50  | Compare means against B to attribute the prompt revision's effect |
| E    | If means clear acceptance criteria (below), close out. Otherwise append findings here and iterate. | —       | — |
| F    | Item 6 (re-generate + re-grade) goes in only after iteration_quality is stable ≥4.0; until then it adds cost without unlocking new signal. | ~$0.50/scenario/run additional | — |

### Pick this up cold — exact next steps

If you're returning to this work without context, follow this checklist in order:

1. **Sanity check:** read the four-run table above (PROMPT_VERSION column tells you which prompt produced which score). Then run `git log -- evals/results/` and `git log analyzer.py` to confirm nothing has shifted since this entry was written.
2. **Confirm baseline still holds:** run `python evals/runner.py --fixture sre-mid-level` once. If iteration_quality scores wildly differently from 3.2 (say, <2.0 or >4.5), the model versions or judge behavior changed and the failure-mode analysis below may not apply — re-diagnose before applying any planned fix.
3. **Inspect prior eval results:** `evals/results/*.jsonl`. The four runs from this session are at timestamps `20260511_225608Z`, `20260511_235339Z`, `20260512_002205Z`, `20260512_003258Z`. Each line is one (fixture, rubric) grading. The `reasons` array on iteration_quality records is the most useful artifact — it explains what the judge saw.
4. **Apply structural items first** (5 + 7 from the plan above). These are cheap and unblock attribution.
5. **Establish the baseline** (step B in the sequencing table above): 3 runs at PROMPT_VERSION 2026-05-11.3 across all three fixtures. Record the mean iteration_quality score per fixture in this TUNING_LOG.
6. **Apply the prompt bundle** (items 1–4 in ONE commit, version → 2026-05-11.4).
7. **Re-baseline** (step D). Compare the new 9-grading mean to the prior 9-grading mean.
8. **Decide:** if acceptance criteria below are met, append a new TUNING_LOG entry summarizing the win and close out. If not, the prompt bundle didn't cleanly land — re-examine which of items 1–4 helped vs hurt by running the eval with subsets of them applied.

### Acceptance criteria — when iteration_quality is "done"

- 3-fixture × 3-run mean iteration_quality ≥ 4.0 at the same PROMPT_VERSION.
- No (fixture, rubric) regression > 0.5 vs the 2026-05-11.3 baseline on the four other rubrics (ats_format, grounding, keyword_coverage, tone, clarification_quality).
- iteration_quality `failed_rules` across the 9 records does NOT contain `redundant_question` (would indicate the build-on-don't-re-ask rule isn't holding) or `targets_stale_draft` (would indicate the current-draft awareness isn't holding).
- `compound_question` and `missing_expected_theme` may appear at most once across the 9 records — they're the residual failure modes prompt revisions 1 and 4 are designed to suppress, but eliminating them entirely is unrealistic given Haiku judge variance.

### Considered and rejected this session

Documenting these so a future tuner doesn't burn budget retrying:

- **Revert PROMPT_VERSION to 2026-05-11.2.** Score didn't move from 3.2 after fix 2 — but the targeted dimension (iteration_probe substance-of-claim quality) clearly improved per grader reasoning. Reverting would give up a real semantic improvement to chase a number that wasn't moving for orthogonal reasons.
- **Run another iteration_quality pass with no changes to confirm 3.2 is stable vs noise.** Given 2.1 / 3.2 / 3.2 / 3.2, the floor looks like 3.2 with the first run as a one-time outlier. Burning another $0.50 to reconfirm wasn't worth it given the 3.2 wasn't going to be the deciding signal anyway — credible attribution needs structural work (more fixtures) first.
- **One-at-a-time prompt tweaks** to chase failed_rules individually. Demonstrated this session: each tweak landed but the aggregate stayed flat because Haiku-judge variance plus rubric strictness across 5 questions × 7+ criteria swamps single-dimension wins. Bundle 1–4 into a single 2026-05-11.4 commit.
- **Lower the iteration_quality pass threshold below 4.0** to make the rubric more forgiving. Rejected because the threshold matches every other rubric in the suite (4.0); making iteration_quality a special case would erode the rubric set's consistency. The fix belongs in the prompt and the fixture, not the threshold.

### Cost / scope notes

- Four iteration_quality runs this session: ~$0.60 total in API costs. Each run is one full pipeline (analyze + clarify + generate + clarify_iteration Sonnet calls) plus 6 Haiku grading calls.
- Three-fixture × 3-run baseline at next PROMPT_VERSION: ~$1.50 per run × 3 runs ≈ $4.50 per baseline (need two baselines — pre and post prompt bundle — so total ~$9.00).
- Item 6 (re-generate + re-grade) adds ~$0.50/scenario/run, so $1.50 per 3-fixture run once enabled.

---

## 2026-05-11 — `2026-05-11.1` → `2026-05-11.2`: iterative refinement loop

### What changed

- `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT` — new dedicated persona for
  the post-generation interview. Two distinguishing instructions vs
  `CLARIFY_SYSTEM_PROMPT`: (1) treat prior clarifications as established truth,
  follow up rather than re-ask; (2) target the CURRENT draft's specific
  weaknesses surfaced by the four signal sources, not generic JD gaps.
- `analyzer.py:clarify_iteration()` — new function with 4-signal-source
  prompt template (current draft, recent edits, deterministic signals,
  prior clarifications). Reuses `_parse_or_retry` with
  `call_kind="iterate_clarify"` for telemetry parity.
- `analyzer.py:generate()` — grounding worked-examples block extended with a
  fourth OK/NOT-OK pair specifically for typed edits ("Shipped V2 to
  enterprise" / "Led V2 launch to 50 enterprise customers"). The grounding
  question itself widens to acknowledge typed edits as ground truth alongside
  clarification answers.
- `analyzer.py:_supplemental_block(iteration)` — wrapper switches to
  `<historical_resumes>` at iteration ≥ 1 with explicit demotion language.
- `evals/rubrics/iteration_quality.md` — new fifth rubric.
- `evals/runner.py` — optional iteration phase grades the new questions
  against `iteration_quality` for fixtures with `iteration_scenarios`.
- `PROMPT_VERSION` bump in the same commit.

### Why

The clarification interview that landed in `2026-05-11.1` proved valuable but
also surfaced a pattern: candidates would type meaningful edits into the
preview, then click REFINE — and the regenerate-from-context path silently
discarded those edits. Two distinct fixes were required:

1. **Edit-aware baselines.** The preview-edit gate (Phase 3) plus
   `edited_resume_text` carve-out in the grounding check let typed edits
   feed the next generation as first-person ground truth. The grounding
   worked-example pair specifically targets the new failure mode this opens
   up: the LLM treating an edit as license to inflate ("shipped V2" →
   "shipped V2 to 50 enterprise customers").
2. **Iteration-aware probing.** The analyze-time `clarify()` is rooted in
   the original resume vs JD gap. Once iteration 1 has produced a draft
   (possibly with edits), the relevant gaps shift: missing keywords may be
   filled, new ambiguities may be introduced by edits, and prior
   clarifications are now established truths the LLM should build on.
   `clarify_iteration` exists to probe that new state — and the
   `iteration_quality` rubric grades whether it actually does.

### What was the result

First two runs on `sre-mid-level` only (`python evals/runner.py --fixture sre-mid-level`):

| Run | Timestamp (UTC)         | iteration_quality | Other rubrics                                                       |
|-----|-------------------------|-------------------|---------------------------------------------------------------------|
| 1   | 2026-05-11T22:56:08Z    | 2.1               | (not tracked in this entry)                                         |
| 2   | 2026-05-11T23:53:39Z    | 3.2               | ats=4.8 grounding=4.8 keyword=4.2 tone=4.2 clarification=4.2 (all pass) |

**Both runs FAIL `iteration_quality` against the 4.0 threshold.** The 1.1
swing on identical inputs (same PROMPT_VERSION, same fixture, same prompts)
is at the upper edge of expected Haiku-judge variance — the underlying
Sonnet generation also varies per call, so the question set isn't bit-identical
across runs either.

Failure mode (from run 2's grader reasoning, the more useful signal):

- The scripted edit (`error budget burn` → `Defined and owned SLOs and the
  error-budget framework on the API edge layer`) produced a malformed bullet
  in the iter-0 generated resume (the original phrase appeared in a
  context that, after substitution, broke the bullet's grammar).
- The iteration_probe correctly detected an issue and asked about it — but
  framed the question as a copy-editing fix ("what is the single clean
  outcome?") rather than as a substantive scope/experience clarification.
- The fixture's `expected_iteration_themes.iteration_probes` specifically
  asks for follow-ups on numeric SLO targets, review cadence, and ownership
  collaboration. The interview missed that opportunity entirely on q1.
- The other 4 questions (q2 multi-region, q3 service mesh, q4 specificity
  signal, q5 Go) are well-targeted with concrete cites, no fabricated gaps,
  no redundancy with priors.
- `failed_rules: ["missing_expected_theme"]` — the iteration_probe slot was
  filled but its content didn't hit any expected theme.

**Diagnosis:** the failure is real but not a fundamental prompt flaw. Two
fixes are plausible:

1. **Tighten the fixture scenario.** The `edit_replacement` produces a
   malformed bullet because the substitution doesn't account for the
   surrounding bullet structure (the Sonnet output wrapped the original
   phrase in a sentence that breaks when substituted). A cleaner
   `edit_target_substring` / `edit_replacement` pair, or a scenario that
   substitutes a whole bullet rather than mid-sentence text, would let the
   iteration_probe focus on substance instead of form.
2. **Add an iteration-probe worked example to CLARIFY_ITERATION_SYSTEM_PROMPT.**
   Mirror the grounding block's OK/NOT-OK pattern: "User typed 'shipped V2
   to enterprise' — OK iteration question: 'Which enterprise customer
   segment? How many?'. NOT OK: 'The bullet has a typo, please clarify.'"
   Pure copy-editing follow-ups should not count as clarifying questions
   because they don't source new ground truth.

Recommended order: (1) first, since the fixture is the proximate cause and
fixing it both restores the eval signal AND tells us whether the prompt has
a deeper issue. If a clean fixture still produces copy-editing-style
questions, then (2) becomes load-bearing.

The "build on, don't re-ask" hypothesis was NOT validated either way in
this run because `prior_clarifications` was empty (the runner's iteration
phase doesn't carry forward analyze-time clarify answers — it could, if we
populate `clarify_answers` from a fixture-supplied dict). That probe gets
exercised once the fixture or runner adds the prior-answers carry-over.

### Cost / scope notes

- `clarify_iteration` adds one Sonnet call per iteration interview clicked.
  Same cost shape as analyze-time `clarify` (~$0.03 per call, mostly cached
  user prefix doesn't apply here — the call uses no cached prefix because
  the current draft varies per iteration).
- The eval iteration phase adds one Sonnet call (clarify_iteration) plus one
  Haiku call (iteration_quality grading) per fixture with scenarios. With
  one fixture (sre-mid-level) currently scoped, total eval cost increment
  is ~$0.05 per `--suite synthetic` run.
- **Deferred to a follow-up entry**: re-generating from the iteration
  context and re-grading against grounding/keyword_coverage. The plan
  documents this as the full Phase 5 eval surface; shipping the
  question-grading half first lets us validate `clarify_iteration` quality
  before paying for the second generate call per fixture per run. If
  iteration_quality scores look good across the next 2-3 runs, add the
  re-generate step and grade the iterated output against grounding +
  keyword_coverage. Expected additional cost: ~$0.50 per scenario per run.

### What we learned

1. **Eval scenarios need to produce a clean iter-0 baseline.** Substituting a
   substring mid-sentence is fragile when the surrounding generated text
   varies. Future fixtures should target whole bullets via the
   edit_target_substring mechanic, OR the runner should grow a smarter edit
   helper that detects bullet boundaries.
2. **A copy-editing question is NOT a clarifying question.** The iteration
   clarifier correctly noticed the malformed bullet but answered the wrong
   question — "is this grammatical?" instead of "what is the underlying
   substantive claim?". The CLARIFY_ITERATION_SYSTEM_PROMPT doesn't currently
   forbid syntax-fix probes; the rubric implicitly does, but the LLM needs
   the explicit guard. Worth a worked-example pair in a future revision.
3. **Single-fixture iteration eval is high-variance.** With one fixture and
   non-deterministic Sonnet generation, score swings of 1.0+ are
   plausible-but-not-attributable. Adding scenarios to pm-senior and
   data-scientist-junior would let us reason about iteration_quality with a
   3-sample mean rather than treating each run as a singular signal.
4. The original "build on, don't re-ask" hypothesis remains untested — see
   "Result" section above for why and how to exercise it next.

---

## 2026-05-09 — `2026-05-06.5` → `2026-05-09.1`: anti-invention worked-examples

### What changed

- `analyzer.py:SYSTEM_PROMPT` — added three ALWAYS/NEVER rules targeting the
  three observed failure-class patterns:
  - "Never restate a candidate's responsibility using a more advanced
    technique than the source describes…"
  - "Never upgrade a tool category into a specific vendor or framework…"
  - "Never escalate scope adjectives (team → organization-wide …)…"
- `analyzer.py:generate()` GROUNDING CHECK — appended a worked-examples
  block with three OK/NOT-OK pairs drawn from the failure data:
  - "Built customer-facing dashboards" → must NOT become "Built time-series
    forecasting dashboards for executive stakeholders"
  - "Used a CI tool" → must NOT become "Authored Jenkins pipelines"
  - "Improved the team's reporting workflow" → must NOT become "Led an
    organization-wide reporting transformation"
- `evals/rubrics/grounding.md` — added the deterministic-backstop input note
  (`deterministic_metrics.grounding_overlap.missing_samples`).
- `PROMPT_VERSION` bump in the same commit per CLAUDE.md.

### Why

Three historical grounding evals on `data-scientist-junior` scored 2-3 with
failure modes clustered as `scope_inflation`, `invented_metric`, `verb_overreach`.
Specific phrases the model had invented:

- "time-series forecasting" (source: "built dashboards")
- "climate-aware transportation forecasting" (source: "Toronto bike-flows")
- "regression analysis" as core expertise (source: one capstone project)

Pattern: the LLM substitutes more specialized vocabulary than the source
warrants — the worked examples teach it where the line is.

### Result

| Fixture | Rubric | Pre-edit (best of 3 historical runs) | Post-edit |
|---|---|---|---|
| data-scientist-junior | grounding | 2 / 5 / 5 (one regression) | 4.8 |
| data-scientist-junior | ats_format | n/a (smoke only) | 4.2 |
| data-scientist-junior | keyword_coverage | n/a | 4.6 |
| data-scientist-junior | tone | n/a | 4.8 |
| pm-senior | grounding | n/a | 4.8 |
| pm-senior | ats_format | n/a | 4.2 |
| pm-senior | keyword_coverage | n/a | 4.2 |
| pm-senior | tone | n/a | 4.2 |
| sre-mid-level | grounding | n/a | 4.8 |
| sre-mid-level | ats_format | n/a | 4.8 |
| sre-mid-level | keyword_coverage | n/a | 4.6 |
| sre-mid-level | tone | n/a | 4.8 |

**12/12 pass** on full synthetic suite. Total cost: $1.46.

Deterministic post-generation metrics (passing scores):

| Fixture | verb_diversity | specificity_density | grounding_overlap |
|---|---|---|---|
| data-scientist-junior | 1.00 | 0.083 | 0.21 |
| pm-senior | 0.90 | 0.10 | 0.31 |
| sre-mid-level | 0.92 | 0.33 | 0.23 |

### What we learned

1. **Worked examples beat abstract rules**. The original SYSTEM_PROMPT had
   "Never invent experience BECAUSE truthfulness is the north star" — a
   correct rule that didn't survive contact with reality. The new "Built
   dashboards" → "NOT OK: time-series forecasting dashboards" pair is
   concrete enough that the LLM patterns from it.

2. **Three failure types cover most invention**. (a) advanced technique
   substitution, (b) tool-vendor specificity, (c) scope adjective escalation.
   Future failures may need a fourth category, but most fabrications fit.

3. **`grounding_overlap.overlap_ratio` is informative but not load-bearing**.
   Empirical data shows passing scores correlate with **0.20-0.31 ratio** —
   the LLM legitimately paraphrases. The actionable signal is `missing_samples`,
   not the ratio. Documented this in the function's docstring.

4. **`specificity_density` is uniformly low (0.08-0.33)**. The LLM is
   under-quantifying — it's safer than fabricating, but it suggests the
   GROUNDING CHECK has overcorrected the model into qualitative-only output.
   Future tuning opportunity: a counter-rule encouraging the LLM to surface
   *existing* numbers from source more aggressively.

5. **The Haiku judge is fairly stable but introduces ±0.5-point noise**.
   The pre-migration int 2/5/5 split on identical inputs across runs
   confirms this. The new 0.0-5.0 scale captures a real signal in 4.2 vs 4.6
   vs 4.8 — fine-grained enough to be actionable but not so noisy that the
   judge's variance dominates.

### Open questions / future tuning targets

- **`pm-senior` keyword_coverage 4.2** — lowest non-passing-margin score in
  the run. Worth a follow-up iteration: are healthtech keywords being
  integrated, or is the model over-deferring to "transferable skills" framing?
- **`ats_format` swing 4.2 → 4.8** — the LLM produces slightly different
  markdown structure across runs. Consider whether `output_format` could
  pin the section ordering more strictly without breaking grounding.
- **`specificity_density` ceiling** — should we set a target floor (e.g.,
  "≥30% of bullets have a quantifier from source") and add a counter-prompt
  if the LLM goes lower? Risk: pushing too hard re-opens the invention door.

### How the dashboard helped

Once Phase 4 landed, three views became immediately useful:

- **Heatmap** showed `data-scientist-junior × grounding` was the only red
  cell, immediately scoping the tuning target.
- **Failure-mode table** showed `scope_inflation`, `invented_metric`,
  `verb_overreach` as the top slugs for that fixture — the three rule
  classes the new SYSTEM_PROMPT lines target.
- **Score-over-time** chart will become useful once we have multiple
  `prompt_version` runs in the data; the prompt_version label on every
  point lets us attribute regressions cleanly.

### Identified gaps in observability

These are not blockers but worth tracking:

1. **No correlation between LLM telemetry and eval results yet.** When
   grounding fails on fixture X, we can't click through to the specific
   `analyze()` and `generate()` calls that produced it. A future enhancement:
   add a `run_id` field to both `logs/llm_calls.jsonl` and
   `evals/results/*.jsonl`, then make the dashboard linkable.

2. **No latency/cost percentiles**. Dashboard shows mean latency and total
   cost but not p50/p95. For a tuning workflow this matters less than for
   production, but worth noting.

3. **No automated regression alerting**. If grounding drops from 4.8 to 3.5
   on tomorrow's run, nothing fires. CI catches PR-time regressions via
   exit code 2 but local development has no analog.

4. **Real-fixture coverage is empty**. `evals/fixtures/real/` is gitignored
   for good reason but means the suite only tests three synthetic personas.
   Tuners should rotate their own real fixtures through to catch
   distribution drift.

---

## 2026-05-09 — `2026-05-09.1` → `2026-05-09.2`: gap-closing iteration

### What changed

**Infrastructure (Gaps 1-3):**
- `run_id` (12-hex UUID) threaded through `analyze()`, `generate()`, `_call_llm`, `evals/runner.py`, and live `app.py` routes. Lands in both `logs/llm_calls.jsonl` and `evals/results/*.jsonl` so the dashboard can correlate which LLM calls produced each graded result. New "Run" column in both dashboard tables.
- `_summarize_calls` now returns `p50_latency_ms`, `p95_latency_ms`, `p50_cost_usd`, `p95_cost_usd` via a new `_percentile` helper. Tail behavior is now visible — a 90s outlier no longer hides inside a healthy mean.
- Local regression alerting in `evals/runner.py`: at the start of each run, `_load_baseline_scores` reads all prior result files and builds a `{(fixture, rubric): most_recent_record}` map. After each grading, `_detect_regression` compares against baseline; drops greater than `REGRESSION_DELTA` (default 0.5, env-overridable) log a `WARNING` and accumulate into an end-of-run summary.

**Tuning (Gaps 4-5):**
- `evals/rubrics/keyword_coverage.md` updated: "covered" now means "in resume body OR in cover letter when the keyword matches `expected.forbidden_inventions`". Prevents the no-win situation where a B2B PM applying to healthtech is forced to choose between fabricating clinical experience (loses grounding) or omitting healthcare keywords (loses keyword_coverage).
- `analyzer.py:SYSTEM_PROMPT` "Always surface existing metrics" rule expanded with concrete examples of what counts: counts ("three reports"), durations ("monthly cadence"), team sizes, GitHub stars, frequencies. The previous rule was too narrow — the LLM was interpreting "metrics" as only `%` and `$` and dropping legitimate quantifiers like "one year" and "two merged PRs".
- `PROMPT_VERSION` 2026-05-09.1 → 2026-05-09.2.

### Why

Five gaps were called out at end of the prior iteration:
1. No correlation between LLM telemetry and eval results
2. No latency/cost percentiles
3. No regression alerting
4. `pm-senior` keyword_coverage stuck at 4.2
5. `specificity_density` uniformly low (0.08-0.33) across all fixtures

Gaps 1-3 were observability gaps; the new tools light up the dashboard. Gaps 4-5 surfaced through the new metrics — once we could see the density data, we could trace it back to the prompt's narrow definition of "metrics".

### Result

| Fixture | Rubric | 2026-05-09.1 | 2026-05-09.2 | Δ |
|---|---|---|---|---|
| data-scientist-junior | ats_format | 4.2 | 4.7 | **+0.5** |
| data-scientist-junior | grounding | 4.8 | 4.8 | 0 |
| data-scientist-junior | keyword_coverage | 4.6 | 4.6 | 0 |
| data-scientist-junior | tone | 4.8 | 4.2 | -0.6 ⚠ |
| pm-senior | ats_format | 4.2 | 4.2 | 0 |
| pm-senior | grounding | 4.8 | 4.8 | 0 |
| pm-senior | keyword_coverage | 4.2 | 4.2 | 0 |
| pm-senior | tone | 4.2 | 4.7 | **+0.5** |
| sre-mid-level | ats_format | 4.8 | 4.8 | 0 |
| sre-mid-level | grounding | 4.8 | 4.8 | 0 |
| sre-mid-level | keyword_coverage | 4.6 | 4.7 | +0.1 |
| sre-mid-level | tone | 4.8 | 4.2 | -0.6 ⚠ |

**12/12 still pass**. Two improvements at +0.5; two regressions at -0.6 on tone (both flagged by the new alerter). The tone regressions are within Haiku judge variance band — the SYSTEM_PROMPT change didn't directly touch tone-related rules, but the broadened "metrics" guidance may have nudged cover letter phrasing slightly. Worth watching across the next 2-3 runs.

Density barely moved (0.083 → 0.11 for data-scientist-junior; pm-senior unchanged at 0.10; sre-mid-level unchanged at 0.33). The expanded rule helped but the LLM is still cautious about preserving small numbers. Future iteration could try adding a worked example pair like the GROUNDING CHECK uses.

### What we learned

1. **The new regression alerter immediately paid for itself.** Two genuine 0.6-point drops on tone surfaced before they could compound across more iterations. Even if these turn out to be judge variance, the alert gives us evidence to confirm or deny that hypothesis next run.

2. **Rubric design can create no-win situations.** The pm-senior keyword_coverage 4.2 wasn't a prompt problem — it was a rubric problem. The rubric punished the model for correctly refusing to fabricate. The fixture's `notes` already acknowledged this; the rubric just hadn't caught up. Lesson: when a fixture's notes describe a deliberate trade-off, the rubric must encode it explicitly.

3. **"Metrics" needs concrete examples in the SYSTEM_PROMPT.** The rule "surface existing metrics" was correct but the LLM was reading "metrics" too narrowly. Adding "counts, durations, team sizes, GitHub stars, frequencies" is the kind of disambiguation that beats abstract instruction every time — same lesson as the GROUNDING CHECK worked examples.

4. **`run_id` is a foundational primitive we should have had from day one.** It's a 12-character string but unlocks correlation, regression analysis, and per-pipeline cost. Future tooling (e.g., a "click run_id to see all telemetry" feature) becomes trivial.

5. **Percentiles tell a different story than means.** This run's mean latency was around 88s but p95 was 142s — the user-visible "feel" of the system depends on tail behavior, not the average.

### Open questions / future tuning targets

- **Tone regressions**: re-run in 2-3 iterations to see if the 4.8→4.2 drop persists or settles back. If it persists, inspect `cover_letter_content` vs the prior version to find the actual source of the tone shift.
- **`pm-senior` keyword_coverage stuck at 4.2 even with the rubric fix**: the judge may not be applying the new "covered in cover letter" rule. Worth checking the next run's `reasons` to confirm. If still stuck, the rubric prose may need to be even more explicit ("score 4.5+ if every must_keyword is in resume AND every forbidden-domain keyword is acknowledged in cover letter").
- **Density still low**: the broadened SYSTEM_PROMPT rule helped one fixture by 0.03 ratio. For a stronger move, consider a worked-example pair in the GROUNDING CHECK ("Source: 'three reports'. OK to write: 'three legacy reports'. NOT OK to drop: 'multiple legacy reports'.").

---

## 2026-05-11 — `2026-05-09.3` → `2026-05-11.1`: optional Q&A interview step

### What changed

- `analyzer.py` — added `CLARIFY_SYSTEM_PROMPT` (a short dedicated persona, ~22 lines) plus `clarify()` between `analyze()` and `generate()`. Reuses `_parse_or_retry` for telemetry parity; emits `call: "clarify"` in `logs/llm_calls.jsonl`. `_call_llm` and `_parse_or_retry` gained an optional `system_prompt` arg so clarify can override the main hiring-manager persona without code duplication.
- `analyzer.py:generate()` — when `context_set["clarifications"]` is non-empty, a `<candidate_clarifications>` block is injected between `<analysis>` and `<resume_rules>` with paired question/answer entries. The GROUNDING CHECK was widened to accept clarification answers as legitimate source material ("first-person ground truth") so the model may surface tech or experience the candidate confirmed even when it doesn't appear in the resume — while the no-invention rule still forbids anything beyond the union of (resume + clarifications).
- `hardening.py` — `ContextSet` TypedDict gained two optional fields: `clarification_questions: list[ClarificationQuestion]` and `clarifications: dict[str, str]`. Both are `total=False` so pre-clarify saved contexts continue to round-trip.
- `app.py` — new routes `POST /api/clarify` (generates questions, persists to the same context file) and `POST /api/answer-clarifications` (stores per-question answers, filters unknown ids and empty text). Both use the standard `_safe_username` + `_within(OUTPUT_DIR)` guards. `run_id` propagates analyze → clarify → generate.
- `templates/index.html` + `static/app.js` + `static/style.css` — collapsible "Clarifying Interview" section inside the Analysis panel with `GET CLARIFYING QUESTIONS` / `SUBMIT ANSWERS & GENERATE` / `SKIP` controls. UI rendering uses safe DOM construction (textContent, appendChild) instead of innerHTML for LLM-supplied strings.
- `evals/rubrics/clarification_quality.md` — new rubric. Grades on: question count (3–5), composition (≥50% experience probes), gap citation specificity (must trace to analyzer output), word limit (≤25 each), no compound or leading questions, theme coverage against `expected_clarification_themes`.
- `evals/runner.py` — runs `clarify()` between analyze and generate; injects the resulting `clarification_questions` into every per-rubric payload (the new rubric uses them, others ignore them). Failures in clarify degrade gracefully — the existing four rubrics still grade.
- `evals/fixtures/synthetic/*/expected.json` — each of the three synthetic fixtures gained `expected_clarification_themes` with `experience_probes` and `scope_probes` lists tailored to that fixture's real gaps, plus `min_clarification_quality_score: 4`.
- `tests/` — new `test_app_clarify.py`; expanded `test_analyzer.py` (clarify() happy-path, retry, system_prompt threading, generate-injection-on/off paths); `test_hardening.py` round-trip for ContextSet with and without the new fields.
- `PROMPT_VERSION` bumped to `2026-05-11.1` in the same commit per CLAUDE.md.

### Why

Two coupled failure modes that show up in the existing eval results:

1. **Fabrication on JD-required skills missing from the resume.** When a JD asks for a technology the candidate's resume doesn't mention but they actually do have experience with, the generator either invents detail (grounding penalty) or stays silent (keyword-coverage penalty). There was no channel to surface the real experience.
2. **Scope ambiguity at the role boundary.** The analyzer's `comparison_analysis` flagged ambiguities ("setting direction vs. executing", "shipped vs. prototype", "sole owner vs. team member") but the generator had to guess. Resume bullets came out vague or, occasionally, over-confident.

The clarify step opens both channels: experience probes surface real-but-undocumented experience (with the candidate's own words as ground truth — citable in the resume); scope probes disambiguate so the generated wording is precise.

### Result

First-run scores will be captured here after the next full `python evals/runner.py --suite synthetic` run. The eval includes the new `clarification_quality` rubric for the first time; the baseline-comparison machinery in `_load_baseline_scores` will pick up subsequent runs automatically. Pre-edit baselines for the four existing rubrics are unchanged (the clarify step is opt-in and was not exercised during prior runs).

Expected impact qualitatively:
- `clarification_quality`: target ≥4.0 on all three fixtures; the per-fixture `expected_clarification_themes` give the judge concrete hit-targets.
- `grounding`: should be unchanged on synthetic fixtures (no answers are injected during the eval run). The real test of grounding under clarifications is a future fixture variant — see "Open questions" below.
- `keyword_coverage`: unchanged on synthetic. In production, when a candidate clarifies "yes, I've used Terraform briefly", keyword coverage should improve because the generator can now surface Terraform.

### What we learned

1. **A dedicated short system prompt beats overloading the main one** when the task is narrow. CLARIFY_SYSTEM_PROMPT is ~22 lines; SYSTEM_PROMPT is ~30 ALWAYS/NEVER rules. Mixing them dilutes both. The cost is a cache miss on the system block, but the user-prefix cache (which carries the heavy content) is unaffected since clarify uses no cached prefix.
2. **Persisting questions to the same context file makes the UI resumable**. The user can refresh the page mid-interview and the questions reload from disk. The alternative — keeping questions only in browser state — would have lost answers on any reload.
3. **The grounding rule needs a precise carve-out, not a blanket exception.** "Clarification answers are first-person ground truth and may be cited even when the resume does not mention them" is the surgical phrasing; the model still must not invent anything beyond the union of (resume + clarifications). Vaguer language ("clarifications override the resume") risks unbounded invention.

### Open questions / future tuning targets

- **First eval results pending**: run `python evals/runner.py --suite synthetic` and append the score table here. If `clarification_quality` is <4.0 on any fixture, inspect `failed_rules` and tighten CLARIFY_SYSTEM_PROMPT — most likely failure mode is questions that don't cite a specific gap source.
- **Contradiction fixture variant**: per the plan, the strongest grounding test is a fixture variant whose injected clarification *contradicts* an inferred resume fact (e.g. resume implies "shipped to production"; clarification says "remained a prototype"). The grounding rubric must fail if the generated resume still claims production. Not yet implemented — needs a `clarifications` field in the fixture itself plus a runner mode that injects them into generate.
- **Addition fixture variant**: similarly, a fixture with an injected positive clarification (e.g. "Yes, I used Terraform on SRE rotation") to verify the generator surfaces it AND the grounding rubric catches any *further* invention beyond the clarified fact.
- **Cost gating**: clarify adds one Sonnet call per fixture per eval run (~$0.01–0.02). For very large eval suites consider a `--no-clarify` flag; not needed today with 3 synthetic fixtures.

---

## Template for future entries

```markdown
## YYYY-MM-DD — `<old_version>` → `<new_version>`: <one-line summary>

### What changed
<concrete file/line edits with paths>

### Why
<failure mode observed; cite the dashboard view or eval result file>

### Result
<table: fixture × rubric, pre vs post>

### What we learned
<1-3 bullets, each a rule-of-thumb for future tuning>

### Open questions / future tuning targets
<things this iteration noticed but didn't fix>
```

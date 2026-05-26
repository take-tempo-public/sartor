# R1 (analyze split) — benchmark + post-mortem, 2026-05-26

> **Purpose:** capture what R1 attempted, what it measured, why it
> regressed, and exactly where v1.0.2 should pick up. Companion to
> [`PERF_ANALYZE.md`](PERF_ANALYZE.md) (which named R1 as a candidate
> optimization) and to [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md)
> entries `2026-05-24.4 → 2026-05-26.1` and `2026-05-26.1 → 2026-05-26.2`
> (which document the prompt-design rationale per iteration).
> **Audience:** the future engineer (or agent) picking R1 back up in
> v1.0.2. Read this before reading the side branch
> `r1-attempted-2026-05-26`; that branch holds the code, this doc
> holds the *why* and the *next moves*.
> **Authoritative for:** the empirical numbers below and the
> diagnosis. Implementation recommendations are *proposals* informed
> by the recruiting-specialist consultation; weight them against
> fresh data when v1.0.2 starts.

## TL;DR

R1 ("split the unified Sonnet `analyze()` call into a Haiku extraction
pass + a Sonnet synthesis pass") was attempted in v1.0.1 with two
iterations. Both regressed `clarification_quality` against the clean
pre-R1 baseline. The performance win was real (analyze p50 103s → ~72s,
≈30% reduction) but the "no quality loss" floor was hard-binding.
Reverted from v1.0.1; preserved on side branch
`r1-attempted-2026-05-26`. **R1 is not dead — three iterations were a
narrow sample, and the diagnosis below points to specific fixable
hypotheses for v1.0.2.**

| Metric                              | Pre-R1 (`2026-05-24.4`) | R1.1 (`2026-05-26.1`) | R1.2 (`2026-05-26.2`) | Decision     |
|-------------------------------------|-------------------------|-----------------------|-----------------------|--------------|
| analyze p50 latency                 | **103.2 s**             | 71.6 s                | ~70 s                 | win          |
| pm-senior / clarification_quality   | **4.2**                 | 3.2                   | **2.1**               | regression   |
| ds-junior / clarification_quality   | 4.2                     | 4.2                   | **3.2**               | regression   |
| sre-mid-level / clarification_quality | 4.2                   | 3.8                   | (run failure)         | partial      |
| All other rubrics                   | flat (±0.3)             | flat (±0.3)           | flat (±0.3)           | held         |

## What R1 attempted

The unified pre-R1 `analyze()` call asked one Sonnet 4.6 persona to do
two cognitively distinct jobs in one pass: (1) extract keyword and
vocabulary signals from the JD, (2) synthesize comparison + suggestions
+ overall strategy against the candidate. The hypothesis — anchored on
the 10 Principles framework's **P6 Specialized Review** (*"A generalist
reviewer trends toward the median. Specialists find what generalists
can't"*) — was that two narrower personas with task-specific
vocabularies would outperform one broad persona.

Two iterations were shipped to the working tree and run through the
synthetic eval suite (~$1.50 per full run, ~30 min wall clock).

### R1.1 (`2026-05-26.1`) — naive split

- **Pass 1 — `analyze_extraction`** (Haiku 4.5, new `EXTRACTION_SYSTEM_PROMPT`):
  produced `essential_skills`, `preferred_skills`, `industry_keywords`,
  `hidden_qualities`, `professional_vocabulary`, `keyword_placement`.
  Persona: "ATS scanner trained on tens of thousands of job descriptions."
- **Pass 2 — `analyze_synthesis`** (Sonnet 4.6, new `SYNTHESIS_SYSTEM_PROMPT`):
  produced `comparison`, `suggestions`, `overall_strategy`. Received
  Pass 1 output as `<extracted_signal>` in its user prompt.
- **`analyze()` becomes a thin orchestrator** sequential Pass 1 → Pass 2;
  merges into legacy `ANALYZE_REQUIRED_KEYS` shape for downstream
  consumer compatibility.
- **Streaming variant** (`analyze_streaming`) emits a new
  `("phase", {"phase": "extraction"|"synthesis"})` sentinel before
  each pass so the frontend can swap status labels.
- **Two phantom keys dropped** from analyze output: `ats_improvements`
  and `ideal_resume_profile` (no downstream consumers in
  `static/app.js`, `analyzer.py`, `app.py`, or any eval rubric).

### R1.2 (`2026-05-26.2`) — recruiter-informed quality fix

After R1.1's regression measurement, a recruiting-specialist subagent
(`general-purpose` with a domain-expert framing prompt; later codified
as [`headhunter.md`](../.claude-plugin/agents/headhunter.md)) diagnosed
the failure: the system was emitting tool-name probes (`"Have you used
Epic?"`) when the JD's underlying signal was portable operating-context
that adjacent-background candidates could map onto.

Three surgical changes landed on top of R1.1:

- **A — Atomic extraction rule.** Added ALWAYS rule requiring ONE
  concept per item in `essential_skills` / `preferred_skills` /
  `industry_keywords`, with worked OK/NOT-OK examples
  (`["EHR", "Epic", "Cerner"]` vs.
  `["EHR systems including Epic and Cerner"]`).
- **B — `hidden_qualities` redefined.** From trait-words ("autonomous",
  "collaborative") to context signals in four categories: operating-
  context fit / scope of ownership / stakeholder gravity / resilience.
  Schema shape unchanged (`list[str]`), only the semantic guidance.
- **C — New `context_probe` question kind in clarify.** Third kind
  alongside `experience_probe` and `scope_probe`. Each context_probe
  translates a `hidden_qualities` context signal into a PORTABLE
  experience question. Composition rule shifted from "≥50% experience
  probes" to "≥60% experience + context probes combined." Clarify
  prompt template gained a new `<context_signals>` block carrying
  `hidden_qualities`.

## Empirical results

Full eval data captured in the result files below; quoted in the table
at the top of this doc. All four runs are in `evals/results/` and
attribute to their `prompt_version` for clean attribution.

| Run                                  | Result file                                      | `prompt_version` | Avg score (15 fixture×rubric pairs) |
|--------------------------------------|--------------------------------------------------|------------------|-------------------------------------|
| Clean pre-R1 baseline                | `evals/results/20260526_202004Z.jsonl`            | `2026-05-24.4`   | 4.43                                |
| R1.1                                 | `evals/results/20260526_200149Z.jsonl`            | `2026-05-26.1`   | 4.36                                |
| R1.2                                 | `evals/results/20260526_205347Z.jsonl`            | `2026-05-26.2`   | 4.05 (1 fixture lost to net failure)|
| (Original muddled "pre" — 2 wks old) | `evals/results/20260513_221926Z.jsonl`            | `2026-05-12.1`   | 4.31                                |

### Latency observations (per-call from `logs/llm_calls.jsonl`)

| Call kind             | PROMPT_VERSION    | N  | p50    | p90    | max    | Notes |
|-----------------------|-------------------|----|--------|--------|--------|-------|
| `analyze`             | `2026-05-24.4`    | 23 | 103.2s | 121.4s | 122.5s | unified pre-R1 |
| `analyze_extraction`  | `2026-05-26.1`    | 4  | 10.6s  | 16.6s  | 16.6s  | Haiku pass 1 |
| `analyze_synthesis`   | `2026-05-26.1`    | 4  | 61.0s  | 69.0s  | 69.0s  | Sonnet pass 2 |
| `generate`            | `2026-05-24.4`    | 13 | 49.6s  | 80.7s  | 81.8s  | unchanged by R1 |
| `generate`            | `2026-05-26.1/.2` | 4  | 58.1s  | 70.4s  | 70.4s  | within noise vs pre |

R1 split = ~30% reduction on analyze p50 (103.2s → 71.6s combined).
The Haiku pass is so much cheaper per-token that even though we're now
making *two* sequential calls, the total wall clock drops. Sample size
is small (n=4 per R1 run); revisit when v1.0.2 lands a stable
implementation.

## Diagnosis — why quality regressed

The eval runner's `_detect_regression` correctly flagged both
iterations. The judge's reasoning made the failure mode explicit on
the worst regression (`pm-senior/clarification_quality` 4.2 → 2.1 on
R1.2):

> *"Q1–Q4 are all experience probes (4/5 = 80%) … No experience probe
> hits any expected_clarification_themes.experience_probes theme.
> Expected themes are: healthcare/healthtech exposure, EHR/Epic/Cerner/
> HL7/FHIR familiarity, revenue-cycle/claims processing, and workflow
> products for clinicians/auditors/lawyers."*

And from the eval log line that diagnoses why R1.2 didn't recover:

> *"clarify produced 5 questions (1 experience probes, 4 scope probes)"*

R1.2's clarify pass emitted **zero `context_probe` questions** despite
the prompt asking for ≥60% experience+context combined. The model
defaulted to `scope_probe` (a kind it knew from R1.1 and earlier
versions) instead of using the new kind. Hypotheses:

1. **Prompt complexity ceiling.** R1.2's `CLARIFY_SYSTEM_PROMPT`
   roughly doubled in length to introduce the new kind + composition
   rule + adjacent-experience requirement. The model may have lost
   structured grounding under the added load. This is a known
   failure mode of long instructional prompts — past a certain length,
   instructions compete for adherence.
2. **Kind-name affordance.** `context_probe` is novel; the model's
   prior exposure to `experience_probe` and `scope_probe` (which have
   shipped for weeks) likely biased its mode-selection toward the
   familiar two. Possibly fixable by *renaming* the existing kinds
   simultaneously to force a clean kind-vocabulary, but that's
   invasive.
3. **Extraction shape mismatch.** R1.2's `hidden_qualities` redefinition
   produced wordier items ("regulated-industry workflows (healthcare/
   clinical-facing context implied by 'patient', 'clinician', 'HIPAA')")
   instead of the trait-words the system was tuned around. The clarify
   pass may have struggled to treat those as actionable input. The
   `<context_signals>` block in the user prompt fed them in directly,
   but the model still wasn't generating probes that mapped them to
   portable experience asks.
4. **Eval judge sensitivity.** The judge is also an LLM; the same
   prompt-complexity ceiling may apply to its grading. The judge is
   strict about *exact theme match* — the expected themes are
   `"healthcare/healthtech exposure"`, `"workflow products for
   clinicians"`, etc. R1.2's questions cited "regulated-industry
   workflows" which is semantically aligned but lexically different.
   Worth checking whether tightening either side improves the score
   without changing system behavior.

The judge's `failed_rules: ["missing_expected_theme"]` is the same on
both regressed fixtures across both iterations, so the failure shape
is consistent — this isn't noise.

## What worked

- **Two-pass structural orchestration** ran cleanly. The streaming
  variant correctly emitted `phase` events; the SSE route forwarded
  them; the frontend rendered phase-specific status labels. 640/640
  tests passed against the split.
- **Haiku routing for extraction** worked mechanically — Haiku
  produced parseable JSON conforming to `ANALYZE_EXTRACTION_REQUIRED_KEYS`
  on the first attempt across all eval fixtures. No retry attempts
  fired during the R1 evals.
- **Cache hit on shared prefix** worked — both passes used identical
  `_stable_user_prefix`; telemetry showed `cache_read_input_tokens`
  on Pass 2 ≈ Pass 1's `cache_create_input_tokens`. Cost amortizes
  the way the design predicted.
- **Two phantom keys dropped** (`ats_improvements`, `ideal_resume_profile`)
  — confirmed no downstream consumer broke. These deletions are worth
  keeping when R1 returns; they're independent of the split.

## What didn't work (and how to think about each)

- **`hidden_qualities` semantic redefinition didn't survive the round
  trip.** Even with the explicit ALWAYS rules and worked examples, the
  Haiku extraction produced inconsistent shapes across fixtures — some
  trait-words, some context-signals, some hybrids. v1.0.2 should treat
  this as a separate schema migration (possibly with an explicit
  `category` sub-field on each item) rather than relying on prose
  guidance.
- **`context_probe` kind didn't get invoked.** Either the model
  doesn't yet have strong enough prior signal for "this is a third
  shape" or the prompt structure didn't make the bias obvious. v1.0.2
  candidates: (a) front-load `context_probe` in the kind enumeration
  and the worked-examples; (b) include a forcing constraint ("emit at
  least one `context_probe` if any `hidden_qualities` items are
  present"); (c) switch clarify from Sonnet to a fresh Haiku call with
  a tighter prompt — the call is short, structured, and Haiku-friendly.
- **Prompt-tune iteration cycles were too expensive.** Each R1
  iteration cost ~$1.50 + ~30 min for a full eval. Three iterations
  before reverting is a lot of budget for not much insight. v1.0.2
  should use the `/prompt-tune` skill (single-fixture cycles, ~$0.05
  per cycle) for the early iterations and reserve the full suite for
  the candidate-shippable version.

## Proposals for v1.0.2

These are *informed guesses*, not commitments. Validate each against
fresh data before building on it.

1. **Start from the `r1-attempted-2026-05-26` branch HEAD.** That's
   the R1.2 state — atomic extraction, redefined `hidden_qualities`,
   `context_probe` kind. The structural plumbing works; what doesn't
   work is the prompt-engineering on the clarify side.
2. **Force `context_probe` emission via a structural constraint, not
   prose.** Today the prompt *asks* for context_probes. Try requiring
   at least one when `hidden_qualities` is non-empty, and surface that
   constraint via the `<instructions>` block, not via the system
   prompt. The schema enforces it at parse time (missing
   `context_probe` → required-keys violation → retry).
3. **Try a fresh Haiku call for clarify alongside the Sonnet path.**
   Clarify is structurally Haiku-friendly (short structured output,
   pattern of three question kinds). Run both side-by-side on the
   eval suite; if Haiku closes the gap, the savings compound on top
   of R1's analyze perf win.
4. **Rebuild the `hidden_qualities` schema with explicit
   `category` field.** Trying to control the shape via prose
   alone didn't land. An object-per-item schema (`{"category":
   "operating_context", "signal": "regulated industry — 'HIPAA',
   'clinician'"}`) gives downstream consumers a stable contract and
   makes the extraction-side validation enforceable.
5. **Sanity-check the eval judge's strict theme-match behavior.**
   Read several `expected_clarification_themes` lists and a sample of
   pre-R1 and R1.2 questions side-by-side. Decide whether judges
   should match on semantic similarity (LLM judge) or exact lexical
   theme presence (deterministic). Today's behavior trends strict;
   that's a *legitimate* signal — strict matches are easier to
   ground — but it punishes wording drift that doesn't actually
   degrade candidate-facing quality.
6. **Use the [`headhunter`](../.claude-plugin/agents/headhunter.md)
   agent between iterations.** The R1.2 fix was informed by a single
   ad-hoc consultation; codifying the agent makes the consultation
   cheap to repeat. Spawn it after each failing eval to diagnose
   which recruiting-domain dimension regressed.

## Where to start (drop-in for v1.0.2)

```bash
# 1. Check out the R1.2 snapshot:
git checkout r1-attempted-2026-05-26
git log -1 --stat    # confirm you're at the wip: R1.2 attempt commit

# 2. Read the diagnosis (this doc + the two TUNING_LOG entries).

# 3. Pick a hypothesis from "Proposals for v1.0.2" above and use the
#    /prompt-tune skill for fast single-fixture iteration:
/prompt-tune pm-senior clarification_quality

# 4. When a candidate change beats the baseline on the smoke subset,
#    run the full synthetic suite for confirmation:
python evals/runner.py --suite synthetic

# 5. Compare three-way against pre-R1 baseline (20260526_202004Z) and
#    R1.2 baseline (20260526_205347Z). Both files are committed.
```

## Adjacent observations worth carrying forward

- **Quality proxies the headhunter named that we haven't operationalized
  yet** (deferred from R1.2 to a follow-up): (1) **top-third density**
  — first 3 bullets of first job contain JD's top 3 essentials, (2)
  **quantification rate** — % of bullets with a number/%/$ /scale
  indicator, (3) **distinctiveness** — "would this bullet look the
  same on 100 other résumés?" All three are deterministic, computable
  from generated output, and addressable without prompt changes. Could
  be added as `deterministic_metrics` on eval records the way
  `verb_diversity` and `specificity_density` are today.
- **Recruiter quote anchoring the design** (from the consultation that
  produced R1.2 and is preserved in
  [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md)): *"Asking 'have you
  used Epic' of someone who hasn't is dead-end. Asking 'have you built
  products for users in regulated, workflow-heavy environments where
  errors have real-world consequences' lets a logistics-PM or a
  fintech-PM map THEIR experience onto a healthtech JD."* The design
  direction stands; the prompt-engineering didn't land it. v1.0.2's
  job is the latter without abandoning the former.
- **Multi-window discipline.** This work surfaced that two Claude
  windows editing the same plan and `RELEASE_CHECKLIST.md` produces
  reconciliation overhead even when both windows are well-behaved.
  See the future entry tracked in [`AGENTS.md`](../AGENTS.md) (TODO
  at time of writing) for the "one-window-owns-the-plan" rule.

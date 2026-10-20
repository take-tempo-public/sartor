```toml
schema = 1
id = 137
kind = "item"
title = "Review current Claude models and call settings for performance and cost"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "docs/model-55-eval-item"]
refs = [
  "analyzer.py:1042-1043",
  "analyzer.py:1573-1595",
  "agents/",
  "docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md",
  "docs/dev/work/items/0174-model-pricing-disagrees-with-pricing-page.md",
]
summary = "Review pinned models and call settings, now including the Claude 5.5 candidate evaluation (absorbs item 173)."
```

**Asked by the owner, 2026-10-01.** A short review task, not a migration.

**What to look at:**
- The LLM routing in `analyzer.py` (`SONNET_MODEL`, `HAIKU_MODEL` at `:850-851`): is each
  call kind on the cheapest model that holds its eval scores?
- Call settings: the thinking-off choice (`:827-831`), prompt caching hit rate
  (`/sartor:bench`), and output-token limits.
- The subagent model pins in `agents/*.md` (the split is explained in `CLAUDE.md`
  §"Model-pin convention").

**Done means** a short written finding with measured before/after numbers where a change is
proposed (eval scores from `evals/runner.py`, cost from `logs/llm_calls.jsonl`). Any prompt
or model change it recommends is its own eval-gated branch, with `PROMPT_VERSION`
discipline.

## Updates

### 2026-10-17 - overlap with item 173 (docs/model-55-eval-item)

The owner asked whether the 5.5 generation of Sonnet, Haiku and Opus has been evaluated; it has not, and
that evaluation is filed as item 173 (`docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md`).
It overlaps this item: 137 is the broad review of routing and call settings, 173 is the specific candidate
list. The session that answered the owner did not find 137 first. Whether 137 absorbs 173 is the owner's call
(recorded as 173's open question). **No review finding for this item was found in the repo by the session
that filed 173** (the item's status is still `open`; its listed branch's git history was not checked). Its `refs` are stale: the model constants are now at `analyzer.py:1042-1043` and the
thinking-off code at `analyzer.py:1573-1595`, not `:850-851` and `:827-831`.

### 2026-10-17 - absorbs item 173 (owner decision); the 5.5 first step is done

**The owner decided "137 absorbs 173" (chat, 2026-10-17).** Item 173 is closed as absorbed. **This item's scope is now
the original review (routing per call kind, thinking-off, cache hit rate, output limits, subagent pins) plus the
Claude 5.5 candidate evaluation.** The detail is not restated here: the observed pins and hazards, the 17 proposals and the
first-step results are in `docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md` (read its `## Updates`
block dated 2026-10-17 first). The `refs` above were corrected to the current line numbers in the same edit.

**Headline results of the first step the owner authorized** (all in 173, with sources and request ids):
- All three 5.5 IDs resolve (`claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-opus-5-5`).
- **`thinking: {"type":"disabled"}` returns `400` on Sonnet 5.5** (use `between_tools`), so `analyzer.py:1594-1595` would break
  every Sonnet call if the constant alone were swapped. Haiku 5.5 accepts `disabled`.
- **`MODEL_PRICING` disagrees with the pricing page for both live pins**: filed as item 174.
- **`claude-haiku-4-5-20251001` is past its earliest retirement date** (Active, "not sooner than October 15, 2026", no
  notice listed) and is also the eval judge, so the Haiku move has a clock this item did not have when filed.
- No Haiku call on this machine's telemetry exceeded 12,506 prompt tokens (Haiku 5.5's higher tier starts at 100,000).

**Suggested order for the work that remains** (a recommendation, not a decision): (1) item 174, the pricing fix, first, because
every cost comparison depends on it; (2) decide the `thinking` policy per model (Sonnet 5.5: `between_tools`; Haiku 5.5:
`disabled` to hold behavior, or adaptive as its own eval-gated change); (3) add telemetry for thinking tokens if the A/B
should see them; (4) the candidate A/B, one swap per branch with the judge held fixed (**needs the owner's spend approval;
none is given**), at an N chosen in advance because the `data-scientist-junior` fixture is bimodal; (5) the subagent pins,
last. `analyzer.py` and `hardening.py` are C-10 gated: a consumer dossier first.

### 2026-10-19 - thinking policy and 5.5 prices built (feat/thinking-policy-55-pricing); the A/B is still unapproved

Built, no pin moved, no paid call made: `analyzer.THINKING_POLICY` + `thinking_setting()` (Sonnet 5.5 `between_tools`, Haiku 5.5
`disabled`, an unlisted model refused with `LLMConfigurationError`), the judge path on the same table, `MODEL_PRICING` keys for
`claude-sonnet-5-5` and `claude-haiku-5-5`, and `MODEL_PRICING_TIERS` for Haiku 5.5's over-100,000-token prices. Consumer dossier:
`docs/dev/blast-radius/thinking-policy-55-pricing.md`. **Sources:** the pricing page re-read 2026-10-19 (all twelve rates match item
173's table; the tier rule is "a request whose prompt is over 100,000 tokens pays higher prices", counting cache reads and writes, per
request); the 400 and 200 behavior is item 173's recorded probe, not re-run. **Correction to item 173:** it called `analyzer.py` and
`hardening.py` "C-10 gated"; `scripts/enforcement/blast_radius.py:198-209` lists both under `ACKNOWLEDGED_NOT_GATED`, so the hook does not
fire on them (the dossier was written anyway).

**Still open under this item:** the candidate A/B (needs the owner's spend approval; none given), a model-override mechanism for
candidate runs (173 proposal 16), the routing review per call kind, cache hit rate and output limits, the subagent pins, Opus 5.5
pricing (no product call), and the stale "no Haiku 5" wording in `CHANGELOG.md`'s 2026-07-05 entry (historical, not edited).

### 2026-10-19 - model override built (feat/model-override-candidate-quarantine); candidate runs now really excluded

**Item 173 proposal 16 answered.** Searched this session (non-test `*.py`): no env var, flag or helper changed the analyzer's model;
`prompt_overrides()` covered system prompts only. Built: `analyzer.model_overrides()` and `evals/runner.py --model-override PIN=ID`
(pins `SONNET_MODEL`, `HAIKU_MODEL`), resolved by value at the one product send site so the judge stays on `JUDGE_MODEL`; a target
without a `THINKING_POLICY` and a `MODEL_PRICING` entry (Opus 5.5 today) is refused before any paid call. Records carry
`model_overrides`; overridden call-log rows carry `pinned_model`. **No pin moved, no spend.** Consumer dossier:
`docs/dev/blast-radius/model-override-candidate-quarantine.md`.

**Finding (read from the code, not reproduced as a user-visible bug):** the documented "candidate runs never pollute score-over-time"
was not true. `_load_baseline_scores` and the dashboard's baseline views excluded nothing, so a prompt-override candidate was the
heatmap cell, flipped the baseline-health badge and seeded the next run's regression comparison. Fixed on the same branch with one
predicate, `hardening.is_candidate_record`, used for both candidate kinds; docs and help text corrected.

**Still open under this item:** the candidate A/B itself (needs the owner's spend approval; none given), the routing review per call
kind, cache hit rate and output limits, the subagent pins, Opus 5.5 price and policy (no product call), the stale "no Haiku 5" wording
in `CHANGELOG.md`'s 2026-07-05 entry. New, not done: the console route `/api/tune/run` takes no model override (CLI only), and
`_load_baseline_scores` still ignores `eval_mode`. Unenforced gap (C-11, owner's call): nothing enumerates the dashboard's baseline
aggregations, so a NEW view that forgets `hardening.is_candidate_record` would pass every test; a test that walks them is possible, not built.

### 2026-10-17 - pricing fixed (item 174); call provenance filed (item 175), a prerequisite for any model swap

- **Item 174 is fixed** on `fix/model-pricing-rates`: `hardening.MODEL_PRICING` now carries the pricing page's rates for Sonnet 5
  (`$2 / $10`) and Haiku 4.5 (`$1 / $5`). Cost comparisons for the 5.5 candidates can start from this table. Keys for the 5.5
  models, and Haiku 5.5's prompt-length tiers (a `compute_call_cost` change), are still this item's.
- **Item 175 is filed** at the owner's instruction (2026-10-17): the call log must record the model version that answered and the
  exact settings sent (thinking, max_tokens, effort, request id, thinking tokens), for product and eval-judge calls, "so we can
  trace every decision to the model that made it and the settings for that model." Today the thinking setting is only
  inferable from `model == SONNET_MODEL`, which breaks the moment this item changes the pin. **Suggested order: 175 before any
  candidate A/B**, so the A/B rows say what ran. No spend is approved by this note.

### 2026-10-19 - free review, part 1: measurements from `logs/llm_calls.jsonl` (docs/item-137-free-review); no code, no spend

**Source and method.** `logs/llm_calls.jsonl` at `26e4f56`: 1,564 rows, 2026-05-06 to 2026-10-18, 0 unparsable; 859 rows are on the
two current pins (`claude-sonnet-5`, `claude-haiku-4-5-20251001`). Product/dev rows = `username` not starting `eval:` (524);
eval rows = `eval:*` (335). Per call kind: n, cache ratio read/(read+write), share of rows with `cache_read > 0`, input and output
percentiles, rows with `stop_reason == "max_tokens"`, cost through `hardening.compute_call_cost`. The script is in the session
scratchpad and is **not committed** (it prints aggregates only); the definitions above re-derive every figure. **Not measured:** the
thinking setting and the answering model, because **no row in the file carries any item-175 field** (`answered_model`,
`request_settings`, `thinking_tokens`, `served_as`, `attempt`, `pinned_model`: 0 of 1,564). Thinking is read from
`THINKING_POLICY` in the code (part 2), not from the log. Eval rows are a smoke/synthetic population (fixed fixtures, run
back to back), so they are reported beside the product rows, never merged into them.

**Finding 1 - `max_tokens` is not binding anywhere.** 0 rows with `stop_reason == "max_tokens"` on the current pins (the 8,192 default;
`check_refinement_scope` has 128 and its one row used 13 output tokens). Largest output seen: `generate` 4,783 and `analyze_synthesis`
4,474 (product), 8,192 is never approached. A lower limit would not change cost (output is billed as produced); it would only bound a
runaway. Not a cost lever.

**Finding 2 - the user-prefix breakpoint on product `analyze_*` costs more than it saves.** Product rows, cache writes vs reads,
priced from `MODEL_PRICING`:

| kind (product, current pin) | n | cache write tokens | cache read tokens | read share | net effect of caching vs no caching |
|---|---|---|---|---|---|
| `analyze_synthesis` (Sonnet 5) | 40 | 305,844 | 34,682 | 10.2% | **-$0.0905** |
| `analyze_extraction` (Haiku 4.5) | 45 | 199,725 | 20,141 | 9.2% | **-$0.0318** |
| eval `analyze_synthesis` (Sonnet 5) | 42 | 50,900 | 74,370 | 59.4% | +$0.1084 |

(net = reads x (input rate - read rate) - writes x (write rate - input rate); Sonnet 5 $2.00 / write $2.50 / read $0.20, Haiku 4.5
$1.00 / $1.25 / $0.10 per million.) The sums are small in dollars: **the size of the effect is cents over five months, not a cost
problem**, and it is worth stating that plainly. What is observed: the product `generate` rows are 5, all dated 2026-07-06, while product
`analyze_synthesis` runs to 2026-10-17 (40 rows). **Inferred, not verified:** the synthesis prefix is written for a `generate` that the
frozen-composition path no longer sends (`architecture.md` says `/api/generate` assembles without an LLM when frozen). Eval shows the
design works when `generate` follows: 22 synthesis-to-generate pairs, gap p10/p50/p90 = 25/29/62 s, **20 of 20 within 300 s read the
cache, 0 of 2 beyond it did** (5-minute ephemeral TTL, as designed).

**Finding 3 - which system blocks cache at all (observed, mechanism pending).** Rows with writes or reads on the system block alone:
Sonnet 5 `generate_cover_letter` (product 83.8% read share, eval 100%), `draft_experience_summary` (write 1,616 / read 1,616),
`draft_gap_fill` (write 32,679, read 0 on 24 calls, so spaced beyond the TTL; the retries read 5,544), `iterate_clarify` and
`draft_surgical_refinement` (writes only). **No cache activity at all** on `draft_summary`, `recommend*`, `clarify`, `avatar_answer`,
`extract_experiences`, `critique_proposal`, `check_refinement_scope` and the eval-side Haiku `analyze_extraction` (0 write, 0 read on
119 rows with the prefix breakpoint set). **Source for the rule that explains it:** the `claude-api` skill's
`shared/prompt-caching.md:131-140` (bundled skill 2.1.304, read 2026-10-19; a prefix shorter than the model's minimum silently
does not cache): **Haiku 4.5 4,096 tokens; Sonnet 5 1,024; Sonnet 5.5 and Haiku 5.5 512** (the skill itself says to check the
prompt-caching docs before relying on the 5.5 values; I did not). Reading the numbers against that: every Haiku 4.5 call
whose whole prefix is under 4,096 tokens (all the kinds above, and eval `analyze_extraction` at a p50 of 2,250 input tokens) cannot
cache, and the breakpoint there is inert, not harmful. Product `analyze_extraction` did write 199,725 tokens because its p95 input is
4,312, so only the long-JD calls cross the line. **Not measured:** the token size of each system prompt (the log records usage, not
prompt size; `count_tokens` would measure it, free but a network call I did not make). Sonnet 5 `draft_summary` (no activity) vs
`draft_gap_fill` (writes about 1,361 tokens a row if every row wrote) is consistent with a system block near the 1,024 line, but that is an
inference from two kinds.

**Consequence for the A/B (a design input, not a prediction):** the minimum drops from 4,096 (Haiku 4.5) to 512 (Haiku 5.5, per the
skill) and from 1,024 (Sonnet 5) to 512 (Sonnet 5.5). A candidate run would therefore start caching blocks that cannot cache today, so
the cache columns of a Haiku 5.5 vs Haiku 4.5 comparison measure a different caching regime as well as a different model. The run
must report cost with the cache effect separated (input, write and read tokens per kind), or the dollar delta cannot be attributed.

**Finding 4 - the retry rows read the first attempt's cache, as designed** (`*_retry` kinds: 100% read share wherever the first
attempt wrote).

**Latency and cost per call, product, current pins (p50 / p95 ms; $ per call):** `analyze_synthesis` 39,917 / 50,716, $0.0605;
`generate` 34,564 / 43,537, $0.0641 (n=5); `analyze_extraction` 14,336 / 20,423, $0.0136; `draft_gap_fill` 10,169 / 15,242, $0.0335;
`clarify` 8,685 / 11,209, $0.0076; `recommend` 4,702 / 9,130, $0.0071; `draft_summary` 3,955 / 6,396, $0.0110. The two longest
user-facing waits are the Sonnet 5 analyze synthesis and generate, with p50 outputs of 3,572 and 3,862 tokens (about 90 to 110 output
tokens a second at the p50: a ratio, not a regression, so "consistent with output-bound" is the most this supports).

**Scale, stated plainly.** The 524 product/dev rows on the current pins cost **$6.71 in total over five months** (Sonnet 5 kinds
$4.50, Haiku 4.5 kinds $2.21, by `compute_call_cost`). This is one user's volume. A 10x price cut on the Haiku share would save
about $2 over that window. The review's case for a swap rests on quality and latency at least as much as on dollars.

### 2026-10-19 - free review, part 2: settings at HEAD and the proposed A/B (docs/item-137-free-review); no code, no spend

**Settings, read from `analyzer.py` at `26e4f56` (each line re-read this session, not taken from a report).** Every call goes through
`_call_llm_streaming`; `MAX_TOKENS = 8192` (:1289) unless stated; no `temperature`, `top_p`, `top_k` or `stop_sequences` anywhere
in `analyzer.py`, `evals/runner.py`, `onboarding/` or `blueprints/` (grep: 0 matches), so API defaults apply. `THINKING_POLICY`
(:1252-1262) is applied at send and no call site overrides it: Sonnet 5 sends `{"type": "disabled"}`, Haiku 4.5 sends no `thinking` field.

| Pin and thinking | call kinds (line of the `model=` / call site) | user-prefix breakpoint |
|---|---|---|
| Sonnet 5, `disabled` | `analyze_synthesis` (:2253), `generate` (:3356, :3407), `generate_cover_letter` (:3563), `iterate_clarify` (:2849), `draft_summary` (:5010), `draft_gap_fill` (:5143), `draft_experience_summary` (:5357), `draft_surgical_refinement` (:5530) | `analyze_synthesis` and `generate` only (same `_stable_user_prefix`); the rest `""` |
| Haiku 4.5, field omitted | `analyze_extraction` (:2239, :2405), `avatar_answer` (:2581), `clarify` (:2714), `critique_proposal` (:3758), `recommend` (:3858), `recommend_summary` (:4022), `recommend_experience_summary` (:4254), `recommend_skill` (:4477), `suggest_skill` (:4703), `suggest_skill_from_corpus` (:4805), `promote_clarification_to_bullet` (:4899), `extract_experiences` (`onboarding/extract_experiences.py:174`) | `analyze_extraction` only; the rest `""` |
| Haiku 4.5, field omitted, `max_tokens=128` | `check_refinement_scope` (:3617-3618) | `""` |
| Judge: Haiku 4.5 (`evals/runner.py:119`) | `judge_grade` (`max_tokens=1024`, :728), `judge_distinctiveness` (`max_tokens=128`, :525) | none |

(`iterate_clarify`, `analyze_synthesis`, `generate` and `generate_cover_letter` name no model at the call site and take the default,
Sonnet: `requested_model = model or SONNET_MODEL`, `analyzer.py:1784`. The streaming path
has no `max_tokens` parameter, so a streamed call is always 8192. `avatar_answer` goes straight to `_call_llm_streaming` with no
parse-and-retry, so it has no `_retry` sibling. Not re-read: the Flask route that fires each kind, which part 3 below cites when
`architecture.md` is corrected.)

**Findings that need a decision or a later branch (not done here):**
1. **Cache economics on product `analyze_*`** (Finding 2): a user-prefix breakpoint that is written on every analyze and read by a
   `generate` that rarely follows. Small in dollars; the proposal is to drop the breakpoint on product synthesis unless the legacy
   `generate` call is about to run, a behaviour change to `analyzer.py` with its own branch and eval. Not proposed for this branch.
2. **`commands/bench.md:20` describes six log fields no row has yet.** The first product call after this branch lands will start writing
   them; until then `/sartor:bench` groups by `(call, model, prompt_version)` only, and its cost is a "rough" figure, so this review
   priced through `compute_call_cost` instead.
3. **Unresolved price discrepancy (not settled by me):** `hardening.py:471-477` has Sonnet 5.5 cache reads at $0.10 per million (citing
   the pricing page footnote, re-read 2026-10-19 by the earlier session); the `claude-api` skill's cached table (2026-10-06) says $0.20.
   The repo's figure is the more recent primary reading. I did not re-fetch the page. It moves a 5.5 cache-read cost by at most 2x on a
   small number, and it matters only if the A/B compares dollars to the cent.

**Proposed candidate A/B (for the owner to approve; nothing run, nothing spent).**
- **Shape:** one swap per branch, judge held on `JUDGE_MODEL` (the override resolves at the product send site only, #191), the baseline arm re-run
  at the same `PROMPT_VERSION` (`2026-10-17.2`; today only 2-row assemble runs exist at that version, so no usable baseline is on disk),
  N chosen in advance because `data-scientist-junior` is bimodal.
- **Order I recommend, and why:** (1) `HAIKU_MODEL=claude-haiku-5-5` first: it is the only dollar lever ($1 / $5 to $0.10 / $0.50 per million,
  repo and skill agree), and Haiku carries 33% of observed product spend ($2.21 of $6.71). (2) `SONNET_MODEL=claude-sonnet-5-5`
  second: same price and tokenizer per the skill, so it is a quality and latency question, not a cost one.
- **Confounds the run must report, not hide:** (a) the **caching regime changes** (minimum 4,096 to 512 tokens for Haiku, 1,024 to 512 for Sonnet),
  so report input, write and read tokens per kind beside the dollar figure; (b) **thinking is not equivalent**: Sonnet 5.5 cannot take
  `disabled` (400), `THINKING_POLICY` sends `between_tools`, and its `high` effort default is "recalibrated" per the skill, so "thinking off, default
  effort" is the same label on a different behaviour; Haiku 5.5 sends `disabled` at its `medium` default; (c) **tokenizer for Haiku 5.5 vs 4.5 is not
  stated in anything I read**; (d) `--suite synthetic` does not exercise most Haiku and four Sonnet kinds (the corpus-mode `draft_*`, `recommend_*`,
  `suggest_*` calls), per the owner's `feedback-corpus-mode-eval-coverage` note, **not re-verified this session**, so a green A/B would say nothing about them;
  (e) `_load_baseline_scores` ignores `eval_mode` (open, above).
- **Cost, as arithmetic on observed runs, not a quote:** the latest paid runs (2026-10-17, current pins) cost $0.40 to $0.52 for a 6-row generate-mode run
  and $0.30 to $0.37 for a 6-row assemble-mode run. A swap at N = 3 per arm is six runs: about **$2.4 to $3.1** (generate) or **$1.8 to $2.2**
  (assemble). The last full 22-row synthetic runs (2026-06-23 to 2026-07-09, $2.1 to $2.4 each) predate both the current pins and the item 174 price
  fix, so they are not a current figure; a full-suite swap is unmeasured. **Not checked:** whether a record's `cost_usd` includes the judge calls.
- **Approval needed from the owner before any of it:** the pin, the suite/subset and mode, N, and the spend ceiling. None is given.

```toml
schema = 1
id = 175
kind = "item"
title = "Record, for every product and eval-judge LLM call, the model version that answered and the exact settings sent, so any decision traces to its model"
status = "open"
decision_owner = "agent"
branches = ["fix/model-pricing-rates", "fix/llm-call-provenance"]
refs = [
  "analyzer.py:741-749",
  "analyzer.py:1496-1655",
  "analyzer.py:1729-1776",
  "analyzer.py:1907-1916",
  "analyzer.py:672",
  "evals/runner.py:112-117",
  "evals/runner.py:440",
  "evals/runner.py:625",
  "db/build_context.py:181",
  "hardening.py:157",
  "docs/dev/work/items/0137-review-models-and-settings-for-performance-and-cost.md",
  "docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md",
  "docs/dev/diagnosis/model-pricing-rates.md",
]
summary = "Built (fix/llm-call-provenance): rows record answering model, request id, settings; judge calls logged. Owner closes."
```

**Filed 2026-10-17 on `fix/model-pricing-rates` from the owner's instruction, given when they chose item 174:** *"be sure that
we are tracking the model, the model version, and the settings such as effort level, thinking etc. so we can trace every
decision to the model that made it and the settings for that model."* **Scope decided by the owner (2026-10-17):** product
calls and eval-judge calls. **Not** dev-agent session stamps (`docs/dev/prov/SPEC.md`), and **no** database column: a stored
draft traces to its model by joining `run_id` against the telemetry log. Built on its own branch (one branch per session).

All findings below were read from the code by an exploration pass this session (`path:line`); **none has been confirmed by
running a call and reading the row**, so the branch's first commit is that observation (C-7).

## What is recorded today

- **One writer for product calls.** Every product call goes through `_call_llm_streaming` (`analyzer.py:1496`), the only SDK
  call being `client.messages.stream(**stream_kwargs)` (`:1600`); `_emit_call_log` (`:741-749`) appends one JSON row per
  attempt to `logs/llm_calls.jsonl`, built at `:1634-1655`.
- **The row has:** `timestamp, username, run_id, call, model, prompt_version, input_tokens, output_tokens,
  cache_creation_input_tokens, cache_read_input_tokens, latency_ms, stop_reason, status`, plus `error_type`, `error_message`
  on errors. `model` is `effective_model`, **the id the code asked for** (`:1639`).
- **Request kwargs actually sent** (`:1582-1595`): `model`, `max_tokens` (default `MAX_TOKENS = 8192`, `:1053`), `system` and
  `messages` with `cache_control: ephemeral`, and `thinking={"type":"disabled"}` **only when `effective_model == SONNET_MODEL`**.
  `effort`/`output_config`, `temperature`, `top_p` and `tools` are never sent, so the API defaults apply.

## What is not recorded (gaps)

1. **The model version that answered.** `final` (the streamed final message) is in scope at `:1604`; `final.model` is never
   read. `claude-sonnet-5` is an alias, so the version behind it is invisible.
2. **The settings sent:** `max_tokens`, `thinking`, and (if ever sent) effort/temperature. "Thinking was off" can only be
   *inferred* from `model == SONNET_MODEL`, and that inference breaks when item 137 changes the Sonnet pin (a `disabled`
   request returns `400` on Sonnet 5.5; item 173's Updates).
3. **The request id**, and **thinking tokens** (the API's `usage` now returns them; item 173's Updates).
4. **Settings that silently differ from what the caller asked for.** `_parse_or_retry`'s retry drops `max_tokens`
   (`analyzer.py:1907-1916`), so `check_refinement_scope`'s retry runs at 8192, not 128 (`:3344`);
   `_parse_or_retry_streaming` has no `max_tokens` parameter (`:1729-1776`) and always uses 8192. Nothing in the log shows it.
5. **Judge calls write no telemetry.** `_grade` (`evals/runner.py:625`, `max_tokens=1024`) and `_score_distinctiveness`
   (`:440`, `max_tokens=128`) call `client.messages.create(model=JUDGE_MODEL, ...)` and discard the response's `model`, `usage`,
   `stop_reason` and request id. A score's only record of its judge is the hardcoded `JUDGE_MODEL` (`:117`). They also
   mean eval `cost_usd` (summed from `llm_calls.jsonl`, `:461-487`) **excludes the judge**.
6. **Eval records name models from a hand-copied dict.** `MODEL_SNAPSHOTS` (`evals/runner.py:112-115`) is a literal, not read
   from `analyzer.SONNET_MODEL`/`HAIKU_MODEL`, so it can drift; it does not say which call kinds ran on Haiku; and it records
   no thinking/max_tokens for either generator or judge. `evals/bootstrap.py:294` and `evals/corpus_drafting_probe.py:221`
   record `prompt_version` and no model.
7. **`prompt_version` is not always the one in effect.** Avatar rows are stamped with the résumé `PROMPT_VERSION`;
   `AVATAR_PROMPT_VERSION` (`analyzer.py:672`) is never logged. The database's `ApplicationRun.prompt_version` is set to the plain
   `PROMPT_VERSION`, not the effective one (`db/build_context.py:181`, so a `candidate:<hash>` override run is stamped as the
   shipped version).
8. **Saved context files and the database carry no model.** `ContextSet` (`hardening.py:157`) has `run_id` and nothing else
   about a model; `evals/schemas/context_set.schema.json` has `"additionalProperties": true`; no table has a model or settings
   column. Out of scope by the owner's decision; the `run_id` join is the trace.

## Constraints found

- **Keep `model` meaning "the id requested".** `compute_call_cost` (`hardening.py:1710`) looks pricing up by `record["model"]`,
  and the dashboard filters on it (`dashboard/routes.py:1063`); a dated version string there prices as `0.0`. The answering
  version needs its **own field**.
- **Adding row fields is safe; changing a field's meaning is not.** No test pins the row's exact key set. Tests that read it:
  `tests/test_call_kind_telemetry.py:234` (`rec["model"] in MODEL_PRICING`), `tests/test_analyzer_model_selection.py:55,66`
  (`rec["model"] == SONNET_MODEL/HAIKU_MODEL`), `tests/test_llm_call_error_capture.py:120-121`. Readers to re-check:
  `dashboard/routes.py` (several), `commands/bench.md:14-19` (groups by `(call, model, prompt_version)`),
  `scripts/perf_baseline.py`, `evals/corpus_drafting_probe.py:110-128`, `evals/runner.py:461-`.
- **Neither `analyzer.py` nor `llm_calls.jsonl` is a C-10 gated surface** (`scripts/enforcement/blast_radius.py:199-203`;
  `evals/runner.py` is not listed). Writing a consumer list is still the right first step. `db/models.py` and
  `evals/schemas/context_set.schema.json` are gated; this item does not touch them.

## Proposed design (for the branch's own plan; not decided)

- Log the request kwargs **derived from the real `stream_kwargs`** (everything except `system`/`messages`, which are large and
  already hashed by `prompt_version`), so a setting added later is recorded without anyone updating a field list.
- Add `response_model` (from `final.model`), `request_id`, `thinking_tokens` (when present in `usage`), and an `attempt`
  number alongside the `_retry` suffix; keep every existing field and its meaning.
- Fix the retry/streaming `max_tokens` drift, or record it: whichever the branch's C-7 instrument says is the real behaviour.
- Judge calls: carry the same provenance in the **eval record** (not `llm_calls.jsonl`), so the eval `cost_usd` and dashboard
  totals do not change meaning silently; or log them with a distinguishing `call` kind and decide how `cost_usd` treats them
  — that choice is the branch's, made in its plan with the owner.
- Derive `MODEL_SNAPSHOTS` from the `analyzer` constants; log the effective avatar and run `prompt_version`.
- A test that fails closed: every kwarg passed to `messages.stream` appears in the row (a stub client that records its kwargs).
  Without a mechanism that fails when a new setting is added unrecorded, this is a prediction (charter C-11).
- Dependencies: item 137's thinking policy is simpler to apply once the row records it; this item can land first and is the
  prerequisite the owner asked for before any model swap.

## Updates

### 2026-10-17 - filed during fix/model-pricing-rates

Filed with the owner's scope decision above. Nothing built; no production code changed for this item.

### 2026-10-19 - built on fix/llm-call-provenance (not closed; the owner closes)

Scope the owner chose: gaps 1-7 (gap 8 stays out). Judge calls: telemetry rows with `judge_*` kinds, excluded from eval `cost_usd`.
Record: `docs/dev/diagnosis/llm-call-provenance.md` (observations 1, 4, 5), `docs/dev/blast-radius/llm-call-provenance.md`.

- **Observed first** (two sub-cent live calls, $0.005324 each run): the row had no settings and no request id, while the SDK had both.
  **Gap 1's mechanism was falsified:** `final.model` echoes the requested alias (`claude-sonnet-5`), so the response never names a dated
  version. `answered_model` is logged anyway (it will show a change if the API ever returns one) but **the API request id is the only
  per-call handle to the answering model.** Whether any response header names a version was not investigated.
- **Built:** `answered_model`, `api_request_id`, `request_settings` (derived from the kwargs sent, minus `system`/`messages`), `served_as`
  (`service_tier`, `speed`, `inference_geo`: not in the original list, added because `speed` and tier change price), `thinking_tokens`,
  `attempt`; judge rows via `analyzer.log_judge_call`; `judge_request_id` on eval records; `MODEL_SNAPSHOTS` derived; avatar rows stamped
  with `AVATAR_PROMPT_VERSION`; `ApplicationRun.prompt_version` is the effective version; the retry keeps `max_tokens` (gap 4).
- **Fail-closed test:** `tests/test_call_provenance.py` (mutation-checked) and its judge twin `tests/test_judge_call_provenance.py`.
- **Not verified live:** a judge row (fakes only); `thinking_tokens` on a call that thinks (null on both probed calls; the streamed `usage`
  carried no `output_tokens_details`). **Not changed:** `_parse_or_retry_streaming` still has no `max_tokens` parameter (three callers, all 8192).
- **Disclosed meaning change:** dashboard spend totals now include judge spend; eval `cost_usd` does not.
- **Left for the owner:** close this item (needs a falsifiable `verified_by`: the probe re-run plus the two new test files, or a
  `closure_exception` for the unobserved parts), and whether to file the unobserved parts as their own watch item.

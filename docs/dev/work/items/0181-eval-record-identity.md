```toml
schema = 1
id = 181
kind = "item"
title = "Eval redesign step 1: record identity and the prompt-version gate"
status = "open"
decision_owner = "agent"
epic = 180
branches = ["feat/eval-record-identity"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Prompt content hashes + version gate, producer id, trace/span/case ids, parse outcome, judge cost in run totals."
```

Step 1 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 1. Scope lives there.
Enumerate the consumers of the call-log row and the eval record first (dashboard, `commands/bench.md`, `evals/tune.py`) and write the dossier.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

### 2026-10-21 -- built on feat/eval-record-identity

Built (the design doc's section 5.5 carries the departures): `call_identity.py` (hash, producer id, W3C ids); `prompt_sha256`, `producer_id` and `parse_outcome` on call-log rows, and `trace_id` / `span_id` / `parent_span_id` / `case_id` on rows written inside an eval run; `trace_id` / `case_id` / `span_id` on eval records and `judge_cost_usd` on the `eval_composite` record; `EvalRunResult` gains `trace_id`, `judge_cost_usd`, `total_cost_usd`; the cost-by-window leak fixed (`_eval_cost_since` replaced by `_trace_cost` / `_case_cost`, selected by id from a byte offset); `evals/prompt_hashes.json`, `scripts/prompt_lock.py` and `tests/test_prompt_hash_gate.py` (the system-prompt half of the bump rule is now a gate; enforcement.md C3). Consumers: `docs/dev/blast-radius/eval-record-identity.md`.

Declared, not done: user-prompt templates are not hashed (unenforced); a hand-edited lock passes; iteration records still recompute `cost_usd` later and include `iterate_clarify` while the others do not; judge rows keep `run_id ""`; the dashboard still embeds whole raw rows (about +28 KB with the two hashes); product-flow tracing is step 10; `case_id` is the fixture name until step 2.

Status left `open`: closing needs a falsifiable `verified_by` the owner agrees to (the new tests, plus a merged gate run). Item 182 stays blocked until this branch lands.

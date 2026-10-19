# Diagnosis — the call log cannot say which model version answered, with what settings (item 175)

> **Status:** gaps 2, 3 and 4 PROVEN (observations 1 and 4); gap 1's mechanism ("`final.model` shows the version")
> FALSIFIED; gaps 5-7 are read from code and still unobserved (judge calls were not probed live).
> **Branch:** `fix/llm-call-provenance`

---

## Symptom

Owner requirement (2026-10-17, item 175): *"be sure that we are tracking the model, the model version, and the
settings such as effort level, thinking etc. so we can trace every decision to the model that made it and the
settings for that model."* Today a `logs/llm_calls.jsonl` row names the model id the code asked for, not the version
that answered, the settings sent, the API request id or thinking tokens; the eval judge calls write no row at all.

---

## Observed

1. **The retry drops the caller's `max_tokens`** (gap 4). Run on HEAD `72d2ff9`, the new strict-xfail test with the
   marker lifted:

   ```
   $ python -m pytest tests/test_refinement_scope.py -q -p no:randomly --runxfail -k retry_keeps
   E   assert [128, 8192] == [128, 128]
   ```

   `tests/test_refinement_scope.py` (`test_retry_keeps_the_callers_max_tokens_cap`) drives
   `check_refinement_scope` (`max_tokens=128`, `analyzer.py:3345`) with two unparseable replies; the fake client's
   captured `stream()` kwargs show attempt 1 at 128 and the `_retry` attempt at 8192 (`MAX_TOKENS`,
   `analyzer.py:1054`). With the marker in place the same test reports `9 passed, 1 xfailed`.

2. **The installed SDK exposes a request id on the stream.** `anthropic 0.88.0`: `python -c "from anthropic.lib.streaming
   import MessageStream as M; print([n for n in dir(M) if 'request' in n.lower() or n=='response'])"` printed
   `['request_id', 'response']`. `pyproject.toml:28` allows `anthropic>=0.40,<1.0`; I did not check 0.40.

3. **The SDK's typed `Usage` model in 0.88.0 has no thinking-token field.** `list(anthropic.types.Usage.model_fields)`
   printed `['cache_creation', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'inference_geo',
   'input_tokens', 'output_tokens', 'server_tool_use', 'service_tier']`. Item 173 saw `output_tokens_details.thinking_tokens`
   in a live response, so whether a streamed `Usage` object carries it as an extra attribute is open (see the probe).

4. **The live probe, before any production change** (2026-10-19T01:46Z UTC, HEAD `72d2ff9` plus the uncommitted probe script,
   anthropic 0.88.0). `python -m scripts.probe_call_provenance --yes`, exit 0, `total cost from rows: $0.005324`
   (Sonnet $0.004228, Haiku $0.001096; the owner-approved ceiling was $0.01). Sonnet call, abridged only by omitting the
   fields that equal the Haiku call's shape:

   ```
   "row_as_logged": { "username": "probe:175", "call": "probe_175", "model": "claude-sonnet-5",
     "prompt_version": "2026-10-17.2", "input_tokens": 13, "output_tokens": 4,
     "cache_creation_input_tokens": 1665, "cache_read_input_tokens": 0, "latency_ms": 1167,
     "stop_reason": "end_turn", "status": "ok" }
   "raw_from_sdk": { "kwargs_sent": { "model": "claude-sonnet-5", "max_tokens": 16,
                                      "thinking": { "type": "disabled" } },
     "answering_model": "claude-sonnet-5", "request_id": "req_011CgAkb7QobNW6SrVLLbzmP",
     "usage": { "cache_creation": { "ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 1665 },
                "cache_creation_input_tokens": 1665, "cache_read_input_tokens": 0, "inference_geo": "global",
                "input_tokens": 13, "output_tokens": 4, "server_tool_use": null,
                "service_tier": "standard", "speed": "standard" } }
   ```

   Haiku call: `row_as_logged.model` = `claude-haiku-4-5-20251001`; `raw_from_sdk.kwargs_sent` =
   `{"model": "claude-haiku-4-5-20251001", "max_tokens": 16}` (no `thinking`); `answering_model` =
   `claude-haiku-4-5-20251001`; `request_id` = `req_011CgAkbEAM84cCiUeAk7683`; `usage.inference_geo` = `not_available`,
   `service_tier` and `speed` = `standard`; `input_tokens` 1076 with both cache fields 0.

   What this shows, and only this:
   - **Gaps 2 and 3 confirmed.** The row carries neither the settings sent (`max_tokens` 16, `thinking: disabled`) nor
     the API request id, and the SDK had both for that very call.
   - **`final.model` returned the alias `claude-sonnet-5`, identical to the id requested.** For the Sonnet pin the
     response itself does not name a dated version.
   - **The streamed `usage` carried no `output_tokens_details` / thinking-token field** on either call (neither call
     was configured to think).
   - **`usage` carried three served-as facts the row drops:** `service_tier`, `speed` and `inference_geo`.

---

## Falsified

- **"`final.model` reveals the version behind the `claude-sonnet-5` alias"** (item 175 gap 1, the hypothesis that the
  answering version is one `getattr` away). Falsified by observation 4: the response's `model` equals the requested alias.
  Logging `final.model` is still cheap and would show a change if the API ever returns a dated id, but today it adds no
  information; the **API request id** is the only per-call handle that traces a row to the answering model.

---

## Inferred

Read from code on 2026-10-17 by item 175's filing pass and re-checked at HEAD this session (anchors held, about one
line of drift). **None of this has been seen in a real row.**

- `_call_llm_streaming` (`analyzer.py:1635-1656`) logs `model` = `effective_model` (the id requested), never
  `final.model` (gap 1); the request kwargs (`max_tokens`, `thinking`) are built at `:1583-1596` and not logged (gap 2);
  the stream's request id and thinking tokens are not read (gap 3).
- `_grade` (`evals/runner.py:625`) and `_score_distinctiveness` (`:440`) call `messages.create` and discard the
  response (gap 5). `MODEL_SNAPSHOTS` (`:112`) is a literal (gap 6). Avatar rows are stamped with the résumé
  `PROMPT_VERSION` and `db/build_context.py:181` stamps `PROMPT_VERSION`, not the effective one (gap 7).
- Whether `output_tokens_details.thinking_tokens` (seen by item 173 on a raw response) ever appears on a streamed `usage`
  is **still unknown**: both probed calls had thinking off or unsupported. The row field is built defensively (absent
  stays absent) and live population on a thinking call is declared unverified.
- Whether any response header or field names a dated Sonnet version is **not investigated**; the stream's `response`
  object exists (observation 2) but its headers were not read.

---

## Falsification

**The live probe**, run before any production change and again after:

`python -m scripts.probe_call_provenance --yes` (two calls, one Sonnet and one Haiku, one-word prompt, `max_tokens` 16;
owner-approved spend of at most $0.01 per run, $0.02 for both runs, 2026-10-18). It prints, per call, the telemetry row
exactly as `_emit_call_log` would write it and the raw facts from the SDK: the answering model, `stream.request_id`, the
full `usage` dump and the request kwargs sent (never the prompt).

- **If the row lacks the answering model, request id and settings that the raw block shows:** gaps 1-3 are confirmed
  and the fields are available to read.
- **If the raw block does not expose one of them** (for example no `output_tokens_details`): that field is not
  buildable on this SDK; record it as such and do not log a guess.
- **If the row already carries them:** the item is mis-filed; stop and report.

---

## The fix

Only after the probe output is under `## Observed`. Order, per the plan: the `max_tokens` retry fix (this test turns
green), then the provenance fields on the product row, then the judge calls.

---

## Acceptance bar

- The strict xfail is removed and `test_retry_keeps_the_callers_max_tokens_cap` passes without a rerun.
- A fail-closed test asserts every kwarg passed to `messages.stream` except `system`/`messages` appears in the row.
- The probe re-run shows the new fields populated from a real response, with spend stated from the rows.
- A judge call's row and its eval record share the API request id.

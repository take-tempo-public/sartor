# Diagnosis — MODEL_PRICING prices the two live pins at rates the pricing page does not list

> **Status:** observed and arithmetic-proven for the two table entries; the *cause* of the Haiku numbers (copied from the
> wrong row) is **not established** — only that they equal that row. Not verified against an invoice.
> **Branch:** `fix/model-pricing-rates` (work item 174)

---

## Symptom

`compute_call_cost` (`hardening.py:1710-1740`) prices every `claude-sonnet-5` call 1.5 times above the published rate and
every `claude-haiku-4-5-20251001` call 20 percent below it. The dashboard, the eval runner's `cost_usd`, and every
telemetry-window spend figure inherit the error, in opposite directions for the two models.

---

## Observed

- **The table at HEAD `dbc6f02`** — `hardening.py:439-465`: Sonnet 5 `in 3.00 / out 15.00 / cache_write 3.75 /
  cache_read 0.30`; Sonnet 4.6 the same; Haiku 4.5 `in 0.80 / out 4.00 / cache_write 1.00 / cache_read 0.08`. The comment
  at `hardening.py:439-445` says "as of 2026-07-05" and calls `$3/$15` "the durable rate".
- **The pricing page, fetched 2026-10-17 with `WebFetch`** (`https://platform.claude.com/docs/en/about-claude/pricing`;
  the page text was saved to a file and these rows are lines 30, 36, 37 and 45 of it, read with a text search, not from
  the tool's summary). Columns: base input, 5m cache write, 1h cache write, cache hit, output, per MTok:

  ```
  | Claude Sonnet 5   | $2 / MTok<sup>3</sup> | $2.50 / MTok | $4 / MTok   | $0.20 / MTok | $10 / MTok<sup>3</sup> |
  | Claude Haiku 4.5  | $1 / MTok             | $1.25 / MTok | $2 / MTok   | $0.10 / MTok | $5 / MTok              |
  | Claude Haiku 3.5  | $0.80 / MTok          | $1 / MTok    | $1.60 / MTok| $0.08 / MTok | $4 / MTok              |
  *3 The $2/$10 per million input/output token pricing for Claude Sonnet 5, announced at launch as introductory
  pricing through August 31, 2026, is now the standard price. The previously scheduled increase to $3/$15 per
  million input/output tokens on September 1, 2026 will not occur.
  ```
- **The Haiku 4.5 table entry equals the page's Haiku 3.5 row** (`0.80 / 4.00 / 1.00 / 0.08`), not Haiku 4.5's.
- **Two real telemetry rows, costed both ways** (read-only probe over `logs/llm_calls.jsonl`, 1564 records; the probe
  lives in the session scratchpad and is not committed). `compute_call_cost` is today's table; "by hand" multiplies the
  row's tokens by the page's rates above (5m cache-write):

  ```
  {"timestamp": "2026-07-05T23:23:06.836800+00:00", "call": "analyze_synthesis", "model": "claude-sonnet-5",
   "input_tokens": 1665, "output_tokens": 2315, "cache_creation_input_tokens": 2848, "cache_read_input_tokens": 0}
    compute_call_cost (current table) = 0.0504
    by hand at pricing-page rates      = 0.0336
  {"timestamp": "2026-05-12T22:50:17.318850+00:00", "call": "extract_experiences", "model": "claude-haiku-4-5-20251001",
   "input_tokens": 1380, "output_tokens": 1324, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    compute_call_cost (current table) = 0.0064
    by hand at pricing-page rates      = 0.008
  ```
  Ratios: 0.0504 / 0.0336 = 1.5 (Sonnet); 0.0064 / 0.008 = 0.8 (Haiku).
- **Tests that assert the old numbers:** `tests/test_hardening.py:763-764` (`claude-sonnet-5`, 1M input `== 3.0`) and
  `tests/test_hardening.py:774-775` (`claude-haiku-4-5-20251001`, 1M cache-read `== 0.08`). The `claude-sonnet-4-6`
  assertions at `:752` and `:799-800` use that model's own (correct) entry.
- **No test asserts that a model constant has a pricing key by value or presence for the eval judge:**
  `tests/test_call_kind_telemetry.py:234` checks `rec["model"] in MODEL_PRICING` on records the tests generate only.
  `evals/runner.py:112-117` holds `MODEL_SNAPSHOTS` and `JUDGE_MODEL` as literals, separate from `analyzer.SONNET_MODEL` /
  `HAIKU_MODEL` (`analyzer.py:1042-1043`).
- **Limits of this evidence:** the page is text I read, not an invoice or the Console usage page; the cache-write rate used
  is the 5-minute one because `cache_control: {"type": "ephemeral"}` is the only TTL the product sends and the telemetry
  keeps one creation count (`analyzer.py:1634-1655`), so a 1-hour write cannot be expressed.

---

## Falsified

- **Item 174 as filed said `hardening.py` is a C-10 gated surface (`blast_radius.py:204`).** It is not: `hardening.py` and
  `analyzer.py` are both in `ACKNOWLEDGED_NOT_GATED` (`scripts/enforcement/blast_radius.py:199-208`, "Watched, not gated").
  The consumer list below is written anyway because the table is read by a widely-consumed helper.
- **Item 174 cites `CHANGELOG.md:5468` for the Sonnet 5 pricing entry.** That line is about render-parity tests; the entry is
  at `CHANGELOG.md:5487-5491`.

---

## Inferred

Nothing beyond the arithmetic above. *Not established:* how the Haiku numbers came to equal the Haiku 3.5 row.

---

## Falsification

The updated assertions are the experiment: with `tests/test_hardening.py:763-764` changed to `== 2.0` and `:774-775` to
`== 0.10`, plus a new test that every model constant (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`, each
`MODEL_SNAPSHOTS` value) has a `MODEL_PRICING` key with all four rates, run on HEAD:

- **If the two updated assertions fail on HEAD (and the coverage test passes):** the table is wrong as observed; build the fix.
- **If they pass on HEAD:** the observation above is wrong. Stop; do not edit the table.

---

## The fix

Correct the two entries (Sonnet 5 → `2.00 / 10.00 / 2.50 / 0.20`; Haiku 4.5 → `1.00 / 5.00 / 1.25 / 0.10`), keeping every
key; rewrite the comment (date, source, 5-minute cache-write); correct the two stale comments in `analyzer.py`
(`:1017-1018` price sentence, `:1043` "no Haiku 5"); add the coverage test; `CHANGELOG.md` `[Unreleased]`.

## Acceptance bar

`pytest tests/test_hardening.py::TestCallCost` passes on the fixed tree and its updated assertions fail on HEAD (output
recorded here after the run); the two telemetry rows above cost `0.0336` and `0.008` through `compute_call_cost`; the full
gate (`python -m scripts.gate --result`) passes with no retried test.

---

## Consumers

`MODEL_PRICING` and `compute_call_cost` are defined only in `hardening.py`; there is no alias or re-export. Searched the
whole tree for `MODEL_PRICING`, `compute_call_cost`, `hardening.compute_call_cost`, and `cost_usd`.

| site | what it does | decision |
|---|---|---|
| `dashboard/routes.py:205-207,771-776` | prices each call for totals, p50/p95, cost by call kind | follows the table; no edit |
| `evals/runner.py:80,483` | `_eval_cost_since` sums telemetry cost into each eval record's `cost_usd` | follows the table; no edit. Eval `cost_usd` shifts for new runs only |
| `evals/corpus_drafting_probe.py:111,128` | per-run cost | follows the table; no edit |
| `scripts/smoke_phase_b1.py:203-217` | prints run cost | follows the table; no edit |
| `tests/test_hardening.py:741-800` | pins values for `claude-sonnet-5`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6` | edit `:763-764`, `:774-775`; add coverage test |
| `tests/test_call_kind_telemetry.py:54,234-236` | `rec["model"] in MODEL_PRICING` | key presence only; unaffected |
| `tests/test_dashboard_routes.py:375-386,861` | `> 0`, `== 0.0`, ordering; uses `claude-sonnet-4-6` | unaffected |
| `analyzer.py:1017-1018,1043` | comments repeating the stale price claim and "no Haiku 5" | comment-only edit; no prompt text, so no `PROMPT_VERSION` bump |

## Deferred

- **Cost figures already published** (`evals/TUNING_LOG.md`, `evals/results/baseline_v1.json`, `docs/dev/perf/PERFORMANCE_HISTORY.md`,
  diagnosis and handoff files, `CHANGELOG*.md`): left as dated records, the owner's decision (2026-10-17). One dated note is added to
  `evals/TUNING_LOG.md` stating which rates they used.
- **`evals/README.md:977-986` cost estimates** (`~$0.35-0.40` smoke, `~$0.12`/fixture): item 134 owns the contradicting estimates.
- **Sonnet 5.5, Haiku 5.5 and Opus keys, and Haiku 5.5's prompt-length tiers:** need a `compute_call_cost` change; item 137's branch.
- **`commands/bench.md:19`** uses "current Anthropic pricing" and does not read the table; not touched.

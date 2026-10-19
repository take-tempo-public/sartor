# Blast radius — thinking-policy-55-pricing

> **Branch:** `feat/thinking-policy-55-pricing`
> **Status:** enumeration complete (greps run 2026-10-19 at `1b40b51`, before the first code edit)

**Registry note (observed):** `scripts/enforcement/blast_radius.py:198-209` lists `analyzer.py` and `hardening.py` under
`ACKNOWLEDGED_NOT_GATED`, so `require-consumer-enumeration` does **not** fire on them. Item 173 called them "C-10 gated"; that
is wrong for the current registry. This dossier is written anyway: charter C-10 covers a widely-consumed helper, and
`MODEL_PRICING` / `compute_call_cost` / the `thinking` request setting are exactly that.

---

## Surface

- `analyzer.py`: new module-level `THINKING_POLICY` table (after `HAIKU_MODEL`, `:1158`); `_call_llm`'s send block
  (`:1719-1720`, the `if effective_model == SONNET_MODEL:` branch) reads the table instead; comments at `:1136`, `:1158`, `:1163`,
  `:1698-1706` updated.
- `hardening.py`: `MODEL_PRICING` (`:451`) gains `claude-sonnet-5-5` and `claude-haiku-5-5`; new `MODEL_PRICING_TIERS`;
  `compute_call_cost` (`:1715-1745`) applies a tier. Signature and return type unchanged.
- `evals/runner.py`: `_judge_create` (`:417-434`) merges the policy value into the request.
- Tests: `tests/test_hardening.py` (`TestCallCost`), `tests/test_call_provenance.py:119`.

---

## Enumeration

`git grep` over `*.py *.yaml *.yml *.js *.html`, docs excluded unless stated. Run at `1b40b51`.

| Name searched | Hits | Where |
|---|---|---|
| `THINKING_POLICY` | 0 | new name |
| `MODEL_PRICING_TIERS` | 0 | new name |
| `SONNET_MODEL ==` | 0 | the old equality test reads `effective_model == SONNET_MODEL` (`analyzer.py:1719`); searched separately below |
| `"thinking"` | 2 | `analyzer.py:1720` (the send), `tests/test_call_provenance.py:119` |
| `thinking=` | 1 | `analyzer.py:1136` (a comment) |
| `messages.stream(` | 5 | `analyzer.py:1726` (**the only product send**), `scripts/probe_call_provenance.py:95` (wraps a client), three prose mentions in tests |
| `messages.create(` | 1 | `evals/runner.py:434` (**the only judge send**) |
| `_judge_create` | 3 | def `evals/runner.py:417`; callers `:488`, `:688` |
| `claude-sonnet-5-5` / `claude-haiku-5-5` in `*.py *.yaml *.js *.html` | 0 / 0 | no code names a 5.5 model yet |
| `model=HAIKU_MODEL` / `model=SONNET_MODEL` (non-test `*.py`) | 14 / 4 | call sites; all reach `_call_llm` |
| other `model=` values | pass-through only | `analyzer.py:1841,1912,1996,2053` are `model=model` hops in the retry wrappers; `evals/runner.py` passes `JUDGE_MODEL`; `evals/grounding_signals.py:60` is an NLI model id, not an Anthropic call |
| `MODEL_PRICING` / `compute_call_cost` | see Consumers rows 5-12 | defined only in `hardening.py`; no alias or re-export |
| literal `claude-(haiku\|sonnet)-N` outside tests/docs/CHANGELOG | 25 lines | `analyzer.py`, `hardening.py`, `evals/runner.py`, `promptfooconfig.yaml`, `agents/*.md`, `AGENTS.md`, `CLAUDE.md`, `evals/README.md`, `scripts/verify_doc_template.py` (an agent-name example string) |

**Negative results:** no other `messages.*` send site in the first-party tree; no JS, HTML or CSS names a model or a thinking
setting; `docs/wiki/pages/` states no thinking rule (only `llm-call-catalog.md:110` and `deterministic-llm-boundary.md:72` mention
the *recorded* `thinking_tokens` field, which does not change).

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `analyzer.py:1719-1720` (`_call_llm` thinking branch) | **update** | Reads `THINKING_POLICY[effective_model]`; a model absent from the table raises `LLMConfigurationError` before `sent_kwargs` is set. Sonnet 5 → `disabled`, Haiku 4.5 → not sent: identical to today. |
| 2 | `analyzer.py:1136`, `:1158`, `:1163`, `:1698-1706` (comments) | **update** | Describe the equality test and "Sonnet path"; they must describe the table. No prompt text moves, so no `PROMPT_VERSION` bump. |
| 3 | `analyzer.py:1841,1912,1996,2053` (`model=model` hops) | no change | Forward the model to `_call_llm`; the policy lookup sits below them. |
| 4 | 14 `model=HAIKU_MODEL` + 4 `model=SONNET_MODEL` call sites, plus `onboarding/extract_experiences.py:174` | no change | All reach `_call_llm`, so all get the lookup. Pins are unchanged, so every one keeps its current request. |
| 5 | `hardening.py:451-470` `MODEL_PRICING` | **update** (add keys) | Two keys added; every existing key kept (historical `llm_calls.jsonl` rows). Flat four-rate shape preserved. |
| 6 | `hardening.py:1715-1745` `compute_call_cost` | **update** | Applies `MODEL_PRICING_TIERS` when prompt tokens exceed the threshold; unchanged for every model without a tier. |
| 7 | `dashboard/routes.py:205,207,771,776` | no change | Calls `compute_call_cost(record)`; signature unchanged. |
| 8 | `evals/runner.py:83,539` | no change | Same. |
| 9 | `evals/corpus_drafting_probe.py:111,128` | no change | Same. |
| 10 | `scripts/smoke_phase_b1.py:203,217` | no change | Same. |
| 11 | `scripts/probe_call_provenance.py:95,129` | no change | Wraps `messages.stream` and calls `compute_call_cost`; both unchanged. |
| 12 | `tests/test_call_kind_telemetry.py:54,238` | no change | Asserts `rec["model"] in MODEL_PRICING`; keys are only added. |
| 13 | `tests/test_hardening.py:742-826` (`TestCallCost`) | **update** (add tests) | Existing assertions hold (flat keys unchanged). Adds: policy ↔ pricing coverage, tier boundary at 100,000 / 100,001, 5.5 cost figures. |
| 14 | `tests/test_call_provenance.py:119` | **update** | "thinking sent iff model is `SONNET_MODEL`" is the old rule; becomes "iff `THINKING_POLICY[model]` is not `None`". New tests: 5.5 values, unknown model raises with one error row and no stream, judge request. |
| 15 | `evals/runner.py:417-434` `_judge_create` | **update** | The one judge send site; merges the policy value (`None` for Haiku 4.5, so today's judge request is unchanged). Callers `:488` and `:688` need no edit. |
| 16 | `evals/runner.py:115-123` (`JUDGE_MODEL`, `MODEL_SNAPSHOTS`) | no change | Pins unchanged; `test_every_model_pin_has_complete_pricing` covers them and the new test covers their policy. |
| 17 | `analyzer.py:780-` `_provenance_fields` and the `request_settings` row field | no change | Records the kwargs actually sent, so a `between_tools` or `disabled` value appears in the row with no edit. |
| 18 | `promptfooconfig.yaml:10,17` | no change | Names `claude-sonnet-5`; the pin does not move. |
| 19 | `agents/*.md` frontmatter, `CLAUDE.md` §"Model-pin convention" | no change | Subagent pins are dev tooling; out of scope (see Deferred). |
| 20 | `docs/wiki/pages/llm-call-catalog.md:110`, `deterministic-llm-boundary.md:72` | no change (to be confirmed by the scoped wiki check at close-out) | State the recorded `thinking_tokens` field, not the sending rule. |
| 21 | `docs/dev/architecture.md` §"LLM routing + cost" | no change expected; verify at close-out | Greps for `thinking` in it returned nothing. |
| 22 | `CHANGELOG.md` | **update** | Pricing keys and request behaviour; no new dependency. |

---

## Deferred

- **Opus 5.5 pricing key and policy entry.** The product makes no Opus call (no `OPUS_MODEL`; item 173). Add both when a call exists.
- **Any pin change** (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`). That is the candidate A/B, one swap per branch, and it needs the
  owner's spend approval; none is given.
- **A model-override mechanism for candidate runs** (item 173 proposal 16). Not searched here, not built. The A/B branch decides it.
- **Subagent pins** (`agents/*.md`). Dev tooling; own small branch after the product decision.
- **Adaptive thinking for Haiku 5.5 or Sonnet 5.5.** The table holds thinking-off. Adopting adaptive is an eval-gated change of its own.
- **`claude-sonnet-4-6`** has a price but no policy entry. It is a historical-cost key only, and no code calls it. The coverage
  test checks pins, not every price key.

---

## Verification

- The new `THINKING_POLICY` tests turn a missed pin red: every pin must be a policy key, and every policy key must be priced.
- A missed send site would have to be a second `messages.stream(` or `messages.create(` in first-party code. Both greps above
  return exactly one such call each, and the plan re-runs them at close-out.
- Existing `test_every_request_kwarg_is_recorded` runs unchanged for Sonnet 5 and Haiku 4.5, proving today's requests are untouched.

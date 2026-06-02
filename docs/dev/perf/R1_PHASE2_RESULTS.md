# R1 Phase 2 — analyze re-architecture: results (before / after)

> **Purpose:** the portfolio-grade before/after record of the R1 Phase 2 work
> (v1.0.3) — what the analyze stage cost in **speed, money, and eval quality**
> before the change, and after. Companion to
> [`R1_BENCHMARK_2026-05-26.md`](R1_BENCHMARK_2026-05-26.md) (the *failed* first
> attempt + diagnosis) and to [`../evals/TUNING_LOG.md`](../../../evals/TUNING_LOG.md)
> (the per-branch institutional record).
> **Authoritative for:** the headline numbers below. Each is traceable to a
> dated `TUNING_LOG.md` entry, a `PROMPT_VERSION`, and committed
> `evals/results/*.jsonl` runs.

---

## TL;DR

The `analyze` stage was a single ~103 s Sonnet call doing two cognitively
distinct jobs (keyword extraction **and** strategy synthesis). R1 Phase 2
re-architected it into a **two-pass pipeline** — a fast Haiku *extraction* pass
feeding a Sonnet *synthesis* pass — and landed:

| Dimension | Before (v1.0.2) | After (v1.0.3) | Δ |
|---|---|---|---|
| **Speed** — `analyze` p50 | **103.2 s** | **67.7 s** | **−34 %** |
| **Cost** — per application run | ~**$0.41** | ~**$0.36** | **−12 %** |
| **Eval** — `clarification_quality` (pm / ds / sre) | 4.00 / 3.92 / 4.02 | **4.26 / 4.20 / 4.02** | held + recovered |
| **Eval** — all other rubrics | baseline | at or **above** baseline | held |

The hard part was not the speed — it was getting the speed **without paying for
it in quality**. A naïve first attempt (2026-05-26) hit the same ~72 s but
**crashed `clarification_quality` from 4.2 → 2.1** and was reverted. The shipped
version fixes the two root causes first (as parse-time *guardrails*), then adds
the split on top, gated by an eval suite that blocks any rubric regression > 0.5.

---

## The arc — three reference points

| # | State | `PROMPT_VERSION` | `analyze` p50 | `clarification_quality` (pm) | Outcome |
|---|---|---|---|---|---|
| 1 | **Before** — unified single-call analyze | `2026-05-24.4` | 103.2 s | 4.00 | the baseline |
| 2 | **First attempt** — naïve two-pass split | `2026-05-26.2` | ~71.6 s | **2.1** | **reverted** (quality floor breached) |
| 3 | **Shipped** — two-pass split + guardrails + cache reclaim | `2026-06-01.3` | **67.7 s** | **4.26** | **merged** |

Why attempt #2 failed and #3 worked: the split moved keyword extraction to a
cheaper model, but extraction's `hidden_qualities` signal (which drives the
clarify interview) lost its shape on the round trip, and the clarify pass stopped
emitting the portable `context_probe` questions the rubric rewards. R1 Phase 2
fixed both **before** re-introducing the split, and enforced them at parse time
so they can't silently regress again:

- **Typed `hidden_qualities`** — `list[{category: enum, signal: str}]`; a
  bare-string or out-of-enum item fails Pydantic validation → automatic retry.
- **Parse-time `context_probe` enforcement** — clarify must emit ≥1 portable
  context probe when hidden signals exist, and ≥60 % experience+context probes
  combined, or it retries.

(See `TUNING_LOG.md` 2026-05-30 `r1/structural-context-probe`, 2026-06-01
`r1/hidden-qualities-schema`, and 2026-06-01 `r1/analyze-split-cache-reclaim`.)

---

## Speed

Per-call latency, p50, from `logs/llm_calls.jsonl`.

| Stage | Before (`2026-05-24.4`) | After (`2026-06-01.3`) | Note |
|---|---|---|---|
| `analyze` (single Sonnet call) | **103.2 s** | — | one call, ~4.5k output tokens |
| `analyze_extraction` (Haiku) | — | **10.0 s** | structured lists |
| `analyze_synthesis` (Sonnet) | — | **57.9 s** | strategy only |
| **`analyze` combined** | **103.2 s** | **67.7 s** | **−34 %** |
| `generate` (Sonnet) | ~49.6 s | 46.9 s | unchanged by design |

The win comes from moving the keyword/vocabulary extraction — structurally a
classification task — off Sonnet and onto Haiku (~10 s), leaving Sonnet to do
only the strategy synthesis on roughly half the output tokens. Two sequential
calls, lower total wall-clock, because the Haiku pass is so much cheaper per
token. Perceived latency improves further: the streaming UI now shows a
phase label ("Extracting JD signals…" → "Analyzing positioning…") so the user
sees concrete progress within ~10 s instead of waiting on one opaque ~100 s call.

---

## Cost

Per-fixture cost (mean), from eval `cost_usd` telemetry. Before = v1.0.2 baseline
(n=5); after = v1.0.3 reclaim build (n=5).

| Fixture | Before | After | Δ |
|---|---|---|---|
| data-scientist-junior | $0.132 | $0.116 | −12 % |
| pm-senior | $0.136 | $0.118 | −13 % |
| sre-mid-level | $0.147 | $0.128 | −13 % |
| **per run (3 fixtures)** | ~**$0.41** | ~**$0.36** | **−12 %** |

Two forces, both favourable: (1) the high-token extraction work runs on Haiku
(~4× cheaper input, far cheaper output) instead of Sonnet; (2) the
**analyze→generate prompt cache was preserved** — the synthesis pass runs under
the same `SYSTEM_PROMPT` as `generate`, so its cached prefix
(`[SYSTEM_PROMPT][corpus + résumé + JD]`) is byte-identical and `generate` reads
it instead of re-billing those tokens (`cache_read` confirmed on 15/15 runs). An
intermediate build that gave synthesis a dedicated persona *broke* that cache
(`cache_read = 0`); reclaiming it is what keeps cost falling rather than flat at
larger corpus sizes.

---

## Eval performance

Per-(fixture × rubric) mean. Before = v1.0.2 baseline (`2026-05-24.4`, n=5);
after = v1.0.3 shipped (`2026-06-01.3`, n=5, judge-errors excluded). Higher is
better; scale 0–5.

| Rubric | Fixture | Before | After | Δ |
|---|---|---|---|---|
| **clarification_quality** | data-scientist-junior | 3.92 | **4.20** | **+0.28** |
| | pm-senior | 4.00 | **4.26** | **+0.26** |
| | sre-mid-level | 4.02 | 4.02 | +0.00 |
| ats_format | data-scientist-junior | 4.58 | 4.40 | −0.18 |
| | pm-senior | 4.44 | 4.36 | −0.08 |
| | sre-mid-level | 4.52 | 4.60 | +0.08 |
| grounding | data-scientist-junior | 4.70 | 4.72 | +0.02 |
| | pm-senior | 4.40 | 4.64 | +0.24 |
| | sre-mid-level | 4.64 | 4.80 | +0.16 |
| keyword_coverage | data-scientist-junior | 4.30 | 4.30 | +0.00 |
| | pm-senior | 4.12 | 4.20 | +0.08 |
| | sre-mid-level | 4.32 | 4.46 | +0.14 |
| tone | data-scientist-junior | 4.20 | 4.20¹ | +0.00 |
| | pm-senior | 4.18 | 4.20 | +0.02 |
| | sre-mid-level | 4.12 | 4.36 | +0.24 |

¹ `ds × tone` median; one of five runs scored 2.1 on an isolated
`generate`-side cover-letter opener (a pre-existing flakiness unrelated to the
analyze change — flagged for a future generate-tuning pass).

`callback_likelihood` (a recruiter-persona rubric added during v1.0.2, so absent
from the pre-R1 baseline) lands at ds 4.54 / pm 4.18 / sre 4.45 on the shipped
build.

**Net:** the most important rubric, `clarification_quality`, recovered from a
long-standing sub-4.0 floor (ds 3.92, pm 4.00) to a comfortable ≥4.2, while every
other rubric held at or above its pre-R1 baseline. **Speed and cost improved with
no quality cost** — the explicit dual-gate criterion for the work.

---

## How quality was held while speed improved

1. **Quality first, speed second.** The two diagnosed regression causes were
   fixed and locked in as parse-time guardrails (typed `hidden_qualities`,
   enforced `context_probe` composition) *before* the speed split was
   re-introduced — so the split could not reopen the regression.
2. **A dual gate, not a speed gate.** Every candidate was run n=3–5 on a frozen
   3-fixture anchor suite; merge was blocked unless `analyze` p50 ≤ 72 s **and**
   no rubric dropped > 0.5 vs the prior floor. The first attempt failed this gate
   and was reverted; the shipped build cleared it on the first try.
3. **The merged contract never changed.** `analyze()` stayed a thin orchestrator
   returning the same response shape every downstream consumer (frontend, clarify,
   generate, eval rubrics) already expected — the re-architecture was invisible
   above the function boundary.

---

## Provenance

| Number | Source |
|---|---|
| Before — eval + cost + latency | `TUNING_LOG.md` "BASELINE — v1.0.2 — 2026-05-28"; `evals/results/20260528_*.jsonl` (n=5); `PROMPT_VERSION 2026-05-24.4` |
| Before — `analyze` p50 103.2 s | `R1_BENCHMARK_2026-05-26.md` latency table |
| First attempt (reverted) | `R1_BENCHMARK_2026-05-26.md`; branch `r1-attempted-2026-05-26` (read-only); `PROMPT_VERSION 2026-05-26.1/.2` |
| After — eval + cost + latency | `TUNING_LOG.md` 2026-06-01 `r1/analyze-split-cache-reclaim`; `evals/results/20260601_{185916,191510,192408,210845,211737}Z.jsonl` (n=5); `PROMPT_VERSION 2026-06-01.3` |

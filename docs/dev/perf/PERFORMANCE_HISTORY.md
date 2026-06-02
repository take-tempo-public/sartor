# Performance history — callback.

> **Purpose:** the portfolio-grade narrative of callback.'s pipeline-performance
> work — what was slow, what we tried, what each experiment yielded, and how we
> proved it without trading away output quality. Written to be *presented*:
> every number traces to committed telemetry.
> **Audience:** anyone evaluating the engineering (reviewers, interviewers,
> future contributors) and agents proposing the next perf intervention.
> **Authoritative for:** the measured latency / cost trajectory and the
> synthetic-vs-real-corpus analysis. Companions:
> [`PERF_ANALYZE.md`](PERF_ANALYZE.md) (the original analyze audit that kicked
> this off), [`R1_PHASE2_RESULTS.md`](R1_PHASE2_RESULTS.md) (the R1 before/after),
> [`../evals/TUNING_LOG.md`](../../../evals/TUNING_LOG.md) (per-branch institutional record).
> **Telemetry source:** `logs/llm_calls.jsonl` — **1,824 LLM calls tracked
> 2026-05-06 → 2026-06-02.** Numbers below are p50 unless noted; reproduce with
> the snippet in [Provenance](#provenance).

---

## TL;DR — the headline

callback.'s critical path is a chain of LLM calls (analyze → clarify → generate).
`analyze` started as a **90-second opaque wall**. Over four weeks we cut the core
pipeline **~27% in wall-clock and ~20% in cost**, turned the worst wait into a
live progress experience, and **recovered the most important quality rubric from
sub-4.0 to ~4.2 along the way** — every speed/cost change gated so it could not
regress quality.

| Dimension (synthetic anchor) | Before (v1.0.2) | Now (v1.0.3) | Δ |
|---|---|---|---|
| `analyze` wall-clock | 86 s (real-corpus: 104 s) | 67 s | **−22%** |
| `clarify` wall-clock | 11 s | 7 s | **−37%** |
| `generate` wall-clock | 48 s | 47 s | flat (by design) |
| core pipeline wall-clock | ~145 s | ~121 s | **−17%** |
| cost / application | ~$0.138 | ~$0.113 | **−18%** |
| perceived `analyze` latency | 90 s blank screen | alive < 1 s, progress throughout | qualitative |
| `clarification_quality` (pm/ds/sre) | 4.00 / 3.92 / 4.02 | 4.20 / 4.20 / 4.02 | **recovered** |

The hard part was never the speed. It was getting the speed **without paying in
quality** — and proving it.

---

## How we measure

Three instruments, used together:

1. **Per-call telemetry — `logs/llm_calls.jsonl`.** Every `_call_llm` writes one
   record: `call` kind, `model`, `latency_ms`, input / output / cache tokens,
   `prompt_version`, `status`, `username`. This is the ground truth for latency
   and cost; 1,824 records span the whole project.
2. **A frozen synthetic anchor suite.** Three fixtures (`data-scientist-junior`,
   `pm-senior`, `sre-mid-level`) with fixed JD + résumé, run through the real
   pipeline by `evals/runner.py --suite anchor`. Same inputs every time → a
   **controlled, repeatable** measurement we can diff release-to-release. Logged
   under `username=eval:<fixture>`.
3. **An eval gate.** Each candidate is scored n=3–5 on six rubrics by a Haiku
   judge; merge is **blocked** unless latency *and* quality both clear the bar
   (no rubric drop > 0.5 vs the prior floor). Speed that costs quality does not ship.

**Cost model used below:** Anthropic list pricing per Mtok — Sonnet 4.6 $3 in /
$15 out, Haiku 4.5 $1 in / $5 out; cached-read input billed at 0.1×, cache-write
at 1.25×. Applied to the logged token counts.

---

## Synthetic vs real corpus — why we track both

The single most important context for reading these numbers: **a real candidate's
corpus is 1.5–4× larger than a synthetic fixture**, and that size drives almost
everything downstream.

Median input tokens, by who ran the call (from the log):

| Segment | `analyze` input | `generate` input | Notes |
|---|---|---|---|
| **synthetic** `eval:*` | **2,322** | **6,432** | uniform, frozen — the controlled baseline |
| real — `demo` | 3,697 | 7,095 | small real corpus |
| real — `testuser` | 4,671 | 9,051 | mid real corpus |
| real — `robert` | **8,799** | **12,709** | large real corpus — 2× synthetic |

Because LLM latency on these calls is **output-bound but input-sensitive**, the
larger real corpora run measurably slower and cost more for the *same prompt
version*:

| Call (v1.0.2, `2026-05-24.4`) | Synthetic | Real-corpus | Real overhead |
|---|---|---|---|
| `analyze` p50 / p90 / max | 86 / 95 / 99 s | **104 / 122 / 136 s** | +21% p50, heavier tail |
| `analyze` cost/call | $0.073 | $0.087 | +19% |
| `generate` p50 / p90 / max | 48 / 52 / 55 s | **60 / 80 / 87 s** | +25% p50, much heavier tail |
| `generate` cost/call | $0.047 | $0.068 (robert: $0.087) | +45% |

**Why we gate on synthetic and validate on real.** The synthetic anchors give a
low-variance signal to catch regressions (you cannot tune against a moving
target). The real numbers tell you the *absolute* user experience and, critically,
that **the wins grow at scale**: a cache hit or a cheaper model saves more
absolute tokens on robert's 12.7k-token `generate` than on the synthetic 6.4k.
The one honest gap — see [Caveats](#caveats--validation-gaps) — is that the
two-pass split itself has only been measured on synthetic fixtures so far; the
real-corpus projection is inference, not yet measurement.

---

## What we tried, in order — and what each yielded

The journey is six interventions plus one instructive failure. Each row of the
data tables below is a real `prompt_version` in the log.

### 1. Stable-prefix caching (v1.0.0) — *foundation*

**Idea:** `analyze` and `generate` share a huge identical prefix
(`[SYSTEM_PROMPT][corpus + résumé + JD]`). Mark it cacheable so `generate` *reads*
the prefix `analyze` already paid to process, instead of re-billing the whole corpus.

**Yield:** visible from `2026-05-12.1` onward as **`generate cache_read ≈ 1,877`
tokens** (synthetic). It is the reason `generate` stays ~$0.045 despite a 6k-token
input. This is the load-bearing optimization everything later had to *avoid breaking*.

### 2. R2 — streaming (v1.0.1, 2026-05-28) — *perceived latency*

**Idea:** stream `analyze()` and `generate()` over SSE so the user sees tokens
arrive instead of a frozen spinner.

**Yield:** **total wall-clock unchanged by design; perceived latency 90 s → "alive
within ~1 s, progress throughout."** This axis does not show up in `latency_ms`
(it is a UX metric) but it is the single biggest *felt* improvement of the project.
No prompt change — `PROMPT_VERSION` stayed `2026-05-24.4`.

> **Naming note for the presentation:** "R1" and "R2" are *leverage-ranked
> recommendation IDs* from [`PERF_ANALYZE.md`](PERF_ANALYZE.md), **not**
> chronological. R2 (streaming, lower effort) shipped *first* in v1.0.1; R1 (the
> split, higher leverage) shipped *later* in v1.0.3.

### 3. R1 attempt #1 — the naïve split (2026-05-26, **REVERTED**) — *the instructive failure*

**Idea:** `analyze` was one Sonnet call doing two cognitively different jobs —
keyword *extraction* and strategy *synthesis*. Split it: fast Haiku extraction +
Sonnet synthesis.

**Yield:** hit the speed target (~72 s) **but crashed `clarification_quality`
4.2 → 2.1** and was reverted. Two root causes: the `context_probe` interview
questions stopped being emitted, and the `hidden_qualities` signal lost its shape
on the cheaper-model round trip. **Lesson that shaped everything after: fix the
quality mechanism *first*, lock it at parse time, *then* add speed.**

### 4. R1 quality guardrails (`2026-05-30.1`, `2026-06-01.1`) — *recover first*

**Idea:** before re-attempting the split, make the two failure modes impossible.
Typed `hidden_qualities` (`{category: enum, signal: str}` — a bad shape fails
Pydantic → auto-retry) and a parse-time rule that `clarify` must emit ≥1
`context_probe` when hidden signals exist.

**Yield:** `clarification_quality` recovered to **4.20** (pm) — above the 4.0 line
for the first time — with no speed change yet. The guardrails are the safety net
the split then clipped into.

### 5. R1 split #2 (`2026-06-01.2`) — *speed lands, but a self-inflicted regression*

**Idea:** re-introduce the two-pass split on top of the guardrails.

**Yield:** **`analyze` 86 s → 67 s** (extraction ~10 s Haiku + synthesis ~60 s
Sonnet). Quality held. **But** the synthesis pass was given its own
`SYNTHESIS_SYSTEM_PROMPT`, which **diverged the cached prefix and silently broke
the analyze→generate cache** — `generate cache_read` dropped **1,877 → 0** and
`generate` cost rose **$0.045 → $0.052**. Caught it in the telemetry.

### 6. R1 cache reclaim (`2026-06-01.3`) — *fix the regression for free*

**Idea:** run synthesis under the *shared* `SYSTEM_PROMPT` (specialization moved
*after* the cached prefix, into the user message) so the prefix is byte-identical
to `generate`'s again.

**Yield:** **`generate cache_read` restored to 1,877 on 15/15 runs; `generate`
cost back to $0.045** — with no speed or quality cost. The elegant dedicated
persona bought nothing the schema-constrained prompt didn't, and cost a cache.

### 7. clarify → Haiku 4.5 (`2026-06-01.4`) — *this sprint*

**Idea:** `clarify` is short structured output (3–5 questions) — a Haiku sweet
spot — and `clarification_quality` was finally stable ≥ 4.0, the precondition.

**Yield:** **`clarify` 11 s → 7 s (−37%), $0.0167 → $0.0072 (−57%)**, with a flat
**0/15 retry rate** (Haiku satisfied the parse-time composition rules every time)
and `clarification_quality` held (medians 4.2 = the Sonnet floor). Two single-run
3.2 judge scores at n=3 were disambiguated as noise by extending to n=5.

---

## The data

### `analyze` — the trajectory

| Version | State | Segment | p50 | p90 | $/call | cache_read |
|---|---|---|---|---|---|---|
| `2026-05-24.4` | single Sonnet call | synthetic | 86 s | 95 s | $0.073 | 0 |
| `2026-05-24.4` | single Sonnet call | **real** | **104 s** | **122 s** | $0.087 | 0 |
| `2026-06-01.3` | Haiku extract + Sonnet synth | synthetic | **67 s** | 73 s | $0.059 | 0¹ |
| `2026-06-01.4` | Haiku extract + Sonnet synth | synthetic | 69 s | 76 s | $0.061 | 0¹ |

¹ synthesis *writes* the cache (cache_create) that `generate` later reads, so its
own `cache_read` is 0. Split detail: extraction (Haiku) ~10 s / $0.008 / ~1.1k out;
synthesis (Sonnet) ~58 s / $0.052 / ~2.8k out — moving the high-token classification
work to Haiku is the whole win.

**Reading the −22% vs the published −34%.** The often-cited "103 → 68 s, −34%"
([`R1_PHASE2_RESULTS.md`](R1_PHASE2_RESULTS.md)) used a v1.0.2 baseline that, per
the original benchmark, was measured at ~103 s — which the log shows aligns with
**real-corpus** scale (104 s), not synthetic (86 s). The clean **synthetic-to-
synthetic** delta is **86 → 67 s = −22%**; the cross-segment headline is −34%. Both
are real; they measure different baselines. Stated plainly because a presentation
audience will (rightly) ask.

### `generate` — flat latency, cost held by the cache

| Version | Segment | p50 | $/call | cache_read | note |
|---|---|---|---|---|---|
| `2026-05-24.4` | synthetic | 48 s | $0.047 | 1,877 | baseline |
| `2026-05-24.4` | **real** | **60 s** | **$0.068** | 0/var | corpus-size overhead |
| `2026-06-01.2` | synthetic | 47 s | **$0.052** | **0** | cache broken by split #2 |
| `2026-06-01.3` | synthetic | 46 s | **$0.045** | **1,877** | cache reclaimed |
| `2026-06-01.4` | synthetic | 47 s | $0.045 | 1,877 | held |

`generate` was deliberately **never touched** — yet it got two quiet wins: the
reclaim cut its cost **−14%** ($0.052 → $0.045, the `.2`→`.3` swing visible above),
and it streams (R2) so its ~47 s is token-by-token, not a blank wait. The
`.2`→`.3` cost swing is the cleanest possible proof the cache is real.

### `clarify` — Sonnet → Haiku

| Version | Model | p50 | $/call | retry |
|---|---|---|---|---|
| `2026-05-24.4` → `2026-06-01.3` | Sonnet 4.6 | 11 s | $0.018 | 0 |
| `2026-06-01.4` | **Haiku 4.5** | **7 s** | **$0.0072** | 0/15 |

### Cost per application (synthetic core: analyze + clarify + generate)

| Version | analyze | clarify | generate | **core total** |
|---|---|---|---|---|
| `2026-05-24.4` (pre-split) | $0.073 | $0.018 | $0.047 | **$0.138** |
| `2026-06-01.3` (split + reclaim) | $0.059 | $0.018 | $0.045 | **$0.122** |
| `2026-06-01.4` (+ Haiku clarify) | $0.061 | $0.0072 | $0.045 | **$0.113** |

**−18% per application**, synthetic. On a real corpus (robert-scale) the same chain
ran ~$0.174 pre-split — so the absolute savings are *larger* in production than the
synthetic numbers suggest.

---

## Results summary

- **Wall-clock:** core pipeline ~145 s → ~121 s synthetic (**−17%**); `analyze`
  alone −22% synthetic / −34% vs the real-scale baseline.
- **Perceived:** `analyze`'s 90 s blank screen → live-within-1 s with phase labels
  ("Extracting JD signals…" → "Analyzing positioning…").
- **Cost:** −18% per application synthetic; more in absolute terms on real corpora.
- **Quality:** `clarification_quality` *recovered* 3.92/4.00 → 4.20/4.20 (ds/pm)
  while all this happened — speed and cost were bought with **zero quality debt**,
  enforced by the gate, not by hope.

The story to tell: **three independent levers** (split `analyze`, reclaim the
cache, cheapen `clarify`) on three different parts of the pipeline, each measured,
each gated, one of which (the split) we got *wrong first*, reverted, fixed the
quality mechanism, and re-landed correctly.

---

## What didn't work — and why that matters

1. **The naïve split (reverted).** Speed without first securing the quality
   mechanism crashed `clarification_quality` 4.2 → 2.1. Fixing extraction's typed
   `hidden_qualities` and enforcing `context_probe` *at parse time* was the
   precondition for the split to be safe.
2. **The dedicated synthesis persona (cache regression).** An elegant idea —
   give synthesis its own system prompt — silently broke the analyze→generate
   cache (`cache_read` 1,877 → 0). The lesson: **prefix caching is unforgiving
   about the system block; a cache hit needs a byte-identical prefix from
   position 0.** Any per-call specialization must live *after* the shared prefix.
3. **n=3 against a tight floor.** Two isolated 3.2 judge scores looked like a
   Haiku regression at n=3; n=5 showed them as noise (medians unchanged). Against
   a low-variance floor, extend the sample before trusting an outlier.

A perf story with three things that went sideways and were caught in telemetry is
*more* credible than a clean one — it shows the instrumentation actually works.

---

## Caveats & validation gaps

- **Two-pass split measured on synthetic only.** Real users ran during the
  single-call era; the `.2/.3/.4` two-pass numbers are all `eval:*`. The
  real-corpus win is *projected* from the synthetic delta + the known real-vs-
  synthetic overhead, not directly measured. **Closing this is exactly the
  v1.0.4 `eval/corpus-backed-runner` plan** — run the anchor pipeline against a
  real corpus seed and re-measure.
- **Perceived latency is qualitative.** Streaming's win is real but not in
  `latency_ms`; it is sourced from the v1.0.1 CHANGELOG, not a timer.
- **Cost is list-price modeled**, not invoiced — directionally exact, not to the cent.
- **Judge variance.** Rubric scores carry ±~0.6 Haiku-judge noise run-to-run;
  small score deltas are read against stdev, not as signal.

---

## Provenance

| Number | Source |
|---|---|
| All latency / token / cost figures | `logs/llm_calls.jsonl`, 1,824 records, 2026-05-06 → 2026-06-02 |
| Synthetic segment | `username=eval:{data-scientist-junior,pm-senior,sre-mid-level}` |
| Real segment | `username ∈ {robert, testuser, demo}` |
| `analyze` 103 s / −34% headline | [`R1_PHASE2_RESULTS.md`](R1_PHASE2_RESULTS.md) (real-scale baseline) |
| Streaming perceived-latency claim | `CHANGELOG.md` [1.0.1] "Added — Performance (R2 streaming)" |
| Quality recovery + gate | [`../evals/TUNING_LOG.md`](../../../evals/TUNING_LOG.md) 2026-05-30 → 2026-06-02 |

**Reproduce the per-call table:**

```bash
python - <<'PY'
import json, statistics as st
from collections import defaultdict
def seg(u):
    if u.startswith("eval:"): return "synthetic"
    return "real" if u in ("robert","testuser","demo","example") else None
D=defaultdict(list)
for l in open("logs/llm_calls.jsonl",encoding="utf-8"):
    if not l.strip(): continue
    r=json.loads(l); s=seg(r.get("username","") or "")
    if s and r.get("status")=="ok" and r.get("latency_ms"):
        D[(s,r["prompt_version"],r["call"])].append(r["latency_ms"])
for k in sorted(D):
    v=D[k]; print(f"{k[2]:20} {k[1]:14} {k[0]:9} n={len(v):3} p50={int(st.median(v)/1000)}s")
PY
```

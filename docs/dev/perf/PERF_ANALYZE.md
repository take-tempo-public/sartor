# Analyze-step latency — audit + recommendations

> **Purpose:** snapshot of where `analyze()` time goes today and what
> could meaningfully reduce it. Sized to inform a decision; not a
> design doc.
> **Audience:** humans deciding whether to spend an iteration on
> analyze latency before v1.0.0; LLMs proposing a faster-path patch.
> **Authoritative for:** the empirical numbers below. Implementation
> recommendations are *proposals*, not decisions.

## TL;DR

Across the last 83 successful `analyze` calls in `logs/llm_calls.jsonl`:

| Call kind             |  N  | p50    | p90    | max     | model     | median tokens (in / cache_read / out) |
|-----------------------|-----|--------|--------|---------|-----------|---------------------------------------|
| **analyze**           |  83 | **90 s** | **121 s** | **293 s** | Sonnet 4.6 | 486 / 5,719 / **4,471** |
| analyze_retry         |   1 | 111 s  | —      | 111 s   | Sonnet 4.6 | 545 / 3,917 / 5,649 |
| clarify               |  19 |  13 s  |  14 s  |  15 s   | Sonnet 4.6 | 3,046 / 0 / 630 |
| iterate_clarify       |   7 |  14 s  |  19 s  |  19 s   | Sonnet 4.6 | 3,972 / 0 / 665 |
| generate              |  74 |  50 s  |  92 s  | 198 s   | Sonnet 4.6 | 6,037 / 3,420 / 2,268 |
| recommend (bullets)   |  12 |   5 s  |   7 s  |   8 s   | Haiku 4.5  | 3,606 / 0 / 417 |
| recommend_summary     |   3 |   3 s  |   3 s  |   3 s   | Haiku 4.5  | 1,498 / 0 / 164 |

**Headline:** `analyze` is the slowest call on the critical path by a
wide margin. p50 = 90 s, p90 = 121 s. The next slowest user-facing call
(`generate`) is roughly half that at p50.

## Where the time goes — diagnosis

1. **Output tokens dominate, not input.** Median input is **486
   tokens** (cached + uncached). Median output is **4,471 tokens** —
   roughly 9× the input. analyze is asked to produce a large structured
   JSON: JD breakdown + ideal résumé + comparison + keyword strategy +
   ATS guidance, all in one response.

2. **Cache hit rate is poor on recent runs.** The five most recent
   analyze calls all report `cache_read_input_tokens = 0`. Looking
   further back, some calls show `cache_read = 5,719` median, but the
   recent pattern is consistent zeros. Two likely causes:
   - Cache TTL (default ~5 min) has expired between user sessions
   - The cached prefix shape is being invalidated by something that
     changes per-call (probably the supplemental block, the dated
     header, or the corpus snapshot embedded in the user message)

3. **Generation is sequential, not streamed.** The user waits for the
   full ~90 s with only the status pill changing. There's no
   token-by-token feedback so the perceived latency tracks the wall
   clock exactly.

4. **Comparable calls support the diagnosis.** `clarify` and
   `iterate_clarify` use the same model (Sonnet 4.6) but ask for
   ~600-700 output tokens and complete in 13-19 s. That's the floor
   the latency would approach if we reduced analyze's output budget.

## Recommendations, ranked

### R1. Split analyze into fast-first + deep-second  (HIGH leverage, MEDIUM effort)

The current analyze prompt asks Sonnet to return all of:

- `essential_skills`, `preferred_skills`, `industry_keywords`
- `ideal_resume_summary` (paragraph)
- `comparison` (paragraph)
- `keyword_strategy` (paragraph)
- `ats_warnings` (list)
- `role_family`, `seniority`, `domain`

A fast first pass on **Haiku 4.5** that returns only the structured
fields (`essential_skills`, `preferred_skills`, `industry_keywords`,
`role_family`, `seniority`, `domain`, `ats_warnings`) would land in
**~5-8 s** based on the Haiku numbers above, unlocking Clarify
immediately.

The prose fields (`ideal_resume_summary`, `comparison`,
`keyword_strategy`) are valuable but not needed before Compose. We can
fire the deep pass in the background after the fast pass returns, or
defer it entirely until the user clicks "Continue to Clarify."

**Expected user-visible latency:** ~5-10 s to first useful screen,
vs 90 s today. **Cost:** one extra Haiku call (~$0.002).

### R2. Streaming output  (MEDIUM leverage, LOW-MEDIUM effort)

Anthropic's Messages API supports streaming via SSE. The user would see
keys + values arriving as Sonnet produces them. Doesn't reduce total
latency but cuts **perceived latency** by ~80% — the user can already
read `essential_skills` while `keyword_strategy` is still generating.

Pairs well with R1: stream the deep-second-pass too if we keep it.

**Expected change:** perceived latency 90 s → ~10-15 s to first
useful content. Total latency unchanged.

### R3. Trim the analyze schema  (LOW leverage, LOW effort)

Audit which fields downstream code actually consumes vs which are
dead weight from earlier iterations. Likely candidates for trimming:
- `comparison` (we already show ATS warnings + ideal/actual diff in UI)
- Verbose `ats_warnings` prose (we could ask for short bullets)

**Expected change:** output tokens 4,471 → maybe 3,000-3,500. Latency
proportional: ~70 s instead of 90 s. Small win, but cheap.

### R4. Restore cache hits  (MEDIUM leverage, LOW effort, RISKY)

Audit the analyze cache_control structure to find what's invalidating
the prefix. Suspects:
- The `<corpus_snapshot>` block (changes per session)
- A timestamped header in `SYSTEM_PROMPT` (would be a bug)
- Re-ordering of supplementals between calls

If we can restore consistent cache hits, recent runs that took 90 s
would drop to ~30-40 s based on the older `cache_read = 5,719`
sample.

**Caveat:** cache hits help latency but the bulk of the time is
*generation*, not prefix processing. Fixing this nets maybe 10-15 s,
not 50 s.

## Recommendation for v1.0.0

Do **R2 (streaming)** for v1.0.0. Highest perceived-latency win for
the smallest code change. Defer R1 (the analyze split) to v1.1 because
it touches the prompt + schema + frontend ordering and warrants its
own dedicated commit + eval cycle.

Skip R3 and R4 until a user complains again; the audit data shows
they're optimizations, not fixes.

## Followups to verify after any change

- Re-run the same fixture analyze 5x; record p50 / p90.
- Compare cache_read tokens before vs after.
- Compare eval scores on the analyze-related rubrics (no regression).
- Re-emit this audit doc with fresh numbers.

## Reproduce this audit

```bash
python -c "
import json, statistics
from collections import defaultdict
rows = [json.loads(l) for l in open('logs/llm_calls.jsonl','r',encoding='utf-8') if l.strip()]
by_kind = defaultdict(list)
for r in rows: by_kind[r.get('call','?')].append(r)
for k, v in sorted(by_kind.items(), key=lambda x: -len(x[1])):
    L = [r['latency_ms'] for r in v if r.get('latency_ms')]
    if not L: continue
    L.sort()
    print(f'{k:<24} N={len(L)} p50={int(statistics.median(L))}ms p90={int(L[int(len(L)*0.9)-1] if len(L)>=10 else L[-1])}ms')
"
```

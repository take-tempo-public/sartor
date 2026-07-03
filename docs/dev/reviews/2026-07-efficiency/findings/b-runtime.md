---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Area B findings — runtime performance & reliability

> Surfaces: `analyzer.py` (LLM routing, prompt assembly, caching),
> `logs/llm_calls.jsonl` telemetry, blueprints/hardening/db hotspots,
> `static/app.js` + `style.css`, alembic chain. Finders: B1 telemetry
> (data appendix below), B2 code-hotspots.
>
> Area summary (B1): 2,955 LLM calls analyzed (2026-05-06 → 2026-07-03),
> total tracked cost $35.14, error rate 0.17% (5 rows, all Sonnet). Cost is
> dominated by Sonnet 4.6 (91.3%); `analyze` ($13.15, 37.4%) and `generate`
> ($12.34, 35.1%) dominate by call kind.
> Area summary (B2): runtime code is generally well-hardened (list_applications
> N+1 fixed, lazy model2vec import, reloader-safe browser-open). Two real
> efficiency gaps (Compose N+1, undocumented cache-miss overrides); biggest
> simplification is the style.css duplicate cascade layer.

## F-run-01 — Split analyze adoption incomplete: 60% of calls bypass the two-pass optimization

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** ~$2.65/month estimated savings if the split reached all 195 analyze calls (22% documented cost reduction × 117 non-split calls).
- **Evidence:**
  - `logs/llm_calls.jsonl` (aggregated): 195 analyze calls but only 78 analyze_extraction + 78 analyze_synthesis pairings — 40% adoption; analyzer.py:1425 shows analyze() SHOULD invoke the split internally.
  - `docs/dev/perf/PERFORMANCE_HISTORY.md:197-204`: documented 22% cost reduction ($0.073 → $0.060/call); current unified analyze averages $0.0674.
- **Dedup:** runtime adoption issue in telemetry — not a test/packaging gap; not in ledger or PX-01..36.

## F-run-02 — Generate cache hits regressed on mixed prompt versions: 38% miss rate vs 100% target

- **Disposition:** WATCH · **Leverage:** P1 · **Simplification:** no
- **Metric:** 92/249 generate calls (38%) have zero cache_read tokens. Versions 2026-05-26.1/.2 and 2026-06-01.2 show 0% hit; 2026-06-01.3+ show 100% — historical mix vs live regression needs disambiguation.
- **Evidence:**
  - `logs/llm_calls.jsonl` (by prompt_version): 2026-05-26.1/.2: 0/7 hits; 2026-06-01.2: 0/9; 2026-06-01.3+: recent versions at/near 100%.
  - `docs/dev/perf/PERFORMANCE_HISTORY.md:213-226`: cache_read ≈ 1,877 tok/hit documented at 100% on 15/15 synthetic runs.
- **Dedup:** live cache-coherence anomaly, not doc drift (ledger #6 unrelated).

## F-run-03 — Analyze p95 latency ceiling breached: 25 calls > 60s, max 126s

- **Disposition:** WATCH · **Leverage:** P1 · **Simplification:** no
- **Metric:** 25/195 analyze calls (12.8%) exceed 60s; p95 = 126.2s vs the documented 67s post-split target. Real-corpus inputs run 2–4× synthetic fixture size.
- **Evidence:**
  - `logs/llm_calls.jsonl`: 2026-05-24.4 analyze rows at 86–122s; sporadic >60s calls persist on split-era versions.
  - `docs/dev/perf/PERFORMANCE_HISTORY.md:75-100`: synthetic anchor ≈2.3k input tokens vs real corpus ≈8.8k; projected real p50 ~104s.
- **Dedup:** measured latency ceiling breach — not the deferred perf-regression gate (PX-35) itself, though PX-35's gate would catch it.

## F-run-04 — Sonnet 4.6 cost skew (91.3% of spend); Haiku call kinds show zero errors

- **Disposition:** BOOST · **Leverage:** P2 · **Simplification:** no
- **Metric:** $32.08 of $35.14 on Sonnet; Haiku $2.51 (7.1%) with 0 errors across 2,118 calls; all 5 error rows are Sonnet (3 analyze, 2 generate).
- **Evidence:** `logs/llm_calls.jsonl` cost-by-model aggregation; error rows at lines 79, 241, 242, 375, 920.
- **Dedup:** operational cost-structure observation from telemetry; not a process/governance item.

## F-run-05 — Prompt-version telemetry mix: 28.3% of all calls still logged on the 2026-05-24.4 baseline

- **Disposition:** KEEP · **Leverage:** P2 · **Simplification:** no
- **Metric:** 835/2,955 calls on 2026-05-24.4 (historical cluster 05-24→05-29); latest 2026-07-01.1 at 1.6%. Eval anchoring on old baselines is good practice but can mask stale paths.
- **Evidence:** `logs/llm_calls.jsonl` Counter(prompt_version); `docs/dev/perf/PERFORMANCE_HISTORY.md:14-16`.
- **Dedup:** telemetry hygiene/version-governance observation; not ledger #4 or PX-09.

## F-run-06 — Compose route N+1: get_application_composition lazy-loads bullets/titles/tags per experience

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** O(3E+B) extra queries per Compose page load (E=experiences, B=bullets) vs the ~3 queries the already-fixed list_applications needs.
- **Evidence:**
  - `blueprints/applications.py:898-903`: Experience query with no selectinload.
  - `blueprints/applications.py:913,916,965`: per-experience `.bullets`/`.titles` + per-bullet tag_links lazy SELECTs — same anti-pattern class as the fixed list_applications N+1 (~148-162).
- **Dedup:** different route from the fixed N+1; not on ledger or PX list.

## F-run-07 — 9 of 11 system-prompt overrides pay an undocumented cache miss; AGENTS.md names only 2

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** no
- **Metric:** doc-accuracy gap across 9 call sites (EXTRACTION, PROPOSAL_CRITIQUE, RECOMMEND ×3, SUGGEST_SKILLS, PROMOTE_CLARIFICATION, AVATAR, …); practical cost likely small (Haiku-cheap, often below the 1024-token cache floor) but the AGENTS.md claim is stale.
- **Evidence:** AGENTS.md "LLM prompts" (names clarify/clarify_iteration only); `analyzer.py:1468,1626,1793,1919,2057,2906,3001,3161,3387,3606,3749,3840` (12 explicit system_prompt= call sites).
- **Dedup:** doc-accuracy gap on the cache-cost claim; not PX-14 (metric union) or the rejected PX-36 (prompt locus).

## F-run-08 — style.css carries a ~780-line duplicate "restyle" cascade layer restating 7+ selectors

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** ~780/3,789 lines (~20%) is a second definition of the same selector set (.cb-main, .cb-panel, .panel-header, .panel-body, .cb-btn, .top-tabs, .top-tab-btn); collapsing removes the later-rule-wins footgun the project memory already documents.
- **Evidence:** `static/style.css:157,170,183,210,300` (first definitions) vs `static/style.css:3019-3789` (restyle block to EOF).
- **Dedup:** memory note documents the gotcha for editors; this proposes collapsing the duplication — new prescription territory.

## F-run-09 — analyzer.py (3,874 LOC) has clean natural split seams that stay merged

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** YES
- **Metric:** response-model block (150-360), 11 prompt constants interleaved with capability functions, call/retry machinery (1081-1424); a prompts/client split would let a prompt edit load ~10-15% of the current file. WATCH not FIX: real refactor with test-churn risk.
- **Evidence:** `analyzer.py:150-360`, `analyzer.py:1081-1424`, prompt constants at 442-3778 + `_BASE_SYSTEM_PROMPTS` registry at 3852-3874.
- **Dedup:** module-size split not previously prescribed; unrelated to ledger #5/#7 axes.

## F-run-10 — Application composite index omits is_active, the third predicate of the default list query

- **Disposition:** FIX · **Leverage:** P3 · **Simplification:** no
- **Metric:** one missing index column; SQLite filters is_active post-scan on the most common list call.
- **Evidence:** `db/models.py:774` (index lacks is_active) vs `blueprints/applications.py:148-155` (default path filters candidate_id + status + is_active).
- **Dedup:** specific index gap, not the post-public migration-test ledger item.

---

## Data appendix — llm_calls.jsonl aggregation (finder B1, 2,955 rows, 2026-05-06 → 2026-07-03)

| Call | Model | Count | Mean lat (ms) | P50 | P95 | Input tok | Output tok | Cache hit % | Err | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| analyze | sonnet-4-6 | 188 | 93,713 | 90,904 | 126,254 | 137,825 | 838,704 | 4.8 | 3 | $13.00 |
| analyze_extraction | haiku-4-5 | 78 | 10,690 | 10,134 | 15,402 | 167,233 | 90,692 | 0.0 | 0 | $0.62 |
| analyze_synthesis | sonnet-4-6 | 78 | 60,769 | 59,187 | 74,575 | 96,232 | 220,037 | 0.0 | 0 | $3.59 |
| clarify (Sonnet) | sonnet-4-6 | 132 | 12,324 | 12,165 | 14,957 | 378,592 | 81,919 | 79.6 | 0 | $2.38 |
| clarify (Haiku) | haiku-4-5 | 47 | 8,391 | 7,727 | 9,948 | 175,843 | 33,439 | 0.0 | 0 | $0.34 |
| generate | sonnet-4-6 | 239 | 53,613 | 48,532 | 87,423 | 1,193,641 | 550,864 | 59.0 | 2 | $11.94 |
| extract_experiences | haiku-4-5 | 1,970 | 103 | 0 | 0 | 228,035 | 132,047 | 0.0 | 0 | $0.89 |
| recommend | haiku-4-5 | 46 | 4,867 | 4,628 | 8,075 | 203,474 | 16,998 | 0.0 | 0 | $0.29 |
| avatar_answer | haiku-4-5 | 70 | 3,375 | 2,899 | 5,950 | 194,077 | 11,341 | 0.0 | 0 | $0.25 |
| **Totals** | | **2,955** | | | | **2,675,436** | **1,974,641** | **59.0** | **5** | **$35.14** |

Cost by call kind (top 6): analyze $13.15 (37.4%) · generate $12.34 (35.1%) ·
analyze_synthesis $3.59 (10.2%) · clarify $2.72 (7.7%) · extract_experiences
$0.89 (2.5%) · analyze_extraction $0.62 (1.8%).

Provenance: `logs/llm_calls.jsonl`. Pricing: Sonnet 4.6 $3/$15 per Mtok in/out,
Haiku $1/$5, cache reads 0.1×. Cache-hit ratio = cache_read/(cache_read+cache_creation).

```toml
schema = 1
id = 6
kind = "item"
title = "PX-39 real-corpus Sonnet-5 baseline"
status = "closed"
decision_owner = "agent"
resolution = "Closed 2026-07-28 (docs/pipeline-truth-and-era4-baseline) with a different deliverable than filed: the analyze+generate split-pair metric this item planned has no subject anymore, because fix/compose-frozen-composition (merged 2026-07-06, one day into this era) retired generate() from the dominant real-corpus path. Defined a new Era 4 in PERFORMANCE_HISTORY.md instead (total LLM wall-clock+cost per application per run_id): frozen path n=13 p50=109.3s $0.2508, legacy path n=2 (86.2s/163.9s, no p50 published). Zero new spend, 128 records copied from owner's E2E clone. Also found the wizard-rail gap that lets a user reach legacy generate() by accident (filed as a new item) and the check_refinement_scope untelemetered-call gap (filed as a new item)."
refs = ["docs/dev/perf/PERFORMANCE_HISTORY.md:178-194", "RELEASE_ARC.md step 12"]
summary = "Measure real-corpus Sonnet-5 latency/cost - 72 non-eval records already exist in E2E telemetry, zero new spend."
```

Open since 2026-06-01; every prior attempt landed "labeling only" because it
ran in an isolated worktree with no `.api_key`. Unblocked 2026-07-21.

Key finding (2026-07-28, this session): the obvious approach — spend a
fresh billed `evals/runner.py` run — isn't necessary. The owner's E2E clone
already has 72 real, non-`eval:`-prefixed, `model=="claude-sonnet-5"` records
in its own `logs/llm_calls.jsonl` (2026-07-06 through 07-09 live-app usage,
already paid for). Also found: `--suite real` is currently non-functional in
this project (no `jd.txt`/`expected.json` under `evals/fixtures/real/` — see
item 16) so it couldn't have been used as originally planned anyway.

Plan: copy the relevant telemetry lines into this project's own
`logs/llm_calls.jsonl` (pure metadata, no PII), extend
`scripts/perf_baseline.py` with p95/cost/model-user filtering (currently only
has p50/p90/max, no cost, no segmentation), compute the split-pair total
(analyze+generate summed per run_id, matching Era 2's own methodology), and
fill the Era 3 row + close the Open Item in `PERFORMANCE_HISTORY.md`.

Explicitly excludes the Microsoft JD/résumé (see item 8's related note) —
owner-directed 2026-07-28: it wasn't app-generated, not a fair pipeline
comparison.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking, ready to resume immediately after this branch

### 2026-07-28 — CLOSED, docs/pipeline-truth-and-era4-baseline

Resumed as planned above, but the plan's own method (analyze+generate summed
per `run_id`, matching Era 2) turned out to have no subject: 13 of the 15 real
Sonnet-5-era application runs never call `generate()` at all — Compose-time
drafting (`draft_positioning_summary`, `draft_gap_fill_bullets`) plus the
deterministic freeze/assemble path replaced it (`fix/compose-frozen-composition`,
merged 2026-07-06). `scripts/perf_baseline.py` was NOT extended as originally
planned — its per-`call`-kind aggregation model doesn't fit the per-`run_id`
metric Era 4 actually needed; the baseline was computed directly instead (see
`PERFORMANCE_HISTORY.md`'s Era 4 section for the full reproduction snippet).
The Microsoft-JD exclusion noted above turned out to be moot — no fresh run
happened at all, so there was never a JD to include or exclude. See also item
17 (doc contradiction, now closed) and item 8 (still blocked — its evidence
path assumed a fresh paid run that this closure didn't produce).

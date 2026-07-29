```toml
schema = 1
id = 6
kind = "item"
title = "PX-39 real-corpus Sonnet-5 baseline"
status = "open"
decision_owner = "agent"
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

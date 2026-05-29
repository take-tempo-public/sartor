<!-- One-sentence summary of the change. The diff shows *what*; explain *why*. -->

## Summary

Closes #<!-- issue number, if any -->

## Layer touched

<!-- Tick the layer(s) — helps reviewers know what to focus on. -->

- [ ] Deterministic (hardening / parser / scraper / generator)
- [ ] LLM pipeline (analyzer)
- [ ] Frontend (templates / static)
- [ ] Flask routes (app.py)
- [ ] Plugin / Claude Code workflow (.claude-plugin)
- [ ] Eval harness (evals)
- [ ] Documentation / project meta

## Checklist

- [ ] `ruff check .` clean
- [ ] `mypy .` clean
- [ ] `pytest` green
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] If a Flask route now reads or writes the filesystem, it calls `_safe_username()` and `_within()`
- [ ] If `analyzer.py:SYSTEM_PROMPT` changed, `PROMPT_VERSION` was bumped in the same commit
- [ ] No real personal data committed (`evals/fixtures/real/` stays gitignored, `configs/*.config` ignored except `example.config`)
- [ ] If this changes user-visible behavior, the README is updated

## Eval evidence

> **Required** when this PR touches `analyzer.py` or any file under `evals/`.
> Delete this section for pure infra / UI / non-prompt changes.

Run **n=3 times** at the same `PROMPT_VERSION`:

```bash
python evals/runner.py --suite anchor --subset smoke   # ~$0.10, grounding only
python evals/runner.py --suite anchor                  # ~$0.50, all rubrics
```

### Results (n=3 runs, mean ± stdev)

| Fixture | ats_format | clarification_quality | grounding | keyword_coverage | tone | iteration_quality |
|---|---|---|---|---|---|---|
| data-scientist-junior | | | | | | |
| pm-senior | | | | | | |
| sre-mid-level | | | | | | |

### Deterministic metrics (mean across n=3)

| Fixture | verb_diversity | specificity_density | grounding_overlap_ratio | cost_usd/run | latency p50 ms |
|---|---|---|---|---|---|
| data-scientist-junior | | | | | |
| pm-senior | | | | | |
| sre-mid-level | | | | | |

### Gate checklist

- [ ] No (fixture × rubric) mean dropped > **0.5** vs `baseline_v1.json` — **regression > 0.5 = blocked**
- [ ] Latency p50 did not increase > **20%** vs baseline — **latency regression > 20% = blocked**
- [ ] Cost/run did not increase > **20%** vs baseline — **cost regression > 20% = blocked**
- [ ] `evals/TUNING_LOG.md` entry written (what changed, why, scores before/after)

## Test plan

<!-- How did you verify? Include commands run, fixtures used, manual gestures performed. -->

## Risk

<!-- What could go wrong, and how would you tell? -->

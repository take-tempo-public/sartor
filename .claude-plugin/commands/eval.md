---
description: Run the callback. eval harness against synthetic or real fixtures.
argument-hint: [--suite synthetic|real|all] [--subset smoke|full] [--fixture NAME]
allowed-tools:
  - Bash
---

Run `python evals/runner.py $ARGUMENTS` (defaulting to `--suite synthetic --subset smoke` if no arguments are given) and surface the results.

After the run completes:

1. Read the JSONL result file the runner printed at the end of stdout.
2. Report a one-line-per-rubric summary: `fixture × rubric → score (pass/fail)` plus the total elapsed time.
3. If any rubric scored below 4, list its `reasons` so the regression is visible. Quote the specific phrases the rubric flagged.
4. Do NOT make code changes based on the eval results. Surface the data and let the human (or `prompt-archaeologist` subagent) decide what to fix.

If the user passed `--suite real` and `evals/fixtures/real/` is empty (only contains `.gitkeep`), report that and exit — there's nothing to grade.

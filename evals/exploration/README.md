# evals/exploration/

This directory holds candidate fixtures under evaluation for promotion to the
next anchor version (`anchor-v2`).

## Promotion rule

A fixture is promoted from exploration to anchor-v2 when it has produced stable
scores (stdev ≤ 0.6) across ≥3 consecutive runs, is discriminating across ≥2
distinct PROMPT_VERSIONs, and has a documented failure mode in TUNING_LOG.md.

Until those conditions are met, fixtures here are experimental. Scores from
exploration fixtures are tracked in JSONL but do not gate merges.

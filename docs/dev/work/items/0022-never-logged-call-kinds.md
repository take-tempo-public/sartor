```toml
schema = 1
id = 22
kind = "item"
title = "recommend_skill/suggest_skill/recommend_experience_summary/draft_surgical_refinement never logged despite being called"
status = "open"
decision_owner = "agent"
refs = ["analyzer.py:3712", "analyzer.py:3935", "analyzer.py:3491", "analyzer.py:4522"]
summary = "4 call kinds have real call sites but zero logged rows ever - dead paths or an instrumentation gap, not yet known."
```

Found 2026-07-28 during the PX-39 (item 6) pipeline trace. `analyzer.py`
defines `call_kind` strings for `recommend_skill` (`analyzer.py:3712`),
`suggest_skill` (`analyzer.py:3935`), `recommend_experience_summary`
(`analyzer.py:3491`), and `draft_surgical_refinement` (`analyzer.py:4522`),
each with a real Flask route that calls it
(`recommend-skills`/`suggest-skills`/`recommend-experience-summaries`/
`draft-refinement` in `blueprints/applications.py`). None of the four appear
even once in this project's `logs/llm_calls.jsonl` (4103+ records checked
2026-07-28), unlike every other call kind in the same file.

Two explanations, not yet distinguished: (a) these routes are real but simply
never exercised by any traffic that populated this log (plausible for
`suggest-skills`, which per the trace has no auto-fire site — user-triggered
only), or (b) something prevents the call from completing/logging when these
routes ARE hit. Needs a live click-through per route to tell which.

## Updates

### 2026-07-28 — filed during docs/pipeline-truth-and-era4-baseline

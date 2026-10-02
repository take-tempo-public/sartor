```toml
schema = 1
id = 137
kind = "item"
title = "Review current Claude models and call settings for performance and cost"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement"]
refs = [
  "analyzer.py:850",
  "analyzer.py:851",
  "analyzer.py:827",
  "agents/",
]
summary = "Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?"
```

**Asked by the owner, 2026-10-01.** A short review task, not a migration.

**What to look at:**
- The LLM routing in `analyzer.py` (`SONNET_MODEL`, `HAIKU_MODEL` at `:850-851`): is each
  call kind on the cheapest model that holds its eval scores?
- Call settings: the thinking-off choice (`:827-831`), prompt caching hit rate
  (`/sartor:bench`), and output-token limits.
- The subagent model pins in `agents/*.md` (the split is explained in `CLAUDE.md`
  §"Model-pin convention").

**Done means** a short written finding with measured before/after numbers where a change is
proposed (eval scores from `evals/runner.py`, cost from `logs/llm_calls.jsonl`). Any prompt
or model change it recommends is its own eval-gated branch, with `PROMPT_VERSION`
discipline.

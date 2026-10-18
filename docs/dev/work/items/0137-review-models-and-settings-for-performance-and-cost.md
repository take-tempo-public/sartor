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

## Updates

### 2026-10-17 - overlap with item 173 (docs/model-55-eval-item)

The owner asked whether the 5.5 generation of Sonnet, Haiku and Opus has been evaluated; it has not, and
that evaluation is filed as item 173 (`docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md`).
It overlaps this item: 137 is the broad review of routing and call settings, 173 is the specific candidate
list. The session that answered the owner did not find 137 first. Whether 137 absorbs 173 is the owner's call
(recorded as 173's open question). **No review finding for this item was found in the repo by the session
that filed 173** (the item's status is still `open`; its listed branch's git history was not checked). Its `refs` are stale: the model constants are now at `analyzer.py:1042-1043` and the
thinking-off code at `analyzer.py:1573-1595`, not `:850-851` and `:827-831`.

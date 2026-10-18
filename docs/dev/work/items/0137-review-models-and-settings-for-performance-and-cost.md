```toml
schema = 1
id = 137
kind = "item"
title = "Review current Claude models and call settings for performance and cost"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "docs/model-55-eval-item"]
refs = [
  "analyzer.py:1042-1043",
  "analyzer.py:1573-1595",
  "agents/",
  "docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md",
  "docs/dev/work/items/0174-model-pricing-disagrees-with-pricing-page.md",
]
summary = "Review pinned models and call settings, now including the Claude 5.5 candidate evaluation (absorbs item 173)."
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

### 2026-10-17 - absorbs item 173 (owner decision); the 5.5 first step is done

**The owner decided "137 absorbs 173" (chat, 2026-10-17).** Item 173 is closed as absorbed. **This item's scope is now
the original review (routing per call kind, thinking-off, cache hit rate, output limits, subagent pins) plus the
Claude 5.5 candidate evaluation.** The detail is not restated here: the observed pins and hazards, the 17 proposals and the
first-step results are in `docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md` (read its `## Updates`
block dated 2026-10-17 first). The `refs` above were corrected to the current line numbers in the same edit.

**Headline results of the first step the owner authorized** (all in 173, with sources and request ids):
- All three 5.5 IDs resolve (`claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-opus-5-5`).
- **`thinking: {"type":"disabled"}` returns `400` on Sonnet 5.5** (use `between_tools`), so `analyzer.py:1594-1595` would break
  every Sonnet call if the constant alone were swapped. Haiku 5.5 accepts `disabled`.
- **`MODEL_PRICING` disagrees with the pricing page for both live pins**: filed as item 174.
- **`claude-haiku-4-5-20251001` is past its earliest retirement date** (Active, "not sooner than October 15, 2026", no
  notice listed) and is also the eval judge, so the Haiku move has a clock this item did not have when filed.
- No Haiku call on this machine's telemetry exceeded 12,506 prompt tokens (Haiku 5.5's higher tier starts at 100,000).

**Suggested order for the work that remains** (a recommendation, not a decision): (1) item 174, the pricing fix, first, because
every cost comparison depends on it; (2) decide the `thinking` policy per model (Sonnet 5.5: `between_tools`; Haiku 5.5:
`disabled` to hold behavior, or adaptive as its own eval-gated change); (3) add telemetry for thinking tokens if the A/B
should see them; (4) the candidate A/B, one swap per branch with the judge held fixed (**needs the owner's spend approval;
none is given**), at an N chosen in advance because the `data-scientist-junior` fixture is bimodal; (5) the subagent pins,
last. `analyzer.py` and `hardening.py` are C-10 gated: a consumer dossier first.

### 2026-10-17 - pricing fixed (item 174); call provenance filed (item 175), a prerequisite for any model swap

- **Item 174 is fixed** on `fix/model-pricing-rates`: `hardening.MODEL_PRICING` now carries the pricing page's rates for Sonnet 5
  (`$2 / $10`) and Haiku 4.5 (`$1 / $5`). Cost comparisons for the 5.5 candidates can start from this table. Keys for the 5.5
  models, and Haiku 5.5's prompt-length tiers (a `compute_call_cost` change), are still this item's.
- **Item 175 is filed** at the owner's instruction (2026-10-17): the call log must record the model version that answered and the
  exact settings sent (thinking, max_tokens, effort, request id, thinking tokens), for product and eval-judge calls, "so we can
  trace every decision to the model that made it and the settings for that model." Today the thinking setting is only
  inferable from `model == SONNET_MODEL`, which breaks the moment this item changes the pin. **Suggested order: 175 before any
  candidate A/B**, so the A/B rows say what ran. No spend is approved by this note.

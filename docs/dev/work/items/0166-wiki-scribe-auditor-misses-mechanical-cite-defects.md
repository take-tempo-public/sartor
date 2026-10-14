```toml
schema = 1
id = 166
kind = "item"
title = "The wiki scribe/auditor pair keeps passing defects that review then catches, including mechanically checkable ones"
status = "open"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "agents/wiki-grounding-auditor.md",
  "agents/wiki-scribe.md",
  "commands/wiki-self-update.md",
  "docs/wiki/log.md",
  "docs/wiki/SCHEMA.md",
  "tests/test_wiki_relevance_classification.py",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "No deterministic cite check exists; review, not the auditor, caught line cites, a removed cite and a false claim."
```

**Observed** (`docs/dev/diagnosis/recurrence-guardrails.md` O4). Three consecutive scoped
passes (`docs/wiki/log.md:2699`, `:2737`, `:2784`) record orchestrator review catching defects
the auditor passed, each with a "Retune signal". Both agents are pinned to `claude-haiku-4-5-20251001`
(`agents/wiki-grounding-auditor.md:4`, `agents/wiki-scribe.md:4`). `/wiki-lint` checks only
that a cited file exists; `scripts/check_doc_links.py` does not cover `docs/wiki/`.

**Owner decision (2026-10-14):** three parts. A deterministic cite check
(`scripts/wiki_cites.py`), the auditor moved to Sonnet 5, and an explicit orchestrator review
step in `commands/wiki-self-update.md`. The review step is prose and is declared
**unenforced** (C-11); semantic misses (inverted behavior, invented UI, false evidence) are
not mechanically checkable (C-0).

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

The retune rule in `commands/wiki-self-update.md:121` has fired three times running without a
response (`docs/wiki/log.md` records each); this is the response.

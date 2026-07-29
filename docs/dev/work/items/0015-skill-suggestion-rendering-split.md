```toml
schema = 1
id = 15
kind = "item"
title = "Suggested skills split mid-parenthetical into separate entries"
status = "open"
decision_owner = "agent"
refs = ["evals/fixtures/real/robert-bootstrap/improvement_brief.md"]
summary = "e.g. 'Eval Framework Design (LLM-as-judge' and 'rubric-based)' saved as two separate skill entries - a comma-split bug."
```

Found 2026-07-28 reviewing the `robert-bootstrap` fixture's annotated
skills. Multiple suggested skills are visibly broken mid-phrase: `Eval
Framework Design (LLM-as-judge` / `rubric-based)`, `Retrieval Systems
(hybrid search` / `reciprocal-rank fusion)`, `Cross-Functional Leadership
(Engineering` / `Design` / `QA)`, `Roadmap & KPI Ownership (NPS` /
`engagement` / `retention)`. Reads like a naive comma-split somewhere in
`suggest_skills`'s output parsing not accounting for commas inside
parentheticals. Not yet traced to the exact call site.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

```toml
schema = 1
id = 125
kind = "item"
title = "Merged epics 37 and 38 still read status = \"blocked\""
status = "open"
decision_owner = "user"
branches = ["feat/docs-ia-design", "feat/docs-split"]
refs = [
  "docs/dev/work/items/0037-*.md",
  "docs/dev/work/items/0038-*.md",
  "scripts/work_items.py",
]
summary = "Epics 37/38 merged (PRs #128, #148) but still blocked on the epic before them; closing needs a verified_by."
```

**Observed.** At D1 close (`docs/dev/handoffs/docs-ia-design.md`, "New this session"), the
epic files for 37 and 38 still carry `status = "blocked"` with `blocked_on` naming the epic
before each one, although both epics merged to `main`.

**Decision needed (owner):** what counts as the C-11 closure artifact for an epic. The merge
PR (`#128`, `#148`)? The final gate run? `scripts/work_items.py` refuses a `closed` status
without `verified_by` or a named `closure_exception`.

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2), carried from the D1 handoff

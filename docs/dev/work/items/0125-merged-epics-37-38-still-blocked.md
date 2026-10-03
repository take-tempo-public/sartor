```toml
schema = 1
id = 125
kind = "item"
title = "Merged epics 37 and 38 still read status = \"blocked\""
status = "closed"
decision_owner = "user"
branches = ["feat/docs-ia-design", "feat/docs-split"]
refs = [
  "docs/dev/work/items/0037-*.md",
  "docs/dev/work/items/0038-*.md",
  "scripts/work_items.py",
]
summary = "Epics 37/38 merged (PRs #128, #148) but still blocked on the epic before them; closing needs a verified_by."
resolution = "Owner decided 2026-10-02: an epic closes on its merge PR plus that PR's green CI run. Applied to epics 37, 38 and 39 the same day."
verified_by = [
  "docs/dev/work/items/0037-*.md, 0038-*.md, 0039-*.md: status closed with verified_by naming merge PR + CI run (scripts/work_items.py check enforces the field)",
]
```

**Observed.** At D1 close (`docs/dev/handoffs/docs-ia-design.md`, "New this session"), the
epic files for 37 and 38 still carry `status = "blocked"` with `blocked_on` naming the epic
before each one, although both epics merged to `main`.

**Decision needed (owner):** what counts as the C-11 closure artifact for an epic. The merge
PR (`#128`, `#148`)? The final gate run? `scripts/work_items.py` refuses a `closed` status
without `verified_by` or a named `closure_exception`.

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2), carried from the D1 handoff

### 2026-10-02 — owner decided; closed (`chore/release-v1.1.0`)

Owner decision 2026-10-02 (item 125): an epic's C-11 closure artifact is its merge PR plus that PR's green CI run. Epics 37 (#128), 38 (#148) and 39 (#150) closed on it. Retries for #128 and #148 were checked in the flake-rate store, not assumed: 0 reruns in each.

```toml
schema = 1
id = 24
kind = "item"
title = "Template-preview fidelity spike (T2) - multi-column/paging out of reach"
status = "deferred"
decision_owner = "user"
blocked_on = "not yet scheduled; needs a product-priority decision on investing in the spike before any code work starts"
refs = [
  "docs/dev/RELEASE_ARC.md:1436-1448",
]
summary = "In-app preview is single-column (python-docx limit); multi-column/paging fidelity needs a spike, never scheduled."
```

Found during the 2026-07-29 old-system-vs-board migration-gap sweep
(`fix/bootstrap-annotation-overwrite`). `RELEASE_ARC.md:1436-1448` (UX
Cohesion Epic) names this **T2**: the in-app preview
(`docx_to_persona_html.py`) extracts only typography onto the Classic
skeleton — python-docx can't represent multi-column/tables/text-boxes/shading
— so colored section bars fall back to Classic and multi-column + accurate
paging are out of reach. Explicitly called "spike-first, not a quick fix,"
cross-referenced to the roadmap's existing `spike/pagedjs-design`. Acceptance
targets already defined: colored bars, multi-column, section spacing,
accurate paging. A scoping caveat is flagged but unresolved: verify whether
the docx **download** (real template as style source) is already faithful
while only the **preview** is lossy.

Never marked landed, resolved, or migrated onto `docs/dev/work/BOARD.md`
during the old-ledger migration — it lived in `RELEASE_ARC.md`'s epic prose,
not the Carry-forward ledger that migration covered.

## Updates

### 2026-07-29 — filed during fix/bootstrap-annotation-overwrite, migration-gap sweep

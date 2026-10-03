```toml
schema = 1
id = 134
kind = "item"
title = "Diagnostics console: the Tuning smoke cost estimate contradicts the Quality smoke estimate"
status = "open"
decision_owner = "agent"
branches = ["feat/dev-docs"]
refs = [
  "dashboard/templates/dashboard.html:2346",
  "dashboard/templates/dashboard.html:2410",
  "dashboard/templates/dashboard.html:2434",
  "dashboard/templates/dashboard.html:1296",
]
summary = "Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right."
```

**Observed in source (2026-09-30, `feat/dev-docs`):**
- Quality smoke hint and confirm: `≈ $0.35–0.40 — 3 fixtures × grounding` (`dashboard.html:2346`,
  `:2352`); the `dashQuality` help says the same (`:1296`).
- Tuning smoke hint and confirm: `≈ $0.20 — two runs (baseline + candidate) × 3 fixtures ×
  grounding` (`:2410`, `:2434`). A Tuning run is two Quality-sized runs
  (`blueprints/diagnostics.py:1159` docstring: "~2× a single run").
- The full-subset figures are consistent: Quality ≈ $0.30, Tuning ≈ $0.60.

**Not verified:** which figure is right. The smoke estimate being higher than full
(`$0.35–0.40` vs `$0.30`) also appears in `AGENTS.md` "Testing and validation" and the
runner's cost table. It may be a real effect of the smoke subset or a stale number. The fix
needs a measured run cost (`evals/TUNING_LOG.md` or `/sartor:bench` over a real smoke run),
not a doc edit.

Found while writing `docs/dev/diagnostics.md` (Epic D D3). That doc doesn't restate the
figures; it points at the console's own `confirm()` dialogs.

## Updates

### 2026-09-30 — filed on `feat/dev-docs` (Epic D D3)

### 2026-10-02 — re-parented out of epic 39 (`chore/release-v1.1.0`)

Epic 39 merged as PR #150 and closed. The owner directed its open children to stand on their own under Open, rather than hold the epic open.

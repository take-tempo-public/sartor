```toml
schema = 1
id = 135
kind = "item"
title = "Copies of the close-out protocol drift from docs/dev/maintainer-lane.md: the template's step 1 and charter.md:206's step number"
status = "open"
decision_owner = "user"
epic = 39
branches = ["feat/dev-docs"]
refs = [
  "docs/dev/AGENT_HANDOFF_TEMPLATE.md:320",
  "docs/dev/maintainer-lane.md",
  "docs/governance/charter.md:206",
]
summary = "Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule."
```

**Observed (2026-09-30, `feat/dev-docs`):**
- `docs/dev/AGENT_HANDOFF_TEMPLATE.md:320` (a `<!-- verbatim -->` block) reads "1. Quality
  gate green: `ruff check .` + `mypy .` + `pytest`". The maintainer lane's step 1 is
  `python -m scripts.gate`, and `scripts/gate.py` runs six steps. The template's copy was
  already out of date before this branch; the split only made the two copies easy to compare.
- `docs/governance/charter.md:206` says "`AGENTS.md`'s close-out step 4 instruct every
  consuming session to run `verify_doc_template.py --event consumed`". That rule is step 5,
  now in `docs/dev/maintainer-lane.md` (reachable through AGENTS.md's pointer section).

**Why the owner decides:**
- Editing a verbatim template block changes what every in-flight handoff is validated
  against (`scripts/enforcement/blast_radius.py`, template entry).
- Editing the charter goes through its amendment ceremony (`charter.md` §"Amendment
  ceremony").

`feat/dev-docs` deferred both on purpose (`docs/dev/blast-radius/dev-docs.md` §Deferred).

**Candidate mechanism, not built:** a test asserting the template's verbatim close-out
block and `maintainer-lane.md` agree on each step's command. The two are hand-synced today
(`docs/dev/diagnosis/ci-wait-required-from-protection.md:98`).

## Updates

### 2026-09-30 — filed on `feat/dev-docs` (Epic D D3)

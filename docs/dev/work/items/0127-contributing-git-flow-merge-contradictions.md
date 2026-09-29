```toml
schema = 1
id = 127
kind = "item"
title = "Live docs contradict AGENTS.md: local --no-ff merge, \"latent\" CI, four-step gate"
status = "open"
decision_owner = "agent"
epic = 39
branches = ["feat/docs-ia-design", "feat/docs-split"]
refs = [
  "CONTRIBUTING.md:57",
  "agents/git-flow.md:19",
  "scripts/gate.py:72-82",
  "docs/dev/docs-ia-design.md",
]
summary = "CONTRIBUTING + git-flow subagent say local git merge --no-ff (AGENTS step 4 forbids); gate called 4 steps, runs 6."
```

**Observed** (DX audit, D1 design §"Open decisions for the owner", last bullet):
- `CONTRIBUTING.md:57` and `agents/git-flow.md:19` instruct a local `git merge --no-ff`,
  against AGENTS.md step 4's PR-only flow. The `git-flow` subagent would follow that rule if
  it were dispatched, so this one is live-harmful.
- `CONTRIBUTING.md` calls CI "latent".
- Docs describe the gate as four steps; `scripts/gate.py:72-82` runs six.

**Plan:** D3 (`feat/dev-docs`) fixes these by default. The owner may pull the `git-flow` one
into an earlier small branch. D4's enumeration-drift lint (design §5.5) is the mechanism
against the gate-step count recurring.

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2), carried from the D1 handoff

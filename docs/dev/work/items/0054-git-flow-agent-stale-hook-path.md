```toml
schema = 1
id = 54
kind = "item"
title = "agents/git-flow.md cites hooks at the retired .claude-plugin/hooks/ path"
status = "watching"
decision_owner = "agent"
refs = [
  "agents/git-flow.md",
]
summary = "Doc cites .claude-plugin/hooks/ (retired path); doubly stale now the hook dispatches via bash-dispatcher.sh."
```

Surfaced by the 2026-08-06 pre-march chain's whole-diff adversarial review
(minor finding): `agents/git-flow.md:23,34,41-43` locates `block-merge-to-main`
in `.claude-plugin/hooks/`, a path retired when hooks re-homed to root
`hooks/` (pre-dating the chain — `main` @ `55f7c1e` already reflects the
re-home, and no chain commit touched this file). After the chain's
`feat/verify-dont-assume-guard` fold, the hook additionally no longer has a
standalone `.sh` at all (it dispatches through `hooks/bash-dispatcher.sh`), so
the sentence is stale twice over. One-file doc fix; fold into the next branch
that touches the subagent catalog rather than a dedicated branch.

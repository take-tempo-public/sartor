```toml
schema = 1
id = 127
kind = "item"
title = "Live docs contradict AGENTS.md: local --no-ff merge, \"latent\" CI, four-step gate"
status = "closed"
decision_owner = "agent"
epic = 39
branches = ["feat/docs-ia-design", "feat/docs-split", "feat/dev-docs"]
refs = [
  "CONTRIBUTING.md:57",
  "agents/git-flow.md:19",
  "scripts/gate.py:72-82",
  "docs/dev/docs-ia-design.md",
]
summary = "CONTRIBUTING + git-flow subagent say local git merge --no-ff (AGENTS step 4 forbids); gate called 4 steps, runs 6."
resolution = "Fixed on feat/dev-docs (Epic D D3 dev half, 2026-09-30). CONTRIBUTING and agents/git-flow.md now say PR-only landing with a merge commit; git-flow's hook claim is narrowed to what block_merge_to_main matches (a local merge/push targeting main; gh pr merge is not hooked) and its retired .claude-plugin/hooks/ path is gone; the .githooks/README hatch example drops --no-ff and names the PR path. 'Latent' CI wording removed from CONTRIBUTING, ci.yml, ci_backstop.py, dependabot.yml, docs-deploy.yml and scorecard.yml (gh run list shows docs-deploy and scorecard running on main 2026-09-28/29). AGENTS.md, CONTRIBUTING and ci.yml now cite scripts/gate.py for the step list instead of restating it. Stated limit: the verifier is a re-runnable scan, not a gate; D4's enumeration-drift lint (docs-ia-design section 5.5) is the planned mechanism against recurrence."
verified_by = [
  "scan of live *.md/*.yml (records excluded) for the four contradiction phrases (local no-ff merge instruction, 'latent until', 'same four steps', 'four steps below'): 9 hits at f0e1b5f, 0 on feat/dev-docs; script and exclusion list in docs/dev/blast-radius/dev-docs.md C1 addendum",
]
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

### 2026-09-30 — closed on `feat/dev-docs` (Epic D D3 dev half)

See `resolution`. Consumer decisions: `docs/dev/blast-radius/dev-docs.md` rows 11-13 and 20, plus the C1 addendum.

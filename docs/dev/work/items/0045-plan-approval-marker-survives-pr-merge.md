```toml
schema = 1
id = 45
kind = "item"
title = "Plan-approval marker survives a PR-channel merge, leaving the plan gate open into the next session"
status = "open"
decision_owner = "agent"
refs = [
  "hooks/cleanup-plan-on-merge.sh",
  "hooks/check-plan-approved.sh",
  "AGENTS.md",
]
summary = "cleanup-plan-on-merge fires only on local `git merge --no-ff`; close-out moved to `gh pr merge`, so the marker survives."
```

Observed 2026-08-04 at the start of `feat/consumer-enumeration-gate`, before any
edit. Three direct observations, no inference:

1. `~/.claude/plans/.approved-C--Dev-sartor` existed (mtime 07:54) naming
   `peaceful-squishing-fountain.md` (mtime 06:16). The plan file is *older* than
   the marker, so `hooks/check-plan-approved.sh:51`'s freshness test passes and the
   gate was **open** — production code was editable in a fresh session that had
   never called `ExitPlanMode`.
2. `hooks/cleanup-plan-on-merge.sh:21-29` runs its deletion only when the Bash
   command text contains **all three** of `git merge`, `--no-ff`, and
   `Merge made by` (plus a structural check that HEAD is a merge commit).
3. `AGENTS.md`'s close-out step 4 flow is `gh pr merge <n> --merge` →
   `git checkout main && git pull --ff-only`. That text contains **none** of the
   three. PR #98 merged through exactly that channel the same day.

So the marker's documented wipe-on-merge behavior no longer happens. The design
intent — "next task starts from a clean blocked state"
(`cleanup-plan-on-merge.sh:3`) — is silently not in force.

**This is a C-10-shaped defect, which is why it was found on this branch.**
`cleanup-plan-on-merge.sh` is a *consumer* of the merge-flow contract. When the
flow changed from a local `--no-ff` merge to the PR channel, its consumers were
never enumerated, and this one was left behind. It is the standing rule's own
first independent catch.

Deliberately **not** fixed here: it needs its own `fix/*` branch and a C-7
dossier (the hypothesis above is well-evidenced but the *fix shape* is not — a
`PostToolUse` matcher on `gh pr merge` and a `SessionStart` reconciliation
against HEAD are both plausible and have different failure modes). Folding it
into a governance branch would blur two changes.

**Interim posture:** an agent must not ride a marker it did not earn. The correct
move on finding a stale approval is `EnterPlanMode` → write the plan →
`ExitPlanMode`, which is what this session did.

## Updates

### 2026-08-04 — filed during feat/consumer-enumeration-gate (found while planning)

```toml
schema = 1
id = 45
kind = "item"
title = "Plan-approval marker survives a PR-channel merge, leaving the plan gate open into the next session"
status = "open"
decision_owner = "user"
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

Filed with the three observations above, on the branch that found it.

### 2026-08-05 — third independent confirmation (`feat/ci-wait-wrapper`)

Confirmed again at session start, before any edit: `~/.claude/plans/.approved-C--Dev-sartor`
was present (mtime 2026-08-04 16:53) in a session that had never called `ExitPlanMode`, and
PR #100 had merged through `gh pr merge --merge` in between. That is now **three consecutive
sessions** finding a live stale marker, so this is the steady state rather than a one-off.

The interim posture held: the marker was **not ridden** — this session ran `EnterPlanMode` →
wrote the plan → `ExitPlanMode` and earned a fresh one. No change to the diagnosis or the
proposed fix shape; recorded only to stop the recurrence count being re-derived by the next
session that trips over it.

### 2026-08-06 — dossier written, both fix shapes characterized, **neither implemented** (`fix/plan-approval-marker-pr-merge`)

Full dossier at `docs/dev/diagnosis/plan-approval-marker-pr-merge.md`. Summary of what
changed and did not:

- **Re-verified live** (not copied) the three inherited observations against THIS session's
  own HEAD (`867cb04`): `hooks/cleanup-plan-on-merge.sh`'s three-`grep` pre-filter (lines
  21/24/27) + structural check (lines 34-41); `AGENTS.md:232`'s `gh pr merge` flow text
  containing none of the three trigger phrases; the real `~/.claude/plans/.approved-C--Dev-sartor`
  marker (READ-ONLY), confirmed to be the chain's own legitimately-earned marker (`HEAD` has
  1 parent — no merge event has occurred in this chain at all, so nothing has tried to wipe
  it) rather than a live instance of the defect.
- **New: an isolated reproduction** (throwaway HOME + throwaway git repo, dossier D2) that
  holds "HEAD is a genuine ≥2-parent merge commit" constant and TRUE in both a PR-channel-shaped
  run and a local-`--no-ff`-shaped run, varying only the Bash command text/output fed to the
  hook. Confirms the mechanism is exactly "command-text shape", not "whether a merge
  structurally happened" — the PR-channel case is not a near-miss, it is fully merge-shaped
  and still untouched by the hook.
- **Both candidate fix shapes characterized in depth, neither implemented:**
  - (a) a `PostToolUse` matcher on `gh pr merge`'s command shape closes only the sub-case of
    an agent typing that command in the same session — it structurally cannot see dependabot's
    server-side auto-merge (enabled in this repo since 2026-08-04), GitHub-UI merges, or merges
    from another terminal/session, which are not edge cases here but the dominant real channel.
  - (b) naive form ("has `main` moved since approval") fails the mandated compaction-mid-session
    test: an unrelated auto-merge landing on `main` while an agent's own unrelated plan is still
    legitimately active would disarm a legitimately-armed marker. A narrower form ("has *this
    approved branch* been merged", via a NEW additive stamp file + branch-existence/ancestor-of-
    main check) is channel-independent and, hand-traced against the compaction scenario, does not
    misfire — but it is a first-of-its-kind mechanism that can autonomously delete approval state,
    and this dossier judges that deserves an explicit owner decision before being written, not
    only before being merged.
- **Item 45 stays OPEN.** No `verified_by` artifact is claimed (none was earned — no fix
  landed). The dossier's own "Decision" section carries a staged, not-yet-built proposal for
  the owner to approve or reject on a future branch.

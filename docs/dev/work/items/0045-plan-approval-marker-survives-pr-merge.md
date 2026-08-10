```toml
schema = 1
id = 45
kind = "item"
title = "Plan-approval marker survives a PR-channel merge, leaving the plan gate open into the next session"
status = "closed"
decision_owner = "user"
resolution = "Fixed on fix/plan-approval-marker-pr-merge (2026-08-07): the owner-approved D3(b) SessionStart design was disproven before being built (ExitPlanMode fires while HEAD is still on main -- a SessionStart reconciler stamped at approval time would archive a legitimately-armed marker at the first startup/resume/compact after EVERY approval; see docs/dev/diagnosis/plan-approval-marker-pr-merge.md \"D3(b) refuted\"). Pivoted to D3(c): the reconciliation lives inside the existing check-plan-approved.sh PreToolUse blocker, with the stamp written late (on the first production edit after approval, when require-feature-branch guarantees HEAD is a real feature branch) rather than at approval time. Channel-independent by construction (local merge, gh pr merge, GitHub UI, dependabot auto-merge all look identical: branch gone, or its tip is now an ancestor of main but wasn't already an ancestor of the main-tip recorded at stamp time). No new hook file, no .claude/settings.json change, no tests/test_governance_hooks_gate.py edit. Owner directive (archive, never delete) implemented via a new shared hooks/lib/retire-approved-plan.sh, sourced by both check-plan-approved.sh and cleanup-plan-on-merge.sh (which switched from rm -f to the same archive path). REOPENED same day (fix/plan-approval-branch-switch-gap): the D3(c) reconciliation ran the late-bind (stamp-overwrite) block BEFORE reconciling whatever was previously stamped, so switching straight from an already-merged branch to a brand-new one -- the ordinary \"finish task, start the next one\" flow, and the ONLY shape require-feature-branch actually allows -- silently inherited the stale approval with no fresh ExitPlanMode. This is the same original symptom, not a new defect class: item 45's own committed test only ever exercised same-branch-continuation and HEAD==main shapes, never a branch switch. Root-caused live (docs/dev/diagnosis/plan-approval-branch-switch-gap.md), including a real-world instance on this session's own real marker, not just the throwaway repro. Fixed by reordering the two blocks so the previously-stamped branch is reconciled -- and archived + exit 2 if warranted -- before it can be overwritten; a candidate belt-and-suspenders addition (force reconciliation on every branch switch regardless of the mtime pre-filter) was tried and dropped after empirically confirming the existing mtime conditions already catch the real case, keeping the fix minimal. RECLOSED same session with the new regression test added to verified_by."
guardrail = "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_new_branch_after_merge_requires_fresh_approval pins the exact transition (branch merges, then a DIFFERENT brand-new branch is checked out and edited) that let this recur once already inside the very fix meant to close it -- any future reordering that reintroduces stamp-overwrite-before-reconcile goes red rather than shipping plausible-but-wrong again."
verified_by = [
  "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_pr_channel_merge_blocks_the_next_edit",
  "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_deleted_branch_blocks_the_next_edit",
  "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_branch_with_no_commits_survives_unrelated_main_movement",
  "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_stamp_is_late_bound_on_the_first_production_edit",
  "tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::test_new_branch_after_merge_requires_fresh_approval",
  "tests/test_plan_approval_scoping.py::TestArchiveAndReceipt::test_cleanup_on_merge_archives_instead_of_deleting",
  "tests/test_plan_approval_scoping.py::TestEfficiency::test_no_git_subprocess_when_main_has_not_moved",
]
refs = [
  "hooks/cleanup-plan-on-merge.sh",
  "hooks/check-plan-approved.sh",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/diagnosis/plan-approval-marker-pr-merge.md",
  "docs/dev/diagnosis/plan-approval-branch-switch-gap.md",
  "AGENTS.md",
]
summary = "Fixed, reopened same day for an uncovered branch-switch transition, refixed: reconcile old stamp before overwrite."
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

### 2026-08-07 — CLOSED (`fix/plan-approval-marker-pr-merge`, second occupancy of this branch name)

The prior session's staged D3(b) design (SessionStart reconciler, approval-time stamp) was
**disproven before being built**, verified directly against this repo's own artifacts:
`.approved-C--Dev-sartor`'s mtime (2026-08-05 20:06:58 -0700) is the write ExitPlanMode
performed, and `git reflog` shows the feature branch wasn't created until 3m42s later — so
`ExitPlanMode` fires while HEAD is on `main`, contradicting the dossier's own hand-trace
premise ("approve on `fix/foo`"). An approval-time stamp would have recorded `branch=main,
sha=<main's own tip>`, which is trivially an ancestor of `main` forever — the reconciler
would archive a legitimately-armed marker at the first `startup/resume/compact` after every
single approval. Full refutation: `docs/dev/diagnosis/plan-approval-marker-pr-merge.md`
"D3(b) refuted".

Owner approved a pivot to D3(c): the same ancestry idea, same archive-not-delete directive,
moved into the existing `check-plan-approved.sh` PreToolUse blocker with a **late-bound**
stamp (written on the first production edit after approval, not at approval time). No new
hook file, no `.claude/settings.json` change, no `tests/test_governance_hooks_gate.py` edit.
18 new regression tests in `tests/test_plan_approval_scoping.py`, all confirmed RED against
the pre-fix hooks before the fix landed (`git stash` + rerun), then GREEN after. Full gate:
`ruff check` / `ruff format --check` / `mypy` / `pytest -m "not ux"` (chunked into 8 batches
after this machine's own background runner exhibited repeated kills unrelated to this
branch's code) all green, 2375 passed / 1 skipped / 0 failed / 0 reruns. Filed a
carry-forward item (55) for the `plan-archived` ledger-event vocabulary drift this fix's
receipt mechanism introduces, rather than silently absorbing it (C-11/C-12). **Two further
genuine defects found and fixed while building the mechanism** (both root-caused by direct
reproduction, not guessed at — full evidence in the dossier's own `## Falsified` section): a
`$HOME`-derived path handed to `python3` as an argv string is silently wrong on
Windows/Git-Bash (fixed via `cygpath -m` translation), and the archive directory name
embedded the full project path, which for a sufficiently long real path pushes past
Windows' 260-char `MAX_PATH` (fixed by hashing the project key to 12 hex chars for the
directory name).

### 2026-08-07 — REOPENED and REFIXED, same day (`fix/plan-approval-branch-switch-gap`)

Found while scoping an unrelated multi-branch orchestration design, not while chasing this
item: `hooks/check-plan-approved.sh`'s branch-merge reconciliation (just closed above) ran
its "late-bind the stamp to `$CUR_BRANCH`" block *before* its "reconcile whatever was
previously stamped" block, so a transition straight from an already-merged branch to a
brand-new one silently overwrote the stamp before the old branch was ever checked. Two
isolated throwaway repros confirmed it (`docs/dev/diagnosis/plan-approval-branch-switch-gap.md`
O1/O2), and it then fired for real on this session's own actual marker while writing the
dossier (O5) — this session had never called `ExitPlanMode`, yet a brand-new branch's first
edit was allowed. A new regression test,
`test_new_branch_after_merge_requires_fresh_approval`, was confirmed RED against the
just-closed code (`returncode == 0` where `2` was required) before the fix, then GREEN
after reordering the two blocks. Full `tests/test_plan_approval_scoping.py` suite (26 tests,
up from 18) green, no reruns, including the pre-existing efficiency test — confirming a
candidate extra safeguard (force reconciliation on every branch switch) was unnecessary and
was dropped rather than kept "to be safe."

```toml
schema = 1
id = 56
kind = "item"
title = "Plan retirement half-completes on main: empty archive dir created, pointer files survive, stale approval stays live"
status = "watching"
decision_owner = "user"
refs = [
  "hooks/lib/retire-approved-plan.sh",
  "hooks/check-plan-approved.sh",
  "docs/dev/epic-a-chain-design-corrections.md",
  ".claude/settings.json",
]
summary = "On main the reconciler dies mid-function: empty archive dir, all three pointers survive, stale approval stays live."
```

Found on 2026-08-08 while executing the stamp-flush correction that the Epic A chain
design needed (finding 1 in
[`docs/dev/epic-a-chain-design-corrections.md`](../../epic-a-chain-design-corrections.md)),
not by a review pass. Third instance in the plan-approval reconciler class — item 45 was
already closed and reopened once.

## Observed

A `Write` attempted while on `main` created
`~/.claude/plans/archive/20260808T153444Z-142537ca4cdd` **empty**, while
`.approved-C--Dev-sartor`, `.current-C--Dev-sartor`, `.approved-branch-C--Dev-sartor` and
the referenced plan file all survived unchanged. The only block message reported was
`require-feature-branch`; no `PLAN RETIRED` line appeared.

`hooks/lib/retire-approved-plan.sh:161` removes all three pointer files unconditionally
and the function returns 0, so a completed call cannot leave them behind. Execution
therefore stopped between the `mkdir -p "$archive_dir"` on `:84` and that `rm`.

The identical `Write` **on a feature branch** retired cleanly: archive dir containing
`manifest.json` *and* the plan file, all three pointers cleared, and a `plan-archived`
ledger receipt written.

## Inferred — unproven, do not cite as cause

The harness terminates the sibling hook once one guard exits 2. The competing explanation
is the 5-second hook timeout configured in `.claude/settings.json`. **Neither was tested.**
A fix branch owes a reproduction that discriminates between them before changing anything —
the two mechanisms imply different fixes, and picking the plausible one is exactly the C-7
failure this repo has paid for repeatedly.

## Impact

Low severity, non-silent in practice: the edit *is* blocked either way, so no unapproved
work lands. The costs are (a) the stale approval survives when the operator believes it was
flushed, and (b) one empty archive dir accumulates per attempt. The Epic A chain hits this
directly, because its single-approval design depends on a clean flush happening first.

## Workaround, in effect now

Create the branch **first**, then take the flush edit on it. Written into
`docs/dev/RELEASE_ARC.md`'s Epic A amendment so the chain does not rediscover it.

## Declared gap (charter C-11 / C-12)

C-11 obliges a fail-closed mechanism on a recognized recurrence, and this qualifies. **No
mechanism was authored on the branch that found it**, deliberately: the discovering branch
was a documentation recovery, and a hook change with an unproven mechanism and no
reproduction does not belong in it. That is a real, unfilled gap — stated here rather than
left for the next reader to assume was covered. The compliant next step is its own `fix/*`
branch with a diagnosis dossier that reproduces the half-completion and discriminates
between the two candidate mechanisms above.

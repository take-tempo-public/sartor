```toml
schema = 1
id = 53
kind = "item"
title = "verify-binary-on-path false-BLOCKs on heredoc bodies containing prose quotes (quote-parity desync)"
status = "watching"
decision_owner = "agent"
refs = [
  "scripts/enforcement/guards/verify_binary_on_path.py",
  "docs/dev/handoffs/fix-plan-approval-marker-pr-merge.md",
]
summary = "Quote-parity tracker ignores heredoc semantics; prose quotes in a commit-message heredoc caused a live false-BLOCK."
```

Observed live 2026-08-06 during `fix/plan-approval-marker-pr-merge` (the same
chain that shipped the guard one branch earlier): a
`git commit -m "$(cat <<'EOF' ...)"` invocation whose heredoc body contained
ordinary prose punctuation (`holds "HEAD is a genuine...`) desynchronized
`_split_top_level`'s quote-parity tracking, which then treated a later prose
word as an unresolved top-level command segment and blocked the whole commit
with `'genuine' not found on PATH`.

Worked around in-session per the guard's own documented false-positive
allowance (rephrase: `git commit -F <file>`), which is exactly the fail-open
posture the block message describes — so the defect costs an inconvenience,
not a wedge. Still a real defect: the guard's design contract is "when parsing
is uncertain, ALLOW", and a heredoc body is a case where its parser is
*confidently wrong* rather than uncertain. Candidate fix: detect a `<<`
heredoc operator in the segment and fail open on the entire remainder (the
existing docstring already lists heredocs as a fail-open family — the tracker
just doesn't implement that exclusion on this path). Small, testable against
the exact observed command shape; out of scope for the chain that found it.

## Updates

### 2026-10-22 -- second recorded recurrence (feat/eval-dataset-format, item 183)

A commit run as `git commit -m "$(cat <<'EOF' ... EOF)"` was BLOCKED with the whole message reported as a binary "not found on PATH". The message contained a single apostrophe ("the persona's own resume"). Same class as the first observation: the quote-parity tracker reads prose inside the heredoc body as shell. The guard's own text says to proceed on a false positive; the clean way through, used for every later commit on that branch, was to write the message with the Write tool and commit with `git commit -F <file>`. The candidate fix above (fail open on the remainder after a `<<` heredoc operator) is unchanged and still unbuilt.

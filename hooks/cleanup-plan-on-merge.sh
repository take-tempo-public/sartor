#!/usr/bin/env bash
# PostToolUse hook on Bash: after a successful git merge --no-ff, retire THIS
# project's plan file and approval state (archive, never delete — owner
# directive, item 45 / D3(c), 2026-08-07: preserve decision provenance) so
# its next task starts from a clean blocked state. Scoped per-project via
# CLAUDE_PROJECT_DIR (F-gov-02/F-gov-03): a merge in one project/worktree
# must never touch another concurrent session's already-approved plan.
#
# Shares hooks/lib/retire-approved-plan.sh with check-plan-approved.sh's own
# branch-merge reconciler, so a plan retired via either channel — a local
# `--no-ff` merge (this script) or a PR-channel/auto/UI merge caught on the
# next edit (the other script) — is retired identically. Do NOT re-add a
# `gh pr merge` text pattern here: the reconciler in check-plan-approved.sh
# already covers that case (and every other channel) independent of command
# text, which is why this script's own pre-filter stays narrowly scoped to
# the one shape it has always covered.
#
# The three grep checks below are a cheap PRE-FILTER only (avoids spawning git
# on every single Bash call) — they are NOT the safety check, because a Bash
# command whose TEXT merely mentions these phrases (e.g. echoed test data) can
# satisfy all three without any real merge happening. Proven live on
# fix/plan-approval-hook-scope, 2026-07-17: a diagnostic command that
# constructed JSON containing "Merge made by" as test data tripped this exact
# check for real and deleted a just-approved plan. The actual deletion is now
# gated on a structural check: HEAD in this project's own repo must currently
# BE a merge commit.

INPUT=$(cat)

# Cheap pre-filter — not the safety check; see comment above.
if ! echo "$INPUT" | grep -q 'git merge'; then
  exit 0
fi
if ! echo "$INPUT" | grep -q -- '--no-ff'; then
  exit 0
fi
if ! echo "$INPUT" | grep -q 'Merge made by'; then
  exit 0
fi

# Structural check: HEAD must actually BE a merge commit right now, in THIS
# project's own repo. A command whose text merely mentions the phrases above
# cannot fake this.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi
PARENT_COUNT=$(git -C "$PROJECT_DIR" log -1 --pretty=%P 2>/dev/null | wc -w)
if [ "${PARENT_COUNT:-0}" -lt 2 ]; then
  exit 0
fi

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLANS_DIR="$HOME/.claude/plans"
PROJECT_KEY=$(echo -n "${CLAUDE_PROJECT_DIR:-unknown}" | tr -c 'A-Za-z0-9' '-')

# Retire only THIS project's recorded plan file(s) — the shared helper reads
# the pointers, archives whatever they point at, and removes the pointer
# files themselves. Never touches another project's files.
LIB="$HOOKS_DIR/lib/retire-approved-plan.sh"
if [ -f "$LIB" ]; then
  # shellcheck source=hooks/lib/retire-approved-plan.sh
  . "$LIB"
  retire_approved_plan "$PLANS_DIR" "$PROJECT_KEY" "$PROJECT_DIR"
fi

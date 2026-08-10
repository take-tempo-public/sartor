#!/usr/bin/env bash
# PreToolUse hook: blocks Edit/Write unless an approval marker exists.
# Exempts writes to the plans directory (plan file must always be writable).
# Marker is created by ExitPlanMode; retired once the approved branch's own
# work has actually merged (any channel) or the branch is gone — see the
# "branch-merge reconciliation" block below (item 45 / D3(c), 2026-08-07;
# supersedes relying on `cleanup-plan-on-merge.sh` alone, which only ever
# caught a local `git merge --no-ff`).
# Scoped per-project via CLAUDE_PROJECT_DIR (F-gov-02/F-gov-03): the marker and the
# "which plan file is this" pointer both live under a per-project key, so a
# concurrent session in a different project/worktree can never trip or satisfy
# this project's gate.

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLANS_DIR="$HOME/.claude/plans"
PROJECT_KEY=$(echo -n "${CLAUDE_PROJECT_DIR:-unknown}" | tr -c 'A-Za-z0-9' '-')
MARKER="$PLANS_DIR/.approved-$PROJECT_KEY"
CURRENT="$PLANS_DIR/.current-$PROJECT_KEY"
STAMP="$PLANS_DIR/.approved-branch-$PROJECT_KEY"

# Read stdin once
INPUT=$(cat)

# Exempt the plans directory — plan file must always be writable in plan mode
FILE_PATH=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" <<< "$INPUT" 2>/dev/null || echo "")

# Normalize path separators (Windows uses backslashes) then check
NORM_PATH=$(echo "$FILE_PATH" | tr '\\' '/')
if echo "$NORM_PATH" | grep -qF ".claude/plans"; then
  # Track which plan file THIS project is actively writing, so
  # mark-plan-approved.sh can record exactly the right file at approval time
  # without ever scanning the whole shared ~/.claude/plans directory.
  case "$NORM_PATH" in
    *.md) echo "$NORM_PATH" > "$CURRENT" ;;
  esac
  exit 0
fi

# No marker → not approved for this project
if [ ! -f "$MARKER" ]; then
  echo "NO EDIT APPROVAL: No approved plan found for this project." >&2
  echo "Write a plan and call ExitPlanMode." >&2
  exit 2
fi

# Marker exists — check only the specific plan file it was approved for (never
# the newest *.md across the whole shared directory, which is what let a
# different project's plan file trip this project's gate).
APPROVED_PLAN=$(cat "$MARKER" 2>/dev/null)
if [ -n "$APPROVED_PLAN" ] && [ -f "$APPROVED_PLAN" ] && [ "$APPROVED_PLAN" -nt "$MARKER" ]; then
  echo "PLAN NOT APPROVED: '$(basename "$APPROVED_PLAN")' is newer than approval marker." >&2
  echo "Call ExitPlanMode and get user approval before editing files." >&2
  exit 2
fi

# --- Branch-merge reconciliation (item 45 / D3(c), 2026-08-07) -----------
# ExitPlanMode fires while HEAD is still on main/master (the feature branch
# is created AFTER approval, per AGENTS.md "Branch before code changes"), so
# the stamp below is written HERE — late-bound, on the first production edit
# — never at approval time. Stamping at approval time was the original
# staged design (D3(b), a SessionStart reconciler) and it is disproven: see
# docs/dev/diagnosis/plan-approval-marker-pr-merge.md "D3(b) refuted".
#
# Cost discipline: everything through the NEED_CHECK decision below uses
# bash builtins + direct file reads only — no `git` subprocess — so a
# steady state (branch unchanged, main unmoved) costs nothing extra beyond
# what this hook already paid. `git` is invoked only once there is actually
# something to reconcile.
#
# Known limit (C-0, stated not silently absorbed): this mechanism only
# covers an ordinary checkout (`.git` is a directory). A linked worktree
# (`.git` is a file) is skipped entirely — no worse than before this branch,
# since the ORIGINAL script had no merge-detection here for any project
# shape, but also no better. Not exercised by this branch's test suite.

# Read the SHA a loose or packed ref currently points to, without calling
# git. Prints nothing (and returns nonzero) if the ref cannot be resolved.
_ref_sha() {
  local gitdir="$1" ref="$2" loose sha
  loose="$gitdir/refs/heads/$ref"
  if [ -f "$loose" ]; then
    IFS= read -r sha < "$loose" 2>/dev/null
    if [ -n "$sha" ]; then
      printf '%s' "$sha"
      return 0
    fi
  fi
  if [ -f "$gitdir/packed-refs" ]; then
    awk -v r="refs/heads/$ref" '$2==r{print $1; found=1} END{exit !found}' "$gitdir/packed-refs" 2>/dev/null
    return $?
  fi
  return 1
}

# Current branch name read from `.git/HEAD` directly (bash builtin `read`,
# no subprocess). Empty output = detached HEAD or unreadable.
_current_branch() {
  local gitdir="$1" head_line
  IFS= read -r head_line < "$gitdir/HEAD" 2>/dev/null || return 1
  case "$head_line" in
    "ref: refs/heads/"*) printf '%s' "${head_line#ref: refs/heads/}"; return 0 ;;
    *) return 1 ;;
  esac
}

# Load STAMPED_BRANCH / STAMPED_BASE from $1 (the stamp file path). Always
# resets both first so a missing/unreadable file leaves them empty.
_read_stamp() {
  STAMPED_BRANCH=""
  STAMPED_BASE=""
  [ -f "$1" ] || return 1
  local l1="" l2=""
  { IFS= read -r l1; IFS= read -r l2; } < "$1" 2>/dev/null
  STAMPED_BRANCH="${l1#branch=}"
  STAMPED_BASE="${l2#base=}"
}

# True (exit 0) iff the branch named $3 should be archived: it no longer
# exists, or it is now an ancestor of $2 (main/master) but was NOT already
# an ancestor of $4 (the main-tip recorded at stamp time) — the second half
# is what stops a freshly-created, zero-commit branch from false-firing the
# instant main moves for an unrelated reason. Fails open (returns 1, "leave
# it alone") on anything ambiguous: no `git` on PATH, an unexpected exit
# code from git, or an unresolvable ref.
_should_archive() {
  local project_dir="$1" main_ref="$2" branch="$3" base="$4"
  [ -n "$branch" ] || return 1
  command -v git >/dev/null 2>&1 || return 1

  git -C "$project_dir" show-ref --verify --quiet "refs/heads/$branch"
  local rc=$?
  if [ "$rc" -eq 1 ]; then
    return 0 # branch is gone -- safe direction: re-earn approval
  elif [ "$rc" -ne 0 ]; then
    return 1 # unexpected error -- fail open
  fi

  local tip
  tip=$(git -C "$project_dir" rev-parse "refs/heads/$branch" 2>/dev/null)
  [ -n "$tip" ] && [ -n "$main_ref" ] || return 1

  git -C "$project_dir" merge-base --is-ancestor "$tip" "refs/heads/$main_ref" 2>/dev/null
  [ $? -eq 0 ] || return 1 # not confirmed merged -- fail open

  if [ -z "$base" ]; then
    return 0 # merged, no base recorded (malformed stamp) -- conservative default
  fi
  git -C "$project_dir" merge-base --is-ancestor "$tip" "$base" 2>/dev/null
  if [ $? -eq 1 ]; then
    return 0 # merged AND moved past the fork point -- archive
  fi
  return 1 # still exactly at the fork point, or unknown -- fail open
}

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -n "$PROJECT_DIR" ] && [ -d "$PROJECT_DIR/.git" ]; then
  GITDIR="$PROJECT_DIR/.git"
  MAIN_REF=""
  if [ -n "$(_ref_sha "$GITDIR" main)" ]; then
    MAIN_REF="main"
  elif [ -n "$(_ref_sha "$GITDIR" master)" ]; then
    MAIN_REF="master"
  fi

  if [ -n "$MAIN_REF" ]; then
    CUR_BRANCH=$(_current_branch "$GITDIR") || CUR_BRANCH=""

    # Reconcile whatever is CURRENTLY stamped FIRST, before anything below can
    # overwrite it — independent of CUR_BRANCH, because the stamped branch may
    # have merged and been left (e.g. `git checkout main`, or a brand-new
    # branch checked out for the NEXT task) within the same session, and that
    # must still reconcile on the next edit even though HEAD is no longer on
    # it. Item 45 / D3(c)'s original ordering did this AFTER the re-stamp
    # block below, which meant switching straight from an already-merged
    # branch to a brand-new one silently overwrote the stamp before the old
    # branch was ever checked — the ordinary "finish task, start the next
    # one" flow inherited a stale approval with no fresh ExitPlanMode. Fixed
    # here (2026-08-07); full evidence:
    # docs/dev/diagnosis/plan-approval-branch-switch-gap.md.
    _read_stamp "$STAMP"
    if [ -n "$STAMPED_BRANCH" ]; then
      BRANCH_REF_FILE="$GITDIR/refs/heads/$STAMPED_BRANCH"
      NEED_CHECK=0
      if [ ! -e "$BRANCH_REF_FILE" ]; then
        NEED_CHECK=1
      elif [ -f "$GITDIR/refs/heads/main" ] && [ "$GITDIR/refs/heads/main" -nt "$STAMP" ]; then
        NEED_CHECK=1
      elif [ -f "$GITDIR/refs/heads/master" ] && [ "$GITDIR/refs/heads/master" -nt "$STAMP" ]; then
        NEED_CHECK=1
      elif [ -f "$GITDIR/packed-refs" ] && [ "$GITDIR/packed-refs" -nt "$STAMP" ]; then
        NEED_CHECK=1
      elif [ "$BRANCH_REF_FILE" -nt "$STAMP" ]; then
        NEED_CHECK=1
      fi

      if [ "$NEED_CHECK" -eq 1 ]; then
        if _should_archive "$PROJECT_DIR" "$MAIN_REF" "$STAMPED_BRANCH" "$STAMPED_BASE"; then
          LIB="$HOOKS_DIR/lib/retire-approved-plan.sh"
          if [ -f "$LIB" ]; then
            # shellcheck source=hooks/lib/retire-approved-plan.sh
            . "$LIB"
            retire_approved_plan "$PLANS_DIR" "$PROJECT_KEY" "$PROJECT_DIR"
          fi
          echo "PLAN RETIRED: branch '$STAMPED_BRANCH' has already merged (or no longer exists) — its approval was archived, not deleted." >&2
          echo "Write a plan and call ExitPlanMode to start the next task." >&2
          exit 2
        fi
        # Nothing to do this round -- advance the mtime baseline so the
        # cheap pre-filter above doesn't re-pay the git calls until
        # something actually changes again.
        touch "$STAMP" 2>/dev/null
      fi
    fi

    # Late-bind (or transfer) the stamp to CUR_BRANCH — only reached if the
    # PREVIOUSLY stamped branch (if any) was just reconciled above and did
    # NOT need archiving (a real `exit 2` above short-circuits before this
    # ever runs). Only while checked out on a real feature branch (never
    # main/master, never detached) — the moment require-feature-branch
    # guarantees this stamp will name the actual work, not main's own tip.
    if [ -n "$CUR_BRANCH" ] && [ "$CUR_BRANCH" != "main" ] && [ "$CUR_BRANCH" != "master" ]; then
      _read_stamp "$STAMP"
      if [ "$STAMPED_BRANCH" != "$CUR_BRANCH" ]; then
        BASE_SHA=$(_ref_sha "$GITDIR" "$MAIN_REF")
        if [ -n "$BASE_SHA" ]; then
          { echo "branch=$CUR_BRANCH"; echo "base=$BASE_SHA"; } > "$STAMP" 2>/dev/null
        fi
      fi
    fi
  fi
fi

exit 0

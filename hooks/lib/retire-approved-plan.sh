#!/usr/bin/env bash
# Shared "retire an approved plan" helper — item 45 / D3(c), 2026-08-07.
#
# Owner directive: a reconciler must never silently DELETE approval state —
# archive, plus a ledger receipt, preserving decision provenance. This file
# is the one definition of that behavior, sourced (never exec'd) by both
# hooks/check-plan-approved.sh (the branch-merge reconciler) and
# hooks/cleanup-plan-on-merge.sh (the local `--no-ff` merge witness), so a
# plan retired by either channel is retired identically.
#
# Deliberately NOT a `hooks/*.sh` entry point: it lives in `hooks/lib/`,
# which `_hook_stems()` (tests/test_governance_hooks_gate.py) globs
# non-recursively and so never sees, and it is never wired in
# `.claude/settings.json`. It IS still committed with the executable bit
# (`tests/test_evidence_gate.py::test_every_hook_script_is_executable_in_the_index`
# globs `hooks/` recursively via `git ls-files`), and
# tests/test_plan_approval_scoping.py asserts the settings.json/_hook_stems
# exemption explicitly rather than leaving it to be discovered.
#
# Never wedges a caller: every failure mode here degrades to "leave the
# pointer files in place" rather than raising — retiring a plan is a nicety
# on top of the caller's own gate decision, not itself a gate.

# Convert a bash-native path to a form the NATIVE (non-MSYS) python3.exe can
# correctly interpret, before handing it over as an argv string. On
# Windows/Git-Bash, `$HOME` (and anything built from it, e.g. `$archive_dir`)
# is auto-translated by the MSYS runtime to POSIX form (`/c/Users/...`, or
# `/tmp/...` when it falls under Git-Bash's own temp mount) — a form bash
# itself resolves correctly but a native Windows Python does not: it treats
# a leading `/c/` as a literal subdirectory of the current drive, not a
# drive reference (`Path('/c/Users/x').resolve()` -> `C:\c\Users\x`, which
# does not exist). Root-caused via direct reproduction, not inferred (see
# fix/plan-approval-marker-pr-merge's own session evidence). `cygpath -m`
# is the MSYS-shipped, correct translator (drive letter + forward slashes,
# valid for both bash and native Windows programs); falls back to the raw
# path unchanged where `cygpath` doesn't exist (real POSIX systems, where
# this translation is a no-op anyway).
_native_path() {
  if [ -n "$1" ] && command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1" 2>/dev/null || printf '%s' "$1"
  else
    printf '%s' "$1"
  fi
}

retire_approved_plan() {
  local plans_dir="$1" project_key="$2" project_dir="$3"
  local marker="$plans_dir/.approved-$project_key"
  local current="$plans_dir/.current-$project_key"
  local stamp="$plans_dir/.approved-branch-$project_key"

  # The archive directory name uses a SHORT hash of project_key, not
  # project_key itself. project_key is the ENTIRE project directory path
  # with every non-alphanumeric byte turned into `-` (see check-plan-approved.sh's
  # own PROJECT_KEY derivation) -- embedding it whole made the archive
  # directory name grow with the project path's own length, and a deeply
  # nested real-world path (or, as directly reproduced this session, a
  # nested pytest tmp_path) pushes `<archive_dir>/manifest.json` past
  # Windows' 260-char MAX_PATH: `plan.md` (7 chars) stayed just under the
  # limit while `manifest.json` (13 chars) tipped it over, which is exactly
  # why the plan moved but the manifest silently failed to write
  # (FileNotFoundError, caught and swallowed) -- confirmed via direct
  # reproduction, not inferred. 12 hex chars matches this project's own
  # fingerprint convention (docs/dev/prov/SPEC.md: sha256, truncated to 12).
  local key_hash
  if command -v sha256sum >/dev/null 2>&1; then
    key_hash=$(printf '%s' "$project_key" | sha256sum | cut -c1-12)
  else
    key_hash="$project_key" # extremely unlikely fallback; a real POSIX box without sha256sum
  fi

  local ts archive_id archive_dir
  ts=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null) || ts="unknown-ts"
  archive_id="${ts}-${key_hash}"
  archive_dir="$plans_dir/archive/$archive_id"

  local approved_plan="" current_plan="" archived_basename=""
  [ -f "$marker" ] && approved_plan=$(cat "$marker" 2>/dev/null)
  [ -f "$current" ] && current_plan=$(cat "$current" 2>/dev/null)

  # mv (never cp/rm) — vacates the live path while preserving the content,
  # which is what keeps a plan file "archived" rather than "deleted".
  if [ -n "$approved_plan" ] && [ -f "$approved_plan" ]; then
    mkdir -p "$archive_dir" 2>/dev/null && mv -f "$approved_plan" "$archive_dir/" 2>/dev/null
    archived_basename=$(basename "$approved_plan")
  fi
  if [ -n "$current_plan" ] && [ "$current_plan" != "$approved_plan" ] && [ -f "$current_plan" ]; then
    mkdir -p "$archive_dir" 2>/dev/null && mv -f "$current_plan" "$archive_dir/" 2>/dev/null
  fi

  local branch=""
  if [ -n "$project_dir" ] && command -v git >/dev/null 2>&1; then
    branch=$(git -C "$project_dir" rev-parse --abbrev-ref HEAD 2>/dev/null) || branch=""
  fi

  # One python3 call writes both the local manifest (untracked, beside the
  # archived plan — may contain the absolute path, since it never leaves
  # $HOME) and the tracked ledger receipt (basename only — this repo is
  # public, and docs/dev/ledger/ is git-tracked). Byte-correct JSON via
  # python, matching this repo's own convention (see wiki-freshness-reminder.sh),
  # rather than printf-escaping paths that may contain quotes/backslashes.
  # Every path handed to python3 goes through _native_path first — see that
  # function's own comment for why (bash and native python3.exe disagree on
  # `$HOME`-derived path syntax on Windows).
  python3 - "$(_native_path "$archive_dir")" "$(_native_path "$project_dir")" \
    "${CLAUDE_CODE_SESSION_ID:-}" "$branch" "$archive_id" \
    "$(_native_path "$approved_plan")" "$(_native_path "$current_plan")" "$archived_basename" <<'PY' 2>/dev/null
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

archive_dir, project_dir, session, branch, archive_id, approved_plan, current_plan, basename = sys.argv[1:9]
ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

# Local manifest — untracked (lives under $HOME/.claude/plans/archive/), so
# the absolute plan path is fine here; it never reaches the tracked repo.
if archive_dir and Path(archive_dir).is_dir():
    manifest = {
        "approved_plan": approved_plan,
        "current_plan": current_plan,
        "project_dir": project_dir,
        "archive_id": archive_id,
        "archived_at": ts,
    }
    try:
        (Path(archive_dir) / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass

# Tracked ledger receipt — basename only, never the absolute path.
# Event name `plan-archived` follows the `compacted` precedent
# (scripts/enforcement/adapters/claude_context_hook.py): a new event added by
# the emitting module without amending docs/dev/prov/SPEC.md, because SPEC.md
# is itself a C-10 gated surface and amending it for a bugfix branch would
# drag require-consumer-enumeration across every ledger consumer. The
# vocabulary drift this creates is filed as a carry-forward ledger row, not
# silently absorbed (C-11/C-12).
if project_dir and session and basename:
    ledger_dir = Path(project_dir) / "docs" / "dev" / "ledger"
    try:
        ledger_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "event": "plan-archived",
            "session": session,
            "branch": branch or "unknown",
            "archive_id": archive_id,
            "plan": basename,
            "ts": ts,
        }
        # newline="\n": text-mode append otherwise translates \n to the platform
        # ending, putting CR bytes in the working tree that .gitattributes
        # (checkout-time only) cannot prevent — the class
        # tests/test_verify_doc_template.py::TestLedgerWorkingTreeBytes fails
        # closed on. This writer was missed by the fix that covered the two
        # Python writers; observed live 2026-08-14 (run-6 preflight).
        with (ledger_dir / f"{session}.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # never wedge the caller's gate over a bookkeeping write
PY

  # The pointer files' own content is preserved above (manifest + receipt) —
  # what they point AT is what was archived, not deleted.
  rm -f "$marker" "$current" "$stamp" 2>/dev/null
  return 0
}

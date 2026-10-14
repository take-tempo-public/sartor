"""Where a hook-written provenance receipt is appended (item 165).

Two hooks append receipts to the session's own ledger shard on their own, with no human in
the loop: the PreCompact hook (`compacted`, `adapters/claude_context_hook.py`) and the plan
gate (`plan-archived`, `plan_gate.py`). The tracked shard `docs/dev/ledger/<session>.jsonl` is
the right home on a feature branch, where the row rides the branch's commits. On `main` it is
the wrong one: the append leaves a tracked file modified on the trunk checkout after a
close-out, and the next session must fold it into its first commit (`71d0d17`, `7bcbc3a`,
`2097a40`; `docs/dev/diagnosis/recurrence-guardrails.md` O3).

So a receipt written while HEAD is on trunk goes to an untracked **spool**,
`.claude/state/ledger/<session>.jsonl`. `.gitignore` covers `.claude/*`, and
`tests/test_ledger_spool.py` fails if that stops being true. Readers that count receipts
(`compaction_count`) read both locations.

**What trunk means here:** `main`, `master`, or `HEAD` (what `git rev-parse --abbrev-ref`
prints for a detached HEAD). **Declared limits (C-0):**

* A branch name of `""` (not a work tree, or `git` failed) keeps the tracked shard. A
  directory with no repo has no `git status` to dirty, and a repo where `git` failed is the
  fail-open direction, i.e. today's behavior.
* `plan_gate` reads `.git/HEAD` itself and reports a detached HEAD as `""`, so its receipt
  stays tracked there.
* The spool is local state. It is never joined into provenance reads
  (`scripts/verify_doc_template.py` reads `docs/dev/ledger/` only), so a trunk-time receipt is
  evidence for this machine's disclosure counts, not part of the committed record.
"""

from __future__ import annotations

from pathlib import Path

#: Branch names a hook-written receipt is spooled for rather than tracked.
TRUNK_BRANCHES = frozenset({"main", "master", "HEAD"})

_TRACKED_PARTS = ("docs", "dev", "ledger")
_SPOOL_PARTS = (".claude", "state", "ledger")


def is_trunk(branch: str) -> bool:
    """True for `main`, `master` and a detached HEAD."""
    return branch in TRUNK_BRANCHES


def tracked_shard(project_dir: Path, session: str) -> Path:
    """The committed provenance shard (`docs/dev/prov/SPEC.md` section 3)."""
    return project_dir.joinpath(*_TRACKED_PARTS, f"{session}.jsonl")


def spool_shard(project_dir: Path, session: str) -> Path:
    """The untracked trunk-time spool beside the other `.claude/` local state."""
    return project_dir.joinpath(*_SPOOL_PARTS, f"{session}.jsonl")


def hook_shard(project_dir: Path, session: str, branch: str) -> Path:
    """Where a hook should append its receipt, given the branch HEAD is on."""
    if is_trunk(branch):
        return spool_shard(project_dir, session)
    return tracked_shard(project_dir, session)


def all_shards(project_dir: Path, session: str) -> tuple[Path, Path]:
    """Both locations a session's receipts may be in, for readers that count them."""
    return tracked_shard(project_dir, session), spool_shard(project_dir, session)

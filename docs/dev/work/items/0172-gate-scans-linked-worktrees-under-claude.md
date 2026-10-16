```toml
schema = 1
id = 172
kind = "item"
title = "Whole-tree gate tests scan linked worktrees under .claude/worktrees and fail the main checkout's gate"
status = "open"
decision_owner = "agent"
branches = ["chore/dependabot-triage-item"]
refs = [
  "tests/test_egress_allowlist.py:167",
  "tests/test_egress_allowlist.py:201",
  "tests/test_docstring_coverage_gate.py",
  "tests/test_ux_toast_wait_gate.py",
  "docs/dev/handoffs/data-root.md",
  "docs/dev/work/items/0171-dependabot-merge-policy-and-major-bumps.md",
]
summary = "A harness worktree under .claude/worktrees fails 3 whole-tree gate tests in the main checkout; hooksPath also changed."
```

**Filed by the session that caused it, 2026-10-16.** That session called the harness's
`EnterWorktree` to avoid disturbing another agent working in the main checkout. The worktree it
created lives **inside** the repository directory, at `.claude/worktrees/<name>`, and the other
agent's gate then failed in place.

## What was observed

Source: `docs/dev/handoffs/data-root.md`, section "What just landed on `main`", Gate, written by the
other agent. Nothing here was re-run by the filing session except the code reads marked as such.

- **Failing in place, passing on a clean checkout of the same commit.** `python -m scripts.gate
  --result` in the repo directory reported `FAILED ... failed step 'pytest -m "not ux" -n auto' ...
  HEAD e31fd09`; a clean detached checkout of `e31fd09` outside the repo reported `PASSED`.
- **The three failing tests** are whole-tree scans:
  `tests/test_egress_allowlist.py::test_static_egress_allowlist`,
  `tests/test_docstring_coverage_gate.py::test_docstring_coverage_meets_floor`,
  `tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist`. Per that handoff all
  three failure texts list the linked worktree's paths, and the repo's own files had 0 of 592
  docstrings missing while 404 worktree files carried 3,008 misses.
- **Code read by the filing session:** `tests/test_egress_allowlist.py:167-169` defines
  `_SCAN_EXCLUDE_PARTS` as `tests`, `.venv`, `venv`, `.git`, `build`, `dist`, `__pycache__`,
  `versions`, with no `.claude`; `_production_py_files` (`:199-206`) walks `REPO_ROOT.rglob("*.py")`
  and filters only on those parts. So a `.claude/worktrees/<name>/` copy of the repo is scanned as
  production code. The other two tests were **not** read for their scan roots.
- **`core.hooksPath` changed.** The same handoff reports that when the worktree appeared the
  per-clone setting became the absolute `C:\Dev\sartor\.githooks`, the gate's hooksPath preflight
  (item 150) refused, and the other agent reset it to `.githooks`. At filing time
  `git config --show-origin --get-all core.hooksPath` reads `file:C:/Dev/sartor/.git/config .githooks`.
  The worktree was created by the harness and `git worktree list --porcelain` shows it
  `locked claude session dependabot-triage-item`. That is **consistent with** the harness having
  written the absolute path, but **what wrote it was not established**.

## Why it matters

`.claude/worktrees/` is the harness's own default location for `EnterWorktree`, and the repo's
`feedback-concurrent-agents-worktree` guidance tells agents to use separate worktrees. Following
that guidance in the default location breaks the gate for whoever works in the main checkout. The
guard that caught it (the gate) worked, but only after the other agent spent a gate run finding
it, and the merge went ahead on CI's clean-checkout result.

## Candidate fixes (not chosen; the first move is an instrument)

1. Add `.claude` to the scan excludes in all three tests (and any other whole-tree scan; a grep
   for `rglob(` and `os.walk` under `tests/` and `scripts/` is the enumeration).
2. Derive the scanned file set from `git ls-files` instead of a tree walk. A linked worktree's files
   are not in the main checkout's index. Cost: the handoff records `git ls-files` at 1.8-5.2 s on
   this machine under memory pressure, so measure before choosing.
3. Create worktrees outside the repo directory (a `worktree.baseRef`/location setting, if the
   harness has one; not checked). This moves the hazard rather than removing it.

Option 1 is the cheapest and leaves the other two open; this repo's charter prefers a gate that
fails closed, so a derived-set test that fails if any `rglob`/`os.walk` scan root lacks the
exclusion would be the C-11 shape. Per C-7 the first commit on the fix branch is a reproduction:
create a linked worktree under `.claude/worktrees/`, run the three tests, record the failure.

## Updates

### 2026-10-16 - filed

Filed from the item-171 session after reading the other agent's handoff. That session's worktree
was removed from inside the repo directory as soon as its work was committed (see item 171).
Open question for the owner: should `EnterWorktree` be used at all in this repo until this item is
fixed, or only with a path outside the tree.

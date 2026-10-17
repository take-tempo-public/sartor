# Diagnosis — whole-tree gate scans read a linked worktree under `.claude/worktrees` as production code

> **Status:** Symptom REPRODUCED on demand (3 of 5 whole-tree scans fail with a worktree present and pass
> without). The mechanism for those three is read in code and matches the failure texts. What wrote
> `core.hooksPath` in the original incident is NOT established. See `## Inferred`.
> **Branch:** `fix/gate-skips-linked-worktrees` (work item 172)

---

## Symptom

`python -m scripts.gate` run in the main checkout failed with a linked worktree sitting at
`.claude/worktrees/<name>`, and passed in a clean checkout of the same commit (item 172, from
`docs/dev/handoffs/data-root.md`, written by another agent; not re-run here beyond the reproduction below).

---

## Observed

All runs: this machine, Git Bash, `main` at `f0cd882` plus the branch `fix/gate-skips-linked-worktrees`
(no code change yet), 2026-10-16. The script was `repro172.sh` (kept in the session scratchpad; the commands
are quoted per entry so it can be redone).

**O1. Control arm: the five scans pass with no linked worktree.**
`python -m pytest tests/test_egress_allowlist.py tests/test_call_kind_telemetry.py tests/test_ux_toast_wait_gate.py tests/test_xfail_controls_gate.py tests/test_docstring_coverage_gate.py -q -p no:randomly`
```
============================= 33 passed in 28.36s =============================
```

**O2. With `git worktree add --detach .claude/worktrees/repro-172 HEAD`, three of the five fail.**
Same command as O1, run with the worktree present (worktree holds 436 `.py` files):
```
FAILED tests/test_egress_allowlist.py::test_static_egress_allowlist - Asserti...
FAILED tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist
FAILED tests/test_docstring_coverage_gate.py::test_docstring_coverage_meets_floor
======================== 3 failed, 30 passed in 49.27s ========================
```
This reproduces the three tests named in item 172.

**O3. The failure texts name the worktree's paths** (second run, three tests only; log
`repro172-fail.log` lines 16, 21, 26-51):
```
E   AssertionError: Unsanctioned network-egress import site(s): ['.claude/worktrees/repro-172/analyzer.py', '.claude/worktrees/repro-172/blueprints/analysis.py', ...
E   AssertionError: UX code references the shared toast #_corpusToast: {('.claude/worktrees/repro-172/tests/test_ux_toast_wait_gate.py', '<module>'): 5, ...
E   AssertionError: Production docstring coverage fell below [tool.interrogate].fail-under (99%). ...
E     | .claude\worktrees\repro-172\analyzer.py   |    48 |    0 |    48 |   100% |
```

**O4. After `git worktree remove --force`, the same five pass again.** `git worktree list` shows only
`C:/Dev/sartor`; same command as O1:
```
============================= 33 passed in 14.08s =============================
```

**O5. The other two scans did NOT fail in O2** (`test_call_kind_telemetry.py`, `test_xfail_controls_gate.py`).
The reason is read in code, not observed as a trace:
- `tests/test_call_kind_telemetry.py:107` walks `REPO_ROOT.rglob("*.py")` with no `.claude` exclude
  (`:63-65`), so it does read the worktree; `:136-139` unions the literals into a `set`.
- `tests/test_xfail_controls_gate.py:172` roots its walk at `REPO_ROOT / "tests"`, which does not reach
  `.claude/`.

**O6. ruff, mypy and collection were not affected by the worktree.**
- `python -m ruff check .` with the worktree present: `All checks passed!`
- `python -m mypy .` with the worktree present: `Success: no issues found in 436 source files` (436 is also the
  count of tracked-plus-untracked-unignored `.py` files, O8).
- `python -m pytest --collect-only -q` with the worktree present: `3686 tests collected in 74.65s`; `grep -c
  "repro-172"` over that output printed `0`.

**O7. `core.hooksPath` did not change** across `git worktree add` or `git worktree remove` done by plain git:
`git config --show-origin --get-all core.hooksPath` printed `file:.git/config	.githooks` before add, after add
and after remove.

**O8. Timing and file sets** (three runs each, `python -c` with `subprocess` / `Path.rglob`):
```
ls-files 66 ms, 436 py     (git ls-files -z --cached --others --exclude-standard)
ls-files 60 ms, 436 py
ls-files 70 ms, 436 py
rglob 2283 ms, 441 py      (Path('.').rglob('*.py'))
rglob 1315 ms, 441 py
```
The set difference on the clean tree: `rglob`-only was five files, all under
`docs-site/node_modules/katex/`; `git`-only was empty.

**O9. Whole-tree walkers under `tests/` and `scripts/`** (Grep for `rglob\(|os\.walk\(|\.glob\("\*\*`): the
repo-root ones are `tests/test_call_kind_telemetry.py:107`, `tests/test_egress_allowlist.py:201`,
`tests/test_ux_toast_wait_gate.py:89`. Subdirectory-rooted ones include `tests/test_xfail_controls_gate.py:65`,
`tests/test_evidence_gate.py:321`, `tests/test_verify_doc_template.py:318`, `tests/test_data_root.py:298`,
`tests/test_egress_allowlist.py:387`. `scripts/` has `.glob("*.md")`-style single-directory globs only.

---

## Falsified

- **"The worktree also breaks ruff, mypy or collection"**: not seen (O6). Nothing to add for them.
- **"`git worktree add` rewrites `core.hooksPath` to an absolute path"**: not seen (O7). The incident's change
  was caused by something else, or by the harness's `EnterWorktree`; see `## Inferred`.
- **"Four scans are exposed" (my plan's first count)**: `test_xfail_controls_gate.py` roots at `tests/` (O5), so it
  is not exposed.

---

## Inferred

- **Mechanism for the three failures.** Each test builds its file set by walking the repo root and filtering on a
  hand-kept list of directory names, and no list has `.claude`; `interrogate` takes its scope from
  `pyproject.toml:361` which lacks it too. O2-O3 are consistent with this. Not proven by removing the cause: that
  is what the fix commit's test run will show.
- **`test_call_kind_telemetry.py` is exposed but passed.** Read from the code (O5), never seen failing. It would
  likely fail if the worktree were on a different commit carrying a new `call_kind` literal. Unverified.
- **What changed `core.hooksPath` in the original incident** is unknown (item 172's own note says the same).
  Candidates: the harness's `EnterWorktree`, or something else running at that moment. Unresolved here.

---

## Falsification

**Experiment, run before the fix:** with a linked worktree at `.claude/worktrees/repro-172`, a new test
`tests/test_repo_files.py` (a git-listed file set excludes a linked worktree, whether the worktree path is
ignored or not) and `tests/test_tree_walk_gate.py` (no repo-root walker outside an allowlist) must **fail on HEAD**.

- If they fail on HEAD: confirmed; build the fix.
- If `test_repo_files.py` passes on HEAD it cannot, since the helper does not exist yet. If the *unmigrated*
  scans still fail in O2 after the migration, the mechanism is wrong.

---

## The fix

A shared `tests/_repo_files.py` giving the git-listed file set; `test_egress_allowlist.py`,
`test_ux_toast_wait_gate.py` and (exposed, though it passed in O2) `test_call_kind_telemetry.py` migrated onto it;
`.claude` added to `[tool.interrogate].exclude` (`pyproject.toml`), since interrogate walks the tree itself; an AST
gate (`tests/test_tree_walk_gate.py`) that fails on any recursive walk not listed with its reason.

**After the fix (same worktree path, `HEAD` = `13ea71b` plus the working tree, `-p no:randomly`):**
```
collected 46 items  ...  ============================= 46 passed in 14.93s =============================
```
(the five scans from O1 plus `test_repo_files.py` and `test_tree_walk_gate.py`, with `.claude/worktrees/repro-172`
holding 438 `.py` files). Before the fix the same worktree failed three of them (O2).

**File-set equality check** (old walk vs `repo_files`, per test, `sets.py` in the session scratchpad): egress 165 to
160 and call_kind 165 to 160, the five removed being the `docs-site/node_modules/katex/**` files (vendored code the
old egress and call_kind scans were reading); toast 438 to 438, no difference.

**Gate mutation check:** a scratch `tests/_scratch_mutation.py` with `REPO_ROOT.rglob("*.py")` made
`test_every_walk_in_tests_and_scripts_is_listed_with_its_exact_count` fail with
`unlisted or wrong count: {'tests/_scratch_mutation.py': 1}`; it passed again once the file was removed.

---

## Acceptance bar

- With `.claude/worktrees/repro-172` present, the five scans from O1 pass; they failed in O2.
- `tests/test_repo_files.py` and `tests/test_tree_walk_gate.py` fail before the fix commit and pass after, with no
  retry in the log (`-p no:randomly`, no `pytest-rerunfailures` involvement).
- `python -m scripts.gate --result` for the final tree, and CI through `python -m scripts.ci_wait` exit 0.

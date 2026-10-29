```toml
schema = 1
id = 52
kind = "item"
title = "Gate-window gap: post-gate artifacts (handoffs, staged modes, amends) are never re-gated against the final committed tree"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/gate-window-class-study.md",
  "scripts/gate.py",
  "docs/dev/handoffs/fix-plan-approval-marker-pr-merge.md",
]
summary = "The tree that lands is never the tree the gate examined; class study documents 6 instances + candidate mechanisms."
```

Filed at the 2026-08-06 pre-march chain close, owner-directed ("document this
durably with a class study ... so that it can be resolved in a future sprint").

The full evidence record — six dated instances (from `dfe1767` through the
chain's Case 2 double-defect and Case 4's amend re-hash), the shared mechanism
(everything after the gate mutates the tree: index-vacuous tests, structurally
un-gateable handoffs, post-citation amends), what already catches it and when,
and three candidate mechanisms — lives in
[`docs/dev/gate-window-class-study.md`](../../gate-window-class-study.md). This
item exists so the class study has a tracked owner-visible handle; the study is
the source of record, not this stub.

Per charter **C-11** this is a recognized recurrence and obliges a fail-closed
mechanism; the chain close-out that filed this item executed candidate
mechanism 1 (a final-tree structural re-check) **by hand** as a working
prototype, which is prose-only and therefore explicitly **unenforced** until a
resolving branch lands it. `decision_owner = "user"` because the mechanism
choice (post-commit gate alias vs pre-push hook vs checklist reorder) changes
the close-out contract every future branch follows.

## Updates

### 2026-10-21 -- a seventh instance, caused by untracked files (feat/eval-record-identity)

The local gate (`python -m scripts.gate`, `--result` PASSED) ran with five new files untracked: `call_identity.py`, `scripts/prompt_lock.py`, three new tests and the dossier. Checks that read `git ls-files` (`tests/test_wiki_cites.py`, `tests/test_wiki_relevance_classification.py`, via `tests/_repo_files.py`) could not see them, so two defects in the wiki edits passed locally. CI checks out tracked files only and failed both tests on py3.11, 3.12 and 3.13 (PR #198, first run). This differs from the earlier instances (post-gate artifacts such as handoffs and amends): here the gate examined a tree that was never the committed one *before* any post-gate step. A cheap candidate mechanism, not built because the choice is the owner's: `scripts/gate.py` refuses, or loudly warns, when `git ls-files --others --exclude-standard` lists anything. Until then the rule is prose and unenforced: `git add` new files before running the gate.

### 2026-10-28 -- another instance, a different cause: the gate ran on Windows, CI runs Linux (PR #204)

`python -m scripts.gate` passed locally on `f5baff5`; CI failed all three Python-version jobs in under a minute at `mypy .`: `evals/golden_author.py:423: error: Statement is unreachable [unreachable]`. The cause was a platform test (`if sys.platform != "win32": return`) before a Windows-only call: mypy evaluates it per platform, so on Linux the call is unreachable and `warn_unreachable` fails. Fixed by finding the API by capability (`getattr(ctypes, "windll", None)`) with a test for the no-`windll` path. **A cheap check that was missing and now exists by hand:** `python -m mypy --platform linux .` reproduces CI's mypy from a Windows machine (it passes after the fix). **No gate mechanism authored:** adding it to `scripts/gate.py` is a change to a C-10 gated surface and is the owner's choice (item 52's mechanism question); the rule is prose and unenforced until then: run `mypy --platform linux .` before pushing code that tests `sys.platform`. The same class can hide in the pytest tier, which CI runs on Linux and the local gate did not.

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

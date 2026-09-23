```toml
schema = 1
id = 111
kind = "item"
title = "check-plan-approved.sh costs ~2 s on every Edit/Write and 8-21 s on its retire path on Windows/MSYS: about 15-20 forks at 0.3-1 s each"
status = "open"
decision_owner = "agent"
branches = ["fix/plan-approval-retired-mid-branch"]
refs = [
  "hooks/check-plan-approved.sh",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/diagnosis/plan-approval-retired-mid-branch.md",
]
summary = "Plan-approval hook: ~2 s per edit, 8-21 s per retire, from MSYS fork count. Item 110 fixed correctness, not speed."
```

**Observed (2026-09-22, session `0ea1b8bf`, this machine, measured under the load of VS Code, WSL and other sessions):**

- The fast path (no retirement) took **1.98 s** once, on every Edit/Write. Its cost is the
  `python3 -c` JSON parse plus the `echo | tr | grep` path checks.
- The retire path took **5.66-14.72 s** before the item-110 fix and **8.53-21.45 s** after
  it (one run exceeded the new 20 s timeout). A `bash -x` profile with
  `PS4='+ $EPOCHREALTIME '` shows no single hot step: `git rev-parse` 1.05 s,
  `git merge-base` 1.04 s, `cygpath` 0.91 s, `python3 -` 0.79 s, `python3 -c` 0.61 s,
  `git show-ref` 0.30 s, and so on.

**Why it matters.** The fast path is a standing tax on every edit. On a busy agent run that
is minutes per session. The retire path exceeding the timeout lets one edit slip through
after a retirement (item 110's stated limit).

**Candidate direction, not decided.** Do the retirement in one `python3` call (mkdir, mv,
manifest, receipt, and the `/c/` → `C:/` path conversion in-process in place of four
`cygpath` forks). Parse the payload without a python fork, or fold the witness and plan
checks into the existing `claude_dispatcher.py` process that already runs on the same
matcher. Measure before and after, per the efficiency rule.

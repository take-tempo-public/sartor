```toml
schema = 1
id = 111
kind = "item"
title = "check-plan-approved.sh costs ~2 s on every Edit/Write and 8-21 s on its retire path on Windows/MSYS: about 15-20 forks at 0.3-1 s each"
status = "closed"
decision_owner = "agent"
branches = ["fix/plan-approval-retired-mid-branch", "fix/python-direct-hooks-plan-gate"]
refs = [
  "hooks/check-plan-approved.sh",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/diagnosis/plan-approval-retired-mid-branch.md",
]
summary = "Plan-approval hook: ~2 s per edit, 8-21 s per retire, from MSYS fork count. Item 110 fixed correctness, not speed."
resolution = "2026-10-07, fix/python-direct-hooks-plan-gate: the plan gate is Python (scripts/enforcement/plan_gate.py), run inside the Edit|Write dispatcher, with no fork on the steady path and at most three git calls on retire. Measured N=10 at about 0.5 GB free: Edit|Write steady 18052 -> 2427 ms median, retire 35956 -> 3022 ms, mark 4117 -> 1819 ms. Timeouts were set from the after-run."
verified_by = [
  "tests/test_plan_approval_scoping.py::TestEfficiency",
  "docs/dev/diagnosis/python-direct-hooks-plan-gate.md (O4/O4b timings)",
]
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

### 2026-10-07 — closed on `fix/python-direct-hooks-plan-gate` (with item 152)

Before/after tables in `docs/dev/diagnosis/python-direct-hooks-plan-gate.md` O4 and O4b. One finding beyond the item's own text: the
cost made the gate **open**, not just slow. A cancelled PreToolUse hook does not block, and
in one session 31 of 40 edits ran with no Edit|Write guard (O3).

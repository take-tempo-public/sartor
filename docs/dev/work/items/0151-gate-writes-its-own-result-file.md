```toml
schema = 1
id = 151
kind = "item"
title = "Recurrence: background-task notifications report exit 0 for a gate whose log says exit 1; the gate should write its own result file"
status = "closed"
decision_owner = "agent"
branches = ["fix/hook-guard-false-blocks"]
refs = [
  "scripts/gate.py",
  "scripts/ci_wait.py",
]
resolution = "2026-10-05, fix/hook-guard-false-blocks: scripts/gate.py writes gate-result.json in the git dir on every terminal path (refusal, failure, pass, interrupt) with exit, failing step, times, HEAD and a tree digest; `python -m scripts.gate --result` exits 0 only when the last run passed on this exact tree. tests/conftest.py redirects it for every test."
verified_by = [
  "tests/test_gate_result_and_hooks_path.py::TestResultFile",
]
summary = "A background gate run is reported 'exit 0' while its log ends 'exit=1'. Third time; needs a result file + checker."
```

**Observed.**
- 2026-10-03, session 3abb1df0: task `b32w6qi12` (the gate via Git Bash, output redirected to a log)
  was reported `completed (exit code 0)`. The log ended `gate: FAILED at \`mypy .\` (exit 1)` /
  `exit=1`. Task `b5kuyio3f` was the same: reported exit 0; the log said
  `gate: FAILED at \`memory preflight\` (exit 1)` / `exit=1`.
- Earlier instances are recorded in the `chore-release-v1-1-0` handoff (recurrence 1: `flake_rates
  collect` reported 0, really 3; `scripts.gate` reported 0, really 1) and in the owner's memory
  `reference-background-task-exit-code-unreliable`.

**Cause:** inferred as harness-side and not verified. The redirect-plus-echo wrapper's own exit
is 0 even when the gate fails, which may be all it is. Either way the repo can't rely on the
notification. The harness-side part is reported to Anthropic separately.

**Fix direction (C-11, recurrence):**
- `scripts/gate.py` writes a machine-readable result file on every terminal path: exit code,
  failing step, start/end time, `git rev-parse HEAD`, and a dirty-tree flag.
- A small checker (`python -m scripts.gate --result`) is the single definition of "the last
  local gate passed on this tree", the same way `ci_wait` defines "the PR is green".
- Commits and handoffs cite that result file, not a notification.

## Updates

### 2026-10-03 — filed on `chore/agent-doc-drift`

### 2026-10-05 — closed on `fix/hook-guard-false-blocks`

scripts/gate.py writes gate-result.json in the git dir on every terminal path (refusal, failure, pass, interrupt) with exit, failing step, times, HEAD and a tree digest; `python -m scripts.gate --result` exits 0 only when the last run passed on this exact tree. tests/conftest.py redirects it for every test.

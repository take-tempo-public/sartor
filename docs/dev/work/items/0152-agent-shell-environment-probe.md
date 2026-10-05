```toml
schema = 1
id = 152
kind = "item"
title = "Agent shell environment varies by session: a Bash tool with no coreutils made a Monitor busy-loop; invoke hooks as Python directly"
status = "open"
decision_owner = "agent"
refs = [
  "hooks/",
  ".claude/settings.json",
  "scripts/enforcement/adapters/",
  "docs/dev/work/items/0111-*.md",
]
summary = "A Bash with no grep/sleep made a Monitor spin. Owner chose Python-direct hooks (no .sh wrappers) + a shell probe."
```

**Observed (2026-10-03, session 3abb1df0).**
- The Bash tool resolved `/usr/bin/bash` with no coreutils: `python`, `ls`, `which`, `grep` and
  `sleep` all returned "command not found", and `verify-binary-on-path` blocked `/usr/bin/ls`.
- A Monitor armed with `until grep -q …; do sleep 15; done` failed both commands on every
  iteration. Its output was 13 `sleep: command not found` lines within seconds, at full CPU, until
  `TaskStop`.
- PowerShell 7 and an explicit `C:\Program Files\Git\bin\bash.exe -lc` both worked.

**Owner decision (2026-10-04): standardize on Python, not a shell.** Asked whether a single
cross-platform shell would work, the owner chose to "fold python-direct hooks into 152". The
logic layer is already Python (gate, `ci_wait`, the enforcement core, `work_items`). The shell
only has to launch `python -m …`.

**Fix (scope of this item):**
1. **Python-direct hooks.** Every hook entry in `.claude/settings.json` calls the Python adapter
   directly (for example `python -m scripts.enforcement.adapters.claude_hook <guard>`), with no
   `hooks/*.sh` wrapper in between. That removes the bash dependency from enforcement and the MSYS
   fork cost item 111 measures (about 2 s per Edit/Write). Item 111 should be re-measured once
   this lands, and may close with it.
2. **The rule, as a gate:** a test fails if a `.claude/settings.json` hook command invokes a
   `.sh` file or a shell interpreter. Logic belongs in a Python module, which is also the durable
   answer to item 142's heredoc-escaping recurrence.
3. **A `SessionStart` probe** reports which of the session's shells can run `python`, `sleep` and
   `grep`, and says which to use. It warns but does not gate, and it can't stop a Monitor. It
   is the cheap part.

**Before building (C-10 / C-0):**
- `.claude/settings.json` and `hooks/` are consumed by more than the harness:
  - `CLAUDE.md`'s hook list and wiring note;
  - `docs/dev/tooling.md` and `docs/governance/enforcement.md`;
  - `tests/test_enforcement_coverage.py`;
  - `tests/test_enforcement_core.py::TestBashDispatcher`, which runs `hooks/bash-dispatcher.sh`
    as a subprocess;
  - the opt-in `.githooks/`.
  Enumerate them grep-complete in a blast-radius dossier first.
- **Not verified:** how Claude Code's hook runner resolves `python` vs `python3` on Windows, macOS
  and Linux. It matters on hypha and the homelab machines. Check the interpreter name there before
  choosing the command string. One option is a single `sys.executable`-independent launcher
  that each platform's settings can point at.
- The plan-gate hooks (`check-plan-approved.sh` and its siblings) are shell scripts with their
  own logic, not wrappers. Porting them is real work, not a rewire.

## Updates

### 2026-10-03 — filed on `chore/agent-doc-drift`

### 2026-10-04 — owner decision: Python-direct hooks folded in
Decision recorded above. `decision_owner` moved to `agent`: the open choice is made, and what
remains is implementation.

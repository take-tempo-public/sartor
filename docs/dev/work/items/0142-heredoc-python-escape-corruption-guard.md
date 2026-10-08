```toml
schema = 1
id = 142
kind = "item"
title = "Recurrence: backslash escapes in a heredoc'd python script corrupt the file it writes"
status = "closed"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "fix/heredoc-escape-guard"]
refs = [
  "scripts/enforcement/guards/block_doubled_backslash.py",
  "scripts/enforcement/adapters/bash_dispatcher.py",
  "docs/dev/diagnosis/heredoc-escape-guard.md",
  "docs/dev/blast-radius/heredoc-escape-guard.md",
]
summary = "Heredoc python scripts with backslash escapes wrote a backspace char and a broken file; a Bash guard could refuse them."
resolution = "2026-10-07, fix/heredoc-escape-guard: the instrument showed the defect is not heredoc-specific. On Windows, Git Bash halves every doubled backslash while rebuilding its argv from the command line, before bash parses (diagnosis O1-O5). The block-doubled-backslash Bash guard refuses any Bash-tool command containing two consecutive backslashes on win32, and allows everything elsewhere (owner decision). The root-cause candidate, MSYS=noglob, is filed as its own item."
verified_by = [
  "tests/test_enforcement_core.py::TestBlockDoubledBackslashUnit",
  "tests/test_enforcement_core.py::TestBashDispatcher::test_doubled_backslash_blocks_through_the_real_dispatcher",
  "tests/test_bash_backslash_collapse.py",
  "docs/dev/diagnosis/heredoc-escape-guard.md (The fix: live BLOCKED in session 17250fd2)",
]
```

**Observed (2026-10-01, `feat/docs-assets-enforcement`), three times in one session.**
- A regex word-boundary escape inside a heredoc'd Python string literal landed in
  `scripts/doc_lints.py` as a literal backspace character (`grep -c $'\x08'` returned 1). That
  silently disabled the 5.7 acronym check until a real-tree run showed the findings missing.
- A newline escape became a real newline in `scripts/check_docs_projection_fresh.py` (ruff:
  "missing closing quote in string literal").
- An edit script's anchor didn't match, and it aborted.

**This is a recurrence.** The owner's memory has recorded the same trap since 2026-08-05
(three earlier instances). Under C-11 a recurrence obligates a mechanism.

**None authored on this branch:** a new Bash guard is outside a docs sprint's scope. A
candidate that fails closed: a `bash-dispatcher` guard that refuses a command running
`python -` (or `python3 -`) from a heredoc whose body contains a backslash, with the message
"write the script with the Write tool and run it by path". False positives are cheap: the
way through is always open. Stated to the owner at D4 close.

### 2026-10-07 — recurred three times on `fix/python-direct-hooks-plan-gate` (no mechanism here: out of scope)

- Bash heredocs collapsed backslash escapes three times this session: `\\n` to a newline, and
  `\\|` to `\|`. Worst, a `\\b` became two literal **backspace bytes** in
  `tests/test_agent_tool_grant_consistency.py`. A byte scan caught them before commit
  (`docs/dev/diagnosis/python-direct-hooks-plan-gate.md` O5).
- The working rule that held: write scripts with the Write tool, never a heredoc. That rule is
  prose and **unenforced**.
- The owner bounded this branch to items 152/111/154/143, so no guard was built; surfaced at
  close-out.

### 2026-10-07 — closed on `fix/heredoc-escape-guard`: the mechanism is before bash, not in heredocs

- **Observed** (`docs/dev/diagnosis/heredoc-escape-guard.md`):
  - Through the Bash tool, a single-quoted `'A\\b'` prints `A\b`, and bash's own argv already
    holds one backslash where two were sent.
  - The PowerShell tool keeps both.
  - Outside Claude Code, native Python starting `bash.exe -c` halves every doubled run. The
    same text on stdin, or with `MSYS=noglob`, arrives intact.
- **All ten recorded incidents' decoded commands held the intended two backslashes.** Three of
  them had no heredoc at all (`grep`, `sed`). So this item's filed candidate ("refuse
  `python -` heredocs with a backslash") would have missed them.
- **The mechanism built:** `block-doubled-backslash`, which refuses any doubled backslash in a
  Bash-tool command on Windows (owner decision: Windows only). It was verified live in the
  closing session.
- **Filed alongside:**
  - item 157, `MSYS=noglob` as the root-cause fix, which the owner chose to keep separate;
  - item 158, bash refusing whole commands with `unexpected EOF while looking for matching '`,
    which this mechanism does not explain.


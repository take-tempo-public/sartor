```toml
schema = 1
id = 157
kind = "item"
title = "Try MSYS=noglob in settings env as the root-cause fix for the Bash tool halving doubled backslashes on Windows"
status = "open"
decision_owner = "agent"
branches = ["fix/heredoc-escape-guard"]
refs = [
  "docs/dev/diagnosis/heredoc-escape-guard.md",
  "scripts/enforcement/guards/block_doubled_backslash.py",
  "tests/test_bash_backslash_collapse.py",
  ".claude/settings.json",
]
summary = "MSYS=noglob stopped Git Bash halving doubled backslashes in a standalone repro; untested inside Claude Code."
```

**Observed (2026-10-07, session `17250fd2`, on `fix/heredoc-escape-guard`).** Native Windows
Python started `C:/Program Files/Git/usr/bin/bash.exe -c "printf %s 'X\\b|Y\b|Z\\\\b'"`, and the
backslash runs came back halved, `[2, 1, 4]` → `[1, 1, 2]`. With `MSYS=noglob` in the child's
environment they came back intact (`docs/dev/diagnosis/heredoc-escape-guard.md` O4).
`tests/test_bash_backslash_collapse.py::test_msys_noglob_keeps_every_backslash` pins that.

**Not verified:**
- whether `.claude/settings.json` `env` reaches the bash that Claude Code starts for the Bash
  tool;
- what else `MSYS=noglob` changes for every Bash call and its children (tests, hooks, git).

The owner chose (2026-10-07) to build the fail-closed guard first (item 142) and keep this
root-cause change on its own branch.

**First move:** add `"env": {"MSYS": "noglob"}` on a branch, restart the session (the env binds
at session start), and re-run the diagnosis dossier's O1 probe through the Bash tool. If
backslashes survive, the `block-doubled-backslash` guard's premise is gone on this machine.
Decide with the owner whether to retire it or key it on the measured behaviour, and update
`tests/test_bash_backslash_collapse.py` in the same diff.

## Updates

### 2026-10-07 — filed during fix/heredoc-escape-guard (item 142's root-cause candidate)

### 2026-10-08 — fix/bash-tool-transport: falsified as a fix (instrument)

`MSYS=noglob` breaks every quoted command on the harness's real command line
(`docs/dev/diagnosis/bash-tool-transport.md` O3).
- The harness wraps each command as `eval '<cmd>'`, rewriting every `'` as `'"'"'` (O1).
- Windows holds that line with every `"` escaped as `\"` (O2).
- Replayed through Git Bash with `MSYS=noglob`, the command `printf '%s|' 'SQ' "DQ" …` fails
  with rc 2 and `-c: line 1: unexpected EOF while looking for matching '`. Without it, the same
  command parses (and halves `\\`).
- The 2026-10-07 standalone success put no `"` on the command line.

Set in `.claude/settings.json` `env`, `MSYS=noglob` would break nearly every Bash-tool call. The
owner chose (2026-10-08) to close this on the standalone evidence, with no in-harness trial and
no session restart. `block-doubled-backslash` stays.

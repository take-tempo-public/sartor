```toml
schema = 1
id = 142
kind = "item"
title = "Recurrence: backslash escapes in a heredoc'd python script corrupt the file it writes"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement"]
refs = ["scripts/enforcement/guards/", "hooks/bash-dispatcher.sh"]
summary = "Heredoc python scripts with backslash escapes wrote a backspace char and a broken file; a Bash guard could refuse them."
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

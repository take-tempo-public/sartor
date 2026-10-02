```toml
schema = 1
id = 136
kind = "item"
title = "block-merge-to-main blocks commands that only contain merge-to-main text (grep patterns, heredoc bodies)"
status = "open"
decision_owner = "agent"
branches = ["feat/dev-docs"]
refs = [
  "scripts/enforcement/guards/block_merge_to_main.py:90",
  "scripts/enforcement/guards/block_merge_to_main.py:133",
]
summary = "_MERGE_MAIN_RE searches raw command text, so a grep pattern or heredoc line holding the phrase blocks."
```

**Observed (2026-09-30, `feat/dev-docs`).** A Bash call ran a python heredoc that edited a
work-item file and a `grep -E` whose pattern held the phrase "git merge --no-ff". Nothing in
it merged anything. It was refused with `BLOCKED (block-merge-to-main): git merge/push
targeting main or master.` The command text also contained the word "main". The workaround
was to move the script into a file and run it by path.

**Mechanism (read in code, consistent with the block):** `targets_main()`
(`block_merge_to_main.py:125-133`) runs `_MERGE_MAIN_RE =
\bgit\s+merge(?!-)\b.*\b(?:main|master)\b` (`:90`) over the raw command string, with no
shell parsing. So quoted strings, heredoc bodies and grep patterns count, but only when
`main`/`master` falls on the same line: `.*` doesn't cross a newline. That's why a later
heredoc on this branch, holding the phrase on its own line, went through.

**Cost:** one re-route per occurrence. The guard fails closed, which is the safe direction.
A fix has to keep that property, for example by matching only a `git` token in command
position, the way `verify-binary-on-path` parses leading binaries. It must not loosen into
missing a real merge. Low priority.

**This is a recurrence.** The owner's session memory recorded "`block_merge_to_main` matches
command TEXT" as a live trap on 2026-08-04. Epic branches were named `epic/a-app-core` and
so on to avoid a `main` substring. Under C-11 a recurrence obligates a mechanism. **None was
authored on `feat/dev-docs`:** the fix changes a safety guard's matching behavior, which is
outside a docs sprint's scope. The current failure is also in the safe direction: it
over-blocks. That gap was stated to the owner at close-out. Until then, the workaround is to
put multi-line scripts in a file and run them by path.

## Updates

### 2026-09-30 — filed on `feat/dev-docs`

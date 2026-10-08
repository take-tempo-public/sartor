```toml
schema = 1
id = 158
kind = "item"
title = "Bash tool sometimes refuses a whole command with \"unexpected EOF while looking for matching '\"; cause unknown"
status = "open"
decision_owner = "agent"
branches = ["fix/heredoc-escape-guard"]
refs = [
  "docs/dev/diagnosis/heredoc-escape-guard.md",
  "~/.claude/projects/C--Dev-sartor/*.jsonl",
]
summary = "Bash refused whole commands with 'unexpected EOF while looking for matching' in about 6 sessions; cause unknown."
```

**Observed (2026-10-07, session `17250fd2`).** The string
`unexpected EOF while looking for matching` appears in these session transcripts
(`~/.claude/projects/C--Dev-sartor/`, ripgrep count per file): `2b79cef7` (1), `d3d2e857` (2),
`dde107cd` (1), `f0c731c3` (1), `ec0ddb33` (3) and `0ea1b8bf` (1).

**Not verified:** that each occurrence is a Bash tool error rather than a quotation in text.
The item 142 transcript explorer reported five of them as real tool errors on commands nowhere
near the Windows command-line length limit, and that report was not re-checked. The owner's
memory records one more instance (2026-09-22, a large `cat > file <<'PYEOF'` heredoc).

**Inferred (unproven):** this is not item 142's backslash halving. That mechanism changes
backslash counts, not quote balance. It might still interact, for example through a `\\'`
sequence collapsing next to a quote, but nobody has looked.

**First move (C-7):** decode the failing commands from those transcripts (`json.loads`, the
`tool_use` `input.command`). Check whether each was really refused by bash, and what its quote
structure and length were. Reproduce one through the Bash tool and through a standalone
`bash.exe -c` before forming a theory.

## Updates

### 2026-10-07 — filed during fix/heredoc-escape-guard (seen while instrumenting item 142)

### 2026-10-08 — fix/bash-tool-transport: two mechanisms, one of them transport (instrument)

`docs/dev/diagnosis/bash-tool-transport.md` O4-O7.

- **Seven real Bash-tool failures.** Twelve hits across the six listed transcripts, item 142's
  session and its subagent, plus one workflow subagent the item did not list
  (`e713dc79…/agent-a2fc7baa7f68397dd`). The other five hits quote the string in text.
- **Six of the seven were cut by Git Bash.** Git Bash silently cuts a command-line argument to
  8,186 characters, counted in characters, not bytes (O4, O5). The harness wraps each command in
  408 more characters on this machine (O6). The six commands were 7,846-14,833 characters long,
  and all parse as written via stdin. They fail only through the command line, at the outer
  `-c:` level (O7). Three of the six contain no doubled backslash, so this is not item 142's
  halving.
- **Reproduced inside the harness (O6).** A padded command just past the cap was refused with
  `-c: line 16: unexpected EOF while looking for matching '"'` and ran nothing. One under it ran
  and printed its own length.
- **The seventh was malformed as written:** `grep -n -i "python\|script\|check_\|```"` opens a
  backtick substitution inside double quotes. Bash refuses it on stdin too, at the inner `eval:`
  level. It is the model's error, loud, with nothing run, and one instance.

The owner chose (2026-10-08) a new, separate guard, `block-long-bash-command`.

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

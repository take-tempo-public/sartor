```toml
schema = 1
id = 141
kind = "item"
title = "wiki-scribe is told to create new pages but its tool grant has no Write"
status = "open"
decision_owner = "agent"
epic = 39
branches = ["feat/docs-assets-enforcement"]
refs = [
  "agents/wiki-scribe.md:5",
  "agents/wiki-scribe.md:94",
  "commands/wiki-self-update.md:53",
]
summary = "Scribe step 5 says create a page for a new concept; tools are Read/Grep/Glob/Edit, so it returns the text instead."
```

**Observed (2026-10-01, D4 step 8).** Three `wiki-scribe` runs asked to create a new page
each returned the full page text and said file creation was "delegated to orchestrator".
None of the three files existed afterwards (`ls`: no such file). The scribe's frontmatter
grants `Read`, `Grep`, `Glob`, `Edit` (`agents/wiki-scribe.md:5-9`). `Edit` can't create a
file, yet its step 5 (`:94`) says to create one, and `/wiki-self-update` plans "created vs
updated" pages (`commands/wiki-self-update.md:53`).

**Cost:** the orchestrator wrote the files from the returned text. That is a hand copy of
model output, with room for silent edits (here: only link-path fixes, recorded in
`docs/wiki/log.md`).

**Fix direction (not built):** grant the scribe `Write`, limited by its instructions to new
files under `docs/wiki/pages/`, or have the command state that new pages are written by the
orchestrator verbatim. The first keeps author ≠ orchestrator; it is a tool-grant change, so
it is a decision about the agent's safety boundary.

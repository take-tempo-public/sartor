```toml
schema = 1
id = 141
kind = "item"
title = "wiki-scribe is told to create new pages but its tool grant has no Write"
status = "closed"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "chore/agent-doc-drift"]
resolution = "2026-10-03, chore/agent-doc-drift: took the item's second option, which leaves the agent's safety boundary unchanged. The scribe's tool grant is unchanged (no Write). Step 5 now says to hand back the path and the complete page text, and /wiki-self-update step 3 says the orchestrator writes it verbatim and logs any change it makes as a separate Edit. A test pins tool grants against create-a-file instructions for every subagent. Granting Write stays open as a future decision if hand copies prove error-prone."
verified_by = [
  "tests/test_agent_tool_grant_consistency.py::test_no_create_instruction_without_a_creating_tool",
  "tests/test_agent_tool_grant_consistency.py::test_the_check_catches_the_original_wording",
]
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

### 2026-10-02 — re-parented out of epic 39 (`chore/release-v1.1.0`)

Epic 39 merged as PR #150 and closed. The owner directed its open children to stand on their own under Open, rather than hold the epic open.

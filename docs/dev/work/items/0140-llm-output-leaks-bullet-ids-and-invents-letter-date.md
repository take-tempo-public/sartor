```toml
schema = 1
id = 140
kind = "item"
title = "LLM output leaks internal bullet ids (b173, b180) into user text, and the cover letter invents its date"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement"]
refs = [
  "analyzer.py:1183",
  "analyzer.py:2903",
  "docs/screenshots/readme_hero_wizard-step1-filled.png",
  "docs/screenshots/walkthrough_coverletter_first-generation.png",
]
summary = "Prompts hand bullets to the model as id=\"b{id}\"; the model echoes the handle into prose. Letter date is ungrounded."
```

**Observed (2026-10-01, D4 screenshot capture, live Sonnet 5 run, synthetic Priya fixture).**
Both shots are committed on this branch:
- **Step 1 analysis, "Where to focus" item 3** (`readme_hero_wizard-step1-filled.png`): "…the
  real-time shipment tracking / routing engine domain match is implied by company name and
  **b173** ('4M+ daily shipments')…"
- **Cover letter** (`walkthrough_coverletter_first-generation.png`): "Earlier, at **b180**, I
  led a monolithic-to-event-driven refactor…" The letter is also dated **"March 2025"**, on a
  run made 2026-10-01.

**Read in code, not yet proven as the mechanism.** Bullets reach the model as
`<bullet id="b{b["id"]}" …>` (`analyzer.py:1183`), and no prompt rule found says the handle
must not appear in prose. `generate_cover_letter_against_resume` (`analyzer.py:2903`) passes
no date input, so the model makes one up.

**Why it matters:** a user sees an internal id in their own analysis and, worse, in a cover
letter they might send. An invented date on a letter is an ungrounded fact (charter C-3).

**Fix direction.** This is a prompt change with `PROMPT_VERSION` discipline and an eval
A/B. Two parts: a rule that ids are handles for `selected_bullets` only, never prose, with
a worked NOT-OK example; and passing today's date into the cover-letter call. **Then
recapture** the two screenshots above.

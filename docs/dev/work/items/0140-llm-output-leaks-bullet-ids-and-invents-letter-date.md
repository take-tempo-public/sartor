```toml
schema = 1
id = 140
kind = "item"
title = "LLM output leaks internal bullet ids (b173, b180) into user text, and the cover letter invents its date"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "fix/llm-handle-leak-and-letter-date"]
refs = [
  "analyzer.py:_corpus_block",
  "analyzer.py:generate_cover_letter_against_resume",
  "docs/dev/diagnosis/llm-handle-leak-and-letter-date.md",
  "docs/dev/blast-radius/llm-handle-leak-and-letter-date.md",
  "docs/screenshots/readme_hero_wizard-step1-filled.png",
  "docs/screenshots/walkthrough_coverletter_first-generation.png",
]
summary = "Fix built and measured; open: cover-letter screenshot not recaptured, one fixture score drop unexplained."
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

## Updates

**2026-10-17, `fix/llm-handle-leak-and-letter-date`.** The fix is built and measured; the item stays **open** because
two acceptance parts are not met. The full record is `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md`.

- **Reproduced first (C-7), then fixed.** On unchanged prompts, all six fixture-runs put ids in the analysis (105
  b/e/t findings in the audited run), and all six dated letters carried a wrong date. The "read in code, not yet
  proven" carrier above is still **untested**: no letter carried a handle in 23 completed runs, so the original `b180`
  letter has not reproduced.
- **Built:** a no-ids rule on 14 persona constants, `<letter_date>` in both cover-letter prompts, the analyze schemas
  reworded (`PROMPT_VERSION 2026-10-17.2`), a validator that re-asks once (a hard error only for `resume_content` /
  `cover_letter_content`), and a `leaked_handles` eval metric. After the change: no b/e/t handle in the completed
  runs, and all 12 dated letters carry the run date.
- **Open 1:** `walkthrough_coverletter_first-generation.png` still shows `b180` and `March 2025`. The capture script
  stopped at the Template to Generate step (no `generate` call logged); cause not established. The hero shot was
  recaptured and shows no ids.
- **Open 2:** `data-scientist-junior` grounding scores fell after the prompt changes (generate `2.1`, `3.2` to `1.2`,
  `1.2`; assemble `4.8` x4 to `1.2` once). Not established whether the change or run-to-run variance; the experiment
  is named in the dossier and not run.
- **Seen, not fixed here:** `_parse_or_retry`'s retry drops `max_tokens`; `pm-senior` generate mode intermittently gets
  an empty response (`Expecting value`); `evals/fixtures/synthetic/corpus` is picked up as a fixture and fails to
  load; analyses saved before the fix that already contain ids will keep feeding later prompts.

---
description: Re-run analyzer.generate() against a saved context_*.json — useful for iterating on prompts or debugging a specific generation.
argument-hint: <path-to-context_*.json>
allowed-tools:
  - Bash
  - Read
---

Re-run document generation using a previously-saved `context_set`, skipping the analyze step.

1. Validate the path argument resolves to `output/{user}/context_*.json` and the file exists. If not, ask the user for a valid path and stop.
2. Run a Python one-liner from the project root that:
   - Loads the context JSON
   - Pulls the saved `llm_analysis` from it (the analyze result was persisted there)
   - Calls `analyzer.generate(client, context, analysis)` with `username='replay:{original_user}'`
   - Writes the result to a sibling `replay_{timestamp}.json` file in the same directory
3. If the original directory contains a previous `resume_*.docx` or `cover_letter_*.docx`, diff the text content of the new replay output against them. Show only the substantive deltas — not formatting noise.
4. Print the new `latency_ms` and `cache_read_input_tokens` from the most recent line of `logs/llm_calls.jsonl`.
5. Ask the user whether to write the new output to `.docx` (would call `generator.generate_resume()`/`generate_cover_letter()`).

Do not delete or overwrite the original outputs.

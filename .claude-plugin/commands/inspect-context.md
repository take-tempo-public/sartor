---
description: Pretty-print and validate a saved context_set JSON against the schema.
argument-hint: <path-to-context_*.json>
allowed-tools:
  - Bash
  - Read
---

Make a saved `context_set` human-readable for debugging.

1. Validate the path argument exists and matches `output/**/context_*.json`. If not, ask the user for a valid path and stop.
2. Validate JSON syntax. If invalid, report the parse error with line number and stop.
3. If `evals/schemas/context_set.schema.json` exists AND `jsonschema` is installed in the active Python env, validate against the schema. Report any violations.
4. Print a structured summary, omitting the bulky text bodies:
   - **Timestamp**
   - **Candidate**: name, email, LinkedIn URL
   - **Primary resume**: filename, format, word count
   - **Supplemental resumes**: count and list of filenames
   - **JD**: word count + first two sentences
   - **Keyword overlap**: match score, count of `matched`, `missing_from_resume`, `only_in_resume`
   - **ATS warnings**: count + the warning strings (one per line)
   - **LLM analysis**: present (yes/no), and if yes, count of `essential_skills`, `suggestions`, `keyword_placement`
5. Do NOT print the full `resume.text`, full `job_description`, or full `profile_text` — that's the noise this command exists to filter out.

This is read-only. Don't modify the file.

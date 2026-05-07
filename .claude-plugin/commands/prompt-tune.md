---
description: A/B test a candidate edit to analyzer.SYSTEM_PROMPT against the eval suite — capture baseline, apply edit, re-run, report deltas.
argument-hint: [--subset smoke|full]
allowed-tools:
  - Bash
  - Read
  - Edit
---

Capture a baseline eval score, apply a user-provided prompt edit, re-run the eval, and report the per-rubric delta.

1. Confirm the working tree is clean (no uncommitted changes to `analyzer.py`). If it isn't, ask the user to stash or commit before proceeding — this skill makes a temporary edit and needs a clean revert path.
2. Run `python evals/runner.py --suite synthetic $ARGUMENTS` (defaulting `--subset full`) and capture the result file path. Parse out the per-rubric scores into a baseline table.
3. Ask the user for the candidate prompt edit:
   - Which lines of `analyzer.py:SYSTEM_PROMPT` (lines 19-42) to change
   - The proposed new wording
4. Apply the Edit. Bump `PROMPT_VERSION` to the next iteration (e.g., `2026-05-06.1` → `2026-05-06.2`).
5. Re-run `python evals/runner.py --suite synthetic $ARGUMENTS` at the same scope.
6. Print a side-by-side table: `rubric × baseline score × new score × delta`. Mark any rubric that regressed in red text (or `(REGRESSION)` if no color).
7. Ask whether to keep the prompt edit or revert.
   - **Keep**: leave the changes, suggest a commit message like `feat(prompts): tighten <rule> per <eval-fixture> regression`
   - **Revert**: undo both the SYSTEM_PROMPT edit and the `PROMPT_VERSION` bump

Do not commit on the user's behalf — they review the diff first.

---
description: A/B test a candidate edit to an analyzer system prompt against the eval suite via the prompt-override primitive — capture baseline, run candidate as an override, report deltas. analyzer.py is never edited during the trial.
argument-hint: [--subset smoke|full]
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---

A/B a candidate system-prompt edit against the eval suite using the
**prompt-override primitive** (`analyzer.prompt_overrides` + the runner's
`--prompt-overrides` flag). The candidate is injected at runtime, so `analyzer.py`
is **not edited during the trial** and the candidate run is logged as
`prompt_version=candidate:<hash>` (it never pollutes the dashboard's
score-over-time). The constant is only edited at the very end, if you choose Keep.

1. Confirm the working tree is clean (`git status`). It no longer needs a revert
   path for the trial itself (the override never touches `analyzer.py`), but a
   clean base keeps the optional final Keep edit reviewable.
2. **Baseline:** run `python evals/runner.py --suite synthetic $ARGUMENTS`
   (defaulting `--subset full`) with **no** overrides. Capture the result file
   path and parse the per-rubric scores into a baseline table.
3. Ask the user for the candidate edit:
   - **Which system-prompt constant** to tune (default `SYSTEM_PROMPT`; any key of
     `analyzer._BASE_SYSTEM_PROMPTS` is valid — e.g. `CLARIFY_SYSTEM_PROMPT`,
     `EXTRACTION_SYSTEM_PROMPT`).
   - The proposed wording change.
4. `Read` the current value of that constant from `analyzer.py`, apply the user's
   change to produce the **full** candidate text, and `Write` it to a temp file
   `evals/_prompt_tune_candidate.json` as a one-key object:
   `{"<CONSTANT_NAME>": "<full candidate prompt text>"}`.
   (Override values are full prompt text, not diffs.)
5. **Candidate:** run
   `python evals/runner.py --suite synthetic --prompt-overrides evals/_prompt_tune_candidate.json $ARGUMENTS`
   at the same scope. The run logs `prompt_version=candidate:<hash>`; note the
   hash from the runner's "PROMPT OVERRIDES ACTIVE" banner.
6. Print a side-by-side table: `rubric × baseline score × candidate score × delta`.
   Mark any regressed rubric in red (or `(REGRESSION)` if no color).
7. Ask whether to **Keep** or **Revert**:
   - **Keep:** `Edit` the chosen constant in `analyzer.py` to the candidate text,
     bump `PROMPT_VERSION` to the next iteration (e.g. `2026-06-01.4` →
     `2026-06-01.5`) in the same edit, and suggest (a) a `evals/TUNING_LOG.md`
     entry following its four-question structure (what changed / why / result with
     the baseline-vs-candidate scores / what we learned) and (b) a commit message
     like `feat(prompts): tighten <rule> per <fixture> regression`. Delete the
     temp candidate JSON.
   - **Revert:** just delete the temp candidate JSON. Nothing in `analyzer.py`
     changed, so there is no code to undo.

Do not commit on the user's behalf — they review the diff first. Add
`evals/_prompt_tune_candidate.json` to `.gitignore` (or always delete it) so a
candidate file is never committed.

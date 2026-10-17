# Diagnosis — LLM prose contains internal id handles (b173, b180) and the cover letter invents its date

> **Status:** Hypothesis A (ids leak into analysis and clarify prose) is **observed**, in every fixture-run. The
> invented letter date is **observed** (6 of 6 dated letters wrong). Hypothesis B (a letter's handle arrives through
> the analysis) is **untested, not refuted**: no letter carried a handle in 11 letters, so the original `b180`
> letter has not reproduced.
> **Branch:** `fix/llm-handle-leak-and-letter-date` (work item 140)

---

## Symptom

On a live Sonnet 5 screenshot capture (2026-10-01, synthetic Priya fixture) the user-visible text carried
internal ids, and the cover letter carried a date the run could not have produced:

- Step 1 analysis, "Where to focus": "…implied by company name and **b173** ('4M+ daily shipments')…"
- Cover letter: "Earlier, at **b180**, I led a monolithic-to-event-driven refactor…", dated **"March 2025"**
  on a run made 2026-10-01.

---

## Observed

- The two screenshots exist in the repo, both written Oct 2 10:23:
  `docs/screenshots/readme_hero_wizard-step1-filled.png` (153410 bytes) and
  `docs/screenshots/walkthrough_coverletter_first-generation.png` (153728 bytes).
- The item's own record of the capture, quoting both texts and the date: `docs/dev/work/items/0140-llm-output-leaks-bullet-ids-and-invents-letter-date.md:18-25`.
- No prompt or response artifact of that run survives. Command run on this branch:
  `grep -rlE "b173|b180" output logs` → no files listed. The only path to the original wording is the two PNGs.
- The cover-letter FORMAT rule demands a date and nothing supplies one:
  `analyzer.py:2434` reads `  - Date, then hiring manager name/title/company (use "Hiring Manager" if name unknown)`.
- The only clock call in `analyzer.py` is the telemetry timestamp: `grep -n "date.today\|datetime.now" analyzer.py`
  → `1452:            "timestamp": datetime.now(timezone.utc).isoformat(),`.
- Bullets are handed to the model as `<bullet id="b{id}" …>` (`analyzer.py:1192`), experiences as `id="e{id}"`
  (`:1163`) and titles as `id="t{id}"` (`:1184`). No prompt constant forbids ids in prose.
- The analyze synthesis prompt tells the model to "cite an extracted skill or résumé item by name"
  (`analyzer.py:1868`) and to "cite the specific signal by name" (`:1847`).
- The cover-letter user prompt (`analyzer.py:2998-3035`) contains no `id="…"` markup. It does include
  `Strategy: {analysis.get("overall_strategy", "")}` (`:3010`).

- **Baseline run 1, instrument commit `6f00573`, prompts unchanged, `PROMPT_VERSION` `2026-08-14.1`** (live, corpus seed
  `evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json`, smoke subset = 3 fixtures; cost `$0.243` per mode,
  `$0.485` total from the result records' `cost_usd`):
  - Command: `python evals/runner.py --suite synthetic --subset smoke --seed <seed> --mode generate` →
    `evals/results/20261017_091327Z.jsonl`; the same with `--mode assemble` → `evals/results/20261017_091722Z.jsonl`.
  - `leaked_handles.total` per fixture, from the runner's log lines: generate 18 (data-scientist-junior), 15
    (sre-mid-level); assemble 15, 12, 29. All in the `analysis` and `clarify` sections (plus 2 in `changes_made`,
    generate mode). **UNAUDITED:** the records held paths and handles but no text, and no response text is persisted
    anywhere (`logs/llm_calls.jsonl` has token counts only), so I could not confirm these are leaks and not detector
    false positives. The next run records a snippet per finding.
  - `letter_carriers` was `{}` in all five fixture-runs: **no handle was found in any cover letter.** The original
    "Earlier, at b180" letter did not reproduce at this n.
  - **Letter date:** the three letters that carried a date in their first lines were all wrong against the run date
    `October 2026`: `October 2024` (generate, data-scientist-junior), `February 2025` (assemble, data-scientist-junior),
    `April 2025` (assemble, sre-mid-level). The other two letters carried no date in their first 3 non-blank lines.
  - `pm-senior`, generate mode: `Pipeline failed … LLM response failed validation: Expecting value: line 1 column 1
    (char 0)` after 2 attempts, call `generate`. Not examined; no handle or date claim rests on it.
  - The `corpus` directory under `evals/fixtures/synthetic/` is picked up as a fixture and fails to load
    (`Fixture load failed: corpus — … corpus\jd.txt`) in both runs. Pre-existing, unrelated to this item.

- **Baseline run 2, instrument commit `a970033` (each finding now carries a snippet), prompts unchanged,
  `PROMPT_VERSION` `2026-08-14.1`.** Same commands and seed as run 1. Results:
  `evals/results/20261017_092238Z.jsonl` (generate) and `evals/results/20261017_092642Z.jsonl` (assemble). Cost from
  the records' `cost_usd`: `$0.400` and `$0.367`; the three live baseline runs so far total `$1.252`.
  - **The findings are real handle mentions, not detector false positives.** Audited from the snippets, for example:
    `analysis.comparison.strengths[1]` "e102 bullet b304 describes building a streaming pipeline…";
    `analysis.comparison.gaps[2]` "…b303 (incident review process) and b305 (on-call rotation ownership)…";
    `analysis.suggestions[2].section` "Experience – Calder Analytics (b304)";
    `clarify.questions[1].text` "That 18-hour-to-5-minute pipeline in e102: did you analyze…" (question text a user reads);
    `proofread_notes[1]` "Checked bullet text b301, b302, b303, b304, b305, b306 reproduced verbatim".
  - **By section** (first-occurrence records per fixture): generate mode `analysis` 49, `clarify` 14, `changes_made`
    2, `proofread_notes` 6; assemble mode `analysis` 38, `clarify` 6. **By kind:** generate `b` 53, `e` 12, `q` 5,
    `t` 1; assemble `b` 39, `q` 5. Every one of the 6 fixture-runs has findings in `analysis`, including the paths the
    UI's "Where to focus" list is built from (`analysis.comparison.gaps[...]`, `static/app.js:1244-1249`, read).
  - **The `q` findings are all in `clarify.reasoning` of one fixture** (`pm-senior`: "(q1, q2) … (q3) … (q4) … (q5)").
    That is the response referring to its own question ids, not an input handle leaking. It is counted by the metric but
    is not the defect; the C3 guard must not treat a clarify response's own `q` ids as leaks.
  - **No cover letter carried a handle.** `letter_carriers` was `{}` for all 6 fixture-runs here (and all 5 in run 1).
    The original "Earlier, at b180" letter has not reproduced in 11 letters.
  - **Letter date:** across both baselines, 6 letters carried a date in their first lines
    (`October 2024`, `February 2025`, `April 2025`, `October 2024`, `June 2024`, `November 2025`); **all 6 differ from the
    run date `October 2026`.** One letter (`pm-senior`, assemble, run 2) opens "I need to flag a mismatch rather than
    force a fit." — a different behaviour, not examined.
- **Letter-date mechanism, still read not observed:** the letter prompt contains no date and no clock call exists
  outside telemetry (above); six wrong dates fit "the model writes one because FORMAT asks for one", but no run has yet
  shown the date disappearing when it is supplied. That is what the candidate run tests.

---

## Falsified

_(Nothing yet.)_

---

## Inferred

**Hypothesis A (unproven):** the analyze synthesis step, asked to cite items "by name", has only ids as names for
corpus bullets, so it writes them into `comparison.gaps` / `suggestions` (the "Where to focus" source).

**Hypothesis B (unproven, by elimination):** the cover letter did not see the corpus block, so `b180` reached it
through `<analysis>` — most likely `overall_strategy` — which was itself written under Hypothesis A. Rival carriers
not excluded: `last_generated_resume` content, a prior letter draft, clarification answers.

**Hypothesis C (unproven):** the invented date is the model satisfying a FORMAT rule that asks for a date and gives
none.

**The gap:** nothing in A or B has been seen in a captured response. I would have to SEE the upstream field that
holds `b180` to know B.

---

## Falsification

**Instrument first (C1):** a deterministic scan, `hardening.find_leaked_handles`, wired into the eval runner as a
sibling record key `leaked_handles`. It scans every string leaf of the analysis, the clarify output, the generated
résumé and letter, and (assemble mode) the recommend outputs — all handle kinds, not just `b`-ids and not just the
letter. It records `letter_carriers`: for each handle in the letter, which upstream fields also contain it.

**Baseline (C2):** run the generate and assemble modes against the corpus seed on HEAD of the instrument commit.

- **If a letter handle appears and an upstream field also holds it:** B is supported for that handle.
- **If a letter handle appears and NO upstream field holds it:** B is **false**. The carrier is something else
  (prior draft, résumé content, clarification). Stop; widen the instrument; do not apply the prompt fix as a
  cure for that path.
- **If no handle appears anywhere in the baseline:** the leak did not reproduce at n=1. That does not show the
  prompt rule works; the validator is then the guarantee and the run only shows no regression. Say so plainly.
- **Date:** if the baseline letter carries a date that differs from the run date, C is supported. If it carries
  none or the right one, C did not reproduce.

---

## The fix

_Not yet. Only after the baseline has run._

---

## Acceptance bar

_To be filled with the baseline and candidate result files._

# Diagnosis — LLM prose contains internal id handles (b173, b180) and the cover letter invents its date

> **Status:** hypothesis only. The carrier of `b180` into the letter is **inferred by elimination, not observed**.
> The baseline run (C2) is what settles it.
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

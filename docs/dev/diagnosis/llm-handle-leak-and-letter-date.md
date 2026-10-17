# Diagnosis — LLM prose contains internal id handles (b173, b180) and the cover letter invents its date

> **Status:** Hypothesis A (ids leak into analysis and clarify prose) is **observed**, in every baseline fixture-run,
> and the rule plus validator removed it from every completed candidate run. The invented letter date is **observed**
> (6 of 6 dated baseline letters wrong, 0 of 4 wrong with `<letter_date>`). Hypothesis B (a letter's handle arrives
> through the analysis) is **untested, not refuted**: no letter carried a handle in 15 letters, so the original `b180`
> letter has not reproduced. **Open cost:** the validator turned 1 of 6 analyze pipelines into a hard error.
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
  the records' `cost_usd`: `$0.400` and `$0.367`; the four live baseline runs (two modes, run twice: `$0.243 + $0.242 + $0.400 + $0.367`) total `$1.252`.
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

- **Cost, corrected.** The `$1.252` above sums `cost_usd` on the result records, which a failed fixture does not
  carry. Summed from `logs/llm_calls.jsonl` with `hardening.compute_call_cost` over each run's time window instead:
  baseline 1 `$0.649`, baseline 2 `$0.767`, candidate `$0.596`: **`$2.013` for all three pairs**, at the owner's
  `~$2` approval before the screenshot recapture (`~$0.27`).

- **Candidate run, commit `54674d0`, `PROMPT_VERSION` `2026-10-17.1`** (rule on 14 personas, `<letter_date>`, guard
  active). Same commands and seed. Results: `evals/results/20261017_094902Z.jsonl` (generate) and
  `evals/results/20261017_095211Z.jsonl` (assemble). All records read `prompt_version 2026-10-17.1`.
  - **Letter date:** all four letters that carried a date read `October 2026` (run date `October 2026`), against 0 of 6
    in the baselines. The `<letter_date>` block fixed the date: the mechanism is now observed, not only read.
  - **Handles in completed runs:** the four fixture-runs that completed have **zero b/e/t handles** (baseline 2:
    105 in the six that completed, every one of the six with some). What remains is 5 `q` findings per affected run, all
    in `clarify.reasoning` ("experience_probe q1, q3"): the clarify response numbering its own questions, the
    self-reference recorded above as not the defect.
  - **The cost of the validator, observed:** `sre-mid-level` triggered it in both modes. Generate mode: the Haiku
    extraction wrote ids into `keyword_placement[2].suggested_location` on **both** attempts, so `analyze_extraction`
    raised and **the pipeline failed**: `LLM response failed validation: Prose contains internal id handle(s) b303 (first
    at keyword_placement[2].suggested_location)…`. Assemble mode: `analyze_extraction` retried once (`b305, b303`) and
    `analyze_synthesis` retried once (`b303, b305, b301, b302`, first at `comparison.strengths[0]`); both recovered.
    So 3 of the 12 analyze passes in the candidate run needed a retry, and 1 of 6 analyze pipelines ended in the hard
    error the owner accepted. n=6; the rate is not estimated here.
  - **The rule alone did not stop the extraction persona** (`EXTRACTION_SYSTEM_PROMPT` carries it). In the same
    fixture the other five fixture-runs wrote no handles in the analysis.
  - **Unrelated, seen in both baseline 1 and the candidate:** `pm-senior`, generate mode, `Expecting value: line 1
    column 1 (char 0)` on both attempts (empty or non-JSON response; it did not occur in baseline 2). Not examined; no
    claim rests on it.
  - **Scores:** `data-scientist-junior` generate-mode grounding read 2.1, 3.2, then 1.2. Its judge reasons name an
    identity mismatch between the fixture and the corpus seed ("not the candidate named in the fixture"), i.e. the
    seed is a platform engineer and the fixture a junior data scientist, so low generate-mode scores are expected
    for that pairing; assemble mode read 4.8, 4.8, 4.8. n=1 per arm: not attributed to the change either way.

- **Verification run, commit `2f4126b`** (same prompts as the candidate; the failure-mode change: a repeated leak is a
  hard error only in `resume_content` / `cover_letter_content`). Same commands and seed. Results:
  `evals/results/20261017_104737Z.jsonl` (generate) and `evals/results/20261017_105248Z.jsonl` (assemble). Cost from
  telemetry: `$0.818` (estimate was `~$0.65`); cumulative `$2.831`.
  - **No pipeline errors from the validator.** All six analyses completed. `pm-senior` generate hit the unrelated
    `Expecting value … (char 0)` empty-response failure on attempt 1 and recovered on the retry this time.
  - **One soft acceptance:** `sre-mid-level` assemble, `analyze_extraction`: attempt 2 still leaked (`b303, b302, b305`
    in `keyword_placement`), was accepted with the logged warning `Accepting response after 2 attempts: handle leak in
    a non-shipped field only`, and its 5 findings are exactly those b-ids in `keyword_placement[*].suggested_location`
    and `.how` (for example "Expand b303 (incident review process) bullet at Meridian Frei…").
  - **Letter date:** all six letters carry `October 2026` (cumulative with the candidate run: 10 of 10 dated letters
    correct, against 0 of 6 in the baselines). **No letter carried a handle** (`letter_carriers {}` throughout).
  - **Handles elsewhere:** 0 b/e/t handles in five of the six fixture-runs; the sixth is the soft acceptance above; the
    remaining `q` findings are the clarify self-references recorded earlier.
  - **The retry cost, measured from `logs/llm_calls.jsonl` (`*_retry` rows of the two analyze personas):** verification
    run 6 retry calls, `$0.132` = 16% of `$0.818`, +112 s of call latency across 6 analyses (4 extraction, 2 synthesis);
    candidate run 3 retry calls, `$0.065` = 11%, +58 s. **4 of the 6 analyses in the verification run needed at least
    one guard retry.**
  - **Where the extraction retries come from (read, then supported by the snippets):** the extraction schema asks for
    `"suggested_location": "Where in the résumé to add it (section / bullet area)"` (`analyzer.py:2029`) while the
    prompt gives the model bullets only as `id="b303"` markup, so "bullet area" is answered with the id. The synthesis
    prompt likewise asks the model to "cite … by name" (`analyzer.py:~1868`). The shared rule alone did not stop it.

- **Targeted verification, commit `692a392`, `PROMPT_VERSION 2026-10-17.2`** (schema rewording: extraction
  `keyword_placement` and synthesis `strengths`/`section`/`action` say to name a bullet by company and role or a quote,
  never an id). Assemble mode, `sre-mid-level` and `data-scientist-junior` only. Results:
  `evals/results/20261017_132655Z.jsonl`, `evals/results/20261017_132814Z.jsonl`. Telemetry cost `$0.193`; cumulative `$3.024`.
  - **Guard retries: 1 retry call across the 2 analyses** (`analyze_extraction_retry` on `data-scientist-junior`),
    against 3 on the same two fixtures in assemble mode under `.1` (`$0.132`/16% of that run was retries). `sre-mid-level`,
    which retried on both attempts and once hard-failed under `.1`, needed none. n=2 analyses: a direction, not a rate.
  - **Handles:** `data-scientist-junior` 0 findings; `sre-mid-level` 5, all the clarify response's own `q1..q5`
    self-references. Both letters read `October 17, 2026` (the full date, copied from `<letter_date>`).
  - **Open, not explained: the `data-scientist-junior` grounding score.** Same fixture, same corpus seed (a platform
    engineer; the fixture expects a junior data scientist, a mismatch the judge names in every run):
    generate mode `2.1`, `3.2` under `.0814.1`, then `1.2`, `1.2` under `.1`; assemble mode `4.8`, `4.8` under the old
    prompts, `4.8`, `4.8` under `.1`, then **`1.2` under `.2`** (`failed_rules`: `invented_credential`, `invented_metric`,
    `jd_pandering`, `scope_inflation`; the letter claimed "building hands-on fluency in scikit-learn and statsmodels now").
    The same kind of claim is flagged in old-prompt runs too (generate `2.1`), so the claim type is not new, but the
    lower scores follow the prompt changes and n is 1–2 per arm. **I have not established whether this is the change or
    run-to-run variance.** What would settle it: repeat this fixture N times on the old and new prompts with
    `--prompt-overrides`, which costs about `$0.15` per run per arm. Not done; not approved.
  - One stray result file in the directory, `evals/results/20261017_093904Z.jsonl`, is from a pytest run
    (`test_eval_runner`, stubbed), not a live run; it is excluded from every figure above.

---

- **Screenshot recapture, 2026-10-17** (`python -m scripts.capture_screenshots --headless --keep-user` against
  `python app.py`, prompts at `2026-10-17.2`):
  - `readme_hero_wizard-step1-filled.png` **recaptured and read**: its "Where to Focus" list is plain language
    ("Consumer-lag debugging is mentioned in only a few corpus bullet variants…"), with no id. That demo corpus ships
    `b173`…`b180`, the very ids in the original symptom (59 handles). The kept run context
    (`output/demo/context_20261017_063211.json`, since removed) scanned offline with `find_leaked_handles`:
    0 leaking leaves across `llm_analysis` and `clarification_questions`. n=1 real run, which itself needed one
    `analyze_extraction_retry`.
  - **`walkthrough_coverletter_first-generation.png` NOT recaptured.** The script stopped at step 9
    (`WizardTemplatePage.continue_to_generate` → `wait_for_selector(Wizard.PANEL_GENERATE)` timed out;
    `scripts/capture_screenshots.py:529`, `ui_pages/wizard_template.py:46`). `logs/llm_calls.jsonl` for the window shows
    analyze, clarify, recommend and draft_summary all `ok` and **no `generate` call**, and the kept context holds an
    `approved_composition`: the failure is in the UI step between Template and Generate, not in an LLM call. **Cause not
    established.** The committed image still shows `b180` and `March 2025`.
  - The seven other PNGs that run overwrote were restored with `git checkout` (they were captured against an existing
    `demo` corpus: the script printed "corpus already has 3 experiences; skipping import", so
    `walkthrough_setup_corpus-empty.png` showed a full corpus).
  - The `demo` candidate (id 5, created `2026-05-26`, 16 applications before this run, now 17) predates this session; its
    experiences carry month dates (`2023-01`, `2019-01`, `2017-01`), so the month-gate explanation I first guessed for
    the failure does not fit (see Falsified). The server's own logger went silent after the Alembic migration at
    start-up, so the server log gave no evidence either way.
  - Cost of the capture, telemetry window `13:31`–`13:33Z`: 6 calls (`analyze_extraction` ×2 incl. retry,
    `analyze_synthesis`, `clarify`, `recommend`, `draft_summary`); cumulative with the evals about `$3.3`.

---

## Falsified

- **"The capture failure is the item 139 stale-demo-rows / month gate problem."** Written down as a guess before
  checking; the demo experiences have `YYYY-MM` start dates, so the month gate does not apply. Not the cause. The real
  cause is open.
- **"The first baseline's 12–29 findings per fixture may be detector false positives."** Checked against the snippets in
  run 2: they are genuine handle mentions.
- **Hypothesis B, as a test:** not falsified and not confirmed. The baselines produced no letter carrying a handle (0 of
  15), so `letter_carriers` never had a case to map.

---

## Inferred

**Hypothesis B (still unproven):** the original `b180` reached the letter through the analysis prose it is given
(`<analysis>` `overall_strategy`), which was itself written under hypothesis A. It never reproduced, so this is the one
claim here that rests on elimination alone. The guard covers the letter regardless (a leak in `cover_letter_content` is
a hard error).

**Mechanism of the extraction-retry cost (read, then supported by 3 snippets and a drop from 3 retry calls to 1):** the
extraction schema asked for a "bullet area" while naming bullets only by id. The reworded schema cut guard retries; the
sample is two analyses.

**Why `data-scientist-junior` scores fell (unknown):** see Observed. Not claimed.

---

## Falsification

**What was run, in order:** the instrument (`6f00573`, then `a970033` adding snippets); baseline runs 1 and 2 on
unchanged prompts; the candidate run; the verification run after the failure-mode change; the targeted run after the
schema rewording. Each outcome is under Observed. Confirmed by observation: hypothesis A (every baseline fixture-run)
and hypothesis C (6 of 6 dated baseline letters wrong; 10 of 10 correct once `<letter_date>` was supplied, plus the
two in the last targeted run). Not testable at this n: hypothesis B.

---

## The fix

- **Prompt rule** (`_NO_HANDLES_IN_PROSE_RULE`, `analyzer.py`): never write an id in prose, with an OK/NOT OK pair, on the
  14 personas shown ids or analysis prose. The critique prompt's `source bullet b41` example, which taught the leak, was
  reworded.
- **Schemas** (`PROMPT_VERSION 2026-10-17.2`): the analyze extraction and synthesis schemas no longer ask for a "bullet
  area" without a way to name it; they say company and role or a quote, never an id.
- **Runtime guard** (`_LLMResponse.reject_handle_leaks`, `_parse_or_retry*`): a prose handle the prompt shipped makes the
  call retry once. If it persists, it raises `LLMResponseError` only when the leak is in `resume_content` /
  `cover_letter_content`; elsewhere the response is accepted with a logged warning (owner decision after the candidate
  run's 1-in-6 hard error). Wired into every call that ships ids; four that ship none are exempt with a reason; a test
  fails any new `_parse_or_retry*` call that is neither (C-11).
- **Letter date**: both cover-letter prompts carry `<letter_date>` from one clock seam, in the user prompt only.
- **Instrument** (kept): `leaked_handles` per record in `evals/runner.py`, with snippets.

---

## Acceptance bar

Met, with the sample sizes stated: no b/e/t handle in 4 of 4 completed candidate fixture-runs, 5 of 6 verification
runs (the sixth is one soft acceptance), and 2 of 2 targeted runs; letters carry the run date in every dated letter after
the change (12 of 12 across the three post-change runs, against 0 of 6 before). The result files are cited under
Observed.

**Not met, stated plainly:** (1) `walkthrough_coverletter_first-generation.png` is not recaptured (cause of the
capture failure open); (2) the `data-scientist-junior` score drop is unexplained; (3) hypothesis B is untested.

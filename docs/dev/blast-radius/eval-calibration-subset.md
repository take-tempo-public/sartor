# Blast radius — eval-calibration-subset

> **Branch:** `feat/eval-calibration-subset`
> **Status:** enumeration complete before the first paid call and before any edit to a consumer (2026-10-31). Measurements are appended under "Measurements" in the turn they are taken (charter C-8).

Item 194, scope 3 (the calibration run), as a staged subset. Owner decisions (chat, 2026-10-31): run scope 3 as a paid ladder with a **total cap of $5.00** over this branch's traces; **judge-to-judge agreement is deferred to item 189** (no second judge exists, `JUDGE_MODEL` is pinned at `evals/runner.py:131`, there is no `--judge-model` flag, and a result record does not keep the judged text, `evals/runner.py:469`); the sample is 1 pilot, then 24 cells in assemble mode, then 4 pairs.

---

## Surface

- `evals/catalog/costs.json`: rewritten whole by `python -m evals.eval_catalog measure --write` (`evals/eval_catalog.py:383-384`). Expected change: `judge_grade` and `judge_distinctiveness` gain rows, `dataset_author` is added, and every `measured_on` is restamped. Never hand-edited.
- `tests/test_eval_spend.py`: five assertions encode "the two judge kinds are unmeasured" against the real `costs.json` (lines 135, 169-172, 188, 203-204). They break the moment the judges are priced. The file's own docstring (lines 6-8) says re-measuring does not break it; that is true for the four measured kinds and false for the judges.
- `docs/dev/work/items/0194-eval-dataset-v1-finish.md`, `0189-eval-judge-calibration.md`, `docs/dev/eval-redesign-design.md`, `CHANGELOG.md`: prose updates only.

Not touched: `evals/runner.py`, `evals/eval_catalog.py`, any golden cell, facts file, manifest hash, prompt or pin, `evals/prompt_hashes.json`. `git diff main -- evals/golden/` must stay empty and `golden_set check` must keep printing `OK (96 cells)`.

---

## Enumeration

Commands run on `main` at `de08716` (whole tracked tree, 2026-10-31):

```
grep -rln "costs.json" (py, toml, yml, md; excluding node_modules and docs/dev/handoffs)  -> 15 files
  code:  evals/eval_catalog.py  evals/runner.py
  tests: tests/test_eval_catalog.py  tests/test_eval_spend.py  tests/test_data_root.py
  docs:  CHANGELOG.md  evals/README.md  docs/dev/eval-redesign-design.md  docs/wiki/pages/eval-harness.md  docs/wiki/log.md
         docs/dev/work/BOARD.md  docs/dev/work/items/0180-... 0182-...  docs/dev/blast-radius/eval-catalog-skeleton.md  eval-dataset-v1-credentials.md
blast_radius.py registry: grep "costs.json|evals/runner|golden|eval_catalog" scripts/enforcement/blast_radius.py -> 0 hits (not a gated surface)
evals/eval_catalog.py: COSTS_PATH :33; read_costs :257-276 (validates integers); aggregate :291-321; measure --write :355-385
evals/runner.py: estimate_spend :1111 (a kind absent from costs.json is `unmeasured`, :1130-1133); format_catalog_list :1176 (unmeasured shows " - ")
tests/test_eval_catalog.py: reads costs.json at :288 (non-empty check) and uses a tmp copy at :503-511  -> no value pinned
tests/test_data_root.py:279: a comment only
tests/test_eval_spend.py: pins "unmeasured" for the judges at :135 :169-172 :188 :203-204 (read the file, lines 1-215)
```

Negative results: no test asserts a numeric token mean; `test_eval_spend.py` derives the measured kinds' expected values from `costs.json` itself (`_price`, :53-63), so re-measuring those four does not break it.

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/catalog/costs.json` | update, by `measure --write` only | The surface. Judges become priced; `--estimate` stops listing them as unmeasured. |
| 2 | `evals/runner.py:1111-1143` `estimate_spend` | no change | Prices any kind present in `costs.json`; the judge kinds' catalog entries already exist (`status = "pending"`, `pending_on = 189`). |
| 3 | `evals/runner.py:1176` `format_catalog_list` | no change | Shows the measured $/call once a row exists. |
| 4 | `evals/eval_catalog.py:257-276` `read_costs` | no change | Validates integer means, a field set per kind; the new rows are the same shape. |
| 5 | `tests/test_eval_spend.py:123-136, 162-172, 182-195, 198-204` | **update in the same commit as `costs.json`** | Each asserts "judge kinds unmeasured" against the real file. Make them independent of the file's contents for the unmeasured case (patch `cat.read_costs` to drop the judge rows), and add one test that a priced judge kind enters `per_kind_usd`. Tighten on the new invariant (memory `enforcing-test-tighten-on-removal`). |
| 6 | `tests/test_eval_catalog.py:288` | no change | Only asserts the file is non-empty. |
| 7 | `tests/test_data_root.py:279` | no change | A comment. |
| 8 | `evals/README.md`, `docs/wiki/pages/eval-harness.md` | check at wiki step | May say the judge kinds are unmeasured; edit only if they do. |
| 9 | `docs/dev/eval-redesign-design.md` tier table and statistics (~:698-711) | update | "Not run; step 3b's calibration run measures it" gets the measured numbers, cited here. |

---

## Sample (derived by a free script, then fixed)

Rule: the 24 professions sorted by name; profession `i` takes `levels[i % 4]` with `levels = [entry, mid, senior, lead]` (6 of each level, by construction). The fixture directory is the cell's `<cell>--<jd-slug>`. Setting coverage of the 24, read from each `profile.json`'s `jds[0].setting`: health-nonprofit 7, small-business 6, enterprise 6, startup 4, **public-sector 1** (`security-mid`). All five settings are present, so no swap was needed. Pairs: the first 2 `advance` and first 2 `change` in manifest order. The sample is purposive: it supports "these strata read as follows", not a rate over the 96.

Pilot: `web-backend-lead--freight-startup` (a lead-tier technology cell).

Free rehearsal (`runner.py --fixture <dir> --mode assemble --estimate`, 28 of 28 exit 0): **$0.1062 per cell, $0.0843 per pair, $2.886 in all, judges excluded** (they are unmeasured). `REHEARSAL_FAILURES=0`.

Cells (24): accounting-entry--tax-firm, admin-assistant-mid--freight-company, carpenter-foreman-senior--residential-builder, construction-pm-lead--design-build, customer-support-entry--subscription-box, data-ml-mid--health-research, electrician-senior--industrial-contractor, hardware-embedded-lead--robotics-startup, hr-entry--food-processing, hvac-technician-mid--residential-hvac, logistics-driving-senior--produce-hauler, medical-assistant-lead--medical-group, mobile-entry--fitness-startup, product-mgmt-mid--commerce-enterprise, project-mgmt-senior--medical-center, registered-nurse-lead--childrens-hospital, sales-entry--office-supply, security-mid--state-agency, social-services-senior--youth-alliance, sre-ops-lead--hospital-network, teacher-entry--charter-network, ux-design-mid--insurance-digital, visual-design-senior--home-goods, web-backend-lead--freight-startup.

Pairs (4): pair--accounting-entry-to-accounting-mid, pair--admin-assistant-mid-to-admin-assistant-senior, pair--web-backend-mid-to-data-ml-mid, pair--mobile-lead-to-ux-design-lead.

---

## Stop rules (fixed before any spend)

- Spend is the **call log summed by trace id** (`hardening.compute_call_cost` over rows carrying this branch's trace ids), never a record's `cost_usd` and never the driver's own counter. Total cap **$5.00**; each runner call also carries `--max-spend 0.40`.
- The driver stops before the next fixture if (spent so far) + (the dearest fixture so far) would exceed $5.00.
- Stop and look on a pipeline error, a missing `eval_composite` record, or more than 2 `judge_error` records. `scenario_misaligned` is a measurement, not a stop.
- The harness never runs alongside pytest or the gate (memory `reference-eval-harness-auth-and-cost`: that caused transient `judge_error`s).
- After the pilot, **stop and report to the owner**; the sweep starts only on their go.

---

## Deferred

- **Judge-to-judge agreement (scope 3's second measurement):** moved to item 189 by the owner. This branch records the judge costs and the `judge_error` rate it observed, which that item can use. It is not measured here; nothing on this branch may be read as agreement.
- **Generate-mode `scenario_misaligned` rate:** not run; the owner chose assemble only.
- **A list or tier flag for the runner:** not built (step 4's flag work). The cost is 28 process starts.
- **Hand-reading the generated résumés:** impossible, records do not keep the text (`runner.py:469`). The read is the judges' reasons and the records.
- **Entry call-log total.** The whole log sums to $59.9670 over 1,747 rows (17 rows on `claude-sonnet-4-20250514` price at $0.00 because that model has no pricing entry). The handoff's $13.0866 is the author-spend figure; I did not reconcile the two. This branch's spend is measured by trace id, so the difference does not affect the cap.

---

## Verification

- `python -m evals.golden_set check` prints `OK (96 cells)` before (done, 2026-10-31) and after; `git diff main -- evals/golden/` is empty.
- After `measure --write`: `costs.json` has `judge_grade` and `judge_distinctiveness` rows; `runner.py --suite golden-v1 --estimate` no longer lists them as unmeasured.
- `pytest tests/test_eval_spend.py tests/test_eval_catalog.py` pass, with the updated unmeasured-case tests failing first against the new `costs.json` (red, then green).
- The gate: `python -m scripts.gate`, cited via `--result`.

---

## Measurements

_(appended as taken: pilot, sweep, analysis, re-measure)_

```toml
schema = 1
id = 183
kind = "item"
title = "Eval redesign step 3a: dataset format, generator, per-cell seeds, reachability check"
status = "closed"
depends_on = [182]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-format"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-dataset-format.md"]
summary = "Step 3a, no paid call: golden-set format, stub-tested generator, per-cell seeds, reachability check, 3 pilots (3b: 191)."
resolution = "Built and merged as PR #200 (acf6d6f, 2026-10-23); the owner asked for it to be closed on 2026-10-27 (docs/close-eval-items-182-183-193). The 2026-10-21 list of what was still open did not get done here, it moved: tier sizes and the O*NET and DDaT re-reads are item 191's, and the C-2 route for the USAJOBS fetch was settled as no fetch (design doc 6.5, decided 2026-10-27, item 193). The generator has never made a real call."
verified_by = [
  "tests/test_golden_set.py",
  "tests/test_golden_author.py",
  "tests/test_golden_reachability.py",
  "tests/test_eval_golden_runner.py",
  "PR #200 merge acf6d6f: python -m scripts.ci_wait 200 exit 0 (read 2026-10-27, after the merge), no absorbed reruns, required checks green (CI run 40025893744)",
]
```

Step 3 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 3. Scope lives there. The owner split the step on 2026-10-22: this item is 3a; the paid generation of the 48 cells, the calibration run and the retirement of `evals/fixtures/synthetic/` are item 191.
Re-read the O*NET and dataset licence pages at the primary source before committing anything (the design doc's research is reported, not verified). The on-demand fetch is an outbound connection: charter C-2 names two destinations, so it takes the D-6 opt-in route and passes `tests/test_egress_allowlist.py`, or returns to the owner as an amendment.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

### 2026-10-20 -- the owner widened the dataset requirement; second research pass recorded (docs/eval-dataset-research)

Owner, 2026-10-20: the golden set has only three tech personas at one level each, and the v1 set becomes ground truth for later releases, so it needs more variation (IT and development, security, administration, project and product management, design and UX, plus other sectors) and a deeper open-set research pass **before v1**. Design doc sections 6.1 to 6.3 record that pass (each row marked reported or raw-read) and 6.4 is the matrix proposal; section 8 questions 9 to 12 are unanswered.

What this step must decide or do, given the research: (1) the profession axis, option A, B or C in 6.4 (recommended B: 12 professions by 4 levels, 48 cells); (2) the golden set's composition, all-authored from O*NET and a level ladder (recommended) or with committed real postings (USAJOBS's terms were read in a browser on 2026-10-20 and permit it, with a carve-out for separately identified restricted content, contact names to scrub, and no rate-limit circumvention; NYC Jobs still needs a ruling); (3) how non-tech levels are defined, since no open ladder was found; (4) final tier sizes from the calibration run's measured cost, not from the 6.4 guess; (5) the C-2 route for the exploration fetch. Re-read at the primary source anything a decision rests on; the tool-mediated rows in 6.1 to 6.3 are not enough.

### 2026-10-21 -- the owner answered section 8 questions 9 to 12 (docs/eval-dataset-decisions)

Decided (recorded in the design doc's section 8 and 6.4): (1) **profession axis: option B**, 12 professions by 4 levels, 48 cells, tech split into six families; (2) **golden set all-authored** from O*NET and a level ladder, no committed third-party posting or résumé text; (3) **non-tech levels: the authored rule is accepted**, written in the dataset manifest and marked authored, not sourced; (5) **exploration fetch: USAJOBS only**, NYC Jobs not targeted.

Still open for this step: (4) tier sizes, from the calibration run's measured cost and not from the 6.4 guess; the C-2 route for the USAJOBS fetch (D-6 opt-in and `tests/test_egress_allowlist.py`, or an amendment back to the owner); re-reading the USAJOBS terms at the start of the step, since the page shows no effective date; the API key, which the owner registers; and the primary-source licence re-reads (O*NET's "Except as noted below" text, the DDaT ladders for roles other than software developer) before any of it is relied on. The status stays blocked on item 182.

### 2026-10-22 -- unblocked; split into 3a and 3b; started on feat/eval-dataset-format

Item 182 landed (PR #199, merge `186a064`), so this item is unblocked. The owner chose this item and decided, in plan mode:
- **Split.** This item is **3a**, no paid call: the cell format, the profile builder, a prose generator script (built and tested against a stub client, not run for real), per-cell seeds in the runner, the reachability check, and three pilot cells converted from the existing personas. **3b is item 191:** the remaining professions, the paid generation of the 48 cells, the capped calibration run, retiring `evals/fixtures/synthetic/`, and the final tier sizes.
- **Prose** is written by the generator script (committed prompt, its own pin `AUTHOR_MODEL` = `claude-opus-5-5`, model id + prompt version + sha256 recorded per cell), not by hand. Opus 5.5 is outside the product pins and both arms of item 137's A/B, so no evaluated model wrote its own test set.
- **One fixture per JD:** `case_id` is `golden-v1/<cell>--<industry>`, so the full tier is up to 96 cases, not 48. 3b's cost estimate must say so.
- **The USAJOBS fetch is deferred.** 3a writes a C-2 / D-6 amendment proposal (design doc 6.5) for the owner's ceremony and builds no fetch code. The terms are re-read in a browser first; the date read is recorded in 6.5.
- **Wiki:** the golden data directory is classified irrelevant in `scripts/wiki_relevance.py`, because about four data files per cell would otherwise reach the merge-blocking limit of 75 on their own.
- Run-size flags and the single-call evals of `generate` / `generate_cover_letter` are step 4 (item 184), by the owner's answers on epic 180.

Consumers: `docs/dev/blast-radius/eval-dataset-format.md`.

### 2026-10-22 -- built (feat/eval-dataset-format); waits on the owner's go to push

Step 3a is built: the format (`evals/golden_set.py`, `evals/golden/golden-v1/` with three converted pilot cells and 12 exact waivers), per-cell seeds in the runner, the stub-tested generator (`evals/golden_author.py`, never run for real), the reachability check, and the docs. No paid call was made. Open on purpose until the PR merges: it closes with a `verified_by` naming `tests/test_golden_set.py`, `tests/test_golden_author.py`, `tests/test_golden_reachability.py`, `tests/test_eval_golden_runner.py` and the green CI run of the merge. Found and filed: item 192 (the committed corpus seed's `area` / `study_type` keys are dropped by the importer). Proposal for the owner: design doc 6.5 (the USAJOBS fetch and charter C-2).

### 2026-10-27 -- closed on docs/close-eval-items-182-183-193

PR #200 merged as `acf6d6f` on 2026-10-23T21:41Z. The owner asked for the closure in chat on 2026-10-27. `python -m scripts.ci_wait 200` was run after the merge and printed `GREEN (exit 0)` and `no absorbed reruns found in any required run log` (CI run 40025893744). The closure rests on the four test files and that run. The 2026-10-21 "still open for this step" list is not closed by this: tier sizes and the primary-source licence re-reads moved to item 191, and the USAJOBS fetch and its C-2 route were dropped by the owner's no-fetch decision of 2026-10-27 (item 193, design doc 6.5).

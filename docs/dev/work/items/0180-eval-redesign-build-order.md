```toml
schema = 1
id = 180
kind = "epic"
title = "Eval redesign build order"
status = "open"
decision_owner = "agent"
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Build the eval redesign (design doc section 9): steps 1-10 are items 181-190, step 11 is item 137."
```

Filed 2026-10-20 after the owner answered the eight decisions in the design doc's section 8.
The scope, the order and the reason for each step live in that doc; this epic does not restate them.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

Step 1 (item 181) is open; steps 2 to 10 are blocked, each on the one before. Item 137 (the
Haiku 5.5 A/B, step 11) is a child of this epic and depends on step 10.

### 2026-10-21 -- step 1 closed, step 2 built on feat/eval-catalog-skeleton

Step 1 (item 181) merged as PR #198 and is closed. Step 2 (item 182) is built on `feat/eval-catalog-skeleton` and waits on its own PR; item 183 (step 3) stays blocked until it lands. Four findings from building step 2 that belong to the build order, not to one item:

- **No step covers a single-call eval of `generate` or `generate_cover_letter`.** Section 9 names the kinds of steps 4 to 6 and neither is in them; their catalog entries are `covered` through the finished document only. Owner's call whether a step should add one (decision_owner stays with the agent for the epic; this one is the owner's).
- **`--max-spend`'s pre-flight cannot price an unmeasured kind**, and both judge kinds are unmeasured until a paid run writes judge rows to the call log. The runtime cap bounds them. Re-run `python -m evals.eval_catalog measure --write` after the first paid run (step 3's calibration run) so the estimate prices the judge.
- **`evals/catalog/costs.json` holds one machine's token means.** Step 3's calibration run on the standard dataset is what makes them a shared figure.
- **No step builds the run-size flags `--eval <kind>`, `--group`, `--affected-by` and `--full`** that design section 5.2 describes. Section 9's rows name the dataset (3), the call evals (4 to 6), the compare protocol (7), the dashboard (8), the judge (9) and OTel (10), not these. They need the catalog (built) and case files (step 3 onward). Decide which step owns them before step 4 starts, since step 4's call evals are what they would run.

### 2026-10-22 -- step 3 split into 3a and 3b; the build-order questions answered (feat/eval-dataset-format)

Step 2 (item 182) merged as PR #199 (`186a064`). The owner chose step 3 and decided, in plan mode:
- **Step 3 is two branches.** 3a is item 183 on `feat/eval-dataset-format` (format, generator, per-cell seeds, reachability check, three pilot cells; no paid call). 3b is new item 191 on `feat/eval-dataset-v1` (the paid generation of the 48 cells, the calibration run, retiring `synthetic/`). Item 184 and item 10 depend on 191 as well as 183. The design doc's section 9 row 3 is split to match.
- **The run-size flags** (`--eval`, `--group`, `--affected-by`, `--full`) are built in **step 4** (item 184), the step whose call evals they select. This answers the 2026-10-21 finding that no step owned them.
- **`generate` and `generate_cover_letter` get a single-call eval in step 4**, taking a captured `context_set` as input, so tuning the generate prompt does not re-run `analyze`. This answers the 2026-10-21 finding that no step covered them. Item 184's scope is not yet edited to say so; it is the first thing step 4 does.
- **One fixture per JD** in the golden set: `case_id` is `golden-v1/<cell>--<industry>`, so the full tier is up to 96 cases.
- **The dataset's prose is written by a generator script** pinned to `claude-opus-5-5`, outside the product pins and both arms of item 137's A/B.
- **The USAJOBS fetch is deferred** to a branch of its own after the owner decides the C-2 / D-6 amendment (3a writes the proposal).

### 2026-10-27 -- step 3b split again; the USAJOBS question closed as no fetch (feat/eval-golden-breadth)

Step 3a merged as PR #200 (`acf6d6f`). The owner reviewed the 48-cell matrix against the need (measure performance across many fields, settings and career moves) and decided, in plan mode:
- **3b is two branches.** 3b-i is new item 193 on `feat/eval-golden-breadth` (format only, no paid call: per-family ladders, a setting axis, certifications, mismatched pairs). 3b-ii is item 191, rescoped to about 24 professions by 4 levels, one fixture per JD (96), plus the pairs, on `feat/eval-dataset-v1`. Items 184 and 10 still depend on 191.
- **No USAJOBS fetch, no key, no charter change.** The golden set is authored and committed; the exploration set becomes a seeded draw from the matrix. Recorded in design doc 6.5, which supersedes the proposal there.
- **Government register is about 5% of the fixtures**, written in the model's own words from our brief; no third-party posting text.
- **Mismatched pairs are in the set** (career changers and career advancers), derived from existing cells with no new prose. How they are graded is steps 8 and 9.

```toml
schema = 1
id = 191
kind = "item"
title = "Eval redesign step 3b-ii: facts, paid generation of the golden cells, calibration run, retire synthetic"
status = "open"
depends_on = [193]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-v1"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-dataset-format.md", "docs/dev/blast-radius/eval-golden-breadth.md"]
summary = "Step 3b-ii: facts for about 24 professions, paid generation, capped calibration run, pairs, retire synthetic/."
```

Step 3b of the eval redesign build order, second half: docs/dev/eval-redesign-design.md section 9, row 3 (split by the owner on 2026-10-22; 3a is item 183; split again on 2026-10-27, 3b-i is item 193). Per owner decision 2 this half blocks the v1.1.0 cut with 3a, so item 10 depends on it.

## Scope

- The O*NET facts and the family ladders for the other professions: about **24 professions** in four groups (tech and product; business and office; healthcare, education and community; trades and construction) **by 4 levels, one fixture per JD, so 96** (the 2026-10-27 breadth decision replaces "12 by 4 = 48 cells"; the three pilots from 3a are the first three). The setting is rotated across cells, about 5% of fixtures use a public-sector register written in the model's words, and the mismatched pairs (career change and career advance) are chosen here from the finished cells. Re-read the O*NET licence text ("Except as noted below") and the DDaT ladders at the primary source before relying on them; read each occupation code on O*NET OnLine (several will be `nearest`).
- The paid generation run through `evals/golden_author.py`, with `--max-spend` and `--confirm-paid`. **It needs the owner's spend approval, estimated first.**
- The capped calibration run on the finished set. Afterwards `python -m evals.eval_catalog measure --write`, so the estimate prices the judge kinds.
- Retire `evals/fixtures/synthetic/` and retarget its consumers (listed under "Deferred" in `docs/dev/blast-radius/eval-dataset-format.md`).
- Final tier sizes, from measured cost, for up to 96 cases (one fixture per JD).
- Freeze `golden-v1`: the manifest goes to `frozen` and `pilot_waivers` must be empty. A check against git history so a frozen cell cannot be rewritten in place.

## Updates

### 2026-10-22 -- filed during feat/eval-dataset-format

Filed when the owner split step 3 into 3a and 3b. Item 184 (step 4) and item 10 (the v1.1.0 cut) now depend on this item as well as on 183.

### 2026-10-27 -- rescoped to 3b-ii; the USAJOBS fetch is not built

Step 3a merged (PR #200, `acf6d6f`). The owner widened the matrix to about 24 professions by 4 levels (96 fixtures, one JD each), a rotating setting axis, about 5% public-sector register, and mismatched pairs, and chose **no fetch**: no USAJOBS code, no key, charter C-2 and D-6 untouched (design doc 6.5). The format changes that make this possible are item 193 (3b-i, no paid call); this item now waits on it. The spend is still the owner's to approve, staged: `--help` and a dry run, then one cell for real with a small cap and a hand check of its prose, then the cap for the rest from that cell's measured cost. The pilots' 12 waivers still have to be gone before the freeze (replace the pilots with generated cells, or enrich them).

### 2026-10-27 -- unblocked; step 3b-i landed, the owner approved this step and a $3 spend cap

Item 193 merged as PR #201 (`2195981`) and is closed, so `blocked_on` no longer holds and the item is `open`. The owner approved this step in chat the same day, with **a total cap of $3 on author-model generation** and nothing else paid (no calibration run, eval or capture without a new ask). The staging above stands: `--help`, a dry run, then ONE cell for real. `golden_author.py` checks the cap between cells, so one cell can overshoot it, and no per-cell cost has ever been observed; read the first cell's actual cost and its prose before generating the next. Still to do first, free: the facts and the family ladders for the other professions, and the primary-source re-reads of the O*NET database terms and the DDaT ladders. The generator has never made a real call.

### 2026-10-28 -- guards, facts for 24 professions, and the first paid cell (branch `feat/eval-dataset-v1`)

The owner chose this item and set the method: stepwise, no run that must be repeated, no stall paid twice, a higher cap acceptable if the design learns as it goes. Built and committed, free: the generator's guards (a total-spend cap read from the call log across runs that counts rejected cells, one attempt per request, resume and batch flags, a stop after repeated rejections, rejected replies kept), a pre-check that stops a paid reply being lost at the write, tier-aware facts (one JD per cell), profession-specific employers, a facts check inside `check_suite`, and `facts/` for 24 professions in the four groups (9, 6, 4, 5) with three new authored ladders. The consumer dossier is `docs/dev/blast-radius/eval-dataset-v1.md`; it also holds the measurements. The gate ran green on the tree at `07d7679` before any paid call (`gate --result`: 4,237 and 189 passed, no retry marker).

**Stage 1, paid, one cell** (`web-backend-lead`, the heaviest, 26 slots; cap $0.50 of the $3 approved): **$0.0882**, one request, accepted first time, 31.3 s, `end_turn`; 4,807 input and 3,449 output tokens for 631 words of visible text, so about three quarters of the output was adaptive thinking. The run's own count and the call log agree. Hand-read: grounded, rule-following, plausible; the only weakness is the builder's (skills and themes drawn with replacement, so one skill appears in four of fourteen bullets). Neither stop rule fired. Projection from this one sample, not a measurement: about $6 to $8 for all 96 cells, so **the $3 cap will not finish the set** and the owner is asked for a new total cap at the checkpoint; nothing beyond stage 2 is paid until they answer. Not yet observed: any other profession or tier, a rewrite request, a refusal.

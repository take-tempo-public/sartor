```toml
schema = 1
id = 183
kind = "item"
title = "Eval redesign step 3: standard dataset, captured inputs, reachability check"
status = "blocked"
blocked_on = "step 2 (item 182) has not landed"
depends_on = [182]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-v1"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "O*NET synthetic matrix, captured upstream inputs, reachability check; on-demand public fetch only if it clears C-2."
```

Step 3 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 3. Scope lives there.
Re-read the O*NET and dataset licence pages at the primary source before committing anything (the design doc's research is reported, not verified). The on-demand fetch is an outbound connection: charter C-2 names two destinations, so it takes the D-6 opt-in route and passes `tests/test_egress_allowlist.py`, or returns to the owner as an amendment.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

### 2026-10-20 -- the owner widened the dataset requirement; second research pass recorded (docs/eval-dataset-research)

Owner, 2026-10-20: the golden set has only three tech personas at one level each, and the v1 set becomes ground truth for later releases, so it needs more variation (IT and development, security, administration, project and product management, design and UX, plus other sectors) and a deeper open-set research pass **before v1**. Design doc sections 6.1 to 6.3 record that pass (each row marked reported or raw-read) and 6.4 is the matrix proposal; section 8 questions 9 to 12 are unanswered.

What this step must decide or do, given the research: (1) the profession axis, option A, B or C in 6.4 (recommended B: 12 professions by 4 levels, 48 cells); (2) the golden set's composition, all-authored from O*NET and a level ladder (recommended) or with committed real postings (USAJOBS's terms were read in a browser on 2026-10-20 and permit it, with a carve-out for separately identified restricted content, contact names to scrub, and no rate-limit circumvention; NYC Jobs still needs a ruling); (3) how non-tech levels are defined, since no open ladder was found; (4) final tier sizes from the calibration run's measured cost, not from the 6.4 guess; (5) the C-2 route for the exploration fetch. Re-read at the primary source anything a decision rests on; the tool-mediated rows in 6.1 to 6.3 are not enough.

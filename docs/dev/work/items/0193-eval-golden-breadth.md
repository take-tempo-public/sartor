```toml
schema = 1
id = 193
kind = "item"
title = "Eval redesign step 3b-i: golden-set breadth (per-family ladders, setting, certifications, mismatched pairs)"
status = "closed"
depends_on = [183]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-golden-breadth"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-golden-breadth.md"]
summary = "Step 3b-i, no paid call: format changes so the golden set spans many fields, settings and mismatched pairs (3b-ii: 191)."
resolution = "Built and merged as PR #201 (2195981, 2026-10-28 UTC); the owner asked for it to be closed on 2026-10-27 (docs/close-eval-items-182-183-193). It closes the format work only. Not verified, and carried to item 191: the generator has never made a real call, so the new JD registers and certification briefs have met only the stub; a resume with a Certifications section has not been run through the product's parse, generate or assemble path; the O*NET codes for the new professions and the DDaT ladders were not read; how a pair is graded (steps 8 and 9) is undecided."
verified_by = [
  "tests/test_golden_set.py (TestTenure was committed failing first at 447169d; also the ladder, setting, certification and pair classes)",
  "tests/test_golden_reachability.py",
  "tests/test_eval_golden_runner.py",
  "tests/test_golden_author.py",
  "python -m scripts.gate passed on d7eb972 (log marker GATE_EXIT=0, 4115 passed + 189 UX passed, no RERUN marker line)",
  "PR #201 merge 2195981: python -m scripts.ci_wait 201 exit 0, no absorbed reruns, required checks green (CI run 40635949353)",
]
```

Step 3b of the eval redesign build order, first half (split by the owner's direction on 2026-10-27; 3b-ii is item 191). Scope and the reasons are in `docs/dev/blast-radius/eval-golden-breadth.md` and the design doc's 6.4; this item points, it does not restate.

## Updates

### 2026-10-27 -- filed and started on feat/eval-golden-breadth

The owner reviewed the matrix against the real need: the golden set exists to measure prompt and model performance across many job fields (administrative assistants, designers and product designers, mobile and hardware engineers, electricians, construction project managers, healthcare, support services, trades), across startups, enterprises and small employers, with a small public-sector share, and across **mismatched résumé/JD pairs** for career changers and career advancers.

Owner answers (chat, plan mode, 2026-10-27): the 24-profession list in four groups is about right; the government register is about 5% of fixtures; mismatched pairs are wanted; the **no-fetch route is recorded** (design doc 6.5; no USAJOBS fetch, no key, charter C-2 and D-6 untouched).

### 2026-10-27 -- built (feat/eval-golden-breadth); waits on the owner's go to push

Built in order, test first: a failing test for the career-length defect (`447169d`), then the ladder per family and the tenure fix, the setting axis, certifications and training-aware education, and the mismatched pairs, with two pilot pairs committed; then the README, CHANGELOG, the dossier and a scoped wiki pass. Nothing under the three pilot cells changed (no hash line was removed from the manifest). No paid call was made, no fetch code exists and the charter is untouched. A scratch mutation check of ten rules caught nine at once; the tenth (an advance pair skipping a tier) was a real test gap and has a test now. Measured on a synthetic suite: 96 cells plus 24 pairs check in about 1.4 s. Open on purpose until the PR merges: it closes with a `verified_by` naming `tests/test_golden_set.py`, `tests/test_golden_reachability.py`, `tests/test_eval_golden_runner.py` and the green CI run of the merge. Item 191 (3b-ii) waits on it. Not done here, on purpose: the facts for the other professions, how the judge weights a pair (steps 8 and 9), and items 182 and 183, which stay `open` for the owner.

### 2026-10-27 -- merged and closed (docs/close-eval-items-182-183-193)

PR #201 merged as `2195981`. The gate had passed on `d7eb972` before the handoff commit, and `python -m scripts.ci_wait 201` printed `GREEN (exit 0)` and `no absorbed reruns found in any required run log` (CI run 40635949353). The owner asked for the closure in chat on 2026-10-27, and said at the same time to close items 182 and 183, which are closed on this branch too. The closure rests on the four test files, the gate pass and that run. The things it does not show are the ones named in `resolution`; they are item 191's to settle. The owner also approved step 3b-ii on 2026-10-27 with a total author-model spend cap of $3 (run one cell first); the cap is recorded in the handoff `docs/dev/handoffs/feat-eval-golden-breadth.md`.

Found by reading the 3a format (before this branch changed it): the level ladder is one global tuple of tech-flavoured scopes; the employer pool, JD header (`— Remote (US)`) and JD shape are tech-startup shaped; there is no certifications section although the corpus already has one; and tenure is drawn from a fixed 18 to 41 month window that ignores the ladder's `years`. This branch changes the format only: per-family ladders, a setting axis, certifications and training-aware education, and pairs derived from existing cells with no new prose. The facts for the new professions and the paid generation stay in item 191.

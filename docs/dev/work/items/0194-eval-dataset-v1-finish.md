```toml
schema = 1
id = 194
kind = "item"
title = "Eval redesign step 3b-iii: fix the certification requirement, calibrate, size the tiers, retire synthetic, freeze golden-v1"
status = "open"
depends_on = [191]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-v1-finish"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-dataset-v1.md", "docs/dev/blast-radius/eval-dataset-v1-finish.md", "docs/dev/work/items/0191-eval-dataset-v1-generation.md"]
summary = "Step 3b-iii: the cert-requirement fix (37 cells), calibration run, tier sizes, retire synthetic/, freeze golden-v1."
```

What is left of the golden set after item 191 built the facts, the generator guards, the 96 cells and the 36 pairs. Item 191 moved these here on purpose: a calibration run on a set that still changes would have to be paid for again, and retiring `evals/fixtures/synthetic/` retargets its consumers onto a set that is complete. Items 184 and 10 depend on this item as well as on 191.

## Scope, in order

1. **DONE on `feat/eval-dataset-v1-finish` (see Updates, 2026-10-28, and the dossier): the requirement is fixed, two more faults found by the hand-read are fixed, 40 cells are regenerated.** *The original text follows.* **Fix the certification requirement, then regenerate the affected cells.** Found by hand-reading `electrician-lead` after the bulk run: a **foreman** posting says "A current State Apprentice Registration Card is required." The builder asks the posting to require `held_certs[:1]` (`evals/golden_set.py`, the `asked_certs` line), the *lowest-tier* certification a candidate holds, so a senior or lead posting requires the entry-level one and a higher one is never asked for. Counted from the committed profiles: 56 cells hold certifications and **37 hold two or more with the posting requiring the lowest** (accounting, carpenter-foreman, electrician, hr, hvac-technician, logistics-driving, medical-assistant, project-mgmt, registered-nurse, security, social-services, sre-ops and teacher, at the tiers where two or more are held). It is a realism fault, not a grounding one: the certification is truly held and the ground truth is consistent. The fix is one line (the highest held, `held_certs[-1]`) plus a test written first, and it changes those cells' profiles, so those 37 cells have to be regenerated: about 37 × $0.075, **about $2.8, and only $2.12 of the owner's $10.00 is left** ($7.88 logged), so this needs a new cap from the owner before it is spent. The regeneration order and stop rules are those of item 191's dossier.
2. **DONE for a first stratified sample on the same branch: 16 more cells read, 23 of 96 in all; the findings are in Updates and the dossier. A freeze still wants the owner's call on them (open questions below).** *The original text follows.* **Read more of the final prose.** Only four of the 96 committed cells were hand-read (`teacher-mid`, `electrician-lead`, `security-mid`, `social-services-entry`), plus earlier versions of five that were discarded. The rest rely on the deterministic checks, which cannot see realism. Read a stratified sample (every group, every tier, every setting including the five public-sector postings) before the freeze and record what it finds; the first sample found the item 1 defect.
3. **The calibration run** (its own spend ask: judge calls, and a run of the full pipeline). Measure the real rate of `scenario_misaligned` iteration runs in assemble mode (a derived scenario depends on its target bullet surviving assembly; the stub's rate was 0 once its prose was distinct), judge-to-judge agreement only (no gold labels, decision 5), and run `python -m evals.eval_catalog measure --write` afterwards so the estimate prices the judge kinds.
4. **Final tier sizes** from the measured cost: sentinel, day-to-day and full golden, for 96 fixtures plus the 36 pairs. `iterate_clarify` fires for every fixture in generate mode (every generated profile iterates), which raises the per-fixture price.
5. **Retire `evals/fixtures/synthetic/`** and retarget its consumers. The list is in item 191's dossier (`docs/dev/blast-radius/eval-dataset-v1.md`, Deferred); it was derived by a subagent and is **not re-derived**, so re-derive it first: `evals/runner.py` (the `--fixture` lookup, the default suite), `evals/corpus_drafting_probe.py`, `scripts/smoke_phase_b1.py`, eight test files in the required gate, the label-gated `eval-smoke` job in `ci.yml`, four catalog TOMLs, `baseline_v1.json` (its regression keys are bare fixture names), the dashboard selects and the console allowlists in `blueprints/diagnostics.py`, and a hash-locked line in `analyzer.py` (`AVATAR_SYSTEM_PROMPT` names `--suite synthetic`).
6. **Freeze `golden-v1`**: the manifest goes to `frozen` (it already has no waivers and no converted cell), plus a check against git history so a frozen cell cannot be rewritten in place, and the dashboard question of how a slash-bearing `case_id` is shown (step 8).

## Open questions for the owner

- ~~Raise the cap for item 1 (about $2.8), or accept the realism fault for v1 and record it?~~ **Answered by the owner on 2026-10-28: raise the total cap to about $13.00 and fix it.** The cap applies to item 1 only; it replaces the $10.00 (of which $7.8797 is logged), covers no calibration run, eval or capture, and the call-log total keeps counting across runs.
- **Entry-tier credentials dated after the career began (new, owner's call):** 23 credentials in 22 of 56 cells; in 11 the posting requires it (a teacher-entry licence dated 2026, role from 2025). The owner's rule bound mid-or-higher only. Binding the entry tier changes about 22 cells' profiles and means regenerating them (about $1.5; $1.79 is left of the $13.00, which covers no other scope), or accept it for v1 and record it?
- **Postings that call a credential both preferred and required (new, owner's call):** two confirmed by reading (construction-pm-senior, logistics-driving-lead), up to 8 of 96 by a crude heuristic. The model writes it, so a fix is a prompt change (bump `AUTHOR_PROMPT_VERSION`, regenerate every cell to keep the set single-version, about $7) or a deterministic check that makes `check` refuse it plus a rewrite of the cells it flags. Accept for v1, or fix?
- **A small employer pool (new, owner's call):** 216 roles use 59 employer names, 32 of them in two or more professions. A facts-side change (per-profession `employers`) would change every affected cell's profile. Accept for v1?
- Try `AUTHOR_EFFORT = "low"`? The owner kept `medium` on 2026-10-28; a different effort would mix settings across cells unless all are regenerated.
- Did the cut-off `sales-senior` request (a ten-minute laptop standby) bill? The call log cannot say; the provider's usage page can. If it did, the true spend is a little above $7.88.
- Does the keep-awake request actually prevent Modern Standby on this laptop? Only a long unattended run will show; a closed lid can still sleep a machine set to.

## Updates

### 2026-10-28 -- filed on feat/eval-dataset-v1

Filed at the close-out of item 191. Nothing here is started.

### 2026-10-28 -- owner decision at the close of item 191

Asked, after the hand-read found the certification-requirement defect: raise the cap, accept the fault, or decide later. **The owner chose to raise the total cap to about $13.00 and fix it** (scope 1). Order of work, unchanged: write the failing test first (the strict expected-failure in `tests/test_golden_set.py::TestCertifications` already asserts the right behaviour; fixing `asked_certs` in `build_profile` flips it to a strict failure, so remove its marker in the same commit), change the one line, delete the 37 stale cells and their fixtures (the suite check refuses a cell that no longer matches a fresh build), regenerate them with `--cell` batches under `--max-total-spend 13`, hand-read a sample of the new postings, and re-derive the pairs that involve a regenerated cell (`python -m evals.golden_set pairs` then `manifest`).

### 2026-10-28 -- scopes 1 and 2 built on feat/eval-dataset-v1-finish

**Scope 1.** Three faults in `build_profile`, each found by hand-reading one cell, each fixed with a test written first that failed on the old code: (1) the posting required the lowest-tier credential held (fixed to the highest); (2) credential years were independent hash draws, so a Master licence could precede the Journeyman licence (21 of 37 multi-credential cells; fixed by handing the sorted draws out in tier order); (3) a mid-or-higher credential could be dated after the role titled for its tier (28 of 37 by my heuristic; fixed with a per-credential cap at that role's start year). The owner chose to fix (2) and (3) before the sweep, so the cells were regenerated once. The third fix reached **three cells outside the 37** (construction-pm-lead, construction-pm-mid, project-mgmt-mid), so **40 cells** were regenerated, with 20 pair fixtures re-derived and three pairs' authored `transferable` terms re-picked. **Spend: $3.3307 on this branch** (the call log reads $11.2104 of the owner's $13.00), of which $0.1833 went on two discarded `electrician-lead` outputs found faulty by the hand-read. None of the 40 cells was rejected. A guard over the real matrix (`tests/test_golden_facts.py`, 24 cases) now fails if any profession recreates the three faults.

**Scope 2.** 16 cells read whole (every group x tier, all 5 settings), plus 5 read during regeneration: 21 final cells, 23 of 96 with the 2 from item 191 that were not regenerated. No grounding fault (no invented employer, number or credential). Three realism findings, each measured over all 96 cells, are put to the owner above: entry-tier credentials after the career began (22 cells), a posting contradicting itself about a credential (2 confirmed, up to 8), and a small employer pool (59 names for 216 roles). The sample is purposive, not random: it supports "these strata read as follows", not a rate.

**Not done, still open on this item:** scopes 3 to 6 (calibration run, tier sizes, retiring `evals/fixtures/synthetic/`, the freeze). The cut-off `sales-senior` request's billing is still unknown, so true spend may be a little above the log's figure.

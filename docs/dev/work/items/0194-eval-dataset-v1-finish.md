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
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-dataset-v1.md", "docs/dev/work/items/0191-eval-dataset-v1-generation.md"]
summary = "Step 3b-iii: the cert-requirement fix (37 cells), calibration run, tier sizes, retire synthetic/, freeze golden-v1."
```

What is left of the golden set after item 191 built the facts, the generator guards, the 96 cells and the 36 pairs. Item 191 moved these here on purpose: a calibration run on a set that still changes would have to be paid for again, and retiring `evals/fixtures/synthetic/` retargets its consumers onto a set that is complete. Items 184 and 10 depend on this item as well as on 191.

## Scope, in order

1. **Fix the certification requirement, then regenerate the affected cells.** Found by hand-reading `electrician-lead` after the bulk run: a **foreman** posting says "A current State Apprentice Registration Card is required." The builder asks the posting to require `held_certs[:1]` (`evals/golden_set.py`, the `asked_certs` line), the *lowest-tier* certification a candidate holds, so a senior or lead posting requires the entry-level one and a higher one is never asked for. Counted from the committed profiles: 56 cells hold certifications and **37 hold two or more with the posting requiring the lowest** (accounting, carpenter-foreman, electrician, hr, hvac-technician, logistics-driving, medical-assistant, project-mgmt, registered-nurse, security, social-services, sre-ops and teacher, at the tiers where two or more are held). It is a realism fault, not a grounding one: the certification is truly held and the ground truth is consistent. The fix is one line (the highest held, `held_certs[-1]`) plus a test written first, and it changes those cells' profiles, so those 37 cells have to be regenerated: about 37 × $0.075, **about $2.8, and only $2.12 of the owner's $10.00 is left** ($7.88 logged), so this needs a new cap from the owner before it is spent. The regeneration order and stop rules are those of item 191's dossier.
2. **Read more of the final prose.** Only four of the 96 committed cells were hand-read (`teacher-mid`, `electrician-lead`, `security-mid`, `social-services-entry`), plus earlier versions of five that were discarded. The rest rely on the deterministic checks, which cannot see realism. Read a stratified sample (every group, every tier, every setting including the five public-sector postings) before the freeze and record what it finds; the first sample found the item 1 defect.
3. **The calibration run** (its own spend ask: judge calls, and a run of the full pipeline). Measure the real rate of `scenario_misaligned` iteration runs in assemble mode (a derived scenario depends on its target bullet surviving assembly; the stub's rate was 0 once its prose was distinct), judge-to-judge agreement only (no gold labels, decision 5), and run `python -m evals.eval_catalog measure --write` afterwards so the estimate prices the judge kinds.
4. **Final tier sizes** from the measured cost: sentinel, day-to-day and full golden, for 96 fixtures plus the 36 pairs. `iterate_clarify` fires for every fixture in generate mode (every generated profile iterates), which raises the per-fixture price.
5. **Retire `evals/fixtures/synthetic/`** and retarget its consumers. The list is in item 191's dossier (`docs/dev/blast-radius/eval-dataset-v1.md`, Deferred); it was derived by a subagent and is **not re-derived**, so re-derive it first: `evals/runner.py` (the `--fixture` lookup, the default suite), `evals/corpus_drafting_probe.py`, `scripts/smoke_phase_b1.py`, eight test files in the required gate, the label-gated `eval-smoke` job in `ci.yml`, four catalog TOMLs, `baseline_v1.json` (its regression keys are bare fixture names), the dashboard selects and the console allowlists in `blueprints/diagnostics.py`, and a hash-locked line in `analyzer.py` (`AVATAR_SYSTEM_PROMPT` names `--suite synthetic`).
6. **Freeze `golden-v1`**: the manifest goes to `frozen` (it already has no waivers and no converted cell), plus a check against git history so a frozen cell cannot be rewritten in place, and the dashboard question of how a slash-bearing `case_id` is shown (step 8).

## Open questions for the owner

- Raise the cap for item 1 (about $2.8), or accept the realism fault for v1 and record it?
- Try `AUTHOR_EFFORT = "low"`? The owner kept `medium` on 2026-10-28; a different effort would mix settings across cells unless all are regenerated.
- Did the cut-off `sales-senior` request (a ten-minute laptop standby) bill? The call log cannot say; the provider's usage page can. If it did, the true spend is a little above $7.88.
- Does the keep-awake request actually prevent Modern Standby on this laptop? Only a long unattended run will show; a closed lid can still sleep a machine set to.

## Updates

### 2026-10-28 -- filed on feat/eval-dataset-v1

Filed at the close-out of item 191. Nothing here is started.

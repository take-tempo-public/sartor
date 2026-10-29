# Blast radius — eval-dataset-v1-finish

> **Branch:** `feat/eval-dataset-v1-finish` (item 194, scopes 1 and 2 only)
> **Status:** enumeration complete at `b62c704` (`main`), written before the first code edit. This branch fixes the
> certification requirement in `build_profile`, regenerates the 37 affected cells under the owner's total cap, re-derives
> the pairs and the manifest, and hand-reads a stratified sample of the finished set. Scopes 3 to 6 (calibration, tier
> sizes, retiring `evals/fixtures/synthetic/`, the freeze) stay open on item 194.

---

## Surface

`evals/golden_set.py`, function `build_profile`, the block that builds each job description's `needs` slot
(`asked_certs`, `cert_ask`; lines 1868 to 1879 at `b62c704`). Today the posting asks for `held_certs[:1]` (and names
`held_certs[0]`), the **lowest**-tier certification the candidate holds. The fix asks for `held_certs[-1:]` and names
`held_certs[-1]`, the highest. `held_certs` is sorted by tier (`golden_set.py:1812`), so the last entry is the highest held.

What does not change: `absent_certs` (the preferred one, and the forbidden inventions built from it), the prose prompt
(`AUTHOR_SYSTEM_PROMPT`, `build_user_prompt`), so `AUTHOR_PROMPT_VERSION` stays `golden-author-2`, and every cell that
holds zero or one certification (`[-1:]` equals `[:1]` for a list of one).

---

## Enumeration

Commands run at `b62c704`, read-only, over the whole tree (the `evals/golden/**` data excluded from the symbol grep
because it holds generated output, and counted separately below):

- `grep -E "asked_certs|held_certs|absent_certs"` outside `evals/golden/**`: **`evals/golden_set.py` only** (lines
  1813, 1814, 1825, 1868 to 1878, 1895, 1922, 1927). Docs hits are prose about the defect (rows 7 to 11). **0 hits** in
  `evals/golden_author.py`, `evals/runner.py`, `static/`, `blueprints/`, `scripts/`.
- `grep -i "lowest-tier|lowest tier|37 of the 56|37 cells"`: the defect is described in `CHANGELOG.md:44-45`,
  `docs/dev/eval-redesign-design.md:775-776`, `docs/dev/work/items/0194-eval-dataset-v1-finish.md` (lines 19, 28, 41),
  `docs/dev/blast-radius/eval-dataset-v1.md:261-262`, `tests/test_golden_set.py:1000-1007,1062`, and the closed handoff
  `docs/dev/handoffs/feat-eval-dataset-v1.md` (a dated record, not edited). **0 hits** in `evals/README.md` and
  `docs/wiki/` for the defect (the wiki describes the builder, checked again at close-out).
- Affected cells, counted from `cells/*/profile.json` with a script (`consumers.py`, scratch): a cell holds two or more
  certifications. **37 cells**: entry 2, mid 9, senior 13, lead 13. The 19 cells that hold exactly one certification and
  the 40 that hold none are unchanged by the fix.
- Cell fixtures: one per cell, `fixtures/<cell>--<industry>`. **37** for the affected cells.
- Pairs: `manifest.json` lists 36. Of those, **18 pairs (31 references)** name an affected cell as `resume_fixture` or
  `jd_fixture`; the other 18 are untouched. A regenerated cell carries all-new prose, so the pair fixtures built from it
  change too.

**The 37 cells:** accounting-lead, accounting-senior, carpenter-foreman-{lead,mid,senior}, electrician-{entry,lead,mid,senior},
hr-{lead,senior}, hvac-technician-{lead,mid,senior}, logistics-driving-{lead,mid,senior}, medical-assistant-{lead,mid,senior},
project-mgmt-{lead,senior}, registered-nurse-{entry,lead,mid,senior}, security-{lead,senior}, social-services-{lead,mid,senior},
sre-ops-{lead,mid,senior}, teacher-{lead,mid,senior}.

**The 18 affected pairs:** carpenter-foreman-senior-to-carpenter-foreman-lead, electrician-entry-to-electrician-mid,
hr-senior-to-hr-lead, hvac-technician-entry-to-hvac-technician-mid, logistics-driving-mid-to-logistics-driving-senior,
medical-assistant-senior-to-medical-assistant-lead, project-mgmt-senior-to-project-mgmt-lead,
registered-nurse-entry-to-registered-nurse-mid, security-senior-to-security-lead, social-services-entry-to-social-services-mid,
sre-ops-mid-to-sre-ops-senior, teacher-senior-to-teacher-lead, sre-ops-mid-to-security-mid, accounting-senior-to-project-mgmt-mid,
registered-nurse-mid-to-medical-assistant-mid, teacher-mid-to-social-services-mid, electrician-senior-to-hvac-technician-mid,
carpenter-foreman-mid-to-construction-pm-mid.

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/golden_set.py` `build_profile` (the `asked_certs` / `cert_ask` lines, ~1868-1879) | **update** | The one-line fix: ask for and name `held_certs[-1]`. |
| 1b | `evals/golden_set.py` `build_profile` (the `cert_years` / `cert_items` block, ~1815-1826) | **update** (added after the hand-read, owner's decision) | Certification years: sorted draws handed out in tier order, so a higher tier is never dated before a lower one. Changes the certification section of 22 of the 37 cells; no cell outside the 37. |
| 1c | `tests/test_golden_set.py::TestCertifications::test_a_higher_tier_certification_is_never_dated_before_a_lower_one` | **new** | Written first; failed 30 of 40 seeds before the fix. |
| 2 | `evals/golden_set.py` `_check_cell_matches_facts` / `check_suite` | no change | Rebuilds every generated cell from its facts. After row 1 it reports exactly the 37 stale cells, which is the free instrument run before any spend. |
| 3 | `evals/golden_set.py` `write_pairs`, `write_manifest` (CLI `pairs`, `manifest`) | no change (re-run) | Re-derive the 18 pairs' fixtures and re-stamp `files` hashes after regeneration. Not hand-edited. |
| 4 | `tests/test_golden_set.py::TestCertifications::test_the_posting_requires_the_highest_certification_the_candidate_holds` (line ~996) | **update** | Remove the strict `xfail` marker in the same commit that fixes the line; the test already asserts the right behaviour. |
| 5 | `tests/test_golden_set.py::TestCertifications::test_the_jd_requires_a_held_certification_and_names_the_next_as_preferred` (line ~1059) | **update** | Found by this grep, not named in the handoff or item 194. It pins the OLD behaviour (mid cell requires `OSHA 30-Hour Card`, `"30" in allowed_numbers`). After the fix a mid cell requires `Journeyman Licence`; the digit assertion needs a different anchor. Updated in the same commit. |
| 6 | `tests/test_golden_set.py` `test_a_built_cell_with_certifications_checks_clean_on_disk` and the `CERT_FACTS`-based tests | no change | Build and check a cell on disk; neither pins which certification the posting asks for (re-run with the suite). |
| 7 | `tests/test_golden_facts.py` | no change | Builds the whole matrix from the committed facts; asserts structure, not the asked certification (re-run with the suite). |
| 8 | `evals/golden/golden-v1/cells/<37 cells>/{profile,prose}.json` | **regenerate** | The profile changes (needs-slot brief, `must_include`, `allowed_numbers`), and prose is written against the brief. Paid; under `--max-total-spend 13`. |
| 9 | `evals/golden/golden-v1/fixtures/<37 cell fixtures>` | **regenerate** | Rendered from the regenerated cell. |
| 10 | `evals/golden/golden-v1/fixtures/<18 pair fixtures>` and `manifest.json` `files` hashes | **re-derive** | `pairs` then `manifest`. |
| 11 | `CHANGELOG.md:44-45` | **update** | "A known defect, not fixed" becomes the fix, with the count and the spend. |
| 12 | `docs/dev/eval-redesign-design.md:775-776` | **update** | "Open (item 194)" becomes fixed. |
| 13 | `docs/dev/work/items/0194-eval-dataset-v1-finish.md` | **update** | Scopes 1 and 2 done; scopes 3 to 6 stay open; Updates entry. |
| 14 | `docs/dev/blast-radius/eval-dataset-v1.md:261-262` | no change | A dated record of what was observed at the time. |
| 15 | `docs/dev/handoffs/feat-eval-dataset-v1.md` | no change | Closed handoff; a dated record. |
| 16 | `docs/wiki/` pages on the golden set / eval harness | **check at close-out** | No hit for the defect; the wiki-relevance check and a scoped `/wiki-self-update` decide whether a page needs an edit. |
| 17 | `evals/README.md` | **check at close-out** | 0 hits for the defect; the README's golden-set section is checked against the final numbers. |

---

## Deferred

- **Scopes 3 to 6 of item 194** (calibration run, final tier sizes, retiring `evals/fixtures/synthetic/`, the freeze).
  Owner's choice this session: this branch takes scopes 1 and 2. The `synthetic/` consumer list is **not** re-derived
  here; the branch that retires it re-derives it first.
- **The 19 cells that hold exactly one certification and the 40 that hold none** are not regenerated: the fix leaves
  their profiles byte-identical (checked by the rebuild instrument below, which must not flag them).
- **A different `AUTHOR_EFFORT`** (open owner question, item 194): the cells keep `medium`, so the set stays single-setting.
- **Whether the cut-off `sales-senior` request billed** (open owner question): the call log cannot say; unchanged.

---

## Verification

- **Free instrument before any spend:** after the fix, `python -m evals.golden_set check` must report a rebuild mismatch
  for **exactly** the 37 cells above and no other. A missing or extra cell means STOP: the enumeration was wrong.
- **After regeneration:** `check` prints `OK (96 cells)`; every needs-slot brief of a multi-certification cell names that
  cell's highest held certification (re-counted from the profiles); `git diff --stat main` touches only the 37 cells, their
  fixtures, the 18 pair fixtures, `manifest.json`, the code and test lines, and docs.
- **Spend:** the logged author total (call log, across runs) stays at or under $13.00. Each run's cost is recorded below in
  the turn it ends.

## Measurements

_(Recorded here in the turn each is learned: the rebuild-instrument result, each paid run's cost, the checkpoint
projection, the hand-read findings.)_

**The free instrument, run after the one-line fix and before any spend (2026-10-28).** `python -m evals.golden_set check`
exited 1 and printed 37 `the stored profile differs from a fresh build` lines and nothing else. Compared by script against
the 37 cells counted from the profiles (two or more certifications): **37 wanted, 37 flagged, 0 missing, 0 extra, 0 other
problem lines.** The 59 other cells rebuild byte-identically, so the fix touched nothing outside the enumeration.
`tests/test_golden_set.py` + `tests/test_golden_facts.py` with `-x`: 226 passed, then `TestCommittedSuite::test_the_committed_suite_is_sound`
failed with exactly those 37 (expected until the cells are regenerated). The old-behaviour test at line ~1059 was found
by grep and rewritten with the fix (row 5).

**Stale cells removed (git rm, not yet committed):** 37 cell directories and their 37 cell fixtures; 59 cells and 95
fixtures (59 + 36 pairs) remain. The 18 affected pair fixtures are not deleted: `write_pairs` overwrites, so `pairs` after
regeneration re-derives them.

**Paid run A, `electrician-lead` (2026-10-28):** `python -u -m evals.golden_author --cell electrician:lead --max-spend 0.20
--max-total-spend 13 --confirm-paid`, exit 0, one request, **$0.0877** (the lead-tier mean was $0.093); the log's own line:
`$7.9674 of $13.0000 in all`. Hand-read: the foreman posting now says "A current Master Electrician Licence is required."
(fixed). The résumé's prose is plausible for a lead, with the stuffed phrasing the earlier cells already showed ("organise
crew power tool use around test windows").

**A second defect, found by that hand-read, in the same function (certification years).** The résumé's certifications read
Apprentice Registration Card 2023, Construction Safety Card 2020, Journeyman Licence **2026**, Master Licence **2019**, for a
career that began in 2013: a Master licence dated seven years before the Journeyman licence. Cause, read in
`evals/golden_set.py:1820-1823`: each held certification's year is `first_year + hash(seed, "cert-year:<name>") % span`, a
uniform draw over the whole career and independent of the certification's tier. **Measured (free,
`scratchpad/cert_years.py`, over the 56 cells that hold certifications, the 37 stale ones read from `HEAD`):** **21 of the 37
cells with two or more certifications have years that are not non-decreasing by tier**; 0 of the 56 have a year outside
`[first role start, 2026]`. Example: carpenter-foreman-lead, first role 2015: Construction Safety Card 2020, Apprenticeship
Completion Certificate 2023, Lead Carpenter Certificate 2016, Crew Supervisor Certificate 2020. It is a realism fault, not a
grounding one. **All 21 are among the 37 cells already being regenerated**, so fixing it before the sweep costs nothing
extra beyond re-doing `electrician-lead`; fixing it after the sweep would regenerate those 21 a second time (about $1.8).
Not fixed yet: it is outside the scope the owner quoted (item 194 scope 1), so the owner is asked.

**Owner's decision (2026-10-28, chat): fix now, then sweep.** Fix: in `build_profile`, `cert_years = sorted(<the same hash
draws>)` handed out in tier order (`golden_set.py`, the `cert_items` block). Test written first:
`TestCertifications::test_a_higher_tier_certification_is_never_dated_before_a_lower_one` (forty seeds, a three-certification
senior cell); it **failed on the unfixed code, 30 of 40 seeds disordered**, and passes after. Same row-1 surface as the
asked-certification fix, same 37 cells.

**Measured after the fix (free, `scratchpad/predict.py`, the 37 old profiles read from `HEAD` and rebuilt):** the
certification section changes in **22** of the 37 and is identical in **15**. That is one more than the 21 tier violations
counted above: `electrician-entry` holds two entry-tier certificates dated 2026 then 2025, which is not a tier violation, but
the sort reorders them (2025, 2026). My earlier expectation "21" was a count of tier violations, not of changed profiles; the
difference is that one cell, which is among the 37 regenerated anyway. One-certification and no-certification cells are
untouched: `golden_set check` after the fix flags exactly one existing cell as stale, `electrician-lead` (the one already
regenerated, with the old years), and none of the 58 others. The `TestCommittedSuite` tests fail until the 36 remaining
cells are regenerated and the pairs re-derived (expected mid-regeneration state).

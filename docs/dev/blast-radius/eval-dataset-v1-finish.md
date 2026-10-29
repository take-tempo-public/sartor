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

**Paid run A2, `electrician-lead` again with the sorted years (2026-10-28):** exit 0, **$0.0956**, log line `$8.0629 of
$13.0000 in all`. The old-years output ($0.0877, run A) is kept outside the repo, in the session scratchpad. The
certifications now ascend with tier (Apprentice Card 2019, Safety Card 2020, Journeyman 2023, Master 2026).

**A third defect, found by hand-reading A2 (credential dates against role titles).** The same résumé has the person working
as a Journeyman Electrician from January 2013 and a Master Electrician from November 2020, but holding the Journeyman
Licence from 2023 and the Master Licence from 2026. Cause: the year draw (`golden_set.py:1815-1826`) knows nothing about the
role titles; a credential tier-N is dated anywhere in the career. It predates the sort fix (run A had Journeyman 2026 against
the same 2013 role). **Measured, free (`scratchpad/audit_titles.py` and `audit_titles_narrow.py`), rebuilding all 37
multi-certification cells with the sorted-year builder:** the strict rule (a tier-t credential dated after the earliest role
titled for any tier >= t) flags **32 of 37**; the narrower rule I would defend (a mid-or-higher credential dated after the
earliest role titled for its own tier) flags **28 of 37**. Examples: accounting-lead, Certified Public Accountant Licence 2026
against a role from 2017; electrician-senior, Journeyman 2022 against a role from 2019. Both rules are heuristics I wrote, not
a check from a source; the strict one over-counts (an entry-level card obtained on the job is plausible), the narrow one is
the figure to use. **I should have run this free audit before the first paid cell**; the hand-read caught it instead, at a
cost of one extra request ($0.0956). Spend stopped here at $8.0629 pending the owner's decision.

**Owner's decision (2026-10-28, chat): bound the dates by role, then sweep.** Fix (`golden_set.py`, the `role_start` /
`role_cap` / `caps` / `cert_years` block): a credential of tier t >= mid is capped at the start year of the earliest role
titled for tier t or above (that cap does not fall as the tier rises); an entry-tier credential takes the lowest cap among
the higher credentials held; a cell holding only entry-tier credentials is capped by nothing; the capped hash draws are
sorted and handed out in tier order. Test first: `TestCertifications::test_a_credential_is_dated_no_later_than_the_role_titled_for_its_tier`
(forty seeds, a lead cell): **failed 78 of 80 credentials on the builder before the cap, passes after**. Entry-tier
credentials are deliberately not bound by a role (the owner's decision said mid-or-higher).

**Measured after the cap (free):** the narrow audit flags **0 of 37**. The strict rule flags **13 of 37**, all of them
entry-tier credentials dated after a later role (accounting-senior: Bookkeeping Certificate 2023, role from 2019); that is
the strict-rule residue and not a regression. `golden_set check` now flags four existing cells as stale, not one:
`electrician-lead` (the A2 cell, old uncapped years) **and three cells outside the 37**: `construction-pm-lead`,
`construction-pm-mid`, `project-mgmt-mid`. Each holds one mid-or-higher credential whose year is now capped (Construction
Safety Manager Certificate 2023 to 2015, 2024 to 2023; Project Practitioner Certificate 2026 to 2024). `scratchpad/diff3.py`
shows the **only** difference in all three is that one year: `slots` are equal and no other section differs. So the role
cap reaches **3 cells the enumeration above did not name** (consumers row 8, 9 and 10 grow by 3 cells each). Decision: they
are regenerated with the rest, because the suite check refuses a profile that differs from a fresh build, and the handoff
forbids hand-editing a cell. Cost about $0.23, within the $13.00 cap; the plan's projection was 37 cells, it is now 40
(36 not yet redone + `electrician-lead` a third time + the 3). The earlier statement above that the fix leaves "no cell
outside the 37" was true of the sort fix and is **false of the role cap**.

**Paid run A3, `electrician-lead` with all three fixes (2026-10-28):** exit 0, **$0.0870**, `$8.1499 of $13.0000 in all`
(three requests for this one cell: $0.0877 + $0.0956 + $0.0870 = $0.2703; the first two are discarded output kept in the
scratchpad). Hand-read: the posting says "Current Master Electrician Licence required"; the certifications read Apprentice
Card 2013, Safety Card 2013, Journeyman Licence 2013 (role from January 2013), Master Licence 2017 (role from November
2020). Dates now agree with the titles and ascend with tier. `golden_set check` reports 0 cells that differ from a fresh
build. Four credentials in one year (2013) is the cap working on a cell whose oldest role is already Journeyman-titled; it
reads as a person who started the job licensed, which the title ladder says.

**Paid run B, four cells (2026-10-28):** `--cell registered-nurse:entry --cell teacher:mid --cell sre-ops:senior --cell
social-services:lead --max-spend 0.50 --max-total-spend 13`, exit 0, 4 written, none rejected, **$0.2737** (entry $0.0482,
mid $0.0672, senior $0.0729, lead $0.0853), `$8.4237 of $13.0000 in all`. **Hand-read, all four, whole résumé and posting:**
every posting requires the credential at the top of the candidate's tier (Reading Specialist Endorsement; Cloud Operations
Certificate; Human Services Supervisor Certificate; the nurse's licence and Basic Life Support card); every mid-or-higher
credential is dated no later than its role (Reading Specialist 2025 / Classroom Teacher from January 2025; Supervisor
Certificate 2019 / Program Manager from November 2020); bullets are grounded in the listed skills and read as the work.
**Faults seen, none systematic:** (1) the nurse's Basic Life Support card is dated 2026, a year after her first role began
(March 2025): the entry-tier credential the owner's rule leaves unbound (the strict-rule residue); (2) a past employer,
"Riverbend Health Network", shares a stem with the target employer, "Riverbend Community Partnership" (social-services-lead),
because the employer pool and the industry names are drawn separately; (3) a hospice employs a Senior Site Reliability
Engineer (sre-ops-senior), odd but possible. A Graduate Registered Nurse posting asking for "2 or more years of experience
as a registered nurse" comes from the entry ladder (0 to 2 years) and was already so in the earlier version.
Hand-read count so far in this branch: 5 final cells (electrician-lead and these four).

**Checkpoint (c), measured.** Final-cell costs this branch: entry $0.0482 (1), mid $0.0672 (1), senior $0.0729 (1), lead
$0.0870 and $0.0853 (2). Remaining after run B: **35 cells**, because the set to redo is 40, not 37 (the 37 + the 3 the role
cap reaches), and 5 are done: entry 1, mid 10, senior 12, lead 12. Priced at item 191's higher per-tier means (entry
$0.052, mid $0.069, senior $0.083, lead $0.093) that is **$2.85**, so the projected total is **$11.28** of $13.00, leaving
$1.72. The conditions in the plan to continue without asking are met: projection under the cap, 0 of 5 rejected. Stated
limit: five requests are not a distribution, and a rewrite costs a further request.

**Paid run C, the sweep of the remaining 35 cells (2026-10-28):** `--cell` x 35 (tiers interleaved) `--skip-existing
--max-spend 3.50 --max-total-spend 13 --confirm-paid`, the log's own marker `SWEEP_EXIT=0`, 35 written, **none rejected, no
rewrite**, **$2.7867** (projection $2.85), `$11.2104 of $13.0000 in all`. About 40 seconds a cell. **Branch total on author
spend: $3.3307** ($11.2104 minus the $7.8797 logged at the start): $3.1474 on the 40 kept cells and **$0.1833 on the two
discarded `electrician-lead` outputs** (runs A and A2, kept in the scratchpad). The call log's total includes the one request
of item 191 whose billing is unknown. Every cell carries `prompt_version golden-author-2`, effort `medium`.

**Four pairs were unsound after regeneration, found by `pairs`.** A pair's authored `transferable` terms must appear in both
the résumé and the posting, and fresh prose no longer contained some: `registered-nurse-entry-to-registered-nurse-mid`
("Bedside handoff" not in the posting), `sre-ops-mid-to-sre-ops-senior` ("Kubernetes" and "Microsoft Azure" not in the
posting) and `registered-nurse-mid-to-medical-assistant-mid` ("team" not in the résumé). Re-picked, keeping any term that
still held, from skill names that appear in both documents (`scratchpad/pair_terms.py`): `Care planning` + `Patient
assessment`; `Ansible` + `Backup and recovery`; `patients` + `Vital signs`. Written with `load_manifest`/`write_manifest`,
not by hand. These are authored fields, so this is a judgment, not a derivation: the terms are real overlaps, and a different
reasonable pick exists. `pairs`, `manifest` and `check` then ran clean: **`OK (96 cells)`**.

**The diff against `b62c704`:** 40 cells, 60 fixture directories (40 cell fixtures + **20** pair fixtures, not 18: the two
extra are `construction-pm-entry-to-construction-pm-mid` and `product-mgmt-mid-to-project-mgmt-mid`, which use the three cells
the role cap reached), `manifest.json`, the code, the tests and docs. Nothing else.

**A guard over the real matrix (C-11, the recurrence of "a check passed data a person could see was wrong").**
`tests/test_golden_facts.py::test_a_cells_credentials_are_asked_dated_and_ordered_like_a_real_career`, per profession over all
four tiers: the posting requires the highest credential held, years do not fall with the tier, and a mid-or-higher credential
is not dated after the earliest role titled for its tier. 24 cases, pass. The old stored profiles from `b62c704` would have
failed it (21 of 37 disordered, 28 of 37 late); that is a count from my audits, not a run of this test against them.
**Unenforced and said plainly:** entry-tier credentials are unbound (13 of 37 under the strict rule), and whether prose reads as
real is still a judgment that only a hand-read supplies.

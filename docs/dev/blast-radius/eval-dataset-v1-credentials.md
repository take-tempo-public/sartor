# Blast radius — eval-dataset-v1-credentials

> **Branch:** `feat/eval-dataset-v1-credentials`
> **Status:** enumeration complete before the first code edit (2026-10-29). Measurements below were taken on `main` at `6b93e7c` and are re-run after the change.

Item 194, findings 1 and 2 of the handoff `eval-dataset-v1-finish`. Owner decisions (chat, 2026-10-29): finding 1 is fixed (entry-tier credentials are bound to the career start); finding 2 is fixed with a fail-closed check plus regeneration of only the cells it flags; finding 3 (the employer pool) is accepted for v1; the author-spend cap for this work is a total of **$14.00** (`--max-total-spend 14.00`; the call log read $11.2104 on entry).

---

## Surface

- `evals/golden_set.py`, `build_profile`: the `role_start` / `role_cap` / `caps` / `entry_cap` / `cert_years` block (~1848 to 1877). Changes: an entry-tier credential's cap becomes the year of the earliest role (`first_year`), replacing the `entry_cap` rule.
- `evals/golden_set.py`, `check_prose` (~426) and a new `check_jd_credential_status`: a JD sentence that names a credential and says "prefer" is refused when the cell's facts name no credential above its tier.
- `evals/golden_set.py`, the builder's "State … as a required licence or certification." / "State … as preferred." phrases (~1921 to 1924): hoisted into shared constants so the check and the brief cannot drift. The profile output must stay byte-identical.
- `evals/golden_author.py`, `author_cell` (~351): calls the new check next to `check_slot_text`, so a violation uses the existing one-rewrite budget.
- Docstrings that say entry-tier credentials are unbound: `evals/golden_set.py:288` (`_certification_problems`), `evals/README.md:550`, `tests/test_golden_facts.py:75`.

Not touched: `AUTHOR_SYSTEM_PROMPT`, `build_user_prompt`, `AUTHOR_PROMPT_VERSION`, any slot brief, any facts file, `evals/catalog/costs.json`, `evals/prompt_hashes.json`. A brief change would change every `profile.json` (and `check_cell` refuses a prose whose `profile_sha256` differs), which is all 96 cells.

---

## Enumeration

Commands run on `main` (6b93e7c); `git grep -n -F` over the whole tracked tree, excluding `docs-site`, `evals/results` and the generated `cells/` and `fixtures/` (their content is the output, counted separately below).

```
build_profile             tests/test_golden_set.py(49) docs/dev/blast-radius/eval-dataset-v1.md(9) docs/dev/blast-radius/eval-dataset-v1-finish.md(5)
                          docs/dev/blast-radius/eval-golden-breadth.md(3) evals/golden_set.py(2) docs/dev/work/items/0194-...(2) docs/dev/handoffs/feat-eval-dataset-v1.md(2)
                          tests/test_golden_reachability.py(1) tests/test_golden_facts.py(1) tests/test_golden_author.py(1) evals/golden_author.py(1)
                          docs/wiki/log.md(1) docs/dev/handoffs/eval-dataset-v1-finish.md(1) CHANGELOG.md(1)
entry_cap                 evals/golden_set.py(2)
role_cap                  evals/golden_set.py(3) docs/dev/blast-radius/eval-dataset-v1-finish.md(1)
cert_years                evals/golden_set.py(2) docs/dev/blast-radius/eval-dataset-v1-finish.md(4) docs/dev/handoffs/eval-dataset-v1-finish.md(1)
_certification_problems   evals/golden_set.py(2) docs/dev/handoffs/eval-dataset-v1-finish.md(2) docs/dev/blast-radius/eval-dataset-v1-finish.md(1)
check_slot_text           evals/golden_set.py(3) evals/golden_author.py(2) tests/test_golden_set.py(4) tests/test_golden_author.py(2) docs/dev/blast-radius/eval-dataset-v1.md(2)
check_prose               evals/golden_set.py(4) tests/test_golden_set.py(5) tests/test_golden_author.py(3) docs/dev/blast-radius/eval-dataset-v1.md(1)
"as preferred"            evals/golden_set.py(1) tests/test_golden_set.py(1) evals/README.md(1)
"as a required"           evals/golden_set.py(2) tests/test_golden_set.py(2) tests/test_golden_facts.py(1)  (the other hits are unrelated prose)
```

Second pass, the prose forms the rule goes by: `git grep -n -i -E "entry-tier credential|unbound|not bound by a role"` found the live statements at `CHANGELOG.md:26`, `evals/README.md:550`, `evals/golden_set.py:1850,1851,1868`, `tests/test_golden_facts.py:75`, `docs/dev/eval-redesign-design.md:779` and `docs/dev/work/items/0194-eval-dataset-v1-finish.md:29,50`; the rest are dated records (the earlier dossier and handoffs) and unrelated uses of "unbounded".

Negative results: no module outside `evals/golden_set.py`, `evals/golden_author.py` and the three golden test files calls `build_profile`, `check_slot_text` or `check_prose`. No JS, template, CSS or TOML consumer (the golden set is not read by the product, the dashboard or the runner's code paths that this change reaches). Wiki pages naming the builder: `docs/wiki/pages/{code-module-map,deterministic-llm-boundary,eval-harness,llm-call-catalog}.md`.

Generated data the change reaches (measured, free, scratch script over `evals/golden/golden-v1/`, 96 cells):

- Finding 1: **22** cells hold an entry-tier credential dated after the cell's earliest role start (23 credentials). The builder diff (`golden_set check`) is the authority for the regeneration set; 22 is a prediction.
- Finding 2, under the facts-based rule: **4** cells: `accounting-senior`, `carpenter-foreman-lead`, `construction-pm-senior`, `logistics-driving-lead`. A broader "credential word in about/duties" rule would flag 35 cells; it was rejected (most of those sentences are consistent with `needs`, and some are false positives such as "licensed electricians"). Three further hits of the facts-based rule were read and are not contradictions: `product-mgmt-senior` and `web-backend-senior` (a "Licensure and qualifications" heading) and `ux-design-senior` ("No clinical licence or professional certification is required").
- Union **25** cells (overlap `accounting-senior`). Recorded last-generation cost of those 25: **$1.7635** (mean $0.0705, dearest $0.0981). Headroom under the $14.00 total: $2.7896.
- Pairs, fixtures and manifest hashes follow from a regenerated cell: `python -m evals.golden_set pairs`, then `manifest`, then `check`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/golden_set.py` `build_profile` (~1848 to 1877) | **update** | Entry-tier cap becomes `first_year`; delete the `entry_cap` rule. Test first. |
| 2 | `evals/golden_set.py` `build_profile` (~1921 to 1924, the `cert_ask` phrases) | **update (refactor, byte-identical)** | Hoist the two phrases to module constants shared with the new check. Profile bytes must not change; the stale-cell list from `golden_set check` is the proof. |
| 3 | `evals/golden_set.py` `check_prose` (~426) and new `check_jd_credential_status` | **update** | The on-disk gate: `golden_set check` and CI fail on a stale cell. |
| 4 | `evals/golden_set.py` `_certification_problems` (288) | **update (docstring only)** | It cannot check the entry cap (a profile carries no tier map); the docstring says so. No logic change. |
| 5 | `evals/golden_set.py` `check_slot_text` (395) | **no change** | It takes no profile; the new check needs the cell's "as preferred" fact, so it is a separate function, not a new argument. |
| 6 | `evals/golden_set.py` `check_cell` (744) and `render`/`pairs` callers of `check_prose` (720, 755, 965) | **no change** | They call `check_prose`, so they pick the new check up. Verified by the tests below. |
| 7 | `evals/golden_author.py` `author_cell` (~351) | **update** | Call the new check beside `check_slot_text` so a violation is rewritten inside the existing budget. |
| 8 | `evals/golden_author.py` `AUTHOR_SYSTEM_PROMPT` (75), `build_user_prompt` (136), `AUTHOR_PROMPT_VERSION` (59) | **no change** | Unchanged text, so no version bump and no re-lock of `evals/prompt_hashes.json`. The test that pins both hashes confirms it. |
| 9 | `tests/test_golden_facts.py:68` (`test_a_cells_credentials_are_asked_dated_and_ordered_like_a_real_career`) | **update** | Remove the `tier == 0: continue` exemption: an entry-tier credential must be no later than the earliest role. Fails on `main`. |
| 10 | `tests/test_golden_set.py:1045` (`test_a_credential_is_dated_no_later_than_the_role_titled_for_its_tier`) | **update** | Same exemption removed; the expected count of checked credentials changes with it (the test's own `control(checked == 80, …)`). |
| 11 | `tests/test_golden_set.py` `TestCertifications` and the `check_prose` tests (1231 to 1281) | **new tests** | The four real sentences are refused; a cell with a preferred credential may state one; "Preferred: experience with Procore" and the three false-positive sentences pass. |
| 12 | `tests/test_golden_author.py` (170, 261, 270, 296, 379) | **no change, re-run** | Fake-client tests that build their own profiles; they pass `check_prose` and must still. |
| 13 | `tests/test_golden_reachability.py` | **no change, re-run** | Calls `build_profile`; reads no credential year. |
| 14 | `evals/golden/golden-v1/cells/<c>/`, `fixtures/<c>--*/` for the regeneration set | **regenerate** | The author tool refuses an existing cell, so the stale ones are deleted (`git rm`) and rewritten under the cap. Hand-edits are forbidden. |
| 15 | `evals/golden/golden-v1/pairs/` and `manifest.json` (hashes, `pairs`) | **re-derive** | `pairs`, `manifest`, `check`. A pair's authored `transferable` term is re-picked only if `check` says the new prose lacks it. |
| 16 | `evals/README.md:548 to 550` | **update** | States that an entry-tier credential is unbound; now it is bound to the career start. |
| 17 | `CHANGELOG.md:26,36` | **update** | New entry under Unreleased with the counts and the spend. The old lines are dated history of the previous branch and are not edited. |
| 18 | `docs/dev/eval-redesign-design.md:779` | **update** | The status line for the three open findings. |
| 19 | `docs/dev/work/items/0194-eval-dataset-v1-finish.md:29,50` | **update** | Findings 1 and 2 done, finding 3 accepted with the owner's reason; spend. The item stays `open` for scopes 3 to 6. |
| 20 | `docs/wiki/pages/{code-module-map,deterministic-llm-boundary,eval-harness,llm-call-catalog}.md` and `docs/wiki/log.md` | **check, then log** | `is_wiki_relevant` decides; if a page states the credential rule it is edited in this branch, else a "verified no-edit" entry. |
| 21 | `docs/dev/blast-radius/eval-dataset-v1-finish.md`, `docs/dev/handoffs/*` | **no change** | Dated records of what was observed and decided then. |
| 22 | `scripts/enforcement/blast_radius.py` registry | **no change** | `evals/golden_set.py` is not a gated surface; this dossier is written because `check_slot_text` / `check_prose` are shared helpers (charter C-10, `AGENTS.md`). |

---

## Deferred

- **Finding 3, the employer pool (accepted for v1, owner 2026-10-29).** 216 roles draw on 59 invented employer names; 32 names appear in two or more professions ("Riverbend Health Network" and "Ironbridge Co" in 8 each). Only 5 of 24 professions name their own employers (`carpenter-foreman`, `electrician`, `hvac-technician`, `logistics-driving`, `teacher`). The owner's reason: the names are invented, used only by a backend eval dataset, and have no effect on any eval score. The fix (an `employers` list of at least three names in the other 19 facts files, which `_employers_for` already honours) would redraw the employers of 76 of the 96 cells, about $6 of author spend; it belongs in a `golden-v2`. **Constraint:** the calibration run (item 194 scope 3) scores this set, so a later cell change invalidates it; any such change lands before that run.
- **A rule on `required` claims.** The facts-based rule covers "preferred with nothing to prefer". It does not catch a sentence that calls a held credential preferred while `needs` requires it when an absent credential also exists, nor a second credential called required. **Unenforced**, and said so (charter C-0).
- **Paraphrase.** The check is a word list (`certif|licen[cs]|credential|endorsement|accredit` with `prefer`). "Ideally" or "a plus" next to a credential passes. **Unenforced.**
- **The entry cap before a paid request.** `_certification_problems` cannot see the facts' tier map, so the cap is checked by the gate tests, not at the point of spend. A candidate for item 194's next branch: have `golden_author` run the matrix invariants as a preflight over every cell it is about to write (the handoff's recurrence 2).
- **73 of the original 96 cells were never read whole.** This branch reads the changed passages of every regenerated cell and the whole of three.
- **The same-year convention.** Binding an entry credential to `first_year` dates it in the same calendar year as the first role, as the mid-tier cap already does (a Journeyman licence 2013 against a role from January 2013). A card earned the year before is equally plausible; the floor is unchanged so that no other cell's years move.

---

## Verification

- Before any edit: the two measurements above. After the change: `python -m evals.golden_set check` names exactly the cells whose profile changed; it must equal the finding-1 prediction (22) or the difference is explained here. Cells outside that list must be byte-identical (`git diff --stat` shows no `profile.json` change for them).
- After regeneration: re-run both measurements over the 96 cells; expect 0 late entry-tier credentials and 0 unbacked "preferred" sentences; `golden_set check` prints `OK (96 cells)`.
- A missed consumer surfaces as a failing test: rows 9 to 13 run under `python -m pytest tests/test_golden_set.py tests/test_golden_facts.py tests/test_golden_author.py tests/test_golden_reachability.py` with `PYTHONUTF8=1`, then the full `python -m scripts.gate`.
- Spend: the call log's author total stays at or under $14.00; `golden_author` stops before a cell that would reach either cap.

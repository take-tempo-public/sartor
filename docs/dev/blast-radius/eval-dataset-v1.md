# Blast radius — eval-dataset-v1

> **Branch:** `feat/eval-dataset-v1` (item 191, eval redesign step 3b-ii)
> **Status:** enumeration complete at `77decd4` (`main`), written before the first code edit. This branch changes the
> generator's guards and CLI, adds the facts for about 24 professions and three authored families, replaces the three
> converted pilots with generated cells, and runs the paid generation in stages. The calibration run, tier sizes,
> retiring `evals/fixtures/synthetic/` and the freeze move to a follow-on item (owner's staging direction, 2026-10-28:
> no run that has to be repeated, no stall that is paid twice, stepwise learning).

---

## Surface

Changed (none is on the `scripts/enforcement/blast_radius.py` registry, which has no golden path, so no hook fires and
this dossier is the prose-binding C-10 step):

- `evals/golden_set.py` — `validate_facts` (an optional `level` on an industry; one per tier when any has it), a small
  `industries_for(facts, level)` helper next to `build_profile`. `build_profile`'s signature is unchanged.
- `evals/golden_author.py` — `main` (new flags, a total-spend cap read from the call log, resume, a rejects directory, a
  consecutive-failure stop), `author_cell` (a render dry-run before a reply is accepted), the request's client options.
  `AUTHOR_SYSTEM_PROMPT` and `build_user_prompt` are **not** touched, so `AUTHOR_PROMPT_VERSION` stays `golden-author-1`.
- `evals/golden/golden-v1/manifest.json` — three new families, about 21 new `professions` rows, `pilot_waivers` emptied,
  the pilot `pairs` replaced; later `files` re-stamped by `python -m evals.golden_set manifest`.
- `evals/golden/golden-v1/facts/*.json` — new directory, about 24 files. Already hashed by `tracked_files`.
- `evals/golden/golden-v1/cells/`, `fixtures/` — the three converted pilot cells and their fixtures and both pilot pairs
  are deleted; generated cells and derived pairs are added.
- Tests: `tests/test_golden_set.py`, `tests/test_golden_author.py`, `tests/test_eval_golden_runner.py`,
  `tests/test_golden_reachability.py`.
- Docs: `evals/README.md`, `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` (6.4), work items 191 and a new follow-on.

Not touched: `evals/runner.py`, `evals/eval_catalog.py`, `evals/fixtures/synthetic/`, `blueprints/diagnostics.py`,
`analyzer.py` (reads `LOG_DIR` only), `hardening.py`, any pin, `PROMPT_VERSION`, `docs/governance/`.

---

## Enumeration

Greps with the Grep tool on 2026-10-28 at `77decd4`. Counts are from the tool output.

```
Grep "validate_facts|ladder_for|\bbuild_profile\(|industries="  (*.py,md,toml,json, whole tree)      -> 5 definitions/uses in evals/, 40 test lines, 6 doc lines
        golden_set.py: validate_facts :1382, ladder_for :762, build_profile :1504
        golden_author.py: ladder_for :355, build_profile :356 (the only non-test caller)
        tests: test_golden_set.py (~38 lines), test_golden_reachability.py :308, test_golden_author.py :166
Grep "golden_author|AUTHOR_PROMPT_VERSION|AUTHOR_MODEL|EXIT_OVER_BUDGET|max-spend|confirm-paid"
        (whole tree minus handoffs, ledger, results, .git, count)                                      -> 182 hits, 30 files
        code/tests that read it: analyzer.py 1, hardening.py 1, evals/eval_catalog.py 4, evals/runner.py 15,
        evals/golden_set.py 1, evals/catalog/dataset_author.toml 2, tests/test_call_kind_telemetry.py 2,
        tests/test_golden_reachability.py 4, tests/test_eval_spend.py 8, tests/test_golden_author.py 32,
        tests/test_eval_catalog.py 3, tests/test_model_overrides.py 1
Grep "pilot_waivers|\"pairs\"|\[\"families\"\]|\[\"professions\"\]|get\(\"professions\""  (*.py,toml,yml)    -> golden_set.py 8 sites, tests 4 files
Grep "borealis-labs|lattice-cloud|atrium-health|data-ml-entry|sre-ops-mid|product-mgmt-senior"
        (whole tree minus handoffs, ledger, results, evals/golden, .git, count)                        -> 6 hits, 5 files
        CHANGELOG.md 1, eval-golden-breadth.md 1 (historical), test_eval_golden_runner.py 1,
        test_golden_reachability.py 1, test_golden_set.py 2
Grep "golden" in scripts/                                                                              -> scripts/wiki_relevance.py :58-60 only
Grep "golden_set|golden_author|golden-v1" in tests/test_data_root.py                                   -> :282 (a reason string)
Grep "golden" in tests/test_eval_catalog.py                                                            -> :34, :67 (`_SUITE_DIRS`), :238 (the author pin)
Grep "golden|logs/" in .gitignore                                                                      -> `logs/` (:48); no golden entry
```

Call log, measured 2026-10-28: `logs/llm_calls.jsonl` is 576,562 bytes, 1,564 rows, **0 rows with `call="dataset_author"`**
(so no real author call has ever been made on this machine). `analyzer.LOG_PATH` and `evals.runner.LLM_LOG_PATH` are both
`sartor_home.data_path("logs", "llm_calls.jsonl")`: one file under two names. A full scan at start costs milliseconds at
this size; a byte-offset scan between cells (the pattern of `runner._log_offset` / `_trace_cost`) costs only the new rows.

Negative results (also findings):
- **0** consumers of `facts/` outside `golden_author.main` and `golden_set` (the directory does not exist yet). No wiki
  page cites a `facts/` path.
- **0** readers of `manifest["pilot_waivers"]` outside `golden_set.check_suite` and two tests; `evals/runner.py` and
  `evals/eval_catalog.py` never read the manifest.
- **0** hits for `golden` in `.github/`, `pyproject.toml` and `.githooks/`: CI does not run `python -m evals.golden_set
  check`; it is covered only by `TestCommittedSuite` inside the gate's pytest run.
- `golden_author` is imported by `evals/runner.py:88` and `evals/eval_catalog.py:339`, so **an import error in
  `golden_author` breaks the whole eval runner**: every edit is followed by `python -c "import evals.runner"`.

Found while enumerating (each changes the plan):
1. **A paid reply can be lost after payment.** `render_fixtures` calls `pick_edit_target` (`golden_set.py:463-476`) on the
   iteration target slot (`r1.b2`, a no-number bullet of 8 to 40 words). It raises `ValueError` when the text has no
   stretch of five words between commas, semicolons, colons or brackets. `author_cell` checks each slot with
   `check_slot_text` only, `check_prose` is the same rule set (read, `golden_set.py:385-404`), so the text passes, the
   cell is returned and paid for, and then `gs.write_cell` (`golden_author.py:399`, outside the `try`) raises an
   uncaught `ValueError`: a traceback, no cell written, the prose gone, and the cost never added to `spent`.
   Decision (as built): `pick_edit_target` is the only text-driven raise in the render path (read: the other is an unknown
   section kind), so `author_cell` runs it on the iteration target slot in the same pass as `check_slot_text` and counts a
   `ValueError` as a failure of that slot; the rewrite request repairs it inside the same attempt budget. A
   `render_fixtures` call after acceptance is a backstop, and `main` also catches `ValueError`/`OSError` from `write_cell`
   and keeps the prose. Observed: with the unmodified code, a comma-split reply is accepted after one request
   (`tests/test_golden_author.py::TestRenderBeforeAccepting::test_such_a_target_is_rewritten_alone_in_the_same_cell`
   failed first, `assert 1 == 2`).
2. **A failed attempt is invisible to the cap.** `spent` (`golden_author.py:386`) is per invocation and adds a cell's
   cost only on success. A cell rejected after two requests is paid for and uncounted. And `log_judge_call` with
   `response=None` records zero tokens, so a request that errors client side (a timeout after the server began
   generating) is **unpriced in the log** and cannot be counted at all. Stated limit; the mitigation is fail-fast.
3. **The client has SDK defaults.** `runner._get_client` (`evals/runner.py:237-245`) builds `anthropic.Anthropic(api_key)`:
   a 600 s timeout and 2 automatic retries, none of which writes a row. A hang can be re-sent and billed twice, and
   only the last attempt is logged.
4. **Every generated profile carries an `iteration`** (`build_profile`, `iteration.mode = "derived"`), so every fixture's
   `expected.json` gets `iteration_scenarios` and `iterate_clarify` fires for every fixture in generate mode. That
   raises the per-fixture price of an eval run and is the follow-on item's cost input; it is not an authoring cost.
5. **Four tests are tied to the three pilots by name** (Consumers 12 to 15 below) and must move with the cells.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/golden_set.py:1382-1441` `validate_facts` | update | accept an optional `level` on each `industries[]` entry; when any entry has one, exactly one entry per tier and no entry without one. Facts without any `level` validate as before, so `FACTS`/`CERT_FACTS` in the tests are unchanged. |
| 2 | `evals/golden_set.py` `build_profile`, the `chosen = ...` line (was `:1647`) | update (default only) | an explicit `industries=` still wins; otherwise `industries_for(facts, level)`; otherwise the first two as before. The signature is unchanged, so no caller changes and facts without tiers build byte-identical profiles (the pinned prompt hash and `cell_seed_for` tests prove it). |
| 3 | `evals/golden_set.py` new `industries_for(facts, level)` | new | returns `[slug]` for a tier's entry, or `None` for facts that name no tiers; the single place the rule lives. |
| 4 | `evals/golden_set.py:762` `ladder_for`, `:775` `_check_ladders` | no change | families are data; three more families pass the same checks (four tiers, `rule_source`, `label`, years, roles fit). |
| 5 | `evals/golden_set.py:1012-1091` `check_suite`, `:1055-1063` waivers | no change | with `pilot_waivers = []` and every cell generated, no predicate fails and no waiver is stale. A draft suite stays valid at every intermediate state (a partial set passes). |
| 6 | `evals/golden_set.py:945-1010` `_pairs_wanted`, `check_pairs`, `write_pairs` | no change | re-derive each pair from its two fixtures; the old pairs are removed from the manifest in the same commit as the pilot cells, new ones added after the cells exist (step 7), so no commit has a pair naming a missing fixture. |
| 7 | `evals/golden_set.py:463-476` `pick_edit_target` and `:479-502` `render_expected` | no change | the defect is handled at the caller (finding 1), not by loosening the rule: the edit target must survive generation. |
| 8 | `evals/golden_author.py` `author_cell`, `AuthorError`, `AuthorRejected` | update | the iteration target is checked with `pick_edit_target` per slot, a `render_fixtures` backstop follows acceptance, and every `AuthorError` carries `usage`, `replies` and `request_ids` (finding 2). Callers of `author_cell` (Grep `author_cell\(`, 26 hits in 3 files): its definition and `main`, 24 in `tests/test_golden_author.py` and `tests/test_golden_reachability.py`. |
| 9 | `evals/golden_author.py` `main` and its argument list | update | adds `--cell P:L` (repeatable), `--skip-existing`, `--max-total-spend` (required with `--confirm-paid`), `--max-consecutive-failures` (default 2); `--profession`/`--level` become optional but go together; `logged_spend`, `cost_of_usage`, `_keep_reject` are new. `--max-spend` stays (this run's cap). Exit codes 0, 1, 3, 4 keep their meanings; a batch now continues past a rejected cell (up to the limit) and exits 1 at the end. A missing or unreadable facts file is now a message and exit 1, not a traceback. |
| 10 | `evals/golden_author.py` the client in `main` | update | `runner._get_client().with_options(timeout=AUTHOR_TIMEOUT_SECONDS, max_retries=0)`. `AUTHOR_TIMEOUT_SECONDS = 420` is **unobserved** (no real call has been timed); the first paid cell's latency revises it. `AUTHOR_MAX_TOKENS`, effort and thinking settings are unchanged and the pinned-prompt test covers the prompt bytes. |
| 11 | `evals/runner.py:237-245` `_get_client` | no change | other callers (judges, the runner) keep the SDK defaults; the author narrows its own client with `with_options` instead of changing a shared helper. |
| 12 | `tests/test_eval_golden_runner.py:30,53-57,142,205-222` `PILOT_CELLS` and the counts | update | replaced by counts derived from the committed manifest; the "pair runs on its résumé's cell" mapping stays. |
| 13 | `tests/test_golden_reachability.py:266-301` `TestCommittedPilots` | update | the waiver assertion goes (no waivers); the "iterating pilot" assertion (`sre-ops-mid--lattice-cloud`, exactly one `iterate_clarify`) is replaced: every generated fixture iterates (finding 4), so it asserts one `iterate_clarify` per fixture that has `iteration_scenarios`. |
| 14 | `tests/test_golden_set.py:1121-1224` `TestWaivers`, `TestConverter`, `TestParser`, and `:1255-1280` `TestCommittedSuite` | update / keep | the converter tests read `evals/fixtures/synthetic/` and stay until that directory is retired (follow-on); they build in `tmp_path`, not the committed suite. The pair assertions at `:1263-1279` name the pilots and are rewritten to the new pairs. |
| 15 | `tests/test_golden_author.py:355-460` `TestCommandLine` | update | `--max-total-spend` becomes required with `--confirm-paid`; the helper `_args` and five tests pass it. New tests: resume, the total cap counting a failed attempt, a render failure, the consecutive-failure stop. |
| 16 | `tests/test_golden_author.py:121-170` `TestRequest` | update | adds an assertion that the request kwargs and `AUTHOR_SYSTEM_PROMPT` bytes are unchanged and that the client is narrowed. |
| 17 | `tests/test_eval_catalog.py:34,67,238` | no change | reads `golden_author.AUTHOR_MODEL` and `GOLDEN_DIR`; re-run to confirm, since every fixture's `expected.json` is read for `covered` cases. |
| 18 | `tests/test_data_root.py:282` `_CODE_ANCHORS["evals/golden_set.py"]` | no change | the rejects directory comes from `analyzer.LOG_DIR` (`sartor_home.data_path`), so no new `Path(__file__)` anchor is added. |
| 19 | `evals/catalog/dataset_author.toml` | no change | the call kind and the exempt reason are unchanged. |
| 20 | `scripts/wiki_relevance.py:58-60` | no change | `evals/golden/` is already irrelevant data; `golden_set.py` and `golden_author.py` stay relevant, so a scoped `/wiki-self-update` runs at close-out. |
| 21 | `docs/wiki/pages/eval-harness.md:264,268`, `code-module-map.md:133` | update (close-out) | the wiki scribe step, committed before the PR. |
| 22 | `evals/README.md` golden-set sections, `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` 6.4 | update | the new flags, facts, families, counts, the measured cost, and the staging. |
| 23 | `.gitignore` | no change | `logs/` is already ignored and the rejects directory is under it. |
| 24 | work items: 191 (updates), a new follow-on item, epic 180 | update | item ids are allocated at commit time. |
| 25 | `evals/golden_set.py` `build_profile`: the theme and skill picks, the role-tier theme pool | update (added after stage 2) | `_cycle` replaces `_pick` for a bullet's skill and theme and for an intro's theme; `leadership_themes` joins the pool for roles at senior tier or above only. This **changes the bytes of every built profile** (pre-freeze, on purpose), so every cell written before it is stale; the five such cells were deleted and regenerated. `cell_seed_for`, `_tenures`, employers and figures are untouched. Consumers: `build_profile` callers are `golden_author.main`, `check_suite` (new) and the tests (grep above). |
| 26 | `evals/golden_set.py` new `_check_cell_matches_facts`, called from `check_suite` | new | a generated cell must equal `build_profile(facts, ladder, level)`; a converted pilot is exempt. Tests that built cells from inputs the manifest does not record (a second profession without a facts file, a ladder override) were updated to record them (`_pair_suite`, `_built_suite`). |
| 28 | `evals/golden_author.py` `AUTHOR_SYSTEM_PROMPT` rule 3 and `AUTHOR_PROMPT_VERSION`; `evals/golden_set.py` skill and certification traps | update (owner-directed) | the prompt now says required strings are matched ignoring case and should be written in lower case mid-sentence unless a proper name, acronym or sentence start; version `golden-author-1` becomes `golden-author-2` (hash `sha256:816b0dbd...`). Because a lower-case claim would slip past a case-sensitive trap, `(?i)` is now on the skill and certification traps (the generic traps are unchanged on purpose: "PhD" matches only in that spelling). This changes every built profile's `forbidden_inventions`, so cells written before it are stale; the five were deleted. **Untested against the model:** the paid test on two cells is pending. Prompt consumers: `golden_author` only (it is not in `_BASE_SYSTEM_PROMPTS`, the prompt lock or the catalog), `check_suite` reads the recorded hash. |
| 27 | `tests/test_golden_author.py::TestConstants::test_the_prompt_text_has_not_moved` | update | its user-prompt hash was computed from builder output, which row 25 changed; it now pins `build_user_prompt` on a fixed literal profile, so a builder change is not mistaken for a prompt change. |

---

## Measured before any spend (2026-10-28, no model, no money)

**What was read.** The O*NET 31.0 licence page, raw (`curl`, text extracted): CC BY 4.0, limited to the downloadable
files on three pages, with a credit text that includes "has modified all or some of this information", and a
trademark rule that the name is never used in the possessive or plural (one existing evidence line broke it and was
reworded). Six tables from `https://www.onetcenter.org/dl_files/database/db_31_0_csv/` were downloaded and read:
`occupation_data`, `task_statements`, `software_skills`, `job_titles`, `sample_of_reported_titles`, `job_zones`. 31.0
names its tables differently from older releases (there is no Technology Skills or Alternate Titles file). **Not read:**
the UK DDaT ladders and the OGL text. They are not relied on: no DDaT content is copied, every ladder stays
`rule_source = "authored"`, and the tech-product ladder is unchanged. The mapping evidence for each of the 21 new
profession rows is in `manifest.json`. Counted from it: 18 of the 24 rows are `exact` and 6 are `nearest` (mobile,
hardware and embedded, UX, social services, and product management and site reliability from 3a); three rows also name
a second occupation for their top tier (social services, carpentry and driving).

**The matrix.** 24 professions in the owner's four groups (9, 6, 4, 5) make 96 fixtures with one JD each; the 96
postings are spread over the five settings (startup 17, enterprise 34, health and nonprofit 22, small business 18,
public sector 5, which is 5.2 percent). `tests/test_golden_facts.py` pins all of that and runs in 5 s.

**The full-size rehearsal** (a throwaway test, deleted; stub prose that is distinct per slot): the 96 cells built and
written in 1.6 s; 24 advance pairs derived and the manifest stamped in about 10 s; `check_suite` over 96 cells, 24
pairs and 24 facts files in 3.6 s; the real pipeline against the recording stub fired exactly the planned call kinds for
all 120 fixtures, in generate mode (3.9 s) and assemble mode (18.9 s); `--estimate` counted 1,512 calls (generate) and
1,632 (assemble) with nothing skipped. Slots per cell are fixed by the ladder: 11, 17, 23 and 26 for entry, mid,
senior and lead, so 1,848 slots in all.

**What the rehearsal found.** With the shared test stub (every bullet is a skill plus the word "steady") 19 of 96
fixtures came back `scenario_misaligned` in assemble mode. Observed on `accounting-entry--tax-firm`: the assembler kept
three of four bullets and dropped the iteration target, which was a near-duplicate of the bullet after it. That is a
property of the degenerate stub, not of the dataset; with distinct stub prose all 96 align. It does show that **a
derived iteration scenario depends on its target bullet surviving assembly**, which model prose that repeats itself
within a role could break. It is the declared `scenario_misaligned` signal, and the calibration run (follow-on item)
is where its real rate is measured.

**The cost, with its one unknown stated.** From the committed facts (4 characters a token and 1.35 tokens a word are
assumptions): the 96 prompts are 988,076 characters, about 247,000 input tokens, $0.99 at $4 a million. Visible output
at the slots' minimum, middle and maximum word counts is about 32,000, 86,000 and 140,000 tokens: $0.65, $1.72 and
$2.79 at $20 a million. **Adaptive thinking tokens are billed as output and have never been observed:** at 2,000,
5,000 or 10,000 tokens a cell they add $3.84, $9.60 or $19.20 over 96 cells. So the whole set is about $2.7 if the
model barely thinks, and the first paid cell's thinking tokens decide whether it is $6 or $20. The earlier "$0.05 to
$0.14 a cell" was a guess about that number. `AUTHOR_EFFORT` is `medium`; a lower effort is the lever if the first
cell shows thinking dominating, and it changes no prompt text. Nothing was sent when this was written.

**Stage 1, observed (the first paid call, 2026-10-28):** `web-backend-lead`, 26 slots. One request, `end_turn`, accepted
on the first attempt, 31.3 s; **4,807 input tokens and 3,449 output tokens, $0.0882** (the run's count and the call log
agree). The 631 words of visible text are about 850 tokens, so about 2,600 tokens, three quarters of the output, were
thinking. Two assumptions above were wrong: the prompt is about 2.8 characters a token, not 4 (the 96 prompts are then
nearer 350,000 input tokens than 247,000), and the 420 s timeout was set against a latency that is a tenth of that
(now 180 s). A projection from this one cell, assuming thinking is between a third and all of its observed size on the
lighter tiers: $0.044 to $0.075 for an entry cell, $0.064 to $0.082 for mid, $0.083 to $0.089 for senior, and
$0.088 for lead, so **about $6.7 to $8.0 for the 96**. One sample is not a distribution; stage 2 adds four more.

**Stage 2, observed (four cells, 2026-10-28):** `teacher-mid` (public-sector JD, own employers) $0.0655 in 23.2 s,
`electrician-entry` $0.0446 in 16.3 s, `accounting-senior` $0.0815 in 27.0 s, `ux-design-senior` $0.0790 in 31.5 s.
All four accepted on the first attempt, no rewrite, no refusal, `end_turn`, counted equal to logged ($0.2707 for the run,
$0.3589 for the five cells). Cost tracks slot count: $0.0040, $0.0039, $0.0035, $0.0034 and $0.0034 a slot for 11, 17,
23, 23 and 26 slots. That puts one profession at about $0.28 and the 96 cells at about **$6.7**, the low end of the
projection above.

**What hand-reading the five cells found, and what was done.** Three things, two of them defects of the builder or the
facts, found at cell 5 and not cell 96:

1. *Leadership leaked into entry roles.* `electrician-entry`: an apprentice "directs helpers and apprentices on daily
   tasks", which contradicts the ladder's own scope for that tier ("working under a journeyman who checks the work").
   Cause: `work_themes` is one pool every tier draws from, and seven professions had leadership work in it. Fix:
   an optional `leadership_themes` in the facts, offered only to roles at senior tier or above, and the seven themes
   moved out of `work_themes`; every profession now has one or two (`tests/test_golden_set.py::TestLeadershipThemes`).
2. *The same skill or theme filled half a résumé.* `accounting-senior` names "Month-end close" in 6 of its 12 bullets,
   `web-backend-lead` repeats "API versioning" in 4 of 15, `teacher-mid` repeats "Nearpod" in 3 of 8. Cause: each
   bullet's skill and theme was drawn independently with replacement. Fix: `_cycle` walks one hashed order, so no item
   is used twice before all are used once (`TestEvenCoverage`).
3. *Skill names are capitalised in mid-sentence* ("Working knowledge of Math manipulatives"). Cause: the author prompt's
   rule 3 says required strings appear "spelled as given" while the check is case-insensitive. **Left unchanged:** a
   prompt change bumps `AUTHOR_PROMPT_VERSION` and a lower-case rule is untested; the owner can decide whether it is
   worth a cell's cost to try. It is a readability quirk, not a grounding fault.

Because both builder changes alter the stored profile, all five cells no longer matched a fresh build of their facts.
That exposed a gap: nothing checked that a generated cell **is** the rebuild of its facts, so editing the facts after
generation would have left a cell describing a profession the facts no longer say. `check_suite` now rebuilds every
generated cell and compares (`TestACellIsTheFunctionOfItsFacts`). The five cells were discarded and are regenerated:
**$0.3589 of the $3 was spent on cells that did not survive**, the price of learning this from five cells.

**Stage 2b, observed (the same five cells, regenerated with the corrected builder):** `web-backend-lead` $0.0862,
`teacher-mid` $0.0645, `electrician-entry` $0.0535, `accounting-senior` $0.0854, `ux-design-senior` $0.0706; $0.3603 for
the run, $0.7191 logged in all; every request first-attempt, `end_turn`, 16 to 31 s. Measured on the model's own text:
every listed skill now appears in the web-backend, teacher, accounting and design cells; no skill appears more than
twice outside the accounting cell, whose worst is 3 where it was 6 (its skill and a theme share the phrase "month-end
close"); `Nearpod` fell from 3 uses to 1 and `API versioning` from 4 to at most 2; and the apprentice now "reports
findings to the journeyman before any repair is made". Output tokens per request varied by up to 27 percent between the
two runs of one cell (2,665 to 3,094 for the design cell), so the same prompt does not cost the same twice.

**The checkpoint projection, from ten requests.** Mean cost per cell by tier: entry $0.0491 (2 cells), mid $0.0650 (2),
senior $0.0791 (4), lead $0.0872 (2). One profession is $0.280, so the 96 cells are about **$6.73**; the 91 still to
write (23 entry, 23 mid, 22 senior, 23 lead; the three pilots are among them) are about **$6.37**, which with the
$0.7191 already logged is about $7.09 in all. Stated limits: ten requests are not a distribution; a rewrite request
costs a further request; and a different profession may think more or less.

**The bulk run, and two faults it found (2026-10-28, sweeps 1 to 3).** Sweep 1 (24 cells, tiers rotated across the
professions) cost $1.7812 and sweep 2 (23 cells) $1.7120: 49 cells, 48 first-attempt, 1 after a single rewrite, none
rejected, per-tier means about 6 percent above the earlier projection under prompt v2 (entry $0.052, mid $0.069,
senior $0.083, lead $0.093). Sweep 3 wrote 14 of its 23 cells and stopped on its own rules:

1. *A fenced reply.* `admin-assistant-lead`: the model wrapped otherwise-valid JSON in a markdown code fence and the
   strict parser called it "not JSON" after the cell had been paid for ($0.09; the 4,604-character reply was kept under
   `logs/golden_rejects/`). One case in 77 requests. Fixed in the parser, not the prompt: `_unfence` accepts a reply that
   is wrapped, and only wrapped, in one fence; prose around a fence and an unclosed fence are still refused
   (`TestAuthorCell`). `AUTHOR_PROMPT_VERSION` is unchanged because the prompt is.
2. *A request across a sleep.* `sales-senior`: `APIConnectionError` after **622.9 s** on a client with a 180 s
   timeout. The Windows system log shows the laptop entered Modern Standby at 3:03:28 PM, the second the request began,
   and left it at 3:13:48 PM, three seconds before the error. The client's timeout counts awake time, so it never
   fired, and the connection was dead on wake. **Whether the server billed that request is unknown**: a client-side
   failure is logged with no tokens, so it is in neither the run's count nor the log's. Mitigation:
   `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` is held for the length of a paid run and released
   afterwards, on every exit path (`TestStagedRun`); the real call was confirmed to take effect on this machine.
   **Unverified:** that it prevents Modern Standby here, and a closed lid can still sleep a machine set to.

**The end state, and a third defect found by sampling the final cells.** After sweeps 3 and 4: 96 cells and 96 fixtures,
24 at each tier, all under prompt `golden-author-2`; 94 accepted on the first attempt and 2 after one rewrite; 36 pairs
(24 advance, 12 change) derived from the finished cells, 132 fixtures, 6 MB. 110 author requests logged $7.8797, of which the
96 kept cells cost $7.0812 and $0.7985 went on cells that were discarded or lost (the two discarded rounds, one reply lost to
a code fence). Hand-reading three more final cells (a lead electrician, a mid security analyst, an entry caseworker; the second
and third are public-sector postings) found the prose grounded and plausible and found one fault no check can see: the foreman
posting requires the entry-level Apprentice Registration Card, because the builder asks the posting to require the *lowest*-tier
certification a candidate holds (`held_certs[:1]` at the `asked_certs` line of `build_profile`). Counted from the profiles, **37
of the 56 cells that hold certifications are affected**. It is a realism fault, not a grounding one. It is not fixed here: the
fix changes those cells' profiles and so means regenerating them (about $2.8) with $2.12 left of the owner's $10.00. It is filed
as item 194, scope 1, for the owner to decide. Only four of the 96 final cells have been hand-read; item 194, scope 2, reads a
stratified sample before the freeze.

---

## Deferred

The **`evals/fixtures/synthetic/` retirement** and every consumer in the list below move to the follow-on item, because a
retirement retargets consumers onto a *complete, calibrated* set, and a calibration run on a set that still changes would
have to be paid for again. The list was derived by an Explore subagent at `77decd4` and **has not been re-derived by me**;
the follow-on item re-derives it before its first edit.

- Readers of the directory: `evals/runner.py` `_select_fixtures` and `--fixture` lookup (about `:882-895`) and the
  `run_suite` default (`:1575`, `:2580-2581`); `evals/corpus_drafting_probe.py:79-80` (the only reader of
  `synthetic/corpus/`); `evals/golden_set.py` `profile_from_persona` and the converter tests; `scripts/smoke_phase_b1.py:34`.
- Tests that read it or count it: `test_eval_runner.py`, `test_eval_spend.py` (including `skipped == ["corpus"]`),
  `test_eval_run_identity.py`, `test_eval_catalog.py:65,248-273`, `test_hardening.py:147-170,246-251,300`,
  `test_eval_golden_runner.py:68,94,167`, `test_golden_set.py` (converter), `test_zero_pii_clone.py:102`,
  `test_data_root.py:277`, `tests/ux/regression/test_20261003_run_lock_ownership.py:68`.
- CI and config: `.github/workflows/ci.yml:97-113` (label-gated `eval-smoke`, `--suite synthetic --subset smoke`),
  `evals/catalog/{clarify,generate,generate_cover_letter,iterate_clarify}.toml` (`cases = ["synthetic/..."]`),
  `evals/anchors/anchor-v1/manifest.json`, `evals/results/baseline_v1.json` (the regression keys are bare fixture names),
  `promptfooconfig.yaml`, the dashboard selects (`dashboard/templates/dashboard.html:424-425,611-612`), and the
  suite allowlists in `blueprints/diagnostics.py:1061-1062,1231-1232`.
- A hash-locked prompt line: `analyzer.py:1319` inside `AVATAR_SYSTEM_PROMPT` names `--suite synthetic`; editing it trips
  the prompt lock.
- The anchor copies of the three personas are byte-identical to `synthetic/`, so retiring the directory does not remove
  the anchor suite.
- **The calibration run, tier sizes and the freeze** (the git-history guard) — the same follow-on item.
- **`--suite all` and the console allowlists** — step 8, as in the previous dossiers.
- **Per-cell manifest re-stamping is kept** (about 2 to 4 s per cell against a call of tens of seconds, measured in
  `eval-golden-breadth.md`): a crash then leaves the manifest consistent. The cost is stated, not hidden.

---

## Verification

How a missed consumer would surface:
- **Anything importing `golden_set` / `golden_author`:** `python -c "import evals.runner"` after every edit, then
  `tests/test_golden_set.py`, `test_golden_author.py`, `test_golden_reachability.py`, `test_eval_golden_runner.py`,
  `test_eval_catalog.py`, `test_data_root.py`, `test_call_kind_telemetry.py`.
- **A committed byte drifting or a pair out of step:** `python -m evals.golden_set check` at every commit that touches
  the suite (a draft suite with fewer cells must pass).
- **The prompt changing by accident:** the existing prompt-hash and bytes tests, plus the new request-kwargs assertion.
- **The render hole:** a test whose stub reply has a comma-split target bullet; committed failing first, then green.
- **The cap missing a failed attempt:** a test with a stub that rejects twice, run twice; the second run must see the first's
  spend in the log.
- **The whole set at full size before any spend:** a free dress rehearsal (plan step 5) builds all 96 profiles from the real
  facts, fills them with stub prose and runs `check_suite`, the reachability check and `--estimate` in both modes.

Run at close-out: the enumeration greps above, once more, against the final tree, and `python -m scripts.gate`.

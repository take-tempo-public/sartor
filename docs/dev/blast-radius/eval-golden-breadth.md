# Blast radius — eval-golden-breadth

> **Branch:** `feat/eval-golden-breadth` (golden-set breadth, eval redesign step 3b-i)
> **Status:** enumeration complete at `99d2566` (the ledger commit on top of `acf6d6f`), written before the first code
> edit. Step 3b was split on 2026-10-27: this branch changes the **format** so the set can span many fields (per-family
> ladders, a setting axis, certifications, mismatched pairs). It makes no paid call. The facts for the new professions and
> the paid generation are 3b-ii (item 191).

---

## Surface

Changed (all under `evals/` and its tests; none is on the `scripts/enforcement/blast_radius.py` registry, which has no
golden path, so no hook fires and this dossier is the prose-binding C-10 step):

- `evals/golden_set.py` — `LEVELS` (kept, still the four normalized tiers), `SECTION_KINDS` (+ `certifications`),
  `build_profile` (ladder source, tenure, employers, JD header and register, certifications, education),
  `_EMPLOYERS` / `_SCHOOLS` (become per-setting / per-profession), `render_resume`, `render_seed` (certifications),
  `_parse_section`, `check_suite` (manifest schema 2, pairs), `check_cell` (pair fixtures are not orphans), a new pair
  deriver.
- `evals/golden_author.py` — reads the family ladder instead of `manifest["levels"]`; `build_user_prompt` carries the
  setting.
- `evals/golden/golden-v1/manifest.json` — `schema` 2: `families{}`, `professions[p].family`, `pairs[]`.
- Tests: `tests/test_golden_set.py` (the `FACTS` / `_ladder` / `_manifest` helpers), `tests/test_golden_author.py`,
  `tests/test_golden_reachability.py`, `tests/test_eval_golden_runner.py`.
- Docs: `evals/README.md`, `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` (6.4, 6.5, section 8), work items.

Not touched: `evals/runner.py`, `evals/eval_catalog.py`, `evals/fixtures/synthetic/`, `blueprints/diagnostics.py`,
`parser.py`, `db/models.py`, `seed_import.py`, any pin, any prompt or `PROMPT_VERSION`, `docs/governance/`.

---

## Enumeration

Two passes, both with the Grep tool on 2026-10-27 at `acf6d6f`/`99d2566`. The first was done by an Explore subagent from the
code (the previous dossier was deliberately not used); the second is my own count-mode spot check of the names below.
Counts are from the tool output.

```
Grep "\bLEVELS\b"   (*.py,md,json,toml, whole tree, count)                                   -> 13 hits, 4 files
        golden_set.py 6, golden_author.py 1, tests/test_golden_set.py 5, docs/wiki/pages/code-module-map.md 1
Grep "_EMPLOYERS|_SCHOOLS|GENERIC_TRAPS|Remote \(US\)|SECTION_KINDS|\["levels"\]|\.levels|manifest\[.levels.\]|ladder\["
                                                                                              -> 25 hits, 7 files
        golden_set.py 19, golden_author.py 1, cells/sre-ops-mid/prose.json 1 (persona text), code-module-map.md 1,
        tests/test_golden_set.py 1, tests/test_build_context_db.py 1 and tests/test_hardening.py 1 (unrelated JD strings)
Grep "golden_set|golden_author|golden-v1|evals/golden"  (*.py,toml,yml,yaml,json,cfg, count) -> 67 hits, 17 files
        runner.py 8, golden_author.py 10, golden_set.py 7, eval_catalog.py 3, wiki_relevance.py 2,
        tests: golden_set 5, golden_reachability 6, eval_golden_runner 8, golden_author 4, eval_catalog 4, data_root 2,
        call_kind_telemetry 2, model_overrides 1; analyzer.py 1 and hardening.py 1 (comments only), dataset_author.toml 2
```

Negative results (also findings):
- **0** consumers of `manifest.json` in `evals/runner.py`, `evals/eval_catalog.py` or `dashboard/`: the runner takes every
  subdirectory of `fixtures/` and never reads the manifest.
- **0** hits for `golden` in `.github/`, `pyproject.toml` and `.githooks/`: CI does not run `python -m evals.golden_set check`;
  it is covered only through `tests/test_golden_set.py::TestCommittedSuite` (inside the gate's pytest run).
- **0** wiki `path:line` cites to `golden_set.py` or `golden_author.py`. The wiki does cite the **symbols** `LEVELS`,
  `SECTION_KINDS`, `SCHEMA`, `SUITE` and `render_fixtures` (`docs/wiki/pages/code-module-map.md:133`), so those names stay.
- `scripts/enforcement/blast_radius.py` has no golden path (`GATED`, `GATED_PREFIXES`, `ACKNOWLEDGED_NOT_GATED`).
- `golden_set.py` has one non-test importer (`golden_author.py`), and `evals/runner.py:88` imports `golden_author`: **an
  import error in either module breaks the whole eval runner**, so every edit is followed by an import of `evals.runner`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/golden_set.py:48` `LEVELS` and its uses `:236-237` (validate), `:691-693` (check_suite), `:1102` (title index) | no change to the name or values | the four tiers stay the pooled axis; the wiki cites the symbol. A family's own label (apprentice, journeyman) is a field of its ladder, not a new tier. |
| 2 | `golden_set.py:691-706` `check_suite` reads `manifest["levels"]` and `["professions"]` | update | manifest `schema` 2: `families[f]["levels"][tier]`, `professions[p]["family"]`. A schema-1 manifest is refused with a message, not migrated silently. |
| 3 | `golden_author.py:345` `gs.build_profile(facts, manifest["levels"][level], level)` and `:333` `choices=gs.LEVELS` | update / no change | looks the ladder up through the profession's family; `choices` keeps the four tiers. |
| 4 | `golden_set.py:1070-1292` `build_profile`, the tenure line `:1109` | update | tenure drawn inside `ladder["years"]` (a defect: the ladder's `years` is never read). A test that fails first pins it. |
| 5 | `golden_set.py:1165,1266,1267` `ladder["scope"]` pasted into summary and iteration prompts | update | the scope now comes from the family ladder, so a trades or office cell no longer says "technical direction for a product area". |
| 6 | `golden_set.py:85` `_EMPLOYERS` (use `:1099`), `:91` `_SCHOOLS` (use `:1176`), `:99` `GENERIC_TRAPS` (use `:1231`) | update / update / no change | employers per setting; schools per profession with a default; the generic traps stay and gain per-profession absent-certification traps. |
| 7 | `golden_set.py:1200-1226` JD slots and the `— Remote (US)` header | update | the header becomes `{company} — {location}` from the facts; slot ids (`jd.<slug>.about/duties/needs`) are unchanged so `check_cell` and `render_jd` (`:387-392`) keep working; headings and register vary by setting. |
| 8 | `golden_set.py:50` `SECTION_KINDS` and every kind-specific branch: `section_slots :172-184`, `render_resume :358-383` (its `else:` renders any unknown kind as skills), `render_seed :509-539` (`:569` hardcodes `certifications: []`), `_parse_section :819-874`, `profile_from_persona :914-967`, `golden_author.py:116-117` | update | add `certifications`; give `render_resume` an explicit branch and make the unknown-kind path raise; `render_seed` emits the seed's existing `certifications` list; the parser learns the heading `Certifications` (the product parser recognises that exact heading, `parser.py:127-135`); `profile_from_persona` needs no change (the pilots have none). |
| 9 | `golden_set.py:621-657` `check_cell` and `:750-752` the orphan test | update | a fixture named `pair--<id>` is recognised through the manifest's `pairs[]` and re-derived byte for byte; any other unmatched fixture stays an orphan. |
| 10 | `golden_set.py:658-666` `tracked_files` hashes only `facts`, `cells`, `fixtures` | no change | pairs live under `fixtures/`, so they are hashed; a new top-level directory would have been unhashed and unflagged, which is why none is added. |
| 11 | `golden_set.py:1332-1381` `PREDICATES`, `REACHABILITY`, `failing_predicates` | no change | they read the résumé side of the profile only. Pairs reuse a cell's profile, so the reachability keys are unchanged; a test ties them to the pair fixtures. |
| 12 | `golden/golden-v1/manifest.json` (6 cell files, 12 fixture files hashed; `pilot_waivers`; 4 ladders) | update | restructured to schema 2 and re-stamped by `python -m evals.golden_set manifest`. The three pilot cells are `converted` with `cell_seed` 0, so **no cell byte changes**; the manifest hashes of cells and fixtures stay equal. New pair fixtures are added. |
| 13 | `evals/runner.py:128,248-298,879-911,914-923,1739,1848,2580` (`GOLDEN_DIR`, `_load_fixture`, `_select_fixtures`, `_suite_of`, `case_id`, suite choices) | no change | `_select_fixtures` takes every subdirectory with no name parsing, `_suite_of` uses the parent directory, `case_id` is `golden-v1/<dir name>`. A pair directory needs `jd.txt`, `expected.json`, and `resume.md` unless in seed mode, and `seed.json` for assemble mode; the pair deriver writes all four. |
| 14 | `evals/eval_catalog.py:339-345` (imports `golden_author` for the pin) and `tests/test_eval_catalog.py:64-67,254-268` (`_SUITE_DIRS`, resolves `base/name` and reads `expected.json`) | no change | the test reads each fixture's `expected.json`; a pair's `expected.json` keeps every key a cell's has. Re-run to confirm. |
| 15 | `blueprints/diagnostics.py:1062,1232` suite allowlists | no change | `golden-v1` stays out of the console until step 8. |
| 16 | `tests/test_golden_set.py:26-97` `FACTS`, `_ladder`, `_manifest`; `:163-167` seed pins; `:182-199,376`; `:211-220`; `:246-252`; `:326-349,429-449`; `:491,495-500`; `:508-551,567-605`; `:643` | update | the helpers move to schema 2 and gain `setting`, `location`, `certifications`; the pinned `cell_seed_for` values do not change (the function takes profession and level only). |
| 17 | `tests/test_golden_author.py:147,401,426,439` | update | the manifest helper and the `ga.main` arguments. |
| 18 | `tests/test_golden_reachability.py:217-222,263-267,284,293-305` | update | `:267` maps a fixture to its cell by `name.split("--")[0]`: a pair must map to its résumé cell and keep the control arm (the old `recommend_summary` gap). |
| 19 | `tests/test_eval_golden_runner.py:30,38,44,129-131,138,192,201,222` | update | hard-coded fixture count 3 and a split on `--`; both move to the new total and a pair-aware helper. |
| 20 | `tests/test_data_root.py:282` `_CODE_ANCHORS["evals/golden_set.py"]` | update, text only | the reason names "(facts, cells, fixtures, manifest)"; no new `Path(__file__)` anchor is added. |
| 21 | `docs/wiki/pages/code-module-map.md:133` and the `eval-harness` page | update | a scoped `/wiki-self-update` on this branch's diff, committed before the PR (`golden_set.py` is wiki-relevant, `scripts/wiki_relevance.py:60`). |
| 22 | `evals/README.md` (golden-set sections), `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` 6.4 / 6.5 / section 8 Q12 | update | document the new axes and counts; 6.5 gets a dated Decision line: **no fetch, no key, C-2 and D-6 untouched**. |
| 23 | work items 191 (rescope to 3b-ii), a new 3b-i item, 183 (left as is) and epic 180 | update | item ids are allocated at commit time. |
| 24 | `evals/fixtures/synthetic/` and its consumers (previous dossier, Consumers 28) | deferred | still 3b-ii's retirement work; this branch leaves the directory byte-identical. |
| 25 | `evals/golden_author.py` live request shape, `AUTHOR_SYSTEM_PROMPT`, `AUTHOR_PROMPT_VERSION` | no change | no live call is made. If `build_user_prompt` gains the setting key, the prompt's text is untouched, so the prompt version does not bump; a test asserts the system prompt bytes are unchanged. |

---

## Deferred

- **The facts files for ~24 professions** (`facts/<profession>.json`; the directory does not exist yet) and the O*NET codes
  and the licence terms for the new professions — 3b-ii (item 191). Not verified here: O*NET coverage of electricians,
  administrative assistants, construction managers, hardware engineers, industrial designers; mobile and UX are expected to
  be `nearest` mappings.
- **How the judge weights a pair** (and whether a pair can fail a gate on callback or only on grounding / no invention) —
  steps 8 and 9. `min_*` scores are judge-visible, not code-enforced (no code applies them), so a pair's `expected.json`
  says in `notes` that the gate is grounding and no invention; the README states the open question.
- **The product parser's heading list** (`parser.py:127-135` recognises `certifications` only; "Licenses" and "Credentials"
  fold into the previous section). A product change; this branch writes the heading `Certifications`.
- **Persona rendering of issuer and date.** Markdown and docx output show the certification's name only
  (`corpus_to_json_resume._collect_certificates`, `generator.py:913-917`): detail the seed carries is dropped on output.
  Not traced into the persona templates. Not a golden-set change.
- **`education.notes`** is never rendered by `corpus_to_json_resume._collect_education`, so an apprenticeship is written into
  `institution` / `degree` / `field`, not `notes`.
- **Freeze enforcement against git history** — 3b-ii, once a frozen version exists to protect.
- **Item 183 stays `open`** and item 182 stays `open`: closing either needs a `verified_by` or an owner-named exception and the
  owner has not asked; both are named in the handoff.
- **A copy of a pair's bytes** (`resume.md`, `jd.txt`, `seed.json`) duplicates a few KB per pair instead of teaching the
  runner a two-directory fixture. Chosen so the runner, the catalog and the console need no change; the cost is stated here.

---

## Verification

How a missed consumer would surface:
- **A renamed or removed symbol the wiki cites:** `scripts/wiki_cites.py` (inside the gate) and the wiki freshness gate.
- **Anything importing `golden_set` / `golden_author`:** `python -c "import evals.runner"` after every edit, then
  `tests/test_golden_set.py`, `test_golden_author.py`, `test_golden_reachability.py`, `test_eval_golden_runner.py`,
  `test_eval_catalog.py`, `test_data_root.py`, `test_call_kind_telemetry.py`.
- **A committed byte drifting:** `python -m evals.golden_set check` and the unchanged manifest hashes of the three pilot cells.
- **A pair out of step with its source cells:** `check_suite` re-derives every pair byte for byte (a mutation check proves it
  fails when a source cell changes).
- **A seed key the importer drops:** the existing test that asserts every rendered seed key is read by `evals/seed_import.py`
  (`tests/test_golden_set.py`) now covers `certifications`.
- **The tenure defect:** a new test builds `senior` and `lead` profiles and asserts total tenure lies inside the ladder's
  `years`; it is committed failing first.

Measured, not estimated: scale and timing are measured in a temp directory at a synthetic 96-cell-plus-pairs size and the
seconds are written here before close-out (the 3a figure was about 0.1 s a fixture in the reachability test).

Run at close-out: the enumeration greps above, once more, against the final tree, and `python -m scripts.gate`.

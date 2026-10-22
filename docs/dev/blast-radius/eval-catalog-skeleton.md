# Blast radius — eval-catalog-skeleton

> **Branch:** `feat/eval-catalog-skeleton` (item 182, eval redesign step 2)
> **Status:** enumeration complete at `d9e268c` (branch tip: the ledger commit on top of `dcbe24d`), written before the
> first code edit. Three corrections found by the greps are recorded under "Findings that changed the plan".

---

## Surface

New:
- `evals/catalog/<call>.toml` x 23, one per member of `tests/test_call_kind_telemetry.py:EXPECTED_CALL_KINDS`.
- `evals/catalog/costs.json`, machine-written integer token means per call kind.
- `evals/eval_catalog.py`, a stdlib-only lazy loader with a `measure` entry point.
- `tests/test_eval_catalog.py`, the gate.

Changed:
- `evals/runner.py`: the `--list`, `--estimate` and `--max-spend` flags; `_call_plan()`; `_suite_of()`; a `max_spend_usd`
  parameter on `run_suite`; the `case_id` value set at `runner.py:1468` becomes `<suite>/<name>`; exit code 4; one new
  trailing defaulted field on `EvalRunResult`.
- `tests/test_eval_run_identity.py:108,162`, `tests/test_data_root.py:_CODE_ANCHORS`.
- Docs: `evals/README.md`, `SECURITY.md:184`, `docs/dev/eval-redesign-design.md`, `CHANGELOG.md`, the wiki pages the
  scoped self-update names, work items 181/182 and `BOARD.md`, the handoff.

No registered gated surface (`scripts/enforcement/blast_radius.py`) is edited, so `require-consumer-enumeration` does not
fire. This dossier is the enumeration the project asks for anyway.

---

## Enumeration

Commands run on `feat/eval-catalog-skeleton` at `d9e268c`. Counts are from the tool output.

```
Grep "case_id"  (whole tree; excluded docs/dev/handoffs, blast-radius, diagnosis, work)   -> 41 hits in 15 files
Grep "run_suite\(|cancel_check|EvalRunResult\("  (*.py)                                    -> first 80 lines read (limit 80)
Grep "_select_fixtures|_load_fixture|EVALS_DIR|FIXTURES_DIR|ANCHOR..." evals/runner.py     -> see Consumers 1-4
Grep "ANCHOR_DIR|FIXTURES_DIR"  (*.py)                                                     -> runner.py + 1 probe + 3 test patches
Grep "EXPECTED_CALL_KINDS"  (whole tree; excluded handoffs, wiki/log.md)                   -> test_call_kind_telemetry.py + 7 doc mentions
Grep "_CODE_ANCHORS|evals/..." tests/test_data_root.py                                     -> :267 registry, :274-277 evals entries, :328-335 both-way check
Grep "exit code|exit_code|--max-spend|--estimate|--list" evals/README.md (-i)              -> :43, :218, :483, :758
```

Negative results (also findings):
- `case_id` has **0** consumers in `dashboard/`, `static/`, `templates/` or `blueprints/` as a *value*: no code compares
  it to a fixture directory name. All comparisons are string equality on whatever the context carries. A grep for
  `split`/`partition` applied to `case_id` over `*.py`, `*.js` and `*.html` found **0** hits.
- `EXPECTED_CALL_KINDS` has exactly **one** code consumer (`test_call_kind_telemetry.py`). The new gate becomes the second.
- `ANCHOR_DIR` has **no** consumer outside `evals/runner.py`.

The `run_suite(` grep hit the 80-line limit. Its callers that matter were all reached before the limit: two in
`blueprints/diagnostics.py`, `runner.main`, and the test files below. **I did not re-run it unlimited**; the plan's
verification re-runs it once at the end, and an uncounted caller would fail on a missing keyword only if it passed the
new parameter, which no caller does.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/runner.py:1468` `trace_context(trace_id, case_id=fixture["name"], ...)` | **update** | The one place `case_id` is set. Becomes `f"{_suite_of(fdir)}/{fixture['name']}"`. |
| 2 | `evals/runner.py:815-841` `_select_fixtures` returns `list[Path]` | **no change** | `_suite_of` derives the label from the returned directory, so the selector's return type stays. |
| 3 | `tests/test_eval_runner.py:1264,1343,1389` patch `runner.FIXTURES_DIR` to a `tmp_path` | **update `_suite_of` design** | The label must be computed from the directory at call time, from its parent chain, never from a captured constant. A tmp fixture under an unrecognised parent must not raise: it falls back to the parent's name. |
| 4 | `evals/runner.py:119` `ANCHOR_DIR`; fixtures at `ANCHOR_DIR/"fixtures"/<name>` | **update** | The anchor suite's parent chain is `anchor-v1/fixtures/<name>`; `_suite_of` treats a parent named `fixtures` as "use the grandparent". |
| 5 | `evals/runner.py:157-164` `_trace_fields`; `:580-605` `_trace_cost`; `:621-623` `_case_cost`; `analyzer.py:751,765,778,958-959` | **no change** | They carry and compare `case_id` as an opaque string. A `/` in it is safe: nothing splits or parses it (grep: no `split("/")` on `case_id`). |
| 6 | `tests/test_eval_run_identity.py:108` `rec["case_id"] == rec["fixture"]` | **update** | The invariant is now `case_id == f"{suite}/{fixture}"`. Written first as a failing test. |
| 7 | `tests/test_eval_run_identity.py:162` the foreign row's `case_id` | **update** | The leak test builds a row for the same case; it must use the new form or it stops modelling a same-case collision. |
| 8 | `tests/test_eval_run_identity.py:125,218`, `test_call_record_identity.py:128-173`, `test_judge_call_provenance.py:218,234` (literal `"fx"` / `case`) | **no change** | They pass their own strings through the carriers; none depends on the form. |
| 9 | `SECURITY.md:184`, `evals/README.md:941`, `docs/dev/eval-redesign-design.md:325` | **update** | Each says `case_id` is the fixture name. |
| 10 | `commands/bench.md:21`, `docs/wiki/pages/llm-call-catalog.md:121`, `deterministic-llm-boundary.md:73` | **no change** | They name the field, not its form. |
| 11 | `docs/wiki/pages/eval-harness.md:25-29,:139` | **check in the wiki pass** | Describes the join "on `trace_id` + `case_id`" and "the fixture's `case_id`". |
| 12 | `CHANGELOG.md:29-30` | **no change** | A dated item-181 entry. |
| 13 | `evals/runner.py:1243` `run_suite(` signature and its callers `blueprints/diagnostics.py:1118,:1306`, `runner.main` at `:2310` | **update (additive)** | New keyword `max_spend_usd=None`. The two blueprint callers pass nothing new and are byte-identical. `main` passes the flag. |
| 14 | Test fakes of `run_suite`: `test_annotation_routes.py:1036,1090,1275,1608,1637`, `test_eval_runner.py:371,398` | **no change** | All take `**kwargs`. |
| 15 | `EvalRunResult(` positional constructions: `runner.py:1372,1378,2145`, `test_annotation_routes.py:1051,1094,1307,1613,1642`, `test_eval_runner.py:373,400` | **no change** | The one new field (`stop_reason`) is appended **last with a default**. |
| 16 | `cancel_check` elsewhere: `evals/bootstrap.py`, `evals/grounding_signals.py`, `blueprints/diagnostics.py:619,880` | **no change** | The spend cap composes inside `run_suite` only. |
| 17 | `tests/test_call_kind_telemetry.py:74-102` `EXPECTED_CALL_KINDS` | **no change** | The new gate imports it; neither file mutates the set. |
| 18 | `tests/test_data_root.py:267-335` `_CODE_ANCHORS` | **update** | `evals/eval_catalog.py` anchors its directory with `Path(__file__)`, so it gets an entry with a reason (the check fails both ways at `:328-335`). |
| 19 | `evals/README.md:43` (exit code `0`/`2`), `:218` "Exit codes", `:758` | **update** | The new exit code 4 and the three flags are documented where exit codes already live. |
| 20 | `.github/workflows/ci.yml:95-113` eval-smoke runs `python evals/runner.py --suite synthetic --subset smoke` | **no change** | No new flag is required, and the default path is byte-identical. Verified by the suite plus a run of the same arguments with the client stubbed. |
| 21 | `tests/test_tree_walk_gate.py` | **no change** | The gate test uses a flat `glob("*.toml")`, never `rglob`. |
| 22 | `tests/test_egress_allowlist.py` | **no change** | `eval_catalog.py` imports no network module. |
| 23 | `pyproject.toml` (`py-modules`, mypy roster, ruff, packaging) | **no change** | `evals` is not packaged; `evals.*` is already in the strict roster; `evals/*` per-file ruff ignores apply to a flat module. A `.toml`/`.json` file under `evals/catalog/` needs no package-data. |
| 24 | `scripts/wiki_relevance.py` | **no change** | `evals/**` is wiki-relevant by default (no override needed); pages that cite `runner.py` symbols are handled in the wiki pass. |
| 25 | `tests/test_gitattributes_coverage.py` | **no change** | `.gitattributes:11` (`*.json text eol=lf`) and `:14` (`*.toml text eol=lf`) already cover both new file types. |

---

## Findings that changed the plan

1. **The loader cannot import `runner`.** The plan said the loader would reuse `runner.EVALS_DIR`. `runner` imports
   `analyzer` and `anthropic` at module level, so the "lazy, stdlib-only" loader would pull in the whole product. The
   loader owns its directory (`Path(__file__)`), and row 18 registers that.
2. **`_suite_of` must tolerate monkeypatched `FIXTURES_DIR`** (row 3).
3. **`EvalRunResult` is built positionally in 9 places** (row 15), so a new field goes last, with a default.

---

## Deferred

- **The `case_id` form for the dashboard.** No dashboard code reads `case_id` today (negative result above). Step 8 will
  decide how it displays a slash-bearing id. Nothing to do here.
- **Catalog entries for `--eval`, `--group`, `--affected-by`.** Step 3. The catalog already carries `groups` and `prompt`,
  which those flags will read.
- **`catalog_entry_hash` on records** (design 5.8). It needs the catalog first; step 8 reads it.
- **Single-call eval of `generate` / `generate_cover_letter`.** No build step names one (design section 9). The entries
  say "covered" for flow-level coverage only. Surfaced to the owner in the handoff; not filed.
- **A `--max-spend` on the CI eval-smoke job.** The label-gated job is untouched.
- **The `run_suite(` grep was limited to 80 lines** (see Enumeration). Re-run unlimited at the end; recorded as a check,
  not a skip.

---

## Verification

A missed consumer would surface as one of:
- `tests/test_eval_run_identity.py` (rows 6-7), which fails first for the `case_id` form;
- `tests/test_data_root.py` (row 18), which fails both ways on an unregistered or stale `evals/` anchor;
- the new `tests/test_eval_catalog.py` gate, which fails on a missing or stale entry, a mismatched pin or prompt, a float
  in `costs.json`, or a loader that parses more than one file for `load()`;
- `tests/test_gitattributes_coverage.py`, `tests/test_packaging.py`, `tests/test_wiki_cites.py` and
  `tests/test_wiki_relevance_classification.py` for the registration surfaces the previous branch missed.

I will `git add` every new file before the gate runs. The previous handoff's recurrence 6 shows `git ls-files`-based checks
cannot see untracked files.

**Stated limits:** the estimate is a floor; the runtime cap can overshoot by one phase; the entry-point-to-kinds table in
`_call_plan()` is declared, and a stub-driven test ties it to the fired calls in both modes and subsets but cannot cover a
path it does not drive.

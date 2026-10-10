# Diagnosis — assertions that pass on the regression they name (items 115, 116, 122) and the shared-toast wait class (item 159)

> **Status:** each item's gap is proven by a mutation that survives the HEAD test. After this
> branch's change, each mutation must fail the strengthened test. Results are recorded below
> as they are observed.
> **Branch:** `test/assertion-strength` (a test branch, not a `fix/*`; this dossier is the
> evidence home the items' `verified_by` cite).

---

## Symptom

- **Item 115:** the UX-8 test never measures `.err-link`'s color, so the F3 cascade fix
  (`dashboard/templates/dashboard.html:54-55`) was verified by reading rules.
- **Item 116:** the "Run this fixture" help (i) exists only after a Collate; no test clicks it.
- **Item 122:** three assertions survive plausible mutants (refuter R2-4 / R2-7).
- **Item 159:** any UX test may synchronize on `#_corpusToast`, the one element every
  `_toast()` call writes; item 155 was one. No class-wide guard existed.

---

## Observed

### A1. Item 122, before: all three mutants survive the HEAD tests

Session `c195419d`, 2026-10-10, local Windows 11, Python 3.13, tests unmodified at `ed22718`.
Command (plugin source: `## Falsification` below):

```
PYTHONPATH=<scratchpad>/mutplug MUT_LOG=<scratchpad>/mutplug/before122.log \
  python -m pytest tests/test_dashboard_copy.py tests/test_annotation_routes.py \
  -k "unglossed or registry_titles or score_grounding_help" -p mut_plugin \
  --mut raw-names,title-hole,error-claim -p no:rerunfailures -o addopts="" -q -rA --tb=line -s
```

```
PASSED tests/test_dashboard_copy.py::TestEveryTileHasLayLineAndBubble::test_help_icon_labels_match_registry_titles[none]
PASSED tests/test_dashboard_copy.py::TestEveryTileHasLayLineAndBubble::test_help_icon_labels_match_registry_titles[title-hole]
PASSED tests/test_dashboard_copy.py::TestCopyContent::test_quality_tiles_have_no_unglossed_raw_names[none]
PASSED tests/test_dashboard_copy.py::TestCopyContent::test_quality_tiles_have_no_unglossed_raw_names[raw-names]
PASSED tests/test_annotation_routes.py::TestScoreGrounding::test_score_grounding_help_matches_server_behaviour[none]
PASSED tests/test_annotation_routes.py::TestScoreGrounding::test_score_grounding_help_matches_server_behaviour[error-claim]
6 passed, 82 deselected in 53.68s
```

The plugin's log confirms each mutation applied (a mutation whose target text is absent
raises `MutationNotApplied` instead of passing):

```
applied title-hole -> ...test_help_icon_labels_match_registry_titles[title-hole]
applied raw-names -> ...test_quality_tiles_have_no_unglossed_raw_names[raw-names]
applied error-claim -> ...test_score_grounding_help_matches_server_behaviour[error-claim]
```

- `raw-names` injects the refuter's mutant, `fabricated_specifics_rate from llm_calls.jsonl
  cost_usd`, into the failure-modes tile's lay line.
- `title-hole` drops one registry entry's own `title:` and relabels its bubble with the NEXT
  entry's title; the unbounded search agrees with the wrong title.
- `error-claim` rewrites the Score-grounding help to "a missing one means it scores nothing,
  with no error shown"; `"error" in body` still holds.

### A2. Items 115 and 116, before: all four mutants survive the HEAD UX tests

Same session, tests unmodified at `ed22718`, 0.74 GB free at the start:

```
PYTHONPATH=<scratchpad>/mutplug MUT_LOG=<scratchpad>/mutplug/before_ux.log python -m pytest \
  "tests/ux/regression/test_20260924_run_detail_modal.py::test_error_count_button_lists_that_call_kinds_errors_only" \
  "tests/ux/flows/test_annotation_tab.py::test_annotation_tab_save_and_collate" -p mut_plugin \
  --mut css-no-fail-rule,css-no-fail-hover,no-dash-help-opener,wrong-help-key \
  -p no:rerunfailures -o addopts="" -q -rA --tb=line
```

```
PASSED ...test_error_count_button_lists_that_call_kinds_errors_only[none]
PASSED ...test_error_count_button_lists_that_call_kinds_errors_only[css-no-fail-rule]
PASSED ...test_error_count_button_lists_that_call_kinds_errors_only[css-no-fail-hover]
PASSED ...test_annotation_tab_save_and_collate[none]
PASSED ...test_annotation_tab_save_and_collate[no-dash-help-opener]
PASSED ...test_annotation_tab_save_and_collate[wrong-help-key]
6 passed in 115.28s (0:01:55)
```

All four logged `applied`. `css-no-fail-rule` deletes `dashboard.html:54` (the F3 fix) from
the served page and `css-no-fail-hover` deletes `:55`; `no-dash-help-opener` deletes
`window.sartorDashHelp = { open: openDashHelp };` and `wrong-help-key` makes the dynamic
bubble open `dashCollate` instead of `dashCollateRun`. Nothing in the HEAD tests notices.

### A0. Item 122.1, probe: what the Quality tiles render today

A read-only render of the populated console (the `populated_page` fixture's data), run from
stdin this session. The only snake_case or `*.json(l)` token in any Quality tile is the rule
id from the fixture's `failed_rules`, and `_Node.all_text()` glues it to its neighbours:

```
[failuremodes] tokens=['modeinvented_metricnamed']
    text='top failure modeinvented_metricnamed in 1 graded result(s)The rule the grader most often said was broken ...'
```

So a token pattern has to run on text joined with separators, or it both hides and invents
matches.

---

## Falsified

_(Nothing yet.)_

---

## Inferred

_(Nothing yet.)_

---

## Falsification

**The instrument:** a scratchpad pytest plugin (`mut_plugin.py`, below) that parametrizes each
targeted test over a `none` control arm plus the requested mutations, and applies the
mutation just before the test body runs. No repo file is edited. Mechanisms:

- UX: `page.route` on the `/_dashboard/` document rewrites the served HTML.
- `populated_page`: the fixture value is swapped in `item.funcargs`.
- `ann_app`: an after-request rewrite on the test's own Flask app.
- The item 159 gate: a module-global swap.

**Outcome rule:** a strengthened assertion is accepted only if its mutation passes the HEAD
test (the gap is real) and fails the new test (the gap is closed), and the `none` arm passes
in the same run.

_(The plugin's verbatim source is appended here once final.)_

---

## The fix

_(Recorded per item as it lands.)_

---

## Acceptance bar

Every row: mutation applied (logged), HEAD test passes it, new test fails it with the
assertion that names the regression, `none` arm passes. Run with `-p no:rerunfailures`.

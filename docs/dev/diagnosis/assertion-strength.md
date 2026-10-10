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

### A3. Item 122, after: the strengthened tests kill all three mutants

Same session, same command as A1 against this branch's `tests/test_dashboard_copy.py` and
`tests/test_annotation_routes.py`:

```
PASSED ...test_help_icon_labels_match_registry_titles[none]
PASSED ...test_quality_tiles_have_no_unglossed_raw_names[none]
PASSED ...test_score_grounding_help_matches_server_behaviour[none]
FAILED ...test_help_icon_labels_match_registry_titles[title-hole]
FAILED ...test_quality_tiles_have_no_unglossed_raw_names[raw-names]
FAILED ...test_score_grounding_help_matches_server_behaviour[error-claim]
3 failed, 3 passed, 82 deselected in 16.17s
```

All three logged `applied`. Each failure is the assertion that names its regression:

```
[mut] title-hole: dropped dashPipeline's title; its bubble now names dashQuality's title
tests\test_dashboard_copy.py:316: AssertionError: _DASH_HELP['dashPipeline'] has no title of its own
AssertionError: ('failuremodes', ['cost_usd', 'fabricated_specifics_rate', 'llm_calls', 'llm_calls.jsonl'])
tests\test_annotation_routes.py:895: assert 'a missing one stops it with an error' in "Score grounding — run the offline scorers here…
```

### A4. Items 115 and 116, after: the new assertions kill all four UX mutants

Same session, 1.08 GB free at the start, against this branch's new
`test_failing_error_count_keeps_danger_color_and_hover_affordance` and the extended
`test_annotation_tab_save_and_collate`, mutations as in A2:

```
PASSED ...test_failing_error_count_keeps_danger_color_and_hover_affordance[none]
PASSED ...test_annotation_tab_save_and_collate[none]
FAILED ...test_failing_error_count_keeps_danger_color_and_hover_affordance[css-no-fail-rule]
FAILED ...test_failing_error_count_keeps_danger_color_and_hover_affordance[css-no-fail-hover]
FAILED ...test_annotation_tab_save_and_collate[no-dash-help-opener]
FAILED ...test_annotation_tab_save_and_collate[wrong-help-key]
4 failed, 2 passed in 65.50s (0:01:05)
```

All four logged `applied`. The failures, with the measured values from a `--tb=short` re-run
of the two CSS mutants:

```
css-no-fail-rule:    test_20260924_run_detail_modal.py:215  expected 'rgb(248, 113, 113)'  Actual value: rgb(96, 165, 250)
css-no-fail-hover:   test_20260924_run_detail_modal.py:217  expected 'rgb(232, 167, 84)'   Actual value: rgb(248, 113, 113)
no-dash-help-opener: Page.wait_for_selector: Timeout 15000ms exceeded.   (the help modal never opens)
wrong-help-key:      test_20260925_dashboard_copy_discovery.py:106: assert 'Collate — tu...o a test case' == 'Run this fix...ou just built'
```

The measured colors are the tokens in `static/style.css`: `--danger` `#f87171` = rgb(248, 113,
113), `--info` `#60a5fa` = rgb(96, 165, 250), `--brand` `#e8a754` = rgb(232, 167, 84). So
without `:54` the failing count renders in the info color (F3's original defect), and without
`:55` hovering it shows danger instead of the brand hover color, both by measurement.

### A5. Item 159: the gate fails closed on every way the allowlist can drift, and on item 155 itself

Same session, against this branch's `tests/test_ux_toast_wait_gate.py`:

```
PYTHONPATH=<scratchpad>/mutplug MUT_LOG=<scratchpad>/mutplug/g159.log python -m pytest \
  tests/test_ux_toast_wait_gate.py -p mut_plugin \
  --mut guard-drop-allow,guard-stale-allow,guard-count,guard-new-site \
  -p no:rerunfailures -o addopts="" -q -rA --tb=line
```

```
PASSED tests/test_ux_toast_wait_gate.py::test_scanner_finds_every_reference_shape_and_skips_prose
PASSED tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist[none]
FAILED ...test_toast_sites_equal_the_allowlist[guard-drop-allow]   :272 UX code references the shared toast #_corpusToast: {(...frozen_gate.py, 'test_step5_rail_is_locked_until_compose_freezes_the_composition'): 1} ...
FAILED ...test_toast_sites_equal_the_allowlist[guard-stale-allow]  :290 Allowlist rot: no longer reference the toast: [('tests/ux/no_such_file.py', 'test_gone')]
FAILED ...test_toast_sites_equal_the_allowlist[guard-count]        :285 ... {'found': 1, 'allowed': 2} ...
FAILED ...test_toast_sites_equal_the_allowlist[guard-new-site]     :272 UX code references the shared toast #_corpusToast: {('../../Users/iam/AppData/Local/Temp/mut159-…/test_new_toast_wait.py', 'test_saves'): 1} ...
4 failed, 2 passed in 8.86s
```

All four logged `applied`. `guard-new-site` adds a file outside the repo holding
`expect(page.locator("#_corpusToast")).to_have_text("Saved")` to the scan.

**Against item 155's own history** (the gate's `_scan` run on the file's past versions, via
`git show`):

```
3cfb98d (as it ran in CI):  expect(page.locator("#_corpusToast")).to_have_text("Company saved")
  unallowlisted: {(...test_20260611_prior_app_resume_robustness.py, 'test_card_company_editable_and_persists'): 1}
a4bef7d (the C-7 instrument commit):
  unallowlisted: {(...test_20260611_prior_app_resume_robustness.py, '_company_round_trip'): 2}
```

So the gate would have failed the commit that introduced item 155's wait.

**Cost:** `test_toast_sites_equal_the_allowlist` took 1.19 s (`--durations`), two reads of the
410 `.py` files. One warm read measured ~0.5 s; the first, cold read of the tree this session
took 9.3 s.

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

Verbatim source (`<scratchpad>/mutplug/mut_plugin.py`, as run for A1-A5):

```python
"""Mutation plugin for `test/assertion-strength` (items 115, 116, 122, 159).

Proves each strengthened assertion fails on the regression it names, without editing a
repo file. Every selected test that a requested mutation targets is parametrized over an
indirect `_mut` fixture, always including `none` (the control arm). Just before the test
body runs, the chosen mutation is applied. A mutation whose target text is absent raises
`MutationNotApplied`, so a mutation that did not apply can never be reported as "survived".

Run (from the repo root):
    PYTHONPATH=<this dir> python -m pytest <nodes> -p mut_plugin --mut a,b \
        -p no:rerunfailures -o addopts="" -q -rA --tb=line

Mechanisms:
- UX (`html`): `page.route` on the `/_dashboard/` document rewrites the served HTML.
- `funcarg`: swaps the value of a fixture argument (`populated_page`) before the body runs.
- `flask`: an after-request rewrite on the test's own `ann_app.app` for `/_dashboard/`.
- `module`: swaps a global on the test module (the item 159 gate).
"""

from __future__ import annotations

import html as html_mod
import os
import re
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest


class MutationNotApplied(AssertionError):
    """The mutation's target text was not found: the run proves nothing."""


def _replace_once(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise MutationNotApplied(f"{name}: target not found: {old[:90]!r}")
    return text.replace(old, new, 1)


# --------------------------------------------------------------------------- html (UX)
_HTML: dict[str, list[tuple[str, str]]] = {
    # Item 115: the F3 fix, and its hover re-declaration (dashboard.html:54-55).
    "css-no-fail-rule": [(".cb-dash td.fail button.err-link { color: var(--danger); }", "")],
    "css-no-fail-hover": [
        (
            ".cb-dash td.fail button.err-link:hover { border-color: var(--brand-edge);"
            " color: var(--brand); }",
            "",
        )
    ],
    # Item 116: the dynamic bubble's opener, and the key it opens.
    "no-dash-help-opener": [("window.sartorDashHelp = { open: openDashHelp };", "")],
    "wrong-help-key": [
        (
            "window.sartorDashHelp.open('dashCollateRun', runHelp)",
            "window.sartorDashHelp.open('dashCollate', runHelp)",
        )
    ],
}


# --------------------------------------------------------------------------- funcarg
def _inject_raw_names(page: str) -> str:
    """122.1: the refuter's surviving mutant, in a Quality tile's lay line."""
    return _replace_once(
        page,
        "The rule the grader most often said was broken",
        "fabricated_specifics_rate from llm_calls.jsonl cost_usd. "
        "The rule the grader most often said was broken",
        "raw-names",
    )


_KEY_RE = re.compile(r"^    (\w+): \{$", re.MULTILINE)
_TITLE_LINE = r"      title: '((?:[^'\\]|\\.)*)',\n"


def _title_hole(page: str) -> str:
    """122.2: entry K loses its own title; K's bubble names entry K+1's title instead.

    The old unbounded search then finds K+1's title from K's start and agrees with the
    rewritten label, so it passes; a search bounded to K's own block finds no title.
    """
    start = page.index("var _DASH_HELP = {")
    end = page.index("\n  };", start)
    keys = _KEY_RE.findall(page[start:end])
    for k, nxt in zip(keys, keys[1:]):
        if f'data-help="{k}"' not in page:
            continue  # only a key with a static bubble is checked by the test
        k_hdr = re.search(rf"    {k}: \{{\n{_TITLE_LINE}", page)
        n_hdr = re.search(rf"    {nxt}: \{{\n{_TITLE_LINE}", page)
        if not (k_hdr and n_hdr):
            continue
        page = page[: k_hdr.start()] + f"    {k}: {{\n" + page[k_hdr.end() :]
        label = html_mod.escape("Help: " + n_hdr.group(1), quote=True)

        def _relabel(m: re.Match[str]) -> str:
            return re.sub(r'aria-label="[^"]*"', f'aria-label="{label}"', m.group(0))

        page, n = re.subn(rf'<[^>]*data-help="{k}"[^>]*>', _relabel, page)
        if not n:
            raise MutationNotApplied(f"title-hole: no bubble tag for {k}")
        print(f"[mut] title-hole: dropped {k}'s title; its bubble now names {nxt}'s title")
        return page
    raise MutationNotApplied("title-hole: no eligible registry key")


_FUNCARG: dict[str, tuple[str, Callable[[str], str]]] = {
    "raw-names": ("populated_page", _inject_raw_names),
    "title-hole": ("populated_page", _title_hole),
}

# --------------------------------------------------------------------------- flask
_FLASK: dict[str, list[tuple[str, str]]] = {
    # 122.3: the help stops claiming a missing prerequisite is an error, yet keeps the word.
    "error-claim": [
        (
            "a missing one stops it with an error rather '",
            "a missing one means it scores nothing, with no error shown, rather '",
        )
    ],
}


# --------------------------------------------------------------------------- module (159)
def _mod_drop_allow(mod: Any) -> Callable[[], None]:
    orig = mod.ALLOWED_TOAST_SITES
    key = next(k for k in orig if "frozen_gate" in k[0])
    mod.ALLOWED_TOAST_SITES = {k: v for k, v in orig.items() if k != key}
    return lambda: setattr(mod, "ALLOWED_TOAST_SITES", orig)


def _mod_stale_allow(mod: Any) -> Callable[[], None]:
    orig = mod.ALLOWED_TOAST_SITES
    mod.ALLOWED_TOAST_SITES = {**orig, ("tests/ux/no_such_file.py", "test_gone"): (1, "stale")}
    return lambda: setattr(mod, "ALLOWED_TOAST_SITES", orig)


def _mod_count(mod: Any) -> Callable[[], None]:
    orig = mod.ALLOWED_TOAST_SITES
    mod.ALLOWED_TOAST_SITES = {k: (v[0] + 1, v[1]) for k, v in orig.items()}
    return lambda: setattr(mod, "ALLOWED_TOAST_SITES", orig)


def _mod_new_site(mod: Any) -> Callable[[], None]:
    tmp = Path(tempfile.mkdtemp(prefix="mut159-"))
    extra = tmp / "test_new_toast_wait.py"
    extra.write_text(
        "from playwright.sync_api import expect\n\n\n"
        "def test_saves(page):\n"
        '    page.click("#save")\n'
        '    expect(page.locator("#_corpusToast")).to_have_text("Saved")\n',
        encoding="utf-8",
    )
    orig = mod._iter_py_files

    def _with_extra(root: Path) -> Iterator[Path]:
        yield from orig(root)
        yield extra

    mod._iter_py_files = _with_extra
    return lambda: setattr(mod, "_iter_py_files", orig)


_MODULE: dict[str, Callable[[Any], Callable[[], None]]] = {
    "guard-drop-allow": _mod_drop_allow,
    "guard-stale-allow": _mod_stale_allow,
    "guard-count": _mod_count,
    "guard-new-site": _mod_new_site,
}

# Which tests each mutation applies to (substring of the test function name).
_TARGETS: dict[str, tuple[str, ...]] = {
    "css-no-fail-rule": (
        "test_failing_error_count_keeps_danger_color",
        "test_error_count_button_lists_that_call_kinds_errors_only",
    ),
    "css-no-fail-hover": (
        "test_failing_error_count_keeps_danger_color",
        "test_error_count_button_lists_that_call_kinds_errors_only",
    ),
    "no-dash-help-opener": ("test_annotation_tab_save_and_collate",),
    "wrong-help-key": ("test_annotation_tab_save_and_collate",),
    "raw-names": ("test_quality_tiles_have_no_unglossed_raw_names",),
    "title-hole": ("test_help_icon_labels_match_registry_titles",),
    "error-claim": ("test_score_grounding_help_matches_server_behaviour",),
    "guard-drop-allow": ("test_toast_sites_equal_the_allowlist",),
    "guard-stale-allow": ("test_toast_sites_equal_the_allowlist",),
    "guard-count": ("test_toast_sites_equal_the_allowlist",),
    "guard-new-site": ("test_toast_sites_equal_the_allowlist",),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--mut", default="", help="comma-separated mutation names")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    requested = [m for m in metafunc.config.getoption("--mut").split(",") if m and m != "none"]
    unknown = [m for m in requested if m not in _TARGETS]
    if unknown:
        raise pytest.UsageError(f"unknown mutation(s): {unknown}")
    name = metafunc.function.__name__
    muts = [m for m in requested if any(t in name for t in _TARGETS[m])]
    if muts:
        metafunc.fixturenames.append("_mut")
        metafunc.parametrize("_mut", ["none", *muts], indirect=True)


@pytest.fixture
def _mut(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> Iterator[None]:
    callspec = getattr(item, "callspec", None)
    mut = callspec.params.get("_mut", "none") if callspec else "none"
    funcargs: dict[str, Any] = getattr(item, "funcargs", {})
    applied: list[str] = []
    cleanup: list[Callable[[], None]] = []

    if mut in _HTML:
        page = funcargs["page"]

        def _handler(route: Any) -> None:
            resp = route.fetch()
            body = resp.text()
            for old, new in _HTML[mut]:
                body = _replace_once(body, old, new, mut)
            applied.append(mut)
            route.fulfill(response=resp, body=body)

        page.route(lambda url: urlparse(url).path == "/_dashboard/", _handler)
    elif mut in _FUNCARG:
        arg, fn = _FUNCARG[mut]
        funcargs[arg] = fn(funcargs[arg])
        applied.append(mut)
    elif mut in _FLASK:
        from flask import request as flask_request

        app = funcargs["ann_app"].app

        def _rewrite(response: Any) -> Any:
            if flask_request.path == "/_dashboard/":
                body = response.get_data(as_text=True)
                for old, new in _FLASK[mut]:
                    body = _replace_once(body, old, new, mut)
                response.set_data(body)
                applied.append(mut)
            return response

        funcs = app.after_request_funcs.setdefault(None, [])
        funcs.append(_rewrite)
        cleanup.append(lambda: funcs.remove(_rewrite))
    elif mut in _MODULE:
        cleanup.append(_MODULE[mut](item.module))  # type: ignore[attr-defined]
        applied.append(mut)

    try:
        return (yield)
    finally:
        for fn in cleanup:
            fn()
        if mut != "none" and not applied:
            raise MutationNotApplied(f"{mut}: never applied during {item.nodeid}")
        if mut != "none":
            with open(os.environ.get("MUT_LOG", os.devnull), "a", encoding="utf-8") as fh:
                fh.write(f"applied {mut} -> {item.nodeid}\n")
```

---

## The fix

_(Recorded per item as it lands.)_

---

## Acceptance bar

Every row: mutation applied (logged), HEAD test passes it, new test fails it with the
assertion that names the regression, `none` arm passes. Run with `-p no:rerunfailures`.

```toml
schema = 1
id = 179
kind = "item"
title = "A test writes stub eval runs into the real evals/results/: 337 of 425 files, so the regression baseline and the dashboard read test output"
status = "open"
decision_owner = "agent"
branches = ["fix/eval-results-test-leak"]
refs = [
  "evals/runner.py:1204",
  "evals/runner.py:581",
  "blueprints/diagnostics.py:1118",
  "blueprints/diagnostics.py:1306",
  "dashboard/routes.py:116",
  "tests/test_annotation_routes.py:1150",
  "tests/conftest.py",
  "docs/dev/diagnosis/eval-results-test-leak.md",
  "docs/dev/diagnosis/llm-handle-leak-and-letter-date.md",
]
summary = "run_suite's out_dir default binds RESULTS_DIR at def time, so a test's patch misses it; 337 stub files in the real dir."
```

**Found 2026-10-19** while scoping item 137's candidate A/B: the real `evals/results/` is mostly test output. Evidence and
the falsification experiment are in `docs/dev/diagnosis/eval-results-test-leak.md`.

**Why it is a mechanism item, not a note (charter C-11).** It is a recurrence of a known class: item 33 (`analyzer.LOG_PATH`),
item 151 (the gate result file) and O7 (the ledger shard) were each closed with an autouse redirect in `tests/conftest.py`.
A one-off stray file in this directory was already seen on 2026-10-17 and recorded as a one-off
(`docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:161`). Each redirect covers the writer someone found; none notices
the next one, so the plan adds a session sentinel that fails closed.

## Updates

### 2026-10-19 — filed on `fix/eval-results-test-leak`

Owner decisions (chat): fix the leak on its own `fix/` branch before item 137's review/A-B; move the existing stub files to
`evals/results/_test_stubs_quarantine/` afterwards (local, gitignored files).

### 2026-10-19 — built on `fix/eval-results-test-leak`; owner closes

Reproduced (the suspect test alone writes the stub signature), fixed (`run_suite(out_dir=None)` resolved at call time), guarded
(autouse per-test redirect plus a session check that fails pytest when the real directory gains a file; proved to fail closed
against the old runner), and the 337 existing stub files moved to `evals/results/_test_stubs_quarantine/`. Evidence:
`docs/dev/diagnosis/eval-results-test-leak.md`. Closing needs a `verified_by`: the regression test
`tests/test_eval_runner.py::TestRunSuite::test_run_suite_default_out_dir_follows_patched_results_dir` and the session check in
`tests/conftest.py` (`pytest_sessionfinish`).

**Not established:** that this test was the writer of all 337 (all share its signature; a second writer with the same stubs would
too). The session check is the instrument for any other. **Known limit (C-0):** it compares file names, and a real eval run in
another terminal during pytest trips it.

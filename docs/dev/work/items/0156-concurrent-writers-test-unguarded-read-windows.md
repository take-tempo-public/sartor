```toml
schema = 1
id = 156
kind = "item"
title = "test_concurrent_writers_do_not_erase_each_other: on Windows a writer thread's own unguarded pre-read can hit PermissionError and drop its delta"
status = "closed"
decision_owner = "agent"
branches = ["fix/python-direct-hooks-plan-gate", "fix/test-reliability"]
refs = [
  "tests/test_hardening.py:1171",
  "tests/test_hardening.py:1185",
  "docs/dev/diagnosis/test-reliability.md",
]
summary = "On Windows a writer thread's own pre-read hit PermissionError mid-replace; its delta was lost. Test or code: unverified."
resolution = "2026-10-09, fix/test-reliability: test, not code. In 700 runs (400 idle, 300 under load) every failure was a harness thread dying in its own pre-read (a plain read raises PermissionError on Windows while another thread os.replace's the file), plus 2 naive-arm write_context_atomic exhaustions; no crash had a context_transaction frame (diagnosis O1-O3). The harness's pre-reads now retry on write_context_atomic's own budget, a transactional writer that raises fails the test by name, and the control counts only writers that finished. hardening.py is unchanged."
verified_by = [
  "tests/test_hardening.py::TestContextTransaction::test_concurrent_writers_do_not_erase_each_other",
  "docs/dev/diagnosis/test-reliability.md (Acceptance bar: 18/300 -> 0/300 under the same load; mutation checks)",
]
```

**Observed (2026-10-07, local Windows 11, Python 3.13, session `08aa18b5`, on
`fix/python-direct-hooks-plan-gate`).**

`python -m pytest tests/test_hardening.py tests/test_wiki_relevance_classification.py
-p no:rerunfailures -q` gave `1 failed, 124 passed`:

```
tests\test_hardening.py:1185: in test_concurrent_writers_do_not_erase_each_other
E   AssertionError: context_transaction lost a delta: only ['k0', 'k1', 'k3', 'k4', 'k5', 'k6', 'k7'] survived
```

with a `PytestUnhandledThreadExceptionWarning` from the writer thread:

```
File "C:\Dev\sartor\tests\test_hardening.py", line 1171, in _transactional
  json.loads(path.read_text(encoding="utf-8"))  # the optimistic pre-call read
PermissionError: [Errno 13] Permission denied: '…\test_concurrent_writers_do_not0\txn.json'
```

- The same test passed in CI on Linux on PR #160 (run 37666513318).
- The branch's diff does not touch `hardening.py` or `tests/test_hardening.py`.
- One run; no rate measured.

**Inferred (unproven):** on Windows, reading a file while another thread `os.replace`s it can
raise a sharing violation (`PermissionError`). The read that died is the **test's own**
"optimistic pre-call read" outside `context_transaction`, so the thread exited before its
transaction. If so, this is a test-harness race, not a lost update in `context_transaction`.
**Not verified:** whether a reader *inside* `context_transaction` can hit the same error, which
would make it a product defect on Windows (memory `reference-atomic-context-write-windows`
records the related "atomic ≠ lost-update-safe" class).

**First move (C-7):** reproduce in a loop on Windows (N runs, failure rate), and capture where
the PermissionError lands: the test's pre-read or the transaction's own read. Fix only what
that shows.

## Updates

### 2026-10-09 — fix/test-reliability: closed

- **Test, not code** (`docs/dev/diagnosis/test-reliability.md` O1–O3).
  - A capability probe showed that a plain read raises `PermissionError` on Windows while
    another thread `os.replace`s the file.
  - The real test, with each writer's crash captured, failed 8 of 400 idle and 18 of 300 under 6
    CPU loaders.
  - Every crash was the harness's own pre-read, in either arm. Two more were naive-arm
    `write_context_atomic` exhaustions.
  - No crash had a `context_transaction` frame.
- **The fix:**
  - the pre-reads retry on `write_context_atomic`'s own bounded budget;
  - a transactional writer that raises fails the test by name;
  - the control counts only naive writers that finished, so a crash can't pass it vacuously.
- **Same load, same machine:** 18/300 → 0/300. Mutation checks: a killed transactional writer
  fails the test by name, and a killed naive writer is excluded and the test passes.
- **Not fixed, filed in the carry-forward ledger:** the threaded UX `live_server` could expose a
  route's optimistic read to the same `PermissionError` on Windows. Not observed.

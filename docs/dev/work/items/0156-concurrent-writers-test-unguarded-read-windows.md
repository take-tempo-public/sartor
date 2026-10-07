```toml
schema = 1
id = 156
kind = "item"
title = "test_concurrent_writers_do_not_erase_each_other: on Windows a writer thread's own unguarded pre-read can hit PermissionError and drop its delta"
status = "open"
decision_owner = "agent"
branches = ["fix/python-direct-hooks-plan-gate"]
refs = [
  "tests/test_hardening.py:1171",
  "tests/test_hardening.py:1185",
]
summary = "On Windows a writer thread's own pre-read hit PermissionError mid-replace; its delta was lost. Test or code: unverified."
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

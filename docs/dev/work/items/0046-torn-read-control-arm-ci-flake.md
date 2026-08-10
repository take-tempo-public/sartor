```toml
schema = 1
id = 46
kind = "item"
title = "CI flake: test_reader_never_observes_a_partial_file's control arm fails when the naive writer doesn't tear"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/test_hardening.py",
  "https://github.com/take-tempo-public/sartor/actions/runs/30940947527/job/92098846975",
]
summary = "Control assertion (`assert naive`) is itself a timing race; a quiet runner completes write_text between reader polls."
```

Observed 2026-08-04 on PR #99 (`feat/consumer-enumeration-gate`). The py3.13 leg of
the `quality` job failed; py3.11 and py3.12 passed on the **same commit, same
workflow run**.

```
tests/test_hardening.py:1041: in test_reader_never_observes_a_partial_file
    assert naive, "harness never reproduced a torn read — the assertion below proves nothing"
E   AssertionError: harness never reproduced a torn read
E   assert []
1 failed, 2196 passed, 6 skipped in 45.13s
```

**Not the subject arm.** `assert not atomic` — the real invariant, that
`write_context_atomic` never exposes a partial file — did not fire. What failed is the
**control**: `_write_naive` (a plain `path.write_text`) was supposed to produce at least
one `JSONDecodeError` in a concurrent reader, and produced none. The test correctly
refuses to report a vacuous pass, which is good design; the control is simply a race in
its own right.

**Mechanism (inferred, not proven):** `_torn_reads` has the writer sleep 0.002s and each
reader sleep 0.004s (`tests/test_hardening.py:1001,1017`). On a fast, unloaded runner a
small-payload `write_text` can complete entirely between two reader polls, so no reader
ever samples a half-written file. Nothing establishes a minimum payload size or forces
interleaving. **Not verified** — no instrumented run was made; this is a code read.

**Attribution — why this is not PR #99's doing:**

- `hardening.py` and `tests/test_hardening.py` are **not in that branch's diff**
  (`git diff --name-only origin/main..HEAD`, 26 files, neither present).
- The identical commit passed the same job on **py3.11 and py3.12**.
- The full gate, including this test, passed **locally on Python 3.13.14** — the same
  version as the failing leg — with zero reruns.

**Rerun masking is not a factor either way:** `--reruns` is enabled only for the CI `ux`
tier (`pyproject.toml:94-95`); the `quality`/`gate` pytest is strict single-attempt. So
this was one honest attempt that failed, not a rerun-exhausted lottery.

**Deliberately not fixed here.** A robust control would need a real change of shape —
retry the naive harness N times before failing, force interleaving, or grow the payload
past a page boundary so a partial write is unavoidable. That is its own `fix/*` with a
C-7 dossier and an instrumented reproduction, not a same-branch patch on a governance
change. Do **not** paper over it by deleting or weakening the control assertion — the
control is the only thing that makes the subject assertion mean anything
(`tests/test_hardening.py:1029-1032` says so explicitly).

Escalation signal: if this blocks a second PR, it stops being a watch item and gets its
own investigation. One sample so far.

## Updates

### 2026-08-04 — filed during feat/consumer-enumeration-gate (CI observation on PR #99)

### 2026-08-06 — independently reproduced by the flake-rate instrument; still n=1

`feat/flake-rate-measurement`'s 30-run backfill (2026-08-03 → 2026-08-06) parsed the
same run this item already cites
([`30940947527`](https://github.com/take-tempo-public/sartor/actions/runs/30940947527))
and independently arrived at the identical result: `tests/test_hardening.py::
TestWriteContextAtomic::test_reader_never_observes_a_partial_file`, py3.13 leg only, 1
of 1 attempts failed. **This is cross-validation of the parsing instrument against a
known artifact, not a new occurrence** — no second failure of this test appears
anywhere in the 30-run window (which spans both before and after this item's own
2026-08-04 filing date). The item's own escalation signal ("if this blocks a second
PR, it stops being a watch item") has not fired. No status change.

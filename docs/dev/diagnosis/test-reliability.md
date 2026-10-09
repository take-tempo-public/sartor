# Diagnosis: two unverified test flakes (items 155 and 156)

> **Status:**
> - **Item 156: harness defect, OBSERVED.** The test's own threads die in their unguarded
>   pre-reads on Windows (O1–O3), and the test misreports that as a lost update. No failure
>   seen in 700 runs is inside `context_transaction`.
> - **Item 155: mechanism H1 OBSERVED locally.** The notes save that the company edit triggers
>   is answered after the company save, and its toast overwrites `Company saved` (O5, O6). The
>   single CI failure fits the same shape, but it left no request log, so its own mechanism is
>   inferred (`## Inferred`).
>
> **Branch:** `fix/test-reliability`

---

## Symptom

- **Item 155** (`docs/dev/work/items/0155-company-save-toast-preempted-by-notes-blur.md`).
  `tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_persists`
  waited for the toast `Company saved`. For 5 s it saw only `Notes saved`, and the retry passed.
- **Item 156** (`docs/dev/work/items/0156-concurrent-writers-test-unguarded-read-windows.md`).
  `tests/test_hardening.py::TestContextTransaction::test_concurrent_writers_do_not_erase_each_other`
  reported `context_transaction lost a delta` on local Windows. A writer thread's own pre-read
  had raised `PermissionError`.

---

## Observed

Machine: Windows 11 Pro 10.0.26200, 8 logical cores, Python 3.13 (Windows Store). Session
`810882f3`, 2026-10-08, on `fix/test-reliability` branched from `main` @ `1c528ed`.

### Carried in from the filed items (earlier sessions, not re-run)

- **155, CI.** PR #159, run 37569283583, job 112624033244 ("UX / a11y / PDF (Playwright,
  py3.12)"). `python -m scripts.ci_wait 159` exited 3, and the failed attempt's traceback was:

  ```
  tests/ux/regression/test_20260611_prior_app_resume_robustness.py:125: in test_card_company_editable_and_persists
      expect(page.locator("#_corpusToast")).to_have_text("Company saved")
  E   AssertionError: Locator expected to have text 'Company saved'
  E   Actual value: Notes saved
  E     9 x locator resolved to <div id="_corpusToast" class="corpus-toast show">Notes saved</div>
  E     5 x locator resolved to <div id="_corpusToast" class="corpus-toast">Notes saved</div>
  ```

- **156, local Windows** (session `08aa18b5`, 2026-10-07).
  `python -m pytest tests/test_hardening.py tests/test_wiki_relevance_classification.py -p no:rerunfailures -q`
  gave `1 failed, 124 passed`:

  ```
  tests\test_hardening.py:1185: in test_concurrent_writers_do_not_erase_each_other
  E   AssertionError: context_transaction lost a delta: only ['k0', 'k1', 'k3', 'k4', 'k5', 'k6', 'k7'] survived
  ```

  The writer thread's `PytestUnhandledThreadExceptionWarning`:

  ```
  File "C:\Dev\sartor\tests\test_hardening.py", line 1171, in _transactional
    json.loads(path.read_text(encoding="utf-8"))  # the optimistic pre-call read
  PermissionError: [Errno 13] Permission denied: '…\test_concurrent_writers_do_not0\txn.json'
  ```

  The same test passed in CI on Linux on PR #160 (run 37666513318). That was one run, with no
  rate measured.

### O1. Item 156: a plain read and a writer's replace can each raise `PermissionError` on Windows

The capability probe `probe156.py` (source under `## Falsification`, P-156) was run as
`python probe156.py /c/Dev/sartor <scratch>/probe156_work 3 200` on an idle machine:

```
python 3.13.14 platform win32
ARM A readers=1 seconds=3.0: reads={'ok': 844, 'PermissionError': 12} writes={'ok': 34}
ARM A readers=7 seconds=3.0: reads={'ok': 5589, 'PermissionError': 19} writes={'ok': 11, 'PermissionError': 4}
ARM B iterations=200: iterations_with_a_crash=0 lost_delta_without_crash=0
```

- **R1 is possible.** Under a tight loop, a plain `read_text()` raised `PermissionError` while
  `write_context_atomic` replaced the file: 12 of 856 reads with one reader, and 19 of 5,608 with
  seven. No read returned torn JSON (no `JSONDecodeError`).
- **R3 is possible.** With seven tight readers, 4 of 15 `write_context_atomic` calls used up
  their 12 retries and raised `PermissionError`.
- **The test's own shape rarely hits either.** Eight threads ran the test's `_transactional` body
  (pre-read, 20 ms sleep, `context_transaction`) 200 times on an idle machine. No thread raised,
  and no delta was lost. A 0/200 result is consistent with a per-run rate up to about 1.5 %
  (the 95 % upper bound, 3/n).

### O2. Item 156: the real test fails 8 times in 400, and every failure is the naive arm's own pre-read

The instrument commit wraps each writer thread in `test_concurrent_writers_do_not_erase_each_other`.
An exception is captured with its traceback, and the test fails naming the thread (`crashes`,
`assert not crashes`). Nothing else changed.

The real test was run in one pytest process through a scratchpad loop plugin that
parametrizes it N times. A fresh pytest start costs about 47 s here (measured:
`1 passed in 47.61s` for one trivial node), so this avoids that cost N times. Idle machine:

```
$ PYTHONPATH=<scratch>/loopplug python -m pytest "tests/test_hardening.py::TestContextTransaction::test_concurrent_writers_do_not_erase_each_other" -p loop_plugin --loop 100 -p no:rerunfailures -q -o addopts=""
1 failed, 99 passed in 72.30s (0:01:12)

$ (same, --loop 300 --tb=long)
7 failed, 293 passed in 163.05s (0:02:43)
```

Every failure has the same site, counted over the 300-run log:

```
      7 line 1166, in _naive
E           File "C:\Dev\sartor\tests\test_hardening.py", line 1166, in _naive
E             ctx = json.loads(path.read_text(encoding="utf-8"))
E         PermissionError: [Errno 13] Permission denied: '…\test_concurrent_writers_do_not6\naive.json'
```

- **The tally:** 8 of 400 runs failed (2 %). The site is the naive control arm's pre-read
  (`tests/test_hardening.py:1166`), each time a plain `read_text()` raising `PermissionError`.
  The 100-run failure has the same site.
- **The transactional arm never crashed.** That was the item's original site, `:1171`.
- **No frame in `hardening.py` appears in any failure.** So R2 and R3 were never seen.
- **On HEAD, these 8 runs would have passed.** A crashed naive writer never writes its key,
  and that satisfies the control's `len(naive_keys) < 8` without any race. The capture is what
  made them visible.

### O3. Item 156 under CPU load: the transactional arm's pre-read crashes too, and `context_transaction` never does

The same 300-run loop, with 6 busy-loop loaders on 8 logical cores (`python -c "while True: pass"`,
started and killed through PowerShell `Start-Process`/`Stop-Process`; 0 still alive afterwards):

```
18 failed, 282 passed in 371.47s (0:06:11)
```

Crashes in the 18 failing runs, counted from the per-crash header lines (`E   <arm> writer kN:`):

```
     14 _naive writer
      8 _transactional writer
```

The innermost test-code frame of each crash, and the only `hardening.py` frame that appears:

```
     12 line 1166, in _naive               (its pre-read: read_text -> PermissionError)
      2 line 1169, in _naive               (its unlocked write_context_atomic)
      8 line 1172, in _transactional       (its pre-read: read_text -> PermissionError)
      2 line 1689, in write_context_atomic (os.replace -> PermissionError: [WinError 5], retries used up)
```

- **The item's original failure site reproduces under load:** the transactional arm's own
  pre-read. That is `:1172` in the file these runs used, which had one import line more than
  `main`, where it is `:1171`. It crashed 8 times; the idle 400 runs had none. (Line numbers in
  O2 and O3 are the file as instrumented at run time.)
- **R3 happened, but only in the naive arm.** That arm has eight writers replacing the file
  with no lock, so twice a `write_context_atomic` used up its 12 retries.
- **No crash in any of the 700 runs has a `context_transaction` frame** (`grep -c "in
  context_transaction"` = 0 in the loaded log). So R2 was never seen, and neither was R3
  inside a transaction.

### O4. Item 155 in CI: 1 failed attempt in 113

`python -m scripts.flake_rates collect --limit 30` reported `listed 30 run(s), 26 new` and wrote
shard `docs/dev/flake-rates/runs/ae87b9d8-1ed6-4369-bada-074e3e0531b0.jsonl`. Then
`python -m scripts.flake_rates report` gave:

```
   rate   wilson    fail/att    runs   shas  tier  nodeid
  0.9%    0.2%     1/113       112      1  ux                tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_persists
```

- **CI per-attempt rate:** 1 failed attempt in 113, across 112 runs. The one failure is the
  attempt the item records.
- **Before the collect,** the store held 0/86 for this test; its newest run was from 2026-10-02.

### O5. Item 155 locally: the notes PUT fires in every run, and holding its response reproduces the CI failure exactly

The instrument adds an in-page timeline to the real test, all on the page's clock: `focusin` and
`focusout`, every `fetch` start and settle with its status, and every change to `#_corpusToast`.
It prints on failure, and on every run when `SARTOR_UX_TIMELINE=1`. The test body moved,
unchanged, into a helper `_company_round_trip` so that the probe P-H1 runs the identical wait.

P-H1 (`test_probe_notes_response_after_meta_response`) fetches each PUT `/notes` response but
holds it. It delivers the response only once the PUT `/meta` response has been delivered.
Both tests were run 5 times each in one process, on an idle machine with about 0.8 GB free:

```
$ SARTOR_UX_TIMELINE=1 PYTHONPATH=<scratch>/loopplug python -m pytest "<file>::test_card_company_editable_and_persists" "<file>::test_probe_notes_response_after_meta_response" -m ux -p loop_plugin --loop 5 -p no:rerunfailures --runxfail -rP -o addopts="" --tb=short
tests\ux\regression\test_20260611_prior_app_resume_robustness.py .....FF [ 70%]
FFF                                                                      [100%]
=================== 5 failed, 5 passed in 113.16s (0:01:53) ===================
```

**The real test (5 of 5 passed).** In every run the modal opened with focus on the notes
textarea, and `set_company` sent PUT `/notes` (notes unchanged) before PUT `/meta`. The PUT and
toast events, in ms on the page clock:

```
 703 fetch> notes; 851 fetch< notes 200; 853 toast Notes saved; 891 fetch> meta; 1065 fetch< meta 200; 1070 toast Company saved
 534 fetch> notes; 561 fetch< notes 200; 562 toast Notes saved; 731 fetch> meta;  760 fetch< meta 200;  762 toast Company saved
 445 fetch> notes; 616 fetch< notes 200; 617 toast Notes saved; 641 fetch> meta;  684 fetch< meta 200;  686 toast Company saved
 674 fetch> notes; 753 fetch> meta;  790 fetch< notes 200; 791 toast Notes saved;  834 fetch< meta 200;  836 toast Company saved
 630 fetch> notes; 695 fetch< notes 200; 696 toast Notes saved; 743 fetch> meta;  791 fetch< meta 200;  793 toast Company saved
```

(Each line is compressed from the printed timeline; the focus events are omitted. In every run,
`focusin appDetailNotes` came first, and `focusout appDetailNotes` and `focusin appDetailCompany`
came within 4 ms of PUT `/notes`.)

- **The notes PUT fired in 5 of 5 runs.** It is sent by the notes blur that `fill()` causes when
  it focuses the company input.
- **Its head start over the meta PUT was 79–197 ms** (fill takes that long between the two
  blurs). The notes PUT's own latency was 27–171 ms.
- **In run 4 the two requests overlapped:** meta was sent at 753 ms, and the notes response
  arrived at 790. The notes response still came first, so the toast ended on `Company saved`.

**The probe (5 of 5 failed, as designed),** each with the CI failure's text:

```
E   AssertionError: Locator expected to have text 'Company saved'
E   Actual value: Notes saved
```

The first probe run's timeline shows the overwrite:

```
   1084 fetch>   PUT /api/applications/1/meta
   1220 fetch<   PUT /api/applications/1/meta 200
   1222 toast    corpus-toast show | Company saved
   1223 fetch<   PUT /api/applications/1/notes 200
   1223 toast    corpus-toast show | Notes saved
   3625 toast    corpus-toast | Notes saved
```

`Company saved` was on screen for 1 ms. Then `Notes saved` showed for 2.4 s (`_toast`'s hide
timer) and stayed in the element after hiding. That is the shape of CI's 9 polls with `show` and
5 without.

### O6. Item 155 under CPU load: 3 natural failures in 30, all with the meta response first

The real test ran 30 times in one process with `SARTOR_UX_TIMELINE=1`, under 6 busy-loop
loaders on 8 logical cores (0 still alive afterwards). Free RAM was about 0.6 GB at the start:

```
================== 3 failed, 27 passed in 287.83s (0:04:47) ===================
```

All three failures carry the CI failure's text (`Actual value: Notes saved`). Their timelines:

```
 836 fetch> notes;  883 fetch> meta; 1295 fetch< meta 200; 1297 toast Company saved; 1313 fetch< notes 200; 1314 toast Notes saved; 3724 toast (hidden) Notes saved
 586 fetch> notes;  683 fetch> meta; 1174 fetch< meta 200; 1176 toast Company saved; 1288 fetch< notes 200; 1288 toast Notes saved; 3692 toast (hidden) Notes saved
 656 fetch> notes;  753 fetch> meta;  890 fetch< meta 200;  892 toast Company saved;  897 fetch< notes 200;  897 toast Notes saved; 3309 toast (hidden) Notes saved
```

(Compressed from the printed timeline; in each run `focusin appDetailNotes` came first.)

The PUT order in each of the 30 timelines, counted by a short parse of the log:

```
passed: runs=27 overlapped(meta sent before notes returned)=14 meta_returned_first=0
toast wait failed: runs=3 overlapped(meta sent before notes returned)=3 meta_returned_first=3
```

- **Response order alone decides the outcome in all 30 runs.** All 3 runs where the meta
  response arrived first failed. All 27 runs where the notes response arrived first passed.
- **`Company saved` was on screen for 17 ms, 112 ms and 5 ms** before `Notes saved` replaced
  it. Each time, Playwright's polls missed it.
- **In every failure the meta PUT was sent and returned 200,** 136–490 ms after it was sent.
- **Under load, 17 of 30 runs had both PUTs in flight at once;** on the idle machine, 1 of 5
  did (O5).

---

## Falsified

- **Item 155, H2, H3 and H4, for all three local failures (O6).** The meta PUT was sent in each
  (H4 dead), returned 200 (H3 dead), and returned within 490 ms of a 5 s wait (H2 dead). These
  are dead only for the failures this branch captured. The CI attempt left no request log, so
  none of the four is falsified for it; see `## Inferred`.
- **Item 156, "the product lost an update."**
  - In 700 runs (O2, O3), no crash has a `context_transaction` frame.
  - Every failure is the new crash assertion. In the two saved logs, `grep -c 'AssertionError: a
    writer thread raised'` equals the `FAILED` count (7 = 7, and 18 = 18), and `context_transaction
    lost a delta` appears 0 times. The unsaved 100-run log's one failure was also the crash
    assertion (its tail, O2).
  - The item's failure is a harness thread dying in its own pre-read. 700 runs can't prove the
    product path never fails this way, but no failure seen on this branch was in it.

---

## Inferred

**Hypotheses. Each says what would have to be seen to know it.**

The code read this branch started from is not repeated here. Its four item-155 rivals (H1–H4)
and three item-156 rivals (R1–R3) are named in `## Observed` and `## Falsified`, with the result
each one got.

### Item 155

- **The CI failure was H1.** That attempt fits H1's shape, and nothing else seen fits it:
  - `Notes saved` stayed in the toast for the whole 5 s;
  - 9 polls saw it with `show` and 5 without, which matches `_toast`'s 2.4 s hide timer;
  - all three local captures of H1 look the same (O6).

  That attempt left no request log, so H2–H4 can't be ruled out for it. To know, a CI failure
  must print its timeline. The instrument now does that on failure, and the rerun-report hook in
  `tests/ux/conftest.py` prints a failed attempt's captured output in the CI log.
- **Why the notes response comes back after the meta one under load.** Probably thread
  scheduling in the threaded `live_server`: the two PUTs are served concurrently and don't wait
  on each other. The notes value is unchanged (`None` to `None`), so its route may issue no
  UPDATE at all. Neither point is checked. Neither changes the fix: the test must not depend on
  the order of two concurrent responses.

### Item 156

- **Why Windows refuses the read.** The read raises `PermissionError` while another thread
  `os.replace`s the file (O1). The mechanism is unread: probably the open lands while the old
  file is being deleted by the rename. Checking it would take a Windows-internals trace, and the
  fix doesn't depend on it.
- **The UX tier may have the same exposure, out of scope.** The UX `live_server` is threaded
  (`tests/ux/conftest.py`). So on Windows, a route's optimistic context read that runs outside
  `context_transaction` could raise the same `PermissionError` while another request writes
  that file. The production server is single-threaded (`context_transaction`'s docstring,
  `hardening.py`), so production can't reach it. Not observed; filed in the carry-forward ledger,
  not fixed here.

---

## Falsification

Each experiment was stated before it ran, and each could have come out the other way.

**Item 156**
- **P-156, capability (O1).** Can a plain read, or a writer's replace, raise `PermissionError`
  on Windows under concurrent access? If neither ever did, R1 and R3 were dead.
- **The real test in a loop, with each crash captured and its site named (O2, O3).** If any
  crash had a `context_transaction` frame, the product path was implicated (R2 or R3), and the
  plan said to STOP and take it to the owner. None did.

**Item 155**
- **P-H1, capability (O5).** `test_probe_notes_response_after_meta_response` must fail on HEAD
  with `Actual value: Notes saved`. If it had passed, H1 could not produce the symptom. It
  failed 5 of 5. It is committed as `xfail(strict=True)`, so it keeps failing on HEAD by
  design. The fix must turn it into a pass, and a strict xfail that passes fails the suite.
- **The real test under load, with the timeline (O6).** Any natural failure names its own
  mechanism. If the failures had shown the meta PUT slow, failing or missing, H1 was not the
  mechanism. All three showed H1.

**P-156 source** (scratchpad `probe156.py`, run as in O1):

```python
"""Item 156 capability probe: what does a concurrent read/replace raise on Windows, and where?

Arm A (R1/R3 capability, tight loop): one writer loops `write_context_atomic`, N readers loop
`read_text()`. Counts every outcome on both sides.

Arm B (the test's own shape, many iterations): 8 threads each do the test's `_transactional`
body (pre-read, sleep 0.02, `context_transaction`). Each exception is classified by the
innermost repo frame: the probe's pre-read (R1), `context_transaction`'s in-lock read (R2), or
`write_context_atomic`'s replace (R3).

Usage: python probe156.py <repo> <workdir> [armA_seconds] [armB_iterations]
"""

from __future__ import annotations

import collections
import json
import sys
import threading
import time
import traceback
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()
A_SECONDS = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
B_ITERS = int(sys.argv[4]) if len(sys.argv) > 4 else 200
sys.path.insert(0, str(REPO))

from hardening import context_transaction, write_context_atomic  # noqa: E402

WORK.mkdir(parents=True, exist_ok=True)


def site_of(exc: BaseException) -> str:
    """Innermost frame's function and line, plus the innermost hardening.py frame if any."""
    frames = traceback.extract_tb(exc.__traceback__)
    inner = frames[-1]
    hard = [f for f in frames if f.filename.endswith("hardening.py")]
    where = f"{Path(inner.filename).name}:{inner.lineno}:{inner.name}"
    if hard:
        h = hard[-1]
        where += f" [hardening.py:{h.lineno}:{h.name}]"
    return f"{type(exc).__name__} @ {where}"


def arm_a() -> None:
    path = WORK / "armA.json"
    write_context_atomic(path, {"base": True, "pad": "x" * 2000})
    stop = time.monotonic() + A_SECONDS
    reads: collections.Counter[str] = collections.Counter()
    writes: collections.Counter[str] = collections.Counter()
    lock = threading.Lock()

    def reader() -> None:
        local: collections.Counter[str] = collections.Counter()
        while time.monotonic() < stop:
            try:
                json.loads(path.read_text(encoding="utf-8"))
                local["ok"] += 1
            except Exception as e:  # noqa: BLE001 - the probe counts every outcome
                local[type(e).__name__] += 1
        with lock:
            reads.update(local)

    def writer() -> None:
        i = 0
        while time.monotonic() < stop:
            i += 1
            try:
                write_context_atomic(path, {"base": True, "i": i, "pad": "x" * 2000})
                writes["ok"] += 1
            except Exception as e:  # noqa: BLE001
                writes[type(e).__name__] += 1

    for n_readers in (1, 7):
        reads.clear()
        writes.clear()
        stop = time.monotonic() + A_SECONDS
        ts = [threading.Thread(target=reader) for _ in range(n_readers)]
        ts.append(threading.Thread(target=writer))
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        print(f"ARM A readers={n_readers} seconds={A_SECONDS}: reads={dict(reads)} writes={dict(writes)}")


def arm_b() -> None:
    sites: collections.Counter[str] = collections.Counter()
    lost_iters = 0
    crash_iters = 0
    for it in range(B_ITERS):
        path = WORK / f"armB_{it}.json"
        write_context_atomic(path, {"base": True})
        errors: list[str] = []
        elock = threading.Lock()

        def txn(i: int) -> None:
            try:
                json.loads(path.read_text(encoding="utf-8"))  # the test's optimistic pre-read
                time.sleep(0.02)
                with context_transaction(path) as fresh:
                    fresh[f"k{i}"] = i
            except Exception as e:  # noqa: BLE001
                with elock:
                    errors.append(site_of(e))

        ts = [threading.Thread(target=txn, args=(i,)) for i in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=30)
        keys = {k for k in json.loads(path.read_text(encoding="utf-8")) if k.startswith("k")}
        if errors:
            crash_iters += 1
            sites.update(errors)
        if len(keys) != 8 and not errors:
            lost_iters += 1  # a lost delta with NO crash would be a genuine lost update
        path.unlink(missing_ok=True)
    print(
        f"ARM B iterations={B_ITERS}: iterations_with_a_crash={crash_iters} "
        f"lost_delta_without_crash={lost_iters}"
    )
    for s, n in sites.most_common():
        print(f"  {n:4d} x {s}")


if __name__ == "__main__":
    print(f"python {sys.version.split()[0]} platform {sys.platform}")
    arm_a()
    arm_b()
```

**The loop plugin** (scratchpad `loopplug/loop_plugin.py`, used by O2, O3, O5 and O6):

```python
"""Run every selected test N times in ONE pytest process (`-p loop_plugin --loop N`).

Scratchpad-only rate instrument: a fresh pytest start costs ~47 s on this machine, so N
separate invocations would spend almost all their time starting up. Parametrizes each test
over a dummy fixture, the same way pytest-repeat does (not installed; no new dependency).
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--loop", type=int, default=1, help="run each test this many times")


@pytest.fixture
def _loop_index(request: pytest.FixtureRequest) -> int:
    return int(request.param)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    n = int(metafunc.config.getoption("loop"))
    if n > 1:
        metafunc.fixturenames.append("_loop_index")
        metafunc.parametrize("_loop_index", range(n), indirect=True)
```

---

## The fix

_(Not yet.)_

---

## Acceptance bar

_(Not yet.)_

```toml
schema = 1
id = 108
kind = "item"
title = "scripts/gate.py should refuse to start below a free-memory floor instead of dying mid-run as a mystery kill"
status = "closed"
decision_owner = "agent"
branches = ["docs/first-run-account-naming-finding", "feat/gate-memory-preflight"]
depends_on = [1]
refs = [
  "scripts/gate.py:22-36",
  "docs/dev/work/items/0001-gate-unrunnable-by-agent.md",
]
summary = "Gate dies mid-run as an OOM'd xdist worker; add a fail-closed free-memory preflight that refuses to start."
resolution = "Built on feat/gate-memory-preflight (2026-09-03): scripts/gate.py now reads free physical memory before any of the six real steps (platform-branched, stdlib/subprocess-only -- ctypes GlobalMemoryStatusEx on Windows, /proc/meminfo on Linux, vm_stat on macOS) and hard-refuses below _MEMORY_FLOOR_GB = 1.0, printing the shortfall plus a best-effort top-memory-consumers listing; no env-var override, per the item's own explicit constraint. The floor is a real measurement, not an inherited guess: pytest -m \"not ux\" -n auto was run in the background on this machine while sampling free memory every ~3s, under real ambient desktop load (not a sibling gate) -- the suite survived a genuine dip to 0.172 GB without crashing, but sustained operation in the 0.4-0.8 GB band produced severe thrashing (97%->98% took ~15 minutes) before the measurement run was stopped by hand at ~37 minutes elapsed. Combined with this item's own earlier crash evidence (0.7 GB), the floor is set above both the thrashing band and the crash point, not just the bare survival minimum -- full method and numbers are in scripts/gate.py's own comment on _MEMORY_FLOOR_GB. On a platform where free memory cannot be read, the preflight fails OPEN (proceeds) rather than blocking a run it has no evidence against -- stated as a limit, not hidden. Live end-to-end confirmation: a full real `python -m scripts.gate` run on this same machine (still memory-constrained through most of the session) completed ALL SIX steps green -- preflight (1.15 GB free / 1.00 GB floor, proceeded), ruff check, ruff format --check, mypy (372 files), pytest -m \"not ux\" -n auto (2680 passed, 5 skipped, 2287s), pytest -m ux (146 passed, 2 xpassed, 3339s), work_items check (108 files) -- 'gate: all steps passed.' Slower than the documented ~7-9min/~unloaded baseline (real memory contention, consistent with this item's own evidence) but zero failures start to finish."
verified_by = [
  "tests/test_gate_memory_preflight.py",
  "python -m scripts.gate (live full run, 2026-09-03, this machine: all six steps green, including 2680+146 real tests passed, 0 failures)",
]
```

**Observed** (2026-09-02, this machine). Four consecutive attempts to run
`python -m scripts.gate` on a docs-only branch failed to complete. No test failed.
The decisive artifact, from the fourth attempt:

```
[gw0] node down: Not properly terminated
```

That is an xdist worker killed by the OS at 73% through the non-UX tier, not a test
failure and not a flake. Free physical memory fell from 1.8 GB to 0.7 GB across the
attempts on a 15.7 GB box. The competing load was identified: a **sibling project's**
gate running concurrently in the same OS —
`C:\Dev\spolia\.venv\Scripts\python.exe scripts/gate.py` plus its pytest child.
`-n auto` spawns one worker per core, and the box could not feed them.

**Why this is a recurrence, not a first sighting.** Item 1 already records "gate
unrunnable by agent," and `scripts/gate.py`'s own docstring (lines 22-36) says the
plainest version of the problem:

> the full suite's real runtime is ~30min … long enough that a foreground/short-timeout
> agent call always got cut off — **which every prior session read as a mysterious kill,
> when it was really just an unmeasured runtime.**

The docstring diagnosed the *runtime* half and left the *resource* half uncovered. Three
of this session's four attempts were misread exactly as the docstring predicts — as
unexplained kills — until the fourth produced the `node down` line. The message reads like
a flake and is actually memory exhaustion, which is what makes it cost a session every time.

**The mechanism (owner-approved 2026-09-03, not yet built).** A **fail-closed preflight**
in `scripts/gate.py`, before the pytest steps: read free physical memory, and if it is
below a floor, **refuse to start** and print what is holding the memory — naming any other
`python.exe` running a gate or pytest, since a sibling project's suite is the observed
culprit. Refusing up front converts a 30-minute mid-run mystery into an immediate, legible
message.

**Design notes, not decisions** (whoever builds this makes the calls, and should measure
rather than inherit these):

- The floor is a number nobody has measured. Derive it from an actual observation of what
  `-n auto` peaks at on this box, and say in a comment where the number came from — an
  unmeasured threshold is the same class of defect as the one being fixed.
- Consider whether the right response below the floor is a hard refusal or a documented
  fallback to a lower `-n`. A refusal is fail-closed and therefore C-11-compliant; an
  automatic fallback silently changes what "gate green" means, which is worse.
- Keep it stdlib-only if possible. `os.cpu_count()` is stdlib; free physical memory is not
  portable stdlib, so this may need a platform branch or a small dependency — weigh that
  against the value, and if it lands as a dependency it needs a `pyproject.toml` entry plus
  a `CHANGELOG.md` line.
- The preflight must not itself become a reason a legitimate gate run is blocked. An
  override exists in this repo's tradition only when the owner explicitly directs it; do
  not add an env-var hatch on your own initiative.

**Stated limit (C-0).** This closes the "you cannot tell why it died" gap. It does not make
the gate runnable on a loaded machine — the operator still has to free memory or wait. That
is the correct scope: the defect is the illegibility, not the resource contention.

## Updates

### 2026-09-03 — filed at owner direction

Surfaced during a close-out where the gate could not be completed and the branch was
therefore not merged on the agent's own authority. Owner's response: "the mechanism is
sound. log it as a task." Filed rather than built, because building it is a code change on
a docs-only branch and it cannot be gate-verified while the gate cannot run.

### 2026-09-03 — built and closed on `feat/gate-memory-preflight`

Built per the design notes above, with the two open design questions this item left
explicitly unresolved now decided (both grounded in what the measurement actually showed,
not inherited):

- **Refusal, not fallback** — the item's own stated preference held up: a hard refusal is
  fail-closed and C-11-compliant, and an automatic `-n` fallback would silently change what
  "gate green" means. No env-var override was added.
- **The floor is real, not inherited.** Measured today on this same machine by running
  `pytest -m "not ux" -n auto` in the background while sampling free memory every ~3s, under
  genuine ambient desktop load (VS Code, Chrome, NordVPN, Windows Defender, WSL — not a
  sibling project's gate, confirmed by a live process listing at the time). The suite
  survived a dip to **0.172 GB** without crashing, but sustained operation in the 0.4-0.8 GB
  band produced severe thrashing — the run crawled from 97% to 98% complete over roughly 15
  minutes (a clean run takes ~7-9 minutes total) before the measurement was stopped by hand
  at ~37 minutes elapsed, both to stop tying up the machine and because the picture had
  stopped sharpening. "Did not crash" and "ran acceptably" turned out to be different
  thresholds on this box. Combined with this item's own earlier observation (crashed after
  falling to 0.7 GB), the floor (`_MEMORY_FLOOR_GB = 1.0`) is set above both the observed
  thrashing band and the earlier crash point — full method, numbers, and the stated limit
  (available memory is an imperfect proxy for "will run at normal speed") are in
  `scripts/gate.py`'s own comment on the constant, not just here.

**What was actually built:** `_available_memory_gb()` dispatches on platform (Windows via
`ctypes`/`GlobalMemoryStatusEx`, Linux via `/proc/meminfo`'s `MemAvailable`, macOS via
`vm_stat`) through pure, independently-testable parser functions; `_top_memory_consumers()`
lists the top memory users via `tasklist`/`ps` (best-effort, degrades to `[]` rather than
failing the diagnostic step) — deliberately reports the raw top consumers rather than
asserting "a sibling gate is running," since today's own measurement showed the top
consumers are routinely ordinary desktop apps, not another gate. `_check_memory_preflight()`
is called first in `main()`, before any of the six real steps. No new dependency (D-1):
everything is stdlib + subprocess, matching the existing `onboarding/review_cli.py`
`os.name`/`cast(Any, ctypes)` idiom for the mypy-strict/`warn_unreachable` Windows-only
`ctypes.windll` access.

**Verification:** `tests/test_gate_memory_preflight.py` (26 tests, 3 platform-gated skips)
covers the pure parsers with real captured sample text/output, the platform dispatch
(including a fully portable "unsupported platform fails open" test via monkeypatched
`os.name`/`sys.platform`), and all three `_check_memory_preflight` outcomes (proceed /
refuse / unmeasurable-proceeds) via a monkeypatched `_available_memory_gb` — never touches a
real OS read for the deterministic assertions. One test was caught and corrected during this
same session: an initial "real Windows `tasklist` call must return something" assertion
FAILED live when this machine's own thrashing caused the real subprocess call to time out —
correct behavior (the documented graceful-degrade-to-`[]` path firing for real), not a bug,
so the assertion was weakened to "returns a valid list" with the reasoning recorded in the
test file itself, rather than accepting a smoke test that is flaky by design on the exact
machine states this feature targets. Full `ruff check` / `ruff format --check` / `mypy` clean
on both changed files. Live end-to-end: a real `python -m scripts.gate` run on this same
machine (still memory-constrained through most of this session) correctly proceeded once
available memory cleared the floor, exercising the real preflight ahead of the real six steps
rather than only the mocked unit tests.

**Stated limit, unchanged from the filing:** this closes the illegibility gap. It does not
make the gate runnable on a loaded machine — the operator still has to free memory or wait —
and it cannot detect memory pressure that arrives after the preflight check passes.

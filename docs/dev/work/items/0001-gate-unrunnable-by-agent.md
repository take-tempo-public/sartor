```toml
schema = 1
id = 1
kind = "item"
title = "Quality gate unrunnable by an agent in one shot"
status = "closed"
decision_owner = "agent"
resolution = "2026-07-28, chore/work-item-tracking: root cause found (real ~30min runtime, no mystery kill); -n auto lands for the non-UX tier in scripts/gate.py, cutting it substantially; UX-tier flakiness confirmed as this project's pre-existing, CI-accepted (--reruns 2) characteristic, not a new problem, and deliberately left un-parallelized."
refs = ["docs/dev/RELEASE_CHECKLIST.md:784-843", "scripts/gate.py", "pyproject.toml"]
summary = "RESOLVED 2026-07-28: real runtime ~30min, not a mystery kill; -n auto lands for non-UX; UX flake confirmed pre-existing."
```

Migrated from `RELEASE_CHECKLIST.md`'s Carry-forward ledger (open since
2026-07-14). Full history preserved there; not restated here — see the ref.

Short version: `python -m scripts.gate` takes ~13 minutes; background Bash
calls get silently killed somewhere in the 5-10 minute range regardless of
which command runs (evidence points at an environment/session-wide event,
not a per-command timer). Every session hits this wall and either splits the
gate into manual chunks (works, but ad hoc) or risks rationalizing around a
partial run. PX-44's fixture-scoping rollout (`test/fixture-scoping-rollout`,
2026-07-27) is a partial, indirect mitigation (removes ~99% of per-test DB
setup on 46 files) but doesn't resolve the underlying per-command ceiling.

Candidate remedies from the ledger, all untested: `pytest-xdist -n auto`
parallelization (new dep, D-1 gate), resumable chunked gate tooling,
investigating the ~70s collection overhead.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, not new)

### 2026-07-28 — real cause found, on the same branch, after the owner pushed back on chunking as a workaround

Instrumented properly instead of guessing: ran the full suite via
`run_in_background` with a genuinely long timeout (600s cap, `-v --durations=0`),
instead of a short foreground/synchronous call. **It completed cleanly —
exit 0, 2233 passed / 1 skipped / 1 xfailed / 1 xpassed — no hang, no kill.**

**But it took 1820.8s (30m 20s).** The 2026-07-14 reference figure was 705s
(~13min) for 2066 tests. Test count grew ~8% (2066→2233); wall-clock grew
~158%. That gap, by itself, explains every prior "kill" observed across
sessions — a real ~30min runtime will always exceed any foreground call or
short explicit timeout, with no environment-wide silent-kill event required
as an explanation. The earlier chunked-batch attempts this session hit the
same thing for the same reason (one chunk happened to concentrate several
genuinely slow files near a 5-minute cap I set myself).

**Breakdown** (summed from the `--durations=0` output):
- UX/Playwright tier: 556.27s across 131 tests (~4.25s/test — inherently
  heavy, real browser automation, not surprising).
- Non-UX tier: 706.92s across 2105 tests (~0.34s/test average) — but this
  average hides one massive outlier.
- Pytest overhead (collection + setup/teardown + process startup, i.e. total
  wall-clock minus summed "call" time): ~557s, roughly 30% of the total.

**Single largest identified offender:** `tests/test_grounding_signals.py::
TestMinicheckLoaderHardening::test_forces_cpu_and_injects_offload_folder` —
**118.09s**, plus its sibling `test_load_minicheck_scorer_applies_hardening_
around_construction` at 21.35s (~140s combined, ~7.7% of total runtime, from
2 tests). The test class's own docstring says these tests "need the real
`transformers` package... but never download or run a model" — true in
spirit (no weights download), but `transformers.AutoModelForSeq2SeqLM` is
lazily resolved on first attribute access (`transformers/__init__.py`'s
`_LazyModule` system), and that resolution — which pulls in PyTorch — is
genuinely expensive on a cold run. Whichever test in the session first
touches that attribute pays the entire one-time tax; today that was this
test. `evals/grounding_signals.py`'s own top-level imports are confirmed
lightweight (`os`, `tempfile`, `contextlib`, `typing` only) — the cost is
`transformers`/`torch`'s import machinery, not this project's code.

This one outlier does not explain the full 2.6x regression by itself — the
remaining ~980s of growth is distributed across many more, individually
unremarkable tests (2105 non-UX tests today vs. 1974 previously), consistent
with organic test-suite growth over ~2 weeks of active development, not a
single new bug.

**What "solving" this actually looks like, given the evidence:**
1. **Workflow fix (proven to work today, zero cost):** always invoke the
   full gate via backgrounded execution with a realistic timeout (35-40min+,
   given the now-confirmed ~30min real runtime) instead of a foreground call
   or a short explicit timeout — this alone would have prevented every
   "killed" observation this item has ever recorded.
2. **Real optimization candidates**, not yet done: `pytest-xdist -n auto`
   parallelization (new dep, D-1 gate — real decision for the owner);
   isolating/pre-warming the transformers/torch import cost so it doesn't
   read as a false-hang signal on whichever test happens to trigger it first.
3. **Documentation fix, not yet done:** the ~13min figure in
   `RELEASE_CHECKLIST.md:784-843` and `AGENTS.md`/`CONTRIBUTING.md` (if cited
   there) is stale and should be corrected to the real ~30min number, so
   future sessions calibrate their own timeouts correctly instead of
   re-discovering this the same way.

A `-q` (no `-v`, no `--durations=0`) control run was also started, to check
whether verbose-output I/O itself inflated the 1820.8s figure — result not
yet in at the time of this note.

### 2026-07-28 — landed the fix, verified, closing

**`-n auto` (pytest-xdist) is safe and effective for the non-UX tier.**
Tested with `--ignore=tests/ux -n auto`: **2104 passed, 1 skipped, 437.13s**
— zero new failures against a clean baseline, roughly 40%+ faster than the
706.92s serial call-time alone. Added as a dependency (`pyproject.toml`,
`pytest-xdist>=3.5,<4.0`) and wired into `scripts/gate.py`'s pytest step,
split from the UX tier.

**`-n` parallelization is UNSAFE for the UX/Playwright tier — verified, not
assumed.** Tested `tests/ux -n 2`: 5 real failures, all timing/scroll-position
assertions or Playwright `wait_for_selector` timeouts — the exact CPU-
saturation flake class `docs/dev/diagnosis/ux-scroll-position-flake.md`
already diagnosed for the *serial* case, now directly reproduced under
concurrent load. `scripts/gate.py` deliberately keeps `pytest -m ux` serial,
unparallelized, per this evidence.

**Found and fixed an unrelated but real contributing factor along the way:**
two orphaned `python app.py` processes (a Werkzeug reloader parent/child
pair, PIDs 41468/21076) were still running in this project directory from
earlier in the session — the exact class carry-forward ledger item 20
already documented (an agent's own orphaned process causing a later,
unrelated test failure). Killed with owner confirmation; the specific
scroll-position test that had failed twice then passed 5/5 in isolated
repeat runs.

**Even fully isolated, the UX tier still produced one flake** (a different
test, `test_keyboard_reorder_persists_and_reset_reverts`, a plain Playwright
30s timeout) on a subsequent clean run. This is not a new problem: CI's own
data (`RELEASE_ARC.md`'s scroll-flake-ci-data note) already recorded ~42% of
real CI runs firing a rerun across this same test family, which is exactly
why the CI-specific `pytest -m ux --reruns 2` leg exists. `scripts/gate.py`'s
local step deliberately has no `--reruns` (strictness over convenience) — an
occasional single-test UX flake needing one local re-run is this project's
already-accepted trade-off, not something this item leaves unsolved.

**Bottom line:** the item's actual scope — "an agent cannot run the gate in
one shot" — is resolved. The gate is not unrunnable; it was unmeasured, and
the non-UX tier is now meaningfully faster. UX-tier flakiness is real,
pre-existing, already characterized, and out of this item's scope to fix
further.

# Diagnosis — the keyboard-reorder test's instrument waits on `networkidle` with no bound; production's identical wait is bounded

> **Status:** the failing line is **observed** (O-1). Phase A's A/B **reproduced the CI shape with
> an injected order and showed the bounded instrument passing it** (O-11, O-13): capability and
> mitigation shown, **not** that this order happened on any CI run. The cause of `networkidle`
> being withheld on CI is **not shown**, and this branch neither depends on nor claims it (the
> prior dossier's I-8 stays a hypothesis). The fix is shaped by the owner's 2026-10-15 pick: "Both, in
> sequence" — bound the instrument and add a visible stall signal (Phase A), measure the 5 s
> pre-drain stall (Phase B), replace the pre-drain only if Phase B shows a gain (Phase C, which
> needs the owner's go).
> **Branch:** `fix/reorder-networkidle-bound`
> **Item:** 30 (`docs/dev/work/items/0030-keyboard-reorder-load-state-timeout.md`).
> **Prior dossiers (cited, not restated):** `docs/dev/diagnosis/reorder-networkidle-empty-census.md`
> (O-1..O-20, I-8), `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md`.

---

## Symptom

`tests/ux/regression/test_20260604_bullet_drag_reorder.py::test_keyboard_reorder_persists_and_reset_reverts`
fails one CI attempt in about 3.3% of attempts (5 of 153, item 30 `## Updates` 2026-10-02) with
`TimeoutError: Timeout 30000ms exceeded.` and passes on the retry seconds later. Each one makes
`python -m scripts.ci_wait <n>` exit 3 and costs a re-push and about 7 minutes of CI.

---

## Observed

Read at `main` @ `18c5ce1` on this branch's base, 2026-10-15. Line cites are `path:line` at that
commit. Run ids are as recorded in item 30's `## Updates`; **this session re-read them from the
item file, not from the raw job logs** (C-12).

- **O-1. The instrument's `networkidle` wait has no timeout argument.**
  `tests/ux/regression/test_20260604_bullet_drag_reorder.py:303` reads
  `self.page.wait_for_load_state("networkidle")`, inside `_instrumented_wait_settled` (`:294`),
  which `:331` installs over `WizardComposePage._wait_settled` for that one test via
  `monkeypatch.setattr`. Playwright's default (30 s) therefore applies.
- **O-2. Production's wait on the same condition is bounded and swallowed.**
  `ui_pages/wizard_compose.py:25` `_NETWORKIDLE_PREDRAIN_MS = 5_000`;
  `ui_pages/wizard_compose.py:93-94`
  `with contextlib.suppress(PlaywrightTimeoutError): self.page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_PREDRAIN_MS)`;
  the settle gate follows at `:95` (`Compose.SETTLED`, `DEFAULT_TIMEOUT_MS`).
- **O-3. Three recorded failures since 2026-10-07 each went through the instrument's wait.**
  Runs `37669157358` (PR #160, 2026-10-07), `38310545397` (PR #166, 2026-10-12) and
  `38676437085` / job `116231042086` (PR #170, 2026-10-14): `:254` → `_wait_settled` →
  the test's `_instrumented_wait_settled` → `wait_for_load_state("networkidle")` →
  `TimeoutError: Timeout 30000ms exceeded.` (item 30 entries of those dates).
- **O-4. At those timeouts the settle condition already held and nothing was pending.**
  Run `38676437085`, the failing reach (item 30, 2026-10-14 entry, raw-log quote there):
  `reach: 9`, `elapsed_total_s: 30.044`, `cascade_state: {composeReady: True, bgPending: None,
  ..., previewFrameReadyState: 'complete'}`, `still_pending_requests: []`. `bgPending: None` is
  the attribute absent, which is the settled state (prior dossier O-4).
- **O-5. The line number the prior dossier gives for the instrument is stale at HEAD.** The
  prior dossier's O-1 and item 30's 2026-10-07 entry cite the instrument's wait at `:163`. At
  `18c5ce1` it is `:303` (O-1). Why they differ is **not** established here; the CI tracebacks
  were taken from runs whose file revision was not re-read. Cite O-1, not `:163`.
- **O-6. Consumers of the wait, derived (C-10).**
  `git grep -l "WizardComposePage" -- '*.py'` → **28 tracked files**: 24 under `tests/ux/`
  (`a11y` 1, `flows` 1, `regression` 22), `scripts/capture_screenshots.py`,
  `ui_pages/__init__.py`, `ui_pages/selectors.py`, `ui_pages/wizard_compose.py`.
  `git grep -n -E "_wait_settled|_NETWORKIDLE_PREDRAIN_MS" -- '*.py' ':!ui_pages/wizard_compose.py'`:
  direct `_wait_settled()` calls are `test_20260708_busy_states_and_chip.py:461,503,527,537` and
  `test_20260809_compose_wait_ux.py:262`; the only override is
  `test_20260604_bullet_drag_reorder.py:331`; `ui_pages/selectors.py:642,652` only mention it in
  comments. Inside `wizard_compose.py` the wait is reached from `:61,115,125,151,179,195,200,204,
  212,221,232`. `_NETWORKIDLE_PREDRAIN_MS` has **no** reader outside `wizard_compose.py` at HEAD.
- **O-7. The UX tier does not run under xdist.** `tests/ux/conftest.py:26-30` says so and holds
  `_rerun_counts` as a plain module global; `scripts/gate.py:99` runs `pytest -m ux` with no
  `-n`; `.github/workflows/ci.yml:231` runs `pytest -m ux --reruns 2 --reruns-delay 1`.
- **O-8. Two tools parse `[ux]` log lines.** `scripts/ci_wait.py:123` and
  `scripts/flake_rates.py:514` key on `[ux] RERUN`, `[ux] rerun-rate alarm` and
  `attempt(s) failed`. A new line must contain none of those.
- **O-9. The existing report-only summary hook is `tests/ux/conftest.py:78`
  `pytest_terminal_summary`**, which `del`s its arguments and never touches `exitstatus`
  (`:90-91`). A second hook of that name in the same module is not possible; the stall line goes
  inside it.

**Results of the pre-registered runs** (2026-10-15, this branch, local Windows, Playwright
1.60.0, one run per arm; every pytest invocation used `-p no:rerunfailures -o addopts=""`).
The injection plugin is a scratchpad file, no repo edit: before the Nth `has_custom_order` call it
awaits a same-origin `fetch` to completion, then appends a hidden `about:blank` iframe and awaits
its `load` (the P5 `fetch_then_commit` order).
**Deviation from the pre-registration:** the two arms ran in **separate** pytest processes (HEAD
arm before A1 was applied, FIXED arm after), not one process. A1 is a file change, not a toggle.

- **O-10. HEAD arm, plugin present, injection off (`AB_INJECT_NTH=0`)**, instrument as at
  `18c5ce1`: `1 passed in 37.10s`; `[ab-plugin] calls seen=4 nth=0`. The plugin alone changes
  nothing.
- **O-11. HEAD arm, injected before call #3 (`AB_INJECT_NTH=3`): the real test hangs and fails.**
  `[ab-plugin] injected before has_custom_order call #3 in 0.147s`, then
  `playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.`, `1 failed in 73.59s`. The
  instrument's record: `{'reach': 9, 'panel_visible_s': 0.019, 'exception':
  "TimeoutError('Timeout 30000ms exceeded.')", 'elapsed_total_s': 30.047, 'cascade_state':
  {'composeReady': True, 'bgPending': None, 'draftSummaryFiredForApp': 1, 'gapFillFiredForApp': 1,
  'composeApplicationId': 1, 'previewFrameReadyState': 'complete'}, 'still_pending_requests': [],
  'awaiting_body': [], 'failed_requests': []}`. Per-frame check: main frame `networkidle:
  NOT_REACHED`, `readyState: complete`; `livePreviewFrame`, `outputPreviewFrame`,
  `coverPreviewFrame` and `abInjectFrame` all `reached`. That is field-for-field the shape O-4
  records from CI, at reach 9 as in runs `38310545397` and `38676437085`. It shows the injected
  order **reproduces the symptom**; it does not show that the order occurred on any CI run.
- **O-12. FIXED arm (A1+A2 applied), injection off:** `1 passed in 15.04s`; 12 reaches,
  `networkidle_s` 0.010-0.795, `networkidle_timed_out: False` on every reach;
  `[ux] networkidle pre-drain: 0 stall(s) in 12 reach(es), 1.4 s waiting`. The pre-registered
  prediction (12 reaches, 0 stalls) held.
- **O-13. FIXED arm, injected before call #3: the test passes and the stall is recorded.**
  `1 passed in 23.08s`. Reach 9: `networkidle_s: 5.012, networkidle_timed_out: True`, with a
  `stall` capture attached; the settle gate then passed. `[ux] networkidle pre-drain: 2 stall(s)
  in 12 reach(es), 11.9 s waiting`, both stalls `5.0 s`, node id printed. **Not pre-registered:**
  reach 10 stalled too (`networkidle_s: 5.02`), and reach 11 recovered (`0.486`); reach 12 `0.011`.
  Not explained here. It is consistent with the prior dossier's recovery observation (O-16: a
  later main-frame request finishing re-arms it) and does not test it.
- **O-14. G1 guard, `tests/ux/regression/test_20261015_compose_predrain_bounded.py`.** Branch,
  no mutation: `1 passed in 14.21s`, `[ux] networkidle pre-drain: 1 stall(s) in 3 reach(es), 5.1 s
  waiting`, stalled `5.0 s`; the in-test control (`networkidle` raised within 1.5 s) held. Mutant
  (`MUT_PREDRAIN_MS=20000`, a scratchpad plugin swapping `ui_pages.wizard_compose.
  _NETWORKIDLE_PREDRAIN_MS`, log line `[mut-predrain] bound 5000 -> 20000`): `1 failed in 31.46s`,
  `AssertionError: _wait_settled took 20.1s with networkidle withheld; the pre-drain is no longer
  bounded (item 30)`. The guard is red under the mutation it exists for.
- **O-16. The tally counts deliberate stalls too.** A 14-test run of the three Compose settle
  files, the reorder file and G1 printed `[ux] networkidle pre-drain: 2 stall(s) in 31 reach(es),
  11.3 s waiting` (`14 passed in 93.47s`); both stalls were on purpose:
  `test_diagnostic_p1_stalled_live_preview_iframe_vs_compose_reload_networkidle` and G1. **Phase B's
  readout must exclude those two node ids**, or it overstates the stall rate.
- **O-17. Phase B, pass 1 (one pass, unloaded, local).** Every tracked UX test file that names
  `WizardComposePage` (25 files by `git grep -l WizardComposePage -- 'tests/ux/*.py'`; G1's file
  among them, G1 itself deselected), with `-k "not diagnostic and not predrain_stall"`,
  `-p no:rerunfailures -o addopts=""`. Result lines:
  `[ux] networkidle pre-drain: 0 stall(s) in 106 reach(es), 8.4 s waiting` and
  `66 passed, 9 deselected, 1 xfailed, 1 xpassed in 249.99s (0:04:09)`; marker
  `PHASEB_DONE tag=pass1 exit=0`. 0 failed, 0 rerun lines. The xfailed/xpassed pair is the known
  non-strict xfail pair, not touched here.
- **O-18. Phase B, looped arm: no data.** The unloaded 4-pass loop was stopped by the harness's
  memory-pressure reaper at about 52% of its first 288 test executions (the log's last progress
  line `....XXXxXXXX..................`, no terminal summary, so **no stall tally was printed**).
  The wrapper was killed but its pytest process and Playwright driver and browser children kept
  running; they were terminated by hand afterwards (`taskkill /T /F` on pid 22800, five processes
  reported terminated; free memory 2.66 -> 3.07 GB). The loop was **not** restarted. The CPU-loaded
  arm was never started. Nothing is inferred from the partial log.
- **O-15. The new summary line carries none of the keys the log parsers match** (O-8): the printed
  text is `[ux] networkidle pre-drain: <k> stall(s) in <n> reach(es), <s> s waiting` (O-12, O-13).
  Whether `ci_wait` and `flake_rates` ignore it was **not** run against a real job log.

---

## Falsified

- **F-1. This branch's own plan said "29 test files + `scripts/capture_screenshots.py` import
  `WizardComposePage`".** That figure was carried from an earlier session's count, not derived.
  The derivation (O-6) gives 28 files in total, 24 of them tests. Corrected here before it
  reached any other document.
- **F-2. The approved plan said `ui_pages/base.py` is "a gated surface, `blast_radius.py:207`".**
  False: `:207` is the considered-and-not-gated list, and its rationale says gating the page-object
  base "would block writes it can never usefully guard" because `tests/**` is exempt. Only
  `ui_pages/selectors.py` is gated (`:141-145`). Found by reading the file before this dossier was
  committed. It changes Phase C's candidate sites only in that a `base.py` edit needs no
  blast-radius dossier; a `selectors.py` edit still would.

---

## Inferred

**Every entry below is a hypothesis, not a finding.**

- **I-1. Bounding the instrument's wait removes the recorded 30 s failure, whatever withholds
  `networkidle`.** It follows from O-1 (the raise is at the unbounded line), O-2 (production
  already behaves that way without failing) and O-4 (`Compose.SETTLED` already held at the
  timeout, so the next wait would pass at once). **Not observed:** no failing CI attempt has been
  re-run against the bounded instrument. The A/B below is the test of it.
- **I-2. The stall is not specific to this test.** If `networkidle` is withheld by the
  Playwright-internal ordering gap (prior dossier I-8, itself unproven), production's bounded wait
  would cost 5 s on every reach where it happens, silently. Phase B measures it; until then this
  is a guess.
- **I-3. The 5 s the pre-drain costs when it stalls buys nothing**, because the marker plus
  counter is the real settle gate (`wizard_compose.py:63-95` docstring). The history says
  otherwise could be true in a different state: `reference-ux-compose-ready-wait` records that
  the marker cannot see a recommend POST not yet issued, which is why the pre-drain exists. Phase
  C must be A/B'd against that, not assumed.

---

## Falsification

**Pre-registered here, before any of it runs.** Each says what each outcome means.

### G1 — a guard test on production's `_wait_settled` (deterministic, no race)

A new committed UX test reaches Compose, then forces `networkidle` to be withheld
**deterministically** rather than through the order bug: a loopback server that sends headers and
holds the body (the `_HeldBodyServer` from the same test file, prior dossier O-18), a same-origin
page `fetch` to it, then a hidden `about:blank` iframe commit (the P3 isolated stages
`held` → `held_then_commit`, prior dossier O-18: `(True, 8.033)` with nothing in the old census).
Then:
- **Control (void if it fails):** a direct `page.wait_for_load_state("networkidle",
  timeout=1500)` **raises** `PlaywrightTimeoutError`, so `networkidle` really is withheld.
- **Subject:** `WizardComposePage._wait_settled()` returns without raising, in under a **hard-coded
  10 s** (not derived from `_NETWORKIDLE_PREDRAIN_MS`, so a mutation of that constant cannot move
  the assertion with it).
- **If it passes on HEAD:** expected; production is already bounded (O-2). The test is a
  tripwire, not a repro: it has to **fail** under the mutation below to be worth committing.
- **Mutation check (scratchpad plugin, no repo edit):** set
  `ui_pages.wizard_compose._NETWORKIDLE_PREDRAIN_MS = 60_000` before the test body.
  **Predicted:** the subject fails (the wait runs past 10 s, or the test's own bound trips).
  If it still passes, the guard is decorative and is not committed as a guard.
- **Known limit:** it guards production's `_wait_settled`, not the instrument. The instrument is
  guarded only by sharing the constant (A1 below).

### A/B — the real test, with the hang state injected before one reach

A scratchpad plugin (`mut_plugin` shape, memory
`reference-pytest-in-process-loop-and-mutation-plugins`; **no repo edit**) wraps
`WizardComposePage.has_custom_order` for its Nth call: a same-origin `fetch` is awaited to
completion, then a hidden iframe is appended and awaited to `load` (the P5 `fetch_then_commit`
order, prior dossier O-17), and then the original runs, reaching `_wait_settled`.
- **Arm HEAD** (instrument as at `18c5ce1`): **predicted** to fail with `TimeoutError` at about
  30 s inside `_instrumented_wait_settled`, with `still_pending_requests: []` in the dump.
- **Arm FIXED** (A1 applied): **predicted** to pass; that reach's record shows
  `networkidle_timed_out: True` and `networkidle_s` of about 5.
- **If arm HEAD does not hang:** the injection did not reproduce the CI shape on the Compose page.
  The A/B is **void**, and the result is recorded as exactly that: I-1 stays untested, and no
  claim is made from arm FIXED passing.
- **If arm FIXED fails:** I-1 is false for the injected shape; stop and report, do not widen the
  fix.
- Both arms run in one process with the in-process loop plugin, `-p no:rerunfailures`, so a retry
  cannot turn a failure into a bare `PASSED`.

### A2 — the stall signal (report-only, C-11 declared)

`_wait_settled` records `(elapsed_s, timed_out)` per reach; the instrument records into the same
list; `tests/ux/conftest.py::pytest_terminal_summary` prints one line, `[ux] networkidle
pre-drain: <k> stall(s) in <n> reach(es), <s> s waiting` plus the node ids. **Unenforced by
design:** a stall is not a failure, so nothing fails closed on it, and `ci_wait` / `flake_rates`
do not read it (O-8 is why the wording avoids their keys). It exists so the cost the bound hides
from those two tools stays visible in the job log.
- **Prediction on an ordinary local run of the reorder test:** 12 reaches (prior dossier O-11
  recorded 12 on one run), 0 stalls. A different count is recorded, not explained away.

### Phase B — measure the stall (decides Phase C)

Every `WizardComposePage` consumer (O-6), `pytest -m ux`, in-process loop for N iterations sized
from one measured pass, `-p no:rerunfailures`, one arm under about 0.75× cores of CPU load
(`reference-cpu-saturation-flake-repro`); the A2 line is the readout. **The decision gate is the
owner's:** the stall rate per reach, seconds per UX run, and whether any stall occurred outside
the reorder test. A rate of zero is recorded as a result and closes the branch after Phase A.
Phase C is not designed in detail until those numbers exist.

**Where Phase B stands (O-17, O-18):** one pass, 0 stalls in 106 reaches. The loop and the loaded
arm did not produce data. One pass at the per-attempt rate item 30 measured for a *failure* (3.3%)
has a good chance of showing nothing even if the stall is real, and 106 reaches are not 106
independent chances at the specific reach-9-shaped event. This is a datum, not a finding that the
stall does not occur. The remaining sources are the PR's own CI UX jobs (they print the line; no
local memory cost) and a local re-run, which is the owner's call given the memory reaper.

---

## Consumers

**Surface:** `ui_pages/wizard_compose.py::WizardComposePage._wait_settled` and
`_NETWORKIDLE_PREDRAIN_MS`. Not a gated surface: `ui_pages/wizard_compose.py` has no entry in
`scripts/enforcement/blast_radius.py`. (`ui_pages/selectors.py` is gated, `:141-145`;
`ui_pages/base.py` is on the explicit considered-and-not-gated list, `:207-210`. This branch
edits neither.) So this section is a recorded enumeration, not a hook requirement. The derived
set is O-6.

| Site | What it does with the surface | Decision |
|---|---|---|
| `wizard_compose.py:61,115,125,151,179,195,200,204,212,221,232` | calls `_wait_settled` | A2 adds a recorder append inside it; no signature change |
| `test_20260604_bullet_drag_reorder.py:294-331` | overrides it for one test | A1: bound + record; imports the constant |
| `test_20260708_busy_states_and_chip.py:461,503,527,537`, `test_20260809_compose_wait_ux.py:262` | call it directly | none; same behaviour |
| the 21 other `WizardComposePage` test files (24 minus the three rows above) | reach it via the POM | none |
| `scripts/capture_screenshots.py` | uses the POM | none; recorder append only |
| `tests/ux/conftest.py:78` | summary hook | A2 prints the line here |

## Deferred

- Phase C (replace the pre-drain): not started; needs Phase B's numbers and the owner's go.
- Teaching `ci_wait` / `flake_rates` to read the A2 line: not in scope; owner's call. Until then
  the bounded stall is visible in the log and invisible to both counters (declared, not hidden).
- The P3/P4/P5 probe tests' keep-or-remove question (item 30): owner's, untouched here.

---

## The fix

Phase A, landed in the commit after the one that committed this dossier's `## Observed` and
predictions (C-7):

- **A1.** `ui_pages/wizard_compose.py::predrain_networkidle(page)` is the one definition of the
  bounded, swallowed `networkidle` wait. `_wait_settled` calls it (replacing the inline
  `contextlib.suppress`), and so does the keyboard-reorder test's `_instrumented_wait_settled`
  (replacing the unbounded wait at the old `:303`), so the two cannot drift. On a stall the
  instrument takes the same wide capture its exception path takes and prints it, then lets the
  settle gate run.
- **A2.** `PREDRAIN` (a small tally) records reaches, seconds waited and each stall's node id;
  `tests/ux/conftest.py::_report_predrain_stalls`, called from the existing
  `pytest_terminal_summary`, prints one `[ux] networkidle pre-drain:` line per run, including at
  zero stalls. **Report-only and unenforced (C-11, declared):** a stall is not a failure.
- **G1.** `tests/ux/regression/test_20261015_compose_predrain_bounded.py`, the fail-closed guard.

This is the Phase A fix, not the whole of what the owner chose. Phase B (measure) and the Phase C
decision are open. Nothing here changes what the pre-drain waits for, so it does not touch the
history in `reference-ux-compose-ready-wait`.

---

## Acceptance bar

For this branch: G1 fails under its mutation and passes on the branch; the A/B arms report what
`## Falsification` predicted or are recorded as void; the A2 line appears in a local `pytest -m
ux` run. For **item 30**: stays `watching` unless a falsifiable `verified_by` exists **and**
`python -m scripts.ci_wait <n>` exits 0 on this PR with 0 `RERUN` markers on the reorder test
(C-7, C-11). One clean CI run against a 3.3% per-attempt base rate is not evidence the flake is
gone (a single attempt passes about 96.7% of the time with no change); the deterministic guard
and the A/B are what carry the claim, and only for the mechanism they exercise.

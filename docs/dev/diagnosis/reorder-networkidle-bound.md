# Diagnosis — the keyboard-reorder test's instrument waits on `networkidle` with no bound; production's identical wait is bounded

> **Status:** the failing line is **observed**; that bounding it removes the recorded failure is
> **inferred** (I-1) and is what Phase A's A/B exists to test. The cause of `networkidle` being
> withheld on CI is **not shown**, and this branch neither depends on nor claims it (the prior
> dossier's I-8 stays a hypothesis). The fix is shaped by the owner's 2026-10-15 pick: "Both, in
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

Not written yet. A1 and A2 land in the second commit, after this dossier's `## Observed` is
committed (C-7) and the G1/A-B predictions above are on record.

---

## Acceptance bar

For this branch: G1 fails under its mutation and passes on the branch; the A/B arms report what
`## Falsification` predicted or are recorded as void; the A2 line appears in a local `pytest -m
ux` run. For **item 30**: stays `watching` unless a falsifiable `verified_by` exists **and**
`python -m scripts.ci_wait <n>` exits 0 on this PR with 0 `RERUN` markers on the reorder test
(C-7, C-11). One clean CI run against a 3.3% per-attempt base rate is not evidence the flake is
gone (a single attempt passes about 96.7% of the time with no change); the deterministic guard
and the A/B are what carry the claim, and only for the mechanism they exercise.

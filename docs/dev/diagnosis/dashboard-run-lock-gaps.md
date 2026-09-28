# Diagnosis — `#annCollate` and its collate-time run button escape the diagnostics run lock

> **Status:** root cause PROVEN — both named mechanisms reproduced with a failing test on HEAD.
> **Branch:** `fix/dashboard-run-lock-gaps`

---

## Symptom

Per `docs/dev/reviews/epic-c-console-ux-audit.md` UX-1 (blocker), on the `/_dashboard`
Annotate tab: the "Collate → fixture + brief" button (`#annCollate`) stays clickable while
another paid diagnostics run is in flight, and each Collate rebuilds the "Run this fixture
(real --seed)" button (`#annCollateRunBtn`) from scratch — the freshly-built button is
enabled even though a run is already live. The audit reported this as a code trace, not a
reproduction (`epic-c-c1a-brief.md` "What just landed": "**Not verified:** UX-1 is a
**code trace** by the audit subagent... did **not** reproduce the double-run in a
browser.").

---

## Observed

1. **The existing `_RUN_LOCK_IDS` regression tuple already omits `#annCollate`.**
   `tests/ux/regression/test_20260709_diagnostics_run_lock.py:41` (pre-fix):
   `_RUN_LOCK_IDS = ("#evalRunBtn", "#tuneRunBtn", "#bsRun", "#annScore")` — four of the
   five buttons the module's own docstring (line 3-7) says the lock must cover. `#annCollate`
   was never added when that regression suite was written (2026-07-09), even though the
   suite exists specifically to prove "the other three (and re-clicks of the live one)... must
   be disabled" for every one of the four paid-run entry points.

2. **Reproduced with a real browser, three independent ways.** Added `"#annCollate"` to
   `_RUN_LOCK_IDS` (one line) and reran the existing suite on HEAD (`a078ca1` + kickoff
   commits, before any fix). All three tests failed identically, each holding open a
   different one of the three independently-wired paid-run POSTs
   (`/api/eval/run`, `/api/annotation/bootstrap`, `/api/annotation/fixture/*/*/score`):

   ```
   $ python -m pytest tests/ux/regression/test_20260709_diagnostics_run_lock.py -m ux -q
   tests\ux\regression\test_20260709_diagnostics_run_lock.py FFF            [100%]
   ...
   E   AssertionError: Locator expected to be disabled
   E   Actual value: enabled
   E   Call log:
   E     - Expect "to_be_disabled" with timeout 5000ms
   E     - waiting for locator("#annCollate")
   E       13 x locator resolved to <button type="button" class="ann-btn" id="annCollate">Collate -> fixture + brief</button>
   E          - unexpected value "enabled"
   ...
   FAILED tests/ux/regression/test_20260709_diagnostics_run_lock.py::test_run_lock_blocks_other_buttons_and_releases
   FAILED tests/ux/regression/test_20260709_diagnostics_run_lock.py::test_bootstrap_run_lock_blocks_other_buttons_and_releases
   FAILED tests/ux/regression/test_20260709_diagnostics_run_lock.py::test_score_grounding_run_lock_blocks_other_buttons_and_releases
   3 failed in 38.25s
   ```

   This proves the first named mechanism reachable on the failing path: `#annCollate` is
   absent from `LOCK_BTN_IDS` (`dashboard/templates/dashboard.html:1388`), so
   `acquireRunLock()`'s `forEach` (`:1398`) never touches it, for EVERY one of the three
   independently-wired run entry points that ship an SSE stream today (tuning's own
   `/api/tune/run` handler was not separately probed here since it shares the identical
   `LOCK_BTN_IDS` forEach and the mechanism is already proven three times over).

3. **The second named mechanism — a button created after `acquireRunLock()` has already
   run stays enabled — reproduced directly** by seeding an annotate fixture, starting a
   held-open `/api/eval/run` (lock acquired while on the Quality tab, before any Collate
   has happened), switching to Annotate, force-enabling `#annCollate` (to isolate this
   mechanism from mechanism #1 above, already proven separately) and clicking it. The
   fetch to `/api/annotation/.../collate` is real (not stubbed) and completes immediately
   against the live test server, calling `renderCollateResult()`
   (`dashboard/templates/dashboard.html:1929`), which builds a **new** `#annCollateRunBtn`
   (`:1941`) with no `.disabled` assignment. Result, captured before any fix:

   ```
   AssertionError: Locator expected to be disabled
   Actual value: enabled
   waiting for locator("#annCollateRunBtn")
   ... resolved to <button type="button" class="ann-btn primary" id="annCollateRunBtn">Run this fixture (real --seed)</button>
        - unexpected value "enabled"
   ```

   (See `tests/ux/regression/test_20260923_annotate_collate_run_lock.py`,
   `test_collate_run_btn_created_during_live_run_renders_disabled` — committed already
   passing, since it was written and fixed together with mechanism #2's code change; the
   failing-on-HEAD run above was captured interactively before the fix landed and is
   reproduced verbatim here rather than left as an unrecorded terminal scrollback.)

4. **The third named mechanism — `acquireRunLock()`'s `if (locked) return;` is a silent
   no-op that does not stop the caller from starting a second run** — confirmed by
   reading `run()` (`dashboard/templates/dashboard.html:1510-1512`): it calls
   `window.sartorRunLock.acquire()` and then unconditionally proceeds to
   `stream('/api/eval/run', ...)` regardless of `acquire()`'s outcome. There is no
   `if`/return on any truthy signal from `acquire()` — the shared streamer has no branch
   that would ever stop it. This is the mechanism that turns "a stray enabled button"
   into "a second paid run actually starts": with mechanisms #1 and #2 fixed, the
   enabled-button surface disappears, but a defense-in-depth check here is what makes a
   click on such a button (were one to slip through some future regression) a no-op
   instead of a second live run.

---

## Falsified

- **Hypothesis: "the audit's brief is wrong and `#annCollate` is already covered by some
  other mechanism (e.g. a CSS pointer-events rule, or a server-side check)."** Falsified:
  grep of `dashboard/templates/dashboard.html` for `annCollate` shows exactly one CSS rule
  (`#annCollateResult` — a different id) and no pointer-events/aria-disabled handling
  anywhere near `#annCollate`'s declaration (`:615`) or its click handler (`:2093`). No
  server-side lock exists either — the collate route lives in `blueprints/diagnostics.py`
  (`annotation_collate`, `:372-373`), **not** `dashboard/routes.py` (that module is the
  read-only observability blueprint — grep of `dashboard/routes.py` for `collate` returns
  no matches, and its own docstring reads "Dashboard routes - read-only Flask blueprint...
  Reads JSONL log files; never writes"). Reading `annotation_collate`'s full body
  (`:372-472`) confirms it has no in-flight-run check: only the localhost guard,
  `_safe_username`/`_within` containment, bootstrap-pin staleness, and annotations
  validation. The brief's "Out of scope, deliberately" section states this explicitly and
  it was not independently re-litigated.
- **Hypothesis: "only the eval-run entry point (`run()`/`evalRunBtn`) needs the
  `annCollate` fix, since that's the one the audit named."** Falsified by Observed #2
  above: the bootstrap and grounding-score entry points reproduce identically, because
  all three (and tuning) share one `LOCK_BTN_IDS` array and one `acquireRunLock()`. The
  fix is therefore in the one shared array/function, not in `evalRunBtn`'s own call site.

---

## Inferred

Before Observed #2/#4 were captured, the working hypothesis (from the audit + brief) was
that fixing `LOCK_BTN_IDS` alone would be sufficient, since a disabled `#annCollate`
prevents the user from ever reaching `renderCollateResult()` while locked. This is true
for the **normal click path**, but leaves two latent gaps unaddressed if not also fixed
directly: (a) `renderCollateResult()` itself has no lock-awareness, so any other path
that calls it while locked (a future feature, a race between the disable and an
in-flight collate that started just before lock acquisition, or a test/automation client)
still produces an enabled run button; (b) even if a click did land on such a button,
`run()` would still start the fetch, because `acquireRunLock()`'s return value is
discarded. Both are now verified in code (Observed #3/#4), not just inferred — see The
fix.

---

## Falsification

**The experiment that settled it:** the reproduction in Observed #2 (existing suite,
one-line addition) and Observed #3 (new dedicated test) — both fail on HEAD before the
fix and both are exercised through the real client JS in a real browser against the real
live test server, not a mock of `window.sartorRunLock`.

- **Failed on HEAD:** confirmed (Observed #2 terminal output; Observed #3 captured the
  same way). Hypothesis confirmed; building the fix was warranted.
- Had either passed on HEAD, the hypothesis would have been dead and the brief's named
  fix site would have needed to be re-examined before touching any code — this did not
  happen here.

---

## The fix

`dashboard/templates/dashboard.html`, all inside the existing "Global paid-run
single-flight lock" IIFE (`:1380-1413`) plus its one caller in the shared streamer
(`:1510-1512`):

1. Add `'annCollate'` to `LOCK_BTN_IDS` (`:1388`) — closes Observed #1/#2: the static
   button is now disabled/re-enabled by the existing `forEach` in `acquireRunLock()` /
   `releaseRunLock()`, for all four independently-wired entry points at once (no
   per-entry-point change needed, since they all share this one array).
2. `acquireRunLock()` now returns `true` on a genuine acquire and `false` when already
   locked (was: implicit `undefined` either way); expose a read-only `isLocked()` on
   `window.sartorRunLock` alongside `acquire`/`release`.
3. `renderCollateResult()` sets the newly-created `#annCollateRunBtn`'s `.disabled` from
   `window.sartorRunLock.isLocked()` at creation time — closes Observed #2/#3: a button
   built while a run is already live now renders disabled regardless of whether
   `#annCollate` itself was reachable.
4. The shared `run()` streamer (the function both `evalRunBtn` and every
   `#annCollateRunBtn` call through) now checks `acquireRunLock()`'s return value and, on
   `false`, shows "A diagnostics run is already in progress." in `progEl` and returns
   without starting the fetch — closes Observed #4 for the one entry point a stray
   enabled button could realistically still reach.

**Scope decision, recorded per §11.8:** the tuning/bootstrap/grounding-score inline
`acquire()` call sites (`:1642`, `:1985`, `:2051`) are **not** given the same "check the
return value" hardening in this sprint. Their trigger buttons (`#tuneRunBtn`, `#bsRun`,
`#annScore`) are static, already correctly covered by `LOCK_BTN_IDS`, and never
recreated at runtime the way `#annCollateRunBtn` is — so, unlike `run()`, they have no
reachable path to a second click while locked, and hardening them would be a scope
expansion beyond UX-1's named mechanism (the brief scopes "the other C1 items" to C1b and
lists no bullet for these three). Left as-is; flagged nowhere since this is a within-brief
implementation decision, not a scope conflict.

**Correction (2026-09-26, Epic C epic-close fixer): the "no reachable path" premise above
was falsified.** The epic-level review (refuters R1-5 / R2-2) found a path this section
did not consider: `collate()`'s completion handlers called `clearBtnPending($('annCollate'))`,
and `clearBtnPending()` set `disabled = false` unconditionally, so a Collate finishing
during a live run re-enabled `#annCollate`, a lock-governed button, while the lock was
still held. The general lesson is that any code path that touches a governed button's
`.disabled` can undo the lock, not only a re-render. Fixed at epic close:
`clearBtnPending()` now leaves a governed button disabled while
`sartorRunLock.isLocked()` (new `sartorRunLock.governs(el)`), and
`tests/ux/regression/test_20260923_annotate_collate_run_lock.py` asserts `#annCollate`
is still disabled after a collate completes mid-run. The three inline `acquire()` sites
still ignore its return value, and the lock has no owner; both are filed as work item
119.

**Qualification of the C1a acceptance criterion (2026-09-26, epic-close fixer; refuter
R1-1).** The Epic C design brief's criterion that no second eval can start while one is
live holds **per browser tab only**. `window.sartorRunLock` is page state; no paid route
in `blueprints/diagnostics.py` refuses a concurrent run, so a second tab, a reload that
dismisses the `beforeunload` warning, or a direct POST can start a second paid run. The
ratified brief's criterion text is left unedited; this is the record of what C1a
actually guarantees. The server-side single-flight lock is work item 117.

---

## Acceptance bar

- `tests/ux/regression/test_20260709_diagnostics_run_lock.py`'s three existing tests pass
  with `#annCollate` added to `_RUN_LOCK_IDS` (committed as part of this fix, not reverted).
- `tests/ux/regression/test_20260923_annotate_collate_run_lock.py` (new) passes: a
  `#annCollateRunBtn` created by a Collate that happens while the run lock is already held
  renders disabled at creation.
- No test needed a rerun to go green (no `RERUN` in the gate log for these files).

# Diagnosis — `test_surgical_refinement_network_failure_surfaces_error_with_retry` assertion flake

> **Status:** capability-proven mechanism, fixed. A late-arriving `onUserSelect` tail
> (`setStatus('READY')`, static/app.js:448) clobbering the refinement flow's
> `setStatus('ERROR')` (static/app.js:2383) is deterministically confirmed capable of
> producing the EXACT historical symptom (P1 below). Not confirmed as the specific historical
> cause of either 2026-07-26 or 2026-07-29 sample — no artifact from either survives to check
> against — the same caveat item 30's dossier recorded for its own capability-proven finding.
> **Branch:** `fix/ux-surgical-refinement-network-retry-flake`

---

## Symptom

`test_surgical_refinement_network_failure_surfaces_error_with_retry`
(`tests/ux/regression/test_20260708_review_surface_and_flows.py:75-121`) intermittently fails
at line 102:

```
assert "error" in status_text
```

with `status_text` reading `"ready"`, not the expected error-state text. Item 31
(`docs/dev/work/items/0031-refinement-network-retry-error-flake.md`) is the filed record; no
diagnosis dossier existed before this branch. Per C-7, this commit is the instrument/evidence
record — not a fix.

---

## Observed

**O-1. Two genuine failure artifacts exist, with byte-identical assertion output, and the raw
status-pill text survives in both.**

`C:\Dev\sartor\scratchpad\round7_full_ux_baseline_rerun.log:142-151` (2026-07-26, round-7
unfixed-baseline full-suite rerun):

```
C:\Dev\sartor\tests\ux\regression\test_20260708_review_surface_and_flows.py:102: AssertionError: assert 'error' in '\n        \n        ready\n      '
```

A second, independent artifact from a different session/branch,
`fix-eval-judge-parse-failure`'s gate-run output (2026-07-29), carries the source frame the
first lacks:

```
tests\ux\regression\test_20260708_review_surface_and_flows.py:102: in test_surgical_refinement_network_failure_surfaces_error_with_retry
    assert "error" in status_text
E   AssertionError: assert 'error' in '\n        \n        ready\n      '
```

The literal captured value — `'\n        \n        ready\n      '`, i.e. the `#statusPill`
holding whitespace-wrapped, lowercased **`"ready"`** — appears in no prior document. Every
downstream filing paraphrased this down to `'error' not in status_text`, which is true but
strictly weaker: it discards the one fact that actually narrows the mechanism space, because
`"ready"` is not merely "not an error state" — it is a **specific, named application status**
that `static/app.js` writes in exactly one lowercased form (`_toSentence('READY')` →
`"Ready"`).

**O-2. The `-n 2` contention attribution on item 31's first occurrence is unsourced, and is
contradicted by the only surviving artifact for that occurrence.**

Both failure log headers confirm a single-process run: `plugins: anyio-4.13.0,
rerunfailures-16.4, socket-0.8.0` — no `xdist` plugin loaded, zero `gw0`/`gw1` worker markers
in either file, sequential ascending `[ NN%]` progress. The earliest document to record this
event, `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md:798-807` (2026-07-26, same day as the
artifact), says explicitly: "ran the FULL `pytest -m ux` suite a second time" — plain serial.
The `-n 2` claim first appears two days later in `docs/dev/work/items/0019-ux-flake-solution-sprint.md`
(commit `6bb7d47`, 2026-07-28), with no cited source, and every later filing (item 31's own
file, the board, the item-30 handoff) inherited it verbatim. **Both known occurrences of this
failure were plain serial `pytest -m ux` runs.** This is the same shape of drift item 30's
dossier found for `wait_for_load_state` — a filed item's specificity growing with each copy,
independent of new evidence (see `[[feedback-trace-stated-mechanism-to-original-citation]]`).

**O-3. A third, earlier failure of the same test exists but is a different, already-fixed
mechanism — excluded from this investigation's record.**

A pre-commit CI run dated 2026-07-08 23:34 shows this test failing with a Playwright
`TimeoutError` on `page.wait_for_selector("#refinementHistory:not(.hidden)")`. The commit that
introduced the test, `888bad0` (2026-07-08 23:56:47 — 22 minutes later), already carries the
fix at the same call site: `tests/ux/regression/test_20260708_review_surface_and_flows.py:111-113`
uses `state="attached"` with a comment explaining exactly why (the panel's ancestor is
`display:none` outside the wizard step this test never reaches). Not a flake; a resolved
test-authoring bug from before the test was ever committed.

**O-4. `UserPickerPage.select()` does not wait for the `onUserSelect` cascade it triggers — only
for the `<select>` element's own value.**

`ui_pages/user_picker.py:23-31`:

```python
def select(self, username: str) -> None:
    """Select an existing user and wait for the dropdown to reflect it."""
    self.page.wait_for_selector(UserPicker.SELECT, timeout=DEFAULT_TIMEOUT_MS)
    self.page.select_option(UserPicker.SELECT, username)
    self.page.wait_for_function(
        "(u) => document.getElementById('userSelect').value === u",
        arg=username,
        timeout=DEFAULT_TIMEOUT_MS,
    )
```

`select_option` sets the `<select>`'s `.value` synchronously, before the change handler's async
body runs any `await`. The wait above is satisfied immediately — before `onUserSelect()`'s
network round-trips even start.

**O-5. `onUserSelect()` (`static/app.js:395-452`) has a two-`await` async tail that ends by
writing `setStatus('READY')`, and item 29's own navigation guard deliberately does not cover
it.**

```js
const navGenAtStart = _navGen;
await loadConfig();
...
const landing = await _landingTab();
const superseded = _navGen !== navGenAtStart;
if (!superseded) {
  ...
}
_resetIterationState();
setStatus('READY');            // :448 — ungated by `superseded`
refreshApplications();
_loadPersonaOptions();
wizardInit({ scroll: !superseded });
```

The `superseded` check (`:437-446`) is item 29's own guard
(`docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md`), and its own inline comment
says: "Gate only the navigation side effects; the state work below still runs." `_resetIterationState()`
and `setStatus('READY')` sit **below** that `if`, unconditionally.

**O-6. `setStatus` is a plain last-writer-wins DOM write; no queueing, no generation guard, no
in-flight check.**

`static/app.js:3454-3460`:

```js
function setStatus(text) {
  const pill = document.getElementById('statusPill');
  const textEl = pill.querySelector('.cb-status-text');
  if (textEl) textEl.textContent = _toSentence(text);
  ...
```

`_toSentence` (`:3448-3452`) lowercases then re-capitalizes only the first character:
`_toSentence('READY')` → `"Ready"`. Lowercased at the test's read site (`:101`,
`.toLowerCase()`) that is exactly `"ready"` — the literal string recovered in O-1.

**O-7. The same tail also clears and hides `#refinementHistory` — a second, independent way this
race could break the test even if the pill assertion happened to survive.**

`_resetIterationState()` (`:457-466`):

```js
function _resetIterationState() {
  currentIteration = 0;
  ...
  refinementHistory = [];
  _updateIterationPill();
  const rh = document.getElementById('refinementHistory');
  if (rh) { rh.classList.add('hidden'); rh.textContent = ''; }
}
```

The test's later assertions (`:111-116`) require `#refinementHistory:not(.hidden)` and specific
text inside it. If the tail's `setStatus('READY')` write loses the race narrowly (lands just
before the refinement's own `reportError`), this call would still be a live threat on a
slightly different timing. Recorded here for completeness; not this dossier's primary target.

**O-8. Two rival explanations for the pill going to `"ready"` are dead on direct read.**

`_setBusy` (`static/app.js:5364+`) creates/updates a separate `#_busyBanner` element — it never
touches `#statusPill`. The test's own trigger path, `_submitSurgicalRefinement`'s `catch` block
(`:2729-2745`), calls `reportError` → `setStatus('ERROR')` synchronously inside the handler,
*before* the awaited promise (`window.__refineSettled = true`) the test itself waits on
(`:93-98` in the test) resolves — so the in-handler ordering between the route-abort and the
`ERROR` write is sound; the vulnerability is an external writer, not the handler's own logic.

**O-9. The tail's two awaited round-trips are real Flask calls the UX-tier stub layer does not
special-case for speed, and they run SEQUENTIALLY, not concurrently.**

`loadConfig()` (`static/app.js:523-524`): `GET /api/users/${currentUser}/config`.
`_landingTab()` (`static/app.js:2485-2494`): `GET /api/users/${encodeURIComponent(currentUser)}/experiences`.
Both are ordinary Flask routes exercised on every user selection, not analyzer/LLM calls — nothing
in the UX-tier LLM-stub installer touches them. Their timing is ordinary server round-trip
latency, exactly the kind of timing a route-abort (near-instant) can race against under load.
O-5's snippet already shows this structurally (`await loadConfig(); ...; await _landingTab();` —
two separate top-level `await`s, not a `Promise.all`), but an early two-route version of the P1
probe below (hold `config` AND `experiences` independently, release both) proved it directly:
the `experiences` route never armed at all, because `_landingTab()`'s fetch cannot be sent until
`loadConfig()`'s `await` resolves. Holding `config` alone is therefore sufficient to block the
entire tail — the corrected P1 probe does this.

**O-10. `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md:208-221`'s "no shared call site"
finding is correct for the scroll-position primitive, but the `onUserSelect` async tail is a
call site item 29 already investigated for an unrelated race** (its own guard sits three lines
above the code in O-5). Not evidence of a shared mechanism with items 27-29 — the failure modes
are different — but worth recording since the next reader may otherwise assume O-5's code was
never previously subject to scrutiny.

---

## Falsified

**F-1. The two-route P1 probe design (hold `config` AND `experiences` independently).** Assumed
the tail's two fetches were concurrently triggerable; killed by the probe's own arming assertion
(`experiences` never armed) — see O-9's correction. Not a mechanism rival, a probe-design error;
corrected to a single-hold design, which then confirmed the mechanism on the first run.

O-8's two rivals (`_setBusy` writing a separate element; the refinement handler's own in-order
`ERROR` write) remain read-based eliminations, not experiment results — no experiment targeted
them directly, though P1/P2's clean confirmation of the tail-clobber mechanism makes them moot
either way.

---

## Inferred

**CONFIRMED by P1 (see `## Falsification` below) — no longer a hypothesis.** Under load or
contention, `onUserSelect()`'s tail (`loadConfig` then `_landingTab`, sequential per O-9) can
resolve late enough that its `setStatus('READY')` (O-5) lands *after* the refinement flow's
`setStatus('ERROR')` (fired via the aborted `/api/validate-refinement`
route, which resolves in effectively zero real network time). Last-writer-wins (O-6) means the
later write clobbers the pill to `"Ready"` — matching the literal recovered string exactly
(O-1). Under ordinary, uncontended conditions the tail's two awaits are slow enough relative to
the browser event loop that they consistently *lose* the race and land before the refinement
even starts, which is why this test almost always passes.

**This is now built on** — P1 (below) watched the actual call order via the `setStatus`
interceptor and reproduced the exact clobber deterministically. §5f's caution (plausibility is
not proof) was respected: the mechanism was not treated as fact until the experiment ran.

---

## Falsification

**Pre-registered before any run, per C-8.** This repo's established equivalent of a
non-browser deterministic experiment for a client-side timing race is a `page.route()`-based
capability probe (precedent: `tests/ux/regression/test_20260604_bullet_drag_reorder.py:299-353`,
item 30 P1/P2) — real browser, but the race is forced deterministically rather than relied upon
to occur by chance.

**Step 1 — wide instrument, baseline run(s).** Patch `window.setStatus` in-page (before
`UserPickerPage.select()` fires) to append `{text, t: performance.now()}` to a
`window.__statusLog` array (records the raw pre-`_toSentence` argument, so `'READY'`/`'ERROR'`
are exact matches). Run the instrumented test with no forcing, reporting the natural ordering.

**Result (2026-07-31, one run, uncontended):**
`log=[{'text': 'READY', 't': 3006.7}, {'text': 'CHECKING REFINEMENT SCOPE', 't': 3142.6},
{'text': 'ERROR', 't': 3408.2}]`, `status_text='error'` (test would pass). Under ordinary
conditions the tail's `setStatus('READY')` lands ~136ms *before* the refinement even starts
(`select()` fully resolves its cascade before the test's `page.evaluate` fires the refinement) —
not because the tail is fast in absolute terms, but because nothing here begins the refinement
until `select()` returns, and `select()`'s own wait (O-4) only waits for the `<select>` value,
not the tail, yet in an *uncontended* single test the tail still finishes first in practice. This
is consistent with the hypothesis: the race is normally won by the tail finishing before the
refinement is even triggered; only extra latency on the tail (contention, an already-slow
config/experiences DB read) would let the refinement's near-instant abort-driven `ERROR` land
first and then get overtaken.

**Step 2 — deterministic capability probes**, each answering "CAN this mechanism alone produce
`status_text == 'ready'`":

- **P1 (force the race the hypothesized way):** HOLD (never auto-continue) the FIRST tail
  request, `**/api/users/*/config` (O-9 — holding this alone blocks the whole tail, since
  `_landingTab()`'s fetch cannot be sent until `loadConfig()`'s `await` resolves; an earlier
  two-route probe design that tried to hold `config` and `experiences` independently found
  `experiences` never arms, which is what proved O-9's sequential-not-concurrent correction).
  Run the refinement to completion while `config` stays held (its `ERROR` write lands
  uncontested). Release the held `config` request, letting the rest of the tail run for real,
  and check whether the pill goes to `'ready'` once the tail's write actually lands.
  - **If `post_release_status` becomes `"ready"` (matching O-1's exact artifact):** hypothesis is
    capability-proven — `setStatus('READY')` from the stale tail is confirmed able to clobber
    `ERROR`.
  - **If it does NOT reproduce:** either the ordering assumption is wrong, or another writer is
    responsible. Record which, precisely, from the `__statusLog`.

**Result, P1 (2026-07-31, one run):**
`pre_release_status='error' post_release_status='ready' log=[{'text': 'CHECKING REFINEMENT
SCOPE', 't': 2528.5}, {'text': 'ERROR', 't': 2602.4}, {'text': 'READY', 't': 2835.5}]`.
**Capability-proven, first try.** `ERROR` lands uncontested while `config` is held, then
releasing it lets the tail's real `_landingTab()` round trip run and land `READY` ~233ms
later — the pill's final state is byte-for-byte `"ready"`, matching both O-1 artifacts exactly.
- **P2 (reverse control):** let `onUserSelect()`'s tail fully settle (poll `window.__statusLog`
  for a `'READY'` entry) *before* firing the refinement note. Confirm the pill correctly shows
  `ERROR` and stays there — i.e. that suppressing the race suppresses the symptom, not just that
  forcing it produces it.

**Result, P2 (2026-07-31, one run):** `log=[{'text': 'READY', ...}, {'text': 'CHECKING
REFINEMENT SCOPE', ...}, {'text': 'ERROR', ...}]`, `status_text='error'` — the control holds:
sequencing the tail strictly before the refinement leaves `ERROR` as the final, correct state.

**If P1 does not reproduce and P2's control also fails to hold ERROR:** the hypothesis is
dead as stated. Per C-7, do not invent a new theory to fit — widen the instrument (check every
other `setStatus` call site listed in the code-read for one that could fire in this window) and
report back before proceeding, rather than guessing again.

---

## The fix

**Scope decision (owner, 2026-07-31): both, two-phase — same pattern item 29 used.**

**Phase 1 — app-side guard (`static/app.js`).** A new `_statusGen` counter, bumped on every
`setStatus()` call, mirrors item 29's own `_navGen` idiom (its comment already distinguishes
"navigation side effects" from "the state work below," explicitly leaving the latter
ungated — this closes exactly that gap). `onUserSelect()` captures `statusGenAtStart` before its
two awaits; if any `setStatus()` call has landed by the time the tail is ready to write, a newer,
more specific status already superseded the generic "you're all set," so both `setStatus('READY')`
and `_resetIterationState()` (which would otherwise wipe the refinement-history entry O-7 flagged)
are skipped. This is a genuine product fix, independent of any test: a real user hitting this
timing window would previously have had a real failure silently overwritten back to "Ready" — the
exact class of bug this pill exists to prevent (this test file's own header comment, `#5`).

**Phase 2 — harness settle contract (`ui_pages/`).** `UserPickerPage.select()` previously waited
only for `#userSelect`'s value to update (O-4) — satisfied before `onUserSelect()`'s awaits even
start. A new `data-user-select-ready` marker (`static/app.js`, cleared synchronously at the top of
`onUserSelect()` before its first `await`, set after both awaits resolve and the Phase-1 guard has
run) gives `UserPicker.SELECT_READY` (`ui_pages/selectors.py`) a real terminal-state signal, mirroring
the established `data-compose-ready` idiom (`ui_pages/wizard_compose.py`). `select()` now waits on
it instead of the bare value. Scoped to `select()` only — `create()` and `select_from_roster()`
also route through `onUserSelect()` (confirmed by direct read) but are unverified by any test on
this branch, so left untouched rather than extending an unverified fix to unverified call paths.

**Verification note:** re-running P1 post-fix (same probe, same commit sequence) serves as a
deterministic fix-verification: `pre_release_status='error' post_release_status='error'`, with
`__statusLog` showing NO `'READY'` entry at all — the guard suppressed the write entirely, not
just raced it back in time. P1 had to be adjusted to poll `SELECT_READY` instead of a `'READY'`
log entry post-fix, since the fixed code deliberately never writes that entry in this scenario —
confirmed by first trying the old wait and getting a real timeout, not by assuming.

---

## Acceptance bar

- P1 capability probe: pre-fix reproduces the exact historical symptom; post-fix, the pill stays
  `'error'` and the guard is confirmed to suppress the write (not just outrun it). **Met.**
- P2 reverse control holds both pre- and post-fix. **Met.**
- The real target test, `test_surgical_refinement_network_failure_surfaces_error_with_retry`,
  10/10 clean serial runs, zero reruns (this loop mainly confirms no regression — the mechanism's
  natural base rate is too low for a 10-run loop to characterize either way; P1 is the load-bearing
  evidence for the fix itself). **Met.**
- Full `pytest -m ux` clean, zero reruns. Full `python -m scripts.gate` green.

# Diagnosis — the Step-5 wizard rail opens Generate with no frozen composition, so the retired legacy `generate()` fires

> **Status:** root cause **PROVEN** — reproduced by a driven browser run against this
> branch's base tip, plus a passing route-level test that pins the server half.
> **Branch:** `fix/wizard-rail-frozen-composition-gate` (Epic A, board item 20)

Base tip: `0e90142` (stacked on A2's `feat/compose-wait-ux`).

---

## Symptom

A user analyzes a job description and then clicks **5 · Generate** on the wizard
rail, skipping **3 · Compose** entirely. The step opens. Generating from there runs
the legacy full-LLM `analyzer.generate()` — the résumé-body path the
frozen-composition re-architecture (`fix/compose-frozen-composition`, merged
2026-07-06) retired for corpus-mode users — instead of the deterministic assemble of
an `approved_composition`.

---

## Observed

Everything in this section is an artifact from a command run on this branch, not a
reading of the source.

1. **The rail lets Step 5 open with nothing frozen — driven, not read.** New
   instrument `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py` drives a
   real Chromium against the real Flask routes (analyzer stubbed): seed corpus user →
   `POST /api/analyze/stream` → read the rail. Run:

   ```
   python -m pytest tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py \
       -m ux -p no:randomly -q --no-header -p no:rerunfailures
   ```

   `3 failed in 12.20s`. The first failure carries the captured rail state verbatim:

   ```
   AssertionError: Step 5 was reachable with no frozen composition; rail state:
   {'steps': {'1': {'reachable': True,  'disabled': False, 'title': "You're on step 1: Job + Analyze"},
              '2': {'reachable': True,  'disabled': False, 'title': 'Go to step 2: Clarify'},
              '3': {'reachable': True,  'disabled': False, 'title': 'Go to step 3: Compose'},
              '4': {'reachable': True,  'disabled': False, 'title': 'Go to step 4: Template'},
              '5': {'reachable': True,  'disabled': False, 'title': 'Go to step 5: Generate'},
              '6': {'reachable': False, 'disabled': True,  'title': ''}},
    'step': 1, 'frozen': False, 'contextPath': True, 'resumePath': False}
   ```

   Read off that table, at the moment immediately after analyze and before any
   Compose interaction: `_compositionFrozen` is `False`, and the Step-5 rail button is
   both `reachable: True` and `disabled: False`. **The user can click it.**

2. **The instrument is wider than the hypothesis, and the wider read is the useful
   one.** The same dump covers all six steps, not just step 5. Only **step 6** is
   gated by anything other than the context path (`resumePath: False` →
   `reachable: False`). Steps 2, 3, 4 and 5 are uniformly open the instant
   `contextPath` becomes true. So the defect is not "step 5 has the wrong condition";
   it is "step 5 has **no** condition of its own", which is a different fix.

3. **The server does run the legacy LLM path for exactly that context shape.** The
   already-committed route test is green at this tip:

   ```
   python -m pytest "tests/test_deterministic_generate.py::TestDeterministicGenerateRoute::test_corpus_without_freeze_falls_back_to_llm" -p no:randomly -q --no-header
   ...
   1 passed in 2.45s
   ```

   That test posts `/api/generate` with a context carrying `career_corpus` and **no**
   `approved_composition`, and asserts `calls["generate"] == 1` — i.e. the legacy
   `analyzer.generate()` fired. It is a *pinned* description of today's server
   behavior, which is what makes observation 1 the whole bug: the rail is the only
   thing standing between a user and that path.

4. **A prior-application resume reports a genuinely-frozen run as unfrozen.** Third
   instrument test: seed an application with a generated résumé **and** a context file
   containing a populated `approved_composition`, resume it from the Prior
   Applications panel, dump the rail. Captured verbatim from the same run:

   ```
   AssertionError: a resumed application with a frozen composition read as unfrozen:
   {'steps': {... '5': {'reachable': True, 'disabled': False, 'title': 'Go to step 5: Generate'},
              '6': {'reachable': True, 'disabled': False, 'title': "You're on step 6: Download"}},
    'step': 6, 'frozen': False, 'contextPath': True, 'resumePath': True}
   ```

   `frozen: False` **while the context on disk carries the frozen document**. This is
   the rival a hypothesis-scoped instrument would have hidden: `_compositionFrozen` is
   a session-only client belief, so the obvious one-line client gate
   (`step === 5 && !_compositionFrozen`) would have locked a legitimately-frozen
   resumed application out of Generate. Observed before the fix was written, not
   discovered by it.

5. **The existing UX suite pins the defect as intended behavior.**
   `tests/ux/regression/test_20260707_generate_surface_download.py::test_legacy_path_never_claims_deterministic_assembly`
   drives exactly the reported flow — its own comment reads *"Straight to Step 5 via
   the rail — no Compose save, nothing frozen"* — and asserts the panel opens. Run at
   this tip: `1 passed`. Any fix for item 20 necessarily invalidates that test's
   premise, so it is a consumer of this change, not collateral.

6. **The client's "frozen" and the server's "frozen" were two predicates, and they
   disagreed.** Found by adversarial review of the first fix; reproduced before any
   further production edit. Two new tests, run against the staged first fix:

   ```
   python -m pytest "tests/test_application_routes.py::TestResumeState" \
       -p no:randomly -q --no-header -p no:rerunfailures
   ...
   FAILED tests/test_application_routes.py::TestResumeState::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_document
   FAILED tests/test_application_routes.py::TestResumeState::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_corpus
   ======================== 2 failed, 16 passed in 23.20s ========================

   tests\test_application_routes.py:1651: in test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_document
       assert rs["has_frozen_composition"] is False
   E   assert True is False
   ```

   Both tests assert the AGREEMENT of the two predicates on one context dict. Each
   one's `assert _frozen_composition(ctx) is None` precondition **passed** on the
   same run — so the server had already decided it would NOT assemble that context
   deterministically, while `resume_state.has_frozen_composition` answered `True` and
   opened the rail. Two shapes reach it: a frozen document with no content
   (`work: []`, no `basics.summary`, `skills: []`), and a context whose analyze-time
   `career_corpus` snapshot is empty.

7. **The same disagreement, driven end to end in a browser — the freeze SUCCEEDS and
   the rail still opens.** New test
   `test_20260809_wizard_rail_frozen_gate.py::test_freezing_a_composition_the_server_wont_assemble_leaves_step5_locked`:
   analyze with one active role, click Retire on the auto-drafted positioning summary,
   soft-retire the role (`Experience.is_active = 0` — the Corpus panel's own action,
   Epic A A1b), then the real **Save and continue**. Run against the staged first fix:

   ```
   python -m pytest "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py::test_freezing_a_composition_the_server_wont_assemble_leaves_step5_locked" \
       -m ux -p no:randomly -q --no-header -p no:rerunfailures
   ...
   E   AssertionError: _compositionFrozen claims a freeze the server's own assemble gate rejects; rail state:
   {'steps': {... '4': {'reachable': True, 'disabled': False, 'title': "You're on step 4: Template"},
              '5': {'reachable': True,  'disabled': False, 'title': 'Go to step 5: Generate'},
              '6': {'reachable': False, 'disabled': True,  'title': 'Generate the documents first.'}},
    'step': 4, 'frozen': True, 'contextPath': True, 'resumePath': False}
   E   assert True is False
   ============================= 1 failed in 27.00s ==============================
   ```

   The three preconditions ahead of that assertion all held on the same run (they
   would have failed first): `approved_composition` **is** a dict on the context (the
   freeze landed), `career_corpus` **is** populated, and
   `_frozen_composition(ctx) is None`. So this is not a failed save reported as
   unfrozen — it is a landed freeze the server will not assemble from, with
   `frozen: True` and Step 5 open behind it.

8. **Where the rail's condition actually lives.** `static/app.js:7144-7151` at this
   tip, quoted verbatim:

   ```js
   function _wizardReachable(step) {
     // Forward gating after B1 reorder:
     //   Step 1 always reachable; Step 2+ needs a successful analysis;
     //   Step 6 needs a successful generation.
     if (step >= 2 && !lastContextPath) return false;
     if (step >= 6 && !lastResumePath) return false;
     return true;
   }
   ```

   No reference to `_compositionFrozen`, `approved_composition`, or Compose. This
   agrees with observation 2 rather than substituting for it.

---

## Falsified

- **"The Step-5 copy toggle is the gate."** `_renderGenerateStepCopy`
  (`static/app.js:7192-7197`) toggles `#generateStepCopyLegacy` /
  `#generateStepCopyFrozen`. Killed by observation 1: in the captured state the panel
  opened and the legacy copy showed. It is an *honesty* mechanism that reports the
  path, never a gate that blocks it. The F-09 comment above it says so in the code's
  own words ("Generate still runs the real LLM path, so the copy must NOT claim
  determinism"), and observation 5 shows a committed test relying on that reachability.

- **"Gate the client on `_compositionFrozen` alone."** My own first candidate fix,
  killed by observation 4 before it was written: `_compositionFrozen` is `false` on
  every resumed application regardless of what the context file holds, so the gate
  would have stranded real frozen runs at Step 6 with Generate greyed out. Cheap to
  kill only because the instrument was scoped wider than step 5's own condition.

- **"There is no legacy user to protect, so the server should just refuse."**
  Not falsified as a design option, but its premise is: `_frozen_composition`
  (`blueprints/generation.py:786-804`) also returns `None` when `career_corpus` is
  falsy, and `db/build_context.py:90-96` builds `career_corpus` from *active*
  experiences — so a candidate with zero active roles produces `career_corpus: []`
  and legitimately reaches the `generate()` fallback. `blueprints/generation.py:271-274`
  states this in the code ("a corpus-mode context that hasn't reached generate yet (or
  a résumé with zero corpus experiences) legitimately has an empty `career_corpus`").
  Two committed route tests pin the fallback
  (`test_legacy_context_still_calls_generate`, `test_corpus_without_freeze_falls_back_to_llm`).
  Making the server refuse would break both and can strand that user. Recorded so the
  next reader does not re-open it as an obvious improvement.

---

## Inferred

**Unproven. Not built on.**

- The historical reason the rail never gained a Compose condition is most likely
  ordering: `_wizardReachable`'s comment dates it to the "B1 reorder", predating
  `fix/compose-frozen-composition`, and the freeze became load-bearing afterwards
  without the rail being revisited. I have **not** verified this against the commit
  history and it changes nothing about the fix — recorded only so it is not mistaken
  for a finding.
- Item 20's filed `refs` (`static/app.js:6958-6965`, `:7002-7011`,
  `blueprints/generation.py:786-804`) are from 2026-07-28. The two `app.js` line
  ranges no longer point at the named functions (A2 moved ~308 lines); the
  `generation.py` range still does. Re-derived above rather than inherited.

---

## Falsification

**The experiment, stated so it can fail, and run before any production edit.**

`tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py`, three tests, driving a
real browser against the real routes:

1. after analyze only, the Step-5 rail button is unreachable **and** rendered disabled
   **and** `wizardGoTo(5)` refuses with a message naming Compose; then, after Compose's
   Save-and-continue, Step 5 opens;
2. the whole six-step reachability table equals `{1:T, 2:T, 3:T, 4:T, 5:F, 6:F}` after
   analyze (so a fix that silently locks some *other* step fails here);
3. a resumed application whose context carries `approved_composition` reads as frozen
   and can reach Step 5.

- **If they fail on the base tip:** the mechanism is confirmed and the fix may be built.
- **If they pass on the base tip:** the hypothesis is dead — stop, widen, report.

**Outcome, run 2026-08-09 on base tip `0e90142`: `3 failed in 12.20s`.** All three
failures are quoted under `## Observed` (1, 2 and 4). Test 3 failing was not predicted
by the filed mechanism and is the reason the fix has a server half.

---

## The fix

Gate Step 5 on a composition freeze that the **server** vouches for, and give the
client an honest way to know it.

1. `static/app.js` — `_wizardReachable` gains one condition: step 5 additionally
   requires `_compositionFrozen`. `wizardGoTo`'s refusal toast and `_wizardRender`'s
   button `title` both name Compose, so a greyed step explains itself (observation 1
   shows disabled buttons currently carry `title: ''`).
2. **`hardening.frozen_composition_doc` — ONE predicate for "this context is
   frozen", with one implementation.** It is the body `_frozen_composition` used to
   carry: corpus-mode (`career_corpus` non-empty) **and** an `approved_composition`
   dict **and** that document has content (`work` / `basics.summary` / `skills`).
   It lives in `hardening.py` because that module owns the `ContextSet` contract, is
   deterministic (no LLM calls added), and is importable by both blueprints —
   `blueprints/applications.py` cannot import `blueprints/generation.py` (the cycle
   is generation → templates → applications). `hardening.py` is in
   `scripts/enforcement/blast_radius.py`'s `ACKNOWLEDGED_NOT_GATED` ("the ordinary
   home for per-branch pipeline work"), so this is not a C-10 gated surface.
   **Three callers, no fourth copy:**
   - `blueprints/generation.py::_frozen_composition` — now a named wrapper that
     delegates. Kept by name because `evals/runner.py` imports it as a seam.
   - `blueprints/applications.py::_pre_generate_hydration` — `has_frozen_composition`.
   - `blueprints/applications.py::save_application_composition` — the `frozen` field
     in the freeze response, computed in-lock on the dict about to be written.
3. `static/app.js` — both setters of `_compositionFrozen` now read that one answer:
   the prior-application resume takes `resume_state.has_frozen_composition` instead
   of hard-`false` (closing observation 4), and `_postComposition` returns the
   response's `frozen` instead of a bare `true` (closing observation 7).

### Reversal — decision 2 of the first fix is superseded

The first fix on this branch deliberately used the **weaker** client-side predicate
("an `approved_composition` key is present"), on the rationale that the stronger one
would lock a zero-active-role candidate out of Generate. **That rationale is
withdrawn**, and the recorded reason is kept rather than overwritten so the next
reader can see which way it went and why:

- The correct gate is **"the server will actually assemble deterministically"**,
  because that is precisely what the copy behind the rail claims ("Assembled
  instantly from your approved composition — same input, same résumé, no AI
  variation"). A weaker gate does not protect the zero-corpus candidate; it walks
  them into a full-LLM run wearing a determinism promise.
- Observations 6 and 7 are the measurement: the two predicates disagreed on two
  reachable context shapes, one of them driven end to end with a freeze that landed.
- **This tightens the gate, intentionally.** A candidate whose analyze-time
  `career_corpus` is empty can no longer reach Generate. They are not walled out:
  steps 1–4 stay reachable off `lastContextPath` (asserted in the new UX test — Step
  3 is `reachable: True, disabled: False` and clicking it opens the Compose panel).
  **Stated precisely, because "go back to Compose and include something" is only
  half true:** for the *contentless-document* shape, Compose is the fix. For the
  *empty-`career_corpus`* shape it is not — that snapshot is frozen at analyze time,
  so the recovery is to add or un-retire a role in the Career Corpus and re-analyze.
  Both routes are reachable from a locked Step 5; neither is signposted by the
  refusal text, which names Compose only. Filed under `## Deferred` below.

**Deliberately NOT changed, with reasons:**

- **The server fallback to `generate()` stays.** See the third `## Falsified` entry:
  it is the correct behavior for an empty-corpus candidate and is pinned by two
  committed tests. The rail is the gate; the fallback is the floor.
- **`#generateStepCopyLegacy` is kept, not deleted.** Step 5 is now reachable only
  when the server will assemble deterministically, so the legacy copy variant has
  **no reachable render at all** — the honest statement of its status, and the
  reason it stays: it is the mechanism that keeps a determinism claim off a
  non-deterministic run, and it is exactly the wrong thing to delete on the branch
  that just found the rail admitting such a run. Deleting it would also mean editing
  `ui_pages/selectors.py`, a gated C-10 surface, to remove
  `Wizard.GENERATE_COPY_LEGACY`. Removal is a separate, deliberate decision, not a
  tidy-up. **Its test does not fabricate reachability**: the F-09 regression asserts
  only that the element is in the DOM and still carries the LLM framing, never that
  a state the app cannot enter renders it.

---

## Deferred

**Filed, not fixed, on this branch. Each needs a decision from the closer.**

1. **A frozen snapshot goes stale silently after a post-freeze Compose edit.**
   Freeze → navigate back to Compose → edit anything: the debounced autosave omits
   `freeze`, so `approved_composition` on disk keeps the pre-edit content while
   `_compositionFrozen` stays `true` and Step 5 stays open. **Pre-existing** — not
   introduced or worsened here, and **generation itself is unaffected**: the server
   re-reads `approved_composition` from the context file on every `/api/generate`
   and never consults the client flag, so what assembles is always the snapshot on
   disk. The defect is that the user's newer edits are silently not in it. Out of
   scope for item 20 (which is about *which path runs*, not *how fresh its input
   is*); surfaced by the adversarial review of this branch and recorded here so it
   is filed rather than rediscovered.

2. **A locked Step 5 names only one of its two recoveries.** `_wizardLockReason(5)`
   says "Save your composition in Compose (step 3) first". That is the right
   instruction for a contentless frozen document, and the *wrong* one for a context
   whose analyze-time `career_corpus` snapshot is empty — no amount of Compose work
   fixes that; the user has to add or un-retire a role in the Career Corpus and
   re-analyze. Not fixed here because distinguishing the two in the toast means the
   client learning *why* the server said no, which is a payload-shape change (a
   reason code alongside `has_frozen_composition` / `frozen`) rather than a copy
   edit. The user is not stuck either way — steps 1–4 stay reachable — but the
   signpost points at one door of two.

---

## Acceptance bar

- The three instrument tests pass, with **no rerun** in the log
  (`-p no:rerunfailures` on the confirming run, so a fail-fail-pass cannot masquerade
  as `PASSED`).
- `tests/ux/regression/test_20260707_generate_surface_download.py` is rewritten at the
  one test that pinned the defect (observation 5) and its two siblings still pass —
  the frozen-copy test in particular, which drives the legitimate Compose → freeze →
  Step 5 route.
- The compose + generate + wizard-navigation UX modules pass **as a group**, not just
  the new file: a targeted green says nothing about a file it did not execute, and
  this change edits shared navigation (`_wizardReachable` is read by `wizardGoTo`,
  `_wizardRender`, `_wizardAdvanceTo` and the popstate restore).
- `tests/test_deterministic_generate.py` stays fully green — the server's
  deterministic-assemble behavior is unchanged by design (`_frozen_composition` now
  delegates to `hardening.frozen_composition_doc`, which is its former body verbatim),
  and a regression there would mean the fix leaked past the rail.
- **The two predicates agree, asserted as agreement rather than as two independent
  expectations** — the three new route-level tests each assert
  `_frozen_composition(ctx) is None` *and* the client-facing field, on the same dict,
  so a future edit to either half fails here:
  `TestResumeState::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_document`,
  `…_on_an_empty_corpus`, and
  `TestPostCompositionFreeze::test_freeze_reports_unfrozen_when_the_snapshot_has_no_content`.
- **The end-to-end arm is driven, not evaluated into place** —
  `test_freezing_a_composition_the_server_wont_assemble_leaves_step5_locked` reaches
  the state through real user actions and checks its own preconditions off the
  server's gate, so it cannot go green because the freeze quietly failed.

### Met — verbatim, 2026-08-09, after the adversarial-review pass

Every run below disabled `pytest-rerunfailures` explicitly (`-p no:rerunfailures`), so
no result here can be a fail-fail-pass reported as a bare `PASSED`. (`pyproject.toml`
does not put `--reruns` in `addopts`; the flag is CI-only. Disabling the plugin makes
that non-negotiable rather than assumed.)

```
python -m pytest tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py \
    tests/ux/regression/test_20260707_generate_surface_download.py \
    -m ux -p no:randomly -q --no-header -p no:rerunfailures
8 passed in 30.53s

python -m pytest tests/test_application_routes.py tests/test_composition_summary.py \
    tests/test_deterministic_generate.py -p no:randomly -q --no-header -p no:rerunfailures
106 passed in 12.71s

python -m pytest -m "not ux" -p no:randomly -q --no-header -p no:rerunfailures
2393 passed, 1 skipped, 148 deselected in 588.80s (0:09:48)

python -m pytest -m ux -p no:randomly -q --no-header -p no:rerunfailures
146 passed, 2394 deselected, 1 xfailed, 1 xpassed in 527.09s (0:08:47)

node --check static/app.js       →  (silent; exit 0)
python -m ruff check .           →  All checks passed!
python -m ruff format --check .  →  345 files already formatted
python -m mypy .                 →  Success: no issues found in 361 source files
```

The **before** side of each new test — the failing output that made these edits
legal under C-7 — is quoted verbatim under `## Observed` 6 and 7, not summarized here.

The `1 xfailed, 1 xpassed` split is the known non-strict xfail pair in
`tests/ux/regression/test_20260708_busy_states_and_chip.py` (board item 62 — either
split is legal and it is not to be chased).

The **full** UX tier was run rather than the compose/generate modules alone, because
this change edits shared navigation: `_wizardReachable` is read by `wizardGoTo`,
`_wizardRender`, `_wizardAdvanceTo` and the popstate restore, so a targeted green
would have said nothing about `test_20260622_wizard_back_nav.py`,
`test_20260526_rail_reenable.py`, `test_20260706_new_tailoring_reset.py` or
`test_20260708_step6_full_hydration.py` — all of which drive the rail and all of
which passed. The review pass widened the blast radius again: `_postComposition`'s
return value is now the server's `frozen` field rather than a bare `true`, and it is
shared with the debounced autosave and two other save paths (they ignore the return,
verified by reading all four call sites — but "verified by reading" is why the whole
tier ran rather than the compose module alone).

### Consumers of the changed contracts, enumerated

Not a gated C-10 surface (`hardening.py` is in `blast_radius.py`'s
`ACKNOWLEDGED_NOT_GATED`; `static/app.js` is ungated by policy), so this is recorded
here rather than in a dossier — but the enumeration was still done first:

- **`_frozen_composition`** — 2 call sites in `blueprints/generation.py`, 1 in
  `evals/runner.py`, plus its own new tests. Name and signature unchanged; body now
  delegates to a verbatim copy of itself, so all three are behavior-identical.
- **the `/composition` response's `frozen` field** — read by `_postComposition`
  (`static/app.js`) and asserted in `tests/test_composition_summary.py` (3 tests).
- **`resume_state.has_frozen_composition`** — read by `resumeApplicationIntoWizard`
  (`static/app.js`) and asserted in `tests/test_application_routes.py` (5 tests).
- **Checked and deliberately excluded:** `blueprints/templates.py::_json_resume_has_content`
  is a *different* predicate ("is this document worth rendering in a preview" — it also
  counts `basics.name`, `education`, `projects`, and does not look at `career_corpus`).
  Folding it into this one would change preview behavior and would be wrong: a
  name-only document should still preview. `analyzer.py:4510` reads
  `approved_composition` to build a prompt block, not to gate anything.
- **`ui_pages/selectors.py:263-266`'s comment** still describes the FROZEN copy as
  showing "only after Compose's Save-and-continue froze an approved_composition",
  which is now under-specified (it also requires the document be assemblable). Left
  alone deliberately: that file is a gated C-10 surface, and a comment refinement
  does not justify the dossier ceremony. Recorded so it is a known imprecision rather
  than an undetected one.

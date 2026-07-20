# Diagnosis — 5 context-write routes share the already-fixed lost-update shape, unprotected

> **Status:** root cause PROVEN — dynamic reproduction succeeded (see Falsification),
> promoting the Inferred hypothesis to an observation for the `/api/clarify` ↔
> `/api/answer-clarifications` pairing. The other 4 sites are the same structural
> shape and not independently reproduced (each pairing has to be checked, per the
> dossier's own falsification standard) — the fix is applied uniformly across all 5
> anyway, since the mechanism (whole-dict write-back over a stale read) is identical
> regardless of which specific pair races on any given run, exactly as O-8 of the
> original dossier states for its 12 sites.
> **Branch:** `fix/context-write-lost-update-gap`

---

## Symptom

No user-reported symptom. Found via proactive code audit while evaluating an unrelated
question (whether `app.run(threaded=True)` would be safe to consider for
`feat/diagnostics-run-cancel`). That question required checking what currently depends
on the server being single-threaded — which led to re-deriving the scope of the prior
`hardening.context_transaction` fix (`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`)
and finding it was narrower than its own docstring implies.

---

## Observed

Every entry below is a direct grep/read result, not a deduction.

1. **The prior fix's own scope statement**, `docs/dev/diagnosis/compose-summary-draft-settle-hole.md:89-99` (O-4): *"Every context writer in `blueprints/applications.py` looks like this: [read whole file → slow LLM call → write whole dict back]... All twelve write sites, confirmed at HEAD: `blueprints/applications.py` lines 1708, 1838, 1946, 2086, 2244, 2334, 2365, 2432, 2646, 2730, 2863, 2962."* — scoped explicitly and only to `blueprints/applications.py`.

2. **`grep -rn "with context_transaction(" .` (repo-wide) returns matches in exactly three files:** `blueprints/applications.py`, `hardening.py` (the definition), `tests/test_hardening.py`. No other production file uses it.

3. **`grep -n "cp\.write_text(json\.dumps(context_set" blueprints/*.py` finds 5 sites outside `applications.py`**, each the identical `json.loads(cp.read_text())` → work → `cp.write_text(json.dumps(context_set, indent=2), encoding="utf-8")` shape, none using `write_context_atomic` or `context_transaction`:
   - `blueprints/analysis.py:490` — inside `POST /api/clarify` (route @422). Read at 459, LLM call `clarify(...)` at 471, write at 490.
   - `blueprints/analysis.py:667` — inside `POST /api/answer-clarifications` (route @596). Read at 642, in-memory merge only (no LLM), write at 667.
   - `blueprints/analysis.py:851` — inside `POST /api/iterate-clarify` (route @698). Read at 735, LLM call `clarify_iteration(...)` at 789, write at 851.
   - `blueprints/generation.py:745` — inside `POST /api/save-edits` (route @662). Read at 708, deterministic normalize (no LLM), write at 745.
   - `blueprints/generation.py:1587` — inside `POST /api/generate-cover-letter` (route @1484). Read at 1522, LLM call `generate_cover_letter_against_resume(...)` at 1551, write at 1587.

4. **All 5 sites read/write the same `OUTPUT_DIR/<username>/context_*.json` namespace** the 12 already-fixed `applications.py` routes use (`_within(cp, current_app.config["OUTPUT_DIR"])` in every route; same `context_path` request field resolves to the same file class) — confirmed by reading each route's path-resolution block.

5. **No client-side serialization exists that would prevent two routes writing the same file concurrently.** Checked `static/app.js` around the fetch call sites for all 5 routes plus the 12 already-fixed ones: only a single-button `disabled=true` scoped to one control in one tab. No cross-route mutex, no per-session lock.

6. **No existing test coverage for concurrent-write safety at any of the 5 sites.** `grep -rln "context_transaction\|TestConcurrentContextWriters" tests/` returns only `tests/test_draft_summary.py` and `tests/test_hardening.py`.

7. **All 5 sites predate the fix.** `git log --diff-filter=A -- blueprints/analysis.py blueprints/generation.py` shows both files created by the blueprint-extraction commits (`6d77229`/`7ef5d86`), before `61ec8584` (2026-07-14, the commit that built `context_transaction` and converted the 12 `applications.py` sites). Not a deliberate exclusion — the fix's own diagnosis doc never mentions either file.

8. **Two documentation sites assert the deployment is threaded; the code says otherwise.** `hardening.py:1556-1559` and `docs/dev/diagnosis/compose-summary-draft-settle-hole.md:296` both state "the Dockerfile runs a single-process **threaded** server." Repo-wide `grep -rn "threaded\s*="` (excluding `.venv`) returns exactly one hit: `tests/ux/conftest.py:97`, a test-only `make_server(..., threaded=True)` fixture. `app.py:292` (`app.run(host=args.host, debug=debug_mode, port=args.port)`) has no `threaded` kwarg; the Dockerfile's `CMD ["sartor", "--host", "0.0.0.0"]` invokes the same call via the `sartor` console script (`pyproject.toml:137-140`).

9. **This inaccuracy was not caught by the existing compliance-witness pass.** `docs/governance/compliance-log.md:91` shows `CW-111 (AFFIRM): "#15" + threaded=True citations exact at the sha` — but that check verified citations in the round2-findings review doc, not the `hardening.py` docstring or the diagnosis dossier, both of which assert the opposite fact.

---

## Falsified

_(Nothing yet — this is a proactively-found structural gap, not a chase through dead-end theories.)_

---

## Inferred

**Hypothesis:** under real request concurrency (i.e. if `app.run(threaded=True)` were ever
flipped, or under the test-only threaded harness), each of these 5 sites reproduces the
exact "lost update" mechanism `compose-summary-draft-settle-hole.md` O-7 proved for the
original 12 — a second writer's stale whole-dict write-back silently erases a first
writer's already-persisted delta to the same context file.

**This is still only a hypothesis** for these specific 5 sites: O-7's reproduction forced
one specific interleaving between `/recommend` and `/draft-summary`, both in
`applications.py`. It has not yet been run against any of these 5 sites, or against a
pairing of one of these 5 with one of the 12 already-fixed routes. The structural match
(identical code shape, identical file namespace, no serialization) is strong circumstantial
evidence but is not itself an observation of the race occurring.

**Gap:** what would have to be SEEN to promote this to fact — the same kind of forced
interleaving test O-7 used (stub each route's slow call, gate two routes on
`threading.Event`s to force writer-B to persist inside writer-A's read-work-write window),
run against at least one of these 5 sites, showing a delta silently vanish on HEAD.

---

## Falsification

**The experiment that settles it. Run BEFORE writing any fix.**

Add `tests/test_context_write_races.py::TestConcurrentContextWriters::test_answer_clarifications_does_not_erase_a_concurrent_clarify`
(or equivalently-named test), mirroring `tests/test_draft_summary.py`'s
`test_recommend_does_not_erase_a_concurrent_draft_summary`: stub `clarify()`'s call inside
`POST /api/clarify` and gate it on a `threading.Event` so `POST /api/answer-clarifications`
can read, merge, and persist its own delta (`clarifications`) in the window between
`/api/clarify`'s read and its (still in-flight) write; then let `/api/clarify` resume and
write its own whole-dict update (`clarification_questions`, `run_id`). Assert both deltas
survive in the final file.

- **If it fails on HEAD** (either delta is silently missing/overwritten): the hypothesis is
  confirmed for at least this pair; extend the same pattern to the other 4 sites as
  additional regression coverage, then build the fix.
- **If it passes on HEAD:** the hypothesis is dead for this specific pairing. Stop, do not
  assume the other 4 sites also pass — each pairing has to be checked, since the exact
  interleaving (which route reads first, which writes first) determines whether a given
  pair actually collides. Widen the instrument and report before fixing anything.

**Result: it fails on HEAD.**
`tests/test_app_clarify.py::TestConcurrentContextWriters::test_answer_clarifications_does_not_erase_a_concurrent_clarify`,
run against unpatched HEAD (`fix/context-write-lost-update-gap` before any production
edit):

```
AssertionError: LOST UPDATE: /api/clarify's whole-dict write-back erased the answer
/api/answer-clarifications had already persisted.
assert None == 'Yes, led a K8s migration for a 12-person team.'
  final['clarifications'] == {}
```

`/api/clarify`'s own delta (`clarification_questions`) survived — it wrote last, as
expected. `/api/answer-clarifications`'s `clarifications["q1"]` key is entirely absent
from the final file, not merely empty — the same "key vanishes outright" signature O-7
observed for the original bug. **The lost update is real, reachable, and reproducible
for this pairing in under a second of actual test body.** What this does NOT prove:
that the other 4 sites collide with each other or with the 12 already-fixed routes in
exactly this way — the mechanism is proven, not every pairing. The fix closes the
mechanism (whole-dict write-back over a stale read) at all 5 sites regardless.

---

## The fix

All 5 sites converted to `hardening.context_transaction(cp)`, matching the established
`blueprints/applications.py` pattern exactly: the delta is computed/applied against the
dict yielded fresh inside the lock, never against the stale pre-call `context_set`
copy. Two sites (`/api/answer-clarifications`, `/api/iterate-clarify`) needed more than
a mechanical swap — their merge/append/id-collision logic read from the pre-call copy
and had to move inside the transaction, re-deriving `existing`/`prior_qs`/`existing_ids`
from the fresh read, or the fix would have only closed the "other route's key
disappears" half of the bug while leaving a second, narrower lost-update inside the
route's own merge (two concurrent submits to the same route, each adding a different
id, one clobbering the other via the same stale-copy mechanism).

- `blueprints/analysis.py:490` (`/api/clarify`) — 2-key delta (`clarification_questions`, `run_id`).
- `blueprints/analysis.py:667` (`/api/answer-clarifications`) — merge moved inside the lock.
- `blueprints/analysis.py:851` (`/api/iterate-clarify`) — id-collision-avoidance + append + notes-append all re-derived from the fresh read inside the lock.
- `blueprints/generation.py:745` (`/api/save-edits`) — up to 3-key delta + notes-append; the now-fully-unused pre-lock `context_set` read was removed rather than left dead.
- `blueprints/generation.py:1587` (`/api/generate-cover-letter`) — 2-key delta; `app_run_id` read from inside the lock for the best-effort DB mirror after.

Also corrected, same branch: `hardening.py`'s `context_transaction` docstring (the false
"threaded server" claim, Observed #8) and an erratum note appended to
`compose-summary-draft-settle-hole.md` (Observed #8) without rewriting that historical
record; a new carry-forward ledger item flagging the compliance-witness gap that let
the false claim stand uncaught (Observed #9).

---

## Acceptance bar

**Met.**

- The falsification test
  (`tests/test_app_clarify.py::TestConcurrentContextWriters::test_answer_clarifications_does_not_erase_a_concurrent_clarify`)
  goes from failing on HEAD (pre-fix) to passing (post-fix) — verified directly, not
  inferred.
- Two more concurrent-writer regression tests added
  (`tests/test_context_write_races.py`), covering the remaining 3 sites
  (`/api/iterate-clarify`, `/api/generate-cover-letter`, each raced against
  `/api/save-edits`) — both pass.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy .` all
  green (330 mypy source files, no issues).
- Full `pytest` suite green: 2038 non-UX tests passed (1 pre-existing skip, 6 chunks,
  all foreground), UX tier 78 passed across a11y+flows+3 regression chunks. One UX
  regression test unrelated to this change
  (`test_20260708_busy_states_and_chip.py::test_restore_scroll_y_loses_to_post_restore_growth`
  — scroll-position-restore mechanics in `static/app.js`, zero relation to
  `context_transaction`/`blueprints/analysis.py`/`blueprints/generation.py`) failed once
  inside a large batched chunk and passed cleanly in an isolated re-run; this matches
  the already-documented, already-tracked "mode C ~17% under CPU saturation" flake
  (`RELEASE_CHECKLIST.md` carry-forward ledger item 4), not a regression from this fix —
  noted here rather than silently re-run into a green summary, per C-7 ("green CI is
  not evidence if the test needed a retry"). No `pytest-rerunfailures` retry was used
  anywhere in this verification; every PASSED above is a bare first-attempt pass.
- No stray processes from this session's own test runs (checked via `tasklist` before
  and after the gate).

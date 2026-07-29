# Diagnosis — annotation bootstrap run silently destroys a prior run's clusters

> **Status:** root cause PROVEN — directly reproduced with a live test against the real route.
> **Branch:** `fix/bootstrap-annotation-overwrite`

---

## Symptom

Item 11 (`docs/dev/work/items/0011-bootstrap-overwrite-destroys-annotations.md`):
a prior session live-confirmed, on a real fixture (`robert-bootstrap`, since
rotated/cleaned up — not present in this clone; `evals/fixtures/real/` is
gitignored user data), that a saved `annotations.json`'s `cluster_index`
values pointed past the end of the current `bootstrap.json`'s cluster list —
one index was "provably orphaned from a generation that no longer exists on
disk." Re-running the bootstrap pipeline for the same fixture slug (e.g.
toggling the grounding-scorers checkbox, or just testing a JD tweak) appeared
to silently discard real, human-verdicted annotation work.

---

## Observed

Reproduced directly, on demand, against the current (unfixed) code — not
inferred from reading the route, and not reliant on the now-absent original
fixture data:

- Added `tests/test_annotation_routes.py::TestBootstrapStream::test_second_run_does_not_destroy_first_runs_bootstrap`,
  which drives the real `/api/annotation/bootstrap` SSE route (stubbed LLM
  pipeline only — no paid calls) twice against the same fixture slug
  (`alice-bootstrap`), with a real `annotations.json` saved via the real
  `/api/annotation/fixture/<user>/<slug>` save route in between (mirroring
  what a human annotator would do between two pipeline runs).
- **Run against HEAD (`48b6099`, unfixed): FAILS.**
  ```
  AssertionError: the first bootstrap run's clusters are gone after the second run
  assert []
  ```
  After the second run, no file under the fixture directory contains the
  first run's cluster content ("First run bullet") anywhere — it is not
  recoverable on disk in any form. The single `bootstrap.json` at
  `blueprints/diagnostics.py:817-820` was overwritten unconditionally by
  `Path.write_text`, with no read-existing-and-merge step, no version check,
  and no warning — confirmed by the write call itself at those exact lines
  (`(fixture_dir / "bootstrap.json").write_text(...)`), and now confirmed
  behaviorally by the failing test above, not just by reading the code.
- The saved `annotations.json` from the first run (built via
  `build_annotation_template`, referencing `cluster_index` 0 against the
  first run's single-cluster `bootstrap.json`) is left on disk unchanged
  after the second run — its `cluster_index: 0` now resolves, via every
  read route (`annotation_load`, `annotation_collate`,
  `annotation_score_grounding`, each of which unconditionally reads
  `fixture_dir / "bootstrap.json"`), to the SECOND run's unrelated cluster
  ("Second run bullet") — a silent semantic swap, not just an out-of-range
  index. This matches the "orphaned index" symptom in item 11's original
  live-confirmed evidence and additionally shows the in-range case is worse:
  no error at all, just wrong data.

---

## Falsified

Nothing chased and killed here — the mechanism was correctly identified by
the session that filed item 11 (citing the exact write site), and this
session's job was to convert that into a live, on-demand reproduction rather
than trust the original (now-gone) fixture evidence. No competing hypothesis
was raised or needed falsifying.

---

## Inferred

None beyond what `## Observed` already demonstrates directly — the failing
test above IS the mechanism, not a guess about it.

---

## Falsification

**Experiment:** `python -m pytest tests/test_annotation_routes.py::TestBootstrapStream::test_second_run_does_not_destroy_first_runs_bootstrap -v`

- **Fails on HEAD (confirmed above):** hypothesis confirmed — build the fix.
- **Passes on HEAD:** would mean the route already preserves prior runs;
  not the case here, so this branch proceeds to the fix.

---

## The fix

Owner-directed fix shape (item 11's own body): never overwrite; use a
versioned/timestamped naming scheme per bootstrap run instead of one fixed
`bootstrap.json` path per slug, so a later run adds a new, dated artifact
rather than destroying the prior one.

Implementation: every bootstrap run writes to a new, never-colliding
`bootstrap-<UTC-timestamp>.json` (plus a `bootstrap.json` "latest" mirror
kept for backward compatibility with existing tooling/tests that read the
legacy fixed name — the mirror is disposable, since the true record is the
versioned file). The annotate/collate/grounding-backfill read routes resolve
which bootstrap doc to use via a new `_resolve_bootstrap_path` helper: when
`annotations.json` already exists, pin to the EXACT file its own
`bootstrap_source` field names (falling back to the newest versioned file,
then the legacy mirror, when there's no annotation yet or its pin is gone).
This closes the actual defect (an in-progress annotation silently reading a
different bootstrap generation's clusters), not just the data-loss surface —
a later run can no longer even semantically hijack an in-progress
annotation's `cluster_index` meanings, because the annotation's own read
path stays pinned to the exact file it was built from.

---

## Acceptance bar

- `test_second_run_does_not_destroy_first_runs_bootstrap` passes (not via a
  rerun — a single clean pass, since a fail-fail-pass reports as a bare
  `PASSED` with no traceback).
- Full existing `tests/test_annotation_routes.py` suite still passes
  unchanged (the `bootstrap.json` mirror keeps every test that reads the
  legacy fixed name working without modification).
- `python -m scripts.gate` green.

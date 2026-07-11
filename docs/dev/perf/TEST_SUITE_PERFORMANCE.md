# Test suite performance — the honest fast-lane numbers

> **Purpose:** the durable, non-review-artifact home for the test-suite
> timing numbers PX-44 (`docs/dev/reviews/2026-07-efficiency/prescriptions.md`)
> asked to be documented, plus the fixture-scoping investigation it
> commissioned. The review's own artifacts
> ([`verification-log.md`](../reviews/2026-07-efficiency/verification-log.md),
> [`findings-register.md`](../reviews/2026-07-efficiency/findings-register.md))
> are point-in-time; this file is where a contributor or future agent should
> look for the current picture.
> **Audience:** contributors deciding which pytest invocation to run locally;
> agents considering a fixture-scoping change.
> **Authoritative for:** the fast/slow test-lane timing numbers and the
> fixture-scoping probe's findings + deferral rationale.

---

## The honest fast-lane numbers (idle measurement)

Re-measured on an otherwise-idle machine at the 2026-07 efficiency review's
seal (`docs/dev/reviews/2026-07-efficiency/verification-log.md`, "Addendum —
idle fast-lane re-measurement (F-tci-01)"):

| Run | Tests | Wall time |
|---|---|---|
| Full suite (`pytest`, no marker filter) | 1,453 | 308.9 s |
| Fast lane (`pytest -m "not slow and not ux"`) | 1,378 | **163.1 s** |
| Slow/UX tier (`pytest -m "slow or ux"`) | 75 | 248.0 s |

**Read this as:** a documented fast lane roughly halves the inner dev loop
(309 s → 163 s), not the ~20×/<15 s originally projected (F-tci-01, since
WEAKENED). The 163 s floor is dominated by per-test Flask/SQLite fixture
overhead across those 1,378 tests (~0.12 s/test average) — see the probe
below. The two tiers sum to more than the full run (411 s vs 309 s) because
separate invocations each pay test collection (and, for the slow/UX tier,
browser/Chromium setup) a second time.

**Method note, stated plainly because it bit the review once already:** never
compare a fast-lane timing taken under concurrent load (e.g. several agents
or a full gate running on the same machine) against an idle baseline — the
review's own first attempt at this measurement was inflated ~1.8× by
concurrent verification agents. Re-measure idle, or don't compare across
load states.

**CONTRIBUTING.md fix (PX-44, this pass):** the PR checklist previously
listed `pytest` (green) *and* `pytest -m ux` (green) as two separate
required steps. Since the default `pytest` invocation carries no marker
filter (`pyproject.toml`'s `addopts = "-v --tb=short"`, no `-m` exclusion),
a plain `pytest` on a machine with Chromium installed already executes the
UX tier once — running `pytest -m ux` afterward re-executed the same ~67-75
tests a second time. Fixed to a single `pytest` bullet with a note that
`pytest -m ux` on its own is for isolating/debugging that tier, not an
additional required step.

---

## Fixture-scoping probe (PX-44)

**Question:** can the ~1,378-test fast lane's per-test Flask/SQLite fixture
overhead be cut by module-scoping the read-mostly fixtures, without
weakening test isolation?

**Method.** The machine this branch (`perf/db-baseline`) ran on had six other
debt-burn-train lanes executing concurrently — exactly the load-contamination
trap the review's own method note (above) warns against. Rather than take a
second unreliable timed run, this probe is a **static count** over the
non-UX test tree (`tests/*.py`, excluding `tests/ux/`):

| Metric | Count |
|---|---|
| Non-UX test files | 118 |
| ...of which call `create_app(` (build a Flask app) | 46 |
| ...of which call `init_db(` (run the full alembic chain) | 43 |
| Total non-UX test functions | 1,868 |
| Test functions living in a `create_app(`-using file | **658 (35%)** |
| `@pytest.fixture` declarations across `tests/*.py` (non-UX, non-conftest) | 63 |
| ...of which declare a non-default scope (`scope="module"` etc.) | **1** |

**Reading this:** roughly a third of the fast lane's test functions live in
files that build a *fresh* Flask app and run the *entire* 15-revision alembic
migration chain (`db/session.init_db()`) at **function** scope — once per
test, not once per file. Only one fixture in the whole non-UX suite
(`tests/ux/conftest.py`'s session-scoped `_browser`, itself out of the fast
lane) uses a non-function scope. This is consistent with the review's timing
signal (~0.12 s/test average over 1,378 tests) and is the single largest
identifiable, mechanical cost driver in the fast lane.

**Why this isn't a small change.** Most of the 46 files interleave read-only
tests (GET / listing routes) and mutating tests (POST / PUT / DELETE, corpus
edits, migrations) in the *same* file, often the same test class, against
the *same* fixture instance. Naively module-scoping the fixture would let
mutations from one test leak into the next — the exact class of bug
`personas-500` (the corpus-race regression `tests/ux/regression/
test_20260526_corpus_render.py` guards, PX-44's explicit carve-out) exists to
catch. A safe version of this change needs one of:

1. **Split read vs. write tests** per file/class so read-only classes can
   share one module-scoped app+DB, while mutating classes stay
   function-scoped — mechanical but touches all 46 files' organization.
2. **SAVEPOINT-per-test rollback**: keep one module- or session-scoped
   Flask app + DB, wrap each test in a nested transaction
   (`session.begin_nested()`) rolled back in a fixture teardown — the
   standard SQLAlchemy pattern for this, but it requires auditing every
   `db.session.get_session()` call site test-side (and possibly route-side,
   if a route commits mid-request) to confirm nothing depends on an
   *actually committed* row surviving past the test (e.g. a second
   `get_session()` call opening a fresh connection would not see an
   uncommitted SAVEPOINT). That audit is the risky part, not the rollback
   mechanism itself.

Either path is a cross-cutting change to test isolation guarantees across
~40% of the suite, landing in the middle of the v1.1.0 debt-burn train
alongside six other concurrent lanes — exactly the condition PX-44's own
tiebreak note ("fixture-scoping touches test isolation mid-epic") flagged as
gate-worthy, not now-worthy.

**Disposition: DEFERRED.** Per PX-44's own escape valve ("if the
fixture-scoping refactor is large/risky, land only the doc + CONTRIBUTING
fix and defer the scoping change with a written note"), this pass lands the
doc + CONTRIBUTING fix above and defers the scoping change itself. Follow-on
branch: `test/fixture-scoping` (as originally named in the prescription).
Recommended starting point for that branch: pilot the SAVEPOINT approach
(option 2) on ONE small, low-risk file first (e.g. a read-only listing-route
test file with no interleaved mutations) and confirm zero cross-test leakage
before generalizing — do not attempt all 46 files in one pass.
`personas-500` and the rest of `tests/ux/` are out of scope for this
refactor either way (already isolated, already outside the fast lane).

---

## Provenance

| Claim | Source |
|---|---|
| Idle fast/full/slow timings | `docs/dev/reviews/2026-07-efficiency/verification-log.md`, "Addendum — idle fast-lane re-measurement (F-tci-01)" |
| CONTRIBUTING.md double-run bug | `docs/dev/reviews/2026-07-efficiency/verification-log.md` F-tci-01; `pyproject.toml` `[tool.pytest.ini_options]` `addopts` (no default marker filter) |
| Fixture-scoping static counts | `grep -rl "create_app("/"init_db(" tests/*.py`, `grep -rn "@pytest.fixture" tests/*.py \| grep -o 'scope="..."'`, run against this branch's working tree, 2026-07-11 |
| `personas-500` carve-out | `tests/ux/regression/test_20260526_corpus_render.py` docstring; `docs/dev/reviews/2026-07-efficiency/prescriptions.md` PX-44 row |

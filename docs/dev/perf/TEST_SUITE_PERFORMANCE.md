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

**Disposition at the time: DEFERRED.** Per PX-44's own escape valve ("if the
fixture-scoping refactor is large/risky, land only the doc + CONTRIBUTING
fix and defer the scoping change with a written note"), that pass landed the
doc + CONTRIBUTING fix above and deferred the scoping change itself to a
follow-on branch: `test/fixture-scoping`.

---

## Pilot result (PX-44, `test/fixture-scoping`, 2026-07-21)

**Mechanism chosen: migrated-template-DB copy — not the SAVEPOINT approach
above.** Re-reading the exact code (`db/session.py`) before piloting surfaced
that SAVEPOINT-per-test rollback is structurally wrong for this codebase: a
route opens its *own* `get_session()` connection and `commit()`s mid-request,
which a test-held `session.begin_nested()` cannot wrap without re-plumbing
production session wiring — the original write-up undersold this as a
"commit-dependence audit," but it's deeper than that. Module-scoping a
read-only file (the other alternative) also has no safe target: every one of
the 46 `create_app`-using files seeds the DB per test via `get_session().
commit()`, even the GET-only ones.

**The template-copy mechanism instead: migrate ONE template SQLite once per
session (`tests/conftest.py::_migrated_template_db`); each test
`shutil.copy2`s it and points `DEFAULT_DB_PATH` at the copy.** This preserves
full per-test FILE isolation — no shared mutable state, no test-body edits —
while paying the alembic chain once instead of once per test. Two traps had
to be closed, both found only by reading `db/session.py` directly:

1. `init_db()` memoizes on a path SET (`_initialized_paths`), never on DB
   state. A copy's resolved path must be pre-registered into that set before
   the first request, or the first route to call bare `init_db()` silently
   re-migrates the copy from scratch, erasing the whole point.
2. Every connection runs `PRAGMA journal_mode = WAL`. Bundled-template seed
   rows can still be sitting in `template.sqlite-wal` when migration
   finishes; a naive copy of only the main file is schema-complete but
   **seed-empty**. The template fixture runs `PRAGMA wal_checkpoint
   (TRUNCATE)` before the first copy to close this.

**Piloted on two files, converted with zero test-body changes:**
`tests/test_corpus_duplicates_route.py` (`dup_app`, 5 tests, GET-only, two
built-in leak canaries — `test_200_needs_onboarding_when_candidate_missing`
and `test_400_when_user_unknown` both assert the candidate does NOT exist)
and `tests/test_clarifications_list.py` (`memory_app`, 9 tests, a
complementary canary: its per-test `Candidate.username` uniqueness turns any
cross-test leak into a hard `IntegrityError`, not a silent wrong answer).

**Isolation proof.** All 14 tests green under three explicit orderings — the
project has no `pytest-randomly` dependency, so order was permuted by hand via
explicit node-id lists rather than adding one for a temporary pilot check:
forward (both files' natural order), fully reversed (both file order and each
file's test order), and scrambled/interleaved across both files. Zero
failures, zero leak-canary trips, in all three. During the pilot (removed
after proving out — see git history on this branch) each fixture additionally
asserted a fresh copy always started at exactly 4 bundled `PersonaTemplate`
rows and 0 `Candidate` rows before yielding.

**Measured, decomposed, honest numbers (idle machine, no concurrent gate/agents):**

| Measurement | Median | N |
|---|---|---|
| Two pilot files, wall time, BEFORE (per-test `init_db`) | 7.89 s | 5 |
| Two pilot files, wall time, AFTER (template copy) | 5.73 s | 5 |
| Bare `init_db(fresh_tmp)` (the removed per-test cost) | 0.138 s | 8 |
| `shutil.copy2(template, fresh_tmp)` (the new per-test cost) | 0.0015 s | 8 |
| `create_app(Config(base_dir=tmp))` (untouched by this pilot) | 0.108 s | 8 |

Per `--durations=0` breakdowns, the BEFORE runs showed per-test fixture
`setup` lines around 0.19–0.47 s; the AFTER runs showed no `setup` line above
the 0.005 s reporting threshold at all — consistent with the decomposition:
this mechanism removes **~99% of the `init_db` slice** (0.138 s → 0.0015 s
median) but leaves `create_app` (0.108 s median) completely untouched, since
that cost was never inside `init_db`'s scope. **Do not read the two-file wall
win (7.89 s → 5.73 s) as the whole-lane number** — it includes the one-time
session template build amortized over only 14 tests; the decomposed
per-operation numbers above are the honest, generalizable figures.

**Regression check.** Full fast lane run twice, once on each side of this
diff, both idle: **2053 passed, 1 skipped, 127 deselected — identical on both
sides.** (The two full-lane wall times, 433 s before / 513 s after, are
*not* a clean before/after comparison — this session's own background
processes were present for the second run — so they're recorded for
completeness, not cited as evidence; the controlled two-file + decomposed
numbers above are the actual timing evidence.)

**Go/no-go on the full rollout: landed, not deferred.** The pilot's
mechanism proved safe and drop-in; the rollout below is the follow-on that
executed on it. `personas-500` and the rest of `tests/ux/` stayed out of
scope either way (already isolated, already outside the fast lane).

---

## Rollout result (PX-44, `test/fixture-scoping-rollout`, 2026-07-27)

**Owner-directed follow-on to the pilot above.** Re-derived the target list
fresh rather than trusting the pilot's 2026-07-11 counts (already 5 days
stale by pilot time, more by rollout time): `grep -l 'create_app(\|init_db('
tests/*.py` gave a 51-file union; after removing the 2 already-converted
pilot files, 44 files matched the pilot's mechanical fixture shape.

**Shared helper, not 44 more hand-duplications.** The pilot's two fixtures
each inlined the same ~6-line copy/monkeypatch/register block. Continuing
that pattern 44 more times would mean one future change to `db/session.py`'s
internals needing 46 synchronized edits instead of one. Factored it into
`_fresh_migrated_db(tmp_path, monkeypatch, _migrated_template_db, *,
filename=...)` in `tests/conftest.py`, next to `_migrated_template_db`. Each
target file keeps its own uniquely-named local fixture, which now calls the
helper as its first step — interface and test bodies unchanged, only the
internal DB-setup lines differ.

**Excluded, with reasons found by reading each file (not assumed from the
mechanical grep match):**
- `tests/test_bundled_templates.py::TestSeedMigration` — directly tests
  `init_db()`'s own migration behavior (asserts a fresh migration settles at
  exactly 4 bundled rows, and a second call is idempotent). Converting it
  would test the copy mechanism instead of `init_db` itself — discovered
  mid-rollout, not anticipated in the pilot's own scoping.
- `tests/test_db_session.py::TestInitDb` — same rationale, already excluded
  at pilot time.
- `tests/test_packaging.py` — `create_app(Config())` with no `tmp_path`
  override; tests default path resolution, not DB behavior.
- `tests/test_migrations_data_safety.py` — hand-built historical schemas via
  raw DDL + `alembic.command.stamp/upgrade/downgrade`; never goes through
  `init_db()`/`create_app()` at all.
- Several individual fixtures across otherwise-converted files never touched
  the DB at all (no `init_db()` call, no `DEFAULT_DB_PATH` monkeypatch) —
  `test_app_clarify.py::app_client`, `test_app_iterate_clarify.py`'s only
  fixture, `test_assistant_route.py`'s only fixture,
  `test_app_security.py::app_module`/`config_route_app`,
  `test_users_routes.py::users_app`. Converting these would add DB-copy
  machinery with no cost to remove — left as-is.

**Special-case scrutiny, not blanket conversion:**
- `tests/test_app_security.py::config_route_db_app` — the one DB-touching
  fixture in that file; converted normally.
- `tests/test_context_write_races.py::races_app` — races two concurrent HTTP
  requests against the same DB file mid-request. The copy mechanism only
  changes how the file reached alembic head, not the concurrency shape (one
  process-global engine, one file, two threads) — but this needed evidence,
  not an assumption. Ran the file's 2 tests 15x in a loop before conversion
  and 15x after: **0/30 failures both ways**, flake rate unchanged. Converted.

**This rollout's own timing evidence** (not re-citing the pilot's numbers as
if they were this session's — re-measured fresh, idle machine, same machine
as the pilot):

| Measurement | Median | N |
|---|---|---|
| Bare `init_db(fresh_tmp)` | 84.4 ms | 8 |
| `shutil.copy2(template, fresh_tmp)` | 1.0 ms | 8 |
| Reduction | 98.8% | — |

Consistent with the pilot's own ~99% figure (different machine load at
measurement time explains the absolute-ms difference from the pilot's
138 ms/1.5 ms).

**Verification, batched (11/13/9/11-file groups, one commit per batch):**
each batch run forward and in explicit reversed file order; each batch also
run together with the immediately-preceding batch as a cross-batch
interaction check. All batches: pass counts identical across every ordering
— 191/191 (batch A), 248/248 ×2 + 439/439 (A+B), 90/90 ×2 + 338/338 (B+C),
164/164 ×2 + 254/254 (C+D).

**Full fast-lane check, chunked (3 file-list groups, never one `pytest
tests/` call, per the ~13-minute full-gate / 5–10-minute agent-command-kill
constraint this rollout doubles as partial mitigation for — ledger item
#1):** **2055 passed, 1 skipped, 1 failed.** The 1 failure
(`test_wiki_freshness_gate.py::test_this_repos_wiki_is_fresh_enough_to_merge`)
is this branch's own file-touch volume (46 test files + this doc) pushing
the repo's wiki-freshness count from 38 (on `main`, passing) to 83 files
changed since the last `/wiki-ingest` checkpoint — past the 75-file
merge-blocking threshold. Not a functional regression in this mechanism;
resolving it is a separate `/wiki-self-update` (or owner override) step at
close-out, not a rollout defect. `ruff check` and `mypy` both clean;
`ruff format --check` flagged 3 files this rollout's own edits left
unformatted, fixed in place.

---

## Provenance

| Claim | Source |
|---|---|
| Rollout target-list derivation (44 mechanical + 2 special-case files) | `grep -l 'create_app(\|init_db(' tests/*.py`, run fresh on `test/fixture-scoping-rollout`, 2026-07-27 |
| Rollout init_db/copy2 timing | inline Python microbenchmark against `db.session.init_db`/`shutil.copy2`, idle machine, N=8, 2026-07-27, this branch |
| Rollout batched verification counts | pytest runs on `test/fixture-scoping-rollout`, per-batch + cross-batch, 2026-07-27 |
| races_app flake-rate check (0/30 before, 0/30 after) | `pytest tests/test_context_write_races.py` × 15 runs each side, 2026-07-27, this branch |
| Full fast-lane chunked result (2055/1/1) + wiki-freshness gate root cause | `pytest tests/ -m "not ux and not slow"` in 3 file-list chunks; `python scripts/wiki_freshness.py` + `git diff --name-only <last_ingest_sha> main/HEAD`, 2026-07-27, this branch |
| Idle fast/full/slow timings | `docs/dev/reviews/2026-07-efficiency/verification-log.md`, "Addendum — idle fast-lane re-measurement (F-tci-01)" |
| CONTRIBUTING.md double-run bug | `docs/dev/reviews/2026-07-efficiency/verification-log.md` F-tci-01; `pyproject.toml` `[tool.pytest.ini_options]` `addopts` (no default marker filter) |
| Fixture-scoping static counts | `grep -rl "create_app("/"init_db(" tests/*.py`, `grep -rn "@pytest.fixture" tests/*.py \| grep -o 'scope="..."'`, run against this branch's working tree, 2026-07-11 |
| `personas-500` carve-out | `tests/ux/regression/test_20260526_corpus_render.py` docstring; `docs/dev/reviews/2026-07-efficiency/prescriptions.md` PX-44 row |
| Pilot mechanism + traps (`init_db` path-set memoization, WAL sidecar) | `db/session.py` (`init_db` lines ~111-157; `_set_sqlite_pragmas` lines ~42-59), read directly on `test/fixture-scoping`, 2026-07-21 |
| Pilot before/after wall + decomposed init_db/copy/create_app timings | `tests/test_corpus_duplicates_route.py` + `tests/test_clarifications_list.py`, `--durations=0`, idle machine, N=5 (wall) / N=8 (decomposition), 2026-07-21, this branch |
| Pilot isolation proof (3 orderings) + regression check (2053 passed both sides) | manual node-id-ordered `pytest` invocations + two full `-m "not slow and not ux"` runs, this branch, 2026-07-21 |

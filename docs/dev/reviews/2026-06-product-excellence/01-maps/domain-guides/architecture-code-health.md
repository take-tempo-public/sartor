---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Architecture & code health

> Lens, not survey. Severity anchor is the signed Product Charter
> (`00-interview/product-charter.md`). A gap matters only if it blocks a
> charter clause. Claims here honor C-0: mechanisms and effort language,
> no absolutes about LLM behavior.

## 1. What mastery means here

For *this* product, architecture mastery is not "clean code" in the
abstract — it is **structural enforceability of the few promises the
charter makes categorically**, plus a structure that stays cheap to
change across a five-year stability horizon (P-6).

- **C-6 (the deterministic–LLM boundary) is "inviolable."** Mastery means
  that word is earned *by construction* — a test or import-lint that
  *fails the build* if a deterministic module grows an LLM call — not by
  prose in AGENTS.md that a future agent can quietly cross. C-0 is explicit
  that categorical claims are made "only where a deterministic test can
  enforce them by construction." A convention-only C-6 is a claim without
  its enforcement mechanism.
- **C-2 (egress) is the same shape**, and the charter already records it
  as machine-verifiable and verified at c6e0437. The architecture's job is
  to keep the destination set enumerable as `analyzer.py` is the *single*
  caller — the boundary that makes egress auditable *is* C-6's boundary.
- **W-4 (modularize in place) is the working method**, not a someday-goal:
  `recall/`, governance, the wiki loop are extracted-in-place packages.
  Mastery is disciplined seams *now* so extraction is friction-light later.
- **The v1.0.8 blueprint split is the near-term proof of P-6 stability:** a
  6,992-LOC monolith decomposed with *no behavior change*, on the path to a
  public cut whose stated reaction is "whoa, this is robust" (A-4).

External best practice (Flask app-factory + blueprints; forward-only
Alembic with tested upgrades; import-contract linting via grimp /
import-linter) is welcome context — but the charter's enforceability
discipline outranks any generic "split big files" advice.

## 2. Current state pointers

**Strengths (name them):**
- The boundary holds *in fact* at c6e0437. None of the seven deterministic
  modules import `analyzer` or `anthropic` (grep across `hardening.py`,
  `generator.py`, `parser.py`, `scraper.py`, `json_resume.py`,
  `corpus_to_json_resume.py`, `pdf_render.py` — zero hits). The directional
  rule "these never reverse" is documented at `docs/architecture.md:209`.
- The data contract is genuinely auditable: one timestamped child context
  per `/api/generate`, `parent_context_path` chain, `_within()` containment
  on every read/write (`docs/architecture.md:639`-651; D-5).
- Persistence is mature for a local app: 19 ORM tables with CHECK
  constraints, partial unique indexes, and deliberate cascade vs SET-NULL /
  soft-retire choices documented per edge (`db/models.py`; e.g.
  `ApplicationBullet.bullet_id` has *no* cascade by design, `models.py:603`).
- Migrations are SQLite-correct: `batch_alter_table(recreate="always")`,
  idempotent guards, and present `downgrade()` paths (`0007_tracker_status_cleanup.py`).

**Gaps / pointers:**
- **C-6 is convention-only.** No import-lint and no boundary test exist
  (no grimp/import-linter in `pyproject.toml`; no test asserts the
  deterministic set is LLM-free). The `route-security-lint` hook guards the
  `_safe_username`/`_within` *security* gate, not the LLM boundary. So the
  charter's most categorical, "inviolable" clause rests on prose + reviewer
  vigilance — exactly the C-0 anti-pattern.
- **The v1.0.8 plan understates its own blast radius.** `app.py` is
  **6,992 LOC / 78 routes** at c6e0437, but RELEASE_ARC Phase 4.8 still
  reads "6,290-LOC / 75-route" (`RELEASE_ARC.md:740`, mirrored in the
  version map row :21). The "67 test files import from `app`" figure
  (`:746`) also wants re-counting — direct `import app` greps to 0 in
  `tests/`, so the real coupling runs through fixtures/conftest and needs
  re-measuring before the split is scoped.
- **Schema is at revision 0007 at c6e0437** (`db/migrations/versions/` ends
  at `0007`); `init_db()` only ever runs `alembic upgrade head`
  (`db/session.py:151`), so the downgrade paths are written but never
  exercised — a long-lived local DB across a public release relies on
  forward migrations being correct first-try on real user data.

## 3. Rubric

**BOOST** — a structural C-6 enforcer lands (import-lint *or* an AST/import
test that fails on a deterministic-module LLM import), wired into the gate;
the "inviolable" claim is now true by construction, closing the C-0 gap.

**KEEP** — the documented directional import rule, the `_within` containment
discipline, the per-edge cascade rationale in `models.py`, and the
idempotent/`batch_alter` migration style. These are already at-bar.

**FIX** — stale refactor framing (LOC/route/test-coupling numbers in
RELEASE_ARC Phase 4.8 re-measured against c6e0437 before `design/app-blueprints`);
confirm the `route-security-lint` hook's `app.py`-only targeting is updated
for blueprint files (flagged at `RELEASE_ARC.md:754`, must not silently stop firing).

**DEBUFF** — any blueprint-split branch that changes behavior, drops a
`_safe_username`/`_within` guard on a moved route, or lets the security-lint
hook go dark on blueprint modules. The v1.0.8 contract is "pure refactor."

**WATCH** — schema drift on long-lived local DBs (no tested downgrade, no
forward-migration test against a realistic pre-populated DB); cheap
pre-factoring (shared-helpers home, app-factory decision) deferred until the
split itself rather than de-risked first.

## 4. Sharpest questions

(Provided via structured output below.)

---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Architecture & code health

**Domain verdict.** The architecture is genuinely strong for a local-first
Flask app at this stage: the C-6 deterministic↔LLM boundary holds *in fact*
at the pin (zero analyzer/anthropic imports across the seven deterministic
modules; exactly one `.messages.create` and one `.messages.stream` call site,
both inside `analyzer.py`), the persistence layer is mature (26 ORM tables
with per-edge cascade rationale, CHECK constraints, SQLite-correct
`batch_alter_table` migrations), and `app.py` is a true leaf in the
production import graph — only test fixtures couple to it, which de-risks the
v1.0.8 blueprint split. The two material gaps are both about *enforceability
and accurate framing*, not behavior: (1) C-6 — the charter's most categorical
"inviolable" clause — has **no automated enforcer** (no import-lint, no
boundary test), so it rests on convention + reviewer vigilance, exactly the
C-0 anti-pattern; and (2) the v1.0.8 refactor plan carries **stale
blast-radius numbers** (6,290 LOC / 75 routes / 67 test-couplings vs. actual
6,992 / 78 / 24) that would mis-scope the split. Neither blocks usability;
the first blocks an honest "inviolable" claim at the public tag.

---

## Register findings

### F-arch-01 — C-6 boundary is convention-only: no import-lint, no boundary test
- **id:** F-arch-01
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-6, C-0, C-2 (egress auditability rides on the same boundary)
- **question-refs:** QB-arch-01, QB-qe-rel-06
- **coordinate:** v1.0.8 (design/app-blueprints); the BOOST is cheapest to land *before* the split scatters routes
- **evidence:** `pyproject.toml@c6e0437` has no grimp/import-linter (deps: flask, anthropic, python-docx, pdfplumber, markdown, beautifulsoup4, requests, pydantic, sqlalchemy, alembic, playwright — verified); CI gate is `ruff check .` + `mypy .` + `pytest` only (`.github/workflows/ci.yml:36,39,42@c6e0437`); no test asserts the deterministic set is LLM-free; `route-security-lint.sh` guards `_safe_username`/`_within`, not the LLM boundary.
- **the finding:** C-6 is the charter's most categorical clause ("Inviolable: deterministic modules make no LLM calls; one module owns all LLM calls"), and C-0 is explicit that categorical claims are earned "only where a deterministic test can enforce them by construction." At the pin the boundary holds by behavior but nothing *fails the build* if a deterministic module grows an `import analyzer` or `import anthropic`. A ~30-line AST/import test over the seven-module set (or an `import-linter` contract) wired into the existing `pytest` gate would convert "inviolable" from prose to construction and close the C-0 gap. This is the BOOST the rubric names. Severity is P1 not P0 because the boundary *does* hold today — but the public tag's "whoa, robust" claim (A-4) is weaker without it, and the v1.0.8 split is the moment a regression is most likely.

### F-arch-02 — v1.0.8 blueprint plan uses stale blast-radius numbers (LOC / routes / test-coupling)
- **id:** F-arch-02
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** P-6 (5-yr stability proof), W-4 (modularize-in-place), A-4 ("robust")
- **question-refs:** QB-arch-03
- **coordinate:** v1.0.8 (Phase 4.8 / design/app-blueprints) — re-measure before scoping
- **evidence:** Actual at pin — `app.py` = **6,992 LOC / 78 routes** (`wc -l`, `grep -cE '@app\.route|@.*\.route'`); RELEASE_ARC says **6,290 LOC / 75 routes** (`docs/dev/RELEASE_ARC.md:21,740`) and **"67 test files import from `app`"** (`:746,775`). Actual test-coupling = **24 files** (`import app`/`from app import` across `tests/`, Grep-verified; mostly deferred `import app as _app` inside fixtures). No non-test module imports `app` (`^import app`/`^from app import` over all `*.py` = zero matches) — `app.py` is a production-import leaf.
- **the finding:** Three numbers that scope the "pure refactor" epic are stale: LOC is understated ~11%, routes by 3, and the test-coupling figure is overstated ~2.8x (67 claimed vs 24 real). The 24-vs-67 gap actually *improves* the picture — the split's coupling surface is much smaller than the plan fears, and `app.py` being an import leaf means no production module needs rewiring — but a plan built on wrong numbers mis-estimates effort in both directions and undercuts the "this is robust" exhibit if a reviewer re-counts. Re-measure against c6e0437 before `design/app-blueprints` and correct RELEASE_ARC:21,740,746,775. (Domain guide flagged this; confirmed and the test-coupling number re-measured here.)

### F-arch-03 — route-security-lint hook hard-targets `app.py` + `@app.route`; goes dark on blueprint modules
- **id:** F-arch-03
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-1, S-1 (PII fear), C-0
- **question-refs:** QB-arch-05, QB-sec-02
- **coordinate:** v1.0.8 (the split moves routes into modules the hook will not scan)
- **evidence:** `.claude-plugin/hooks/route-security-lint.sh@c6e0437` short-circuits unless the edited path matches `(^|/)app\.py$`, and only triggers on `@app\.route\(` (not `@bp.route`/`@dashboard_bp.route`). The existing `dashboard/routes.py` blueprint (`Blueprint(...)` at :28, `@dashboard_bp.route` at :908) is already outside the hook's coverage — proof it is app.py-scoped today. RELEASE_ARC:753-754 already lists this as a known compat item.
- **the finding:** The `_safe_username`/`_within` security gate is the S-1 PII defense, and its only *automated* enforcement is a hook that will stop firing the moment routes move into `blueprints/*.py` with `@bp.route` decorators. The DEBUFF the rubric warns of is "let the security-lint hook go dark on blueprint modules." Before the split lands a route into a blueprint, the hook's path filter and decorator regex must be generalized (or replaced by an AST check that finds any `*.route` decorator in any module under the routes package). Note this is a *known* item in the arc — the finding is to ensure it is treated as a split prerequisite, not a follow-up, so coverage never lapses.

### F-arch-04 — C-6 holds by behavior at the pin (KEEP — affirm, do not churn)
- **id:** F-arch-04
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** C-6, C-2
- **question-refs:** QB-arch-02, map-BOOST-5 (verify)
- **coordinate:**
- **evidence:** Zero `import analyzer`/`import anthropic` (or `from`) across `hardening/parser/generator/scraper/json_resume/corpus_to_json_resume/pdf_render.py` — confirmed by git-grep AND a sandboxed AST import-node scan of all seven modules fetched from c6e0437 (result: NONE). Exactly **one** `.messages.create` (`analyzer.py:2310`) and **one** `.messages.stream` (`analyzer.py:974`) in the whole non-test/non-eval tree. `app.py` constructs the client (`_get_client()` :87/95) and delegates — it never calls `.messages.*` directly. Directional rule documented `docs/architecture.md:209` ("These directions never reverse").
- **the finding:** The map's BOOST-5 candidate ("deterministic/LLM boundary held by construction") is **confirmed at the behavior level** — the egress-bearing call code is centralized in one module, which is precisely what keeps C-2's destination set enumerable and auditable. This is at-bar and should be affirmed so it is not disturbed during the blueprint split. The one caveat (BOOST-5 says "by construction" — it is not yet enforced *by construction*) is F-arch-01's job; the *fact* of the boundary is solid and worth protecting.

### F-arch-05 — "All LLM calls live in analyzer.py" is precise for call code, looser for prompt templates
- **id:** F-arch-05
- **disposition:** WATCH
- **leverage:** P3
- **charter-trace:** C-6, C-0 (claims precision)
- **question-refs:** QB-arch-02
- **coordinate:**
- **evidence:** `onboarding/extract_experiences.py:29` imports `_parse_or_retry` from analyzer and routes its call through it (`:126`), but builds its own `user_prompt` (`:117-124`) and defines `EXTRACT_EXPERIENCES_SYSTEM_PROMPT` (`:133`) — a prompt template living *outside* analyzer.py. `onboarding/corpus_import.py:398,407` constructs an `anthropic.Anthropic` client (lazily, under `--with-llm`) and delegates to `extract_experiences`. AGENTS.md says "All LLM calls live in `analyzer.py`" and (re prompts) "Edit there, not inline."
- **the finding:** The C-6-load-bearing invariant — *one module owns the API-invocation code, so egress stays auditable* — is intact: every `.messages.*` call funnels through analyzer's `_call_llm_streaming`/`_parse_or_retry`/scope-check. But the doc's stronger phrasings ("all LLM calls live in analyzer.py"; "all prompts edited there") are slightly broader than reality, since a system-prompt constant and user-prompt builder for `extract_experiences` sit in `onboarding/`. Not a violation and not P1 — flagged so the v1.0.7 governance/charter graduation states C-6 as "one module owns the LLM *call mechanism*" rather than "all prompts," which a future reader could falsify by finding the onboarding prompt and wrongly conclude the boundary leaks.

### F-arch-06 — Persistence layer is mature: per-edge cascade rationale, CHECK constraints, named keys (KEEP)
- **id:** F-arch-06
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** D-5, C-4 (audit/integrity), P-6
- **question-refs:** QB-arch-06 (adjacent), domain-guide KEEP
- **coordinate:**
- **evidence:** `db/models.py@c6e0437`: 26 `__tablename__` declarations; FKs carry explicit `ondelete=` choices (CASCADE for owned children, SET NULL for `tag` refs — `:190`); `ApplicationBullet.bullet_id` deliberately has **no** cascade with an inline rationale ("deleting a referenced bullet must fail. Retire instead via Bullet.is_active = 0", `:603-605`); CHECK constraints with named keys (`ck_tag_kind` :199, etc.).
- **the finding:** The deletion semantics are reasoned per edge rather than blanket-cascaded, soft-retire is preferred over destructive delete on audit-bearing rows, and constraints are named (so migrations can target them). This is above-bar for a local single-user app and directly serves the audit-trail posture (D-5). Affirm so it survives the typing ratchet / blueprint churn untouched. (Minor: the domain guide's "19 ORM tables" is itself stale — the real count is 26; the layer is larger and more mature than the guide stated.)

### F-arch-07 — Audit-trail spine is real and inspectable (KEEP / BOOST-8 verified)
- **id:** F-arch-07
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** D-5, C-4
- **question-refs:** QB-arch-07, map-BOOST-8 (verify)
- **coordinate:**
- **evidence:** `hardening.save_iteration_context()` (`hardening.py:1221`) writes a new child context and sets `child["parent_context_path"] = parent_path` (`:1259`); the `parent_context_path` field is a typed contract member (`:124`). `_within()` containment governs reads/writes (per architecture.md:639-651 and the `_within` guards cited in eval tooling, architecture.md:209-region). PROMPT_VERSION stamping (`analyzer.py:268`, `effective_prompt_version()` :312, stamped at `:1003`) and per-call cost logging (`log` to `logs/llm_calls.jsonl`, `:328-332`) ride on every call.
- **the finding:** Map BOOST-8 ("audit-trail-by-default") is **confirmed**: each `/api/generate` writes a timestamped child, the parent chain is the iteration audit trail, every LLM call is prompt-versioned and cost-logged. This is a durable provenance spine and a real exhibit for A-4. Affirm and protect under refactor.

### F-arch-08 — Migrations are SQLite-correct, but no forward/downgrade path is tested against a populated DB
- **id:** F-arch-08
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** P-6 (long-lived local DB across public release), D-5, S-1 (data integrity-adjacent)
- **question-refs:** QB-arch-06, QB-qe-rel-05
- **coordinate:**
- **evidence:** Schema ends at `0007_tracker_status_cleanup.py` (`db/migrations/versions/`); migration style is correct (`batch_alter_table("application", recreate="always")` upgrade :53 / downgrade :73; `downgrade()` present :61). `init_db()` only ever runs `alembic upgrade head` (`db/session.py:108-133`). The only migration test (`tests/test_db_session.py:54-68`) asserts a **fresh** temp DB reaches head with 27 tables — it never upgrades from a pre-populated older revision and never exercises a `downgrade()` round-trip.
- **the finding:** The written downgrade paths and the `recreate="always"` table rebuilds are unexercised in CI. For a single-user local SQLite the blast radius is bounded (no concurrent writers; recreate-always rebuilds cleanly), so this is WATCH not FIX — but across a public release a user's long-lived DB relies on the *next* forward migration being correct first-try on real data, and there is no test that seeds an `0006`-era DB and upgrades it. A cheap de-risk before v1.1.0: one test that builds a DB at revision N-1 with a few rows and asserts `upgrade head` preserves them. Tracked under WS-2/WS-3 recurring lanes, not a tag blocker.

### F-arch-09 — W-4 "modularize-in-place" is practiced but the `recall/` evidence is design-only at the pin
- **id:** F-arch-09
- **disposition:** WATCH
- **leverage:** P3
- **charter-trace:** W-4
- **question-refs:** QB-arch-04, map-BOOST-4 (verify)
- **coordinate:** WS-4b / v1.0.7 (memory extraction lane)
- **evidence:** `run_suite()` extraction is real and merged (`3a91bea` "extract run_suite() core"; `evals/runner.py:836` `def run_suite` separate from `:1415 def main`). But `recall/` is **not committed** at c6e0437 (`git ls-tree -r c6e0437 | grep recall` → empty); it exists only as a design in `docs/dev/memory-architecture.md`. The domain guide and map-BOOST-4 cite "`recall/` package" as in-place evidence.
- **the finding:** W-4 is genuinely practiced — the `run_suite()` byte-identical-style extraction and the documented directional seams are real — so map-BOOST-4 holds *on those grounds*. But the specific "`recall/` package extracted-in-place" evidence is premature: it is a design artifact, not code, at the pin. When the BOOST-4 pattern graduates to governance, cite `run_suite()` + the deterministic-module seams as the landed evidence and mark `recall/` as planned, so the rubric doesn't rest on uncommitted code. Low leverage; framing accuracy only.

### F-arch-10 — Typed-spine ratchet (WS-2) is mid-flight; mypy is partial-strict, appropriate for the pin
- **id:** F-arch-10
- **disposition:** KEEP
- **leverage:** P3
- **charter-trace:** P-6, A-4
- **question-refs:** (general code-health)
- **coordinate:** post-public WS-2 ratchet; v1.0.8 absorbs the route-return type scan (PV-4)
- **evidence:** `pyproject.toml:107-118` — mypy runs with `strict_optional`, `warn_redundant_casts`, `warn_unused_ignores`, `no_implicit_reexport`, `follow_imports=silent`, third-party `ignore_missing_imports` — but **not** full `strict = true`. CI runs `mypy .` (`ci.yml:39`). RELEASE_ARC scopes WS-2 (strict-typing ratchet + typed `context_set`) as a recurring post-public lane and folds the route-return scan (PV-4) into the v1.0.8 split.
- **the finding:** The typing posture is deliberately incremental, not lax — `mypy .` is in the gate and the strict ratchet is explicitly a separate recurring epic, not a v1.1.0 blocker. This matches S-2 ("incomplete-for-elegance acceptable in user-capabilities") and the P-6 stability horizon. Affirm the current bar as appropriate for the pin; the finding is to confirm WS-2 stays a tracked lane (it is) rather than silently sliding, and that PV-4's route-return scan lands *with* the blueprint split so no untyped route body slips through during the move.

---

## Appendix (beyond the ~10 register cap)

### A-arch-01 — Dashboard blueprint already demonstrates the split is viable
- **disposition:** KEEP / context
- **evidence:** `dashboard/routes.py:28` `Blueprint("dashboard", ...)`, registered into `app`; `app` imports the blueprint, not vice versa. The diagnostics surface already lives behind a blueprint with a localhost host-header guard.
- **note:** Concrete proof the app-factory/blueprint pattern composes here; the v1.0.8 split is extending an existing seam, not inventing one. Lowers the W-4/P-6 risk for the split. (The security-lint coverage gap from F-arch-03 is the one thing this existing blueprint already exposes.)

### A-arch-02 — `init_db()` per-process caching rationale is documented (integrity nicety)
- **disposition:** KEEP
- **evidence:** `db/session.py:112-124` documents that alembic's `command.upgrade()` mutates module-level globals, so `init_db` caches by resolved db_path and is idempotent per (process, path). Comment dated 2026-05-26.
- **note:** A non-obvious SQLite/alembic footgun handled deliberately with an inline why — consistent with the codebase's "reason per edge" discipline.

### A-arch-03 — `analyzer.py` at 2,890 LOC is the next monolith after `app.py`
- **disposition:** WATCH
- **evidence:** `analyzer.py` = 2,890 LOC at the pin; it owns all prompt constants, all call kinds, streaming + non-streaming wrappers, the prompt-override registry, telemetry, and the scope-check classifier.
- **note:** Not in the v1.0.8 scope (which targets `app.py`) and not a blocker — but as the sole C-6 caller it is the single most security-sensitive file, and its size will eventually warrant the same modularize-in-place treatment (prompts vs. call-mechanism vs. telemetry seams). Flag for a future W-4 window, post-public; keeping the *call mechanism* in one place is the invariant to preserve even if prompts move out.

### A-arch-04 — Domain-guide stat corrections (housekeeping)
- **disposition:** context
- **evidence/note:** Two figures in the domain guide are themselves stale vs c6e0437: "19 ORM tables" (actual 26) and the framing that direct `import app` "greps to 0 in tests" (true for top-level `import app`, but 24 test files import it via deferred `import app as _app` inside fixtures). Neither changes a finding; recorded so the Phase-3 register and any governance graduation use the corrected numbers.

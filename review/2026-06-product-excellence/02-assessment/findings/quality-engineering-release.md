---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Quality engineering & release discipline

> Domain assessor for the 2026-06 pre-v1.1.0 product-excellence review.
> Severity anchor: the SIGNED Product Charter. C-0 discipline observed —
> mechanism/effort language, no absolutes about LLM behavior.

## Domain verdict

callback.'s quality engineering is genuinely strong where the charter's
*deterministic* claims live: the deterministic↔LLM boundary (C-6) holds at the
pin, migrations are exercised forward through the real alembic chain, the
deterministic modules are well-tested, CI is least-privilege across a 3.11–3.13
matrix, and the perf work is provenance-traced. The release *discipline* is also
mature — defect-vs-expected settled first, every fix ships a dated regression
test, paid surfaces are consent-gated. The gap is precise and charter-traced:
**the two categorically-claimed clauses (C-2 egress, C-6 boundary) have no
deterministic enforcer wired into the gate**, the a11y/PDF tier (E-2's
machine-checked taxonomy) silently skips in CI because Chromium is never
installed, **none of the agreed E-2 machine badges exist at the pin**, and one
D-4-violating human SLA is still shipped in two docs. These are the difference
between "claims kept honest by a test" (the charter's bar) and "claims kept
honest by reviewer vigilance."

Dynamic checks run (sandboxed, this clone, no paid calls): `pytest` on
`test_db_session` + `test_app_security` + `test_hardening` + `test_pdf_render`
(113 passed); `pytest -m a11y` (4 passed — Chromium IS present in this clone, so
the gate is real and works *when the browser exists*); `pytest --collect-only`
(1075 tests); AST-free grep of the seven deterministic modules for
`analyzer`/`anthropic` imports (all clean); workflow/file-existence audit for
the E-2 badge set. The CDN/scrape "verify-landed" checks below are witness-only
(already ruled).

---

## Register (highest leverage first)

### F-qe-01 — C-2 egress has no machine-falsifiability test; the only network test stubs the scraper
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** C-2, C-0, E-2
- **Question refs:** QB-qe-rel-03 (also QB-sec-01)
- **Finding:** The charter calls C-2 "machine-verifiable" and lists a committed
  network-egress falsifiability test among the agreed E-2 badge measures. No such
  test exists at the pin. The only network-shaped test, `tests/test_scraper.py:53`,
  monkeypatches `scraper.requests.get` to assert the scraper's URL-shaping — that
  proves the *scraper's* behavior, not that no other code path opens a socket to a
  non-sanctioned destination. C-0 makes "a categorical claim with no deterministic
  enforcer" the cardinal sin, and C-2 (no egress beyond the two sanctioned classes)
  is exactly such a claim. A process-wide socket-deny / route-allowlist test
  (assert only `api.anthropic.com` + the opt-in scrape host can be reached) would
  convert C-2 from audit-by-hand to continuous enforcement and is the single
  highest-leverage gate this domain can add — it directly answers the S-1 PII fear
  with a test.
- **Evidence:** `tests/test_scraper.py:53@c6e0437` (`monkeypatch.setattr("scraper.requests.get", ...)`); no `socket`/allowlist deny test in `tests/` (grep of `pytest_socket|disable_socket|block_network|allowlist` returns only stub-monkeypatch hits); charter C-2 L98 ("machine-verifiable — and **was verified at `c6e0437`**" — by hand, not by a committed gate)
- **Coordinate:** v1.0.7 pre-public hardening / E-2 badge set

### F-qe-02 — The a11y/PDF/paged.js tier silently skips in CI (Chromium never installed)
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** E-2, A-2
- **Question refs:** QB-qe-rel-01 (also QB-exp-a11y-01)
- **Finding:** CI's `quality` job runs bare `pytest` (`ci.yml:42`) with no
  `playwright install chromium` step, and the default `addopts` carry no
  `-m "not ux"` filter — so CI *collects* the ux/a11y tests but the session-scoped
  `_browser` fixture calls `pytest.skip` when the binary is absent
  (`conftest.py:80,85`). The axe a11y gate (E-2's "machine-checked taxonomy in CI,
  free forever") and the *only* end-to-end PDF/paged.js coverage therefore run on
  the maintainer's machine alone, never as a required check on a PR. I confirmed
  behaviorally that the gate is real and passes *when Chromium is present*
  (`pytest -m a11y` → 4 passed in this clone), so the fix is purely a CI step, not
  new test construction. This blocks the explicit E-2 commitment and leaves the
  regression cliffs the LLM-stubbed unit suite cannot catch (PDF render, axe
  contrast/name, reflow) unguarded on every PR.
- **Evidence:** `.github/workflows/ci.yml:42@c6e0437` (`run: pytest`, no Chromium install); `pyproject.toml:125` (`addopts = "-v --tb=short"` — no ux exclusion); `tests/ux/conftest.py:85@c6e0437` (`pytest.skip("Chromium not installed …")`); dynamic: `pytest -m a11y` → 4 passed here
- **Coordinate:** Sprint 6.5 (a11y/education) / E-2 badge set

### F-qe-03 — None of the agreed E-2 machine badges exist at the pin
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** E-2, C-0
- **Question refs:** QB-qe-rel-02 (also QB-sec-06, QB-sec-07)
- **Finding:** The charter's agreed badge set (E-2) is lockfile + Dependabot,
  OpenSSF Scorecard, REUSE, the egress falsifiability test, and one-time Private
  Vulnerability Reporting. At the pin: no `requirements*.txt`/`poetry.lock`/`uv.lock`
  (dependencies are unpinned semver ranges in `pyproject.toml`, plus an unpinned
  VCS dep `minicheck @ git+https://...` in the `eval-grounding` extra); no
  `.github/dependabot.yml`; no Scorecard workflow; no `LICENSES/` dir or `.reuse`
  config; no `PRIVACY.md`. Each absent badge maps to a specific claim it would
  enforce — lockfile+Dependabot to supply-chain integrity (S-1-adjacent), REUSE to
  vendored-license honesty (the MPL-2.0 `axe.min.js`, see F-qe-07), the egress test
  to C-2 (F-qe-01). E-1 directs pursuing every badge-able external measure; these
  are the machine-run ones the charter already filtered *to*, so they are not
  cargo-cult. Note the discipline is correct in the negative direction too: no
  coverage-% / SLSA / ATS-score vanity badge exists (the DEBUFF set is correctly
  absent).
- **Evidence:** `pyproject.toml@c6e0437` deps are ranges (`flask>=3.0,<4.0` …) + `minicheck @ git+https://github.com/Liyan06/MiniCheck.git`; `ls` shows no lockfile, no `.github/dependabot.yml`, no `.github/workflows/scorecard.yml`, no `LICENSES/`/`.reuse`, no `PRIVACY.md` at the pin; `.github/workflows/` contains only `ci.yml`
- **Coordinate:** v1.0.7 pre-public hardening

### F-qe-04 — C-6 boundary holds at the pin but is enforced by convention, not by a gate
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** C-6, C-0
- **Question refs:** QB-qe-rel-06 (also QB-arch-01/02)
- **Finding:** C-6 ("deterministic modules make no LLM calls") is a charter
  *inviolable*. I verified it holds at the pin: none of the seven modules
  (`hardening`, `parser`, `generator`, `scraper`, `json_resume`,
  `corpus_to_json_resume`, `pdf_render`) import `analyzer` or `anthropic`. But the
  hold is by behavior + reviewer vigilance + CHANGELOG assertion, not by
  construction — there is no test or import-linter that *fails the build* if an LLM
  import appears in those modules (no `grimp`/`import-linter` in `pyproject.toml`,
  no boundary test in `tests/`; `route-security-lint` guards the security gate, not
  the LLM boundary). Per C-0, a categorical claim earns the absolute only where a
  deterministic test holds it by construction. An ~10-line AST/import test over the
  seven modules (assert no `analyzer`/`anthropic`/`anthropic.*` import) would make
  C-6 self-enforcing and is the cheapest gate in the inventory. This is the
  qe-rel-side complement to QB-arch-01 (arch asks "does an enforcer exist"; this
  asks "is it wired into the gate" — answer to both: no).
- **Evidence:** dynamic grep of the seven modules for `^\s*(import|from)\s+(analyzer|anthropic)` → all clean@c6e0437; `pyproject.toml@c6e0437` has no import-linter/grimp; no boundary test among the 60 files in `tests/`; `docs/architecture.md` C-6 is prose + per-CHANGELOG assertion
- **Coordinate:** v1.0.8 blueprint split (the split moves route bodies; a boundary gate protects C-6 across the move)

### F-qe-05 — Migrations exercised forward (KEEP); but no data-bearing upgrade is tested
- **Disposition:** KEEP
- **Leverage:** P2
- **Charter trace:** P-6, D-5
- **Question refs:** QB-arch-06 (qe-rel slice)
- **Finding:** Affirm and protect: `init_db()` runs the real alembic
  `command.upgrade(cfg, "head")` chain (`db/session.py:151`) over all seven
  versions, and `test_db_session.py:54` (`test_creates_all_tables`) asserts the head
  schema (27 tables) *through that path* — not `create_all()`. This is the right
  shape for a long-lived local DB across a public release and should not be churned.
  The one gap (BOOST opportunity per the domain rubric, not a defect): the suite
  proves the chain *reaches* head, not that a *data-bearing* migration transforms
  rows. `0005_curate_bundled_templates.py` is exactly such a migration (drops the
  Compact row, renames Hybrid Tech, FK-NULLs referencing runs — the 5→4 template
  curation). A test that pre-populates the pre-0005 rows, upgrades, and asserts the
  transformation (row dropped, FK NULLed, count = 4) would guard the only class of
  migration that can silently corrupt a real user's DB on upgrade.
- **Evidence:** `db/session.py:151@c6e0437` (`command.upgrade(cfg, "head")`); `tests/test_db_session.py:54-66@c6e0437` (schema-reaching assertion, `assert n == 27`); `db/migrations/versions/0005_curate_bundled_templates.py@c6e0437` (data-bearing, FK ON DELETE SET NULL); dynamic: `pytest tests/test_db_session.py` → 6 passed
- **Coordinate:**

### F-qe-06 — Perf-regression "gate" is a manual tuning-time loop, not a wired CI gate; two-pass split is synthetic-only measured
- **Disposition:** WATCH
- **Leverage:** P2
- **Charter trace:** T-D, M-2, E-1
- **Question refs:** QB-qe-rel-04
- **Finding:** The perf baselines are excellent and provenance-traced to
  `logs/llm_calls.jsonl` (1,824 calls) — a genuine strength. But the "eval gate"
  described in `PERFORMANCE_HISTORY.md` §"How we measure" is a *manual* tuning-time
  scoring loop (Haiku judge, n=3-5, maintainer runs `evals/runner.py`), not an
  automated CI gate: CI's only eval job is the label-gated `eval-smoke` (grounding
  only, requires the `eval` PR label + `ANTHROPIC_API_KEY`), and no workflow
  enforces a p50/cost floor. The doc credits the `.2→.3` cache regression to being
  "caught in the telemetry" — i.e. by a human reading the log, the exact silent
  break a committed floor (anchor-suite p50/cost vs a checked-in number, off
  existing telemetry, no paid call needed) would catch automatically. Separately,
  the two-pass split numbers are synthetic-only measured (the T-D gap in numeric
  form). WATCH not FIX: a perf gate is post-public-acceptable and the manual loop is
  real discipline; flagged so it is a tracked task, not assumed automated.
- **Evidence:** `docs/dev/perf/PERFORMANCE_HISTORY.md` §"How we measure" item 3 ("merge is **blocked**" — but the mechanism is the human-run judge, no CI hook); `.github/workflows/ci.yml:44-66@c6e0437` (`eval-smoke` is `if: contains(... labels … 'eval')`, grounding-only); grep of `.github/` for `perf|latency|p50` → only `PULL_REQUEST_TEMPLATE.md`
- **Coordinate:** v1.0.7 PV-2 grounding calibration

### F-qe-07 — Vendored-license honesty is human-readable but not machine-declared (REUSE gap)
- **Disposition:** FIX
- **Leverage:** P2
- **Charter trace:** E-2, D-5
- **Question refs:** QB-sec-06 (qe-rel slice of QB-qe-rel-02)
- **Finding:** The vendored `axe.min.js` is MPL-2.0 (not MIT); its license is
  honestly disclosed in `tests/ux/a11y/vendor/README.md:9` and `CHANGELOG.md`, and
  the full MPL notice is preserved at the top of the file — exemplary at the
  human-readable level (a partial KEEP). But the top-level `LICENSE` is MIT-only,
  and there is no SPDX/REUSE machine declaration, so any automated license scan
  (REUSE lint, Scorecard's License check) sees an under-declared repo. The
  to-be-vendored Chart.js (PX-01, MIT) compounds this. REUSE config + per-file SPDX
  headers (or a `LICENSES/` + `.reuse/dep5`) is the concrete thing the E-2 REUSE
  badge would force and is the lowest-effort badge to earn given the disclosure
  discipline already in place.
- **Evidence:** `tests/ux/a11y/vendor/axe.min.js` header (`Mozilla Public License, v. 2.0`, Deque © 2015-2024)@c6e0437; `tests/ux/a11y/vendor/README.md:9@c6e0437` ("License: MPL-2.0"); `LICENSE@c6e0437` (MIT only); no `LICENSES/`/`.reuse`/SPDX headers at the pin
- **Coordinate:** v1.0.7 pre-public hardening; coordinate with PX-01 (vendor Chart.js)

### F-qe-08 — D-4-violating human SLA still shipped in SECURITY.md and CODE_OF_CONDUCT.md
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** D-4, P-3
- **Question refs:** QB-qe-rel-07 (also QB-sec-05)
- **Finding:** D-4 (commitments hygiene) requires hard human SLAs softened to
  best-effort wording; the posture directive is explicit that promises which create
  recurring obligations on the owner's life get retired. `SECURITY.md:134-135` still
  reads "We aim to respond within 5 business days and to issue a fix within 30 days
  of confirmation" — a hard SLA. The same 5-business-day promise survives in
  `CODE_OF_CONDUCT.md:15` ("The maintainer will respond within 5 business days").
  Both are wording fixes (no code), but they are the literal class of commitment the
  charter's posture directive names, and S-1 ranks "amateurish planning" second only
  to PII leak — shipping a contractual SLA a solo maintainer can't reliably honor is
  exactly that risk. Note `SECURITY.md:58` already uses "best-effort" for the scrape,
  so the house style for the fix exists.
- **Evidence:** `SECURITY.md:134-135@c6e0437`; `CODE_OF_CONDUCT.md:15@c6e0437`; charter D-4 L169-173 (existing 5-business-day promise named explicitly as the thing to soften)
- **Coordinate:** v1.0.7 pre-public hardening

### F-qe-09 — M-2 binding tag evidence is not in the Phase 5 tag-criteria checklist
- **Disposition:** FIX
- **Leverage:** P1
- **Charter trace:** M-2, T-D, D-4
- **Question refs:** QB-qe-rel-05
- **Finding:** M-2 is the charter's written, self-imposed v1.1.0 tag evidence (≥10
  real applications across a composition matrix with zero release-blocking bugs;
  tuning loop exercised end-to-end with at-a-glance metrics; two first-run bars
  evidenced; explainability artifacts shipped). The RELEASE_ARC Phase 5 tag-criteria
  list (`RELEASE_ARC.md:793-814`) carries only the lighter set — visual assets,
  fresh-clone < 5 min, GitHub live, type-scan-held, "user judges showcase-ready."
  The M-2 real-corpus work IS tracked elsewhere in the arc (Phase 4.5 walkthrough,
  PV-1 `eval/live-shakedown-labels` at v1.0.7), so this is not "unplanned" — it is a
  *checklist completeness* gap: the binding M-2 gate isn't reflected where a closing
  agent reads the v1.1.0 tag criteria, risking a tag that meets §793 but not M-2.
  The release pass itself is correctly D-4-shaped (one-time machine+human evidence,
  no recurring SLA smuggled in) — that part is a KEEP; the fix is to surface M-2 in
  the Phase 5 checklist (or cross-reference it explicitly) so the two cannot drift.
- **Evidence:** `docs/dev/RELEASE_ARC.md:793-814@c6e0437` (tag-criteria list — no ≥10-apps / tuning-loop / first-run-bar / owner-blind-A/B line); charter M-2 L263-279 (the binding evidence); M-2 traceable in arc only at L432/L712 (Phase 4.5 / PV-1), not Phase 5
- **Coordinate:** v1.0.8 → v1.1.0 (the arc's own Phase 5)

### F-qe-10 — Release discipline patterns are exemplary — affirm so they aren't churned
- **Disposition:** KEEP
- **Leverage:** P2
- **Charter trace:** E-1, S-2, A-4
- **Question refs:** QB-qe-rel-02 (DEBUFF-avoidance side), map BOOST-6/7
- **Finding:** Affirm the practices that make the gaps above narrow rather than
  systemic: (a) least-privilege CI (`permissions: contents: read`, `ci.yml:9-10`)
  across a genuine 3.11/3.12/3.13 matrix; (b) defect-vs-expected settled before
  fixing — the v1.0.6 sprints repeatedly verified bugs reproduced (template-count
  was stale not broken, cost-chart "does not reproduce as stated") before touching
  code; (c) every walkthrough fix ships a dated `tests/ux/regression/test_YYYYMMDD_*`
  guard; (d) paid eval/tune routes are localhost-only with `confirm()` cost-band
  gating + eager 4xx before spend; (e) the `eval-smoke` CI job is correctly
  label-gated and secret-scoped so paid runs never fire on every PR. These are the
  difference between a solo repo that *looks* disciplined and one that *is*; the
  review should protect them from refactor churn, not just the code.
- **Evidence:** `.github/workflows/ci.yml:9-10,13-18@c6e0437` (least-priv + matrix); `ci.yml:44-66` (label+secret-gated eval-smoke); map BOOST-6/7/9 candidates (verified: regression-test-per-fix pattern present across `tests/ux/regression/`); 1075 tests collected at the pin
- **Coordinate:**

---

## Appendix (beyond the ~10 register cap)

### A-qe-01 — C-2 v1.0.6 fixes: verify-landed status at the pin (witness only, already ruled)
- **Disposition:** WATCH (verify-landed, not re-litigated)
- **Charter trace:** C-2(i)(iii)
- These were RULED 2026-06-12 (fix v1.0.6, which is in-flight/not tagged at the
  pin). Confirmed NOT yet landed at `c6e0437`, as expected: Chart.js still loads
  from `cdn.jsdelivr.net` at runtime (`dashboard/templates/dashboard.html:15`,
  SRI-pinned but real third-party egress; `static/vendor/` holds only
  `paged.polyfill.js`, no chart); `scraper.fetch_url_content` has no caller in
  `app.py` (dead code). No action for this review beyond noting the prescriptions
  (PX-01, PX-02) remain open at the pin and their landing should be a v1.0.6 gate.
  Cross-ref QB-sec-04.

### A-qe-02 — `minicheck` unpinned VCS dependency in the eval-grounding extra
- **Disposition:** WATCH
- **Charter trace:** D-1, D-6
- `pyproject.toml` `eval-grounding` extra pins `minicheck @ git+https://github.com/Liyan06/MiniCheck.git`
  with no commit/tag — a moving target for the power-user tuning install (D-6
  opt-in). Low blast radius (opt-in extra, not the base path), but a lockfile / `@`-ref
  pin would harden the reproducibility of the one install that already pulls ~3.2GB
  of weights. Folds into F-qe-03's lockfile prescription.

### A-qe-03 — `pyproject.toml` version is 1.0.5 at the pin
- **Disposition:** WATCH
- **Charter trace:** (housekeeping)
- `pyproject.toml:version = "1.0.5"` while the map places the pin mid-v1.0.6.
  Expected (v1.0.6 untagged), noted only so the eventual v1.1.0 `chore/release`
  branch (`RELEASE_ARC.md:791`) is the single place the version bumps — no drift
  risk at the pin.

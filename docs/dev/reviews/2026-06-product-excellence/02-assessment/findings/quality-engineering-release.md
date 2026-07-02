---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Quality engineering & release discipline — findings

> Severity anchor: the SIGNED Product Charter. A gap matters only insofar as
> it blocks a charter clause. C-0 discipline honored throughout — mechanisms
> and effort language, no absolutes about LLM behavior. Evidence pinned at
> c6e0437 via git show / git ls-tree (worktree HEAD b85be08 carries review
> commits on top; all code evidence read at the pin).

## Domain verdict

sartor. has a genuinely strong quality core: a py3.11-3.13 CI matrix with
least-privilege permissions, a real alembic-to-head migration test, a
provenance-traced perf baseline with real-corpus columns, and the standout
an eval-quality regression gate that exits non-zero on a rubric drop > 0.5.
That gate is the kind of machine enforcement the charter (E-1, C-0) prizes.
But the release-discipline perimeter has structural holes: the entire
UX/a11y/PDF-render tier silently skips in CI (no Chromium install), the two
clauses the charter calls machine-verifiable are not machine-enforced (C-2
egress has no committed falsifiability test; C-6 holds by AST-confirmed
convention but no gate fails on an LLM import), none of the agreed E-2
machine badges exist (no lockfile, Dependabot, Scorecard, REUSE, egress
test, PVR), and two hard human SLAs still ship in violation of D-4. The
throughline: where a claim is categorical, the enforcer is usually absent —
exactly the C-0 cardinal sin — so the v1.1.0 public tag should not land
until the inviolable-clause gates exist.

---

## Register (highest leverage first)

### F-qe-rel-01 — UX/a11y/PDF tier silently skips in CI; the E-2 "machine-checked in CI, free forever" promise is local-only
- disposition: FIX
- leverage: P0
- charter-trace: E-2, A-2, C-5 (PDF/ATS render path)
- question-refs: QB-qe-rel-01, QB-exp-a11y-01 (x-ref), DEBUFF-1 (verified)
- evidence: .github/workflows/ci.yml:30-42@c6e0437 — the quality job installs
  .[dev] and runs ruff/mypy/pytest with no playwright-install-chromium step.
  tests/ux/conftest.py:80-87@c6e0437 pytest.skips the whole UX tier when
  Chromium is absent; tests/test_pdf_render.py:320-325,382-387@c6e0437 guard
  the two real-PDF end-to-end classes with skipif(not _chromium_available()).
  CI default pytest (pyproject addopts="-v --tb=short", no -m "not slow")
  collects those slow tests but they skip for want of the binary.
- finding: The agreed E-2 promise is "machine-checked taxonomy in CI, free
  forever." At the pin no required CI check exercises the axe a11y gate, the
  paged.js/PDF render path, reflow/zoom, contrast, or tab-order — they run
  only on the maintainer machine. The LLM-stubbed unit suite cannot catch a
  PDF-render regression, an axe contrast/name regression, or a reflow break;
  every PR merges with those paths unguarded. The docstring at
  test_pdf_render.py:13 ("CI is configured to run it") and RELEASE_ARC.md:18
  ("gate green incl. pytest -m ux") both overstate CI actual coverage — the
  gate is a local maintainer step, not a CI check. Fix is a CI job that
  installs Chromium and runs pytest -m ux as a required check.
- coordinate: Sprint 6.3 landed the axe gate; this is the CI-wiring
  follow-on. Touches the v1.0.7 pre-public hardening lane and the v1.1.0
  fresh-clone release pass.

### F-qe-rel-02 — C-2 (no egress beyond two sanctioned classes) is asserted, not machine-falsifiable
- disposition: FIX
- leverage: P0
- charter-trace: C-2, C-0, E-2, S-1
- question-refs: QB-qe-rel-03, QB-sec-01 (x-ref)
- evidence: No egress/allowlist/socket test exists at the pin — git ls-tree
  -r c6e0437 -- tests/ returns no egress/network/allowlist file. The only
  network-shaped test stubs the scraper: tests/test_scraper.py:53@c6e0437
  monkeypatches scraper.requests.get and asserts the URL shape — it proves
  the scraper behavior, not that no other socket opens.
  tests/test_app_security.py@c6e0437 asserts the filesystem route guards only
  (no socket/host assertions).
- finding: The charter calls C-2 "machine-verifiable and was verified at
  c6e0437" — but that verification was a one-time human code audit, not a
  standing gate. The destination set is enumerable (configured provider +
  opt-in scrape), which is exactly what makes a committed falsifiability test
  feasible: a socket/transport allowlist that fails the build on any outbound
  destination outside the two sanctioned classes. Without it, the C-2 "ever"
  is an unenforced absolute (C-0 violation) and S-1 (the owner number-one
  release fear, PII leak) rests on prose. This is the single highest-value
  BOOST the charter names for this domain.
- coordinate: Pairs with the PX-01 Chart.js vendoring (v1.0.6) — once the
  last runtime CDN is gone, the allowlist has a clean enumeration to assert
  against.

### F-qe-rel-03 — None of the agreed E-2 machine badges exist at the pin
- disposition: FIX
- leverage: P1
- charter-trace: E-2, C-0, D-1
- question-refs: QB-qe-rel-02, QB-sec-06/07 (x-ref)
- evidence: At c6e0437: no .github/dependabot.yml (git ls-tree .github/ shows
  only ISSUE_TEMPLATE/, PULL_REQUEST_TEMPLATE.md, workflows/ci.yml); no
  Scorecard workflow; no LICENSES/ dir, no .reuse/REUSE.toml; no committed
  egress test; root LICENSE is MIT-only. Dependencies float by range, no
  lockfile (pyproject.toml dependencies all >=X,<Y; no
  requirements*.txt/*.lock). The vendored tests/ux/a11y/vendor/axe.min.js
  carries an MPL-2.0 header (axe v4.10.2) the MIT-only LICENSE does not
  declare at the machine-readable level.
- finding: The agreed E-2 set — lockfile+Dependabot, OpenSSF Scorecard,
  REUSE, the network-egress test, one-time PVR — is the charter "right
  badges, none of the cargo-cult ones." All five are absent. Each enforces a
  stated claim: lockfile/Dependabot makes CI reproducible and supply-chain
  drift visible (D-1 minimal-deps hygiene); REUSE forces honest declaration
  of the vendored MPL-2.0 file (the per-file notice is preserved, so this is
  under-declaration, not a hidden violation — P1/P2, not P0); the egress test
  is F-qe-rel-02. Build the machine-run set; skip the theater (coverage-%,
  SLSA-before-artifacts, ATS-score) per the DEBUFF rule.
- coordinate: Naturally batches with the v1.1.0 fresh-clone / GitHub-push
  release branch (release/fresh-clone-v1-1-0, chore/release-v1.1.0).

### F-qe-rel-04 — C-6 deterministic-LLM boundary holds by convention; no gate fails on an LLM import
- disposition: FIX
- leverage: P1
- charter-trace: C-6, C-0
- question-refs: QB-qe-rel-06, QB-arch-01/02 (x-ref)
- evidence: AST-inspected all seven deterministic modules at the pin
  (hardening, parser, generator, scraper, json_resume,
  corpus_to_json_resume, pdf_render) — zero direct analyzer/anthropic imports
  (dynamic check, below). No boundary/import-lint test exists (git ls-tree
  tests/ has no boundary file); pyproject.toml has no import-linter/grimp. The
  CHANGELOG-asserts-it pattern and the route-security-lint hook guard
  security, not the LLM boundary.
- finding: C-6 is the charter "inviolable" boundary, and at the pin it
  genuinely holds — but by reviewer vigilance + CHANGELOG convention, not by
  construction. C-0 says a categorical claim must have a deterministic
  enforcer; this one has none. A ~15-line AST test (or an import-linter
  contract) that fails the build when any of the seven modules imports
  analyzer/anthropic (directly or transitively) converts an honored
  convention into a machine-held invariant. Cheap, high-symbolic-value, and
  exactly the kind of gate E-1 prefers over recurring vigilance.
- coordinate: Land before the v1.0.8 blueprint split — a refactor that moves
  code across modules is precisely when a silent boundary breach could slip
  in unnoticed.

### F-qe-rel-05 — Eval-quality regression gate exists and blocks; affirm it (do not churn)
- disposition: KEEP
- leverage: P1
- charter-trace: E-1, C-0, C-3, M-2
- question-refs: QB-qe-rel-04 (partial), BOOST (eval-gate-blocks-quality)
- evidence: evals/runner.py:99@c6e0437 REGRESSION_DELTA=0.5; :480-501
  _detect_regression flags is_regression = delta < -REGRESSION_DELTA against
  the baseline_v1.json 5-run aggregate mean (:382,397-409); :1403 exit_code=0
  if (n_fail==0 and not regressions) else 2; main() propagates via
  sys.exit(main()) (:1530). The eval-smoke CI job runs it (ci.yml:44-66).
- finding: This is a real machine gate, not a narrative: a candidate prompt
  that drops any (fixture x rubric) score by > 0.5 vs the committed baseline
  causes a non-zero exit and fails the CI job. The 0.5 threshold is
  deliberately sized to judge variance (runner.py:95-98). This is the charter
  preferred shape — machine-run, keeps itself honest, off existing telemetry.
  Affirmed so it is not refactored away. Two bounded caveats keep it from
  P0-grade: it is label-gated (only runs when a PR carries the eval label —
  ci.yml:47), so a prompt change merged without the label is unguarded; and
  it is synthetic-fixture-only.
- coordinate: (none)

### F-qe-rel-06 — No automated perf-regression gate; perf is a strong narrative + a manual PR checklist
- disposition: WATCH
- leverage: P2
- charter-trace: T-D, M-2, E-1
- question-refs: QB-qe-rel-04
- evidence: docs/dev/perf/PERFORMANCE_HISTORY.md@c6e0437 carries p50 latency
  + cost per prompt_version sourced to logs/llm_calls.jsonl (1,824 calls;
  :14,48-51) and — overturning the domain-guide synthetic-only framing for
  the narrative — real-corpus columns (:67-97: synthetic vs
  demo/testuser/robert token + latency). But the only perf gate is the human
  PR checkbox PULL_REQUEST_TEMPLATE.md:61@c6e0437 (latency p50 > 20% =
  blocked); no automated guard exists (git grep for a perf gate in
  evals/runner.py / tests / CI returns only telemetry-emit lines, not an
  assertion).
- finding: The perf baselines are excellent and provenance-traced — the
  narrative is a strength. The gap is enforcement: the cheapest credible
  guard (anchor-suite p50/cost vs a committed floor, off the existing
  telemetry) would catch a silent cache break — the same drop the team caught
  by hand. Left as WATCH because the eval gate (F-qe-rel-05) already catches
  quality drops; a perf-only floor is opportunistic, not a tag blocker. The
  quality-side T-D gap (eval scores synthetic-only) is the sharper one — see
  F-qe-rel-07.
- coordinate: (none)

### F-qe-rel-07 — T-D not closed at the pin: eval/grounding gates run only on synthetic fixtures (real fixtures empty)
- disposition: WATCH
- leverage: P1
- charter-trace: T-D, M-2, C-3
- question-refs: QB-qe-rel-04, QB-qe-rel-05, QB-eval-02 (x-ref), DEBUFF-6
- evidence: evals/fixtures/real/.gitkeep@c6e0437 is the only entry — no real
  fixtures. PERFORMANCE_HISTORY.md:93-97@c6e0437 gate-on-synthetic and
  validate-on-real describes the design; the eval gate (F-qe-rel-05) seeds
  from baseline_v1.json synthetic anchors only. The green CI suite is
  LLM-stubbed end-to-end.
- finding: Every standing quality gate runs on frozen synthetic fixtures.
  This is correct for low-variance regression detection, but it means the
  suite cannot catch a regression that manifests only on a real corpus (PDF
  render at robert-scale 12.7k tokens, parser determinism on real docx,
  prompt drift). The charter accepts this tension (T-D) and scopes its
  closure to the v1.1.0 M-2 release pass (>=10 real apps + tuning loop
  exercised). The finding is not that synthetic gating is wrong — it is that
  functionally-complete-at-v1.1.0 remains unevidenced on real data at the
  pin, and the M-2 pass is the only thing that closes it. Track as a named
  release-blocking task, not a silent assumption.
- coordinate: v1.0.7 PV-1 (live-shakedown labels) / PV-2 (grounding
  calibration) consume the real-corpus labels; the v1.1.0 M-2 matrix is the
  closure event.

### F-qe-rel-08 — Two hard human SLAs still ship, in violation of D-4
- disposition: FIX
- leverage: P1
- charter-trace: D-4, P-3
- question-refs: QB-qe-rel-07, QB-sec-05 (x-ref)
- evidence: SECURITY.md:134-135@c6e0437 promises respond-within-5-business-
  days and fix-within-30-days-of-confirmation. CODE_OF_CONDUCT.md:15@c6e0437
  promises the maintainer will respond within 5 business days.
- finding: D-4 (commitments hygiene) requires public docs to make no
  response-time SLAs and no recurring human-labor promises; existing ones are
  softened to best-effort. Both promises are hard human SLAs on a solo
  project — exactly the obligation-that-consumes-its-owner risk P-3 and D-4
  guard against. SECURITY.md already uses best-effort wording elsewhere (:58
  best-effort, fails gracefully), so the fix is a small, consistent softening
  of two lines. Mechanical, but a charter-clause violation shipping publicly
  — should land before the public tag.
- coordinate: Batches with the C-2 doc corrections (PX-03, SECURITY/vision/
  README enumeration) already scheduled for v1.0.6.

### F-qe-rel-09 — Migration test reaches head but is not data-bearing; long-lived-DB upgrade unverified
- disposition: WATCH
- leverage: P2
- charter-trace: P-6, D-5
- question-refs: QB-arch-06 (x-ref), QB-qe-rel-05, BOOST (data-bearing migration)
- evidence: db/session.py:33-52@c6e0437 init_db() runs the real alembic
  command.upgrade(cfg, head) chain (KEEP — a genuine forward migration path,
  not create_all). tests/test_db_session.py:54-65@c6e0437
  test_creates_all_tables asserts the head schema reaches 27 tables through
  that path — but only the table count; no test asserts a data-bearing
  upgrade (e.g. a curation migration transforming existing rows on a
  pre-populated DB).
- finding: The migrate-to-head discipline is a strength and is affirmed. The
  gap, charter-relevant for a public release of a tool with a long-lived
  local DB (P-6 five-year horizon; D-5 auditable iterations): no forward
  migration is exercised against a realistic pre-populated DB, so a
  row-transforming migration that corrupts or drops existing user data on
  upgrade would pass CI. The domain-guide named BOOST (a migration test that
  asserts a data-bearing upgrade transforms rows, not just reaches head) is
  the closure. WATCH because no destructive migration is in flight at the
  pin; elevate to FIX if a 1.1.x migration touches existing rows.
- coordinate: (none)

### F-qe-rel-10 — CI matrix + least-privilege permissions + deterministic-module test set; affirm
- disposition: KEEP
- leverage: P2
- charter-trace: E-1, C-5, C-6
- question-refs: QB-qe-rel-01/06 (supporting)
- evidence: ci.yml:9-10@c6e0437 permissions: contents: read (least-privilege
  by default — a Scorecard-positive already in place); ci.yml:16-19
  py3.11/3.12/3.13 matrix with fail-fast: false. The deterministic-boundary
  (C-6) modules are genuinely tested — test_parser, test_scraper (network
  stubbed, :53), test_json_resume, test_ats_roundtrip (C-5 round-trip),
  test_corpus_to_json_resume, test_bundled_templates (C-5 template-count
  pin), the non-Chromium test_pdf_render HTML-render classes.
- finding: The unit-tier quality engineering is solid and matches the charter
  machine-run preference. The py3.11-3.13 matrix, the already-least-privilege
  CI token, and the deterministic-module + ATS-round-trip +
  bundled-template-count test set are real assets — named so they are not
  churned in the v1.0.8 blueprint refactor or a WS-3 suite pass. The gaps
  above are all additive (CI Chromium job, egress test, boundary gate,
  badges) — none require dismantling what works.
- coordinate: Protect through the v1.0.8 blueprint split (WS-1) and any WS-3
  test-suite engineering pass.

---

## Appendix (beyond the register cap)

### F-qe-rel-A1 — Eval-quality gate is label-gated, so unlabeled prompt PRs are unguarded
- disposition: WATCH | leverage: P2 | charter-trace: E-1, C-0
- evidence: ci.yml:47@c6e0437 gates the eval-smoke job on the PR carrying the
  eval label.
- finding: The strong eval regression gate (F-qe-rel-05) runs only when a
  human remembers to apply the eval label. A prompt change merged without it
  skips the gate entirely. The AGENTS.md PROMPT_VERSION-bump rule is a
  tribal/prose convention, not an enforced trigger. Consider auto-applying
  the eval label (or running the gate) when a PR touches analyzer.py /
  PROMPT_VERSION. Low-cost path-filter, closes a human-memory hole in an
  otherwise machine gate.

### F-qe-rel-A2 — Docstring/arc claims overstate CI actual UX/PDF coverage
- disposition: FIX | leverage: P3 | charter-trace: P-3, C-0
- evidence: tests/test_pdf_render.py:13@c6e0437 claims CI is configured to run
  it; RELEASE_ARC.md:18@c6e0437 claims the gate green incl. pytest -m ux —
  both describe coverage CI does not have (no Chromium install). The v1.0.5
  pytest -m ux green was a maintainer-local run.
- finding: A P-3 sources-and-describes-every-part-of-itself project should
  not carry a docstring asserting a CI behavior that does not exist. Correct
  the two lines as part of the F-qe-rel-01 CI-wiring fix (the claim becomes
  true once Chromium is installed in CI) or soften them now.

### F-qe-rel-A3 — Floating dependency ranges + no lockfile make CI non-reproducible
- disposition: WATCH | leverage: P2 | charter-trace: D-1, E-2
- evidence: pyproject.toml@c6e0437 all deps >=X,<Y; no requirements*.txt or
  *.lock at the pin.
- finding: Folded into the E-2 lockfile+Dependabot fix (F-qe-rel-03) but
  noted separately: with floating ranges and pip install -e .[dev] in CI, two
  CI runs of the same commit can resolve different transitive versions — a
  green build is not reproducible, and a transitive regression surfaces as
  flakiness, not a pinned diff. A lockfile (or a requirements.lock consumed
  in CI) closes this and is the substrate Dependabot needs.

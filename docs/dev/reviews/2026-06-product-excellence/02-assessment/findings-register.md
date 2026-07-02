---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings register — 2026-06 product-excellence review

> Master register for the eight-domain product-excellence assessment of
> **sartor.** Severity anchor: the SIGNED Product Charter
> (`../00-interview/product-charter.md`). All evidence pinned at
> `c6e0437`. Honors C-0 claims discipline (mechanism-and-effort language;
> no absolutes about LLM behavior).
>
> **Leverage tiers** are 10-Principles references (P0 = Survival, P1 =
> Hardening, P2/P3 = lower-altitude craft), used here as the review's
> priority axis. The **verdict** column carries the adversarial
> verification result for every P0/P1 finding (`-` for P2/P3, which were
> not adversarially re-verified). **WEAKENED** findings keep their place
> but MUST be read with the revised claim in
> [`verification-log.md`](verification-log.md) — the headline superlative
> or severity was trimmed even though the substance survived.
>
> Per-finding detail lives in [`findings/<domain>.md`](findings/);
> per-verdict detail (falsification attempt + counter-evidence + revised
> claim) in [`verification-log.md`](verification-log.md).

---

## Register (sorted by leverage, then domain)

| F-id | Domain | Title | Disp. | Lev. | Verdict | Coordinate | Charter trace | Evidence (one-line) |
|---|---|---|---|---|---|---|---|---|
| F-qe-rel-01 | quality-eng/release | UX/a11y/PDF tier silently skips in CI; E-2 "machine-checked in CI, free forever" is local-only | FIX | P0 | CONFIRMED | Sprint 6.3 / v1.0.7 / v1.1.0 | E-2, A-2, C-5 | ci.yml has no playwright install; conftest pytest.skip on missing Chromium; pdf skipif |
| F-qe-rel-02 | quality-eng/release | C-2 no-egress is asserted, not machine-falsifiable | FIX | P0 | CONFIRMED | PX-01 (v1.0.6) | C-2, C-0, E-2, S-1 | no egress/allowlist/socket test at pin; test_scraper only stubs requests.get |
| F-arch-01 | architecture/code-health | C-6 boundary convention-only: no import-lint/boundary test | FIX | P1 | CONFIRMED | v1.0.8 | C-6, C-0, C-2 | no import-linter in pyproject; CI = ruff+mypy+pytest; no boundary test |
| F-arch-02 | architecture/code-health | v1.0.8 blueprint plan: stale blast-radius numbers | FIX | P1 | CONFIRMED | v1.0.8 | P-6, W-4, A-4 | RELEASE_ARC 6290-LOC/75-route/67-test vs actual 6992/78/24 |
| F-arch-03 | architecture/code-health | route-security-lint hook app.py-scoped, dark on blueprints | FIX | P1 | **WEAKENED** | v1.0.8 | C-1, S-1, C-0 | hook app.py-only; dashboard_bp uncovered but localhost-gated, read-only, no path from input |
| F-vision-01 | product-vision | Constraints are a flat "won't-cross" tier; charter wants enforceability tiering | FIX | P1 | **WEAKENED** | v1.0.7 (charter extraction) | C-0, C-1, C-6 | vision.md:75-77 header + six flat sub-sections (not ~7); drop the "C-8" trace |
| F-vision-02 | product-vision | Absolute no-invention register in vision.md + system-model.md violates C-0 | FIX | P1 | CONFIRMED | - | C-0, C-3, A-4 | vision.md:50 "LLM cannot invent facts"; owner recanted R2-4.2/R2-4.4 |
| F-vision-03 | product-vision | Interviews never a success criterion; outcome loop shipped but docs say "(Future v2)" | FIX | P1 | CONFIRMED | Sprint 6.6 / v1.0.7 M-2 | P-4, M-1, T-A | Application sent_at/outcome_at/status=interview shipped; PRODUCT_SHAPE 6x "(Future v2)" |
| F-vision-04 | product-vision | "one person, one machine, one job at a time" single-tenant-as-value contradicts "local and yours" | FIX | P1 | CONFIRMED | - | C-1, P-2, A-2 | vision.md:33,42 vs list_users()/userSelect multi-profile; owner pre-flagged R2-4.1 |
| F-vision-05 | product-vision | vision.md:92 "no third-party CDN fetches at runtime" false at the pin | FIX | P1 | CONFIRMED | v1.0.6 PX-01 | C-0, C-2, P-3 | vision.md:89-93 vs dashboard.html:15 cdn.jsdelivr.net Chart.js |
| F-expa11y-01 | experience/a11y | a11y taxonomy NOT machine-checked in CI (local-only gate) | FIX | P1 | CONFIRMED | - | E-2, A-2 | ci.yml quality job = ruff/mypy/pytest only; conftest skip on chromium |
| F-expa11y-02 | experience/a11y | cold no-API-key user error-dumped mid-analyze, not guided | FIX | P1 | CONFIRMED | Sprint 6.5 (KW3) | A-1, M-2 | _get_client passes empty key; AuthenticationError uncaught -> bare 500/500 |
| F-expa11y-03 | experience/a11y | no ACCESSIBILITY.md honest-status page exists at the pin | FIX | P1 | CONFIRMED | v1.0.7 / Sprint 6.5 | E-2, P-3 | git ls-tree c6e0437 finds no ACCESSIBILITY.md; only tests/ux/a11y/* |
| F-expa11y-04 | experience/a11y | diagnostics legends are dev-register; lay metrics legend unwritten | FIX | P1 | CONFIRMED | Sprint 6.5 / v1.0.7 M-2 | S-3, M-2, E-2, A-2 | dashboard.html dev-register tiles/banners/legends; lay legend unbuilt |
| F-expa11y-07 | experience/a11y | keyboard bullet-reorder alternative, pinned by a real "a11y floor" test | KEEP | P1 | CONFIRMED | - | E-2, C-4, AL-2 | app.js buttons+aria-labels+_moveBulletRow; regression test asserts persistence |
| F-expa11y-08 | experience/a11y | _announce() live-region discipline intact at every async completion | KEEP | P1 | CONFIRMED | - | E-2, C-4 | index.html:18 region + helper + 7 success call sites; no test guards it |
| F-expa11y-09 | experience/a11y | modal focus-trap + Escape + focus-return; vendored dependency-free axe gate | KEEP | P1 | **WEAKENED** | - | E-2, C-4 | both modals implement trap by static reading, NOT yet test-verified; axe claims solid |
| F-qe-rel-03 | quality-eng/release | None of the agreed E-2 machine badges exist at the pin | FIX | P1 | CONFIRMED | v1.1.0 fresh-clone | E-2, C-0, D-1 | no dependabot/Scorecard/REUSE/SPDX/lockfile; axe MPL-2.0 declared only in prose |
| F-qe-rel-04 | quality-eng/release | C-6 deterministic-LLM boundary holds by convention; no gate fails on an LLM import | FIX | P1 | CONFIRMED | v1.0.8 WS-1 | C-6, C-0 | AST: 7 modules clean; no boundary test; no import-linter/grimp |
| F-qe-rel-05 | quality-eng/release | Eval-quality regression gate exists and blocks; affirm it | KEEP | P1 | CONFIRMED | - | E-1, C-0, C-3, M-2 | REGRESSION_DELTA=0.5 -> exit_code 2 -> fails eval-smoke; grounding-only in CI |
| F-qe-rel-07 | quality-eng/release | T-D not closed: eval/grounding gates run only on synthetic fixtures | WATCH | P1 | **WEAKENED** | v1.0.7 PV-1/PV-2 | T-D, M-2, C-3 | real dir empty; gap genuinely open BUT already a named release-blocking task (drop "silent") |
| F-qe-rel-08 | quality-eng/release | Two hard human SLAs still ship, in violation of D-4 | FIX | P1 | CONFIRMED | v1.0.6 (with PX-03) | D-4, P-3 | SECURITY.md:134-135 5-day/30-day; CODE_OF_CONDUCT.md:15 5-day |
| F-eval-01 | eval/grounding | AL-1 over-suppression uninstrumented and unfalsifiable from data | FIX | P1 | CONFIRMED | v1.0.7 PV-2 | AL-1, C-3, T-B, S-2, M-2 | _dropoffPick minKeep/maxKeep/ratio; ride-along metrics omit bullet count |
| F-eval-02 | eval/grounding | Real loop never exercised; L1/L2 uncalibrated (blocks M-2/T-D) | FIX | P1 | CONFIRMED | v1.0.7 PV-1/PV-2 | M-2, T-D, C-3 | fixtures/real = .gitkeep only; UNCALIBRATED stamp; corroborated TUNING_LOG |
| F-eval-03 | eval/grounding | No lay metrics legend on groundedness / tuning panes (S-3) | FIX | P1 | CONFIRMED | Sprint 6.5 | S-3, M-2, A-2 | dashboard.html groundedness labels + dev-register tuning banner |
| F-eval-04 | eval/grounding | Dynamic source-union scoring distinguishes asserted-beyond from synthesized-within (C-3) | KEEP | P1 | **WEAKENED** | - | C-3, R2-4.4 | metric union folds THREE sources, not typed edits; GROUNDING_METRIC.md overstates four |
| F-sec-01 | oss-sec/privacy | C-2 egress asserted in prose, not by a committed falsifiability test | FIX | P1 | CONFIRMED | v1.0.7 hardening | C-2, E-2, C-0 | no egress/socket test; test_scraper stubs requests.get; no pytest-socket |
| F-sec-02 | oss-sec/privacy | C-1 loopback bind implicit (Flask default), neither pinned nor asserted | FIX | P1 | CONFIRMED | v1.0.8 | C-1, S-1, C-0 | app.py:6988 app.run() no host=; SERVER_NAME a third silent flip vector |
| F-sec-03 | oss-sec/privacy | SECURITY.md "No external CDN is loaded at runtime" — false at the pin | FIX | P1 | CONFIRMED | v1.0.6 PX-01 | C-0, C-2(i), P-3, S-1 | SECURITY.md:85 + no-CSP row vs dashboard.html:15; test enforces the CDN tag |
| F-sec-04 | oss-sec/privacy | Egress enumeration divergent across docs (SECURITY.md 3 classes incl. phantom JD-URL fetch) | FIX | P1 | CONFIRMED | v1.0.6 PX-03 | C-2(iv), C-0 | SECURITY.md 3 classes vs README/vision 2; jd_url provenance-only, never fetched |
| F-sec-05 | oss-sec/privacy | Route containment dense, unit-tested, build-time-guarded | KEEP | P1 | CONFIRMED | v1.0.8 | C-1, S-1, D-5 | _safe_username 82x/_within 59x; 9 tests pass; block-secrets blocks key shapes + key files |
| F-sec-06 | oss-sec/privacy | Fresh hostile clone carries zero real PII and zero secrets | KEEP | P1 | CONFIRMED | - | S-1, C-1, D-5 | .gitignore broad ignores; synthetic fixtures only; zero key-shapes across full history |
| F-sec-07 | oss-sec/privacy | Two human-response SLAs survive at the pin (D-4 softening pending) | FIX | P1 | CONFIRMED | v1.0.7 pre-public | D-4, P-3 | SECURITY.md:134-135; CODE_OF_CONDUCT.md:15 |
| F-sec-11 | oss-sec/privacy | CODE_OF_CONDUCT routes vuln/conduct reports to the WRONG repo (stale channel) | FIX | P1 | CONFIRMED | E-2 / v1.0.7 | E-2, P-3, S-1 | COC:13 Cooksey/resume vs amodal1/sartor everywhere; also ISSUE_TEMPLATE/config.yml |
| F-docs-01 | docs/wiki | SECURITY.md asserts a JD-URL egress class the code lacks; 3 public docs disagree | FIX | P1 | CONFIRMED | v1.0.6 PX-03 | C-2, C-2(iv), C-0, P-3, S-1 | SECURITY.md 3 classes vs vision/README 2; jd_url provenance only |
| F-docs-02 | docs/wiki | SECURITY.md:85 "No external CDN is loaded at runtime" false at the pin | FIX | P1 | CONFIRMED | v1.0.6 PX-01 | C-2, C-2(i), C-0, P-3, S-1 | SECURITY.md:85 + no-CSP row vs dashboard.html:15 |
| F-docs-03 | docs/wiki | "The LLM cannot invent facts" — flat C-0-barred absolute owner flagged overstated | FIX | P1 | CONFIRMED | - | C-0, C-3, A-4, P-3 | vision.md:50, overview.md:19/26, llms.txt:4 (line anchors drift); R2-4.2/R2-4.4 |
| F-docs-04 | docs/wiki | Public docs describe a live profile/website scrape that is dead code at the pin | FIX | P1 | CONFIRMED | v1.0.6 PX-02 | C-2, C-2(iii), P-3, C-0 | scraper fns no runtime caller (removed 559bd62); strike non-dependency-downloads.md:31 cite |
| F-docs-05 | docs/wiki | Install docs fold Chromium ~150 MB into base prerequisite | FIX | P1 | **WEAKENED** | Sprint 6.5 | D-6, A-2, A-1, M-2 | factual but NOT a clean D-6 contradiction (wiki/README file Chromium as basic-tool); leverage downgrades ~P3 |
| F-gov-01 | governance/memory | block-merge hook misses the dominant direction — convention-only for the common path | FIX | P1 | CONFIRMED | v1.0.7 | C-0, E-1, T-C, S-1 | feature-merge --no-ff PASSES unblocked; only the reverse direction blocks |
| F-gov-02 | governance/memory | Two live W-1 collisions structural in code; no isolation rule written as governance | FIX | P1 | CONFIRMED | v1.0.7 | W-1, R2-11 | global ~/.claude/plans/.approved + cleanup wipes all *.md; no per-session scope |
| F-gov-03 | governance/memory | Serial-session framing still authoritative; real parallel model uncodified | FIX | P1 | CONFIRMED | v1.0.7 | W-1 | RELEASE_ARC:390/863 "one branch per session"; two live worktrees contradict daily |
| F-gov-04 | governance/memory | Seven enforced blocker hooks real and honestly separated from witness/tribal rules | KEEP | P1 | CONFIRMED | - | C-0, E-1, T-C | exit-2 reachable in 7 blockers; 3 witnesses exit 0; minor cite imprecision AGENTS.md:96 |
| F-gov-05 | governance/memory | Governance-extraction design register-grade: extract-don't-restate, one home, @import safety condition | KEEP | P1 | CONFIRMED | v1.0.7 | W-2, C-0 | governance-extraction.md full; @AGENTS.md real in CLAUDE.md:16; v1.0.7 tag criteria |
| F-vision-06 | product-vision | Corpus-Item ladder: vision.md Learnings drift from PRODUCT_SHAPE disposition | FIX | P2 | - | Sprint 6.6 (B.4/B.5) | P-6, S-2 | vision.md:222-229 "v1.1/v1.2" vs PRODUCT_SHAPE superseded banner -> v1.0.6 |
| F-vision-07 | product-vision | ATS framing categorical; charter's escape hatch not named in vision.md | FIX | P2 | - | - | C-5 | vision.md:57-63 + :250-259; no hatch named |
| F-vision-08 | product-vision | system-model.md seven-functions self-model with visible honesty seams | KEEP | P2 | - | WS-4b | A-4, P-3, C-0 | system-model.md:60-126 functions + honesty seams :106-108/:148-164 |
| F-vision-09 | product-vision | Corpus-Item asymmetry matrix as the falsifiable diagnosis of record | KEEP | P2 | - | - | P-6, S-2 | PRODUCT_SHAPE.md:31-42 matrix w/ model-line cites; dated banners |
| F-vision-10 | product-vision | Charter-admitted audiences (A-2/A-3/A-5) absent from public identity | WATCH | P2 | - | v1.0.7 | A-2, A-3, A-5 | vision.md:16-19 audience block; continuum/builders/blocked-ATS unnamed |
| F-arch-06 | architecture/code-health | Persistence layer mature: per-edge cascade, CHECK constraints | KEEP | P2 | - | - | D-5, C-4, P-6 | db/models ondelete; ApplicationBullet no-cascade; ck_tag_kind |
| F-arch-07 | architecture/code-health | Audit-trail spine real and inspectable | KEEP | P2 | - | - | D-5, C-4 | save_iteration_context; PROMPT_VERSION stamps; llm_calls.jsonl |
| F-arch-08 | architecture/code-health | Migrations correct but no populated-DB upgrade/downgrade test | WATCH | P2 | - | - | P-6, D-5, S-1 | schema ends 0007; batch_alter; test_db_session fresh-only |
| F-arch-04 | architecture/code-health | C-6 boundary holds by behavior at the pin | KEEP | P2 | - | - | C-6, C-2 | 7 modules NONE import analyzer/anthropic (grep+AST) |
| F-expa11y-05 | experience/a11y | axe scope is a first cut; several agreed taxonomy lines have no machine check | FIX | P2 | - | - | E-2 | test_axe_smoke 4 tests; no reflow/tab-order/history assertion |
| F-expa11y-06 | experience/a11y | zero History API: browser Back exits the SPA and discards wizard state | WATCH | P2 | - | v1.0.8 back-nav | E-2, S-1 | app.js grep history.(push/replace)State/popstate = 0 |
| F-expa11y-10 | experience/a11y | corpus-first IA + the two M-2 first-run bars unbuilt at the pin | WATCH | P2 | - | Sprint 6.4/6.5 / v1.1.0 | S-3, M-2 | index.html Tailor-first; RELEASE_ARC Sprint 6.4/6.5/v1.1.0 planned |
| F-qe-rel-06 | quality-eng/release | No automated perf-regression gate; perf is a strong narrative + manual PR checklist | WATCH | P2 | - | - | T-D, M-2, E-1 | PERFORMANCE_HISTORY telemetry; only gate = PR-template manual checkbox |
| F-qe-rel-09 | quality-eng/release | Migration test reaches head but not data-bearing; long-lived-DB upgrade unverified | WATCH | P2 | - | - | P-6, D-5 | session.py upgrade head; test asserts 27 tables (count only) |
| F-qe-rel-10 | quality-eng/release | CI matrix + least-privilege permissions + deterministic-module test set; affirm | KEEP | P2 | - | v1.0.8 WS-1/WS-3 | E-1, C-5, C-6 | permissions contents:read; py3.11/3.12/3.13 matrix; deterministic-module tests |
| F-eval-05 | eval/grounding | Candidate A/B non-polluting; default path byte-identical (KEEP-verified) | KEEP | P2 | - | - | A-2, C-4 | prompt_overrides; default effective_prompt_version()==PROMPT_VERSION |
| F-eval-06 | eval/grounding | Manual promote + fail-closed, LLM-free annotation contract | KEEP | P2 | - | - | C-4 | validate_annotations; _scorer_disagreements; LLM-free |
| F-eval-07 | eval/grounding | Paid eval/tune routes are cost- and consent-gated (BOOST-verified) | BOOST | P2 | - | - | C-1, D-6 | localhost gate + cost-band confirm on paid routes |
| F-eval-08 | eval/grounding | Uncalibrated L1/L2 state surfaced and tracked, not silently trusted | KEEP | P2 | - | v1.0.7 PV-2 | C-0, M-2 | grounding_signals never imported by prod, flag-gated; UNCALIBRATED stamp |
| F-eval-09 | eval/grounding | Sharpened L0 detector eval/display-only; hot path still uses lossy proto-L0 | WATCH | P2 | - | v1.0.7 PV-2 | C-0, C-3 | compute_fabricated_specifics callers = runner+dashboard only; app.py uses overlap |
| F-eval-10 | eval/grounding | Committed synthetic suite exercises only the legacy generate path; corpus-mode uncovered | FIX | P2 | - | v1.0.7 PV-1 | C-3, M-2, A-4 | runner _build_context no DB; corpus-mode path uncovered by CI fixtures |
| F-sec-08 | oss-sec/privacy | License declaration MIT-only; vendored axe asset is MPL-2.0 (under-declared) | FIX | P2 | - | v1.0.6 | E-2, D-5 | LICENSE MIT-only; axe.min.js MPL-2.0 header; no LICENSES/REUSE/SPDX |
| F-sec-09 | oss-sec/privacy | None of the agreed E-2 machine gates (lockfile/Dependabot, Scorecard, REUSE, egress test, PVR) committed | WATCH | P2 | - | v1.1.0 public-tag | E-2, C-0, P-3 | ci.yml only; no dependabot/Scorecard/REUSE/egress test/lockfile/PVR/PRIVACY.md |
| F-sec-10 | oss-sec/privacy | HF eval-grounding download honors D-6 (opt-in, lazy, graceful) — unpinned VCS dep WATCH | KEEP | P2 | - | - | D-6, C-2(ii), A-2 | [eval-grounding] lazy import + localhost gate; minicheck unpinned |
| F-docs-06 | docs/wiki | Sprint 6.5 eval-stack install guide does not exist; ~3.2 GB HF opt-in only in a wiki provenance page | FIX | P2 | - | Sprint 6.5 | D-6, C-2(ii), A-2, M-2 | find docs *eval-stack* empty; HF/3.2GB only in docs/dev + one wiki page |
| F-docs-07 | docs/wiki | wiki one grounding rule + cite/backlink/synthesis convention genuinely practiced | KEEP | P2 | - | - | P-3, W-2, S-3, A-4 | SCHEMA.md; 8/8 backlink slugs resolve; [synthesis] tags 1-5/page |
| F-docs-08 | docs/wiki | Sentinel-honesty: .last_ingest_sha left at sentinel rather than falsely advanced | KEEP | P2 | - | WS-4b | P-3, W-2, C-0 | .last_ingest_sha sentinel; log.md; index.md |
| F-docs-09 | docs/wiki | Governance-extraction design records the load-bearing @import safety condition | KEEP | P2 | - | v1.0.7 | W-2, C-0 | SCHEMA.md D5; governance-extraction.md:27-52 |
| F-docs-10 | docs/wiki | WS-4b code cold-ingest untested: grounding at module scale + rot-detection never fired | WATCH | P2 | - | WS-4b | P-3, W-2, A-4 | index.md; .last_ingest_sha never advanced (sha->HEAD check never fired) |
| F-gov-06 | governance/memory | Witness-class freshness reminder + honest sentinel = working amendment-ceremony precedent | KEEP | P2 | - | - | C-0, E-1, W-2 | wiki-freshness-reminder.sh; .last_ingest_sha sentinel; charter L338-344 |
| F-gov-07 | governance/memory | check-plan-approved prints a hand-create-the-marker hint contradicting the never-hand-create rule | DEBUFF | P2 | - | v1.0.7 | C-0, W-2 | check-plan-approved.sh:31-33; contradicts AGENTS.md + memory |
| F-gov-08 | governance/memory | No W-4 maturity metric for four of five incubants; only recall/ has a readiness condition | FIX | P2 | - | - | W-4 | memory-architecture.md:216-219 recall/ readiness; no signal for other four |
| F-gov-09 | governance/memory | Read-only subagents are the compliance-agent precedent | KEEP | P2 | - | - | W-2, C-4 | prompt-archaeologist.md read-only; agents dir listing |
| F-gov-10 | governance/memory | Operator-stack triad: memory->context richly designed, governance->posture has no design home yet | WATCH | P2 | - | v1.0.7 | W-2, A-2, A-4, R2-10 | memory-architecture POLICY plane; PRODUCT_SHAPE assistant=retrieval; no governance->assistant artifact |
| F-arch-05 | architecture/code-health | All-LLM-in-analyzer precise for call code, looser for prompts | WATCH | P3 | - | - | C-6, C-0 | onboarding/extract_experiences; corpus_import; AGENTS.md |
| F-arch-09 | architecture/code-health | W-4 practiced but recall package design-only at pin | WATCH | P3 | - | WS-4b / v1.0.7 | W-4 | run_suite in runner.py; recall not committed; memory-architecture.md |
| F-arch-10 | architecture/code-health | WS-2 typing ratchet mid-flight; mypy partial-strict appropriate | KEEP | P3 | - | - | P-6, A-4 | pyproject partial-strict; CI mypy; RELEASE_ARC WS-2/PV-4 |

> **No REFUTED findings.** Every adversarially-verified P0/P1 finding
> returned CONFIRMED or WEAKENED; none was struck. (Had any been REFUTED
> it would appear here as ~~F-id~~ with a one-line reason, per protocol —
> the list is intentionally empty, not omitted.)

---

## Verification outcomes (P0/P1 only)

Forty-four findings carry P0/P1 leverage and were adversarially
re-verified (re-derive every citation at `c6e0437`; attempt
falsification; record counter-evidence). Results:

- **CONFIRMED: 38**
- **WEAKENED: 6** — `F-arch-03`, `F-vision-01`, `F-expa11y-09`,
  `F-qe-rel-07`, `F-eval-04`, `F-docs-05`
- **REFUTED: 0**

Both P0 findings (`F-qe-rel-01`, `F-qe-rel-02`) are CONFIRMED.

**Read WEAKENED findings with their revised claim** (see
[`verification-log.md`](verification-log.md)) — in every case the
substance survived but a superlative, a severity, or a sub-claim was
trimmed:

- **`F-arch-03`** — structural claim holds (hook is app.py-only) but the
  single blueprint route is localhost-gated/read-only/builds no path from
  user input, so there is no realized PII/traversal gap **today**;
  downgrade FIX/P1 -> P2/P3 (latent guardrail-coverage gap that becomes
  load-bearing during the planned blueprint refactor) + one-line
  SECURITY.md:211 tightening.
- **`F-vision-01`** — keep FIX/P1; cite **six** sub-sections (not "~7")
  and **drop the "C-8" trace** (no such charter clause; it is
  discovery-brief item #8).
- **`F-expa11y-09`** — both modals **implement** trap+Escape+focus-return
  by static reading but the behavior is **not yet test-covered**; read
  "in working form" as "implemented per static inspection, not yet
  covered." The vendored-axe half is fully solid.
- **`F-qe-rel-07`** — the gap is genuinely open on real data at the pin,
  but **drop the "silent assumption" framing**: it is already a named,
  sequenced, release-blocking task set (PV-1/PV-2 -> v1.0.7); fix the cite
  to `docs/dev/perf/PERFORMANCE_HISTORY.md`.
- **`F-eval-04`** — keep the P1 AFFIRM, but the deterministic **metric**
  union folds **three** sources (primary + supplementals + clarification
  answers), **not** first-person typed edits; `GROUNDING_METRIC.md:24-31`
  overstates a four-part union — flag that doc/code drift alongside the
  affirmation.
- **`F-docs-05`** — factually accurate but **not a clean D-6
  contradiction** (the cited wiki page + README file Chromium as a
  basic-tool / normal-use install for end-user PDF output); downgrade to
  ~P3 docs progressive-disclosure polish; the real action is reconciling
  the inconsistent Chromium classification across docs.

---

## COORDINATE — findings touching in-flight work (surface to owner now)

These findings name sprints/branches/version tags live in
`RELEASE_ARC.md`. They must reach the owner immediately so the in-flight
work either absorbs the fix or is sequenced against it.

**v1.0.6 (PX-01 Chart.js vendoring + PX-02/PX-03 egress-doc corrections)**
- `F-vision-05`, `F-sec-03`, `F-docs-02` — PX-01: vision.md:92 /
  SECURITY.md:85 + no-CSP row false CDN claim; all clear when Chart.js
  vendors.
- `F-sec-04`, `F-docs-01` — PX-03: SECURITY.md phantom JD-URL egress
  class; reconcile to the two-class enumeration.
- `F-docs-04` — PX-02 re-wire + PX-03 docs-correct: public docs describe a
  dead-code profile scrape; both rulings unlanded at the pin.
- `F-qe-rel-02` — the missing egress falsifiability test would have caught
  the PX-01 CDN fetch and keeps C-2 honest after vendoring.
- `F-qe-rel-08`, `F-sec-07` — D-4 SLA softening, batched with v1.0.6 doc
  corrections.
- `F-sec-08` — declare axe MPL-2.0 / REUSE alongside the Chart.js vendor.
- `F-vision-06` — Corpus-Item ladder: PRODUCT_SHAPE reschedules ESI/SGI to
  v1.0.6.

**Sprint 6.5 (education/diagnostics + first-run onboarding)**
- `F-expa11y-04`, `F-eval-03` — lay metrics legend on groundedness/tuning
  panes (the same surface from two domains).
- `F-expa11y-02` — cold no-API-key first-run guidance modal (KW3).
- `F-docs-05` — Chromium install progressive disclosure (see WEAKENED).
- `F-docs-06` — Sprint 6.5 eval-stack install guide does not yet exist.

**Sprint 6.6 / Corpus-Item ladder (B.4/B.5/B.8)**
- `F-vision-03` — outcome capture B.8; reconcile PRODUCT_SHAPE six
  "(Future v2)" refs with the already-shipped status funnel.
- `F-vision-06` — B.4 experience-summary-item / B.5 skill-group-item.

**v1.0.7 (hardening + governance extraction + grounding calibration)**
- `F-vision-01` — charter/governance extraction to
  `docs/governance/charter.md`.
- `F-vision-03` (M-2 explainability), `F-vision-10` (assistant serves the
  A-2 continuum).
- `F-expa11y-03` — ACCESSIBILITY.md honest-status page.
- `F-qe-rel-07`, `F-eval-02` (PV-1/PV-2 real-loop calibration),
  `F-eval-08`, `F-eval-09` (PV-2 / explainability).
- `F-sec-01` (egress falsifiability test), `F-sec-07`, `F-sec-11`
  (PVR / disclosure-channel fix).
- `F-gov-01`, `F-gov-02`, `F-gov-03`, `F-gov-05`, `F-gov-10` (governance
  extraction + parallel-session codification + governance->assistant
  design home), `F-gov-07` (DEBUFF the hand-create hint).

**v1.0.8 (blueprint split, WS-1)**
- `F-arch-01`, `F-arch-02`, `F-arch-03`, `F-qe-rel-04` — C-6 boundary test
  + stale blast-radius numbers + extend route-security-lint beyond app.py
  + the import-boundary gate.
- `F-sec-02` (blueprint split moves main()/bind — pin the loopback bind
  then), `F-sec-05` (keep the guard pair + fire the hook on blueprint
  files).
- `F-expa11y-06` — back-nav item.

**v1.1.0 (fresh-clone / public-tag release pass)**
- `F-qe-rel-01` (P0: dedicated CI job installing Chromium + `pytest -m ux`
  as a required check), `F-qe-rel-03`, `F-sec-09` (E-2 machine badges),
  `F-expa11y-10` (fresh-clone <5min M-2 bars).

**WS-4b (wiki cold-ingest of code)**
- `F-vision-08` (system-model seeds wiki overview.md), `F-arch-09`,
  `F-docs-08`, `F-docs-10`.

---

## Disposition rollup (all 81 findings)

| Disposition | Count |
|---|---|
| BOOST | 1 |
| KEEP | 25 |
| FIX | 41 |
| DEBUFF | 1 |
| WATCH | 13 |
| **Total** | **81** |

By leverage: **P0 = 2**, **P1 = 42**, **P2 = 34**, **P3 = 3**.

The FIX set at P0-P1 is the actionable spine; the KEEP/BOOST set is the
affirm-and-protect ledger — surfaces that are right and must not regress
through the v1.0.8 blueprint split or the v1.1.0 public tag.



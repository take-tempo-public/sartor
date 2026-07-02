---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Assessment question bank — sartor. (2026-06 product-excellence review)

> Phase 2 artifact. Candidate questions arrive from the eight domain guides;
> additional questions are minted from the interview record's assessment leads
> (AL-1..AL-7), the Round-2 verification brief items that survived the
> 2026-06-12 rulings, and the product map's BOOST/DEBUFF candidates (each
> candidate gets one verifying question). Severity anchor: the SIGNED Product
> Charter (`00-interview/product-charter.md`).
>
> **Pruning rule applied:** every question traces to ≥1 charter statement
> (P/C/D/E/A/S/M/W ID). Untraceable candidates are cut — see the cut list at
> the bottom (no silent drops). Near-duplicates across domains are merged;
> the surviving home carries an explicit cross-reference.
>
> **Out of scope by ruling (NO questions minted):** PX-01 (vendor Chart.js),
> PX-02 (re-wire scrape), PX-03 (correct `jd_url` docs), and the four C-2
> (i)–(iv) rulings — all decided 2026-06-12. The AL leads that *point at*
> those fixes are reframed here as **verify-the-fix-landed / verify-the-
> enforcer-exists** questions (the prescription is ruled; whether it shipped
> and whether a gate now holds it is still assessable).
>
> Domain short-codes: `vision`, `exp-a11y`, `arch`, `eval`, `qe-rel`, `sec`,
> `docs`, `gov`.

---

## Domain 1 — Product vision & definition (`vision`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-vision-01 | Does any public-facing vision doc **tier** its self-imposed constraints by enforceability (machine-inviolable vs negotiable-default), or are all ~12 presented as one uniform "won't-cross" set? | C-0, C-8(brief), C-1, C-6 | `vision.md:76-175` "Self-imposed constraints" | guide Q1 / brief-C8 |
| QB-vision-02 | Is "an interview from a sartor-written resume" stated anywhere as a **success criterion**, not only as a deferred v2 "Mark sent" feature? | P-4, M-1, C-6(success-loop) | `vision.md:46-72`; `PRODUCT_SHAPE §4 L133-139` | guide Q2 / brief-C6 |
| QB-vision-03 | Does the ATS framing carry the charter's escape hatch (edit the produced document for non-ATS needs), or is it stated categorically with no hatch? | C-5 | `vision.md:57-63, 250-259` | guide Q3 / brief-C4 |
| QB-vision-04 | Is the Corpus-Item ladder still the load-bearing thesis after Phase 4.5 (converging vs re-dispositioned), and does `vision.md` Learnings agree with `PRODUCT_SHAPE`'s current disposition, or do they drift? | P-6, S-2 | `PRODUCT_SHAPE.md:31-42, 410-417, §10`; `vision.md:222-229` | guide Q4 / map-DEBUFF-2 |
| QB-vision-05 | Where would portfolio polish (A-4 "whoa, robust") tempt a vision claim in **absolute register** resting on LLM behavior ("never invents", "always grounded" as a guarantee vs mechanism+effort)? | C-0, C-3, A-4 | `vision.md:75-149` constraints; system-model "one law" | guide Q5 |
| QB-vision-06 | Do the charter-admitted audiences (A-5 blocked-ATS integration, A-2 user→power-user→dev continuum, A-3 builders) appear in the public identity, or does "one person, one machine, one job at a time" structurally **exclude** them? | A-2, A-3, A-5 | `vision.md:16-19, 41-43`; brief-C5 | guide Q6 / brief-C5 |
| QB-vision-07 | Is the egress promise stated with the **enumerable-destination qualifier** that makes it verifiable ("the two sanctioned classes"), or as a bare absolute ("never leaves the machine, ever") that C-0 bars? | C-0, C-2 | `vision.md:89-93`; `README.md:127` | brief-C10 / map-BOOST-relates / x-ref QB-docs-01 |
| QB-vision-08 | Does the "local and yours" identity replace the prior person-count language (R2-4.1) consistently, and is single-tenancy correctly demoted from value to non-value (household sharing in-model)? | C-1, P-2 | `vision.md:16-19, 41-43`; R2-4.1; S23 | brief-C2/C5 (post-ruling residue) |

---

## Domain 2 — Product experience & accessibility (`exp-a11y`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-exp-a11y-01 | Is the agreed a11y taxonomy **machine-checked in CI, free forever**, or local-only? (Does CI install Chromium and run `pytest -m ux`, or do the axe/a11y tiers silently skip?) | E-2, A-2 | `ci.yml@c6e0437`; `tests/ux/conftest.py:80,85` | guide / brief-A7 / map-DEBUFF-1 / x-ref QB-qe-rel-01 |
| QB-exp-a11y-02 | Is the bullet drag-reorder reachable by **keyboard** (the E-2 reorder alternative), and does the named "a11y floor" regression test actually pin it? | E-2, C-4, AL-2 | `static/app.js:~4820` up/down aria-labels; `tests/ux/regression/test_20260604_bullet_drag_reorder.py:9`; `style.css:2188` | AL-2 / guide |
| QB-exp-a11y-03 | Does browser **Back/history** preserve wizard state, or does zero History API usage mean Back exits the SPA and discards expensive state (a11y + data-loss, not polish)? | E-2 (back/history), S-1(data-loss-adjacent) | `static/app.js@c6e0437` (History API absent); arc v1.0.8 back-nav item | AL-3 / guide |
| QB-exp-a11y-04 | Does axe scope cover the **full agreed taxonomy** (wizard Step-2/5/6, modals, iframes, tab-order, reflow/zoom), or only `serious`/`critical` on a first-cut surface set? | E-2 | `tests/ux/a11y/test_axe_smoke.py` + its docstring | guide / brief-A7 |
| QB-exp-a11y-05 | Is the **cold no-API-key user** guided (preflight) or error-dumped mid-analyze with a generic connection error? | A-1, M-2 (first-run) | `app.py:89-95` `_get_client()`; `app.py:658/744` error path | guide |
| QB-exp-a11y-06 | Are the **two first-run bars** met — fresh-clone skip-clarify smoke < 5 min AND clarify-inclusive ~15 min "surprisingly good" (owner-blind A/B vs hand-tailored)? | M-2, A-1 | `templates/index.html:48`; RELEASE_ARC Phase 5 first-run bars; Sprint 6.4 | guide / brief-A2 / R2-6 |
| QB-exp-a11y-07 | Are diagnostics/power-user surfaces in the a11y scope and explainable **lay-legibly** (a non-coder legend), or dev-register internals? | E-2 (diagnostics in scope), S-3, A-2 | `dashboard/templates/dashboard.html:461-693`; axe gate scans `/_dashboard` | guide / R2-12.2 / x-ref QB-eval-04 |
| QB-exp-a11y-08 | Is corpus-first onboarding + smart landing (Sprint 6.4) landed, or do top tabs still open Tailor-first — leaving the S-3 discoverability path open? | S-3, M-2 | `templates/index.html:48` `topTabTailor active`; RELEASE_ARC Sprint 6.4 | guide / map §3 |
| QB-exp-a11y-09 | Is the `_announce()` live-region discipline intact at every async completion (and not over-fed), protecting the working E-2 mechanism under refactor? | E-2 (live-region), C-4 | `templates/index.html:18`; `static/app.js:2237` + call sites 591/795/1124/1226/1527/1632/1695 | guide (KEEP-protection) |

---

## Domain 3 — Architecture & code health (`arch`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-arch-01 | Is C-6 (deterministic↔LLM boundary) enforced **by construction** — an import-lint or AST/import test that fails the build on an LLM import in a deterministic module — or convention + reviewer vigilance only? | C-6, C-0 | `pyproject.toml` (no grimp/import-linter); no boundary test; `route-security-lint` guards security not LLM | guide / map-BOOST-5 (verify) / x-ref QB-qe-rel-06 |
| QB-arch-02 | Does the C-6 boundary actually hold at the pin — do any of the seven deterministic modules import `analyzer`/`anthropic`? | C-6 | `hardening/parser/generator/scraper/json_resume/corpus_to_json_resume/pdf_render.py`; `docs/architecture.md:209` | guide (KEEP-verify) / map-BOOST-5 |
| QB-arch-03 | Does the v1.0.8 blueprint-split plan use **accurate** blast-radius numbers, or stale ones (LOC/routes/test-coupling) that mis-scope the refactor? | P-6, W-4, A-4 | `app.py` 6,992 LOC/78 routes @c6e0437 vs `RELEASE_ARC.md:740,746`, map row :21 | guide / map §3 v1.0.8 |
| QB-arch-04 | Is W-4 "modularize-in-place" genuinely practiced (extracted-in-place packages, byte-identical extractions) or aspirational? | W-4 | `recall/` package; `run_suite()` extraction `3a91bea`; memory-architecture design | guide / map-BOOST-4 (verify) |
| QB-arch-05 | Will the blueprint split keep `_safe_username`/`_within` on every moved route, and does `route-security-lint` keep firing on blueprint files (not silently go dark)? | C-1, S-1, C-0 | `RELEASE_ARC.md:754`; `.claude-plugin/hooks/route-security-lint.sh` | guide (DEBUFF-guard) / x-ref QB-sec-02 |
| QB-arch-06 | Are schema migrations safe on a **long-lived local DB across a public release** — is any forward migration tested against a realistic pre-populated DB, or only "reaches head"? | P-6, D-5 | `db/migrations/versions/` ends 0007; `db/session.py:151` upgrade head; `test_db_session.py:54` | guide / x-ref QB-qe-rel-05 |
| QB-arch-07 | Is the audit-trail-by-default spine real and inspectable — one timestamped child context per `/api/generate` with a `parent_context_path` chain under `_within()` containment? | D-5, C-4 | `docs/architecture.md:639-651`; `hardening.save_iteration_context()` | guide (KEEP) / map-BOOST-8 (verify) |

---

## Domain 4 — Eval / grounding / tuning as product (`eval`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-eval-01 | Is there an **instrument for AL-1** — suggested-bullet count charted over PROMPT_VERSION history — so the suspected over-suppression regression is decidable from data rather than anecdote? | C-3, AL-1, T-B, S-2 | `TUNING_LOG.md` 2026-05-24; `_dropoffPick` in `static/app.js`; PROMPT_VERSION git log on `analyzer.py` | AL-1 / guide |
| QB-eval-02 | Has the real loop been **exercised end-to-end** producing labels — or is `evals/fixtures/real/` empty (`.gitkeep` only), leaving L1/L2 uncalibrated and M-2/T-D unmet? | M-2, T-D | `evals/fixtures/real/`; `GROUNDING_METRIC.md §calibration` | guide / map-DEBUFF-6 / x-ref QB-qe-rel-04 |
| QB-eval-03 | Does the metric distinguish "**asserted beyond ground**" (the violation) from "**synthesized within ground**" (the feature) — i.e. does grounding scoring use the dynamic source union (résumé + supplementals + clarifications + typed edits)? | C-3 | `GROUNDING_METRIC.md §reframe/§detector-ladder`; `evals/grounding_signals.py` | guide / R2-4.4 |
| QB-eval-04 | Is there a **lay metrics legend** in the groundedness/diagnostics panes, or only raw technical labels ("fabricated rate", "flagged", "L0", `prompt_version`)? | S-3, M-2 (v1.0.7 lay legend) | `dashboard/templates/dashboard.html:300-318` | guide / R2-9 / merged-with QB-exp-a11y-07 (kept here for the legend specifics) |
| QB-eval-05 | Is the annotate→tune→verify loop **driveable by a power-user from the browser**, with candidate A/B non-polluting (`prompt_version=candidate:<hash>`) and a default path that is byte-identical (cache untouched)? | A-2, C-4 | `dashboard/routes.py`; `analyzer.py:290, :2873`; `evals/README.md` §tuning console | guide (KEEP-verify) |
| QB-eval-06 | Is **promote** a deliberate manual human gate (consistent with C-4), and is the annotation contract fail-closed + LLM-free? | C-4 | `evals/README.md §6`; `evals/annotation.py:203, :487` | guide / map-BOOST-9 (consent-gating relates) |
| QB-eval-07 | Are paid eval/tune routes **cost/consent-gated** (localhost-only, `confirm()` cost-band, eager 4xx before spend) — honoring local-and-yours? | C-1, D-6 | `/api/tune/run`, `/api/eval/run`; `dashboard/routes.py` | map-BOOST-9 (verify) |
| QB-eval-08 | Are L1/L2 numbers being treated as **trustworthy before calibration**, or is the uncalibrated state surfaced as a tracked release task? | C-0, M-2 | `evals/grounding_signals.py` behind `--grounding-signals`; `GROUNDING_METRIC.md §calibration` | guide (DEBUFF) |

---

## Domain 5 — Quality engineering & release discipline (`qe-rel`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-qe-rel-01 | Does any **required CI check** exercise the PDF-render / paged.js / a11y paths, or do they only run on the maintainer's laptop because `pytest -m ux` skips without Chromium? | E-2 | `ci.yml:13-42`; `tests/ux/conftest.py:85` | guide Q1 / brief-A7,C-research / map-DEBUFF-1 / x-ref QB-exp-a11y-01 |
| QB-qe-rel-02 | Which of the agreed **E-2 machine gates** (lockfile+Dependabot, Scorecard, REUSE, egress test, PVR) are committed at the candidate tag, and which charter claim does each enforce? (A gate enforcing nothing = cargo-cult; a claim with no gate = unenforced absolute.) | E-2, C-0 | `.github/` (no dependabot/Scorecard); no `LICENSES/`/`.reuse`; no egress test @c6e0437 | guide Q2 / brief-C-table |
| QB-qe-rel-03 | Is C-2 (no egress beyond the two sanctioned classes) **machine-falsifiable**, or asserted in prose only? (Today the only network test stubs `requests.get`.) | C-2, C-0, E-2 | `tests/test_app_security.py`; `tests/test_scraper.py:53` | guide Q3 / brief-C-research / x-ref QB-sec-01 |
| QB-qe-rel-04 | Is there a **perf-regression gate**, or only a perf narrative — and is the two-pass split synthetic-only measured (the T-D gap in numeric form)? | T-D, M-2, E-1 | `docs/dev/perf/PERFORMANCE_HISTORY.md` §"How we measure"/§Caveats; `logs/llm_calls.jsonl` | guide Q4 |
| QB-qe-rel-05 | What does the **v1.1.0 release pass** look like under D-4 — one-time machine+human evidence (D-4 compliant) closing T-D, or does it smuggle in a recurring human SLA? | D-4, M-2, T-D | RELEASE_ARC Phase 5 tag criteria; M-2 matrix | guide Q5 / brief-A1,M3 / R2-5 |
| QB-qe-rel-06 | Do the deterministic-boundary tests prove C-6 **by construction**, or only by behavior/convention (no gate fails on an LLM import in the seven modules)? | C-6, C-0 | deterministic-module test set; `pyproject.toml` | guide Q6 / x-ref QB-arch-01 (kept distinct: arch asks "does an enforcer exist", qe-rel asks "is it wired into the gate") |
| QB-qe-rel-07 | Is the `SECURITY.md` 5-business-day response + 30-day fix **SLA softened to best-effort** (D-4), and is the same 5-day promise in `CODE_OF_CONDUCT.md:15` softened too? | D-4, P-3 | `SECURITY.md:134`; `CODE_OF_CONDUCT.md:15` | guide / brief-C9 / x-ref QB-sec-05 |

---

## Domain 6 — Open-source readiness, security & privacy (`sec`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-sec-01 | Is there a committed **egress-allowlist falsifiability test** that fails on any destination outside the two sanctioned classes, converting C-2's "machine-verifiable" from audit-by-hand to continuous enforcement? | C-2, E-2, C-0 | no egress test @c6e0437; `tests/test_app_security.py` unit-only | guide / brief-C-research / x-ref QB-qe-rel-03 |
| QB-sec-02 | Is C-1's loopback bind **pinned and asserted**, or implicit (relying on Flask's `127.0.0.1` default with no `host=` and no test)? Are `_safe_username`/`_within` present on all 78 routes? | C-1, S-1 | `app.py:6988` `app.run(...)` no `host=`; guards at `app.py:110,124` (66×/48×) | guide / x-ref QB-arch-05 |
| QB-sec-03 | Does a fresh hostile clone contain **zero real PII and zero secrets** — gitignore + committed fixtures auditable as synthetic-only? | S-1, C-1, D-5 | `.gitignore` L2,L13-24,L38-52; `configs/testuser.config`; `resumes/testuser/casey_rivera_*` | guide (S-1 lens) |
| QB-sec-04 | Did the ruled C-2 v1.0.6 fixes actually **land at the assessed state** — Chart.js vendored (no CDN), scrape re-wired (not dead code), egress docs at two-class enumeration? (Verify-the-fix, not re-decide.) | C-2(i)(iii)(iv) | `dashboard/templates/dashboard.html:15`; `scraper.py:71` (dead at pin); `SECURITY.md:56-59` | AL-4/AL-5 (verify-landed) / map §3 |
| QB-sec-05 | Is the **per-system tool bundling + progressive disclosure** (D-6) honored — HF grounding-scorer models and Chromium invisible to users who never enter those systems, with threaded install docs and an explicit opt-in carve-out for the HF download? | D-6, C-2(ii), A-2 | `app.py:6261/6465/~6671` (HF download routes); `docs/install.md:26-30,61-64`; `docs/eval-stack-install-guide` (absent) | AL-6 (ruling D-6) / guide / x-ref QB-docs-04 |
| QB-sec-06 | Is **license completeness** machine-declared — SPDX/REUSE covering the vendored `axe.min.js` (MPL-2.0, not MIT) and the to-be-vendored Chart.js — or does `LICENSE` (MIT-only) under-declare the vendored reality? | E-2, D-5 | `LICENSE`; `tests/ux/a11y/vendor/axe.min.js` MPL-2.0 header; no `LICENSES/`/`.reuse` | guide / brief-C-table(REUSE) |
| QB-sec-07 | Is **Private Vulnerability Reporting** enabled as a one-time setup step, and does a `PRIVACY.md` exist pairing the egress test with the what-leaves-the-machine doc? | E-2, P-3 | `SECURITY.md:129` (routes to advisories); no PVR setup; no `PRIVACY.md` @c6e0437 | guide / brief-C-table(PVR) |

---

## Domain 7 — Documentation & wiki architecture (`docs`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-docs-01 | Is the egress enumeration **identical across SECURITY/vision/README and matched to code** (two sanctioned classes), or three-way-divergent (SECURITY.md three classes incl. a non-existent JD-URL fetch)? | C-2, C-0 | `SECURITY.md:56-59`; `vision.md:89-90`; `README.md:127` | AL-7 / guide / brief-C10 / x-ref QB-vision-07, QB-sec-04 |
| QB-docs-02 | Does any public doc **assert a capability code doesn't have** (live scrape, "no external CDN loaded at runtime") that survives to the assessed state? | C-2, C-0, P-3 | `SECURITY.md:85` "no external CDN"; `dashboard.html:15`; `scraper.py` dead path | guide / map-DEBUFF-2,5 |
| QB-docs-03 | Does the committed LLM-wiki keep its **one grounding rule** (select/condense/connect, never assert past sources) with `path:line` cites, `[[backlinks]]`, `[synthesis]` tags — and is `.last_ingest_sha` honestly held at sentinel (no false code-pass claim)? | P-3, W-2, S-3 | `SCHEMA.md:74-81`; `log.md:36-42`; `index.md:39-45` | guide (KEEP-verify) |
| QB-docs-04 | Do install docs disclose **progressively** (user path clean; Chromium ~150 MB lifted out of base prerequisite; eval-stack ~3.2 GB HF opt-in threaded), or fold dev/PDF needs into the user path? | D-6, A-2, A-1 | `docs/install.md:26-30,61-64`; `non-dependency-downloads.md:34-81`; missing `docs/eval-stack-install-guide` | guide / AL-6 / x-ref QB-sec-05 |
| QB-docs-05 | Can a stranger land in `docs/`, follow `llms.txt`/README→wiki, and reach an **accurate self-description** with working `path:line` cites — the legible public/internal boundary (A-2)? | P-3, A-2, A-4 | `llms.txt` (root); `docs/wiki/index.md`; README→wiki path | guide (BOOST-verify) |
| QB-docs-06 | When WS-4b code cold-ingest runs, does the **grounding rule hold at module scale** and does `.last_ingest_sha`→HEAD **rot-detection actually fire** post-ingest? | P-3, W-2 | `index.md:39-45` (code not ingested); `.last_ingest_sha` vs HEAD | guide (WATCH) / map §3 WS-4b |
| QB-docs-07 | Will governance extraction leave **exactly one home per rule** (cite-don't-restate, no second copy) while preserving agent rule-access via `@import`? | W-2, C-0 | `SCHEMA.md:34-48` (D5); `governance-extraction.md:45-52` | guide / x-ref QB-gov-05 |

---

## Domain 8 — Governance, memory & incubation (`gov`)

| ID | Question | Charter trace | Where to look | Source |
|---|---|---|---|---|
| QB-gov-01 | Are the **two live W-1 collisions** structurally closed — worktree-aware branch detection and a per-session/per-worktree-scoped approval marker — or still global/worktree-blind in code? | W-1, R2-11 | `require-feature-branch.sh:36`; `check-plan-approved.sh:6`; `cleanup-plan-on-merge.sh:28` | guide / R2-11 / brief-C7 |
| QB-gov-02 | Is CONTRIBUTING's multi-agent section still titled **"Future:"** (stale serial-session framing R2-11 directed retired), and does any doc codify the real multi-altitude parallelism with isolation rules (worktree-per-session, global-state ownership, branch ownership)? | W-1 | `CONTRIBUTING.md:219`; AGENTS.md serial close-out | guide / R2-11 / brief-C7 / map-DEBUFF-3 |
| QB-gov-03 | Does a **W-4 maturity metric** exist for any of the five incubants, or is extraction trigger-language only (maturity "TBD — review to propose")? | W-4 | `RELEASE_ARC`/PRODUCT_SHAPE extraction notes; system-model | guide / map-BOOST-4(relates) |
| QB-gov-04 | Is the **operator-stack triad** (memory→context, governance→posture, operator-LLM) given a named **governance interface** in the v1.0.7 assistant design, or is governance→assistant absent (serving dev agents + wiki-lint only)? | W-2, A-2, A-4 | `system-model.md` Memory/Governance/Operation; v1.0.7 assistant design; `governance-extraction.md` | guide / brief-A5 / R2-10 |
| QB-gov-05 | Does governance extraction lift the scattered hard rules into **one canonical home** (`docs/governance/charter.md`) preserving agent rule-access via `@import` — without spawning a second copy of any rule? | W-2, C-0 | `governance-extraction.md:45-52`; `SCHEMA.md:34-48` | guide / map §3 v1.0.7 / x-ref QB-docs-07 |
| QB-gov-06 | Are the **enforced blocker hooks** real (PreToolUse `exit 2`, registered) and honestly separated from witness-class nudges and tribal-only prose rules (PROMPT_VERSION bump, new-dep→pyproject+CHANGELOG, close-out pre-sweep, handoff reproduction)? | C-0, E-1, T-C | `.claude/settings.json:15-95`; `wiki-freshness-reminder.sh:59` (exits 0); AGENTS.md tribal rules | guide (KEEP/WATCH-verify) |
| QB-gov-07 | Does the **amendment ceremony** exist as written governance (dated entry + CHANGELOG + owner sign-off + compliance-agent witness flag), with a witness-class drift report as its enforcement precedent? | C-0(amendment), E-1 | charter "Amendment ceremony" L338-344; `wiki-freshness-reminder.sh` witness precedent | guide / charter amendment clause |
| QB-gov-08 | Is the **agent-station** dependency (W-3 canary = v1.1.0 GitHub integration) tracked with a fallback posture, given it is an unbuilt product the maintenance story routes through? | W-3, D-4 | RELEASE_ARC post-public lanes; R2-8; T8 | guide (WATCH) / brief-A4,M4 / R2-8 |

---

## Cut list (candidates traced to NO charter statement, or already ruled — no silent drops)

| Cut candidate | Origin | One-line reason |
|---|---|---|
| "Should sartor. ship an opt-in PII-scrubbed quality-export channel?" | brief-C1/M1; interview Q9 | RECANTED at R2-1 ("the docs are right, it's not worth it"); the no-telemetry promise stands unqualified — no charter clause supports a question, decided. |
| "Does sartor. support a coach/headhunter multi-client mode?" | brief-C2/C5/M5; interview Q4 | RULED out of scope at R2-2; single-tenant multi-client deliberately neither built nor documented — no charter clause to assess against. |
| "Should non-ATS templates ship bundled behind a visible flag?" | brief-C4/M8; tension T4 | RULED categorical at R2-3 (ATS-safe all the time; user edits the produced doc) — the only residual (escape-hatch wording) is already QB-vision-03; the flag-semantics question is decided. |
| "Vendor Chart.js / fix the CDN load." | AL-4 / PX-01 | Already RULED (fix v1.0.6); prescription decided. Reframed as verify-landed inside QB-sec-04 — no separate decide-question. |
| "Re-wire the dead profile/website scrape." | AL-5 / PX-02 | Already RULED (re-wire v1.0.6); decided. Verify-landed folded into QB-sec-04. |
| "Correct `jd_url`/JD-URL-fetch docs to two-class enumeration." | AL-7 / PX-03 | Already RULED (docs fix v1.0.6); decided. The live doc-drift *verification* survives as QB-docs-01/QB-vision-07 (still assessable); the prescription itself is not re-questioned. |
| "Is the HF model download a charter violation?" | AL-6 | RULED sanctioned power-user opt-in under D-6; not a violation. The surviving assessable question (is D-6 bundling/disclosure honored?) is QB-sec-05 — the violation-framing is cut. |
| "Adopt a two-tier constitution as proposed in R2-4?" | brief / R2-4 | Proposal REJECTED as offered (R2-4); the grounded enumeration was delivered and resolved in R2-Continued. The live residue (claims-tier flatness in vision docs) is QB-vision-01; the proposal-as-asked is decided. |
| "Provider-agnostic eval re-baseline timing/floors?" | brief-A3; tension T3; R2-7 | DIRECTION SET (R2-7: benchmark OSS models per call-kind, publish, ship tooling, no refusal floor; timing as-arc, post-public). No v1.1.0-scoped charter obligation to assess at the pin — deferred lane, not a current gap. |
| "ATS-score / resume-efficacy badge?" | brief-C-research | Charter + brief explicitly say do NOT badge (vendor marketing, no credible measure); no charter clause supports pursuing it — untraceable as an excellence question. |
| "SLSA / PyPI Trusted Publishing / coverage-% badge now?" | brief-C-table | Brief rules these post-public/theater "until artifacts ship" (users clone today); no v1.1.0 charter obligation — out of assessed scope. |
| "90-day stars/social-sharing success measurement mechanism?" | interview Q7; brief-M2 | Accepted as largely **unobservable by design** (R2-1, M-3 "not gates"); C-2 forecloses any measurement channel — nothing assessable to ask. |

---

## Coverage-balance note

Scrutiny concentrates, as the charter's severity inputs predict, on the
**machine-enforceability of the two truly-inviolable clauses** and on the
**S-1 PII fear**: **C-2 (egress)** is the single most-questioned clause
(QB-qe-rel-03, QB-sec-01, QB-sec-04, QB-docs-01, QB-docs-02, QB-vision-07,
plus the C-2(ii)/D-6 carve-out), and **C-6 (deterministic boundary)** carries
three convergent "is it enforced by construction?" questions (QB-arch-01/02,
QB-qe-rel-06) — appropriate, since C-0 makes "categorical claim without a
deterministic enforcer" the cardinal sin. **E-2** (the a11y taxonomy + badge
set) and **S-3 / M-2** (explainability, first-run, real-data exercise) are the
next-densest, matching the owner's self-named furthest-below-bar area and the
T-D unexercised-machinery gap. **AL-1..AL-7 are each represented**: AL-1→
QB-eval-01; AL-2→QB-exp-a11y-02; AL-3→QB-exp-a11y-03; AL-4/AL-5→QB-sec-04;
AL-6→QB-sec-05/QB-docs-04; AL-7→QB-docs-01. Every BOOST/DEBUFF map candidate
has a verifying question (BOOST-1..9 and DEBUFF-1..8 each cited above).

**Lightly-scrutinized clauses (one question each — flagged, not zero):** P-1
(preamble identity, folded into QB-vision-08), P-5 (kill conditions — touched
only obliquely via the provider-agnostic cut and QB-vision-02's grounding
thesis), C-4 (candidate-stays-in-control — present but always as a secondary
trace: QB-exp-a11y-02/09, QB-eval-06, QB-arch-07), and A-3 (builders — only
QB-vision-06). **Clauses with ZERO questions (flagged, by design):** **P-5**
(kill conditions: grounding-infeasibility / superseded-by-better-open-project)
— no decidable artifact exists to assess at the pin, so it is intentionally
unquestioned, not overlooked; **M-3** (90-day post-public hopes) — explicitly
unobservable-by-design (C-2), every candidate question cut; **D-2** (provider-
agnostic planned amendment) — direction-set, post-public lane, deliberately
deferred from this pin's assessment. **T-A** (per-user-excellence trade) and
**E-1** (pursue-every-badge tempered) are framing/severity inputs rather than
assessable surfaces; they appear as *traces* throughout but mint no standalone
question — flagged here so their absence reads as intentional.

---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Round-2 Verification Brief

> Produced by a three-agent fan-out between interview Rounds 1 and 2:
> (1) owner-answers vs repo docs, (2) owner-answers vs RELEASE_ARC, (3)
> external badge/certification research. All doc citations at `c6e0437`.
> This brief feeds Round 2 questions and, later, the Phase 2 question bank
> and Phase 4 release-pass plan. Agent-produced; findings below are
> *hypotheses for the owner*, not assessment conclusions.

## A. Owner vs docs — contradictions (C1–C11)

| ID | Divergence | Key citation | Severity |
|---|---|---|---|
| C1 | Q9 opt-in quality export vs SECURITY.md's categorical "No telemetry … **(and never will, by design)**" | SECURITY.md §Threat model L54-56; vision.md L89-93; README L127 | real-conflict |
| C2 | Q10 "single-tenant — negotiable" + Q4 coach/headhunter channel vs THREE docs in terminal language ("we won't" / "no plans" / "will not build") | vision.md L278-280; SECURITY.md L22-25; PRODUCT_SHAPE §8 L465-467 | real-conflict |
| C3 | Q10 "Anthropic-only will go away" vs vision.md won't-cross framing + SECURITY.md hard-coded egress; PRODUCT_SHAPE already plans providers at 1.1.x while owner says v2.x.x — docs disagree with each other too | vision.md L75-78,118; SECURITY.md L38-41,56-59; PRODUCT_SHAPE §11.4 L733-737 | drift |
| C4 | Q10 flagged non-ATS escape hatch vs vision.md heading "ATS-safety is the product" + categorical retirement rule | vision.md L57-63, L250-259 | real-conflict |
| C5 | the coach/headhunter business audience appears in ZERO repo docs; identity sentence "one person, one machine, one job at a time" structurally excludes it | vision.md L41-43, L16-19 | drift |
| C6 | Owner's success metric (interviews; the product's literal name) written nowhere as a success criterion — outcome exists only as a deferred v2 feature | vision.md L46-72; PRODUCT_SHAPE §4 L133-139 | drift |
| C7 | Q20 routine multi-altitude agent parallelism vs CONTRIBUTING's "Future: multi-agent identity" framing + AGENTS.md serial close-out model | CONTRIBUTING L50, L219-226; AGENTS.md L75-85 | real-conflict |
| C8 | vision.md presents ALL constraints as one uniform won't-cross tier; Q10 reveals only two are actually inviolable — the doc overstates ~2/3 of its own constitution | vision.md L75-174 | drift |
| C9 | Q18 agent-station maintenance vehicle vs CONTRIBUTING's prescribed identity pathway (Actions GITHUB_TOKEN → GitHub App, no per-agent PATs); SECURITY.md's 5-business-day vuln response rests on it | CONTRIBUTING L219-226; SECURITY.md L134-135 | drift |
| C10 | Q1 "only egress is the llm calls" undercounts: SECURITY.md enumerates three egress classes (Anthropic, profile scrape, pasted-JD fetch); vision/README say two | SECURITY.md L56-59 | wording-only |
| C11 | Q12 wants a badge-backed public a11y bar; vision goals/constraints and README badge surface are completely silent on a11y (zero badges of any kind) | vision.md L46-174; README L1-20 | drift |

**Charter anchors (strong agreements):** grounding/no-invention as core (Q1/Q2 ↔ vision Goal 1 + system-model "one law"); deterministic boundary inviolable (Q10 ↔ vision L127-149, AGENTS.md); local-first identity + rationale (Q10/Q11 ↔ vision L81-93); human-control gates (Q1 ↔ vision Goal 3); no direct ATS integration (Q6 ↔ vision L39, PRODUCT_SHAPE L267-270); interview-outcome loop already diagnosed as "the killer-feature gap" (PRODUCT_SHAPE §4); "a product that knows itself" verbatim in PRODUCT_SHAPE §11.4; operator-stack triad maps 1:1 onto system-model.md's Memory/Governance/Operation; first-15-min path matches README's six-step wizard; Q14's three exhibits are precisely the repo's deepest investments; real-data eval gap admitted on both sides; governance-accelerates thesis matches system-model.

## B. Owner vs release arc — misalignments (A1–A7) and absences (M1–M8)

- **A1.** Q17 tag-confidence evidence (personal use, no bugs, interviews, tuning loop exercised, readable metrics) — NONE is a written v1.1.0 criterion; only "User judges it showcase-ready" catches it. Arc builds the machinery (Sprint 6.0 real-data capture, PV-1/PV-2) but gates existence, not lived evidence. (RELEASE_ARC §Phase 5 tag criteria)
- **A2.** Fresh-clone <5 min (arc) vs owner's ~15-min clarify-inclusive first run with a QUALITY clause ("surprisingly good") — irreconcilable as written; the 5-min bar implicitly forces skip-clarify, undercutting the experience Q5 demands. (§Phase 5; RELEASE_CHECKLIST risk #4)
- **A3.** Provider abstraction scoped purely as analyzer.py work at 1.1.1-candidate; owner says v2.x.x; NOTHING covers the eval consequences (baselines pin sonnet/haiku snapshots; the rubric judge IS Haiku; PV-2 thresholds calibrated on Sonnet output; TUNING_LOG floors model-specific). Q2's grounding kill-condition makes weak local models existential. (§Post-public 1.1.1)
- **A4.** Post-public arc = feature epics only; assumes the current owner-driven model. agent-station appears nowhere; no issue-triage/response-promise/community-PR/security-report operations item exists. (§Post-public)
- **A5.** Operator-stack triad: memory→assistant wired (recall/ extraction contract); governance→assistant ABSENT — v1.0.7 governance extraction serves dev agents + wiki-lint only; no item makes the constitution direct the assistant's runtime posture. No compliance agent anywhere in the arc. (§Phase 4.7)
- **A6.** Q15 explainability: Sprint 6.5 + doc-assistant attack it, but the deep tuning-loop narrative lives in dev docs (project policy keeps it out of user docs); no item makes metrics lay-readable; no tag criterion measures the explainability OUTCOME. (§Phase 4.5 Sprint 6.5; §Phase 4.7)
- **A7.** A11y gate = axe serious/critical on ~9 surfaces, wizard Steps 2/5/6 + modals explicitly deferred; nothing between now and v1.1.0 raises it to anything badge-able. (§Phase 4.5 Sprint 6.3)

**Missing from arc entirely (M1–M8):** M1 Q9 opt-in export channel (zero hits); M2 any post-public success observation (Q7's stars/sharing unobservable); M3 Q17 evidence as written criteria; M4 agent-station or ANY named maintenance vehicle + fallback; M5 the business/coach audience; M6 compliance agent (rulebook half only); M7 badging/external-measures sweep (S20); M8 ATS-flag semantics (T4/C4).

**Notable alignments:** user-owned tag pacing; functional completeness front-loaded pre-public; B.8 Parts 1+2 instrument interviews-as-measure; the three "whoa" exhibits = the arc's three deepest investments; Q16 fears structurally mitigated (PII risk register, walkthrough cycles); Sprint 6.4 maps onto the 15-minute path; modularize-in-place extraction practice already real.

## C. External measures research (badge landscape)

### Accessibility proposal (the Q12 "push me" answer)
- **Bar: WCAG 2.2 Level AA, full-app scope** (incl. /_dashboard), declared at v1.1.0 via a dated, methodology-backed self-evaluation. 2.2 is the current W3C Recommendation (Oct 2023), supersedes 2.1, exceeds every regulatory floor (508/EN 301 549 cite 2.0/2.1); the 9 new 2.2 criteria are unusually cheap for this app (no auth, no drag, consistent single-page layout) — material new work is only 2.5.8 Target Size (24px) and 2.4.11 Focus Not Obscured.
- **Found defect: the a11y/UX gate silently SKIPS in CI** — ci.yml never installs Chromium, so `pytest -m ux` skips by design and the gate runs only on the maintainer's machine. First fix: dedicated CI job installing Chromium, `pytest -m ux` as a required check.
- **CI mechanisms:** widen axe to ALL violations with runOnly tags [wcag2a, wcag21aa, wcag22aa, best-practice] + committed allowlist-with-justification; keyboard-only wizard traversal tests (Tab order, activation parity, no traps, Escape/focus-return, skip-link); focus-management assertions (panel-switch focus, follow-up-question focus, :focus-visible, 2.4.11); 320px reflow + text-spacing tests; token-level contrast tests once the design system formalizes; prefers-reduced-motion honored + asserted.
- **Manual norm:** per-release 2–4 h pass — NVDA+Chrome (+NVDA+Firefox spot-check), Narrator secondary, keyboard-only full wizard incl. iterate-clarify, 200%/400% zoom, error-announcement check; logged in a committed `docs/a11y/audit-log.md` (date, NVDA version, panels). JAWS not justified at solo budget.
- **Public artifact:** NO legitimate WCAG badge program exists (overlay-vendor "badges" are anti-credible). Credible stack: (1) at v1.1.0, an Accessibility Conformance Statement via the free W3C WCAG-EM Report Tool, published as ACCESSIBILITY.md, linked from README, citing the CI gate + audit log as evidence; (2) post-public on demand, ACR on VPAT 2.5 (self-asserted, only valuable if procurement asks); (3) stretch, a third-party audit (Deque/TPGi; ~low-thousands–$15k, unverified) as a funded/community milestone.
- **Effort:** CI mechanisms 2–4 days; first WCAG-EM evaluation + statement 1–2 days; 2–4 h/release recurring; $0.

### Other measures — recommended commitment set
| Measure | Certifies | Effort | Enforcement value | Rec |
|---|---|---|---|---|
| OpenSSF Best Practices badge (passing) | Public itemized FLOSS-practice self-cert (repo is unusually close already) | hours | moderate-continuous (public dated answers; 14-day vuln-response commitment) | **v1.1.0** |
| OpenSSF Scorecard + badge | ~18 machine-checked supply-chain heuristics, re-scored automatically | days | **HIGH continuous — best available "keeps us honest"**; forces SHA-pinned actions, Dependabot, branch protection, CodeQL; solo ceiling ~7–8 (Code-Review penalizes solo merges — document honestly, don't game) | **v1.1.0** |
| REUSE compliance (FSFE) + live badge | Every file machine-readable SPDX licensing; forces declaring vendored axe.min.js (MPL-2.0, not MIT) | hours | real-continuous (`reuse lint` in CI is binary) | **v1.1.0** |
| GitHub Private Vulnerability Reporting + GHSA/CVE (GitHub-as-CNA) | Working standard disclosure channel + real CVE capability | hours | moderate-continuous; live before day one public | **v1.1.0** |
| Lockfile + Dependabot/Renovate (Scorecard-checked) | Reproducible resolution + automated security updates. Decision needed: lock governs dev/CI only (recommended) vs user installs | days | high-continuous | **v1.1.0** |
| Network-egress falsifiability test + PRIVACY.md | No privacy certification exists for this class — substitute is a committed socket/route-allowlist CI test (only api.anthropic.com + user-initiated scrape) + exact what-leaves-the-machine doc | days | egress test = real continuous enforcement | **v1.1.0** |
| Coverage badge (Codecov, patch-coverage gate) | Honest config = failing patch-coverage check, not vanity % (analyzer.py is eval-measured, not coverage-measured) | hours | high IF gating; theater if badge-only | post-public |
| SLSA L2–3 attestations; PyPI Trusted Publishing + PEP 740 | Artifact provenance — zero value until artifacts ship (users clone today) | hours | high once publishing exists | post-public |
| Reproducible builds; docs-quality badge | No badge exists / subsumed by SLSA; docs discipline already exceeds external bars | — | — | skip |

### Areas with NO credible external measure (internal evidence must carry)
LLM grounding/fabrication quality (publish eval methodology + headline scores, labeled internal); prompt-eval rigor (public TUNING_LOG is the credibility move); privacy/local-first (falsifiable egress test is the substitute); docs quality; resume-efficacy claims (do NOT badge; "ATS score" checkers are vendor marketing); LLM cost transparency (/bench data worth publishing); bus-factor=1 (acknowledge in README/GOVERNANCE, don't game); UX-beyond-a11y.
